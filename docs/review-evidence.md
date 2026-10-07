# v0.2 review-evidence design

## Decision

v0.2 introduces a provider-independent review-evidence boundary alongside, rather than inside, the existing `HistoryProvider`. Git history and PR/review evidence describe different sources and have different retrieval, completeness, and provenance semantics. They meet only after paths are mapped through the existing component strategy.

```mermaid
flowchart LR
    Git[GitHistoryProvider] --> A[Git authorship evidence]
    Provider[ReviewEvidenceProvider] --> P[Pull request and review evidence]
    A --> Map[Existing component strategy]
    P --> Map
    Map --> Views[Separate authorship and review views]
```

No domain object in this boundary contains GitHub REST, GraphQL, or Azure DevOps DTOs. A GitHub adapter may later translate provider payloads at its edge; an Azure DevOps adapter must be able to populate the same domain contract.

## Provider-independent domain contract

The future domain layer should use immutable value objects equivalent to these concepts:

| Concept | Required information | Notes |
| --- | --- | --- |
| `ProviderReference` | provider key, public repository reference, provider object identifier | Repository references must be credential-free. |
| `PullRequestEvidence` | reference, author identity, merged timestamp, changed paths, reviews | A PR is accepted only when required fields are structurally valid. |
| `ChangedPath` | repository-relative path | Maps through the existing `ComponentStrategy`; provider-specific file records stay at the adapter edge. |
| `ReviewEvidence` | provider review-event identifier, reviewer identity where supplied, state, timestamp where supplied, dismissal metadata where supplied, ordering metadata | Retains event history; it is not pre-collapsed by the adapter. |
| `ReviewState` | APPROVED, CHANGES_REQUESTED, COMMENTED, plus explicit provider-unknown/other state | Known states remain distinct. |
| `Reviewer` | stable identity, optional display name, provider-declared bot flag when supplied | No team or employment inference. |
| `ReviewEvidenceCollection` | items, provenance, completeness, diagnostics | Distinguishes COMPLETE, PARTIAL, and FAILED collection outcomes. |

`ReviewEvidenceProvider.acquire(request)` should return `ReviewEvidenceCollection`, not `History`. The request will eventually contain a public repository reference and an explicit boundary/configuration. It must not accept or emit credentials as data. A provider adapter validates and normalizes at its edge before creating domain evidence.

## Data flow and derivation

1. Acquire merged PR evidence and collection provenance from `ReviewEvidenceProvider`.
2. Validate required PR/provider identity, merge time, author, and changed paths. Isolate invalid records in diagnostics rather than invent values.
3. Deduplicate provider review events by provider event identifier.
4. Retain all events and derive one effective review per reviewer/PR according to the v0.2 state-transition ordering contract.
5. Map each distinct changed path with the existing component strategy. A multi-component PR is represented once per component.
6. Apply the documented qualification policy to effective reviews. Preserve non-qualifying evidence and reasons.
7. Derive review coverage, reviewer distribution, reviewer HHI, unreviewed merged PR references, and an authorship-versus-review comparison view.

The review aggregation must not mutate Git evidence or invoke v0.1 scoring. A future report extension should add a versioned `review_evidence` section to a Git report or define an explicit joined view; both choices must preserve a Git-only report unchanged.

## Implemented public-provider boundary

The local explorer uses a public GitHub REST adapter for GitHub repository URLs or local repositories with a GitHub `origin` remote. It collects the latest 20 closed pull requests at collection time, then retrieves paths and review events for merged pull requests in that bounded set. More pages, including files or reviews beyond the first API page, are explicitly marked `PARTIAL`; a provider failure is marked `FAILED`. No token, authentication header, raw provider payload, URL query, fragment, or user-info is accepted into the evidence contract.

On 2026-10-07, the public `dotnet/eShop` validation collection returned `PARTIAL` evidence with one merged pull request in its latest 20 closed pull requests. This is a live provider boundary, not the v0.1 fixed Git revision, and must not be compared as a complete historical PR census.

## Qualification, coverage, and concentration

