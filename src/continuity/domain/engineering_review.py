"""Exact offline review windows and duration statistics; no acquisition."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fractions import Fraction


def instant(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('invalid review instant')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, 'start', instant(self.start))
        object.__setattr__(self, 'end', instant(self.end))
        if not timedelta(0) < self.end - self.start <= timedelta(days=3650):
            raise ValueError('invalid review window')

    def contains(self, value: datetime) -> bool:
        return self.start <= instant(value) < self.end


@dataclass(frozen=True)
class Windows:
    current: Window
    previous: Window
    assessment_as_of: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.current, Window) or not isinstance(self.previous, Window):
            raise ValueError('invalid review windows')
        object.__setattr__(self, 'assessment_as_of', instant(self.assessment_as_of))
        if (self.previous.end != self.current.start
                or self.previous.end - self.previous.start != self.current.end - self.current.start
                or self.assessment_as_of < self.current.end):
            raise ValueError('incomparable review windows')

    @classmethod
    def default(cls, assessment_as_of: datetime) -> 'Windows':
        boundary = instant(assessment_as_of).replace(hour=0, minute=0, second=0, microsecond=0)
        return cls(Window(boundary - timedelta(days=30), boundary),
                   Window(boundary - timedelta(days=60), boundary - timedelta(days=30)),
                   assessment_as_of)


def elapsed_microseconds(start: datetime, end: datetime) -> int:
    delta = instant(end) - instant(start)
    if delta < timedelta(0):
        raise ValueError('invalid review duration')
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


@dataclass(frozen=True)
class Distribution:
    count: int
    median: Fraction | None
    p75: int | None
    p90: int | None


def distribution(values: tuple[int, ...]) -> Distribution:
    if not isinstance(values, tuple) or any(type(v) is not int or v < 0 for v in values):
        raise ValueError('invalid review sample')
    ordered = sorted(values)
    n = len(ordered)
    median = (Fraction(ordered[(n - 1) // 2] + ordered[n // 2], 2) if n else None)
    return Distribution(n, median, ordered[(3 * n + 3) // 4 - 1] if n >= 4 else None,
                        ordered[(9 * n + 9) // 10 - 1] if n >= 10 else None)
