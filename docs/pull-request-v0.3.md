# spec: define v0.3 traceability evidence

Base: `main`. Head: `release/v0.3-azure-devops-traceability`.

Defines how Engineering Continuity Lab will explain why code changed using historical artifact evidence. This PR is specification, architecture, evidence-model and verification design only, based on latest stable main after v0.2; product implementation explicitly stops here.

- Product goal: inspect **Work Item → PR → Commit → Changed Path → Component** and useful shorter chains, with understandable gaps rather than individual/process-quality scores.
- Provider-independent minimum immutable values and typed relationships. A separate TraceabilityEvidenceProvider feeds offline core derivation; existing Git and v0.2 normalized PR evidence retain ownership. No Azure REST DTOs leak into core.
- Azure DevOps Services/Server design includes configurable deployment/organization-or-collection/project/repository scope, endpoint/API-version/capability profiles, continuation semantics, verified enterprise TLS, network isolation and adapter-private authentication. No universal Server support, live API or authentication implementation claim.
- DIRECT_PROVIDER_LINK and DIRECT_SOURCE_LINK observations are distinct from DERIVED_LINK paths/component mapping, retaining ordered supporting provenance. No inference from messages, branch names, identities, nearby timestamps or text similarity.
- COMPLETE/PARTIAL/FAILED acquisition, SUPPORTED/UNSUPPORTED/UNKNOWN capability and VERIFIED/PARTIAL/MISSING/UNAVAILABLE trace outcomes are independent. Scoped complete negative evidence is required for MISSING; positive paths can coexist with partial collection. Explicit N/F aggregate rules remove zero-chain status ambiguity.
- Four descriptive metrics define distinct scoped PR/commit/change/work-item numerator/denominator populations, source/boundary/completeness and unknown/excluded counts; no zero-population 0% or hidden quality threshold.
- Minimum-data/privacy design omits unnecessary personal/comment/attachment/custom-field data and confidential titles, uses approved safe labels/aliases, sanitizes errors and forbids credentials/raw responses/local paths/publication of private employer/NATO/NCIA/defence/customer evidence.
- Project-owned SYNTHETIC BASE plus named complete/partial/missing/duplicate/malformed/cycle/failure/capability/window/privacy variants define deterministic future oracles. Live Azure validation is optional secondary/manual evidence, not a prerequisite for offline design.
- v0.1/v0.2 runtime and reports remain unchanged. Future additive traceability section/report_version 3.0 requires coordinated consumers because current v0.2 browser validators reject unknown envelopes. Typed/versioned link grammar permits future v0.4 extension without implementing it.
- New IDs: ECL-FR-301–328, ECL-NFR-301–313, ECL-AC-301–339. Every requirement and criterion maps to design, planned implementation and planned evidence; runtime status remains ACCEPTED/planned, never VERIFIED.
- QA/current baseline: 79 Python tests, strict mypy across 20 files, 20 Node model/handler/Pages tests, JS syntax/static assets and unchanged 0.2.0 wheel build pass. No source/UI/CLI/test/packaging/auth/network/schema code changes.
- Independent Code Reviewer record includes R1 MAJOR aggregate-status overlap returned to Product Owner/Architect, clarified cardinality rules and QA AC339; **APPROVE — design/specification only**, with no unresolved BLOCKER/MAJOR findings; record: `docs/validation/v0.3-design-review.md`.

Open later gates: actually tested Server version/capability matrix, transport/auth/trust policy, continuation/retry budgets, private alias-map persistence, UI layout, exact v3 serialization/consumer rollout. These do not block the specified offline first implementation and cannot be silently chosen during later roles.

Recommended first implementation PR, only after separate authorization: `feat: add offline normalized traceability evidence and synthetic derivation` — immutable values, fixture-only provider, typed paths/gaps/coverage and QA fixtures; no live Azure/auth/UI/CLI/schema/v0.4 implementation.

Files: `specs/v0.3/{product-spec,acceptance-criteria,traceability}.md`, `docs/traceability-evidence.md`, review/verification records and minimal README/index updates. No implementation starts after this PR, and no merge/release is performed in this task.
