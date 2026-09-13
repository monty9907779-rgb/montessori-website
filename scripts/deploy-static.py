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
        script_type = attrs.get('type', '').lower().strip()
        executable_script = (
            tag == 'script'
            and 'src' not in attrs
            and script_type not in {'application/ld+json', 'application/json', 'importmap'}
        )
        if tag == 'style' or executable_script:
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
    required_sources = {
        'img-src': ['https://www.google.de'],
        # analytics.google.com is where gtag actually sends hits. The policy
        # listed only *.analytics.google.com, which does not match the apex
        # host, so every GA beacon was refused and the blog reported nothing.
        'connect-src': ['https://ad.doubleclick.net', 'https://stats.g.doubleclick.net',
                        'https://www.google.com', 'https://analytics.google.com'],
    }
    for directive, sources in required_sources.items():
        match = re.search(r'(' + re.escape(directive) + r' [^;]+)', policy)
        if not match:
            raise RuntimeError('Missing CSP directive: ' + directive)
        value = match.group(1)
        additions = [source for source in sources if source not in value]
        if additions:
            policy = policy[:match.end()] + ' ' + ' '.join(additions) + policy[match.end():]
    lines = ['# Generated exactly from the current canonical static release.']
    for group, hashes in parser.values.items():
        prefix = 'mk_csp_' + group + '_'
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


def refresh_tamper_baseline():
    """Keep the daily security scanner's pristine copies in step with this release.

    /opt/montessori/security_scan.py restores /etc/nginx/sites-enabled/montessori-ksa
    and snippets/mk-headers.conf from baseline/pristine whenever their sha256
    differs from baseline/hashes.txt. Without this step every deploy that touches
    nginx is silently reverted at 06:00 the next morning (seen 2026-09-09..13).
    """
    base = Path('/opt/montessori/baseline')
    hashes = base / 'hashes.txt'
    pristine = base / 'pristine'
    if not hashes.exists() or not pristine.exists():
        return
    lines = hashes.read_text().splitlines()
    out = []
    for line in lines:
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1] in (str(NGINX), str(HEADERS)):
            target = Path(parts[1])
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            copy = pristine / target.relative_to('/')
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, copy)
            out.append(digest + '  ' + parts[1])
        else:
            out.append(line)
    atomic(hashes, ('\n'.join(out) + '\n').encode())


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
        refresh_tamper_baseline()
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
