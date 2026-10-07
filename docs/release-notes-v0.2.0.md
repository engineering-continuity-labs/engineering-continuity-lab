# Engineering Continuity Lab v0.2.0 — PR & Review Evidence

Recommended tag: `v0.2.0`, after merge and green required CI. No release or tag is created by this continuation.

- Public GitHub merged-PR evidence follows actual validated REST next links across PRs, changed files, and review events, with explicit page safety limits and conservative handling of GitHub's file ceiling.
- Public API rate limits and provider failures retain usable normalized evidence as PARTIAL; interruptions before usable PR evidence are FAILED. No authentication or token support is introduced.
- Deterministic effective-state semantics distinguish APPROVED and CHANGES_REQUESTED from COMMENTED, dismissed, self, bot, missing-reviewer and unsupported reviews. Duplicate events never multiply reviewer units; case variants share one identity.
- Reviews show coverage, reviewer shares/HHI/risk, unreviewed PR references, exclusions, and separate compatible Git authorship HHI. Missing or incompatible evidence is unavailable rather than a zero/LOW result.
- Additive `report_version: "2.0"` preserves the unchanged `experimental-v0.1` Git model and every Git field. Whole-report JSON export/reopen preserves normalized events, provenance, completeness and rendered results; malformed or contradictory review evidence is rejected.
- The static demo bundles a new truthful dotnet/eShop PARTIAL snapshot: 100 closed PR records inspected, 9 merged observed, 6 retained, 24 events, 5 qualifying effective reviews, and 7 components. It makes no GitHub API calls. The v0.1 fixed Git baseline remains unchanged.
- Expanded deterministic fixtures cover pagination, partial retention, safe errors, state transitions, aggregation, report compatibility and actual UI upload/download handlers. Specifications, QA evidence and traceability are updated.

Limitations: public unauthenticated collection may hit GitHub rate limits, the snapshot is not atomic, and complete live eShop history remains MANUAL/PARTIAL. The static sample uses review directory depth 1 and Git baseline depth 2; it explicitly declines incompatible comparisons. Real-browser visual inspection remains MANUAL in this environment because no browser surface is available; actual renderer and report handlers are automated. Review metrics describe historical recorded interaction, not knowledge, quality, performance or replaceability.

Next v0.3 step: after v0.2 merges, start the Product Owner stage for Azure DevOps traceability in `specs/v0.3/`, defining provider boundaries, provenance, observable requirements, non-goals and acceptance criteria. Then hand off to Solution Architect and QA before implementation. No v0.3 work is started here.
