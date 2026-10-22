"""Official Gemini SDK boundary, loaded lazily so Forensics needs no AI config."""
import json
import os
from datetime import datetime, timezone
from time import monotonic

import httpx

from app.schemas.lesson import LessonGenerationMetadata
from app.services.studio.repository import conflict
from app.studio.ports import ProviderFailure, ProviderResult


class GeminiProvider:
    def __init__(self, *, transport=None):
        self.transport = transport

    def _client(self, request):
        key = os.getenv('GEMINI_API_KEY', '').strip()
        if not key:
            raise conflict('studio_not_configured', 'Studio requer GEMINI_API_KEY no backend. O material foi preservado.')
        from google import genai
        from google.genai import types
        remaining = request.deadline - monotonic()
        if remaining <= 0:
            raise ProviderFailure('timeout')
        return genai.Client(api_key=key, http_options=types.HttpOptions(
            async_client_args={'transport': self.transport} if self.transport else None,
            timeout=max(1, int(remaining * 1000)), retry_options=types.HttpRetryOptions(attempts=1),
        )).aio

    @property
    def model(self):
        return os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')

    async def count_input_tokens(self, request):
        try:
            async with self._client(request) as client:
                # Include instruction + serialized schema, not only teacher material.
                result = await client.models.count_tokens(model=self.model, contents=[request.system_instruction, json.dumps(request.material, ensure_ascii=False), json.dumps(request.response_schema)])
                if result.total_tokens is None:
                    raise ProviderFailure('unavailable')
                return result.total_tokens
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderFailure('timeout') from None
        except Exception as exc:
            self._raise_safe(exc)

    async def complete(self, request):
        from google.genai import types
        started = monotonic()
        try:
            async with self._client(request) as client:
                response = await client.models.generate_content(
                    model=self.model, contents=json.dumps(request.material, ensure_ascii=False),
                    config=types.GenerateContentConfig(system_instruction=request.system_instruction,
                        response_mime_type='application/json', response_json_schema=dict(request.response_schema),
                        max_output_tokens=request.max_output_tokens, tools=[],
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)),
                )
            if not response.candidates:
                raise ProviderFailure('blocked')
            candidate = response.candidates[0]
            if candidate.finish_reason != types.FinishReason.STOP:
                raise ProviderFailure('truncated' if candidate.finish_reason == types.FinishReason.MAX_TOKENS else 'blocked')
            content = response.text
            if not content:
                raise ProviderFailure('truncated')
            usage = response.usage_metadata
            return ProviderResult(content.encode('utf-8'), LessonGenerationMetadata(
                provider='gemini', model=response.model_version or self.model, prompt_version=request.prompt_version,
                schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(), duration_ms=int((monotonic()-started)*1000),
                input_tokens=usage.prompt_token_count if usage else None,
                output_tokens=(usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else None,
            ))
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderFailure('timeout') from None
        except Exception as exc:
            self._raise_safe(exc)

    def _raise_safe(self, exc):
        from google.genai.errors import APIError
        from app.studio.ports import RepositoryConflict
        if isinstance(exc, (ProviderFailure, RepositoryConflict)):
            raise exc
        code = exc.code if isinstance(exc, APIError) else None
        raise ProviderFailure('unauthorized' if code in (401, 403) else 'rate_limited' if code == 429 else 'unavailable') from None
