"""Manual real-provider smoke. Requires explicit permission for paid Gemini calls.

After approval: python -X utf8 scripts/smoke_studio_t10.py --allow-paid-gemini
No mocks or seed; separate SQLite; output contains only IDs and safe metrics.
"""
import argparse
import json
import os
import logging
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid-gemini', action='store_true', help='Confirm permission to send the CRISPR example to Gemini and incur API usage.')
    parser.add_argument('--scenario', choices=('crispr', 'rna'), default='crispr')
    parser.add_argument('--preview-only', action='store_true', help='Measure the real preview without generating a lesson.')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    options = parser.parse_args()
    if not options.allow_paid_gemini:
        print('Ensaio não executado: requer autorização explícita para chamadas Gemini cobradas.')
        return 2
    from dotenv import load_dotenv
    load_dotenv(options.env_file)
    if not os.getenv('GEMINI_API_KEY', '').strip():
        print('Ensaio não executado: GEMINI_API_KEY ausente no backend.')
        return 2
    os.environ['MATILDA_DB'] = str(ROOT / '.runtime' / 'studio-t13-smoke.sqlite')
    # Known real snapshots, explicitly dated cache. No separate paid source calls.
    os.environ['MATILDA_CACHE_TTL'] = '999999999'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.schemas.lesson import LessonBundle
    from app.api.studio_preview import get_provider
    from app.integrations.gemini_client import GeminiProvider
    from app.studio.ports import ProviderFailure

    class BudgetedProvider(GeminiProvider):
        def __init__(self):
            super().__init__()
            self.calls = {'preview': 0, 'lesson': 0}

        async def complete(self, request):
            # Per invocation: at most 2 real preview calls and 1 lesson call.
            limit = 2 if request.stage == 'preview' else 1
            if self.calls[request.stage] >= limit:
                raise ProviderFailure('unavailable')
            self.calls[request.stage] += 1
            return await super().complete(request)

    class StageRecorder(logging.Handler):
        def __init__(self):
            super().__init__()
            self.events = []

        def emit(self, record):
            message = record.getMessage()
            if message.startswith('studio_stage '):
                self.events.append(json.loads(message.removeprefix('studio_stage ')))

    recorder = StageRecorder()
    logger = logging.getLogger('matilda.studio.timings')
    logger.addHandler(recorder)
    provider = BudgetedProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    scenario = {
        'crispr': ('Edição genética com CRISPR-Cas9', '10.1126/science.1231143', 'CRISPR-Cas9 permite discutir edição genética, reconhecimento do DNA por RNA guia e clivagem da molécula.'),
        'rna': ('RNA mensageiro e imunidade', '10.1056/NEJMoa2034577', 'RNA mensageiro e modificação de nucleosídeos permitem discutir reconhecimento imune e produção de proteínas.'),
    }[options.scenario]
    origin = {'Origin': 'http://localhost:5173'}
    started = monotonic()
    with TestClient(app) as client:
        response = client.post('/api/studio/preview', headers=origin, json={
            'title': scenario[0], 'duration_minutes': 50, 'doi': scenario[1], 'material_text': scenario[2],
        })
        if response.status_code != 201:
            return report_failure(response, 'preview', recorder.events, provider.calls)
        preview = response.json()
        if options.preview_only:
            print(json.dumps({'status': 'preview_passed', 'scenario': options.scenario, 'preview_id': preview['preview_id'],
                'preview_metadata': preview['generation_metadata'], 'stages': recorder.events, 'provider_calls': provider.calls,
                'total_seconds': round(monotonic() - started, 3)}, ensure_ascii=False))
            return 0
        response = client.post(f"/api/studio/previews/{preview['preview_id']}/review", headers=origin, json={
            'review_revision': preview['review_revision'], 'approved_objectives': ['Explicar o mecanismo molecular e conferir as fontes documentais.'],
            'decisions': [{'suggestion_id': item['id'], 'status': 'accepted' if index == 0 else 'rejected'} for index, item in enumerate(preview['suggestions'])],
        })
        if response.status_code != 200:
            return report_failure(response, 'review', recorder.events, provider.calls)
        reviewed = response.json()
        from uuid import uuid4
        response = client.post('/api/studio/generate', headers={**origin, 'Idempotency-Key': str(uuid4())}, json={
            'preview_id': reviewed['preview_id'], 'review_revision': reviewed['review_revision'],
            'accepted_suggestion_ids': [item['id'] for item in reviewed['suggestions'] if item['status'] == 'accepted'],
        })
        if response.status_code != 201:
            return report_failure(response, 'generation', recorder.events, provider.calls)
        bundle = LessonBundle.model_validate(response.json())
        recovered = client.get('/api/studio/lessons/' + bundle.lesson_bundle_id)
        if recovered.status_code != 200 or recovered.json() != response.json():
            return report_failure(recovered, 'read', recorder.events, provider.calls)
        exported = client.get('/api/studio/lessons/' + bundle.lesson_bundle_id + '/export?format=markdown')
        if exported.status_code != 200:
            return report_failure(exported, 'export', recorder.events, provider.calls)
        print(json.dumps({'status': 'passed', 'preview_id': preview['preview_id'], 'lesson_bundle_id': bundle.lesson_bundle_id,
            'preview_metadata': preview['generation_metadata'], 'lesson_metadata': bundle.generation_metadata.model_dump(),
            'scenario': options.scenario, 'stages': recorder.events, 'provider_calls': provider.calls,
            'scientific_sources': 'dated_cache', 'export_status': exported.status_code,
            'total_seconds': round(monotonic() - started, 3), 'slides': len(bundle.slides), 'sections': len(bundle.sections)}, ensure_ascii=False))
    return 0


def report_failure(response, stage, timings=None, calls=None):
    print(json.dumps({'status': 'failed', 'stage': stage, 'http': response.status_code,
        'code': response.json().get('code'), 'stages': timings, 'provider_calls': calls}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
