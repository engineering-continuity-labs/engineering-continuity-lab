"""Read-only Azure acquisition; all path/gap/coverage derivation stays offline."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Callable

from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import (
    ArtifactKind as K, ArtifactReference as Ref, Direction as D, EvidenceBoundary,
    GapReason as G, LookupEvidence, Observation, Population as P, TraceDiagnostic,
    TraceLink, TraceLinkOrigin as O, TraceLinkType as T, TraceabilityCapability as C,
    TraceabilityEvidenceCollection as Collection, WorkItemEvidence,
    WorkItemState as WS, WorkItemType as WT, aware,
)
from continuity.traceability_providers import azure_dto as dto
from continuity.traceability_providers.azure_profile import (
    AzureApiProfile, AzureDevOpsDeployment, AzureDevOpsProfile, AzureIdentityMap,
    AzureLimits, native_id, public_alias,
)
from continuity.traceability_providers.azure_transport import (
    AzureHttpTransport, AzureResponse, AzureTransport, AzureTransportError,
)

__all__ = ["AzureApiProfile", "AzureDevOpsDeployment", "AzureDevOpsProfile", "AzureIdentityMap",
           "AzureLimits", "AzureHttpTransport", "AzureDevOpsTraceabilityProvider"]


@dataclass(frozen=True)
class _State:
    status: S = S.COMPLETE
    capability: C = C.SUPPORTED


def _combine(states: list[_State]) -> _State:
    capability = C.UNSUPPORTED if any(s.capability == C.UNSUPPORTED for s in states) else (
        C.UNKNOWN if any(s.capability == C.UNKNOWN for s in states) else C.SUPPORTED)
    status = S.COMPLETE if all(s.status == S.COMPLETE for s in states) else (
        S.FAILED if states and all(s.status == S.FAILED for s in states) else S.PARTIAL)
    return _State(status, capability)


@dataclass(repr=False)
class _Scan:
    records: list[object] = field(default_factory=list)
    state: _State = field(default_factory=_State)

    def invalid(self) -> None:
        self.state = _State(S.PARTIAL, self.state.capability)


@dataclass(frozen=True, repr=False)
class AzureDevOpsTraceabilityProvider:
    profile: AzureDevOpsProfile
    identities: AzureIdentityMap
    collected_at: datetime
    snapshot: str
    transport: AzureTransport | None = None

    def __post_init__(self) -> None:
        aware(self.collected_at)
        public_alias(self.snapshot)
        if isinstance(self.transport, AzureHttpTransport) and self.transport.profile != self.profile:
            raise ValueError("Azure transport profile mismatch")

    def acquire(self) -> Collection:
        return _Acquisition(self).run()


class _Acquisition:
    def __init__(self, provider: AzureDevOpsTraceabilityProvider) -> None:
        self.p = provider.profile
        self.ids = provider.identities
        self.at = provider.collected_at.astimezone(timezone.utc)
        self.iso = self.at.isoformat(timespec="microseconds").replace("+00:00", "Z")
        self.transport = provider.transport if provider.transport is not None else AzureHttpTransport(self.p)
        self.repo = ("git", "repositories", self.p.repository)
        self.boundary = EvidenceBoundary("azure-acquisition", "azure-devops", self.p.instance_alias,
            self.p.project_alias, self.p.repository_alias, self.at, provider.snapshot,
            "completed-pr-project-wi-revision-ancestry", self.ids.fingerprint,
            "completed-closed-at-asof", self.p.revision, normalization_version="azure-rest-1")
        self.links: dict[object, TraceLink] = {}
        self.diagnostics: list[TraceDiagnostic] = []
        self.requests = 0

    def _request(self, endpoint: tuple[str, ...], query: dict[str, str],
                 body: dict[str, str] | None = None) -> AzureResponse:
        self.requests += 1
        if self.requests > self.p.limits.max_requests:
            raise AzureTransportError("response_limit")
        return self.transport.request(endpoint, query, body)

    def _scan(self, endpoint: tuple[str, ...], query: dict[str, str], *,
              member: str = "value", continuation: bool = False,
              change_paging: bool = False) -> _Scan:
        scan = _Scan()
        token: str | None = None
        tokens: set[str] = set()
        for page in range(self.p.limits.max_pages):
            params = dict(query)
            params["top" if change_paging else "$top"] = str(self.p.limits.page_size)
            if continuation:
                if token is not None:
                    params["continuationToken"] = token
            else:
                params["skip" if change_paging else "$skip"] = str(page * self.p.limits.page_size)
            try:
                response = self._request(endpoint, params)
                values = dto.array(dto.obj(response.payload).get(member))
                room = self.p.limits.max_items - len(scan.records)
                scan.records.extend(values[:min(room, self.p.limits.page_size)])
                if len(values) > min(room, self.p.limits.page_size):
                    scan.invalid()
                    break
                if continuation:
                    token = response.continuation
                    if token is None:
                        # A full page without a token cannot establish exhaustion.
                        if len(values) == self.p.limits.page_size:
                            scan.invalid()
                        break
                    if (not isinstance(token, str) or not token or len(token) > 2048
                            or any(ord(c) < 32 or ord(c) == 127 for c in token) or token in tokens):
                        scan.invalid()
                        break
                    tokens.add(token)
                elif len(values) < self.p.limits.page_size:
                    break
                if len(scan.records) >= self.p.limits.max_items:
                    scan.invalid()
                    break
            except AzureTransportError as error:
                scan.state = _State(S.PARTIAL if scan.records else S.FAILED,
                                    C.UNSUPPORTED if error.unsupported else C.SUPPORTED if scan.records else C.UNKNOWN)
                break
            except (ValueError, TypeError, OverflowError):
                scan.invalid()
                break
        else:
            scan.invalid()
        return scan

    def _one(self, endpoint: tuple[str, ...], query: dict[str, str],
             parse: Callable[[object], list[object]]) -> _Scan:
        try:
            records = parse(self._request(endpoint, query).payload)
            result = _Scan(records[:self.p.limits.max_items])
            if len(records) > self.p.limits.max_items:
                result.invalid()
            return result
        except AzureTransportError as error:
            return _Scan(state=_State(S.FAILED, C.UNSUPPORTED if error.unsupported else C.UNKNOWN))
        except (ValueError, TypeError, OverflowError):
            return _Scan(state=_State(S.PARTIAL))

    def _wi_ids(self) -> _Scan:
        scan = _Scan()
        cursor = 0
        for _ in range(self.p.limits.max_pages):
            query = ("SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
                     f"AND [System.Id] > {cursor} ORDER BY [System.Id] ASC ASOF '{self.iso}'")
            try:
                response = self._request(("wit", "wiql"), {"$top": str(self.p.limits.page_size), "timePrecision": "true"}, {"query": query})
                root = dto.obj(response.payload)
                if root.get("queryType") != "flat" or dto.timestamp(root.get("asOf")) != self.at:
                    raise ValueError("invalid Azure query snapshot")
                values = dto.array(root.get("workItems"))
                valid_ids: set[int] = set()
                invalid_page = False
                for raw_ref in values:
                    try:
                        identifier = dto.reference_id(raw_ref)
                        if identifier <= cursor:
                            raise ValueError("invalid Azure query progress")
                        valid_ids.add(identifier)
                    except (ValueError, TypeError, OverflowError):
                        invalid_page = True
                page_ids = sorted(valid_ids)
                room = self.p.limits.max_items - len(scan.records)
                scan.records.extend(page_ids[:min(room, self.p.limits.page_size)])
                if invalid_page or len(values) > self.p.limits.page_size or len(page_ids) > room:
                    scan.invalid()
                    # Valid positives survive, but a rejected page cannot supply a safe next cursor.
                    break
                if len(values) < self.p.limits.page_size:
                    break
                if not page_ids or len(scan.records) >= self.p.limits.max_items:
                    scan.invalid()
                    break
                cursor = page_ids[-1]
            except AzureTransportError as error:
                scan.state = _State(S.PARTIAL if scan.records else S.FAILED,
                                    C.UNSUPPORTED if error.unsupported else C.SUPPORTED if scan.records else C.UNKNOWN)
                break
            except (ValueError, TypeError, OverflowError):
                scan.invalid()
                break
        else:
            scan.invalid()
        return scan

    def _ref(self, kind: K, identifier: str, context: str = "") -> Ref:
        return Ref(kind, "azure-devops", self.p.instance_alias,
                   self.p.project_alias if kind == K.WORK_ITEM else self.p.repository_alias,
                   identifier, "" if kind == K.WORK_ITEM else self.p.repository_alias, context)

    def _wi(self, identifier: int) -> Ref:
        return self._ref(K.WORK_ITEM, self.ids.alias(identifier, work_item=True))

    def _pr(self, identifier: int) -> Ref:
        return self._ref(K.PULL_REQUEST, self.ids.alias(identifier, work_item=False))

    def _observation(self, identity: str) -> Observation:
        return Observation("az-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
                           self.boundary.identifier, self.at, "provider_recorded_association")

    def _add(self, source: Ref, target: Ref, kind: T) -> None:
        link = TraceLink(source, target, kind, O.DIRECT_PROVIDER_LINK,
                         (self._observation(repr((source.key, target.key, kind))),))
        self.links[link.key] = link

    def _bad(self, endpoint: Ref | None = None, relationship: T | None = None) -> None:
        self.diagnostics.append(TraceDiagnostic(G.INVALID_OBSERVATION, endpoint, relationship))

    def run(self) -> Collection:
        pr_scan = self._scan(self.repo + ("pullrequests",), {
            "searchCriteria.status": "completed", "searchCriteria.maxTime": self.iso,
            "searchCriteria.queryTimeRangeType": "Closed"})
        prs: dict[int, Ref] = {}
        for raw in pr_scan.records:
            try:
                pr = dto.pull_request(raw, self.p.project, self.p.repository, read_refs=False)
                if not pr.completed:
                    continue
                if pr.closed_at is None or pr.closed_at > self.at:
                    raise ValueError("invalid Azure PR boundary")
                prs[pr.identifier] = self._pr(pr.identifier)
            except (ValueError, TypeError, OverflowError):
                pr_scan.invalid()
                self._bad()

        commit_scan = self._scan(self.repo + ("commits",), {
            "searchCriteria.itemVersion.version": self.p.revision,
            "searchCriteria.itemVersion.versionType": "commit",
            "searchCriteria.includeWorkItems": "false", "searchCriteria.includePushData": "false"})
        commits: dict[str, Ref] = {}
        for raw in commit_scan.records:
            try:
                commit_key = dto.commit_id(dto.obj(raw).get("commitId"))
                commits[commit_key] = self._ref(K.COMMIT, commit_key)
            except (ValueError, TypeError):
                commit_scan.invalid()
                self._bad()

        wi_scan = self._wi_ids()
        items: dict[int, WorkItemEvidence] = {}
        wi_labels: dict[int, tuple[str, str]] = {}
        conflicted_ids: set[int] = set()
        wi_states: dict[int, _State] = {}
        wi_ids = sorted(set(native_id(i) for i in wi_scan.records))
        for offset in range(0, len(wi_ids), self.p.limits.work_item_batch):
            batch = wi_ids[offset:offset + self.p.limits.work_item_batch]
            params = {"ids": ",".join(str(i) for i in batch), "asOf": self.iso,
                      "fields": "System.Id,System.WorkItemType,System.State", "errorPolicy": "Fail"}
            if self.p.include_artifact_relations:
                params["$expand"] = "Relations"
            result = self._one(("wit", "workitems"), params, lambda v: dto.array(dto.obj(v).get("value")))
            found: set[int] = set()
            for raw in result.records:
                try:
                    record = dto.obj(raw)
                    wi_key = native_id(record.get("id"))
                    if wi_key not in batch:
                        raise ValueError("invalid Azure work item boundary")
                    ref = self._wi(wi_key)
                    fields = dto.obj(record.get("fields"))
                    if "System.Id" in fields and native_id(fields["System.Id"]) != wi_key:
                        raise ValueError("invalid Azure work item identity")
                    work_type, wi_state = dto.text(fields.get("System.WorkItemType")), dto.text(fields.get("System.State"))
                    item = WorkItemEvidence(ref,
                        {"User Story": WT.STORY, "Product Backlog Item": WT.STORY, "Requirement": WT.REQUIREMENT,
                         "Bug": WT.BUG, "Task": WT.TASK}.get(work_type, WT.OTHER),
                        {"New": WS.OPEN, "To Do": WS.OPEN, "Open": WS.OPEN, "Active": WS.ACTIVE,
                         "Doing": WS.ACTIVE, "Resolved": WS.ACTIVE, "Closed": WS.CLOSED, "Done": WS.CLOSED}.get(wi_state, WS.OTHER),
                        self._observation("wi-" + ref.identifier))
                    labels = (work_type, wi_state)
                    if wi_key in conflicted_ids or wi_labels.get(wi_key, labels) != labels:
                        conflicted_ids.add(wi_key)
                        items.pop(wi_key, None)
                        # Associations from conflicting DTOs are quarantined. Independent PR
                        # references acquired later remain explicit but unresolved by the core.
                        self.links = {key: link for key, link in self.links.items() if link.source != ref}
                        found.add(wi_key)
                        wi_states[wi_key] = _State(S.PARTIAL)
                        result.invalid()
                        self.diagnostics.append(TraceDiagnostic(G.CONFLICTING_OBSERVATION, ref))
                        continue
                    wi_labels[wi_key] = labels
                    items[wi_key] = item
                    found.add(wi_key)
                    relation_state = _State() if self.p.include_artifact_relations else _State(capability=C.UNSUPPORTED)
                    wi_states.setdefault(wi_key, relation_state)
                    if self.p.include_artifact_relations:
                        relations = dto.array(record.get("relations", []))
                        if len(relations) > self.p.limits.max_relations:
                            relation_state = _State(S.PARTIAL)
                        for relation in relations[:self.p.limits.max_relations]:
                            try:
                                r = dto.obj(relation)
                                if r.get("rel") != "ArtifactLink":
                                    continue
                                uri = dto.text(r.get("url"))
                                # Other artifact systems are outside this provider's Git contract.
                                if not uri.startswith("vstfs:///"):
                                    raise ValueError("invalid Azure artifact")
                                if not uri.lower().startswith("vstfs:///git"):
                                    continue
                                family, artifact_target = dto.artifact(uri, self.p.project, self.p.repository)
                                self._add(ref, self._ref(K.COMMIT, artifact_target) if family == "Commit" else self._pr(int(artifact_target)),
                                          T.WI_COMMIT if family == "Commit" else T.WI_PR)
                            except (ValueError, TypeError, OverflowError):
                                relation_state = _State(S.PARTIAL)
                                self._bad(ref, T.WI_COMMIT)
                                self._bad(ref, T.WI_PR)
                    wi_states[wi_key] = _combine([wi_states.get(wi_key, relation_state), relation_state])
                except (ValueError, TypeError, OverflowError):
                    result.invalid()
                    self._bad()
            if found != set(batch):
                result.invalid()
            wi_scan.state = _combine([wi_scan.state, result.state])
            for wi_key in found:
                wi_states[wi_key] = _combine([wi_states[wi_key], result.state])

        pr_wi: dict[int, _State] = {}
        pr_commits: dict[int, _State] = {}
        for pr_key, ref in sorted(prs.items()):
            endpoint = self.repo + ("pullrequests", str(pr_key))
            detail = self._one(endpoint, {}, lambda v: [v])
            refs: tuple[int, ...] | None = None
            for raw in detail.records:
                try:
                    pr = dto.pull_request(raw, self.p.project, self.p.repository)
                    if pr.identifier != pr_key or not pr.completed or pr.closed_at is None or pr.closed_at > self.at:
                        raise ValueError("invalid Azure PR detail")
                    if pr.work_item_refs is not None:
                        parsed_refs: list[int] = []
                        if len(pr.work_item_refs) > self.p.limits.max_relations:
                            detail.invalid()
                            self._bad(ref, T.WI_PR)
                        for raw_ref in pr.work_item_refs[:self.p.limits.max_relations]:
                            try:
                                parsed_refs.append(dto.reference_id(raw_ref))
                            except (ValueError, TypeError, OverflowError):
                                detail.invalid()
                                self._bad(ref, T.WI_PR)
                        refs = tuple(parsed_refs)
                except (ValueError, TypeError, OverflowError):
                    detail.invalid()
                    self._bad(ref, T.WI_PR)
            if refs is None and detail.state.status == S.COMPLETE:
                detail = self._one(endpoint + ("workitems",), {}, lambda v: dto.array(dto.obj(v).get("value")))
                native_refs: list[int] = []
                if len(detail.records) > self.p.limits.max_relations:
                    detail.invalid()
                    self._bad(ref, T.WI_PR)
                for raw in detail.records[:self.p.limits.max_relations]:
                    try:
                        native_refs.append(dto.reference_id(raw))
                    except (ValueError, TypeError, OverflowError):
                        detail.invalid()
                        self._bad(ref, T.WI_PR)
                refs = tuple(native_refs)
            for wi in sorted(set(refs or ())):
                try:
                    self._add(self._wi(wi), ref, T.WI_PR)
                except (ValueError, TypeError, OverflowError):
                    detail.invalid()
                    self._bad(ref, T.WI_PR)
            pr_wi[pr_key] = detail.state
            members = self._scan(endpoint + ("commits",), {}, continuation=True)
            for raw in members.records:
                try:
                    member_ref = self._ref(K.COMMIT, dto.commit_id(dto.obj(raw).get("commitId")))
                    self._add(ref, member_ref, T.PR_COMMIT)
                except (ValueError, TypeError):
                    members.invalid()
                    self._bad(ref, T.PR_COMMIT)
            pr_commits[pr_key] = members.state

        paths: dict[Ref, _State] = {}
        change_states: dict[str, _State] = {}
        for change_key, ref in sorted(commits.items()):
            if not self.p.include_changes:
                change_states[change_key] = _State(capability=C.UNSUPPORTED)
                continue
            changes = self._scan(self.repo + ("commits", change_key, "changes"), {}, member="changes", change_paging=True)
            local_paths: set[Ref] = set()
            for raw in changes.records:
                try:
                    path = dto.changed_path(raw)
                    if path is not None:
                        path_target = self._ref(K.CHANGED_PATH, path, change_key)
                        self._add(ref, path_target, T.COMMIT_PATH)
                        local_paths.add(path_target)
                except (ValueError, TypeError):
                    changes.invalid()
                    self._bad(ref, T.COMMIT_PATH)
            change_states[change_key] = changes.state
            for path_ref in local_paths:
                paths[path_ref] = changes.state

        all_wi = _combine([wi_scan.state] + list(wi_states.values()))
        if not self.p.include_artifact_relations:
            all_wi = _State(all_wi.status, C.UNSUPPORTED)
        wi_pr_states = {i: s if self.p.include_artifact_relations else _State(s.status)
                        for i, s in wi_states.items()}
        all_wi_pr = _combine([wi_scan.state] + list(wi_pr_states.values()))
        all_pr_wi = _combine([pr_scan.state] + list(pr_wi.values()))
        all_members = _combine([pr_scan.state] + list(pr_commits.values()))
        all_changes = _combine([commit_scan.state] + list(change_states.values())) if self.p.include_changes else _State(capability=C.UNSUPPORTED)
        all_states = [pr_scan.state, commit_scan.state, wi_scan.state, all_wi, all_pr_wi, all_members, all_changes]
        lookups: list[LookupEvidence] = []

        def lookup(state: _State, *, population: P | None = None, endpoint: Ref | None = None,
                   relationship: T | None = None, direction: D = D.OUTBOUND) -> None:
            lookups.append(LookupEvidence(self.boundary.identifier, state.capability, state.status,
                                         endpoint, relationship, direction, population))
            # A global diagnostic would taint unrelated lookups during core normalization.
            # FAILED/unsupported/unknown already carry sanitized categories in the lookup.
            if state.status == S.PARTIAL and state.capability == C.SUPPORTED and endpoint is not None:
                self.diagnostics.append(TraceDiagnostic(G.INCOMPLETE_LOOKUP, endpoint, relationship))

        for population, state in ((P.PULL_REQUESTS, pr_scan.state), (P.WORK_ITEMS, wi_scan.state),
                                  (P.COMMITS, commit_scan.state), (P.CHANGES, all_changes)):
            lookup(state, population=population)
        for identifier, item in sorted(items.items()):
            lookup(_combine([all_pr_wi, wi_pr_states[identifier]]), endpoint=item.reference, relationship=T.WI_PR)
            lookup(wi_states[identifier], endpoint=item.reference, relationship=T.WI_COMMIT)
        for identifier, ref in sorted(prs.items()):
            lookup(_combine([pr_wi[identifier], all_wi_pr]), endpoint=ref, relationship=T.WI_PR, direction=D.INBOUND)
            lookup(pr_commits[identifier], endpoint=ref, relationship=T.PR_COMMIT)
        for commit_lookup_key, ref in sorted(commits.items()):
            lookup(all_wi, endpoint=ref, relationship=T.WI_COMMIT, direction=D.INBOUND)
            lookup(all_members, endpoint=ref, relationship=T.PR_COMMIT, direction=D.INBOUND)
            lookup(change_states[commit_lookup_key], endpoint=ref, relationship=T.COMMIT_PATH)
        for ref, state in sorted(paths.items(), key=lambda p: p[0].key):
            lookup(state, endpoint=ref, relationship=T.COMMIT_PATH, direction=D.INBOUND)

        any_evidence = bool(items or prs or commits or paths or self.links)
        if self.requests > self.p.limits.max_requests:
            if items:
                self.diagnostics.append(TraceDiagnostic(G.INCOMPLETE_LOOKUP, next(iter(items.values())).reference, T.WI_PR))
            elif prs:
                self.diagnostics.append(TraceDiagnostic(G.INCOMPLETE_LOOKUP, next(iter(prs.values())), T.PR_COMMIT))
            elif commits:
                self.diagnostics.append(TraceDiagnostic(G.INCOMPLETE_LOOKUP, next(iter(commits.values())), T.COMMIT_PATH))
        status = S.COMPLETE if all(s.status == S.COMPLETE for s in all_states) else S.PARTIAL if any_evidence else S.FAILED
        # Existing normalization is a domain operation, not Azure-specific derivation.
        from continuity.analysis.traceability import normalize
        return normalize(Collection((self.boundary,), tuple(items.values()), tuple(prs.values()), tuple(prs.values()),
                                    tuple(commits.values()), tuple(paths), tuple(self.links.values()), tuple(lookups),
                                    status, tuple(self.diagnostics)))
