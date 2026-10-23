"""Fault injection at the provider port after real NVIDIA MockTransport completion.

Local-key faults cannot be emitted by compact-v3; they defend the materializer
against an expansion/adapter regression without claiming the model controls keys.
"""
import json

import httpx
import pytest

from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider
from app.main import app
from app.schemas.lesson import LessonGenerationMetadata
from app.studio.ports import ProviderResult
from studio_flow_provider import FlowProvider
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_provider import completion
from test_studio_flow import create, generate, review


@pytest.fixture
def reviewed(client, monkeypatch, caplog):
    monkeypatch.setenv('NVIDIA_API_KEY', 'PRIVATE_CREDENTIAL')
    caplog.set_level('INFO', logger='matilda.studio.validation')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    app.dependency_overrides[get_provider] = lambda: FlowProvider()
    saved, _ = review(client, create(client))
    yield saved
    app.dependency_overrides.clear()


def completed_provider(mutate):
    calls = []
    def upstream(http):
        calls.append(1)
        material = json.loads(json.loads(http.content)['messages'][1]['content'])
        value = compact_lesson()
        value['sections'][0]['slides'][0].setdefault('evidence_ids', []).append(next(iter(material['authorized_evidence'])))
        return httpx.Response(200, json=completion(json.dumps(value)))
    inner = NVIDIAProvider(transport=httpx.MockTransport(upstream))
    class CompletedProvider:
        async def count_input_tokens(self, request):
            return await inner.count_input_tokens(request)
        async def complete(self, request):
            result = await inner.complete(request)
            value = json.loads(result.content)
            changed = mutate(value, result.metadata)
            return changed if isinstance(changed, ProviderResult) else ProviderResult(json.dumps(value).encode(), result.metadata)
    return CompletedProvider(), calls


def corrupt(fault, value, metadata):
    if fault in ('duplicate_sections', 'duplicate_slides', 'duplicate_activities'):
        collection = value[{'duplicate_sections': 'sections', 'duplicate_slides': 'slides', 'duplicate_activities': 'activities'}[fault]]
        if len(collection) == 1:
            collection.append(dict(collection[0]))
        else:
            collection[1]['key'] = collection[0]['key']
    elif fault == 'missing_slide':
        value['sections'][0]['slide_keys'] = ['PRIVATE_LINK']
    elif fault == 'missing_activity':
        value['sections'][0]['activity_keys'] = ['PRIVATE_LINK']
    elif fault == 'slide_missing_section':
        value['slides'][0]['section_key'] = 'PRIVATE_LINK'
    elif fault == 'activity_missing_section':
        value['activities'][0]['section_key'] = 'PRIVATE_LINK'
    elif fault == 'wrong_slide_owner':
        value['slides'][0]['section_key'] = value['sections'][1]['key']
    elif fault == 'wrong_activity_owner':
        value['sections'][0]['activity_keys'] = value['sections'][-1]['activity_keys']
    elif fault == 'orphan_slide':
        value['sections'][1]['slide_keys'].pop()
        value['slides'][1]['duration_minutes'] = value['sections'][1]['duration_minutes']
    elif fault == 'orphan_activity':
        value['sections'][-1]['activity_keys'] = []
    elif fault == 'duplicate_slide_link':
        value['sections'][0]['slide_keys'] *= 2
    elif fault == 'unauthorized_section_claim':
        value['sections'][0]['explanation_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'PRIVATE_EVIDENCE'})
    elif fault == 'unauthorized_slide_claim':
        value['slides'][0]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'PRIVATE_EVIDENCE'})
    elif fault == 'section_duration':
        value['sections'][0]['duration_minutes'] += 1
    elif fault == 'slide_duration':
        value['slides'][0]['duration_minutes'] += 1
    elif fault == 'objective_range':
        value['sections'][0]['objective_indexes'] = [999]
    elif fault == 'activity_objective_range':
        value['activities'][0]['objective_indexes'] = [999]
    elif fault == 'objective_duplicate':
        value['sections'][0]['objective_indexes'] = [0, 0]
    elif fault == 'draft_extra':
        value['PRIVATE_EXTRA'] = 'PRIVATE_TEXT'
    elif fault == 'draft_missing':
        del value['materials']
    elif fault == 'draft_type':
        return ProviderResult('PRIVATE_TEXT', metadata)
    elif fault == 'draft_size':
        return ProviderResult(b'x' * (128 * 1024 + 1), metadata)
    elif fault == 'draft_json':
        return ProviderResult(b'{"PRIVATE_TEXT":', metadata)
    elif fault == 'draft_duplicate_json':
        return ProviderResult(b'{"PRIVATE_TEXT":1,"PRIVATE_TEXT":2}', metadata)
    elif fault == 'draft_root':
        return ProviderResult(b'[]', metadata)
    elif fault == 'layout_process':
        value['slides'][0]['layout'] = 'PROCESS'
    elif fault == 'layout_question':
        value['slides'][0]['layout'] = 'QUESTION'
    elif fault == 'layout_concept':
        value['slides'][0]['layout'] = 'CONCEPT'
        value['slides'][0]['content_blocks'] = []
    elif fault == 'layout_spotlight':
        value['slides'][1]['layout'] = 'SCIENTIST_SPOTLIGHT'
    elif fault == 'visible_limit':
        value['slides'][0]['title'] = 'PRIVATE_TEXT'
        value['slides'][0]['content_blocks'] = [{'type': 'text', 'text': 'x' * 600}]
    elif fault == 'metadata_missing':
        return ProviderResult(json.dumps(value).encode(), None)
    elif fault == 'metadata_prompt':
        metadata.prompt_version = 'PRIVATE_VERSION'
    elif fault == 'metadata_input_budget':
        metadata.input_tokens = 12001
    elif fault == 'metadata_output_budget':
        metadata.output_tokens = 8001
    elif fault == 'metadata_negative':
        metadata.duration_ms = -1
    elif fault == 'metadata_type':
        metadata.model = {'PRIVATE_KEY': 'PRIVATE_TEXT'}
    elif fault == 'metadata_time':
        metadata.generated_at = 'PRIVATE_TIMESTAMP'
    elif fault == 'metadata_version':
        metadata.schema_version = 2
    elif fault == 'internal':
        class BrokenMetadata(LessonGenerationMetadata):
            def model_dump(self, **kwargs):
                raise RuntimeError('PRIVATE_TEXT')
        return ProviderResult(json.dumps(value).encode(), BrokenMetadata.model_validate(metadata.model_dump()))
    else:
        raise AssertionError(fault)


