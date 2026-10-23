"""NVIDIA live smoke: explicit consent, at most 3 calls, hard 180-second process limit.

Two scientific previews and one 50-minute lesson with persisted read/Markdown.
Never run this as evidence of production readiness without a successful live report.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
MAX_CALLS = 3
MAX_SECONDS = 180


from app.integrations.nvidia_client import NVIDIAProvider, DEFAULT_MODEL
from app.services.studio.repository import conflict


class BudgetedNVIDIA(NVIDIAProvider):
    def __init__(self, *, transport=None):
        super().__init__(transport=transport)
        self.calls = 0
        self.operations = set()

    @property
    def model(self):
        # A smoke authorization is scoped to this exact requested model.
        return DEFAULT_MODEL

    async def complete(self, request):
        operation = (request.stage, request.deadline)
        # One attempt per operation. No silent paid correction/retry in smoke.
        if self.calls >= MAX_CALLS or operation in self.operations:
            raise conflict('invalid_generation', 'Limite de chamadas do ensaio atingido.', retryable=False)
        self.operations.add(operation)
        self.calls += 1
        return await super().complete(request)

class Recorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        message = record.getMessage()
        for prefix in ('nvidia_attempt ', 'nvidia_lesson_quality ', 'studio_stage ', 'studio_preview_validation ', 'studio_lesson_validation '):
            if message.startswith(prefix):
                self.events.append({'type': prefix.strip(), **json.loads(message[len(prefix):])})
                break
        if message.startswith('studio_validation '):
            # Only the fixed classification is captured, never exception text.
            self.events.append({'type': 'studio_validation', 'outcome':
                'pydantic_validation' if 'pydantic_validation' in message else 'scientific_validation'})


def run_smoke(provider, *, lesson_scenario='crispr'):
    """Run real public HTTP and SQLite; provider injection is only for offline tests."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.studio_preview import get_provider
    from app.schemas.studio import EnrichmentPreview
    from app.schemas.lesson import LessonBundle

    recorder = Recorder()
    loggers = [logging.getLogger(name) for name in
               ('matilda.studio.nvidia', 'matilda.studio.timings', 'matilda.studio.validation')]
    previous = [(logger.level, logger.propagate) for logger in loggers]
    for logger in loggers:
        logger.addHandler(recorder)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    before = app.dependency_overrides.copy()
    app.dependency_overrides[get_provider] = lambda: provider
    started = monotonic()
    report = {'status': 'failed', 'scientific_sources': 'dated_cache', 'steps': [],
              'max_external_calls': MAX_CALLS, 'max_seconds': MAX_SECONDS}
    stage = 'startup'

    def step(client, method, path, *, name, expected, **kwargs):
        nonlocal stage
        stage = name
        tick = monotonic()
        response = getattr(client, method)(path, **kwargs)
        report['steps'].append({'stage': name, 'http_status': response.status_code,
                                'duration_ms': round((monotonic() - tick) * 1000)})
        if response.status_code != expected:
            try:
                code = response.json().get('code')
            except (ValueError, AttributeError):
                code = None
            allowed = {'invalid_input', 'input_too_large', 'not_found', 'review_conflict', 'generation_in_progress',
                       'session_limit', 'invalid_generation', 'generation_timeout', 'studio_not_configured', 'provider_unavailable'}
            report['code'] = code if code in allowed else 'unexpected_response'
            raise SmokeFailure()
        return response

    try:
        previews = {}
        origin = {'Origin': 'http://localhost:5173'}
        with TestClient(app) as client:
            scenarios = {
                'crispr': ('Edição genética com CRISPR-Cas9', '10.1126/science.1231143',
                           'CRISPR-Cas9 permite discutir edição genética, reconhecimento do DNA por RNA guia e clivagem da molécula.'),
                'rna': ('RNA mensageiro e imunidade', '10.1056/NEJMoa2034577',
                        'RNA mensageiro e modificação de nucleosídeos permitem discutir reconhecimento imune e produção de proteínas.'),
            }
            for name, (title, doi, material) in scenarios.items():
                result = step(client, 'post', '/api/studio/preview', name=name + '_preview', expected=201,
                              headers=origin, json={'title': title, 'duration_minutes': 50, 'doi': doi, 'material_text': material})
                preview = EnrichmentPreview.model_validate(result.json())
                if not preview.suggestions:
                    report['code'] = 'invalid_generation'
                    raise SmokeFailure()
                previews[name] = preview
                report['steps'][-1].update(json_validated=True, metadata=preview.generation_metadata.model_dump(),
                                          suggestions=len(preview.suggestions))
            preview = previews[lesson_scenario]
            reviewed = step(client, 'post', f'/api/studio/previews/{preview.preview_id}/review', name='review', expected=200,
                headers=origin, json={'review_revision': preview.review_revision,
                    'approved_objectives': ['Explicar o mecanismo molecular e conferir as fontes documentais.'],
                    'decisions': [{'suggestion_id': item.id, 'status': 'accepted' if index == 0 else 'rejected'}
                                  for index, item in enumerate(preview.suggestions)]}).json()
            response = step(client, 'post', '/api/studio/generate', name='lesson', expected=201,
                headers={**origin, 'Idempotency-Key': str(uuid4())}, json={
                    'preview_id': reviewed['preview_id'], 'review_revision': reviewed['review_revision'],
                    'accepted_suggestion_ids': [item['id'] for item in reviewed['suggestions'] if item['status'] == 'accepted']})
            bundle = LessonBundle.model_validate(response.json())
            if bundle.metadata.duration_minutes != 50 or not bundle.references:
                report['code'] = 'invalid_generation'
                raise SmokeFailure()
            report['steps'][-1].update(json_validated=True, metadata=bundle.generation_metadata.model_dump(),
                                      slides=len(bundle.slides), sections=len(bundle.sections))
            path = '/api/studio/lessons/' + bundle.lesson_bundle_id
            recovered = step(client, 'get', path, name='read', expected=200)
            if recovered.json() != response.json():
                report['code'] = 'persistence_mismatch'
                raise SmokeFailure()
            exported = step(client, 'get', path + '/export?format=markdown', name='markdown', expected=200)
            if not exported.content or 'attachment' not in exported.headers.get('content-disposition', ''):
                report['code'] = 'invalid_export'
                raise SmokeFailure()
            report.update(status='passed', lesson_scenario=lesson_scenario, lesson_bundle_id=bundle.lesson_bundle_id)
    except SmokeFailure:
        report['failed_stage'] = stage
    except Exception:
        # Do not print exception/response text; they may contain teacher material.
        report.update(failed_stage=stage, code='unexpected_error')
    finally:
        report.update(events=recorder.events, total_seconds=round(monotonic() - started, 3))
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)
        for logger, (level, propagate) in zip(loggers, previous):
            logger.removeHandler(recorder)
            logger.setLevel(level)
            logger.propagate = propagate
    return report


