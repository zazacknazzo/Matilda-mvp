"""Sanitized NVIDIA authoring diagnostics, exercised over hosted MockTransport."""
import asyncio
import json

import httpx
import pytest

from app.integrations.nvidia_client import NVIDIAProvider
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_provider import completion, request_for


def event_for(monkeypatch, caplog, value, **changes):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    calls = []
    def upstream(_):
        calls.append(1)
        return httpx.Response(200, json=completion(json.dumps(value)))
    provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
    with pytest.raises((ValueError, KeyError, TypeError)):
        asyncio.run(provider.complete(request_for('lesson', **changes)))
    assert calls == [1]
    events = [json.loads(r.message.removeprefix('nvidia_attempt ')) for r in caplog.records
              if r.message.startswith('nvidia_attempt ')]
    assert len(events) == 1 and events[0]['phase'] == 'validation'
    assert not any(private in caplog.text for private in ('PRIVATE_CREDENTIAL', 'PRIVATE_TEACHER', 'PRIVATE_SOURCE'))
    return events[0]


@pytest.mark.parametrize('first_minutes', [10, 11])
def test_legacy_minutes_are_rejected_without_repair(monkeypatch, caplog, first_minutes):
    value = compact_lesson()
    for section in value['sections']:
        section['duration_minutes'] = section.pop('time_weight')
    value['sections'][0]['duration_minutes'] = first_minutes
    event = event_for(monkeypatch, caplog, value)
    assert event['failure_code'] == 'lesson_schema_invalid'


@pytest.mark.parametrize('material,code', [
    ({}, 'lesson_configuration_missing'),
    ({'configuration': {}}, 'lesson_configuration_missing'),
    ({'configuration': {'duration_minutes': 'PRIVATE_TEACHER'}}, 'lesson_configuration_invalid'),
])
def test_configuration_failures_are_distinct(monkeypatch, caplog, material, code):
    event = event_for(monkeypatch, caplog, compact_lesson(), material=material)
    assert event['failure_code'] == code


def test_structural_failure_does_not_log_pydantic_input(monkeypatch, caplog):
    value = compact_lesson()
    value['sections'][0]['slides'][0]['speaker_notes'] = {'PRIVATE_TEACHER': 'PRIVATE_SOURCE'}
    event = event_for(monkeypatch, caplog, value)
    assert event['outcome'] == 'pydantic_validation' and event['failure_code'] == 'lesson_schema_invalid'


def test_expansion_failure_is_distinct_and_sanitized(monkeypatch, caplog):
    import app.integrations.nvidia_lesson as lesson
    def broken(**kwargs):
        raise ValueError('PRIVATE_TEACHER PRIVATE_SOURCE')
    monkeypatch.setattr(lesson, 'LessonDraft', broken)
    event = event_for(monkeypatch, caplog, compact_lesson())
    assert event['failure_code'] == 'lesson_expansion_invalid'


@pytest.mark.parametrize('duration', [True, 9, 121, 50.0, None])
def test_invalid_approved_duration_is_not_coerced(monkeypatch, caplog, duration):
    event = event_for(monkeypatch, caplog, compact_lesson(), material={'configuration': {'duration_minutes': duration, 'learning_objectives': ['Approved.']}})
    assert event['failure_code'] == 'lesson_configuration_invalid'


def test_insufficient_time_for_slide_minimum_is_distinct(monkeypatch, caplog):
    from test_nvidia_compact_lesson import weighted_lesson
    event = event_for(monkeypatch, caplog, weighted_lesson([4, 4, 4], [1, 1, 1]),
                      material={'configuration': {'duration_minutes': 10, 'learning_objectives': ['Approved.']}})
    assert event['failure_code'] == 'lesson_time_budget_infeasible'
    assert event['approved_minutes'] == 10 and event['minimum_minutes'] == 12


def test_expanded_size_limit_is_enforced_before_return(monkeypatch, caplog):
    from test_nvidia_compact_lesson import weighted_lesson
    value = weighted_lesson([4, 4, 4], [1, 1, 1])
    value['prior_knowledge'] = ['x' * 20000] * 5
    for section in value['sections']:
        for slide in section['slides']:
            slide['speaker_notes'] = 'y' * 1500
    event = event_for(monkeypatch, caplog, value)
    assert event['outcome'] == 'response_too_large'
    assert event['failure_code'] == 'lesson_expanded_response_too_large'
