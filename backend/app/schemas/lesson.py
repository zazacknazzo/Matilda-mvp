"""T02 / M0 v1: transport contracts only; no retrieval, routes or generation.

Scientific IDs are external references. Structural validation does not replace
T09 checking the frozen, authorized preview and its canonical server snapshots.
"""
from datetime import datetime, timedelta
from typing import Annotated, Literal, Mapping
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

Id = Annotated[str, Field(min_length=1, pattern=r'\S')]
Text = Annotated[str, Field(min_length=1, max_length=20_000, pattern=r'\S')]
Index = Annotated[int, Field(ge=0)]
Minutes = Annotated[int, Field(gt=0, le=120)]


class LessonModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    @field_validator('schema_version', mode='before', check_fields=False)
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise PydanticCustomError('lesson_schema_version_invalid', 'schema_version exige inteiro, não booleano/string.')
        return value


class TextBlock(LessonModel):
    type: Literal['text']
    text: Text


class BulletsBlock(LessonModel):
    type: Literal['bullets']
    items: list[Text] = Field(min_length=1)


class StepsBlock(LessonModel):
    type: Literal['steps']
    items: list[Text] = Field(min_length=2, max_length=6)


class QuestionBlock(LessonModel):
    type: Literal['question']
    text: Text


class EvidenceClaimBlock(LessonModel):
    type: Literal['evidence_claim']
    evidence_id: Id


ContentBlock = Annotated[
    TextBlock | BulletsBlock | StepsBlock | QuestionBlock | EvidenceClaimBlock,
    Field(discriminator='type'),
]


def unique(values, label):
    if len(values) != len(set(values)):
        raise PydanticCustomError('lesson_duplicate_identifier', f'{label}: identificadores/índices duplicados.')


def utc(value: str) -> str:
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PydanticCustomError('lesson_timestamp_invalid', 'Data ISO 8601 UTC exigida.') from exc
    if 'T' not in value or stamp.utcoffset() != timedelta(0):
        raise PydanticCustomError('lesson_timestamp_invalid', 'Data ISO 8601 UTC exigida.')
    return value


class LessonMetadata(LessonModel):
    title: Annotated[str, Field(min_length=1, max_length=160, pattern=r'\S')]
    subject: Annotated[str, Field(min_length=1, max_length=80, pattern=r'\S')]
    education_level: Annotated[str, Field(min_length=1, max_length=80, pattern=r'\S')]
    duration_minutes: Annotated[int, Field(ge=10, le=120)]
    learning_objectives: list[Annotated[str, Field(min_length=1, max_length=300, pattern=r'\S')]] = Field(min_length=1, max_length=10)
    prior_knowledge: list[Text]
    materials: list[Text]


class LessonGenerationMetadata(LessonModel):
    provider: Id
    model: Id
    prompt_version: Id
    schema_version: Literal[1]
    generated_at: str
    duration_ms: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None

    _utc = field_validator('generated_at')(utc)


class LessonReference(LessonModel):
    """Server-owned snapshot of an actually used, verified documentary source."""
    id: Id
    contribution_id: Id
    claim_supported: Annotated[str, Field(min_length=1, max_length=1_500, pattern=r'\S')]
    source_title: Text
    source_url: str
    source_type: Literal['documental', 'historical']
    excerpt_or_location: Text
    verification_status: Literal['verified']
    researcher_ids: list[Id] = Field(min_length=1)
    participants: list[Text] = Field(min_length=1)
    limitations: list[Text] = Field(min_length=1)
    retrieved_at: str
    from_cache: bool

    _utc = field_validator('retrieved_at')(utc)

    @field_validator('source_url')
    @classmethod
    def safe_link(cls, value):
        try:
            parts = urlsplit(value)
            invalid = (parts.scheme not in ('http', 'https') or not parts.hostname
                       or parts.username or parts.password or any(c.isspace() for c in value))
        except ValueError:
            raise PydanticCustomError('lesson_reference_url_invalid', 'Fonte exige URL HTTP(S) sem credenciais/espaços.') from None
        if invalid:
            raise PydanticCustomError('lesson_reference_url_invalid', 'Fonte exige URL HTTP(S) sem credenciais/espaços.')
        return value

    @model_validator(mode='after')
    def identities(self):
        unique(self.researcher_ids, 'Pesquisadores')
        unique(self.participants, 'Participantes')
        return self


