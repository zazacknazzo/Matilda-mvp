"""NVIDIA hosted Chat Completions boundary. No SDK retries or provider fallback."""
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import re
from time import monotonic

import httpx

from app.schemas.lesson import LessonGenerationMetadata
from app.services.studio.repository import conflict
from app.studio.ports import POLICY, ProviderFailure, ProviderResult

DEFAULT_MODEL = 'nvidia/nemotron-3.5-super-vl-120b-a12b'
DEFAULT_BASE_URL = 'https://integrate.api.nvidia.com/v1'
log = logging.getLogger('matilda.studio.nvidia')


def serialize(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


class NVIDIAProvider:
    def __init__(self, *, transport=None):
        self.transport = transport

    @property
    def model(self):
        return os.getenv('NVIDIA_MODEL', DEFAULT_MODEL)

    def _payload(self, request):
        return {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': request.system_instruction},
                {'role': 'user', 'content': serialize(request.material)},
            ],
            'temperature': 1, 'top_p': 0.95, 'stream': False,
            'reasoning_effort': 'none' if request.stage == 'preview' else 'low',
            'max_tokens': min(request.max_output_tokens, POLICY.max_output_tokens),
            'tool_choice': 'none',
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'PreviewPlan' if request.stage == 'preview' else 'LessonDraft',
                'schema': dict(request.response_schema),
            }},
        }

    async def count_input_tokens(self, request):
        if monotonic() >= request.deadline:
            raise ProviderFailure('timeout')
        # Byte ceiling, NOT chars/4: includes serialized material, schema, instructions,
        # role wrappers and configuration. Reserve covers hidden chat-template tokens.
        return len(serialize(self._payload(request)).encode('utf-8')) + 1024

    async def complete(self, request):
        started = monotonic()
        event = {'stage': request.stage, 'http_status': None, 'outcome': 'unavailable'}
        try:
            # Includes queue/network/body parsing; a second attempt never resets this.
            if monotonic() >= request.deadline:
                raise ProviderFailure('timeout')
            estimate = await self.count_input_tokens(request)
            event['estimated_input_tokens'] = estimate
            if estimate > min(request.max_input_tokens, POLICY.max_input_tokens):
                event['outcome'] = 'input_too_large'
                raise conflict('input_too_large', 'Entrada excede o limite seguro de tokens.')
            key = os.getenv('NVIDIA_API_KEY', '').strip()
            if not key:
                event['outcome'] = 'not_configured'
                raise conflict('studio_not_configured', 'Studio requer NVIDIA_API_KEY no backend. O material foi preservado.')
            try:
                base = httpx.URL(os.getenv('NVIDIA_BASE_URL', DEFAULT_BASE_URL))
            except httpx.InvalidURL:
                event['outcome'] = 'not_configured'
                raise conflict('studio_not_configured', 'NVIDIA_BASE_URL inválida no backend.') from None
            if base.scheme != 'https' or not base.host or base.userinfo or base.query or base.fragment:
                event['outcome'] = 'not_configured'
                raise conflict('studio_not_configured', 'NVIDIA_BASE_URL exige HTTPS sem credenciais, query ou fragmento.')
            async with asyncio.timeout(max(0, request.deadline - monotonic())):
                async with httpx.AsyncClient(transport=self.transport, timeout=max(.001, request.deadline - monotonic()),
                                            follow_redirects=False, trust_env=False,
                                            limits=httpx.Limits(max_connections=POLICY.global_concurrency)) as client:
                    async with client.stream('POST', str(base).rstrip('/') + '/chat/completions',
                            json=self._payload(request), headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}) as response:
                        event['http_status'] = response.status_code
                        self._check_status(response.status_code, event)
                        body = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=4096):
                            if len(body) + len(chunk) > POLICY.max_body_bytes:
                                self._invalid('response_too_large', event)
                            body.extend(chunk)
                    result = self._parse(bytes(body), request, started, event)
            event['outcome'] = 'completed'
            return result
        except (httpx.TimeoutException, TimeoutError):
            event['outcome'] = 'timeout'
            raise ProviderFailure('timeout') from None
        except httpx.HTTPError:
            event['outcome'] = 'unavailable'
            raise ProviderFailure('unavailable') from None
        except ProviderFailure as failure:
            # Empty content has the existing truncated port reason, distinct telemetry.
            if event['outcome'] == 'unavailable':
                event['outcome'] = failure.reason
            raise
        finally:
            event['duration_ms'] = int((monotonic() - started) * 1000)
            log.info('nvidia_attempt %s', serialize(event))

    @staticmethod
    def _check_status(status, event):
        if status == 200:
            return
        if status in (401, 403):
            raise ProviderFailure('unauthorized')
        if status == 429:
            raise ProviderFailure('rate_limited')
        if status == 202:
            # Already accepted upstream. Retrying POST could create paid duplicate work.
            event['outcome'] = 'pending_response'
            raise conflict('invalid_generation', 'A NVIDIA aceitou a operação, mas o resultado está pendente. Não foi iniciada outra inferência.', retryable=False)
        if status >= 500:
            raise ProviderFailure('unavailable')
        event['outcome'] = 'invalid_request'
        raise conflict('invalid_generation', 'A requisição ou o JSON Schema não foi aceito pela NVIDIA.', retryable=False)

    @staticmethod
    def _invalid(reason, event):
        event['outcome'] = reason
        raise ValueError(reason) from None

    def _parse(self, body, request, started, event):
        try:
            value = json.loads(body, object_pairs_hook=unique_keys,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(value, dict):
                raise ValueError()
            # Preserve usage on failed/truncated completions when NVIDIA supplies it.
            reported_usage = value.get('usage')
            if isinstance(reported_usage, dict):
                for upstream, metric in (('prompt_tokens', 'actual_input_tokens'), ('completion_tokens', 'output_tokens')):
                    count = reported_usage.get(upstream)
                    if type(count) is int and count >= 0:
                        event[metric] = count
                if 'actual_input_tokens' in event:
                    event['input_token_delta'] = event['actual_input_tokens'] - event['estimated_input_tokens']
            choices = value.get('choices')
            if not choices:
                event['outcome'] = 'empty_content'
                raise ProviderFailure('truncated')
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError()
            choice = choices[0]
            finish = choice.get('finish_reason')
            if finish != 'stop':
                raise ProviderFailure('blocked' if finish == 'content_filter' else 'truncated')
            message = choice['message']
            if message.get('tool_calls') or message.get('function_call') or message.get('refusal'):
                raise ProviderFailure('blocked')
            content = message.get('content')
            if content is None or isinstance(content, str) and not content.strip():
                event['outcome'] = 'empty_content'
                raise ProviderFailure('truncated')
            if not isinstance(content, str):
                raise ValueError()
            model, usage = value['model'], value['usage']
            if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9/_.:-]{1,200}', model):
                raise ValueError()
            input_tokens, output_tokens = usage['prompt_tokens'], usage['completion_tokens']
            if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError):
            self._invalid('invalid_response', event)
        event.update(model=model, actual_input_tokens=input_tokens, output_tokens=output_tokens,
                     input_token_delta=input_tokens-event['estimated_input_tokens'])
        if input_tokens > min(request.max_input_tokens, POLICY.max_input_tokens):
            event['outcome'] = 'input_too_large'
            raise conflict('input_too_large', 'O uso informado pela NVIDIA excede o limite seguro de entrada.')
        if output_tokens > min(request.max_output_tokens, POLICY.max_output_tokens):
            raise ProviderFailure('truncated')
        try:
            payload = json.loads(content, object_pairs_hook=unique_keys,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(payload, dict):
                raise ValueError()
            encoded = content.encode('utf-8')
        except (ValueError, TypeError, RecursionError):
            self._invalid('invalid_json', event)
        return ProviderResult(encoded, LessonGenerationMetadata(
            provider='nvidia', model=model, prompt_version=request.prompt_version, schema_version=1,
            generated_at=datetime.now(timezone.utc).isoformat(), duration_ms=int((monotonic()-started)*1000),
            input_tokens=input_tokens, output_tokens=output_tokens,
        ))


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key.')
        result[key] = value
    return result
