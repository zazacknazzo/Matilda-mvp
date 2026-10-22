"""T09 test-only fixtures; no scientific retrieval, SDK or production storage."""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path

from app.schemas.lesson import LessonBundle, LessonGenerationMetadata
from app.schemas.models import Concept, DiscoveryMatch, Paper
from app.schemas.studio import EnrichmentPreview, GenerateRequest
from app.services.studio.generation import GenerationService
from app.services.studio.generation_repository import IsolatedGenerationRepository
from app.services.studio.lesson_validator import ScientificAuthority
from app.studio.ports import ProviderFailure, ProviderResult

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'tests/fixtures/studio'


def load(path):
    return json.loads((FIXTURES / path).read_text(encoding='utf8'))


def preview(name='text'):
    return EnrichmentPreview.model_validate(load(f'api/{name}-preview.json'))


def authority(name='text'):
    # Independent gold fixtures, not the preview/provider payload under test.
    gold = preview(name)
    scientific = load('scientific/' + {'text': 'text', 'rna': 'rna', 'no-coverage': 'uncovered-text'}[name] + '.json')
    concepts = json.loads((ROOT / 'data/concepts.json').read_text(encoding='utf8'))
    return ScientificAuthority(
        matches=[DiscoveryMatch.model_validate(item) for item in scientific['expected_matches']],
        references={item.id: item for item in gold.evidence_references},
        concepts=[Concept.model_validate(item) for item in concepts],
        papers=[Paper.model_validate(item) for item in scientific['papers']],
    )


def draft(name='crispr-50'):
    bundle = LessonBundle.model_validate(load(f'lessons/{name}.json'))
    sections = {item.id: f'section-{i}' for i, item in enumerate(bundle.sections)}
    slides = {item.id: f'slide-{i}' for i, item in enumerate(bundle.slides)}
    activities = {item.id: f'activity-{i}' for i, item in enumerate(bundle.activities)}
    return {
        'prior_knowledge': bundle.metadata.prior_knowledge, 'materials': bundle.metadata.materials,
        'sections': [{**item.model_dump(exclude={'id', 'slide_ids', 'activity_ids'}), 'key': sections[item.id],
                      'slide_keys': [slides[key] for key in item.slide_ids], 'activity_keys': [activities[key] for key in item.activity_ids]}
                     for item in bundle.sections],
        'slides': [{**item.model_dump(exclude={'id', 'section_id', 'evidence_ids', 'contribution_ids'}),
                    'key': slides[item.id], 'section_key': sections[item.section_id]} for item in bundle.slides],
        'activities': [{**item.model_dump(exclude={'id', 'section_id'}), 'key': activities[item.id], 'section_key': sections[item.section_id]} for item in bundle.activities],
        'limitations': ['Exemplo de provedor simulado; não é uma geração real.'],
    }


def request_for(value):
    return GenerateRequest(preview_id=value.preview_id, review_revision=value.review_revision,
                           accepted_suggestion_ids=[item.id for item in value.suggestions if item.status == 'accepted'])


class Clock:
    def __init__(self):
        self.stamp = datetime.fromisoformat('2026-10-21T12:20:00+00:00')
        self.ticks = 100.0

    def advance(self, seconds):
        self.stamp += timedelta(seconds=seconds)
        self.ticks += seconds

    def now(self):
        return self.stamp.isoformat()

    def monotonic(self):
        return self.ticks


class Provider:
    def __init__(self, payload=None, *, reason=None, tokens=400, clock=None, elapsed=0):
        self.payload = draft() if payload is None else payload
        self.reason, self.tokens, self.clock, self.elapsed = reason, tokens, clock, elapsed
        self.requests = []
        self.counts = []
        self.started = asyncio.Event()
        self.release = None

    async def count_input_tokens(self, request):
        self.counts.append(request)
        return self.tokens

    async def complete(self, request):
        self.requests.append(request)
        self.started.set()
        if self.release is not None:
            await self.release.wait()
        if self.clock:
            self.clock.advance(self.elapsed)
        if self.reason:
            raise ProviderFailure(self.reason)
        payload = self.payload(request) if callable(self.payload) else self.payload
        content = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode('utf8')
        return ProviderResult(content, LessonGenerationMetadata(
            provider='fixture', model='not-generated', prompt_version=request.prompt_version, schema_version=1,
            generated_at='2026-10-21T12:20:00Z', duration_ms=0, input_tokens=400, output_tokens=800,
        ))


def setup(tmp_path, *, name='text', provider=None, value=None, clock=None):
    value = value or preview(name)
    clock = clock or Clock()
    repository = IsolatedGenerationRepository(tmp_path / 'generation.sqlite')
    repository.store_reference_preview(session_id='owner', preview=value)
    provider = provider or Provider()
    service = GenerationService(repository, provider, lambda _: authority(name), now=clock.now, monotonic_clock=clock.monotonic)
    return service, repository, provider, value, clock
