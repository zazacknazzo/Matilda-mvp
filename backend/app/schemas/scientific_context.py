"""Additive M0 contracts. No retrieval, network access or Studio endpoints.

Parse shape first, then call validate_sources/validate_source with server-owned
records. A well-shaped ID alone is never proof of a scientific source.
"""
from datetime import datetime, timedelta
from typing import Annotated, Literal, Protocol, Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Concept, DiscoveryMatch, Paper

Identifier = Annotated[str, Field(min_length=1, pattern=r'\S')]
Quote = Annotated[str, Field(min_length=1, max_length=20_000, pattern=r'\S')]


class ContextModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class SourceDocument(ContextModel):
    id: Identifier
    project_id: Identifier
    type: Literal['text', 'concept_list', 'paper_metadata']
    title: Annotated[str, Field(min_length=1, max_length=160, pattern=r'\S')]
    content: Quote
    doi: str | None = None
    extraction_status: Literal['ready'] = 'ready'

    @field_validator('doi')
    @classmethod
    def valid_doi(cls, value):
        if value is not None:
            # Same effective 250-character limit and URL policy as Forensics.
            from fastapi import HTTPException
            from app.integrations.openalex import normalize_doi
            try:
                if normalize_doi(value) != value:
                    raise ValueError('Use o DOI canônico normalizado do Forensics.')
            except HTTPException as exc:
                raise ValueError('DOI inválido.') from exc
        return value

    @model_validator(mode='after')
    def document_kind(self):
        if self.type == 'paper_metadata' and self.doi is None:
            raise ValueError('Metadados exigem DOI real.')
        if self.type == 'concept_list':
            entries = self.content.splitlines()
            if not 1 <= len(entries) <= 20 or any(not x.strip() or len(x) > 100 for x in entries):
                raise ValueError('Conceitos: 1–20 linhas não vazias, até 100 caracteres cada.')
        return self


class Provenance(ContextModel):
    source_document_id: Identifier
    concept_id: Identifier | None = None
    method: Literal['teacher_input', 'editorial_alias', 'openalex_metadata', 'ai_suggested']
    quote: Quote | None = None
    retrieved_at: str | None = None
    from_cache: bool | None = None
    source_url: str | None = None

    @field_validator('retrieved_at')
    @classmethod
    def utc_date(cls, value):
        if value is not None:
            try:
                stamp = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError('Data ISO 8601 UTC exigida.') from exc
            if 'T' not in value or stamp.utcoffset() != timedelta(0):
                raise ValueError('Data ISO 8601 UTC exigida.')
        return value

    @field_validator('source_url')
    @classmethod
    def http_url(cls, value):
        if value is not None:
            parts = urlsplit(value)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
                raise ValueError('URL científica HTTP(S) sem credenciais exigida.')
        return value

    @model_validator(mode='after')
    def scientific_source(self):
        remote = (self.retrieved_at, self.from_cache, self.source_url)
        if self.method == 'openalex_metadata' or any(x is not None for x in remote):
            if any(x is None for x in remote):
                raise ValueError('Consulta científica exige data, cache e URL juntos.')
        if self.method == 'ai_suggested' and self.concept_id is not None:
            raise ValueError('Sugestão de IA não resolve ID científico.')
        return self


class SourceAnchor(ContextModel):
    source_document_id: Identifier
    quote: Quote
    occurrence: Annotated[int, Field(ge=0)]

    def validate_source(self, document: SourceDocument) -> None:
        if document.id != self.source_document_id:
            raise ValueError('Âncora aponta para outro documento.')
        # Occurrences are literal, case sensitive, left to right, non-overlapping.
        if self.occurrence >= document.content.count(self.quote):
            raise ValueError('Trecho ou ocorrência não existe no documento original.')


