"""Plain terminal views, independent of scoring and without runtime dependencies."""
from collections import Counter

from continuity.analysis.filtering import FilterConfig, FilterEvidence
from continuity.analysis.service import Report, simulate_departure


def safe(value: str) -> str:
    """Keep repository-controlled control characters out of terminal output."""
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in value)


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    clean = [tuple(safe(cell) for cell in row) for row in [headers, *rows]]
    widths = [max(len(row[i]) for row in clean) for i in range(len(headers))]
    lines = ["  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in clean]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def render(report: Report, evidence: FilterEvidence, command: str, person: str | None = None,
           filters: FilterConfig = FilterConfig()) -> str:
    people = {p.contributor for c in report.components for p in c.contributors}
    lines = ["Engineering Continuity Lab — experimental Git activity proxy",
             f"Revision: {report.revision}", f"Reference date: {report.as_of.isoformat()}",
             f"Commits: {report.commit_count} | Contributors: {len(people)} | Components: {len(report.components)}",
             f"File changes: {evidence.retained_file_changes} retained / {evidence.input_file_changes} total; {evidence.excluded_file_changes} excluded"]
    lines.append(f"Filters: bots={filters.exclude_bots}, generated={filters.exclude_generated}; "
                 f"path globs={safe(repr(filters.paths))}; author globs={safe(repr(filters.authors))}")
    if report.shallow:
        lines.append("WARNING: shallow clone; history is incomplete.")
    if evidence.reasons:
        lines.append("Exclusions: " + ", ".join(f"{k}={v}" for k, v in evidence.reasons.items()))
    rows: list[tuple[str, ...]]
    lines.append("")
    if not report.components:
        lines.append("No changed-file evidence remains; no risk classification is available.")
    elif command == "analyze":
        counts = Counter(c.risk for c in report.components)
        lines.append("Risk counts: " + " | ".join(f"{r}: {counts[r]}" for r in ("CRITICAL", "HIGH", "MEDIUM", "LOW")))
        rows = [(c.component, c.risk, f"{c.concentration:.3f}", str(len(c.contributors)),
                 c.contributors[0].contributor, f"{c.contributors[0].share:.1%}")
                for c in sorted(report.components, key=lambda c: (-c.concentration, c.component))]
        lines.append(table(("Component", "Risk", "HHI", "People", "Top contributor", "Share"), rows))
    elif command == "person":
        lines.append("Contributor: " + safe(person or ""))
        rows = [(c.component, c.risk, f"{p.score:.3f}", f"{p.share:.1%}", str(p.commits), str(len(p.files)),
                 f"{p.signals['recency']:.3f}")
                for c in sorted(report.components, key=lambda c: (-c.concentration, c.component))
                for p in c.contributors if p.contributor == person]
        lines.append(table(("Component", "Risk", "Score", "Share", "Commits", "Files", "Recency"), rows))
    elif command == "simulate-departure":
        lines.append("Departure: " + safe(person or ""))
        rows = [(i.component, f"{i.estimated_knowledge_loss:.1%}", str(len(i.remaining_contributors)),
                 i.best_successor_candidate or "None evidenced", f"{i.successor_file_overlap:.1%}", str(len(i.uncovered_files)))
                for i in simulate_departure(report, person or "")]
        lines.append(table(("Component", "Modeled loss", "Remaining", "Successor candidate", "Overlap", "Uncovered files"), rows))
        for i in simulate_departure(report, person or ""):
            lines.append(safe(i.component) + " remaining: " + (", ".join(safe(p) for p in i.remaining_contributors) or "none"))
    lines.extend(["", "Git activity is only a proxy for knowledge; scores and risk thresholds are experimental.",
                  "Use --format json for full signals and file-level evidence."])
    return "\n".join(lines)
