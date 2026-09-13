"""Provider-independent evidence and component contracts."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Author:
    name: str
    email: str

    @property
    def key(self) -> str:
        return self.email.casefold()


@dataclass(frozen=True)
class Change:
    path: str
    additions: int | None
    deletions: int | None


@dataclass(frozen=True)
class Commit:
    revision: str
    author: Author
    date: datetime
    changes: tuple[Change, ...]


@dataclass(frozen=True)
class History:
    revision: str
    commits: tuple[Commit, ...]
    shallow: bool = False


class HistoryProvider(Protocol):
    def read(self) -> History: ...


class ComponentStrategy(Protocol):
    def component(self, path: str) -> str: ...


@dataclass(frozen=True)
class DirectoryComponents:
    depth: int = 1

    def __post_init__(self) -> None:
        if self.depth < 1:
            raise ValueError("component depth must be positive")

    def component(self, path: str) -> str:
        directories = path.split("/")[:-1]
        return "/".join(directories[:self.depth]) or "(root)"
