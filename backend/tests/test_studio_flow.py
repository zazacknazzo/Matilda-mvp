"""T10 real HTTP/science/storage journey. Only Gemini is replaced at its boundary."""
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.studio_preview import get_provider, owner
from app.services.studio.runtime_repository import StudioRepository
from app.schemas.studio import EnrichmentPreview, GenerateRequest
from app.studio.ports import SESSION_COOKIE, ProviderFailure, POLICY, RepositoryConflict
from studio_flow_provider import FlowProvider
from test_studio_preview import ORIGIN, REQUEST


@pytest.fixture
def flow(client):
    provider = FlowProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    yield provider
    app.dependency_overrides.clear()


def create(client):
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 201, response.text
    return response.json()


def review(client, value, *, accept=True):
    body = {'review_revision': value['review_revision'], 'approved_objectives': ['Explicar a edição genética.'],
            'decisions': [{'suggestion_id': s['id'], 'status': 'accepted' if accept and i == 0 else 'rejected'} for i, s in enumerate(value['suggestions'])]}
    response = client.post(f"/api/studio/previews/{value['preview_id']}/review", json=body, headers=ORIGIN)
    assert response.status_code == 200, response.text
    return response.json(), body


def generation(value):
    return {'preview_id': value['preview_id'], 'review_revision': value['review_revision'],
            'accepted_suggestion_ids': [s['id'] for s in value['suggestions'] if s['status'] == 'accepted']}


def generate(client, value, key='flow-key'):
    return client.post('/api/studio/generate', json=generation(value), headers={**ORIGIN, 'Idempotency-Key': key})


def test_full_crispr_journey_resume_bundle_identity_and_replay(client, flow):
    initial = create(client)
    assert len(initial['suggestions']) >= 2
    saved, body = review(client, initial)
    path = f"/api/studio/previews/{initial['preview_id']}"
    assert saved['review_revision'] == 1
    assert client.get(path).json() == saved
    stale = client.post(path + '/review', json=body, headers=ORIGIN)
    assert stale.status_code == 409
    assert client.get(path).json() == saved
    response = generate(client, saved)
    assert response.status_code == 201, response.text
    bundle = response.json()
    assert bundle['preview_id'] == saved['preview_id']
    assert bundle['review_revision'] == saved['review_revision']
    assert bundle['metadata']['learning_objectives'] == saved['approved_objectives']
    allowed = {eid for s in saved['suggestions'] if s['status'] == 'accepted' for eid in s['evidence_ids']}
    assert {r['id'] for r in bundle['references']} <= allowed
    assert flow.lesson_requests[0].material['accepted_suggestions'][0]['id'] == saved['suggestions'][0]['id']
    assert len(flow.lesson_requests[0].material['accepted_suggestions']) == 1
    result_path = '/api/studio/lessons/' + bundle['lesson_bundle_id']
    with TestClient(app) as resumed:
        resumed.cookies.update(client.cookies)
        response = resumed.get(result_path)
        assert response.status_code == 200
        assert response.json() == bundle
        assert response.headers['cache-control'] == 'no-store'
        assert 'set-cookie' not in response.headers
    replay = generate(client, saved)
    assert replay.status_code == 200, replay.text
    assert replay.json() == bundle
    assert 'set-cookie' not in replay.headers
    assert len(flow.lesson_requests) == 1
    assert client.get(path).json()['last_lesson_bundle_id'] == bundle['lesson_bundle_id']
    export = client.get(result_path + '/export?format=markdown')
    assert export.status_code == 200
    assert 'attachment' in export.headers['content-disposition']
    assert len(flow.lesson_requests) == 1


def test_reject_all_has_no_historical_attributions(client, flow):
    saved, _ = review(client, create(client), accept=False)
    response = generate(client, saved)
    assert response.status_code == 201, response.text
    assert response.json()['references'] == []
    assert all(slide['evidence_ids'] == [] for slide in response.json()['slides'])
    assert flow.lesson_requests[0].material['authorized_evidence'] == {}


