"""Resolve server-owned source documents without fabricating bibliographic data."""
from collections.abc import Sequence
from uuid import uuid4

from app.schemas import Concept, Paper
from app.schemas.scientific_context import Provenance, ScientificContext, SourceDocument
from .concept_analysis import editorial_alias_quote, extract_concepts
from .contribution_search import search_context_contributions
from .storage import load_json


def build_scientific_context(
    source_documents: Sequence[SourceDocument],
    *,
    papers: Sequence[Paper] = (),
    analysis_id: str | None = None,
) -> ScientificContext:
    """Resolve original material and already-retrieved papers, without network IO.

    The caller owns project/session checks and supplies canonical metadata documents
    (title, then two newlines and the real abstract when available).
    """
    if len(papers) > 1:
        raise ValueError('O MVP permite somente um artigo de comparação.')
    by_doi = {paper.doi: paper for paper in papers}
    concepts = {}
    provenance = []
    for document in source_documents:
        if document.type == 'paper_metadata':
            paper = by_doi.get(document.doi)
            if paper is None:
                raise ValueError('Metadados exigem artigo real já recuperado.')
            for concept in paper.concepts:
                concepts.setdefault(concept.id, concept)
                provenance.append(Provenance(
                    source_document_id=document.id, concept_id=concept.id, method='openalex_metadata',
                    retrieved_at=paper.retrieved_at, from_cache=paper.from_cache, source_url=paper.source_url,
                ))
            continue
        provenance.append(Provenance(
            source_document_id=document.id, method='teacher_input', quote=document.content,
        ))
        for concept in extract_concepts({'title': document.content}, None):
            concepts.setdefault(concept.id, concept)
            provenance.append(Provenance(
                source_document_id=document.id, concept_id=concept.id, method='editorial_alias',
                quote=editorial_alias_quote(document.content, concept.aliases),
            ))
    has_material = any(document.type != 'paper_metadata' for document in source_documents)
    limitations = list(papers[0].limitations) if papers else [
        'Sem artigo comparável: citação UNKNOWN. Correspondência temática não comprova influência histórica.',
    ]
    if papers and has_material:
        limitations.append('A comparação bibliográfica refere-se somente ao artigo vinculado, não ao material do professor.')
    context = ScientificContext(
        id=str(uuid4()), origin_type='mixed' if papers and has_material else 'doi' if papers else 'material',
        paper_ids=[paper.id for paper in papers], analysis_id=analysis_id,
        concept_ids=list(concepts), concept_labels=[concept.name for concept in concepts.values()],
        source_document_ids=[document.id for document in source_documents], provenance=provenance,
        limitations=limitations or ['Correspondência temática não comprova influência histórica.'],
    )
    context.validate_references(source_documents, concepts=[Concept(**entry) for entry in load_json('concepts.json')], papers=papers)
    if not search_context_contributions(context, comparison_paper=papers[0] if papers else None):
        context.limitations.append('Sem cobertura elegível neste catálogo; isto não indica inexistência de contribuições femininas.')
    return context
