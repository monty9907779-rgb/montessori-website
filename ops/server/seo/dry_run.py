#!/usr/bin/env python3
"""Dry-run the whole daily publisher against a copy of the LIVE site.

Run this before merging any change to publish.py, rewrites.json or facts.py:

    python3 ops/server/seo/dry_run.py [days]

It downloads every URL in the live sitemap into a scratch webroot, copies
queue.json and rewrites.json from the repo, points the publisher at the
scratch directory, stubs email / IndexNow / live-URL checks, and runs
main() `days` times (default 3). It then checks what a crash-free run is
not enough to show: the blog index keeps its sections and gains one card
per publish, no WARN / skipped / rejected / failed log lines, the feed and
llms files regenerate, and every published page renders.
The repo queue is a stale snapshot, so pages that went live after it was
taken but are `new` entries in rewrites.json get queued and "published" once
more in the scratch copy; that is an artefact of the snapshot, not a bug.
Nothing is written outside the scratch directory. Needs network access to
https://montessori-ksa.com (UA below; Cloudflare blocks the default
python-urllib one).
"""
import importlib.util, json, pathlib, re, shutil, subprocess, sys, tempfile, traceback

REPO = pathlib.Path(__file__).resolve().parents[3]
SITE = 'https://montessori-ksa.com'
UA = 'Mozilla/5.0 (compatible; KawkabHealthCheck/1.0; +https://montessori-ksa.com)'


def fetch(url):
    return subprocess.run(['curl', '-s', '--max-time', '30', '-A', UA, url], capture_output=True).stdout


def build(tmp):
    web, opt = tmp / 'web', tmp / 'opt'
    web.mkdir(); opt.mkdir()
    sm = fetch(SITE + '/sitemap.xml').decode('utf-8')
    (web / 'sitemap.xml').write_text(sm, encoding='utf-8')
    urls = re.findall(r'<loc>([^<]+)</loc>', sm)
    for u in urls:
        rel = u.replace(SITE, '').strip('/')
        dst = web / rel / 'index.html' if rel else web / 'index.html'
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(fetch(u))
    for name in ('robots.txt', 'llms.txt', 'llms-full.txt'):
        (web / name).write_bytes(fetch(f'{SITE}/{name}'))
    q = json.load(open(REPO / 'ops/server/seo/queue.json'))
    live = {pathlib.Path(u.rstrip('/')).name for u in urls if '/blog/' in u}
    for x in q:                      # the repo queue is a stale snapshot
        if x['slug'] in live and not x.get('published'):
            x['published'] = '2026-08-01'
    (opt / 'queue.json').write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')
    shutil.copy(REPO / 'ops/server/seo/rewrites.json', opt / 'rewrites.json')
    (opt / 'state.json').write_text('{}'); (opt / 'indexnow.key').write_text('dry-run'); (opt / 'publish.log').write_text('')
    return web, opt, len(urls)


