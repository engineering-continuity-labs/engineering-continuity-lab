# v0.5 Engineering System Review — Product Owner contract

Status: IMPLEMENTED in staged increments through Azure acquisition and executive-review presentation. Verification status remains requirement-specific in `traceability.md`; live provider access, accessibility observation and physical-print evidence remain MANUAL. The historical design wording below is retained as provenance.

## Problem, persona and value

Engineering managers, technical managers and chief engineers need a system-level evidence picture before an engineering review: what was assessed, which components merit investigation, what changed, and which sources cannot support a conclusion. Existing continuity/review/traceability/requirement evidence is useful but does not describe delivery flow or explicit defects. Add those two independent dimensions together and compose an Engineering System Review; reuse existing evidence without redefining its mathematics or claims.

Journey: identify system and assessment period → inspect sources/completeness and dimension snapshot → select an evidence-backed finding/component → inspect original evidence/threshold/comparison → choose a conservative investigation → export an offline review with its limitations. Preserve current Overview / Continuity / Traceability / Reviews & Verification organization; future manager review is a composed landing/export, not a return to eight competing tabs. The first screen contains system, period, sources, attention findings, dimension cards, components to investigate and unavailable evidence.

## Scope and requirements

| ID | Observable requirement |
| --- | --- |
| ECL-FR-501 | Compose a manager-facing Engineering System Review with the twelve sections below, independent dimension values/counts/status and evidence drilldowns; never collapse dimensions into a health, team, developer or maturity score. |
| ECL-FR-502 | Preserve existing Git concentration, review interaction, traceability and exact-version/target historical verification semantics; display their original identities, configuration, source time and limitations rather than reranking people or relabelling old evidence as current. |
| ECL-FR-503 | Represent provider-neutral independently selected work-item and PR populations with approved scoped aliases, explicit states/types/timestamps/history capability and source boundaries; derive delivery throughput, open age and qualified duration distributions only from explicitly observed values. |
| ECL-FR-504 | Represent independently selected explicit Bug work items with approved aliases, observed created/resolved/state/history and configured priority/severity; derive opened/resolved/open/aged/reopened/distribution metrics with unavailable semantics for missing required fields/history. |
| ECL-FR-505 | Expose build counts, result categories, qualified duration and comparison where evidence supports them; build success is not product quality. Deployment metrics are deferred in this increment with explicit unsupported/deferred capability. |
| ECL-FR-506 | Use explicit comparable current/previous windows and inventory instants, timezone/interval semantics, retrieval boundaries, source-selection/mapping policy and completeness; reject unequal windows and suppress invalid/unsupported trends rather than manufacture comparison. |
| ECL-FR-507 | Populate component dimensions only from accepted explicit traceability or declared exact scope mappings; show unmapped populations and overlapping memberships; neither association count nor summed component rows inflate global distinct units. |
| ECL-FR-508 | Generate deterministic evidence-backed Findings with type, scope, severity, exact evidence references, versioned transparent rule, measured values, threshold/comparison and limitations. Observations do not establish cause or readiness. |
| ECL-FR-509 | Offer fixed recommended-investigation templates scoped to supporting evidence; never use LLM conclusions, prescribe employment decisions, or frame duration/defects as individual productivity/performance. |
| ECL-FR-510 | Provide first-class completeness for every dimension/population/required field/history/mapping/window: provider/profile, capability, acquisition state, selected/eligible/excluded units, bounds and reasons. Unsupported/failed/unknown absence remains unavailable, not zero. |
| ECL-FR-511 | Define separate deterministic machine-readable assessment and offline self-contained printable HTML outputs referencing validated evidence; do not mutate report4.0 or require a server after generation. Browser and HTML use the same assessment, no native PDF scope. |
| ECL-FR-512 | Keep future acquisition separate from pure analysis/composition; preserve Azure target profiles and runtime-only PAT/read-only/privacy transport constraints, with per-operation capability and no synthetic-to-live certification. |
| ECL-FR-513 | Plan a clearly SYNTHETIC Atlas manager example with mixed continuity/review/trace/requirements plus normal/slow/aging delivery, opened/resolved/aged/reopened defects and successful/failed builds; include missing/partial/unmapped cases. |

