"""T12 behavior at M0 persistence and HTTP boundaries; no live provider calls."""
import asyncio

from app.services.studio.generation_repository import IsolatedGenerationRepository
from generation_fixtures import request_for, setup


def run(coroutine):
    return asyncio.run(coroutine)


def test_status_after_restart_recovers_only_at_deadline_plus_grace(tmp_path):
    service, repo, provider, value, clock = setup(tmp_path)
    run(repo.claim_generation(session_id='owner', request=request_for(value),
                              idempotency_key='stable', now=clock.now()))
    restarted = IsolatedGenerationRepository(repo.path)
    clock.advance(89)
    current = run(restarted.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert current.generation_status == 'generating'
    clock.advance(1)
    recovered = run(restarted.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert recovered.generation_status == 'failed'
    assert recovered.last_error.code == 'generation_timeout'
    assert recovered.suggestions == value.suggestions
    assert recovered.approved_objectives == value.approved_objectives
    assert recovered.source_documents == value.source_documents
    assert not provider.requests
    result = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='stable'))
    assert result.bundle.preview_id == value.preview_id


def test_maintenance_sweeps_on_startup_and_while_idle_without_read_or_renewal(tmp_path):
    from app.services.studio.operations import studio_maintenance_lifespan

    async def scenario():
        _, repo, _, value, clock = setup(tmp_path)
        clock.advance(8 * 86400)
        lifespan = studio_maintenance_lifespan(repo, now=clock.now, interval_seconds=0.01)
        async with lifespan(None):
            assert await repo.cleanup_expired(now=clock.now()) == 0
            repo.store_reference_preview(session_id='owner', preview=value)
            await asyncio.sleep(0.04)
            assert await repo.cleanup_expired(now=clock.now()) == 0
        repo.store_reference_preview(session_id='owner', preview=value)
        await asyncio.sleep(0.03)
        assert await repo.cleanup_expired(now=clock.now()) == 1
    run(scenario())


def test_metrics_aggregate_success_replay_and_failure_without_sensitive_payloads(tmp_path, caplog):
    import pytest
    from app.services.studio.generation import GenerationService
    from app.services.studio.metrics import StudioMetrics
    from app.studio.ports import RepositoryConflict
    from generation_fixtures import authority

    service, repo, provider, value, clock = setup(tmp_path)
    metrics = StudioMetrics()
    service = GenerationService(repo, provider, lambda _: authority(), now=clock.now,
                                monotonic_clock=clock.monotonic, metrics=metrics)
    caplog.set_level('INFO', logger='matilda.studio.operations')
    first = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='first'))
    replay = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='first'))
    assert replay.bundle == first.bundle and replay.replayed
    provider.payload = b'{RAW_SECRET TEACHER_MATERIAL'
    with pytest.raises(RepositoryConflict):
        run(service.generate(session_id='owner', request=request_for(value), idempotency_key='second'))
    stats = metrics.snapshot()
    assert stats['generation_outcomes'] == {'completed': 1, 'replayed': 1, 'failed': 1}
    assert stats['generation_errors'] == {'invalid_generation': 1}
    assert stats['provider_attempts'] == 3
    assert stats['input_tokens_counted'] == 1200
    assert stats['output_tokens_reported'] > 0
    assert 'RAW_SECRET' not in caplog.text + str(stats)
    assert 'TEACHER_MATERIAL' not in caplog.text + str(stats)
    assert value.source_documents[0].content not in caplog.text + str(stats)
    assert 'owner' not in str(stats)


def test_maintenance_failure_is_sanitized_observed_and_does_not_stop_host(tmp_path, caplog):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.services.studio.metrics import StudioMetrics
    from app.services.studio.operations import studio_maintenance_lifespan

    _, repo, _, _, clock = setup(tmp_path)
    # A directory in place of the SQLite file is a real filesystem outage.
    repo.path.unlink()
    repo.path.mkdir()
    metrics = StudioMetrics()
    app = FastAPI(lifespan=studio_maintenance_lifespan(repo, now=clock.now, metrics=metrics))

    @app.get('/health')
    def health():
        return {'ok': True}

    with TestClient(app) as client:
        assert client.get('/health').json() == {'ok': True}
    assert metrics.snapshot()['maintenance_errors'] == 1
    assert metrics.snapshot()['maintenance_runs'] == 1
    assert 'storage_unavailable' in caplog.text
    assert str(repo.path) not in caplog.text
    assert 'Traceback' not in caplog.text


