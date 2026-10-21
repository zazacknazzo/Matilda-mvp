"""T05 HTTP seam: real science + SQLite, only the external provider is controlled."""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.lesson import LessonGenerationMetadata
from app.schemas.studio import EnrichmentPreview
from app.studio.ports import ProviderResult

ORIGIN = {'Origin': 'http://localhost:5173'}
MATERIAL = '  CRISPR-Cas9 permite discutir edição genética.\nPreservar este texto.  '
REQUEST = {'title': 'Edição genética', 'material_text': MATERIAL, 'concepts': ['CRISPR-Cas9']}


class PreviewProvider:
    """Only installed by tests through FastAPI dependency override."""
    def __init__(self):
        self.requests = []

    async def count_input_tokens(self, request):
        return 400

    async def complete(self, request):
        self.requests.append(request)
        source = request.material['source_documents'][0]
        matches = request.material['authorized_contributions']
        suggestions = []
        if matches:
            match = matches[0]
            suggestions.append({
                'contribution_id': match['contribution_id'],
                'concept_ids': match['concept_ids'][:1],
                'evidence_ids': match['evidence_ids'][:1],
                'source_anchor': {'source_document_id': source['id'], 'quote': source['content'], 'occurrence': 0},
                'pedagogical_rationale': 'Relacionar mecanismo molecular e análise documental.',
                'suggested_content': 'Compare a afirmação documental com o mecanismo apresentado no material.',
            })
        return ProviderResult(json.dumps({'suggested_objectives': ['Explicar a edição genética.'], 'suggestions': suggestions}).encode(), LessonGenerationMetadata(
            provider='test-external', model='controlled', prompt_version=request.prompt_version,
            schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(), duration_ms=1,
            input_tokens=400, output_tokens=80,
        ))


@pytest.fixture
def provider(client):
    from app.api.studio_preview import get_provider
    controlled = PreviewProvider()
    app.dependency_overrides[get_provider] = lambda: controlled
    yield controlled
    app.dependency_overrides.clear()


def test_text_creates_canonical_preview_and_survives_new_api_client(client, provider):
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 201, response.text
    preview = EnrichmentPreview.model_validate(response.json())
    assert preview.source_documents[0].content == MATERIAL
    assert preview.scientific_context.paper_ids == []
    assert preview.suggestions[0].status == 'pending'
    assert preview.suggestions[0].source_anchor.quote == MATERIAL
    reference = preview.evidence_references[0]
    assert preview.suggestions[0].historical_claim == reference.claim_supported
    assert reference.source_url.startswith('https://')
    assert len(reference.participants) > 1
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/api/studio' in cookie
    with TestClient(app) as resumed:
        resumed.cookies.update(client.cookies)
        saved = resumed.get('/api/studio/previews/' + preview.preview_id)
        assert saved.status_code == 200
        assert saved.json() == response.json()
    assert len(provider.requests) == 1


def test_provider_cannot_smuggle_new_ids_or_historical_text(client, provider):
    original_complete = provider.complete

    async def poisoned(request):
        result = await original_complete(request)
        payload = json.loads(result.content)
        payload['suggestions'][0]['historical_claim'] = 'Uma afirmação histórica inventada.'
        return ProviderResult(json.dumps(payload).encode(), result.metadata)

    provider.complete = poisoned
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 502, response.text
    assert response.json()['code'] == 'invalid_generation'
    project_id = response.json()['project_id']
    assert project_id
    provider.complete = original_complete
    retry = client.post('/api/studio/preview', json={**REQUEST, 'project_id': project_id}, headers=ORIGIN)
    assert retry.status_code == 201
    assert retry.json()['source_documents'][0]['content'] == MATERIAL


