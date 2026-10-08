# v0.3 product specification: traceability evidence

**Status: ACCEPTED product contract; offline core and additive report v3 serialization implemented.** Runtime verification is scoped by criterion in `traceability.md`; The first Azure acquisition library is implemented with synthetic validation; live deployment compatibility and traceability presentation remain separate gates. Product Owner handoffs and regression evidence are recorded in the design/verification records.

## Problem, value and change boundary

Git authorship (v0.1) and PR review interaction (v0.2) describe historical activity. They do not explain why a change happened. v0.3 will expose observed paths between engineering intent and implementation so a reader can inspect connected, fragmented, missing or unavailable evidence. The primary dimension is the artifact/component, never an employee.

The initial normative chain is **Work Item → Pull Request → Commit → Changed Path → Component**. Shorter observed paths are also useful: Work Item → PR → Component, Work Item → Commit → Component, PR → Commit → Component, Commit → Component. A short path does not satisfy the full-chain contract and must expose skipped/missing/unavailable hops; no relationship is fabricated to fill the gap.

The original specification PR delivered specifications, architecture, evidence-model and verification design only. In that original PR the Developer materialized documents and validated the unchanged baseline, stopping before product implementation: no domain classes, executable fixtures, provider client, runtime logic, schema changes, UI, CLI, authentication or Azure DevOps network access is added.

## Accepted eventual scope and non-goals

Azure DevOps Services and Azure DevOps Server/on-premises are the first planned concrete provider family. Work-item/PR/commit relationships must be provider-recorded; Git commit changes and deterministic component mapping complete the chain. Core concepts remain provider-independent. The first implementation operated offline on explicitly SYNTHETIC project-owned evidence. The separately authorized Azure acquisition increment below adds a read-only library provider; live compatibility remains unvalidated.

Initial queries inspect work items affecting a component, PRs and commits associated with a work item, affected components, PRs/commits without observed intent, work items without observed implementation, and exactly where a chain stops. Merged PRs only contribute to PR coverage; open/abandoned PR references may be retained as unresolved contextual references but are excluded from that denominator.

Non-goals: individual ranking/compliance/performance metrics; inferred ticket matches from messages, branches, author identity, timing or semantic similarity; LLMs, embeddings, vector/graph databases; Jira/GitHub Issues adapters; work-item parent/child/related hierarchies; comments, descriptions, attachments, profiles and arbitrary custom fields; authentication implementation; v0.4 requirements/ADR/ICD/test/verification-document ingestion; v0.5 handover assessment. No coverage percentage judges process quality or proves a requirement was implemented correctly.

## Functional requirements

