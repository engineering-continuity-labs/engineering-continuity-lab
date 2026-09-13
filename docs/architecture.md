# Architecture

The flow is CLI → history provider → domain evidence → component strategy → scoring and analysis → JSON. Python's standard library handles Git subprocesses, TOML, argument parsing, serialization, and tests. Packaging uses setuptools.

- `domain/models.py`: immutable Author, Change, Commit, and History values; structural HistoryProvider and ComponentStrategy protocols. These contain no Git subprocess or CLI behavior.
- `git/history.py`: GitHistory implements the provider contract. It resolves HEAD once and reads that revision's ancestry, recording hashes, canonical author names/emails, timezone-aware author dates, paths, and numstat additions/deletions. Binary counts remain unknown. NUL framing supports tabs and newlines in paths. Merge commits retain metadata without diffs; ordinary branch commits supply their changes.
- `scoring/model.py`: validated configuration, normalized weighted score, exponential recency, and explicit concentration thresholds. Pure functions make model changes independently testable.
- `analysis/service.py`: groups evidence by replaceable component strategy and contributor; aggregates activity; produces signal breakdowns, normalized shares, concentration, and departure impacts. Successors are ranked by departed-file overlap, then score, then email for stable ties.
- `cli.py`: translates input and output only. Each command reconstructs a report from the same evidence/configuration; there is no hidden state or database.

To replace directory grouping, supply another ComponentStrategy to `analyze`. To introduce another evidence source later, implement HistoryProvider and map its evidence into the domain contract, explicitly preserving provenance. No future provider is implemented in v0.1.

Git extraction and aggregation are in-memory. Very large histories may require a streaming provider and indexed aggregates later. Historical file ownership is intentionally different from current line blame. Scores retain all historical contributors, including inactive ones. The Git checkout's mailmap is an additional identity input: reproducibility requires the same mailmap, revision, configuration, and reference date. The tool never changes the analyzed checkout.

Tests create disposable real Git repositories and exercise parsing, binary paths, renames/deletions, merges, mailmaps, CLI views, scoring boundaries, configurable weights, recency, persistence, and departure coverage.
