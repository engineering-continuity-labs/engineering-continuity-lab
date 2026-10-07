# feat: add offline normalized traceability evidence and synthetic derivation

Base: `main`; head: `feat/v0.3-offline-traceability-domain`.

Implements the first accepted v0.3 runtime slice after specification PR #17 merged. Explains observed engineering intent→implementation paths using provider-independent offline normalized evidence and project-owned SYNTHETIC fixtures. This is **not Azure DevOps integration**; no live Azure API calls are made.

## Scope and contracts

- Immutable scoped artifact/work-item/boundary/observation/link/lookup/path/gap/report values; reuse existing CollectionStatus and ComponentStrategy. Git source and v0.2 PR/review evidence retain ownership through nonmutating projections with strict provenance/revision checks.
- Explicit WI_PR, WI_COMMIT, PR_COMMIT, COMMIT_PATH, PR_PATH, PATH_COMPONENT and WI_COMPONENT types. DIRECT_PROVIDER_LINK, DIRECT_SOURCE_LINK and DERIVED_LINK remain separate; derived links retain support and cannot be authoritative input.
- Pure canonical normalization quarantines conflicting observations, rejects unsupported/malformed/self/reverse links, preserves valid observations and deduplicates counts. Bounded typed traversal supports normative WI→PR→Commit→Path→Component and explicit shorter paths/gaps.
- Collection COMPLETE/PARTIAL/FAILED, capability SUPPORTED/UNSUPPORTED/UNKNOWN and trace VERIFIED/PARTIAL/MISSING/UNAVAILABLE remain independent. Missing requires correctly scoped complete supported negative lookup. Positive full paths can remain VERIFIED during incomplete collection while aggregates stay partial/unavailable.
- Exact identities, compatible revision/filter/alias maps and explicit cross-query/window join contracts; no inferred relationships from titles, author, timing, branch or messages.
- Four distinct coverage populations, null unavailable/zero-population ratios, source/boundary/completeness/unknown and dimension-specific distinct exclusion counts. Alternate routes cannot inflate metrics.
- Safe alias/provenance values, optional explicitly approved titles, fixed diagnostic categories; no assignee/comments/raw responses/settings/secrets or personal score fields.

## Synthetic validation

BASE matches accepted AC326 exactly: PR intent **3/4**, commit intent **4/4**, WI implementation **2/3**, payment changes **2/2**, tests **1/1**, catalog **1/1**. PR52 has no observed direct WI association despite independent commit intent; PR54 has no observed commits; WI1003 has no observed implementation. MULTIPATH plus duplicate/conflict/cycle/malformed/capability/partial/failure/empty/linked-only/boundary/snapshot/no-inference variants cover offline failure boundaries.

## QA, traceability and independent review

- 56 new offline tests; **135 total Python tests pass** including all79 existing v0.1/v0.2 regressions.
- Strict mypy24 files; Node20 tests; JS/static entrypoint checks; wheel0.2.0; whitespace checks pass.
- Per-criterion evidence/status recorded in specs/v0.3/traceability.md. Live acquisition and future serialization/presenter/extension criteria remain ACCEPTED/PARTIAL rather than fabricated VERIFIED claims.
- Independent reviewer: **APPROVE**, no unresolved BLOCKER/MAJOR. Four MAJOR findings fixed/re-reviewed: snapshot false-missing membership, lookup scope, source-provenance relabelling, excluded-link count inflation. Review and validation records under docs/validation/v0.3-offline-*.md.

## Non-goals and next step

No Azure REST/auth/network adapter, UI/CLI, report-v3 serialization, hosted demo, inference/LLM/embedding/graph infrastructure, Jira/GitHub Issues, employee ranking or v0.4. Current Git/review output, scoring, browser behavior and package version remain unchanged. No release is created or implementation PR automatically merged.

Next recommended PR: `spec: define v0.3 traceability report serialization contract` before `feat: add versioned traceability report serialization`; resolve exact fields/consistency/version migration and coordinated consumer compatibility first. Live Services/Server profile/transport/auth/TLS/continuation validation is separately gated.
