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

All commands emit JSON to stdout; failures emit a diagnostic to stderr and exit 2. Names match exactly, ignoring case; use email to disambiguate. Empty contributor strings are errors. `--component-depth 2` groups `src/api/file.py` under `src/api`; the default depth is 1. Root files form `(root)`.

Reports contain revision, reference date, shallow-history flag, effective configuration, component concentration/risk, per-contributor signals and line activity, and file contributor coverage. Departure reports show estimated loss as a fraction, remaining contributors, successor overlap, and uncovered historical files. Default reference time is the newest author date, so reruns of unchanged evidence remain stable. Use `--as-of 2026-09-13T00:00:00+00:00` to measure age at an explicit time; it must not precede included commits.

Copy [the example configuration](docs/scoring.example.toml) and pass `--config path/to/config.toml` to any command. All six weights are required when overriding weights; they are normalized automatically.

## Scope and limitations

v0.1 uses local Git HEAD ancestry only. There is no Azure DevOps integration, graph database, LLM, or web UI. All tracked historical paths count, including deleted files, generated code, vendored files, tests, and docs. Renames count as deletion plus addition; this version does not track semantic file identity. Bots count as contributors. Git mailmap canonicalization is honored; otherwise identities group by case-insensitive email. Reviews, pairing, operational experience, uncommitted work, and knowledge transfer are invisible.

Shallow clones produce incomplete evidence and are flagged. Prefer a full clone. Concentration can be low even when every contributor is inactive; consult recency alongside risk. Sparse components can be critical after a single commit. Validate findings with the team before making continuity plans.

## Development

```sh
python -m unittest discover -s tests -v
python -m pip install mypy
python -m mypy --strict src
```

See [architecture](docs/architecture.md), [scoring model](docs/scoring-model.md), and [eShop validation](docs/validation.md).