@pytest.mark.parametrize('fault,code', [
    ('duplicate_sections', 'lesson_duplicate_local_key'), ('duplicate_slides', 'lesson_duplicate_local_key'),
    ('duplicate_activities', 'lesson_duplicate_local_key'), ('missing_slide', 'lesson_section_slide_link_invalid'),
    ('missing_activity', 'lesson_section_activity_link_invalid'), ('slide_missing_section', 'lesson_slide_section_link_invalid'),
    ('activity_missing_section', 'lesson_activity_section_link_invalid'), ('wrong_slide_owner', 'lesson_section_slide_link_invalid'),
    ('wrong_activity_owner', 'lesson_section_activity_link_invalid'), ('orphan_slide', 'lesson_slide_ownership_invalid'),
    ('orphan_activity', 'lesson_activity_ownership_invalid'), ('duplicate_slide_link', 'lesson_duplicate_identifier'),
    ('unauthorized_section_claim', 'lesson_evidence_not_authorized'), ('unauthorized_slide_claim', 'lesson_evidence_not_authorized'),
    ('section_duration', 'lesson_duration_mismatch'), ('slide_duration', 'lesson_section_duration_mismatch'),
    ('objective_range', 'lesson_objective_not_approved'), ('activity_objective_range', 'lesson_objective_not_approved'),
    ('objective_duplicate', 'lesson_duplicate_identifier'), ('draft_extra', 'lesson_draft_schema_invalid'),
    ('draft_missing', 'lesson_draft_schema_invalid'), ('draft_type', 'lesson_draft_type_invalid'),
    ('draft_size', 'lesson_draft_size_invalid'), ('draft_json', 'lesson_draft_json_invalid'),
    ('draft_duplicate_json', 'lesson_draft_json_invalid'), ('draft_root', 'lesson_draft_schema_invalid'),
    ('layout_process', 'lesson_slide_layout_invalid'), ('layout_question', 'lesson_slide_layout_invalid'),
    ('layout_concept', 'lesson_slide_layout_invalid'), ('layout_spotlight', 'lesson_slide_layout_invalid'),
    ('visible_limit', 'lesson_slide_content_too_large'), ('metadata_missing', 'lesson_metadata_invalid'),
    ('metadata_prompt', 'lesson_metadata_prompt_mismatch'), ('metadata_input_budget', 'lesson_metadata_budget_invalid'),
    ('metadata_output_budget', 'lesson_metadata_budget_invalid'), ('metadata_negative', 'lesson_metadata_invalid'),
    ('metadata_type', 'lesson_metadata_invalid'), ('metadata_time', 'lesson_metadata_invalid'),
    ('metadata_version', 'lesson_metadata_invalid'), ('internal', 'lesson_internal_failure'),
])
def test_post_provider_rejections_are_specific_safe_and_do_not_publish(client, reviewed, caplog, fault, code):
    provider, calls = completed_provider(lambda value, metadata: corrupt(fault, value, metadata))
    app.dependency_overrides[get_provider] = lambda: provider
    response = generate(client, reviewed)
    assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    for field in ('suggestions', 'approved_objectives', 'review_revision', 'source_documents'):
        assert current[field] == reviewed[field]
    assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'failed'
    events = [json.loads(record.message.removeprefix('studio_lesson_validation ')) for record in caplog.records
              if record.message.startswith('studio_lesson_validation ')]
    assert any(event['failure_code'] == code for event in events)
    assert calls and all('"outcome":"completed"' in record.message for record in caplog.records
                         if record.message.startswith('nvidia_attempt '))
    from app.studio.lesson_diagnostics import CODES, PYDANTIC_TYPES
    for event in events:
        assert set(event) <= {'stage', 'validation_phase', 'failure_code', 'outcome', 'validation_types'}
        assert set(event.get('validation_types', [])) <= CODES | PYDANTIC_TYPES | {'other'}
    forbidden = ['PRIVATE_CREDENTIAL', 'PRIVATE_LINK', 'PRIVATE_EVIDENCE', 'PRIVATE_TEXT', 'PRIVATE_EXTRA',
                 'PRIVATE_VERSION', 'PRIVATE_TIMESTAMP', 'PRIVATE_KEY',
                 *(ref['id'] for ref in reviewed['evidence_references'])]
    assert not any(text in caplog.text + response.text for text in forbidden)


