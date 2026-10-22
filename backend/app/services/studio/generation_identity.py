"""Shared operation identity for production and isolated generation adapters."""
import json
from datetime import datetime
from hashlib import sha256
from app.schemas.studio import utc


def timestamp(now):
    return datetime.fromisoformat(utc(now)).timestamp()


def fingerprint(preview, request):
    value = {
        'request': request.model_dump(),
        'configuration': preview.project.model_dump(include={'title', 'subject', 'education_level', 'duration_minutes'}),
        'objectives': preview.approved_objectives,
        'suggestions': [item.model_dump() for item in preview.suggestions],
        'context': preview.scientific_context.model_dump(),
        'documents': [item.model_dump() for item in preview.source_documents],
        'evidence': [item.model_dump() for item in preview.evidence_references],
    }
    value['request']['accepted_suggestion_ids'].sort()
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
