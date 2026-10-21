from app.schemas import Concept, Contribution, Evidence, Researcher, DiscoveryMatch, Paper
from app.schemas.scientific_context import ScientificContext
from .storage import load_json
from .gap_analysis import bibliography_index, classify_citation

def search_contributions(paper):
    """Compatible Forensics entry point; keep its serialized matches unchanged."""
    return _search_contributions(paper.concepts, paper)


def search_context_contributions(
    context: ScientificContext,
    *,
    comparison_paper: Paper | None = None,
) -> list[DiscoveryMatch]:
    """Retrieve from a server-validated context; compare only its linked paper."""
    if comparison_paper is not None and comparison_paper.id not in context.paper_ids:
        raise ValueError('O artigo de comparação não pertence ao contexto.')
    editorial = {entry['id']: Concept(**entry) for entry in load_json('concepts.json')}
    paper_concepts = {concept.id: concept for concept in comparison_paper.concepts} if comparison_paper else {}
    concepts = []
    for identifier, label in zip(context.concept_ids, context.concept_labels):
        concept = paper_concepts.get(identifier) or editorial.get(identifier)
        if concept is None:
            continue
        if concept.name != label:
            raise ValueError('Label incompatível com o conceito resolvido.')
        provenance = list(concept.provenance)
        provenance.extend(
            f'material docente: {item.source_document_id} (editorial_alias)'
            for item in context.provenance
            if item.concept_id == identifier and item.method == 'editorial_alias'
        )
        concepts.append(concept.model_copy(update={'provenance': list(dict.fromkeys(provenance))}))
    matches = _search_contributions(concepts, comparison_paper)
    if comparison_paper is not None and context.origin_type == 'mixed':
        for match in matches:
            if any(concept.id not in paper_concepts for concept in match.matched_concepts):
                names = ', '.join(concept.name for concept in match.matched_concepts)
                match.explanation = f'O contexto inclui conceitos do material relacionados a esta contribuição: {names}. A fonte documenta a contribuição; a correspondência temática não comprova influência histórica.'
                match.limitations[0] = 'A conexão com os conceitos do material não comprova influência histórica direta.'
            match.limitations.append('A comparação bibliográfica refere-se somente ao artigo vinculado, não ao material do professor.')
    return matches


def _search_contributions(resolved_concepts, paper):
    contributions = [Contribution(**x) for x in load_json('contributions.json')]
    evidence = [Evidence(**x) for x in load_json('evidence.json')]
    people = {x['id']: Researcher(**x) for x in load_json('researchers.json')}
    index = bibliography_index()
    matches = []
    for contribution in contributions:
        concepts = [c for c in resolved_concepts if c.id in contribution.concept_ids]
        sources = [e for e in evidence if e.contribution_id == contribution.id and e.verification_status == 'verified' and e.source_type in ('documental', 'historical')]
        researchers = [people[i] for i in contribution.researcher_ids]
        if contribution.scientific_field == 'Biologia molecular e RNA' and not any(c.id in ('mrna', 'nucleoside') for c in concepts):
            continue
        if not concepts or not sources or contribution.verification_status != 'verified' or any(r.identity_status != 'verified' for r in researchers):
            continue
        names = ', '.join(c.name for c in concepts)
        status = classify_citation(paper, contribution, index)
        limitations = ['A contribuição está documentada; a conexão conceitual com o artigo não comprova influência histórica direta.', 'A autoria é coletiva. A lista de participantes preserva os coautores da publicação associada.']
        if status == 'NOT_FOUND_IN_RETRIEVED_REFERENCES':
            limitations.append('Publicação não localizada apenas nas referências recuperadas; a bibliografia completa não foi auditada.')
        if status == 'UNKNOWN':
            limitations.append('Dados insuficientes para determinar citação; o artigo não pode citar a si próprio.')
        explanation = f'O artigo e esta contribuição compartilham os conceitos: {names}. A fonte documenta a contribuição descrita. Essa correspondência é temática; uma citação, quando identificada, é registrada separadamente.'
        if paper is None:
            explanation = 'Contribuição documentada relacionada aos conceitos do material. Não há artigo comparável; correspondência temática não comprova influência histórica.'
            limitations = ['Sem artigo comparável: dados insuficientes para determinar citação.', 'A autoria é coletiva; participantes canônicos preservados.', 'Correspondência temática não comprova influência histórica direta.']
        matches.append(DiscoveryMatch(contribution=contribution, researchers=researchers, evidence=sources, matched_concepts=concepts, citation_status=status, explanation=explanation, limitations=limitations, relevance=len(concepts)))
    return sorted(matches, key=lambda m: (-m.relevance, m.contribution.id))
