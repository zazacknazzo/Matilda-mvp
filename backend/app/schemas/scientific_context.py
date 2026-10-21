"""Additive Studio scientific contracts. No retrieval or external calls live here."""
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Concept, Paper


NonBlank = Annotated[str, Field(min_length=1, pattern=r'\S')]
DocumentText = Annotated[NonBlank, Field(max_length=20000)]


class ScientificModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class SourceDocument(ScientificModel):
    id: NonBlank
    project_id: NonBlank
    type: Literal['text', 'concept_list', 'paper_metadata']
    title: DocumentText
    content: DocumentText
    doi: str | None = None
    extraction_status: Literal['ready'] = 'ready'

    @field_validator('doi')
    @classmethod
    def canonical_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.integrations.openalex import normalize_doi
        try:
            return normalize_doi(value)
        except HTTPException as exc:
            raise ValueError('DOI inválido.') from exc

    @model_validator(mode='after')
    def document_limits(self):
        if self.type == 'paper_metadata' and self.doi is None:
            raise ValueError('Metadados bibliográficos exigem DOI real.')
        if self.type == 'concept_list':
            terms = self.content.splitlines()
            if len(terms) > 20 or any(not term.strip() or len(term) > 100 for term in terms):
                raise ValueError('Lista exige até 20 conceitos não vazios de até 100 caracteres.')
        return self


class Provenance(ScientificModel):
    source_document_id: NonBlank
    concept_id: NonBlank | None = None
    method: Literal['teacher_input', 'editorial_alias', 'openalex_metadata', 'ai_suggested']
    quote: DocumentText | None = None
    retrieved_at: str | None = Field(default=None, json_schema_extra={'format': 'date-time'})
    from_cache: bool | None = None
    source_url: str | None = None

    @model_validator(mode='after')
    def scientific_retrieval(self):
        if self.method == 'ai_suggested' and self.concept_id is not None:
            raise ValueError('Sugestão de IA não pode atribuir ID científico.')
        if self.method == 'teacher_input' and self.concept_id is not None:
            raise ValueError('Entrada docente exige resolução científica separada, sem concept_id.')
        metadata = (self.retrieved_at, self.from_cache, self.source_url)
        if self.method == 'openalex_metadata' or any(value is not None for value in metadata):
            if any(value is None for value in metadata):
                raise ValueError('Consulta científica exige data, cache e URL de origem.')
            moment = datetime.fromisoformat(self.retrieved_at)
            if moment.utcoffset() != timedelta(0):
                raise ValueError('Data de consulta deve ser UTC com fuso explícito.')
            parsed = urlsplit(self.source_url)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError('Origem científica exige URL HTTP/HTTPS sem credenciais.')
        return self


class SourceAnchor(ScientificModel):
    source_document_id: NonBlank
    quote: DocumentText
    occurrence: int = Field(ge=0)

    def locate(self, document: SourceDocument) -> tuple[int, int]:
        """Return Python character offsets for a zero-based literal occurrence."""
        if document.id != self.source_document_id:
            raise ValueError('Âncora aponta para outro documento.')
        start = -1
        for _ in range(self.occurrence + 1):
            start = document.content.find(self.quote, start + 1)
            if start == -1:
                raise ValueError('Ocorrência literal da âncora não existe no documento.')
        return start, start + len(self.quote)


def _quoted_editorial_alias(content: str, quote: str, aliases: Sequence[str]) -> bool:
    from app.services.concept_analysis import contains, normalized

    start = content.find(quote)
    while start != -1:
        end = start + len(quote)
        # Keep word boundaries from the original document, including combining marks.
        before = normalized(content[:start])[-1:]
        after = normalized(content[end:])[:1]
        if any(contains(quote, alias) and contains(before + quote + after, alias) for alias in aliases):
            return True
        start = content.find(quote, start + 1)
    return False


