#!/usr/bin/env node
/**
 * Regenerate frontend/src/api/openapi.d.ts from the backend's OpenAPI
 * schema. Invokes the backend's dump_openapi.py via the venv python
 * (prefers backend/venv, falls back to whichever python3 is on PATH),
 * then pipes the JSON through openapi-typescript.
 *
 * Usage:
 *   node scripts/generate-api-types.mjs            # write to disk
 *   node scripts/generate-api-types.mjs --check    # fail if out-of-date (CI)
 */

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import openapiTS, { astToString } from 'openapi-typescript';

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = resolve(HERE, '..');
const REPO_ROOT = resolve(FRONTEND_ROOT, '..');
const BACKEND_ROOT = resolve(REPO_ROOT, 'backend');
const OUTPUT_PATH = resolve(FRONTEND_ROOT, 'src/api/openapi.d.ts');

const CHECK_MODE = process.argv.includes('--check');

function resolvePython() {
  // Preference order: backend venv's python (has all project deps),
  // a repo-level /tmp workstation venv, then whatever's on PATH.
  const candidates = [
    resolve(BACKEND_ROOT, 'venv/bin/python'),
    '/tmp/whis-v24-venv/bin/python',
    'python3',
    'python',
  ];
  for (const candidate of candidates) {
    if (candidate.includes('/') && !existsSync(candidate)) continue;
    const probe = spawnSync(candidate, ['--version'], { encoding: 'utf-8' });
    if (probe.status === 0) return candidate;
  }
  throw new Error(
    'No usable Python interpreter found. Activate the backend venv or install python3.',
  );
}

function dumpOpenApi() {
  const python = resolvePython();
  const dump = spawnSync(
    python,
    [resolve(BACKEND_ROOT, 'scripts/dump_openapi.py')],
    { encoding: 'utf-8', maxBuffer: 32 * 1024 * 1024, cwd: BACKEND_ROOT },
  );
  if (dump.status !== 0) {
    console.error(dump.stderr);
    throw new Error('dump_openapi.py failed');
  }
  return dump.stdout;
}

async function generateTypes(schemaJson) {
  const schemaObject = JSON.parse(schemaJson);
  const ast = await openapiTS(schemaObject, {
    // Pydantic emits `default: <value>` on optional fields that have a
    // default. Without this flag, openapi-typescript promotes those
    // fields to required (because server responses will always include
    // them). Request bodies rely on Pydantic filling the default
    // server-side, so frontend callers shouldn't be forced to supply
    // them. False gives us `field?: T | null` everywhere a Pydantic
    // Optional field carries a default.
    defaultNonNullable: false,
  });
  return astToString(ast);
}

async function main() {
  const schemaJson = dumpOpenApi();
  const generated = await generateTypes(schemaJson);

  if (CHECK_MODE) {
    if (!existsSync(OUTPUT_PATH)) {
      console.error(
        `\n✗ ${OUTPUT_PATH} is missing. Run \`npm run codegen:api\` and commit the result.\n`,
      );
      process.exit(1);
    }
    const current = readFileSync(OUTPUT_PATH, 'utf-8');
    if (current.trim() !== generated.trim()) {
      console.error(
        `\n✗ ${OUTPUT_PATH} is out of date.\n` +
          `  Run \`npm run codegen:api\` and commit the result.\n`,
      );
      process.exit(1);
    }
    console.log('✓ openapi.d.ts matches the backend schema.');
    return;
  }

  mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
  writeFileSync(OUTPUT_PATH, generated);
  console.log(`✓ wrote ${OUTPUT_PATH}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
