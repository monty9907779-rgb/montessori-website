#!/usr/bin/env python3
"""Python twin of scripts/package-static.mjs for hosts without Node (the server).

Builds the static release directory that scripts/deploy-static.py installs:

    python3 scripts/package-static.py /tmp/rel && python3 /tmp/rel/deploy-static.py /tmp/rel

Same file selection, same sw.js release stamp (mk-shell-<git rev>), same
release.json {revision, cacheName, files: {path: sha256}} as the Node packager,
so deploy-static.py cannot tell them apart. Run on the server from a fresh
clone of main when deploy.sh cannot be run from a workstation (no SSH key):
deploy-static.py also regenerates the inline-script CSP hashes — copying a page
such as accounts/index.html by hand leaves the old hashes in place and the
browser blanks the page.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'public'
FIXED_ASSETS = ['app.js', 'app-admin.css', 'bot.css', 'bot.js', 'dashboard.css',
                'fees-2026-2027.jpeg', 'install.js', 'logo-nav.webp', 'whatsapp-admin.css',
                'whatsapp-admin.js', 'enrollment-transfer.css', 'enrollment-transfer.js',
                'students-transfer.js', 'sw-update.js']
TOP_LEVEL = ['sw.js', 'offline.html', 'manifest-staff.webmanifest', 'manifest-me.webmanifest',
             'icon-maskable-512.png']
PLACEHOLDER = 'mk-shell-__RELEASE__'


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    destination = Path(sys.argv[1]).resolve()
    revision = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    cache_name = 'mk-shell-' + revision

    files = {}
    for entry in sorted(PUBLIC.iterdir()):
        if entry.is_dir() and (entry / 'index.html').exists():
            for child in sorted(entry.iterdir()):
                if re.search(r'\.(html|js|css)$', child.name):
                    files[entry.name + '/' + child.name] = ''
    for name in FIXED_ASSETS:
        files['assets/' + name] = ''
    # Every /assets/… a packaged page references must ship with it (see the
    # 15/9 note in package-static.mjs); a reference to a missing file fails.
    referenced = set()
    for name in list(files):
        if not name.endswith('.html'):
            continue
        html = (PUBLIC / name).read_text(encoding='utf-8')
        referenced.update(re.findall(r'(?:src|href)=["\']/assets/([^"\'?#]+)', html))
    added = []
    for rel in sorted(referenced):
        key = 'assets/' + rel
        if key in files:
            continue
        if not (PUBLIC / key).exists():
            raise SystemExit('Packaged page references /%s but public/%s does not exist' % (key, key))
        files[key] = ''
        added.append(key)
    for name in TOP_LEVEL:
        files[name] = ''

    for name in list(files):
        raw = (PUBLIC / name).read_bytes()
        if name == 'sw.js':
            content = raw.decode('utf-8')
            if PLACEHOLDER not in content:
                raise SystemExit('public/sw.js is missing the release cache placeholder')
            raw = content.replace(PLACEHOLDER, cache_name, 1).encode('utf-8')
        files[name] = hashlib.sha256(raw).hexdigest()
        target = destination / 'public' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    for source, name in (('scripts/deploy-static.py', 'deploy-static.py'),
                         ('ops/nginx/montessori-ksa.conf', 'montessori-ksa.conf')):
        shutil.copyfile(ROOT / source, destination / name)
    (destination / 'release.json').write_text(
        json.dumps({'revision': revision, 'cacheName': cache_name, 'files': files}, indent=2) + '\n',
        encoding='utf-8')
    print('Packaged %d static files from public/ at %s with cache %s%s' % (
        len(files), revision, cache_name,
        ' (+%d by reference: %s)' % (len(added), ', '.join(added)) if added else ''))


if __name__ == '__main__':
    main()
