#!/usr/bin/env python3
"""Offline public-fixture payload measurement; HTTPX cannot leave the process."""
import argparse
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import httpx
from fastapi.testclient import TestClient
from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider, serialize
from app.main import app


def measure_payloads():
    samples = []
    def upstream(request):
        body = json.loads(request.content)
        material = json.loads(body['messages'][1]['content'])
        samples.append({
            'payload_utf8_bytes': len(serialize(body).encode()),
            'system_utf8_bytes': len(body['messages'][0]['content'].encode()),
            'material_utf8_bytes': len(serialize(material).encode()),
            'schema_utf8_bytes': len(serialize(body['response_format']['json_schema']['schema']).encode()),
            'estimated_input_tokens': len(serialize(body).encode()) + 1024,
        })
        # Abort before planning; no automatic retry on 401, never a real request.
        return httpx.Response(401)
    original_env = {key: os.environ.get(key) for key in ('MATILDA_DB', 'MATILDA_CACHE_TTL', 'NVIDIA_API_KEY', 'NVIDIA_MODEL')}
    overrides = app.dependency_overrides.copy()
    try:
        with tempfile.TemporaryDirectory(prefix='matilda-payload-') as temporary:
            os.environ.update(MATILDA_DB=str(Path(temporary) / 'measure.sqlite'),
                MATILDA_CACHE_TTL='999999999', NVIDIA_API_KEY='offline-controlled',
                NVIDIA_MODEL='nvidia/nemotron-3.5-super-vl-120b-a12b')
            app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
            with TestClient(app) as client:
                for scenario, doi, text in (
                    ('crispr', '10.1126/science.1231143', 'CRISPR-Cas9 permite discutir edição genética, reconhecimento do DNA por RNA guia e clivagem da molécula.'),
                    ('rna', '10.1056/NEJMoa2034577', 'RNA mensageiro e modificação de nucleosídeos permitem discutir reconhecimento imune e produção de proteínas.'),
                ):
                    response = client.post('/api/studio/preview', headers={'Origin': 'http://localhost:5173'},
                        json={'title': 'Edição genética com CRISPR-Cas9' if scenario == 'crispr' else 'RNA mensageiro e imunidade', 'duration_minutes': 50, 'doi': doi, 'material_text': text})
                    if response.status_code != 503 or len(samples) != (1 if scenario == 'crispr' else 2):
                        raise RuntimeError('A medição offline não alcançou o transporte controlado.')
                    samples[-1]['scenario'] = scenario
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        for key, value in original_env.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
    return {'mode': 'offline_mock_transport', 'external_calls': 0, 'samples': samples}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    logging.disable(logging.CRITICAL)
    result = json.dumps(measure_payloads(), ensure_ascii=False, indent=2) + '\n'
    if options.output:
        options.output.write_text(result)
    else:
        print(result, end='')
