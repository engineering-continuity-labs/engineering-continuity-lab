"""Immutable provider-neutral offline traceability contracts (ECL-FR-301–328).

Safe alias tokens are deliberate: native private identifiers and transport settings
belong to adapters, never these evidence values. No exported report schema is added.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from typing import Protocol

from continuity.domain.reviews import CollectionStatus


class ArtifactKind(StrEnum):
    WORK_ITEM = "WORK_ITEM"
    PULL_REQUEST = "PULL_REQUEST"
    COMMIT = "COMMIT"
    CHANGED_PATH = "CHANGED_PATH"
    PR_PATH = "PR_PATH"
    COMPONENT = "COMPONENT"


class TraceLinkType(StrEnum):
    WI_PR = "WI_PR"
    WI_COMMIT = "WI_COMMIT"
    PR_COMMIT = "PR_COMMIT"
    COMMIT_PATH = "COMMIT_PATH"
    PR_PATH = "PR_PATH"
    PATH_COMPONENT = "PATH_COMPONENT"
    WI_COMPONENT = "WI_COMPONENT"


class TraceLinkOrigin(StrEnum):
    DIRECT_PROVIDER_LINK = "DIRECT_PROVIDER_LINK"
    DIRECT_SOURCE_LINK = "DIRECT_SOURCE_LINK"
    DERIVED_LINK = "DERIVED_LINK"


class TraceabilityCapability(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class TraceStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"


class WorkItemType(StrEnum):
    REQUIREMENT = "REQUIREMENT"
    STORY = "STORY"
    BUG = "BUG"
    TASK = "TASK"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class WorkItemState(StrEnum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Population(StrEnum):
    WORK_ITEMS = "WORK_ITEMS"
    PULL_REQUESTS = "PULL_REQUESTS"
    COMMITS = "COMMITS"
    CHANGES = "CHANGES"


class Direction(StrEnum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class GapReason(StrEnum):
    NO_OBSERVED_LINK = "NO_OBSERVED_LINK"
    INCOMPLETE_LOOKUP = "INCOMPLETE_LOOKUP"
    LOOKUP_UNAVAILABLE = "LOOKUP_UNAVAILABLE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    OUTSIDE_BOUNDARY = "OUTSIDE_BOUNDARY"
    INCOMPATIBLE_BOUNDARY = "INCOMPATIBLE_BOUNDARY"
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    CONFLICTING_OBSERVATION = "CONFLICTING_OBSERVATION"
    UNSUPPORTED_RELATION = "UNSUPPORTED_RELATION"
    UNRESOLVED_NORMATIVE_SEGMENT = "UNRESOLVED_NORMATIVE_SEGMENT"
    EMPTY_POPULATION = "EMPTY_POPULATION"


def safe_token(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("invalid safe identifier")


def safe_path(value: str) -> None:
    if (not value or len(value) > 1024 or value.startswith("/") or "\\" in value
            or any(p in ("", ".", "..") for p in value.split("/"))
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(c in value for c in (":", "?", "#", "@"))):
        raise ValueError("invalid repository-relative path")


def aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")


@dataclass(frozen=True, eq=False)
class ArtifactReference:
    kind: ArtifactKind
    provider: str
    instance: str
    scope: str
    identifier: str
    repository: str = ""
    context: str = ""
    configuration: str = ""
    algorithm: str = "sha1"

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ArtifactKind):
            raise ValueError("invalid artifact kind")
        if self.kind in (ArtifactKind.COMMIT, ArtifactKind.CHANGED_PATH, ArtifactKind.COMPONENT):
            # Source identity is canonical; observing provider lives in provenance.
            object.__setattr__(self, "provider", "source")
            object.__setattr__(self, "instance", "offline")
            object.__setattr__(self, "scope", "components" if self.kind == ArtifactKind.COMPONENT else "git")
        if self.kind not in (ArtifactKind.COMMIT, ArtifactKind.CHANGED_PATH):
            object.__setattr__(self, "algorithm", "sha1")
        for v in (self.provider, self.instance, self.scope):
            safe_token(v)
        if self.kind != ArtifactKind.WORK_ITEM:
            safe_token(self.repository)
        elif self.repository or self.context or self.configuration:
            raise ValueError("invalid work-item scope")
        if self.kind == ArtifactKind.COMMIT:
            self._hash(self.identifier)
            if self.context or self.configuration:
                raise ValueError("invalid commit context")
        elif self.kind == ArtifactKind.CHANGED_PATH:
            safe_path(self.identifier)
            self._hash(self.context)
            if self.configuration:
                raise ValueError("invalid change configuration")
        elif self.kind == ArtifactKind.PR_PATH:
            safe_path(self.identifier)
            safe_token(self.context)
            if self.configuration:
                raise ValueError("invalid PR path configuration")
        elif self.kind == ArtifactKind.COMPONENT:
            if self.identifier != "(root)":
                safe_path(self.identifier)
            safe_token(self.context)
            safe_token(self.configuration)
        else:
            safe_token(self.identifier)
            if self.context or self.configuration:
                raise ValueError("invalid artifact context")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ArtifactReference) and self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    def _hash(self, value: str) -> None:
        size = {"sha1": 40, "sha256": 64}.get(self.algorithm)
        if size is None or not re.fullmatch(r"[0-9a-f]{" + str(size) + r"}", value):
            raise ValueError("invalid full commit hash")

    @property
    def key(self) -> tuple[str, ...]:
        # Git identity belongs to repository/source, not the observing adapter.
        if self.kind in (ArtifactKind.COMMIT, ArtifactKind.CHANGED_PATH, ArtifactKind.COMPONENT):
            return (self.kind, self.repository, self.algorithm, self.context,
                    self.configuration, self.identifier)
        return (self.kind, self.provider, self.instance, self.scope, self.repository,
                self.context, self.configuration, self.identifier)


@dataclass(frozen=True)
class EvidenceBoundary:
    identifier: str
    provider: str
    instance: str
    project: str
    repository: str
    collected_at: datetime
    snapshot: str
    query: str
    identity_mapping: str
    filter_policy: str
    revision: str | None = None
    time_field: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    normalization_version: str = "offline-1"
    join_contract: str | None = None

    def __post_init__(self) -> None:
        for v in (self.identifier, self.provider, self.instance, self.project,
                  self.repository, self.snapshot, self.query, self.identity_mapping,
                  self.filter_policy, self.normalization_version):
            safe_token(v)
        if self.join_contract is not None:
            safe_token(self.join_contract)
        aware(self.collected_at)
        if self.revision is not None and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.revision):
            raise ValueError("invalid boundary revision")
        if (self.start is None) != (self.end is None):
            raise ValueError("incomplete time interval")
        if self.start is not None and self.end is not None:
            aware(self.start)
            aware(self.end)
            if self.start >= self.end or self.time_field is None:
                raise ValueError("invalid time interval")
        if self.time_field is not None:
            safe_token(self.time_field)


@dataclass(frozen=True)
class Observation:
    identifier: str
    boundary: str
    observed_at: datetime
    basis: str

    def __post_init__(self) -> None:
        for v in (self.identifier, self.boundary, self.basis):
            safe_token(v)
        aware(self.observed_at)

    @property
    def key(self) -> tuple[str, str]:
        return self.boundary, self.identifier


@dataclass(frozen=True)
class WorkItemEvidence:
    reference: ArtifactReference
    type: WorkItemType
    state: WorkItemState
    provenance: Observation
    title: str | None = None
    title_approved: bool = False
    created_at: datetime | None = None
    changed_at: datetime | None = None
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.reference.kind != ArtifactKind.WORK_ITEM:
            raise ValueError("invalid work-item reference")
        if not isinstance(self.type, WorkItemType) or not isinstance(self.state, WorkItemState):
            raise ValueError("invalid normalized work-item label")
        if self.title is not None and (not self.title_approved or len(self.title) > 256
                                      or any(ord(c) < 32 for c in self.title)):
            raise ValueError("unapproved work-item title")
        for stamp in (self.created_at, self.changed_at, self.closed_at):
            if stamp is not None:
                aware(stamp)


LinkKey = tuple[tuple[str, ...], tuple[str, ...], str, str]


@dataclass(frozen=True)
class TraceLink:
    source: ArtifactReference
    target: ArtifactReference
    type: TraceLinkType
    origin: TraceLinkOrigin
    observations: tuple[Observation, ...]
    supports: tuple[LinkKey, ...] = ()

    @property
    def key(self) -> LinkKey:
        return self.source.key, self.target.key, self.type, self.origin


@dataclass(frozen=True)
class LookupEvidence:
    boundary: str
    capability: TraceabilityCapability = TraceabilityCapability.SUPPORTED
    status: CollectionStatus = CollectionStatus.COMPLETE
    endpoint: ArtifactReference | None = None
    relationship: TraceLinkType | None = None
    direction: Direction = Direction.OUTBOUND
    population: Population | None = None

    def __post_init__(self) -> None:
        safe_token(self.boundary)
        if not isinstance(self.capability, TraceabilityCapability) or not isinstance(self.status, CollectionStatus):
            raise ValueError("invalid lookup state")
        if not isinstance(self.direction, Direction):
            raise ValueError("invalid lookup direction")
        if self.population is not None:
            if self.endpoint is not None or self.relationship is not None:
                raise ValueError("invalid population lookup")
        elif self.endpoint is None or self.relationship is None:
            raise ValueError("invalid relationship lookup")

    @property
    def key(self) -> tuple[object, ...]:
        return (self.endpoint.key if self.endpoint else (), self.relationship,
                self.direction, self.population)


@dataclass(frozen=True)
class TraceDiagnostic:
    reason: GapReason
    endpoint: ArtifactReference | None = None
    relationship: TraceLinkType | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason, GapReason):
            raise ValueError("invalid diagnostic category")


@dataclass(frozen=True)
class TraceabilityEvidenceCollection:
    boundaries: tuple[EvidenceBoundary, ...]
    work_items: tuple[WorkItemEvidence, ...]
    pull_requests: tuple[ArtifactReference, ...]
    merged_pull_requests: tuple[ArtifactReference, ...]
    commits: tuple[ArtifactReference, ...]
    changed_paths: tuple[ArtifactReference, ...]
    links: tuple[TraceLink, ...]
    lookups: tuple[LookupEvidence, ...]
    status: CollectionStatus = CollectionStatus.COMPLETE
    diagnostics: tuple[TraceDiagnostic, ...] = ()
    component_strategy: str = "directory"
    component_configuration: str = "depth-2"

    def __post_init__(self) -> None:
        safe_token(self.component_strategy)
        safe_token(self.component_configuration)


class TraceabilityEvidenceProvider(Protocol):
    def acquire(self) -> TraceabilityEvidenceCollection: ...


@dataclass(frozen=True)
class TraceGap:
    endpoint: ArtifactReference
    relationship: TraceLinkType
    direction: Direction
    status: TraceStatus
    reason: GapReason


@dataclass(frozen=True)
class TracePath:
    nodes: tuple[ArtifactReference, ...]
    supports: tuple[LinkKey, ...]
    boundaries: tuple[str, ...]
    status: TraceStatus
    gaps: tuple[TraceGap, ...] = ()
    rule_version: str = "offline-1"


@dataclass(frozen=True)
class ArtifactTraceResult:
    artifact: ArtifactReference
    status: TraceStatus
    paths: tuple[TracePath, ...]
    gaps: tuple[TraceGap, ...]


@dataclass(frozen=True)
class CoverageMetric:
    dimension: str
    numerator: int
    denominator: int
    value: float | None
    status: TraceStatus
    collection_status: CollectionStatus
    boundaries: tuple[str, ...]
    sources: tuple[str, ...]
    unknown_count: int = 0
    excluded_count: int = 0
    reason: GapReason | None = None
    component: ArtifactReference | None = None


@dataclass(frozen=True)
class TraceabilityReport:
    evidence: TraceabilityEvidenceCollection
    direct_links: tuple[TraceLink, ...]
    derived_links: tuple[TraceLink, ...]
    paths: tuple[TracePath, ...]
    gaps: tuple[TraceGap, ...]
    artifacts: tuple[ArtifactTraceResult, ...]
    metrics: tuple[CoverageMetric, ...]
    summary: TraceStatus
    diagnostics: tuple[TraceDiagnostic, ...]
    derivation_version: str = "offline-1"
