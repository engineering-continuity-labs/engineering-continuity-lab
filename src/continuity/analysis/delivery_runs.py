"""Offline PR and build metrics from explicitly normalized source records."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from fractions import Fraction

from continuity.domain.engineering_review import Distribution, Window, distribution, elapsed_microseconds, instant
from continuity.domain.verification import approved


def reference(value: tuple[str, ...], kind: str) -> None:
    if not isinstance(value, tuple) or len(value) != 5 or value[0] != kind:
        raise ValueError('invalid delivery reference')
    for alias in value:
        approved(alias)


class PRState(StrEnum):
    OPEN = 'OPEN'
    MERGED = 'MERGED'
    ABANDONED = 'ABANDONED'
    UNKNOWN = 'UNKNOWN'


class BuildResult(StrEnum):
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    PARTIAL_SUCCESS = 'PARTIAL_SUCCESS'
    CANCELED = 'CANCELED'
    UNKNOWN = 'UNKNOWN'


@dataclass(frozen=True)
class PullRequest:
    reference: tuple[str, ...]
    state: PRState
    state_as_of: datetime
    created_at: datetime | None
    merged_at: datetime | None
    observation: str = 'observation'

    def __post_init__(self) -> None:
        reference(self.reference, 'PR')
        approved(self.observation)
        if not isinstance(self.state, PRState):
            raise ValueError('invalid PR state')
        object.__setattr__(self, 'state_as_of', instant(self.state_as_of))
        for name in ('created_at', 'merged_at'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, instant(value))
        if (self.merged_at is not None and (self.state != PRState.MERGED or self.merged_at > self.state_as_of)
                or self.created_at is not None and self.created_at > self.state_as_of
                or self.created_at is not None and self.merged_at is not None and self.merged_at < self.created_at):
            raise ValueError('contradictory PR timestamps')


@dataclass(frozen=True)
class Build:
    reference: tuple[str, ...]
    result: BuildResult
    terminal: bool
    start_at: datetime | None
    finish_at: datetime | None
    observation: str = 'observation'

    def __post_init__(self) -> None:
        reference(self.reference, 'BUILD')
        approved(self.observation)
        if not isinstance(self.result, BuildResult) or type(self.terminal) is not bool:
            raise ValueError('invalid build result')
        for name in ('start_at', 'finish_at'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, instant(value))
        if (not self.terminal and (self.finish_at is not None or self.result != BuildResult.UNKNOWN)
                or self.start_at is not None and self.finish_at is not None and self.finish_at < self.start_at):
            raise ValueError('contradictory build timestamps')


@dataclass(frozen=True)
class PRMetrics:
    merged: int | None
    open_inventory: int | None
    lead: Distribution
    open_ages: tuple[tuple[tuple[str, ...], int | None], ...]
    merged_refs: tuple[tuple[str, ...], ...]
    unknown: int
    conflicts: tuple[tuple[str, ...], ...]
    availability: str
    lead_complete: bool
    inventory_complete: bool
    inventory_unknown: int


def analyze_prs(records: tuple[PullRequest, ...], window: Window, *,
                enumeration_complete: bool) -> PRMetrics:
    if (not isinstance(records, tuple) or len(records) > 10000
            or any(not isinstance(r, PullRequest) for r in records)
            or type(enumeration_complete) is not bool):
        raise ValueError('invalid PR population')
    grouped: dict[tuple[str, ...], set[PullRequest]] = {}
    for r in records:
        grouped.setdefault(r.reference, set()).add(r)
    conflicts = tuple(sorted(k for k, v in grouped.items() if
                      any(len({r for r in v if r.observation == observation}) > 1
                          for observation in {r.observation for r in v})))
    def inconsistent_merge(observations: set[PullRequest]) -> bool:
        merges = {r.merged_at for r in observations if r.merged_at is not None}
        if len(merges) != 1:
            return False
        merged_at = next(iter(merges))
        assert merged_at is not None
        return any(r.state in (PRState.OPEN, PRState.ABANDONED) and r.state_as_of > merged_at
                   or r.state == PRState.MERGED and r.state_as_of <= merged_at for r in observations)
    ambiguous = tuple(k for k, v in grouped.items() if
                      len({r.created_at for r in v if r.created_at is not None}) > 1
                      or len({r.merged_at for r in v if r.merged_at is not None}) > 1
                      or any(len({r.state for r in v if r.state_as_of == boundary}) > 1
                             for boundary in {r.state_as_of for r in v}) or inconsistent_merge(v))
    retained_list = []
    inventories_list = []
    for key in sorted(grouped):
        if key in conflicts or key in ambiguous:
            continue
        observations = grouped[key]
        candidates = [r for r in observations if r.state == PRState.MERGED and r.merged_at is not None]
        retained_list.append(min(candidates or list(observations), key=lambda r: (r.created_at is None, r.observation)))
        at_boundary = [r for r in observations if r.state_as_of == window.end]
        if at_boundary:
            inventories_list.append(min(at_boundary, key=lambda r: (r.created_at is None, r.observation)))
    retained = tuple(retained_list)
    merged = tuple(r for r in retained if r.state == PRState.MERGED and r.merged_at is not None
                   and window.contains(r.merged_at))
    unknown = sum(r.state == PRState.UNKNOWN or r.state == PRState.MERGED and r.merged_at is None for r in retained)
    complete = enumeration_complete and not conflicts and not ambiguous and unknown == 0
    inventories = tuple(inventories_list)
    opened = tuple(r for r in inventories if r.state == PRState.OPEN
                   and (r.created_at is None or r.created_at < window.end))
    inventory_unknown = sum(r.state == PRState.UNKNOWN for r in inventories)
    inventory_complete = complete and len(inventories) == len(retained) and inventory_unknown == 0
    durations = tuple(elapsed_microseconds(r.created_at, r.merged_at) for r in merged
                      if r.created_at is not None and r.merged_at is not None)
    ages = tuple((r.reference, elapsed_microseconds(r.created_at, window.end)
                  if r.created_at is not None else None) for r in opened)
    return PRMetrics(len(merged) if complete or merged else None,
                     len(opened) if inventory_complete or opened else None,
                     distribution(durations), ages, tuple(r.reference for r in merged), unknown + len(ambiguous), conflicts,
                     'OBSERVED' if complete else ('PARTIAL' if retained else 'UNAVAILABLE'),
                     complete and len(durations) == len(merged), inventory_complete, inventory_unknown)


@dataclass(frozen=True)
class BuildMetrics:
    categories: tuple[tuple[BuildResult, int], ...]
    known_terminal: int
    success_fraction: Fraction | None
    failure_fraction: Fraction | None
    durations: Distribution
    unfinished: int
    undated: int
    references: tuple[tuple[str, ...], ...]
    conflicts: tuple[tuple[str, ...], ...]
    availability: str
    duration_complete: bool


def analyze_builds(records: tuple[Build, ...], window: Window, *,
                   enumeration_complete: bool) -> BuildMetrics:
    if (not isinstance(records, tuple) or len(records) > 10000
            or any(not isinstance(r, Build) for r in records)
            or type(enumeration_complete) is not bool):
        raise ValueError('invalid build population')
    grouped: dict[tuple[str, ...], set[Build]] = {}
    for r in records:
        grouped.setdefault(r.reference, set()).add(r)
    conflicts = tuple(sorted(k for k, v in grouped.items() if
                      any(len({r for r in v if r.observation == observation}) > 1
                          for observation in {r.observation for r in v})))
    ambiguous = tuple(k for k, v in grouped.items() if
                      len({r.start_at for r in v if r.start_at is not None}) > 1
                      or len({r.finish_at for r in v if r.finish_at is not None}) > 1
                      or len({r.result for r in v if r.result != BuildResult.UNKNOWN}) > 1)
    retained_list = []
    for key in sorted(grouped):
        if key in conflicts or key in ambiguous:
            continue
        observations = grouped[key]
        terminal_candidates = [r for r in observations if r.terminal]
        selected = min(terminal_candidates or list(observations),
                       key=lambda r: (r.finish_at is None, r.result == BuildResult.UNKNOWN, r.observation))
        start = next((r.start_at for r in observations if r.start_at is not None), None)
        finish = next((r.finish_at for r in observations if r.finish_at is not None), None)
        result = next((r.result for r in observations if r.result != BuildResult.UNKNOWN), BuildResult.UNKNOWN)
        retained_list.append(Build(selected.reference, result, selected.terminal, start, finish, selected.observation))
    retained = tuple(retained_list)
    terminal = tuple(r for r in retained if r.terminal and r.finish_at is not None and window.contains(r.finish_at))
    categories = tuple((category, sum(r.result == category for r in terminal)) for category in BuildResult)
    counts = dict(categories)
    known = len(terminal) - counts[BuildResult.UNKNOWN]
    unfinished = sum(not r.terminal for r in retained)
    undated = sum(r.terminal and r.finish_at is None for r in retained)
    durations = tuple(elapsed_microseconds(r.start_at, r.finish_at) for r in terminal
                      if r.start_at is not None and r.finish_at is not None)
    return BuildMetrics(categories, known, Fraction(counts[BuildResult.SUCCESS], known) if known else None,
                        Fraction(counts[BuildResult.FAILURE], known) if known else None,
                        distribution(durations), unfinished, undated, tuple(r.reference for r in terminal), conflicts,
                        'OBSERVED' if enumeration_complete and not conflicts and not ambiguous and not undated else
                        ('PARTIAL' if retained else 'UNAVAILABLE'),
                        enumeration_complete and not conflicts and not ambiguous and not undated
                        and len(durations) == len(terminal))
