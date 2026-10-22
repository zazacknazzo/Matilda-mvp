"""T06 public resolver + existing HTTP APIs; no T05 repository or provider."""
import asyncio
import json
from pathlib import Path

import pytest
import httpx
from fastapi import HTTPException
from app.schemas.scientific_context import SourceDocument

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/studio/scientific'


@pytest.mark.parametrize('name', ['crispr', 'rna', 'no-coverage'])
def test_resolve_doi_preserves_real_science_and_cache(client, name):
    from app.services.studio.source_resolver import resolve_scientific_source

    fixture = json.loads((FIXTURES / f'{name}.json').read_text())
    paper = fixture['papers'][0]
    result = asyncio.run(resolve_scientific_source(project_id='project', doi='https://doi.org/' + paper['doi']))
    snapshot = result.snapshot()

    assert snapshot['papers'] == [client.get('/api/papers/' + paper['doi']).json()]
    assert snapshot['matches'] == fixture['expected_matches']
    assert snapshot['scientific_context']['origin_type'] == 'doi'
    assert snapshot['scientific_context']['analysis_id'] is None
    assert snapshot['source_documents'][0]['content'] == paper['title'] + ('\n\n' + paper['abstract'] if paper['abstract'] else '')
    assert snapshot['papers'][0]['from_cache'] is True
    assert all(p['retrieved_at'] == paper['retrieved_at'] and p['from_cache'] is True for p in snapshot['scientific_context']['provenance'])


@pytest.mark.parametrize('doi', ['10.1126/science.1231143', '10.1056/NEJMoa2034577'])
def test_analysis_reuse_needs_no_network_and_snapshot_survives_link_expiry(client, monkeypatch, doi):
    from app.services.studio.source_resolver import resolve_scientific_source
    from app.services import storage
    from app.integrations import openalex

    investigation = client.post('/api/analyses', json={'doi': doi}).json()
    original = httpx.AsyncClient

    def forbidden(request):
        pytest.fail('Reusing an investigation must not call OpenAlex')

    monkeypatch.setattr(openalex.httpx, 'AsyncClient', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(forbidden)))
    monkeypatch.setenv('MATILDA_CACHE_TTL', '0')
    result = asyncio.run(resolve_scientific_source(project_id='project', analysis_id=investigation['id']))
    snapshot = result.snapshot()
    assert snapshot['matches'] == investigation['contributions']
    assert snapshot['papers'] == [investigation['paper']]
    assert snapshot['scientific_context']['analysis_id'] == investigation['id']
    moment = storage.time.time()
    monkeypatch.setattr(storage.time, 'time', lambda: moment + 8 * 86400)
    assert client.get('/api/analyses/' + investigation['id']).status_code == 404
    assert result.snapshot() == snapshot
    # A consumer may serialize or edit its own copy without mutating the source.
    snapshot['matches'].clear()
    assert result.snapshot()['matches'] == investigation['contributions']


@pytest.mark.parametrize('source', [
    {'doi': '10.1126/science.1231143', 'analysis_id': 'missing'},
    {'doi': ''}, {'doi': 'https://example.com/secret'}, {'doi': 'inválido'}, {'analysis_id': ''}, {},
])
def test_invalid_or_ambiguous_origin_is_422(client, source):
    from app.services.studio.source_resolver import resolve_scientific_source

    with pytest.raises(HTTPException) as error:
        asyncio.run(resolve_scientific_source(project_id='project', **source))
    assert error.value.status_code == 422


def test_documents_must_be_server_owned_material_from_target_project(client):
    from app.services.studio.source_resolver import resolve_scientific_source

    document = SourceDocument(id='doc', project_id='other', type='text', title='Material', content='CRISPR')
    with pytest.raises(ValueError, match='projeto'):
        asyncio.run(resolve_scientific_source(project_id='project', documents=[document]))


@pytest.mark.parametrize('content,expected_ids', [
    ('CRISPR-Cas9', ['crispr-2012', 'crispr-2014', 'crispr-2010', 'crispr-2011']),
    ('RNA mensageiro', ['rna-2005', 'rna-2008']),
    ('Imunogenicidade', []), ('Dinâmica de fluidos', []),
])
def test_material_dossier_has_canonical_matches_without_paper_or_graph(client, content, expected_ids):
    from app.services.studio.source_resolver import resolve_scientific_source

    document = SourceDocument(id='doc', project_id='project', type='text', title='Material', content=content)
    result = asyncio.run(resolve_scientific_source(project_id='project', documents=[document]))
    snapshot = result.snapshot()
    assert snapshot['source_documents'] == [document.model_dump()]
    assert snapshot['papers'] == []
    assert 'graph' not in snapshot
    assert snapshot['scientific_context']['analysis_id'] is None
    assert snapshot['scientific_context']['origin_type'] == 'material'
    assert [m['contribution']['id'] for m in snapshot['matches']] == expected_ids
    for match in snapshot['matches']:
        assert match['citation_status'] == 'UNKNOWN'
        assert match['relation_type'] == 'RELATED_TO'
        for evidence in match['evidence']:
            assert client.get('/api/evidence/' + evidence['id']).json() == evidence
    if not expected_ids:
        assert any('não indica inexistência de contribuições femininas' in limit for limit in result.scientific_context.limitations)


