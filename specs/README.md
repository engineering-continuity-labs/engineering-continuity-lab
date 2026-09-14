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
