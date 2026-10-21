"""T11 isolated router factory. T13 registers it with real session/repository adapters.

Importing this module does not install routes in the Forensics app.
"""
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.schemas.studio import ExportQuery, StudioError
from app.services.studio.lesson_export import export_filename, lesson_markdown
from app.studio.ports import StudioRepository


SessionResolver = Callable[[Request], Awaitable[str | None]]


def create_export_router(
    repository: StudioRepository,
    resolve_session: SessionResolver,
    *,
    clock: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat(),
) -> APIRouter:
    router = APIRouter()

    def error(status: int, code: str, detail: str) -> JSONResponse:
        envelope = StudioError(code=code, detail=detail, retryable=False)
        return JSONResponse(status_code=status, content=envelope.model_dump(), headers={'Cache-Control': 'no-store, private'})

    @router.get('/api/studio/lessons/{lesson_bundle_id}/export')
    async def export_lesson(lesson_bundle_id: str, request: Request):
        try:
            pairs = list(request.query_params.multi_items())
            if len(pairs) != len(dict(pairs)):
                raise ValueError('Repeated query.')
            ExportQuery.model_validate(dict(pairs))
        except (ValidationError, ValueError):
            return error(422, 'invalid_input', 'Formato ou parâmetros de exportação inválidos.')
        session_id = await resolve_session(request)
        if not session_id:
            return error(404, 'not_found', 'Aula indisponível.')
        # T03 get_lesson checks ownership and expiry at this explicit instant.
        # This read never calls a provider, renews retention or sets a cookie.
        bundle = await repository.get_lesson(session_id=session_id, lesson_bundle_id=lesson_bundle_id, now=clock())
        if bundle is None or bundle.lesson_bundle_id != lesson_bundle_id:
            return error(404, 'not_found', 'Aula indisponível.')
        try:
            content = lesson_markdown(bundle)
        except (ValidationError, ValueError, KeyError):
            return error(502, 'invalid_generation', 'Aula inválida para exportação.')
        return Response(content, media_type='text/markdown', headers={
            'Content-Disposition': f'attachment; filename="{export_filename(bundle.lesson_bundle_id)}"',
            'Cache-Control': 'no-store, private',
            'X-Content-Type-Options': 'nosniff',
        })

    return router