def test_mixed_origin_preserves_literal_material_and_limits_comparison_to_paper(client):
    from app.services.studio.source_resolver import resolve_scientific_source

    document = SourceDocument(id='doc', project_id='project', type='concept_list', title='Conceitos', content='RNA mensageiro')
    result = asyncio.run(resolve_scientific_source(project_id='project', doi='10.1126/science.1231143', documents=[document]))
    assert result.scientific_context.origin_type == 'mixed'
    assert result.source_documents[0] == document
    assert any(p.quote == 'RNA mensageiro' and p.method == 'editorial_alias' for p in result.scientific_context.provenance)
    assert any('somente ao artigo vinculado' in limit for limit in result.scientific_context.limitations)
    assert len(result.matches) == 6


@pytest.mark.parametrize('status,expected', [(404, 404), (401, 503), (429, 503), (503, 503)])
def test_resolver_preserves_forensics_source_error_policy(client, monkeypatch, status, expected):
    from app.integrations import openalex
    from app.services.studio.source_resolver import resolve_scientific_source

    original = httpx.AsyncClient
    monkeypatch.setattr(openalex.httpx, 'AsyncClient', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(lambda req: httpx.Response(status, json={'secret': 'upstream-private-error'}))))
    with pytest.raises(HTTPException) as error:
        asyncio.run(resolve_scientific_source(project_id='project', doi='10.9999/t06-no-cache'))
    assert error.value.status_code == expected
    assert 'upstream-private-error' not in str(error.value.detail)


def test_missing_or_expired_analysis_is_404(client, monkeypatch):
    from app.services import storage
    from app.services.studio.source_resolver import resolve_scientific_source

    identifier = client.post('/api/analyses', json={'doi': '10.1126/science.1231143'}).json()['id']
    moment = storage.time.time()
    monkeypatch.setattr(storage.time, 'time', lambda: moment + 8 * 86400)
    for analysis_id in ('missing', identifier):
        with pytest.raises(HTTPException) as error:
            asyncio.run(resolve_scientific_source(project_id='project', analysis_id=analysis_id))
        assert error.value.status_code == 404
        assert error.value.detail == client.get('/api/analyses/' + analysis_id).json()['detail']


def test_existing_investigation_keeps_its_recorded_contributions_and_warnings(client, monkeypatch, tmp_path):
    from app.services import storage
    from app.services.studio.source_resolver import resolve_scientific_source

    analysis = client.post('/api/analyses', json={'doi': '10.1126/science.1231143'}).json()
    # The editorial files may change after an investigation was persisted.
    for name in ('concepts.json', 'researchers.json', 'contributions.json', 'evidence.json'):
        records = storage.load_json(name)
        if name == 'contributions.json':
            for record in records:
                record['title'] = 'Título editorial atualizado'
        (tmp_path / name).write_text(json.dumps(records))
    monkeypatch.setattr(storage, 'DATA', tmp_path)
    result = asyncio.run(resolve_scientific_source(project_id='project', analysis_id=analysis['id']))
    assert result.snapshot()['matches'] == analysis['contributions']
    assert set(analysis['coverage_warnings']) <= set(result.scientific_context.limitations)


@pytest.mark.parametrize('cached', [False, True])
def test_source_timeout_preserves_explicit_stale_cache_policy(client, monkeypatch, cached):
    from app.integrations import openalex
    from app.services.studio.source_resolver import resolve_scientific_source

    original = httpx.AsyncClient
    def timeout(request):
        raise httpx.ReadTimeout('private upstream message')
    monkeypatch.setattr(openalex.httpx, 'AsyncClient', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(timeout)))
    monkeypatch.setenv('MATILDA_CACHE_TTL', '0')
    if cached:
        result = asyncio.run(resolve_scientific_source(project_id='project', doi='10.1126/science.1231143'))
        assert result.papers[0].from_cache and result.papers[0].cache_stale
        assert any('cache anterior' in limit for limit in result.scientific_context.limitations)
        assert all(p.retrieved_at == result.papers[0].retrieved_at and p.from_cache for p in result.scientific_context.provenance)
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(resolve_scientific_source(project_id='project', doi='10.9999/t06-no-cache'))
        assert error.value.status_code == 503
        assert 'private upstream message' not in str(error.value.detail)