| ID | Observable eventual requirement |
| --- | --- |
| ECL-FR-301 | Represent minimum work-item evidence independently of provider DTOs: scoped identifier, normalized type/state, optional approved title/timestamps, and provenance. |
| ECL-FR-302 | Accept a planned Azure DevOps traceability adapter for Services and Server, with declared supported/unsupported relationship capabilities rather than assuming cloud equivalence. |
| ECL-FR-303 | Retain acquisition/source provenance for every work item and relationship, including safe project/repository scope, boundary and completeness. |
| ECL-FR-304 | Represent observed direct links with typed endpoints, observation basis and source evidence; reject unsupported claims as non-authoritative diagnostics. |
| ECL-FR-305 | Derive trace paths only through existing valid observed links and documented path-to-component mapping; retain the ordered supporting references and derivation rule. |
| ECL-FR-306 | Represent provider-observed Work Item → PR links, including one-to-many and many-to-one associations without multiplying artifact counts. |
| ECL-FR-307 | Represent direct Work Item → Commit links where provider evidence exists, separately from a path derived through a PR. |
| ECL-FR-308 | Represent provider-observed PR → Commit membership without claiming all PR commits are reachable at the selected Git revision. |
| ECL-FR-309 | Retain observed Commit → Changed Path evidence for the exact repository and commit revision. |
| ECL-FR-310 | Map changed paths through the existing component strategy, recording its configuration and mapping one path to its selected component. |
| ECL-FR-311 | Expose a complete normative trace chain and its support independently from broader collection completeness. |
| ECL-FR-312 | Preserve shorter paths and explain each unresolved expected hop; a PR-level changed-path shortcut never invents a commit. |
| ECL-FR-313 | Label an absent relationship MISSING only when the relevant artifact and relationship lookup are supported, complete and within the selected boundary. |
| ECL-FR-314 | Label evidence UNAVAILABLE when a required capability, usable source, compatible scope or population is unavailable; expose the reason. |
| ECL-FR-315 | Propagate incomplete enumeration/enrichment, truncation, malformed records or interrupted lookup as PARTIAL for the affected scope, retaining valid positive evidence. |
| ECL-FR-316 | Produce identical paths, gaps, counts and ordering from identical normalized input, identity mappings, boundaries and configuration. |
| ECL-FR-317 | Normalize exact duplicate links once while preserving distinct observations; isolate contradictory duplicates without inflating coverage. |
| ECL-FR-318 | Reject or isolate malformed required IDs/endpoints/links deterministically with safe diagnostics; missing optional fields do not erase valid links. |
| ECL-FR-319 | Display source-specific collection times, query/time/revision scopes and completeness; prohibit silent joins or comparisons across incompatible boundaries. |
| ECL-FR-320 | Preserve v0.1 scoring/reports and v0.2 review semantics/reports unchanged; absence of traceability evidence remains valid and means unavailable. |
| ECL-FR-321 | Use minimum approved data, omit confidential titles/identities by default, and prevent sensitive content from crossing export/error/public-artifact boundaries. |
| ECL-FR-322 | Distinguish FAILED acquisition from valid empty evidence; retain useful validated evidence with PARTIAL on interruption and never report an unperformed lookup as MISSING. |
| ECL-FR-323 | Permit configurable Server base/collection/project/repository and API/capability profiles without cloud URLs, credentials or network assumptions in core values. |
| ECL-FR-324 | Define and later validate a project-owned SYNTHETIC fixture containing complete/partial/missing/unavailable/failure, multicomponent, duplicate and malformed cases. |
| ECL-FR-325 | Distinguish DIRECT_PROVIDER_LINK, DIRECT_SOURCE_LINK (e.g. observed Git changes) and DERIVED_LINK; derived Work Item → Component never claims direct provider assertion. |
| ECL-FR-326 | Report coverage as explicit distinct numerator/denominator with boundary, provider/source, completeness, excluded/unknown populations and unavailable zero-denominator ratios. |
| ECL-FR-327 | Show artifact-oriented path/gap explanations and separate coverage dimensions, without a single opaque traceability score or people ranking. |
| ECL-FR-328 | Retain cycle diagnostics and terminate path derivation safely; cyclic/unsupported relationships cannot create evidence or repeated traversal counts. |
| ECL-FR-329 | Serialize a derived traceability report through an intentional public contract containing normalized evidence and its auditable derived result, not implementation-specific object dumps. |
| ECL-FR-330 | Import traceability reports into validated provider-neutral values and reject contradictions between normalized evidence and serialized paths, gaps, artifact states or metrics. |
| ECL-FR-331 | Add `traceability_evidence` under envelope `report_version` 3.0 without renaming or removing Git or review fields. |
| ECL-FR-332 | Preserve explicit artifact kinds/scopes, typed link endpoints, origins, ordered support, collection/capability/trace states and derivation/configuration identity across round trips. |
| ECL-FR-333 | Serialize coverage numerator, denominator, ratio/null semantics, status, boundary/source, unknown and excluded counts; reject inconsistent arithmetic. |
| ECL-FR-334 | Validate and export/import v3 traceability reports in the static browser while retaining v1/v2 compatibility and rejecting unsupported future types/versions. |
| ECL-FR-335 | Provide deterministic canonical traceability serialization and a project-owned synthetic report derived from the accepted BASE fixture. |

## Status contract: three independent axes

Collection status reuses **COMPLETE / PARTIAL / FAILED** from the established evidence vocabulary; capability is **SUPPORTED / UNSUPPORTED / UNKNOWN** per relationship kind and scoped lookup. Trace/path status is **VERIFIED / PARTIAL / MISSING / UNAVAILABLE**. Governance verification status in the traceability matrix is a fourth, separate concept: this design does not mark runtime requirements VERIFIED.

