# v0.3 acceptance criteria and QA design

**Status: ACCEPTED verification contract.** Offline execution evidence is recorded per criterion in `traceability.md`; report v3 serialization/import/export is implemented and tested. The Azure acquisition library has synthetic provider evidence; live deployment compatibility and traceability presenter gates remain deferred. Original offline design oracles below are unchanged.

## Acceptance cases

| ID | Given / When / Then | Planned evidence |
| --- | --- | --- |
| ECL-AC-301 | Given a SYNTHETIC work item with minimum scoped ID/type/state, when normalized, then it has safe provenance and no provider DTO or required personal fields. | Domain contract / normalization fixtures |
| ECL-AC-302 | Given one WI linked explicitly to one PR, when paths derive, then WI_PR is DIRECT_PROVIDER_LINK with source/observation/boundary refs and exactly one association. | BASE WI-1001→PR-51 |
| ECL-AC-303 | Given one WI linked to several PRs and several WIs linked to one PR, when aggregated, then associations remain distinct but a PR counts once. | BASE WI-1001→PR-51/54; WI-1001/1002→PR-51 |
| ECL-AC-304 | Given a PR with several observed commits, when membership derives, then each PR_COMMIT is preserved and components follow observed changes only. | BASE PR-51→a/b |
| ECL-AC-305 | Given an explicit WI_COMMIT link, when intent coverage derives, then it qualifies independently without inventing a WI_PR or full normative chain. | BASE WI-1002→c; PR-52 still lacks WI_PR |
| ECL-AC-306 | Given one commit touching one component, when mapped, then its exact revision/path links to the existing strategy output with mapping provenance. | BASE a→src/payments/retry.py |
| ECL-AC-307 | Given a commit touching several paths/components, when mapped, then each distinct change occurrence maps correctly; repeated paths and alternative intent routes do not multiply units. | MULTIPATH variant |
| ECL-AC-308 | Given WI_PR→PR_COMMIT→COMMIT_PATH→PATH_COMPONENT, when inspected, then a VERIFIED connection path exposes four supporting hops, direct/source/derived labels and both boundaries, without claiming business correctness. | BASE WI-1001→PR-51→a→path→src/payments |
| ECL-AC-309 | Given a supported COMPLETE WI_PR lookup on a merged PR with no link, when evaluated, then that in-boundary hop is MISSING, even if its commit has an independent WI_COMMIT link. | BASE PR-52 |
| ECL-AC-310 | Given WI_COMMIT evidence with COMPLETE empty WI_PR lookup, when full-chain status derives, then the shorter path remains visible and the full normative PR segment is unresolved/MISSING; no PR is manufactured. | DIRECT_ONLY variant |
| ECL-AC-311 | Given a WI linked to a PR with COMPLETE empty commit membership, when inspected, then the commit hop is MISSING, full chain PARTIAL and no code implementation or component denominator is invented. | BASE PR-54 |
| ECL-AC-312 | Given an independently enumerated WI with complete implementation lookups and no links, when evaluated, then implementation is MISSING within that query, not proof the requirement is unimplemented everywhere. | BASE WI-1003 |
| ECL-AC-313 | Given an observed commit with COMPLETE empty applicable intent lookups, when inspected, then it exposes a MISSING intent gap and remains in the Git denominator. | NO_INTENT variant |
| ECL-AC-314 | Given exact duplicate links or two PR routes reaching the same commit/change, when counted, then unique artifacts/occurrences count once and observation provenance remains auditable. | DUPLICATES variant |
| ECL-AC-315 | Given same-key contradictory observations, when normalized, then they are quarantined deterministically with PARTIAL affected lookup and cannot inflate coverage. | CONFLICT variant, reversed input order |
| ECL-AC-316 | Given self/cyclic/reverse relations, when paths derive, then unsupported observations cannot become authoritative links and traversal terminates with bounded diagnostics. | CYCLE variant |
| ECL-AC-317 | Given malformed IDs, absolute/traversal paths, invalid timestamps or mismatched endpoint kinds, when normalized, then required invalid records are isolated with safe diagnostic and affected scope PARTIAL. | MALFORMED variants |
| ECL-AC-318 | Given an unsupported link type, when normalized, then it does not contribute any path/count, and the reason/capability remains explicit rather than silently mapping it to a known type. | UNSUPPORTED_TYPE variant |
| ECL-AC-319 | Given absent optional title/timestamps or unrecognized type/state label, when normalized, then valid required evidence survives; UNKNOWN/OTHER is explicit and missing optional fields do not alone make lookup partial. | OPTIONAL variant |
| ECL-AC-320 | Given a supported population/relationship lookup interrupted after valid observations, when derived, then positive paths survive, population coverage is PARTIAL, and absent links are not labelled MISSING. | PARTIAL variant |
| ECL-AC-321 | Given acquisition FAILED before useful evidence, when inspected, then output is UNAVAILABLE with FAILED collection and no zero-coverage/missing negative claim. Given later failure, useful evidence survives as PARTIAL. | FAILED and LATE_FAILURE variants |
| ECL-AC-322 | Given unsupported/unknown relationship capability, when evaluated, then its gaps/affected coverage are UNAVAILABLE with explanation, not empty COMPLETE or MISSING. | CAPABILITY variant |
| ECL-AC-323 | Given identical normalized evidence in different input orders, when derivation repeats, then canonical refs/paths/gaps/counts/statuses match byte-for-byte after deterministic serialization. | BASE permutation cases |
| ECL-AC-324 | Given different repository/instance scopes with equal native IDs, when joining, then identities do not collide; full exact Git revisions and explicit identity maps are required, never abbreviated/text/author matching. | SCOPES variant |
| ECL-AC-325 | Given provider commits outside Git revision reachability or incompatible query/component-depth/alias maps, when joined, then refs remain explicit with UNAVAILABLE downstream evidence and cannot change eligible populations or silently compare ratios. | BOUNDARY variant |
| ECL-AC-326 | Given the accepted BASE population, when the four metrics derive, then merged-PR coverage=3/4, commit coverage=4/4, payment changes=2/2, tests=1/1, catalog=1/1, WI implementation=2/3; every ratio carries source/boundary/completeness and no quality judgement. | BASE expected manifest |
| ECL-AC-327 | Given zero population or linked-only WI discovery without independent enumeration, when coverage derives, then relevant ratios are null/UNAVAILABLE, not 0%; any known counts remain separately identified. | EMPTY and LINKED_ONLY variants |
| ECL-AC-328 | Given a v0.1 Git-only report, when v3 validation/import/export is added, then existing fields, loading, departure, scoring and classification remain unchanged and traceability remains absent. | Existing browser v1 regression and exact export/import round trip |
| ECL-AC-329 | Given a v0.2 report with review evidence, when imported/exported and when review coexists with v3 traceability, then qualification, units, shares, HHI, provenance/completeness and fields remain unchanged. | Existing v2 regression plus v3 combined-envelope round trip |
| ECL-AC-330 | Given fixture data, when used in docs/tests/CI, then it is labelled SYNTHETIC with project-owned artificial IDs/full hashes; no claim of live Azure evidence or private/employer/defence/customer data. | Fixture-origin audit + synthetic provider manifest check |
| ECL-AC-331 | Given synthetic secret sentinels, raw response/exception fields and confidential metadata, when serialized/imported/errored, then only allowlisted fields/safe aliases remain; no token/header/body/transport setting/local path/unapproved title is emitted or accepted as provenance. | Python and browser allowlist/privacy negative fixtures |
| ECL-AC-332 | Given Services and Server deployment profiles with differing versions/collection URLs/capabilities/continuation mechanisms, when a future adapter normalizes, then core refs stay provider-neutral and unsupported relationships remain unavailable. | Adapter-profile fixtures; later MANUAL live compatibility matrix |
| ECL-AC-333 | Given evidence timestamps, when reports derive, then collection/query/UTC time-field and fixed-revision differences are retained; changing titles/timing/author text cannot create links. | Snapshot/version tests and no-inference negative cases |
| ECL-AC-334 | Given a PR-only changed-path observation without commits, when projected to components, then WI→PR→Component is an explicitly shorter chain and PR snapshot paths never enter commit-change coverage. | PR_PATH_ONLY variant |
| ECL-AC-335 | Given a valid full positive path inside a PARTIAL collection, when shown, then the path can be VERIFIED while collection/population coverage stay PARTIAL and other missing observations remain unknown. | POSITIVE_PARTIAL variant |
| ECL-AC-336 | Given the v3 traceability report contract, when a report is serialized/imported, then its additive section round-trips while existing Git/review fields remain unchanged and contradictory paths/counts are rejected. | v3 Python/browser round trips plus semantic negative fixtures |
| ECL-AC-337 | Given future artifact views, when inspected, then path sources, gaps and descriptive metrics remain separate from people evidence and no combined/individual traceability score is emitted. | Future presenter review/manual UI gate |
| ECL-AC-338 | Given a future v0.4 kind/link, when extension is designed, then typed/versioned extension can coexist without reinterpreting existing trace links; v0.3 rejects unsupported kinds until explicitly accepted. | Future extension design/schema contract tests |
| ECL-AC-339 | Given known distinct population N and full-chain-supported count F, when summary derives, then unavailable/unsupported/incompatible or N=0 yields UNAVAILABLE; any incomplete required lookup yields PARTIAL; supported COMPLETE N>0/F=0 yields MISSING; 0<F<N yields PARTIAL; F=N yields VERIFIED. Individual short paths keep PARTIAL and their hop gap states; no alternate-route count changes F. | Cardinality/status boundary fixtures, including all-missing and positive-in-partial cases |
| ECL-AC-340 | Given any report version, when traceability evidence is present, then `report_version` is `3.0`, `model` remains `experimental-v0.1`, and top-level `traceability_evidence` has schema version `1.0`; v1/v2 remain valid without it, and v3 may omit it. | Python/browser envelope compatibility matrix |
| ECL-AC-341 | Given a serialized traceability section, when imported, then only declared artifact/link/status/reason/schema values and exact typed scoped references are accepted; unknown future values fail closed. | Unknown schema/artifact/link enum negative tests |
| ECL-AC-342 | Given normalized evidence and derived paths/links, when imported, then endpoint kinds/origins, ordered supports, unique canonical paths and normative hop order are validated; derived WI_COMPONENT requires a supporting path and cycles/repeated normative endpoints are rejected. | Python re-derivation and browser semantic/path fixtures |
| ECL-AC-343 | Given a serialized gap or artifact trace state, when imported, then MISSING requires supported COMPLETE scoped negative lookup evidence; VERIFIED requires all normative hops; unexplained MISSING/VERIFIED contradictions are rejected. | Qualified-lookup and status contradiction fixtures |
| ECL-AC-344 | Given serialized coverage metrics, when imported, then counts are nonnegative, numerator does not exceed denominator, positive denominators use the exact ratio, and zero/unavailable populations use null as specified. | Arithmetic, boundary, null and zero-denominator tests |
| ECL-AC-345 | Given collection, capability and trace states, when imported, then COMPLETE/PARTIAL/FAILED, SUPPORTED/UNSUPPORTED/UNKNOWN and VERIFIED/PARTIAL/MISSING/UNAVAILABLE remain independent; FAILED without usable evidence cannot imply MISSING. | Collection/capability/status combination fixtures |
| ECL-AC-346 | Given identical normalized BASE evidence with input collections permuted, when serialized twice, then canonical JSON is byte-identical with stable ordering of all public collections. | Exact-byte determinism and permutation tests |
| ECL-AC-347 | Given a report derived from synthetic BASE, when serialized and imported, then PR intent is 3/4, commit intent 4/4, work-item implementation 2/3, and payment/tests/catalog are 2/2, 1/1, 1/1. | Generated from `base_fixture()`; no copied oracle payload |
| ECL-AC-348 | Given v1 Git-only, v2 review, v3 traceability, v3 review+traceability, v3 PARTIAL and v3 FAILED reports, when browser validated/exported/imported, then compatible data survives and malformed/unknown future report versions fail. | Browser model/import/export compatibility matrix |
| ECL-AC-349 | Given a Python-canonical v3 report, when browser validated/imported/exported, then traceability is structurally identical; browser-valid JSON imported in Python reconstructs the same normalized result. | Python-browser-Python round trip |

