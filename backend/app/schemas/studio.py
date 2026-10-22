"""T03 / M0 v1 contracts. No routes, repository or provider implementation."""
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Annotated, Literal, TypeVar

from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from .lesson import (
    Id, Text, LessonModel, LessonBundle, LessonReference, LessonGenerationMetadata,
    utc, unique,
)
from .models import Concept, DiscoveryMatch, Paper
from .scientific_context import ScientificContext, SourceDocument, SourceAnchor


Objective = Annotated[str, Field(min_length=1, max_length=300, pattern=r'\S')]
Title = Annotated[str, Field(min_length=1, max_length=160, pattern=r'\S')]
Subject = Annotated[str, Field(min_length=1, max_length=80, pattern=r'\S')]
Revision = Annotated[int, Field(ge=0)]
ProjectStatus = Literal['draft', 'preview_ready', 'reviewed', 'generating', 'ready']
GenerationStatus = Literal['idle', 'generating', 'ready', 'failed']
StudioErrorCode = Literal[
    'invalid_input', 'not_found', 'review_conflict', 'generation_in_progress',
    'input_too_large', 'session_limit', 'invalid_generation',
    'provider_unavailable', 'studio_not_configured', 'generation_timeout',
]


class PreviewRequest(LessonModel):
    title: Title
    subject: Subject = 'Ciências'
    education_level: Subject = 'Ensino Médio'
    duration_minutes: Annotated[int, Field(ge=10, le=120)] = 50
    objectives: list[Objective] = Field(default_factory=list, max_length=10)
    concepts: list[Annotated[str, Field(min_length=1, max_length=100, pattern=r'\S')]] = Field(default_factory=list, max_length=20)
    material_text: Annotated[str, Field(max_length=20000)] = ''
    doi: str | None = None
    analysis_id: Id | None = None
    project_id: Id | None = None

    @field_validator('title', 'subject', 'education_level', mode='before')
    @classmethod
    def trim_configuration(cls, value):
        return value.strip() if isinstance(value, str) else value

    _doi = field_validator('doi')(SourceDocument.canonical_doi.__func__)

    @model_validator(mode='after')
    def scientific_origin(self):
        if self.doi is not None and self.analysis_id is not None:
            raise ValueError('DOI e investigação são origens alternativas.')
        if not (self.material_text.strip() or self.concepts or self.doi or self.analysis_id):
            raise ValueError('Informe material, conceitos, DOI ou investigação.')
        return self


class StudioError(LessonModel):
    detail: Id
    code: StudioErrorCode
    retryable: bool
    project_id: Id | None = None


class LessonProject(LessonModel):
    id: Id
    title: Title
    subject: Subject
    education_level: Subject
    duration_minutes: Annotated[int, Field(ge=10, le=120)]
    learning_objectives: list[Objective] = Field(max_length=10)
    scientific_context_id: Id | None = None
    status: ProjectStatus
    created_at: str
    updated_at: str
    last_teacher_activity_at: str
    expires_at: str

    _utc = field_validator('created_at', 'updated_at', 'last_teacher_activity_at', 'expires_at')(utc)

    @model_validator(mode='after')
    def retention(self):
        created, updated, activity, expires = map(datetime.fromisoformat, (
            self.created_at, self.updated_at, self.last_teacher_activity_at, self.expires_at,
        ))
        if not created <= activity <= updated or expires != activity + timedelta(days=7):
            raise ValueError('Projeto exige cronologia consistente e retenção de 7 dias por ação docente.')
        if self.status != 'draft' and self.scientific_context_id is None:
            raise ValueError('Projeto após draft exige contexto científico.')
        return self


class EnrichmentSuggestion(LessonModel):
    id: Id
    project_id: Id
    concept_ids: list[Id] = Field(min_length=1)
    source_anchor: SourceAnchor
    researcher_ids: list[Id] = Field(min_length=1)
    contribution_id: Id
    evidence_ids: list[Id] = Field(min_length=1)
    scientific_explanation: Text
    historical_claim: Text
    pedagogical_rationale: Text
    suggested_content: Text
    status: Literal['pending', 'accepted', 'rejected']

    @model_validator(mode='after')
    def identifiers(self):
        for name in ('concept_ids', 'researcher_ids', 'evidence_ids'):
            unique(getattr(self, name), name)
        return self


