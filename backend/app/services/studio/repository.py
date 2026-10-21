"""Additive SQLite storage for T05; no transaction spans a provider call.

Owns the preview subset of StudioRepository. Review/generation remain separate
consumers of the reserved entities and the M0 ports, not executable placeholders.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.schemas.studio import EnrichmentPreview, LessonProject, StudioError
from app.services.storage import database_path
from app.studio.ports import POLICY, RepositoryConflict


def conflict(code, detail, *, retryable=False, project_id=None):
    return RepositoryConflict(StudioError(code=code, detail=detail, retryable=retryable, project_id=project_id))


def not_found():
    return conflict('not_found', 'Recurso indisponível ou sessão expirada.')


class PreviewRepository:
    @contextmanager
    def transaction(self):
        path = database_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=2)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            for statement in (
                'CREATE TABLE IF NOT EXISTS studio_sessions (id TEXT PRIMARY KEY, expires_at TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS lesson_projects (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES studio_sessions(id) ON DELETE CASCADE, payload TEXT NOT NULL, request TEXT NOT NULL, expires_at TEXT NOT NULL, last_error TEXT)',
                'CREATE TABLE IF NOT EXISTS source_documents (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES lesson_projects(id) ON DELETE CASCADE, payload TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS enrichment_previews (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES lesson_projects(id) ON DELETE CASCADE, payload TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS enrichment_suggestions (id TEXT PRIMARY KEY, preview_id TEXT NOT NULL REFERENCES enrichment_previews(id) ON DELETE CASCADE, payload TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS lesson_bundles (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES lesson_projects(id) ON DELETE CASCADE, preview_id TEXT NOT NULL REFERENCES enrichment_previews(id), payload TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS studio_preview_operations (project_id TEXT PRIMARY KEY REFERENCES lesson_projects(id) ON DELETE CASCADE, session_id TEXT NOT NULL, active_until REAL NOT NULL)',
                'CREATE TABLE IF NOT EXISTS studio_usage (session_id TEXT NOT NULL REFERENCES studio_sessions(id) ON DELETE CASCADE, started_at REAL NOT NULL, stage TEXT NOT NULL)',
            ):
                db.execute(statement)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _cleanup(self, db, now):
        timestamp = datetime.fromisoformat(now).timestamp()
        db.execute('DELETE FROM studio_preview_operations WHERE active_until <= ?', (timestamp,))
        db.execute('DELETE FROM studio_usage WHERE started_at <= ?', (timestamp - 3600,))
        result = db.execute('DELETE FROM lesson_projects WHERE expires_at <= ? AND id NOT IN (SELECT project_id FROM studio_preview_operations)', (now,))
        db.execute('DELETE FROM studio_sessions WHERE expires_at <= ? AND id NOT IN (SELECT session_id FROM studio_preview_operations)', (now,))
        return result.rowcount

    async def cleanup_expired(self, *, now):
        with self.transaction() as db:
            return self._cleanup(db, now)

    async def save_material(self, *, session_id, project, request, documents, now):
        with self.transaction() as db:
            self._cleanup(db, now)
            existing = db.execute('SELECT session_id, payload FROM lesson_projects WHERE id=? AND expires_at>?', (project.id, now)).fetchone()
            session = db.execute('SELECT expires_at FROM studio_sessions WHERE id=?', (session_id,)).fetchone()
            if request.project_id and (not existing or existing[0] != session_id or not session or session[0] <= now):
                raise not_found()
            if db.execute('SELECT 1 FROM studio_preview_operations WHERE session_id=?', (session_id,)).fetchone():
                raise conflict('generation_in_progress', 'Uma operação Studio já está em andamento.', retryable=True)
            timestamp = datetime.fromisoformat(now).timestamp()
            usage = db.execute('SELECT started_at FROM studio_usage WHERE session_id=? AND stage=? ORDER BY started_at', (session_id, 'preview')).fetchall()
            if len(usage) >= POLICY.previews_per_hour:
                raise conflict('session_limit', 'Limite de cinco prévias por hora. Aguarde antes de tentar novamente.', retryable=True)
            if db.execute('SELECT COUNT(*) FROM studio_preview_operations').fetchone()[0] >= POLICY.global_concurrency:
                raise conflict('provider_unavailable', 'Studio ocupado. Tente novamente em instantes.', retryable=True)
            if existing:
                project.created_at = LessonProject.model_validate_json(existing[1]).created_at
            db.execute('INSERT INTO studio_sessions VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET expires_at=excluded.expires_at', (session_id, project.expires_at))
            db.execute('INSERT INTO lesson_projects VALUES (?, ?, ?, ?, ?, NULL) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, request=excluded.request, expires_at=excluded.expires_at, last_error=NULL', (project.id, session_id, project.model_dump_json(), request.model_dump_json(), project.expires_at))
            for document in documents:
                db.execute('INSERT INTO source_documents VALUES (?, ?, ?)', (document.id, project.id, document.model_dump_json()))
            db.execute('INSERT INTO studio_preview_operations VALUES (?, ?, ?)', (project.id, session_id, timestamp + POLICY.preview_backend_seconds + POLICY.recovery_grace_seconds))
            db.execute('INSERT INTO studio_usage VALUES (?, ?, ?)', (session_id, timestamp, 'preview'))

    async def publish_preview(self, *, session_id, preview, now):
        with self.transaction() as db:
            row = db.execute('SELECT p.payload FROM lesson_projects p JOIN studio_preview_operations o ON o.project_id=p.id WHERE p.id=? AND p.session_id=? AND o.active_until>?', (preview.project_id, session_id, datetime.fromisoformat(now).timestamp())).fetchone()
            if not row:
                raise not_found()
            current = LessonProject.model_validate_json(row[0])
            if current.expires_at != preview.expires_at:
                raise conflict('review_conflict', 'O projeto mudou durante a operação.')
            db.execute('INSERT INTO enrichment_previews VALUES (?, ?, ?)', (preview.preview_id, preview.project_id, preview.model_dump_json()))
            for suggestion in preview.suggestions:
                db.execute('INSERT INTO enrichment_suggestions VALUES (?, ?, ?)', (suggestion.id, preview.preview_id, suggestion.model_dump_json()))
            db.execute('UPDATE lesson_projects SET payload=?, last_error=NULL WHERE id=?', (preview.project.model_dump_json(), preview.project_id))
            db.execute('DELETE FROM studio_preview_operations WHERE project_id=?', (preview.project_id,))

    async def fail_preview(self, *, session_id, project_id, error, now):
        with self.transaction() as db:
            db.execute('UPDATE lesson_projects SET last_error=? WHERE id=? AND session_id=?', (error.model_dump_json(), project_id, session_id))
            db.execute('DELETE FROM studio_preview_operations WHERE project_id=? AND session_id=?', (project_id, session_id))

    async def get_preview(self, *, session_id, preview_id, now):
        with self.transaction() as db:
            self._cleanup(db, now)
            row = db.execute('SELECT e.payload, p.payload FROM enrichment_previews e JOIN lesson_projects p ON p.id=e.project_id JOIN studio_sessions s ON s.id=p.session_id WHERE e.id=? AND p.session_id=? AND p.expires_at>? AND s.expires_at>?', (preview_id, session_id, now, now)).fetchone()
            if not row:
                return None
            payload = json.loads(row[0])
            project = json.loads(row[1])
            # Previous previews keep their immutable configuration/context/decisions.
            for key in ('updated_at', 'last_teacher_activity_at', 'expires_at'):
                payload['project'][key] = project[key]
            payload['expires_at'] = project['expires_at']
            return EnrichmentPreview.model_validate(payload)

    async def append_documents(self, *, session_id, project_id, documents, now):
        with self.transaction() as db:
            if not db.execute('SELECT 1 FROM lesson_projects WHERE id=? AND session_id=? AND expires_at>?', (project_id, session_id, now)).fetchone():
                raise not_found()
            for document in documents:
                db.execute('INSERT INTO source_documents VALUES (?, ?, ?)', (document.id, project_id, document.model_dump_json()))