An effective APPROVED or CHANGES_REQUESTED review by an identified, non-author, provider-non-bot reviewer qualifies. COMMENTED remains an observed event but does not qualify. An effective event marked dismissed by the provider does not qualify. Missing reviewer identities and unknown states remain explicit non-qualifying evidence.

Review coverage is PR-level within each component, not file-line coverage: each distinct merged PR mapped to a component appears once in the denominator; it appears in the numerator when it has at least one qualifying reviewer. This is a readable measure of provider-recorded review exposure, not a claim that every changed line was reviewed.

Reviewer distribution counts one unit per qualifying `(component, pull request, reviewer)`. The reviewer HHI is calculated only over these units. The review threshold configuration is a distinct v0.2 contract, even though its initial bands use familiar labels. A component with no qualifying units is `UNAVAILABLE`; classifying it LOW would be misleading.

## Comparison boundary

Authorship concentration comes from existing Git analysis. Review concentration and coverage come from the review evidence collection. A comparison requires compatible component naming and component-depth configuration. It must render source boundaries independently: a fixed Git revision and a provider collection boundary may represent different historical windows.

The comparison can describe concentration patterns, such as HIGH authorship/LOW review. It must not combine values into a person score, declare a continuity outcome, or infer expertise or replacement readiness.

## Failure, privacy, and security boundaries

- A provider transport or authorization failure is a failed collection, not an empty review result.
- A provider-declared partial response is PARTIAL; coverage and unreviewed counts carry that status.
- Missing optional display names or timestamps do not discard otherwise valid evidence. Missing required identifiers, merge status, or paths isolate a record and record diagnostics.
- Provider raw payloads, access tokens, authorization headers, secrets, credential-bearing URLs, and local temporary paths do not cross into core domain values, reports, logs, or user-facing errors.
- Store normalized minimum evidence and audit provenance only. Do not retain comment bodies, sentiment, or unrelated personal profile fields.

## Validation strategy

dotnet/eShop is the primary v0.2 validation repository because it anchors comparison to the v0.1 baseline. Its v0.2 provider collection must record public repository reference, retrieval timestamp, selected merged-PR boundary, page/completeness status, and provider limitations. The v0.1 revision `b4a40872005d4bb29e5b1fa1ff7e244143d39215` remains a documented Git baseline, but provider PR/review evidence may not be meaningfully restricted to that revision.

If eShop lacks a required public edge case, one additional public repository may be used only after the missing case and repository choice are documented. It supplements rather than replaces eShop.

## Planned QA verification

Implementation must begin with provider-neutral fixtures, then provider-adapter integration fixtures. The required cases are: one PR with several reviewers; several PR authors in one component; APPROVED, CHANGES_REQUESTED, and COMMENTED states; repeated events by one reviewer; self-review; a PR touching several components; no reviews; only non-qualifying reviews; equal reviewer shares; duplicate provider events; missing optional timestamps and display names; bot identities; dismissed and historical state transitions; deterministic order; empty review evidence; malformed and partial responses; provider failure; unchanged v0.1 Git-only reports; and the documented dotnet/eShop collection run.

QA must separately assert:

- effective state and qualification decisions, including their visible exclusion reasons;
- PR-level coverage numerator/denominator rather than file-line coverage;
- reviewer-unit normalization and HHI boundary behavior;
- no reviewer concentration label for an empty qualifying population;
- no combined authorship/review person score;
- provenance/completeness propagation;
- absence of credential material and raw provider payloads in output and error fixtures.

Provider integration tests must not require private repositories, employer data, or credentials in CI. A mocked provider transport may exercise public-provider pagination, malformed records, and error semantics. The real public dotnet/eShop validation is a documented manual/integration boundary check, not a source fixture committed into this repository.

## Open implementation decisions

1. Whether a future provider boundary is an explicit date range, PR-number range, or provider snapshot identifier.
2. The additive report versioning shape and whether joined views are emitted as one report or linked reports.
3. How a concrete provider expresses unavailable changed-file lists for a merged PR without misreporting component coverage.
4. Whether provider-declared bot exclusion is fixed v0.2 policy or an explicit future configuration option. The initial specified policy is exclusion with visible reason.
