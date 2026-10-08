# Architecture

The flow is CLI → repository acquisition → history provider → domain evidence → explicit evidence filters → component strategy → scoring and analysis → JSON. The optional `continuity explorer` command serves the existing browser explorer and a narrow analysis endpoint on `127.0.0.1`; the browser sends only a local repository path to that loopback service. Python's standard library handles Git subprocesses, TOML, argument parsing, serialization, HTTP serving, temporary workspaces, and tests. Packaging uses setuptools.

- `domain/models.py`: immutable Author, Change, Commit, and History values; structural HistoryProvider and ComponentStrategy protocols. These contain no Git subprocess or CLI behavior.
- `git/history.py`: GitHistory implements the provider contract. It resolves HEAD once and reads that revision's ancestry, recording hashes, canonical author names/emails, timezone-aware author dates, paths, and numstat additions/deletions. Binary counts remain unknown. NUL framing supports tabs and newlines in paths. Merge commits retain metadata without diffs; ordinary branch commits supply their changes.
- `scoring/model.py`: validated configuration, normalized weighted score, exponential recency, and explicit concentration thresholds. Pure functions make model changes independently testable.
- `analysis/service.py`: groups evidence by replaceable component strategy and contributor; aggregates activity; produces signal breakdowns, normalized shares, concentration, and departure impacts. Successors are ranked by departed-file overlap, then score, then email for stable ties.
- `cli.py`: translates input and output only. Each command reconstructs a report from the same evidence/configuration; there is no hidden state or database.
- `git/source.py`: resolves a local path or a public HTTPS clone URL into a local repository workspace. Remote URLs are cloned with Git argument arrays into a unique temporary directory without a depth limit. The context-managed workspace removes only its own temporary clone, on both success and failure. `GitHistory` remains responsible solely for reading an already available repository.

To replace directory grouping, supply another ComponentStrategy to `analyze`. To introduce another evidence source later, implement HistoryProvider and map its evidence into the domain contract, explicitly preserving provenance. No future provider is implemented in v0.1.

Git extraction and aggregation are in-memory. Very large histories may require a streaming provider and indexed aggregates later. Historical file ownership is intentionally different from current line blame. Scores retain all historical contributors, including inactive ones. The Git checkout's mailmap is an additional identity input: reproducibility requires the same mailmap, revision, configuration, and reference date. The tool never changes the analyzed checkout.

## Remote repository acquisition

Public HTTPS clone URLs flow through `RepositoryWorkspace` before `GitHistory`: `input → source validation → full temporary clone → existing analysis → cleanup`. HTTPS is provider-neutral; GitHub and GitLab are not treated specially. SSH, `file`, FTP, and URL credentials are rejected because authenticated remote access is outside the current scope. Clone progress is emitted to stderr, and an additive remote `source` field records the supplied URL without disclosing the generated temporary directory. Scoring and domain layers do not receive remote URL or workspace concerns.

Tests create disposable real Git repositories and exercise parsing, binary paths, renames/deletions, merges, mailmaps, CLI views, scoring boundaries, configurable weights, recency, persistence, and departure coverage.

## Reporting and filtering extension

`analysis/filtering.py` applies explicit filters to immutable history evidence before aggregation. Commit metadata, revision, and shallow status survive filtering. This preserves the original time reference. A separate FilterEvidence value records input/retained/excluded file-change counts, reason counts, and excluded paths/author identities. No heuristic runs unless enabled.

`reporting/text.py` renders plain tables from typed reports without recalculating scores. Repository-controlled control characters are escaped in text. JSON continues to expose full signals and evidence, with additive filter metadata. No new runtime dependency is required.

## Static public demo

`ui/dist` is also a self-contained GitHub Pages artifact. Its relative asset references work both at the local explorer root and under `/engineering-continuity-lab/`. The packaged `eshop-report.js` is an analysis report generated from the documented dotnet/eShop validation revision and rendered on first load; it contains Git-derived report evidence, not eShop source code. The hosted page has no service dependency and does not contact eShop. A selected JSON report is read with the browser File API, validated by the existing model contract, and retained only in JavaScript memory until reset or page unload.

The page detects the loopback explorer before exposing repository-analysis controls. On GitHub Pages it makes no explorer API request, so a hosted visit does not attempt analysis, upload a report, or send report data to another service. The Pages workflow uploads only `ui/dist`, with the standard GitHub Actions Pages deployment environment and minimum deployment permissions. The static demo adds no analytics, cookies, telemetry, or third-party scripts.
## Report v3 Serialization

The v3 envelope is additive: retain `model: "experimental-v0.1"` and all existing Git fields, set `report_version: "3.0"` when traceability is attached, and preserve `review_evidence` unchanged. The optional top-level `traceability_evidence` has its own `schema_version: "1.0"`; a v3 Git-only envelope is valid, while the section is accepted only in v3. `model` identifies the original analysis model; `report_version` owns envelope evolution.

`continuity.reporting.traceability` owns explicit JSON conversion. It serializes only allowlisted provider-neutral evidence values and derived output; domain dataclasses remain JSON-agnostic. Import constructs the existing domain values, rejects unsupported enum/field values, requires input evidence already be normalized, reruns `derive()` using the declared directory component configuration, then compares every declared derived result with the recomputed canonical result. This makes Python derivation the semantic authority for paths, qualified gaps, artifact states and metrics.

The section has two owned objects. `collection` contains collection status, component strategy/configuration, sorted evidence boundaries, work items, the four independently enumerated reference populations, observed links, lookups and safe diagnostics. `result` contains derivation version, aggregate trace status, direct and derived links, canonical paths, gaps, artifact statuses, coverage metrics and safe diagnostics. Reference objects carry explicit `kind`, provider/instance/scope, identifier, repository, context, configuration and hash algorithm. Link support is represented as typed link identities, never Python class names or display text.

Canonical serialization sorts every semantically unordered list by stable typed identity and serializes object keys consistently. Derived links are separate from observations, retain their ordered support identities and cannot enter the input collection as authoritative links. Ratios are finite numerator/denominator values when available; empty or unavailable populations use null and preserve their status/reason. Collection, capability and trace statuses are independent.

The browser validator mirrors the declared v1/v2/v3 envelope and traceability rules, validates reference/link/path/gap/coverage semantics, and preserves v3 data on export/import. It does not add traceability to ordinary repository analysis or render a traceability view. Unknown versions/types fail closed. Private labels, transport data, credentials, raw provider responses, arbitrary titles and local paths are not part of this schema; safe aliases and approved synthetic labels are the only provenance values eligible for publication.

The independent report review corrections retain this boundary: additional wire identity/order, lookup ownership, diagnostic normalization and recognizable-private-value checks live in the reporting/browser consumers. Domain types and offline derivation are unchanged. Canonical Python timestamp output is UTC; the browser validates Gregorian ISO timestamps and uses microsecond instants and Unicode code points for equivalent boundary/order checks. Duplicate JSON fields and input-reflecting parser errors fail closed. Opaque aliases still require the source approval described by the product privacy contract; syntactic checks cannot certify provenance origin.
