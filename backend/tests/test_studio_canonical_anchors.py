"""Public Studio API seam: real NVIDIA/science/SQLite, controlled external HTTP."""
import json

import httpx
import pytest

from app.main import app
from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from test_studio_preview import ORIGIN, provider

RNA = {'title': 'RNA mensageiro', 'duration_minutes': 50, 'doi': '10.1056/NEJMoa2034577',
       'material_text': 'RNA mensageiro e modificação de nucleosídeos permitem discutir reconhecimento imune e produção de proteínas.'}


@pytest.mark.parametrize('change,reason', [
    ({'source_document_id': 'private-invalid-document'}, 'invalid_source_document'),
    ({'quote': 'private-nonliteral-quote'}, 'non_literal_quote'),
    ({'occurrence': 99}, 'invalid_occurrence'),
])
def test_rna_public_anchor_rejects_document_quote_and_occurrence_separately(client, provider, change, reason):
    # Full public preview remains the persisted/read contract, after private selections resolve.
    from app.schemas.studio import EnrichmentPreview
    from pydantic import ValidationError
    response = client.post('/api/studio/preview', json=RNA, headers=ORIGIN)
    assert response.status_code == 201
    value = response.json()
    assert len(value['source_documents']) == 2
    value['suggestions'][0]['source_anchor'].update(change)
    with pytest.raises(ValidationError) as caught:
        EnrichmentPreview.model_validate(value)
    errors = caught.value.errors(include_input=False)
    assert any(e['type'] == 'invalid_source_anchor' and e['ctx']['anchor_error'] == reason for e in errors)