def corrupt_bundle(fault, bundle):
    if fault == 'review':
        bundle.review_revision += 1
    elif fault == 'project':
        bundle.project_id = 'PRIVATE_PROJECT'
    elif fault == 'preview':
        bundle.preview_id = 'PRIVATE_PREVIEW'
    elif fault == 'configuration':
        bundle.metadata.title = 'PRIVATE_CONFIG'
    elif fault == 'configuration_duration':
        bundle.metadata.duration_minutes += 1
        bundle.sections[0].duration_minutes += 1
        bundle.slides[0].duration_minutes += 1
    elif fault == 'objectives':
        bundle.metadata.learning_objectives = ['PRIVATE_OBJECTIVE']
    elif fault == 'contribution_binding':
        bundle.slides[0].contribution_ids = ['PRIVATE_CONTRIBUTION']
    elif fault == 'evidence_binding':
        bundle.slides[0].evidence_ids = []
    elif fault == 'reference_snapshot':
        bundle.references[0].claim_supported = 'PRIVATE_FAKE_CLAIM'
    elif fault == 'reference_url':
        bundle.references[0].source_url = 'https://PRIVATE_USER:PRIVATE_PASSWORD@example.test'
    elif fault == 'reference_url_parse':
        bundle.references[0].source_url = 'http://[PRIVATE_HOST'
    elif fault == 'reference_time':
        bundle.references[0].retrieved_at = 'PRIVATE_TIME'
    elif fault == 'reference_status':
        bundle.references[0].verification_status = 'pending'
    elif fault == 'reference_participants':
        bundle.references[0].participants *= 2
    elif fault == 'unused_reference':
        bundle.references.append(bundle.references[0].model_copy(update={'id': 'PRIVATE_UNUSED'}))
    elif fault == 'unauthorized_reference':
        old = bundle.references[0].id
        bundle.references[0].id = 'PRIVATE_REFERENCE'
        for section in bundle.sections:
            for block in section.explanation_blocks:
                if block.type == 'evidence_claim' and block.evidence_id == old:
                    block.evidence_id = 'PRIVATE_REFERENCE'
        for slide in bundle.slides:
            slide.evidence_ids = ['PRIVATE_REFERENCE' if value == old else value for value in slide.evidence_ids]
            for block in slide.content_blocks:
                if block.type == 'evidence_claim' and block.evidence_id == old:
                    block.evidence_id = 'PRIVATE_REFERENCE'
    elif fault == 'duplicate_identifier':
        bundle.activities.append(bundle.activities[0].model_copy())
    elif fault == 'bundle_size':
        bundle.metadata.prior_knowledge = ['x' * 20000] * 7
    elif fault == 'sections_count':
        bundle.sections *= 3
    elif fault == 'slides_count':
        bundle.slides = bundle.slides[:3]
    elif fault == 'activities_count':
        bundle.activities = []
    elif fault == 'version':
        bundle.schema_version = 2
    else:
        raise AssertionError(fault)