class ScientificContext(ContextModel):
    id: Identifier
    origin_type: Literal['doi', 'material', 'mixed']
    paper_ids: list[Identifier] = Field(default_factory=list)
    concept_ids: list[Identifier] = Field(default_factory=list)
    concept_labels: list[Identifier] = Field(default_factory=list)
    source_document_ids: list[Identifier] = Field(min_length=1)
    provenance: list[Provenance] = Field(min_length=1)
    limitations: list[Identifier] = Field(default_factory=list)
    analysis_id: Identifier | None = None

    @model_validator(mode='after')
    def relationships(self):
        for values in (self.paper_ids, self.concept_ids, self.source_document_ids):
            if len(values) != len(set(values)):
                raise ValueError('IDs duplicados no contexto.')
        if len(self.concept_ids) != len(self.concept_labels):
            raise ValueError('Labels devem estar alinhados aos IDs por posição.')
        if self.origin_type == 'material' and (self.paper_ids or self.analysis_id is not None):
            raise ValueError('Material sem DOI não cria Paper nem investigação.')
        if self.origin_type in ('doi', 'mixed') and len(self.paper_ids) != 1:
            raise ValueError('Contexto DOI/misto exige um artigo comparável.')
        for source in self.provenance:
            if source.source_document_id not in self.source_document_ids:
                raise ValueError('Procedência de documento fora do contexto.')
            if source.concept_id is not None and source.concept_id not in self.concept_ids:
                raise ValueError('Procedência de conceito fora do contexto.')
        for concept_id in self.concept_ids:
            if not any(p.concept_id == concept_id for p in self.provenance):
                raise ValueError('Conceito sem procedência.')
        if not self.concept_ids and not self.limitations:
            raise ValueError('Sem cobertura exige limitação explícita.')
        return self

    def validate_sources(
        self, *, source_documents: Sequence[SourceDocument],
        concepts: Sequence[Concept], papers: Sequence[Paper] = (),
    ) -> None:
        """Check foreign keys against resolved, server-owned records, never AI data."""
        documents = {d.id: d for d in source_documents}
        if len(documents) != len(source_documents) or set(documents) != set(self.source_document_ids):
            raise ValueError('Documentos ausentes, extras ou duplicados.')
        if len({d.project_id for d in source_documents}) != 1:
            raise ValueError('Documentos devem pertencer ao mesmo projeto.')
        actual_papers = {p.id: p for p in papers}
        if len(actual_papers) != len(papers) or set(actual_papers) != set(self.paper_ids):
            raise ValueError('Artigos reais não coincidem com o contexto.')
        resolved = {c.id: c for c in concepts}
        if any(cid not in resolved or resolved[cid].name != label for cid, label in zip(self.concept_ids, self.concept_labels)):
            raise ValueError('Conceito desconhecido ou label incompatível com a fonte resolvida.')
        kinds = {d.type for d in source_documents}
        if (self.origin_type == 'doi' and kinds != {'paper_metadata'}
                or self.origin_type == 'material' and 'paper_metadata' in kinds
                or self.origin_type == 'mixed' and ('paper_metadata' not in kinds or len(kinds) < 2)):
            raise ValueError('Origem incompatível com os documentos.')
        for document in source_documents:
            if document.type == 'paper_metadata' and not any(
                p.doi == document.doi and document.title == p.title
                and document.content in (p.title, p.title + '\n\n' + (p.abstract or ''))
                for p in papers
            ):
                raise ValueError('Metadados sem artigo real correspondente.')
        for source in self.provenance:
            document = documents[source.source_document_id]
            if source.quote is not None and source.quote not in document.content:
                raise ValueError('Citação de procedência não é literal.')
            if source.concept_id is not None and source.method in ('editorial_alias', 'teacher_input'):
                from app.services.concept_analysis import contains
                if not any(contains(document.title + ' ' + document.content, alias)
                           for alias in resolved[source.concept_id].aliases):
                    raise ValueError('Conceito sem correspondência editorial no documento.')
            if source.method == 'openalex_metadata' and not any(
                document.type == 'paper_metadata' and p.doi == document.doi
                and source.source_url == p.source_url and source.retrieved_at == p.retrieved_at
                and source.from_cache == p.from_cache
                and (source.concept_id is None or source.concept_id in {c.id for c in p.concepts})
                for p in papers
            ):
                raise ValueError('Procedência OpenAlex não coincide com o artigo recuperado.')


class ScientificRetriever(Protocol):
    """Target seam for T04; declaration only. Inputs must pass source validation.

    comparable_paper is required for doi/mixed and absent for material. Only its
    bibliography is comparable. Preserve DiscoveryMatch and deterministic order.
    """
    def __call__(
        self, context: ScientificContext, *, comparable_paper: Paper | None = None,
    ) -> list[DiscoveryMatch]: ...
