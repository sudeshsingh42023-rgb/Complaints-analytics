"""
generate_data.py
-----------------
Generates a synthetic multi-channel customer complaints dataset that mirrors
the structure a Global Complaints & Privacy analytics team would work with
(complaint date, market/geography, channel, product line, root-cause
category, resolution time, escalation/regulatory flags).

This stands in for a real complaints data warehouse table you'd normally
pull from BigQuery. Swap this script out for a BigQuery extract and every
downstream script (analysis.py, regulatory_report.py) keeps working as long
as the output schema matches.
"""

import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

np.random.seed(42)

N_COMPLAINTS = 50000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2026, 9, 1)

MARKETS = {
    "US": 0.35, "UK": 0.15, "IN": 0.15, "AU": 0.10,
    "CA": 0.10, "SG": 0.08, "MX": 0.07,
}
CHANNELS = {"Call": 0.45, "Email": 0.20, "Chat": 0.25, "Social": 0.10}
PRODUCT_LINES = ["Card Services", "Merchant Services", "Travel & Lifestyle",
                  "Rewards & Membership", "Digital/App", "Billing & Statements"]

# Root cause categories, deliberately skewed so a Pareto pattern emerges
ROOT_CAUSES = {
    "Billing/charge discrepancy": 0.28,
    "Delayed dispute resolution": 0.18,
    "App/digital platform bug": 0.14,
    "Agent miscommunication": 0.12,
    "Fraud/unauthorized charge handling": 0.10,
    "Rewards/points not credited": 0.08,
    "Privacy/data handling concern": 0.06,
    "Other": 0.04,
}

SEVERITY = {"Low": 0.5, "Medium": 0.35, "High": 0.15}


def weighted_choice(options, n):
    keys = list(options.keys())
    probs = list(options.values())
    return np.random.choice(keys, size=n, p=probs)


def random_dates(start, end, n):
    delta = (end - start).days
    offsets = np.random.randint(0, delta, size=n)
    return [start + timedelta(days=int(o)) for o in offsets]


def main():
    n = N_COMPLAINTS
    df = pd.DataFrame({
        "complaint_id": [f"C{100000+i}" for i in range(n)],
        "complaint_date": random_dates(START_DATE, END_DATE, n),
        "market": weighted_choice(MARKETS, n),
        "channel": weighted_choice(CHANNELS, n),
        "product_line": np.random.choice(PRODUCT_LINES, size=n),
        "root_cause": weighted_choice(ROOT_CAUSES, n),
        "severity": weighted_choice(SEVERITY, n),
    })

    # Resolution time (days) — base distribution + systemic slow spots
    base_days = np.random.gamma(shape=2.0, scale=1.6, size=n)

    # Certain root causes are structurally slower to resolve (systemic issue,
    # not agent performance) -- this is the "signal" root-cause analysis
    # is meant to surface.
    slow_causes = {"Delayed dispute resolution", "App/digital platform bug",
                   "Fraud/unauthorized charge handling"}
    slow_mask = df["root_cause"].isin(slow_causes)
    base_days[slow_mask.values] *= np.random.uniform(2.2, 3.5, slow_mask.sum())

    # A couple of markets have SLA strain (ops capacity), independent of root cause
    strained_markets = {"IN", "MX"}
    strain_mask = df["market"].isin(strained_markets)
    base_days[strain_mask.values] *= np.random.uniform(1.2, 1.6, strain_mask.sum())

    df["resolution_days"] = np.round(base_days, 1)

    # Outcome
    resolved_prob = np.where(df["resolution_days"] > 15, 0.75, 0.95)
    df["resolved"] = np.random.binomial(1, resolved_prob).astype(bool)

    # Escalation to regulator (FOS/CFPB-style) — more likely for high severity,
    # slow resolution, and privacy-related complaints
    escalate_score = (
        (df["severity"] == "High").astype(int) * 0.25
        + (df["resolution_days"] > 20).astype(int) * 0.20
        + (df["root_cause"] == "Privacy/data handling concern").astype(int) * 0.30
        + 0.03
    )
    df["escalated_to_regulator"] = np.random.binomial(1, escalate_score.clip(0, 0.9)).astype(bool)

    # Repeat complainant flag (same customer complaining again within 90 days)
    # Simulate at the row level for simplicity/demo purposes
    df["repeat_complaint"] = np.random.binomial(1, 0.12, size=n).astype(bool)

    df = df.sort_values("complaint_date").reset_index(drop=True)

    df.to_csv("data/complaints.csv", index=False)

    # Load into SQLite to stand in for a BigQuery table -- the queries.sql
    # file is written in standard SQL and only needs light dialect changes
    # (e.g. DATE_TRUNC, EXTRACT) to run natively on BigQuery.
    conn = sqlite3.connect("data/complaints.db")
    df.to_sql("complaints", conn, if_exists="replace", index=False)
    conn.close()

    print(f"Generated {len(df):,} complaint records")
    print(f"  -> data/complaints.csv")
    print(f"  -> data/complaints.db (table: complaints)")


if __name__ == "__main__":
    main()
