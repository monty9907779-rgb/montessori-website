#!/usr/bin/env node
// Content-hash ?v= for the redesigned public pages (2026-11, from kindy-connect
// scripts/public-site/asset-versions.mjs). Sets every /assets/*.css|js reference
// in those pages, and in the assets that already use the hash scheme, to
// ?v=<first 10 hex of the file's sha256>, so a changed file gets a new URL.
// Admin pages keep their numeric ?v= (verify-admin.mjs pins those). Idempotent.
//
//   node scripts/asset-versions.mjs [--check]     (--check: exit 1 if stale)
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..', 'public');
const check = process.argv.includes('--check');
const redesigned = (text) => text.includes('<!--ps:js-->') || text.includes('/assets/home.css');
const hashScheme = /\/assets\/[\w./-]+\.(?:css|js)\?v=[0-9a-f]{10}\b/;

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* walk(p);
    else if (/\.(html|js)$/.test(name)) yield p;
  }
}

const hashes = new Map();
function version(asset) {
  if (!hashes.has(asset)) {
    const file = join(root, 'assets', asset);
    hashes.set(asset, existsSync(file) ? createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 10) : null);
  }
  return hashes.get(asset);
}

const REF = /(\/assets\/)([\w./-]+\.(?:css|js))(\?v=[\w.-]*)?(?=["'`)\s])/g;
const stale = [];
for (const file of walk(root)) {
  const before = readFileSync(file, 'utf8');
  const isAsset = file.startsWith(join(root, 'assets') + '/');
  if (isAsset ? !hashScheme.test(before) : !redesigned(before)) continue;
  const self = isAsset ? file.slice(join(root, 'assets').length + 1) : null;
  const after = before.replace(REF, (m, prefix, asset) => {
    if (asset === self) return m;   // a file naming itself can never match its own hash
    const v = version(asset);
    return v ? `${prefix}${asset}?v=${v}` : m;
  });
  if (after !== before) {
    stale.push(file.slice(root.length + 1));
    if (!check) writeFileSync(file, after);
  }
}
console.log(`${check ? 'stale' : 'updated'}: ${stale.length} file(s)${stale.length ? ' — ' + stale.join(', ') : ''}`);
if (check && stale.length) process.exit(1);
