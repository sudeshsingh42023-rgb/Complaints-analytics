-- ============================================================================
-- queries.sql
-- Complaints Root-Cause Analytics & Regulatory Reporting — SQL query bank
--
-- Written in standard SQL against the `complaints` table. These run as-is
-- against the SQLite demo DB (data/complaints.db). To port to BigQuery:
--   - DATE(...) / strftime(...) -> DATE_TRUNC(...) / FORMAT_DATE(...)
--   - Table ref: complaints -> `project.dataset.complaints`
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. PARETO ANALYSIS: which root causes drive the bulk of complaint volume?
--    (the 80/20 cut that should drive engineering/process prioritization)
-- ----------------------------------------------------------------------------
WITH cause_counts AS (
    SELECT
        root_cause,
        COUNT(*) AS complaint_count
    FROM complaints
    GROUP BY root_cause
),
ranked AS (
    SELECT
        root_cause,
        complaint_count,
        SUM(complaint_count) OVER (ORDER BY complaint_count DESC) AS running_total,
        SUM(complaint_count) OVER () AS grand_total
    FROM cause_counts
)
SELECT
    root_cause,
    complaint_count,
    ROUND(100.0 * complaint_count / grand_total, 1) AS pct_of_total,
    ROUND(100.0 * running_total / grand_total, 1) AS cumulative_pct
FROM ranked
ORDER BY complaint_count DESC;


-- ----------------------------------------------------------------------------
-- 2. RESOLUTION TIME OUTLIERS BY ROOT CAUSE (systemic vs. one-off issues)
--    Uses window functions to compare each cause's median against the
--    overall median, flagging structurally slow categories.
-- ----------------------------------------------------------------------------
WITH by_cause AS (
    SELECT
        root_cause,
        AVG(resolution_days) AS avg_resolution_days,
        COUNT(*) AS n
    FROM complaints
    GROUP BY root_cause
),
overall AS (
    SELECT AVG(resolution_days) AS overall_avg FROM complaints
)
SELECT
    b.root_cause,
    b.n AS complaint_count,
    ROUND(b.avg_resolution_days, 1) AS avg_resolution_days,
    ROUND(o.overall_avg, 1) AS overall_avg_resolution_days,
    ROUND(b.avg_resolution_days - o.overall_avg, 1) AS delta_vs_overall,
    CASE WHEN b.avg_resolution_days > 1.5 * o.overall_avg
         THEN 'SYSTEMIC DELAY - investigate'
         ELSE 'within normal range' END AS flag
FROM by_cause b
CROSS JOIN overall o
ORDER BY delta_vs_overall DESC;


-- ----------------------------------------------------------------------------
-- 3. MONTHLY TREND BY MARKET (month-over-month % change using LAG())
--    Surfaces markets with rising complaint volume before they become a
--    widespread problem -- the kind of early-warning view a GC&P team lead
--    would want in a recurring report.
-- ----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        market,
        strftime('%Y-%m', complaint_date) AS month,
        COUNT(*) AS complaint_count
    FROM complaints
    GROUP BY market, month
)
SELECT
    market,
    month,
    complaint_count,
    LAG(complaint_count) OVER (PARTITION BY market ORDER BY month) AS prior_month_count,
    ROUND(
        100.0 * (complaint_count - LAG(complaint_count) OVER (PARTITION BY market ORDER BY month))
        / NULLIF(LAG(complaint_count) OVER (PARTITION BY market ORDER BY month), 0),
        1
    ) AS mom_pct_change
FROM monthly
ORDER BY market, month;


-- ----------------------------------------------------------------------------
-- 4. REGULATORY ESCALATION RATE BY MARKET & SEVERITY
--    Feeds directly into a "timely, accurate updates to regulators" report.
-- ----------------------------------------------------------------------------
SELECT
    market,
    severity,
    COUNT(*) AS total_complaints,
    SUM(CASE WHEN escalated_to_regulator THEN 1 ELSE 0 END) AS escalated_count,
    ROUND(100.0 * SUM(CASE WHEN escalated_to_regulator THEN 1 ELSE 0 END) / COUNT(*), 1) AS escalation_rate_pct
FROM complaints
GROUP BY market, severity
ORDER BY escalation_rate_pct DESC;


-- ----------------------------------------------------------------------------
-- 5. REPEAT COMPLAINT RATE BY PRODUCT LINE
--    A high repeat rate on a product line signals the root cause hasn't
--    actually been fixed at the source -- a key "did the fix work" metric.
-- ----------------------------------------------------------------------------
SELECT
    product_line,
    COUNT(*) AS total_complaints,
    SUM(CASE WHEN repeat_complaint THEN 1 ELSE 0 END) AS repeat_complaints,
    ROUND(100.0 * SUM(CASE WHEN repeat_complaint THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_rate_pct
FROM complaints
GROUP BY product_line
ORDER BY repeat_rate_pct DESC;


-- ----------------------------------------------------------------------------
-- 6. SLA COMPLIANCE BY CHANNEL (resolved within 10 days = compliant)
--    Uses a running percentile-style bucket via CASE + window function to
--    approximate SLA compliance tiers per channel.
-- ----------------------------------------------------------------------------
SELECT
    channel,
    COUNT(*) AS total_complaints,
    SUM(CASE WHEN resolution_days <= 10 THEN 1 ELSE 0 END) AS within_sla,
    ROUND(100.0 * SUM(CASE WHEN resolution_days <= 10 THEN 1 ELSE 0 END) / COUNT(*), 1) AS sla_compliance_pct,
    ROUND(AVG(resolution_days), 1) AS avg_resolution_days
FROM complaints
GROUP BY channel
ORDER BY sla_compliance_pct ASC;


-- ----------------------------------------------------------------------------
-- 7. HIGH-SEVERITY, UNRESOLVED, AGING COMPLAINTS (operational triage list)
--    The kind of ad-hoc query an analyst would run same-day to flag cases
--    needing immediate attention before they become an escalation.
-- ----------------------------------------------------------------------------
SELECT
    complaint_id,
    market,
    channel,
    product_line,
    root_cause,
    resolution_days,
    complaint_date
FROM complaints
WHERE severity = 'High'
  AND resolved = 0
  AND resolution_days > 14
ORDER BY resolution_days DESC
LIMIT 50;
