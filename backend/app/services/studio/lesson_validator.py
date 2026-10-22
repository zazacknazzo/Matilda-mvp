"""T09 provider-only schema and materialization into the frozen T02/T03 contracts.

Only local component keys and authorized evidence IDs may come from the model.
Configuration, scientific snapshots, final IDs and generation metadata are server-owned.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Annotated, Literal, Sequence
from uuid import uuid4

from pydantic import Field

from app.schemas.lesson import (
    ContentBlock, EvidenceClaimBlock, Index, LessonBundle, LessonGenerationMetadata,
    LessonModel, LessonReference, Minutes, Text,
)
from app.schemas.models import Concept, DiscoveryMatch, Paper
from app.schemas.studio import EnrichmentPreview, GenerateRequest, validate_lesson_response
from app.studio.ports import POLICY

LocalKey = Annotated[str, Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,39}$')]


class DraftSection(LessonModel):
    key: LocalKey
    title: Text
    duration_minutes: Minutes
    objective_indexes: list[Index] = Field(min_length=1)
    explanation_blocks: list[ContentBlock]
    slide_keys: list[LocalKey] = Field(min_length=1)
    activity_keys: list[LocalKey]


class DraftSlide(LessonModel):
    key: LocalKey
    section_key: LocalKey
    layout: Literal['TITLE', 'CONCEPT', 'PROCESS', 'SCIENTIST_SPOTLIGHT', 'QUESTION', 'SUMMARY']
    title: Annotated[str, Field(min_length=1, max_length=100)]
    subtitle: Text | None = None
    content_blocks: list[ContentBlock] = Field(max_length=6)
    speaker_notes: Annotated[str, Field(max_length=1500)]
    duration_minutes: Minutes


class DraftActivity(LessonModel):
    key: LocalKey
    section_key: LocalKey
    type: Literal['comprehension', 'discussion']
    prompt: Text
    teacher_guidance: Text
    objective_indexes: list[Index] = Field(min_length=1)
    assessment_criteria: list[Text] = Field(min_length=1)


class LessonDraft(LessonModel):
    prior_knowledge: list[Text]
    materials: list[Text]
    sections: list[DraftSection] = Field(min_length=3, max_length=8)
    slides: list[DraftSlide] = Field(min_length=4, max_length=12)
    activities: list[DraftActivity] = Field(min_length=1, max_length=4)
    limitations: list[Text]


@dataclass(frozen=True)
class ScientificAuthority:
    """Resolve independently from trusted server science, never provider output."""
    matches: Sequence[DiscoveryMatch]
    references: Mapping[str, LessonReference]
    concepts: Sequence[Concept]
    papers: Sequence[Paper] = ()

    def validate(self, preview: EnrichmentPreview) -> None:
        preview.validate_scientific_authority(self.matches, self.references, concepts=self.concepts, papers=self.papers)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key.')
        result[key] = value
    return result


def materialize_lesson(content: bytes, *, preview: EnrichmentPreview, request: GenerateRequest,
                       metadata: LessonGenerationMetadata) -> LessonBundle:
    if not isinstance(content, bytes) or len(content) > POLICY.max_body_bytes:
        raise ValueError('Provider response too large.')
    payload = json.loads(content.decode('utf-8'), object_pairs_hook=_unique_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON.')))
    draft = LessonDraft.model_validate(payload)
    identifiers = {}
    for kind, collection in (('section', draft.sections), ('slide', draft.slides), ('activity', draft.activities)):
        keys = [item.key for item in collection]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate component keys.')
        identifiers[kind] = {key: str(uuid4()) for key in keys}
    accepted = {eid for suggestion in preview.suggestions if suggestion.status == 'accepted' for eid in suggestion.evidence_ids}
    allowed = {ref.id: ref for ref in preview.evidence_references if ref.id in accepted}
    used = []

    def evidence_ids(blocks):
        values = list(dict.fromkeys(block.evidence_id for block in blocks if isinstance(block, EvidenceClaimBlock)))
        if any(value not in allowed for value in values):
            raise ValueError('Evidence outside the approved review.')
        used.extend(values)
        return values

    sections = []
    for section in draft.sections:
        evidence_ids(section.explanation_blocks)
        sections.append({
            'id': identifiers['section'][section.key],
            **section.model_dump(exclude={'key', 'slide_keys', 'activity_keys'}),
            'slide_ids': [identifiers['slide'][key] for key in section.slide_keys],
            'activity_ids': [identifiers['activity'][key] for key in section.activity_keys],
        })
    slides = []
    for slide in draft.slides:
        selected = evidence_ids(slide.content_blocks)
        slides.append({
            **slide.model_dump(exclude={'key', 'section_key'}),
            'id': identifiers['slide'][slide.key], 'section_id': identifiers['section'][slide.section_key],
            'evidence_ids': selected,
            'contribution_ids': list(dict.fromkeys(allowed[eid].contribution_id for eid in selected)),
        })
    activities = [{**item.model_dump(exclude={'key', 'section_key'}),
                   'id': identifiers['activity'][item.key], 'section_id': identifiers['section'][item.section_key]}
                  for item in draft.activities]
    references = [allowed[eid] for eid in dict.fromkeys(used)]
    bundle = LessonBundle(
        lesson_bundle_id=str(uuid4()), project_id=preview.project_id, preview_id=preview.preview_id,
        schema_version=1, review_revision=preview.review_revision,
        metadata={
            'title': preview.project.title, 'subject': preview.project.subject,
            'education_level': preview.project.education_level, 'duration_minutes': preview.project.duration_minutes,
            'learning_objectives': preview.approved_objectives,
            'prior_knowledge': draft.prior_knowledge, 'materials': draft.materials,
        },
        sections=sections, slides=slides, activities=activities, references=references,
        limitations=list(dict.fromkeys([
            *preview.limitations, *(text for ref in references for text in ref.limitations),
            *draft.limitations, 'Conteúdo pedagógico gerado por IA; revisão docente integral necessária.',
        ])),
        generation_metadata=metadata,
    )
    validate_lesson_response(bundle, preview=preview, request=request)
    return bundle
