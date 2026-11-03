#!/bin/bash
# One-off install of the 2026-11-03 GEO changes (PRs #105, #106) on the server.
# The server self-update.sh is frozen and pinned (الترسانة), so the new public
# files and the nginx charset are not shipped by the daily job. Run as root:
#   curl -fsSL https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main/ops/server/seo/geo-apply-1103.sh -o /tmp/geo.sh && bash /tmp/geo.sh
# Every file passes pristine_sync.py --scan first; backups go to /opt/seo/*.bak-geo-*;
# nginx is reloaded only if nginx -t passes; no article is published, no email sent.
set -u
RAW=https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main
W=/var/www/montessori-ksa
T=$(mktemp -d)
SCAN=/opt/security-weekly/pristine_sync.py
stamp=$(date +%Y%m%d-%H%M%S)
fetch() { curl -fsSL --max-time 60 -o "$2" "$RAW/$1?t=$(date +%s)"; }

echo "== 1. publish.py from main (security scan first)"
if fetch ops/server/seo/publish.py "$T/publish.py" && python3 -m py_compile "$T/publish.py" \
   && grep -q home_geo_extras "$T/publish.py" && python3 "$SCAN" --scan "$T/publish.py" --as /opt/seo/publish.py; then
  cp -p /opt/seo/publish.py "/opt/seo/publish.py.bak-geo-$stamp"
  cat "$T/publish.py" > /opt/seo/publish.py
  cp -p /opt/seo/publish.py /opt/montessori/baseline/pristine/publish.py && echo "baseline refreshed"
  echo "publish.py installed"
else
  echo "publish.py NOT installed (download/compile/scan failed)"; exit 1
fi

echo "== 2. new public files (scan first)"
for rel in about/index.html en/about/index.html .well-known/ai.txt; do
  f="$T/$(echo "$rel" | tr '/' '_')"
  fetch "public/$rel" "$f" || { echo "skip $rel: download"; continue; }
  if python3 "$SCAN" --scan "$f" --as "$W/$rel"; then
    install -d -m 755 -o www-data -g www-data "$(dirname "$W/$rel")"
    install -m 644 -o www-data -g www-data "$f" "$W/$rel" && echo "installed $rel"
  else
    echo "skip $rel: scan flagged it"
  fi
done

echo "== 3. nginx charset"
C=/etc/nginx/conf.d/mk-charset.conf
if grep -rqsE '^\s*charset\s' /etc/nginx/nginx.conf /etc/nginx/conf.d/; then
  echo "charset already set somewhere"
else
  printf '# GEO 2026-11-03: Content-Type charset for non-browser fetchers\ncharset utf-8;\n' > "$C"
  if nginx -t 2>&1; then systemctl reload nginx && echo "nginx reloaded"; else rm -f "$C"; echo "nginx -t failed, removed"; fi
fi

echo "== 4. homepage GEO patch (as www-data, no article published)"
cp -p "$W/index.html" "/opt/seo/home-ar.html.bak-geo-$stamp"; cp -p "$W/en/index.html" "/opt/seo/home-en.html.bak-geo-$stamp"; cp -p "$W/sitemap.xml" "/opt/seo/sitemap.xml.bak-geo-$stamp"
cd /opt/seo && runuser -u www-data -- python3 -c "
import importlib.util as u, datetime as d
s = u.spec_from_file_location('p', '/opt/seo/publish.py'); m = u.module_from_spec(s); s.loader.exec_module(m)
t = d.date.today(); b = [(m.ROOT/f).read_text(encoding='utf-8') for f in ('index.html', 'en/index.html')]
for f, e in (('index.html', False), ('en/index.html', True)):
    print(f, m._patch_file(m.ROOT/f, lambda x, e=e: m.home_geo_extras(x, e)))
m.ensure_about_in_sitemap(t); m._bump_home_lastmod(b, t); print('patch ok')
"

echo "== 5. verify"
curl -sI -H 'Host: montessori-ksa.com' http://127.0.0.1/ | grep -i content-type
for k in k-foot__upd 'id="summary"' cid=12601466599204157435 'href="/about/"'; do echo "$k: $(grep -c -- "$k" $W/index.html) / en $(grep -c -- "$k" $W/en/index.html)"; done
grep -c '/about/</loc>' $W/sitemap.xml
rm -rf "$T"; echo DONE
