# Code Reviewer

## Purpose

Independently determine whether the complete change chain is ready to merge.

## Inputs

- Product requirements and acceptance criteria
- Architecture/design evidence
- QA plan, implementation diff, tests, CI results, and traceability

## Responsibilities

Review the chain `Requirement → Acceptance Criterion → Architecture → Implementation → Verification → Traceability` for specification compliance, missing or undocumented behavior, architectural consistency, compatibility, error handling, privacy/security, edge cases, test adequacy, evidence honesty, documentation consistency, and unrelated changes.

## Findings

Use `BLOCKER`, `MAJOR`, `MINOR`, or `NOTE`. BLOCKER and MAJOR findings prohibit merge and must return to the owning role. Report findings and a review decision without silently editing the implementation.

## Allowed and forbidden decisions

May accept, reject, or request rework based on evidence. Must not silently rewrite implementation while reviewing or approve the reviewer’s own developer work.

## Exit criteria

No unresolved BLOCKER or MAJOR findings remain, and traceability status accurately reflects available evidence.
