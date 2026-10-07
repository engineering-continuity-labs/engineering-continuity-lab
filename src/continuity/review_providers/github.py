"""Public GitHub REST adapter with complete, explicit pagination."""
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qsl, urlsplit

from continuity.domain.reviews import (
    CollectionStatus, ProviderProvenance, PullRequestEvidence,
    ReviewEvidenceCollection, ReviewEvidenceRequest, ReviewEvent, ReviewIdentity,
    ReviewState,
)

_GITHUB = re.compile(r"^(?:https://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def github_repository(reference: str) -> str:
    """Return an owner/repository reference, rejecting non-public-GitHub inputs."""
    match = _GITHUB.fullmatch(reference.strip())
    if match is None:
        raise ValueError("review evidence currently supports a public GitHub repository URL")
    return f"{match.group(1)}/{match.group(2)}"


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _identity(value: object) -> ReviewIdentity | None:
    if not isinstance(value, dict) or not isinstance(value.get("login"), str):
        return None
    login = value["login"]
    try:
        return ReviewIdentity(login, value.get("name") if isinstance(value.get("name"), str) else login,
                              value.get("type") == "Bot")
    except ValueError:
        return None


def _state(value: object) -> ReviewState:
    values = {item.value: item for item in ReviewState}
    return values.get(str(value).upper(), ReviewState.UNKNOWN)


BOUNDARY = "public closed-PR history reachable via GitHub REST Link pagination; merged PRs only; files and review events; maximum 1000 pages per endpoint; interrupted collection is incomplete"
RATE_LIMIT = "GitHub public API rate limit prevented complete review evidence collection."
FAILURE = "GitHub public API failure prevented complete review evidence collection."


@dataclass(frozen=True)
class _Pages:
    items: list[dict[str, Any]]
    diagnostics: tuple[str, ...] = ()
    interrupted: bool = False


def _next_target(link: str, path: str) -> str | None:
    targets = []
    for part in link.split(","):
        match = re.fullmatch(r'\s*<([^>]+)>\s*;(.*)', part)
        if match:
            relation = re.search(r'(?:^|;)\s*rel\s*=\s*(?:"([^"]*)"|([^;\s]+))', match[2])
            if relation and "next" in (relation[1] or relation[2]).split():
                targets.append(match[1])
    if not targets:
        if re.search(r'\bnext\b', link):
            raise ValueError("invalid pagination link")
        return None
    if len(targets) != 1:
        raise ValueError("ambiguous pagination link")
    target = urlsplit(targets[0])
    original = urlsplit(path)
    query = parse_qsl(target.query, keep_blank_values=True)
    previous = dict(parse_qsl(original.query))
    allowed = {"page", "per_page", "state", "sort", "direction"}
    if (target.scheme != "https" or target.netloc != "api.github.com" or target.path != original.path
            or target.fragment or len(dict(query)) != len(query) or any(k not in allowed for k, _ in query)
            or any(k != "page" and previous.get(k) != v for k, v in query)
            or any(k != "page" and dict(query).get(k) != v for k, v in previous.items())
            or not dict(query).get("page", "").isdigit() or int(dict(query)["page"]) < 1):
        raise ValueError("unsafe pagination link")
    return target.path + "?" + target.query


class GitHubPublicReviewEvidence:
    """Fetch a public snapshot without tokens or raw payload retention."""

    def __init__(self, maximum_pages: int = 1000) -> None:
        if isinstance(maximum_pages, bool) or not isinstance(maximum_pages, int) or maximum_pages < 1:
            raise ValueError("maximum pages must be positive")
        self.maximum_pages = maximum_pages

    def _get(self, path: str) -> tuple[list[Any], str]:
        request = Request(f"https://api.github.com{path}", headers={
            "Accept": "application/vnd.github+json", "User-Agent": "engineering-continuity-lab",
        })
        with urlopen(request, timeout=20) as response:  # nosec B310: fixed GitHub API origin
            data: object = json.loads(response.read())
            if not isinstance(data, list):
                raise ValueError("unexpected collection")
            return data, response.headers.get("Link", "")

    def _all(self, path: str) -> _Pages:
        items: list[dict[str, Any]] = []
        diagnostics: list[str] = []
        visited: set[str] = set()
        for _ in range(self.maximum_pages):
            if path in visited:
                diagnostics.append("GitHub pagination cycle prevented complete collection.")
                return _Pages(items, tuple(diagnostics), True)
            visited.add(path)
            try:
                batch, link = self._get(path)
                for item in batch:
                    if isinstance(item, dict):
                        items.append(item)
                    else:
                        diagnostics.append("Malformed GitHub collection record omitted.")
                next_path = _next_target(link, path)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
                limited = False
                if isinstance(error, HTTPError):
                    headers: Any = error.headers or {}
                    limited = error.code == 429 or (error.code == 403 and (
                        headers.get("X-RateLimit-Remaining") == "0" or headers.get("Retry-After") is not None))
                    if error.code == 403 and not limited:
                        # Inspect only a bounded rate-limit indicator; never retain or emit the body.
                        try:
                            message = error.read(4096).decode("utf-8", errors="replace").casefold()
                            limited = "rate limit" in message or "abuse detection" in message
                        except (OSError, ValueError):
                            pass
                diagnostics.append(RATE_LIMIT if limited else FAILURE)
                return _Pages(items, tuple(diagnostics), True)
            if next_path is None:
                return _Pages(items, tuple(diagnostics))
            path = next_path
        diagnostics.append("GitHub pagination safety page limit prevented complete collection.")
        return _Pages(items, tuple(diagnostics), True)

    def acquire(self, request: ReviewEvidenceRequest) -> ReviewEvidenceCollection:
        repository = github_repository(request.repository)
        provenance = ProviderProvenance("github", repository,
            BOUNDARY.replace("1000", str(self.maximum_pages)), datetime.now(UTC))
        pulls = self._all(f"/repos/{repository}/pulls?state=closed&sort=updated&direction=desc&per_page=100")
        diagnostics = list(pulls.diagnostics)
        evidence: list[PullRequestEvidence] = []
        seen: dict[int, dict[str, Any]] = {}
        merged_count = sum(1 for pull in pulls.items if pull.get("merged_at") is not None)
        interrupted = pulls.interrupted
        for pull in pulls.items:
            number = pull.get("number")
            if isinstance(number, bool) or not isinstance(number, int) or number < 1 or "merged_at" not in pull:
                diagnostics.append("Malformed required pull request fields omitted.")
                continue
            if number in seen:
                if pull != seen[number]:
                    diagnostics.append("Conflicting duplicate pull request omitted.")
                continue
            seen[number] = pull
            if pull["merged_at"] is None:
                continue
            author = _identity(pull.get("user"))
            merged_at = _time(pull.get("merged_at"))
            if author is None or merged_at is None:
                diagnostics.append("Malformed merged pull request omitted.")
                continue
            files = self._all(f"/repos/{repository}/pulls/{number}/files?per_page=100")
            diagnostics.extend(files.diagnostics)
            paths: set[str] = set()
            for item in files.items:
                filename = item.get("filename")
                if (not isinstance(filename, str) or not filename.strip() or filename.startswith("/")
                        or ".." in filename.split("/") or "\\" in filename):
                    diagnostics.append("Malformed changed path omitted.")
                else:
                    paths.add(filename)
            if len(files.items) >= 3000:
                diagnostics.append("GitHub changed-file API ceiling may omit paths; evidence is incomplete.")
            interrupted = interrupted or files.interrupted
            if not paths:
                diagnostics.append(f"Pull request {number} has no usable changed paths.")
                if files.interrupted:
                    break
                continue
            # Avoid further calls after a transport/safety interruption; keep known paths.
            reviews = _Pages([], (), True) if files.interrupted else self._all(
                f"/repos/{repository}/pulls/{number}/reviews?per_page=100")
            diagnostics.extend(reviews.diagnostics)
            events: dict[str, ReviewEvent] = {}
            for item in reviews.items:
                identifier = item.get("id")
                if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 1:
                    diagnostics.append("Malformed review identifier omitted.")
                    continue
                submitted = _time(item.get("submitted_at"))
                reviewer = _identity(item.get("user"))
                if item.get("submitted_at") is not None and submitted is None:
                    diagnostics.append("Malformed optional review timestamp; provider ordering used.")
                if item.get("submitted_at") is None:
                    diagnostics.append("Missing optional review timestamp; provider ordering used.")
                if item.get("user") is not None and reviewer is None:
                    diagnostics.append("Malformed reviewer identity; review remains non-qualifying.")
                event = ReviewEvent(str(identifier), _state(item.get("state")), reviewer,
                                    submitted, identifier, item.get("state") == "DISMISSED")
                retained = events.get(event.identifier)
                if retained is not None and retained != event:
                    diagnostics.append("Conflicting duplicate review event omitted.")
                    # Do not let conflicting state qualify; retain an explicit unknown event.
                    events[event.identifier] = ReviewEvent(str(identifier), ReviewState.UNKNOWN, None,
                                                           provider_order=identifier)
                elif retained is None:
                    events[event.identifier] = event
            evidence.append(PullRequestEvidence(str(number), author, merged_at,
                tuple(sorted(paths)), tuple(events[k] for k in sorted(events))))
            interrupted = interrupted or reviews.interrupted
            if files.interrupted or reviews.interrupted:
                break
        status = CollectionStatus.PARTIAL if any(not d.startswith("Missing optional") for d in diagnostics) or interrupted else CollectionStatus.COMPLETE
        if interrupted and not evidence:
            status = CollectionStatus.FAILED
        return ReviewEvidenceCollection(provenance, tuple(evidence), status,
            tuple(dict.fromkeys(diagnostics)), len(pulls.items), merged_count)
