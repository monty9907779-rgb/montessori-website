#!/bin/bash
# Mirror the article queue from the server into a dedicated clone, once a day.
#
# queue.json is the source of truth for every published article; the HTML is
# regenerated from it daily. The server holds the only live copy, so this keeps
# a diffable history beside the code. (Disaster recovery is already covered:
# /opt/seo/queue.json rides along in opt-config.tar.gz to B2 every night.)
#
# Runs from a LaunchAgent, so it must never prompt and never leave the repo
# dirty. Every failure exits non-zero with a reason on stderr; launchd records
# it in the log below.
#
# REPO is a plain `git clone` of this same repo, kept ONLY for this job, at
# ~/.local/share — deliberately NOT the working copy under ~/Documents (that
# tree is iCloud "Desktop & Documents" synced, and a launchd-spawned bash gets
# "Operation not permitted" writing into it or even chdir'ing there, no matter
# what Full Disk Access is granted — this bit the first version of this script
# on its very first run: 2026-09-14). Since nothing else ever commits into
# this clone, every run resets it to origin/main first so it can never drift
# or get stuck on a bad local state.
set -uo pipefail

REPO="$HOME/.local/share/montessori-queue-sync"
DEST="$REPO/ops/server/seo/queue.json"
SERVER="root@187.127.79.242"
TMP="$(mktemp -t queue-sync)"
LOCK="$HOME/.local/share/montessori-queue-sync.lock"
trap 'rm -f "$TMP"' EXIT

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "FAIL: $*" >&2; exit 1; }

# mkdir is atomic on every filesystem here; macOS has no flock(1). A stray
# lock older than 30 minutes means a previous run crashed without cleaning up.
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
    log "قفل قديم (أكتر من ٣٠ دقيقة) — بيتشال"
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" || die "تعذّر أخذ القفل حتى بعد تنظيفه"
  else
    log "تشغيلة تانية شغّالة بالفعل — خروج بهدوء"
    exit 0
  fi
fi
trap 'rm -f "$TMP"; rmdir "$LOCK" 2>/dev/null' EXIT

[ -d "$REPO/.git" ] || die "نسخة المزامنة مش موجودة — git clone https://github.com/monty9907779-rgb/montessori-website.git $REPO"
git -C "$REPO" fetch --quiet origin main || die "git fetch فشل"
git -C "$REPO" reset --quiet --hard origin/main || die "git reset فشل"

# One SSH connection: the server's UFW rate-limits 22/tcp at six new
# connections per thirty seconds, and each retry refreshes the ban window.
ssh -o ConnectTimeout=25 -o BatchMode=yes "$SERVER" "cat /opt/seo/queue.json" > "$TMP" \
  || die "SSH فشل — الملف ما اتسحبش"
[ -s "$TMP" ] || die "الملف المسحوب فاضي"

# Validate and privacy-scan before anything touches the working tree.
# The repo is PUBLIC on GitHub: on 2026-09-13 a staff member's personal mobile
# was live in 24 articles as a public contact number. This gate exists so that
# cannot reach the repo, and it fails closed.
python3 - "$TMP" "$DEST" <<'PY' || exit 1
import json, re, sys, pathlib

new_path, dest_path = sys.argv[1], sys.argv[2]
raw = pathlib.Path(new_path).read_text(encoding='utf-8')

try:
    items = json.loads(raw)
except Exception as exc:
    sys.exit('FAIL: JSON غير صالح — %s' % exc)
if not isinstance(items, list):
    sys.exit('FAIL: الجذر ليس list')
if len(items) < 100:
    sys.exit('FAIL: عدد المقالات %d أقل من الحد الأدنى 100' % len(items))

dest = pathlib.Path(dest_path)
if dest.exists():
    try:
        old = len(json.loads(dest.read_text(encoding='utf-8')))
    except Exception:
        old = None
    if old is not None and len(items) < old - 5:
        sys.exit('FAIL: انكماش مريب — %d مقال مقابل %d' % (len(items), old))

OFFICIAL = '0541558173'
phones = {p for p in re.findall(r'05\d{8}', raw) if p != OFFICIAL}
if phones:
    sys.exit('FAIL: رقم غير الرسمي في الطابور: %s' % ', '.join(sorted(phones)))

leaks = set(re.findall(r'ghp_\w+|github_pat_\w+|Bearer \w+', raw))
leaks |= {m.group(0) for m in re.finditer(r'(?:password|api[_-]?key|secret)\s*[=:]\s*\S+', raw, re.I)}
if leaks:
    sys.exit('FAIL: سر محتمل في الطابور: %s' % ', '.join(sorted(leaks))[:200])

print('OK %d مقال (%d منشور)' % (len(items), sum(1 for a in items if a.get('published'))))
PY

if [ -f "$DEST" ] && cmp -s "$TMP" "$DEST"; then
  log "الطابور زي ما هو — مفيش تغيير"
  exit 0
fi

cp "$TMP" "$DEST" || die "cp فشل — الوجهة $DEST"
COUNT=$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(len(d),sum(1 for a in d if a.get("published")))' "$DEST") \
  || die "قراءة الملف المنسوخ فشلت"
set -- $COUNT

git -C "$REPO" add -- "$DEST" || die "git add فشل"
git -C "$REPO" diff --cached --quiet -- "$DEST" && { log "مفيش فرق بعد الإضافة"; exit 0; }
git -C "$REPO" commit -q -m "chore: sync article queue ($1 مقال، $2 منشور)" -- "$DEST" \
  || die "git commit فشل"
git -C "$REPO" push -q origin HEAD:main || die "الدفع فشل — الكوميت محلي في $REPO، محتاج تدخّل"
log "اتدفع: $1 مقال ($2 منشور)"
