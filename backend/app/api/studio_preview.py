"""HTTP boundary for previews only. Review and generation mount separately in T10."""
import asyncio
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas.studio import EnrichmentPreview, LessonProject, PreviewRequest, StudioError
from app.services.studio.preview import create_preview, original_documents
from app.services.studio.repository import conflict, not_found
from app.studio.ports import POLICY, SESSION_COOKIE, ProviderFailure, RepositoryConflict

router = APIRouter(prefix='/api/studio', tags=['Studio'])
log = logging.getLogger('matilda.studio')


def now():
    return datetime.now(timezone.utc).isoformat()


def get_provider():
    from app.integrations.gemini_client import GeminiProvider
    return GeminiProvider()


def get_repository():
    from app.services.studio.runtime_repository import StudioRepository
    return StudioRepository()


def owner(token):
    return hashlib.sha256(token.encode()).hexdigest()


def error_response(error, *, token=None, secure=False, expires_at=None):
    statuses = {'invalid_input': 422, 'input_too_large': 413, 'not_found': 404, 'review_conflict': 409,
                'generation_in_progress': 409, 'session_limit': 429, 'invalid_generation': 502,
                'generation_timeout': 504, 'studio_not_configured': 503, 'provider_unavailable': 503}
    response = JSONResponse(error.model_dump(), status_code=statuses[error.code], headers={'Cache-Control': 'no-store'})
    if error.code == 'session_limit':
        response.headers['Retry-After'] = '3600'
    if token:
        set_session(response, token, secure, expires_at)
    return response


def set_session(response, token, secure, expires_at):
    expiry = datetime.fromisoformat(expires_at)
    max_age = max(0, int((expiry - datetime.fromisoformat(now())).total_seconds()))
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, expires=expiry,
                        httponly=True, secure=secure, samesite='lax', path='/api/studio')


@router.post('/preview', response_model=EnrichmentPreview, status_code=201,
    responses={status: {'model': StudioError} for status in (404, 409, 413, 422, 429, 502, 503, 504)},
    openapi_extra={
        'requestBody': {'required': True, 'content': {'application/json': {'schema': PreviewRequest.model_json_schema()}}},
        'parameters': [{'name': 'Origin', 'in': 'header', 'required': True, 'schema': {'type': 'string'}}],
    })
async def post_preview(http: Request, provider=Depends(get_provider), repository=Depends(get_repository)):
    started = monotonic()
    project = None
    admitted = False
    token = http.cookies.get(SESSION_COOKIE) or secrets.token_urlsafe(32)
    session_id = owner(token)
    try:
        async with asyncio.timeout(max(0, started + POLICY.preview_backend_seconds - monotonic())):
            allowed = os.getenv('MATILDA_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
            if http.headers.get('origin') not in [origin.strip() for origin in allowed]:
                raise conflict('invalid_input', 'Origem de escrita não autorizada.')
            body = bytearray()
            async for chunk in http.stream():
                if len(body) + len(chunk) > POLICY.max_body_bytes:
                    raise conflict('input_too_large', 'Corpo excede 128 KiB.')
                body.extend(chunk)
            request = PreviewRequest.model_validate_json(bytes(body))
            timestamp = now()
            project = LessonProject(id=request.project_id or str(uuid4()), title=request.title, subject=request.subject,
                                    education_level=request.education_level, duration_minutes=request.duration_minutes,
                                    learning_objectives=request.objectives, status='draft', created_at=timestamp, updated_at=timestamp,
                                    last_teacher_activity_at=timestamp, expires_at=(datetime.fromisoformat(timestamp) + timedelta(days=7)).isoformat())
            documents = original_documents(request, project.id)
            await repository.save_material(session_id=session_id, project=project, request=request, documents=documents, now=timestamp)
            admitted = True
            preview = await create_preview(request=request, project=project, documents=documents, session_id=session_id,
                                               provider=provider, repository=repository, deadline=started + POLICY.preview_backend_seconds, now=now)
            response = JSONResponse(preview.model_dump(), status_code=201, headers={'Cache-Control': 'no-store'})
            set_session(response, token, http.url.scheme == 'https', project.expires_at)
            log.info('preview_complete id=%s model=%s seconds=%.3f', preview.preview_id, preview.generation_metadata.model, monotonic()-started)
            return response
    except ValidationError:
        error = StudioError(code='invalid_input', detail='Entrada inválida: confira campos, tipos e limites.', retryable=False)
    except RepositoryConflict as exc:
        error = exc.error
    except (TimeoutError, ProviderFailure) as exc:
        reason = exc.reason if isinstance(exc, ProviderFailure) else 'timeout'
        code = 'generation_timeout' if reason == 'timeout' else 'invalid_generation' if reason in ('blocked', 'truncated') else 'provider_unavailable'
        error = StudioError(code=code, detail='O Gemini não concluiu a prévia. O material foi preservado; confira a configuração ou tente novamente.', retryable=reason not in ('unauthorized', 'blocked'), project_id=project.id if admitted else None)
    except HTTPException as exc:
        code = {404: 'not_found', 422: 'invalid_input', 502: 'invalid_generation'}.get(exc.status_code, 'provider_unavailable')
        error = StudioError(code=code, detail='Não foi possível recuperar a fonte científica.', retryable=exc.status_code >= 500)
    except ValueError:
        error = StudioError(code='invalid_input', detail='Documento ou contexto científico inválido; confira os limites da entrada.', retryable=False)
    if admitted:
        error.project_id = project.id
        await repository.fail_preview(session_id=session_id, project_id=project.id, error=error, now=now())
    log.info('preview_failed code=%s seconds=%.3f', error.code, monotonic()-started)
    return error_response(error, token=token if admitted else None, secure=http.url.scheme == 'https', expires_at=project.expires_at if admitted else None)


@router.get('/previews/{preview_id}', response_model=EnrichmentPreview, responses={404: {'model': StudioError}})
async def get_preview(preview_id: str, http: Request, repository=Depends(get_repository)):
    origin = http.headers.get('origin')
    allowed = {item.strip() for item in os.getenv('MATILDA_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')}
    if origin is not None and origin not in allowed:
        return error_response(conflict('invalid_input', 'Origem não autorizada.').error)
    token = http.cookies.get(SESSION_COOKIE)
    preview = await repository.get_preview(session_id=owner(token), preview_id=preview_id, now=now()) if token else None
    if preview is None:
        return error_response(not_found().error)
    return JSONResponse(preview.model_dump(), headers={'Cache-Control': 'no-store'})
