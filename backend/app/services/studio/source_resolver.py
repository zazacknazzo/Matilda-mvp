"""T06 source resolution, independent of the Studio host/repository/provider.

Inputs are server-owned. The Studio caller enforces session/project ownership
and persists the returned snapshot at admission/publication, never just a link.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException

from app.integrations.openalex import retrieve_paper
from app.schemas import Analysis, DiscoveryMatch, Paper
from app.schemas.scientific_context import ScientificContext, SourceDocument
from app.services.contribution_search import search_context_contributions
from app.services.scientific_context import build_scientific_context
from app.services.storage import get_analysis


@dataclass(frozen=True)
class ResolvedScientificSource:
    """Composition of M0 models, not a new HTTP contract or client authority."""
    scientific_context: ScientificContext
    source_documents: list[SourceDocument]
    papers: list[Paper]
    matches: list[DiscoveryMatch]

    def snapshot(self) -> dict:
        """Detached JSON data; usable without re-reading a retained investigation."""
        return {
            'scientific_context': self.scientific_context.model_dump(mode='json'),
            'source_documents': [document.model_dump(mode='json') for document in self.source_documents],
            'papers': [paper.model_dump(mode='json') for paper in self.papers],
            'matches': [match.model_dump(mode='json') for match in self.matches],
        }


async def resolve_scientific_source(
    *, project_id: str, doi: str | None = None, analysis_id: str | None = None,
    documents: Sequence[SourceDocument] = (),
) -> ResolvedScientificSource:
    """Resolve material/DOI/investigation through existing Forensics and T04.

    HTTPException preserves Forensics status/detail; an HTTP Studio caller adapts
    only the envelope. No investigation or graph is fabricated for material.
    """
    if doi is not None and analysis_id is not None:
        raise HTTPException(422, 'Informe DOI ou investigação, nunca ambos.')
    if analysis_id is not None and not analysis_id.strip():
        raise HTTPException(422, 'Identificador de investigação inválido.')
    if doi is None and analysis_id is None and not documents:
        raise HTTPException(422, 'Informe material, DOI ou investigação.')
    if not project_id.strip() or any(document.project_id != project_id for document in documents):
        raise ValueError('Documentos devem pertencer ao projeto de destino.')
    if any(document.type == 'paper_metadata' for document in documents):
        raise ValueError('Metadados são construídos somente a partir do artigo resolvido.')
    source_documents = [document.model_copy(deep=True) for document in documents]
    analysis = None
    if analysis_id is not None:
        stored = get_analysis(analysis_id)
        if stored is None:
            raise HTTPException(404, 'Investigação não encontrada ou expirada (retenção: 7 dias).')
        analysis = Analysis.model_validate(stored)
        papers = [analysis.paper]
    else:
        papers = [await retrieve_paper(doi)] if doi is not None else []
    if papers:
        paper = papers[0]
        source_documents.append(SourceDocument(
            id=str(uuid4()), project_id=project_id, type='paper_metadata',
            title=paper.title, content=paper.title + ('\n\n' + paper.abstract if paper.abstract else ''), doi=paper.doi,
        ))
    context = build_scientific_context(source_documents, papers=papers, analysis_id=analysis_id)
    if analysis is not None:
        context.limitations = list(dict.fromkeys([*context.limitations, *analysis.coverage_warnings]))
    # An unchanged investigation is a recorded scientific snapshot, not a request
    # to silently replace its participants/claims with a later catalog revision.
    matches = analysis.contributions if analysis is not None and not documents else search_context_contributions(
        context, comparison_paper=papers[0] if papers else None,
    )
    return ResolvedScientificSource(context, source_documents, papers, matches)
