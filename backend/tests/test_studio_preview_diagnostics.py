"""Public API diagnostic seam, production NVIDIA + science + SQLite; mocked HTTP only."""
import json

import httpx
import pytest

from app.main import app
from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from test_studio_preview import ORIGIN


def test_schema_valid_empty_plan_reports_exact_coverage_rejection_without_content(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    calls = []
    def upstream(http):
        calls.append(1)
        return httpx.Response(200, json={
            'model': 'private/nvidia/nemotron-3.5-super-120b-a12b',
            'usage': {'prompt_tokens': 1330, 'completion_tokens': 96},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({
                'suggested_objectives': ['Explicar o mecanismo molecular.'], 'suggestions': []})}}],
        })
    caplog.set_level('INFO', logger='matilda.studio.validation')
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', headers=ORIGIN, json={
            'title': 'CRISPR', 'duration_minutes': 50, 'doi': '10.1126/science.1231143',
            'material_text': 'CRISPR-Cas9 permite discutir edição genética. PRIVATE_TEACHER_TEXT'})
        assert response.status_code == 502
        assert response.json()['code'] == 'invalid_generation'
        diagnostics = [json.loads(r.message.removeprefix('studio_preview_validation ')) for r in caplog.records
                       if r.message.startswith('studio_preview_validation ')]
        assert diagnostics
        assert all(e['code'] == 'coverage_mismatch' and e['plan_pydantic_valid'] is True
                   and e['authorized_contributions'] == 4 and e['returned_suggestions'] == 0 for e in diagnostics)
        assert 'PRIVATE_TEACHER_TEXT' not in caplog.text
        assert 'test-private-key' not in caplog.text
        assert 'Explicar o mecanismo molecular.' not in caplog.text
    finally:
        app.dependency_overrides.clear()


def rejected_plan(client, monkeypatch, caplog, mutate):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    def upstream(http):
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        candidate = material['scientific_candidates'][0]
        plan = {'suggested_objectives': ['Conferir as fontes documentais.'], 'suggestions': [{
            'candidate_id': candidate['id'],
            'pedagogical_rationale': 'Comparar o mecanismo e sua documentação.',
            'suggested_content': 'Leia a evidência e discuta o mecanismo.',
        }]}
        mutate(plan, material)
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', headers=ORIGIN, json={
            'title': 'CRISPR', 'material_text': 'CRISPR-Cas9. PRIVATE_TEACHER_TEXT'})
        diagnostics = [json.loads(r.message.removeprefix('studio_preview_validation ')) for r in caplog.records
                       if r.message.startswith('studio_preview_validation ')]
        assert 'PRIVATE_TEACHER_TEXT' not in caplog.text and 'PRIVATE_INVALID_ID' not in caplog.text
        return response, diagnostics
    finally:
        app.dependency_overrides.clear()


def test_model_cannot_override_candidate_contribution(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['contribution_id'] = 'PRIVATE_INVALID_ID'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False
               and e['returned_suggestions'] is None for e in diagnostics)


def test_unknown_scientific_candidate_is_reported_without_logging_identifier(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['candidate_id'] = 'PRIVATE_INVALID_ID'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'invalid_scientific_candidate' and e['plan_pydantic_valid'] is True for e in diagnostics)


def test_model_cannot_override_candidate_concept(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['concept_ids'] = ['PRIVATE_INVALID_ID']
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False for e in diagnostics)


def test_ineligible_identity_keeps_rejection_with_specific_code():
    from generation_fixtures import authority, preview
    trusted, value = authority(), preview()
    affected = next(m for m in trusted.matches if m.contribution.id == value.suggestions[0].contribution_id)
    affected.researchers[0] = affected.researchers[0].model_copy(update={'identity_status': 'pending'})
    with pytest.raises(ValueError) as caught:
        value.validate_scientific_authority(trusted.matches, trusted.references, concepts=trusted.concepts, papers=trusted.papers)
    assert getattr(caught.value, 'type', None) == 'invalid_identity'


def test_provider_schema_requires_suggestion_only_when_scientific_coverage_exists(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    from types import SimpleNamespace
    from studio_flow_provider import FlowProvider
    external = FlowProvider()
    seen = []
    async def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        schema = body['response_format']['json_schema']['schema']
        covered = bool(material['scientific_candidates'])
        seen.append(covered)
        assert schema['properties']['suggestions']['minItems'] == (1 if covered else 0)
        assert schema['properties']['suggestions']['maxItems'] == (20 if covered else 0)
        result = await external.complete(SimpleNamespace(stage='preview', material=material, prompt_version='controlled'))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': result.content.decode()}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        for text in ('CRISPR-Cas9 permite discutir edição genética.', 'O movimento uniforme permite discutir velocidade.'):
            response = client.post('/api/studio/preview', headers=ORIGIN, json={'title': 'Ciências', 'material_text': text})
            assert response.status_code == 201
        assert seen == [True, False]
    finally:
        app.dependency_overrides.clear()


def test_model_receives_indivisible_candidates_and_documents_without_administrative_duplicates(client, monkeypatch):
    from types import SimpleNamespace
    from studio_flow_provider import FlowProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    external, inspected = FlowProvider(), []
    async def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        schema = body['response_format']['json_schema']['schema']
        suggestion = schema['$defs']['PlannedSuggestion']['properties']
        contributions = material['scientific_contributions']
        choices = material['scientific_candidates']
        assert len(contributions) == 4 and 4 <= len(choices) <= 8
        assert set(suggestion) == {'candidate_id', 'pedagogical_rationale', 'suggested_content'}
        assert set(suggestion['candidate_id']['enum']) == {a['id'] for a in choices}
        assert set(contributions) == {a['contribution'] for a in choices}
        for document in material['source_documents']:
            assert set(document) == {'key', 'type', 'content'}
        for choice in choices:
            document = next(d for d in material['source_documents'] if d['key'] == choice['document'])
            assert choice['quote'] in document['content']
            assert contributions[choice['contribution']]['evidence_claims']
        inspected.append(True)
        result = await external.complete(SimpleNamespace(stage='preview', material=material, prompt_version='controlled'))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': result.content.decode()}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', headers=ORIGIN, json={
            'title': 'CRISPR', 'doi': '10.1126/science.1231143', 'material_text': '  CRISPR-Cas9 permite discutir edição genética.'})
        assert response.status_code == 201 and inspected == [True]
    finally:
        app.dependency_overrides.clear()


