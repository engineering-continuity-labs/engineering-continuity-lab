# feat: complete v0.2 PR and review evidence

Base: `main`. Head: `release/v0.2.0`.

The previous work already contained provider-neutral evidence, deterministic review aggregation, a public GitHub adapter, the local Reviews view, a partial eShop sample, and initial pagination/report-version/export changes. Existing commit `7d7d7a7158bd0de9a1f7c838a6dc8c59ccaaa75d` is preserved. This continuation closes collection, validation, compatibility, and verification gaps.

- Pagination follows actual validated REST Link next targets across closed PRs, changed files, and reviews. Same-endpoint/public-origin restrictions, cycles, the 1000-page limit, malformed evidence, and GitHub's file ceiling cannot silently declare COMPLETE.
- Public API collection requires no token. HTTP 403/429 rate limits receive safe diagnostics; validated mapped evidence survives later interruptions as PARTIAL, while interruption without usable PRs is FAILED. Raw responses, headers, request internals and secrets never enter reports.
- Additive `report_version: "2.0"` retains `model: "experimental-v0.1"` for unchanged Git scoring and preserves every Git field. JSON export/import retains provenance, completeness, events and results; structural, arithmetic and retained-event contradictions are rejected. Absence means unavailable.
- Deterministic effective-state qualification/exclusions and deduplication preserve one reviewer unit per PR/component. The UI displays compatible authorship HHI independently of reviewer HHI/coverage and declines comparisons with different/unknown component scope.
- Actual dotnet/eShop validation at `2026-10-07T16:35:19.861137+00:00` is PARTIAL: 100 closed inspected, 9 merged observed, 6 retained, 24 events, 5 qualifying effective reviews, 7 components. Public API failure/rate limits prevented complete history. The normalized static sample replaces the old bounded sample and never calls GitHub APIs from Pages.
- Local evidence: 79 Python tests, strict mypy over 20 files, 20 Node tests (19 model/UI-handler + 1 Pages), JavaScript syntax checks, whitespace check and v0.2.0 wheel build all pass. Real Python analysis -> browser export/import and actual upload/download renderer handlers are covered.
- v0.1 suite passes unchanged. The fixed eShop Git baseline retains 347 commits, 48 components and LOW 33 / MEDIUM 10 / HIGH 0 / CRITICAL 5.
- Independent review APPROVE after repairing R1 MAJOR raw-event consistency; no unresolved BLOCKER/MAJOR. R2 count-selection concern withdrawn/clarified. Security/privacy review covers provider isolation, minimum normalized evidence, escaped rendering, credential-free provenance, no raw-error leakage and no hosted upload.
- Normative semantics are VERIFIED in `specs/v0.2/traceability.md`. Live eShop history remains MANUAL/PARTIAL, public snapshots are non-atomic, and real-browser layout inspection remains MANUAL because no browser surface is available. Actual rendering and handlers are automated.

Evidence: `docs/validation/v0.2-completion.md`, `docs/validation/v0.2-code-review.md`, `docs/validation/eshop-v0.2-summary.json`. Release notes: `docs/release-notes-v0.2.0.md`. Recommended tag after merge/green required CI: `v0.2.0`. No tag/release or v0.3 work is created.

PR CI must pass before merge. PR creation in this execution was blocked by GitHub integration permissions (`403 Resource not accessible by integration`); browser fallback was unavailable (`Computer Use permissions are not granted`). Open the PR through an authorized GitHub session and wait for CI. The automation did not claim remote green checks.

Compare: https://github.com/engineering-continuity-labs/engineering-continuity-lab/compare/main...release/v0.2.0?expand=1
