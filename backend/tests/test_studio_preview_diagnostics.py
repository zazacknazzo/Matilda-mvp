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
        match, document = material['authorized_contributions'][0], material['source_documents'][0]
        plan = {'suggested_objectives': ['Conferir as fontes documentais.'], 'suggestions': [{
            'contribution_id': match['contribution_id'], 'concept_ids': match['concept_ids'][:1],
            'evidence_ids': match['evidence_ids'][:1],
            'source_anchor': {'source_document_id': document['id'], 'quote': document['content'], 'occurrence': 0},
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


def test_unknown_contribution_is_distinguished_from_evidence_failure(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['contribution_id'] = 'PRIVATE_INVALID_ID'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert all(e['code'] == 'unknown_contribution' and e['plan_pydantic_valid'] is True
               and e['returned_suggestions'] == 1 for e in diagnostics)


def test_nonliteral_source_anchor_is_reported_without_logging_quote(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['source_anchor']['quote'] = 'PRIVATE_INVALID_ID'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'invalid_source_anchor' and e['plan_pydantic_valid'] is True for e in diagnostics)


def test_invalid_concept_is_distinguished_from_structural_pydantic_failure(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['suggestions'][0]['concept_ids'] = ['PRIVATE_INVALID_ID']
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'invalid_concept' and e['plan_pydantic_valid'] is True for e in diagnostics)


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
        covered = bool(material['authorized_contributions'])
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


def test_model_receives_bound_ids_and_real_literal_anchor_examples(client, monkeypatch):
    from types import SimpleNamespace
    from studio_flow_provider import FlowProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    external = FlowProvider()
    inspected = []
    async def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        schema = body['response_format']['json_schema']['schema']
        suggestion = schema['$defs']['PlannedSuggestion']['properties']
        authorized = material['authorized_contributions']
        assert len(authorized) == 4
        assert set(suggestion['contribution_id']['enum']) == {a['contribution_id'] for a in authorized}
        assert set(suggestion['concept_ids']['items']['enum']) == {cid for a in authorized for cid in a['concept_ids']}
        assert set(suggestion['evidence_ids']['items']['enum']) == {eid for a in authorized for eid in a['evidence_ids']}
        documents = {doc['id']: doc['content'] for doc in material['source_documents']}
        assert set(schema['$defs']['SourceAnchor']['properties']['source_document_id']['enum']) == set(documents)
        examples = material['source_anchor_examples']
        assert len(examples) == len(documents) == 2
        for example in examples:
            assert example['occurrence'] == 0 and example['quote'].strip()
            assert example['quote'] in documents[example['source_document_id']]
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


def test_evidence_from_another_authorized_contribution_is_still_rejected(client, monkeypatch, caplog):
    def mutate(plan, material):
        plan['suggestions'][0]['evidence_ids'] = material['authorized_contributions'][1]['evidence_ids'][:1]
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'unauthorized_evidence' and e['plan_pydantic_valid'] is True for e in diagnostics)


def test_invalid_plan_shape_is_distinguished_from_scientific_failure(client, monkeypatch, caplog):
    def mutate(plan, _):
        plan['PRIVATE_INVALID_ID'] = 'PRIVATE_TEACHER_TEXT'
    response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
    assert response.status_code == 502
    assert diagnostics and all(e['code'] == 'pydantic_validation' and e['plan_pydantic_valid'] is False
                               and e['returned_suggestions'] is None for e in diagnostics)


def test_missing_anchor_document_and_nonexistent_occurrence_are_never_accepted(client, monkeypatch, caplog):
    for change in ({'source_document_id': 'PRIVATE_INVALID_ID'}, {'occurrence': 2}):
        caplog.clear()
        def mutate(plan, _, change=change):
            plan['suggestions'][0]['source_anchor'].update(change)
        response, diagnostics = rejected_plan(client, monkeypatch, caplog, mutate)
        assert response.status_code == 502
        assert diagnostics and all(e['code'] == 'invalid_source_anchor' for e in diagnostics)


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