def test_sdk_transport_is_real_and_disables_tools(client, monkeypatch):
    """Exercise the official SDK; replace only its HTTP connection to Google."""
    import httpx
    from app.api.studio_preview import get_provider
    from app.integrations.gemini_client import GeminiProvider
    requests = []

    def google(request):
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if request.url.path.endswith(':countTokens'):
            return httpx.Response(200, json={'totalTokens': 600})
        material = json.loads(body['contents'][0]['parts'][0]['text'])
        match = material['authorized_contributions'][0]
        document = material['source_documents'][0]
        plan = {'suggested_objectives': ['Explicar o mecanismo.'], 'suggestions': [{
            'contribution_id': match['contribution_id'], 'concept_ids': match['concept_ids'][:1],
            'evidence_ids': match['evidence_ids'][:1],
            'source_anchor': {'source_document_id': document['id'], 'quote': 'CRISPR-Cas9', 'occurrence': 0},
            'pedagogical_rationale': 'Conferir a documentação.', 'suggested_content': 'Leia a evidência e compare os mecanismos.'}]}
        return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [{'text': json.dumps(plan)}]}, 'finishReason': 'STOP'}],
            'modelVersion': 'gemini-3.8-flash', 'usageMetadata': {'promptTokenCount': 600, 'candidatesTokenCount': 100, 'thoughtsTokenCount': 20}})

    monkeypatch.setenv('GEMINI_API_KEY', 'secret-test-never-render')
    app.dependency_overrides[get_provider] = lambda: GeminiProvider(transport=httpx.MockTransport(google))
    try:
        response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
        assert response.status_code == 201, response.text
        assert response.json()['generation_metadata']['provider'] == 'gemini'
        assert response.json()['generation_metadata']['output_tokens'] == 120
        generation = requests[-1][1]
        assert not generation.get('tools')
        assert generation['generationConfig']['responseMimeType'] == 'application/json'
        assert generation['generationConfig']['maxOutputTokens'] == 8000
        assert 'secret-test-never-render' not in response.text
        assert requests[0][0].endswith(':countTokens')
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('field,value', [
    ('contribution_id', 'invented'),
    ('evidence_ids', ['evidence-kariko-2005']),
    ('concept_ids', ['invented-concept']),
    ('source_anchor', {'source_document_id': 'foreign-document', 'quote': 'CRISPR', 'occurrence': 0}),
    ('source_anchor', {'source_document_id': 'keep', 'quote': 'not in the material', 'occurrence': 0}),
    ('source_anchor', {'source_document_id': 'keep', 'quote': 'CRISPR-Cas9', 'occurrence': 50}),
    ('researcher_ids', ['invented-researcher']),
])
def test_rejects_unauthorized_provider_references(client, provider, field, value):
    original = provider.complete

    async def poison(request):
        result = await original(request)
        payload = json.loads(result.content)
        if field == 'source_anchor' and value['source_document_id'] == 'keep':
            value['source_document_id'] = request.material['source_documents'][0]['id']
        payload['suggestions'][0][field] = value
        return ProviderResult(json.dumps(payload).encode(), result.metadata)

    provider.complete = poison
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 502, response.text
    assert 'preview_id' not in response.json()


def test_isolation_retention_and_new_preview_keep_prior_original(client, provider, monkeypatch):
    import app.api.studio_preview as api
    current = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(api, 'now', lambda: current.isoformat())
    first = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN).json()
    path = '/api/studio/previews/' + first['preview_id']
    with TestClient(app) as other:
        assert other.get(path).status_code == 404
        denied = other.post('/api/studio/preview', json={**REQUEST, 'project_id': first['project_id']}, headers=ORIGIN)
        assert denied.status_code == 404
        assert first['project_id'] not in denied.text
    from datetime import timedelta
    current += timedelta(days=2)
    resumed = client.get(path)
    assert resumed.status_code == 200
    assert 'set-cookie' not in resumed.headers
    assert resumed.json()['expires_at'] == first['expires_at']
    newer = client.post('/api/studio/preview', json={**REQUEST, 'title': 'Novo tema', 'material_text': 'CRISPR em outro texto.', 'project_id': first['project_id']}, headers=ORIGIN)
    assert newer.status_code == 201, newer.text
    previous = client.get(path).json()
    assert previous['source_documents'][0]['content'] == MATERIAL
    assert previous['project']['title'] == REQUEST['title']
    assert previous['expires_at'] == newer.json()['expires_at']
    current += timedelta(days=7, seconds=1)
    assert client.get(path).status_code == 404
    assert client.get('/api/studio/previews/' + newer.json()['preview_id']).status_code == 404


@pytest.mark.parametrize('payload', [
    {'title': 'Só tema'}, {**REQUEST, 'material_text': 'x' * 20001},
    {**REQUEST, 'duration_minutes': True}, {**REQUEST, 'unknown': 'field'},
    {**REQUEST, 'concepts': ['x'] * 21}, {**REQUEST, 'objectives': ['x' * 301]},
    {**REQUEST, 'doi': 'https://internal.invalid/secret'},
])
def test_invalid_input_never_calls_provider(client, provider, payload):
    response = client.post('/api/studio/preview', json=payload, headers=ORIGIN)
    assert response.status_code == 422
    assert response.json()['code'] == 'invalid_input'
    assert provider.requests == []


