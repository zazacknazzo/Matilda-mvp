"""Scientific candidate selection through public HTTP and controlled hosted HTTP."""
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from app.schemas.scientific_context import SourceAnchor, SourceDocument
from test_studio_canonical_anchors import RNA
from test_studio_candidate_budget import CRISPR
from test_studio_preview import ORIGIN


def test_rna_model_selects_one_candidate_server_owns_all_scientific_fields(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    selected = []
    def upstream(http):
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        properties = body['response_format']['json_schema']['schema']['$defs']['PlannedSuggestion']['properties']
        assert set(properties) == {'candidate_id', 'pedagogical_rationale', 'suggested_content'}
        candidate = material['scientific_candidates'][0]
        contribution = material['scientific_contributions'][candidate['contribution']]
        assert contribution['title'] == 'Modificações de nucleosídeos e reconhecimento imune de RNA'
        assert contribution['evidence_claims']
        document = next(d for d in material['source_documents'] if d['key'] == candidate['document'])
        assert candidate['quote'] == 'RNA mensageiro' and candidate['quote'] in document['content']
        selected.append(candidate)
        plan = {'suggested_objectives': ['Explicar o mecanismo molecular.'], 'suggestions': [{
            'candidate_id': candidate['id'], 'pedagogical_rationale': 'Relacionar o mecanismo ao material.',
            'suggested_content': 'Compare a fonte documental e o mecanismo molecular.'}]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', json=RNA, headers=ORIGIN)
        assert response.status_code == 201
        suggestion = response.json()['suggestions'][0]
        assert suggestion['contribution_id'] == 'rna-2005'
        assert suggestion['concept_ids'] == ['mrna'] and suggestion['evidence_ids'] == ['evidence-rna-2005']
        assert suggestion['source_anchor']['quote'] == selected[0]['quote']
        assert suggestion['source_anchor']['occurrence'] == selected[0]['occurrence']
        assert suggestion['researcher_ids'] == ['kariko']
        assert '"scientific_authority_valid":true' in caplog.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('payload', [CRISPR, {**RNA, 'concepts': ['mRNA']}], ids=['crispr', 'rna-multiple-documents'])
def test_all_contributions_and_document_choices_preserve_forensics_authority(client, monkeypatch, payload):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    analysis = client.post('/api/analyses', json={'doi': payload['doi']}).json()
    authority = {m['contribution']['id']: m for m in analysis['contributions']}
    selected, sent_documents = [], []
    def upstream(http):
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        selected.extend(material['scientific_candidates'])
        sent_documents.extend(material['source_documents'])
        assert len(selected) <= 8
        assert len({c['contribution'] for c in selected}) == len(authority)
        assert len({c['document'] for c in selected}) >= 2
        plan = {'suggested_objectives': ['Comparar o mecanismo e a documentação.'], 'suggestions': [{
            'candidate_id': candidate['id'], 'pedagogical_rationale': 'Relacionar o conceito ao material.',
            'suggested_content': 'Discuta o conceito e confronte a documentação.'} for candidate in selected]}
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(plan)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = client.post('/api/studio/preview', json=payload, headers=ORIGIN)
        assert response.status_code == 201
        value = response.json()
        assert {s['contribution_id'] for s in value['suggestions']} == set(authority)
        references = {r['id']: r for r in value['evidence_references']}
        for chosen, suggestion in zip(selected, value['suggestions'], strict=True):
            trusted = authority[suggestion['contribution_id']]
            assert set(suggestion['concept_ids']) <= {c['id'] for c in trusted['matched_concepts']}
            assert suggestion['researcher_ids'] == trusted['contribution']['researcher_ids']
            assert set(suggestion['evidence_ids']) == {e['id'] for e in trusted['evidence']}
            for evidence in trusted['evidence']:
                assert references[evidence['id']]['participants'] == trusted['contribution']['participants']
                assert all(references[evidence['id']][key] == item for key, item in evidence.items())
            document = next(d for d in value['source_documents'] if d['id'] == suggestion['source_anchor']['source_document_id'])
            sent = next(d for d in sent_documents if d['key'] == chosen['document'])
            assert document['content'] == sent['content']
            anchor = SourceAnchor.model_validate(suggestion['source_anchor'])
            assert anchor.quote == chosen['quote'] and anchor.occurrence == chosen['occurrence']
            start, end = anchor.locate(SourceDocument.model_validate(document))
            assert document['content'][start:end] == chosen['quote']
        resumed = client.get('/api/studio/previews/' + value['preview_id']).json()
        assert resumed['suggestions'] == value['suggestions']
    finally:
        app.dependency_overrides.clear()
