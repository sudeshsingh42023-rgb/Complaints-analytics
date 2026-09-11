"""
analysis.py
------------
Runs the queries from sql/queries.sql against the complaints database and
renders the results as the charts a GC&P insights package / dashboard would
contain:
  1. Pareto chart of root causes (which issues drive most volume)
  2. Resolution time by root cause vs. overall average (systemic delay flag)
  3. Monthly complaint volume trend by market
  4. Regulatory escalation rate heatmap-style bar by market
  5. SLA compliance by channel

Run: python3 analysis.py
Outputs land in charts/ and a combined findings summary in reports/.
"""

import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

DB_PATH = "data/complaints.db"
CHARTS_DIR = "charts"
REPORTS_DIR = "reports"

plt.rcParams["figure.dpi"] = 130
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def q(conn, sql):
    return pd.read_sql_query(sql, conn)


def chart_pareto(conn):
    df = q(conn, """
        WITH cause_counts AS (
            SELECT root_cause, COUNT(*) AS complaint_count
            FROM complaints GROUP BY root_cause
        ),
        ranked AS (
            SELECT root_cause, complaint_count,
                   SUM(complaint_count) OVER (ORDER BY complaint_count DESC) AS running_total,
                   SUM(complaint_count) OVER () AS grand_total
            FROM cause_counts
        )
        SELECT root_cause, complaint_count,
               100.0*complaint_count/grand_total AS pct_of_total,
               100.0*running_total/grand_total AS cumulative_pct
        FROM ranked ORDER BY complaint_count DESC
    """)

    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    bars = ax1.bar(df["root_cause"], df["complaint_count"], color="#5B8DEF")
    ax1.set_ylabel("Complaint count")
    ax1.set_xticklabels(df["root_cause"], rotation=35, ha="right")
    ax1.set_title("Root Cause Pareto: Where Complaint Volume Concentrates")

    ax2 = ax1.twinx()
    ax2.plot(df["root_cause"], df["cumulative_pct"], color="#E4572E", marker="o")
    ax2.set_ylabel("Cumulative %")
    ax2.axhline(80, color="grey", linestyle="--", linewidth=1)
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter())

    fig.tight_layout()
    fig.savefig(f"{CHARTS_DIR}/01_pareto_root_causes.png")
    plt.close(fig)
    return df


def chart_resolution_delay(conn):
    df = q(conn, """
        WITH by_cause AS (
            SELECT root_cause, AVG(resolution_days) AS avg_resolution_days, COUNT(*) AS n
            FROM complaints GROUP BY root_cause
        ),
        overall AS (SELECT AVG(resolution_days) AS overall_avg FROM complaints)
        SELECT b.root_cause, b.avg_resolution_days, o.overall_avg
        FROM by_cause b CROSS JOIN overall o
        ORDER BY b.avg_resolution_days DESC
    """)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#E4572E" if v > 1.5 * df["overall_avg"].iloc[0] else "#5B8DEF"
              for v in df["avg_resolution_days"]]
    ax.barh(df["root_cause"], df["avg_resolution_days"], color=colors)
    ax.axvline(df["overall_avg"].iloc[0], color="black", linestyle="--", linewidth=1,
               label=f"Overall avg ({df['overall_avg'].iloc[0]:.1f}d)")
    ax.set_xlabel("Avg resolution time (days)")
    ax.set_title("Resolution Time by Root Cause — Red = Systemic Delay (>1.5x avg)")
    ax.legend()
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(f"{CHARTS_DIR}/02_resolution_delay_by_cause.png")
    plt.close(fig)
    return df


