"""M0 contract tests use only checked-in catalogs/snapshots, never external APIs."""
import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.openalex import parse_paper
from app.schemas import Concept, Contribution, DiscoveryMatch, Evidence, Researcher
from app.schemas.scientific_context import ScientificContext, SourceAnchor, SourceDocument, Provenance
from app.services.concept_analysis import contains, extract_concepts
from app.services.contribution_search import search_contributions
from app.services.gap_analysis import bibliography_index, classify_citation
from app.services.storage import DATA, load_json

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/scientific'
SCENARIOS = ['crispr-doi', 'rna-doi', 'text-no-doi', 'mixed', 'no-coverage', 'rna-insufficient', 'rna-material']


def read(name):
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def get_paper(doi):
    raw = json.loads((DATA / 'openalex_snapshots' / f'{doi.replace("/", "_")}.json').read_text(encoding='utf-8'))
    return parse_paper(raw['data'], doi, raw['retrieved_at'], from_cache=True)


def validate_fixture(value):
    documents = [SourceDocument.model_validate(d) for d in value['source_documents']]
    context = ScientificContext.model_validate(value['scientific_context'])
    papers = [get_paper(doi) for doi in value['paper_dois']]
    # Only editorial records and topics actually returned by the linked snapshot
    # can resolve IDs; the context itself is never its own authority.
    concepts = [Concept(**c) for c in load_json('concepts.json')]
    concepts.extend(c for p in papers for c in p.concepts)
    context.validate_sources(source_documents=documents, concepts=concepts, papers=papers)
    by_id = {d.id: d for d in documents}
    for raw in value['anchors']:
        anchor = SourceAnchor.model_validate(raw)
        anchor.validate_source(by_id[anchor.source_document_id])
    for source in context.provenance:
        if source.method == 'editorial_alias':
            canonical = next(c for c in concepts if c.id == source.concept_id)
            document = by_id[source.source_document_id]
            assert any(contains(document.content + ' ' + document.title, alias) for alias in canonical.aliases)
    for raw in value['expected_matches']:
        validate_match(raw, context, papers)
    return context


def validate_match(raw, context, papers):
    """Fixture audit, not a second production selection/retrieval engine."""
    match = DiscoveryMatch.model_validate(raw)
    contribution = match.contribution
    assert contribution.model_dump() == next(c for c in load_json('contributions.json') if c['id'] == contribution.id)
    assert contribution.verification_status == 'verified'
    assert [r.id for r in match.researchers] == contribution.researcher_ids
    people = {r['id']: r for r in load_json('researchers.json')}
    for person in match.researchers:
        assert person.model_dump() == Researcher(**people[person.id]).model_dump()
        assert person.identity_status == 'verified'
    assert match.evidence
    evidence = {e['id']: e for e in load_json('evidence.json')}
    for source in match.evidence:
        assert source.model_dump() == evidence[source.id]
        assert source.contribution_id == contribution.id
        assert source.verification_status == 'verified'
        assert source.source_type in ('documental', 'historical')
    assert match.matched_concepts
    assert {c.id for c in match.matched_concepts} <= set(context.concept_ids) & set(contribution.concept_ids)
    assert match.relation_type == 'RELATED_TO'
    expected = classify_citation(papers[0], contribution, bibliography_index()) if papers else (
        'UNKNOWN' if contribution.related_dois else 'THEMATIC_ONLY'
    )
    assert match.citation_status == expected
    if contribution.scientific_field == 'Biologia molecular e RNA':
        assert any(c.id in ('mrna', 'nucleoside') for c in match.matched_concepts)


@pytest.mark.parametrize('name', SCENARIOS)
def test_shared_valid_examples(name):
    value = read(name)
    context = validate_fixture(value)
    # JSON serialization preserves snake_case, explicit nulls, and all literals.
    assert ScientificContext.model_validate_json(context.model_dump_json()) == context


@pytest.mark.parametrize('case', read('invalid'), ids=lambda c: c['name'])
def test_shared_invalid_examples(case):
    value = read(case['fixture'])
    if case['target'] == 'context':
        target = value['scientific_context']
    elif case['target'] == 'anchor':
        target = value['anchors'][0]
    elif case['target'] == 'matches':
        target = value
    else:
        target = value['expected_matches'][0]
    for key in case['path'][:-1]:
        target = target[key]
    target[case['path'][-1]] = case['value']
    with pytest.raises((ValueError, AssertionError)):
        validate_fixture(value)


