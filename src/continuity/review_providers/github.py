"""Public GitHub REST adapter with bounded, explicit collection completeness."""
from datetime import UTC, datetime
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
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


class GitHubPublicReviewEvidence:
    """Fetch a bounded public snapshot without tokens or raw payload retention."""

    def __init__(self, maximum_pull_requests: int = 20) -> None:
        if maximum_pull_requests < 1:
            raise ValueError("maximum pull requests must be positive")
        self.maximum_pull_requests = maximum_pull_requests

    def _get(self, path: str) -> tuple[list[dict[str, Any]], bool]:
        request = Request(f"https://api.github.com{path}", headers={
            "Accept": "application/vnd.github+json", "User-Agent": "engineering-continuity-lab",
        })
        with urlopen(request, timeout=20) as response:  # nosec B310: fixed GitHub API origin
            data: object = json.loads(response.read())
            if not isinstance(data, list):
                raise ValueError("GitHub returned an unexpected collection")
            return [item for item in data if isinstance(item, dict)], "rel=\"next\"" in response.headers.get("Link", "")

    def acquire(self, request: ReviewEvidenceRequest) -> ReviewEvidenceCollection:
        repository = github_repository(request.repository)
        retrieved = datetime.now(UTC)
        provenance = ProviderProvenance("github", repository, request.evidence_boundary, retrieved)
        try:
            pulls, has_more = self._get(f"/repos/{repository}/pulls?state=closed&sort=updated&direction=desc&per_page={self.maximum_pull_requests}")
            merged = [pull for pull in pulls if pull.get("merged_at")]
            evidence: list[PullRequestEvidence] = []
            diagnostics: list[str] = []
            for pull in merged:
                number = pull.get("number")
                identifier = str(number) if isinstance(number, int) else ""
                author = _identity(pull.get("user"))
                merged_at = _time(pull.get("merged_at"))
                if not identifier or author is None or merged_at is None:
                    diagnostics.append("malformed merged pull request omitted")
                    continue
                files, files_more = self._get(f"/repos/{repository}/pulls/{identifier}/files?per_page=100")
                reviews, reviews_more = self._get(f"/repos/{repository}/pulls/{identifier}/reviews?per_page=100")
                paths = tuple(sorted({item["filename"] for item in files if isinstance(item.get("filename"), str)}))
                if not paths:
                    diagnostics.append(f"pull request {identifier} has no usable changed paths")
                    continue
                events: list[ReviewEvent] = []
                for item in reviews:
                    if not isinstance(item.get("id"), int):
                        diagnostics.append(f"pull request {identifier} has a malformed review identifier")
                        continue
                    submitted = _time(item.get("submitted_at"))
                    reviewer = _identity(item.get("user"))
                    if isinstance(item.get("submitted_at"), str) and submitted is None:
                        diagnostics.append(f"pull request {identifier} has a malformed optional review timestamp")
                    if isinstance(item.get("user"), dict) and reviewer is None:
                        diagnostics.append(f"pull request {identifier} has a malformed reviewer identity")
                    events.append(ReviewEvent(
                        str(item["id"]), _state(item.get("state")), reviewer, submitted, item["id"],
                        item.get("state") == "DISMISSED",
                    ))
                evidence.append(PullRequestEvidence(identifier, author, merged_at, paths, tuple(events)))
                if files_more or reviews_more:
                    diagnostics.append(f"pull request {identifier} evidence is paginated")
            status = CollectionStatus.PARTIAL if has_more or diagnostics else CollectionStatus.COMPLETE
            return ReviewEvidenceCollection(provenance, tuple(evidence), status, tuple(diagnostics))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            return ReviewEvidenceCollection(provenance, (), CollectionStatus.FAILED,
                                            (f"GitHub public evidence collection failed: {type(error).__name__}",))
