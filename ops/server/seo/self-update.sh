#!/bin/bash
# Pull the SEO/GEO automation from GitHub main and install it on the server.
# Runs daily from root's crontab, before the publisher. Every file is
# checked first (py_compile / JSON parse / bash -n), the previous copy is kept
# as .prev, and nothing is replaced when a download or check fails, so a bad
# push cannot break the daily publisher.
set -uo pipefail
RAW="https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main/ops/server"
LOG=/opt/seo/self-update.log
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

# remote path | local path | kind
FILES="seo/publish.py|/opt/seo/publish.py|py
seo/rewrites.json|/opt/seo/rewrites.json|json
seo/self-update.sh|/opt/seo/self-update.sh|sh"

changed=0
while IFS='|' read -r rel dst kind; do
  f="$TMP/$(basename "$dst")"
  if ! curl -fsSL --max-time 60 -o "$f" "$RAW/$rel?t=$(date +%s)"; then log "skip $rel: download failed"; continue; fi
  [ -s "$f" ] || { log "skip $rel: empty"; continue; }
  case "$kind" in
    py)   python3 -m py_compile "$f" 2>>"$LOG" || { log "skip $rel: compile failed"; continue; } ;;
    json) python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" 2>>"$LOG" || { log "skip $rel: bad json"; continue; } ;;
    sh)   bash -n "$f" 2>>"$LOG" || { log "skip $rel: syntax error"; continue; } ;;
  esac
  [ -d "$(dirname "$dst")" ] || { log "skip $rel: $(dirname "$dst") missing"; continue; }
  if [ -f "$dst" ] && cmp -s "$f" "$dst"; then continue; fi
  [ -f "$dst" ] && cp -p "$dst" "$dst.prev"
  install -m 644 "$f" "$dst"
  [ "$kind" = sh ] && chmod 755 "$dst"
  case "$dst" in /opt/seo/*|/opt/geo-watch/*) chown www-data:www-data "$dst" ;; esac
  log "updated $dst"; changed=$((changed+1))
done <<< "$FILES"
log "done, $changed file(s) updated"

# ── nursery addon (Odoo): the dashboard's Excel importer ─────────────────────
# ops/server/nursery/*.py are the source of /api/manager/excel/import. The
# addon directory is discovered once (cached) and nothing is touched when it
# cannot be found; a changed file keeps the owner/mode of the one it replaces
# and Odoo is restarted so the new parser is the one serving the dashboard.
ADDON_CACHE=/opt/seo/nursery-addon.path
addon=""
[ -s "$ADDON_CACHE" ] && addon="$(cat "$ADDON_CACHE")"
if [ -z "$addon" ] || [ ! -f "$addon/controllers/excel_import.py" ]; then
  addon="$(find /opt /usr/lib /usr/local /srv /home /root /var/lib /mnt -maxdepth 8 -type f \
             -path '*/nursery/controllers/excel_import.py' \
             -not -path '*/montessori-website/*' -not -path '*/.git/*' -not -path '*/legacy*' \
             2>/dev/null | head -1)"
  addon="${addon%/controllers/excel_import.py}"
  [ -n "$addon" ] && printf '%s\n' "$addon" > "$ADDON_CACHE"
fi
if [ -n "$addon" ] && [ -f "$addon/controllers/excel_import.py" ]; then
  nursery_changed=0
  ref="$addon/controllers/excel_import.py"
  while IFS='|' read -r rel dst; do
    f="$TMP/nursery-$(basename "$dst")"
    if ! curl -fsSL --max-time 60 -o "$f" "$RAW/$rel?t=$(date +%s)"; then log "skip $rel: download failed"; continue; fi
    [ -s "$f" ] || { log "skip $rel: empty"; continue; }
    python3 -m py_compile "$f" 2>>"$LOG" || { log "skip $rel: compile failed"; continue; }
    if [ -f "$dst" ] && cmp -s "$f" "$dst"; then continue; fi
    if [ -f "$dst" ]; then
      cp -p "$dst" "$dst.prev"
      cat "$f" > "$dst"
    else
      install -m 644 -o "$(stat -c %U "$ref")" -g "$(stat -c %G "$ref")" "$f" "$dst"
    fi
    rm -f "$(dirname "$dst")"/__pycache__/"$(basename "${dst%.py}")".*.pyc 2>/dev/null
    log "updated $dst"; nursery_changed=$((nursery_changed+1))
  done <<< "nursery/excel_import.py|$addon/controllers/excel_import.py
nursery/import_month.py|$addon/import_month.py"
  if [ "$nursery_changed" -gt 0 ]; then
    unit="$(systemctl list-units --type=service --all --no-legend 2>/dev/null | awk '{print $1}' | grep -iE '^odoo' | head -1)"
    if [ -n "$unit" ]; then
      if systemctl restart "$unit" 2>>"$LOG"; then log "restarted $unit for the nursery addon"; else log "restart $unit FAILED — restart Odoo by hand"; fi
    else
      log "odoo service not found — restart Odoo by hand so the new excel_import.py loads"
    fi
  fi
else
  log "nursery addon not found — excel_import.py not installed (set $ADDON_CACHE to the addon dir)"
fi
