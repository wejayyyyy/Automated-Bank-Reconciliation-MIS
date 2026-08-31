# Automated Bank Reconciliation MIS

This project produces reconciliation results from bank and ledger CSV files, then refreshes the Excel MIS dashboard from the same output. A matching Power BI dashboard is included for publishing to Power BI Service.

## Project layout

```text
data/input/       Source bank and ledger CSV files
data/output/      Generated reconciliation result used by both dashboards
src/              Reconciliation engine
scripts/          One-click refresh and Power BI Service refresh scripts
dashboards/excel/ Excel MIS dashboard
dashboards/powerbi/ Power BI dashboard
docs/             Setup and operating instructions
```

## First-time setup

1. Install Python 3.
2. From the project root, run `py -3 -m pip install -r requirements.txt`.
3. The Excel workbook is already configured to locate the project output folder automatically. `scripts\configure_excel_query.ps1` is included only as a repair script if the query is ever replaced.

## Refresh the Excel dashboard

Run:

```powershell
.\scripts\refresh_all.ps1
```

The script regenerates `data/output/reconciliation_results.csv`, refreshes the Excel query, recalculates the KPI formulas, and saves the workbook. Do not keep the workbook open while the script is running.

## Power BI

Open the PBIX from `dashboards/powerbi`. See `docs/POWERBI_SETUP.md` for the one-time local source setup and Power BI Service automation steps.

## GitHub

Commit the project folder, including the small demonstration CSV files and the generated sample output. Do not commit tokens, credentials, or Power BI local configuration files.
