"""Production Studio adapter: one project/preview/bundle store, atomic admissions."""
import json
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from app.schemas.lesson import LessonBundle, LessonReference
from app.schemas.models import Concept, DiscoveryMatch, Paper
from app.schemas.studio import EnrichmentPreview, GenerateRequest, validate_lesson_response
from app.studio.ports import POLICY, GenerationClaim
from .generation import generation_error
from .generation_identity import fingerprint, timestamp
from .lesson_validator import ScientificAuthority
from .repository import PreviewRepository, not_found


class StudioRepository(PreviewRepository):
    def _preview(self, db, session_id, preview_id, now):
        row = db.execute('SELECT e.payload, p.payload, p.last_error FROM enrichment_previews e JOIN lesson_projects p ON p.id=e.project_id JOIN studio_sessions s ON s.id=p.session_id WHERE e.id=? AND p.session_id=? AND p.expires_at>? AND s.expires_at>?', (preview_id, session_id, now, now)).fetchone()
        if not row:
            return None
        value, project = json.loads(row[0]), json.loads(row[1])
        for key in ('updated_at', 'last_teacher_activity_at', 'expires_at'):
            value['project'][key] = project[key]
        value['expires_at'] = project['expires_at']
        value['last_error'] = json.loads(row[2]) if row[2] else None
        return EnrichmentPreview.model_validate(value)

    def _save(self, db, preview):
        preview = EnrichmentPreview.model_validate(preview.model_dump())
        db.execute('UPDATE enrichment_previews SET payload=? WHERE id=?', (preview.model_dump_json(), preview.preview_id))
        db.execute('UPDATE lesson_projects SET payload=?, expires_at=?, last_error=? WHERE id=?', (preview.project.model_dump_json(), preview.expires_at, preview.last_error.model_dump_json() if preview.last_error else None, preview.project_id))
        for suggestion in preview.suggestions:
            db.execute('UPDATE enrichment_suggestions SET payload=? WHERE id=? AND preview_id=?', (suggestion.model_dump_json(), suggestion.id, preview.preview_id))

    def scientific_authority(self, preview):
        with self.transaction() as db:
            row = db.execute('SELECT payload FROM studio_scientific_snapshots WHERE preview_id=?', (preview.preview_id,)).fetchone()
        if not row:
            raise ValueError('Scientific snapshot unavailable; create a new preview.')
        value = json.loads(row[0])
        return ScientificAuthority(
            [DiscoveryMatch.model_validate(x) for x in value['matches']],
            {k: LessonReference.model_validate(v) for k, v in value['references'].items()},
            [Concept.model_validate(x) for x in value['concepts']],
            [Paper.model_validate(x) for x in value['papers']],
        )

    def _renew(self, db, preview, session_id, now):
        preview.project.updated_at = preview.project.last_teacher_activity_at = now
        preview.expires_at = preview.project.expires_at = (datetime.fromisoformat(now) + timedelta(days=POLICY.retention_days)).isoformat()
        db.execute('UPDATE studio_sessions SET expires_at=? WHERE id=?', (preview.expires_at, session_id))

    def _idle(self, db, session_id, project_id):
        if db.execute('SELECT 1 FROM studio_preview_operations WHERE session_id=? OR project_id=?', (session_id, project_id)).fetchone():
            raise generation_error('generation_in_progress', retryable=True, project_id=project_id)

    async def save_review(self, *, session_id, preview_id, request, now):
        with self.transaction() as db:
            self._cleanup(db, now)
            preview = self._preview(db, session_id, preview_id, now)
            if preview is None:
                raise not_found()
            self._idle(db, session_id, preview.project_id)
            try:
                request.validate_preview(preview)
            except ValueError:
                raise generation_error('review_conflict', project_id=preview.project_id) from None
            for decision in request.decisions:
                item = next(s for s in preview.suggestions if s.id == decision.suggestion_id)
                item.status = decision.status
                for field in ('pedagogical_rationale', 'suggested_content'):
                    value = getattr(decision, field)
                    if value is not None:
                        setattr(item, field, value)
            preview.approved_objectives = list(request.approved_objectives)
            preview.review_revision += 1
            preview.project.status = 'reviewed' if all(s.status != 'pending' for s in preview.suggestions) else 'preview_ready'
            preview.generation_status = 'idle'
            preview.last_error = None
            self._renew(db, preview, session_id, now)
            self._save(db, preview)
            return preview

    async def get_lesson(self, *, session_id, lesson_bundle_id, now):
        with self.transaction() as db:
            self._cleanup(db, now)
            row = db.execute('SELECT b.payload FROM lesson_bundles b JOIN lesson_projects p ON p.id=b.project_id JOIN studio_sessions s ON s.id=p.session_id WHERE b.id=? AND p.session_id=? AND p.expires_at>? AND s.expires_at>?', (lesson_bundle_id, session_id, now, now)).fetchone()
            return LessonBundle.model_validate_json(row[0]) if row else None

    async def claim_generation(self, *, session_id, request, idempotency_key, now):
        with self.transaction() as db:
            self._cleanup(db, now)
            preview = self._preview(db, session_id, request.preview_id, now)
            if preview is None:
                raise not_found()
            try:
                request.validate_preview(preview)
            except ValueError:
                raise generation_error('review_conflict', project_id=preview.project_id) from None
            digest = fingerprint(preview, request)
            db.row_factory = sqlite3.Row
            existing = db.execute('SELECT * FROM studio_generation_operations WHERE session_id=? AND key=?', (session_id, idempotency_key)).fetchone()
            if existing and existing['fingerprint'] != digest:
                raise generation_error('review_conflict', project_id=preview.project_id)
            if existing and existing['state'] == 'completed':
                row = db.execute('SELECT payload FROM lesson_bundles WHERE id=?', (existing['bundle_id'],)).fetchone()
                if not row:
                    raise not_found()
                return GenerationClaim(None, LessonBundle.model_validate_json(row[0]))
            self._idle(db, session_id, preview.project_id)
            if db.execute("SELECT COUNT(*) FROM studio_usage WHERE session_id=? AND stage='lesson'", (session_id,)).fetchone()[0] >= POLICY.generations_per_hour:
                raise generation_error('session_limit', retryable=True, project_id=preview.project_id)
            if db.execute('SELECT COUNT(*) FROM studio_preview_operations').fetchone()[0] >= POLICY.global_concurrency:
                raise generation_error('provider_unavailable', retryable=True, project_id=preview.project_id)
            claim = str(uuid4())
            stamp = timestamp(now)
            db.execute('INSERT INTO studio_generation_operations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL) ON CONFLICT(session_id, key) DO UPDATE SET claim=excluded.claim, state=excluded.state, deadline=excluded.deadline, frozen=excluded.frozen, request=excluded.request, bundle_id=NULL', (session_id, idempotency_key, claim, preview.preview_id, digest, 'generating', stamp + POLICY.generation_backend_seconds, preview.model_dump_json(), request.model_dump_json()))
            db.execute('INSERT INTO studio_preview_operations VALUES (?, ?, ?)', (preview.project_id, session_id, stamp + POLICY.generation_backend_seconds + POLICY.recovery_grace_seconds))
            db.execute('INSERT INTO studio_usage VALUES (?, ?, ?)', (session_id, stamp, 'lesson'))
            preview.project.status = preview.generation_status = 'generating'
            preview.last_error = None
            self._renew(db, preview, session_id, now)
            self._save(db, preview)
            return GenerationClaim(claim, None)

    async def complete_generation(self, *, claim_id, bundle, now):
        with self.transaction() as db:
            db.row_factory = sqlite3.Row
            op = db.execute("SELECT * FROM studio_generation_operations WHERE claim=? AND state='generating'", (claim_id,)).fetchone()
            if not op:
                raise generation_error('review_conflict')
            if timestamp(now) > op['deadline']:
                raise generation_error('generation_timeout', retryable=True)
            frozen = EnrichmentPreview.model_validate_json(op['frozen'])
            request = GenerateRequest.model_validate_json(op['request'])
            current = self._preview(db, op['session_id'], op['preview_id'], now)
            if current is None or fingerprint(current, request) != op['fingerprint']:
                raise generation_error('review_conflict')
            bundle = LessonBundle.model_validate(bundle.model_dump())
            validate_lesson_response(bundle, preview=frozen, request=request)
            db.execute('INSERT INTO lesson_bundles VALUES (?, ?, ?, ?)', (bundle.lesson_bundle_id, bundle.project_id, bundle.preview_id, bundle.model_dump_json()))
            db.execute("UPDATE studio_generation_operations SET state='completed', bundle_id=? WHERE claim=?", (bundle.lesson_bundle_id, claim_id))
            current.project.status = current.generation_status = 'ready'
            current.project.updated_at = now
            current.last_lesson_bundle_id = bundle.lesson_bundle_id
            current.last_error = None
            self._save(db, current)
            db.execute('DELETE FROM studio_preview_operations WHERE project_id=?', (current.project_id,))
            return bundle

    def _fail(self, db, op, error, now):
        preview = self._preview(db, op['session_id'], op['preview_id'], now)
        if preview:
            preview.project.status = 'reviewed'
            preview.project.updated_at = now
            preview.generation_status = 'failed'
            preview.last_error = error
            self._save(db, preview)
            db.execute('DELETE FROM studio_preview_operations WHERE project_id=?', (preview.project_id,))
        db.execute("UPDATE studio_generation_operations SET state='failed' WHERE claim=?", (op['claim'],))

    async def fail_generation(self, *, claim_id, error, now):
        with self.transaction() as db:
            db.row_factory = sqlite3.Row
            op = db.execute("SELECT * FROM studio_generation_operations WHERE claim=? AND state='generating'", (claim_id,)).fetchone()
            if op:
                self._fail(db, op, error, now)

    def _cleanup(self, db, now):
        db.row_factory = sqlite3.Row
        for op in db.execute("SELECT * FROM studio_generation_operations WHERE state='generating' AND deadline+?<=?", (POLICY.recovery_grace_seconds, timestamp(now))).fetchall():
            self._fail(db, op, generation_error('generation_timeout', retryable=True).error, now)
        return super()._cleanup(db, now)
