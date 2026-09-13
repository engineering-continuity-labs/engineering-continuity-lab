"""Aggregate traceable file evidence and derive concentration and departure views."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from continuity.domain.models import ComponentStrategy, History
from continuity.scoring.model import ScoringConfig, recency, risk, score


@dataclass
class Activity:
    commits: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)
    months: set[str] = field(default_factory=set)
    dates: list[datetime] = field(default_factory=list)
    churn: int = 0
    additions: int = 0
    deletions: int = 0
    unknown_line_changes: int = 0


@dataclass
class FileActivity:
    commits: list[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    unknown_line_changes: int = 0
    first_activity: str = ""
    last_activity: str = ""


@dataclass(frozen=True)
class ContributorScore:
    contributor: str
    name: str
    score: float
    share: float
    signals: dict[str, float]
    commits: int
    files: tuple[str, ...]
    additions: int
    deletions: int
    unknown_line_changes: int
    file_activity: dict[str, FileActivity]


@dataclass(frozen=True)
class ComponentReport:
    component: str
    concentration: float
    risk: str
    contributors: tuple[ContributorScore, ...]
    file_contributors: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Report:
    revision: str
    as_of: datetime
    shallow: bool
    commit_count: int
    components: tuple[ComponentReport, ...]


@dataclass(frozen=True)
class DepartureImpact:
    component: str
    estimated_knowledge_loss: float
    remaining_contributors: tuple[str, ...]
    best_successor_candidate: str | None
    successor_file_overlap: float
    uncovered_files: tuple[str, ...]


def analyze(history: History, strategy: ComponentStrategy, config: ScoringConfig,
            as_of: datetime | None = None) -> Report:
    if not history.commits:
        raise ValueError("history has no commits")
    as_of = as_of or max(c.date for c in history.commits)
    if as_of.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    if any(c.date > as_of for c in history.commits):
        raise ValueError("as_of precedes an included commit")
    groups: dict[str, dict[str, Activity]] = defaultdict(lambda: defaultdict(Activity))
    names: dict[str, str] = {}
    file_activity: dict[tuple[str, str], dict[str, FileActivity]] = defaultdict(dict)
    for commit in sorted(history.commits, key=lambda c: (c.date, c.revision)):
        who = commit.author.key
        names[who] = commit.author.name
        for change in commit.changes:
            component_name = strategy.component(change.path)
            a = groups[component_name][who]
            evidence = file_activity[(component_name, who)].setdefault(change.path, FileActivity())
            evidence.commits.append(commit.revision)
            evidence.additions += change.additions or 0
            evidence.deletions += change.deletions or 0
            evidence.unknown_line_changes += int(change.additions is None or change.deletions is None)
            evidence.first_activity = evidence.first_activity or commit.date.isoformat()
            evidence.last_activity = commit.date.isoformat()
            a.commits.add(commit.revision)
            a.files.add(change.path)
            a.months.add(commit.date.strftime("%Y-%m"))
            a.dates.append(commit.date)
            a.additions += change.additions or 0
            a.deletions += change.deletions or 0
            a.unknown_line_changes += int(change.additions is None or change.deletions is None)
            a.churn += (change.additions or 0) + (change.deletions or 0)
    reports: list[ComponentReport] = []
    for component, people in sorted(groups.items()):
        files = set.union(*(a.files for a in people.values()))
        months = set.union(*(a.months for a in people.values()))
        touches = sum(len(a.commits) for a in people.values())
        churn = sum(a.churn for a in people.values())
        owners = {f: tuple(sorted(p for p, a in people.items() if f in a.files)) for f in sorted(files)}
        signals = {p: {
            "change_ownership": a.churn / churn if churn else len(a.commits) / touches,
            "recency": recency(max(a.dates), as_of, config.half_life_days),
            "change_frequency": len(a.commits) / touches,
            "code_area_breadth": len(a.files) / len(files),
            "unique_contribution": sum(len(owners[f]) == 1 for f in a.files) / len(files),
            "historical_persistence": len(a.months) / len(months),
        } for p, a in people.items()}
        scores = {p: score(s, config) for p, s in signals.items()}
        total = sum(scores.values())
        if total == 0:
            raise ValueError(f"weights produce no score for component {component!r}")
        contributors = tuple(sorted((ContributorScore(
            p, names[p], scores[p], scores[p] / total, signals[p], len(a.commits),
            tuple(sorted(a.files)), a.additions, a.deletions, a.unknown_line_changes,
            dict(sorted(file_activity[(component, p)].items())),
        ) for p, a in people.items()), key=lambda p: (-p.share, p.contributor)))
        concentration = min(1.0, sum(p.share ** 2 for p in contributors))
        reports.append(ComponentReport(component, concentration, risk(concentration), contributors, owners))
    return Report(history.revision, as_of, history.shallow, len(history.commits), tuple(reports))


def resolve_person(report: Report, query: str) -> str:
    if not query.strip():
        raise ValueError("provide a contributor name or email")
    candidates = {p.contributor for c in report.components for p in c.contributors
                  if query.casefold() in (p.contributor, p.name.casefold())}
    if len(candidates) != 1:
        raise ValueError("contributor not found or name is ambiguous; use an exact email")
    return candidates.pop()


def simulate_departure(report: Report, contributor: str) -> tuple[DepartureImpact, ...]:
    impacts: list[DepartureImpact] = []
    for component in report.components:
        departed = next((p for p in component.contributors if p.contributor == contributor), None)
        if departed is None:
            continue
        remaining = [p for p in component.contributors if p.contributor != contributor]
        def overlap(p: ContributorScore) -> float:
            return len(set(p.files) & set(departed.files)) / len(departed.files)
        ranked = sorted(remaining, key=lambda p: (-overlap(p), -p.score, p.contributor))
        successor = ranked[0] if ranked and overlap(ranked[0]) > 0 else None
        impacts.append(DepartureImpact(
            component.component, departed.share, tuple(p.contributor for p in ranked),
            successor.contributor if successor else None, overlap(successor) if successor else 0,
            tuple(f for f in departed.files if len(component.file_contributors[f]) == 1),
        ))
    return tuple(sorted(impacts, key=lambda i: (-i.estimated_knowledge_loss, i.component)))
