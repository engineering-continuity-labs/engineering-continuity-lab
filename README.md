# Engineering Continuity Lab

An evidence-driven experiment for measuring engineering knowledge concentration and continuity risk from Git history. **Git activity is only a proxy for knowledge. The scoring model is experimental.** Scores are not assessments of ability, productivity, or actual replacement readiness.

## Quick start

Requires Python 3.12+ and Git on PATH. No runtime Python dependencies.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
continuity analyze --repo /path/to/repository
continuity person "Contributor Name" --repo /path/to/repository
continuity simulate-departure "contributor@example.com" --repo /path/to/repository
```

All commands emit JSON to stdout by default; use `--format text` for readable terminal tables. Failures emit a diagnostic to stderr and exit 2. Names match exactly, ignoring case; use email to disambiguate. Empty contributor strings are errors. `--component-depth 2` groups `src/api/file.py` under `src/api`; the default depth is 1. Root files form `(root)`.

Reports contain revision, reference date, shallow-history flag, effective configuration, component concentration/risk, per-contributor signals and line activity, and file contributor coverage. Departure reports show estimated loss as a fraction, remaining contributors, successor overlap, and uncovered historical files. Default reference time is the newest author date, so reruns of unchanged evidence remain stable. Use `--as-of 2026-09-13T00:00:00+00:00` to measure age at an explicit time; it must not precede included commits.

Copy [the example configuration](docs/scoring.example.toml) and pass `--config path/to/config.toml` to any command. All six weights are required when overriding weights; they are normalized automatically.

## Readable reports and explicit filters

```sh
continuity analyze --repo /path/to/repository --component-depth 2 --format text
continuity person "contributor@example.com" --repo /path/to/repository --format text
continuity simulate-departure "contributor@example.com" --repo /path/to/repository --format text

continuity analyze --repo /path/to/repository --component-depth 2 --format text \
  --exclude-bots --exclude-generated \
  --exclude-path 'vendor/*' --exclude-author 'automation@example.com'
```

Text analysis lists highest concentration first with risk, HHI, contributor count, leading contributor, and score share. Person tables include score, share, commits, files, and recency. Departure tables include modeled loss, remaining contributors, successor overlap, and uncovered-file count. JSON remains the default and includes all original fields plus `filters` and `filter_evidence`.

Filtering is opt-in and available on all three commands:

- `--exclude-bots`: matches the literal `[bot]` marker in canonical author name/email, case-insensitively. It does not identify all automation accounts.
- `--exclude-generated`: matches `*.g.cs`, `*.g.i.cs`, `*.generated.*`, `*.min.js`, and `*.min.css`. This is a filename heuristic, not content detection; inspect excluded paths before relying on it.
- `--exclude-path GLOB`: repeatable case-sensitive pattern against the full repository-relative path.
- `--exclude-author GLOB`: repeatable case-insensitive pattern against canonical name or email.

Quote globs to prevent your shell expanding them. Patterns use Python `fnmatchcase`: `*` matches slashes too, `?` matches one character, and brackets define character sets. These are not gitignore rules. For example `vendor/*` covers root vendor descendants; `*.g.cs` matches at any depth. Use the dedicated bot flag to match literal `[bot]`.

Reports show retained/excluded file-change counts and reasons. JSON also lists paths touched by any exclusion and authors matched by author filters; a listed path may still have retained changes from another author. A file changed in five commits counts as five file-change records. Reasons are counted once per excluded record, in order: author pattern, bot marker, path pattern, generated filename.

Filtered commits retain metadata, so commit count and reference date describe the original history. Only retained changes contribute to scoring; the contributor count includes only authors with retained changes. If all changes are excluded, analysis returns no components or risk labels. Person/departure queries for excluded people return a clear not-found error. Apply the same options when comparing views.

## Scope and limitations

v0.1 uses local Git HEAD ancestry only. There is no Azure DevOps integration, graph database, or LLM. An optional browser report explorer is available in `ui/`. By default all tracked historical paths count, including deleted files, generated code, vendored files, tests, and docs. Renames count as deletion plus addition; this version does not track semantic file identity. Bots count as contributors unless explicitly filtered. Git mailmap canonicalization is honored; otherwise identities group by case-insensitive email. Reviews, pairing, operational experience, uncommitted work, and knowledge transfer are invisible.

Shallow clones produce incomplete evidence and are flagged. Prefer a full clone. Concentration can be low even when every contributor is inactive; consult recency alongside risk. Sparse components can be critical after a single commit. Validate findings with the team before making continuity plans.

## Development

```sh
python -m unittest discover -s tests -v
python -m pip install mypy
python -m mypy --strict src
```

See [architecture](docs/architecture.md), [scoring model](docs/scoring-model.md), and [eShop validation](docs/validation.md).

## Browser report explorer

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory ui/dist
```

Open `http://127.0.0.1:8765` and select an `analyze` JSON report. The UI opens with clearly labeled synthetic data, never a private report. It shows concentration/risk, contributor signals, historical files, and departure scenarios. Reports stay in browser memory and are never uploaded or persisted. A reload resets the report. Maximum file size is 30 MB. Person/departure JSON exports are not accepted as complete analysis reports.

Bot/generated filters must be applied in the CLI before export; the UI displays their scope and offers risk/search view filters. It does not pretend to recompute scores without original Git evidence. `ui/dist` contains authored static HTML/CSS/JavaScript with no build or runtime dependencies. Run `node --test ui/tests/*.test.js` for the UI domain checks.

The optional WebMCP departure action is feature-detected. A supported browser tool context was unavailable during implementation, so its live registration has not been verified. Browser visual/interaction QA was not performed; model tests and static checks were performed.
