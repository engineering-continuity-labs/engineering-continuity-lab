# v0.4 acceptance criteria and pre-development QA plan

Status: PLANNED; no v0.4 runtime verification claimed. Requirements and architecture precede Developer work.

| ID | Observable criterion / planned evidence |
| --- | --- |
| ECL-AC-401 | Same alias across kind/scope/version remains distinct; invalid or missing required identity fields are rejected safely. Typed identity positives/negatives. |
| ECL-AC-402 | Only legal explicit relation pairs accepted; title/branch/path/numeric resemblance creates no link. Cross-scope/wrong-kind/cycle/malformed negatives. |
| ECL-AC-403 | v0.3 snapshot identity/scope/revision mismatch cannot support current joins; absent WI/component is unresolved, not created. Exact and stale snapshot fixtures. |
| ECL-AC-404 | Full and direct/PR_PATH-only shorter requirement-code chains retain every original status/origin/support and both source bounds; association alone has no qualified code numerator. |
| ECL-AC-405 | Test linkage may exist without execution; PASS/FAIL count as qualified execution, SKIPPED/UNKNOWN do not. Exact version/target qualification tested separately from run outcome. |
| ECL-AC-406 | Missing/wrong test version or target revision/snapshot excluded; all valid distinct runs remain visible; same scoped observation ID with contradictory fields quarantined independent of response order. |
| ECL-AC-407 | Unsupported/unknown/failed/partial lookup never establishes MISSING; complete supported empty lookup can. Positive links survive late partial failure. |
| ECL-AC-408 | Multiple links/routes/runs do not multiply units; independent unlinked requirements/tests stay in denominators; linked-only external artifacts cannot expand denominator. |
| ECL-AC-409 | Exact BASE counts are requirement-code2/4, requirement-test2/4, requirement-architecture2/4 and qualified executed-tests2/4; distinct qualified runs PASS1/FAIL1/SKIPPED1/UNKNOWN1. |
| ECL-AC-410 | Partial supported evidence shows observed counts with partial badge; unavailable/zero-denominator fraction is null and reasoned, distinct from measured0. No readiness/success-rate aggregate. |
| ECL-AC-411 | Every unresolved segment/conflict explains scoped reference, relationship, capability/completeness and reason; observed/derived labels stay distinct. |
| ECL-AC-412 | Permuting populations, associations, observations, boundaries/diagnostics does not change output; semantic node/support order remains preserved. |
| ECL-AC-413 | Credential/raw-content/reverse-map/local-path sentinels never enter public evidence or errors. Arbitrary alias publication remains a separately recorded source-owner responsibility. |
| ECL-AC-414 | Finite item/link/observation/path limits stop with truthful scoped partial positives; no unbounded traversal/inference/network occurs during offline derivation. |
| ECL-AC-415 | Old v1/v2/v3 reports/scoring/UI remain identical; existing consumers reject new kinds/future versions until a separate rollout explicitly implements them. |
| ECL-AC-416 | Verification metadata describes declared historical runs only; no claim that tests executed locally or that a requirement is correct/compliant. |

## Project-owned SYNTHETIC BASE oracle

Fixed approved aliases, immutable versions and one exact joined v0.3 BASE snapshot:

- Requirements Q1–Q4 independently selected. Q1→WI1001 and Q2→WI1002 each have an existing VERIFIED code path. Q3→WI1003 has no code path; Q4 has no association. Requirement implementation2/4.
- Tests T1–T4 independently selected. T1→Q1, T2→Q2, T3→Q1, T4 unlinked. Distinct requirements with test associations2/4.
- Documents ADR1→Q1 and ICD1→Q2; ADR1 also explicitly references an existing component. Architecture requirement linkage2/4.
- Four exact-version/target observations: V1→T1 PASS, V2→T2 FAIL, V3→T3 SKIPPED, V4→T4 UNKNOWN. Qualified executed-tests2/4. Distinct outcome counts1 each; no success-rate score.

Variants: EMPTY; NO_LINKS; PARTIAL; LATE_FAILURE; FAILED; UNSUPPORTED; WRONG_SCOPE; STALE_REVISION; WRONG_TEST_VERSION; UNLINKED_POPULATIONS; LINKED_ONLY; DUPLICATES; CONFLICTING_RUN; MULTIPLE_RUNS; SHORT_CODE_PATH; MALFORMED; PRIVACY; LIMIT; REORDERED. Existing v0.3 boundary/gap semantics remain authority.

Automated implementation gates: core unit/negative/regression/integration and exact counts, strict typing, existing Python/Node/UI/syntax/wheel/diff checks. Manual gates: source publication/version approval, live adapters/deployment compatibility and any later real visual verification. Design PR gates verify document chain and unchanged baseline, not runtime behavior.
