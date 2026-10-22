"""T09 composable POST handler. Registration with production belongs to T10."""
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.schemas.studio import GenerateRequest, GenerationHeaders, validate_request_bytes
from app.services.studio.generation import GenerationService, generation_error
from app.studio.contracts import ERROR_HTTP_STATUS
from app.studio.ports import POLICY, RepositoryConflict


def create_generation_router(
    service: GenerationService,
    resolve_session: Callable[[Request], Awaitable[str | None]],
    renew_session_cookie: Callable[[Request, Response, str], None],
    *, trusted_origins: frozenset[str],
) -> APIRouter:
    router = APIRouter()

    @router.post('/api/studio/generate')
    async def generate(http: Request):
        admitted_expiry = []
        try:
            headers = GenerationHeaders.model_validate({'Origin': http.headers.get('origin'), 'Idempotency-Key': http.headers.get('idempotency-key')})
            if headers.origin not in trusted_origins:
                raise generation_error('invalid_input')
            body = bytearray()
            async for chunk in http.stream():
                if len(body) + len(chunk) > POLICY.max_body_bytes:
                    raise generation_error('input_too_large')
                body.extend(chunk)
            request = validate_request_bytes(GenerateRequest, bytes(body))
            session_id = await resolve_session(http)
            if not session_id:
                raise generation_error('not_found')
            result = await service.generate(session_id=session_id, request=request, idempotency_key=headers.idempotency_key,
                                            on_admitted=admitted_expiry.append)
            response = JSONResponse(result.bundle.model_dump(), status_code=200 if result.replayed else 201, headers={'Cache-Control': 'no-store'})
            if not result.replayed:
                renew_session_cookie(http, response, result.expires_at)
            return response
        except ValidationError:
            error = generation_error('invalid_input').error
        except RepositoryConflict as failure:
            error = failure.error
        response = JSONResponse(error.model_dump(), status_code=ERROR_HTTP_STATUS[error.code], headers={'Cache-Control': 'no-store'})
        if error.code == 'session_limit':
            response.headers['Retry-After'] = '3600'
        if admitted_expiry:
            renew_session_cookie(http, response, admitted_expiry[0])
        return response

    return router
