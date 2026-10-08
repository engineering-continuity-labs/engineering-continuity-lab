"""Pure offline v0.4 derivation over explicit versioned evidence (FR401–414)."""
from dataclasses import dataclass, replace
from datetime import timezone
from hashlib import sha256

from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import (ArtifactKind, ArtifactReference, Direction as D, TracePath,
                                           TraceStatus as TS, TraceabilityCapability as C)
from continuity.domain.verification import (Association, Collection, Kind as K, Lookup, Outcome, Reference,
                                          Relation as R, Run, Snapshot, endpoint_key, _LEGAL)
from continuity.reporting.traceability import traceability_to_json


@dataclass(frozen=True)
class Diagnostic:
    reason: str
    endpoint: Reference | None = None
    relation: R | None = None


@dataclass(frozen=True)
class Projection:
    association: Association
    code_path: TracePath


@dataclass(frozen=True)
class QualifiedRun:
    run: Run
    qualified: bool
    reason: str | None


@dataclass(frozen=True)
class Metric:
    dimension: str
    numerator: int
    denominator: int
    value: float | None
    status: TS
    unknown_count: int
    excluded_count: int
    reason: str | None


@dataclass(frozen=True)
class Gap:
    endpoint: Reference
    relation: R
    direction: D
    status: TS
    reason: str


@dataclass(frozen=True)
class RequirementResult:
    reference: Reference
    implementation: TS
    tests: TS
    architecture: TS


@dataclass(frozen=True, repr=False)
class Report:
    collection: Collection
    associations: tuple[Association, ...]
    projections: tuple[Projection, ...]
    runs: tuple[QualifiedRun, ...]
    requirements: tuple[RequirementResult, ...]
    metrics: tuple[Metric, ...]
    gaps: tuple[Gap, ...]
    outcomes: tuple[tuple[Outcome, int], ...]
    diagnostics: tuple[Diagnostic, ...]
    dropped: tuple[tuple[str, int], ...]
    snapshot_valid: bool
    rule_version: str = 'offline-evidence-1'


def snapshot_for(code: object, alias: str) -> Snapshot:
    from continuity.domain.traceability import TraceabilityReport
    if not isinstance(code, TraceabilityReport) or not code.evidence.boundaries:
        raise ValueError('invalid code snapshot')
    boundaries = code.evidence.boundaries
    repository = boundaries[0].repository
    revisions = {b.revision for b in boundaries if b.revision is not None}
    if len(revisions) != 1 or any(b.repository != repository or b.revision is None for b in boundaries):
        raise ValueError('invalid code snapshot')
    revision = next(iter(revisions))
    if revision is None:
        raise ValueError('invalid code snapshot')
    return Snapshot(alias, repository, revision, sha256(traceability_to_json(code).encode()).hexdigest())


def _run_key(run: Run) -> tuple[object, ...]:
    return (run.reference.key, run.test.key, run.target.alias, run.target.repository, run.target.revision,
            run.target.fingerprint, run.observed_at.astimezone(timezone.utc).isoformat(), run.outcome,
            run.boundary, run.group or '')


