"""Private NVIDIA choices are bounded by the frozen server authority."""
import asyncio
import json

import httpx

from app.integrations.nvidia_client import NVIDIAProvider
from test_nvidia_provider import completion, request_for
from test_nvidia_compact_lesson import compact_lesson


def test_claim_schema_accepts_only_the_authorized_canonical_ids(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    allowed = {'allowed-evidence-a': 'Canonical claim A.', 'allowed-evidence-b': 'Canonical claim B.'}
    def upstream(http):
        body = json.loads(http.content)
        schema = body['response_format']['json_schema']['schema']
        evidence = schema['$defs']['EvidenceClaimBlock']['properties']['evidence_id']
        assert evidence['enum'] == ['allowed-evidence-a', 'allowed-evidence-b']
        value = compact_lesson()
        value['sections'][0]['slides'][0]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'allowed-evidence-b'})
        return httpx.Response(200, json=completion(json.dumps(value)))
    request = request_for('lesson', material={'configuration': {'duration_minutes': 50, 'learning_objectives': ['Approved.']},
                                            'authorized_evidence': allowed})
    result = asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request))
    assert 'allowed-evidence-b' in result.content.decode()


def test_approved_objectives_are_bounded_in_both_section_and_activity_schema(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    def upstream(http):
        schema = json.loads(http.content)['response_format']['json_schema']['schema']
        for name in ('CompactSection', 'CompactActivity'):
            assert schema['$defs'][name]['properties']['objective_indexes']['items']['enum'] == [0, 1]
        return httpx.Response(200, json=completion(json.dumps(compact_lesson())))
    request = request_for('lesson', material={'configuration': {'duration_minutes': 50, 'learning_objectives': ['A.', 'B.']}})
    asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request))


def test_layout_is_checked_before_provider_reports_completed(monkeypatch, caplog):
    import pytest
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    value = compact_lesson()
    value['sections'][0]['slides'][0]['layout'] = 'PROCESS'
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson')))
    assert 'lesson_slide_layout_invalid' in caplog.text


def test_no_authority_removes_claims_and_spotlight_but_valid_pedagogy_remains(monkeypatch):
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    def upstream(http):
        schema = json.loads(http.content)['response_format']['json_schema']['schema']
        assert 'EvidenceClaimBlock' not in schema['$defs']
        properties = schema['$defs']['CompactSlide']['properties']
        assert 'SCIENTIST_SPOTLIGHT' not in properties['layout']['enum']
        items = properties['content_blocks']['items']
        assert 'evidence_claim' not in items['discriminator']['mapping']
        assert len(items['oneOf']) == 4
        return httpx.Response(200, json=completion(json.dumps(compact_lesson())))
    result = asyncio.run(NVIDIAProvider(transport=httpx.MockTransport(upstream)).complete(request_for('lesson')))
    assert 'evidence_claim' not in result.content.decode()


def test_unknown_or_previous_request_evidence_is_rejected_without_replacement(monkeypatch, caplog):
    import pytest
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    seen = []
    def upstream(http):
        schema = json.loads(http.content)['response_format']['json_schema']['schema']
        seen.append(schema['$defs']['EvidenceClaimBlock']['properties']['evidence_id']['enum'])
        value = compact_lesson()
        value['sections'][0]['slides'][0]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'old-evidence'})
        return httpx.Response(200, json=completion(json.dumps(value)))
    provider = NVIDIAProvider(transport=httpx.MockTransport(upstream))
    for allowed in ({'old-evidence': 'Canonical.'}, {'new-evidence': 'Another canonical claim.'}):
        request = request_for('lesson', material={'configuration': {'duration_minutes': 50, 'learning_objectives': ['Approved.']},
                                                'authorized_evidence': allowed})
        if 'old-evidence' in allowed:
            assert b'old-evidence' in asyncio.run(provider.complete(request)).content
        else:
            with pytest.raises(ValueError):
                asyncio.run(provider.complete(request))
    assert seen == [['old-evidence'], ['new-evidence']]
    assert 'lesson_evidence_not_authorized' in caplog.text
    assert 'old-evidence' not in caplog.text and 'new-evidence' not in caplog.text


def test_claim_is_rejected_with_no_authority_even_if_upstream_ignores_schema(monkeypatch, caplog):
    import pytest
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    value = compact_lesson()
    value['sections'][0]['slides'][0]['content_blocks'].append({'type': 'evidence_claim', 'evidence_id': 'PRIVATE_ID'})
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
    with pytest.raises(ValueError):
        asyncio.run(provider.complete(request_for('lesson')))
    assert 'lesson_evidence_not_authorized' in caplog.text and 'PRIVATE_ID' not in caplog.text


def test_unapproved_and_duplicate_objective_indexes_are_rejected(monkeypatch, caplog):
    import pytest
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    caplog.set_level('INFO', logger='matilda.studio.nvidia')
    for indexes, code in (([1], 'lesson_objective_not_approved'), ([0, 0], 'lesson_duplicate_identifier')):
        caplog.clear()
        value = compact_lesson()
        value['sections'][0]['objective_indexes'] = indexes
        provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=completion(json.dumps(value)))))
        with pytest.raises(ValueError):
            asyncio.run(provider.complete(request_for('lesson')))
        assert code in caplog.text


def test_authorized_schema_is_included_in_input_budget_without_truncation(monkeypatch):
    import pytest
    from app.studio.ports import RepositoryConflict
    monkeypatch.setenv('NVIDIA_API_KEY', 'controlled')
    allowed = {('evidence-' + str(index) + '-' + 'x' * 500): 'Canonical claim.' for index in range(20)}
    request = request_for('lesson', material={'configuration': {'duration_minutes': 50, 'learning_objectives': ['Approved.']},
                                            'authorized_evidence': allowed})
    calls = []
    provider = NVIDIAProvider(transport=httpx.MockTransport(lambda _: calls.append(1)))
    with pytest.raises(RepositoryConflict) as error:
        asyncio.run(provider.complete(request))
    assert error.value.error.code == 'input_too_large' and calls == []