@pytest.mark.parametrize('doi,expected', read('forensics-baseline').items())
def test_all_current_forensics_snapshots_unchanged(doi, expected):
    assert [m.model_dump(mode='json') for m in search_contributions(get_paper(doi))] == expected


@pytest.mark.parametrize('name', ['crispr-doi', 'rna-doi'])
def test_doi_fixtures_match_real_http_contract(client, name):
    value = read(name)
    response = client.post('/api/analyses', json={'doi': value['paper_dois'][0]})
    assert response.status_code == 201
    assert response.json()['contributions'] == value['expected_matches']


def test_material_has_no_fictional_paper_and_unknown_is_not_absence():
    value = read('text-no-doi')
    context = validate_fixture(value)
    assert context.paper_ids == [] and value['paper_dois'] == []
    assert value['expected_matches']
    assert {m['citation_status'] for m in value['expected_matches']} == {'UNKNOWN'}


def test_mixed_bibliography_is_only_the_linked_paper():
    value = read('mixed')
    validate_fixture(value)
    rna = [m for m in value['expected_matches'] if 'mrna' in m['contribution']['concept_ids']]
    assert rna
    for match in rna:
        assert match['citation_status'] == classify_citation(
            get_paper(value['paper_dois'][0]), Contribution(**match['contribution']), bibliography_index()
        )
    sources = value['scientific_context']['provenance']
    assert any(p.get('concept_id') == 'mrna' and p['method'] == 'editorial_alias' for p in sources)
    assert not any(p.get('concept_id') == 'mrna' and p['method'] == 'openalex_metadata' for p in sources)


@pytest.mark.parametrize('name', ['no-coverage', 'rna-insufficient'])
def test_zero_scientific_suggestions_has_explicit_coverage_limit(name):
    value = read(name)
    assert value['expected_matches'] == []
    assert validate_fixture(value).limitations


@pytest.mark.parametrize('text,expected', [
    ('EDIÇÃO GENÔMICA', {'genome-editing'}), ('crisprs', {'crispr'}),
    ('microcrispr semimrna', set()), ('RNA', set()),
    ('immunogenicity', {'rna-immunity'}), ('RNA mensageiro', {'mrna'}),
])
def test_aliases_normalization_and_word_boundaries_are_forensics(text, expected):
    assert {c.id for c in extract_concepts({'title': text}, None)} == expected


def test_rna_insufficient_and_unknown_concepts_do_not_pass_forensics():
    paper = get_paper('10.1056/nejmoa2034577')
    for concept in [Concept(id='rna-immunity', name='Reconhecimento imune de RNA'),
                    Concept(id='unknown', name='Não resolvido')]:
        assert search_contributions(paper.model_copy(update={'concepts': [concept]})) == []


@pytest.mark.parametrize('case', [c for c in read('invalid') if c['target'] == 'eligibility'], ids=lambda c: c['name'])
def test_existing_engine_rejects_invalid_catalog_records(monkeypatch, case):
    from app.services import contribution_search
    value = read(case['fixture'])['expected_matches'][0]
    data = copy.deepcopy(value)
    target = data
    for key in case['path'][:-1]:
        target = target[key]
    target[case['path'][-1]] = case['value']
    # Isolate the selected contribution so another verified source cannot mask the case.
    records = {'contributions.json': [data['contribution']], 'evidence.json': [data['evidence'][0]],
               'researchers.json': data['researchers']}
    original = contribution_search.load_json
    monkeypatch.setattr(contribution_search, 'load_json', lambda name: records.get(name) if name in records else original(name))
    assert search_contributions(get_paper(read(case['fixture'])['paper_dois'][0])) == []


