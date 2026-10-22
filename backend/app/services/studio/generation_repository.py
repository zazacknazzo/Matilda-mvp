"""T09 opt-in isolated SQLite adapter for the generation subset of M0.

Requires an explicit database path and a server-seeded reference review. It is not
selected by production and does not import or migrate the T05 repository.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.schemas.lesson import LessonBundle
from app.schemas.studio import EnrichmentPreview, GenerateRequest, StudioError, validate_lesson_response
from app.studio.ports import POLICY, GenerationClaim
from .generation import generation_error
from .generation_identity import timestamp, fingerprint


class IsolatedGenerationRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS t09_sessions (owner TEXT PRIMARY KEY, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS t09_previews (id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES t09_sessions(owner), body TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS t09_bundles (id TEXT PRIMARY KEY, owner TEXT NOT NULL, preview_id TEXT NOT NULL REFERENCES t09_previews(id) ON DELETE CASCADE, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS t09_operations (owner TEXT NOT NULL, key TEXT NOT NULL, claim TEXT NOT NULL UNIQUE, preview_id TEXT NOT NULL REFERENCES t09_previews(id) ON DELETE CASCADE, fingerprint TEXT NOT NULL, state TEXT NOT NULL, started REAL NOT NULL, deadline REAL NOT NULL, frozen TEXT NOT NULL, request TEXT NOT NULL, bundle_id TEXT, PRIMARY KEY(owner, key));
                CREATE TABLE IF NOT EXISTS t09_usage (owner TEXT NOT NULL REFERENCES t09_sessions(owner), admitted REAL NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=2, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _preview(self, db, owner, identifier, now):
        row = db.execute('SELECT p.body FROM t09_previews p JOIN t09_sessions s ON s.owner=p.owner WHERE p.id=? AND p.owner=? AND p.expires>? AND s.expires>?', (identifier, owner, timestamp(now), timestamp(now))).fetchone()
        return EnrichmentPreview.model_validate_json(row['body']) if row else None

    def _save(self, db, preview):
        db.execute('UPDATE t09_previews SET body=?, expires=? WHERE id=?', (preview.model_dump_json(), timestamp(preview.expires_at), preview.preview_id))

    def store_reference_preview(self, *, session_id, preview):
        """Explicit test/development admission. No HTTP endpoint calls this method."""
        preview = EnrichmentPreview.model_validate(preview.model_dump())
        with self.transaction() as db:
            if db.execute('SELECT 1 FROM t09_operations WHERE preview_id=? AND state=?', (preview.preview_id, 'generating')).fetchone():
                raise generation_error('generation_in_progress', retryable=True)
            old = db.execute('SELECT owner FROM t09_previews WHERE id=?', (preview.preview_id,)).fetchone()
            if old and old['owner'] != session_id:
                raise generation_error('not_found')
            db.execute('INSERT INTO t09_sessions VALUES (?, ?) ON CONFLICT(owner) DO UPDATE SET expires=MAX(expires, excluded.expires)', (session_id, timestamp(preview.expires_at)))
            db.execute('INSERT INTO t09_previews VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body, expires=excluded.expires', (preview.preview_id, session_id, preview.model_dump_json(), timestamp(preview.expires_at)))

    async def get_preview(self, *, session_id, preview_id, now):
        with self.transaction() as db:
            self._recover(db, now)
            return self._preview(db, session_id, preview_id, now)

    async def get_lesson(self, *, session_id, lesson_bundle_id, now):
        with self.transaction() as db:
            row = db.execute('SELECT body, preview_id FROM t09_bundles WHERE id=? AND owner=?', (lesson_bundle_id, session_id)).fetchone()
            if not row or self._preview(db, session_id, row['preview_id'], now) is None:
                return None
            return LessonBundle.model_validate_json(row['body'])

    async def claim_generation(self, *, session_id, request, idempotency_key, now):
        with self.transaction() as db:
            self._recover(db, now)
            preview = self._preview(db, session_id, request.preview_id, now)
            if preview is None:
                raise generation_error('not_found')
            try:
                request.validate_preview(preview)
            except ValueError:
                raise generation_error('review_conflict', project_id=preview.project_id) from None
            stamp = timestamp(now)
            digest = fingerprint(preview, request)
            existing = db.execute('SELECT * FROM t09_operations WHERE owner=? AND key=?', (session_id, idempotency_key)).fetchone()
            if existing and existing['fingerprint'] != digest:
                raise generation_error('review_conflict', project_id=preview.project_id)
            if existing and existing['state'] == 'completed':
                row = db.execute('SELECT body FROM t09_bundles WHERE id=? AND owner=?', (existing['bundle_id'], session_id)).fetchone()
                if not row:
                    raise generation_error('not_found')
                return GenerationClaim(None, LessonBundle.model_validate_json(row['body']))
            if db.execute("SELECT 1 FROM t09_operations WHERE owner=? AND state='generating'", (session_id,)).fetchone():
                raise generation_error('generation_in_progress', retryable=True, project_id=preview.project_id)
            db.execute('DELETE FROM t09_usage WHERE admitted<=?', (stamp - 3600,))
            if db.execute('SELECT COUNT(*) FROM t09_usage WHERE owner=?', (session_id,)).fetchone()[0] >= POLICY.generations_per_hour:
                raise generation_error('session_limit', retryable=True, project_id=preview.project_id)
            if db.execute("SELECT COUNT(*) FROM t09_operations WHERE state='generating'").fetchone()[0] >= POLICY.global_concurrency:
                raise generation_error('provider_unavailable', retryable=True, project_id=preview.project_id)
            claim_id = str(uuid4())
            db.execute('INSERT INTO t09_operations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL) ON CONFLICT(owner, key) DO UPDATE SET claim=excluded.claim, state=excluded.state, started=excluded.started, deadline=excluded.deadline, frozen=excluded.frozen, request=excluded.request, bundle_id=NULL',
                (session_id, idempotency_key, claim_id, preview.preview_id, digest, 'generating', stamp, stamp + POLICY.generation_backend_seconds, preview.model_dump_json(), request.model_dump_json()))
            preview.project.status = 'generating'
            preview.generation_status = 'generating'
            preview.last_error = None
            preview.project.updated_at = preview.project.last_teacher_activity_at = now
            preview.expires_at = preview.project.expires_at = (datetime.fromisoformat(now) + timedelta(days=POLICY.retention_days)).isoformat()
            self._save(db, preview)
            db.execute('UPDATE t09_sessions SET expires=? WHERE owner=?', (timestamp(preview.expires_at), session_id))
            db.execute('INSERT INTO t09_usage VALUES (?, ?)', (session_id, stamp))
            return GenerationClaim(claim_id, None)

    async def complete_generation(self, *, claim_id, bundle, now):
        with self.transaction() as db:
            operation = db.execute("SELECT * FROM t09_operations WHERE claim=? AND state='generating'", (claim_id,)).fetchone()
            if operation is None:
                raise generation_error('review_conflict')
            if timestamp(now) > operation['deadline']:
                raise generation_error('generation_timeout', retryable=True)
            frozen = EnrichmentPreview.model_validate_json(operation['frozen'])
            request = GenerateRequest.model_validate_json(operation['request'])
            current = self._preview(db, operation['owner'], operation['preview_id'], now)
            if current is None or current.review_revision != request.review_revision or fingerprint(current, request) != operation['fingerprint']:
                raise generation_error('review_conflict')
            bundle = LessonBundle.model_validate(bundle.model_dump())
            validate_lesson_response(bundle, preview=frozen, request=request)
            db.execute('INSERT INTO t09_bundles VALUES (?, ?, ?, ?)', (bundle.lesson_bundle_id, operation['owner'], bundle.preview_id, bundle.model_dump_json()))
            db.execute("UPDATE t09_operations SET state='completed', bundle_id=? WHERE claim=? AND state='generating'", (bundle.lesson_bundle_id, claim_id))
            current.project.status = 'ready'
            current.project.updated_at = now
            current.generation_status = 'ready'
            current.last_lesson_bundle_id = bundle.lesson_bundle_id
            current.last_error = None
            self._save(db, current)
            return bundle

    def _fail(self, db, operation, error, now):
        row = db.execute('SELECT body FROM t09_previews WHERE id=?', (operation['preview_id'],)).fetchone()
        if row:
            preview = EnrichmentPreview.model_validate_json(row['body'])
            preview.project.status = 'reviewed'
            preview.project.updated_at = now
            preview.generation_status = 'failed'
            preview.last_error = StudioError.model_validate(error.model_dump())
            self._save(db, preview)
        db.execute("UPDATE t09_operations SET state='failed' WHERE claim=?", (operation['claim'],))

    async def fail_generation(self, *, claim_id, error, now):
        with self.transaction() as db:
            operation = db.execute("SELECT * FROM t09_operations WHERE claim=? AND state='generating'", (claim_id,)).fetchone()
            if operation:
                self._fail(db, operation, error, now)

    def _recover(self, db, now):
        for operation in db.execute("SELECT * FROM t09_operations WHERE state='generating' AND deadline+?<=?", (POLICY.recovery_grace_seconds, timestamp(now))).fetchall():
            self._fail(db, operation, generation_error('generation_timeout', retryable=True).error, now)

    async def cleanup_expired(self, *, now):
        with self.transaction() as db:
            stamp = timestamp(now)
            self._recover(db, now)
            count = db.execute("DELETE FROM t09_previews WHERE expires<=? AND id NOT IN (SELECT preview_id FROM t09_operations WHERE state='generating')", (stamp,)).rowcount
            db.execute('DELETE FROM t09_usage WHERE admitted<=?', (stamp - 3600,))
            return count
