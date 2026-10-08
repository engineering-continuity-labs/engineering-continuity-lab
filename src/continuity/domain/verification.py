"""v0.4 immutable offline evidence; no network, JSON or inferred associations."""
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum
import re
from typing import TypeAlias

from continuity.domain.reviews import CollectionStatus
from continuity.domain.traceability import (ArtifactReference, Direction, TraceabilityCapability,
                                           TraceabilityReport, TraceLinkOrigin, aware, safe_token)


class Kind(StrEnum):
    REQUIREMENT = 'REQUIREMENT'
    ARCHITECTURE_DOCUMENT = 'ARCHITECTURE_DOCUMENT'
    TEST = 'TEST'
    VERIFICATION = 'VERIFICATION'


class Relation(StrEnum):
    REQUIREMENT_WORK_ITEM = 'REQUIREMENT_WORK_ITEM'
    DOCUMENT_REQUIREMENT = 'DOCUMENT_REQUIREMENT'
    DOCUMENT_COMPONENT = 'DOCUMENT_COMPONENT'
    TEST_REQUIREMENT = 'TEST_REQUIREMENT'
    VERIFICATION_TEST = 'VERIFICATION_TEST'


class Outcome(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    SKIPPED = 'SKIPPED'
    UNKNOWN = 'UNKNOWN'


_PRIVATE = re.compile(r'(?:gh[pousr]_|github_pat_|glpat-|sk-[A-Za-z0-9_-]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|(?:authorization|bearer|password|passwd|cookie|set-cookie|pat|token|secret)[=: ]|(?:authorization|bearer|password|cookie|pat|token|secret)_SENTINEL|https?://)', re.I)


def approved(value: str) -> None:
    if not isinstance(value, str) or _PRIVATE.search(value):
        raise ValueError('invalid evidence alias')
    safe_token(value)


@dataclass(frozen=True)
class Reference:
    kind: Kind
    instance: str
    scope: str
    identifier: str
    version: str
    document_kind: str = ''

    def __post_init__(self) -> None:
        if not isinstance(self.kind, Kind):
            raise ValueError('invalid evidence kind')
        for value in (self.instance, self.scope, self.identifier, self.version):
            approved(value)
        if (self.kind == Kind.ARCHITECTURE_DOCUMENT and self.document_kind not in ('ADR', 'ICD')
                or self.kind != Kind.ARCHITECTURE_DOCUMENT and self.document_kind != ''):
            raise ValueError('invalid document kind')

    @property
    def key(self) -> tuple[str, ...]:
        return (self.kind, self.document_kind, self.instance, self.scope, self.identifier, self.version)


Endpoint: TypeAlias = Reference | ArtifactReference


def endpoint_key(endpoint: Endpoint) -> tuple[str, ...]:
    if isinstance(endpoint, Reference):
        return ('v0.4', *endpoint.key)
    return ('v0.3', *endpoint.key)


@dataclass(frozen=True)
class Snapshot:
    alias: str
    repository: str
    revision: str
    fingerprint: str

    def __post_init__(self) -> None:
        approved(self.alias)
        approved(self.repository)
        if (not isinstance(self.revision, str) or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', self.revision)
                or not isinstance(self.fingerprint, str) or not re.fullmatch(r'[a-f0-9]{64}', self.fingerprint)):
            raise ValueError('invalid evidence snapshot')


_LEGAL = {
    Relation.REQUIREMENT_WORK_ITEM: ('REQUIREMENT', 'WORK_ITEM'),
    Relation.DOCUMENT_REQUIREMENT: ('ARCHITECTURE_DOCUMENT', 'REQUIREMENT'),
    Relation.DOCUMENT_COMPONENT: ('ARCHITECTURE_DOCUMENT', 'COMPONENT'),
    Relation.TEST_REQUIREMENT: ('TEST', 'REQUIREMENT'),
    Relation.VERIFICATION_TEST: ('VERIFICATION', 'TEST'),
}


@dataclass(frozen=True)
class Association:
    source: Reference
    target: Endpoint
    relation: Relation
    boundary: str
    origin: TraceLinkOrigin = TraceLinkOrigin.DIRECT_PROVIDER_LINK

    def __post_init__(self) -> None:
        if (not isinstance(self.source, Reference) or not isinstance(self.target, (Reference, ArtifactReference))
                or not isinstance(self.relation, Relation) or (self.source.kind, self.target.kind) != _LEGAL[self.relation]
                or self.origin not in (TraceLinkOrigin.DIRECT_PROVIDER_LINK, TraceLinkOrigin.DIRECT_SOURCE_LINK)
                or not isinstance(self.origin, TraceLinkOrigin)):
            raise ValueError('invalid evidence association')
        if isinstance(self.target, Reference) and (self.source.instance, self.source.scope) != (self.target.instance, self.target.scope):
            raise ValueError('invalid evidence association scope')
        if isinstance(self.target, ArtifactReference) and self.relation == Relation.REQUIREMENT_WORK_ITEM and self.source.scope != self.target.scope:
            raise ValueError('invalid evidence association scope')
        if isinstance(self.target, ArtifactReference):
            for field in fields(self.target):
                value = getattr(self.target, field.name)
                if isinstance(value, str) and _PRIVATE.search(value):
                    raise ValueError('invalid public reference')
        approved(self.boundary)

    @property
    def key(self) -> tuple[object, ...]:
        return (endpoint_key(self.source), endpoint_key(self.target), self.relation, self.origin, self.boundary)


@dataclass(frozen=True)
class Run:
    reference: Reference
    test: Reference
    target: Snapshot
    observed_at: datetime
    outcome: Outcome
    boundary: str
    group: str | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.reference, Reference) or self.reference.kind != Kind.VERIFICATION
                or not isinstance(self.test, Reference) or self.test.kind != Kind.TEST
                or (self.reference.instance, self.reference.scope) != (self.test.instance, self.test.scope)
                or not isinstance(self.target, Snapshot) or not isinstance(self.outcome, Outcome)
                or not isinstance(self.observed_at, datetime)):
            raise ValueError('invalid verification observation')
        aware(self.observed_at)
        approved(self.boundary)
        if self.group is not None:
            approved(self.group)


