"""Offline developer measurement; real API/SQLite, test preparation and local HTTP401."""
import argparse
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.api.studio_preview import get_provider
from app.integrations.nvidia_client import NVIDIAProvider, serialize
from studio_flow_provider import FlowProvider
from test_studio_flow import create, review, generate
from generation_fixtures import draft
from nvidia_transport import compact_payload


def required_count(value):
    if isinstance(value, dict):
        return len(value.get('required', [])) + sum(required_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(required_count(v) for v in value)
    return 0


def measure():
    result = {}
    before = app.dependency_overrides.copy()
    env = {key: os.environ.get(key) for key in ('MATILDA_DB', 'NVIDIA_API_KEY')}
    try:
        with tempfile.TemporaryDirectory() as temporary:
            os.environ.update(MATILDA_DB=str(Path(temporary) / 'measure.sqlite'), NVIDIA_API_KEY='offline-controlled')
            app.dependency_overrides[get_provider] = lambda: FlowProvider()
            with TestClient(app) as client:
                saved, _ = review(client, create(client))
                def upstream(request):
                    body = json.loads(request.content)
                    schema = body['response_format']['json_schema']['schema']
                    result.update(payload_bytes=len(serialize(body).encode()),
                        estimated_input_tokens=len(serialize(body).encode()) + 1024,
                        schema_bytes=len(serialize(schema).encode()), required_entries=required_count(schema),
                        system_bytes=len(body['messages'][0]['content'].encode()),
                        material_bytes=len(body['messages'][1]['content'].encode()), max_tokens=body['max_tokens'],
                        reasoning_effort=body['reasoning_effort'], stream=body['stream'],
                        sample_output_bytes=len(serialize(compact_payload(draft('no-enrichment-50'))).encode()))
                    return httpx.Response(401)
                app.dependency_overrides[get_provider] = lambda: NVIDIAProvider(transport=httpx.MockTransport(upstream))
                if generate(client, saved).status_code != 503 or not result:
                    raise RuntimeError('Medição não alcançou o transporte controlado.')
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)
        for key, value in env.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    options = parser.parse_args()
    logging.disable(logging.CRITICAL)
    rendered = json.dumps(measure(), ensure_ascii=False, indent=2) + '\n'
    if options.output: options.output.write_text(rendered)
    else: print(rendered, end='')