## Project-owned synthetic fixture contract

Fixture namespace is `synthetic/ecl-traceability-demo`; project `demo-project`, repository `demo-system`; no actual enterprise tenant or external project. Display names below are artificial. Work-item identifiers are canonical `1001`/`1002`/`1003`; PR identifiers `51`–`54`; `WI-`/`PR-` are display labels. Commits a/b/c/d denote full 40-character SHA-1 hashes made of a/b/c/d respectively, not abbreviated IDs. All observations use a fixed UTC fixture timestamp, versioned normalization/identity map and a component directory depth of 2.

BASE boundary enumerates three work items independently, four merged PRs and four observed Git commits/changes; all required lookup operations are SUPPORTED and COMPLETE within this fixture boundary. Work-item data: WI-1001 STORY, “Add payment retry policy”, ACTIVE; WI-1002 BUG, “Fix synthetic catalog timeout”, CLOSED; WI-1003 REQUIREMENT, “Add synthetic inventory export”, OPEN. Titles are approved synthetic labels; no author, assignee, employee or reviewer dimension is needed.

| Observed artifact | Explicit direct observations | Changed paths / expected derivation |
| --- | --- | --- |
| WI-1001 | WI_PR to PR-51 and PR-54 | Via PR-51 reaches payment/test components; PR-54 commit hop missing |
| WI-1002 | WI_PR to PR-51 and PR-53; WI_COMMIT to c | Reaches payment/test/catalog; no inferred WI_PR to PR-52 |
| WI-1003 | COMPLETE empty WI_PR and WI_COMMIT/implementation lookups | MISSING observed implementation |
| PR-51 | PR_COMMIT to a and b | Two work items, two commits, unique PR unit |
| PR-52 | PR_COMMIT to c; COMPLETE empty WI_PR lookup | MISSING direct PR intent even though c has direct work-item evidence |
| PR-53 | PR_COMMIT to d | WI-1002 link observed |
| PR-54 | COMPLETE empty PR_COMMIT and PR_PATH lookups | WI links retained, no observed code; excluded from change population because no occurrence exists |
| a | COMMIT_PATH to `src/payments/retry.py` | DERIVED mapping to `src/payments` |
| b | COMMIT_PATH to `tests/payments/test_retry.py` | DERIVED mapping to `tests/payments` |
| c | COMMIT_PATH to `src/catalog/timeout.py` | DERIVED mapping to `src/catalog`; WI_COMMIT path, not full PR intent chain |
| d | COMMIT_PATH to `src/payments/timeout.py` | DERIVED mapping to `src/payments` |

