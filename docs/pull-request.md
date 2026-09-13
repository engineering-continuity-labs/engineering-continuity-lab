# feat: add Git knowledge risk baseline

Implements the first Git-only Engineering Continuity Lab baseline. The `continuity analyze`, `continuity person`, and `continuity simulate-departure` commands expose JSON evidence, six configurable scoring signals, component concentration/risk, and successor candidates ranked by file overlap.

The design separates provider-independent domain evidence, Git extraction, replaceable directory component detection, pure scoring, and analysis. Reports retain file-level commit hashes, activity dates, line counts, effective configuration, and analyzed revision. Documentation explicitly treats Git activity as an experimental knowledge proxy and explains limits around merges, renames, shallow history, bots, and inactive contributors.

Validation: 17 unit/integration tests pass; strict mypy passes for all source modules; editable package installation and all three CLI commands succeed against full dotnet/eShop revision b4a40872005d4bb29e5b1fa1ff7e244143d39215. Depth-2 analysis yields 347 commits, 59 contributors, and 48 components (33 LOW, 10 MEDIUM, 5 CRITICAL). Validation source stays outside this repository. See docs/validation.md for reproduction and interpretation.

No Azure DevOps, Neo4j, LLM, or web UI is included.
