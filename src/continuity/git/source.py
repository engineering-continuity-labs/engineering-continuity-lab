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
    """Return a local workspace for a path or HTTPS clone URL without embedded credentials."""
    value = source.strip()
    if not value:
        raise ValueError("repository path or clone URL cannot be empty")
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme != "https":
            raise ValueError("only HTTPS Git clone URLs without embedded credentials are supported")
        if not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("repository URLs with embedded credentials are not supported")
        if parsed.query or parsed.fragment:
            raise ValueError("clone URL must not include a query or fragment")
        return clone_https(value, progress)
    if value.startswith("git@"):
        raise ValueError("SSH Git URLs are not yet supported; use an HTTPS clone URL without embedded credentials")
    return RepositoryWorkspace(Path(value), None)


def clone_https(url: str, progress: Progress | None = None) -> RepositoryWorkspace:
    """Clone an HTTPS repository without embedded URL credentials into a unique workspace."""
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
        raise ValueError("unable to clone repository; confirm the HTTPS clone URL and local Git access are valid")
    return RepositoryWorkspace(destination, url, temporary)