BASE oracles: PR direct intent=3/4; commit intent=4/4; change intent per component payment=2/2, tests=1/1, catalog=1/1; work-item code implementation=2/3. PR-52 WI_PR and PR-54 PR_COMMIT are MISSING hops; WI-1003 has MISSING observed implementation. Short direct WI_COMMIT paths are useful and count for commit intent, while never claiming the full WI_PR chain. 100% commit intent therefore coexists with explicit PR/full-chain gaps. All metrics state SYNTHETIC, selected populations and COMPLETE collection; no metric is quality or performance.

## Variant manifest and expected failure boundaries

Each variant is a named transformation of BASE, not a second unlabelled provider dataset. A future fixture generator must emit inputs and exact oracles, including counts of rejected/unknown/excluded records. The offline provider now implements named immutable fixture transformations; none are live Azure data.

| Variant | Planned mutation / oracle |
| --- | --- |
| MULTIPATH | Add an additional path on a in `src/catalog`; separate occurrence joins correct component; one commit still counts once. |
| DIRECT_ONLY | Remove WI_PR routes for an otherwise directly linked WI/commit; retain valid shorter route, explicitly unresolved PR segment. |
| NO_INTENT | Remove WI-1002→c; complete intent lookups on c: commit metric 3/4 and catalog changes 0/1, MISSING observed intent, not bad quality. |
| DUPLICATES | Repeat link observations and add PR-53→a; retain distinct observations/routes without changing BASE metric counts. |
| CONFLICT | Same observation ID with conflicting endpoints; quarantine both ambiguous assertions, PARTIAL lookup, order-independent result. |
| CYCLE | Inject self/reverse/cyclic unsupported relations; reject authoritative contribution, bounded safe diagnostics, no endless path. |
| MALFORMED | Empty/scoped-wrong ID, invalid full hash, bad required time, path traversal, endpoint kind mismatch; isolate required invalid records and mark affected lookup partial. |
| UNSUPPORTED_TYPE | Add an arbitrary relation type; no fake normalization into WI_PR. |
| OPTIONAL | Remove approved title/optional dates and supply unknown type/state; keep links and completeness with explicit null/UNKNOWN. |
| PARTIAL / LATE_FAILURE | Stop a lookup after valid records; retain positives, mark incomplete coverage and no negative MISSING for uncollected links. |
| FAILED | No usable collection; UNAVAILABLE result/FAILED collection, not an empty successful set. |
| CAPABILITY | Remove WI_COMMIT support or set unknown PR_COMMIT; affected gaps/ratios UNAVAILABLE, never MISSING. |
| SCOPES | Duplicate native IDs in other instance/repo; keep isolated identities; no cross-scope inference. |
| BOUNDARY | Git revision excludes d, time/type queries exclude a work item, change component depth or alias map; explicit excluded/unavailable populations and no silent count inflation. |
| EMPTY / LINKED_ONLY | Empty independently enumerated populations: null ratios; link-discovered WI subset without enumeration: WI metric UNAVAILABLE. |
| PR_PATH_ONLY | WI→PR plus PR snapshot paths, no commit evidence/capability: short projection retained; no commit/change unit invented. |
| POSITIVE_PARTIAL | Keep a complete positive normative path while another lookup is interrupted; positive path VERIFIED and collection/coverage PARTIAL coexist. |
| PRIVACY / NO_INFERENCE | Inject clearly synthetic forbidden-field sentinels or matching message/branch/timing/author text without links; allowlisted outputs omit sentinels and create no relationships. |

