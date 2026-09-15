"""Resolve supported repository inputs into safe local Git workspaces."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable
from urllib.parse import urlsplit


Progress = Callable[[str], None]


@dataclass(frozen=True)
class RepositoryWorkspace:
    """A local path or a temporary full clone, cleaned up by its context manager."""

    path: Path
    source: str | None
    _temporary: TemporaryDirectory[str] | None = None

    def __enter__(self) -> "RepositoryWorkspace":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()


def resolve_repository(source: str, progress: Progress | None = None) -> RepositoryWorkspace:
    """Return a local workspace for a path or supported public HTTPS clone URL."""
    value = source.strip()
    if not value:
        raise ValueError("repository path or clone URL cannot be empty")
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme != "https":
            raise ValueError("only public HTTPS Git clone URLs are supported")
        if not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("authenticated repository URLs are not yet supported")
        if parsed.query or parsed.fragment:
            raise ValueError("clone URL must not include a query or fragment")
        return clone_https(value, progress)
    if value.startswith("git@"):
        raise ValueError("SSH Git URLs are not yet supported; use a public HTTPS clone URL")
    return RepositoryWorkspace(Path(value), None)


def clone_https(url: str, progress: Progress | None = None) -> RepositoryWorkspace:
    """Clone a public HTTPS repository with complete history into a unique workspace."""
    temporary = TemporaryDirectory(prefix="continuity-")
    destination = Path(temporary.name) / "repository"
    if progress is not None:
        progress("Cloning repository...")
    result = subprocess.run(
        ["git", "clone", "--", url, str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        temporary.cleanup()
        raise ValueError("unable to clone repository; confirm the public HTTPS clone URL is valid")
    return RepositoryWorkspace(destination, url, temporary)
