# v0.4: requirements, test and architecture evidence

Status: ACCEPTED intended behavior after Independent Code Reviewer APPROVE; no v0.4 runtime is implemented by this specification PR.

## Problem and value

v0.3 exposes observed work-item/code paths but cannot answer which approved requirements have declared implementation, test or architecture evidence. v0.4 adds auditable explicit associations and bounded verification observations. It describes evidence availability and observed outcomes, never proves business correctness or employee knowledge.

First implementation scope is offline, provider-neutral normalized evidence and synthetic verification. Acquisition/document parsing, new authentication and presentation/export rollout are later increments against this same product contract. v0.5 handover/readiness assessment remains separate.

## Functional requirements

| ID | Observable requirement |
| --- | --- |
| ECL-FR-401 | Represent Requirement, ArchitectureDocument (kind ADR or ICD), Test and VerificationEvidence with explicit artifact kind, approved scope/identifier and immutable declared artifact version. Equal display names across kinds/scopes/versions never establish equality. |
| ECL-FR-402 | Accept only declared typed associations: REQUIREMENT_WORK_ITEM, DOCUMENT_REQUIREMENT, DOCUMENT_COMPONENT, TEST_REQUIREMENT and VERIFICATION_TEST. A document's presence, title/text, name, path similarity, timestamps or test name never infer a link. |
| ECL-FR-403 | Preserve v0.3 artifact references as references into an explicitly identified immutable evidence snapshot. A requirement may have a declared WI association without a complete v0.3 code path; the latter remains independently PARTIAL/MISSING/UNAVAILABLE. |
| ECL-FR-404 | Requirement implementation evidence is an explicit REQUIREMENT_WORK_ITEM association followed by an existing valid WI-to-component path in the referenced v0.3 snapshot. Show every supporting hop and its own trace status. Direct WI_COMMIT and PR_PATH-only shorter paths retain their existing meanings. Do not call association alone implementation evidence. |
| ECL-FR-405 | A test association describes declared coverage of a requirement, not successful execution. A verification observation declares one test version, one target source revision/snapshot, timestamp and outcome PASS/FAIL/SKIPPED/UNKNOWN; optional execution-group alias is approved and non-secret. No runtime/provider payload or arbitrary test log is required. |
| ECL-FR-406 | Observations match only exact declared test version and target snapshot/revision. Missing version/target qualification cannot establish a current PASS. Retain contradictory same-observation identities as scoped conflict diagnostics; do not select PASS or the latest timestamp as truth. Distinct qualified runs may legitimately disagree and all remain visible. |
| ECL-FR-407 | Show independent lookup/population capability and completeness using SUPPORTED/UNSUPPORTED/UNKNOWN and COMPLETE/PARTIAL/FAILED. Positive evidence survives partial collection. MISSING requires complete supported scoped lookup; unavailable enumeration cannot imply absence. |
| ECL-FR-408 | Expose separate raw-count dimensions: requirement implementation linkage (eligible requirements with a qualified code path / independently selected requirements); declared requirement test linkage (requirements with an explicit test association / selected requirements); architecture requirement linkage (requirements with an explicit ADR/ICD association / selected requirements); qualified executed tests (selected tests with at least one exact-version/target PASS or FAIL observation / independently selected tests). Every unit counts once per dimension, even with multiple routes/runs. |
| ECL-FR-409 | Metrics retain numerator/denominator, unknown/excluded counts, scoped boundaries, capability/completeness and explanations. Null denotes unavailable or zero denominator; zero is a measured available fraction. Positive numerators are retained under incomplete evidence, but absence never becomes a verified zero through unavailable lookup. Pass/fail/skipped/unknown run counts are separate observations, never a success rate or opaque readiness score. |
| ECL-FR-410 | Explain selected requirement/test/document artifacts, explicit associations, derived code paths, unresolved segments, conflicts and verification qualification/outcomes using safe references and provenance. Evidence connection verification never means the requirement is correct or sufficiently tested. |
| ECL-FR-411 | The same normalized evidence, versions, snapshot joins and boundaries yields identical derived explanations, distinct counts and canonical ordering. Semantic supporting-hop order is retained. |
| ECL-FR-412 | Any later serialization/import/presentation rollout uses a deliberate new versioned extension. Existing v1/v2/v3 reports and v0.3 typed/link semantics remain unchanged; existing consumers continue rejecting unsupported future kinds/versions. |

## Nonfunctional requirements

| ID | Requirement |
| --- | --- |
| ECL-NFR-401 | Keep native/private document names, reverse mappings, raw document/test content, logs, credentials, local paths and network configuration outside public evidence. Only source-approved aliases and bounded allowlisted metadata may be published; syntax cannot establish publication rights. |
| ECL-NFR-402 | Fixed sanitized error categories never echo malformed input, source content or credentials. Use project-owned synthetic fixtures only for automated provider examples. |
| ECL-NFR-403 | Finite collection/relationship/observation/path limits and explicit typed acyclic path rules prevent arbitrary recursive graph traversal. Limit exhaustion preserves scoped partial positives. |
| ECL-NFR-404 | Offline derivation performs no network/auth/LLM/embedding inference, mutates no prior evidence and adds no people score or ranking. |
| ECL-NFR-405 | Requirement → acceptance → design → implementation → verification → independent review remains traceable; ACCEPTED design and synthetic automation do not certify a real deployment. |
| ECL-NFR-406 | Verification observations are historical declared outcomes, not a live execution claim. Reproducibility retains artifact versions, selected populations, target snapshots, source boundaries, mapping and rule versions. |