class EnrichmentPreview(LessonModel):
    preview_id: Id
    project_id: Id
    schema_version: Literal[1]
    scientific_context: ScientificContext
    concepts: list[Concept]
    suggested_objectives: list[Objective] = Field(max_length=10)
    suggestions: list[EnrichmentSuggestion]
    evidence_references: list[LessonReference]
    limitations: list[Text]
    review_revision: Revision
    expires_at: str
    generation_metadata: LessonGenerationMetadata
    generation_status: GenerationStatus
    last_lesson_bundle_id: Id | None = None
    project: LessonProject
    source_documents: list[SourceDocument] = Field(min_length=1)
    approved_objectives: list[Objective] = Field(default_factory=list, max_length=10)
    last_error: StudioError | None = None

    _utc = field_validator('expires_at')(utc)

    @field_validator('concepts', mode='before')
    @classmethod
    def strict_shared_concepts(cls, value):
        # Preserve the legacy Concept model; tighten only this new API boundary.
        if isinstance(value, list):
            return [Concept.model_validate(item, strict=True, extra='forbid') for item in value]
        return value

    @model_validator(mode='after')
    def references_and_state(self):
        context = self.scientific_context
        if self.project_id != self.project.id or self.project.scientific_context_id != context.id:
            raise ValueError('Projeto/contexto não correspondem à prévia.')
        if self.expires_at != self.project.expires_at:
            raise ValueError('Prévia deve informar o prazo corrente do projeto.')
        for items, label in ((self.suggestions, 'Sugestões'), (self.evidence_references, 'Evidências'), (self.source_documents, 'Documentos'), (self.concepts, 'Conceitos')):
            unique([item.id for item in items], label)
        documents = {document.id: document for document in self.source_documents}
        if set(documents) != set(context.source_document_ids) or any(d.project_id != self.project_id for d in documents.values()):
            raise ValueError('Documentos não pertencem ao contexto/projeto.')
        if [(c.id, c.name) for c in self.concepts] != list(zip(context.concept_ids, context.concept_labels)):
            raise ValueError('Conceitos não coincidem com o contexto.')
        references = {reference.id: reference for reference in self.evidence_references}
        used = set()
        for suggestion in self.suggestions:
            if suggestion.project_id != self.project_id or not set(suggestion.concept_ids) <= set(context.concept_ids):
                raise PydanticCustomError('invalid_concept', 'Sugestão fora do projeto/contexto.')
            document = documents.get(suggestion.source_anchor.source_document_id)
            if document is None:
                raise PydanticCustomError('invalid_source_anchor', 'Âncora fora dos documentos da prévia.')
            suggestion.source_anchor.locate(document)
            for identifier in suggestion.evidence_ids:
                reference = references.get(identifier)
                if reference is None or reference.contribution_id != suggestion.contribution_id or reference.researcher_ids != suggestion.researcher_ids:
                    raise ValueError('Evidência/pesquisadores não pertencem à contribuição da sugestão.')
            claim = '\n\n'.join(references[identifier].claim_supported for identifier in suggestion.evidence_ids)
            if suggestion.historical_claim != claim:
                raise ValueError('Afirmação histórica deve preservar literalmente as evidências canônicas.')
            used.update(suggestion.evidence_ids)
        if used != set(references):
            raise ValueError('Referências devem corresponder às sugestões da prévia.')
        if not self.suggestions and not self.limitations:
            raise ValueError('Sem sugestões exige limitação de cobertura.')
        reviewed = bool(self.approved_objectives) and all(s.status != 'pending' for s in self.suggestions)
        if self.project.status in ('reviewed', 'generating', 'ready') and not reviewed:
            raise ValueError('Estado exige objetivos aprovados e sugestões decididas.')
        if self.project.status == 'draft':
            raise ValueError('Draft não é prévia publicada.')
        if self.project.status == 'preview_ready' and reviewed:
            raise ValueError('Revisão completa exige estado reviewed.')
        if self.review_revision == 0 and (self.approved_objectives or any(s.status != 'pending' for s in self.suggestions)):
            raise ValueError('Revisão inicial não contém decisões docentes.')
        if (self.generation_status == 'generating') != (self.project.status == 'generating'):
            raise ValueError('Geração em andamento exige estado generating.')
        if (self.generation_status == 'ready') != (self.project.status == 'ready') or (self.generation_status == 'ready' and self.last_lesson_bundle_id is None):
            raise ValueError('Resultado pronto exige projeto ready e ID recuperável da aula.')
        if self.generation_status == 'failed' and (self.project.status != 'reviewed' or self.last_error is None):
            raise ValueError('Falha preserva revisão utilizável e registra erro separado.')
        if self.last_error is not None and self.last_error.project_id not in (None, self.project_id):
            raise ValueError('Erro não pode expor outro projeto.')
        return self

    def validate_scientific_authority(
        self, matches: Sequence[DiscoveryMatch], allowed_references: Mapping[str, LessonReference],
        *, concepts: Sequence[Concept], papers: Sequence[Paper] = (),
    ) -> None:
        """Authority must come from server-resolved sources, never from this payload."""
        self.scientific_context.validate_references(self.source_documents, concepts=concepts, papers=papers)
        if any(ref.id not in allowed_references or ref != allowed_references[ref.id] for ref in self.evidence_references):
            raise ValueError('Referência não autorizada ou snapshot adulterado.')
        by_contribution = {match.contribution.id: match for match in matches}
        by_evidence = {ref.id: ref for ref in self.evidence_references}
        for suggestion in self.suggestions:
            match = by_contribution.get(suggestion.contribution_id)
            if match is None:
                raise PydanticCustomError('unknown_contribution', 'Contribuição/identidade não elegível na ciência autorizada.')
            if match.contribution.verification_status != 'verified':
                raise PydanticCustomError('ineligible_contribution', 'Contribuição/identidade não elegível na ciência autorizada.')
            if any(r.identity_status != 'verified' for r in match.researchers):
                raise PydanticCustomError('invalid_identity', 'Contribuição/identidade não elegível na ciência autorizada.')
            if suggestion.researcher_ids != match.contribution.researcher_ids or [r.id for r in match.researchers] != suggestion.researcher_ids:
                raise PydanticCustomError('invalid_identity', 'Pesquisadores não correspondem à contribuição autorizada.')
            if not set(suggestion.concept_ids) <= ({c.id for c in match.matched_concepts} & set(match.contribution.concept_ids)):
                raise PydanticCustomError('invalid_concept', 'Conceitos não correspondem à contribuição autorizada.')
            for identifier in suggestion.evidence_ids:
                evidence = next((e for e in match.evidence if e.id == identifier), None)
                reference = by_evidence[identifier]
                if evidence is None or evidence.contribution_id != suggestion.contribution_id or evidence.verification_status != 'verified' or evidence.source_type not in ('documental', 'historical'):
                    raise ValueError('Evidência não elegível para a contribuição autorizada.')
                if any(getattr(reference, key) != value for key, value in evidence.model_dump().items()) or reference.participants != match.contribution.participants:
                    raise ValueError('Afirmação, fonte ou autoria coletiva adulterada.')


