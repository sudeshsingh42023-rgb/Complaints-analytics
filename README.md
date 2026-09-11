# Customer Complaints Root-Cause Analytics & Regulatory Reporting Pipeline

Built for: **Analyst-Data Analytics, American Express — Global Complaints & Privacy (GC&P)**

## What this is

An end-to-end analytics pipeline over a synthetic multi-channel customer
complaints dataset (50,000 records — call/email/chat/social, 7 international
markets, 6 product lines), modeled after the kind of complaints warehouse
table a GC&P Analytics, Insights & Reporting team would query. It covers:

1. **Root cause analysis** — Pareto/80-20 breakdown of which issue
   categories drive the bulk of complaint volume
2. **Systemic delay detection** — flags root causes with structurally
   longer resolution times (process/system issue, not agent variance)
3. **Cross-geography trend monitoring** — month-over-month complaint
   volume by market, to catch emerging problems early
4. **Regulatory escalation tracking** — escalation-to-regulator rate by
   market and severity
5. **SLA compliance by channel** — where resolution is falling behind target
6. **Automated regulatory reporting** — a scheduled-report-style script
   that produces a formatted compliance summary each period, instead of
   being rebuilt by hand every cycle

## Why this maps to the JD

| JD requirement | Where it's addressed |
|---|---|
| Strong SQL / BigQuery expertise | `sql/queries.sql` — CTEs, window functions (`LAG`, running totals), aggregations |
| Research into root cause of complaints | `analysis.py` — Pareto + systemic delay flagging |
| Insights packages for business units/markets | `reports/findings_summary.md` |
| Timely, accurate updates to regulators | `regulatory_report.py` |
| Multiple markets / cross-geography trends | Market-level breakdowns throughout |
| Data visualization | `charts/*.png` (5 charts) |

## Project structure

```
complaints-analytics/
├── generate_data.py         # synthetic complaints dataset generator
├── analysis.py               # runs SQL, produces charts + findings summary
├── regulatory_report.py      # automated compliance report generator
├── sql/
│   └── queries.sql           # 7 annotated SQL queries (BigQuery-portable)
├── data/
│   ├── complaints.csv
│   └── complaints.db         # SQLite stand-in for a BigQuery table
├── charts/                   # 5 generated PNG charts (the "dashboard")
└── reports/
    ├── findings_summary.md
    └── regulatory_report_<period>.md
```

## How to run

```bash
pip install pandas numpy matplotlib tabulate
python3 generate_data.py       # builds data/complaints.csv + complaints.db
python3 analysis.py            # runs sql/queries.sql logic, writes charts/
python3 regulatory_report.py   # writes reports/regulatory_report_<period>.md
```

## Porting to real BigQuery

This uses SQLite only so the project runs standalone with no cloud account.
To point it at BigQuery instead:
- Replace `sqlite3.connect(...)` with `google.cloud.bigquery.Client()`
- Swap SQLite-specific functions in `sql/queries.sql`
  (`strftime('%Y-%m', ...)` → `FORMAT_DATE('%Y-%m', ...)`)
- Point queries at your dataset: `` `project.dataset.complaints` ``

## Adapting for a resume bullet

Suggested phrasing once you've run this and reviewed the outputs:

> Built a SQL-based analytics pipeline over 50K+ multi-channel customer
> complaint records across 7 markets; applied Pareto and systemic-delay
> analysis to identify root causes driving 80% of complaint volume and
> automated a recurring regulatory compliance report, replacing manual
> reporting effort.

Feel free to swap in your actual numbers once you adapt the dataset size /
scope, or point it at a real public dataset (e.g. CFPB Consumer Complaint
Database) for an even more defensible "real data" story in interviews.
