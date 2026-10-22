"""Real API/science/SQLite plus NVIDIA adapter. Only hosted HTTP is controlled."""
import json

import pytest

from app.api.studio_preview import get_provider
from app.main import app
from app.schemas.lesson import LessonBundle
from nvidia_transport import controlled_nvidia
from studio_flow_provider import FlowProvider
from test_studio_flow import review, generate
from test_studio_preview import ORIGIN


@pytest.fixture
def external(client, monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-nvidia-key')
    controlled = FlowProvider()
    app.dependency_overrides[get_provider] = lambda: controlled_nvidia(controlled)
    yield controlled
    app.dependency_overrides.clear()


@pytest.mark.parametrize('doi,text', [
    ('10.1126/science.1231143', 'CRISPR-Cas9 permite discutir edição genética.'),
    ('10.1056/NEJMoa2034577', 'RNA mensageiro e modificação de nucleosídeos permitem discutir imunidade.'),
])
def test_both_scientific_paths_produce_50_minute_lesson_resume_and_markdown(client, external, doi, text, caplog):
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    initial = client.post('/api/studio/preview', headers=ORIGIN, json={
        'title': 'Mecanismo molecular', 'duration_minutes': 50, 'doi': doi, 'material_text': text})
    assert initial.status_code == 201, initial.text
    preview = initial.json()
    assert preview['suggestions'] and preview['generation_metadata']['provider'] == 'nvidia'
    assert all(ref['participants'] for ref in preview['evidence_references'])
    assert generate(client, preview).status_code == 409
    saved, _ = review(client, preview)
    response = generate(client, saved)
    assert response.status_code == 201, response.text
    bundle = LessonBundle.model_validate(response.json())
    assert bundle.metadata.duration_minutes == 50
    assert sum(s.duration_minutes for s in bundle.sections) == 50
    assert bundle.generation_metadata.provider == 'nvidia'
    assert bundle.references
    assert client.get('/api/studio/lessons/' + bundle.lesson_bundle_id).json() == response.json()
    assert generate(client, saved).json() == response.json()
    assert len(external.lesson_requests) == 1
    exported = client.get('/api/studio/lessons/' + bundle.lesson_bundle_id + '/export?format=markdown')
    assert exported.status_code == 200 and bundle.references[0].participants[0] in exported.text
    events = [json.loads(r.message.removeprefix('nvidia_attempt ')) for r in caplog.records if r.message.startswith('nvidia_attempt ')]
    assert len(events) == 2
    assert all(e['estimated_input_tokens'] <= 12000 for e in events)
    assert all(e['actual_input_tokens'] == 900 and e['input_token_delta'] < 0 for e in events)
    assert 'test-private-nvidia-key' not in caplog.text + response.text


@pytest.mark.parametrize('stage', ['preview', 'lesson'])
@pytest.mark.parametrize('failure,attempts,code,retryable', [
    (401, 1, 'provider_unavailable', False), (403, 1, 'provider_unavailable', False),
    (400, 1, 'invalid_generation', False), (422, 1, 'invalid_generation', False),
    (429, 2, 'provider_unavailable', True), (503, 2, 'provider_unavailable', True),
    ('invalid_json', 2, 'invalid_generation', True), ('invalid_schema', 2, 'invalid_generation', True),
    ('truncated', 1, 'invalid_generation', True),
])
def test_failures_preserve_material_and_review_and_allow_explicit_recovery(
    client, external, monkeypatch, caplog, stage, failure, attempts, code, retryable,
):
    import httpx
    from app.integrations.nvidia_client import NVIDIAProvider
    from test_studio_flow import create, generation
    from test_studio_preview import REQUEST
    caplog.set_level('INFO', logger='matilda.studio.validation')
    calls = []
    saved = None
    if stage == 'lesson':
        saved, _ = review(client, create(client))

    def failing(http):
        calls.append(json.loads(http.content))
        if isinstance(failure, int):
            return httpx.Response(failure, text='UPSTREAM_PRIVATE_MATERIAL test-private-nvidia-key')
        return httpx.Response(200, json={
            'model': 'controlled', 'usage': {'prompt_tokens': 900, 'completion_tokens': 1200},
            'choices': [{'finish_reason': 'length' if failure == 'truncated' else 'stop',
                         'message': {'content': '{private' if failure == 'invalid_json' else '{}'}}]})

    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(failing))
    response = generate(client, saved) if saved else client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.json()['code'] == code and response.json()['retryable'] is retryable
    assert len(calls) == attempts
    if failure == 'invalid_schema':
        assert 'pydantic_validation' in caplog.text
    assert len({json.dumps(c['response_format']) for c in calls}) == 1
    assert 'UPSTREAM_PRIVATE_MATERIAL' not in response.text
    if saved:
        current = client.get('/api/studio/previews/' + saved['preview_id']).json()
        assert current['source_documents'] == saved['source_documents']
        assert current['approved_objectives'] == saved['approved_objectives']
        assert current['suggestions'] == saved['suggestions']
        assert current['generation_status'] == 'failed' and current['last_lesson_bundle_id'] is None
    app.dependency_overrides[get_provider] = lambda: controlled_nvidia(external)
    recovery = generate(client, saved) if saved else client.post('/api/studio/preview', json={**REQUEST, 'project_id': response.json()['project_id']}, headers=ORIGIN)
    assert recovery.status_code == 201, recovery.text


def test_unknown_provider_is_safe_configuration_failure_and_forensics_still_works(client, monkeypatch):
    from test_studio_preview import REQUEST
    monkeypatch.setenv('AI_PROVIDER', 'typo')
    response = client.post('/api/studio/preview', json=REQUEST, headers=ORIGIN)
    assert response.status_code == 503
    assert response.json()['code'] == 'studio_not_configured'
    assert client.get('/api/papers/10.1126/science.1231143').status_code == 200


def test_nvidia_smoke_runs_both_previews_lesson_read_and_export_offline(client, external, monkeypatch):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'scripts/smoke_studio_nvidia.py'
    spec = importlib.util.spec_from_file_location('nvidia_smoke', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    report = smoke.run_smoke(controlled_nvidia(external))
    assert report['status'] == 'passed', report
    assert [s['stage'] for s in report['steps']] == ['crispr_preview', 'rna_preview', 'review', 'lesson', 'read', 'markdown']
    assert sum(e['type'] == 'nvidia_attempt' for e in report['events']) == 3
    assert all(s.get('json_validated') for s in report['steps'] if s['stage'] in ('crispr_preview', 'rna_preview', 'lesson'))
    assert report['steps'][3]['slides'] >= 4 and report['steps'][3]['sections'] >= 3
    assert 'test-private-nvidia-key' not in json.dumps(report)