class ReviewDecision(LessonModel):
    suggestion_id: Id
    status: Literal['accepted', 'rejected']
    pedagogical_rationale: Text | None = None
    suggested_content: Text | None = None


class ReviewRequest(LessonModel):
    review_revision: Revision
    decisions: list[ReviewDecision]
    approved_objectives: list[Objective] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def distinct_decisions(self):
        unique([decision.suggestion_id for decision in self.decisions], 'Decisões')
        return self

    def validate_preview(self, preview: EnrichmentPreview) -> None:
        if self.review_revision != preview.review_revision:
            raise ValueError('review_conflict: revisão obsoleta.')
        if preview.generation_status == 'generating':
            raise ValueError('generation_in_progress: revisão bloqueada durante geração.')
        if not {d.suggestion_id for d in self.decisions} <= {s.id for s in preview.suggestions}:
            raise ValueError('Decisão de sugestão fora da prévia.')


class GenerateRequest(LessonModel):
    preview_id: Id
    review_revision: Revision
    accepted_suggestion_ids: list[Id]

    @model_validator(mode='after')
    def distinct_accepted(self):
        unique(self.accepted_suggestion_ids, 'Sugestões aceitas')
        return self

    def validate_preview(self, preview: EnrichmentPreview) -> None:
        if self.preview_id != preview.preview_id or self.review_revision != preview.review_revision:
            raise ValueError('review_conflict: prévia ou revisão diferente.')
        if not preview.approved_objectives or any(s.status == 'pending' for s in preview.suggestions):
            raise ValueError('Gerar exige objetivos aprovados e todas as sugestões decididas.')
        if set(self.accepted_suggestion_ids) != {s.id for s in preview.suggestions if s.status == 'accepted'}:
            raise ValueError('IDs aceitos não coincidem com a revisão persistida.')


class StudioWriteHeaders(LessonModel):
    origin: Id = Field(alias='Origin')


class GenerationHeaders(StudioWriteHeaders):
    idempotency_key: Annotated[str, Field(alias='Idempotency-Key', min_length=1, max_length=128, pattern=r'\S')]


class ExportQuery(LessonModel):
    format: Literal['markdown'] = 'markdown'


def validate_lesson_response(bundle: LessonBundle, *, preview: EnrichmentPreview, request: GenerateRequest) -> None:
    """Bind the imported T02 bundle to the server-owned, frozen teacher review."""
    request.validate_preview(preview)
    if (bundle.project_id, bundle.preview_id, bundle.review_revision) != (preview.project_id, preview.preview_id, preview.review_revision):
        raise ValueError('Aula não pertence à revisão autorizada.')
    project, metadata = preview.project, bundle.metadata
    if (metadata.title, metadata.subject, metadata.education_level, metadata.duration_minutes, metadata.learning_objectives) != (
        project.title, project.subject, project.education_level, project.duration_minutes, preview.approved_objectives,
    ):
        raise ValueError('Aula deve preservar configuração e objetivos aprovados pelo professor.')
    accepted_evidence = {eid for s in preview.suggestions if s.status == 'accepted' for eid in s.evidence_ids}
    bundle.validate_authorized_references({ref.id: ref for ref in preview.evidence_references if ref.id in accepted_evidence})


RequestModel = TypeVar('RequestModel', bound=LessonModel)


def validate_request_bytes(model: type[RequestModel], body: bytes) -> RequestModel:
    """The future HTTP adapter must also bound the stream before reading it fully."""
    if len(body) > 128 * 1024:
        raise ValueError('input_too_large: corpo excede 128 KiB.')
    return model.model_validate_json(body)
