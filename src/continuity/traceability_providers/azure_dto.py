"""Strict projections of Azure REST DTOs; no raw identities/errors are returned."""
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import unquote

from continuity.domain.traceability import safe_path
from continuity.traceability_providers.azure_profile import guid, native_id


_PRIVATE_PATH = re.compile(
    r"(?:gh[pousr]_|github_pat_|glpat-|sk-[A-Za-z0-9_-]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
    r"(?:authorization|bearer|password|passwd|cookie|set-cookie|pat|token|secret)[_=: ]|"
    r"(?:authorization|bearer|password|cookie|pat|token|secret)_SENTINEL|"
    r"https?://|file://|(?:^|/)(?:Users|home|tmp|private/var|var/tmp)/)", re.IGNORECASE
)


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError("invalid Azure record")
    return value


def array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("invalid Azure record")
    return value


def text(value: object) -> str:
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid Azure record")
    return value


def commit_id(value: object) -> str:
    result = text(value)
    if not re.fullmatch(r"[0-9a-fA-F]{40}", result):
        raise ValueError("invalid Azure commit")
    return result.lower()


def timestamp(value: object) -> datetime:
    result = text(value)
    # Azure .NET timestamps may use 100ns ticks; normalize to domain microseconds.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,7})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", result):
        raise ValueError("invalid Azure timestamp")
    try:
        return datetime.fromisoformat(result.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        raise ValueError("invalid Azure timestamp") from None


def reference_id(value: object) -> int:
    raw = obj(value).get("id")
    if isinstance(raw, str) and re.fullmatch(r"[1-9][0-9]{0,9}", raw):
        return native_id(int(raw))
    return native_id(raw)


@dataclass(frozen=True, repr=False)
class PullRequestDto:
    identifier: int
    completed: bool
    closed_at: datetime | None
    work_item_refs: tuple[object, ...] | None


def pull_request(value: object, project: str, repository: str, *, read_refs: bool = True) -> PullRequestDto:
    dto = obj(value)
    identifier = native_id(dto.get("pullRequestId"))
    repo = obj(dto.get("repository"))
    if guid(repo.get("id")) != repository or guid(obj(repo.get("project")).get("id")) != project:
        raise ValueError("invalid Azure PR scope")
    status = text(dto.get("status"))
    if status not in ("completed", "active", "abandoned"):
        raise ValueError("invalid Azure PR state")
    closed = timestamp(dto.get("closedDate")) if status == "completed" else None
    refs = None if not read_refs or "workItemRefs" not in dto else tuple(array(dto["workItemRefs"]))
    return PullRequestDto(identifier, status == "completed", closed, refs)


def artifact(value: object, project: str, repository: str) -> tuple[str, str]:
    uri = text(value)
    prefix = "vstfs:///Git/"
    if not uri.startswith(prefix):
        raise ValueError("invalid Azure artifact")
    family, separator, suffix = uri[len(prefix):].partition("/")
    if separator != "/" or family not in ("Commit", "PullRequestId"):
        raise ValueError("invalid Azure artifact")
    if "%" in suffix:
        # Only a uniformly encoded separator is documented. No mixed/double escape.
        if "/" in suffix or re.sub(r"%2[fF]", "", suffix).find("%") != -1:
            raise ValueError("invalid Azure artifact")
        suffix = unquote(suffix, errors="strict")
    pieces = suffix.split("/")
    if len(pieces) != 3 or guid(pieces[0]) != project or guid(pieces[1]) != repository:
        raise ValueError("invalid Azure artifact scope")
    if family == "Commit":
        return family, commit_id(pieces[2])
    if not re.fullmatch(r"[1-9][0-9]{0,9}", pieces[2]):
        raise ValueError("invalid Azure artifact")
    return family, str(native_id(int(pieces[2])))


def changed_path(value: object) -> str | None:
    item = obj(obj(value).get("item"))
    folder = item.get("isFolder", False)
    if type(folder) is not bool:
        raise ValueError("invalid Azure path")
    if folder or item.get("gitObjectType") == "tree":
        return None
    path = text(item.get("path"))
    if not path.startswith("/"):
        raise ValueError("invalid Azure path")
    path = path[1:]
    safe_path(path)
    # Avoid recognizable private/credential markers before entering domain evidence.
    if _PRIVATE_PATH.search(path):
        raise ValueError("unapproved Azure path")
    return path
