"""The lesson-only smoke itself, with only hosted HTTP replaced."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from test_nvidia_compact_lesson import compact_lesson


def module():
    path = Path(__file__).resolve().parents[2] / 'scripts/smoke_studio_nvidia_lesson.py'
    spec = importlib.util.spec_from_file_location('lesson_smoke_test', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_isolated_smoke_prepares_simulated_preview_but_only_lesson_uses_nvidia(client, monkeypatch):
    smoke = module()
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-private-key')
    calls = []
    def upstream(http):
        body = json.loads(http.content)
        calls.append(body)
        assert body['model'] == 'nvidia/nemotron-3.5-super-vl-120b-a12b'
        assert body['response_format']['json_schema']['name'] == 'LessonDraft'
        assert body['response_format']['json_schema']['strict'] is True
        assert body['reasoning_effort'] == 'none'
        properties = body['response_format']['json_schema']['schema']['$defs']['CompactSection']['properties']
        assert 'time_weight' in properties and 'duration_minutes' not in properties
        material = json.loads(body['messages'][1]['content'])
        result = compact_lesson()
        result['sections'][1]['slides'][1].setdefault('evidence_ids', []).append(next(iter(material['authorized_evidence'])))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1400, 'completion_tokens': 1600},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(result)}}]})
    provider = smoke.SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    report = smoke.run_lesson_smoke(provider)
    assert report['status'] == 'passed' and provider.calls == len(calls) == 1
    assert report['lesson_contract'] == 'compact-v4-layouts'
    assert report['steps'][2]['approved_minutes'] == report['steps'][2]['section_minutes'] == report['steps'][2]['slide_minutes'] == 50
    assert report['preparation_simulated'] is True and report['full_flow_proven'] is False
    assert [s['stage'] for s in report['steps']] == ['preparation', 'review', 'lesson', 'read', 'replay', 'markdown']
    assert report['steps'][2]['json_validated'] is True
    assert report['steps'][4]['http_status'] == 200
    assert 'controlled-private-key' not in json.dumps(report)
    assert 'Explique cada etapa' not in json.dumps(report)


@pytest.mark.parametrize('failure', [503, 'invalid_schema', 'truncated', 'invalid_weight', 'legacy_minutes', 'invalid_json', 'duplicate_json'])
def test_isolated_smoke_never_pays_for_retry_or_correction(client, monkeypatch, failure):
    smoke = module()
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-private-key')
    calls = []
    def upstream(_):
        calls.append(1)
        if isinstance(failure, int):
            return httpx.Response(failure, text='private-key private-teacher-material')
        value = compact_lesson()
        if failure == 'invalid_weight':
            value['sections'][0]['time_weight'] = 0
        elif failure == 'legacy_minutes':
            for section in value['sections']:
                section['duration_minutes'] = section.pop('time_weight')
            value['sections'][0]['duration_minutes'] = 11
        else:
            value = {}
        content = ('{bad' if failure == 'invalid_json' else
                   '{"PRIVATE_SOURCE":1,"PRIVATE_SOURCE":2}' if failure == 'duplicate_json' else json.dumps(value))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100},
            'choices': [{'finish_reason': 'length' if failure == 'truncated' else 'stop', 'message': {'content': content}}]})
    provider = smoke.SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    report = smoke.run_lesson_smoke(provider)
    assert report['status'] == 'failed' and report['failed_stage'] == 'lesson'
    assert calls == [1] and provider.calls == 1
    if failure in ('invalid_weight', 'legacy_minutes', 'invalid_schema'):
        events = [event for event in report['events'] if event['type'] == 'nvidia_attempt']
        assert len(events) == 1 and events[0]['failure_code'] == 'lesson_schema_invalid'
    if failure in ('invalid_json', 'duplicate_json'):
        events = [event for event in report['events'] if event['type'] == 'nvidia_attempt']
        assert len(events) == 1 and events[0]['json_target'] == 'message_content'
        assert events[0]['failure_code'] == ('json_syntax_invalid' if failure == 'invalid_json' else 'json_duplicate_key')
        assert events[0]['content_bytes'] > 0 and events[0]['finish_reason'] == 'stop'
    assert 'PRIVATE_SOURCE' not in json.dumps(report)
    assert 'private-teacher-material' not in json.dumps(report)


def test_isolated_smoke_refuses_missing_cache_before_any_external_http(client, monkeypatch, tmp_path):
    from app.services import storage
    smoke = module()
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-private-key')
    original_client, calls = httpx.AsyncClient, []
    def upstream(_):
        calls.append(1)
        return httpx.Response(503)
    def controlled_client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(upstream)
        return original_client(*args, **kwargs)
    monkeypatch.setattr(httpx, 'AsyncClient', controlled_client)
    provider = smoke.SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    report = smoke.run_lesson_smoke(provider)
    assert report['status'] == 'failed' and report['code'] == 'preparation_cache_unavailable'
    assert provider.calls == 0 and calls == []


@pytest.mark.parametrize('fault,code', [('link', 'lesson_section_slide_link_invalid'), ('metadata', 'lesson_metadata_prompt_mismatch')])
def test_isolated_smoke_captures_post_provider_diagnostics_without_extra_http(client, monkeypatch, fault, code):
    smoke = module()
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    calls = []
    def upstream(http):
        calls.append(1)
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        value = compact_lesson()
        value['sections'][0]['slides'][0].setdefault('evidence_ids', []).append(next(iter(material['authorized_evidence'])))
        return httpx.Response(200, json={'model': 'controlled', 'usage': {'prompt_tokens': 900, 'completion_tokens': 1100},
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]})
    class PostProviderFault(smoke.SingleCallNVIDIA):
        async def complete(self, request):
            from app.studio.ports import ProviderResult
            result = await super().complete(request)
            value = json.loads(result.content)
            if fault == 'link':
                value['sections'][0]['slide_keys'] = ['PRIVATE_LINK']
            else:
                result.metadata.prompt_version = 'PRIVATE_VERSION'
            return ProviderResult(json.dumps(value).encode(), result.metadata)
    provider = PostProviderFault(transport=httpx.MockTransport(upstream))
    report = smoke.run_lesson_smoke(provider)
    assert report['status'] == 'failed' and report['code'] == 'invalid_generation'
    assert provider.calls == 1 and calls == [1]
    events = [event for event in report['events'] if event['type'] == 'studio_lesson_validation']
    assert events and events[0]['failure_code'] == code
    assert not any(private in json.dumps(report) for private in ('PRIVATE_LINK', 'PRIVATE_VERSION'))
