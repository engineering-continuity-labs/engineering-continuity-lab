# v0.1 traceability matrix

**Status values:** VERIFIED means an explicit automated check exists; PARTIAL means some evidence exists but no criterion-specific automated assertion; MANUAL means review is required.

| Spec ID | Acceptance criteria | Implementation | Verification | Status |
| --- | --- | --- | --- | --- |
| ECL-FR-001, 002, 017 | ECL-AC-001, 002, 003 | `src/continuity/git/history.py` | `tests/test_git_history.py` | VERIFIED |
| ECL-FR-003 | ECL-AC-004 | `src/continuity/domain/models.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-004–006, 018–019; ECL-SC-001–017 | ECL-AC-005–008, 011 | `src/continuity/analysis/service.py`, `src/continuity/scoring/model.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-007 | ECL-AC-009–010 | `src/continuity/analysis/service.py`, `src/continuity/cli.py` | `tests/test_git_history.py`, `tests/test_scoring.py` | VERIFIED |
| ECL-FR-008–009; ECL-SC-016–019 | ECL-AC-011–014 | `src/continuity/analysis/service.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-010–011 | ECL-AC-019 | `src/continuity/cli.py`, `src/continuity/reporting/text.py` | `tests/test_git_history.py`, `tests/test_reporting.py` | VERIFIED |
| ECL-FR-012–016 | ECL-AC-015–018 | `src/continuity/analysis/filtering.py`, `src/continuity/cli.py` | `tests/test_filtering.py`, `tests/test_git_history.py` | VERIFIED |
| ECL-FR-020; ECL-SC-016–019 | ECL-AC-020 | `ui/dist/model.js`, `ui/dist/app.js`, `ui/dist/index.html` | `ui/tests/model.test.js` | PARTIAL — model and departure calculations are tested; rendered UI behavior is not automated. |
| ECL-FR-021 | ECL-AC-021 | `ui/dist/model.js`, `ui/dist/app.js` | `ui/tests/model.test.js` | VERIFIED |
| ECL-NFR-001 | — | `pyproject.toml` | CI Python 3.12 configuration | VERIFIED |
| ECL-NFR-002 | ECL-AC-006 | `src/continuity/analysis/service.py`, `src/continuity/scoring/model.py` | `tests/test_scoring.py` | PARTIAL — fixed-reference guard is tested; full repeated CLI output is not. |
| ECL-NFR-003, 008 | — | `src/continuity/scoring/model.py`, `README.md`, `specs/` | Documentation review | MANUAL |
| ECL-NFR-004, 007 | ECL-AC-001 | `src/continuity/git/history.py` | `tests/test_git_history.py` | PARTIAL — Git reads are exercised; no dedicated mutation assertion exists. |
| ECL-NFR-005 | ECL-AC-022 | `ui/dist/app.js`, `ui/dist/index.html` | Static source review | MANUAL |
| ECL-NFR-006 | — | `pyproject.toml`, `ui/` | Dependency manifest review | MANUAL |
| ECL-NFR-009 | ECL-AC-002 | `src/continuity/git/history.py`, `src/continuity/analysis/service.py` | `tests/test_git_history.py`, `tests/test_scoring.py` | VERIFIED |

No implementation/spec mismatch was found during this conversion. The visible gaps are browser rendered-flow coverage, a repeated end-to-end determinism assertion, explicit repository non-mutation testing, and objectively verified browser-local-only behavior.
