# nursery — Odoo addon pieces that live in this repo

`excel_import.py` and `dashboard.py` are the server-side source of the
`/dashboard/` numbers. They are **not** deployed by `deploy.sh` (that ships
`public/` only). Copy them into the `nursery` addon on `187.127.79.242`,
restart Odoo, then re-import the month.

```bash
# from a checkout of main
scp ops/server/nursery/excel_import.py ops/server/nursery/import_month.py \
    root@187.127.79.242:/opt/odoo/addons/nursery/        # adjust to the real addon path
ssh root@187.127.79.242 'systemctl restart odoo'
```

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