def test_pending_objectives_invalid_ids_and_locked_fields(client, flow):
    initial = create(client)
    assert generate(client, initial).status_code == 409
    path = f"/api/studio/previews/{initial['preview_id']}/review"
    body = {'review_revision': 0, 'approved_objectives': ['Explicar.'], 'decisions': []}
    partial = client.post(path, json=body, headers=ORIGIN)
    assert partial.status_code == 200
    assert generate(client, partial.json()).status_code == 409
    for mutation in ({'approved_objectives': []}, {'historical_claim': 'forged'}, {'decisions': [{'suggestion_id': initial['suggestions'][0]['id'], 'status': 'accepted', 'evidence_ids': ['forged']}]}):
        response = client.post(path, json={**body, 'review_revision': 1, **mutation}, headers=ORIGIN)
        assert response.status_code == 422, response.text
    assert client.get(path.removesuffix('/review')).json()['review_revision'] == 1
    assert flow.lesson_requests == []


def test_session_origin_and_expiry(client, flow, monkeypatch):
    saved, _ = review(client, create(client))
    bundle_response = generate(client, saved)
    assert bundle_response.status_code == 201, bundle_response.text
    bundle = bundle_response.json()
    path = f"/api/studio/previews/{saved['preview_id']}/review"
    lesson_path = '/api/studio/lessons/' + bundle['lesson_bundle_id']
    with TestClient(app) as other:
        assert other.get(lesson_path).status_code == 404
        assert other.post(path, json={'review_revision': 1, 'decisions': [], 'approved_objectives': ['Explicar.']}, headers=ORIGIN).status_code == 404
        assert generate(other, saved).status_code == 404
    assert client.get(lesson_path, headers={'Origin': 'https://evil.invalid'}).status_code == 422
    assert client.post(path, json={}, headers={'Origin': 'https://evil.invalid'}).status_code == 422
    assert client.post('/api/studio/generate', json=generation(saved), headers={'Origin': 'https://evil.invalid', 'Idempotency-Key': 'x'}).status_code == 422
    db = sqlite3.connect(__import__('os').environ['MATILDA_DB'])
    db.execute("UPDATE studio_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
    db.commit()
    db.close()
    assert client.get(lesson_path).status_code == 404
    assert generate(client, saved).status_code == 404


@pytest.mark.parametrize('poison,tokens,code', [(True, 400, 'invalid_generation'), (False, 12001, 'input_too_large')])
def test_real_generation_rejects_evidence_and_token_overruns(client, flow, poison, tokens, code):
    saved, _ = review(client, create(client))
    flow.poison, flow.tokens = poison, tokens
    response = generate(client, saved)
    assert response.status_code in (413, 502), response.text
    assert response.json()['code'] == code
    current = client.get(f"/api/studio/previews/{saved['preview_id']}").json()
    assert current['generation_status'] == 'failed'
    assert current['approved_objectives'] == saved['approved_objectives']
    assert current['last_lesson_bundle_id'] is None
    flow.poison, flow.tokens = False, 400
    assert generate(client, saved).status_code == 201


def test_body_caps_and_failure_preserve_forensics(client, flow, monkeypatch):
    saved, _ = review(client, create(client))
    for path in (f"/api/studio/previews/{saved['preview_id']}/review", '/api/studio/generate'):
        response = client.post(path, content=b'x' * (POLICY.max_body_bytes + 1), headers={**ORIGIN, 'Idempotency-Key': 'body'})
        assert response.status_code == 413
    app.dependency_overrides.clear()
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    response = generate(client, saved)
    assert response.status_code == 503
    assert response.json()['code'] == 'studio_not_configured'
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/papers/10.1126/science.1231143').status_code == 200


def test_atomic_claim_blocks_review_and_preview_and_cleanup_recovers(client, flow):
    saved, _ = review(client, create(client))
    repo = StudioRepository()
    session = owner(client.cookies.get(SESSION_COOKIE))
    request = GenerateRequest.model_validate(generation(saved))
    stamp = datetime.now(timezone.utc)
    claim = asyncio.run(repo.claim_generation(session_id=session, request=request, idempotency_key='atomic', now=stamp.isoformat()))
    assert claim.claim_id
    with pytest.raises(RepositoryConflict):
        asyncio.run(repo.claim_generation(session_id=session, request=request, idempotency_key='parallel', now=stamp.isoformat()))
    assert client.post(f"/api/studio/previews/{saved['preview_id']}/review", json={'review_revision': 1, 'decisions': [], 'approved_objectives': ['Explicar.']}, headers=ORIGIN).status_code == 409
    assert client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN).status_code == 409
    later = (stamp + timedelta(seconds=POLICY.generation_backend_seconds + POLICY.recovery_grace_seconds + 1)).isoformat()
    asyncio.run(repo.cleanup_expired(now=later))
    recovered = asyncio.run(repo.get_preview(session_id=session, preview_id=saved['preview_id'], now=later))
    assert recovered.generation_status == 'failed'
    assert recovered.approved_objectives == saved['approved_objectives']


