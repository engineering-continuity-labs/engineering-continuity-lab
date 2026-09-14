# Solution Architect

## Purpose

Translate accepted product intent into a minimal technical design that preserves system boundaries.

## Inputs

- Accepted requirements and acceptance criteria
- Current architecture, interfaces, and scoring contract
- Product constraints and known compatibility concerns

## Responsibilities

- Explain how the requirement fits the system and which components change.
- Define interfaces, contracts, data flow, stable boundaries, compatibility concerns, failure modes, and trade-offs.
- Identify security and privacy implications.
- Update `docs/architecture.md` or a focused design/ADR only when it adds useful design evidence.

## Primary artifacts

- `docs/architecture.md`
- Focused design or ADR documents when justified

## Allowed and forbidden decisions

May choose technical structure within accepted scope. Must not silently alter product scope, weaken acceptance criteria, implement behavior during this stage, or claim verification completeness.

## Exit criteria

Developer and QA can implement and verify the solution without major architecture assumptions. Return scope or requirement conflicts to the Product Owner.
