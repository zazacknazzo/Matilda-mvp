"""Production composition for review, generation and immutable lesson delivery."""
import logging
import os
from time import monotonic

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.studio_generation import create_generation_router
from app.api.studio_preview import error_response, get_provider, get_repository, now, owner, set_session
from app.schemas.studio import ReviewRequest, validate_request_bytes
from app.services.studio.generation import GenerationService
from app.api.studio_exports import create_export_router
from app.services.studio.runtime_repository import StudioRepository
from app.services.studio.repository import conflict, not_found
from app.studio.ports import POLICY, SESSION_COOKIE, RepositoryConflict

router = APIRouter(prefix='/api/studio', tags=['Studio'])
log = logging.getLogger('matilda.studio')


def trusted_origins():
    return frozenset(x.strip() for x in os.getenv('MATILDA_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','))


def validate_origin(http):
    # Browsers may omit Origin on same-origin GET; a supplied Origin is checked.
    origin = http.headers.get('origin')
    if origin is not None and origin not in trusted_origins():
        raise conflict('invalid_input', 'Origem não autorizada.')


async def resolve_session(http):
    token = http.cookies.get(SESSION_COOKIE)
    return owner(token) if token else None


def renew_cookie(http, response, expires_at):
    token = http.cookies.get(SESSION_COOKIE)
    if token:
        set_session(response, token, http.url.scheme == 'https', expires_at)


class LoggedGenerationService(GenerationService):
    async def generate(self, **kwargs):
        started = monotonic()
        result = await super().generate(**kwargs)
        log.info('lesson_complete id=%s model=%s seconds=%.3f replay=%s', result.bundle.lesson_bundle_id, result.bundle.generation_metadata.model, monotonic()-started, result.replayed)
        return result


def get_generation_service(repository=Depends(get_repository), provider=Depends(get_provider)):
    return LoggedGenerationService(repository, provider, repository.scientific_authority)


@router.post('/previews/{preview_id}/review')
async def review(preview_id: str, http: Request, repository=Depends(get_repository)):
    try:
        if http.headers.get('origin') not in trusted_origins():
            raise conflict('invalid_input', 'Origem de escrita não autorizada.')
        session = await resolve_session(http)
        if not session:
            raise not_found()
        body = bytearray()
        async for chunk in http.stream():
            if len(body) + len(chunk) > POLICY.max_body_bytes:
                raise conflict('input_too_large', 'Corpo excede 128 KiB.')
            body.extend(chunk)
        request = validate_request_bytes(ReviewRequest, bytes(body))
        preview = await repository.save_review(session_id=session, preview_id=preview_id, request=request, now=now())
        response = JSONResponse(preview.model_dump(), headers={'Cache-Control': 'no-store'})
        renew_cookie(http, response, preview.expires_at)
        return response
    except ValidationError:
        return error_response(conflict('invalid_input', 'Confira objetivos, decisões e campos permitidos.').error)
    except RepositoryConflict as exc:
        return error_response(exc.error)


async def owned_lesson(http, repository, lesson_id):
    validate_origin(http)
    session = await resolve_session(http)
    bundle = await repository.get_lesson(session_id=session, lesson_bundle_id=lesson_id, now=now()) if session else None
    if bundle is None:
        raise not_found()
    return bundle


@router.get('/lessons/{lesson_id}')
async def lesson(lesson_id: str, http: Request, repository=Depends(get_repository)):
    try:
        bundle = await owned_lesson(http, repository, lesson_id)
        return JSONResponse(bundle.model_dump(), headers={'Cache-Control': 'no-store'})
    except RepositoryConflict as exc:
        return error_response(exc.error)


# Absolute paths from the existing T09 router: no prefix here.
generation_router = create_generation_router(None, resolve_session, renew_cookie, trusted_origins=trusted_origins(), service_dependency=get_generation_service)
root_router = APIRouter()
root_router.include_router(router)
root_router.include_router(generation_router)
router = root_router

async def export_session(http):
    if http.headers.get('origin') is not None and http.headers['origin'] not in trusted_origins():
        return None
    return await resolve_session(http)

router.include_router(create_export_router(StudioRepository(), export_session))
