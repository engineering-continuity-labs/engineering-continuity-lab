"""Pure, deterministic typed offline evidence normalization and derivation."""
from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from continuity.domain.models import ComponentStrategy, DirectoryComponents, History
from continuity.domain.reviews import CollectionStatus, ReviewEvidenceCollection
from continuity.domain.traceability import (
    ArtifactKind as K, ArtifactReference as Ref, ArtifactTraceResult, CoverageMetric,
    Direction as D, EvidenceBoundary, GapReason as R, LinkKey, LookupEvidence,
    Observation, Population as P, TraceDiagnostic, TraceGap, TraceLink,
    TraceLinkOrigin as O, TraceLinkType as T, TracePath, TraceStatus as S,
    TraceabilityCapability as C, TraceabilityEvidenceCollection as Collection,
    TraceabilityReport, WorkItemEvidence,
)


LEGAL = {
    T.WI_PR: (K.WORK_ITEM, K.PULL_REQUEST, (O.DIRECT_PROVIDER_LINK,)),
    T.WI_COMMIT: (K.WORK_ITEM, K.COMMIT, (O.DIRECT_PROVIDER_LINK,)),
    T.PR_COMMIT: (K.PULL_REQUEST, K.COMMIT, (O.DIRECT_PROVIDER_LINK,)),
    T.COMMIT_PATH: (K.COMMIT, K.CHANGED_PATH, (O.DIRECT_SOURCE_LINK, O.DIRECT_PROVIDER_LINK)),
    T.PR_PATH: (K.PULL_REQUEST, K.PR_PATH, (O.DIRECT_PROVIDER_LINK,)),
}


def _refs(refs: Iterable[Ref]) -> tuple[Ref, ...]:
    return tuple(sorted(set(refs), key=lambda r: r.key))


def _diagnostic_key(d: TraceDiagnostic) -> tuple[object, ...]:
    return d.reason, d.endpoint.key if d.endpoint else (), d.relationship or ""


def _gap_key(g: TraceGap) -> tuple[object, ...]:
    return g.endpoint.key, g.relationship, g.direction, g.status, g.reason


def _compatible(a: EvidenceBoundary, b: EvidenceBoundary) -> bool:
    same_scope = (a.repository, a.identity_mapping, a.filter_policy) == (
        b.repository, b.identity_mapping, b.filter_policy)
    same_query = (a.query, a.time_field, a.start, a.end) == (b.query, b.time_field, b.start, b.end)
    declared_join = a.join_contract is not None and a.join_contract == b.join_contract
    same_revision = a.revision is None or b.revision is None or a.revision == b.revision
    return (same_scope and same_revision and a.join_contract == b.join_contract
            and (same_query or declared_join))


