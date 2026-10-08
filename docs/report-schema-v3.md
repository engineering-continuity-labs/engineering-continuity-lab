# Report Schema v3

**Status: ACCEPTED for implementation on `feat/v0.3-traceability-report-v3`.** This is the additive public JSON contract for the offline v0.3 traceability report. It does not imply a live provider or traceability presentation.

## Envelope and version ownership

The Git report remains the existing report, with its current fields and values. When traceability is attached, set `report_version` to the string `3.0` and add one optional top-level `traceability_evidence` object. Keep `model: "experimental-v0.1"`: it identifies the original Git analysis model, while `report_version` owns serialized-envelope evolution. Do not rename, remove, or recalculate existing Git fields. Existing `review_evidence` remains byte/structure-equivalent and may coexist with traceability.

The top-level section is optional in v3 so a Git-only report remains valid. If present, it is valid only in v3. A v1 Git-only report and a v2 report with review evidence remain valid as before. Unknown report versions fail closed.

```json
{
  "model": "experimental-v0.1",
  "report_version": "3.0",
  "components": [],
  "review_evidence": {},
  "traceability_evidence": {
    "schema_version": "1.0",
    "collection": {},
    "result": {}
  }
}
```

The example abbreviates the unchanged Git report and traceability members; empty objects are not valid evidence.

## Traceability section

`schema_version` is exactly `1.0`. Unknown schema versions and unknown fields are rejected. The section contains:

- `collection`: the allowlisted normalized input needed to audit and reconstruct derivation.
- `result`: the explicit, auditable derived output. Import recomputes this from `collection` and requires exact semantic equality with the supplied result.

### Collection

`collection` has exactly these members:

- `status`: `COMPLETE`, `PARTIAL`, or `FAILED`.
- `component_strategy`: `{ "name": "directory", "configuration": "depth-N" }`. Only the existing directory strategy is supported; `N` must be a positive depth.
- `boundaries`: sorted `EvidenceBoundary` records containing `identifier`, `provider`, `instance`, `project`, `repository`, `collected_at`, `snapshot`, `query`, `identity_mapping`, `filter_policy`, nullable `revision`, `time_field`, `start`, `end`, `normalization_version`, and `join_contract`.
- `work_items`: sorted minimum records containing only `reference`, normalized `type` and `state`, and safe `provenance`. Optional title and lifecycle timestamps are deliberately omitted because they are not required for derivation.
- `populations`: independently enumerated `pull_requests`, `merged_pull_requests`, `commits`, and `changed_paths`, each a sorted array of typed references. Work-item enumeration is represented by `work_items`.
- `observed_links`: sorted provider/source observations only. Each has `source`, `target`, `type`, `origin`, `observations`, and an empty `supports` array. Direct origins are never rewritten as derived evidence.
- `lookups`: sorted lookup records with `boundary`, `capability`, `status`, nullable `endpoint`/`relationship`, `direction`, and nullable `population`.
- `diagnostics`: sorted safe enum records with `reason` and nullable `endpoint`/`relationship`; free text is forbidden.

All public values use explicit field allowlists. `EvidenceBoundary` and `Observation` timestamps must be timezone-aware ISO-8601 values. Native credentials, raw provider records, HTTP settings, URLs, local paths, personal identities, unapproved titles, and private reverse-alias maps are not representable.

### References and links

Every artifact reference has exactly `kind`, `provider`, `instance`, `scope`, `identifier`, `repository`, `context`, `configuration`, and `algorithm`. The supported kinds are `WORK_ITEM`, `PULL_REQUEST`, `COMMIT`, `CHANGED_PATH`, `PR_PATH`, and `COMPONENT`. Values are scoped identifiers, not display labels. Existing domain validation applies to safe tokens, relative paths, full Git hashes, path/revision context, and component configuration.

Link objects use exact typed endpoints and one of `WI_PR`, `WI_COMMIT`, `PR_COMMIT`, `COMMIT_PATH`, `PR_PATH`, `PATH_COMPONENT`, or `WI_COMPONENT`. Origins are `DIRECT_PROVIDER_LINK`, `DIRECT_SOURCE_LINK`, and `DERIVED_LINK`. The endpoint-kind/origin grammar is the `LEGAL` grammar in `continuity.analysis.traceability`: provider WI/PR/commit relations, source/provider commit-path observations, provider PR-path observations, and derived path/component or WI/component relations. Unsupported types and origin/end-point combinations are rejected.

