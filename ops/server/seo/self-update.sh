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
