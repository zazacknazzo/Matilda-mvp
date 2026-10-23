"""SQLite guard faults are injected into temporary state; assertions use HTTP."""
from datetime import datetime, timedelta
import json

import pytest

from app.api.studio_preview import get_provider, get_repository
from app.main import app
from app.services.studio.runtime_repository import StudioRepository
from test_lesson_materialization_matrix import reviewed, completed_provider
from test_studio_flow import generate


@pytest.mark.parametrize('fault,code,status', [
    ('claim', 'lesson_generation_claim_missing', 409),
    ('deadline', 'lesson_deadline_exceeded', 504),
    ('snapshot', 'lesson_persistence_snapshot_invalid', 503),
    ('fingerprint', 'lesson_persistence_review_mismatch', 409),
    ('insert', 'lesson_storage_failure', 503),
])
def test_repository_guards_record_specific_rejections_and_rollback(client, reviewed, caplog, fault, code, status):
    class GuardedRepository(StudioRepository):
        async def complete_generation(self, *, claim_id, bundle, now):
            if fault == 'claim':
                claim_id = 'missing-claim'
            elif fault == 'deadline':
                now = (datetime.fromisoformat(now) + timedelta(seconds=76)).isoformat()
            else:
                # Simulate corrupted operation state or a failed physical INSERT;
                # these states cannot be authored by the model or normal review API.
                with self.transaction() as db:
                    if fault == 'snapshot':
                        db.execute('UPDATE studio_generation_operations SET frozen=? WHERE claim=?', ('{}', claim_id))
                    elif fault == 'fingerprint':
                        db.execute('UPDATE studio_generation_operations SET fingerprint=? WHERE claim=?', ('corrupt', claim_id))
                    else:
                        db.execute("CREATE TRIGGER reject_lesson BEFORE INSERT ON lesson_bundles BEGIN SELECT RAISE(ABORT, 'PRIVATE_STORAGE'); END")
            return await super().complete_generation(claim_id=claim_id, bundle=bundle, now=now)
    provider, calls = completed_provider(lambda value, metadata: None)
    app.dependency_overrides[get_provider] = lambda: provider
    app.dependency_overrides[get_repository] = GuardedRepository
    response = generate(client, reviewed)
    assert response.status_code == status and calls == [1]
    assert code in caplog.text and 'PRIVATE_STORAGE' not in caplog.text + response.text
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'failed'
    for field in ('suggestions', 'approved_objectives', 'review_revision', 'source_documents'):
        assert current[field] == reviewed[field]


def test_failure_recording_fault_keeps_original_safe_error_and_leaves_recovery_to_lifecycle(client, reviewed, caplog):
    import sqlite3
    class FailingRepository(StudioRepository):
        async def complete_generation(self, **kwargs):
            raise sqlite3.OperationalError('PRIVATE_STORAGE')
        async def fail_generation(self, **kwargs):
            raise sqlite3.OperationalError('PRIVATE_CLEANUP')
    provider, calls = completed_provider(lambda value, metadata: None)
    app.dependency_overrides[get_provider] = lambda: provider
    app.dependency_overrides[get_repository] = FailingRepository
    response = generate(client, reviewed)
    assert response.status_code == 503 and response.json()['code'] == 'provider_unavailable'
    assert calls == [1] and 'lesson_failure_recording_failed' in caplog.text
    current = client.get('/api/studio/previews/' + reviewed['preview_id']).json()
    assert current['last_lesson_bundle_id'] is None and current['generation_status'] == 'generating'
    assert current['suggestions'] == reviewed['suggestions']
    assert 'PRIVATE_STORAGE' not in caplog.text and 'PRIVATE_CLEANUP' not in caplog.text


def test_unknown_pydantic_types_and_input_locations_are_redacted(client, reviewed, caplog):
    from pydantic import ValidationError
    from pydantic_core import PydanticCustomError
    def fail(value, metadata):
        raise ValidationError.from_exception_data('PRIVATE_MODEL', [{
            'type': PydanticCustomError('PRIVATE_TYPE', 'PRIVATE_MESSAGE'),
            'loc': ('PRIVATE_LOCATION',), 'input': 'PRIVATE_INPUT',
        }])
    provider, calls = completed_provider(fail)
    app.dependency_overrides[get_provider] = lambda: provider
    response = generate(client, reviewed)
    assert response.status_code == 502 and calls
    events = [json.loads(record.message.removeprefix('studio_lesson_validation ')) for record in caplog.records
              if record.message.startswith('studio_lesson_validation ')]
    assert events and all(event['validation_types'] == ['other'] for event in events)
    assert not any(text in caplog.text + response.text for text in
                   ('PRIVATE_MODEL', 'PRIVATE_TYPE', 'PRIVATE_MESSAGE', 'PRIVATE_LOCATION', 'PRIVATE_INPUT'))