Non-goals: requirement/document NLP ingestion, inferred matching, test execution/orchestration, signing/certification, business correctness, architectural quality scoring, approval automation, live Azure/test-system adapters, v0.5 handover scoring, package/release change in this design PR.

## Authorized offline implementation and demo increment

The user requested a working v0.4 demo. Implement the first offline core plus an isolated synthetic presentation artifact, with no changes to existing Git envelope versions or generic report import.

| ID | Requirement |
| --- | --- |
| ECL-FR-413 | Provide a clearly SYNTHETIC v0.4 demo with BASE, partial collection, stale target, conflicting observation and empty scenarios. Show original evidence identities/versions/snapshot, four coverage dimensions, separate historical outcomes, requirement code-chain evidence and gap/qualification explanations. Scenario choice changes only demo data, not the currently loaded Git report. |
| ECL-FR-414 | Export the selected demo using its explicit v0.4-demo-1 artifact contract; do not present it as a browser-importable v1/v2/v3 Git report or claim it was acquired from a real source. |

## Product experience increment

FR415–420 are reserved by a separate unfinished portable-report branch and are not implemented/claimed here. No prior IDs are renumbered.

| ID | Observable requirement |
| --- | --- |
| ECL-FR-421 | Organize the first-time experience around Overview, Continuity, Traceability and Reviews & Verification; component-first exploration and secondary historical people/scenario details replace eight competing primary tabs. |
| ECL-FR-422 | Default to a clearly SYNTHETIC coherent Atlas Commerce showcase; offer the unchanged public eShop validation sample separately. Explicit source switching replaces the displayed report without mutating prior reports; imports never silently acquire showcase facts. |
| ECL-FR-423 | Bundle meaningful review source events spanning merged PRs/components/authors/reviewers, approved/changes-requested/commented/repeated events, self/bot exclusions, unreviewed and multi-component PRs, coverage below100% and different concentration patterns; use existing derivation, never hand-authored aggregates. |
| ECL-FR-424 | Overview exposes separate truthful available component/concentration/review/implementation/requirement/test dimensions and gaps, with counts/status; unavailable is not zero and overlapping component PR counts never inflate global coverage. |
| ECL-FR-425 | Present implementation/requirement/architecture/test connections as one traceability story and distinguish PR reviews from exact-version/target historical observations; retain complete provenance, exclusions and status behind accessible inspectors. |
| ECL-FR-426 | Missing evidence provides informative unavailable states and collection guidance; synthetic samples cannot be mistaken for user/public evidence. Version/schema terms belong in advanced metadata, and header makes no unverified release claim. |
| ECL-FR-427 | Preserve native keyboard-operable controls, clear focus and status/source distinction, wrapping primary navigation and contained table overflow; user report upload/export, legacy contracts and existing synthetic scenario semantics remain intact. |

## Portable offline evidence increment (PO)

This increment enables a lead/architect to attach their own explicit approved offline aliases to a report without proprietary source scanning. Preserve the four-area product experience. No inference, live acquisition, execution, scoring change or release.

| ID | Observable requirement |
| --- | --- |
| ECL-FR-428 | Accept a bounded strict offline evidence manifest with explicit source-owner publication approval and attach it to an existing valid report; perform no network/authentication/scanning. Provide evidence-attach with named report/manifest inputs, optional output and stdout otherwise. |
| ECL-FR-429 | Portable report4.0 keeps experimental-v0.1 and optional existing review/traceability plus verification_evidence; import/export roundtrips exact normalized source and derived semantics in Python and Explorer. Preserve v1/v2/v3 and fail closed on future versions/unknown fields. |
| ECL-FR-430 | Bind attached evidence to exact immutable traceability identity/scope/revision/configuration; stale joins are explicit unavailable, unknown WI/components unresolved, never manufactured. Requirement implementation needs an existing valid code path; exact test-version/target and existing conflict/coverage rules remain authoritative. |
| ECL-FR-431 | Deterministic output preserves distinct units, semantic hop order, conflict quarantine and all historical outcomes; Python/browser acceptance materially agrees across malformed/partial/unsupported/duplicate/conflict/limit inputs. |
| ECL-FR-432 | Public output is allowlisted approved aliases and historical metadata only; reject secret/private/raw/local-path fields and malformed Unicode/duplicate keys/nonfinite/deep input, with sanitized fixed errors and explicit exit codes. Syntax never establishes publication permission. |
| ECL-FR-433 | Loaded real v4 evidence appears in existing Overview, Traceability and Reviews & Verification; synthetic scenarios remain isolated, Atlas remains labelled working, eShop never inherits synthetic facts, failed import retains previous report. |
