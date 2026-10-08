# v0.3 traceability of the traceability feature

**Status: offline runtime and report-v3 serialization implemented; validation is scoped below.** Trace-path VERIFIED means observed connection evidence; governance VERIFIED means the named automated acceptance tests passed. Azure acquisition is implemented and synthetically tested in the separate increment below; live compatibility, traceability presentation and v0.4 remain deferred.

Architecture D301–D311 remains normative. Product Owner/Architect/QA handoffs for this slice are in `docs/validation/v0.3-offline-plan.md`. Actual modules: `src/continuity/domain/traceability.py`, `src/continuity/analysis/traceability.py`, `src/continuity/traceability_providers/synthetic.py`; tests: `tests/test_traceability.py`. Original design mapping below is retained with updated requirement-level status; grouped requirements including later delivery remain PARTIAL/ACCEPTED. See per-AC evidence for exact verification boundaries.

| Spec ID | Acceptance criteria | Design | Implementation / remaining plan | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| ECL-FR-301 | ECL-AC-301, 319 | D301, D302, D310 | `domain/traceability.py`: minimum immutable WI values | synthetic domain/optional-field cases | VERIFIED |
| ECL-FR-302, 323; ECL-NFR-311 | ECL-AC-322, 332 | D301, D305, D309 | `traceability_providers/azure_devops.py`, `azure_profile.py` | Provider profile/capability/continuation tests; live compatibility MANUAL | PARTIAL |
| ECL-FR-303; ECL-NFR-303, 308 | ECL-AC-302, 308, 324–325, 333 | D302, D303, D306 | provenance/boundary/reference values | scoped joins, source timestamps, deterministic snapshot cases | PARTIAL |
| ECL-FR-304, 325 | ECL-AC-302, 305, 308, 318, 334 | D303, D304 | typed observed links and supported projection rules | direct/source/derived label/support fixtures | VERIFIED |
| ECL-FR-305, 311–312 | ECL-AC-308, 310–311, 334–335 | D303–D306 | `analysis/traceability.py`: typed paths and hop gaps | complete and short-chain fixtures with ordered support refs | VERIFIED |
| ECL-FR-306 | ECL-AC-302–303, 309 | D303, D305, D307 | scoped WI_PR observations | one-to-many/many-to-one/direct-absence fixtures | VERIFIED |
| ECL-FR-307 | ECL-AC-305, 310, 313 | D303, D305, D307 | independent WI_COMMIT observations | direct-only/no-intent fixtures; no invented WI_PR | VERIFIED |
| ECL-FR-308 | ECL-AC-304, 311, 325 | D303, D306, D308 | PR membership refs/projection | several commits, empty membership, outside-Git-revision cases | VERIFIED |
| ECL-FR-309–310 | ECL-AC-306–307, 325, 334 | D302, D303, D308 | immutable Git/change projection and existing ComponentStrategy | exact revision/path/multicomponent/configuration tests | VERIFIED |
| ECL-FR-313–315, 322; ECL-NFR-310 | ECL-AC-309–313, 320–322, 327, 335 | D305–D307 | per-population/per-hop capability and lookup evidence | complete-empty vs missing/partial/failed/unsupported fixtures | VERIFIED |
| ECL-FR-316–317, 328; ECL-NFR-302 | ECL-AC-314–316, 323–324 | D302, D304 | canonical ordering, duplicate isolation and bounded path grammar | permutation, collision, contradictory duplicate and cycle fixtures | VERIFIED |
| ECL-FR-318 | ECL-AC-315, 317–319 | D302–D305 | validation/quarantine of required evidence | malformed IDs/paths/types/time/kinds, absent optional data | VERIFIED |
| ECL-FR-319 | ECL-AC-324–325, 333 | D306 | eligibility and boundary compatibility projection | incompatible windows/revisions/depth/alias maps; no text/author inference | VERIFIED |
| ECL-FR-320; ECL-NFR-307 | ECL-AC-328–329, 336, 340, 348–349 | D308; `docs/report-schema-v3.md` | immutable joins and additive v3 report envelope; `continuity/reporting/traceability.py`, `ui/dist/model.js` | `tests/test_traceability_reporting.py`, `ui/tests/model.test.js`, `ui/tests/reviews-ui.test.js` | VERIFIED |
| ECL-FR-321; ECL-NFR-304–306, 313 | ECL-AC-301, 330–331, 333 | D302, D310 | allowlists, safe aliases, sanitized diagnostic values | synthetic sentinels, no-person/no-inference negative cases; origin review | PARTIAL |
| ECL-FR-324 | ECL-AC-301–327, 330–335 | D311; QA fixture manifest | `traceability_providers/synthetic.py` in-memory BASE/variant fixtures | BASE oracles and named variants in acceptance criteria | PARTIAL |
| ECL-FR-326–327 | ECL-AC-326–327, 334–335, 337, 339 | D305, D307, D308 | four independent artifact coverage results; later presenter | population/count/dedup/null ratios; future artifact-only content review | PARTIAL |
| ECL-NFR-301, 312 | ECL-AC-301, 332–333 | D301, D309 | offline core/provider boundary | domain dependency and fixture-network-isolation tests | PARTIAL |
| ECL-NFR-309 | ECL-AC-336, 338 | D308, D311 | later additive versioned schema/types | future consumer migration/version/unsupported-kind tests | ACCEPTED |
| ECL-FR-329–335 | ECL-AC-336, 340–349 | `docs/report-schema-v3.md`; `docs/architecture.md` | `continuity/reporting/traceability.py`; `ui/dist/model.js`; generated BASE fixture | `tests/test_traceability_reporting.py`; Python/browser semantic and round-trip tests | VERIFIED |
| ECL-NFR-314–317 | ECL-AC-331, 341–346, 348–349 | `docs/report-schema-v3.md` | canonical allowlisted serializer and browser validation | deterministic, recognizable-private-value, semantic-negative and Python/browser tests pass; arbitrary alias origin approval remains manual | PARTIAL |

