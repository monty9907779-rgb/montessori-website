#!/bin/bash
# ONE-TIME install (as root). After this, server changes ship from GitHub with no more pasting:
#   curl -fsSL https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main/ops/server/seo/install-server-apply.sh -o /tmp/i.sh && bash /tmp/i.sh
# Installs /opt/seo/server-apply-runner.sh + /etc/cron.d/seo-server-apply (daily 04:40 UTC, after auto-deploy at 04:30).
# The runner downloads ops/server/seo/server-apply.sh from main, runs the pristine scan on it,
# and executes it only if the scan passes. Output: /opt/seo/server-apply.log
set -eu
RAW=https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main
cat > /opt/seo/server-apply-runner.sh <<'RUN'
#!/bin/bash
set -u
RAW=https://raw.githubusercontent.com/monty9907779-rgb/montessori-website/main
SCAN=/opt/security-weekly/pristine_sync.py
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
echo "=== $(date -u +%FT%TZ) server-apply"
curl -fsSL --max-time 60 -o "$T/apply.sh" "$RAW/ops/server/seo/server-apply.sh?t=$(date +%s)" || { echo "download failed"; exit 1; }
bash -n "$T/apply.sh" || { echo "syntax error, not run"; exit 1; }
if [ -f "$SCAN" ]; then python3 "$SCAN" --scan "$T/apply.sh" --as /opt/seo/server-apply.sh || { echo "scan flagged it, not run"; exit 1; }; fi
bash "$T/apply.sh"
RUN
chmod 755 /opt/seo/server-apply-runner.sh
echo '40 4 * * * root /opt/seo/server-apply-runner.sh >> /opt/seo/server-apply.log 2>&1' > /etc/cron.d/seo-server-apply
chmod 644 /etc/cron.d/seo-server-apply
echo "installed; running once now"
/opt/seo/server-apply-runner.sh 2>&1 | tee -a /opt/seo/server-apply.log | tail -25