| ID | Nonfunctional requirement |
| --- | --- |
| ECL-NFR-501 | Public output excludes secrets, local paths, native DTOs/reverse mappings, descriptions/comment text/logs, employee performance labels and new personal identities; source owner explicitly approves aliases and aggregate publication. Syntax is not permission. |
| ECL-NFR-502 | Pure offline assessment is deterministic for identical evidence/windows/mapping/rules; bounded inputs, strict Unicode/JSON/version/field validation and sanitized errors; conflicts cannot turn into favorable evidence. |
| ECL-NFR-503 | Keep measurement, acquisition capability, collection completeness, finding severity and governance verification distinct; report uncertainty, exclusions and sample adequacy without hiding positive evidence. |
| ECL-NFR-504 | Preserve legacy report contracts, core math and four-area UX; no runtime dependency/package version/release/tag change in this design PR. |
| ECL-NFR-505 | Follow PO → Architect → QA → independent design review; runtime acceptance is PLANNED and live/publication/visual authenticity remains MANUAL until actually verified. |

## Final report sections

1. Executive Engineering Snapshot (independent dimension cards, attention and unavailable evidence).
2. System / Component Landscape (approved scope, populations and mappings).
3. Engineering Continuity (original concentration and historical supporting evidence).
4. Change Traceability (existing observed paths/gaps, no inferred links).
5. Review Health (historical qualifying interaction/coverage, never review quality).
6. Requirements & Verification (four original independent dimensions/outcomes).
7. Delivery Flow (windowed counts, age, qualified durations).
8. Quality / Defect Evidence (explicit Bug population and limitations).
9. Build Health where supported; deferred deployments remain visible unavailable.
10. Engineering Risks / Findings (observations, deterministic rules, inspectable evidence).
11. Evidence Completeness & Limitations (all dimensions, including missing sources).
12. Recommended Investigation / Management Actions (investigation templates only).

## Product policies accepted before architecture

Default current window is the last30 complete UTC days, previous the preceding30 complete UTC days, with explicit assessment_as_of; explicit equal-duration contiguous windows are allowed. Historical comparisons require comparable independent populations/source/mapping/units and sufficient history; a source's live current state does not establish past-window inventory. Complete supported empty event count may be measured0, but empty durations/fractions are null. Unknown timestamps/state mappings/history are excluded with reasons and cannot become0 or a fabricated transition.

Duration summaries are descriptive distributions of qualifying evidence, not productivity. Show median with n>=1, p75 with n>=4, p90 with n>=10; disclose sample size and censoring, never extrapolate incomplete samples. Transparent default attention thresholds may be configured and versioned; severity denotes investigation attention, not probability of failure or employee competence. Comparative findings require complete comparable qualified samples; partial sources retain observations and completeness warnings without causal claims.

## Explicit roadmap decision

At this PO handoff, proposed **v0.5 becomes Engineering System Review**, comprising Delivery Flow + Quality/Defects + manager composition. The previously planned Technical Handover Verification moves to proposed **v0.6**. Historical v0.1–v0.4 specifications retain their original text/context; README roadmap will link this decision and must not imply either future capability is implemented. v0.4 release preparation remains a separate task; this design PR does not release it.

Non-goals: runtime metrics/acquisition/UI in this PR, relationship inference/title similarity, document/test/build-log scanning, live execution, native PDF, deployment portability, causal/LLM advice, defect density without a denominator, team/person/health scores, performance evaluation, handover readiness certification.

PO exit: target user, journey, observable dimensions, time/sampling/claim policies, acceptance intent and non-goals are explicit. Architect/QA may proceed; no implementation or verification approval is claimed.

## Manager comprehension increment

