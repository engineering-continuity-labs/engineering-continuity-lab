# v0.1 scoring contract

**Status:** Verified. This is the normative scoring contract; [docs/scoring-model.md](../../docs/scoring-model.md) explains it.

All signals are finite values in `[0, 1]`, calculated for a contributor within one component. `files` means distinct historical changed paths retained after filtering; `touches` means the sum of distinct contributor commit counts in the component; `months` means distinct `%Y-%m` values from author timestamps.

| ID | Signal and default weight | Input evidence, formula, edge cases, limitations |
| --- | --- | --- |
| ECL-SC-001 | Change Ownership, 0.25 | Contributor additions plus deletions divided by component total churn. If total churn is zero, use contributor commits divided by `touches`. Binary/unknown line counts are zero churn; churn overvalues rewrites and formatting. |
| ECL-SC-002 | Recency, 0.20 | Latest contributor component timestamp and reference time: `2 ^ (-max(0, age_days) / half_life_days)`. Future evidence is clamped to age zero; activity is not understanding. |
| ECL-SC-003 | Change Frequency, 0.20 | Contributor distinct component commits divided by `touches`. A commit counts once per contributor/component even if it changes several files; commit practices affect it. |
| ECL-SC-004 | Code-area Breadth, 0.15 | Contributor distinct files divided by component distinct files. Deleted, generated, and renamed paths may distort breadth. |
| ECL-SC-005 | Unique Contribution, 0.10 | Files historically touched only by the contributor divided by component distinct files. It measures unique Git history, not exclusive knowledge. |
| ECL-SC-006 | Historical Persistence, 0.10 | Contributor active months divided by component active months. It measures repeated activity periods, not tenure; author time zones define months. |

## Aggregation and risk contracts

- **ECL-SC-010 Raw score:** `sum(weight × signal) / sum(weights)`.
- **ECL-SC-011 Weight normalization:** weights must name exactly the six signals, be finite and non-negative, and have a positive sum. The formula normalizes by that sum.
- **ECL-SC-012 Share normalization:** contributor share is raw score divided by the component’s total raw score. A zero total raises an error rather than inventing shares.
- **ECL-SC-013 Half-life:** default half-life is 180 days. The reference timestamp defaults to the latest included author date and may be set explicitly with a timezone; it cannot precede included evidence.
- **ECL-SC-014 Concentration:** HHI is `Σ share²` for component contributors.
- **ECL-SC-015 Risk boundaries:** LOW `< 0.40`; MEDIUM `0.40 ≤ HHI < 0.60`; HIGH `0.60 ≤ HHI < 0.80`; CRITICAL `HHI ≥ 0.80`.
- **ECL-SC-016 Departure loss:** equals the departing contributor’s pre-departure score share.
- **ECL-SC-017 Remaining shares:** are not renormalized to hide modeled loss.
- **ECL-SC-018 Successor:** rank remaining contributors by descending fraction of departed files they touched, then descending raw score, then contributor email ascending.
- **ECL-SC-019 No successor:** return no successor when the best remaining file overlap is zero.

## Invariants and limitations

Signal values and concentration must be finite and in `[0,1]`; component shares must sum approximately to 1. A reference timestamp cannot precede included evidence. Empty histories and zero total component scores are errors.

Churn bias, formatting, squashing, aliases, bots, generated code, historical/deleted files, missing branches, mailmap quality, and directory grouping can distort results. Semantic knowledge, reviews, pairing, operations, availability, and handover readiness are not represented.
