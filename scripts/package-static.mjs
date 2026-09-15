import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const destination = path.resolve(process.argv[2]);
const files = {};
const revision = execFileSync('git', ['rev-parse', '--short=12', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
const cacheName = `mk-shell-${revision}`;
for (const entry of fs.readdirSync(path.join(root, 'public'), { withFileTypes: true })) {
  if (entry.isDirectory() && fs.existsSync(path.join(root, 'public', entry.name, 'index.html'))) {
    for (const name of fs.readdirSync(path.join(root, 'public', entry.name))) {
      if (/\.(html|js|css)$/.test(name)) files[`${entry.name}/${name}`] = '';
    }
  }
}
for (const name of ['app.js', 'app-admin.css', 'bot.css', 'bot.js', 'dashboard.css', 'fees-2026-2027.jpeg', 'install.js', 'logo-nav.webp', 'whatsapp-admin.css', 'whatsapp-admin.js', 'enrollment-transfer.css', 'enrollment-transfer.js', 'students-transfer.js', 'sw-update.js']) {
  files[`assets/${name}`] = '';
}
// 15/9: the allowlist above silently dropped assets/ai.js for twelve days — the
// AI page kept shipping index.html that pointed at a script this packager never
// sent. Every /assets/… the packaged pages reference must ship with them, and a
// reference to a file that does not exist locally is a hard failure, not a
// green deploy. Files that live only on the server (app.css, wa-fix.js,
// reviews.json, …) are untouched: only what packaged HTML references is added.
const referenced = new Set();
for (const name of Object.keys(files)) {
  if (!name.endsWith('.html')) continue;
  const html = fs.readFileSync(path.join(root, 'public', name), 'utf8');
  for (const match of html.matchAll(/(?:src|href)=["']\/assets\/([^"'?#]+)/g)) referenced.add(match[1]);
}
const addedByReference = [];
for (const rel of [...referenced].sort()) {
  const key = `assets/${rel}`;
  if (key in files) continue;
  if (!fs.existsSync(path.join(root, 'public', key))) {
    throw new Error(`Packaged page references /${key} but public/${key} does not exist`);
  }
  files[key] = '';
  addedByReference.push(key);
}
for (const name of ['sw.js', 'offline.html', 'manifest-staff.webmanifest', 'manifest-me.webmanifest', 'icon-maskable-512.png']) files[name] = '';
for (const name of Object.keys(files)) {
  const raw = fs.readFileSync(path.join(root, 'public', name));
  let buffer = raw;
  if (name === 'sw.js') {
    const content = raw.toString('utf8');
    if (!content.includes('mk-shell-__RELEASE__')) {
      throw new Error('public/sw.js is missing the release cache placeholder');
    }
    buffer = Buffer.from(content.replace('mk-shell-__RELEASE__', cacheName), 'utf8');
  }
  files[name] = crypto.createHash('sha256').update(buffer).digest('hex');
  const target = path.join(destination, 'public', name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, buffer);
}
for (const [source, name] of [['scripts/deploy-static.py', 'deploy-static.py'], ['ops/nginx/montessori-ksa.conf', 'montessori-ksa.conf']]) {
  fs.copyFileSync(path.join(root, source), path.join(destination, name));
}
fs.writeFileSync(path.join(destination, 'release.json'), JSON.stringify({ revision, cacheName, files }, null, 2) + '\n');
console.log(`Packaged ${Object.keys(files).length} static files from public/ at ${revision} with cache ${cacheName}` + (addedByReference.length ? ` (+${addedByReference.length} by reference: ${addedByReference.join(', ')})` : ''));
