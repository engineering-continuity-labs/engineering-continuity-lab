# v0.2 product specification: PR and review evidence

**Status:** Implemented and automatically verified on `release/v0.2.0`, independently reviewed. Real public eShop collection remains MANUAL/PARTIAL; remote PR CI is pending. Evidence is recorded in `traceability.md`.

## Problem and product goal

Git history records who changed a component. v0.2 adds a separate view of historical pull-request review interaction: who reviewed merged changes, how widely qualifying review evidence is distributed, and where component-level authorship and review concentration differ.

Review activity is evidence of historical engineering interaction. It is not evidence of actual understanding, competency, employee importance, organizational dependency, replaceability, or handover readiness.

## Scope

v0.2 covers merged pull requests only. It records pull-request author and provider provenance, merge timestamp, changed paths, mapped components, reviewer identities, review state, and review timestamps where supplied. The first planned concrete provider is GitHub public-repository evidence; the domain contract remains provider-independent.

The existing v0.1 Git analysis remains valid and unchanged. v0.2 is additive: it does not alter Git signals, scoring weights, authorship concentration semantics, continuity-risk labels, or departure simulation.

## Non-goals

v0.2 excludes Azure DevOps integration, private-repository authentication, requirements/test/architecture traceability, technical-handover scoring, LLM inference, semantic or sentiment analysis of review comments, employee ranking, team-membership inference, and any combined human knowledge score derived from authorship and review evidence.

## Functional requirements

| ID | Requirement |
| --- | --- |
| ECL-FR-201 | The system shall acquire evidence for merged pull requests from a ReviewEvidenceProvider and retain provider provenance for each pull request. |
| ECL-FR-202 | The system shall preserve pull-request author, provider pull-request identifier, merge timestamp, changed paths, reviewer identity where supplied, review state, and review timestamp where supplied. |
| ECL-FR-203 | The system shall include only merged pull requests in v0.2 component review views and shall identify the merged-filter boundary in output provenance. |
| ECL-FR-204 | The system shall map each changed path to the existing component strategy and shall associate a pull request with every distinct component reached by its changed paths. |
| ECL-FR-205 | The system shall preserve APPROVED, CHANGES_REQUESTED, and COMMENTED as distinct review states. COMMENTED shall not silently count as APPROVED. |
| ECL-FR-206 | The system shall retain review-event history where the provider supplies it and derive at most one effective review state for each reviewer and pull request using documented deterministic state-transition rules. |
| ECL-FR-207 | The system shall report component review coverage as the percentage of component-mapped merged pull requests with at least one qualifying review. |
| ECL-FR-208 | The system shall report component review evidence distribution as normalized shares of qualifying reviewer units, separately from authorship evidence. |
| ECL-FR-209 | The system shall calculate and classify reviewer concentration transparently from component qualifying reviewer units, and shall report unavailable rather than LOW when no qualifying reviewer units exist. |
| ECL-FR-210 | The system shall identify the count and provider references of component-mapped merged pull requests with no qualifying review evidence. |
| ECL-FR-211 | The system shall present component-level authorship concentration and reviewer concentration as separate dimensions, and shall identify their comparison without combining them into a human score. |
| ECL-FR-212 | The system shall preserve excluded or non-qualifying review evidence with an explicit reason where it affects coverage or concentration. |
| ECL-FR-213 | The system shall produce deterministic derived review views for identical evidence, component configuration, qualification policy, and effective-state ordering inputs. |
| ECL-FR-214 | The system shall make incomplete, malformed, or partial provider evidence explicit and shall not present affected coverage as complete. |
| ECL-FR-215 | The system shall retain only the minimum provider evidence needed for the defined views and shall avoid persisting raw provider payloads. |
| ECL-FR-216 | The system shall preserve v0.1 Git-only analysis behavior and allow a Git-only report to remain valid without review evidence. |
| ECL-FR-217 | v0.2 validation shall use the public dotnet/eShop repository as its primary target and shall document any boundary difference from the v0.1 fixed Git revision. |
| ECL-FR-218 | Public acquisition shall traverse all reachable closed-PR, file, and review pages under an explicit safety limit, retaining only merged PRs. Uncollected or malformed evidence shall never be COMPLETE. Public rate limits require no authentication and produce PARTIAL when valid mapped PR evidence survives, otherwise FAILED. |
| ECL-FR-219 | Reports shall add `report_version: "2.0"` when review evidence is present, preserve the v0.1 Git model and fields, and support export/import without losing provenance, completeness, events, or derived results. Missing review evidence means unavailable, not zero. Malformed review structures shall be rejected on import. |

