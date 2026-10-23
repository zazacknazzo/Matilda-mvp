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
        {'title': 'Introdução', 'time_weight': 10, 'objective_indexes': [0], 'slides': [
            {'title': 'Questão inicial', 'content': {'layout': 'TITLE', 'introduction': 'Como investigar o mecanismo?'}, 'speaker_notes': 'Levante hipóteses com a turma. Peça que cada grupo descreva como testaria sua explicação e compare as justificativas apresentadas.'}], 'activities': []},
        {'title': 'Mecanismo', 'time_weight': 25, 'objective_indexes': [0], 'slides': [
            {'title': 'Mecanismo molecular', 'content': {'layout': 'CONCEPT', 'text': 'O RNA guia reconhece uma sequência complementar no DNA e orienta a proteína para o local de clivagem. Distinga reconhecimento, ligação e corte molecular.'}, 'speaker_notes': 'Explique cada etapa a partir do material. Peça aos alunos que relacionem o reconhecimento da sequência de DNA ao papel do RNA e justifiquem a resposta.'},
            {'title': 'Análise da documentação', 'content': {'layout': 'SUMMARY', 'synthesis': 'Distinga mecanismo e documentação.'}, 'speaker_notes': 'Peça justificativas para a comparação. Solicite que os grupos diferenciem os mecanismos moleculares das afirmações históricas documentadas nas fontes.'}], 'activities': []},
        {'title': 'Avaliação', 'time_weight': 15, 'objective_indexes': [0], 'slides': [
            {'title': 'Conferir a compreensão', 'content': {'layout': 'QUESTION', 'question': 'Como sustentar a explicação?'}, 'speaker_notes': 'Discuta as respostas e as limitações. Registre os argumentos apresentados, examine as evidências citadas e retome as dúvidas sobre o mecanismo molecular.'}],
         'activities': [{'type': 'discussion', 'prompt': 'Explique o mecanismo com apoio no material.', 'teacher_guidance': 'Solicite uma justificativa e compare os argumentos de cada grupo com o mecanismo descrito no material.', 'objective_indexes': [0], 'assessment_criteria': ['Conceitos e justificativa coerentes.']}]},
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
        value['sections'][1]['slides'][1].setdefault('evidence_ids', []).append(evidence)
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
        assert any(b.get('text') == 'Explique cada etapa a partir do material. Peça aos alunos que relacionem o reconhecimento da sequência de DNA ao papel do RNA e justifiquem a resposta.' for b in bundle['sections'][1]['explanation_blocks'])
        assert bundle['references'] and bundle['references'][0]['participants']
        path = '/api/studio/lessons/' + bundle['lesson_bundle_id']
        assert client.get(path).json() == bundle
        assert client.get(path + '/export?format=markdown').status_code == 200
        assert generate(client, saved).json() == bundle and len(calls) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('failure', ['empty_notes', 'legacy_minutes', 'too_many_slides', 'unauthorized_evidence', 'invalid_objective'])
def test_invalid_compact_lesson_never_publishes_or_changes_teacher_review(client, monkeypatch, failure):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    def upstream(_):
        value = compact_lesson()
        if failure == 'empty_notes':
            value['sections'][0]['slides'][0]['speaker_notes'] = ''
        elif failure == 'legacy_minutes':
            value['sections'][0]['duration_minutes'] = 11
        elif failure == 'too_many_slides':
            value['sections'][0]['slides'] *= 10
        elif failure == 'unauthorized_evidence':
            value['sections'][0]['slides'][0].setdefault('evidence_ids', []).append('private-invalid')
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


def test_weighted_sections_allocate_approved_time_through_provider(monkeypatch):
    import asyncio
    from app.services.studio.lesson_validator import LessonDraft
    from test_nvidia_provider import completion, request_for
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    value = compact_lesson()
    for section, weight in zip(value['sections'], (1, 1, 1)):
        section['time_weight'] = weight
    calls = []
    def upstream(http):
        calls.append(1)
        schema = json.loads(http.content)['response_format']['json_schema']['schema']
        properties = schema['$defs']['CompactSection']['properties']
        assert 'time_weight' in properties and 'duration_minutes' not in properties
        return httpx.Response(200, json=completion(json.dumps(value)))
    provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
    result = asyncio.run(provider.complete(request_for('lesson')))
    draft = LessonDraft.model_validate_json(result.content)
    assert [s.duration_minutes for s in draft.sections] == [17, 17, 16]
    assert [s.duration_minutes for s in draft.slides] == [17, 9, 8, 16]
    assert calls == [1]


def weighted_lesson(slide_counts, weights):
    from copy import deepcopy
    value = compact_lesson()
    template = {**value['sections'][0], 'slides': [value['sections'][1]['slides'][0]]}
    activity = value['sections'][-1]['activities'][0]
    value['sections'] = []
    for count, weight in zip(slide_counts, weights):
        section = deepcopy(template)
        section['time_weight'] = weight
        section['slides'] = [deepcopy(template['slides'][0]) for _ in range(count)]
        value['sections'].append(section)
    value['sections'][-1]['activities'] = [activity]
    return value


