import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import vm from 'node:vm';

const root = path.resolve(import.meta.dirname, '..', 'public');
const projectRoot = path.resolve(import.meta.dirname, '..');
const versions = { 'app.js' : '55', 'app-admin.css': '11', 'install.js': '4' };
const referencedScripts = new Set();
let pages = 0;
for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
  const file = path.join(root, entry.name, 'index.html');
  if (!entry.isDirectory() || !fs.existsSync(file)) continue;
  const html = fs.readFileSync(file, 'utf8');
  assert.ok(html.includes('/assets/install.js?v=4'), `${entry.name}: missing install.js`);
  assert.ok(!/<script\b[^>]*\bsrc=["'][^"']+["'][^>]*><\/script>\s*<\/script>/i.test(html), `${entry.name}: stray script close after external script`);
  for (const [asset, version] of Object.entries(versions)) {
    for (const match of html.matchAll(new RegExp('/assets/' + asset.replace('.', '\\.') + '\\?v=(\\d+)', 'g'))) {
      assert.equal(match[1], version, `${entry.name}: outdated ${asset}`);
    }
  }
  for (const match of html.matchAll(/(?:src|href)="(\/[^"?#]+\.(?:js|css))(?:\?[^"#]*)?"/g)) {
    assert.ok(fs.existsSync(path.join(root, match[1])), `${entry.name}: missing ${match[1]}`);
    if (match[1].endsWith('.js')) referencedScripts.add(match[1].slice(1));
  }
  pages++;
}
const dashboard = fs.readFileSync(path.join(root, 'dashboard/index.html'), 'utf8');
assert.ok(dashboard.includes('/assets/dashboard.css?v=1'));
assert.ok(dashboard.includes('/dashboard/excel-sync.js?v=1'));
assert.ok(dashboard.includes('/dashboard/excel-sync.css?v=1'));
assert.ok(!dashboard.includes('dashboard-specific polish'));
assert.ok(fs.readFileSync(path.join(root, 'sw.js'), 'utf8').includes("mk-shell-__RELEASE__"));
assert.ok(fs.readFileSync(path.join(root, 'assets/install.js'), 'utf8').includes("updateViaCache: 'none'"));
const nginx = fs.readFileSync(path.join(projectRoot, 'ops/nginx/montessori-ksa.conf'), 'utf8');
assert.ok(nginx.includes('location ^~ /api/'));
assert.ok(nginx.includes('proxy_pass http://127.0.0.1:8069;'));
assert.ok(nginx.includes('location = /sw.js'));
assert.ok(nginx.includes('Cache-Control "no-cache, must-revalidate"'));
assert.ok(nginx.includes('location = /manifest.webmanifest'));
assert.ok(nginx.includes('Cache-Control "no-cache"'));
assert.ok(nginx.includes('location ~* \\.(js|css)$'));
const logic = fs.readFileSync(path.join(root, 'dashboard/dashboard-inline-1.js'), 'utf8');
assert.ok(!logic.includes('whatsapp_autoreply') && !logic.includes('whatsapp_settings'));
assert.ok(logic.includes('href="/whatsapp/"'));
for (const file of new Set(['assets/app.js', 'assets/install.js', 'assets/whatsapp-admin.js', 'sw.js', 'dashboard/dashboard-inline-1.js', 'dashboard/dashboard-inline-2.js', ...referencedScripts])) {
  new vm.Script(fs.readFileSync(path.join(root, file), 'utf8'), { filename: file });
}

const events = {};
const deleted = [];
let claimed = false;
let request;
const cache = { add: async () => {}, };
const context = {
  URL,
  location: { origin: 'https://montessori-ksa.com' },
  self: { addEventListener: (name, listener) => { events[name] = listener; }, skipWaiting: async () => {}, clients: { claim: async () => { claimed = true; } } },
  caches: { open: async () => cache, keys: async () => ['mk-shell-old', 'mk-shell-__RELEASE__', 'unrelated'], delete: async (key) => deleted.push(key), match: async () => 'offline' },
  fetch: async (...args) => { request = args; return 'online'; },
};
vm.runInNewContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'), context);
let pending;
events.activate({ waitUntil: (promise) => { pending = promise; } });
await pending;
assert.deepEqual(deleted, ['mk-shell-old']);
assert.ok(claimed);
function fetchEvent(url, mode = 'cors') {
  let response;
  events.fetch({ request: { method: 'GET', url, mode }, respondWith: (value) => { response = value; } });
  return response;
}
assert.equal(fetchEvent('https://montessori-ksa.com/api/dashboard'), undefined);
assert.equal(await fetchEvent('https://montessori-ksa.com/assets/app.js?v=48'), 'online');
assert.equal(request[1].cache, 'no-cache');
assert.equal(await fetchEvent('https://montessori-ksa.com/assets/install.js?v=4'), 'online');
assert.equal(request[1].cache, 'no-cache');
context.fetch = async () => { throw Error('offline'); };
assert.equal(await fetchEvent('https://montessori-ksa.com/dashboard/', 'navigate'), 'offline');
console.log(`Verified ${pages} admin pages, independent WhatsApp, script syntax, and worker cache lifecycle.`);