class LessonSection(LessonModel):
    id: Id
    title: Text
    duration_minutes: Minutes
    objective_indexes: list[Index] = Field(min_length=1)
    explanation_blocks: list[ContentBlock]
    slide_ids: list[Id] = Field(min_length=1)
    activity_ids: list[Id]


def validate_slide_content(layout, title, subtitle, blocks, *, has_contribution):
    kinds = {b.type for b in blocks}
    if layout == 'PROCESS' and 'steps' not in kinds:
        raise PydanticCustomError('lesson_slide_layout_invalid', 'PROCESS exige 2–6 etapas.')
    if layout == 'QUESTION' and 'question' not in kinds:
        raise PydanticCustomError('lesson_slide_layout_invalid', 'QUESTION exige pergunta.')
    if layout == 'CONCEPT' and not kinds.intersection({'text', 'bullets'}):
        raise PydanticCustomError('lesson_slide_layout_invalid', 'CONCEPT exige texto ou tópicos.')
    if layout == 'SCIENTIST_SPOTLIGHT' and ('evidence_claim' not in kinds or not has_contribution):
        raise PydanticCustomError('lesson_slide_layout_invalid', 'Spotlight exige contribuição e bloco documental.')
    visible = len(title) + len(subtitle or '')
    for block in blocks:
        if isinstance(block, (TextBlock, QuestionBlock)):
            visible += len(block.text)
        elif isinstance(block, (BulletsBlock, StepsBlock)):
            visible += sum(len(x) for x in block.items)
    if visible > 600:
        raise PydanticCustomError('lesson_slide_content_too_large', 'Slide excede 600 caracteres pedagógicos visíveis.')


class LessonSlide(LessonModel):
    id: Id
    section_id: Id
    layout: Literal['TITLE', 'CONCEPT', 'PROCESS', 'SCIENTIST_SPOTLIGHT', 'QUESTION', 'SUMMARY']
    title: Annotated[str, Field(min_length=1, max_length=100, pattern=r'\S')]
    subtitle: Text | None = None
    content_blocks: list[ContentBlock] = Field(max_length=6)
    speaker_notes: Annotated[str, Field(max_length=1_500)]
    duration_minutes: Minutes
    contribution_ids: list[Id]
    evidence_ids: list[Id]

    @model_validator(mode='after')
    def layout_and_content(self):
        unique(self.contribution_ids, 'Contribuições')
        unique(self.evidence_ids, 'Evidências')
        validate_slide_content(self.layout, self.title, self.subtitle, self.content_blocks,
                               has_contribution=bool(self.contribution_ids))
        if {b.evidence_id for b in self.content_blocks if isinstance(b, EvidenceClaimBlock)} != set(self.evidence_ids):
            raise PydanticCustomError('lesson_evidence_binding_mismatch', 'Evidências do slide devem coincidir com seus blocos documentais.')
        return self


class LessonActivity(LessonModel):
    id: Id
    section_id: Id
    type: Literal['comprehension', 'discussion']
    prompt: Text
    teacher_guidance: Text
    objective_indexes: list[Index] = Field(min_length=1)
    assessment_criteria: list[Text] = Field(min_length=1)