- **VERIFIED trace path:** every required hop exists with valid provenance and compatible artifact scope. It verifies connection evidence only, not business correctness or understanding. It may coexist with a PARTIAL collection; the collection badge must remain visible.
- **MISSING hop:** a supported, complete lookup found no relationship for an in-boundary endpoint. Example: a fully enumerated merged PR has no observed work-item link. It says nothing about work items outside the selected boundary.
- **UNAVAILABLE hop:** unsupported/unknown capability, failed lookup with no usable evidence, incompatible boundaries, missing source population or an unresolvable excluded reference; state the cause. Zero observed population yields no ratio, not 0%.
- **PARTIAL trace:** some expected hop is incomplete/malformed or only a short chain is evidenced. Known complete absence on a hop remains a MISSING gap; unavailable hops remain UNAVAILABLE gaps. Positive supported portions remain visible.

A component groups individual path/gap states; it never hides them behind a single score. Define `N` as distinct eligible artifacts in the selected summary population and `F` as those with at least one full supported normative chain (not the number of alternate paths). A component summary uses mapped commit/path occurrences as its population; artifact-specific summaries identify their population explicitly. Apply these rules in order:

| Condition | Aggregate summary |
| --- | --- |
| Required source/population/capability or compatible boundary is unavailable, or N=0 | UNAVAILABLE with reason; no zero-ratio claim |
| N>0 and any required lookup/population is incomplete/malformed/interrupted | PARTIAL, even if all currently observed artifacts have positive paths |
| N>0, required lookups are supported and COMPLETE, F=0 | MISSING full-chain evidence in this boundary |
| Supported COMPLETE population, 0<F<N | PARTIAL, with individual MISSING gaps listed |
| Supported COMPLETE population, F=N | VERIFIED connection evidence only |

Individual shorter paths remain PARTIAL full-chain results with per-hop gaps even when a complete aggregate population with F=0 is summarized MISSING. Direct WI_COMMIT paths may satisfy intent metrics while full normative PR chains are missing; those two dimensions are never conflated. A positive full path can remain VERIFIED during incomplete collection; the aggregate stays PARTIAL or UNAVAILABLE under the rules above. The independent collection state is always displayed. This cardinality contract resolves independent design-review R1 without changing scope.

## Coverage populations and observable metrics

All ratios count DISTINCT scoped artifacts. A valid observed positive link/path is usable during partial acquisition; a noncovered artifact is not automatically MISSING. Report unknown/excluded counts and per-relationship lookup states. Ratios from an incomplete population are labelled observed-population PARTIAL, not extrapolated to repository history. An unsupported required capability, incompatible joined scope, or zero denominator makes the ratio unavailable (null), with counts retained only where independently established.

| Dimension | Numerator | Denominator | Required relation scope |
| --- | --- | --- | --- |
| Merged-PR intent coverage | Observed merged PRs with ≥1 valid direct work-item link to a resolved in-boundary work item | Distinct merged PRs enumerated in selected repository/query boundary | Work items and WI→PR lookups for each enumerated PR; no guessed link |
| Commit intent coverage | Observed commits with a resolved WI→Commit link or compatible WI→PR→Commit path | Distinct commits in the selected Git revision/time/filter boundary | Complete identities and compatible WI/PR/commit membership scope |
| Component-change intent coverage | Distinct `(repository, commit, changed path)` occurrences mapped to that component with a supported work-item path | Distinct observed occurrences mapped to that component under the same Git/filter/component configuration | Commit intent plus observed changes; this is neither lines nor number of contributors |
| Work-item implementation coverage | Enumerated work items reaching ≥1 observed commit/path/component by a supported path | Distinct work items explicitly enumerated in selected project/work-item query boundary | WI→PR/Commit and implementation lookups; a work item linked only to a PR is not yet observed code implementation |

The work-item query must enumerate the chosen work-item population independently of linked PRs; otherwise unlinked work items cannot be counted or labelled missing. Boundary includes type/state filters if selected, explicit half-open UTC time windows `[start,end)` with the field used, and the repository/revision set. Cross-boundary links remain explainable references but cannot inflate numerator or redefine denominator. Overlapping PRs sharing one commit count once in commit/change metrics. Metrics are descriptive evidence coverage; no strong/weak quality thresholds are adopted in initial v0.3.

## Non-functional requirements

