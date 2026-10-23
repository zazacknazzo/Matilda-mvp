"""Coarse authoring gates reject missing pedagogy, without grading teachers."""
from copy import deepcopy
import asyncio
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_lesson_smoke import module
from test_nvidia_provider import completion, request_for
from studio_flow_provider import FlowProvider
from test_studio_flow import create, generate, review


def test_a_lesson_of_only_titles_is_not_published_as_fifty_minutes(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client), accept=False)
    value = compact_lesson()
    for section in value['sections']:
        for slide in section['slides']:
            slide['content'] = {'layout': 'TITLE'}
    provider = module().SingleCallNVIDIA(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        response = generate(client, saved)
        assert response.status_code == 502
        assert 'lesson_pedagogy_insufficient' in caplog.text
        current = client.get('/api/studio/previews/' + saved['preview_id']).json()
        assert current['last_lesson_bundle_id'] is None
        assert current['suggestions'] == saved['suggestions']
        assert provider.calls == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('field', ['prompt', 'teacher_guidance', 'assessment_criteria'])
def test_perfunctory_activity_fields_are_rejected_without_completion(monkeypatch, field):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    value = compact_lesson()
    value['sections'][-1]['activities'][0][field] = ['Ok.'] if field == 'assessment_criteria' else 'Ok.'
    provider = module().SingleCallNVIDIA(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson')))


@pytest.mark.parametrize('fault,missing', [
    ('teaching', 'objective_teaching_coverage_missing'),
    ('assessment', 'objective_assessment_coverage_missing'),
    ('conceptual', 'conceptual_content_below_floor'),
])
def test_objective_labels_or_tiny_concepts_do_not_certify_pedagogy(monkeypatch, caplog, fault, missing):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    value = compact_lesson()
    value['sections'][1]['objective_indexes'] = [0, 1]
    value['sections'][-1]['activities'][0]['objective_indexes'] = [0, 1]
    if fault == 'teaching':
        value['sections'][1]['objective_indexes'] = [0]
    elif fault == 'assessment':
        value['sections'][-1]['activities'][0]['objective_indexes'] = [0]
    else:
        value['sections'][1]['slides'][0]['content']['text'] = 'DNA.'
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson', material={
            'configuration': {'duration_minutes': 50, 'learning_objectives': ['A.', 'B.']}})))
    assert 'lesson_pedagogy_insufficient' in caplog.text and missing in caplog.text


def test_quality_report_is_sanitized_and_explicit_about_teacher_review(client, monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    def upstream(http):
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        value = compact_lesson()
        value['sections'][0]['slides'][0]['evidence_ids'] = list(material['authorized_evidence'])
        return httpx.Response(200, json=completion(json.dumps(value)))
    provider = module().SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    report = module().run_lesson_smoke(provider)
    assert report['status'] == 'passed' and provider.calls == 1
    quality = next(event for event in report['events'] if event['type'] == 'nvidia_lesson_quality')
    assert quality['structural_checks_passed'] is True
    assert quality['taught_objectives'] == quality['assessed_objectives'] == quality['objective_count'] == 1
    assert quality['used_evidence_count'] == 1 and quality['approved_minutes'] == 50
    assert quality['teacher_review_required'] is True
    assert set(quality['teacher_review_points']) >= {
        'conceptual_depth', 'instructional_notes', 'activity_applicability',
        'semantic_objective_alignment', 'scientific_relevance', 'pacing'}
    rendered = json.dumps(report)
    assert 'PRIVATE_CREDENTIAL' not in rendered
    assert 'O RNA guia reconhece' not in rendered
    assert 'Explique cada etapa a partir do material' not in rendered
