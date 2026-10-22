"""StudioProvider seam: real NVIDIA adapter, only external HTTP is simulated."""
import asyncio
import json
from time import monotonic

import httpx
import pytest

from app.studio.ports import ProviderRequest


def request_for(stage='preview', **changes):
    from app.services.studio.preview import PreviewPlan
    from app.services.studio.lesson_validator import LessonDraft
    return ProviderRequest(**{
        'stage': stage, 'system_instruction': 'Retorne somente JSON em português brasileiro.',
        'material': {'text': 'RNA mensageiro'},
        'response_schema': (PreviewPlan if stage == 'preview' else LessonDraft).model_json_schema(),
        'deadline': monotonic() + 2, 'prompt_version': 'test-v1', **changes,
    })


def completion(content='{}', **changes):
    return {'model': 'nvidia/nemotron-3.5-super-vl-120b-a12b',
            'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': content}}],
            'usage': {'prompt_tokens': 900, 'completion_tokens': 1100}, **changes}


@pytest.mark.parametrize('stage,effort', [('preview', 'none'), ('lesson', 'low')])
def test_structured_completion_uses_full_schema_and_actual_usage(monkeypatch, stage, effort):
    from app.integrations.nvidia_client import NVIDIAProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-private-key')
    seen = []
    req = request_for(stage)

    def upstream(http):
        assert str(http.url) == 'https://integrate.api.nvidia.com/v1/chat/completions'
        assert http.headers['authorization'] == 'Bearer test-private-key'
        body = json.loads(http.content)
        seen.append(body)
        assert body['reasoning_effort'] == effort
        assert body['stream'] is False
        assert body['temperature'] == 1 and body['top_p'] == 0.95
        assert body['max_tokens'] == 8000
        assert body['response_format'] == {'type': 'json_schema', 'json_schema': {
            'name': 'PreviewPlan' if stage == 'preview' else 'LessonDraft', 'schema': req.response_schema}}
        assert not body.get('tools') and body['tool_choice'] == 'none'
        assert body['messages'][0]['role'] == 'system'
        assert json.loads(body['messages'][1]['content']) == req.material
        return httpx.Response(200, json=completion())

    async def run():
        provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
        estimate = await provider.count_input_tokens(req)
        assert 1000 < estimate < 12000 and seen == []
        result = await provider.complete(req)
        assert result.content == b'{}'
        assert result.metadata.provider == 'nvidia'
        assert result.metadata.input_tokens == 900 and result.metadata.output_tokens == 1100
        assert result.metadata.prompt_version == 'test-v1'
        assert result.metadata.duration_ms >= 0
        assert result.metadata.model == 'nvidia/nemotron-3.5-super-vl-120b-a12b'
    asyncio.run(run())


@pytest.mark.parametrize('status,reason,code', [
    (400, None, 'invalid_generation'), (422, None, 'invalid_generation'),
    (401, 'unauthorized', None), (403, 'unauthorized', None),
    (429, 'rate_limited', None), (500, 'unavailable', None), (503, 'unavailable', None),
    (302, None, 'invalid_generation'), (202, None, 'invalid_generation'),
])
def test_http_failures_are_classified_and_never_expose_upstream(monkeypatch, caplog, status, reason, code):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import ProviderFailure, RepositoryConflict
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_KEY')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(status, text='PRIVATE_KEY PRIVATE_MATERIAL')))
    with pytest.raises(RepositoryConflict if code else ProviderFailure) as caught:
        asyncio.run(provider.complete(request_for()))
    if code:
        assert caught.value.error.code == code and caught.value.error.retryable is False
    else:
        assert caught.value.reason == reason
    assert 'PRIVATE_KEY' not in str(caught.value) + caplog.text
    assert 'PRIVATE_MATERIAL' not in str(caught.value) + caplog.text
    assert f'"http_status":{status}' in caplog.text


@pytest.mark.parametrize('value,reason', [
    (completion(choices=[]), 'empty_content'),
    (completion(choices=[{'finish_reason': 'length', 'message': {'content': '{}'}}]), 'truncated'),
    (completion(choices=[{'finish_reason': 'content_filter', 'message': {'content': '{}'}}]), 'blocked'),
    (completion(choices=[{'finish_reason': None, 'message': {'content': '{}'}}]), 'truncated'),
    (completion('  '), 'empty_content'),
    (completion('{bad'), 'invalid_json'),
    (completion('{"a":1,"a":2}'), 'invalid_json'),
    (completion('{"a":NaN}'), 'invalid_json'),
    (completion('[]'), 'invalid_json'),
    (completion(usage={'prompt_tokens': 12001, 'completion_tokens': 1}), 'input_too_large'),
    (completion(usage={'prompt_tokens': 100, 'completion_tokens': 8001}), 'truncated'),
    (completion(usage={'prompt_tokens': True, 'completion_tokens': 1}), 'invalid_response'),
    (completion(usage=None), 'invalid_response'),
    (completion(model=None), 'invalid_response'),
    (completion(choices=[{'finish_reason': 'stop', 'message': {'content': '{}', 'tool_calls': [{'id': 'x'}]}}]), 'blocked'),
])
def test_incomplete_or_invalid_responses_are_failures(monkeypatch, caplog, value, reason):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import ProviderFailure, RepositoryConflict
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-key')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    with pytest.raises((ProviderFailure, RepositoryConflict, ValueError)):
        asyncio.run(provider.complete(request_for()))
    assert f'"outcome":"{reason}"' in caplog.text