## Executed offline acceptance evidence

All references below resolve to `tests/test_traceability.py`, with method prefix `test_acNNN_`; multiple tests sharing the prefix collectively cover that criterion. Tests verify the offline normalized contract, not live provider correctness or a public report serialization API. Invalid constructor values are safely rejected; a fixture acquisition boundary isolates rejected required records via `isolate_invalid_fixture_record`, without retaining raw input.

| Acceptance criterion | Actual automated evidence | Status / boundary |
| --- | --- | --- |
| ECL-AC-301 | `test_ac301_*` | VERIFIED — offline synthetic contract |
| ECL-AC-302 | `test_ac302_*` | VERIFIED — offline synthetic contract |
| ECL-AC-303 | `test_ac303_*` | VERIFIED — offline synthetic contract |
| ECL-AC-304 | `test_ac304_*` | VERIFIED — offline synthetic contract |
| ECL-AC-305 | `test_ac305_*` | VERIFIED — offline synthetic contract |
| ECL-AC-306 | `test_ac306_*` | VERIFIED — offline synthetic contract |
| ECL-AC-307 | `test_ac307_*` | VERIFIED — offline synthetic contract |
| ECL-AC-308 | `test_ac308_*` | VERIFIED — offline synthetic contract |
| ECL-AC-309 | `test_ac309_*` | VERIFIED — offline synthetic contract |
| ECL-AC-310 | `test_ac310_*` | VERIFIED — offline synthetic contract |
| ECL-AC-311 | `test_ac311_*` | VERIFIED — offline synthetic contract |
| ECL-AC-312 | `test_ac312_*` | VERIFIED — offline synthetic contract |
| ECL-AC-313 | `test_ac313_*` | VERIFIED — offline synthetic contract |
| ECL-AC-314 | `test_ac314_*` | VERIFIED — offline synthetic contract |
| ECL-AC-315 | `test_ac315_*` | VERIFIED — offline synthetic contract |
| ECL-AC-316 | `test_ac316_*` | VERIFIED — offline synthetic contract |
| ECL-AC-317 | `test_ac317_*` | VERIFIED — offline synthetic contract |
| ECL-AC-318 | `test_ac318_*` | VERIFIED — offline synthetic contract |
| ECL-AC-319 | `test_ac319_*` | VERIFIED — offline synthetic contract |
| ECL-AC-320 | `test_ac320_*` | VERIFIED — offline synthetic contract |
| ECL-AC-321 | `test_ac321_*` | VERIFIED — offline synthetic contract |
| ECL-AC-322 | `test_ac322_*` | VERIFIED — offline synthetic contract |
| ECL-AC-323 | `test_ac323_*` | VERIFIED — offline synthetic contract |
| ECL-AC-324 | `test_ac324_*` | VERIFIED — offline synthetic contract |
| ECL-AC-325 | `test_ac325_*` | VERIFIED — offline synthetic contract |
| ECL-AC-326 | `test_ac326_*` | VERIFIED — offline synthetic contract |
| ECL-AC-327 | `test_ac327_*` | VERIFIED — offline synthetic contract |
| ECL-AC-330 | `test_ac330_*` | VERIFIED — offline synthetic contract |
| ECL-AC-332 | `tests/test_azure_devops_provider.py`, `tests/test_azure_transport.py` | PARTIAL — automated Server/Services profile evidence passes; real deployments MANUAL |
| ECL-AC-333 | `test_ac333_*` | VERIFIED — offline synthetic contract |
| ECL-AC-334 | `test_ac334_*` | VERIFIED — offline synthetic contract |
| ECL-AC-335 | `test_ac335_*` | VERIFIED — offline synthetic contract |
| ECL-AC-337 | deferred; unsupported future relation rejection has AC318 evidence only | ACCEPTED — later adapter/report/presenter/extension gate |
| ECL-AC-338 | deferred; unsupported future relation rejection has AC318 evidence only | ACCEPTED — later adapter/report/presenter/extension gate |
| ECL-AC-339 | `test_ac339_*` | VERIFIED — offline synthetic contract |
| ECL-AC-328 | `ui/tests/model.test.js`; `tests/test_traceability_reporting.py` | VERIFIED — v1 Git-only round trip and no traceability mutation |
| ECL-AC-329 | `ui/tests/model.test.js`; `ui/tests/reviews-ui.test.js` | VERIFIED — v2 review behavior and v3 combined envelope round-trip |
| ECL-AC-331 | `tests/test_traceability_reporting.py`; `tests/test_traceability_reporting_review.py`; shared adversarial corpus; `ui/tests/model.test.js` | PARTIAL — synthetic allowlist/recognizable credential/path/error negatives pass; arbitrary alias origin/publication requires source approval |
| ECL-AC-336 | `tests/test_traceability_reporting.py`; `ui/tests/model.test.js` | VERIFIED — v3 additive section and contradictory paths/counts rejected |
| ECL-AC-340–349 | `tests/test_traceability_reporting.py`; `ui/tests/model.test.js` | VERIFIED — automated synthetic envelope/semantics/status/metric/ordering/BASE/PR_PATH_ONLY and cross-runtime checks; historical report corrections have fresh Independent Code Reviewer APPROVE; current closure regressions and evidence are recorded separately |