Each observation contains `identifier`, `boundary`, `observed_at`, and `basis`. Derived links have no observations and carry nonempty `supports`, an ordered list of full typed link identities `{source, target, type, origin}`. Those identities must resolve to serialized observed/derived links. Path supports use the same wire identities in derivation order. This keeps direct assertions distinct from derived associations and preserves provenance through import.

### Result

`result` has exactly:

- `derivation_version`: current derivation rule version.
- `summary`: `VERIFIED`, `PARTIAL`, `MISSING`, or `UNAVAILABLE`.
- `direct_links` and `derived_links`: explicit typed link arrays; each must equal the recomputed normalized result.
- `paths`: canonical records with ordered `nodes`, ordered `supports`, sorted `boundaries`, `status`, canonical `gaps`, and `rule_version`.
- `gaps`: canonical records with typed `endpoint`, `relationship`, `direction`, `status`, and `reason`.
- `artifacts`: one record per canonical artifact with typed `artifact` and `status`; paths and gaps are the corresponding top-level records and are not duplicated into embedded subtrees.
- `metrics`: records containing `dimension`, integer `numerator`/`denominator`, numeric `value` or null, trace `status`, `collection_status`, `boundaries`, `sources`, `unknown_count`, `excluded_count`, nullable `reason`, and nullable typed `component`.
- `diagnostics`: sorted safe enum records with nullable typed endpoint/relationship.

Collection status, per-lookup capability, trace/path status, and metric status are separate values. `FAILED` without useful evidence is valid and yields unavailable trace results, not a complete empty result. Positive paths can be `VERIFIED` while collection/aggregate status is `PARTIAL`.

For a metric with a positive denominator and available population, `value` equals `numerator / denominator`; incomplete acquisition may still report the observed ratio with `PARTIAL` status. `numerator` cannot exceed `denominator`. A zero denominator or unavailable population has `value: null` and `UNAVAILABLE` status. Unknown and excluded counts are nonnegative integers. Python import derives and compares these exact fields instead of trusting submitted arithmetic.

## Import validation and canonical form

Python deserialization constructs existing domain values, rejects unknown/missing fields and enum values, verifies normalized input, and reruns the existing pure `derive()` operation with the declared directory strategy. The canonical result must equal the supplied result. This enforces relationship endpoint kinds/origins, qualifying evidence for `MISSING`, normative full-hop sequence for `VERIFIED`, no repeated path endpoint/cycle, unique paths, support resolution, metric arithmetic and status cardinality using the current offline semantics.

The browser applies the equivalent schema, reference, link grammar, support, path/gap/status, and coverage checks. It validates before import and export and preserves traceability fields exactly. Neither consumer silently reinterprets unknown future versions, artifact kinds, relation kinds, or values.

Canonical JSON uses UTF-8, sorted object keys, compact separators, no NaN/Infinity, and stable ordering for all unordered arrays: boundaries, work items, populations, observations, links, lookups, diagnostics, derived links, paths, gaps, artifacts, and metrics. Semantically ordered path nodes/supports are not reordered. Python's canonical serializer is the byte-stability reference; browser export preserves that JSON structure and array ordering.

## Compatibility, privacy, and limitations

- v1 Git-only and v2 review reports continue to import/export without traceability changes.
- v3 keeps the model identifier and all Git/review fields; traceability is additive and optional.
- No normal `continuity explorer` analysis fabricates work items or emits traceability without an explicit report object.
- Only synthetic normalized evidence is serialized in this task. There is no Azure adapter/auth/network path, UI traceability tab, CLI acquisition, v0.4 type, or live data.
- Existing versioned unknown fields/types are rejected, not ignored. A future schema requires an explicit version and coordinated consumer work.
- Approved synthetic work-item labels may be serialized. Private titles, personal fields, credentials, raw responses, arbitrary transport configuration, local paths, and private-source names are excluded.
