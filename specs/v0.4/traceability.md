# v0.4 offline core and isolated synthetic demo traceability

Accepted design is implemented for the offline increment below. Generic report-envelope v4 import, CLI and live adapters remain deferred. Automated evidence is synthetic; origin approval and live/visual verification remain MANUAL. Historical design gate: `docs/validation/v0.4-design-verification.md`.

| Requirements | Acceptance | Architecture/design | Implementation | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| FR401–402 | AC401–402 | Typed refs/legal grammar | domain/verification.py | identity/grammar negatives | VERIFIED |
| FR403–404 | AC403–404 | Exact snapshot join/code projection | analysis/verification.py | snapshot/target/membership tests | VERIFIED |
| FR405–406 | AC405–406,416 | Qualification/conflict boundary | domain + analysis/verification.py | version/stale/conflict/multiple-run tests | VERIFIED |
| FR407 | AC407,410 | Scoped completeness | analysis/verification.py | missing/partial/unsupported/conflicting lookup tests | VERIFIED |
| FR408–409 | AC408–410 | Distinct selected populations | analysis/verification.py | exact BASE four dimensions/outcomes, empty/zero tests | VERIFIED |
| FR410 | AC411,416 | Auditable explanations | analysis/reporting verification.py; ui/dist/verification.js | paths/gaps/qualification rendering tests | VERIFIED / MANUAL visual |
| FR411 | AC412 | Stable ordering | analysis/reporting verification.py | permutation/duplicate/timezone tests; bundle --check | VERIFIED |
| FR412 | AC415 | Isolated rollout | existing v1/v2/v3 unchanged | complete legacy regression; demo import rejection | VERIFIED compatibility / deferred general v4 |
| FR413–414 | AC417–418 | Isolated synthetic demo | generator, sample, verification.js, app.js | verification-ui.test.js actual handlers/export/escaping | VERIFIED / MANUAL visual |
| NFR401–402 | AC413 | Private/public boundary | domain/verification.py; allowlisted reporting | privacy sentinels; synthetic source only | VERIFIED synthetic / MANUAL origin approval |
| NFR403–404 | AC414–415 | Bounded pure graph | domain/analysis verification.py | limits/exhaustion/no mutation tests | VERIFIED |
| NFR405 | AC401–418 | Role handoffs | specs/design/QA before runtime | independent runtime review and CI recorded in validation | Independent APPROVE; CI required before merge |
| NFR406 | AC403,405–406,416 | Historical provenance | typed snapshots/runs + serializer | version/target/time/outcome tests | VERIFIED synthetic / MANUAL live |

Implementation paths are under `src/continuity/`. Automated Python evidence is `tests/test_verification_evidence.py`; browser evidence is `ui/tests/verification-ui.test.js` plus legacy tests. Exact validation and review: `docs/validation/v0.4-offline-demo-verification.md`. VERIFIED refers to the named automated scope, not live correctness or unperformed manual browser interaction. Package remains 0.2.0; no release/tag created.


## Product experience increment (independent APPROVE; final-head CI required)

| Requirement | Acceptance | Design | Implementation | Verification |
| --- | --- | --- | --- | --- |
| FR421 | AC425,431 | product-experience-v0.4 PO journey | app.js/index.html/pages.css | product-experience.test.js navigation/native structure |
| FR422 | AC426,430 | explicit selected source/context | generator/showcase.js + app.js | actual source/upload/export/context tests |
| FR423 | AC427 | existing review derivation | scripts/generate_showcase.py | test_product_showcase.py exact oracle; browser validator |
| FR424 | AC428 | distinct selected PR units/full metrics | experience.js | full-source4/6, requirement2/4, null/absent tests |
| FR425 | AC429 | concise story + full inspectors | experience.js + original renderers | path/review/observation/safe text tests |
| FR426 | AC430 | unavailable/source/version terminology | app/index/presenters | missing states, sample isolation, no stale header |
| FR427 | AC431 | native controls/wrapped UI | app/index/pages.css | actual handlers/keyboard hooks/full legacy regression; OS visual MANUAL |

Final evidence and independent review: docs/validation/v0.4-product-experience-verification.md. No portable backend, version bump/release/tag or v0.5 work is claimed. FR415–420/AC419–424 are reserved by the separate unfinished portable branch and are not reused.