## Review, CI and remaining delivery

The independent takeover run passed 160 Python tests, strict mypy for 25 source files, 26 Node tests (25 model/review and one Pages), both JavaScript syntax checks, wheel build and `git diff --check`. Exact commands, initial sandbox failures and delivery status are recorded in `docs/validation/v0.3-report-v3-verification.md`. This replaces inherited 148/149-count and unsubstantiated approval claims.

The complete historical initial review found two BLOCKER, seven MAJOR and one MINOR findings; all original counterexamples and corrections remain in `docs/validation/v0.3-report-v3-review.md`. Fresh separate non-author review on main `47ca31560d0d1a6c76ee6d3a76d9c9bbb19b74ad` found three additional MAJOR Python/browser gaps (RP-R11–13); minimal browser corrections and three paired Python/Node regressions closed them. Final Independent Code Reviewer APPROVE: R1–R4/R6–R10 VERIFIED CLOSED; R5 SUPERSEDED by retained history and fresh evidence. Actual full221Python/30Node/30-source checks passed; closure PR CI is a separate merge gate. Automated VERIFIED criteria alone are not approval. No live Azure, visual UI, release or v0.4 status is upgraded.

The Services/Server acquisition library is now implemented below. Actual deployment/API/auth/TLS compatibility, traceability presentation, explorer acquisition integration and v0.4 remain deferred. Synthetic profiles cannot establish live Server support or certify arbitrary private aliases for publication. The earlier offline implementation review remains in `docs/validation/v0.3-offline-review.md`. PRs #17–21 are merged; no v0.3 release/tag exists, and this closure does not merge or release anything.