def chart_monthly_trend(conn):
    df = q(conn, """
        SELECT market, strftime('%Y-%m', complaint_date) AS month, COUNT(*) AS complaint_count
        FROM complaints GROUP BY market, month ORDER BY market, month
    """)
    pivot = df.pivot(index="month", columns="market", values="complaint_count").fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    pivot.plot(ax=ax, marker=".", linewidth=1.3)
    ax.set_title("Monthly Complaint Volume by Market")
    ax.set_ylabel("Complaints")
    ax.set_xlabel("Month")
    ax.legend(title="Market", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{CHARTS_DIR}/03_monthly_trend_by_market.png")
    plt.close(fig)
    return df


def chart_escalation_rate(conn):
    df = q(conn, """
        SELECT market,
               COUNT(*) AS total_complaints,
               SUM(CASE WHEN escalated_to_regulator THEN 1 ELSE 0 END) AS escalated_count,
               100.0*SUM(CASE WHEN escalated_to_regulator THEN 1 ELSE 0 END)/COUNT(*) AS escalation_rate_pct
        FROM complaints GROUP BY market ORDER BY escalation_rate_pct DESC
    """)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(df["market"], df["escalation_rate_pct"], color="#8E44AD")
    ax.set_ylabel("Escalation-to-regulator rate (%)")
    ax.set_title("Regulatory Escalation Rate by Market")
    for b, v in zip(bars, df["escalation_rate_pct"]):
        ax.text(b.get_x() + b.get_width()/2, v + 0.1, f"{v:.1f}%", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{CHARTS_DIR}/04_escalation_rate_by_market.png")
    plt.close(fig)
    return df


def chart_sla_by_channel(conn):
    df = q(conn, """
        SELECT channel,
               COUNT(*) AS total_complaints,
               100.0*SUM(CASE WHEN resolution_days <= 10 THEN 1 ELSE 0 END)/COUNT(*) AS sla_compliance_pct
        FROM complaints GROUP BY channel ORDER BY sla_compliance_pct ASC
    """)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    colors = ["#E4572E" if v < 70 else "#2ECC71" for v in df["sla_compliance_pct"]]
    bars = ax.barh(df["channel"], df["sla_compliance_pct"], color=colors)
    ax.axvline(80, color="black", linestyle="--", linewidth=1, label="80% SLA target")
    ax.set_xlabel("SLA compliance (% resolved <= 10 days)")
    ax.set_title("SLA Compliance by Channel")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{CHARTS_DIR}/05_sla_compliance_by_channel.png")
    plt.close(fig)
    return df


def write_findings_summary(pareto, delay, escalation, sla):
    top_cause = pareto.iloc[0]
    top_80_causes = pareto[pareto["cumulative_pct"] <= 80]
    systemic = delay[delay["avg_resolution_days"] > 1.5 * delay["overall_avg"].iloc[0]]
    worst_market = escalation.iloc[0]
    worst_channel = sla.iloc[0]

    lines = [
        "# Complaints Insights Summary\n",
        f"_Auto-generated from {DB_PATH} — {len(pareto)} root-cause categories, "
        f"analysis window per generate_data.py_\n",
        "## Key Findings\n",
        f"1. **Root cause concentration:** '{top_cause['root_cause']}' alone accounts for "
        f"{top_cause['pct_of_total']:.1f}% of all complaints. The top "
        f"{len(top_80_causes)} categories together drive ~80% of volume — "
        f"prioritizing fixes here has outsized impact.\n",
        f"2. **Systemic delay flags:** {', '.join(systemic['root_cause'].tolist()) if len(systemic) else 'None'} "
        f"show resolution times over 1.5x the overall average, indicating a process/system issue "
        f"rather than one-off agent variance.\n",
        f"3. **Regulatory exposure:** {worst_market['market']} has the highest escalation-to-regulator "
        f"rate at {worst_market['escalation_rate_pct']:.1f}% — a candidate for a targeted intervention "
        f"before it shows up in the next regulatory review.\n",
        f"4. **Channel SLA gap:** {worst_channel['channel']} has the weakest SLA compliance at "
        f"{worst_channel['sla_compliance_pct']:.1f}% of cases resolved within 10 days, "
        f"against an 80% target.\n",
        "## Recommended Actions\n",
        "- Route root-cause categories above the 80% Pareto line to a formal engineering/process review\n",
        "- Set up automated weekly alerting when a market's escalation rate crosses a defined threshold\n",
        "- Investigate channel-specific bottlenecks (staffing, tooling) for the lowest-SLA channel\n",
        "- Track repeat-complaint rate by product line month-over-month to confirm fixes are actually working\n",
    ]
    with open(f"{REPORTS_DIR}/findings_summary.md", "w") as f:
        f.write("\n".join(lines))


def main():
    conn = sqlite3.connect(DB_PATH)
    pareto = chart_pareto(conn)
    delay = chart_resolution_delay(conn)
    chart_monthly_trend(conn)
    escalation = chart_escalation_rate(conn)
    sla = chart_sla_by_channel(conn)
    write_findings_summary(pareto, delay, escalation, sla)
    conn.close()
    print("Charts written to charts/")
    print("Findings summary written to reports/findings_summary.md")


if __name__ == "__main__":
    main()
