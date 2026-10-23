"""Public API and hosted HTTP seams; real science, provider and SQLite, no network."""
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from test_studio_preview import ORIGIN

CRISPR = {'title': 'CRISPR', 'duration_minutes': 50, 'doi': '10.1126/science.1231143',
          'material_text': 'CRISPR-Cas9 permite discutir edição genética.'}


def events(caplog, prefix):
    return [json.loads(record.message.removeprefix(prefix + ' ')) for record in caplog.records
            if record.message.startswith(prefix + ' ')]


def test_invalid_candidate_near_budget_preserves_first_diagnosis_and_saved_preview(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    caplog.set_level('INFO', logger='matilda.studio')
    calls, reject = [], []
    def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        calls.append(1)
        candidate = material['scientific_candidates'][0]
        plan = {'suggested_objectives': ['Explicar o mecanismo.'], 'suggestions': [{
            'candidate_id': 'controlled-invalid-id' if reject else candidate['id'],
            'pedagogical_rationale': 'Relacionar material e documento.', 'suggested_content': 'Compare o mecanismo.'}]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 2867, 'completion_tokens': 143},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        seed = client.post('/api/studio/preview', json=CRISPR, headers=ORIGIN)
        assert seed.status_code == 201
        baseline = events(caplog, 'nvidia_attempt')[-1]['estimated_input_tokens']
        reject.append(True)
        padded = {**CRISPR, 'project_id': seed.json()['project_id'],
                  'material_text': CRISPR['material_text'] + 'x' * (11958 - baseline)}
        caplog.clear()
        failed = client.post('/api/studio/preview', json=padded, headers=ORIGIN)
        assert failed.status_code == 413 and failed.json()['code'] == 'input_too_large'
        assert len(calls) == 2  # One seed and one failed operation; no corrective HTTP.
        attempt = events(caplog, 'nvidia_attempt')
        assert len(attempt) == 1 and attempt[0]['estimated_input_tokens'] == 11958
        validation = events(caplog, 'studio_preview_validation')
        assert validation[0]['code'] == 'invalid_scientific_candidate'
        assert validation[0]['plan_pydantic_valid'] is True
        assert validation[0]['authorized_contributions'] == 4 and validation[0]['returned_suggestions'] == 1
        assert validation[-1]['code'] == 'corrective_input_too_large'
        assert validation[-1]['previous_code'] == 'invalid_scientific_candidate'
        assert validation[-1]['estimated_input_tokens'] > 12000
        resumed = client.get('/api/studio/previews/' + seed.json()['preview_id']).json()
        assert resumed['source_documents'] == seed.json()['source_documents']
        assert resumed['suggestions'] == seed.json()['suggestions']
        assert resumed['last_error']['code'] == 'input_too_large'
        assert 'controlled-key' not in caplog.text and 'Compare o mecanismo.' not in caplog.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('estimate,status,new_calls', [(12000, 201, 1), (12001, 413, 0)])
def test_exact_input_ceiling_checked_before_http_without_changing_the_counter(client, monkeypatch, caplog, estimate, status, new_calls):
    from types import SimpleNamespace
    from studio_flow_provider import FlowProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    calls, external = [], FlowProvider()
    async def upstream(http):
        body = json.loads(http.content)
        calls.append(1)
        result = await external.complete(SimpleNamespace(stage='preview', material=json.loads(body['messages'][1]['content']), prompt_version='controlled'))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': result.content.decode()}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        seed = client.post('/api/studio/preview', json=CRISPR, headers=ORIGIN)
        assert seed.status_code == 201
        baseline = events(caplog, 'nvidia_attempt')[-1]['estimated_input_tokens']
        response = client.post('/api/studio/preview', headers=ORIGIN, json={**CRISPR,
            'project_id': seed.json()['project_id'], 'material_text': CRISPR['material_text'] + 'x' * (estimate - baseline)})
        assert response.status_code == status and len(calls) == 1 + new_calls
        if status == 201:
            assert events(caplog, 'nvidia_attempt')[-1]['estimated_input_tokens'] == 12000
        else:
            assert response.json()['code'] == 'input_too_large'
            assert client.get('/api/studio/previews/' + seed.json()['preview_id']).json()['suggestions'] == seed.json()['suggestions']
    finally:
        app.dependency_overrides.clear()