## Review semantics

### Evidence units and state transitions

A **review event** is one provider-supplied review record. Events remain distinguishable by state and timestamp. Duplicate provider event identifiers are retained once. For each `(provider pull request, reviewer)` pair, the **effective review** is the newest event, ordered by provider review timestamp; if it is absent, provider event ordering and then stable provider event identifier order are used. The ordering basis is recorded. An effective event marked dismissed by the provider is retained but is non-qualifying.

A review is **qualifying** when its effective state is APPROVED or CHANGES_REQUESTED, its reviewer identity is present, the reviewer differs from the PR author, and the provider has not identified the reviewer as a bot. COMMENTED, dismissed reviews, self-reviews, provider-declared bot reviews, missing-reviewer events, and any state not explicitly qualified remain visible but do not count as qualifying review evidence. This policy measures recorded review interaction; it does not judge review quality.

One qualifying reviewer contributes one **qualifying reviewer unit** to each component touched by that pull request. Multiple events from the same reviewer on the same PR do not multiply units. A PR touching multiple components contributes independently to every mapped component.

### Coverage and concentration

For a component, review coverage is:

`distinct merged PRs mapped to the component with >= 1 qualifying reviewer / distinct merged PRs mapped to the component`

The numerator and denominator must both be reported. A component with no mapped merged PRs has unavailable coverage, not 0% coverage. A partial provider response labels coverage PARTIAL rather than complete.

Reviewer distribution is each reviewer’s qualifying reviewer units for the component divided by all qualifying reviewer units for that component. Reviewer concentration is the Herfindahl-Hirschman Index of those shares. v0.2 defines separate review thresholds: LOW `< 0.40`, MEDIUM `>= 0.40 and < 0.60`, HIGH `>= 0.60 and < 0.80`, and CRITICAL `>= 0.80`. These labels are deliberately parallel to the v0.1 vocabulary for readability, but their population and semantics are review units rather than Git contributor scores.

### Comparison view

When a compatible v0.1 authorship result is available for the same component strategy, the view may display authorship concentration beside reviewer concentration and coverage. For example, HIGH authorship concentration with LOW reviewer concentration indicates concentrated recorded change activity with more distributed qualifying review interaction. HIGH/HIGH indicates both evidence dimensions are concentrated. Neither result proves knowledge, dependency, or a future continuity outcome.

## Non-functional requirements

| ID | Requirement |
| --- | --- |
| ECL-NFR-201 | Core v0.2 domain concepts and provider contracts shall not contain GitHub API request/response types. |
| ECL-NFR-202 | Provider provenance shall identify provider, public repository reference, evidence boundary, retrieval time, and completeness without retaining credential-bearing URLs or raw payloads. |
| ECL-NFR-203 | Tokens, authorization headers, API secrets, credential-bearing URLs, local temporary paths, and unnecessary raw provider data shall not be emitted in reports, logs, or errors. |
| ECL-NFR-204 | Missing optional timestamps or reviewer display fields shall not cause evidence loss; missing required identifiers shall follow the documented partial or malformed-evidence behavior. |
| ECL-NFR-205 | Existing v0.1 report consumers shall remain compatible with Git-only reports; future review fields shall be additive and versioned. |
| ECL-NFR-206 | Public-provider validation shall record provider boundary, pagination/completeness state, and collection time because provider review history cannot necessarily be constrained to the v0.1 Git revision. |

## Limitations

The model does not know whether a review was substantive, whether a reviewer read every changed line, whether another person understood the change, or whether provider history is complete. Provider-visible review state can change over time; both the retained event history and derived effective state are historical snapshots.
