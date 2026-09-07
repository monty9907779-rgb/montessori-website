import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const destination = path.resolve(process.argv[2]);
const files = {};
for (const entry of fs.readdirSync(path.join(root, 'public'), { withFileTypes: true })) {
  if (entry.isDirectory() && fs.existsSync(path.join(root, 'public', entry.name, 'index.html'))) {
    for (const name of fs.readdirSync(path.join(root, 'public', entry.name))) {
      if (/\.(html|js|css)$/.test(name)) files[`${entry.name}/${name}`] = '';
    }
  }
}
for (const name of ['app.js', 'app-admin.css', 'dashboard.css', 'install.js', 'whatsapp-admin.css', 'whatsapp-admin.js', 'enrollment-transfer.css', 'enrollment-transfer.js', 'students-transfer.js', 'sw-update.js']) {
  files[`assets/${name}`] = '';
}
for (const name of ['sw.js', 'offline.html', 'manifest-staff.webmanifest', 'manifest-me.webmanifest', 'icon-maskable-512.png']) files[name] = '';
for (const name of Object.keys(files)) {
  const content = fs.readFileSync(path.join(root, 'public', name));
  files[name] = crypto.createHash('sha256').update(content).digest('hex');
  const target = path.join(destination, 'public', name);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
}
for (const [source, name] of [['scripts/deploy-static.py', 'deploy-static.py'], ['ops/nginx/montessori-ksa.conf', 'montessori-ksa.conf']]) {
  fs.copyFileSync(path.join(root, source), path.join(destination, name));
}
const revision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
fs.writeFileSync(path.join(destination, 'release.json'), JSON.stringify({ revision, files }, null, 2) + '\n');
console.log(`Packaged ${Object.keys(files).length} static files from public/ at ${revision}`);
