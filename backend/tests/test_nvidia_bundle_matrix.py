"""Combinatorial valid lessons through NVIDIA HTTP, frozen review and SQLite."""
from copy import deepcopy
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from app.schemas.lesson import LessonBundle
from studio_flow_provider import FlowProvider
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_provider import completion
from test_studio_flow import create, generate
from test_studio_preview import ORIGIN


CASES = [(sections, slides, activities, evidence)
         for sections in range(3, 9) for slides in (max(4, sections), 12)
         for activities in (1, 4) for evidence in (False, True)]


def authored_lesson(sections, slides, activities, allowed):
    template = compact_lesson()
    sample = template['sections'][0]['slides'][0]
    activity = template['sections'][-1]['activities'][0]
    result = {**template, 'sections': []}
    layouts = ['TITLE', 'CONCEPT', 'PROCESS', 'QUESTION', 'SUMMARY']
    if allowed:
        layouts.append('SCIENTIST_SPOTLIGHT')
    for section_index in range(sections):
        result['sections'].append({'title': f'Etapa {section_index + 1}', 'time_weight': section_index + 1,
                                   'objective_indexes': [section_index % 2], 'slides': [], 'activities': []})
    for index in range(slides):
        slide = deepcopy(sample)
        slide.update(layout=layouts[index % len(layouts)], title='Mecanismo e documentação',
                     speaker_notes='Nota do modelo: peça uma explicação e examine as justificativas.')
        if slide['layout'] == 'PROCESS':
            slide['content_blocks'] = [{'type': 'steps', 'items': ['Leia o mecanismo.', 'Compare as etapas.']}]
        elif slide['layout'] == 'QUESTION':
            slide['content_blocks'] = [{'type': 'question', 'text': 'Como justificar o mecanismo?'}]
        elif slide['layout'] == 'SCIENTIST_SPOTLIGHT':
            slide['content_blocks'] = [{'type': 'evidence_claim', 'evidence_id': sorted(allowed)[0]}]
        elif index == 0 and allowed:
            slide['content_blocks'].extend({'type': 'evidence_claim', 'evidence_id': key} for key in sorted(allowed))
        result['sections'][index % sections]['slides'].append(slide)
    for index in range(activities):
        value = deepcopy(activity)
        value['objective_indexes'] = [index % 2]
        result['sections'][-1]['activities'].append(value)
    return result


@pytest.mark.parametrize('sections,slides,activities,evidence', CASES)
def test_combinations_reach_bundle_sqlite_replay_and_markdown(client, monkeypatch, sections, slides, activities, evidence):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    initial = create(client)
    saved = client.post('/api/studio/previews/' + initial['preview_id'] + '/review', headers=ORIGIN, json={
        'review_revision': initial['review_revision'], 'approved_objectives': ['Explicar o mecanismo.', 'Examinar a documentação.'],
        'decisions': [{'suggestion_id': item['id'], 'status': 'accepted' if evidence else 'rejected'} for item in initial['suggestions']],
    }).json()
    calls = []
    def upstream(http):
        calls.append(1)
        body = json.loads(http.content)
        material = json.loads(body['messages'][1]['content'])
        allowed = material['authorized_evidence']
        assert bool(allowed) is evidence
        assert len(material['configuration']['learning_objectives']) == 2
        schema = body['response_format']['json_schema']['schema']
        if evidence:
            assert schema['$defs']['EvidenceClaimBlock']['properties']['evidence_id']['enum'] == sorted(allowed)
        else:
            assert 'EvidenceClaimBlock' not in schema['$defs']
        value = authored_lesson(sections, slides, activities, allowed)
        return httpx.Response(200, json=completion(json.dumps(value)))
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = generate(client, saved)
        assert response.status_code == 201, response.text
        bundle = LessonBundle.model_validate(response.json())
        assert (len(bundle.sections), len(bundle.slides), len(bundle.activities)) == (sections, slides, activities)
        assert bundle.metadata.duration_minutes == sum(s.duration_minutes for s in bundle.sections) == 50
        assert sum(s.duration_minutes for s in bundle.slides) == 50
        assert all(slide.duration_minutes >= 1 for slide in bundle.slides)
        assert bundle.metadata.learning_objectives == saved['approved_objectives']
        assert bundle.review_revision == saved['review_revision']
        assert all(slide.speaker_notes == 'Nota do modelo: peça uma explicação e examine as justificativas.' for slide in bundle.slides)
        trusted = {reference['id']: reference for reference in saved['evidence_references']}
        for reference in bundle.references:
            assert reference.model_dump() == trusted[reference.id]
        assert bool(bundle.references) is evidence
        expected_layouts = {'TITLE', 'CONCEPT', 'PROCESS', 'QUESTION', 'SUMMARY'}
        if evidence:
            expected_layouts.add('SCIENTIST_SPOTLIGHT')
        if slides >= len(expected_layouts):
            assert {slide.layout for slide in bundle.slides} == expected_layouts
        accepted = {key for item in saved['suggestions'] if item['status'] == 'accepted' for key in item['evidence_ids']}
        assert {reference.id for reference in bundle.references} == accepted
        for section in bundle.sections:
            owned = [slide for slide in bundle.slides if slide.section_id == section.id]
            assert set(section.slide_ids) == {slide.id for slide in owned}
            assert sum(slide.duration_minutes for slide in owned) == section.duration_minutes
        for slide in bundle.slides:
            assert {reference.contribution_id for reference in bundle.references if reference.id in slide.evidence_ids} == set(slide.contribution_ids)
        path = '/api/studio/lessons/' + bundle.lesson_bundle_id
        assert client.get(path).json() == response.json()
        replay = generate(client, saved)
        assert replay.status_code == 200 and replay.json() == response.json()
        exported = client.get(path + '/export?format=markdown')
        assert exported.status_code == 200 and 'attachment' in exported.headers['content-disposition']
        current = client.get('/api/studio/previews/' + saved['preview_id']).json()
        assert current['last_lesson_bundle_id'] == bundle.lesson_bundle_id and current['generation_status'] == 'ready'
        assert current['suggestions'] == saved['suggestions'] and current['approved_objectives'] == saved['approved_objectives']
        assert calls == [1]
    finally:
        app.dependency_overrides.clear()
