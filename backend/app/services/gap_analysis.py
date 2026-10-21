"""Compare persistent IDs only. Missing references never establish historical intent."""
from pathlib import Path
import json
from .storage import DATA

def bibliography_index():
    index = {}
    for path in (DATA / 'openalex_snapshots').glob('*.json'):
        raw = json.loads(path.read_text())['data']
        if raw.get('doi') and raw.get('id'):
            index[raw['doi'].removeprefix('https://doi.org/').lower()] = raw['id']
    return index

def classify_citation(paper, contribution, index):
    if not contribution.related_dois:
        return 'THEMATIC_ONLY'
    if paper is None:
        return 'UNKNOWN'
    ids = [index.get(doi) for doi in contribution.related_dois]
    if any(identifier in paper.referenced_work_ids for identifier in ids if identifier):
        return 'CITED'
    if paper.references_status == 'unavailable' or any(identifier is None for identifier in ids) or paper.id in ids:
        return 'UNKNOWN'
    return 'NOT_FOUND_IN_RETRIEVED_REFERENCES'
