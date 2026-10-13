# v0.5 acceptance and pre-development QA plan

Status: PLANNED runtime verification. This PR verifies only specification/design consistency, independent review and unchanged baseline CI. Synthetic numbers below are reproducible hand-worked planned oracles, not executed/generated fixtures; live profiles/publication/actual rendering remain MANUAL.

| ID | Observable criterion / planned evidence |
| --- | --- |
| ECL-AC-501 | Manager first screen identifies system/period/sources/attention/unavailable/components/limitations; twelve sections and four-area navigation retained, no hidden overall/team/person/maturity score. ALL_DIMENSIONS, NO_OVERALL_SCORE. |
| ECL-AC-502 | Existing continuity/review/traceability/four requirement metrics/outcomes are imported unchanged with original rule/source time; historical source not represented as current-window evidence, no changed legacy envelope/math. |
| ECL-AC-503 | Scoped independent WI/PR/Build identities, selection/fingerprints and nullable fields roundtrip; exact duplicates count once and contradictory same observation quarantines before limits; no favorable/latest selection. |
| ECL-AC-504 | NORMAL_FLOW four durations2/4/6/8d gives median5d,p75=6d,p90null; AGING_WORK/open31d classified30–90 bucket and ATTENTION; NO_COMPLETION has no cycle duration, not0. |
| ECL-AC-505 | PARTIAL_HISTORY/FAILED_COLLECTION/UNSUPPORTED_HISTORY retain positive observed subsets with reasons; missing initial/history sequence cannot establish first/last episode, zero reopens or historical inventory. |
| ECL-AC-506 | CURRENT_VS_PREVIOUS equal contiguous windows, half-open boundary and explicit UTC/as_of/retrieval; reject UNEQUAL_WINDOW_REJECTED, overlap/gap/nonpositive/future inventory/malformed timestamps. Calendar offset equivalents yield same instants/output. |
| ECL-AC-507 | OPEN_PR age from exact boundary state+created, MERGED_PR from actual merge event, SLOW_PR explicit lead duration; abandoned completion is not merge, created filtering cannot certify completed population. |
| ECL-AC-508 | BUILD_SUCCESS/BUILD_FAILURE: known terminal SUCCESS2/FAILURE1/PARTIAL_SUCCESS1 → success2/4,failure1/4; UNKNOWN separately excluded, queue-only/unfinished duration unavailable. NO_BUILD_CAPABILITY=null, never0. |
| ECL-AC-509 | Quantile exact rational arithmetic, nearest-rank p75 n>=4/p90 n>=10, median n>=1; n3 p75null,n9 p90null,n10 available, sample/exclusions/censoring visible. |
| ECL-AC-510 | BUG_OPENED/BUG_RESOLVED/AGED_BUG/REOPENED_BUG use independent explicit lifecycle; selected representative resolution episode and distinct Bug units, no current-state/old-resolved-field reopen inference. |
| ECL-AC-511 | NO_HISTORY reopen null unless observed partial positives; PRIORITY/SEVERITY_CONFIGURED preserve configured separate categories/unknowns; SEVERITY_UNAVAILABLE=null even with empty inventory. |
| ECL-AC-512 | BUG_COMPONENT_LINK uses exact accepted support or typed declared mapping; UNMAPPED_BUG remains global/unavailable component; UNKNOWN_COMPONENT/scope/revision/depth mismatch cannot manufacture memberships or component0. |
| ECL-AC-513 | OPENED_GT_RESOLVED4vs2 delta2 triggers ER08 only complete compatible populations; RESOLVED_GT_OPENED2vs4 delta−2 no ER08; neither difference proves backlog growth due reopens/removals. |
| ECL-AC-514 | ZERO_POPULATION complete supported event/inventory counts0 but quantiles/fractionsnull; Quality PARTIAL/FAILED and missing required field produce subset/unknown/null, not measured totals. |
| ECL-AC-515 | COMPONENT_MIX counts a multi-component PR/Bug/build once globally and once per supported component; complete negatives require complete population+mapping lookup; repository build evidence alone not component membership. |
| ECL-AC-516 | TREND_IMPROVING/DEGRADING use exact comparable unit/state/type/mapping/sample/precision windows; median5→10d delta5d/100%, ER06; reversed delta−5d/−50%, no ER06; previous0 suppresses relative trend, unequal/incomplete/small samples suppress comparison. |
| ECL-AC-517 | Findings ER01–09 expose exact refs/scope/rule/threshold/severity/limitations; unsupported data yields completeness notices only; boundary thresholds tested30/90d,0.5review,0.25/0.5build,25%duration, positive defectdelta. No causal/LLM/personnel advice. |
| ECL-AC-518 | PARTIAL_EVIDENCE/MISSING_DELIVERY/MISSING_QUALITY display every completeness/capability/field/history/mapping/window axis and surviving positives; no implicit Atlas fallback or old snapshot relabel. |
| ECL-AC-519 | SAFE_PUBLIC_OUTPUT rejects DTOs/descriptions/comments/logs/secrets/local paths/reverse maps/extra person data and unknown keys/versions/duplicate JSON/nonfinite/depth/size; aliases need explicit publication approval. HTML escapes text and JSON script-breakout/URL probes, no external requests. |
| ECL-AC-520 | DETERMINISTIC/REORDERED_INPUT identical JSON/findings/HTML for equivalent sets/UTC spellings, ordered supports/history retained; IDs independent of wallclock/input order, output digests and refs verified on reimport; invalid refs/results fail closed. |
| ECL-AC-521 | Eventual offline CLI→validated package→assessment JSON/HTML→browser/no-server reopen/print QA planned; existing v1–v4 unaffected. No CLI/UI/metric implementation/release in this PR. |
| ECL-AC-522 | Every retained Azure profile has separate population/field/history/build capability and bounded pagination/failure tests; deployment DEFERRED_BY_DESIGN/UNSUPPORTED; synthetic fixtures never certify live compatibility. |

