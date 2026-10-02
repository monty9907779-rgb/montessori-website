#!/bin/bash
# Re-sync the automatic staff deductions of one day, optionally registering
# that day as an official holiday first.
#
#   resync-deductions.sh 2026-09-23                 # re-sync only
#   resync-deductions.sh 2026-09-23 "اليوم الوطني"   # register holiday, then re-sync
#
# evaluate_day() returns nothing on a holiday (like Fri/Sat), and sync_day()
# removes automatic *draft* deductions that are no longer wanted — manual or
# confirmed entries are never touched. The daily cron only re-syncs today and
# yesterday, so a holiday registered late needs this once for its date.
# Runs the Odoo shell inside the "odoo" container; DB connection settings are
# read from /etc/odoo/odoo.conf or the container environment (HOST/USER/...).
set -euo pipefail
DAY="${1:-}"; NAME="${2:-}"
[[ "$DAY" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "usage: $0 YYYY-MM-DD [holiday name]" >&2; exit 2; }
CONTAINER="${ODOO_CONTAINER:-odoo}"
DB="${ODOO_DB:-odoo}"

docker exec -i "$CONTAINER" sh -c '
  C=/etc/odoo/odoo.conf
  g(){ grep -E "^$1\s*=" $C 2>/dev/null | head -1 | cut -d= -f2- | tr -d " "; }
  H=$(g db_host); H=${H:-${HOST:-db}}; P=$(g db_port); P=${P:-${PORT:-5432}}
  U=$(g db_user); U=${U:-${USER:-odoo}}; W=$(g db_password); W=${W:-${PASSWORD:-odoo}}
  echo "db: $U@$H:$P / '"$DB"'"
  exec odoo shell -c $C -d '"$DB"' --db_host="$H" --db_port="$P" --db_user="$U" --db_password="$W" --no-http
' <<PY
from datetime import date, datetime
import pytz
day = date.fromisoformat("$DAY")
name = """$NAME""".strip()
H = env['nursery.holiday'].sudo()
if name and not H.search_count([('date_from','<=',day),('date_to','>=',day)]):
    H.create({'name': name, 'date_from': day, 'date_to': day})
    print('holiday added:', day, name)
D = env['nursery.deduction'].sudo()
dom = [('date','=',day),('state','!=','cancelled')]
print('deductions on', day, 'before:', D.search_count(dom))
p = D.rule_params(); now_local = datetime.now(pytz.utc).astimezone(pytz.timezone('Asia/Riyadh'))
for emp in env['hr.employee'].sudo().search([('active','=',True),('user_id','!=',False)]):
    D.sync_day(emp, day, p, now_local)
print('deductions on', day, 'after :', D.search_count(dom))
env.cr.commit()
PY
