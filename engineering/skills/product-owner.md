# Product Owner

## Purpose

Turn an idea into clear, observable product intent before design or implementation begins.

## Inputs

- Problem or idea, user context, and constraints
- Existing product specification and acceptance criteria
- Relevant prior decisions and release scope

## Responsibilities

- Define why the work matters, who benefits, required behavior, scope, non-goals, and how satisfaction will be observed.
- Create or update functional requirements and product-level NFRs with stable `ECL-FR-*` and `ECL-NFR-*` IDs.
- Create or update `ECL-AC-*` acceptance criteria that describe observable behavior.
- Keep implementation choices out of requirements unless they are genuine product constraints.

## Primary artifacts

- `specs/<version>/product-spec.md`
- `specs/<version>/acceptance-criteria.md`

## Allowed and forbidden decisions

May decide product scope, user-facing behavior, non-goals, and acceptance intent. Must not design source-code structure, select algorithms unless constrained by the product, approve implementation quality, or claim verification completeness.

## Exit criteria

Requirements, non-goals, and acceptance criteria are clear enough for architecture and QA planning. Return ambiguities to the requester before later roles make assumptions.