def normalize(evidence: Collection) -> Collection:
    """Quarantine ambiguous observations rather than taking first/last arrival."""
    diagnostics = list(evidence.diagnostics)
    boundaries = {b.identifier: b for b in evidence.boundaries}
    if len(boundaries) != len(set(evidence.boundaries)):
        raise ValueError("conflicting boundary identity")
    candidates: list[TraceLink] = []
    observations: dict[tuple[str, str], set[tuple[LinkKey, Observation]]] = defaultdict(set)
    for link in evidence.links:
        legal = LEGAL.get(link.type)
        reason: R | None = None
        if legal is None:
            reason = R.UNSUPPORTED_RELATION
        elif (link.source.kind, link.target.kind) != legal[:2] or link.origin not in legal[2]:
            reason = R.INVALID_OBSERVATION
        elif not link.observations or link.supports:
            reason = R.INVALID_OBSERVATION
        elif link.source == link.target:
            reason = R.INVALID_OBSERVATION
        elif link.type == T.COMMIT_PATH and (
            link.source.repository != link.target.repository
            or link.source.identifier != link.target.context
            or link.source.algorithm != link.target.algorithm):
            reason = R.INVALID_OBSERVATION
        elif link.type == T.PR_PATH and (
            link.source.repository != link.target.repository
            or link.source.identifier != link.target.context):
            reason = R.INVALID_OBSERVATION
        for observation in link.observations:
            boundary = boundaries.get(observation.boundary)
            if boundary is None:
                reason = R.INVALID_OBSERVATION
                continue
            for ref in (link.source, link.target):
                if ref.repository and ref.repository != boundary.repository:
                    reason = R.INCOMPATIBLE_BOUNDARY
                if ref.kind == K.WORK_ITEM and (
                    ref.provider, ref.instance, ref.scope) != (
                        boundary.provider, boundary.instance, boundary.project):
                    reason = R.INCOMPATIBLE_BOUNDARY
                if ref.kind in (K.PULL_REQUEST, K.PR_PATH) and (
                    ref.provider, ref.instance, ref.scope) != (boundary.provider, boundary.instance, boundary.repository):
                    reason = R.INCOMPATIBLE_BOUNDARY
        if reason is not None:
            for ref in (link.source, link.target):
                diagnostics.append(TraceDiagnostic(reason, ref, link.type if legal else None))
            continue
        candidates.append(link)
        for observation in link.observations:
            observations[observation.key].add((link.key, observation))
    conflicts = {key for key, values in observations.items() if len(values) > 1}
    grouped: dict[LinkKey, TraceLink] = {}
    for link in candidates:
        valid = tuple(o for o in link.observations if o.key not in conflicts)
        if len(valid) != len(link.observations):
            diagnostics.extend(TraceDiagnostic(R.CONFLICTING_OBSERVATION, ref, link.type)
                               for ref in (link.source, link.target))
        if not valid:
            continue
        old = grouped.get(link.key)
        union = set(valid) | (set(old.observations) if old else set())
        grouped[link.key] = replace(link, observations=tuple(sorted(
            union, key=lambda o: (o.boundary, o.identifier, o.observed_at, o.basis))))
    work_items: dict[Ref, set[WorkItemEvidence]] = defaultdict(set)
    for item in evidence.work_items:
        work_items[item.reference].add(item)
    items: list[WorkItemEvidence] = []
    for ref, values in work_items.items():
        if len(values) != 1 or any(v.provenance.boundary not in boundaries for v in values):
            diagnostics.append(TraceDiagnostic(R.CONFLICTING_OBSERVATION, ref))
        elif any((ref.provider, ref.instance, ref.scope) !=
                 (boundaries[v.provenance.boundary].provider, boundaries[v.provenance.boundary].instance,
                  boundaries[v.provenance.boundary].project) for v in values):
            diagnostics.append(TraceDiagnostic(R.INCOMPATIBLE_BOUNDARY, ref))
        else:
            items.extend(values)
    lookups: dict[tuple[object, ...], list[LookupEvidence]] = defaultdict(list)
    for lookup in evidence.lookups:
        lookups[lookup.key].append(lookup)
    normalized_lookups: list[LookupEvidence] = []
    for lookup_values in lookups.values():
        first = sorted(lookup_values, key=lambda l: (l.boundary, l.capability, l.status))[0]
        capability = C.SUPPORTED
        status = CollectionStatus.COMPLETE
        for lookup in lookup_values:
            if lookup.boundary not in boundaries or lookup.capability != C.SUPPORTED:
                capability = C.UNKNOWN if any(v.capability == C.UNKNOWN for v in lookup_values) else C.UNSUPPORTED
            if lookup.status != CollectionStatus.COMPLETE:
                status = (CollectionStatus.FAILED if all(v.status == CollectionStatus.FAILED for v in lookup_values)
                          else CollectionStatus.PARTIAL)
            if (lookup.boundary in boundaries and first.boundary in boundaries
                    and not _compatible(boundaries[lookup.boundary], boundaries[first.boundary])):
                capability = C.UNKNOWN
        for lookup in lookup_values:
            boundary = boundaries.get(lookup.boundary)
            lookup_ref = lookup.endpoint
            if boundary is not None and lookup_ref is not None:
                valid_scope = (not lookup_ref.repository or lookup_ref.repository == boundary.repository)
                if lookup_ref.kind == K.WORK_ITEM:
                    valid_scope &= (lookup_ref.provider, lookup_ref.instance, lookup_ref.scope) == (
                        boundary.provider, boundary.instance, boundary.project)
                elif lookup_ref.kind in (K.PULL_REQUEST, K.PR_PATH):
                    valid_scope &= (lookup_ref.provider, lookup_ref.instance, lookup_ref.scope) == (
                        boundary.provider, boundary.instance, boundary.repository)
                if not valid_scope:
                    capability = C.UNKNOWN
                    diagnostics.append(TraceDiagnostic(R.INCOMPATIBLE_BOUNDARY, lookup_ref, lookup.relationship))
        for diagnostic in diagnostics:
            if (diagnostic.endpoint is None or diagnostic.endpoint == first.endpoint) and (
                diagnostic.relationship is None or diagnostic.relationship == first.relationship):
                if diagnostic.reason == R.INCOMPATIBLE_BOUNDARY:
                    capability = C.UNKNOWN
                else:
                    status = CollectionStatus.PARTIAL
        normalized_lookups.append(replace(first, capability=capability, status=status))
    # Invalid population shapes fail safely; this is a normalized-value API.
    for refs, kind in ((evidence.pull_requests, K.PULL_REQUEST),
                       (evidence.merged_pull_requests, K.PULL_REQUEST),
                       (evidence.commits, K.COMMIT), (evidence.changed_paths, K.CHANGED_PATH)):
        if any(ref.kind != kind for ref in refs):
            raise ValueError("invalid population kind")
    if not set(evidence.merged_pull_requests) <= set(evidence.pull_requests):
        raise ValueError("merged population must be independently observed")
    status = evidence.status
    if diagnostics and status == CollectionStatus.COMPLETE:
        status = CollectionStatus.PARTIAL
    if status == CollectionStatus.FAILED and (items or grouped or evidence.commits):
        status = CollectionStatus.PARTIAL
    return replace(evidence, boundaries=tuple(sorted(set(evidence.boundaries), key=lambda b: b.identifier)),
                   work_items=tuple(sorted(items, key=lambda w: w.reference.key)),
                   pull_requests=_refs(evidence.pull_requests),
                   merged_pull_requests=_refs(evidence.merged_pull_requests),
                   commits=_refs(evidence.commits), changed_paths=_refs(evidence.changed_paths),
                   links=tuple(grouped[k] for k in sorted(grouped)),
                   lookups=tuple(sorted(normalized_lookups, key=lambda l: repr(l.key))),
                   diagnostics=tuple(sorted(set(diagnostics), key=_diagnostic_key)), status=status)