def test_body_limit_and_origin_are_checked_before_ai(client, provider):
    assert client.post('/api/studio/preview', content=b' ' * (128 * 1024 + 1), headers=ORIGIN).status_code == 413
    assert client.post('/api/studio/preview', json=REQUEST).status_code == 422
    assert client.post('/api/studio/preview', json=REQUEST, headers={'Origin': 'https://evil.invalid'}).status_code == 422
    assert client.post('/api/studio/preview', content=b'{invalid', headers=ORIGIN).status_code == 422
    assert provider.requests == []


@pytest.mark.parametrize('material', ['Trigonometria e triângulos.', 'Imunogenicidade isolada.'])
def test_no_coverage_is_explicit_and_does_not_invent_science(client, provider, material):
    response = client.post('/api/studio/preview', json={'title': 'Aula', 'material_text': material}, headers=ORIGIN)
    assert response.status_code == 201, response.text
    preview = response.json()
    assert preview['suggestions'] == [] and preview['evidence_references'] == []
    assert any('Sem cobertura' in limitation for limitation in preview['limitations'])


@pytest.mark.parametrize('reason,status,retryable', [
    ('timeout', 504, True), ('unauthorized', 503, False), ('rate_limited', 503, True),
    ('blocked', 502, False), ('truncated', 502, True), ('unavailable', 503, True),
])
def test_provider_errors_preserve_project_and_allow_explicit_retry(client, provider, reason, status, retryable):
    from app.studio.ports import ProviderFailure
    original = provider.complete

    async def fail(request):
        raise ProviderFailure(reason)

    provider.complete = fail
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == status, response.text
    error = response.json()
    assert error['retryable'] is retryable and error['project_id']
    provider.complete = original
    retry = client.post('/api/studio/preview', json={**REQUEST, 'project_id': error['project_id']}, headers=ORIGIN)
    assert retry.status_code == 201
    assert retry.json()['source_documents'][0]['content'] == MATERIAL


def test_no_key_affects_studio_only(client, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 503
    assert response.json()['code'] == 'studio_not_configured'
    assert response.json()['project_id']
    analysis = client.post('/api/analyses', json={'doi': '10.1126/science.1231143'})
    assert analysis.status_code == 201
    assert analysis.json()['contributions']


def test_input_token_limit_blocks_paid_generation(client, provider):
    async def excessive(request):
        return 12001
    provider.count_input_tokens = excessive
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 413
    assert provider.requests == []


def test_five_preview_quota_is_persisted_across_clients(client, provider):
    for _ in range(5):
        assert client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN).status_code == 201
    with TestClient(app) as restarted:
        restarted.cookies.update(client.cookies)
        response = restarted.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
        assert response.status_code == 429
        assert int(response.headers['Retry-After']) > 0
    assert len(provider.requests) == 5


def test_concurrent_requests_are_admitted_atomically(client, provider):
    import asyncio
    import httpx
    original = provider.complete

    async def journey():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def blocked(request):
            entered.set()
            await release.wait()
            return await original(request)

        # Establish a real session; the following POSTs share its cookie.
        seed = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
        assert seed.status_code == 201
        provider.complete = blocked
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver', cookies=client.cookies) as api:
            first = asyncio.create_task(api.post('/api/studio/preview', json=REQUEST, headers=ORIGIN))
            await asyncio.wait_for(entered.wait(), timeout=2)
            second = await api.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
            assert second.status_code == 409
            assert second.json()['code'] == 'generation_in_progress'
            release.set()
            assert (await first).status_code == 201
    asyncio.run(journey())


def test_backend_deadline_cancels_and_releases_admission(client, provider, monkeypatch):
    import asyncio
    from dataclasses import replace
    import app.api.studio_preview as api
    original = provider.complete
    monkeypatch.setattr(api, 'POLICY', replace(api.POLICY, preview_backend_seconds=0.03))

    async def slow(request):
        await asyncio.sleep(1)
        return await original(request)

    provider.complete = slow
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 504
    provider.complete = original
    retry = client.post('/api/studio/preview', json={**REQUEST, 'project_id': response.json()['project_id']}, headers=ORIGIN)
    assert retry.status_code == 201