@pytest.mark.parametrize('model,payload', [
    (SourceAnchor, {'source_document_id': 'doc', 'quote': 'x', 'occurrence': -1}),
    (SourceAnchor, {'source_document_id': 'doc', 'quote': 'x', 'occurrence': True}),
    (SourceAnchor, {'source_document_id': 'doc', 'quote': 'x', 'occurrence': '0'}),
    (SourceAnchor, {'source_document_id': 'doc', 'quote': ' ', 'occurrence': 0}),
    (Provenance, {'source_document_id': 'doc', 'method': 'ai_suggested', 'concept_id': 'crispr'}),
    (Provenance, {'source_document_id': 'doc', 'method': 'openalex_metadata'}),
    (Provenance, {'source_document_id': 'doc', 'method': 'teacher_input', 'from_cache': False}),
])
def test_strict_types_and_invariants(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize('model,payload', [
    (ScientificContext, read('text-no-doi')['scientific_context']),
    (SourceDocument, read('text-no-doi')['source_documents'][0]),
    (SourceAnchor, read('text-no-doi')['anchors'][0]),
    (Provenance, read('text-no-doi')['scientific_context']['provenance'][0]),
])
def test_new_models_reject_extra_fields(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate({**payload, 'unexpected': 'value'})


@pytest.mark.parametrize('field,value', [
    ('content', 'x' * 20_001), ('title', 'x' * 161), ('doi', '10.1234/' + 'x' * 243),
    ('doi', 'https://evil.test/x'), ('doi', '10.1234/a b'),
    ('type', 'pdf'), ('content', ''),
])
def test_document_limits(field, value):
    document = read('text-no-doi')['source_documents'][0]
    document[field] = value
    with pytest.raises(ValidationError):
        SourceDocument.model_validate(document)


def test_document_boundary_and_immutable_literal_content():
    document = SourceDocument(id='doc', project_id='project', type='text', title='x' * 160, content=' ' + 'x' * 19_998 + ' ')
    assert len(document.content) == 20_000
    assert document.content.startswith(' ') and document.content.endswith(' ')
    # Immutability is per persisted preview in T03, not a client editing method here.
    SourceDocument(id='doc', project_id='p', type='text', title='t', content='t', doi='10.1234/' + 'x' * 242)


def test_concept_list_limits_and_anchor_overlapping_policy():
    payload = dict(id='d', project_id='p', type='concept_list', title='t', content='\n'.join(['x' * 100] * 20))
    SourceDocument(**payload)
    for content in ['\n'.join(['x'] * 21), 'x' * 101, 'crispr\n\nmrna']:
        with pytest.raises(ValidationError):
            SourceDocument(**{**payload, 'content': content})
    doc = SourceDocument(id='d', project_id='p', type='text', title='t', content='aaaa')
    SourceAnchor(source_document_id='d', quote='aa', occurrence=1).validate_source(doc)
    with pytest.raises(ValueError):
        SourceAnchor(source_document_id='d', quote='aa', occurrence=2).validate_source(doc)


@pytest.mark.parametrize('stamp', ['2026-10-21', '2026-10-21T12:00:00', '2026-10-21T12:00:00-03:00', 'bad'])
def test_provenance_requires_utc(stamp):
    with pytest.raises(ValidationError):
        Provenance(source_document_id='d', method='openalex_metadata', retrieved_at=stamp, from_cache=False, source_url='https://openalex.org/W1')


def test_forensics_schemas_keep_existing_extra_field_policy():
    assert Concept(id='crispr', name='CRISPR', legacy_extra='ignored').id == 'crispr'


def test_citation_semantics_without_associated_publication():
    contribution = Contribution(**load_json('contributions.json')[0]).model_copy(update={'related_dois': []})
    assert classify_citation(get_paper('10.1126/science.1231143'), contribution, {}) == 'THEMATIC_ONLY'


@pytest.mark.parametrize('change', ['project', 'paper', 'metadata', 'remote', 'alias', 'duplicate', 'origin'])
def test_source_binding_rejects_untrusted_records(change):
    value = read('mixed')
    if change == 'project':
        value['source_documents'][0]['project_id'] = 'other-project'
    elif change == 'paper':
        value['paper_dois'] = ['10.1056/nejmoa2034577']
    elif change == 'metadata':
        value['source_documents'][0]['content'] = 'Metadados inventados'
    elif change == 'remote':
        value['scientific_context']['provenance'][0]['from_cache'] = False
    elif change == 'alias':
        value['source_documents'][1]['content'] = 'Sem termos científicos'
        for source in value['scientific_context']['provenance']:
            if source['source_document_id'] == 'doc-material':
                source['quote'] = 'Sem termos científicos'
    elif change == 'duplicate':
        value['scientific_context']['concept_ids'].append(value['scientific_context']['concept_ids'][0])
        value['scientific_context']['concept_labels'].append(value['scientific_context']['concept_labels'][0])
    else:
        value['scientific_context']['origin_type'] = 'doi'
    with pytest.raises(ValueError):
        validate_fixture(value)