def aggregate_status(n: int, f: int, *, available: bool = True, complete: bool = True) -> S:
    if not 0 <= f <= n:
        raise ValueError("invalid distinct artifact counts")
    if not available or n == 0:
        return S.UNAVAILABLE
    if not complete:
        return S.PARTIAL
    return S.MISSING if f == 0 else S.VERIFIED if f == n else S.PARTIAL


class _Context:
    def __init__(self, evidence: Collection) -> None:
        self.e = evidence
        self.boundaries = {b.identifier: b for b in evidence.boundaries}
        self.lookups = {l.key: l for l in evidence.lookups}
        self.population = set(w.reference for w in evidence.work_items) | set(evidence.pull_requests) | set(
            evidence.commits) | set(evidence.changed_paths)
        self.links: list[TraceLink] = []
        self.excluded_refs: set[Ref] = set()
        self.incompatible = False
        self.diagnostics: list[TraceDiagnostic] = list(evidence.diagnostics)
        for link in evidence.links:
            # PR snapshot paths need no Git population; commit paths do.
            resolved = (link.source in self.population and
                        (link.target in self.population or link.target.kind == K.PR_PATH))
            compatible = all(_compatible(a, b) for a in self.boundaries.values()
                             for b in (self.boundaries[o.boundary] for o in link.observations))
            if not resolved or not compatible:
                self.excluded_refs.update(ref for ref in (link.source, link.target)
                                          if ref not in self.population and ref.kind != K.PR_PATH)
                self.incompatible |= not compatible
                for ref in (link.source, link.target):
                    self.diagnostics.append(TraceDiagnostic(
                        R.OUTSIDE_BOUNDARY if not resolved else R.INCOMPATIBLE_BOUNDARY, ref, link.type))
            else:
                self.links.append(link)
        self.outgoing: dict[Ref, list[TraceLink]] = defaultdict(list)
        self.incoming: dict[Ref, list[TraceLink]] = defaultdict(list)
        for link in self.links:
            self.outgoing[link.source].append(link)
            self.incoming[link.target].append(link)

    def lookup(self, endpoint: Ref | None = None, relationship: T | None = None,
               direction: D = D.OUTBOUND, population: P | None = None) -> LookupEvidence | None:
        return self.lookups.get((endpoint.key if endpoint else (), relationship, direction, population))

    def gap(self, ref: Ref, kind: T, direction: D = D.OUTBOUND) -> TraceGap:
        lookup = self.lookup(ref, kind, direction)
        if self.incompatible:
            status, reason = S.UNAVAILABLE, R.INCOMPATIBLE_BOUNDARY
        elif lookup is None or lookup.status == CollectionStatus.FAILED:
            status, reason = S.UNAVAILABLE, R.LOOKUP_UNAVAILABLE
        elif lookup.capability != C.SUPPORTED:
            status, reason = S.UNAVAILABLE, R.CAPABILITY_UNAVAILABLE
        elif lookup.status != CollectionStatus.COMPLETE:
            status, reason = S.PARTIAL, R.INCOMPLETE_LOOKUP
        elif any(d.endpoint == ref and d.relationship == kind and d.reason == R.OUTSIDE_BOUNDARY
                 for d in self.diagnostics):
            status, reason = S.UNAVAILABLE, R.OUTSIDE_BOUNDARY
        else:
            status, reason = S.MISSING, R.NO_OBSERVED_LINK
        return TraceGap(ref, kind, direction, status, reason)

    def state(self, populations: tuple[P, ...], kinds: tuple[T, ...]) -> tuple[bool, bool]:
        selected = [self.lookup(population=p) for p in populations]
        selected.extend(l for l in self.e.lookups if l.relationship in kinds)
        available = not self.incompatible and all(l is not None and l.capability == C.SUPPORTED
                        and l.status != CollectionStatus.FAILED for l in selected)
        complete = self.e.status == CollectionStatus.COMPLETE and all(
            l is not None and l.status == CollectionStatus.COMPLETE for l in selected)
        # Require every eligible endpoint's requested lookup, not just supplied records.
        for kind in kinds:
            source, target, _ = LEGAL[kind]
            for ref in self.population:
                if ref.kind in (source, target):
                    lookup = self.lookup(ref, kind, D.OUTBOUND if ref.kind == source else D.INBOUND)
                    if lookup is None or lookup.capability != C.SUPPORTED or lookup.status == CollectionStatus.FAILED:
                        available = False
                    if lookup is None or lookup.status != CollectionStatus.COMPLETE:
                        complete = False
        return available, complete


