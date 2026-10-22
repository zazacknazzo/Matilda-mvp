"""Deadline through HTTP API, NVIDIA HTTPX transport, validators and real SQLite."""
import asyncio
from dataclasses import replace
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from studio_flow_provider import FlowProvider
from test_studio_flow import create, generate, review


@pytest.mark.parametrize('phase', ['waiting_headers', 'reading_body'])
def test_outer_lesson_deadline_records_phase_and_preserves_review(client, monkeypatch, caplog, phase):
    import app.services.studio.generation as generation
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-private-key')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    # Time is an allowed seam: preserve the 75-minus-reserve relationship, scaled down.
    original_policy = generation.POLICY
    monkeypatch.setattr(generation, 'POLICY', replace(generation.POLICY,
        generation_backend_seconds=.08, persistence_reserve_seconds=.02))
    calls = []
    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"choices":['
            await asyncio.sleep(5)
            yield b']}'
    async def upstream(_):
        calls.append(1)
        if phase == 'reading_body':
            return httpx.Response(200, stream=SlowBody())
        await asyncio.sleep(5)
        return httpx.Response(200)
    app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
    try:
        response = generate(client, saved)
        assert response.status_code == 504 and response.json()['code'] == 'generation_timeout'
        assert len(calls) == 1
        events = [json.loads(r.message.removeprefix('nvidia_attempt ')) for r in caplog.records
                  if r.message.startswith('nvidia_attempt ')]
        assert len(events) == 1 and events[0]['http_status'] == (200 if phase == 'reading_body' else None)
        assert events[0]['outcome'] == 'timeout'
        assert events[0]['failure_phase'] == phase
        assert (events[0]['first_body_ms'] is not None) == (phase == 'reading_body')
        assert events[0]['failure_reason'] == 'deadline_exceeded'
        resumed = client.get('/api/studio/previews/' + saved['preview_id']).json()
        assert resumed['suggestions'] == saved['suggestions']
        assert resumed['approved_objectives'] == saved['approved_objectives']
        assert resumed['generation_status'] == 'failed' and resumed['last_lesson_bundle_id'] is None
        assert 'controlled-private-key' not in caplog.text
        monkeypatch.setattr(generation, 'POLICY', original_policy)
        from nvidia_transport import controlled_nvidia
        recovery_provider = FlowProvider()
        app.dependency_overrides[get_provider] = lambda: controlled_nvidia(recovery_provider)
        recovered = generate(client, saved)
        assert recovered.status_code == 201
        assert generate(client, saved).json() == recovered.json()
        assert len(recovery_provider.lesson_requests) == 1
    finally:
        app.dependency_overrides.clear()


def test_caller_cancellation_is_never_logged_as_provider_unavailability(monkeypatch, caplog):
    from time import monotonic
    from test_nvidia_provider import request_for
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-private-key')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    async def upstream(_):
        await asyncio.sleep(5)
        return httpx.Response(200)
    async def run():
        provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
        try:
            await asyncio.wait_for(provider.complete(request_for(deadline=monotonic() + 5)), timeout=.02)
        except TimeoutError:
            pass
        else:
            raise AssertionError('Controlled transport must be cancelled.')
    asyncio.run(run())
    event = next(json.loads(r.message.removeprefix('nvidia_attempt ')) for r in caplog.records if r.message.startswith('nvidia_attempt '))
    assert event['outcome'] == 'cancelled'
    assert event['failure_reason'] == 'caller_cancelled' and event['failure_phase'] == 'waiting_headers'
