"""T02 models/fixtures only. No generation, routes, UI or external calls."""
import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.lesson import (
    LessonBundle, LessonReference, LessonSlide, TextBlock,
)
from app.services.storage import DATA, load_json

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/lessons'
VALID = ['crispr-50', 'rna-50', 'no-enrichment-50', 'optional-fields']


def read(name):
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def allowed_references():
    return {key: LessonReference.model_validate(value) for key, value in read('authorized-references').items()}


@pytest.mark.parametrize('name', VALID)
def test_valid_shared_bundle(name):
    bundle = LessonBundle.model_validate(read(name))
    bundle.validate_authorized_references(allowed_references())
    assert bundle.metadata.duration_minutes == 50
    assert sum(s.duration_minutes for s in bundle.sections) == 50
    assert sum(s.duration_minutes for s in bundle.slides) == 50
    assert LessonBundle.model_validate_json(bundle.model_dump_json()) == bundle
    assert bundle.generation_metadata.provider == 'fixture'
    assert bundle.generation_metadata.model == 'not-generated'


@pytest.mark.parametrize('case', read('invalid'), ids=lambda c: c['name'])
def test_shared_counterexamples_rejected(case):
    value = read(case['fixture'])
    target = value
    for key in case['path'][:-1]:
        target = target[key]
    target[case['path'][-1]] = case['value']
    with pytest.raises(ValidationError):
        LessonBundle.model_validate(value)


@pytest.mark.parametrize('name', ['crispr-50', 'rna-50'])
def test_all_six_layouts_and_activity_time_counted_once(name):
    bundle = LessonBundle.model_validate(read(name))
    assert {s.layout for s in bundle.slides} == {
        'TITLE', 'CONCEPT', 'PROCESS', 'SCIENTIST_SPOTLIGHT', 'QUESTION', 'SUMMARY',
    }
    assert bundle.activities[0].section_id == 'section-3'
    assert bundle.sections[2].duration_minutes == 15
    assert not hasattr(bundle.activities[0], 'duration_minutes')
    assert bundle.activities[0].assessment_criteria
    assert all(s.speaker_notes for s in bundle.slides)


def test_no_enrichment_has_no_historical_claims_or_spotlight():
    bundle = LessonBundle.model_validate(read('no-enrichment-50'))
    assert bundle.references == []
    assert all(s.layout != 'SCIENTIST_SPOTLIGHT' and s.contribution_ids == [] and s.evidence_ids == [] for s in bundle.slides)
    assert all(b.type != 'evidence_claim' for s in bundle.sections for b in s.explanation_blocks)
    assert bundle.limitations
    bundle.validate_authorized_references({})


def test_optional_fields_and_explicit_null_have_same_default():
    bundle = LessonBundle.model_validate(read('optional-fields'))
    assert bundle.slides[0].subtitle is None
    assert bundle.generation_metadata.input_tokens is None
    assert bundle.generation_metadata.output_tokens is None
    assert bundle.metadata.prior_knowledge == []
    assert bundle.metadata.materials == []
    value = bundle.model_dump(mode='json')
    assert value['slides'][0]['subtitle'] is None
    assert value['generation_metadata']['input_tokens'] is None


@pytest.mark.parametrize('ref', list(read('authorized-references').values()), ids=lambda r: r['id'])
def test_real_evidence_and_all_collective_participants_preserved(ref):
    evidence = next(e for e in load_json('evidence.json') if e['id'] == ref['id'])
    contribution = next(c for c in load_json('contributions.json') if c['id'] == ref['contribution_id'])
    for key, value in evidence.items():
        assert ref[key] == value
    assert ref['researcher_ids'] == contribution['researcher_ids']
    assert ref['participants'] == contribution['participants']
    assert len(ref['participants']) > len(ref['researcher_ids'])
    for rid in ref['researcher_ids']:
        assert next(r for r in load_json('researchers.json') if r['id'] == rid)['identity_status'] == 'verified'
    doi = ref['source_url'].removeprefix('https://doi.org/').lower()
    snapshot = json.loads((DATA / 'openalex_snapshots' / (doi.replace('/', '_') + '.json')).read_text(encoding='utf-8'))
    assert ref['retrieved_at'] == snapshot['retrieved_at']
    assert ref['from_cache'] is True


def test_real_but_unauthorized_evidence_rejected():
    bundle = LessonBundle.model_validate(read('rna-50'))
    allowed = allowed_references()
    allowed.pop(bundle.references[0].id)
    # The ID exists in the catalog; existence is insufficient for this review.
    with pytest.raises(ValueError, match='autorizada'):
        bundle.validate_authorized_references(allowed)