def test_migration_preserves_forensics_records_and_reuses_real_analysis(client, provider):
    analysis = client.post('/api/analyses', json={'doi': '10.1126/science.1231143'}).json()
    path = '/api/analyses/' + analysis['id']
    response = client.post('/api/studio/preview', json={'title': 'A partir do artigo', 'analysis_id': analysis['id']}, headers=ORIGIN)
    assert response.status_code == 201, response.text
    assert response.json()['scientific_context']['paper_ids'] == [analysis['paper']['id']]
    assert response.json()['scientific_context']['analysis_id'] == analysis['id']
    assert response.json()['source_documents'][0]['doi'] == analysis['paper']['doi']
    assert client.get(path).json() == analysis
    assert client.get(path + '/export?format=json').status_code == 200
    assert client.get('/api/catalog/candidates').status_code == 200


def test_live_openapi_exposes_preview_request_and_safe_errors(client):
    schema = client.get('/openapi.json').json()
    operation = schema['paths']['/api/studio/preview']['post']
    assert operation['requestBody']['required'] is True
    assert operation['requestBody']['content']['application/json']['schema']['properties']['material_text']['maxLength'] == 20000
    assert {'201', '413', '422', '429', '502', '503', '504'} <= set(operation['responses'])


def test_crashed_preview_is_recoverable_after_deadline_and_grace(client, provider, monkeypatch):
    import asyncio
    import httpx
    from datetime import timedelta
    import app.api.studio_preview as api
    current = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(api, 'now', lambda: current.isoformat())
    first = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN).json()
    original = provider.complete

    async def simulate_crash(request):
        raise asyncio.CancelledError()

    provider.complete = simulate_crash

    async def interrupted():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver', cookies=client.cookies) as api_client:
            with pytest.raises(asyncio.CancelledError):
                await api_client.post('/api/studio/preview', json={**REQUEST, 'project_id': first['project_id']}, headers=ORIGIN)
    asyncio.run(interrupted())
    provider.complete = original
    assert client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN).status_code == 409
    current += timedelta(seconds=61)
    with TestClient(app) as restarted:
        restarted.cookies.update(client.cookies)
        recovered = restarted.post('/api/studio/preview', json={**REQUEST, 'project_id': first['project_id']}, headers=ORIGIN)
        assert recovered.status_code == 201, recovered.text
        assert restarted.get('/api/studio/previews/' + first['preview_id']).status_code == 200


def test_two_global_slots_do_not_block_forensics(client, provider):
    import asyncio
    import httpx
    original = provider.complete

    async def journey():
        entered = asyncio.Event()
        release = asyncio.Event()
        count = 0
        async def blocked(request):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
            await release.wait()
            return await original(request)
        provider.complete = blocked
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as api:
            first = asyncio.create_task(api.post('/api/studio/preview', json=REQUEST, headers=ORIGIN))
            second = asyncio.create_task(api.post('/api/studio/preview', json=REQUEST, headers=ORIGIN))
            await asyncio.wait_for(entered.wait(), timeout=2)
            third = await api.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
            assert third.status_code == 503
            assert (await api.get('/api/health')).status_code == 200
            release.set()
            assert (await first).status_code == 201
            assert (await second).status_code == 201
    asyncio.run(journey())


@pytest.mark.parametrize('content', [b'{invalid', b'[]', b'{}', b' ' * (128 * 1024 + 1)])
def test_bad_json_or_oversized_output_cannot_publish_preview(client, provider, content):
    original = provider.complete
    async def invalid(request):
        result = await original(request)
        return ProviderResult(content, result.metadata)
    provider.complete = invalid
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 502
    assert response.json()['code'] == 'invalid_generation'


def test_cookie_expiry_matches_admitted_project_even_after_provider_delay(client, provider, monkeypatch):
    from datetime import timedelta
    from email.utils import parsedate_to_datetime
    import app.api.studio_preview as api
    current = datetime.now(timezone.utc)
    monkeypatch.setattr(api, 'now', lambda: current.isoformat())
    original = provider.complete
    async def takes_time(request):
        nonlocal current
        current += timedelta(seconds=20)
        return await original(request)
    provider.complete = takes_time
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 201
    cookie = response.headers['set-cookie']
    assert 'Max-Age=604780' in cookie
    expiry = next(part.strip()[8:] for part in cookie.split(';') if part.strip().startswith('expires='))
    assert parsedate_to_datetime(expiry).timestamp() == int(datetime.fromisoformat(response.json()['expires_at']).timestamp())
