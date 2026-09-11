"""
regulatory_report.py
----------------------
Simulates the "timely, accurate updates to regulators" reporting requirement
called out in the JD. Generates a formatted, point-in-time compliance report
that could be scheduled (cron/Airflow) to run weekly/monthly, rather than
built by hand each cycle.

Run: python3 regulatory_report.py
Output: reports/regulatory_report_<date>.md
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "data/complaints.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM complaints", conn)
    conn.close()

    df["complaint_date"] = pd.to_datetime(df["complaint_date"])
    latest_month = df["complaint_date"].max().to_period("M")
    period_df = df[df["complaint_date"].dt.to_period("M") == latest_month]

    total = len(period_df)
    escalated = period_df["escalated_to_regulator"].sum()
    high_sev = (period_df["severity"] == "High").sum()
    unresolved_high_sev_aging = period_df[
        (period_df["severity"] == "High")
        & (~period_df["resolved"])
        & (period_df["resolution_days"] > 14)
    ]

    by_market = (
        period_df.groupby("market")
        .agg(
            total_complaints=("complaint_id", "count"),
            escalated=("escalated_to_regulator", "sum"),
            avg_resolution_days=("resolution_days", "mean"),
        )
        .round(1)
        .sort_values("escalated", ascending=False)
    )

    report_date = datetime.now().strftime("%Y-%m-%d")

    lines = []
    lines.append(f"# Complaints Regulatory Compliance Report\n")
    lines.append(f"**Reporting period:** {latest_month}  \n**Generated:** {report_date}\n")
    lines.append("## Summary\n")
    lines.append(f"- Total complaints logged: **{total:,}**")
    lines.append(f"- Escalated to regulator: **{escalated:,}** ({100*escalated/total:.1f}%)")
    lines.append(f"- High-severity complaints: **{high_sev:,}**")
    lines.append(f"- High-severity, unresolved, aging >14 days: **{len(unresolved_high_sev_aging)}** "
                 f"(requires immediate attention)\n")

    lines.append("## By Market\n")
    lines.append(by_market.to_markdown())
    lines.append("")

    if len(unresolved_high_sev_aging):
        lines.append("## Cases Requiring Immediate Attention\n")
        cols = ["complaint_id", "market", "product_line", "root_cause", "resolution_days"]
        lines.append(unresolved_high_sev_aging[cols].sort_values(
            "resolution_days", ascending=False).head(20).to_markdown(index=False))

    out_path = f"reports/regulatory_report_{latest_month}.md"
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Regulatory report written to {out_path}")


if __name__ == "__main__":
    main()
