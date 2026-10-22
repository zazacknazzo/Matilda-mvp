"""Compact NVIDIA authoring contract, observed through HTTP and canonical bundle."""
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from studio_flow_provider import FlowProvider
from test_studio_flow import create, generate, review


def compact_lesson():
    return {'prior_knowledge': ['Noções de DNA.'], 'materials': ['Quadro.'], 'limitations': [], 'sections': [
        {'title': 'Introdução', 'duration_minutes': 10, 'objective_indexes': [0], 'slides': [
            {'layout': 'TITLE', 'title': 'Questão inicial', 'content_blocks': [{'type': 'text', 'text': 'Como investigar o mecanismo?'}], 'speaker_notes': 'Levante hipóteses com a turma.'}], 'activities': []},
        {'title': 'Mecanismo', 'duration_minutes': 25, 'objective_indexes': [0], 'slides': [
            {'layout': 'CONCEPT', 'title': 'Mecanismo molecular', 'content_blocks': [{'type': 'text', 'text': 'Compare os conceitos do material.'}], 'speaker_notes': 'Explique cada etapa a partir do material.'},
            {'layout': 'SUMMARY', 'title': 'Análise da documentação', 'content_blocks': [{'type': 'text', 'text': 'Distinga mecanismo e documentação.'}], 'speaker_notes': 'Peça justificativas para a comparação.'}], 'activities': []},
        {'title': 'Avaliação', 'duration_minutes': 15, 'objective_indexes': [0], 'slides': [
            {'layout': 'QUESTION', 'title': 'Conferir a compreensão', 'content_blocks': [{'type': 'question', 'text': 'Como sustentar a explicação?'}], 'speaker_notes': 'Discuta as respostas e as limitações.'}],
         'activities': [{'type': 'discussion', 'prompt': 'Explique o mecanismo com apoio no material.', 'teacher_guidance': 'Solicite uma justificativa.', 'objective_indexes': [0], 'assessment_criteria': ['Conceitos e justificativa coerentes.']}]},
    ]}


def test_compact_authoring_builds_canonical_links_times_plan_read_and_markdown(client, monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    calls = []
    def upstream(http):
        body = json.loads(http.content)
        calls.append(body)
        schema = body['response_format']['json_schema']['schema']
        assert body['reasoning_effort'] == 'none' and body['stream'] is False
        section = schema['$defs']['CompactSection']['properties']
        assert 'slides' in section and 'slide_keys' not in section and 'key' not in section
        material = json.loads(body['messages'][1]['content'])
        assert set(material['source_documents'][0]) == {'type', 'content'}
        value = compact_lesson()
        evidence = next(iter(material['authorized_evidence']))
        value['sections'][1]['slides'][1]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': evidence})
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1400, 'completion_tokens': 1600},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = generate(client, saved)
        assert response.status_code == 201
        bundle = response.json()
        assert len(bundle['sections']) == 3 and len(bundle['slides']) == 4 and len(bundle['activities']) == 1
        assert [s['duration_minutes'] for s in bundle['slides']] == [10, 13, 12, 15]
        assert sum(s['duration_minutes'] for s in bundle['sections']) == 50
        assert bundle['sections'][1]['slide_ids'] == [s['id'] for s in bundle['slides'][1:3]]
        assert bundle['sections'][2]['activity_ids'] == [bundle['activities'][0]['id']]
        assert any(b.get('text') == 'Explique cada etapa a partir do material.' for b in bundle['sections'][1]['explanation_blocks'])
        assert bundle['references'] and bundle['references'][0]['participants']
        path = '/api/studio/lessons/' + bundle['lesson_bundle_id']
        assert client.get(path).json() == bundle
        assert client.get(path + '/export?format=markdown').status_code == 200
        assert generate(client, saved).json() == bundle and len(calls) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('failure', ['empty_notes', 'wrong_total', 'too_many_slides', 'unauthorized_evidence', 'invalid_objective'])
def test_invalid_compact_lesson_never_publishes_or_changes_teacher_review(client, monkeypatch, failure):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    def upstream(_):
        value = compact_lesson()
        if failure == 'empty_notes':
            value['sections'][0]['slides'][0]['speaker_notes'] = ''
        elif failure == 'wrong_total':
            value['sections'][0]['duration_minutes'] = 11
        elif failure == 'too_many_slides':
            value['sections'][0]['slides'] *= 10
        elif failure == 'unauthorized_evidence':
            value['sections'][0]['slides'][0]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'private-invalid'})
        else:
            value['sections'][0]['objective_indexes'] = [999]
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1400, 'completion_tokens': 1600},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]})
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = generate(client, saved)
        assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
        resumed = client.get('/api/studio/previews/' + saved['preview_id']).json()
        assert resumed['suggestions'] == saved['suggestions'] and resumed['approved_objectives'] == saved['approved_objectives']
        assert resumed['last_lesson_bundle_id'] is None and resumed['generation_status'] == 'failed'
    finally:
        app.dependency_overrides.clear()
