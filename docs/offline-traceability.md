# v0.3 first implementation: offline traceability

This document describes the first offline core increment and its project-owned SYNTHETIC validation. Additive report v3 serialization/import/export and the separately merged [read-only Azure provider](azure-devops-provider.md) now exist. The offline core itself performs no network/authentication. The provider has runtime-only PAT transport and synthetic REST/loopback validation; real deployment compatibility, local connection/config UX, visual traceability UI, hosted traceability sample and v0.4 remain deferred.

The public report contract and compatibility rules are documented in [Report Schema v3](report-schema-v3.md). The traceability section is optional and Python/browser consumers retain v1/v2 behavior.

```python
from continuity.analysis.traceability import derive
from continuity.traceability_providers.synthetic import SyntheticTraceabilityProvider

report = derive(SyntheticTraceabilityProvider("BASE").acquire())
for metric in report.metrics:
    print(metric.dimension, metric.numerator, metric.denominator, metric.value)
```

BASE implements the exact accepted AC326 oracle: PR3/4, commit4/4, WI2/3; payment2/2, tests1/1, catalog1/1. BASE has one path per commit; MULTIPATH separately exercises several paths/components without changing the BASE oracle.

`ArtifactReference` is a kind-tagged immutable value. Work items/PRs use provider+instance+project/repository aliases; Git commit/path/component identities belong to the canonical repository/source, not the observing provider. Repository keys must be approved globally scoped aliases shared through the declared identity-map fingerprint, not ambiguous display names. Full hashes and exact commit/path contexts are required. Existing Git/PR owners project without mutation (Git selected revision and review provider/repository/query/collection time must match the approved boundary) via `project_history`/`project_reviews`; PR changed-path snapshots never fabricate commits.

Boundary metadata identifies snapshots, query/revision/time/filter/identity scopes. `join_contract` defaults absent; different query/time windows require an explicit shared approved contract declaring selected populations compatible; incompatible repository/mapping/filter/revision/contracts cannot silently join. Callers enumerate the actual selected populations and supply each directional lookup, independently from discovered links. Missing lookup means UNAVAILABLE, never complete empty. Times are source values, not inferred causality. CollectionStatus is reused from v0.2 without changing its API/serialization.

References accept bounded safe alias tokens; paths reject absolute/traversal/control/credential URL syntax. Titles default absent and require explicit approval; the provider's approved titles are synthetic only. Observations contain safe references and categories, never raw responses/settings/exceptions. Constructors reject malformed required values with fixed errors; fixture acquisition can isolate such rejected values using `isolate_invalid_fixture_record`, retaining only a safe category and known affected scope. This API consumes normalized values, not arbitrary private DTOs; approving aliases/titles remains an acquisition responsibility.

Normalization retains valid direct evidence, sorts and deduplicates observations, and quarantines conflicting observation identities. Unsupported/self/reverse relations cannot contribute paths. Typed traversal is bounded to five nodes/four hops, keeps short paths and per-hop gaps, and retains ordered support. Derived mapping/shortcuts cannot be submitted as observed facts. Coverage deduplicates artifact/occurrence populations; null ratios preserve unavailable/empty contexts. Excluded counts are dimension-specific distinct out-of-boundary references, plus observed nonmerged PRs for the merged-PR metric; extra routes/hops cannot inflate them. PR snapshots are excluded from commit-change units. Positive full paths may remain VERIFIED during PARTIAL collection; aggregate status still follows N/F/completeness precedence.

The Python derivation value remains JSON-agnostic. `continuity.reporting.traceability` owns the explicit v3 conversion and semantic import validation; the browser validates and round-trips the same synthetic contract without a traceability presentation. Existing Git scoring and v0.2 review semantics remain unchanged. The provider boundary was implemented by PR #20 and is independently reviewed in the [closure record](validation/v0.3-azure-provider-review.md). Next feature PR: `feat/v0.3-azure-local-connection`, with its own Product Owner/Architect/QA contract for user-facing config/acquisition. Visual traceability UI and v0.4 remain separate later work.
