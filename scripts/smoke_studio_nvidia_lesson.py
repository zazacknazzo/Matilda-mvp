"""Lesson-only NVIDIA smoke: simulated preparation, one real inference, 100 s total.

Does not prove the full live flow. Requires explicit authorization; no paid retry.
"""
import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT)]
from app.integrations.nvidia_client import NVIDIAProvider, DEFAULT_MODEL, DEFAULT_BASE_URL
from app.services.studio.repository import conflict
from scripts.smoke_studio_nvidia import Recorder, SmokeFailure

MAX_SECONDS = 100


class SingleCallNVIDIA(NVIDIAProvider):
    def __init__(self, *, transport=None):
        super().__init__(transport=transport)
        self.calls = 0

    @property
    def model(self):
        return DEFAULT_MODEL

    async def complete(self, request):
        if request.stage != 'lesson' or self.calls >= 1:
            raise conflict('invalid_generation', 'Limite de uma inferência lesson atingido; nenhuma nova chamada foi iniciada.')
        self.calls += 1
        return await super().complete(request)


class SimulatedPreparation:
    """Only pedagogy is simulated; canonical source resolution/authority runs normally."""
    async def count_input_tokens(self, request):
        return 400

    async def complete(self, request):
        from app.schemas.lesson import LessonGenerationMetadata
        from app.studio.ports import ProviderResult
        if request.stage != 'preview':
            raise ValueError('Preparação simulada não gera aula.')
        candidates = request.material['scientific_candidates']
        suggestions = [{'candidate_id': candidates[0]['id'],
            'pedagogical_rationale': 'Comparar o mecanismo e a documentação científica.',
            'suggested_content': 'Examine o mecanismo descrito no material e confira a documentação.'}] if candidates else []
        return ProviderResult(json.dumps({'suggested_objectives': ['Explicar o mecanismo molecular e conferir as fontes.'],
            'suggestions': suggestions}).encode(), LessonGenerationMetadata(
                provider='simulated-preparation', model='deterministic-selection', prompt_version=request.prompt_version,
                schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(), duration_ms=0,
                input_tokens=0, output_tokens=0))