def test_rna_model_selects_authorized_anchor_and_server_materializes_original(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    selected = []
    def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        schema = body['response_format']['json_schema']['schema']
        properties = schema['$defs']['PlannedSuggestion']['properties']
        assert set(properties) == {'candidate_id', 'pedagogical_rationale', 'suggested_content'}
        candidate = material['scientific_candidates'][0]
        assert candidate['quote'] == 'RNA mensageiro'
        selected.append(candidate)
        plan = {'suggested_objectives': ['Explicar o mecanismo molecular.'], 'suggestions': [{
            'candidate_id': candidate['id'],
            'pedagogical_rationale': 'Relacionar o mecanismo ao documento.',
            'suggested_content': 'Leia a fonte e discuta o mecanismo molecular.',
        }]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', json=RNA, headers=ORIGIN)
        assert response.status_code == 201
        assert response.json()['suggestions'][0]['source_anchor']['quote'] == selected[0]['quote']
        assert '"scientific_authority_valid":true' in caplog.text
    finally:
        app.dependency_overrides.clear()


def test_repeated_unicode_terms_use_exact_server_occurrence_not_first_substring(client, monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    chosen = []
    def upstream(http):
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        contribution = material['scientific_candidates'][0]['contribution']
        choices = [a for a in material['scientific_candidates'] if a['contribution'] == contribution]
        assert [a['occurrence'] for a in choices] == [1, 2]
        candidate = choices[1]
        chosen.append(candidate)
        plan = {'suggested_objectives': ['Explicar o RNA mensageiro.'], 'suggestions': [{
            'candidate_id': candidate['id'],
            'pedagogical_rationale': 'Relacionar o conceito à documentação.', 'suggested_content': 'Compare o mecanismo e a fonte.'}]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', headers=ORIGIN, json={
            'title': 'RNA', 'material_text': '🧬 µ · xmRNA; mRNA e mRNA.'})
        assert response.status_code == 201
        assert response.json()['suggestions'][0]['source_anchor']['occurrence'] == chosen[0]['occurrence'] == 2
        assert chosen[0]['quote'] == 'mRNA'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('payload,expected_quote,expected_document,coverage', [
    ({'material_text': 'CRISPR-Cas9.'}, 'Cas9', 'text', 4),
    ({'material_text': 'RNA mensageiro.'}, 'RNA mensageiro', 'text', 2),
    ({'material_text': '🧬 EDIC\u0327A\u0303O GENO\u0302MICA.'}, 'EDIC\u0327A\u0303O GENO\u0302MICA', 'text', 2),
    ({'material_text': '🧬 EDIÇÃO GENÔMICA.'}, 'EDIÇÃO GENÔMICA', 'text', 2),
    ({'material_text': 'Movimento uniforme.', 'concepts': ['mRNA']}, 'mRNA', 'concept_list', 2),
    ({'material_text': 'Movimento uniforme.', 'doi': RNA['doi']}, None, 'paper_metadata', 2),
    ({'material_text': 'Movimento uniforme.'}, None, None, 0),
])
def test_canonical_selection_covers_only_grounded_science(client, monkeypatch, payload, expected_quote, expected_document, coverage):
    from types import SimpleNamespace
    from studio_flow_provider import FlowProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    external, seen = FlowProvider(), []
    async def upstream(http):
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        matches = material['scientific_contributions']
        assert len(matches) == coverage
        choices = material['scientific_candidates']
        assert len(choices) <= 8
        if coverage:
            anchor = choices[0]
            document = next(d for d in material['source_documents'] if d['key'] == anchor['document'])
            assert document['type'] == expected_document
            assert anchor['quote'] in document['content']
            if expected_quote is not None:
                assert anchor['quote'] == expected_quote
        else:
            assert choices == []
        seen.append(True)
        result = await external.complete(SimpleNamespace(stage='preview', material=material, prompt_version='controlled'))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': result.content.decode()}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', json={'title': 'Ciências', **payload}, headers=ORIGIN)
        assert response.status_code == 201 and seen == [True]
        preview = response.json()
        assert bool(preview['suggestions']) is bool(coverage)
        if not coverage:
            assert preview['evidence_references'] == [] and any('Sem cobertura' in x for x in preview['limitations'])
        assert client.get('/api/studio/previews/' + preview['preview_id']).json()['suggestions'] == preview['suggestions']
    finally:
        app.dependency_overrides.clear()


def test_keyword_only_coverage_without_literal_document_anchor_fails_before_inference(client, provider, caplog):
    from datetime import datetime, timezone
    from app.services.storage import save_cache
    caplog.set_level('INFO', logger='matilda.studio.validation')
    doi = '10.9999/keyword-only'
    save_cache(doi, {'id': 'https://openalex.org/W999999', 'doi': 'https://doi.org/' + doi,
        'title': 'Documento sem trecho do conceito.', 'keywords': [{'display_name': 'mRNA'}]},
        datetime.now(timezone.utc).isoformat())
    response = client.post('/api/studio/preview', json={'title': 'Ciências', 'doi': doi}, headers=ORIGIN)
    assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
    assert response.json()['retryable'] is False and provider.requests == []
    assert '"code":"missing_grounded_anchor"' in caplog.text
    assert '"authorized_contributions":2' in caplog.text
    assert 'Documento sem trecho' not in caplog.text


def test_anchor_ids_stable_on_retry_and_rejected_in_another_operation(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    payloads, stale = [], []
    def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        payloads.append((material['scientific_candidates'], body['response_format']))
        candidate = material['scientific_candidates'][0]
        # First operation: controlled retry after an invalid ID, then a valid selection.
        # Second operation: an old (once valid) identifier must be rejected twice.
        if len(payloads) == 1:
            stale.append(candidate['id'])
        anchor_id = 'unknown' if len(payloads) == 1 else candidate['id'] if len(payloads) == 2 else stale[0]
        plan = {'suggested_objectives': ['Explicar o conceito.'], 'suggestions': [{
            'candidate_id': anchor_id,
            'pedagogical_rationale': 'Relacionar à documentação.', 'suggested_content': 'Discuta o mecanismo.'}]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        first = client.post('/api/studio/preview', json=RNA, headers=ORIGIN)
        assert first.status_code == 201
        assert payloads[0] == payloads[1]
        second = client.post('/api/studio/preview', json=RNA, headers=ORIGIN)
        assert second.status_code == 502 and len(payloads) == 4
        assert stale[0] not in {a['id'] for a in payloads[2][0]}
        assert '"code":"invalid_scientific_candidate"' in caplog.text
        assert client.get('/api/studio/previews/' + first.json()['preview_id']).status_code == 200
    finally:
        app.dependency_overrides.clear()
