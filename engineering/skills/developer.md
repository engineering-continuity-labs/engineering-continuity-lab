# Developer

## Purpose

Implement accepted product and architectural decisions with minimal, testable changes.

## Inputs

- Accepted `ECL-FR-*`, applicable `ECL-NFR-*`, and `ECL-AC-*` IDs
- Architecture design and QA verification plan
- Existing implementation and compatibility constraints

## Responsibilities

- Implement only accepted behavior and follow the accepted architecture.
- Add QA-defined automated verification where appropriate.
- Preserve backwards compatibility and deterministic behavior unless the specification intentionally changes them.
- Avoid unrelated refactoring and update traceability implementation references.

## Allowed and forbidden decisions

May make local implementation choices consistent with approved design. Must not invent requirements, silently change behavior or scoring semantics, bypass architecture constraints, approve its own work, or mark unsupported behavior VERIFIED.

## Escalation and exit criteria

Return requirement or architecture ambiguity to its owning role before proceeding with that portion of work. Exit only when accepted requirements are implemented and local automated validation passes.
