#!/usr/bin/env python3
"""Install the reviewed static admin release, with backup and nginx rollback."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

SITE = Path('/var/www/montessori-ksa')
NGINX = Path('/etc/nginx/sites-enabled/montessori-ksa')
PARTS = Path('/etc/nginx/snippets/mk-csp-parts.conf')
HEADERS = Path('/etc/nginx/snippets/mk-headers.conf')


class Hashes(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.values = {'script': set(), 'style': set(), 'attr': set()}
        self.tag = None
        self.body = ''

    def add(self, group, value):
        digest = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        self.values[group].add("'sha256-" + digest + "'")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'style' in attrs:
            self.add('attr', attrs['style'])
        if tag == 'style' or (tag == 'script' and 'src' not in attrs):
            self.tag, self.body = tag, ''

    def handle_data(self, data):
        if self.tag:
            self.body += data

    def handle_endtag(self, tag):
        if tag == self.tag:
            self.add(tag, self.body)
            self.tag = None


def atomic(path, content, owner=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.release-tmp')
    temporary.write_bytes(content)
    temporary.chmod(0o644)
    if owner:
        shutil.chown(temporary, *owner)
    os.replace(temporary, path)


def refresh_csp():
    parser = Hashes()
    for file in SITE.rglob('*.html'):
        if any(part.startswith('_status-') for part in file.parts):
            continue
        parser.feed(file.read_text(encoding='utf-8'))
    policy = HEADERS.read_text()
    current = PARTS.read_text()
    lines = ['# Generated from the canonical static release; existing grants preserved.']
    for group, hashes in parser.values.items():
        prefix = 'mk_csp_' + group + '_'
        for value in re.findall(r'set \$' + prefix + r'\d+ "([^"]*)";', current):
            hashes.update(value.split())
        chunks = ['']
        for value in sorted(hashes):
            if len(chunks[-1]) + len(value) > 1700:
                chunks.append('')
            chunks[-1] += (' ' if chunks[-1] else '') + value
        names = []
        for index, value in enumerate(chunks, 1):
            name = '$' + prefix + f'{index:02d}'
            names.append(name)
            lines.append('set ' + name + ' "' + value + '";')
        policy, count = re.subn(r'\$' + prefix + r'\d+(?:\s+\$' + prefix + r'\d+)*', ' '.join(names), policy)
        if count != 1:
            raise RuntimeError('Unexpected CSP variable layout: ' + group)
    atomic(PARTS, ('\n'.join(lines) + '\n').encode())
    atomic(HEADERS, policy.encode())


def main():
    release = Path(sys.argv[1]).resolve()
    manifest = json.loads((release / 'release.json').read_text())
    for name, digest in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Invalid release path')
        if hashlib.sha256((release / 'public' / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Release checksum mismatch: ' + name)
    subprocess.run(['nginx', '-t'], check=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = Path('/opt/montessori/backups') / ('static-' + stamp)
    backup.mkdir(parents=True)
    shutil.copytree(SITE, backup / 'site')
    for file in [NGINX, PARTS, HEADERS]:
        shutil.copy2(file, backup / file.name)
    duplicate = NGINX.with_name('montessori-ksa.orig')
    duplicate_backup = backup / 'montessori-ksa.orig'
    existed = {name for name in manifest['files'] if (SITE / name).exists()}
    try:
        # Assets precede HTML, so new documents never reference missing files.
        for name in sorted(manifest['files'], key=lambda name: name.endswith('.html')):
            atomic(SITE / name, (release / 'public' / name).read_bytes(), ('www-data', 'www-data'))
        atomic(NGINX, (release / 'montessori-ksa.conf').read_bytes())
        if duplicate.exists():
            shutil.move(duplicate, duplicate_backup)
        refresh_csp()
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        for name, digest in manifest['files'].items():
            if hashlib.sha256((SITE / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Installed checksum mismatch: ' + name)
    except Exception:
        for name in manifest['files']:
            if name in existed:
                shutil.copy2(backup / 'site' / name, SITE / name)
            elif (SITE / name).exists():
                (SITE / name).unlink()
        for file in [NGINX, PARTS, HEADERS]:
            shutil.copy2(backup / file.name, file)
        if duplicate_backup.exists():
            shutil.copy2(duplicate_backup, duplicate)
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        raise
    shutil.copy2(release / 'release.json', backup / 'release.json')
    old_deploy = Path('/root/deploy-montessori/deploy.sh')
    if old_deploy.exists():
        shutil.copy2(old_deploy, backup / 'legacy-deploy.sh')
        atomic(old_deploy, b'#!/bin/sh\necho "Retired deployment source. Run bash deploy.sh from the montessori-website Git repository." >&2\nexit 1\n')
        old_deploy.chmod(0o755)
    print('DEPLOYED ' + manifest['revision'] + ' BACKUP=' + str(backup))


if __name__ == '__main__':
    main()