@pytest.mark.parametrize('fault,code', [
    ('review', 'lesson_review_mismatch'), ('project', 'lesson_review_mismatch'), ('preview', 'lesson_review_mismatch'),
    ('configuration', 'lesson_configuration_mismatch'), ('configuration_duration', 'lesson_configuration_mismatch'),
    ('objectives', 'lesson_objectives_mismatch'), ('contribution_binding', 'lesson_contribution_binding_mismatch'),
    ('evidence_binding', 'lesson_evidence_binding_mismatch'), ('reference_snapshot', 'lesson_reference_snapshot_mismatch'),
    ('reference_url', 'lesson_reference_url_invalid'), ('reference_url_parse', 'lesson_reference_url_invalid'), ('reference_time', 'lesson_timestamp_invalid'),
    ('reference_status', 'lesson_bundle_schema_invalid'), ('reference_participants', 'lesson_duplicate_identifier'),
    ('unused_reference', 'lesson_reference_usage_mismatch'), ('unauthorized_reference', 'lesson_evidence_not_authorized'),
    ('duplicate_identifier', 'lesson_duplicate_identifier'), ('bundle_size', 'lesson_bundle_too_large'),
    ('sections_count', 'lesson_bundle_schema_invalid'), ('slides_count', 'lesson_bundle_schema_invalid'),
    ('activities_count', 'lesson_bundle_schema_invalid'), ('version', 'lesson_bundle_schema_invalid'),
])
def test_bundle_and_frozen_review_are_rechecked_before_sqlite_publish(client, reviewed, caplog, fault, code):
    from app.api.studio_preview import get_repository
    from app.services.studio.runtime_repository import StudioRepository
    class CorruptingRepository(StudioRepository):
        async def complete_generation(self, *, claim_id, bundle, now):
            corrupt_bundle(fault, bundle)
            return await super().complete_generation(claim_id=claim_id, bundle=bundle, now=now)
    provider, calls = completed_provider(lambda value, metadata: None)
    app.dependency_overrides[get_provider] = lambda: provider
    app.dependency_overrides[get_repository] = CorruptingRepository
    response = generate(client, reviewed)
    assert response.status_code == 502 and response.json()['code'] == 'invalid_generation'
    assert calls == [1]
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'failed'
    for field in ('suggestions', 'approved_objectives', 'review_revision', 'source_documents'):
        assert current[field] == reviewed[field]
    assert code in caplog.text
    assert 'PRIVATE_' not in caplog.text + response.text


@pytest.mark.parametrize('kind,code', [('storage', 'lesson_storage_failure'), ('internal', 'lesson_internal_failure')])
def test_persistence_failures_are_safe_and_do_not_publish(client, reviewed, caplog, kind, code):
    import sqlite3
    from app.api.studio_preview import get_repository
    from app.services.studio.runtime_repository import StudioRepository
    class FailingRepository(StudioRepository):
        async def complete_generation(self, **kwargs):
            raise (sqlite3.OperationalError if kind == 'storage' else RuntimeError)('PRIVATE_ERROR')
    provider, calls = completed_provider(lambda value, metadata: None)
    app.dependency_overrides[get_provider] = lambda: provider
    app.dependency_overrides[get_repository] = FailingRepository
    response = generate(client, reviewed)
    assert response.status_code == 503 and response.json()['code'] == 'provider_unavailable'
    assert calls == [1] and code in caplog.text and 'PRIVATE_ERROR' not in caplog.text + response.text
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'failed'


@pytest.mark.parametrize('kind', ['storage', 'validation'])
def test_completion_read_failure_keeps_valid_bundle_and_replay_does_not_infer_again(client, reviewed, caplog, kind):
    import sqlite3
    from app.api.studio_preview import get_repository
    from app.services.studio.runtime_repository import StudioRepository
    class LostResponseRepository(StudioRepository):
        committed = False
        failed_read = False
        async def complete_generation(self, **kwargs):
            result = await super().complete_generation(**kwargs)
            self.committed = True
            return result
        async def get_preview(self, **kwargs):
            if self.committed and not self.failed_read:
                self.failed_read = True
                if kind == 'validation':
                    from pydantic import ValidationError
                    raise ValidationError.from_exception_data('PRIVATE_MODEL', [{'type': 'string_type', 'loc': ('PRIVATE_FIELD',), 'input': None}])
                raise sqlite3.OperationalError('PRIVATE_ERROR')
            return await super().get_preview(**kwargs)
    repository = LostResponseRepository()
    provider, calls = completed_provider(lambda value, metadata: None)
    app.dependency_overrides[get_provider] = lambda: provider
    app.dependency_overrides[get_repository] = lambda: repository
    assert generate(client, reviewed).status_code == 503
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    assert current['generation_status'] == 'ready' and current['last_lesson_bundle_id']
    replay = generate(client, reviewed)
    assert replay.status_code == 200 and replay.json()['lesson_bundle_id'] == current['last_lesson_bundle_id']
    assert calls == [1]
    assert ('lesson_storage_failure' if kind == 'storage' else 'lesson_completion_schema_invalid') in caplog.text
    assert '"validation_phase":"completion"' in caplog.text
    assert not any(value in caplog.text for value in ('PRIVATE_ERROR', 'PRIVATE_MODEL', 'PRIVATE_FIELD'))
