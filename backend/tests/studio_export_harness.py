"""T11 test/development HTTP host only. No real session, database or generation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
import uvicorn

from app.api.studio_exports import create_export_router
from app.schemas.lesson import LessonBundle


FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/lessons'


class FixtureRepository:
    async def get_lesson(self, *, session_id, lesson_bundle_id, now):
        for name in ('crispr-50', 'rna-50', 'no-enrichment-50', 'optional-fields'):
            path = FIXTURES / f'{name}.json'
            bundle = LessonBundle.model_validate_json(path.read_bytes())
            if bundle.lesson_bundle_id == lesson_bundle_id:
                return bundle
        return None


async def fixture_session(request):
    # Explicit test substitute. Never register this resolver in the product host.
    return 'fixture-owner'


app = FastAPI(title='EXEMPLO T11 — autorização e repositório simulados')
app.include_router(create_export_router(FixtureRepository(), fixture_session, clock=lambda: '2026-10-21T12:00:00Z'))


@app.get('/healthz')
def health():
    return {'test_harness': True}


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8001)