def run_lesson_smoke(provider, *, scenario='crispr'):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.studio_preview import get_provider
    from app.schemas.studio import EnrichmentPreview
    from app.schemas.lesson import LessonBundle
    recorder = Recorder()
    loggers = [logging.getLogger(name) for name in ('matilda.studio.nvidia', 'matilda.studio.timings', 'matilda.studio.validation')]
    previous = [(logger.level, logger.propagate) for logger in loggers]
    before = app.dependency_overrides.copy()
    for logger in loggers:
        logger.addHandler(recorder)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    report = {'status': 'failed', 'scope': 'lesson_only', 'preparation_simulated': True,
              'full_flow_proven': False, 'max_external_calls': 1, 'max_seconds': MAX_SECONDS, 'steps': []}
    started, stage = monotonic(), 'startup'

    def step(client, method, path, name, expected, **kwargs):
        nonlocal stage
        stage, tick = name, monotonic()
        response = getattr(client, method)(path, **kwargs)
        report['steps'].append({'stage': name, 'http_status': response.status_code,
                                'duration_ms': round((monotonic() - tick) * 1000, 3)})
        if response.status_code != expected:
            try:
                code = response.json().get('code')
            except (ValueError, AttributeError):
                code = None
            report['code'] = code if code in {'invalid_input', 'input_too_large', 'not_found', 'review_conflict',
                'generation_in_progress', 'session_limit', 'invalid_generation', 'generation_timeout',
                'studio_not_configured', 'provider_unavailable'} else 'unexpected_response'
            raise SmokeFailure()
        return response

    try:
        source = {
            'crispr': ('10.1126/science.1231143', 'CRISPR-Cas9 permite discutir edição genética e clivagem do DNA.'),
            'rna': ('10.1056/NEJMoa2034577', 'RNA mensageiro e modificação de nucleosídeos permitem discutir imunidade.'),
        }[scenario]
        app.dependency_overrides[get_provider] = lambda: SimulatedPreparation()
        with TestClient(app) as client:
            origin = {'Origin': 'http://localhost:5173'}
            response = step(client, 'post', '/api/studio/preview', 'preparation', 201, headers=origin,
                json={'title': 'Mecanismo molecular e fontes', 'duration_minutes': 50, 'doi': source[0], 'material_text': source[1]})
            preview = EnrichmentPreview.model_validate(response.json())
            if not preview.suggestions:
                raise SmokeFailure()
            report['steps'][-1].update(simulated=True, json_validated=True, suggestions=len(preview.suggestions),
                                      provider=preview.generation_metadata.provider)
            saved = step(client, 'post', f'/api/studio/previews/{preview.preview_id}/review', 'review', 200, headers=origin,
                json={'review_revision': preview.review_revision, 'approved_objectives': preview.suggested_objectives,
                      'decisions': [{'suggestion_id': s.id, 'status': 'accepted'} for s in preview.suggestions]}).json()
            app.dependency_overrides[get_provider] = lambda: provider
            generation = {'preview_id': saved['preview_id'], 'review_revision': saved['review_revision'],
                          'accepted_suggestion_ids': [s['id'] for s in saved['suggestions'] if s['status'] == 'accepted']}
            headers = {**origin, 'Idempotency-Key': str(uuid4())}
            generated = step(client, 'post', '/api/studio/generate', 'lesson', 201, headers=headers, json=generation)
            bundle = LessonBundle.model_validate(generated.json())
            if bundle.metadata.duration_minutes != 50 or not bundle.references:
                raise SmokeFailure()
            report['steps'][-1].update(json_validated=True, metadata=bundle.generation_metadata.model_dump(),
                                      slides=len(bundle.slides), sections=len(bundle.sections), activities=len(bundle.activities))
            path = '/api/studio/lessons/' + bundle.lesson_bundle_id
            read = step(client, 'get', path, 'read', 200)
            replay = step(client, 'post', '/api/studio/generate', 'replay', 200, headers=headers, json=generation)
            if read.json() != generated.json() or replay.json() != generated.json():
                report['code'] = 'persistence_mismatch'
                raise SmokeFailure()
            exported = step(client, 'get', path + '/export?format=markdown', 'markdown', 200)
            if not exported.content or 'attachment' not in exported.headers.get('content-disposition', ''):
                raise SmokeFailure()
            report.update(status='passed', lesson_bundle_id=bundle.lesson_bundle_id)
    except SmokeFailure:
        report.update(failed_stage=stage)
        report.setdefault('code', 'invalid_generation')
    except Exception:
        report.update(failed_stage=stage, code='unexpected_error')
    finally:
        report.update(events=recorder.events, total_seconds=round(monotonic() - started, 3), external_calls_reserved=provider.calls)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)
        for logger, (level, propagate) in zip(loggers, previous):
            logger.removeHandler(recorder)
            logger.setLevel(level)
            logger.propagate = propagate
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid-nvidia', action='store_true', help='Autorizar uma chamada NVIDIA real somente para lesson, limite total 100 s.')
    parser.add_argument('--scenario', choices=('crispr', 'rna'), default='crispr')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    options = parser.parse_args()
    if not options.allow_paid_nvidia:
        print(json.dumps({'status': 'not_run', 'code': 'explicit_authorization_required', 'max_calls': 1, 'max_seconds': MAX_SECONDS}))
        return 2
    if not options.worker:
        try:
            worker = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', '--allow-paid-nvidia',
                '--scenario', options.scenario, '--env-file', str(options.env_file.resolve())],
                timeout=MAX_SECONDS, capture_output=True, text=True, check=False)
            print(json.dumps(json.loads(worker.stdout), ensure_ascii=False))
            return worker.returncode
        except subprocess.TimeoutExpired:
            print(json.dumps({'status': 'failed', 'code': 'execution_limit', 'max_calls': 1, 'max_seconds': MAX_SECONDS}))
        except (OSError, ValueError):
            print(json.dumps({'status': 'failed', 'code': 'worker_failure'}))
        return 1
    from dotenv import load_dotenv
    load_dotenv(options.env_file)
    if not os.getenv('NVIDIA_API_KEY', '').strip():
        print(json.dumps({'status': 'not_run', 'code': 'nvidia_key_missing'}))
        return 2
    os.environ.update(AI_PROVIDER='nvidia', NVIDIA_BASE_URL=DEFAULT_BASE_URL,
        MATILDA_DB=str(ROOT / '.runtime' / ('nvidia-lesson-smoke-' + str(uuid4()) + '.sqlite')),
        MATILDA_CACHE_TTL='999999999', MATILDA_CORS_ORIGINS='http://localhost:5173')
    report = run_lesson_smoke(SingleCallNVIDIA(), scenario=options.scenario)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
