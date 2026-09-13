# Experimental scoring model v0.1

**Git activity is only a proxy for knowledge.** The model is an explainable hypothesis, not a validated measurement of knowledge or probability of failure. Thresholds and default weights are heuristic. They require empirical calibration and human review.

For each component and contributor, calculate six signals in [0, 1]:

| Signal | Definition | Default weight |
| --- | --- | --- |
| Change ownership | Contributor additions + deletions divided by component total churn. If all churn is zero/unknown, use change-frequency share. | .25 |
| Recency | 2 raised to minus days since latest component activity divided by half-life days (default 180). | .20 |
| Change frequency | Distinct contributor commits touching the component divided by the sum of contributor commit counts in that component. | .20 |
| Code-area breadth | Distinct historical files touched by contributor divided by component historical files. | .15 |
| Unique contribution | Component files touched only by this contributor divided by all component files. | .10 |
| Historical persistence | Distinct active author-date calendar months for contributor divided by component active calendar months. | .10 |

A commit touching multiple files counts once for frequency within a component. Line counts still sum over all its changes. Binary/unknown counts contribute no numeric churn; their file/commit/month evidence still counts. Months are taken in each author's recorded timezone. Persistence measures repeated periods of activity, not elapsed tenure. Recency defaults to the newest author timestamp in the entire history. An explicit reference date must include a timezone and be no earlier than the evidence.

The raw score is `sum(weight × signal) / sum(weights)`. Weights must be finite, nonnegative, cover all six signals, and have positive total. Shares are raw scores divided by the component's total raw score. If a custom configuration yields zero total evidence score, analysis fails explicitly instead of inventing shares.

Concentration is the Herfindahl index `sum(share²)`. One contributor yields 1; N equal contributors yield 1/N.

| Risk | Concentration |
| --- | --- |
| LOW | below .40 |
| MEDIUM | .40 to below .60 |
| HIGH | .60 to below .80 |
| CRITICAL | .80 to 1 |

Departure loss is the departing contributor's **pre-departure score share**, not a claim about irreplaceable knowledge. Remaining shares are not renormalized to conceal the loss. Uncovered files identify historical paths with no other contributor. The successor candidate maximizes the fraction of departed files they have touched, breaking ties by component score and then email. No candidate is offered without file overlap. This does not establish availability or readiness, and overlap ignores depth of understanding.

Churn can overvalue rewrites or formatting. Breadth and unique contribution include deleted/generated files. Squashing, imports, aliases, bots, and missing branches distort evidence. Concentration is relative: uniformly stale contributors can still produce LOW risk. Use signal breakdowns, counts, and team knowledge together. Changing component depth can materially change the classification.
