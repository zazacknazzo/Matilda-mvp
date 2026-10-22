"""T13 production HTTP/SQLite seams. Only external providers are controlled."""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from test_studio_flow import flow, create, review, generate
from test_studio_preview import ORIGIN


def test_transform_investigation_uses_recorded_science_and_canonical_sources(client, flow, monkeypatch, tmp_path):
    from app.services import storage

    analysis = client.post('/api/analyses', json={'doi': '10.1126/science.1231143'}).json()
    # T06 guarantees a recorded investigation survives an editorial update.
    for name in ('concepts.json', 'researchers.json', 'contributions.json', 'evidence.json'):
        records = storage.load_json(name)
        if name == 'contributions.json':
            for record in records:
                record['title'] = 'Later editorial title'
        (tmp_path / name).write_text(json.dumps(records))
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    response = client.post('/api/studio/preview', json={'title': 'CRISPR', 'analysis_id': analysis['id']}, headers=ORIGIN)
    assert response.status_code == 201, response.text
    preview = response.json()
    from app.services.studio.runtime_repository import StudioRepository
    from app.schemas.studio import EnrichmentPreview
    authority = StudioRepository().scientific_authority(EnrichmentPreview.model_validate(preview))
    assert [item.model_dump(mode='json') for item in authority.matches] == analysis['contributions']
    assert preview['scientific_context']['analysis_id'] == analysis['id']
    assert preview['source_documents'][0]['doi'] == analysis['paper']['doi']
    assert all(ref['participants'] for ref in preview['evidence_references'])


def test_preview_reports_separate_stage_timings_without_material_or_secrets(client, flow, caplog):
    import asyncio
    caplog.set_level('INFO', logger='matilda.studio.timings')
    original = flow.complete

    async def count(request):
        await asyncio.sleep(0.02)
        return 400

    async def complete(request):
        await asyncio.sleep(0.04)
        return await original(request)

    flow.count_input_tokens, flow.complete = count, complete
    value = create(client)
    events = [json.loads(record.message.removeprefix('studio_stage ')) for record in caplog.records if record.message.startswith('studio_stage ')]
    assert {event['stage'] for event in events} == {
        'scientific_retrieval', 'context', 'token_count', 'structured_generation', 'validation', 'persistence',
    }
    assert next(event['duration_ms'] for event in events if event['stage'] == 'token_count') >= 15
    assert next(event['duration_ms'] for event in events if event['stage'] == 'structured_generation') >= 35
    assert all(event['status'] == 'ok' for event in events)
    assert value['source_documents'][0]['content'] not in caplog.text


def test_host_composes_t12_maintenance_and_aggregate_generation_metrics(client, flow):
    from app.main import app
    metrics = app.state.studio_metrics
    assert metrics.snapshot()['maintenance_runs'] >= 1
    saved, _ = review(client, create(client))
    first = generate(client, saved)
    assert first.status_code == 201
    assert generate(client, saved).status_code == 200
    assert metrics.snapshot()['generation_outcomes'] == {'completed': 1, 'replayed': 1}


def test_real_export_checks_session_expiry_formats_headers_and_private_material(client, flow):
    from app.main import app
    from app.services.studio.runtime_repository import StudioRepository
    private = 'CRISPR-Cas9. PRIVATE_ORIGINAL_T13 never belongs in a generated export.'
    response = client.post('/api/studio/preview', json={'title': 'CRISPR <script>literal</script>', 'material_text': private}, headers=ORIGIN)
    assert response.status_code == 201
    saved, _ = review(client, response.json())
    response = generate(client, saved)
    assert response.status_code == 201
    path = '/api/studio/lessons/' + response.json()['lesson_bundle_id'] + '/export'
    response = client.get(path + '?format=markdown')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/markdown')
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['content-disposition'].startswith('attachment; filename="matilda-')
    assert 'set-cookie' not in response.headers
    assert 'PRIVATE_ORIGINAL_T13' not in response.text
    assert '<script>' not in response.text
    with TestClient(app) as other:
        assert other.get(path).status_code == 404
    for query in ('?format=pdf', '?format=markdown&format=markdown', '?unknown=x'):
        assert client.get(path + query).status_code == 422
    assert client.get(path, headers={'Origin': 'https://evil.invalid'}).status_code == 404
    assert len(flow.lesson_requests) == 1
    asyncio.run(StudioRepository().cleanup_expired(now=(datetime.now(timezone.utc) + timedelta(days=8)).isoformat()))
    assert client.get(path).status_code == 404