## Named acceptance matrix

All rows PLANNED until implemented. Delivery/Quality/Report namespaces distinguish repeated PARTIAL/FAILED labels.

| Group | Cases | Explicit expectation |
| --- | --- | --- |
| Delivery | NORMAL_FLOW, AGING_WORK, NO_COMPLETION | AC504 exact counts/durations, censored open inventory, no0 duration |
| Delivery | PARTIAL_HISTORY, FAILED_COLLECTION, UNSUPPORTED_HISTORY | AC505 per-history capability/coverage, observed positives only |
| Delivery | CURRENT_VS_PREVIOUS, UNEQUAL_WINDOW_REJECTED | AC506/516 exact windows/half-open/compare gates |
| Delivery | OPEN_PR, MERGED_PR, SLOW_PR | AC507 separate PR populations/actual merge/explicit timestamps |
| Delivery | BUILD_SUCCESS, BUILD_FAILURE, NO_BUILD_CAPABILITY | AC508 exact categories/denominator/null |
| Quality | BUG_OPENED, BUG_RESOLVED, AGED_BUG, REOPENED_BUG | AC510 planned lifecycle table below |
| Quality | NO_HISTORY, PRIORITY, SEVERITY_CONFIGURED, SEVERITY_UNAVAILABLE | AC511 configured field/history, no inferred categories/reopens |
| Quality | BUG_COMPONENT_LINK, UNMAPPED_BUG | AC512/515 mapping support and global distinct counts |
| Quality | OPENED_GT_RESOLVED, RESOLVED_GT_OPENED | AC513 separate population delta, no conservation claim |
| Quality | ZERO_POPULATION, PARTIAL, FAILED | AC514 count/null/subset versus unavailable |
| Report | ALL_DIMENSIONS, PARTIAL_EVIDENCE, MISSING_DELIVERY, MISSING_QUALITY | AC501/502/518 independent cards/source separation |
| Report | COMPONENT_MIX, TREND_IMPROVING, TREND_DEGRADING | AC515/516 no overlapping totals, gated direction |
| Report | NO_OVERALL_SCORE, SAFE_PUBLIC_OUTPUT | AC501/519 no health/team/person/quality-density score or leaks |
| Report | DETERMINISTIC, REORDERED_INPUT | AC520 stable full refs/rules/sets and preserved history order |

Additional negatives: conflicted revisions/sequence/observations, duplicate pages, equal timestamps with explicit sequence versus missing sequence, future/inverted dates, reopen crossing window, missing initial state, as_of selection skew, different process/precision/selection/mapping across windows, exact boundary start/end, unknown priority/severity/state, removed/deleted Bugs, canceled/unknown/unfinished builds, partial pipeline, multi-component mappings, retained historical v4 boundary, path/title/branch resemblance, source approval false, forged metrics/ref/digest, malicious markup, exact and excessive input/output bounds. Tests must exercise actual future handlers/roundtrip and no-network HTML, not just mirror a serializer.

## Planned Atlas lifecycle source oracle

Current `[2026-09-01T00:00:00Z,2026-10-01T00:00:00Z)`, previous `[2026-08-02,2026-09-01)`, complete UTC boundaries. All state transitions below have explicit immutable event IDs/monotone sequence; source owners declare the selected states OPEN/COMPLETE/REMOVED and created-start policy. This is source design, not a runtime fixture.

| Bug | Created UTC date | Observed lifecycle through current.end | End state / age | Explicit component |
| --- | --- | --- | --- | --- |
| B1 | Sep1 | OPEN→COMPLETE Sep5 | COMPLETE; first episode4d | Catalog |
| B2 | Sep3 | OPEN→COMPLETE Sep10→OPEN Sep15→COMPLETE Sep20 | COMPLETE; selected last episode5d; reopened once | Payments |
| B3 | Sep21 | OPEN, no completion | OPEN10d | Catalog |
| B4 | Aug17 | OPEN, no completion | OPEN45d, aged | Payments |
| B5 | Sep10 | OPEN→REMOVED Sep12 | REMOVED, not resolved | Unmapped |
| B6 | Aug28 | OPEN→REMOVED Sep22 | REMOVED, not resolved | Unmapped |

