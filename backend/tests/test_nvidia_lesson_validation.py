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


def test_wrong_total_has_specific_sanitized_diagnostic(monkeypatch, caplog):
    value = compact_lesson()
    value['sections'][0]['duration_minutes'] = 11
    event = event_for(monkeypatch, caplog, value)
    assert event['failure_code'] == 'lesson_duration_mismatch'
    assert event['approved_minutes'] == 50 and event['section_minutes'] == 51


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