@pytest.mark.parametrize('counts,weights,expected', [
    ([1, 2, 1], [1, 1, 1], [17, 17, 16]),
    ([1, 1, 1, 1], [1, 1, 1, 1], [13, 13, 12, 12]),
    ([2, 1, 3, 1, 1], [1, 1, 1, 1, 1], [11, 10, 11, 9, 9]),
    ([1, 1, 1, 1], [1, 2, 3, 4], [6, 10, 15, 19]),
    ([1, 1, 10], [1000, 1, 1], [39, 1, 10]),
    ([1, 1, 2], [1, 1000, 1], [1, 47, 2]),
    ([1, 1, 1, 1, 1], [1000, 1, 1, 1, 1], [46, 1, 1, 1, 1]),
    ([4, 4, 4], [1000, 1000, 1000], [17, 17, 16]),
    ([1] * 8, [1] * 8, [7, 7, 6, 6, 6, 6, 6, 6]),
])
def test_weighted_time_survives_full_bundle_validation_without_evidence(
    client, monkeypatch, counts, weights, expected,
):
    from app.schemas.lesson import LessonBundle
    from test_nvidia_provider import completion
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-key')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client), accept=False)
    value = weighted_lesson(counts, weights)
    calls = []
    def upstream(http):
        calls.append(1)
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        assert material['authorized_evidence'] == {}
        return httpx.Response(200, json=completion(json.dumps(value)))
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = generate(client, saved)
        assert response.status_code == 201, response.text
        bundle = LessonBundle.model_validate(response.json())
        assert [s.duration_minutes for s in bundle.sections] == expected
        assert bundle.metadata.duration_minutes == sum(expected) == 50
        assert len(bundle.slides) == sum(counts) and len(bundle.activities) == 1
        assert bundle.references == []
        for section, count in zip(bundle.sections, counts):
            slides = [slide for slide in bundle.slides if slide.section_id == section.id]
            assert len(slides) == count
            assert sum(slide.duration_minutes for slide in slides) == section.duration_minutes
            assert all(type(slide.duration_minutes) is int and slide.duration_minutes >= 1 for slide in slides)
            assert max(slide.duration_minutes for slide in slides) - min(slide.duration_minutes for slide in slides) <= 1
            assert all(slide.evidence_ids == [] and slide.contribution_ids == [] for slide in slides)
            assert all(slide.speaker_notes == value['sections'][0]['slides'][0]['speaker_notes'] for slide in slides)
        assert calls == [1]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('weight', [0, -1, 1001, True, 1.5, '1', None])
def test_invalid_weights_are_not_repaired(monkeypatch, caplog, weight):
    from test_nvidia_lesson_validation import event_for
    value = compact_lesson()
    value['sections'][0]['time_weight'] = weight
    event = event_for(monkeypatch, caplog, value)
    assert event['failure_code'] == 'lesson_schema_invalid'


@pytest.mark.parametrize('fault', ['missing_weight', 'legacy_only', 'no_activities', 'five_activities',
    'three_slides', 'thirteen_slides', 'two_sections', 'nine_sections', 'missing_notes', 'blank_notes',
    'missing_prompt', 'missing_guidance', 'missing_criteria'])
def test_missing_pedagogy_and_invalid_counts_are_rejected(monkeypatch, caplog, fault):
    from test_nvidia_lesson_validation import event_for
    value = compact_lesson()
    section = value['sections'][0]
    activity = value['sections'][-1]['activities'][0]
    if fault == 'missing_weight':
        del section['time_weight']
    elif fault == 'legacy_only':
        for item in value['sections']:
            item['duration_minutes'] = item.pop('time_weight')
    elif fault == 'no_activities':
        value['sections'][-1]['activities'] = []
    elif fault == 'five_activities':
        section['activities'] = [activity] * 4
    elif fault == 'three_slides':
        value['sections'][1]['slides'].pop()
    elif fault == 'thirteen_slides':
        section['slides'] *= 10
    elif fault == 'two_sections':
        value['sections'].pop()
    elif fault == 'nine_sections':
        value['sections'] += [section] * 6
    elif fault == 'missing_notes':
        del section['slides'][0]['speaker_notes']
    elif fault == 'blank_notes':
        section['slides'][0]['speaker_notes'] = '  '
    else:
        del activity[{'missing_prompt': 'prompt', 'missing_guidance': 'teacher_guidance',
                      'missing_criteria': 'assessment_criteria'}[fault]]
    event = event_for(monkeypatch, caplog, value)
    assert event['failure_code'] == 'lesson_schema_invalid'
