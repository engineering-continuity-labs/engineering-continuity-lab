# Engineering workflow

Engineering Continuity Lab uses a spec-driven workflow for AI-assisted and human-assisted changes. The source of truth for product behavior remains `specs/`; these rules govern how changes move from an idea to merge.

## Change classes

**Behavioral or architectural changes** include any observable product behavior, public contract, scoring behavior, data model, persistence, provider boundary, security/privacy boundary, or architecture decision. They must use every role below, in order:

`Problem / Idea → Product Owner → Solution Architect → QA Engineer → Developer → Code Reviewer → CI / Verification → Merge`

**Trivial non-behavioral changes** are limited to typos, formatting, and comment-only edits. They may use a reduced workflow, but still require relevant review and CI. A behavior change must never be classified as trivial.

Later roles must not silently alter decisions owned by earlier roles. Record a needed change and return the work to the owning role instead.

## Roles and handoffs

| Role | Inputs | Responsibilities and allowed decisions | Outputs | Forbidden decisions | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| Product Owner | Problem or idea, existing specs, user context | Define value, scope, non-goals, observable requirements, product NFRs, acceptance criteria, and stable Spec IDs. | Updated product spec and acceptance criteria. | Source structure, algorithms except product constraints, implementation approval, verification-complete claims. | Requirements and acceptance criteria are clear enough for design and QA. |
| Solution Architect | Accepted requirements and acceptance criteria, current architecture | Choose how requirements fit the system; define boundaries, affected components, interfaces, data flow, compatibility, privacy/security risks, failure modes, and trade-offs. | Updated architecture documentation or focused design/ADR when justified. | Product-scope changes, weakened acceptance criteria, implementation, verification-complete claims. | Developer and QA can proceed without major architecture assumptions. |
| QA Engineer | Requirements, acceptance criteria, architecture | Plan positive, negative, boundary, regression, integration, and necessary manual verification. Map evidence honestly to requirements. | Updated acceptance criteria, traceability, and test plan or tests as appropriate. | Fabricated coverage, unsupported VERIFIED status, product-intent changes, weakened criteria. | A pre-development verification strategy exists; after development, remaining gaps are PARTIAL or MANUAL. |
| Developer | Accepted requirements, architecture, QA plan | Implement the agreed behavior minimally, preserve compatibility and determinism where required, and add QA-defined automated checks. | Implementation, tests, updated traceability implementation references. | Invented requirements, silent behavior or scoring changes, architecture bypass, self-approval, unsupported VERIFIED status. | Accepted requirements are implemented and local automated validation passes. |
| Code Reviewer | Requirement-to-verification chain and complete diff | Independently assess specification compliance, architecture, interfaces, errors, privacy/security, edge cases, tests, traceability, docs, and unrelated changes. | Findings with severity and a review decision. | Silent implementation rewrites or approval of their own developer work. | No unresolved BLOCKER or MAJOR findings. |

The detailed role instructions live in `engineering/skills/`.

## Escalation and merge rules

- Requirement ambiguity returns to the Product Owner.
- Architecture conflict or a missing contract returns to the Solution Architect.
- An untestable acceptance criterion returns to the Product Owner and Solution Architect.
- Missing or inadequate verification returns to QA and Developer.
- A BLOCKER or MAJOR review finding prohibits merge until resolved and re-reviewed.
- CI or required validation failure prohibits merge until repaired and rerun.
- Merge requires the applicable workflow exit criteria, recorded review outcome, and green relevant CI.

## Traceability

Maintain this lifecycle where it applies:

`Spec ID → Acceptance Criterion → Architecture / Design → Implementation → Verification → Review status`

Do not create artificial architecture artifacts merely to populate a table. A small change may correctly reference existing architecture. Keep `VERIFIED`, `PARTIAL`, and `MANUAL` statuses evidence-based.
