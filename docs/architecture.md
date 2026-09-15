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
