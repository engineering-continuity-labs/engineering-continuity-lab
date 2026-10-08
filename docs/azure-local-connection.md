# Local Azure connection design

Architect handoff: `continuity azure-acquire --config FILE --approve-publication [--anonymous]` is isolated from Git analysis commands. A dedicated CLI adapter validates a bounded (1 MiB) UTF-8 TOML document before prompting or constructing transport. Required tables are connection, publication and identities; optional limits use existing AzureLimits. Exact allowed keys/types are checked; no secret keys or HTTP bypass accepted.

Connection data remains adapter-private. Existing profile/map validation owns URLs, versions, GUIDs, alias grammar, limits and revisions. The adapter owns strict TOML structure and timezone-aware time input. Publication approval covers aliases, commit hashes and repository-relative paths; syntax is not certification. Prompting requires interactive stdin, uses getpass with fallback warnings treated as failure, and never reads credentials from argv/config/environment.

Existing transport performs all bounded reads, existing derive owns components/coverage, and existing serializer owns standalone report-v3 traceability-section output. The adapter builds output fully before stdout, preserves completeness and emits only fixed error categories. No domain/report/browser/scoring changes. Tests inject the existing synthetic transport through mocks; production exposes no loopback HTTP setting.

Exit codes: COMPLETE 0, invalid input/authentication/processing 2, PARTIAL 3, FAILED 4. Acquisition failure can still yield a truthful FAILED report; it is not a promise that authentication succeeded. Network is read-only, TLS verified. No local output file or credential persistence is introduced.

## Usage

Copy `examples/azure-connection.toml` to a private local file, replace the synthetic native GUIDs/base/collection/revision, and explicitly approve each public scope/artifact alias and repository-relative path. Keep the native connection file private; it is non-secret with respect to credentials, not public metadata. The identity tables map numeric native IDs to approved aliases; unapproved discovered IDs stay quarantined with partial evidence. Update the fingerprint whenever the map changes. `collected_at` is an explicit timezone-aware selection instant, not an atomic Azure snapshot guarantee. Component depth is 1–32. Optional `[limits]` uses the existing bounded provider limits.

```sh
continuity azure-acquire --config /private/location/azure.toml --approve-publication
# A hidden terminal prompt requests the runtime PAT. No PAT flag or env lookup.
# Explicit anonymous reads also work without an interactive terminal:
continuity azure-acquire --config /private/location/azure.toml --approve-publication --anonymous
```

Stdout contains a standalone report-v3 `traceability_evidence` section, accepted by `traceability_from_json`. It is **not** a browser-importable Git report envelope; this command has no Git scoring evidence and does not invent it. A library caller can attach the derived report to a genuine compatible Git report via existing `with_traceability`. Explorer integration and visualization remain deferred. Shell redirection is caller-managed; check exit status before using a redirected file because shell redirection can create an empty file on errors. A nonzero PARTIAL/FAILED exit still contains a valid evidence section.

The CLI does not verify publication rights, PAT read-only scopes, live deployment compatibility or clock/snapshot correctness. Use code/work-item read access and a dedicated non-sensitive environment for live validation. Never place credentials in the TOML file; unknown keys, including PAT/auth fields, are rejected before any read request.

Architect correction LC-R01: Azure-scoped argparse failures, including unknown options and values, must enter the same fixed diagnostic/exit-2 boundary before loading config/prompt/network. Standard argparse help remains available; existing Git command argument errors keep their prior behavior. QA adds CLI secret/unknown option/private config path rejection checks.