def test_valid_plan_reports_passed_validation_and_counts_without_content(client, monkeypatch, caplog):
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, lambda plan, material: None)
    assert response.status_code == 201
    assert len(diagnostics) == 1
    event = diagnostics[0]
    assert event['code'] == 'ok' and event['outcome'] == 'passed'
    assert event['plan_pydantic_valid'] is True and event['preview_pydantic_valid'] is True
    assert event['scientific_authority_valid'] is True
    assert event['authorized_contributions'] == 4 and event['returned_suggestions'] == 1


def test_smoke_reports_coverage_failure_and_prevents_corrective_paid_call(client, monkeypatch):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'scripts/smoke_studio_nvidia.py'
    spec = importlib.util.spec_from_file_location('nvidia_smoke_diagnostics', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    monkeypatch.setenv('NVIDIA_MODEL', 'must-not-use-another-model')
    calls = []
    def upstream(http):
        body = json.loads(http.content)
        assert body['model'] == 'nvidia/nemotron-3.5-super-vl-120b-a12b'
        calls.append(1)
        return httpx.Response(200, json={'model': 'private/nvidia/nemotron-3.5-super-120b-a12b',
            'usage': {'prompt_tokens': 1330, 'completion_tokens': 96},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({
                'suggested_objectives': ['Explicar o mecanismo molecular.'], 'suggestions': []})}}]})
    provider = smoke.BudgetedNVIDIA(transport=httpx.MockTransport(upstream))
    report = smoke.run_smoke(provider)
    assert report['status'] == 'failed' and report['failed_stage'] == 'crispr_preview'
    assert calls == [1] and provider.calls == 1
    failures = [e for e in report['events'] if e['type'] == 'studio_preview_validation']
    assert len(failures) == 1
    assert failures[0]['code'] == 'coverage_mismatch' and failures[0]['plan_pydantic_valid'] is True
    assert failures[0]['authorized_contributions'] == 4 and failures[0]['returned_suggestions'] == 0
    assert 'test-private-key' not in json.dumps(report)
    assert 'Explicar o mecanismo molecular.' not in json.dumps(report)


def test_model_cannot_override_candidate_evidence(client, monkeypatch, caplog):
    def mutate(plan, material):
        plan['suggestions'][0]['evidence_ids'] = ['evidence-crispr-2011']
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False for e in diagnostics)


def test_invalid_plan_shape_is_distinguished_from_scientific_failure(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['PRIVATE_INVALID_ID'] = 'PRIVATE_TEACHER_TEXT'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False
                               and e['returned_suggestions'] is None for e in diagnostics)


def test_model_authored_source_anchor_is_forbidden_even_if_it_is_literal(client, monkeypatch, caplog):
    def mutate(plan, material):
        plan['suggestions'][0]['source_anchor'] = {'source_document_id': 'd1', 'quote': 'CRISPR', 'occurrence': 0}
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False for e in diagnostics)


@pytest.mark.parametrize('status', [202, 401, 429, 503])
def test_smoke_does_not_spend_a_second_inference_after_upstream_failure(client, monkeypatch, status):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'scripts/smoke_studio_nvidia.py'
    spec = importlib.util.spec_from_file_location('nvidia_smoke_budget', path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    calls = []
    def upstream(_):
        calls.append(1)
        return httpx.Response(status, text='PRIVATE_TEACHER_TEXT test-private-key')
    provider = smoke.BudgetedNVIDIA(transport=httpx.MockTransport(upstream))
    report = smoke.run_smoke(provider)
    assert report['status'] == 'failed' and report['failed_stage'] == 'crispr_preview'
    assert calls == [1] and provider.calls == 1
    assert 'PRIVATE_TEACHER_TEXT' not in json.dumps(report)
    assert 'test-private-key' not in json.dumps(report)


def test_crossed_legacy_ids_are_rejected_instead_of_repaired(client, monkeypatch, caplog):
    def mutate(plan, material):
        plan['suggestions'][0].update(contribution_id='crispr-2012', concept_ids=['crispr'],
                                      evidence_ids=['evidence-crispr-2011'], source_anchor_id='old-anchor')
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False for e in diagnostics)
