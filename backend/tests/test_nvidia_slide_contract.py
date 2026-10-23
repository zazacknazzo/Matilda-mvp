"""NVIDIA authoring is tested both as JSON Schema and through its adapter seam."""
import asyncio
from copy import deepcopy
import json

import httpx
from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest

from app.integrations.nvidia_client import NVIDIAProvider
from app.integrations.nvidia_lesson import contract
from app.integrations.nvidia_slides import CompactSlide
from app.services.studio.lesson_validator import LessonDraft
from test_nvidia_compact_lesson import compact_lesson
from test_nvidia_provider import completion, request_for


CONTENTS = [
    ({'layout': 'TITLE', 'introduction': 'Investigue o mecanismo molecular.'},
     [{'type': 'text', 'text': 'Investigue o mecanismo molecular.'}]),
    ({'layout': 'CONCEPT', 'text': 'O RNA guia orienta a proteína ao DNA.', 'bullets': ['Compare RNA e DNA.']},
     [{'type': 'text', 'text': 'O RNA guia orienta a proteína ao DNA.'},
      {'type': 'bullets', 'items': ['Compare RNA e DNA.']}]),
    ({'layout': 'PROCESS', 'steps': ['O RNA reconhece a sequência.', 'A proteína cliva o DNA.']},
     [{'type': 'steps', 'items': ['O RNA reconhece a sequência.', 'A proteína cliva o DNA.']}]),
    ({'layout': 'QUESTION', 'question': 'Como o RNA participa do reconhecimento?'},
     [{'type': 'question', 'text': 'Como o RNA participa do reconhecimento?'}]),
    ({'layout': 'SUMMARY', 'synthesis': 'Diferencie reconhecimento e clivagem.'},
     [{'type': 'text', 'text': 'Diferencie reconhecimento e clivagem.'}]),
    ({'layout': 'SCIENTIST_SPOTLIGHT', 'evidence_id': 'authorized-a'},
     [{'type': 'evidence_claim', 'evidence_id': 'authorized-a'}]),
]


def authored_slide(content):
    return {'title': 'Mecanismo', 'subtitle': None, 'content': deepcopy(content),
            'speaker_notes': 'Compare as hipóteses dos alunos com o mecanismo e peça que justifiquem cada etapa.'}


def schema_for(allowed=True):
    return contract(request_for('lesson', material={
        'configuration': {'duration_minutes': 50, 'learning_objectives': ['Explicar o mecanismo.']},
        'authorized_evidence': {'authorized-a': 'Afirmação canônica.'} if allowed else {},
    }))[2]


def slide_validator(allowed=True):
    schema = schema_for(allowed)
    return Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/CompactSlide'})


@pytest.mark.parametrize('content,expected', CONTENTS, ids=[c['layout'] for c, _ in CONTENTS])
def test_all_layouts_are_schema_valid_and_convert_exactly_through_provider(monkeypatch, content, expected):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    slide = authored_slide(content)
    assert slide_validator().is_valid(slide)
    value = compact_lesson()
    value['sections'][0]['slides'][0] = slide
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    result = asyncio.run(provider.complete(request_for('lesson', material={
        'configuration': {'duration_minutes': 50, 'learning_objectives': ['Explicar o mecanismo.']},
        'authorized_evidence': {'authorized-a': 'Afirmação canônica.'},
    })))
    public = LessonDraft.model_validate_json(result.content).slides[0]
    assert public.layout == content['layout']
    assert [b.model_dump() for b in public.content_blocks] == expected
    assert public.speaker_notes == slide['speaker_notes']


def test_transmitted_schema_cannot_accept_process_with_only_generic_text():
    value = compact_lesson()
    value['sections'][0]['slides'][0] = {
        'layout': 'PROCESS', 'title': 'Mecanismo',
        'content_blocks': [{'type': 'text', 'text': 'Explicação sem etapas.'}],
        'speaker_notes': 'Peça aos alunos que expliquem o mecanismo.',
    }
    _, _, schema = contract(request_for('lesson'))
    Draft202012Validator.check_schema(schema)
    assert not Draft202012Validator(schema).is_valid(value)


@pytest.mark.parametrize('content,_', CONTENTS, ids=[c['layout'] for c, _ in CONTENTS])
def test_layout_tag_is_required_and_other_variant_fields_are_forbidden(content, _):
    slide = authored_slide(content)
    missing = deepcopy(slide)
    del missing['content']['layout']
    assert not slide_validator().is_valid(missing)
    with pytest.raises(ValidationError):
        CompactSlide.model_validate(missing)
    for other, _ in CONTENTS:
        if other['layout'] == content['layout']:
            continue
        mixed = deepcopy(slide)
        mixed['content'].update({k: v for k, v in other.items() if k != 'layout'})
        assert not slide_validator().is_valid(mixed)
        with pytest.raises(ValidationError):
            CompactSlide.model_validate(mixed)


