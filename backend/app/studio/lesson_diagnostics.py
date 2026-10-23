"""Fixed lesson rejection codes; no exception messages, locations or input values."""
import json
import logging

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

CODES = frozenset({
    'lesson_activity_ownership_invalid',
    'lesson_activity_section_link_invalid',
    'lesson_bundle_too_large',
    'lesson_configuration_mismatch',
    'lesson_contribution_binding_mismatch',
    'lesson_draft_json_invalid',
    'lesson_draft_size_invalid',
    'lesson_duplicate_identifier',
    'lesson_duplicate_local_key',
    'lesson_duration_mismatch',
    'lesson_evidence_binding_mismatch',
    'lesson_objective_not_approved',
    'lesson_objectives_mismatch',
    'lesson_reference_snapshot_mismatch',
    'lesson_reference_url_invalid',
    'lesson_reference_usage_mismatch',
    'lesson_review_mismatch',
    'lesson_schema_version_invalid',
    'lesson_section_activity_link_invalid',
    'lesson_section_duration_mismatch',
    'lesson_section_slide_link_invalid',
    'lesson_slide_content_too_large',
    'lesson_slide_layout_invalid',
    'lesson_slide_ownership_invalid',
    'lesson_slide_reference_invalid',
    'lesson_slide_section_link_invalid',
    'lesson_timestamp_invalid',
    'lesson_metadata_prompt_mismatch', 'lesson_metadata_budget_invalid', 'lesson_deadline_exceeded',
    'lesson_storage_failure', 'lesson_failure_recording_failed', 'lesson_generation_claim_missing',
    'lesson_persistence_review_mismatch', 'lesson_persistence_snapshot_invalid',
    'lesson_evidence_not_authorized', 'lesson_internal_failure', 'lesson_metadata_invalid',
    'lesson_draft_schema_invalid', 'lesson_bundle_schema_invalid', 'lesson_provider_output_invalid',
})
PHASES = frozenset({'provider', 'metadata', 'draft', 'materialization', 'bundle', 'review', 'persistence', 'completion'})
PYDANTIC_TYPES = frozenset({
    'missing', 'extra_forbidden', 'string_type', 'string_too_short', 'string_too_long',
    'string_pattern_mismatch', 'int_type', 'int_parsing', 'greater_than', 'greater_than_equal',
    'less_than', 'less_than_equal', 'list_type', 'too_short', 'too_long', 'literal_error',
    'union_tag_invalid', 'union_tag_not_found', 'model_type', 'dict_type', 'bool_type',
    'json_invalid', 'value_error', 'finite_number',
})


class LessonRejected(ValueError):
    def __init__(self, code, phase='materialization', *, validation_types=()):
        self.code = code if code in CODES else 'lesson_internal_failure'
        self.phase = phase if phase in PHASES else 'materialization'
        self.validation_types = tuple(sorted(set(validation_types) & (PYDANTIC_TYPES | CODES | {'other'})))
        super().__init__(self.code)


def validation_rejection(failure, phase):
    types = {error['type'] for error in failure.errors(include_url=False, include_input=False, include_context=False)}
    known = sorted(types & CODES)
    fallback = {'metadata': 'lesson_metadata_invalid', 'draft': 'lesson_draft_schema_invalid',
                'bundle': 'lesson_bundle_schema_invalid'}.get(phase, 'lesson_provider_output_invalid')
    safe_types = {kind if kind in PYDANTIC_TYPES or kind in CODES else 'other' for kind in types}
    return LessonRejected(known[0] if known and phase != 'metadata' else fallback, phase, validation_types=safe_types)


def record_failure(failure, phase):
    if isinstance(failure, ValidationError):
        failure = validation_rejection(failure, phase)
    elif isinstance(failure, PydanticCustomError):
        failure = LessonRejected(failure.type, phase)
    elif not isinstance(failure, LessonRejected):
        fallback = 'lesson_provider_output_invalid' if phase == 'provider' else 'lesson_internal_failure'
        failure = LessonRejected(fallback, phase)
    event = {'stage': 'lesson', 'validation_phase': failure.phase, 'failure_code': failure.code,
             'outcome': 'pydantic_validation' if failure.validation_types else 'scientific_validation'}
    if failure.validation_types:
        event['validation_types'] = list(failure.validation_types)
    logging.getLogger('matilda.studio.validation').info('studio_lesson_validation %s',
                                                     json.dumps(event, separators=(',', ':')))