| ID | Requirement |
| --- | --- |
| ECL-NFR-301 | Core immutable evidence and derivation shall be independent of provider SDKs, REST DTOs, Azure URL/auth types and network clients. |
| ECL-NFR-302 | Normalization and derivation shall be deterministic with explicit identity rules, sorted output, deduplication, bounded traversal and cycle handling. |
| ECL-NFR-303 | Every retained record/link/path shall have auditable sanitized source/boundary provenance; derivations retain their supporting evidence references. |
| ECL-NFR-304 | Never persist or emit PATs, auth headers, bearer tokens, passwords, cookies, secret-bearing URLs, raw responses or local temporary paths. |
| ECL-NFR-305 | Do not retain unnecessary personal fields, comments, attachments/custom fields or confidential text; default persisted/exported views use approved labels or opaque aliases. |
| ECL-NFR-306 | Errors shall contain stable sanitized categories and safe scope aliases only; raw exception/provider bodies and network configuration remain adapter-private. |
| ECL-NFR-307 | v0.1/v0.2 input validity, scoring, reviews and optional-section absence shall remain unchanged; new report evidence must be additive and versioned. |
| ECL-NFR-308 | Reproducibility shall identify input snapshots, query/revision/time bounds, identity mapping, component strategy/filter configuration, normalization/derivation versions and collection time. |
| ECL-NFR-309 | Schema evolution shall use typed extensible references/links and explicit versions without adding v0.4 runtime concepts in v0.3 or reinterpreting old fields. |
| ECL-NFR-310 | Partial/failed/unsupported relationship acquisition shall never be interpreted as a complete empty population or complete negative evidence. |
| ECL-NFR-311 | Services/Server API versions, capabilities, pagination and deployment configuration shall be explicit adapter profiles; no universal version compatibility claim. |
| ECL-NFR-312 | Core derivation shall run offline on normalized evidence with no hidden network calls, authentication or LLM/inference dependency. |
| ECL-NFR-313 | Public documentation, fixtures, CI and validation shall use only SYNTHETIC, intentionally public or project-owned approved public data, never employer/NATO/NCIA/defence/customer/private-project evidence. |
| ECL-NFR-314 | Repeated serialization of the same normalized result shall produce byte-identical canonical traceability JSON with stable ordering and no acquisition-order dependence. |
| ECL-NFR-315 | Import validation shall enforce the same typed path, link, gap, support, status and coverage semantics as offline derivation; unknown future values fail closed. |
| ECL-NFR-316 | Serialized traceability shall use explicit field allowlists and safe normalized provenance; it shall not expose provider DTOs, credentials, transport settings, local paths or unapproved private labels. |
| ECL-NFR-317 | Python and browser validation/export/import shall preserve accepted v3 traceability evidence and reject the same unsupported schema/type categories. |

## Privacy and future presentation contract

References must be scoped and non-secret. Adapter-private native project/repository identifiers and URLs may be needed transiently to acquire evidence, but default persisted/shared provenance uses approved public scopes or stable opaque aliases with a mapping fingerprint; reverse mappings and confidential titles are not exported. Work-item title is optional, disabled for private content unless explicitly approved, and never needed for joins. Creation/change/closure timestamps are optional context, not causal links; choose only useful ones explicitly. No individual identities are introduced by v0.3; existing v0.1/v0.2 identity fields are untouched.

An eventual artifact view shows component, observed work items/PRs/commit/path references, direct/derived labels, each unresolved hop and reason, raw distinct coverage counts and both source boundaries. No tab, controls, network flow or runtime report change is created here. UI layout is a future Product Owner/Architect gate; these content semantics are already normative.

## Handoff and remaining delivery gates

Product Owner exit: value, scope, non-goals, populations and observable outcomes are explicit. Architecture must resolve identity/join ownership, typed paths and capability/completeness evidence before QA/Developer work. QA defines cases in `acceptance-criteria.md`; the separately authorized first runtime slice is offline only. Runtime work requires separate authorization; the first offline slice was explicitly authorized after specification PR #17 merged.

## First Azure DevOps acquisition increment (Product Owner)

ECL-FR-302/323 remain the provider boundary; the following refines its first live-capable implementation without changing offline status/coverage rules.

