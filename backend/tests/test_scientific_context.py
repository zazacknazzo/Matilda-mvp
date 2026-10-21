"""Behavior at T04's context boundary, using the shared M0 examples."""
import json
from pathlib import Path

import pytest

from app.schemas import Paper
from app.schemas.scientific_context import ScientificContext, SourceDocument


FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/scientific'


def example(name):
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def test_text_recovers_canonical_matches_without_a_paper():
    from app.services.contribution_search import search_context_contributions

    payload = example('text')
    context = ScientificContext.model_validate(payload['scientific_context'])
    matches = search_context_contributions(context)

    assert [match.model_dump(mode='json') for match in matches] == payload['expected_matches']


def test_material_resolves_editorial_aliases_with_literal_provenance():
    from app.services.scientific_context import build_scientific_context

    document = SourceDocument(
        id='doc', project_id='project', type='text', title='Material',
        content='CRISPRs: EDIÇÃO GENÔMICA e CRISPR-Cas9. antiCRISPR e cas90 não são aliases.',
    )
    context = build_scientific_context([document])

    assert context.id
    assert context.origin_type == 'material'
    assert context.paper_ids == []
    assert context.analysis_id is None
    assert context.concept_ids == ['crispr', 'cas9', 'genome-editing']
    assert context.concept_labels == ['CRISPR', 'Cas9', 'Edição genômica']
    assert {(p.concept_id, p.quote) for p in context.provenance if p.method == 'editorial_alias'} == {
        ('crispr', 'CRISPR'), ('cas9', 'Cas9'), ('genome-editing', 'EDIÇÃO GENÔMICA'),
    }
    assert all(p.source_document_id == 'doc' for p in context.provenance)
    assert document.content == 'CRISPRs: EDIÇÃO GENÔMICA e CRISPR-Cas9. antiCRISPR e cas90 não são aliases.'


@pytest.mark.parametrize('content,expected_ids', [
    ('Dinâmica de fluidos em uma tubulação.', []),
    ('antiCRISPR e cas90 e termo inexistente', []),
    ('Immunogenicity', ['rna-immunity']),
])
def test_uncovered_material_has_explicit_empty_results(content, expected_ids):
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    document = SourceDocument(id='doc', project_id='project', type='text', title='Material', content=content)
    context = build_scientific_context([document])

    assert context.concept_ids == expected_ids
    assert search_context_contributions(context) == []
    assert any('não indica inexistência de contribuições femininas' in limitation for limitation in context.limitations)
    assert any(p.method == 'teacher_input' and p.quote == content for p in context.provenance)


@pytest.mark.parametrize('name', ['crispr', 'rna', 'no-coverage'])
def test_doi_context_reuses_investigation_and_preserves_frozen_matches(client, monkeypatch, name):
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    payload = example(name)
    response = client.post('/api/analyses', json={'doi': payload['papers'][0]['doi']})
    assert response.status_code == 201
    analysis = response.json()
    paper = Paper.model_validate(analysis['paper'])
    documents = [SourceDocument.model_validate(d) for d in payload['source_documents']]

    context = build_scientific_context(documents, papers=[paper], analysis_id=analysis['id'])
    matches = search_context_contributions(context, comparison_paper=paper)

    assert context.origin_type == 'doi'
    assert context.paper_ids == [paper.id]
    assert context.analysis_id == analysis['id']
    assert context.concept_ids == [c.id for c in paper.concepts]
    assert [match.model_dump(mode='json') for match in matches] == payload['expected_matches'] == analysis['contributions']
    assert all((p.retrieved_at, p.from_cache, p.source_url) == (paper.retrieved_at, True, paper.source_url) for p in context.provenance)
    assert all(limitation in context.limitations for limitation in paper.limitations)


def test_mixed_context_keeps_material_provenance_and_compares_only_linked_paper():
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    payload = example('mixed')
    paper = Paper.model_validate(payload['papers'][0])
    documents = [SourceDocument.model_validate(d) for d in payload['source_documents']]
    context = build_scientific_context(documents, papers=[paper])
    matches = search_context_contributions(context, comparison_paper=paper)

    assert context.origin_type == 'mixed'
    assert context.concept_ids == payload['scientific_context']['concept_ids']
    assert any(p.concept_id == 'mrna' and p.source_document_id == 'doc-mixed-material' and p.quote == 'RNA mensageiro' for p in context.provenance)
    # M0's mixed example has illustrative editorial prose ("artigo de CRISPR").
    # Compare all scientific fields and verify the bibliographic scope separately.
    scientific_fields = ('contribution', 'researchers', 'evidence', 'matched_concepts', 'relation_type', 'citation_status', 'relevance')
    assert [dict((key, match.model_dump(mode='json')[key]) for key in scientific_fields) for match in matches] == [
        {key: match[key] for key in scientific_fields} for match in payload['expected_matches']
    ]
    rna_match = next(match for match in matches if match.contribution.id == 'rna-2005')
    assert 'material' in rna_match.explanation
    assert 'O artigo e esta contribuição compartilham' not in rna_match.explanation
    assert any('somente ao artigo vinculado, não ao material' in limitation for limitation in context.limitations)


