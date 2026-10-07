# v0.2 traceability matrix

**Scope of implementation:** public GitHub provider, provider-neutral evidence domain, deterministic aggregation, and local explorer review-evidence view. The bounded provider intentionally labels pagination as PARTIAL. Existing Git scoring stays unchanged.

| Spec ID | Acceptance criteria | Design | Planned implementation | Planned verification | Status |
| --- | --- | --- | --- | --- | --- |
| ECL-FR-201–206; ECL-NFR-201–204 | ECL-AC-201–205, 214–215, 218 | `docs/review-evidence.md` | `domain/reviews.py`; `analysis/reviews.py`; `review_providers/github.py` | Fixture/provider tests, credential-free provenance and collection-status cases | PARTIAL |
| ECL-FR-207–212 | ECL-AC-206–212 | `docs/review-evidence.md` | `analysis/reviews.py`; local explorer review-evidence view | Deterministic aggregation, mapping and explorer tests | PARTIAL |
| ECL-FR-213–216; ECL-NFR-205 | ECL-AC-213, 216 | `docs/review-evidence.md` | bounded GitHub adapter and additive local explorer field | Repeated fixture derivation plus v0.1 suite regression | PARTIAL |
| ECL-FR-217; ECL-NFR-206 | ECL-AC-217 | `docs/review-evidence.md` | `review_providers/github.py` bounded public collection | 2026-10-07 dotnet/eShop run: `PARTIAL`, one merged PR in the latest 20 closed PRs | MANUAL |

No v0.2 requirement is VERIFIED: bounded public-provider collection, additive explorer integration, and live-provider validation remain PARTIAL or MANUAL until pagination, exported-report versioning, and repeatable validation fixtures are complete.
