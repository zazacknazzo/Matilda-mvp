"""Test-only provider transport. Never imported by app/ or selected in production."""
from app.schemas.lesson import LessonGenerationMetadata
from app.studio.ports import ProviderFailure, ProviderRequest, ProviderResult


class RecordedStudioProvider:
    def __init__(self, case):
        self.case = case

    async def count_input_tokens(self, request: ProviderRequest) -> int:
        return 100  # Declared fixture count, never an estimate for real material.

    async def complete(self, request: ProviderRequest) -> ProviderResult:
        if self.case['reason'] is not None:
            raise ProviderFailure(self.case['reason'])
        return ProviderResult(
            content=self.case['content'].encode('utf-8'),
            metadata=LessonGenerationMetadata(
                provider='fixture', model='not-generated', prompt_version=request.prompt_version,
                schema_version=1, generated_at='2026-10-21T12:00:00Z', duration_ms=0,
                input_tokens=100, output_tokens=10,
            ),
        )