| ID | Requirement |
| --- | --- |
| ECL-FR-336 | An explicit immutable deployment profile selects Server current/7.2, Server 2022.1/7.1, Server 2022/7.0 or Services/7.2; a compatible explicit override never triggers automatic downgrade. |
| ECL-FR-337 | Read-only acquisition independently enumerates completed repository PRs, all project work-item IDs and commit ancestry at an explicit immutable Git revision. It obtains provider-declared WI_PR, PR_COMMIT and explicit WI_COMMIT artifacts; optional commit changes feed existing derivation. |
| ECL-FR-338 | Every exported scope and native numeric artifact identity uses an explicitly approved alias mapping. Native addresses, names, IDs, credentials and DTOs remain acquisition-private. Titles stay disabled. Exact project/repository identities qualify artifact links; display names/text never establish links. |
| ECL-FR-339 | Endpoint-specific paging and deterministic work-item batches have finite bounds; interrupted enumeration retains positive evidence with partial affected lookups. Unsupported, unknown, failed and complete-empty evidence remain distinguishable. |
| ECL-NFR-318 | Stdlib-only transport verifies TLS, bounds time/response bytes, strictly decodes JSON, blocks redirects and credential-bearing URLs, persists no cookies, and sanitizes failures. Optional PAT is supplied only at runtime. Plain HTTP is restricted to explicit loopback test mode. |

Scope: library provider and synthetic validation, no connection UI/CLI, OAuth, NTLM, Kerberos, writes, releases or people analytics. Live Server compatibility requires a separate dedicated non-sensitive environment; synthetic success cannot certify it. The caller approves scope, artifact aliases and repository paths for publication.

## Local Azure connection increment (Product Owner)

Authorized after merged closure PR #21. This increment supersedes the prior library-only exclusion of CLI acquisition; all provider/report privacy and completeness semantics remain normative.

| ID | Requirement |
| --- | --- |
| ECL-FR-340 | A local CLI acquires Azure traceability using an explicit non-secret TOML connection file containing deployment/scope, exact revision, approved aliases/mapping, snapshot, timezone-aware collection instant and component depth. Existing Git commands remain compatible. |
| ECL-FR-341 | Require explicit approval that exported aliases, commit hashes and repository-relative paths may be published before acquisition. Reject unknown/malformed configuration before network activity; never infer public aliases from native identities. |
| ECL-FR-342 | PAT authentication uses a hidden interactive terminal prompt only; no PAT option, environment-variable lookup or persisted credential. Explicit anonymous mode supports non-interactive execution. Non-interactive PAT invocation fails without network access. |
| ECL-FR-343 | Emit standalone report-v3 traceability-section JSON (not a Git report envelope) to stdout with acquisition completeness preserved. Return 0 for COMPLETE, 3 for PARTIAL, 4 for FAILED, and 2 for configuration/authentication/processing errors. Diagnostics are fixed sanitized categories on stderr, with no private config/path or credential values. |
| ECL-NFR-319 | Connection parsing is bounded and strict, rejects duplicate/unknown fields and credential-shaped fields, exposes no HTTP/TLS bypass, and never echoes configuration contents or terminal secrets. |

Non-goals: explorer/UI integration, credential storage, name resolution, live compatibility certification, new scoring/schema/derivation, OAuth/NTLM/Kerberos, version bump or release.

## Traceability Explorer presentation increment (Product Owner)

User authorizes completing and merging this increment after independent review and CI. Existing FR327/334 and privacy/status semantics remain normative. No acquisition, auth, scoring or report schema change.

| ID | Requirement |
| --- | --- |
| ECL-FR-344 | A Traceability view renders validated v3 report evidence: collection status separate from path/artifact status, raw distinct coverage counts with null/unavailable handling and unknown/excluded counts, scoped boundaries, artifacts, ordered paths/hop origins/supports and each gap reason/direction. VERIFIED means observed connection evidence only. |
| ECL-FR-345 | Users can filter paths by component, trace status and artifact text, inspect supporting evidence, and open a clearly synthetic sample. Filters affect presentation only, preserve totals/evidence and reset when a new report loads. Legacy reports show unavailable rather than fabricated zero coverage. |
| ECL-NFR-320 | Escape displayed artifact/provenance text; never construct provider URLs from aliases. No network acquisition, browser persistence or new credentials; validated import/export keeps the underlying report unchanged. Controls have accessible labels and empty-state feedback; long references wrap. |

Non-goals: Azure explorer connection integration, standalone-section envelope fabrication, live compatibility certification, v0.4, release/tag/version bump.
