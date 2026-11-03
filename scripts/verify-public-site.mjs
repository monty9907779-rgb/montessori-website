// Checks the redesigned public pages in public/ (home, English pages, /blog/,
// /privacy/, /wa/, /partners/) before deploy.sh ships them, and the assets
// /opt/seo/publish.py needs to render articles in the redesign template.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';

const root = path.resolve(import.meta.dirname, '..', 'public');
const SITE = 'https://montessori-ksa.com';
const redesigned = (html) => html.includes('<!--ps:js-->') || html.includes('/assets/home.css');
const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
  e.isDirectory() ? walk(path.join(dir, e.name)) : (e.name === 'index.html' ? [path.join(dir, e.name)] : []));

const pages = walk(root).filter((file) => redesigned(fs.readFileSync(file, 'utf8')));
assert.ok(pages.length >= 20, `expected the redesigned pages in public/, found ${pages.length}`);
for (const must of ['index.html', 'en/index.html', 'blog/index.html', 'en/blog/index.html', 'privacy/index.html', 'wa/index.html']) {
  assert.ok(pages.includes(path.join(root, must)), `public/${must} is missing or not the redesign`);
}

const version = (asset) => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'assets', asset))).digest('hex').slice(0, 10);
let refs = 0;
for (const file of pages) {
  const rel = path.relative(root, file);
  const html = fs.readFileSync(file, 'utf8');
  // every /assets/ file a page names (src, href, srcset, inline url(), JSON-LD) exists
  for (const m of html.matchAll(/(?:https:\/\/montessori-ksa\.com)?\/assets\/([\w./-]+\.(?:css|js|woff2|webp|avif|jpe?g|png|svg|ico|json))(\?v=[\w.-]+)?/g)) {
    assert.ok(fs.existsSync(path.join(root, 'assets', m[1])), `${rel}: missing /assets/${m[1]}`);
    if (m[2] && /^\?v=[0-9a-f]{10}$/.test(m[2])) {
      assert.equal(m[2].slice(3), version(m[1]), `${rel}: stale ?v= on /assets/${m[1]} (run node scripts/asset-versions.mjs)`);
    }
    refs++;
  }
  // no script the redesign removed, no inline handlers the CSP would block
  assert.ok(!/static\.cloudflareinsights\.com|__CF\$cv\$params/.test(html), `${rel}: Cloudflare edge snippet captured in the page`);
  assert.ok(!html.includes('montessori-registration-fix'), `${rel}: old registration-fix script`);
  assert.ok(!/\son[a-z]+="/i.test(html), `${rel}: inline event handler`);
  assert.ok(!/4\.7\s*(?:★|&#9733;)|٤٫٧/.test(html), `${rel}: numeric star rating`);
  assert.ok(html.includes(`<link rel="canonical" href="${SITE}/`), `${rel}: missing canonical`);
}

// what publish.py's redesign_ready() and hero_figure() read from the webroot
for (const f of ['assets/home.css', 'assets/logo-mark-92.webp', 'assets/blog.css', 'assets/fonts.css']) {
  assert.ok(fs.existsSync(path.join(root, f)), `public/${f} missing (publish.py redesign_ready)`);
}
const blogCss = fs.readFileSync(path.join(root, 'assets/blog.css'), 'utf8');
for (const marker of ['/* ---------- blog index ---------- */', '/* ---------- article page ---------- */', '.lead-answer']) {
  assert.ok(blogCss.includes(marker), `assets/blog.css lacks ${marker} (publish.py splits it on these)`);
}
const POOL = ['18AmxJGSzkXFACqG4pA2qasufXmQMXXHK', '1tOy85z8eimnAXtmOaa061NYhIdv_NemA', '1X4ke_GBVBaE5dqFJ8ACfAKeoNNzssFNQ',
  '1VMJOmDnqr3niyLeye2SAtyQExXYTj4ns', '1_lh7XoF9FqgyROroAHGmOb7HRh1MuEaQ', '1cNkIXcn45SF2iG0P09muLu0d4zmEEaVq'];
for (const id of POOL) {
  for (const w of [480, 640, 800, 1200, 1520]) for (const ext of ['avif', 'webp']) {
    assert.ok(fs.existsSync(path.join(root, `assets/img/${id}-${w}.${ext}`)), `missing assets/img/${id}-${w}.${ext}`);
  }
  for (const w of [800, 1200]) assert.ok(fs.existsSync(path.join(root, `assets/img/${id}-${w}.jpg`)), `missing assets/img/${id}-${w}.jpg`);
}
console.log(`Verified ${pages.length} redesigned public pages, ${refs} asset references, and the article photo set.`);
