# Traceability Explorer design

Architect handoff: add a Traceability tab to the current static/local explorer shell. A dedicated pure presentation module consumes only already-validated traceability evidence from existing validateReport/importReport. It renders collection status, dimension counts, boundaries, artifact states, ordered paths/supports and gap reasons. It never derives new status/coverage, joins Git to Azure or turns aliases into native links. The app owns three labelled filters and resets them at report load. Complete evidence export stays in the existing handler.

Component filter matches typed component references in paths; status filter matches existing path status; text search matches typed artifact references in paths. Global counts/boundaries/gaps/artifacts remain visible and are labelled as full report; filtered path counts are separate. A synthetic report sample is generated from the existing BASE producer into a checked-in module, with no personal/real Azure data. Original Git scoring panels are unchanged. Missing traceability has an explicit unavailable state.

Render escape helpers cover all dynamic HTML, details retain semantic node/support order and textual status labels avoid reliance on color. No URL building/network/persistence/auth. CSS enables readable wrap and responsive controls/tables. Tests exercise pure projection and actual app handlers; new UI tests join CI. No domain/report/model/schema changes.

## Usage and interpretation

Choose the Traceability tab and open the synthetic sample, or use the existing Open saved JSON action with a validated full v3 Git report containing traceability evidence. Legacy reports show unavailable. Standalone `azure-acquire` sections still need a genuine Git report envelope via existing library integration before browser import; this feature does not merge evidence or acquire Azure data.

Expand a path to inspect exact typed/scoped references, mapping configuration/hash algorithm, supporting hop origins and observations, source boundaries and unresolved reasons. Component/status/artifact search filters only path display; full-report coverage/artifact/gap/lookup sections retain original totals. Source details expose declared collection/query/revision/time bounds, not a live consistency guarantee. VERIFIED is connection evidence, not understanding or business correctness. Null coverage is unavailable, including empty denominators. PARTIAL/FAILED collection badges remain visible independently. Export/reopen preserves the original validated report.

Accessibility/visual QA: native labelled selects/search, textual statuses, keyboard-native details and responsive wrap CSS are implemented and automated hooks tested. Actual OS/browser responsive/keyboard/screenshot inspection remains MANUAL because Computer Use returned “Computer Use permissions are not granted”; no successful visual check is claimed.