@dataclass(frozen=True)
class Lookup:
    endpoint: Reference | None = None
    relation: Relation | None = None
    population: Kind | None = None
    direction: Direction = Direction.OUTBOUND
    status: CollectionStatus = CollectionStatus.COMPLETE
    capability: TraceabilityCapability = TraceabilityCapability.SUPPORTED

    def __post_init__(self) -> None:
        if (not isinstance(self.direction, Direction) or not isinstance(self.status, CollectionStatus)
                or not isinstance(self.capability, TraceabilityCapability)):
            raise ValueError('invalid evidence lookup')
        if self.population is not None:
            if (self.population not in (Kind.REQUIREMENT, Kind.TEST, Kind.ARCHITECTURE_DOCUMENT)
                    or not isinstance(self.population, Kind) or self.endpoint is not None or self.relation is not None
                    or self.direction != Direction.OUTBOUND):
                raise ValueError('invalid evidence population lookup')
        elif (not isinstance(self.endpoint, Reference) or not isinstance(self.relation, Relation)
              or self.endpoint.kind != _LEGAL[self.relation][0 if self.direction == Direction.OUTBOUND else 1]):
            raise ValueError('invalid evidence endpoint lookup')

    @property
    def key(self) -> tuple[str, ...]:
        return (self.population or '', self.relation or '', self.direction,
                *(self.endpoint.key if self.endpoint else ()))


@dataclass(frozen=True)
class Limits:
    artifacts: int = 1000
    associations: int = 4000
    runs: int = 2000
    paths: int = 10000

    def __post_init__(self) -> None:
        for value, maximum in ((self.artifacts, 10000), (self.associations, 40000), (self.runs, 10000), (self.paths, 10000)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('invalid evidence limit')


@dataclass(frozen=True, repr=False)
class Collection:
    artifacts: tuple[Reference, ...]
    associations: tuple[Association, ...]
    runs: tuple[Run, ...]
    lookups: tuple[Lookup, ...]
    snapshot: Snapshot
    code: TraceabilityReport
    boundary: str
    collected_at: datetime
    status: CollectionStatus = CollectionStatus.COMPLETE
    limits: Limits = Limits()

    def __post_init__(self) -> None:
        for values, cls, maximum in ((self.artifacts, Reference, 10000), (self.associations, Association, 40000),
                                     (self.runs, Run, 10000), (self.lookups, Lookup, 40000)):
            if not isinstance(values, tuple) or len(values) > maximum or any(not isinstance(v, cls) for v in values):
                raise ValueError('invalid evidence collection')
        if (any(a.kind == Kind.VERIFICATION for a in self.artifacts) or not isinstance(self.snapshot, Snapshot)
                or not isinstance(self.code, TraceabilityReport) or not isinstance(self.limits, Limits)
                or not isinstance(self.status, CollectionStatus) or not isinstance(self.collected_at, datetime)):
            raise ValueError('invalid evidence collection')
        approved(self.boundary)
        aware(self.collected_at)