def test_token_estimate_accounts_for_every_byte_including_unicode_and_schema_without_network(monkeypatch):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import RepositoryConflict
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-key')
    def forbidden(_):
        pytest.fail('Input above safety ceiling must never reach NVIDIA')
    provider = NVIDIAProvider(transport=httpx.MockTransport(forbidden))
    async def run():
        original = await provider.count_input_tokens(request_for())
        assert await provider.count_input_tokens(request_for(system_instruction='x' * 12001)) > 12000
        assert await provider.count_input_tokens(request_for(response_schema={'description': 'x' * 12001})) > 12000
        large = request_for(material={'text': '🧬' * 3001})
        assert await provider.count_input_tokens(large) > 12000
        assert await provider.count_input_tokens(request_for(system_instruction='a')) < original
        with pytest.raises(RepositoryConflict) as caught:
            await provider.complete(large)
        assert caught.value.error.code == 'input_too_large'
    asyncio.run(run())


def test_absolute_deadline_covers_slow_body_and_reused_request(monkeypatch):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import ProviderFailure
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-key')
    class Slow(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(.08)
            yield b'{}'
    calls = []
    def upstream(_):
        calls.append(1)
        return httpx.Response(200, stream=Slow())
    async def run():
        req = request_for(deadline=monotonic() + .02)
        provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
        for _ in range(2):
            with pytest.raises(ProviderFailure) as caught:
                await provider.complete(req)
            assert caught.value.reason == 'timeout'
        assert len(calls) == 1
    asyncio.run(run())


def test_response_bytes_are_bounded_before_json_parsing(monkeypatch, caplog):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import POLICY
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-key')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    consumed = []
    class Oversized(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(1000):
                consumed.append(1)
                yield b'x' * 4096
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=Oversized())))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for()))
    assert len(consumed) <= POLICY.max_body_bytes // 4096 + 1
    assert 'response_too_large' in caplog.text


@pytest.mark.parametrize('error,reason', [(httpx.ReadTimeout('PRIVATE'), 'timeout'), (httpx.ConnectError('PRIVATE'), 'unavailable')])
def test_network_errors_are_sanitized(monkeypatch, error, reason):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import ProviderFailure
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-key')
    def upstream(_):
        raise error
    with pytest.raises(ProviderFailure) as caught:
        asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for()))
    assert caught.value.reason == reason and 'PRIVATE' not in str(caught.value)


def test_provider_selection_defaults_to_nvidia_and_requires_explicit_gemini(monkeypatch):
    from app.api.studio_preview import get_provider
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.integrations.gemini_client import GeminiProvider
    from app.studio.ports import RepositoryConflict
    monkeypatch.delenv('AI_PROVIDER', raising=False)
    assert isinstance(get_provider(), NVIDIAProvider)
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    assert isinstance(get_provider(), GeminiProvider)
    monkeypatch.setenv('AI_PROVIDER', 'typo')
    with pytest.raises(RepositoryConflict) as caught:
        asyncio.run(get_provider().count_input_tokens(request_for()))
    assert caught.value.error.code == 'studio_not_configured'


def test_missing_nvidia_key_never_uses_available_gemini_key(monkeypatch):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import RepositoryConflict
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'must-not-be-used')
    def forbidden(_):
        pytest.fail('Unconfigured NVIDIA must never invoke any upstream')
    with pytest.raises(RepositoryConflict) as caught:
        asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(forbidden)).complete(request_for()))
    assert caught.value.error.code == 'studio_not_configured'


@pytest.mark.parametrize('url', ['http://integrate.api.nvidia.com/v1', 'https://key:secret@integrate.api.nvidia.com/v1', 'https://integrate.api.nvidia.com/v1?key=secret'])
def test_unsafe_base_url_fails_without_sending_material(monkeypatch, url):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import RepositoryConflict
    monkeypatch.setenv('NVIDIA_API_KEY', 'key')
    monkeypatch.setenv('NVIDIA_BASE_URL', url)
    def forbidden(_):
        pytest.fail('Unsafe endpoint must never be contacted')
    with pytest.raises(RepositoryConflict) as caught:
        asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(forbidden)).complete(request_for()))
    assert caught.value.error.code == 'studio_not_configured'


def test_explicit_model_and_output_budget_are_honored(monkeypatch):
    from app.integrations.nvidia_client import NVIDIAProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'key')
    monkeypatch.setenv('NVIDIA_MODEL', 'nvidia/configured-version')
    monkeypatch.setenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1/')
    def upstream(http):
        body = json.loads(http.content)
        assert body['model'] == 'nvidia/configured-version' and body['max_tokens'] == 1200
        return httpx.Response(200, json=completion(model='nvidia/actual-version'))
    result = asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for(max_output_tokens=1200)))
    assert result.metadata.model == 'nvidia/actual-version'
