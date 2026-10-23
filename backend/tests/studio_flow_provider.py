"""External provider substitute ONLY. HTTP, science, SQLite and validators stay real."""
import json
from datetime import datetime, timezone

from test_studio_preview import PreviewProvider
from generation_fixtures import draft
from app.schemas.lesson import LessonGenerationMetadata
from app.studio.ports import ProviderResult


class FlowProvider(PreviewProvider):
    def __init__(self):
        super().__init__()
        self.lesson_requests = []
        self.poison = False
        self.tokens = 400
        self.failure = None
        self.before_lesson = None

    async def count_input_tokens(self, request):
        return self.tokens

    async def complete(self, request):
        if self.failure:
            raise self.failure
        if request.stage == 'preview':
            result = await super().complete(request)
            value = json.loads(result.content)
            candidates = request.material['scientific_candidates']
            if len(candidates) > 1:
                item = dict(value['suggestions'][0])
                item.update(candidate_id=candidates[1]['id'])
                value['suggestions'].append(item)
            return ProviderResult(json.dumps(value).encode(), result.metadata)
        self.lesson_requests.append(request)
        if self.before_lesson:
            self.before_lesson()
        value = draft('no-enrichment-50')
        for section in value['sections']:
            section['objective_indexes'] = [0]
        for activity in value['activities']:
            activity['objective_indexes'] = [0]
        allowed = list(request.material['authorized_evidence'])
        if allowed or self.poison:
            claim = {'type': 'evidence_claim', 'evidence_id': 'forbidden-id' if self.poison else allowed[0]}
            value['sections'][0]['explanation_blocks'].append(claim)
            value['slides'][0]['content_blocks'].append(claim)
        return ProviderResult(json.dumps(value).encode(), LessonGenerationMetadata(
            provider='external-test-only', model='controlled', prompt_version=request.prompt_version,
            schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=1, input_tokens=400, output_tokens=800))
