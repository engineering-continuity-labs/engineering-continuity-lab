# v0.1 traceability matrix

**Status values:** VERIFIED means an explicit automated check exists; PARTIAL means some evidence exists but no criterion-specific automated assertion; MANUAL means review is required.

| Spec ID | Acceptance criteria | Implementation | Verification | Status |
| --- | --- | --- | --- | --- |
| ECL-FR-001, 002, 017 | ECL-AC-001, 002, 003 | `src/continuity/git/history.py` | `tests/test_git_history.py` | VERIFIED |
| ECL-FR-022 | ECL-AC-023–026 | `src/continuity/cli.py` | `tests/test_git_history.py` | VERIFIED |
| ECL-FR-023, ECL-NFR-010 | ECL-AC-027–029 | `src/continuity/explorer.py`, `src/continuity/cli.py`, `ui/dist/app.js`, `ui/dist/index.html` | `tests/test_explorer.py`, static JavaScript checks | PARTIAL — local API and CLI dispatch are automated; rendered browser interaction remains manual. |
| ECL-FR-024–027, ECL-NFR-011 | ECL-AC-030–034 | `src/continuity/git/source.py`, `src/continuity/cli.py`, `docs/architecture.md` | `tests/test_repository_source.py`, `tests/test_git_history.py` | VERIFIED — real disposable repositories exercise full clone integration through a mocked transport; CI does not require external network access. |
| ECL-FR-003 | ECL-AC-004 | `src/continuity/domain/models.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-004–006, 018–019; ECL-SC-001–017 | ECL-AC-005–008, 011 | `src/continuity/analysis/service.py`, `src/continuity/scoring/model.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-007 | ECL-AC-009–010 | `src/continuity/analysis/service.py`, `src/continuity/cli.py` | `tests/test_git_history.py`, `tests/test_scoring.py` | VERIFIED |
| ECL-FR-008–009; ECL-SC-016–019 | ECL-AC-011–014 | `src/continuity/analysis/service.py` | `tests/test_scoring.py` | VERIFIED |
| ECL-FR-010–011 | ECL-AC-019 | `src/continuity/cli.py`, `src/continuity/reporting/text.py` | `tests/test_git_history.py`, `tests/test_reporting.py` | VERIFIED |
| ECL-FR-012–016 | ECL-AC-015–018 | `src/continuity/analysis/filtering.py`, `src/continuity/cli.py` | `tests/test_filtering.py`, `tests/test_git_history.py` | VERIFIED |
| ECL-FR-020; ECL-SC-016–019 | ECL-AC-020 | `ui/dist/model.js`, `ui/dist/app.js`, `ui/dist/index.html` | `ui/tests/model.test.js` | PARTIAL — model and departure calculations are tested; rendered UI behavior is not automated. |
| ECL-FR-029 | ECL-AC-036 | `ui/dist/app.js`, `ui/dist/index.html` | static JavaScript checks, manual browser review | PARTIAL — terminology is statically checked; rendered language remains a manual review. |
| ECL-FR-030–032; ECL-NFR-012–013 | ECL-AC-037–042 | `ui/dist/`, `.github/workflows/pages.yml`, `docs/github-pages.md` | `ui/tests/pages-static.test.js`, `ui/tests/model.test.js`, static JavaScript checks | PARTIAL — static contracts and demo data are automated; hosted deployment, browser privacy behavior, and responsive rendering require manual verification. |
| ECL-FR-033–034; ECL-NFR-014 | ECL-AC-043–045 | `src/continuity/explorer.py`, `src/continuity/cli.py`, `ui/dist/app.js`, `ui/dist/index.html` | `tests/test_explorer.py`, static JavaScript checks | PARTIAL — API and CLI dispatch are automated; rendered export/import and browser-launch fallback remain manual. |
| ECL-FR-037 | ECL-AC-050 | `ui/dist/index.html` | `ui/tests/pages-static.test.js` | VERIFIED |
| ECL-FR-038 | ECL-AC-051 | `ui/dist/eshop-report.js`, `ui/dist/app.js`, `ui/dist/index.html` | `ui/tests/model.test.js`, `ui/tests/pages-static.test.js` | PARTIAL — report identity and static import are automated; browser boot and hosted deployment remain manual checks. |
| ECL-FR-039 | ECL-AC-052 | `ui/dist/index.html`, `ui/dist/pages.css` | `ui/tests/pages-static.test.js` | PARTIAL — action labels are statically checked; hover and keyboard-visible tooltips require browser review. |
| ECL-FR-040 | ECL-AC-053 | `ui/dist/index.html`, `ui/dist/pages.css` | `ui/tests/pages-static.test.js` | PARTIAL — initial view and compact layout are statically checked; rendered density remains manual. |
| ECL-FR-021 | ECL-AC-021 | `ui/dist/model.js`, `ui/dist/app.js` | `ui/tests/model.test.js` | VERIFIED |
| ECL-NFR-001 | — | `pyproject.toml` | CI Python 3.12 configuration | VERIFIED |
| ECL-NFR-002 | ECL-AC-006 | `src/continuity/analysis/service.py`, `src/continuity/scoring/model.py` | `tests/test_scoring.py` | PARTIAL — fixed-reference guard is tested; full repeated CLI output is not. |
| ECL-NFR-003, 008 | — | `src/continuity/scoring/model.py`, `README.md`, `specs/` | Documentation review | MANUAL |
| ECL-NFR-004, 007 | ECL-AC-001 | `src/continuity/git/history.py` | `tests/test_git_history.py` | PARTIAL — Git reads are exercised; no dedicated mutation assertion exists. |
| ECL-NFR-005 | ECL-AC-022 | `ui/dist/app.js`, `ui/dist/index.html` | Static source review | MANUAL |
| ECL-NFR-006 | — | `pyproject.toml`, `ui/` | Dependency manifest review | MANUAL |
| ECL-NFR-009 | ECL-AC-002 | `src/continuity/git/history.py`, `src/continuity/analysis/service.py` | `tests/test_git_history.py`, `tests/test_scoring.py` | VERIFIED |

No implementation/spec mismatch was found during this conversion. The visible gaps are browser rendered-flow coverage, a repeated end-to-end determinism assertion, explicit repository non-mutation testing, and objectively verified browser-local-only behavior.
