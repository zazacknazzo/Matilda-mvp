"""Standalone API description for review. Does not create/register product routes."""
from pydantic.json_schema import models_json_schema

from app.schemas.lesson import LessonBundle
from app.schemas.studio import (
    EnrichmentPreview, ExportQuery, GenerateRequest, GenerationHeaders,
    PreviewRequest, ReviewRequest, StudioError,
)
from .ports import SESSION_COOKIE


ERROR_HTTP_STATUS = {
    'invalid_input': 422, 'not_found': 404, 'review_conflict': 409,
    'generation_in_progress': 409, 'input_too_large': 413, 'session_limit': 429,
    'invalid_generation': 502, 'provider_unavailable': 503,
    'studio_not_configured': 503, 'generation_timeout': 504,
}


def studio_openapi() -> dict:
    models = [
        (PreviewRequest, 'validation'), (ReviewRequest, 'validation'),
        (GenerateRequest, 'validation'), (GenerationHeaders, 'validation'),
        (ExportQuery, 'validation'), (EnrichmentPreview, 'serialization'),
        (LessonBundle, 'serialization'), (StudioError, 'serialization'),
    ]
    references, definitions = models_json_schema(models, ref_template='#/components/schemas/{model}')
    spec = {
        'openapi': '3.1.0', 'info': {'title': 'Matilda Studio — contrato T03, sem endpoints implementados', 'version': '1'},
        'paths': {}, 'components': {
            'schemas': definitions['$defs'],
            'securitySchemes': {'studioSession': {'type': 'apiKey', 'in': 'cookie', 'name': SESSION_COOKIE}},
        },
    }
    operations = [
        ('post', '/api/studio/preview', 'studio_preview', PreviewRequest, EnrichmentPreview, [201], [404, 409, 413, 422, 429, 502, 503, 504]),
        ('get', '/api/studio/previews/{id}', 'studio_get_preview', None, EnrichmentPreview, [200], [404]),
        ('post', '/api/studio/previews/{id}/review', 'studio_review', ReviewRequest, EnrichmentPreview, [200], [404, 409, 413, 422]),
        ('post', '/api/studio/generate', 'studio_generate', GenerateRequest, LessonBundle, [200, 201], [404, 409, 413, 422, 429, 502, 503, 504]),
        ('get', '/api/studio/lessons/{id}', 'studio_get_lesson', None, LessonBundle, [200], [404]),
        ('get', '/api/studio/lessons/{id}/export', 'studio_export_lesson', None, None, [200], [404, 422]),
    ]
    for method, path, identifier, request, response, successes, errors in operations:
        parameters = []
        if '{id}' in path:
            parameters.append({'in': 'path', 'name': 'id', 'required': True, 'schema': {'type': 'string', 'minLength': 1}})
        if method == 'post':
            parameters.append({'in': 'header', 'name': 'Origin', 'required': True, 'schema': {'type': 'string'}, 'description': 'Validar contra a origem configurada antes de qualquer escrita.'})
        if request == GenerateRequest:
            parameters.append({'in': 'header', 'name': 'Idempotency-Key', 'required': True, 'schema': {'type': 'string', 'minLength': 1, 'maxLength': 128, 'pattern': r'\S'}})
        if identifier == 'studio_export_lesson':
            parameters.append({'in': 'query', 'name': 'format', 'required': False, 'schema': {'type': 'string', 'const': 'markdown', 'default': 'markdown'}})
        responses = {}
        for status in successes:
            content = {'application/json': {'schema': references[(response, 'serialization')]}} if response else {'text/markdown': {'schema': {'type': 'string'}}}
            responses[str(status)] = {'description': 'Resultado validado/persistido; consulta e repetição concluída não chamam IA.', 'content': content}
            if response is None:
                responses[str(status)]['headers'] = {'Content-Disposition': {'schema': {'type': 'string'}, 'description': 'attachment; nome seguro, Markdown UTF-8'}}
        for status in errors:
            responses[str(status)] = {'description': 'Erro sanitizado; recurso de outra sessão/expirado usa 404 genérico.', 'content': {'application/json': {'schema': references[(StudioError, 'serialization')]}}}
            if status == 429:
                responses[str(status)]['headers'] = {'Retry-After': {'schema': {'type': 'integer', 'minimum': 0}, 'description': 'Obrigatório quando a espera for temporal.'}}
        operation = {'operationId': identifier, 'parameters': parameters, 'security': [{'studioSession': []}], 'responses': responses}
        if request:
            operation['requestBody'] = {'required': True, 'content': {'application/json': {'schema': references[(request, 'validation')]}}}
        if identifier == 'studio_preview':
            operation['security'].append({})
        if method == 'post':
            for status in successes:
                if identifier != 'studio_generate' or status == 201:
                    operation['responses'][str(status)]['headers'] = {'Set-Cookie': {'schema': {'type': 'string'}, 'description': 'Sessão inicial/renovada; HttpOnly; SameSite=Lax; Secure em HTTPS; Path=/api/studio'}}
        spec['paths'][path] = {method: operation}
    return spec
