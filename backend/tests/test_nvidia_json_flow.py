"""Malformed hosted outputs never publish a lesson or alter the saved review."""
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.main import app
from app.schemas.lesson import LessonBundle
from studio_flow_provider import FlowProvider
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_lesson_smoke import module as smoke_module
from test_nvidia_provider import completion
from test_studio_flow import create, generate, review


@pytest.mark.parametrize('fault,code', [
    ('valid', None), ('trailing_comma', 'json_syntax_invalid'),
    ('unclosed_quote', 'json_syntax_invalid'), ('duplicate_key', 'json_duplicate_key'),
    ('root_array', 'json_root_not_object'), ('markdown', 'json_syntax_invalid'),
    ('interrupted', 'json_syntax_invalid'), ('nan', 'json_nonfinite_constant'),
    ('infinity', 'json_nonfinite_constant'), ('undefined', 'json_syntax_invalid'),
    ('wrong_schema', 'lesson_schema_invalid'),
])
def test_json_categories_preserve_review_and_only_valid_content_is_persisted(client, monkeypatch, caplog, fault, code):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    calls = []
    note = 'Discuta "DNA", RNA e limitações.\nTexto literal: {NaN}, ``` e átomos. Peça que os alunos fundamentem cada resposta no mecanismo descrito.'
    def upstream(http):
        calls.append(1)
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        value = compact_lesson()
        value['sections'][0]['slides'][0]['speaker_notes'] = note
        value['sections'][1]['slides'][1].setdefault('evidence_ids', []).append(next(iter(material['authorized_evidence'])))
        if fault == 'wrong_schema':
            value['sections'][0]['time_weight'] = 'PRIVATE_TEACHER'
        content = json.dumps(value, ensure_ascii=False)
        if fault == 'trailing_comma':
            content = content[:-1] + ',}'
        elif fault == 'unclosed_quote':
            content = '{"text":"PRIVATE_TEACHER}'
        elif fault == 'duplicate_key':
            content = '{"PRIVATE_SOURCE":1,"PRIVATE_SOURCE":2}'
        elif fault == 'root_array':
            content = '[' + content + ']'
        elif fault == 'markdown':
            content = '```json\n' + content + '\n```'
        elif fault == 'interrupted':
            content = content[:-1]
        elif fault == 'nan':
            content = '{"n":NaN}'
        elif fault == 'infinity':
            content = '{"n":Infinity}'
        elif fault == 'undefined':
            content = '{"n":undefined}'
        return httpx.Response(200, json=completion(content))
    provider = smoke_module().SingleCallNVIDIA(transport=httpx.MockTransport(upstream))
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        response = generate(client, saved)
        resumed = client.get('/api/studio/previews/' + saved['preview_id']).json()
        for key in ('suggestions', 'approved_objectives', 'review_revision', 'source_documents'):
            assert resumed[key] == saved[key]
        for key in ('id', 'title', 'subject', 'education_level', 'duration_minutes'):
            assert resumed['project'][key] == saved['project'][key]
        assert calls == [1] and provider.calls == 1
        event = next(json.loads(record.message.removeprefix('nvidia_attempt ')) for record in caplog.records
                     if record.message.startswith('nvidia_attempt '))
        if code:
            assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
            assert resumed['last_lesson_bundle_id'] is None and resumed['generation_status'] == 'failed'
            assert event['failure_code'] == code and event['phase'] == 'validation'
            assert event['outcome'] == ('pydantic_validation' if fault == 'wrong_schema' else 'invalid_json')
        else:
            assert response.status_code == 201, response.text
            bundle = LessonBundle.model_validate(response.json())
            assert bundle.metadata.duration_minutes == sum(s.duration_minutes for s in bundle.sections) == 50
            assert sum(s.duration_minutes for s in bundle.slides) == 50
            assert bundle.slides[0].speaker_notes == note
            assert bundle.references and all(s.duration_minutes >= 1 for s in bundle.slides)
            assert resumed['last_lesson_bundle_id'] == bundle.lesson_bundle_id
            path = '/api/studio/lessons/' + bundle.lesson_bundle_id
            assert client.get(path).json() == response.json()
            assert generate(client, saved).json() == response.json()
            assert client.get(path + '/export?format=markdown').status_code == 200
            assert calls == [1] and provider.calls == 1
        assert not any(secret in caplog.text + response.text for secret in
                       ('PRIVATE_CREDENTIAL', 'PRIVATE_TEACHER', 'PRIVATE_SOURCE'))
    finally:
        app.dependency_overrides.clear()
