# nursery — Odoo addon pieces that live in this repo

`excel_import.py` and `dashboard.py` are the server-side source of the
`/dashboard/` numbers. They are **not** deployed by `deploy.sh` (that ships
`public/` only).

## Deploy

`excel_import.py` and `import_month.py` ride the server's daily
`ops/server/seo/self-update.sh` (root crontab, runs before the SEO
publisher): it pulls them from GitHub `main`, compiles them, installs them
into the `nursery` addon (`<addon>/controllers/excel_import.py`,
`<addon>/import_month.py`; the addon dir is discovered once and cached in
`/opt/seo/nursery-addon.path`), keeps the previous copy as `.prev`, and
restarts the Odoo service. So: merge to `main`, and within a day the
dashboard imports with the new parser. `/opt/seo/self-update.log` records
what happened. By hand, the same thing is:

```bash
scp ops/server/nursery/excel_import.py root@187.127.79.242:<addon>/controllers/
scp ops/server/nursery/import_month.py root@187.127.79.242:<addon>/
ssh root@187.127.79.242 'systemctl restart odoo'
```

## Re-importing a finished month from the dashboard

`مزامنة Excel` → choose the month (e.g. سبتمبر 2026) → upload the workbook →
اعتماد. The roster (serials, classes, dates) is rebuilt as long as no later
month has a payment yet (`_roster_allowed`); after a successful import of a
month that already ended, the month is **closed automatically**
(`_close_finished_month`). From then on the site refuses every change to it.

## How the month gets its numbers

1. The owner uploads the accounting workbook (`مزامنة Excel`) or pulls the
   saved Google Sheet (`مزامنة لينك الشيت`).
2. `_parse_records` reads the month tab: the student table, and the
   **salary** (`Teacher Name | Date | Forecast Salary | Actual Salary | Notes`)
   and **expense** (`Serial | Expense Name | Expense Date | Value`) tables that
   sit side by side under it. Serial / Remaining cells that are formulas
   without a cached value are evaluated here, so an openpyxl-written workbook
   imports exactly like one saved from Excel.
3. `_excel_month_metrics` reproduces the sheet's summary row:
   - `collected` = Σ Last Payment Amount; `randa_cash` / `bank_transfer` by method
   - `expenses` = −Σ Value (the sheet's positive "Expenses" cell)
   - `on_hand_randa` = Nesrin opening line + Randa cash + negative expense lines
   - `salaries` = Σ Actual Salary; `expected_salaries` = Σ Forecast Salary
   - `other_expenses` = outflows minus the `مرتبات` hand-over line, so the
     dashboard's `income − salaries − other` equals the sheet's `Net`
4. `_replace_month_from_excel` rebuilds that month (fees, payments, entries,
   salary cards) and stores the metrics in `nursery.ext_fin`, which
   `dashboard.py` reads for the KPI row and the "مطابقة ملخص Excel" card.

## Closed months

- `/api/manager/month/close` (accounts page) sets `nursery.month.state = closed`.
- Every site path (`excel/import` preview, commit, replace, and the sheet
  sync) refuses a closed month — the import is a no-op with
  `الشهر مقفول — لا يمكن التعديل.`
- The only way to change a closed month is `import_month.py` run through
  `odoo shell` on the server (see its docstring). It reopens the month for
  the duration of the import and closes it again.

## Tests

```bash
python3 ops/server/nursery/test_excel_import.py
```

The test builds a synthetic workbook with the real layout (formula serials,
a mid-month leaver without a serial, side-by-side salary/expense tables) and
checks the parsed records and the metrics against hand-computed values.

## Staff deductions and holidays

`models/nursery.py` (shipped from `ops/server/nursery/models_nursery.py`) skips
Friday, Saturday **and every day inside `nursery.holiday`** when generating
automatic deductions. Register official holidays in that table before the day
if you can. If a holiday is registered late, re-sync its date once — the
daily cron only re-syncs today and yesterday:

```
/opt/seo/resync-deductions.sh 2026-09-23 "اليوم الوطني"   # registers + re-syncs
/opt/seo/resync-deductions.sh 2026-09-23                 # re-sync only
```

Only automatic *draft* deductions are removed; manual or confirmed ones stay.

To see exactly what the AI answers for a month's staff deductions (the
per-employee table) without logging in:

```
/opt/seo/show-deductions.sh 2026-09   # defaults to the current month
```

## Deploy channel (how changes reach the server)

`ops/server/seo/self-update.sh` runs daily from root's cron on the VPS and
pulls from `main`: the SEO publisher files, the nursery addon files
(`excel_import.py`, `roles.py`, `models_nursery.py` → `models/nursery.py`,
`import_month.py`, `import_unlock.json` — Odoo is restarted when any changed),
the AI page files (`public/ai/index.html`, `public/assets/ai.js`, `ai.css`)
and the maintenance scripts (`resync-deductions.sh`, `show-deductions.sh`).
To deploy right now: `bash /opt/seo/self-update.sh`. When the script itself
changed it re-runs once automatically, so a single run is always enough.

The accounts page (`public/accounts/index.html`) is **not** on that list: it
has inline `<script>` blocks, and the CSP hash for each is regenerated only by
the static release (`bash deploy.sh` from a workstation). When a single page
had to be copied onto the server by hand, regenerate the hashes afterwards,
on the server, from a clone of `main`:

```bash
rm -rf /tmp/mw && git clone -q --depth 1 https://github.com/monty9907779-rgb/montessori-website /tmp/mw \
  && python3 /tmp/mw/scripts/deploy-static.py --refresh-csp
```

A full release can also be built on the server without Node
(`python3 scripts/package-static.py /tmp/rel && python3 /tmp/rel/deploy-static.py /tmp/rel`;
`package-static.py` is a byte-identical twin of `package-static.mjs`), but
only once `public/` on `main` matches what is live: on 2026-10-02 the live
`assets/app.js` (release `mk-shell-46e8d3a05147`, a commit that is not on
GitHub) carried a newer notification bell than `main`, so a full release from
`main` would have regressed it.

Rules learned the hard way:
- Never edit an inline `<style>` or `style=` in a served page: the site's
  CSP allows inline styles by sha256 hash only (`scripts/deploy-static.py`
  generates them). Put page CSS in an external file under `/assets/`.
- The same holds for inline `<script>` blocks (2026-10-02: accounts/index.html
  copied by hand → CSP blocked its script → blank page). Pages with inline
  scripts ship only through the static release, never through self-update.
- Browser assets are cached by Cloudflare per URL: bump `?v=N` on
  `ai.js` / `ai.css` in `index.html` whenever they change.
- The controllers/models on the server had drifted from the `work/`
  snapshots before; edit the files in `ops/server/nursery/` (the deployed
  source of truth) and let self-update ship them.