def test_changed_review_same_key_conflicts_and_immutable_bundle_survives(client, flow):
    saved, _ = review(client, create(client))
    first = generate(client, saved)
    assert first.status_code == 201, first.text
    revised, _ = review(client, client.get(f"/api/studio/previews/{saved['preview_id']}").json(), accept=False)
    assert generate(client, revised).status_code == 409
    result = client.get('/api/studio/lessons/' + first.json()['lesson_bundle_id'])
    assert result.json() == first.json()
    assert generate(client, revised, key='new-review').status_code == 201

def test_official_gemini_sdk_both_stages_only_google_transport_is_simulated(client, flow, monkeypatch):
    import httpx
    from types import SimpleNamespace
    from app.integrations.gemini_client import GeminiProvider
    calls = []

    async def google(request):
        body = json.loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path.endswith(':countTokens'):
            return httpx.Response(200, json={'totalTokens': 600})
        material = json.loads(body['contents'][0]['parts'][0]['text'])
        stage = 'preview' if 'scientific_candidates' in material else 'lesson'
        result = await flow.complete(SimpleNamespace(stage=stage, material=material, prompt_version=f'studio-{stage}-v1'))
        return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [{'text': result.content.decode()}]}, 'finishReason': 'STOP'}],
            'modelVersion': 'gemini-controlled-sdk', 'usageMetadata': {'promptTokenCount': 600, 'candidatesTokenCount': 800, 'thoughtsTokenCount': 20}})

    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-never-render')
    app.dependency_overrides[get_provider] = lambda: GeminiProvider(transport=httpx.MockTransport(google))
    saved, _ = review(client, create(client))
    response = generate(client, saved)
    assert response.status_code == 201, response.text
    bundle = response.json()
    assert bundle['generation_metadata']['provider'] == 'gemini'
    assert bundle['generation_metadata']['model'] == 'gemini-controlled-sdk'
    assert bundle['generation_metadata']['output_tokens'] == 820
    assert 'test-key-never-render' not in response.text
    outputs = [body for path, body in calls if path.endswith(':generateContent')]
    assert len(outputs) == 2
    assert len(calls) == 4
    for body in outputs:
        assert not body.get('tools')
        assert body['generationConfig']['maxOutputTokens'] == 8000
        assert body['generationConfig']['responseMimeType'] == 'application/json'


def test_retention_removes_generated_project_without_damaging_forensics(client, flow):
    from app.services.storage import database_path
    saved, _ = review(client, create(client))
    response = generate(client, saved)
    assert response.status_code == 201, response.text
    assert client.post('/api/analyses', json={'doi': '10.1126/science.1231143'}).status_code == 201
    later = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    asyncio.run(StudioRepository().cleanup_expired(now=later))
    with sqlite3.connect(database_path()) as db:
        for table in ('lesson_projects', 'enrichment_previews', 'lesson_bundles', 'studio_scientific_snapshots', 'studio_generation_operations'):
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM analyses').fetchone()[0] == 1

