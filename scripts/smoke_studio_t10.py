"""Manual real-provider smoke. Requires explicit permission for paid Gemini calls.

After approval: python -X utf8 scripts/smoke_studio_t10.py --allow-paid-gemini
No mocks or seed; separate SQLite; output contains only IDs and safe metrics.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid-gemini', action='store_true', help='Confirm permission to send the CRISPR example to Gemini and incur API usage.')
    options = parser.parse_args()
    if not options.allow_paid_gemini:
        print('Ensaio não executado: requer autorização explícita para chamadas Gemini cobradas.')
        return 2
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    if not os.getenv('GEMINI_API_KEY', '').strip():
        print('Ensaio não executado: GEMINI_API_KEY ausente no backend.')
        return 2
    os.environ['MATILDA_DB'] = str(ROOT / '.runtime' / 'studio-t10-smoke.sqlite')
    from fastapi.testclient import TestClient
    from app.main import app
    from app.schemas.lesson import LessonBundle
    origin = {'Origin': 'http://localhost:5173'}
    started = monotonic()
    with TestClient(app) as client:
        response = client.post('/api/studio/preview', headers=origin, json={
            'title': 'Edição genética com CRISPR-Cas9', 'duration_minutes': 50, 'concepts': ['CRISPR-Cas9'],
            'material_text': 'CRISPR-Cas9 permite discutir edição genética, reconhecimento do DNA por RNA guia e clivagem da molécula. Relacione mecanismos moleculares e evidências documentais.',
        })
        if response.status_code != 201:
            return report_failure(response, 'preview')
        preview = response.json()
        response = client.post(f"/api/studio/previews/{preview['preview_id']}/review", headers=origin, json={
            'review_revision': preview['review_revision'], 'approved_objectives': ['Explicar o mecanismo de edição genética por CRISPR-Cas9.'],
            'decisions': [{'suggestion_id': item['id'], 'status': 'accepted' if index == 0 else 'rejected'} for index, item in enumerate(preview['suggestions'])],
        })
        if response.status_code != 200:
            return report_failure(response, 'review')
        reviewed = response.json()
        from uuid import uuid4
        response = client.post('/api/studio/generate', headers={**origin, 'Idempotency-Key': str(uuid4())}, json={
            'preview_id': reviewed['preview_id'], 'review_revision': reviewed['review_revision'],
            'accepted_suggestion_ids': [item['id'] for item in reviewed['suggestions'] if item['status'] == 'accepted'],
        })
        if response.status_code != 201:
            return report_failure(response, 'generation')
        bundle = LessonBundle.model_validate(response.json())
        recovered = client.get('/api/studio/lessons/' + bundle.lesson_bundle_id)
        if recovered.status_code != 200 or recovered.json() != response.json():
            return report_failure(recovered, 'read')
        print(json.dumps({'status': 'passed', 'preview_id': preview['preview_id'], 'lesson_bundle_id': bundle.lesson_bundle_id,
            'preview_metadata': preview['generation_metadata'], 'lesson_metadata': bundle.generation_metadata.model_dump(),
            'total_seconds': round(monotonic() - started, 3), 'slides': len(bundle.slides), 'sections': len(bundle.sections)}, ensure_ascii=False))
    return 0


def report_failure(response, stage):
    print(json.dumps({'status': 'failed', 'stage': stage, 'http': response.status_code, 'code': response.json().get('code')}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