class SmokeFailure(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid-nvidia', action='store_true', help='Autorização explícita: até 3 chamadas NVIDIA, 180 s; material de exemplo.')
    parser.add_argument('--lesson-scenario', choices=('crispr', 'rna'), default='crispr')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    options = parser.parse_args()
    if not options.allow_paid_nvidia:
        print(json.dumps({'status': 'not_run', 'code': 'explicit_authorization_required', 'max_calls': MAX_CALLS, 'max_seconds': MAX_SECONDS}))
        return 2
    if not options.worker:
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', '--allow-paid-nvidia',
                '--lesson-scenario', options.lesson_scenario, '--env-file', str(options.env_file)],
                timeout=MAX_SECONDS, capture_output=True, text=True, check=False)
            # The worker emits only the allowlisted report. Never relay stderr.
            report = json.loads(result.stdout)
            print(json.dumps(report, ensure_ascii=False))
            return result.returncode
        except subprocess.TimeoutExpired:
            print(json.dumps({'status': 'failed', 'code': 'execution_limit', 'max_calls': MAX_CALLS, 'max_seconds': MAX_SECONDS}))
            return 1
        except (ValueError, OSError):
            print(json.dumps({'status': 'failed', 'code': 'worker_failure'}))
            return 1
    from dotenv import load_dotenv
    load_dotenv(options.env_file)
    if not os.getenv('NVIDIA_API_KEY', '').strip():
        print(json.dumps({'status': 'not_run', 'code': 'nvidia_key_missing'}))
        return 2
    os.environ['AI_PROVIDER'] = 'nvidia'
    os.environ['MATILDA_DB'] = str(ROOT / '.runtime' / ('nvidia-smoke-' + str(uuid4()) + '.sqlite'))
    os.environ['MATILDA_CACHE_TTL'] = '999999999'
    os.environ['MATILDA_CORS_ORIGINS'] = 'http://localhost:5173'


    provider = BudgetedNVIDIA()
    report = run_smoke(provider, lesson_scenario=options.lesson_scenario)
    report['external_calls'] = provider.calls
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
