# Specification governance

Specifications define expected observable behavior. Documentation explains architecture, rationale, usage, and validation evidence. `src/` implements the specifications, and tests provide verification evidence.

The lifecycle is: **Problem → Specification → Acceptance Criteria → Architecture / Implementation → Verification → Traceability**. New product behavior starts with a specification change. A behavioral change identifies its affected Spec IDs before implementation, and its acceptance criteria and traceability are updated with verification evidence.

## Statuses

- **Draft** — proposed behavior, not yet approved.
- **Accepted** — approved intended behavior.
- **Implemented** — implemented but not yet fully verified.
- **Verified** — implemented with recorded verification evidence.
- **Superseded** — replaced by a later specification; retain it for history.

## Stable identifiers

- `ECL-FR-xxx`: Functional Requirement
- `ECL-NFR-xxx`: Non-Functional Requirement
- `ECL-SC-xxx`: Scoring Contract
- `ECL-AC-xxx`: Acceptance Criterion

## Rules

1. New product behavior requires a specification change first.
2. Behavioral changes identify affected Spec IDs.
3. Implementation is traceable to specifications.
4. Verification evidence is traceable to acceptance criteria.
5. A specification describes observable behavior, not implementation detail, unless an implementation constraint is intentional.
6. Unknown or unverified behavior is stated explicitly rather than inferred.
7. Experimental assumptions remain visible.

v0.1 specifications are in [v0.1](v0.1/). They are normative for implemented v0.1 behavior; material that explains why or how belongs in `docs/`.

v0.2 specification and design work is in [v0.2](v0.2/). It defines implemented public PR/review evidence behavior, additive report compatibility, and evidence-based verification status. Git-only v0.1 scoring remains unchanged.


v0.3 [specifications](v0.3/product-spec.md) now cover implemented offline traceability, report v3, read-only Azure library/local CLI and the Traceability Explorer. [Traceability](v0.3/traceability.md) scopes automated evidence and remaining MANUAL live/visual checks; no v0.3 release is claimed. Trace status, collection status and governance verification are separate concepts.

v0.4 [product design](v0.4/product-spec.md), [QA plan](v0.4/acceptance-criteria.md), [planned traceability](v0.4/traceability.md) and [architecture](../docs/v0.4-evidence-design.md) define the next requirements/test/architecture increment. No v0.4 runtime verification is claimed. v0.5 remains roadmap-only.
