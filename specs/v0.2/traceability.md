# v0.2 traceability matrix

**Scope of implementation PR:** provider-neutral evidence domain and deterministic fixture-driven aggregation only. No provider client, report schema, CLI, UI, or scoring code exists in this change.

| Spec ID | Acceptance criteria | Design | Planned implementation | Planned verification | Status |
| --- | --- | --- | --- | --- | --- |
| ECL-FR-201–206; ECL-NFR-201–204 | ECL-AC-201–205, 214–215, 218 | `docs/review-evidence.md` | `domain/reviews.py`; `analysis/reviews.py` | `tests/test_review_evidence.py` fixtures, credential-free provenance and collection-status cases | PARTIAL |
| ECL-FR-207–212 | ECL-AC-206–212 | `docs/review-evidence.md` | `analysis/reviews.py` | `tests/test_review_evidence.py` deterministic aggregation and mapping fixtures | PARTIAL |
| ECL-FR-213–216; ECL-NFR-205 | ECL-AC-213, 216 | `docs/review-evidence.md` | `analysis/reviews.py`; no report integration | Repeated fixture derivation plus v0.1 suite regression | PARTIAL |
| ECL-FR-217; ECL-NFR-206 | ECL-AC-217 | `docs/review-evidence.md` | Future public-provider validation harness | Documented dotnet/eShop collection run; optional secondary-repository justification | MANUAL |

No v0.2 requirement is VERIFIED: provider acquisition, additive report/CLI/UI integration, and public-provider validation remain future work.
