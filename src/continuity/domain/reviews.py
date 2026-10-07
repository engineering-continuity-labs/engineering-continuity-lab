"""Provider-neutral pull-request and review evidence contracts.

These types intentionally contain no provider API payloads.  Adapters turn
provider responses into this minimum evidence before the analysis layer sees it.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlsplit


class ReviewState(StrEnum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"
    UNKNOWN = "UNKNOWN"


class CollectionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ReviewIdentity:
    identifier: str
    display_name: str | None = None
    is_bot: bool = False

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("review identity identifier must not be empty")


def _validate_public_reference(reference: str) -> None:
    """Reject credential-bearing URLs before they can enter reports or errors."""
    parsed = urlsplit(reference)
    if parsed.scheme and (parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("repository reference must not contain credentials")


@dataclass(frozen=True)
class ReviewEvidenceRequest:
    repository: str
    evidence_boundary: str

    def __post_init__(self) -> None:
        if not self.repository.strip() or not self.evidence_boundary.strip():
            raise ValueError("review evidence request fields must not be empty")
        _validate_public_reference(self.repository)


@dataclass(frozen=True)
class ProviderProvenance:
    provider: str
    repository: str
    evidence_boundary: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        if not all((self.provider.strip(), self.repository.strip(), self.evidence_boundary.strip())):
            raise ValueError("provider provenance fields must not be empty")
        _validate_public_reference(self.repository)
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must include a timezone")


@dataclass(frozen=True)
class ReviewEvent:
    identifier: str
    state: ReviewState
    reviewer: ReviewIdentity | None
    submitted_at: datetime | None = None
    provider_order: int | None = None
    dismissed: bool = False

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("review event identifier must not be empty")
        if self.submitted_at is not None and self.submitted_at.tzinfo is None:
            raise ValueError("submitted_at must include a timezone")


@dataclass(frozen=True)
class PullRequestEvidence:
    identifier: str
    author: ReviewIdentity
    merged_at: datetime | None
    changed_paths: tuple[str, ...]
    reviews: tuple[ReviewEvent, ...]

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("pull request identifier must not be empty")
        if self.merged_at is not None and self.merged_at.tzinfo is None:
            raise ValueError("merged_at must include a timezone")


@dataclass(frozen=True)
class ReviewEvidenceCollection:
    provenance: ProviderProvenance
    pull_requests: tuple[PullRequestEvidence, ...]
    status: CollectionStatus = CollectionStatus.COMPLETE
    diagnostics: tuple[str, ...] = ()


class ReviewEvidenceProvider(Protocol):
    def acquire(self, request: ReviewEvidenceRequest) -> ReviewEvidenceCollection: ...
