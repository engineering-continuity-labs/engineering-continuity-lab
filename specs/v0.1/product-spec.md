# v0.1 product specification

**Status:** Implemented

Verification status is tracked per requirement in [traceability.md](traceability.md). Some v0.1 requirements currently remain PARTIAL or MANUAL.

## Purpose and users

Engineering Continuity Lab is an evidence-driven experiment for identifying concentration in Git-derived engineering activity and exploring continuity risk when contributors leave. Git activity is a proxy for engineering knowledge.

It does **not** claim to measure human competency, actual knowledge, organizational replaceability, employee performance, or true handover readiness.

Primary users are technical leads, software architects, engineering managers, and maintainers.

## Goals and non-goals

v0.1 analyzes Git history, derives transparent knowledge-proxy signals, identifies component concentration, exposes contributor evidence, simulates contributor departure, and retains explainable evidence.

v0.1 excludes Azure DevOps integration, pull-request review intelligence, architecture decision extraction, LLM inference, semantic code understanding, actual competency verification, and automated employee evaluation.

## Functional requirements

| ID | Requirement |
| --- | --- |
| ECL-FR-001 | Analyze a local Git repository. |
| ECL-FR-002 | Extract commit, author, date, changed-path, and line-change evidence where available. |
| ECL-FR-003 | Group paths into directory-based components using configurable depth. |
| ECL-FR-004 | Calculate contributor evidence signals per component. |
| ECL-FR-005 | Calculate contributor score shares and component concentration. |
| ECL-FR-006 | Classify concentration as LOW, MEDIUM, HIGH, or CRITICAL. |
| ECL-FR-007 | Expose contributor-specific evidence. |
| ECL-FR-008 | Simulate contributor departure. |
| ECL-FR-009 | Report modeled loss, remaining contributors, successor candidate, and uncovered historical files. |
| ECL-FR-010 | Support JSON reporting. |
| ECL-FR-011 | Support readable text reporting. |
| ECL-FR-012 | Support explicit bot filtering. |
| ECL-FR-013 | Support generated-file filtering. |
| ECL-FR-014 | Support user-provided path exclusions. |
| ECL-FR-015 | Support user-provided contributor exclusions. |
| ECL-FR-016 | Expose filter evidence and effective configuration. |
| ECL-FR-017 | Detect and flag shallow Git history. |
| ECL-FR-018 | Support an explicit scoring reference timestamp. |
| ECL-FR-019 | Support externally configurable scoring weights and half-life. |
| ECL-FR-020 | The browser explorer shall load a local `analyze` JSON report and display concentration, contributor evidence, and departure scenarios without uploading or persisting the report. |
| ECL-FR-021 | The browser explorer shall reject incompatible or structurally invalid reports. |
| ECL-FR-022 | When an analysis-related CLI command runs interactively without an explicit repository path, prompt for a local repository path. In non-interactive execution, fail clearly and instruct the caller to provide `--repo`. |
| ECL-FR-023 | The local browser explorer shall accept a local repository path and run the existing analysis through a loopback-only local service, then display the resulting report without remote repository access. |
| ECL-FR-024 | Analysis-related CLI commands shall accept either a local repository path or a public HTTPS Git clone URL. |
| ECL-FR-025 | For a public HTTPS Git clone URL, the system shall clone complete history into a temporary workspace, analyze it through the existing Git pipeline, and remove the workspace when the command completes or fails. |
| ECL-FR-026 | The system shall reject unsupported repository URL schemes and embedded URL credentials with clear errors because authenticated repository access is not supported. |
| ECL-FR-027 | Analysis-related CLI commands shall emit remote-clone progress to stderr so JSON stdout remains machine-readable. |
| ECL-FR-028 | The local browser explorer shall present distinct local-path and public-HTTPS-clone-URL inputs and resolve each through the applicable repository acquisition flow. |
| ECL-FR-029 | The browser explorer shall present contributor scenarios as system-continuity evidence, using neutral continuity, coverage, and historical-overlap terminology without changing the report schema or calculation semantics. |
| ECL-FR-030 | The browser explorer shall be publishable as a static public demo that loads a bundled safe demo report by default and supports exploration of overview, components, contributors, evidence, and continuity stress-test views. |
| ECL-FR-031 | The public browser demo shall let a visitor load a compatible local analysis JSON report, replace the displayed demo state with it, and reset to the bundled demo without uploading or persisting the report. |
| ECL-FR-032 | The public browser demo shall link visibly to the project repository and shall state that its continuity results are historical activity evidence rather than employee evaluation, expertise, value, or replaceability. |

## Non-functional requirements

| ID | Requirement |
| --- | --- |
| ECL-NFR-001 | Require Python 3.12 or newer. |
| ECL-NFR-002 | Produce deterministic analysis for identical evidence, configuration, and reference timestamp. |
| ECL-NFR-003 | Keep scoring explainable through named signals and exposed configuration. |
| ECL-NFR-004 | Perform repository analysis locally. |
| ECL-NFR-005 | Keep browser reports local to browser memory. |
| ECL-NFR-006 | Keep the runtime dependency-light. |
| ECL-NFR-007 | Do not mutate an analyzed repository. |
| ECL-NFR-008 | State limitations and uncertainty explicitly. |
| ECL-NFR-009 | Retain evidence provenance where Git supplies it. |
| ECL-NFR-010 | Bind the local browser analysis service to loopback only and reject unsupported API paths and invalid request payloads. |
| ECL-NFR-011 | Remote acquisition shall use argument-array Git subprocess calls without shell execution, shall not use shallow cloning, and shall not expose temporary workspace paths or credentials in reports or errors. |
| ECL-NFR-012 | The hosted demo shall require no authentication, backend, analytics, telemetry, tracking, cookies, or third-party data service; selected report data shall remain in browser memory. |
| ECL-NFR-013 | Static browser assets and internal navigation shall work when hosted below the repository GitHub Pages subpath. |

The normative score contract is [scoring-spec.md](scoring-spec.md). Acceptance criteria and verification status are [acceptance-criteria.md](acceptance-criteria.md) and [traceability.md](traceability.md).