def derive(evidence: Collection, strategy: ComponentStrategy | None = None) -> TraceabilityReport:
    e = normalize(evidence)
    if strategy is None:
        strategy = DirectoryComponents(depth=2)
    if isinstance(strategy, DirectoryComponents):
        if e.component_strategy != "directory" or e.component_configuration != f"depth-{strategy.depth}":
            raise ValueError("incompatible component configuration")
    else:
        raise ValueError("unsupported reproducible component strategy")
    ctx = _Context(e)
    mappings: list[TraceLink] = []
    for ref in _refs(l.target for l in ctx.links if l.type in (T.COMMIT_PATH, T.PR_PATH)):
        component = Ref(K.COMPONENT, "source", "offline", "components", strategy.component(ref.identifier),
                        ref.repository, e.component_strategy, e.component_configuration)
        supports = tuple(sorted(l.key for l in ctx.links if l.target == ref))
        mappings.append(TraceLink(ref, component, T.PATH_COMPONENT, O.DERIVED_LINK, (), supports))
    outgoing: dict[Ref, list[TraceLink]] = defaultdict(list)
    for link in ctx.links + mappings:
        outgoing[link.source].append(link)
    next_kind = {K.WORK_ITEM: T.WI_PR, K.PULL_REQUEST: T.PR_COMMIT, K.COMMIT: T.COMMIT_PATH}
    paths: list[TracePath] = []
    gaps: list[TraceGap] = []
    for ref in sorted(ctx.population, key=lambda r: r.key):
        if ref.kind not in (K.WORK_ITEM, K.PULL_REQUEST, K.COMMIT):
            continue
        stack: list[tuple[tuple[Ref, ...], tuple[TraceLink, ...]]] = [((ref,), ())]
        while stack:
            nodes, links = stack.pop()
            last = nodes[-1]
            edges = outgoing.get(last, [])
            if edges:
                for link in reversed(sorted(edges, key=lambda l: l.key)):
                    if link.target in nodes or len(nodes) >= 5:
                        ctx.diagnostics.append(TraceDiagnostic(R.INVALID_OBSERVATION, last, link.type))
                        continue
                    stack.append((nodes + (link.target,), links + (link,)))
                continue
            full = tuple(n.kind for n in nodes) == (
                K.WORK_ITEM, K.PULL_REQUEST, K.COMMIT, K.CHANGED_PATH, K.COMPONENT)
            path_gaps: list[TraceGap] = []
            if not full:
                if last.kind in next_kind:
                    path_gaps.append(ctx.gap(last, next_kind[last.kind]))
                if ref.kind == K.PULL_REQUEST:
                    incoming = [l for l in ctx.incoming[ref] if l.type == T.WI_PR]
                    if not incoming:
                        path_gaps.append(ctx.gap(ref, T.WI_PR, D.INBOUND))
                    else:
                        path_gaps.append(TraceGap(ref, T.WI_PR, D.INBOUND, S.PARTIAL,
                                                  R.UNRESOLVED_NORMATIVE_SEGMENT))
                elif ref.kind == K.COMMIT:
                    incoming = [l for l in ctx.incoming[ref] if l.type == T.PR_COMMIT]
                    if not incoming:
                        path_gaps.append(ctx.gap(ref, T.PR_COMMIT, D.INBOUND))
                    else:
                        path_gaps.append(TraceGap(ref, T.PR_COMMIT, D.INBOUND, S.PARTIAL,
                                                  R.UNRESOLVED_NORMATIVE_SEGMENT))
                    # Intent absence considers both recorded direct and PR routes.
                    has_intent = any(l.type == T.WI_COMMIT for l in ctx.incoming[ref]) or any(
                        any(w.type == T.WI_PR for w in ctx.incoming[p.source]) for p in incoming)
                    if not has_intent:
                        path_gaps.append(ctx.gap(ref, T.WI_COMMIT, D.INBOUND))
                if any(l.type == T.WI_COMMIT for l in links):
                    if any(l.type == T.WI_PR for l in ctx.outgoing[ref]):
                        path_gaps.append(TraceGap(ref, T.WI_PR, D.OUTBOUND, S.PARTIAL,
                                                  R.UNRESOLVED_NORMATIVE_SEGMENT))
                    else:
                        path_gaps.append(ctx.gap(ref, T.WI_PR))
                if any(l.type == T.PR_PATH for l in links):
                    pr = next(n for n in nodes if n.kind == K.PULL_REQUEST)
                    if any(l.type == T.PR_COMMIT for l in ctx.outgoing[pr]):
                        path_gaps.append(TraceGap(pr, T.PR_COMMIT, D.OUTBOUND, S.PARTIAL,
                                                  R.UNRESOLVED_NORMATIVE_SEGMENT))
                    else:
                        path_gaps.append(ctx.gap(pr, T.PR_COMMIT))
            supports = tuple(l.key for l in links)
            boundary_refs = tuple(sorted({o.boundary for l in links for o in l.observations}))
            paths.append(TracePath(nodes, supports, boundary_refs, S.VERIFIED if full else S.PARTIAL,
                                   tuple(sorted(set(path_gaps), key=_gap_key))))
            gaps.extend(path_gaps)
    # WI implementation absence needs both outbound alternatives, not just WI_PR.
    for item in e.work_items:
        if not outgoing[item.reference]:
            gaps.append(ctx.gap(item.reference, T.WI_COMMIT))
    canonical_paths = tuple(sorted(set(paths), key=lambda p: (tuple(n.key for n in p.nodes), p.supports)))
    canonical_gaps = tuple(sorted(set(gaps), key=_gap_key))
    intent_pr = {l.target for l in ctx.links if l.type == T.WI_PR}
    intent_commits = {l.target for l in ctx.links if l.type == T.WI_COMMIT} | {
        l.target for l in ctx.links if l.type == T.PR_COMMIT and l.source in intent_pr}
    implemented_wi = {p.nodes[0] for p in canonical_paths if p.nodes[0].kind == K.WORK_ITEM
                      and p.nodes[-1].kind == K.COMPONENT
                      and any(n.kind == K.COMMIT for n in p.nodes)}
    occurrence_components = {l.source: l.target for l in mappings if l.source.kind == K.CHANGED_PATH}
    observed_changes = {l.target for l in ctx.links if l.type == T.COMMIT_PATH}
    intent_changes = {l.target for l in ctx.links if l.type == T.COMMIT_PATH and l.source in intent_commits}
    metrics: list[CoverageMetric] = []
    boundary_ids = tuple(b.identifier for b in e.boundaries)
    sources = tuple(sorted({b.provider for b in e.boundaries}))

    def metric(name: str, population: set[Ref], covered: set[Ref], populations: tuple[P, ...],
               kinds: tuple[T, ...], component: Ref | None = None) -> None:
        available, complete = ctx.state(populations, kinds)
        n, f = len(population), len(population & covered)
        status = aggregate_status(n, f, available=available, complete=complete)
        value = f / n if n and available else None
        reason = (R.EMPTY_POPULATION if not n else R.CAPABILITY_UNAVAILABLE if not available
                  else R.INCOMPLETE_LOOKUP if not complete else None)
        if name == "merged_pr_intent":
            excluded = {r for r in ctx.excluded_refs if r.kind == K.PULL_REQUEST} | (
                set(e.pull_requests) - set(e.merged_pull_requests))
        elif name == "commit_intent":
            excluded = {r for r in ctx.excluded_refs if r.kind == K.COMMIT}
        elif name == "work_item_implementation":
            excluded = {r for r in ctx.excluded_refs if r.kind == K.WORK_ITEM}
        else:
            excluded = {r for r in ctx.excluded_refs if r.kind == K.CHANGED_PATH and component is not None
                        and r.repository == component.repository
                        and strategy.component(r.identifier) == component.identifier}
        metrics.append(CoverageMetric(name, f, n, value, status, e.status, boundary_ids, sources,
                                      0 if complete and available else n - f, len(excluded), reason, component))

    metric("merged_pr_intent", set(e.merged_pull_requests), intent_pr,
           (P.PULL_REQUESTS, P.WORK_ITEMS), (T.WI_PR,))
    metric("commit_intent", set(e.commits), intent_commits,
           (P.COMMITS, P.WORK_ITEMS, P.PULL_REQUESTS), (T.WI_PR, T.WI_COMMIT, T.PR_COMMIT))
    for component in _refs(occurrence_components.values()):
        population = {p for p in observed_changes if occurrence_components.get(p) == component}
        metric("component_change_intent", population, intent_changes,
               (P.CHANGES, P.COMMITS, P.WORK_ITEMS, P.PULL_REQUESTS),
               (T.WI_PR, T.WI_COMMIT, T.PR_COMMIT, T.COMMIT_PATH), component)
    metric("work_item_implementation", {w.reference for w in e.work_items}, implemented_wi,
           (P.WORK_ITEMS, P.COMMITS, P.CHANGES, P.PULL_REQUESTS),
           (T.WI_PR, T.WI_COMMIT, T.PR_COMMIT, T.COMMIT_PATH))
    artifacts: list[ArtifactTraceResult] = []
    available, complete = ctx.state((P.WORK_ITEMS, P.PULL_REQUESTS, P.COMMITS, P.CHANGES),
                                    (T.WI_PR, T.PR_COMMIT, T.COMMIT_PATH))
    for ref in _refs(ctx.population | set(occurrence_components.values())):
        related = tuple(p for p in canonical_paths if ref in p.nodes)
        related_gaps = tuple(g for g in canonical_gaps if g.endpoint == ref)
        full = any(p.status == S.VERIFIED for p in related)
        # Positive full paths survive partial acquisition; aggregate is separate.
        if ref.kind == K.COMPONENT:
            occurrences = {p for p, c in occurrence_components.items() if c == ref}
            full_occurrences = {n for p in related if p.status == S.VERIFIED
                                for n in p.nodes if n.kind == K.CHANGED_PATH}
            status = aggregate_status(len(occurrences), len(occurrences & full_occurrences),
                                      available=available, complete=complete)
        elif full:
            status = S.VERIFIED
        elif related and any(p.supports for p in related):
            status = S.PARTIAL
        elif any(g.status == S.UNAVAILABLE for g in related_gaps):
            status = S.UNAVAILABLE
        elif any(g.status == S.PARTIAL for g in related_gaps):
            status = S.PARTIAL
        else:
            status = aggregate_status(1, 0, available=available, complete=complete)
        artifacts.append(ArtifactTraceResult(ref, status, related, related_gaps))
    full_changes = {n for p in canonical_paths if p.status == S.VERIFIED
                    for n in p.nodes if n.kind == K.CHANGED_PATH}
    summary = aggregate_status(len(observed_changes), len(full_changes & observed_changes),
                               available=available, complete=complete)
    shortcuts: dict[LinkKey, TraceLink] = {}
    for path in canonical_paths:
        if path.nodes[0].kind == K.WORK_ITEM and path.nodes[-1].kind == K.COMPONENT:
            link = TraceLink(path.nodes[0], path.nodes[-1], T.WI_COMPONENT, O.DERIVED_LINK, (), path.supports)
            # Retain each supported route via TracePath; shortcut union is auditable.
            old = shortcuts.get(link.key)
            if old:
                link = replace(link, supports=tuple(sorted(set(old.supports + link.supports))))
            shortcuts[link.key] = link
    return TraceabilityReport(e, e.links, tuple(sorted(mappings + list(shortcuts.values()), key=lambda l: l.key)),
                              canonical_paths, canonical_gaps, tuple(artifacts), tuple(metrics), summary,
                              tuple(sorted(set(ctx.diagnostics), key=_diagnostic_key)))