## First Azure provider increment

The user-authorized scope is ECL-FR-336–339 / ECL-NFR-318, refining ECL-FR-302/303/322/323/325 and ECL-NFR-301/304–306/310–313/316. PO requirements and pre-development QA strategy are in the product/acceptance documents. Architecture and URL/capability/privacy contracts are in `docs/azure-devops-provider.md` and `docs/architecture.md`. Implementation remains confined to `traceability_providers/azure_{profile,transport,dto,devops}.py`. Domain/derive/report behavior is unchanged.

| Spec → acceptance | Architecture → implementation | Actual automated verification | Status |
| --- | --- | --- | --- |
| ECL-FR-336 / ECL-AC-350, existing AC332 | Deployment/version/URL contracts → azure_profile.py | All four profiles, explicit compatible/incompatible override and Server/Services encoding tests | VERIFIED for runtime config/fixtures; live deployment compatibility MANUAL |
| ECL-FR-337 / ECL-AC-351 | Independent populations/provider links → azure_devops.py + azure_dto.py | Azure-shaped BASE → provider → derive: PR3/4, commit4/4, WI2/3, component2/2,1/1,1/1; Python/report/browser round trip | VERIFIED (synthetic) |
| ECL-FR-338 / ECL-AC-352 | Exact GUID scope/approved aliases → azure_profile.py + azure_dto.py | Artifact grammar, foreign project/repo, wrong family, malformed refs and no-text-inference negatives; provider origins/components | VERIFIED (synthetic); alias/path publication origin MANUAL |
| ECL-FR-339 / ECL-AC-353, existing AC320–322/335/339 | Per-operation completeness → azure_devops.py | Offset/keyset/continuation pages, 200+1 batching, duplicates, short-page continuation, late/first failures, limits, empty/zero, unsupported and scoped status negatives | VERIFIED (synthetic) |
| ECL-NFR-318 / ECL-AC-354, existing AC331 | Native/credential/TLS boundary → azure_transport.py | Strict JSON, finite bounds, PAT/body/person sentinels, categorical HTTP401/403/404/405/429/5xx, verified SSL context, no redirects/cookies/pickle; real synthetic loopback pipeline | PARTIAL — automated transport/privacy passes; source approval and live deployment TLS/auth MANUAL |
| ECL-NFR-314/317 / ECL-AC-355 | Existing derive/report retained | Original provider regression record plus fresh closure:208 Python /29-source mypy /27 Node tests, wheel/syntax checks | VERIFIED for executed automated regression gates |

Exact commands/results: `docs/validation/v0.3-azure-provider-verification.md`. Developer history and actual independent post-merge review: `docs/validation/v0.3-azure-provider-review.md`. Automated evidence does not approve the developer's own work. PR #20 and its main/PR CI are merged/green as recorded in the closure verification. Actual independent review now occurs in the closure; no self-approval is inferred from merge. No v0.3 release/tag/automatic merge.

