"""Explicit, auditable filtering of evidence before scoring."""
from dataclasses import dataclass, replace
from fnmatch import fnmatchcase

from continuity.domain.models import History

# Deliberately narrow heuristics; callers can supply repository-specific patterns.
GENERATED_PATTERNS = ("*.g.cs", "*.g.i.cs", "*.generated.*", "*.min.js", "*.min.css")


@dataclass(frozen=True)
class FilterConfig:
    exclude_bots: bool = False
    exclude_generated: bool = False
    paths: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilterEvidence:
    input_file_changes: int
    retained_file_changes: int
    excluded_file_changes: int
    excluded_authors: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    reasons: dict[str, int]


def filter_history(history: History, config: FilterConfig) -> tuple[History, FilterEvidence]:
    """Retain commit metadata so the original reference date never shifts.

    Each excluded file-change receives one reason, in precedence order:
    explicit author, bot heuristic, explicit path, generated-path heuristic.
    """
    excluded_authors: set[str] = set()
    excluded_paths: set[str] = set()
    reasons: dict[str, int] = {}
    commits = []
    total = retained = 0
    for commit in history.commits:
        identity = (commit.author.key, commit.author.name.casefold())
        author_reason = ""
        if any(fnmatchcase(value, pattern.casefold()) for value in identity for pattern in config.authors):
            author_reason = "author_pattern"
        elif config.exclude_bots and any("[bot]" in value for value in identity):
            author_reason = "bot_marker"
        changes = []
        for change in commit.changes:
            total += 1
            reason = author_reason
            if not reason and any(fnmatchcase(change.path, p) for p in config.paths):
                reason = "path_pattern"
            if not reason and config.exclude_generated and any(fnmatchcase(change.path, p) for p in GENERATED_PATTERNS):
                reason = "generated_path"
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
                excluded_paths.add(change.path)
                if author_reason:
                    excluded_authors.add(commit.author.key)
            else:
                changes.append(change)
                retained += 1
        commits.append(replace(commit, changes=tuple(changes)))
    return replace(history, commits=tuple(commits)), FilterEvidence(
        total, retained, total - retained, tuple(sorted(excluded_authors)),
        tuple(sorted(excluded_paths)), dict(sorted(reasons.items())),
    )