def test_retention_reads_export_and_completed_replay_do_not_renew_after_24h(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.studio_exports import create_export_router

    service, repo, provider, value, clock = setup(tmp_path)
    first = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='same'))
    async def session(http):
        return http.cookies.get('test_owner')
    app = FastAPI()
    app.include_router(create_export_router(repo, session, clock=clock.now))
    path = f'/api/studio/lessons/{first.bundle.lesson_bundle_id}/export?format=markdown'
    with TestClient(app) as client:
        client.cookies.set('test_owner', 'owner')
        clock.advance(2 * 86400)
        resumed = run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
        assert resumed.suggestions == value.suggestions
        assert resumed.expires_at == first.expires_at
        response = client.get(path)
        assert response.status_code == 200 and 'set-cookie' not in response.headers
        replay = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='same'))
        assert replay.replayed and replay.expires_at == first.expires_at
        clock.advance(5 * 86400)
        assert client.get(path).status_code == 404
        assert run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now())) is None
        assert run(repo.cleanup_expired(now=clock.now())) == 1
        assert run(repo.cleanup_expired(now=clock.now())) == 0
    assert len(provider.requests) == 1


def test_admitted_generation_renews_but_cleanup_cannot_erase_it_or_previous_bundle(tmp_path):
    from app.studio.ports import RepositoryConflict
    import pytest

    service, repo, provider, value, clock = setup(tmp_path)
    first = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='first'))
    clock.advance(7 * 86400 - 1)
    claim = run(repo.claim_generation(session_id='owner', request=request_for(value), idempotency_key='second', now=clock.now()))
    admitted = run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert admitted.expires_at > first.expires_at
    clock.advance(89)
    assert run(repo.cleanup_expired(now=clock.now())) == 0
    pending = run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert pending.generation_status == 'generating'
    clock.advance(1)
    restarted = IsolatedGenerationRepository(repo.path)
    assert run(restarted.cleanup_expired(now=clock.now())) == 0
    failed = run(restarted.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert failed.generation_status == 'failed'
    assert failed.suggestions == value.suggestions
    assert failed.expires_at == admitted.expires_at
    assert failed.last_lesson_bundle_id == first.bundle.lesson_bundle_id
    assert run(restarted.get_lesson(session_id='owner', lesson_bundle_id=first.bundle.lesson_bundle_id, now=clock.now())) == first.bundle
    with pytest.raises(RepositoryConflict):
        run(restarted.complete_generation(claim_id=claim.claim_id, bundle=first.bundle, now=clock.now()))


def test_success_after_45_second_target_is_not_aborted(tmp_path):
    from generation_fixtures import Clock, Provider
    clock = Clock()
    # Valid response arriving after the UX target remains a success.
    service, repo, _, value, clock = setup(tmp_path, clock=clock, provider=Provider(clock=clock, elapsed=46))
    result = run(service.generate(session_id='owner', request=request_for(value), idempotency_key='slow'))
    assert result.bundle.preview_id == value.preview_id
    assert service.metrics.snapshot()['generation_duration_ms'] == 46000
    assert service.metrics.snapshot()['generation_outcomes'] == {'completed': 1}


def test_raw_transport_exception_never_escapes_http_or_metrics(tmp_path, caplog):
    from test_studio_generation import http_client
    service, repo, provider, value, clock = setup(tmp_path)
    async def disconnected(request):
        raise ConnectionError('RAW_API_KEY TEACHER_MATERIAL upstream-body')
    # Only the external transport boundary is substituted.
    provider.complete = disconnected
    client, renewals = http_client(service)
    with client:
        client.cookies.set('test_owner', 'owner')
        response = client.post('/api/studio/generate', json=request_for(value).model_dump(),
                               headers={'Origin': 'http://testserver', 'Idempotency-Key': 'same'})
    assert response.status_code == 503
    assert response.json()['code'] == 'provider_unavailable'
    assert 'RAW_API_KEY' not in response.text + caplog.text + str(service.metrics.snapshot())
    assert 'TEACHER_MATERIAL' not in response.text + caplog.text + str(service.metrics.snapshot())
    saved = run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert saved.generation_status == 'failed' and saved.last_lesson_bundle_id is None
    assert saved.suggestions == value.suggestions
