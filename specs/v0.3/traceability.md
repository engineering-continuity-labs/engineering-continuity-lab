# v0.3 traceability of the traceability feature

**Status: ACCEPTED design baseline; runtime NOT IMPLEMENTED.** The feature's proposed runtime trace-path label VERIFIED is different from verification status in this matrix. No runtime requirement is VERIFIED by this design/specification PR. `ACCEPTED` means specified intended behavior and planned evidence, not that future code exists or passes tests.

Architecture references D301–D311 resolve to `docs/traceability-evidence.md`. All implementation/test filenames below are **planned**, absent from this change. Current existing files are used only as design inputs. Product Owner → Solution Architect → QA handoffs are recorded in the corresponding documents; Developer delivers documentation and stops before product implementation at the user's explicit instruction.

| Spec ID | Acceptance criteria | Design | Planned implementation | Planned verification | Status |
| --- | --- | --- | --- | --- | --- |
| ECL-FR-301 | ECL-AC-301, 319 | D301, D302, D310 | `domain/traceability.py`: minimum immutable WI values | synthetic domain/optional-field cases | ACCEPTED |
| ECL-FR-302, 323; ECL-NFR-311 | ECL-AC-322, 332 | D301, D305, D309 | later `traceability_providers/azure_devops.py` profile boundary | Services/Server capability/continuation fixtures; live compatibility MANUAL later | ACCEPTED |
| ECL-FR-303; ECL-NFR-303, 308 | ECL-AC-302, 308, 324–325, 333 | D302, D303, D306 | provenance/boundary/reference values | scoped joins, source timestamps, deterministic snapshot cases | ACCEPTED |
| ECL-FR-304, 325 | ECL-AC-302, 305, 308, 318, 334 | D303, D304 | typed observed links and supported projection rules | direct/source/derived label/support fixtures | ACCEPTED |
| ECL-FR-305, 311–312 | ECL-AC-308, 310–311, 334–335 | D303–D306 | `analysis/traceability.py`: typed paths and hop gaps | complete and short-chain fixtures with ordered support refs | ACCEPTED |
| ECL-FR-306 | ECL-AC-302–303, 309 | D303, D305, D307 | scoped WI_PR observations | one-to-many/many-to-one/direct-absence fixtures | ACCEPTED |
| ECL-FR-307 | ECL-AC-305, 310, 313 | D303, D305, D307 | independent WI_COMMIT observations | direct-only/no-intent fixtures; no invented WI_PR | ACCEPTED |
| ECL-FR-308 | ECL-AC-304, 311, 325 | D303, D306, D308 | PR membership refs/projection | several commits, empty membership, outside-Git-revision cases | ACCEPTED |
| ECL-FR-309–310 | ECL-AC-306–307, 325, 334 | D302, D303, D308 | immutable Git/change projection and existing ComponentStrategy | exact revision/path/multicomponent/configuration tests | ACCEPTED |
| ECL-FR-313–315, 322; ECL-NFR-310 | ECL-AC-309–313, 320–322, 327, 335 | D305–D307 | per-population/per-hop capability and lookup evidence | complete-empty vs missing/partial/failed/unsupported fixtures | ACCEPTED |
| ECL-FR-316–317, 328; ECL-NFR-302 | ECL-AC-314–316, 323–324 | D302, D304 | canonical ordering, duplicate isolation and bounded path grammar | permutation, collision, contradictory duplicate and cycle fixtures | ACCEPTED |
| ECL-FR-318 | ECL-AC-315, 317–319 | D302–D305 | validation/quarantine of required evidence | malformed IDs/paths/types/time/kinds, absent optional data | ACCEPTED |
| ECL-FR-319 | ECL-AC-324–325, 333 | D306 | eligibility and boundary compatibility projection | incompatible windows/revisions/depth/alias maps; no text/author inference | ACCEPTED |
| ECL-FR-320; ECL-NFR-307 | ECL-AC-328–329, 336 | D308 | immutable joins; later coordinated report/consumer extension | existing v0.1/v0.2 regressions and future no-mutation/round-trip tests | ACCEPTED |
| ECL-FR-321; ECL-NFR-304–306, 313 | ECL-AC-301, 330–331, 333 | D302, D310 | allowlists, safe aliases, sanitized diagnostic values | synthetic sentinels, no-person/no-inference negative cases; origin review | ACCEPTED |
| ECL-FR-324 | ECL-AC-301–327, 330–335 | D311; QA fixture manifest | planned labelled `tests/fixtures/traceability/` + fixture-only provider | BASE oracles and named variants in acceptance criteria | ACCEPTED |
| ECL-FR-326–327 | ECL-AC-326–327, 334–335, 337, 339 | D305, D307, D308 | four independent artifact coverage results; later presenter | population/count/dedup/null ratios; future artifact-only content review | ACCEPTED |
| ECL-NFR-301, 312 | ECL-AC-301, 332–333 | D301, D309 | offline core/provider boundary | domain dependency and fixture-network-isolation tests | ACCEPTED |
| ECL-NFR-309 | ECL-AC-336, 338 | D308, D311 | later additive versioned schema/types | future consumer migration/version/unsupported-kind tests | ACCEPTED |

## Verification classes and review gate

- **Design integrity:** document/spec-chain review, unique/referenced stable IDs and explicit future oracles. Independent review result is recorded in `docs/validation/v0.3-design-review.md` when performed.
- **Existing baseline regression:** full v0.1/v0.2 Python/mypy/browser/static/wheel checks recorded in `docs/validation/v0.3-design-verification.md` when run. A green baseline does not verify v0.3 runtime semantics.
- **Future runtime verification:** all matrix rows remain ACCEPTED/planned until their implementation plus fixture checks exist. Tests are not fabricated as existing coverage.
- **MANUAL future live checks:** actual Services/Server deployment versions, enterprise trust/auth/network and any optional public live project are unvalidated; synthetic capability profiles do not establish actual Server support.
- **PARTIAL design delivery:** if PR creation/remote CI is blocked by external permissions, record it exactly; do not call the proposed feature implemented or remote CI green.

## Recommended next PR and open gates

After this design PR is accepted, request a separate offline implementation change as described by D311: immutable domain, fixture-only provider, typed derivation/status/coverage and QA synthetic cases; existing Git/PR ownership reused. No live adapter, UI/CLI/auth/report producer/consumer rollout or v0.4 work in that first implementation PR. Exact deployment versions, live authentication/trust policy, endpoint budgets, safe private alias-map persistence, UI layout and concrete serialized v3 migration are later explicit owning-role gates, not hidden Developer choices. No implementation begins in this task.