The twelve accepted technical areas remain audit structure; normal navigation uses four layers defined in docs/v0.5-manager-report-experience.md.

| ID | Requirement |
| --- | --- |
| ECL-FR-514 | Compact Executive Summary answers attention, affected components, observed dimensions and source sufficiency without technical identifiers. |
| ECL-FR-515 | Exact-bound component table/detail separates dimensions and orders explicit attention first; unbound evidence is Unavailable. |
| ECL-FR-516 | Human labels and qualified readable trends preserve original values, findings, independent dimensions and observation-only wording. |
| ECL-FR-517 | Four-layer progressive disclosure preserves complete methodology, exact evidence, normative package and accessible offline/print export. |

## Human evidence increment

| ID | Requirement |
| --- | --- |
| ECL-FR-518 | Present observation, human evidence details and optional technical audit through progressive disclosure; no JSON parsing required. |
| ECL-FR-519 | Canonical package remains unchanged normative machine artifact with clear download/helper and inert invisible embedding. |
| ECL-FR-520 | Sources, completeness, periods, finding methods/support and independent dimension evidence remain readable, exact and scope-qualified. |
| ECL-FR-521 | Print contains human evidence, excludes raw JSON; privacy, offline portability, validation and package parity remain intact. |

## Azure acquisition increment

| ID | Requirement |
| --- | --- |
| ECL-FR-522 | Acquire selected read-only Azure WI histories, repository PRs and definition-scoped builds into existing normative contracts. |
| ECL-FR-523 | One-command validated JSON/offline HTML, optionally composing an existing genuine Git report. |
| ECL-FR-524 | Explicit population/history/cutoff limitations and partial/failed/unsupported distinctions; approved alias privacy without inferred mapping/categories. |
| ECL-FR-525 | Preserve connection/profile/transport/metric compatibility and bounded runtime-only credential handling. |

## Executive-review UX increment

| ID | Requirement |
| --- | --- |
| ECL-FR-526 | Present the public landing page around the manager journey: evidence acquisition, normalization, independent analysis, review generation and component investigation. The landing and Engineering System Review SHALL use the same ECL application shell: dark navigation rail, navigation vocabulary, typography, spacing and responsive behavior. The technical explorer remains available as a secondary route. |
| ECL-FR-527 | Offer only honest review entry points: a clearly synthetic demonstration, a loopback Local Explorer for a local path or HTTPS Git clone URL (including Azure DevOps Server/on-prem), and a locally generated existing review. The browser SHALL not request, persist or transmit a PAT or accept URL credentials; an already configured local Git credential manager may be used by Git. The landing SHALL name what data each path uses; the generated review header SHALL identify its synthetic or locally generated evidence source. The Git URL path analyzes Git history only and does not claim Azure work-item/build acquisition. |
| ECL-FR-528 | Present an Engineering System Review with a manager-facing sidebar, exactly four executive KPI cards (Continuity, Delivery, Defects and Builds), attention findings, component investigation and methodology/evidence. KPI presentation does not introduce a combined score or alter assessment semantics. |
| ECL-FR-529 | Allow component search and show cross-dimension values only where the accepted package provides an exact component binding. Unbound traceability/verification values remain Unavailable; no relationship may be inferred for presentation. |
| ECL-FR-530 | Keep the HTML review offline, printable and auditable through its unchanged canonical evidence package and visible JSON download. The same generated-report presentation serves synthetic and genuine packages with provenance retained. |
| ECL-FR-531 | Reduce executive cognitive load through progressive disclosure: the Executive Review SHALL begin with a compact, deterministic selection of at most three accepted attention-finding groups and direct evidence-inspection anchors. The four independent executive dimensions, full finding inventory, component drill-down and methodology SHALL remain available as subsequent layers. This presentation SHALL not invent priorities, actions, causal explanations, health scores or favourable conclusions from unavailable evidence. |

Accepted handoffs: docs/v0.5-azure-engineering-review.md. Non-atomic live enumeration is deliberately PARTIAL.