## Independent provider closure

Base `5f4d66715cd765751ebf57da565925211fd6e79f` is the green PR #20 merge. Initial independent Code Reviewer decision REQUEST CHANGES identified AZ-R01–04 (4 MAJOR,0 BLOCKER,0 MINOR), beyond the prior developer preflight. Corrections are confined to the Azure acquisition/DTO boundary; no new capability or changes to core derivation/report/browser/scoring. Exact proofs, owning-role handoffs, fresh208 Python/27 Node/29-source verification and final independent APPROVE decision are in `docs/validation/v0.3-azure-provider-review.md` and `docs/validation/v0.3-closure-verification.md`.

| Finding → existing criterion | Correction implementation | Regression evidence | Current gate |
| --- | --- | --- | --- |
| AZ-R01 → AC315/353 | `azure_devops.py`: quarantine conflicting raw required WI labels, prevent resurrection, preserve separately sourced unresolved refs | `test_az_r01_conflicting_wi_is_quarantined_without_coverage_or_resurrection` | VERIFIED (synthetic regression); independently re-reviewed CLOSED |
| AZ-R02 → AC320/353 | `azure_devops.py`: per-reference WIQL validation/positive retention, partial stop | `test_az_r02_*` malformed positions, late/nonprogress pages | VERIFIED (synthetic regression); independently re-reviewed CLOSED |
| AZ-R03 → AC353 | `azure_devops.py`: same reference limit on dedicated fallback | `test_az_r03_*` overlimit/exactlimit/malformed positives | VERIFIED (synthetic regression); independently re-reviewed CLOSED |
| AZ-R04 → AC331/354 | `azure_dto.py`: pre-domain recognizable-private-path rejection | `test_az_r04_*` credential sentinel families and safe paths | VERIFIED (synthetic regression); independently re-reviewed CLOSED |

Synthetic/runtime criteria cannot certify live Azure Server/Services API, TLS or authentication. Those remain MANUAL/PARTIAL. Package 0.2.0 is unchanged; the separate local Azure connection increment is recorded below; visual traceability presentation remains deferred.

Final Azure closure decision is APPROVE from independent reviewer `/root/azure_independent_review`; AZ-R01–04 are CLOSED and no BLOCKER/MAJOR/MINOR remains in that inspected scope. That Azure approval did not close the historical report-v3 whole-diff gate; the separate current report review above now closes it. Neither review certifies a live deployment. Closure remote PR CI remains required; fresh local evidence is recorded in the closure verification, not inferred from prior totals.

## Local connection increment

| Requirements | Acceptance | Architecture / Implementation | Evidence | Status |
| --- | --- | --- | --- | --- |
| ECL-FR-340 | ECL-AC-357 | docs/azure-local-connection.md → azure_connection.py + cli.py | tests/test_azure_connection.py all-profile config projection, synthetic acquisition and section round trip | VERIFIED — synthetic automation; independent APPROVE |
| ECL-FR-341 / ECL-NFR-319 | ECL-AC-358 | strict bounded private TOML + existing profile/map validation | missing approval, unknown/duplicate/secret keys, invalid types/bounds/identity, oversize, HTTP rejection and no acquisition | VERIFIED — synthetic automation; independent APPROVE |
| ECL-FR-342 | ECL-AC-359 | hidden runtime-only prompt; anonymous opt-in | TTY checks, empty/EOF/interrupt, getpass fallback refusal, runtime transport input and sentinel exclusion | VERIFIED — synthetic automation; independent APPROVE |
| ECL-FR-343 | ECL-AC-360 | existing provider → derive → section serializer; fixed diagnostics/status exits | COMPLETE/PARTIAL/FAILED round trips and raw error sanitization | VERIFIED — synthetic automation; independent APPROVE |

No CLI synthetic result certifies a live Azure deployment, publication rights or PAT scopes; these remain MANUAL. Independent review decision and exact gate results are recorded in docs/validation/v0.3-azure-local-connection-verification.md.