class LessonBundle(LessonModel):
    lesson_bundle_id: Id
    project_id: Id
    preview_id: Id
    schema_version: Literal[1]
    review_revision: Annotated[int, Field(ge=0)]
    metadata: LessonMetadata
    sections: list[LessonSection] = Field(min_length=3, max_length=8)
    slides: list[LessonSlide] = Field(min_length=4, max_length=12)
    activities: list[LessonActivity] = Field(min_length=1, max_length=4)
    references: list[LessonReference]
    limitations: list[Text] = Field(min_length=1)
    generation_metadata: LessonGenerationMetadata

    @model_validator(mode='after')
    def links_and_times(self):
        for name in ('sections', 'slides', 'activities', 'references'):
            unique([item.id for item in getattr(self, name)], name)
        sections = {s.id: s for s in self.sections}
        slides = {s.id: s for s in self.slides}
        activities = {a.id: a for a in self.activities}
        references = {r.id: r for r in self.references}
        linked_slides, linked_activities, used = [], [], set()
        if sum(s.duration_minutes for s in self.sections) != self.metadata.duration_minutes:
            raise PydanticCustomError('lesson_duration_mismatch', 'Seções não somam a duração da aula.')
        for owner in [*self.sections, *self.activities]:
            unique(owner.objective_indexes, 'Objetivos')
            if any(i >= len(self.metadata.learning_objectives) for i in owner.objective_indexes):
                raise PydanticCustomError('lesson_objective_not_approved', 'Objetivo não pertence à lista aprovada.')
        for section in self.sections:
            unique(section.slide_ids, 'Slides da seção')
            unique(section.activity_ids, 'Atividades da seção')
            if any(sid not in slides or slides[sid].section_id != section.id for sid in section.slide_ids):
                raise PydanticCustomError('lesson_section_slide_link_invalid', 'Slide não pertence à seção indicada.')
            if any(aid not in activities or activities[aid].section_id != section.id for aid in section.activity_ids):
                raise PydanticCustomError('lesson_section_activity_link_invalid', 'Atividade não pertence à seção indicada.')
            if sum(slides[sid].duration_minutes for sid in section.slide_ids) != section.duration_minutes:
                raise PydanticCustomError('lesson_section_duration_mismatch', 'Slides não somam a duração da seção, incluindo atividades.')
            linked_slides.extend(section.slide_ids)
            linked_activities.extend(section.activity_ids)
            used.update(b.evidence_id for b in section.explanation_blocks if isinstance(b, EvidenceClaimBlock))
        if len(linked_slides) != len(slides) or set(linked_slides) != set(slides):
            raise PydanticCustomError('lesson_slide_ownership_invalid', 'Cada slide deve ser referenciado exatamente uma vez.')
        if len(linked_activities) != len(activities) or set(linked_activities) != set(activities):
            raise PydanticCustomError('lesson_activity_ownership_invalid', 'Cada atividade deve ser referenciada exatamente uma vez.')
        for slide in self.slides:
            if slide.section_id not in sections or any(eid not in references for eid in slide.evidence_ids):
                raise PydanticCustomError('lesson_slide_reference_invalid', 'Slide contém seção/evidência desconhecida.')
            if {references[eid].contribution_id for eid in slide.evidence_ids} != set(slide.contribution_ids):
                raise PydanticCustomError('lesson_contribution_binding_mismatch', 'Contribuições não coincidem com as evidências dos blocos.')
            used.update(slide.evidence_ids)
        if used != set(references):
            raise PydanticCustomError('lesson_reference_usage_mismatch', 'Referências devem conter exatamente as evidências utilizadas.')
        if len(self.model_dump_json().encode('utf-8')) > 128 * 1024:
            raise PydanticCustomError('lesson_bundle_too_large', 'LessonBundle excede 128 KiB.')
        return self

    def validate_authorized_references(self, allowed: Mapping[str, LessonReference]) -> None:
        """Call with trusted snapshots of accepted suggestions from frozen review.

        T09 must first enforce identity/eligibility, session, revision, context and
        accepted decisions. Never derive this mapping from provider output.
        """
        if any(reference.id not in allowed for reference in self.references):
            raise PydanticCustomError('lesson_evidence_not_authorized', 'Evidência fora da revisão autorizada ou snapshot adulterado.')
        if any(reference != allowed[reference.id] for reference in self.references):
            raise PydanticCustomError('lesson_reference_snapshot_mismatch', 'Evidência fora da revisão autorizada ou snapshot adulterado.')
