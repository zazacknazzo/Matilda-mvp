"""Strict structured-content parsing across the NVIDIA hosted HTTP seam."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.integrations.nvidia_client import NVIDIAProvider
from app.studio.ports import ProviderFailure
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_provider import completion, request_for


def event_from(caplog):
    events = [json.loads(record.message.removeprefix('nvidia_attempt ')) for record in caplog.records
              if record.message.startswith('nvidia_attempt ')]
    assert len(events) == 1
    return events[0]


def rejected_content(monkeypatch, caplog, content):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    calls = []
    def upstream(_):
        calls.append(1)
        # Escaping in the envelope permits testing an unpaired surrogate in content.
        return httpx.Response(200, content=json.dumps(completion(content), ensure_ascii=True).encode('utf-8'))
    with pytest.raises(ValueError) as caught:
        asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for('lesson')))
    assert calls == [1]
    assert not any(secret in caplog.text + str(caught.value) for secret in
                   ('PRIVATE_SOURCE', 'PRIVATE_TEACHER', 'PRIVATE_CREDENTIAL'))
    return event_from(caplog)


def test_duplicate_key_is_diagnosed_without_exposing_key_or_content(monkeypatch, caplog):
    event = rejected_content(monkeypatch, caplog, '{"PRIVATE_SOURCE":1,"PRIVATE_SOURCE":2}')
    assert event['outcome'] == 'invalid_json' and event['phase'] == 'validation'
    assert event['failure_code'] == 'json_duplicate_key'


def test_trailing_comma_has_syntax_position_without_response_excerpt(monkeypatch, caplog):
    event = rejected_content(monkeypatch, caplog, '{"PRIVATE_TEACHER":"á",}')
    assert event['failure_code'] == 'json_syntax_invalid'
    # CPython versions point to either the comma or the following closing brace.
    assert event['error_position'] in (22, 23) and event['error_line'] == 1
    assert event['error_column'] in (23, 24)
    assert event['content_chars'] == 24 and event['content_bytes'] == 25
    assert event['finish_reason'] == 'stop'


@pytest.mark.parametrize('content,code', [
    pytest.param('{"text":"PRIVATE_TEACHER}', 'json_syntax_invalid', id='unclosed_quote'),
    pytest.param('{"text":"PRIVATE_TEACHER",}', 'json_syntax_invalid', id='trailing_comma'),
    pytest.param('```json\n{"text":"PRIVATE_TEACHER"}\n```', 'json_syntax_invalid', id='markdown'),
    pytest.param('{"text":', 'json_syntax_invalid', id='interrupted'),
    pytest.param('{"a":1} {"b":2}', 'json_syntax_invalid', id='multiple_roots'),
    pytest.param('[{"text":"PRIVATE_TEACHER"}]', 'json_root_not_object', id='array'),
    pytest.param('"PRIVATE_TEACHER"', 'json_root_not_object', id='string'),
    pytest.param('null', 'json_root_not_object', id='null'),
    pytest.param('42', 'json_root_not_object', id='number'),
    pytest.param('true', 'json_root_not_object', id='boolean'),
    pytest.param('{"n":NaN}', 'json_nonfinite_constant', id='nan'),
    pytest.param('{"n":Infinity}', 'json_nonfinite_constant', id='infinity'),
    pytest.param('{"n":-Infinity}', 'json_nonfinite_constant', id='negative_infinity'),
    pytest.param('{"n":undefined}', 'json_syntax_invalid', id='undefined'),
    pytest.param('{"n":None}', 'json_syntax_invalid', id='python_none'),
    pytest.param('{"nested":{"PRIVATE_SOURCE":1,"PRIVATE_SOURCE":2}}', 'json_duplicate_key', id='nested_duplicate'),
    pytest.param('{"a":1,"\\u0061":2}', 'json_duplicate_key', id='escaped_duplicate'),
    pytest.param('{"n":' + '9' * 5000 + '}', 'json_integer_too_large', id='integer_limit'),
    pytest.param('{"text":"\ud800"}', 'json_unicode_invalid', id='unpaired_surrogate'),
])
def test_content_categories_are_distinct_over_hosted_http(monkeypatch, caplog, content, code):
    event = rejected_content(monkeypatch, caplog, content)
    assert event['outcome'] == 'invalid_json' and event['failure_code'] == code
    assert event['json_target'] == 'message_content' and event['finish_reason'] == 'stop'
    assert event['model'] == 'nvidia/nemotron-3.5-super-vl-120b-a12b'
    assert event['content_chars'] == len(content)


def test_hosted_lesson_requests_strict_schema_and_explicit_json_object(monkeypatch, caplog):
    from app.services.studio.lesson_validator import LessonDraft
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    seen = []
    def upstream(http):
        body = json.loads(http.content)
        seen.append(body)
        assert body['response_format']['json_schema']['strict'] is True
        instruction = body['messages'][0]['content']
        assert 'um único objeto JSON completo' in instruction
        assert 'Sem Markdown' in instruction and 'aspas duplas' in instruction
        return httpx.Response(200, json=completion(json.dumps(compact_lesson())))
    result = asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for('lesson')))
    draft = LessonDraft.model_validate_json(result.content)
    assert sum(s.duration_minutes for s in draft.sections) == 50
    assert len(seen) == 1
    event = event_from(caplog)
    assert event['outcome'] == 'completed' and event['json_schema_strict'] is True


@pytest.mark.parametrize('body,code', [
    (b'{"PRIVATE_SOURCE":', 'json_syntax_invalid'),
    (b'{"PRIVATE_SOURCE":1,"PRIVATE_SOURCE":2}', 'json_duplicate_key'),
    (b'[]', 'json_root_not_object'),
    (b'{"n":NaN}', 'json_nonfinite_constant'),
    (b'\xff', 'json_unicode_invalid'),
])
def test_bad_envelope_is_not_reported_as_model_content(monkeypatch, caplog, body, code):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body)))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson')))
    event = event_from(caplog)
    assert event['outcome'] == 'invalid_response' and event['failure_code'] == code
    assert event['json_target'] == 'envelope' and 'content_chars' not in event
    assert 'PRIVATE_SOURCE' not in caplog.text


def test_transmitted_schema_preserves_v4_references_variants_and_required_fields(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    baseline = json.loads((Path(__file__).resolve().parents[2] /
                          'tests/fixtures/studio/nvidia/compact-v4-layouts.schema.json').read_text())
    def upstream(http):
        body = json.loads(http.content)
        response_format = body['response_format']
        assert response_format['type'] == 'json_schema'
        assert set(response_format['json_schema']) == {'name', 'schema', 'strict'}
        schema = response_format['json_schema']['schema']
        assert schema == baseline
        assert schema['type'] == 'object' and schema['additionalProperties'] is False
        section = schema['$defs']['CompactSection']
        assert set(section['required']) == {'title', 'time_weight', 'objective_indexes', 'slides', 'activities'}
        assert section['properties']['time_weight'] == {'minimum': 1, 'maximum': 1000, 'type': 'integer'}
        content = schema['$defs']['CompactSlide']['properties']['content']
        assert len(content['anyOf']) == 6 and 'discriminator' not in content
        def references(value):
            if isinstance(value, dict):
                if '$ref' in value:
                    assert value['$ref'].startswith('#/$defs/')
                    assert value['$ref'].removeprefix('#/$defs/') in schema['$defs']
                for child in value.values():
                    references(child)
            elif isinstance(value, list):
                for child in value:
                    references(child)
        references(schema)
        value = compact_lesson()
        value['sections'][1]['objective_indexes'] = [0, 1]
        value['sections'][-1]['activities'][0]['objective_indexes'] = [0, 1]
        return httpx.Response(200, json=completion(json.dumps(value)))
    request = request_for('lesson', material={
        'configuration': {'duration_minutes': 50, 'learning_objectives': ['Approved A.', 'Approved B.']},
        'authorized_evidence': {'allowed-evidence-a': 'Canonical A.', 'allowed-evidence-b': 'Canonical B.'}})
    asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request))


def test_preview_does_not_enable_lesson_strict_mode_or_prompt(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    def upstream(http):
        body = json.loads(http.content)
        assert 'strict' not in body['response_format']['json_schema']
        assert body['messages'][0]['content'] == request_for().system_instruction
        return httpx.Response(200, json=completion('{}'))
    asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for()))


def test_untrusted_finish_reason_is_never_logged(monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    value = completion(choices=[{'finish_reason': 'PRIVATE_TEACHER'}])
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    with pytest.raises(ProviderFailure):
        asyncio.run(provider.complete(request_for('lesson')))
    assert 'PRIVATE_TEACHER' not in caplog.text and event_from(caplog)['finish_reason'] == 'unknown'


def test_length_finish_is_truncated_before_attempting_to_decode_partial_content(monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    value = completion(choices=[{'finish_reason': 'length', 'message': {'content': '{"PRIVATE_TEACHER":'}}])
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    with pytest.raises(ProviderFailure) as caught:
        asyncio.run(provider.complete(request_for('lesson')))
    assert caught.value.reason == 'truncated'
    event = event_from(caplog)
    assert event['outcome'] == 'truncated' and event['finish_reason'] == 'length'
    assert 'json_target' not in event and 'PRIVATE_TEACHER' not in caplog.text
