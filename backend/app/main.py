import logging
import os
import time
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.api.studio_lifecycle import studio_lifespan
from app.integrations.openalex import retrieve_paper
from app.schemas import Analysis, AnalysisRequest, Paper, Graph, Evidence
from app.services.contribution_search import search_contributions
from app.services.graph_builder import build_graph
from app.services.storage import load_json, save_analysis, get_analysis, update_analysis, list_candidates, get_candidate

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
logging.basicConfig(level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
log = logging.getLogger('matilda')
app = FastAPI(lifespan=studio_lifespan, title='Matilda Forensics', version='0.1.0', description='Investigação documental de contribuições científicas. Relação temática não comprova influência histórica.')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('MATILDA_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

@app.get('/api/health')
def health():
    return {'status':'ok', 'service':'matilda-forensics'}

@app.get('/api/papers/{doi:path}', response_model=Paper)
async def paper(doi: str):
    return await retrieve_paper(doi)

@app.post('/api/analyses', response_model=Analysis, status_code=201)
async def create_analysis(request: AnalysisRequest):
    started = time.monotonic()
    try:
        paper = await retrieve_paper(request.doi)
        matches = search_contributions(paper)
        warnings = list(paper.limitations)
        warnings.append('Catálogo inicial: 3 pesquisadoras e 6 contribuições em RNA e CRISPR; não representa toda a ciência.')
        if not matches:
            warnings.append('Não foram encontradas contribuições verificadas neste catálogo. Isso não indica inexistência de contribuições femininas.')
        graph = build_graph(paper, matches, warnings)
        analysis = Analysis(id=str(uuid4()), root_paper_id=paper.id, created_at=datetime.now(timezone.utc).isoformat(), paper=paper, contributions=matches, graph=graph, coverage_warnings=warnings, evidence_summary={'contributions':len(matches), 'documents':len({e.id for m in matches for e in m.evidence})})
        save_analysis(analysis)
        log.info('analysis_complete id=%s seconds=%.3f candidates=%d verified=%d warnings=%d', analysis.id, time.monotonic()-started, len(matches), len(matches), len(warnings))
        return analysis
    except HTTPException as exc:
        log.warning('analysis_failed status=%d seconds=%.3f', exc.status_code, time.monotonic()-started)
        raise

def find_analysis(identifier):
    result = get_analysis(identifier)
    if not result:
        raise HTTPException(404, 'Investigação não encontrada ou expirada (retenção: 7 dias).')
    return Analysis.model_validate(result)

@app.get('/api/analyses/{identifier}', response_model=Analysis)
def analysis(identifier: str):
    return find_analysis(identifier)

@app.post('/api/analyses/{identifier}/discovery', response_model=Analysis)
async def expand_discovery(identifier: str):
    from app.services.automatic_catalog import discover_catalog
    result = find_analysis(identifier)
    result.external_discovery = await discover_catalog(result.paper)
    update_analysis(result)
    return result


@app.get('/api/catalog/candidates')
def catalog_candidates(offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    return list_candidates(offset, limit)


@app.get('/api/catalog/candidates/{identifier}')
def catalog_candidate(identifier: str):
    record = get_candidate(identifier)
    if not record:
        raise HTTPException(404, 'Candidato não encontrado.')
    return record


@app.get('/api/analyses/{identifier}/graph', response_model=Graph)
def graph(identifier: str):
    return find_analysis(identifier).graph

@app.get('/api/evidence/{identifier}', response_model=Evidence)
def evidence(identifier: str):
    for entry in load_json('evidence.json'):
        if entry['id'] == identifier:
            return entry
    raise HTTPException(404, 'Evidência não encontrada.')

@app.get('/api/analyses/{identifier}/export')
def export(identifier: str, format: str = 'markdown'):
    result = find_analysis(identifier)
    if format == 'json':
        return Response(result.model_dump_json(indent=2), media_type='application/json', headers={'Content-Disposition':f'attachment; filename="matilda-{identifier}.json"'})
    if format != 'markdown':
        raise HTTPException(422, 'Formato suportado: markdown ou json.')
    lines = ['# Matilda Forensics', '', result.paper.title, 'DOI: https://doi.org/'+result.paper.doi, 'Fonte: '+result.paper.source_url, 'Metadados recuperados em: '+result.paper.retrieved_at, 'Cache: '+str(result.paper.from_cache), '']
    for match in result.contributions:
        lines += ['## '+match.contribution.title, match.contribution.description, '', 'Pesquisadoras: '+', '.join(r.name for r in match.researchers), 'Participantes da publicação: '+', '.join(match.contribution.participants), 'Relação: '+match.relation_type, 'Comparação bibliográfica: '+match.citation_status, match.explanation]
        for evidence in match.evidence:
            lines += ['Fonte: '+evidence.source_title, evidence.source_url, 'Localização: '+evidence.excerpt_or_location, 'Afirmação sustentada: '+evidence.claim_supported]
        lines += ['Limitações:'] + ['- '+w for w in match.limitations] + ['']
    if result.external_discovery:
        lines += ['## Descoberta automática — pendente de revisão', 'Status: '+result.external_discovery.status]
        for connection in result.external_discovery.candidates:
            candidate = connection.candidate
            lines += ['### '+candidate.work.title, 'DOI: https://doi.org/'+candidate.work.doi, 'Status editorial: '+candidate.verification_status, 'Método: '+candidate.extraction_method, 'Trecho do resumo: '+(candidate.excerpt or 'Indisponível'), 'Relação: RELATED_TO; comparação bibliográfica: '+connection.citation_status]
            lines += ['Motivo de recuperação: '+reason for reason in connection.retrieval_reasons]
            lines += ['Identidade: '+identity.author_name+' — '+identity.status+'; fontes: '+', '.join(identity.source_urls) for identity in candidate.identities]
            lines += ['Fonte: '+source.source+'; URL: '+source.source_url+'; recuperada em: '+source.retrieved_at+'; cache: '+str(source.from_cache) for source in candidate.work.sources]
            lines += ['Limite: '+warning for warning in candidate.limitations]
        lines += ['Limite da ampliação: '+warning for warning in result.external_discovery.warnings]
    lines += ['## Cobertura e limitações'] + ['- '+w for w in result.coverage_warnings]
    return Response('\n'.join(lines), media_type='text/markdown; charset=utf-8', headers={'Content-Disposition':f'attachment; filename="matilda-{identifier}.md"'})

# Studio is composed independently; no provider is initialized at import/startup.
from app.api.studio_preview import router as studio_preview_router
app.include_router(studio_preview_router)
