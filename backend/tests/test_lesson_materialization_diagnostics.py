"""Materialization failures over the hosted HTTP seam and persisted Studio API."""
import json

import httpx

from app.api.studio_preview import get_provider
from app.main import app
from scripts.smoke_studio_nvidia import Recorder
from studio_flow_provider import FlowProvider
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_lesson_smoke import module as smoke_module
from test_nvidia_provider import completion
from test_studio_flow import create, generate, review


def test_unauthorized_evidence_has_specific_safe_diagnostic_and_preserves_review(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    calls = []
    def upstream(_):
        calls.append(1)
        value = compact_lesson()
        value['sections'][0]['slides'][0].setdefault('evidence_ids', []).append('PRIVATE_EVIDENCE_ID')
        return httpx.Response(200, json=completion(json.dumps(value)))
    provider = smoke_module().SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        response = generate(client, saved)
        assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
        assert calls == [1]
        current = client.get('/api/studio/previews/' + saved['preview_id']).json()
        for key in ('suggestions', 'approved_objectives', 'review_revision', 'source_documents'):
            assert current[key] == saved[key]
        assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'failed'
        recorder = Recorder()
        for record in caplog.records:
            recorder.emit(record)
        assert not any(secret in caplog.text + response.text for secret in ('PRIVATE_CREDENTIAL', 'PRIVATE_EVIDENCE_ID'))
        assert any(event.get('failure_code') == 'lesson_evidence_not_authorized' for event in recorder.events)
    finally:
        app.dependency_overrides.clear()


def test_missing_slide_link_has_specific_diagnostic_after_completed_nvidia(client, monkeypatch, caplog):
    from app.integrations.nvidia_client import NVIDIAProvider
    from app.studio.ports import ProviderResult
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    inner = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(compact_lesson())))))
    class BrokenExpansion:
        async def count_input_tokens(self, request):
            return await inner.count_input_tokens(request)
        async def complete(self, request):
            result = await inner.complete(request)
            value = json.loads(result.content)
            value['sections'][0]['slide_keys'] = ['PRIVATE_UNKNOWN_KEY']
            return ProviderResult(json.dumps(value).encode(), result.metadata)
    app.dependency_overrides[get_provider] = lambda: BrokenExpansion()
    try:
        response = generate(client, saved)
        assert response.status_code == 502
        assert 'PRIVATE_UNKNOWN_KEY' not in caplog.text + response.text
        assert 'lesson_section_slide_link_invalid' in caplog.text
    finally:
        app.dependency_overrides.clear()


def test_metadata_prompt_mismatch_is_diagnosed_after_completed_nvidia(client, monkeypatch, caplog):
    from app.integrations.nvidia_client import NVIDIAProvider
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    inner = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(compact_lesson())))))
    class BrokenMetadata:
        async def count_input_tokens(self, request):
            return await inner.count_input_tokens(request)
        async def complete(self, request):
            result = await inner.complete(request)
            result.metadata.prompt_version = 'PRIVATE_VERSION'
            return result
    app.dependency_overrides[get_provider] = lambda: BrokenMetadata()
    try:
        response = generate(client, saved)
        assert response.status_code == 502
        assert 'PRIVATE_VERSION' not in caplog.text + response.text
        assert 'lesson_metadata_prompt_mismatch' in caplog.text
    finally:
        app.dependency_overrides.clear()