class ScientificContext(ScientificModel):
    id: NonBlank
    origin_type: Literal['doi', 'material', 'mixed']
    paper_ids: list[NonBlank] = Field(default_factory=list)
    concept_ids: list[NonBlank] = Field(default_factory=list)
    concept_labels: list[NonBlank] = Field(default_factory=list)
    source_document_ids: list[NonBlank] = Field(min_length=1)
    provenance: list[Provenance] = Field(default_factory=list)
    limitations: list[NonBlank] = Field(default_factory=list)
    analysis_id: NonBlank | None = None

    @model_validator(mode='after')
    def consistent_context(self):
        for identifiers in (self.paper_ids, self.concept_ids, self.source_document_ids):
            if len(identifiers) != len(set(identifiers)):
                raise ValueError('IDs duplicados no contexto.')
        if len(self.concept_ids) != len(self.concept_labels):
            raise ValueError('IDs e labels de conceitos devem estar alinhados.')
        if self.origin_type == 'material' and (self.paper_ids or self.analysis_id is not None):
            raise ValueError('Material sem DOI não pode inventar artigo ou investigação.')
        if self.origin_type != 'material' and not self.paper_ids:
            raise ValueError('Origem DOI ou mista exige artigo real.')
        if not self.concept_ids and not self.limitations:
            raise ValueError('Contexto sem cobertura exige limitação explícita.')
        for provenance in self.provenance:
            if provenance.source_document_id not in self.source_document_ids:
                raise ValueError('Procedência aponta para documento fora do contexto.')
            if provenance.concept_id is not None and provenance.concept_id not in self.concept_ids:
                raise ValueError('Procedência aponta para conceito fora do contexto.')
        if set(self.concept_ids) != {p.concept_id for p in self.provenance if p.concept_id is not None}:
            raise ValueError('Todo conceito exige procedência.')
        return self

    def validate_references(
        self,
        source_documents: Sequence[SourceDocument],
        *,
        concepts: Sequence[Concept],
        papers: Sequence[Paper] = (),
    ) -> None:
        """Check against server-resolved documents, editorial concepts and real papers."""
        documents = {document.id: document for document in source_documents}
        if len(documents) != len(source_documents) or set(documents) != set(self.source_document_ids):
            raise ValueError('Documentos não correspondem ao contexto.')
        if len({document.project_id for document in source_documents}) != 1:
            raise ValueError('Documentos devem pertencer ao mesmo projeto.')
        resolved_papers = {paper.id: paper for paper in papers}
        if len(resolved_papers) != len(papers) or set(resolved_papers) != set(self.paper_ids):
            raise ValueError('Artigos não correspondem ao contexto.')
        metadata_documents = [document for document in source_documents if document.type == 'paper_metadata']
        has_material = len(metadata_documents) < len(source_documents)
        expected_origin = 'mixed' if metadata_documents and has_material else 'doi' if metadata_documents else 'material'
        if self.origin_type != expected_origin:
            raise ValueError('Tipos dos documentos não correspondem à origem do contexto.')
        by_doi = {paper.doi: paper for paper in papers}
        if {document.doi for document in metadata_documents} != set(by_doi):
            raise ValueError('Metadados não correspondem aos artigos resolvidos.')
        for document in metadata_documents:
            paper = by_doi[document.doi]
            content = paper.title + ('\n\n' + paper.abstract if paper.abstract else '')
            if document.title != paper.title or document.content != content:
                raise ValueError('Metadados devem preservar título e resumo reais do artigo.')
        known = {concept.id: concept.name for concept in concepts}
        known.update({concept.id: concept.name for paper in papers for concept in paper.concepts})
        for identifier, label in zip(self.concept_ids, self.concept_labels):
            if known.get(identifier) != label:
                raise ValueError('Conceito desconhecido ou label incompatível.')
        for provenance in self.provenance:
            document = documents[provenance.source_document_id]
            if provenance.quote is not None and provenance.quote not in document.content:
                raise ValueError('Trecho da procedência não é literal.')
            if provenance.method == 'editorial_alias':
                editorial = next((concept for concept in concepts if concept.id == provenance.concept_id), None)
                if editorial is None or provenance.quote is None or not _quoted_editorial_alias(document.content, provenance.quote, editorial.aliases):
                    raise ValueError('Procedência não corresponde a um alias editorial do conceito.')
            if provenance.retrieved_at is not None:
                paper = by_doi.get(document.doi) if document.type == 'paper_metadata' else None
                if paper is None or (provenance.retrieved_at, provenance.from_cache, provenance.source_url) != (paper.retrieved_at, paper.from_cache, paper.source_url):
                    raise ValueError('Procedência da consulta difere do artigo real.')
                if provenance.concept_id is not None and provenance.concept_id not in {concept.id for concept in paper.concepts}:
                    raise ValueError('Conceito não pertence aos metadados do artigo.')