## QA handoff, evidence classification and design-only regression gate

Planned runtime suites: domain normalization/references; typed derivation/status/coverage; fixture-provider completeness/error/capability; immutable v0.1/v0.2 join regression; later adapter profile/transport tests; separately gated future report/presenter tests. Tests do not need credentials or live projects. Private on-prem validation is not a public-repository fixture source. A suitable intentionally public Azure project can only be secondary MANUAL evidence after origin/privacy/capability review; lack of one does not block the offline design.

Design PR checks: stable unique Spec IDs and complete FR/NFR→AC→design→planned implementation/verification mapping; no `src/`, UI, CLI, test, packaging, auth or runtime schema modifications; independent specification review; all existing `unittest`, strict mypy, Node model/handler/Pages, syntax/static assets and wheel build checks. These checks show baseline compatibility and document integrity, not v0.3 runtime coverage.

Runtime statuses now follow the executed criterion mapping in `traceability.md`; later delivery remains ACCEPTED/PARTIAL and no live compatibility is VERIFIED. Live Server support stays MANUAL/unvalidated. QA exit: every criterion has synthetic observable oracles or a clearly deferred adapter/report/UI verification gate; no acceptance criterion was weakened to match existing code.

## Independent report review regression mapping

Existing criteria remain unchanged. ECL-AC-331/341/348/349 include the shared adversarial corpus in `tests/traceability_report_adversaries.py`: exact source identities, unresolved lookup boundaries, every string-bearing provenance/reference record field, recognizable credential markers, duplicate JSON fields and sanitized parser errors. ECL-AC-342/346 include shortcut support ordering, artifact ordering, independent collection permutations, multiple boundaries/diagnostics, Unicode code-point ordering and equivalent timestamp representations. ECL-AC-343/345 include diagnostic-induced lookup completeness, UNKNOWN and incompatible-scope lookup normalization. ECL-AC-341/349 include real Gregorian dates, ISO precision/offset bounds and microsecond boundary compatibility. The corrective QA implementation is `tests/test_traceability_reporting_review.py` and `ui/tests/model.test.js`; the historical report correction review remains a separate pending independent re-review record. The Azure closure reviews report interactions and does not claim an unperformed review of the whole historical report diff.