@pytest.mark.parametrize('content,_', CONTENTS[1:], ids=[c['layout'] for c, _ in CONTENTS[1:]])
def test_required_variant_content_cannot_be_omitted(content, _):
    field = next(k for k in content if k != 'layout')
    slide = authored_slide(content)
    del slide['content'][field]
    assert not slide_validator().is_valid(slide)
    with pytest.raises(ValidationError):
        CompactSlide.model_validate(slide)


def test_title_introduction_is_optional_without_invented_text():
    slide = authored_slide({'layout': 'TITLE'})
    assert slide_validator().is_valid(slide)
    assert CompactSlide.model_validate(slide).public_fields()['content_blocks'] == []


@pytest.mark.parametrize('steps', [[], ['Uma etapa.'], ['Etapa.'] * 7, ['Etapa.', ' '], 'Etapas'])
def test_process_requires_two_to_six_nonblank_steps(steps):
    slide = authored_slide({'layout': 'PROCESS', 'steps': steps})
    assert not slide_validator().is_valid(slide)
    with pytest.raises(ValidationError):
        CompactSlide.model_validate(slide)


@pytest.mark.parametrize('content,_', CONTENTS, ids=[c['layout'] for c, _ in CONTENTS])
def test_unknown_fields_and_missing_or_blank_teacher_notes_are_rejected(content, _):
    for field, value in [('extra', 'PRIVATE'), ('speaker_notes', ''), ('speaker_notes', ' '),
                         ('speaker_notes', 'N' * 1501)]:
        slide = authored_slide(content)
        slide[field] = value
        assert not slide_validator().is_valid(slide)
        with pytest.raises(ValidationError):
            CompactSlide.model_validate(slide)
    slide = authored_slide(content)
    del slide['speaker_notes']
    assert not slide_validator().is_valid(slide)
    with pytest.raises(ValidationError):
        CompactSlide.model_validate(slide)


@pytest.mark.parametrize('content,_', CONTENTS, ids=[c['layout'] for c, _ in CONTENTS])
def test_public_visible_budget_is_preserved_for_every_variant(content, _):
    slide = authored_slide(content)
    public = CompactSlide.model_validate(slide).public_fields()
    visible = len(slide['title'])
    for block in public['content_blocks']:
        visible += len(block.get('text', '')) + sum(len(x) for x in block.get('items', []))
    slide['subtitle'] = 'Á' * (600 - visible)
    assert CompactSlide.model_validate(slide).public_fields()['layout'] == content['layout']
    slide['subtitle'] += 'X'
    with pytest.raises(ValidationError) as rejected:
        CompactSlide.model_validate(slide)
    assert {e['type'] for e in rejected.value.errors()} == {'lesson_slide_content_too_large'}


@pytest.mark.parametrize('content,_', CONTENTS, ids=[c['layout'] for c, _ in CONTENTS])
@pytest.mark.parametrize('allowed', [True, False])
def test_evidence_is_bounded_by_the_actual_review_for_every_layout(monkeypatch, content, _, allowed):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    request = request_for('lesson', material={
        'configuration': {'duration_minutes': 50, 'learning_objectives': ['Approved.']},
        'authorized_evidence': {'authorized-a': 'Canonical.'} if allowed else {},
    })
    for eid in ('authorized-a', 'unknown-evidence'):
        slide = authored_slide(content)
        if content['layout'] == 'SCIENTIST_SPOTLIGHT':
            slide['content']['evidence_id'] = eid
        else:
            slide['evidence_ids'] = [eid]
        valid = allowed and eid == 'authorized-a'
        assert slide_validator(allowed).is_valid(slide) is valid
        value = compact_lesson()
        value['sections'][0]['slides'][0] = slide
        provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
        if valid:
            result = asyncio.run(provider.complete(request))
            public = LessonDraft.model_validate_json(result.content).slides[0]
            assert any(b.type == 'evidence_claim' and b.evidence_id == eid for b in public.content_blocks)
        else:
            with pytest.raises(ValueError):
                asyncio.run(provider.complete(request))


def test_wire_schema_has_exclusive_variants_without_openapi_discriminator():
    schema = schema_for()
    assert 'discriminator' not in json.dumps(schema) and 'oneOf' not in json.dumps(schema)
    branches = schema['$defs']['CompactSlide']['properties']['content']['anyOf']
    layouts = []
    for branch in branches:
        variant = schema['$defs'][branch['$ref'].removeprefix('#/$defs/')]
        assert variant['additionalProperties'] is False
        assert 'layout' in variant['required']
        layouts.append(variant['properties']['layout']['const'])
    assert set(layouts) == {c['layout'] for c, _ in CONTENTS}
    no_authority = schema_for(False)
    assert 'SpotlightContent' not in no_authority['$defs']
    assert 'SCIENTIST_SPOTLIGHT' not in json.dumps(no_authority)


def test_perfunctory_teacher_notes_are_rejected_in_schema_and_adapter(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled-only')
    slide = authored_slide(CONTENTS[0][0])
    slide['speaker_notes'] = 'Explique.'
    assert not slide_validator().is_valid(slide)
    value = compact_lesson()
    value['sections'][0]['slides'][0] = slide
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson')))
