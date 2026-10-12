# v0.5 design traceability

Status: design chain only, runtime PLANNED. PO requirements/AC precede Architect contracts and QA cases. No runtime implementation or VERIFIED coverage implied.

| Requirement | Acceptance | Design | Implementation | Verification / review |
| --- | --- | --- | --- | --- |
| FR501–502 | AC501–502,518,521 | engineering-system-review composition/sections | NOT IMPLEMENTED | report/legacy cases PLANNED; independent design review required |
| FR503 | AC503–507,509 | delivery-flow identity/lifecycle/metrics | NOT IMPLEMENTED | named Delivery matrix PLANNED |
| FR504 | AC510–514 | quality-evidence lifecycle/fields/metrics | NOT IMPLEMENTED | named Quality matrix + exact planned Bug table |
| FR505 | AC508,522 | delivery builds/deployment decision | NOT IMPLEMENTED | category/sample/profile cases PLANNED; live MANUAL |
| FR506 | AC506,509,516 | delivery time/comparison contract | NOT IMPLEMENTED | UTC/boundary/equal-window/adequacy negatives PLANNED |
| FR507 | AC512,515 | composition component joins + quality mappings | NOT IMPLEMENTED | overlap/unmapped/snapshot negatives PLANNED |
| FR508–509 | AC517 | composition ER01–09 findings/investigations | NOT IMPLEMENTED | exact thresholds/ref/severity/no-cause cases PLANNED |
| FR510 | AC505,514,518 | per-dimension completeness axes | NOT IMPLEMENTED | partial/failed/unsupported/empty cases PLANNED |
| FR511 | AC519–521 | separate JSON/package/offline HTML | NOT IMPLEMENTED | canonical/markup/roundtrip/no-network/print PLANNED, OS MANUAL |
| FR512 | AC522 | both designs Azure operation/profile contracts | NOT IMPLEMENTED | synthetic later; deployment/live MANUAL |
| FR513 | AC504,508,510,513,516,520 | Atlas hand-worked source oracle | NOT IMPLEMENTED | no generated/executed fixture claimed |
| NFR501 | AC519 | allowlisted public boundary | NOT IMPLEMENTED | privacy automation PLANNED; origin approval MANUAL |
| NFR502–503 | AC503,505–506,509,514,516–520 | deterministic/bounded/qualified measurement | NOT IMPLEMENTED | negative/parity/sampling checks PLANNED |
| NFR504–505 | AC502,521–522 | governance, roadmap decision and legacy boundaries | docs only | independent design review + unchanged baseline CI required |

Paths refer to `docs/v0.5-*.md`. Independent design APPROVE, V05-R01 MINOR VERIFIED CLOSED, no unresolved findings. This approves specification, not runtime implementation. Recorded findings and actual documentation/CI gates: `docs/validation/v0.5-engineering-system-review-design.md` (local baseline passed; final pushed-head CI required). Historical v0.1–v0.4 specs remain unmodified. Proposed roadmap moves handover to v0.6 explicitly in the PO decision; package remains0.2.0, no tag/release/runtime implementation.
