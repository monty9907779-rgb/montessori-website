#!/bin/bash
# Idempotent server-side apply, fetched from GitHub main and run daily by /etc/cron.d/seo-server-apply
# (installed once by install-server-apply.sh). Edit THIS file to ship server changes (nginx rules etc.).
#
# 1. publish.py from main: seven articles that competed for «حضانة اطفال جدة»
#    are merged into best-montessori-nursery-jeddah (REDIRECTED), /wa/ leaves
#    the sitemap.
# 2. about pages: shorter title / description, English privacy link.
# 3. nginx: 301 rules for the merged articles (nginx -t first, restored on failure).
# 4. site refresh as www-data: internal links, blog index, sitemap, llms.txt and
#    feed drop the merged URLs; their pages are removed only after the live URL
#    is confirmed to 301 (copies in /opt/seo/retired/). No article is published,
#    no email is sent.
set -u
RAW=https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main
W=/var/www/montessori-ksa
NGX=/etc/nginx/sites-enabled/montessori-ksa
T=$(mktemp -d)
SCAN=/opt/security-weekly/pristine_sync.py
stamp=$(date +%Y%m%d-%H%M%S)
fetch() { curl -fsSL --max-time 60 -o "$2" "$RAW/$1?t=$(date +%s)"; }
scan() { [ -f "$SCAN" ] || return 0; python3 "$SCAN" --scan "$1" --as "$2"; }

echo "== 1. publish.py from main (security scan first)"
if fetch ops/server/seo/publish.py "$T/publish.py" && python3 -m py_compile "$T/publish.py" \
   && grep -q retire_redirected_page "$T/publish.py" && scan "$T/publish.py" /opt/seo/publish.py; then
  cp -p /opt/seo/publish.py "/opt/seo/publish.py.bak-merge-$stamp"
  cat "$T/publish.py" > /opt/seo/publish.py
  [ -d /opt/montessori/baseline/pristine ] && cp -p /opt/seo/publish.py /opt/montessori/baseline/pristine/publish.py && echo "baseline refreshed"
  echo "publish.py installed"
else
  echo "publish.py NOT installed (download/compile/scan failed)"; exit 1
fi

echo "== 2. about pages (scan first)"
for rel in about/index.html en/about/index.html; do
  f="$T/$(echo "$rel" | tr '/' '_')"
  fetch "public/$rel" "$f" || { echo "skip $rel: download"; continue; }
  if scan "$f" "$W/$rel"; then
    cp -p "$W/$rel" "/opt/seo/$(echo "$rel" | tr '/' '_').bak-merge-$stamp" 2>/dev/null
    install -m 644 -o www-data -g www-data "$f" "$W/$rel" && echo "installed $rel"
  else
    echo "skip $rel: scan flagged it"
  fi
done

echo "== 3. nginx 301 rules"
if grep -q 'best-nursery-guide-jeddah/' "$NGX"; then
  echo "rules already present"
else
  cp -p "$NGX" "/opt/seo/nginx-montessori-ksa.bak-merge-$stamp"
  python3 - "$NGX" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read()
anchor = "return 301 /blog/nursery-registration-documents-jeddah/;\n    }\n"
rules = {
    'best-nurseries-jeddah-2026': 'best-montessori-nursery-jeddah',
    'best-nursery-guide-jeddah': 'best-montessori-nursery-jeddah',
    'trusted-nursery-recommendation-jeddah': 'best-montessori-nursery-jeddah',
    'reliable-nursery-recommendation-jeddah': 'best-montessori-nursery-jeddah',
    'safe-educational-nursery-options-jeddah': 'best-montessori-nursery-jeddah',
    'safe-educational-nursery-jeddah-options': 'best-montessori-nursery-jeddah',
    'best-quality-price-nursery-jeddah': 'nursery-prices-jeddah',
}
block = "    # 2026-11-04: articles merged into one pillar (REDIRECTED in publish.py).\n" + "".join(
    "    location = /blog/%s/ {\n        return 301 /blog/%s/;\n    }\n" % kv for kv in rules.items())
if anchor in t:
    t = t.replace(anchor, anchor + block, 1)
else:
    # no earlier redirect rule: put them right after the status-file guard
    guard = "location ^~ /_status- { return 404; }\n"
    if guard not in t:
        sys.exit("no anchor found in nginx config")
    t = t.replace(guard, guard + "\n" + block, 1)
open(p, 'w').write(t)
print("rules added")
PY
  if nginx -t 2>&1; then
    systemctl reload nginx && echo "nginx reloaded"
  else
    cp -p "/opt/seo/nginx-montessori-ksa.bak-merge-$stamp" "$NGX"; echo "nginx -t failed, config restored"; exit 1
  fi
fi

echo "== 4. site refresh (as www-data, no article published)"
cp -p "$W/sitemap.xml" "/opt/seo/sitemap.xml.bak-merge-$stamp"
cp -p "$W/index.html" "/opt/seo/home-ar.html.bak-merge-$stamp"
cp -p "$W/blog/index.html" "/opt/seo/blog-index.html.bak-merge-$stamp"
install -d -m 755 -o www-data -g www-data /opt/seo/retired
cd /opt/seo && runuser -u www-data -- python3 -c "
import importlib.util as u, datetime as d, json
s = u.spec_from_file_location('p', '/opt/seo/publish.py'); m = u.module_from_spec(s); s.loader.exec_module(m)
t = d.date.today()
q = [m.normalized_article(a) for a in json.loads(m.QUEUE.read_text())]
m.compute_underlinked(q)
m.repair_static_site()
for f in ('index.html', 'en/index.html', 'about/index.html', 'en/about/index.html', 'blog/index.html'):
    if (m.ROOT/f).exists(): m._patch_file(m.ROOT/f, m.canonical_links)
m.refresh_index_cards(q); m.ensure_index_cards(q)
m.repair_published_articles(q, t)
for p in list(m.ROOT.glob('blog/*/index.html')) + list(m.ROOT.glob('en/blog/*/index.html')):
    m._patch_file(p, m.canonical_links)
m.write_feed(q); m.write_llms_txt(q); m.write_llms_full(q)
m.prune_noindex_from_sitemap(q)
print('refresh ok')
"

echo "== 5. verify"
for s in best-nurseries-jeddah-2026 best-nursery-guide-jeddah trusted-nursery-recommendation-jeddah best-quality-price-nursery-jeddah; do
  echo "$s: $(curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}' -H 'Host: montessori-ksa.com' https://127.0.0.1/blog/$s/ -k)"
done
echo "pillar: $(curl -s -o /dev/null -w '%{http_code}' -k -H 'Host: montessori-ksa.com' https://127.0.0.1/blog/best-montessori-nursery-jeddah/)"
echo "merged URLs left in sitemap: $(grep -cE 'best-nurseries-jeddah-2026|best-nursery-guide-jeddah|trusted-nursery-recommendation|best-quality-price-nursery|safe-educational-nursery' $W/sitemap.xml)"
echo "/wa/ in sitemap: $(grep -c '/wa/</loc>' $W/sitemap.xml)"
echo "pages retired: $(ls /opt/seo/retired | wc -l)"
rm -rf "$T"; echo DONE