def project_history(history: History, boundary: EvidenceBoundary) -> tuple[tuple[Ref, ...], tuple[Ref, ...], tuple[TraceLink, ...]]:
    """Nonmutating projection; Git author/scoring facts are never copied or changed."""
    if boundary.revision is None or history.revision != boundary.revision:
        raise ValueError("incompatible Git source revision")
    commits: list[Ref] = []
    paths: list[Ref] = []
    links: list[TraceLink] = []
    for commit in history.commits:
        algorithm = "sha256" if len(commit.revision) == 64 else "sha1"
        ref = Ref(K.COMMIT, "source", "offline", "git", commit.revision, boundary.repository, algorithm=algorithm)
        commits.append(ref)
        for index, change in enumerate(commit.changes):
            path = Ref(K.CHANGED_PATH, "source", "offline", "git", change.path,
                       boundary.repository, commit.revision, algorithm=algorithm)
            paths.append(path)
            observation = Observation(f"git-{commit.revision}-{index}", boundary.identifier,
                                      boundary.collected_at, "git_commit_change")
            links.append(TraceLink(ref, path, T.COMMIT_PATH, O.DIRECT_SOURCE_LINK, (observation,)))
    return _refs(commits), _refs(paths), tuple(sorted(links, key=lambda l: l.key))