## Azure provider QA plan (recorded before development)

| ID | Observable acceptance | Planned evidence |
| --- | --- | --- |
| ECL-AC-350 | All four deployment profiles and compatible overrides construct collection-aware, encoded URLs using the selected version; incompatible overrides fail without fallback. | Profile and URL tests; live compatibility MANUAL |
| ECL-AC-351 | Azure-shaped project-owned BASE passes through provider, derive and report-v3 import/export with PR 3/4, commits 4/4, WI 2/3 and component changes 2/2,1/1,1/1. Independent lists retain unlinked artifacts. | Synthetic REST fixtures and oracle/round-trip tests |
| ECL-AC-352 | Exact scoped artifact identities and provider references yield only direct provider links; malformed/cross-scope identities and text never create links. REST paths retain provider origin; existing derive creates components. | Scoping/encoding/no-inference/normalization negatives |
| ECL-AC-353 | Paging, batching, duplicates, limits, failures and disabled operations preserve exact scoped capability/completeness; incomplete lookup never justifies MISSING. | Page/batch/zero/partial/failed/unsupported/status tests |
| ECL-AC-354 | Native config, private IDs, people fields, titles, PAT/header/cookie/body/exception sentinels do not escape normalized evidence, report or transport errors/repr. TLS remains verified and redirect/URL escapes fail. | Mocked transport and loopback integration; publication origin MANUAL |
| ECL-AC-355 | Equivalent 7.0/7.1/7.2 REST inputs normalize identically with deterministic ordering; complete regression checks and wheel pass. | Profile matrix/permutations/full Python and Node checks |

