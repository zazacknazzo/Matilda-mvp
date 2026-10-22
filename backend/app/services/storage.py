import json
import os
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'data'

def database_path():
    return Path(os.getenv('MATILDA_DB', str(ROOT / '.runtime/matilda.db')))

@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS cache (doi TEXT PRIMARY KEY, payload TEXT NOT NULL, retrieved_at TEXT NOT NULL, stored_at REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, payload TEXT NOT NULL, stored_at REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS external_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, retrieved_at TEXT NOT NULL, stored_at REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS catalog_candidates (id TEXT PRIMARY KEY, doi TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS catalog_revisions (candidate_id TEXT NOT NULL, revision TEXT NOT NULL, payload TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(candidate_id, revision))')
        db.execute('DELETE FROM analyses WHERE stored_at < ?', (time.time() - 7 * 86400,))
        yield db

def load_json(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))

def cached(doi):
    with connection() as db:
        row = db.execute('SELECT payload, retrieved_at, stored_at FROM cache WHERE doi = ?', (doi,)).fetchone()
    if row:
        return json.loads(row[0]), row[1], time.time() - row[2]
    path = DATA / 'openalex_snapshots' / (doi.replace('/', '_') + '.json')
    if path.exists():
        from datetime import datetime
        snapshot = json.loads(path.read_text())
        return snapshot['data'], snapshot['retrieved_at'], time.time() - datetime.fromisoformat(snapshot['retrieved_at']).timestamp()
    return None

def save_cache(doi, raw, retrieved_at):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)', (doi, json.dumps(raw), retrieved_at, time.time()))

def save_analysis(analysis):
    with connection() as db:
        db.execute('INSERT INTO analyses VALUES (?, ?, ?)', (analysis.id, analysis.model_dump_json(), time.time()))

def get_analysis(identifier):
    with connection() as db:
        row = db.execute('SELECT payload FROM analyses WHERE id = ?', (identifier,)).fetchone()
    return json.loads(row[0]) if row else None


def update_analysis(analysis):
    with connection() as db:
        db.execute('UPDATE analyses SET payload = ? WHERE id = ?', (analysis.model_dump_json(), analysis.id))


def external_cached(key, ttl=86400):
    with connection() as db:
        row = db.execute('SELECT payload, retrieved_at, stored_at FROM external_cache WHERE key = ?', (key,)).fetchone()
    if row and time.time() - row[2] < ttl:
        return json.loads(row[0]), row[1]
    return None


def save_external_cache(key, payload, retrieved_at):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO external_cache VALUES (?, ?, ?, ?)', (key, json.dumps(payload), retrieved_at, time.time()))


def upsert_candidate(candidate):
    from hashlib import sha256
    from datetime import datetime, timezone
    payload = candidate.model_dump_json()
    revision = sha256(payload.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with connection() as db:
        db.execute('INSERT INTO catalog_candidates VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at', (candidate.id, candidate.work.doi, payload, now, now))
        db.execute('INSERT OR IGNORE INTO catalog_revisions VALUES (?, ?, ?, ?)', (candidate.id, revision, payload, now))


def list_candidates(offset=0, limit=30):
    with connection() as db:
        total = db.execute('SELECT COUNT(*) FROM catalog_candidates').fetchone()[0]
        rows = db.execute('SELECT payload FROM catalog_candidates ORDER BY updated_at DESC, id LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [json.loads(row[0]) for row in rows]}


def get_candidate(identifier):
    with connection() as db:
        row = db.execute('SELECT payload FROM catalog_candidates WHERE id = ?', (identifier,)).fetchone()
        revisions = db.execute('SELECT revision, observed_at FROM catalog_revisions WHERE candidate_id = ? ORDER BY observed_at', (identifier,)).fetchall()
    return {'candidate': json.loads(row[0]), 'revisions': [{'revision': revision, 'observed_at': observed_at} for revision, observed_at in revisions]} if row else None
