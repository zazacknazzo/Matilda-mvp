// Compile the actual shared JSON examples against the additive TypeScript types.
// Run from the repository root after `npm ci` in frontend.
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync, unlinkSync, rmdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = resolve(import.meta.dirname, '..');
const runtime = join(root, '.runtime');
mkdirSync(runtime, { recursive: true });
const directory = mkdtempSync(join(runtime, 'scientific-types-'));
const target = join(directory, 'examples.ts');
const scenarios = ['crispr-doi', 'rna-doi', 'text-no-doi', 'mixed', 'no-coverage', 'rna-insufficient', 'rna-material'];
const header = `import type { SourceDocument, ScientificContext, SourceAnchor, ScientificMatch } from '../../frontend/src/types/scientific-context';
type Fixture = { schema_version: 1; source_documents: SourceDocument[]; scientific_context: ScientificContext; anchors: SourceAnchor[]; paper_dois: string[]; expected_matches: ScientificMatch[] };
`;
try {
  const examples = scenarios.map((name, i) => `const example${i} = ${readFileSync(join(root, 'tests/fixtures/studio/scientific', name + '.json'), 'utf8').trim()} satisfies Fixture;`);
  writeFileSync(target, header + examples.join('\n'));
  const result = spawnSync(process.execPath, [join(root, 'frontend/node_modules/typescript/bin/tsc'), '--noEmit', '--strict', '--skipLibCheck', '--target', 'ES2022', '--module', 'ESNext', '--moduleResolution', 'bundler', target], { stdio: 'inherit' });
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
  if (result.status === 0) console.log(`Scientific contracts: ${scenarios.length} shared fixtures passed TypeScript.`);
} finally {
  unlinkSync(target);
  rmdirSync(directory);
}
