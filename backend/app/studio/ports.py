"""T03 ports. Implementations must obey docs/studio-contracts.md atomically.

No provider SDK, key lookup, SQL, locks or network calls belong in this module.
Provider doubles live only in tests; no fixture is a production success fallback.
"""
from dataclasses import dataclass
from typing import Literal, Mapping, Protocol

from pydantic import JsonValue

from app.schemas.lesson import LessonBundle, LessonGenerationMetadata
from app.schemas.scientific_context import SourceDocument
from app.schemas.studio import (
    EnrichmentPreview, GenerateRequest, LessonProject, PreviewRequest, ReviewRequest, StudioError,
)


@dataclass(frozen=True)
class StudioPolicy:
    retention_days: int = 7
    preview_backend_seconds: int = 45
    generation_backend_seconds: int = 75
    preview_client_seconds: int = 55
    generation_client_seconds: int = 85
    minimum_proxy_seconds: int = 100
    recovery_grace_seconds: int = 15
    persistence_reserve_seconds: int = 5
    max_body_bytes: int = 128 * 1024
    max_input_tokens: int = 12000
    max_output_tokens: int = 8000
    max_provider_attempts: int = 2
    session_concurrency: int = 1
    global_concurrency: int = 2
    previews_per_hour: int = 5
    generations_per_hour: int = 5


POLICY = StudioPolicy()
SESSION_COOKIE = 'matilda_studio_session'


@dataclass(frozen=True)
class ProviderRequest:
    """Trusted instructions/schema and untrusted material in separate fields.

    deadline is absolute monotonic time shared by attempts; no new full timeout.
    output schema is supplied by T09 and uses local component keys, not final IDs.
    Adapters disable tools/browser/code and account for tokens before generation.
    """
    stage: Literal['preview', 'lesson']
    system_instruction: str
    material: Mapping[str, JsonValue]
    response_schema: Mapping[str, JsonValue]
    deadline: float
    prompt_version: str
    max_input_tokens: int = POLICY.max_input_tokens
    max_output_tokens: int = POLICY.max_output_tokens


@dataclass(frozen=True)
class ProviderResult:
    """Untrusted UTF-8 JSON, bounded before parsing; incomplete output is an error."""
    content: bytes
    metadata: LessonGenerationMetadata


class ProviderFailure(Exception):
    """Sanitized failure, without raw prompt, key or upstream error text."""
    def __init__(self, reason: Literal['timeout', 'rate_limited', 'unauthorized', 'blocked', 'truncated', 'unavailable']):
        if reason not in ('timeout', 'rate_limited', 'unauthorized', 'blocked', 'truncated', 'unavailable'):
            raise ValueError('Motivo de falha do provedor desconhecido.')
        self.reason = reason
        super().__init__(reason)


class StudioProvider(Protocol):
    async def count_input_tokens(self, request: ProviderRequest) -> int: ...
    async def complete(self, request: ProviderRequest) -> ProviderResult: ...


@dataclass(frozen=True)
class GenerationClaim:
    """A completed duplicate returns its existing bundle; otherwise claim_id owns work."""
    claim_id: str | None
    completed_bundle: LessonBundle | None

    def __post_init__(self):
        if (self.claim_id is None) == (self.completed_bundle is None) or (self.claim_id is not None and not self.claim_id.strip()):
            raise ValueError('Reclamação exige operação ativa ou aula concluída, exclusivamente.')


class RepositoryConflict(Exception):
    """An adapter must translate this safe envelope to the documented HTTP status."""
    def __init__(self, error: StudioError):
        self.error = error
        super().__init__(error.code)


class StudioRepository(Protocol):
    """All methods enforce ownership/expiry. now is an explicit UTC timestamp.

    save_material/save_review/claim_generation admit/renew atomically. Reads,
    publication, completion and failure never add a second renewal.
    Claiming and finalizing never hold a DB transaction across the provider call.
    See the contract document for exact quota/retry/cleanup guarantees.
    """
    async def save_material(self, *, session_id: str, project: LessonProject, request: PreviewRequest, documents: list[SourceDocument], now: str) -> None: ...
    async def publish_preview(self, *, session_id: str, preview: EnrichmentPreview, now: str) -> None: ...
    async def fail_preview(self, *, session_id: str, project_id: str, error: StudioError, now: str) -> None: ...
    async def get_preview(self, *, session_id: str, preview_id: str, now: str) -> EnrichmentPreview | None: ...
    async def save_review(self, *, session_id: str, preview_id: str, review: ReviewRequest, now: str) -> EnrichmentPreview: ...
    async def claim_generation(self, *, session_id: str, request: GenerateRequest, idempotency_key: str, now: str) -> GenerationClaim: ...
    async def complete_generation(self, *, claim_id: str, bundle: LessonBundle, now: str) -> LessonBundle: ...
    async def fail_generation(self, *, claim_id: str, error: StudioError, now: str) -> None: ...
    async def get_lesson(self, *, session_id: str, lesson_bundle_id: str, now: str) -> LessonBundle | None: ...
    async def cleanup_expired(self, *, now: str) -> int: ...
