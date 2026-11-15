#!/usr/bin/env python3
"""Server-side static pages sync from GitHub main (no Mac, no SSH key needed).

Run by server-apply.sh (daily root cron, after the pristine scan). It builds the
same static release that `bash deploy.sh` builds on a workstation, but only
installs it when that is provably safe:

* publisher-owned files (blog/index.html, rewritten daily by publish.py) are left out;
* a page is overwritten only if the live copy is byte-identical to SOME earlier
  version of that file in main's git history. A live page that matches no known
  version was edited by hand (the 2026-10-02 accounts/index.html incident):
  then NOTHING is deployed and the file names are logged for the owner;
* nginx config is NOT replaced (the live config is fed back to deploy-static.py
  unchanged); nginx rules ship through server-apply.sh instead;
* deploy-static.py itself backs up the site, checks checksums, refreshes the CSP
  hashes, reloads nginx and rolls back on any failure.

Default mode is CHECK (prints the plan, changes nothing). It installs only when
/opt/seo/static-sync.enable exists. Env MK_LIVE / MK_NGINX override paths (tests).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = os.environ.get('MK_REPO', 'https://github.com/monty9907779-rgb/montessori-website')
LIVE = Path(os.environ.get('MK_LIVE', '/var/www/montessori-ksa'))
NGINX = Path(os.environ.get('MK_NGINX', '/etc/nginx/sites-enabled/montessori-ksa'))
ENABLE = Path(os.environ.get('MK_ENABLE', '/opt/seo/static-sync.enable'))
EXCLUDE = {'blog/index.html'}      # rewritten every day by publish.py
STAMPED = {'sw.js'}                # release stamp differs per revision: always allowed
HISTORY = 300


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def history_hashes(clone, relpath):
    out = run('git', 'log', '--format=%H', '-n', str(HISTORY), '--', relpath, cwd=clone)
    seen = set()
    for commit in out.split():
        blob = subprocess.run(['git', 'show', commit + ':' + relpath], cwd=clone,
                              capture_output=True)
        if blob.returncode == 0:
            seen.add(sha(blob.stdout))
    return seen


def main():
    work = Path(tempfile.mkdtemp(prefix='static-sync-'))
    try:
        clone = work / 'mw'
        run('git', 'clone', '-q', '--depth', str(HISTORY), REPO, str(clone))
        rel = work / 'rel'
        run(sys.executable, str(clone / 'scripts/package-static.py'), str(rel))
        manifest = json.loads((rel / 'release.json').read_text())
        files = {n: d for n, d in manifest['files'].items() if n not in EXCLUDE}

        unchanged, new, ok, blocked = [], [], [], []
        for name, digest in sorted(files.items()):
            live = LIVE / name
            if not live.exists():
                new.append(name)
                continue
            live_sha = sha(live.read_bytes())
            if live_sha == digest:
                unchanged.append(name)
            elif name in STAMPED:
                ok.append(name)
            elif live_sha in history_hashes(clone, 'public/' + name):
                ok.append(name)
            else:
                blocked.append(name)
        print('static-sync plan: %d unchanged, %d new, %d to update, %d blocked (unknown live version)'
              % (len(unchanged), len(new), len(ok), len(blocked)))
        for label, names in (('new', new), ('update', ok), ('BLOCKED', blocked)):
            for name in names[:60]:
                print('  %s %s' % (label, name))
        if blocked:
            print('static-sync: NOT deploying. These live files match no version in git history '
                  '(hand-edited?). Owner decision needed:', ', '.join(blocked))
            return 0
        if not (new or [n for n in ok if n not in STAMPED]):
            print('static-sync: live already matches main (a differing sw.js stamp alone is not a reason to deploy).')
            return 0
        if not ENABLE.exists():
            print('static-sync: CHECK mode only (touch %s to allow installs).' % ENABLE)
            return 0

        # Filtered release: drop publisher-owned files, keep the live nginx config.
        for name in EXCLUDE:
            (rel / 'public' / name).unlink(missing_ok=True)
        manifest['files'] = files
        (rel / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        shutil.copyfile(NGINX, rel / 'montessori-ksa.conf')
        result = subprocess.run([sys.executable, str(rel / 'deploy-static.py'), str(rel)],
                                capture_output=True, text=True)
        print(result.stdout.strip())
        if result.returncode != 0:
            print('static-sync: deploy-static.py FAILED (rolled back):', result.stderr.strip()[-800:])
            return 1
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
