"""Project-owned SYNTHETIC fixture, never live Azure DevOps evidence.

BASE is the exact accepted AC326 fixture. Variants are immutable transformations,
not alternate unlabeled provider data. This module performs no I/O or network calls.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from continuity.domain.traceability import (
    ArtifactKind as K, ArtifactReference as Ref, Direction as D, EvidenceBoundary,
    GapReason, LookupEvidence, Observation, Population as P, TraceDiagnostic,
    TraceLink, TraceLinkOrigin as O, TraceLinkType as T, TraceabilityCapability as C,
    TraceabilityEvidenceCollection as Collection, WorkItemEvidence,
    WorkItemState, WorkItemType,
)
from continuity.domain.reviews import CollectionStatus

SYNTHETIC = "SYNTHETIC project-owned ecl-traceability-demo"
STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
REPOSITORY = "demo-system"


def reference(kind: K, identifier: str, context: str = "") -> Ref:
    return Ref(kind, "synthetic", "ecl-traceability-demo",
               "demo-project" if kind == K.WORK_ITEM else REPOSITORY, identifier,
               "" if kind == K.WORK_ITEM else REPOSITORY, context)


def observation(identifier: str, basis: str = "provider_recorded_association") -> Observation:
    return Observation(identifier, "synthetic-base", STAMP, basis)


def base_fixture() -> Collection:
    boundary = EvidenceBoundary("synthetic-base", "synthetic", "ecl-traceability-demo",
                                "demo-project", REPOSITORY, STAMP, "base-v1", "all-fixture-artifacts",
                                "synthetic-alias-v1", "all", "d" * 40)
    wi = tuple(reference(K.WORK_ITEM, str(i)) for i in (1001, 1002, 1003))
    items = tuple(WorkItemEvidence(ref, kind, state, observation(f"wi-{ref.identifier}"), title, True)
                  for ref, kind, state, title in zip(wi,
                      (WorkItemType.STORY, WorkItemType.BUG, WorkItemType.REQUIREMENT),
                      (WorkItemState.ACTIVE, WorkItemState.CLOSED, WorkItemState.OPEN),
                      ("Add payment retry policy", "Fix synthetic catalog timeout", "Add synthetic inventory export")))
    prs = tuple(reference(K.PULL_REQUEST, str(i)) for i in (51, 52, 53, 54))
    commits = tuple(reference(K.COMMIT, char * 40) for char in "abcd")
    paths = tuple(reference(K.CHANGED_PATH, path, commit.identifier) for commit, path in zip(commits,
                  ("src/payments/retry.py", "tests/payments/test_retry.py",
                   "src/catalog/timeout.py", "src/payments/timeout.py")))
    links: list[TraceLink] = []

    def add(source: Ref, target: Ref, kind: T, origin: O = O.DIRECT_PROVIDER_LINK) -> None:
        links.append(TraceLink(source, target, kind, origin,
                              (observation(f"link-{len(links)}", "git_commit_change" if origin == O.DIRECT_SOURCE_LINK
                                           else "provider_recorded_association"),)))

    for a, b in ((0, 0), (0, 3), (1, 0), (1, 2)):
        add(wi[a], prs[b], T.WI_PR)
    add(wi[1], commits[2], T.WI_COMMIT)
    for a, b in ((0, 0), (0, 1), (1, 2), (2, 3)):
        add(prs[a], commits[b], T.PR_COMMIT)
    for commit, path in zip(commits, paths):
        add(commit, path, T.COMMIT_PATH, O.DIRECT_SOURCE_LINK)
    lookups = [LookupEvidence(boundary.identifier, population=p) for p in P]
    legal = {T.WI_PR: (K.WORK_ITEM, K.PULL_REQUEST), T.WI_COMMIT: (K.WORK_ITEM, K.COMMIT),
             T.PR_COMMIT: (K.PULL_REQUEST, K.COMMIT), T.COMMIT_PATH: (K.COMMIT, K.CHANGED_PATH),
             T.PR_PATH: (K.PULL_REQUEST, K.PR_PATH)}
    for ref in wi + prs + commits + paths:
        for kind, (source, target) in legal.items():
            if ref.kind in (source, target):
                lookups.append(LookupEvidence(boundary.identifier, endpoint=ref, relationship=kind,
                                             direction=D.OUTBOUND if ref.kind == source else D.INBOUND))
    return Collection((boundary,), items, prs, prs, commits, paths, tuple(links), tuple(lookups))


@dataclass(frozen=True)
class SyntheticTraceabilityProvider:
    """Repeatable in-memory source with explicitly selected fixture variant."""
    variant: str = "BASE"

    def acquire(self) -> Collection:
        e = base_fixture()
        if self.variant == "BASE":
            return e
        if self.variant == "NO_INTENT":
            return replace(e, links=tuple(l for l in e.links if l.type != T.WI_COMMIT))
        if self.variant == "DIRECT_ONLY":
            return replace(e, links=tuple(l for l in e.links if l.type != T.WI_PR))
        if self.variant == "MULTIPATH":
            path = reference(K.CHANGED_PATH, "src/catalog/additional.py", e.commits[0].identifier)
            link = TraceLink(e.commits[0], path, T.COMMIT_PATH, O.DIRECT_SOURCE_LINK,
                             (observation("multipath", "git_commit_change"),))
            lookup = LookupEvidence("synthetic-base", endpoint=path, relationship=T.COMMIT_PATH, direction=D.INBOUND)
            return replace(e, changed_paths=e.changed_paths + (path,), links=e.links + (link,), lookups=e.lookups + (lookup,))
        if self.variant == "DUPLICATES":
            route = TraceLink(e.pull_requests[2], e.commits[0], T.PR_COMMIT, O.DIRECT_PROVIDER_LINK,
                              (observation("alternate-route"),))
            extra_observation = replace(e.links[0], observations=(observation("second-observation"),))
            return replace(e, links=e.links + e.links + (route, extra_observation))
        if self.variant == "CONFLICT":
            conflict = replace(e.links[0], target=e.pull_requests[1])
            return replace(e, links=e.links + (conflict,))
        if self.variant in ("CYCLE", "MALFORMED", "UNSUPPORTED_TYPE"):
            bad = replace(e.links[0], target=e.links[0].source,
                          type=T.WI_COMPONENT if self.variant == "UNSUPPORTED_TYPE" else T.WI_PR)
            return replace(e, links=e.links + (bad,))
        if self.variant == "OPTIONAL":
            return replace(e, work_items=tuple(replace(w, title=None, title_approved=False,
                               type=WorkItemType.UNKNOWN, state=WorkItemState.OTHER) for w in e.work_items))
        if self.variant in ("PARTIAL", "POSITIVE_PARTIAL", "LATE_FAILURE"):
            lookups = tuple(replace(l, status=CollectionStatus.PARTIAL)
                            if l.endpoint == e.pull_requests[3] and l.relationship == T.PR_COMMIT else l
                            for l in e.lookups)
            return replace(e, status=CollectionStatus.PARTIAL, lookups=lookups)
        if self.variant == "FAILED":
            return replace(e, work_items=(), pull_requests=(), merged_pull_requests=(), commits=(),
                           changed_paths=(), links=(), status=CollectionStatus.FAILED,
                           lookups=tuple(replace(l, status=CollectionStatus.FAILED) for l in e.lookups))
        if self.variant == "CAPABILITY":
            return replace(e, lookups=tuple(replace(l, capability=C.UNSUPPORTED)
                             if l.relationship == T.WI_COMMIT else l for l in e.lookups))
        if self.variant == "EMPTY":
            return replace(e, work_items=(), pull_requests=(), merged_pull_requests=(), commits=(),
                           changed_paths=(), links=(), lookups=tuple(l for l in e.lookups if l.population))
        if self.variant == "LINKED_ONLY":
            return replace(e, lookups=tuple(l for l in e.lookups if l.population != P.WORK_ITEMS))
        if self.variant == "BOUNDARY":
            return replace(e, commits=e.commits[:-1], changed_paths=e.changed_paths[:-1])
        if self.variant == "PR_PATH_ONLY":
            path = reference(K.PR_PATH, "src/payments/snapshot.py", e.pull_requests[3].identifier)
            link = TraceLink(e.pull_requests[3], path, T.PR_PATH, O.DIRECT_PROVIDER_LINK,
                             (observation("pr-snapshot"),))
            return replace(e, links=e.links + (link,))
        if self.variant == "NO_INFERENCE":
            return replace(e, links=tuple(l for l in e.links if l.type not in (T.WI_PR, T.WI_COMMIT)),
                           work_items=tuple(replace(w, title="PR-51 commit a payment retry") for w in e.work_items))
        raise ValueError("unknown synthetic fixture variant")


def isolate_invalid_fixture_record(evidence: Collection, *, endpoint: Ref | None = None,
                                   relationship: T | None = None) -> Collection:
    """Acquisition boundary for rejected required values; never reflect raw input.

A fixture builder calls this after a domain constructor rejects an invalid record.
The original malformed value/exception must not be retained. No untrusted DTO loader
or arbitrary file/network reader is offered by this offline provider.
"""
    return replace(evidence, status=CollectionStatus.PARTIAL,
                   diagnostics=evidence.diagnostics + (TraceDiagnostic(
                       GapReason.INVALID_OBSERVATION, endpoint, relationship),))
