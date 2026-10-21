// Compile the actual shared JSON examples without type assertions or casts.
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync, unlinkSync, rmdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = resolve(import.meta.dirname, '..');
mkdirSync(join(root, '.runtime'), { recursive: true });
const directory = mkdtempSync(join(root, '.runtime', 'lesson-types-'));
const target = join(directory, 'examples.ts');
const scenarios = ['crispr-50', 'rna-50', 'no-enrichment-50', 'optional-fields'];
try {
  const header = "import type { LessonBundle } from '../../frontend/src/types/lesson';\n";
  const examples = scenarios.map((name, i) => `const example${i} = ${readFileSync(join(root, 'tests/fixtures/studio/lessons', name + '.json'), 'utf8').trim()} satisfies LessonBundle;`);
  writeFileSync(target, header + examples.join('\n'));
  const result = spawnSync(process.execPath, [join(root, 'frontend/node_modules/typescript/bin/tsc'), '--noEmit', '--strict', '--skipLibCheck', '--target', 'ES2022', '--module', 'ESNext', '--moduleResolution', 'bundler', target], { stdio: 'inherit' });
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
  if (result.status === 0) console.log(`Lesson contracts: ${scenarios.length} shared JSON fixtures passed TypeScript.`);
} finally {
  unlinkSync(target);
  rmdirSync(directory);
}