def test_generation_quota_and_wrong_ids_use_real_admission(client, flow):
    saved, _ = review(client, create(client))
    invalid = generation(saved)
    invalid['accepted_suggestion_ids'] = ['foreign-suggestion']
    response = client.post('/api/studio/generate', json=invalid, headers={**ORIGIN, 'Idempotency-Key': 'invalid'})
    assert response.status_code == 409
    assert flow.lesson_requests == []
    for index in range(POLICY.generations_per_hour):
        response = generate(client, saved, key=f'quota-{index}')
        assert response.status_code == 201, response.text
        saved, _ = review(client, client.get(f"/api/studio/previews/{saved['preview_id']}").json())
    limited = generate(client, saved, key='over-limit')
    assert limited.status_code == 429
    assert limited.headers['retry-after'] == '3600'
    assert len(flow.lesson_requests) == POLICY.generations_per_hour


def test_t12_restart_preserves_t10_bundle_review_retention_and_same_key(client, flow):
    """The production M0 adapter and isolated T12 recovery agree after merging."""
    from app.services.studio.generation import GenerationService

    saved, _ = review(client, create(client))
    first = generate(client, saved, key='original').json()
    session = owner(client.cookies.get(SESSION_COOKIE))
    request = GenerateRequest.model_validate(generation(saved))
    clock = datetime.fromisoformat(saved['expires_at']) - timedelta(seconds=1)
    repository = StudioRepository()
    interrupted = asyncio.run(repository.claim_generation(
        session_id=session, request=request, idempotency_key='interrupted', now=clock.isoformat(),
    ))
    admitted = asyncio.run(repository.get_preview(session_id=session, preview_id=saved['preview_id'], now=clock.isoformat()))
    assert admitted.expires_at > saved['expires_at']
    # Reconstruct the adapter over the same real SQLite, without reseeding state.
    restarted = StudioRepository()
    clock += timedelta(seconds=POLICY.generation_backend_seconds + POLICY.recovery_grace_seconds - 1)
    assert asyncio.run(restarted.cleanup_expired(now=clock.isoformat())) == 0
    pending = asyncio.run(restarted.get_preview(session_id=session, preview_id=saved['preview_id'], now=clock.isoformat()))
    assert pending.generation_status == 'generating'
    clock += timedelta(seconds=1)
    recovered = asyncio.run(restarted.get_preview(session_id=session, preview_id=saved['preview_id'], now=clock.isoformat()))
    assert recovered.generation_status == 'failed'
    assert recovered.last_error.code == 'generation_timeout'
    assert recovered.suggestions == admitted.suggestions
    assert recovered.approved_objectives == admitted.approved_objectives
    assert recovered.source_documents == admitted.source_documents
    assert recovered.expires_at == admitted.expires_at
    assert recovered.last_lesson_bundle_id == first['lesson_bundle_id']
    previous = asyncio.run(restarted.get_lesson(session_id=session, lesson_bundle_id=first['lesson_bundle_id'], now=clock.isoformat()))
    assert previous.model_dump(mode='json') == first
    with pytest.raises(RepositoryConflict):
        asyncio.run(restarted.complete_generation(claim_id=interrupted.claim_id, bundle=previous, now=clock.isoformat()))
    assert len(flow.lesson_requests) == 1
    service = GenerationService(restarted, flow, restarted.scientific_authority, now=lambda: clock.isoformat())
    retried = asyncio.run(service.generate(session_id=session, request=request, idempotency_key='interrupted'))
    assert not retried.replayed
    assert retried.bundle.lesson_bundle_id != first['lesson_bundle_id']
    clock += timedelta(days=1)
    reopened = StudioRepository()
    replay_service = GenerationService(reopened, flow, reopened.scientific_authority, now=lambda: clock.isoformat())
    replay = asyncio.run(replay_service.generate(session_id=session, request=request, idempotency_key='interrupted'))
    assert replay.replayed and replay.bundle == retried.bundle
    assert replay.expires_at == retried.expires_at
    assert len(flow.lesson_requests) == 2
    assert asyncio.run(reopened.get_lesson(session_id='other-owner', lesson_bundle_id=replay.bundle.lesson_bundle_id, now=clock.isoformat())) is None
    assert asyncio.run(reopened.get_lesson(session_id=session, lesson_bundle_id=first['lesson_bundle_id'], now=clock.isoformat())) == previous
