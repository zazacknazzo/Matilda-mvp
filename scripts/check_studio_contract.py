"""Validate/compile the same T03 HTTP fixtures for backend and frontend consumers."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.schemas.studio import (  # noqa: E402
    EnrichmentPreview, PreviewRequest, ReviewRequest, GenerateRequest,
    GenerationHeaders, StudioWriteHeaders, ExportQuery, StudioError,
)
from app.schemas.lesson import LessonBundle  # noqa: E402

FIXTURES = ROOT / 'tests/fixtures/studio/api'


def read(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def main():
    examples = []
    for path in sorted(FIXTURES.glob('*-preview.json')):
        examples.append((EnrichmentPreview, json.loads(path.read_text(encoding='utf-8'))))
    for key, model in [('preview', PreviewRequest), ('review', ReviewRequest), ('generate', GenerateRequest)]:
        examples.extend((model, value) for value in read('requests')[key])
    examples.extend((StudioError, value['body']) for value in read('errors'))
    for exchange in read('http-examples'):
        if 'headers' in exchange:
            model = GenerationHeaders if exchange['operation_id'] == 'studio_generate' else StudioWriteHeaders
            examples.append((model, exchange['headers']))
        if 'query' in exchange:
            examples.append((ExportQuery, exchange['query']))
        if exchange.get('response', {}).get('fixture', '').startswith('../lessons/'):
            examples.append((LessonBundle, read(exchange['response']['fixture'])))
    source = [
        'import type {EnrichmentPreview, PreviewRequest, ReviewRequest, GenerateRequest, GenerationHeaders, StudioWriteHeaders, ExportQuery, StudioError} from "../../frontend/src/types/studio";',
        'import type {LessonBundle} from "../../frontend/src/types/lesson";',
    ]
    for model, value in examples:
        model.model_validate(value)
        source.append(f'({json.dumps(value, ensure_ascii=False)}) satisfies {model.__name__};')
    (ROOT / '.runtime').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='studio-contract-', dir=ROOT / '.runtime') as directory:
        target = Path(directory) / 'contracts.ts'
        target.write_text('\n'.join(source), encoding='utf-8')
        subprocess.run([
            'node', str(ROOT / 'frontend/node_modules/typescript/bin/tsc'), '--noEmit', '--strict',
            '--skipLibCheck', '--moduleResolution', 'bundler', '--module', 'ESNext',
            '--target', 'ES2022', str(target),
        ], cwd=ROOT, check=True)
    print(f'{len(examples)} Studio HTTP payloads conform to Pydantic and TypeScript contracts.')


if __name__ == '__main__':
    main()