def derive(collection: Collection) -> Report:
    diagnostics: set[Diagnostic] = set()
    dropped: dict[str, int] = {}

    def limited[T](name: str, values: list[T], maximum: int) -> tuple[T, ...]:
        dropped[name] = max(0, len(values) - maximum)
        if dropped[name]:
            diagnostics.add(Diagnostic('LIMIT_EXHAUSTED'))
        return tuple(values[:maximum])

    artifacts = limited('artifacts', sorted(set(collection.artifacts), key=lambda a:a.key), collection.limits.artifacts)
    selected = set(artifacts)
    by_kind = {kind:tuple(a for a in artifacts if a.kind == kind) for kind in (K.REQUIREMENT, K.TEST, K.ARCHITECTURE_DOCUMENT)}
    run_groups: dict[Reference, set[Run]] = {}
    for run in collection.runs:
        run_groups.setdefault(run.reference, set()).add(run)
    conflicting = {ref for ref, values in run_groups.items() if len(values) > 1}
    conflicted_tests = {run.test for ref in conflicting for run in run_groups[ref]}
    for ref in conflicting:
        diagnostics.add(Diagnostic('CONFLICTING_OBSERVATION', ref, R.VERIFICATION_TEST))
    runs = limited('runs', sorted((next(iter(values)) for ref, values in run_groups.items() if ref not in conflicting), key=_run_key), collection.limits.runs)
    run_refs = {run.reference for run in runs}
    groups: dict[tuple[str, ...], set[Lookup]] = {}
    for lookup in collection.lookups:
        groups.setdefault(lookup.key, set()).add(lookup)
    lookups: dict[tuple[str, ...], Lookup] = {}
    for key, values in groups.items():
        ordered = sorted(values, key=lambda l:(l.status, l.capability))
        first = ordered[0]
        if len(values) > 1:
            diagnostics.add(Diagnostic('CONFLICTING_LOOKUP', first.endpoint, first.relation))
            first = replace(first, status=S.PARTIAL, capability=C.UNKNOWN)
        if first.endpoint in conflicted_tests and first.relation == R.VERIFICATION_TEST:
            first = replace(first, status=S.PARTIAL, capability=C.UNKNOWN)
        lookups[key] = first
    try:
        snapshot_valid = collection.snapshot == snapshot_for(collection.code, collection.snapshot.alias)
    except ValueError:
        snapshot_valid = False
    if not snapshot_valid:
        diagnostics.add(Diagnostic('SNAPSHOT_MISMATCH'))
    legacy = {w.reference for w in collection.code.evidence.work_items} | {a.artifact for a in collection.code.artifacts if a.artifact.kind == ArtifactKind.COMPONENT}
    run_pairs = {(run.reference,run.test) for run in runs}
    associations: list[Association] = []
    for link in sorted(set(collection.associations), key=lambda a:a.key):
        resolved = link.source in selected or link.source in run_refs
        if isinstance(link.target, Reference):
            resolved &= link.target in selected
        else:
            resolved &= snapshot_valid and link.target in legacy and link.source.scope in {b.project for b in collection.code.evidence.boundaries}
        if link.boundary != collection.boundary or not resolved:
            diagnostics.add(Diagnostic('UNRESOLVED_ASSOCIATION', link.source, link.relation))
        elif link.relation == R.VERIFICATION_TEST:
            if (link.source,link.target) in run_pairs:
                associations.append(link)
            else:
                diagnostics.add(Diagnostic('UNRESOLVED_ASSOCIATION', link.source, link.relation))
        else:
            associations.append(link)
    kept = limited('associations', associations, collection.limits.associations)
    def path_key(path: TracePath) -> tuple[object, ...]:
        return (tuple(endpoint_key(n) for n in path.nodes),
                path.supports,
                path.status,path.boundaries)
    paths_by_wi: dict[ArtifactReference,list[TracePath]] = {}
    for path in collection.code.paths:
        paths_by_wi.setdefault(path.nodes[0],[]).append(path)
    for candidates in paths_by_wi.values():
        candidates.sort(key=path_key)
    projections: list[Projection] = []
    total_paths = 0
    for link in kept:
        if link.relation == R.REQUIREMENT_WORK_ITEM and isinstance(link.target,ArtifactReference):
            candidates = paths_by_wi.get(link.target,[])
            total_paths += len(candidates)
            capacity = max(0,collection.limits.paths-len(projections))
            projections.extend(Projection(link,path) for path in candidates[:capacity])
    kept_paths = tuple(projections)
    dropped['paths'] = total_paths-len(kept_paths)
    if dropped['paths']:
        diagnostics.add(Diagnostic('LIMIT_EXHAUSTED'))
    verification_pairs = {(a.source,a.target) for a in kept if a.relation == R.VERIFICATION_TEST}
    qualified: list[QualifiedRun] = []
    for run in runs:
        reason = None
        if run.boundary != collection.boundary:
            reason = 'BOUNDARY_MISMATCH'
        elif run.test not in selected:
            reason = 'UNOBSERVED_TEST_VERSION'
        elif not snapshot_valid or run.target != collection.snapshot:
            reason = 'TARGET_MISMATCH'
        elif (run.reference,run.test) not in verification_pairs:
            reason = 'UNRESOLVED_VERIFICATION'
        qualified.append(QualifiedRun(run, reason is None, reason))
        if reason:
            diagnostics.add(Diagnostic(reason, run.test, R.VERIFICATION_TEST))
    partial = bool(diagnostics) or collection.status != S.COMPLETE
    status = S.PARTIAL if partial else S.COMPLETE
    if collection.status == S.FAILED and not (artifacts or kept or runs):
        status = S.FAILED
    normalized = replace(collection, artifacts=artifacts, associations=kept, runs=runs,
                         lookups=tuple(lookups[k] for k in sorted(lookups)), status=status)

    def get(endpoint: Reference | None = None, relation: R | None = None, direction: D = D.OUTBOUND,
            population: K | None = None) -> Lookup | None:
        key = Lookup(endpoint, relation, population, direction).key
        return lookups.get(key)

    def state(populations: tuple[K, ...], relations: tuple[R, ...]) -> tuple[bool, bool]:
        requested = [get(population=p) for p in populations]
        for relation in relations:
            source, target = _LEGAL[relation]
            for artifact in (*artifacts, *sorted(run_refs, key=lambda a:a.key)):
                if artifact.kind == source:
                    requested.append(get(artifact, relation))
                elif artifact.kind == target:
                    requested.append(get(artifact, relation, D.INBOUND))
        available = all(l is not None and l.capability == C.SUPPORTED and l.status != S.FAILED for l in requested)
        complete = status == S.COMPLETE and all(l is not None and l.status == S.COMPLETE for l in requested)
        return available, complete

    def absence(ref: Reference, relation: R, direction: D = D.OUTBOUND) -> TS:
        source, target = _LEGAL[relation]
        populations = tuple(K(k) for k in (source, target) if k in by_kind)
        required = [get(population=k) for k in populations] + [get(ref, relation, direction)]
        if any(l is None or l.capability != C.SUPPORTED or l.status == S.FAILED for l in required):
            return TS.UNAVAILABLE
        return TS.MISSING if status == S.COMPLETE and all(l is not None and l.status == S.COMPLETE for l in required) else TS.PARTIAL

    code_requirements = {p.association.source for p in kept_paths if p.code_path.status == TS.VERIFIED and p.code_path.nodes[-1].kind == ArtifactKind.COMPONENT}
    test_requirements = {a.target for a in kept if a.relation == R.TEST_REQUIREMENT}
    document_requirements = {a.target for a in kept if a.relation == R.DOCUMENT_REQUIREMENT}
    executed_tests = {r.run.test for r in qualified if r.qualified and r.run.outcome in (Outcome.PASS, Outcome.FAIL)}
    requirement_results = []
    for ref in by_kind[K.REQUIREMENT]:
        paths = [p for p in kept_paths if p.association.source == ref]
        implementation = (TS.VERIFIED if ref in code_requirements else TS.PARTIAL if any(p.code_path.status == TS.PARTIAL for p in paths) else TS.UNAVAILABLE if any(p.code_path.status == TS.UNAVAILABLE for p in paths) else absence(ref, R.REQUIREMENT_WORK_ITEM))
        if not snapshot_valid:
            implementation = TS.UNAVAILABLE
        requirement_results.append(RequirementResult(ref, implementation,
            TS.VERIFIED if ref in test_requirements else absence(ref, R.TEST_REQUIREMENT, D.INBOUND),
            TS.VERIFIED if ref in document_requirements else absence(ref, R.DOCUMENT_REQUIREMENT, D.INBOUND)))
    gaps = []
    for item in requirement_results:
        for relation, direction, trace_state in ((R.REQUIREMENT_WORK_ITEM,D.OUTBOUND,item.implementation),
                                                (R.TEST_REQUIREMENT,D.INBOUND,item.tests),
                                                (R.DOCUMENT_REQUIREMENT,D.INBOUND,item.architecture)):
            if trace_state != TS.VERIFIED:
                reason = 'NO_OBSERVED_LINK' if trace_state == TS.MISSING else 'LOOKUP_UNAVAILABLE' if trace_state == TS.UNAVAILABLE else 'INCOMPLETE_EVIDENCE'
                if relation == R.REQUIREMENT_WORK_ITEM and not snapshot_valid:
                    reason = 'SNAPSHOT_MISMATCH'
                gaps.append(Gap(item.reference,relation,direction,trace_state,reason))
    dimensions = (
        ('requirement_implementation', code_requirements, K.REQUIREMENT, (K.REQUIREMENT,), (R.REQUIREMENT_WORK_ITEM,)),
        ('requirement_tests', test_requirements, K.REQUIREMENT, (K.REQUIREMENT, K.TEST), (R.TEST_REQUIREMENT,)),
        ('requirement_architecture', document_requirements, K.REQUIREMENT, (K.REQUIREMENT, K.ARCHITECTURE_DOCUMENT), (R.DOCUMENT_REQUIREMENT,)),
        ('executed_tests', executed_tests, K.TEST, (K.TEST,), (R.VERIFICATION_TEST,)),
    )
    metrics = []
    for name, covered, population, populations, relations in dimensions:
        available, complete = state(populations, relations)
        if name == 'requirement_implementation':
            code_metric = next(m for m in collection.code.metrics if m.dimension == 'work_item_implementation')
            available &= snapshot_valid and code_metric.value is not None
            complete &= collection.code.evidence.status == S.COMPLETE and code_metric.collection_status == S.COMPLETE
        if name == 'executed_tests':
            available &= snapshot_valid
        n, denominator = len(covered & set(by_kind[population])), len(by_kind[population])
        excluded = len({d.endpoint for d in diagnostics if d.relation in relations and d.endpoint is not None})
        missing = sum(getattr(r, {'requirement_implementation':'implementation','requirement_tests':'tests','requirement_architecture':'architecture'}[name]) in (TS.UNAVAILABLE, TS.PARTIAL) for r in requirement_results) if population == K.REQUIREMENT else len(({r.run.test for r in qualified if not r.qualified} | conflicted_tests) & set(by_kind[K.TEST]))
        metric_status = TS.UNAVAILABLE if not available or not denominator else TS.VERIFIED if complete and n == denominator else TS.MISSING if complete and not n else TS.PARTIAL
        metrics.append(Metric(name,n,denominator,n/denominator if available and denominator else None,metric_status,missing,excluded,
                              'EMPTY_POPULATION' if not denominator else 'LOOKUP_UNAVAILABLE' if not available else 'INCOMPLETE_EVIDENCE' if not complete else None))
    return Report(normalized,kept,kept_paths,tuple(qualified),tuple(requirement_results),tuple(metrics),tuple(gaps),
                  tuple((outcome,sum(r.qualified and r.run.outcome == outcome for r in qualified)) for outcome in Outcome),
                  tuple(sorted(diagnostics,key=lambda d:(d.reason,d.endpoint.key if d.endpoint else (),d.relation or ''))),
                  tuple(sorted(dropped.items())),snapshot_valid)
