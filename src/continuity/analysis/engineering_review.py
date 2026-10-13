"""Pure lifecycle analysis shared by delivery and explicit defect populations.

This module consumes already normalized observations. It does not acquire or
infer history, source aliases, state mappings or component relationships.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from continuity.domain.engineering_review import Distribution, Window, distribution, elapsed_microseconds, instant
from continuity.domain.verification import approved


class State(StrEnum):
    OPEN = 'OPEN'
    COMPLETE = 'COMPLETE'
    REMOVED = 'REMOVED'
    UNKNOWN = 'UNKNOWN'


@dataclass(frozen=True)
class Transition:
    identifier: str
    sequence: int
    occurred_at: datetime
    previous: State
    next: State

    def __post_init__(self) -> None:
        approved(self.identifier)
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError('invalid lifecycle sequence')
        if not isinstance(self.previous, State) or not isinstance(self.next, State):
            raise ValueError('invalid lifecycle state')
        object.__setattr__(self, 'occurred_at', instant(self.occurred_at))


@dataclass(frozen=True)
class Lifecycle:
    """One immutable normalized observation, with explicit history coverage."""
    reference: tuple[str, str, str, str, str]
    observation: str
    created_at: datetime | None
    initial_state: State
    history_start: datetime
    history_end: datetime
    history_complete: bool
    transitions: tuple[Transition, ...]
    priority: str | None = None
    severity: str | None = None
    type_alias: str = 'item'
    history_capability: str = 'SUPPORTED'
    category_as_of: datetime | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.reference, tuple) or len(self.reference) != 5
                or self.reference[0] != 'WORK_ITEM'):
            raise ValueError('invalid lifecycle reference')
        for alias in self.reference:
            approved(alias)
        approved(self.observation)
        approved(self.type_alias)
        if (self.history_capability not in ('SUPPORTED', 'UNSUPPORTED', 'UNKNOWN')
                or self.history_complete and self.history_capability != 'SUPPORTED'):
            raise ValueError('invalid history capability')
        for category in (self.priority, self.severity):
            if category is not None:
                approved(category)
        if not isinstance(self.initial_state, State) or type(self.history_complete) is not bool:
            raise ValueError('invalid lifecycle coverage')
        for name in ('history_start', 'history_end'):
            object.__setattr__(self, name, instant(getattr(self, name)))
        if self.created_at is not None:
            object.__setattr__(self, 'created_at', instant(self.created_at))
        if self.category_as_of is not None:
            object.__setattr__(self, 'category_as_of', instant(self.category_as_of))
            if self.category_as_of > self.history_end:
                raise ValueError('invalid category boundary')
        if (self.history_start > self.history_end or not isinstance(self.transitions, tuple)
                or len(self.transitions) > 40000 or any(not isinstance(t, Transition) for t in self.transitions)):
            raise ValueError('invalid lifecycle history')
        previous = self.initial_state
        last_sequence = -1
        last_time = self.history_start
        identifiers: set[str] = set()
        for event in self.transitions:
            if (event.sequence <= last_sequence or event.occurred_at < last_time
                    or event.occurred_at > self.history_end or event.identifier in identifiers
                    or event.previous != previous):
                raise ValueError('contradictory lifecycle history')
            identifiers.add(event.identifier)
            previous, last_sequence, last_time = event.next, event.sequence, event.occurred_at
        if self.created_at is not None and (self.created_at > self.history_end
                or self.history_start < self.created_at
                or any(t.occurred_at < self.created_at for t in self.transitions)):
            raise ValueError('invalid lifecycle creation')


@dataclass(frozen=True)
class LifecycleResult:
    reference: tuple[str, str, str, str, str]
    completions: tuple[str, ...]
    reopens: tuple[str, ...]
    duration_microseconds: int | None
    inventory: State | None
    age_microseconds: int | None
    complete_history: bool


def lifecycle(record: Lifecycle, window: Window, *, created_start: bool) -> LifecycleResult:
    if type(created_start) is not bool:
        raise ValueError('invalid lifecycle start policy')
    complete = (record.history_complete and record.initial_state != State.UNKNOWN
                and not any(t.previous == State.UNKNOWN or t.next == State.UNKNOWN for t in record.transitions
                            if t.occurred_at < window.end)
                and (record.history_start <= window.start or record.history_start == record.created_at)
                and record.history_end >= window.end)
    # A complete window prefix need not include creation. It cannot establish
    # the first episode's start unless the initial OPEN begins at creation.
    start = (record.created_at if created_start and record.initial_state == State.OPEN
             and record.created_at == record.history_start else None)
    state = record.initial_state
    completions: list[str] = []
    reopens: list[str] = []
    representative: int | None = None
    for event in record.transitions:
        if event.occurred_at >= window.end:
            break
        if event.next == State.OPEN and event.previous != State.OPEN:
            start = event.occurred_at
            if event.previous == State.COMPLETE and window.contains(event.occurred_at):
                reopens.append(event.identifier)
        if event.next == State.COMPLETE and event.previous != State.COMPLETE:
            if window.contains(event.occurred_at):
                completions.append(event.identifier)
                representative = elapsed_microseconds(start, event.occurred_at) if start is not None else None
            start = None
        if event.next == State.REMOVED:
            start = None
        state = event.next
    inventory = state if complete and (record.created_at is None or record.created_at < window.end) else None
    age = (elapsed_microseconds(record.created_at, window.end)
           if inventory == State.OPEN and record.created_at is not None and record.created_at < window.end else None)
    return LifecycleResult(record.reference, tuple(completions), tuple(reopens),
                           representative if complete else None, inventory, age, complete)


@dataclass(frozen=True)
class PopulationResult:
    results: tuple[LifecycleResult, ...]
    opened: int | None
    completed: int | None
    reopened: int | None
    open_inventory: int | None
    aged: int | None
    durations: Distribution
    conflicts: tuple[tuple[str, str, str, str, str], ...]
    availability: str
    excluded_references: tuple[tuple[str, str, str, str, str], ...]
    duration_complete: bool
    unknown_ages: int
    age_buckets: tuple[int, ...]


def analyze_population(records: tuple[Lifecycle, ...], window: Window, *,
                       enumeration_complete: bool, created_start: bool) -> PopulationResult:
    if (not isinstance(records, tuple) or len(records) > 10000
            or any(not isinstance(r, Lifecycle) for r in records)
            or type(enumeration_complete) is not bool):
        raise ValueError('invalid lifecycle population')
    if sum(len(r.transitions) for r in records) > 40000:
        raise ValueError('invalid lifecycle history limit')
    grouped: dict[tuple[str, str, str, str, str], set[Lifecycle]] = {}
    for record in records:
        grouped.setdefault(record.reference, set()).add(record)
    # Multiple differing full-history observations cannot be merged safely.
    # Quarantine the identity, retaining explicit incompleteness rather than
    # selecting the newest or most favorable completion.
    def contradictory(observations: set[Lifecycle]) -> bool:
        by_observation: dict[str, set[Lifecycle]] = {}
        for r in observations:
            by_observation.setdefault(r.observation, set()).add(r)
        return any(len(v) > 1 for v in by_observation.values())
    conflicts = tuple(sorted(ref for ref, observations in grouped.items() if contradictory(observations)))
    def covering(observations: set[Lifecycle]) -> Lifecycle | None:
        # A longer immutable observation may extend an exact history prefix.
        # No incompatible event or state is selected by recency or outcome.
        ordered = sorted(observations, key=lambda r: (r.history_end, len(r.transitions), r.observation))
        longest = ordered[-1]
        for r in ordered:
            if ((r.created_at, r.initial_state, r.history_start, r.type_alias) !=
                    (longest.created_at, longest.initial_state, longest.history_start, longest.type_alias)
                    or longest.transitions[:len(r.transitions)] != r.transitions
                    or any(t.occurred_at < r.history_end for t in longest.transitions[len(r.transitions):])
                    and r.history_complete):
                return None
        qualified = [r for r in ordered if r.history_complete and r.history_end >= window.end
                     and (r.history_start <= window.start or r.history_start == r.created_at)]
        return qualified[-1] if qualified else longest
    merged = {ref: covering(observations) for ref, observations in grouped.items()}
    ambiguous = tuple(ref for ref, merged_record in merged.items() if merged_record is None)
    retained = tuple(r for ref in sorted(grouped) if (r := merged[ref]) is not None
                     if ref not in conflicts and ref not in ambiguous)
    results = tuple(lifecycle(r, window, created_start=created_start) for r in retained)
    complete = enumeration_complete and not conflicts and not ambiguous and all(r.complete_history for r in results)
    opened_known = sum(r.created_at is not None and window.contains(r.created_at) for r in retained)
    fields_complete = all(r.created_at is not None for r in retained)
    def count(value: int, qualified: bool) -> int | None:
        return value if qualified or value > 0 else None
    durations = tuple(r.duration_microseconds for r in results if r.duration_microseconds is not None)
    open_count = sum(r.inventory == State.OPEN for r in results)
    aged_count = sum(r.age_microseconds is not None and r.age_microseconds >= 30 * 86400000000 for r in results)
    return PopulationResult(results, count(opened_known, enumeration_complete and not conflicts and not ambiguous and fields_complete),
                            count(sum(bool(r.completions) for r in results), complete),
                            count(sum(bool(r.reopens) for r in results), complete),
                            count(open_count, complete), count(aged_count, complete and fields_complete),
                            distribution(durations), conflicts, 'OBSERVED' if complete and fields_complete else
                            ('PARTIAL' if results else 'UNAVAILABLE'), tuple(sorted(set(ambiguous) | set(conflicts))),
                            complete and len(durations) == sum(bool(r.completions) for r in results),
                            sum(r.inventory == State.OPEN and r.age_microseconds is None for r in results),
                            tuple(sum(r.age_microseconds is not None and lower * 86400000000 <= r.age_microseconds
                                      and (upper is None or r.age_microseconds < upper * 86400000000)
                                      for r in results) for lower, upper in ((0, 7), (7, 30), (30, 90), (90, None))))