Six independent Bugs: current creations B1/B2/B3/B5=4, distinct completions B1/B2=2 (three completion events, not three Bugs), open B3/B4=2, aged B4=1, reopened B2=1. Selected resolution values4d/5d median4.5d,p75/p90null (n2). Priority P1/P2 and severity S1/S2 are explicitly configured categories with source fingerprint, never imported arbitrary process text. A separate unsupported-severity variant has same Bugs and null severity, never fabricated low values. Unmapped removed Bugs illustrate global selection; add a separately defined open unmapped Bug variant to test component-negative completeness.

Full flow oracle: four distinct completed WI/window with complete selected start/completion episodes; previous2/4/6/8d,current4/8/12/16d; source completion dates within their windows and no repeated episodes. Exact event records/explicit mappings become executable fixture in later implementation QA, against these expected counts, not invented aggregate JSON. Build run sample SUCCESS2/FAILURE1/PARTIAL_SUCCESS1 with explicit starts/finishes/revisions, durations2/4/6/8min and exact repository/component mapping qualifications.

## Gates and evidence classification

Before development: independent design review attacks reproducibility, unavailable/zero, snapshots/windows/mapping, denominators, conflicts/precision, findings/privacy and completeness. No runtime tests created in this design-only PR. This PR CI must keep baseline regressions/type/syntax/generator/wheel checks green and prove diff only approved documentation. Future runtime requires new source-oracle and adversarial tests, full regression, Python/browser/package/export parity and independent review. Live Server/Services/custom process/PAT/certificate/history correctness, publication rights, real browser/mobile/print accessibility are MANUAL until performed. QA exit: each requirement has a testable acceptance and explicit evidence classification; no implementation VERIFIED claim.

## Manager comprehension acceptance

Defined before development; test plan: docs/v0.5-manager-report-experience.md. Two-minute comprehension is MANUAL, not inferred from markup.

| ID | Named criterion | Expected observation |
| --- | --- | --- |
| ECL-AC-523 | MANAGER_TWO_MINUTE_SUMMARY | Executive Summary comes first: system/period/provenance, ≤8 finding groups, 6–9 cards, ≤10 attention components and compact coverage; two-minute human comprehension MANUAL. |
| ECL-AC-524 | HUMAN_FINDING_LABELS | All ER01–09 findings use fixed observation labels in normal UI; original rule IDs preserved in audit. |
| ECL-AC-525 | NO_RULE_ID_PRIMARY_VIEW | Primary summary contains no rule ID/version, raw ref, schema or fingerprint. |
| ECL-AC-526 | COMPONENT_ATTENTION_TABLE | Semantic component table separates six dimensions, sorts explicit severity first, and leaves unbound evidence Unavailable. |
| ECL-AC-527 | COMPONENT_DETAIL | Native component disclosure shows exact-bound measures and Inspect evidence anchor without raw refs initially. |
| ECL-AC-528 | TREND_HUMANIZATION | Qualified median trends display current/previous, signed unit delta and relative percentage; unqualified comparison says Trend unavailable. |
| ECL-AC-529 | UNAVAILABLE_NOT_ZERO | Null/missing/failed/unsupported remain Unavailable; accepted complete zero stays zero; unknown is never Normal. |
| ECL-AC-530 | NO_CAUSAL_LANGUAGE | Labels and investigation text describe observed evidence without team overload, quality decline, root cause or employee judgment. |
| ECL-AC-531 | NO_OVERALL_SCORE | No overall product/team/maturity score, combined number or combined traffic-light status. |
| ECL-AC-532 | METHOD_DETAILS_PRESERVED | Capabilities, collection/mapping status, boundaries, sample sizes, exclusions and thresholds remain inspectable. |
| ECL-AC-533 | EXACT_EVIDENCE_AVAILABLE | Every finding has its exact full support and rule/version/scope accessible; full source package retained. |
| ECL-AC-534 | SYNTHETIC_LABEL | Explicit synthetic render displays SYNTHETIC MANAGER EXAMPLE; aliases never infer provenance. |
| ECL-AC-535 | PRINT_ORDER | Print follows Executive Summary→Components→Engineering Details→Evidence & Methodology; disclosures opened for print and restored after. |
| ECL-AC-536 | KEYBOARD_ACCESS | Semantic headings/tables, native keyboard disclosures/anchors and visible focus; real keyboard/screen-reader verification MANUAL. |
| ECL-AC-537 | SAFE_DYNAMIC_TEXT | Dynamic labels and source text escaped, inert JSON cannot break out; no remote assets/telemetry; size limit retained. |
| ECL-AC-538 | SMALL_SCREEN | Desktop and narrow screenshots inspected; cards stack and tables scroll without losing evidence; real mobile usability MANUAL. |
| ECL-AC-539 | SOURCE_PARITY | Validated input equals embedded/downloaded reimport; Atlas medians10/5d, defect4/2/2/1/1, build2/1/1 and fractions unchanged; no core math/source changes. |
