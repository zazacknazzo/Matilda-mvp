"""T11 isolated serializer/router tests. No production session/DB claims."""
from datetime import datetime
from pathlib import Path
import copy
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.studio_exports import create_export_router
from app.schemas.lesson import LessonBundle
from app.services.studio.lesson_export import export_filename, lesson_markdown, markdown_text


FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/lessons'


def fixture(name='crispr-50') -> LessonBundle:
    return LessonBundle.model_validate_json((FIXTURES / f'{name}.json').read_bytes())


@pytest.mark.parametrize('name', ['crispr-50', 'rna-50', 'no-enrichment-50', 'optional-fields'])
def test_same_lesson_has_objectives_timing_slides_notes_activities_and_sources(name):
    bundle = fixture(name)
    original = copy.deepcopy(bundle.model_dump())
    output = lesson_markdown(bundle)
    assert output == lesson_markdown(bundle)
    assert bundle.model_dump() == original
    assert markdown_text(bundle.metadata.title) in output
    assert f'{bundle.metadata.duration_minutes} minutos' in output
    for objective in bundle.metadata.learning_objectives:
        assert markdown_text(objective) in output
    elapsed = 0
    for section in bundle.sections:
        assert f'{elapsed}–{elapsed + section.duration_minutes} min' in output
        elapsed += section.duration_minutes
    assert elapsed == bundle.metadata.duration_minutes
    for slide in bundle.slides:
        assert markdown_text(slide.title) in output
        if slide.speaker_notes:
            assert markdown_text(slide.speaker_notes) in output
    for activity in bundle.activities:
        assert markdown_text(activity.prompt) in output
        assert markdown_text(activity.teacher_guidance) in output
        for criterion in activity.assessment_criteria:
            assert markdown_text(criterion) in output
    for reference in bundle.references:
        assert markdown_text(reference.claim_supported) in output
        assert reference.source_url in output
        for person in reference.participants:
            assert markdown_text(person) in output
        for limitation in reference.limitations:
            assert markdown_text(limitation) in output
    for limitation in bundle.limitations:
        assert markdown_text(limitation) in output
    assert 'source_documents' not in output
    assert 'material_text' not in output


def test_empty_enrichments_invent_no_sources():
    output = lesson_markdown(fixture('no-enrichment-50'))
    assert 'Sem enriquecimentos científicos aprovados' in output
    assert 'https://' not in output


def test_markdown_and_html_injections_are_plain_text_and_urls_are_delimited():
    bundle = fixture()
    bundle.metadata.title = '<script>alert(1)</script> [hack](javascript:alert(1))'
    bundle.slides[0].speaker_notes = 'Notas\n# título injetado\n<img src=x> `código`'
    bundle.references[0].source_url = 'https://example.com/source_(1)?a=1&b=2'
    output = lesson_markdown(bundle)
    assert '<script>' not in output and '<img' not in output
    assert '&lt;script&gt;' in output
    assert '\\[hack\\]\\(javascript:' in output
    assert '\n# título injetado' not in output
    assert '(<https://example.com/source_%281%29?a=1&b=2>)' in output
    assert '\\`código\\`' in output


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'data:text/html,x', '//evil.test', 'https://user:secret@example.com', 'https://example.com/\x00x'])
def test_mutated_or_unsafe_reference_blocks_export(url):
    bundle = fixture()
    bundle.references[0].source_url = url
    with pytest.raises(ValueError):
        lesson_markdown(bundle)


def test_invalid_bundle_is_not_exported_and_opaque_id_is_safe_filename():
    bundle = fixture()
    bundle.metadata.duration_minutes += 1
    with pytest.raises(ValueError):
        lesson_markdown(bundle)
    filename = export_filename('../aula\r\nX-Fake: injected/ç')
    assert re.fullmatch(r'matilda-aula-[a-f0-9]{24}\.md', filename)


class ReadOnlyRepository:
    """Controlled authorization/expiry double implementing only the read port."""
    def __init__(self, bundle):
        self.bundle = bundle
        self.calls = []
        self.expires_at = '2026-10-28T12:10:00Z'

    async def get_lesson(self, *, session_id, lesson_bundle_id, now):
        self.calls.append((session_id, lesson_bundle_id, now))
        if session_id != 'owner' or lesson_bundle_id != self.bundle.lesson_bundle_id or datetime.fromisoformat(now) >= datetime.fromisoformat(self.expires_at):
            return None
        return self.bundle


def client_for(repository, now='2026-10-21T12:00:00Z'):
    async def session(request):
        return request.cookies.get('test_session')
    app = FastAPI()
    app.include_router(create_export_router(repository, session, clock=lambda: now))
    return TestClient(app)


def test_authorized_get_download_is_utf8_safe_and_read_only():
    bundle = fixture()
    bundle.metadata.title = 'Aula\r\nX-Injected: sim'
    repo = ReadOnlyRepository(bundle)
    with client_for(repo) as client:
        client.cookies.set('test_session', 'owner')
        path = f'/api/studio/lessons/{bundle.lesson_bundle_id}/export'
        response = client.get(path)
        replay = client.get(path + '?format=markdown')
    assert response.status_code == replay.status_code == 200
    assert response.content == replay.content == lesson_markdown(bundle).encode('utf-8')
    assert response.headers['content-type'] == 'text/markdown; charset=utf-8'
    assert re.fullmatch(r'attachment; filename="matilda-aula-[a-f0-9]{24}\.md"', response.headers['content-disposition'])
    assert 'x-injected' not in response.headers
    assert response.headers['cache-control'] == 'no-store, private'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'set-cookie' not in response.headers
    assert repo.expires_at == '2026-10-28T12:10:00Z'
    assert len(repo.calls) == 2


@pytest.mark.parametrize('session,now', [(None, '2026-10-21T12:00:00Z'), ('other', '2026-10-21T12:00:00Z'), ('owner', '2026-10-28T12:10:00Z')])
def test_missing_foreign_and_expired_sessions_receive_same_safe_error(session, now):
    repo = ReadOnlyRepository(fixture())
    with client_for(repo, now) as client:
        if session:
            client.cookies.set('test_session', session)
        response = client.get(f'/api/studio/lessons/{repo.bundle.lesson_bundle_id}/export')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Aula indisponível.', 'code': 'not_found', 'retryable': False, 'project_id': None}
    assert 'CRISPR' not in response.text
    if session is None:
        assert not repo.calls


@pytest.mark.parametrize('query', ['?format=pdf', '?format=', '?unknown=markdown', '?format=markdown&format=markdown'])
def test_invalid_formats_or_parameters_fail_before_repository(query):
    repo = ReadOnlyRepository(fixture())
    with client_for(repo) as client:
        client.cookies.set('test_session', 'owner')
        response = client.get(f'/api/studio/lessons/{repo.bundle.lesson_bundle_id}/export{query}')
    assert response.status_code == 422
    assert response.json()['code'] == 'invalid_input'
    assert not repo.calls


def test_export_route_is_not_registered_in_production_and_bad_content_does_not_leak():
    from app.main import app
    assert not any(getattr(route, 'path', '').endswith('/export') and '/studio/' in route.path for route in app.routes)
    bundle = fixture()
    bundle.references[0].source_url = 'javascript:SECRET'
    with client_for(ReadOnlyRepository(bundle)) as client:
        client.cookies.set('test_session', 'owner')
        response = client.get(f'/api/studio/lessons/{bundle.lesson_bundle_id}/export')
    assert response.status_code == 502
    assert 'SECRET' not in response.text