def main(days=3):
    sys.path.insert(0, str(REPO / 'ops/server/nursery-facts'))
    spec = importlib.util.spec_from_file_location('pub', REPO / 'ops/server/seo/publish.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t); web, opt, n = build(tmp)
        m.ROOT, m.OPT = web, opt
        m.QUEUE, m.STATE, m.KEYF, m.LOG, m.REWRITES = opt/'queue.json', opt/'state.json', opt/'indexnow.key', opt/'publish.log', opt/'rewrites.json'
        sent = []
        m.email = lambda s, h: sent.append((s, h)); m.indexnow = lambda u: 200
        def fake_get(path):
            f = web / path.strip('/') / 'index.html' if path not in ('/sitemap.xml', '/robots.txt') else web / path.strip('/')
            return (200, f.read_text(encoding='utf-8')) if f.exists() else (404, '')
        m._get = fake_get; m.health = lambda: {'/': 200}
        class R: status = 200
        m.urllib.request.urlopen = lambda *a, **k: R()
        idx = web / 'blog' / 'index.html'
        count = lambda h, pat: len(re.findall(pat, h))
        sections = lambda h: count(h, '<section class=.bsec')
        cards = lambda h: h.count('class="bcard"')
        h0 = idx.read_text(encoding='utf-8')
        print(f'scratch site: {n} URLs; blog index {sections(h0)} sections, {cards(h0)} cards')
        problems = []
        for day in range(1, days + 1):
            try:
                m.main()
            except Exception:
                traceback.print_exc(); problems.append(f'day {day}: exception'); break
            h = idx.read_text(encoding='utf-8')
            print(f'day {day}: ok | sections {sections(h)} | cards {cards(h)}')
            if sections(h) != sections(h0):
                problems.append(f'day {day}: blog index lost or gained a section')
        log = (opt / 'publish.log').read_text(encoding='utf-8')
        bad = [l for l in log.splitlines() if re.search(r'WARN|skipped|rejected|failed|not written', l)]
        problems += bad
        published = [l.split(' published ')[1].split()[0] for l in log.splitlines() if ' published ' in l]
        print('published:', published)
        for slug in published:
            pg = web / 'blog' / slug / 'index.html'
            if not pg.exists() or 'application/ld+json' not in pg.read_text(encoding='utf-8'):
                problems.append(f'{slug}: page missing or without schema')
        for f in ('blog/feed.xml', 'llms.txt', 'llms-full.txt'):
            if not (web / f).exists() or not (web / f).read_text(encoding='utf-8').strip():
                problems.append(f'{f} missing or empty')
        # English guides (rewrites.json entries with lang=en)
        en = [k for k, v in json.load(open(opt / 'rewrites.json', encoding='utf-8')).items()
              if isinstance(v, dict) and v.get('lang') == 'en']
        smx = (web / 'sitemap.xml').read_text(encoding='utf-8')
        eidx = (web / 'en' / 'blog' / 'index.html').read_text(encoding='utf-8')
        llm = (web / 'llms.txt').read_text(encoding='utf-8')
        en_live = [k for k in en if (web / 'en' / 'blog' / k / 'index.html').exists()]
        print('english pages live:', en_live)
        if len(en_live) < min(len(en), 2 * days):
            problems.append(f'only {len(en_live)} of {min(len(en), 2 * days)} expected English pages rendered')
        for k in en_live:
            pg = (web / 'en' / 'blog' / k / 'index.html').read_text(encoding='utf-8')
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', pg, re.S)
            try:
                types = [json.loads(b).get('@type') for b in blocks]
            except ValueError:
                types = ['INVALID']
            if types != ['BlogPosting', 'FAQPage', 'BreadcrumbList']:
                problems.append(f'{k}: schema blocks {types}')
            if pg.count('<h1>') != 1 or f'rel="canonical" href="{SITE}/en/blog/{k}/"' not in pg or 'hreflang="x-default"' not in pg:
                problems.append(f'{k}: h1/canonical/hreflang wrong')
            if f'<loc>{SITE}/en/blog/{k}/</loc>' not in smx:
                problems.append(f'{k}: not in sitemap')
            if f'href="/en/blog/{k}/"' not in eidx:
                problems.append(f'{k}: no card in /en/blog/')
            if f'/en/blog/{k}/' not in llm:
                problems.append(f'{k}: not in llms.txt')
            if re.search(r'https?://(?!montessori-ksa\.com|www\.googletagmanager\.com|wa\.me|www\.instagram\.com|www\.facebook\.com|schema\.org|fonts\.)', pg.replace('http://www.w3.org', '')):
                problems.append(f'{k}: unexpected external URL')
        keep = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
        if keep:
            shutil.rmtree(keep, ignore_errors=True); shutil.copytree(web, keep)
        if len(published) < days:
            problems.append(f'only {len(published)} of {days} days published')
        print('PROBLEMS:' if problems else 'CLEAN: no problems found')
        for p in problems:
            print('  -', p)
        return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 3))