def project_reviews(reviews: ReviewEvidenceCollection, boundary: EvidenceBoundary) -> tuple[tuple[Ref, ...], tuple[Ref, ...], tuple[TraceLink, ...]]:
    """Reference projection only; review/merge facts remain owned by v0.2 evidence."""
    source = reviews.provenance
    if (source.provider, source.repository, source.evidence_boundary, source.retrieved_at) != (
            boundary.provider, boundary.repository, boundary.query, boundary.collected_at):
        raise ValueError("incompatible review source provenance")
    refs: list[Ref] = []
    merged: list[Ref] = []
    links: list[TraceLink] = []
    for pr in reviews.pull_requests:
        ref = Ref(K.PULL_REQUEST, boundary.provider, boundary.instance, boundary.repository,
                  pr.identifier, boundary.repository)
        refs.append(ref)
        if pr.merged_at is not None:
            merged.append(ref)
        for index, value in enumerate(pr.changed_paths):
            path = Ref(K.PR_PATH, boundary.provider, boundary.instance, boundary.repository,
                       value, boundary.repository, pr.identifier)
            observation = Observation(f"pr-{pr.identifier}-{index}", boundary.identifier,
                                      boundary.collected_at, "provider_pr_changed_path")
            links.append(TraceLink(ref, path, T.PR_PATH, O.DIRECT_PROVIDER_LINK, (observation,)))
    return _refs(refs), _refs(merged), tuple(sorted(links, key=lambda l: l.key))