@pytest.mark.parametrize('field,value', [
    ('claim_supported', 'Afirmação histórica inventada pelo modelo.'),
    ('contribution_id', 'rna-2008'), ('participants', ['Pessoa inventada']),
    ('source_url', 'https://example.org/invented'), ('limitations', ['Sem limitações.']),
    ('researcher_ids', ['invented']), ('from_cache', False),
])
def test_scientific_snapshot_tampering_rejected(field, value):
    raw = read('crispr-50')
    raw['references'][0][field] = value
    if field == 'contribution_id':
        raw['slides'][3]['contribution_ids'] = [value]
    bundle = LessonBundle.model_validate(raw)
    with pytest.raises(ValueError, match='adulterado'):
        bundle.validate_authorized_references(allowed_references())


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'data:text/html,hello', '//evil.test', 'file:///C:/x',
    'https://user:pass@example.org/paper', 'https://example.org/\nsecret',
])
def test_reference_links_reject_unsafe_schemes_and_credentials(url):
    raw = read('crispr-50')['references'][0]
    with pytest.raises(ValidationError):
        LessonReference.model_validate({**raw, 'source_url': url})


def test_html_stays_literal_plain_text_not_a_new_block_kind():
    raw = read('no-enrichment-50')
    literal = '<img src=x onerror="alert(1)"><script>alert(1)</script>'
    raw['slides'][1]['content_blocks'] = [{'type': 'text', 'text': literal}]
    bundle = LessonBundle.model_validate(raw)
    assert bundle.slides[1].content_blocks[0].text == literal
    # Escaping is the renderer's responsibility in T08; these contracts execute nothing.
    with pytest.raises(ValidationError):
        LessonSlide.model_validate({**raw['slides'][1], 'content_blocks': [{'type': 'html', 'text': literal}]})


@pytest.mark.parametrize('field,value', [
    ('duration_minutes', True), ('duration_minutes', 5.0), ('duration_minutes', 0),
    ('speaker_notes', None), ('evidence_ids', None), ('subtitle', 12),
])
def test_strict_slide_types(field, value):
    raw = read('crispr-50')['slides'][0]
    with pytest.raises(ValidationError):
        LessonSlide.model_validate({**raw, field: value})


def test_character_boundaries_not_silently_truncated():
    raw = read('crispr-50')['slides'][0]
    raw.update(title='x' * 100, subtitle=None, speaker_notes='n' * 1500,
               content_blocks=[{'type': 'text', 'text': 'é' * 500}])
    assert len(LessonSlide.model_validate(raw).speaker_notes) == 1500
    raw['content_blocks'][0]['text'] += 'x'
    with pytest.raises(ValidationError, match='600'):
        LessonSlide.model_validate(raw)
    reference = read('crispr-50')['references'][0]
    assert len(LessonReference.model_validate({**reference, 'claim_supported': 'x' * 1500}).claim_supported) == 1500


def test_full_payload_size_limit_in_utf8_bytes():
    raw = read('crispr-50')
    raw['limitations'] = ['á' * 20_000] * 4
    with pytest.raises(ValidationError, match='128 KiB'):
        LessonBundle.model_validate(raw)


@pytest.mark.parametrize('path', [
    ['metadata'], ['generation_metadata'], ['sections', 0], ['slides', 0],
    ['activities', 0], ['references', 0], ['slides', 0, 'content_blocks', 0],
])
def test_nested_models_reject_extra_fields(path):
    raw = read('crispr-50')
    target = raw
    for key in path:
        target = target[key]
    target['unexpected'] = 'reject'
    with pytest.raises(ValidationError):
        LessonBundle.model_validate(raw)


def test_missing_section_evidence_and_broken_document_sets():
    raw = read('crispr-50')
    raw['sections'][0]['explanation_blocks'] = [{'type': 'evidence_claim', 'evidence_id': 'missing'}]
    with pytest.raises(ValidationError):
        LessonBundle.model_validate(raw)


def test_json_schema_is_standalone_and_strict():
    schema = LessonBundle.model_json_schema()
    assert schema['additionalProperties'] is False
    assert schema['properties']['schema_version']['const'] == 1
    for definition in schema['$defs'].values():
        if definition.get('type') == 'object':
            assert definition['additionalProperties'] is False
    assert 'discriminator' in schema['$defs']['LessonSlide']['properties']['content_blocks']['items']
    assert not any(name in schema['$defs'] for name in ('Paper', 'ScientificContext'))


def test_duplicate_slides_and_activities_cannot_hide_missing_links():
    for field in ('slides', 'activities'):
        raw = read('crispr-50')
        raw[field].append(copy.deepcopy(raw[field][0]))
        with pytest.raises(ValidationError):
            LessonBundle.model_validate(raw)


def test_evidence_claim_does_not_accept_free_text_even_if_canonical():
    raw = read('crispr-50')
    raw['slides'][3]['content_blocks'][0]['claim_supported'] = raw['references'][0]['claim_supported']
    with pytest.raises(ValidationError):
        LessonBundle.model_validate(raw)
    assert TextBlock(type='text', text='Conteúdo pedagógico').type == 'text'
