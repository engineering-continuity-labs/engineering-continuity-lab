# Real-world validation: dotnet/eShop

Validated on 2026-09-13 with Python 3.12.14 and a full clone of https://github.com/dotnet/eShop.git. The clone and full JSON reports were kept outside this repository; no eShop source is included.

Analyzed revision: `b4a40872005d4bb29e5b1fa1ff7e244143d39215`.
Reference author date: `2026-08-28T12:33:30-05:00` (newest included author timestamp).
Configuration: default six weights, 180-day half-life, directory depth 2.

```sh
git clone https://github.com/dotnet/eShop.git /tmp/continuity-eshop-validation
git -C /tmp/continuity-eshop-validation checkout b4a40872005d4bb29e5b1fa1ff7e244143d39215
continuity analyze --repo /tmp/continuity-eshop-validation --component-depth 2 > /tmp/eshop-analysis.json
continuity person "maleger@microsoft.com" --repo /tmp/continuity-eshop-validation --component-depth 2 > /tmp/eshop-person.json
continuity simulate-departure "maleger@microsoft.com" --repo /tmp/continuity-eshop-validation --component-depth 2 > /tmp/eshop-departure.json
```

All three commands completed successfully. The analysis contains 347 commits, 59 contributors with changed-file evidence, and 48 components. Risk counts: 33 LOW, 10 MEDIUM, 0 HIGH, 5 CRITICAL.

The five CRITICAL components have a single recorded contributor: `.aspire`, `.devcenter/catalog`, `.github/skills`, `tests/Application.UnitTests`, and `tests/eShop.AppHost.UnitTests`. This is historical activity concentration; it does not establish that nobody else understands these areas.

The sample departure has a 100% modeled share in `.github/skills`, `tests/Application.UnitTests`, and `tests/eShop.AppHost.UnitTests`, with no evidenced successor in those components. Its share is approximately 66.82% in `tests/Webhooks.FunctionalTests`; the overlap-based successor candidate has touched 20% of the departed contributor's files. This illustrates why score share and successor coverage must be inspected together.

Validation checks execution and internal consistency, not predictive accuracy. Imports, generated assets, old paths, bots, and sparse history can distort these results. No independent ground truth for actual team knowledge was available.

## Filter and terminal-report validation

At the same revision and depth, `--exclude-bots --exclude-generated` retained 2,710 of 2,923 changed-file records, excluding 194 for the bot marker and 19 for generated filename patterns. Contributors decreased from 59 to 57. Component count remained 48; classifications became 32 LOW, 11 MEDIUM, 0 HIGH, and 5 CRITICAL. The reference timestamp remained unchanged. This is a sensitivity check, not proof that filtering improves predictive accuracy.

All three commands were exercised with `--format text` and these filters. The unfiltered JSON component results were also compared with the original validation report to check that default scores remain unchanged.