@pytest.mark.parametrize('content', ['RNA mensageiro', 'modified nucleosides'])
def test_specific_rna_material_is_eligible(content):
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    document = SourceDocument(id='doc', project_id='project', type='concept_list', title='Conceitos', content=content)
    context = build_scientific_context([document])
    matches = search_context_contributions(context)

    assert [match.contribution.id for match in matches] == ['rna-2005', 'rna-2008']
    assert all(match.citation_status == 'UNKNOWN' and match.relation_type == 'RELATED_TO' for match in matches)


def test_decomposed_accents_preserve_literal_material_quotes():
    from app.services.scientific_context import build_scientific_context

    content = 'EDIC\u0327A\u0303O GENO\u0302MICA'
    document = SourceDocument(id='doc', project_id='project', type='text', title='Material', content=content)
    context = build_scientific_context([document])

    assert context.concept_ids == ['genome-editing']
    assert next(p.quote for p in context.provenance if p.concept_id == 'genome-editing') == content


@pytest.mark.parametrize('case', example('ineligible-catalog'), ids=lambda case: case['name'])
def test_context_uses_the_same_documentary_eligibility(monkeypatch, tmp_path, case):
    from app.services import storage
    from app.services.storage import load_json
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    # The filesystem is the catalog boundary; exercise the real selection code.
    catalogs = {name: load_json(name) for name in ('concepts.json', 'researchers.json', 'contributions.json', 'evidence.json')}
    for change in case['changes']:
        record = next(record for record in catalogs[change['catalog']] if record['id'] == change['id'])
        record[change['field']] = change['value']
    for name, records in catalogs.items():
        (tmp_path / name).write_text(json.dumps(records), encoding='utf-8')
    monkeypatch.setattr(storage, 'DATA', tmp_path)

    document = SourceDocument(id='doc', project_id='project', type='text', title='Material', content='RNA mensageiro')
    context = build_scientific_context([document])
    matches = search_context_contributions(context)

    assert [match.contribution.id for match in matches] == case['expected_ids']
    if not matches:
        assert any('Sem cobertura elegível' in limitation for limitation in context.limitations)


def test_context_without_comparable_paper_keeps_thematic_only_for_no_publication(monkeypatch, tmp_path):
    from app.services import storage
    from app.services.storage import load_json
    from app.services.scientific_context import build_scientific_context
    from app.services.contribution_search import search_context_contributions

    for name in ('concepts.json', 'researchers.json', 'contributions.json', 'evidence.json'):
        records = load_json(name)
        if name == 'contributions.json':
            for record in records:
                record['related_dois'] = []
        (tmp_path / name).write_text(json.dumps(records), encoding='utf-8')
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    document = SourceDocument(id='doc', project_id='project', type='text', title='Material', content='RNA mensageiro')
    matches = search_context_contributions(build_scientific_context([document]))

    assert len(matches) == 2
    assert all(match.citation_status == 'THEMATIC_ONLY' for match in matches)


def test_unrelated_comparison_paper_is_rejected():
    from app.services.contribution_search import search_context_contributions

    context = ScientificContext.model_validate(example('text')['scientific_context'])
    paper = Paper.model_validate(example('crispr')['papers'][0])
    with pytest.raises(ValueError, match='não pertence ao contexto'):
        search_context_contributions(context, comparison_paper=paper)


def test_context_refuses_modified_bibliographic_documents():
    from app.services.scientific_context import build_scientific_context

    payload = example('crispr')
    paper = Paper.model_validate(payload['papers'][0])
    document = SourceDocument.model_validate(payload['source_documents'][0])
    document.content += '\nRNA mensageiro'
    with pytest.raises(ValueError, match='preservar título e resumo reais'):
        build_scientific_context([document], papers=[paper])
