#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
node scripts/verify-admin.mjs
STAGE="$(mktemp -d)"
node scripts/package-static.mjs "$STAGE"
COPYFILE_DISABLE=1 tar -czf "$STAGE/release.tgz" -C "$STAGE" public release.json deploy-static.py montessori-ksa.conf
REMOTE="$(ssh -o BatchMode=yes root@187.127.79.242 mktemp -d /tmp/montessori-release.XXXXXXXX)"
scp "$STAGE/release.tgz" "root@187.127.79.242:$REMOTE/release.tgz"
ssh -o BatchMode=yes root@187.127.79.242 "tar -xzf '$REMOTE/release.tgz' -C '$REMOTE' && python3 '$REMOTE/deploy-static.py' '$REMOTE'"
