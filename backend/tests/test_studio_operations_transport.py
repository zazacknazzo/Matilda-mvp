"""Real SDK + generation/SQLite; Google HTTP transport alone is controlled.

These tests never contact Google and do not prove live model/quota availability.
"""
import json

import httpx
import pytest

from app.integrations.gemini_client import GeminiProvider
from app.services.studio.generation import GenerationService
from generation_fixtures import authority, request_for, setup
from test_studio_generation import http_client


@pytest.mark.parametrize('case,status,code,attempts,retryable', [
    (401, 503, 'provider_unavailable', 1, False),
    (403, 503, 'provider_unavailable', 1, False),
    (429, 503, 'provider_unavailable', 2, True),
    ('blocked', 503, 'provider_unavailable', 1, False),
    ('invalid', 502, 'invalid_generation', 2, True),
    ('incomplete', 502, 'invalid_generation', 1, True),
    ('timeout', 504, 'generation_timeout', 1, True),
    ('disconnect', 503, 'provider_unavailable', 2, True),
])
def test_transport_failures_preserve_review_without_fake_content_or_secret(
    tmp_path, monkeypatch, caplog, case, status, code, attempts, retryable,
):
    calls = []
    def upstream(request):
        if request.url.path.endswith(':countTokens'):
            return httpx.Response(200, json={'totalTokens': 600})
        calls.append(json.loads(request.content))
        if isinstance(case, int):
            return httpx.Response(case, json={'error': {'code': case, 'message': 'RAW_SECRET TEACHER_MATERIAL'}})
        if case == 'timeout':
            raise httpx.ReadTimeout('RAW_SECRET TEACHER_MATERIAL')
        if case == 'disconnect':
            raise httpx.ConnectError('RAW_SECRET TEACHER_MATERIAL')
        if case == 'blocked':
            return httpx.Response(200, json={'promptFeedback': {'blockReason': 'SAFETY'}})
        return httpx.Response(200, json={'candidates': [{
            'content': {'role': 'model', 'parts': [{'text': '{RAW_SECRET TEACHER_MATERIAL'}]},
            'finishReason': 'MAX_TOKENS' if case == 'incomplete' else 'STOP',
        }]})

    _, repo, _, value, clock = setup(tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY', 'RAW_SECRET')
    service = GenerationService(repo, GeminiProvider(transport=httpx.MockTransport(upstream)),
                                lambda _: authority(), now=clock.now)
    client, renewals = http_client(service)
    with client:
        client.cookies.set('test_owner', 'owner')
        response = client.post('/api/studio/generate', json=request_for(value).model_dump(),
                               headers={'Origin': 'http://testserver', 'Idempotency-Key': 'stable'})
    assert response.status_code == status
    assert response.json()['code'] == code and response.json()['retryable'] is retryable
    assert len(calls) == attempts
    assert all(not call.get('tools') for call in calls)
    assert all(call['generationConfig']['maxOutputTokens'] == 8000 for call in calls)
    observed = response.text + caplog.text + str(service.metrics.snapshot())
    assert 'RAW_SECRET' not in observed and 'TEACHER_MATERIAL' not in observed
    assert 'lesson_bundle_id' not in response.json()
    import asyncio
    saved = asyncio.run(repo.get_preview(session_id='owner', preview_id=value.preview_id, now=clock.now()))
    assert saved.suggestions == value.suggestions and saved.approved_objectives == value.approved_objectives
    assert saved.source_documents == value.source_documents and saved.last_lesson_bundle_id is None
    assert saved.generation_status == 'failed'
    assert len(renewals) == 1
