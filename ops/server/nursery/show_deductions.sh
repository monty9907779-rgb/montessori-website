#!/bin/bash
# Print exactly what the AI page answers to «خصومات الموظفين في <month>» —
# the deterministic per-employee table — without needing a manager token.
# Read-only. Useful to check a month after holidays were registered/re-synced.
#
#   show-deductions.sh            # current month
#   show-deductions.sh 2026-09    # September 2026
set -euo pipefail
YM="${1:-$(date +%Y-%m)}"
[[ "$YM" =~ ^[0-9]{4}-[0-9]{2}$ ]] || { echo "usage: $0 [YYYY-MM]" >&2; exit 2; }
CONTAINER="${ODOO_CONTAINER:-odoo}"
DB="${ODOO_DB:-odoo}"

docker exec -i "$CONTAINER" sh -c '
  C=/etc/odoo/odoo.conf
  g(){ grep -E "^$1\s*=" $C 2>/dev/null | head -1 | cut -d= -f2- | tr -d " "; }
  H=$(g db_host); H=${H:-${HOST:-db}}; P=$(g db_port); P=${P:-${PORT:-5432}}
  U=$(g db_user); U=${U:-${USER:-odoo}}; W=$(g db_password); W=${W:-${PASSWORD:-odoo}}
  exec odoo shell -c $C -d '"$DB"' --db_host="$H" --db_port="$P" --db_user="$U" --db_password="$W" --no-http
' 2>/dev/null <<PY
from calendar import monthrange
from odoo.addons.nursery.controllers.roles import NurserySSO
ym = "$YM"; y, m = int(ym[:4]), int(ym[5:7])
last = '%s-%02d' % (ym, monthrange(y, m)[1])
AR = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
D = env['nursery.deduction'].sudo()
LBL = getattr(D, 'DTYPE_LABELS', None) or {}
deds = D.search([('state','!=','cancelled'),('date','>=',ym + '-01'),('date','<=',last)], order='date')
rows = [{'employee': d.employee_id.name if d.employee_id else '',
         'type': LBL.get(d.dtype, d.dtype) if LBL else d.dtype,
         'amount': d.amount, 'state': d.state} for d in deds]
print("\n===== رد الذكاء على: خصومات الموظفين في %s =====\n" % AR[m-1])
print(NurserySSO._deductions_table(rows, '%s %d' % (AR[m-1], y)))
print("\nأيام عليها خصومات:", ', '.join(sorted({str(d.date) for d in deds})) or 'لا شيء')
PY
