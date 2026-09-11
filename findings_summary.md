# Complaints Insights Summary

_Auto-generated from data/complaints.db — 8 root-cause categories, analysis window per generate_data.py_

## Key Findings

1. **Root cause concentration:** 'Billing/charge discrepancy' alone accounts for 28.1% of all complaints. The top 4 categories together drive ~80% of volume — prioritizing fixes here has outsized impact.

2. **Systemic delay flags:** Fraud/unauthorized charge handling, App/digital platform bug, Delayed dispute resolution show resolution times over 1.5x the overall average, indicating a process/system issue rather than one-off agent variance.

3. **Regulatory exposure:** MX has the highest escalation-to-regulator rate at 10.8% — a candidate for a targeted intervention before it shows up in the next regulatory review.

4. **Channel SLA gap:** Call has the weakest SLA compliance at 82.1% of cases resolved within 10 days, against an 80% target.

## Recommended Actions

- Route root-cause categories above the 80% Pareto line to a formal engineering/process review

- Set up automated weekly alerting when a market's escalation rate crosses a defined threshold

- Investigate channel-specific bottlenecks (staffing, tooling) for the lowest-SLA channel

- Track repeat-complaint rate by product line month-over-month to confirm fixes are actually working
