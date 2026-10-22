"""Explicit T09 development host: simulated provider and reference reviews only."""
import asyncio
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from app.api.studio_generation import create_generation_router
from app.services.studio.generation import GenerationService
from app.services.studio.generation_repository import IsolatedGenerationRepository
from app.services.studio.operations import studio_maintenance_lifespan
from app.schemas.studio import GenerateRequest
from app.studio.ports import ProviderFailure
from generation_fixtures import Clock, Provider, authority, draft, preview

runtime = tempfile.TemporaryDirectory(prefix='matilda-t09-')
repo = IsolatedGenerationRepository(Path(runtime.name) / 'generation.db')
clock = Clock()


class ScenarioProvider:
    def __init__(self):
        self.calls = 0

    async def count_input_tokens(self, request):
        return 400

    async def complete(self, request):
        self.calls += 1
        case = request.material['configuration']['title'].rsplit(' / ', 1)[-1]
        if case in ('timeout', 'unauthorized'):
            raise ProviderFailure(case)
        if case == 'slow':
            await asyncio.sleep(0.3)
        return await Provider(b'{invalid' if case == 'invalid' else draft('no-enrichment-50' if case == 'empty' else 'crispr-50')).complete(request)


provider = ScenarioProvider()
service = GenerationService(repo, provider, lambda value: authority('no-coverage' if value.preview_id == 'preview-empty' else 'text'), now=clock.now)


def reset():
    fresh = Clock()
    clock.stamp, clock.ticks = fresh.stamp, fresh.ticks
    with repo.transaction() as db:
        for table in ('t09_operations', 't09_bundles', 't09_previews', 't09_usage', 't09_sessions'):
            db.execute(f'DELETE FROM {table}')
    provider.calls = 0
    for case in ('success', 'invalid', 'timeout', 'unauthorized', 'slow', 'empty', 'pending'):
        value = preview('no-coverage' if case == 'empty' else 'pending' if case == 'pending' else 'text')
        value.preview_id = f'preview-{case}'
        value.project.title += ' / ' + case
        repo.store_reference_preview(session_id='fixture-owner', preview=value)


reset()
app = FastAPI(title='EXEMPLO T09/T12 — provedor, sessão e revisões simulados',
              lifespan=studio_maintenance_lifespan(repo, now=clock.now, metrics=service.metrics))


async def session(request):
    return 'fixture-owner'


app.include_router(create_generation_router(service, session, lambda *_: None,
                   trusted_origins=frozenset({'http://127.0.0.1:5177'})))


@app.get('/api/studio/previews/{identifier}')
async def get_preview(identifier: str):
    value = await repo.get_preview(session_id='fixture-owner', preview_id=identifier, now=clock.now())
    return JSONResponse(value.model_dump()) if value else JSONResponse({'code': 'not_found'}, status_code=404)


@app.post('/test/reset')
def reset_test():
    reset()
    return {'test_only': True}


@app.get('/test/stats')
def stats():
    return {'provider_calls': provider.calls}


@app.post('/test/interrupt')
async def interrupt(body: dict):
    """Controlled process-loss scenario, never imported by the product host."""
    global repo
    await repo.claim_generation(session_id='fixture-owner', request=GenerateRequest.model_validate(body['request']),
                                idempotency_key=body['key'], now=clock.now())
    repo = IsolatedGenerationRepository(repo.path)
    service.repository = repo
    return {'test_only': True}


@app.post('/test/advance')
def advance(body: dict):
    clock.advance(body['seconds'])
    return {'test_only': True}


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8017)
