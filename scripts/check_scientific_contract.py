"""Compile shared scientific JSON examples against the serialized TypeScript types."""
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/studio/scientific'


def main():
    source = ['import type {ScientificContext, SourceDocument, SourceAnchor} from "./scientific-context";']
    count = 0
    for path in sorted(FIXTURES.glob('*.json')):
        example = json.loads(path.read_text())
        if not isinstance(example, dict) or 'scientific_context' not in example:
            continue
        for key, shape in [('scientific_context', 'ScientificContext'), ('source_documents', 'SourceDocument[]'), ('anchors', 'SourceAnchor[]')]:
            source.append(f'({json.dumps(example[key], ensure_ascii=False)}) satisfies {shape};')
        count += 1
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', dir=ROOT / 'frontend/src/types', encoding='utf-8') as check:
        check.write('\n'.join(source))
        check.flush()
        subprocess.run([
            str(ROOT / 'frontend/node_modules/.bin/tsc'), '--noEmit', '--strict',
            '--skipLibCheck', '--moduleResolution', 'bundler', '--module', 'ESNext',
            '--target', 'ES2022', check.name,
        ], cwd=ROOT, check=True)
    print(f'{count} scientific fixtures conform to TypeScript contracts.')


if __name__ == '__main__':
    main()
