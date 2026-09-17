# v0.1 acceptance criteria

**Status:** Verified unless traceability marks an item PARTIAL or MANUAL. These criteria describe current behavior.

| ID | Given / When / Then |
| --- | --- |
| ECL-AC-001 | **Given** a non-empty local Git repository, **when** it is analyzed, **then** a report includes its HEAD revision and commit count. |
| ECL-AC-002 | **Given** commits with normal, binary, renamed, deleted, and unusual path changes, **when** history is read, **then** author/date/path evidence and available numstat values are retained without duplicate merge diffs. |
| ECL-AC-003 | **Given** a shallow clone, **when** it is analyzed, **then** the report flags it as shallow. |
| ECL-AC-004 | **Given** a path and component depth, **when** components are assigned, **then** the directory prefix at that depth is used and root files use `(root)`. |
| ECL-AC-005 | **Given** valid custom weights, **when** scores are calculated, **then** the normalized weighted score uses them; invalid weights fail. |
| ECL-AC-006 | **Given** identical history, filters, configuration, and explicit reference time, **when** analysis repeats, **then** scores and classifications match. |
| ECL-AC-007 | **Given** invalid signals, invalid configuration, or a reference before evidence, **when** scoring runs, **then** it fails rather than emit an invalid score. |
| ECL-AC-008 | **Given** boundary HHI values, **when** risk is classified, **then** LOW, MEDIUM, HIGH, and CRITICAL boundaries follow ECL-SC-015. |
| ECL-AC-009 | **Given** a unique contributor query, **when** a person view is requested, **then** their component evidence is returned. |
| ECL-AC-010 | **Given** an empty, absent, or ambiguous contributor query, **when** a person view is requested, **then** it fails with a clear error. |
| ECL-AC-011 | **Given** a contributor in a component, **when** departure is simulated, **then** modeled loss equals that contributor’s pre-departure share. |
| ECL-AC-012 | **Given** files touched only by a departing contributor, **when** departure is simulated, **then** those files are reported as uncovered. |
| ECL-AC-013 | **Given** remaining contributors with overlapping files, **when** departure is simulated, **then** the candidate with the highest overlap is selected using documented tie breaks. |
| ECL-AC-014 | **Given** no remaining historical file overlap, **when** departure is simulated, **then** no successor candidate is returned. |
| ECL-AC-015 | **Given** authors carrying `[bot]`, **when** bot exclusion is enabled, **then** their changed-file records are excluded and evidence records the reason. |
| ECL-AC-016 | **Given** a matching generated filename, **when** generated-file exclusion is enabled, **then** its changed-file record is excluded and evidence records the reason. |
| ECL-AC-017 | **Given** matching custom path or author globs, **when** exclusions are enabled, **then** matching changed-file records are excluded with deterministic reason precedence. |
| ECL-AC-018 | **Given** every changed-file record is excluded, **when** analysis runs, **then** it returns an empty component report without inventing risk labels. |
| ECL-AC-019 | **Given** each CLI command, **when** JSON or text output is selected, **then** it contains the applicable evidence and view. |
| ECL-AC-020 | **Given** a structurally valid analysis JSON report, **when** the browser explorer loads it, **then** it shows component, contributor, and departure views consistent with the report. |
| ECL-AC-021 | **Given** an incompatible or malformed report, **when** the browser explorer loads it, **then** it rejects it without accepting corrupted state. |
| ECL-AC-022 | **Given** a local report file, **when** it is loaded in the browser explorer, **then** the application keeps it in browser memory; no network upload behavior exists in its static code. |
| ECL-AC-023 | **Given** `--repo` is supplied to `analyze`, `person`, or `simulate-departure`, **when** the command runs, **then** no repository prompt appears and the supplied path is analyzed. |
| ECL-AC-024 | **Given** an interactive terminal and no `--repo`, **when** an analysis-related command runs, **then** it prompts for a local repository path, trims surrounding whitespace, rejects an empty response, and analyzes the entered path. |
| ECL-AC-025 | **Given** an invalid supplied or entered repository path, **when** analysis starts, **then** the existing clear Git repository validation error is shown. |
| ECL-AC-026 | **Given** non-interactive execution and no `--repo`, **when** an analysis-related command runs, **then** it fails without waiting for input and instructs the caller to provide `--repo`. |
| ECL-AC-027 | **Given** the local explorer service and a valid local repository path, **when** the browser requests analysis, **then** the existing analysis report is returned and rendered without changing scoring semantics. |
| ECL-AC-028 | **Given** an invalid local repository path or invalid browser request, **when** the local explorer service receives it, **then** it returns a clear error and does not run remote access or cloning. |
| ECL-AC-029 | **Given** the explorer command, **when** it starts, **then** it serves the browser interface and API on loopback only. |
| ECL-AC-030 | **Given** a local repository path or a public HTTPS Git clone URL, **when** `analyze`, `person`, or `simulate-departure` receives it interactively or through `--repo`, **then** the command uses the same source-resolution flow and produces its existing view. |
| ECL-AC-031 | **Given** a public HTTPS clone URL, **when** it is analyzed, **then** Git performs a full clone without a depth limit, the complete history is analyzed, and the temporary clone is removed after success or failure. |
| ECL-AC-032 | **Given** a clone failure, unsupported URL scheme, SCP-like URL, file URL, or URL with embedded credentials, **when** analysis starts, **then** it fails clearly without shell execution, credential logging, or a persisted workspace. |
| ECL-AC-033 | **Given** JSON output and a remote URL, **when** cloning, history reading, and analysis run, **then** progress is written only to stderr, JSON stdout remains valid, and remote provenance identifies the supplied URL without exposing a temporary path. |
| ECL-AC-034 | **Given** a local repository path, **when** it is analyzed, **then** existing behavior remains compatible and the local repository is never deleted or modified. |
| ECL-AC-035 | **Given** the local browser explorer, **when** a user chooses local-path or public-HTTPS clone analysis, **then** each source is visibly distinct and uses the shared resolver without exposing a temporary workspace. |
| ECL-AC-036 | **Given** a valid report, **when** the browser displays a contributor scenario, **then** it labels evidence impact, coverage gaps, and historical evidence overlap without presenting a contributor as a replacement recommendation. |
| ECL-AC-037 | **Given** the hosted demo at a repository Pages subpath, **when** it loads without a local explorer service, **then** its CSS, JavaScript, navigation, and bundled demo report render without backend requests. |
| ECL-AC-038 | **Given** a visitor opens the hosted demo, **when** the page finishes loading, **then** a bundled synthetic report is already displayed and Overview, Components, Contributors, Evidence, and Continuity Stress Test are available. |
| ECL-AC-039 | **Given** a compatible local analysis JSON file, **when** a visitor loads it, **then** the browser validates it, displays it in place of the bundled demo, keeps it only in browser memory, and can reset to the bundled demo. |
| ECL-AC-040 | **Given** a malformed or incompatible local JSON file, **when** a visitor loads it, **then** the displayed report remains valid and a clear error is shown. |
| ECL-AC-041 | **Given** the hosted demo, **when** a visitor inspects its primary actions and privacy message, **then** View on GitHub targets the project repository and the page visibly states that reports remain in the browser without upload or persistence. |
| ECL-AC-042 | **Given** the hosted demo at a normal mobile width, **when** a visitor uses primary controls with keyboard or touch, **then** controls have visible focus, content remains usable without horizontal page overflow, and the continuity disclaimer is visible. |
