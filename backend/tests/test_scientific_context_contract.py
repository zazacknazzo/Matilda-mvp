"""Public contract examples for T01; no Studio retrieval adapter is exercised."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import Concept, Paper
from app.schemas.scientific_context import ScientificContext, SourceAnchor, SourceDocument
from app.services.storage import load_json


FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/scientific'


def validate_example(example):
    documents = [SourceDocument.model_validate_json(json.dumps(d)) for d in example['source_documents']]
    papers = [Paper(**paper) for paper in example.get('papers', [])]
    context = ScientificContext.model_validate_json(json.dumps(example['scientific_context']))
    context.validate_references(documents, concepts=[Concept(**c) for c in load_json('concepts.json')], papers=papers)
    for payload in example['anchors']:
        anchor = SourceAnchor.model_validate_json(json.dumps(payload))
        document = next(document for document in documents if document.id == anchor.source_document_id)
        anchor.locate(document)
    return context


@pytest.mark.parametrize('name', ['crispr', 'rna', 'text', 'mixed', 'no-coverage', 'uncovered-text', 'rna-insufficient'])
def test_shared_examples_are_valid(name):
    validate_example(json.loads((FIXTURES / f'{name}.json').read_text()))


def set_example_value(example, path, value):
    container = example
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = value


@pytest.mark.parametrize('case', json.loads((FIXTURES / 'invalid-contexts.json').read_text()), ids=lambda c: c['name'])
def test_invalid_context_examples_are_rejected(case):
    example = json.loads((FIXTURES / (case['fixture'] + '.json')).read_text())
    set_example_value(example, case['path'], case['value'])
    with pytest.raises(ValueError, match=case['error']):
        validate_example(example)


@pytest.mark.parametrize('name', ['crispr', 'rna', 'no-coverage'])
def test_forensics_matches_frozen_baseline(client, name):
    example = json.loads((FIXTURES / f'{name}.json').read_text())
    response = client.post('/api/analyses', json={'doi': example['papers'][0]['doi']})
    assert response.status_code == 201
    analysis = response.json()
    assert analysis['paper'] == example['papers'][0]
    assert analysis['contributions'] == example['expected_matches']


@pytest.mark.parametrize('case', json.loads((FIXTURES / 'ineligible-catalog.json').read_text()), ids=lambda c: c['name'])
def test_existing_engine_rejects_ineligible_catalog_examples(monkeypatch, tmp_path, case):
    from app.services import storage
    from app.services.contribution_search import search_contributions

    # Substitute the catalog file boundary, never the eligibility implementation.
    catalogs = {name: load_json(name) for name in ['concepts.json', 'researchers.json', 'contributions.json', 'evidence.json']}
    for change in case['changes']:
        record = next(record for record in catalogs[change['catalog']] if record['id'] == change['id'])
        record[change['field']] = change['value']
    for name, records in catalogs.items():
        (tmp_path / name).write_text(json.dumps(records))
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    example = json.loads((FIXTURES / 'rna.json').read_text())
    matches = search_contributions(Paper(**example['papers'][0]))
    assert [match.contribution.id for match in matches] == case['expected_ids']


def test_immunogenicity_alone_is_not_specific_enough_for_the_existing_rna_engine():
    from app.services.contribution_search import search_contributions

    example = json.loads((FIXTURES / 'rna.json').read_text())
    paper = Paper(**example['papers'][0])
    # A real bibliographic record with only the nonspecific editorial concept.
    paper.concepts = [Concept(**next(c for c in load_json('concepts.json') if c['id'] == 'rna-immunity'))]
    assert search_contributions(paper) == []
    insufficient = json.loads((FIXTURES / 'rna-insufficient.json').read_text())
    assert validate_example(insufficient).concept_ids == ['rna-immunity']
    assert insufficient['expected_matches'] == []


@pytest.mark.parametrize('text,expected', [
    ('EDIÇÃO GENÔMICA', ['genome-editing']),
    ('CRISPRs e CRISPR-Cas9', ['crispr', 'cas9']),
    ('antiCRISPR e cas90 e conceito inexistente', []),
    ('immunogenicity', ['rna-immunity']),
])
def test_editorial_alias_baseline(text, expected):
    from app.services.concept_analysis import extract_concepts

    assert [concept.id for concept in extract_concepts({'title': text}, None)] == expected


@pytest.mark.parametrize('name', ['crispr', 'rna', 'text', 'mixed', 'no-coverage', 'uncovered-text', 'rna-insufficient'])
def test_example_matches_preserve_canonical_science_and_citation_meaning(name):
    from app.schemas import DiscoveryMatch
    from app.services.gap_analysis import bibliography_index, classify_citation

    example = json.loads((FIXTURES / f'{name}.json').read_text())
    context = validate_example(example)
    contributions = {c['id']: c for c in load_json('contributions.json')}
    evidence = {e['id']: e for e in load_json('evidence.json')}
    matches = [DiscoveryMatch(**match) for match in example['expected_matches']]
    assert matches == sorted(matches, key=lambda match: (-match.relevance, match.contribution.id))
    for match in matches:
        assert match.contribution.model_dump() == contributions[match.contribution.id]
        assert match.contribution.verification_status == 'verified'
        assert [person.id for person in match.researchers] == match.contribution.researcher_ids
        assert all(person.identity_status == 'verified' for person in match.researchers)
        assert match.evidence
        for item in match.evidence:
            assert item.model_dump() == evidence[item.id]
            assert item.contribution_id == match.contribution.id
            assert item.verification_status == 'verified'
            assert item.source_type in ('documental', 'historical')
        assert {c.id for c in match.matched_concepts} == set(match.contribution.concept_ids) & set(context.concept_ids)
        assert match.relevance == len(match.matched_concepts)
        assert match.relation_type == 'RELATED_TO'
        assert match.limitations
        if example['papers']:
            assert match.citation_status == classify_citation(Paper(**example['papers'][0]), match.contribution, bibliography_index())
        else:
            assert match.citation_status == ('UNKNOWN' if match.contribution.related_dois else 'THEMATIC_ONLY')
    if not matches:
        assert context.limitations


@pytest.mark.parametrize('change', [{'quote': ''}, {'quote': '  '}, {'occurrence': True}, {'occurrence': 1.0}, {'unexpected': 1}])
def test_anchor_rejects_invalid_shapes(change):
    payload = {'source_document_id': 'doc-text', 'quote': 'CRISPR', 'occurrence': 0}
    with pytest.raises(ValidationError):
        SourceAnchor.model_validate_json(json.dumps(payload | change))


def test_anchor_counts_overlapping_literal_occurrences_and_checks_document_identity():
    document = SourceDocument(id='doc', project_id='project', type='text', title='Original', content='ababa')
    anchor = SourceAnchor(source_document_id='doc', quote='aba', occurrence=1)
    assert anchor.locate(document) == (2, 5)
    with pytest.raises(ValueError, match='outro documento'):
        anchor.locate(document.model_copy(update={'id': 'other'}))


def test_resolved_editorial_alias_cannot_claim_a_different_concept():
    example = json.loads((FIXTURES / 'text.json').read_text())
    example['scientific_context']['provenance'][0]['quote'] = 'edição genômica'
    with pytest.raises(ValueError, match='alias'):
        validate_example(example)


def test_text_context_preserves_original_without_a_paper():
    example = json.loads((FIXTURES / 'text.json').read_text())
    documents = [SourceDocument.model_validate_json(json.dumps(d)) for d in example['source_documents']]
    context = ScientificContext.model_validate_json(json.dumps(example['scientific_context']))
    context.validate_references(documents, concepts=[Concept(**c) for c in load_json('concepts.json')])
    anchor = SourceAnchor.model_validate_json(json.dumps(example['anchors'][0]))

    assert context.paper_ids == []
    assert context.analysis_id is None
    assert documents[0].content == 'CRISPR permite estudar edição genômica. CRISPR será discutido em grupo.'
    assert anchor.locate(documents[0]) == (40, 46)
    assert context.model_dump(mode='json') == example['scientific_context']


@pytest.mark.parametrize('change', [
    {'concept_labels': []},
    {'concept_ids': ['crispr', 'crispr']},
    {'source_document_ids': ['doc-text', 'doc-text']},
    {'paper_ids': ['https://openalex.org/W1']},
    {'analysis_id': 'invented-analysis'},
    {'provenance': []},
])
def test_material_rejects_inconsistent_context(change):
    payload = json.loads((FIXTURES / 'text.json').read_text())['scientific_context']
    with pytest.raises(ValidationError):
        ScientificContext.model_validate_json(json.dumps(payload | change))


@pytest.mark.parametrize('change', [
    {'content': 'x' * 20001},
    {'doi': 'https://evil.test/not-a-doi'},
    {'type': 'paper_metadata'},
    {'content': '   '},
    {'type': 'concept_list', 'content': '\n'.join(['CRISPR'] * 21)},
    {'type': 'concept_list', 'content': 'x' * 101},
    {'unexpected': True},
    {'id': 123},
])
def test_source_document_rejects_invalid_input(change):
    document = json.loads((FIXTURES / 'text.json').read_text())['source_documents'][0]
    with pytest.raises(ValidationError):
        SourceDocument.model_validate_json(json.dumps(document | change))


@pytest.mark.parametrize('change', [
    {'retrieved_at': '2026-10-21T12:00:00'},
    {'retrieved_at': 'not-a-date'},
    {'retrieved_at': '2026-10-21T12:00:00Z'},
    {'method': 'openalex_metadata'},
    {'from_cache': 'true'},
])
def test_provenance_rejects_incomplete_or_non_utc_retrieval(change):
    from app.schemas.scientific_context import Provenance
    provenance = json.loads((FIXTURES / 'text.json').read_text())['scientific_context']['provenance'][0]
    with pytest.raises(ValidationError):
        Provenance.model_validate_json(json.dumps(provenance | change))
