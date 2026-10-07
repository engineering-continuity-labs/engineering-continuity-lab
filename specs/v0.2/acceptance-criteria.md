# v0.2 acceptance criteria: PR and review evidence

**Status:** Runtime acceptance criteria; automated and manual evidence is recorded in `traceability.md`.

| ID | Given / When / Then |
| --- | --- |
| ECL-AC-201 | **Given** a provider returns merged PR evidence, **when** it is acquired, **then** each retained PR records provider provenance, PR identifier, author, merge timestamp, and changed paths. |
| ECL-AC-202 | **Given** open, closed-unmerged, and merged PRs, **when** review evidence is derived, **then** only merged PRs contribute and the merged boundary is visible in provenance. |
| ECL-AC-203 | **Given** a PR with APPROVED, CHANGES_REQUESTED, and COMMENTED events, **when** its events are represented, **then** all three states remain distinguishable and COMMENTED does not qualify merely because it is a review event. |
| ECL-AC-204 | **Given** multiple events by one reviewer on one PR, **when** the effective review is derived, **then** event history remains available and exactly one effective state follows timestamp, provider order, and stable-id tie breaking. |
| ECL-AC-205 | **Given** a merged PR that touches paths in multiple components, **when** paths are mapped, **then** the PR is associated once with each distinct component reached by the existing component strategy. |
| ECL-AC-206 | **Given** a component with mapped merged PRs, **when** coverage is calculated, **then** the output reports distinct PR numerator, denominator, and percentage using the qualifying-review policy. |
| ECL-AC-207 | **Given** a component-mapped PR with APPROVED or CHANGES_REQUESTED from a non-author, non-bot reviewer, **when** qualifying evidence is derived, **then** that reviewer contributes one unit for that PR and component. |
| ECL-AC-208 | **Given** COMMENTED, dismissed, self-review, provider-declared bot, missing-reviewer, or unsupported-state evidence, **when** qualification is evaluated, **then** it does not contribute a qualifying unit and the exclusion reason is represented. |
| ECL-AC-209 | **Given** a component with qualifying reviewer units, **when** reviewer distribution is reported, **then** each reviewer share is normalized over those units and multiple events from the same reviewer on one PR do not multiply their share. |
| ECL-AC-210 | **Given** reviewer shares for a component, **when** reviewer concentration is classified, **then** HHI and the v0.2 review thresholds are reported with LOW, MEDIUM, HIGH, or CRITICAL; with no qualifying units it is unavailable. |
| ECL-AC-211 | **Given** mapped merged PRs without qualifying reviewer units, **when** component review evidence is reported, **then** their count and provider references are available separately from coverage. |
| ECL-AC-212 | **Given** compatible Git authorship and review evidence for a component, **when** a comparison is shown, **then** authorship concentration, reviewer concentration, and coverage remain separate values and no combined person score is emitted. |
| ECL-AC-213 | **Given** identical evidence, component configuration, qualification policy, and ordering inputs, **when** derived review views repeat, **then** units, shares, coverage, concentration, and order match. |
| ECL-AC-214 | **Given** missing optional timestamps or reviewer display fields, **when** provider evidence is processed, **then** valid required evidence remains usable and the fallback ordering or missing field is recorded. |
| ECL-AC-215 | **Given** malformed required provider fields, duplicate event identifiers, an incomplete page, or provider failure, **when** acquisition or derivation runs, **then** invalid records are rejected or isolated deterministically, duplicates do not multiply evidence, and output exposes failure or PARTIAL completeness. |
| ECL-AC-216 | **Given** a Git-only v0.1 report, **when** v0.2 support is introduced, **then** the existing report remains valid and its scoring, classifications, and stress-test results do not change. |
| ECL-AC-217 | **Given** dotnet/eShop validation, **when** v0.2 evidence is collected, **then** the result records the public repository, provider collection boundary, retrieval time, completeness, and how that boundary differs from the v0.1 fixed Git revision. |
| ECL-AC-218 | **Given** provider integration, **when** evidence, errors, or provenance are persisted or rendered, **then** no token, authorization header, API secret, credential-bearing URL, raw payload, or local temporary path is exposed. |
| ECL-AC-219 | **Given** GitHub-style next links across PR, file, and review pages, **when** acquisition runs, **then** exact validated same-endpoint next targets are followed deterministically; completion has no incomplete-pagination diagnostic, while safety exhaustion, cycles, malformed records, and continuation failures are explicit. |
| ECL-AC-220 | **Given** HTTP 403 rate-limit or 429 responses, **when** public acquisition cannot finish, **then** normalized valid PR evidence is retained with PARTIAL, or FAILED if none survives, and only a safe diagnostic is emitted. |
| ECL-AC-221 | **Given** a Git-only v0.1 report or a v2 COMPLETE/PARTIAL/no-qualifying-review report, **when** it is exported and reopened, **then** Git fields and review results/provenance remain identical; structurally or numerically inconsistent review evidence is rejected. |