QA strategy: test positive associations, independent empty populations and absent hops; malformed required fields, missing batch members, foreign IDs/artifacts, repeated tokens, short continuation pages, exact-limit pages, offset changes and WI keyset progress; first/late failures and 401/403/404/405/429/5xx; strict JSON and secret-bearing exception/body/header inputs. An independent Code Reviewer is required by AGENTS.md; it does not prescribe a human reviewer. Developer verification is not approval. Live TLS/auth/API/deployment compatibility remains MANUAL until observed.

## Closure review corrective QA plan

No acceptance criterion is weakened or added by this closure. Independent post-merge findings AZ-R01–04 refine verification of existing contracts: AC315/353 require quarantine rather than representative selection for contradictory same-ID WI records; AC320/353 require preserving valid WIQL IDs around malformed/nonprogress refs; AC353 bounds both inline and fallback PR references; AC331/354 reject recognizable credential-shaped paths before normalized evidence. Planned synthetic regressions are in `tests/test_azure_closure_review.py`; exact review/verification outcomes remain in the closure and Azure review records. Full regression must pass and corrections must be independently re-reviewed before approval. Live compatibility remains MANUAL.

## Local Azure connection QA plan (before development)

| ID | Observable criterion | Planned verification |
| --- | --- | --- |
| ECL-AC-357 | A valid Server/Services TOML file maps exact profile, approved identities and boundaries into the existing pipeline and emits an accepted report-v3 traceability section. | All four profiles; injected synthetic REST fixture pipeline and traceability round-trip validator; existing Git CLI regressions. |
| ECL-AC-358 | Missing publication approval, unknown/duplicate keys, wrong types, invalid boundaries/maps, oversize files, secret fields and HTTP profiles fail before acquisition with fixed diagnostics. | Negative parser/CLI tests, secret and private-path sentinels. |
| ECL-AC-359 | Interactive PAT is hidden and runtime-only; anonymous mode does not prompt; noninteractive PAT and interrupted/empty prompts fail safely without acquiring. | Mock terminal/getpass, warning fallback, EOF and interrupt checks. |
| ECL-AC-360 | COMPLETE/PARTIAL/FAILED reports remain valid and map to exit 0/3/4; fatal errors produce no JSON and exit 2 without leaking raw exception text. | Synthetic positive, late failure and first failure, report round trip, stderr sentinel assertions. |

Live deployment compatibility remains MANUAL. Developer must preserve all prior report/provider/CLI tests. Independent review and green CI remain merge gates.
