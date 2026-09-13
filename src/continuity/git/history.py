"""Read HEAD ancestry using NUL-delimited Git records, without checkout changes."""
from datetime import datetime
from pathlib import Path
import subprocess

from continuity.domain.models import Author, Change, Commit, History


class GitHistory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _git(self, *args: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.path), *args], capture_output=True, check=False
        )
        if result.returncode:
            raise ValueError(result.stderr.decode("utf-8", "replace").strip())
        return result.stdout

    def read(self) -> History:
        revision = self._git("rev-parse", "--verify", "HEAD").decode().strip()
        shallow = self._git("rev-parse", "--is-shallow-repository").strip() == b"true"
        # No rename inference: a move is a deletion plus addition. Merge commits
        # retain metadata but have no diff, avoiding double-counted branch work.
        tokens = self._git(
            "log", revision, "--format=%x00COMMIT%x00%H%x00%aN%x00%aE%x00%aI",
            "--numstat", "-z", "--no-renames", "--diff-merges=off", "--no-ext-diff",
        ).split(b"\0")
        commits: list[Commit] = []
        i = 0
        while i < len(tokens):
            if tokens[i] != b"COMMIT":
                i += 1
                continue
            sha, name, email, date = [t.decode("utf-8", "replace") for t in tokens[i+1:i+5]]
            i += 5
            changes: list[Change] = []
            while i < len(tokens) and tokens[i] != b"COMMIT":
                record = tokens[i].lstrip(b"\n")
                if record:
                    added, deleted, path = record.split(b"\t", 2)
                    changes.append(Change(
                        path.decode("utf-8", "surrogateescape"),
                        None if added == b"-" else int(added),
                        None if deleted == b"-" else int(deleted),
                    ))
                i += 1
            commits.append(Commit(sha, Author(name, email), datetime.fromisoformat(date), tuple(changes)))
        return History(revision, tuple(commits), shallow)
