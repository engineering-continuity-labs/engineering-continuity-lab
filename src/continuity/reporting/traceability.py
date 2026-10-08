"""Explicit, canonical JSON boundary for v0.3 traceability reports."""
from collections.abc import Mapping
from datetime import datetime, timezone
import json
import re
from typing import Any, TypeVar

from continuity.analysis.traceability import derive, normalize
from continuity.domain.reviews import CollectionStatus
from continuity.domain.traceability import (
    ArtifactKind,
    ArtifactReference,
    ArtifactTraceResult,
    CoverageMetric,
    Direction,
    EvidenceBoundary,
    GapReason,
    LinkKey,
    LookupEvidence,
    Observation,
    Population,
    TraceDiagnostic,
    TraceGap,
    TraceLink,
    TraceLinkOrigin,
    TraceLinkType,
    TracePath,
    TraceStatus,
    TraceabilityCapability,
    TraceabilityEvidenceCollection,
    TraceabilityReport,
    WorkItemEvidence,
    WorkItemState,
    WorkItemType,
)
from continuity.domain.models import DirectoryComponents


SCHEMA_VERSION = "1.0"
_T = TypeVar("_T")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
_PRIVATE = re.compile(
    r"(?:gh[pousr]_|github_pat_|glpat-|sk-[A-Za-z0-9_-]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
    r"(?:authorization|bearer|password|passwd|cookie|set-cookie|pat|token|secret)[=: ]|"
    r"(?:authorization|bearer|password|cookie|pat|token|secret)_SENTINEL|"
    r"https?://|file://|(?:^|/)(?:Users|home|tmp|private/var|var/tmp)/)", re.IGNORECASE
)


def _public_values(value: Any, depth: int = 0) -> None:
    """Reject recognizable private material; opaque aliases still require source approval."""
    if depth > 100:
        raise ValueError("invalid public traceability value")
    if isinstance(value, str):
        if _PRIVATE.search(value) or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("invalid public traceability value")
    elif isinstance(value, dict):
        for key, item in value.items():
            _public_values(key, depth + 1)
            _public_values(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _public_values(item, depth + 1)


def _object(value: Any, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid traceability object")
    return value


def _enum(enum_type: type[_T], value: Any) -> _T:
    if not isinstance(value, str):
        raise ValueError("invalid traceability enum")
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except ValueError:
        raise ValueError("invalid traceability enum") from None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    result = value.astimezone(timezone.utc).isoformat()
    _required_datetime(result)
    return result


def _datetime(value: Any, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise ValueError("invalid traceability timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid traceability timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("invalid traceability timestamp")
    return parsed


def _required_datetime(value: Any) -> datetime:
    parsed = _datetime(value)
    if parsed is None:
        raise ValueError("invalid traceability timestamp")
    return parsed


def _ref_to_dict(ref: ArtifactReference) -> dict[str, str]:
    return {
        "kind": ref.kind.value,
        "provider": ref.provider,
        "instance": ref.instance,
        "scope": ref.scope,
        "identifier": ref.identifier,
        "repository": ref.repository,
        "context": ref.context,
        "configuration": ref.configuration,
        "algorithm": ref.algorithm,
    }


def _ref_from_dict(value: Any) -> ArtifactReference:
    data = _object(value, {"kind", "provider", "instance", "scope", "identifier", "repository",
                           "context", "configuration", "algorithm"})
    if not all(isinstance(item, str) for item in data.values()):
        raise ValueError("invalid traceability reference")
    ref = ArtifactReference(
        _enum(ArtifactKind, data["kind"]), data["provider"], data["instance"], data["scope"],
        data["identifier"], data["repository"], data["context"], data["configuration"], data["algorithm"],
    )
    if dict(data) != _ref_to_dict(ref):
        raise ValueError("noncanonical traceability reference")
    return ref


def _identity_to_dict(key: LinkKey) -> dict[str, Any]:
    source, target, link_type, origin = key
    return {
        "source": _ref_to_dict_from_key(source),
        "target": _ref_to_dict_from_key(target),
        "type": str(link_type),
        "origin": str(origin),
    }


def _ref_to_dict_from_key(key: tuple[str, ...]) -> dict[str, str]:
    kind = ArtifactKind(key[0])
    if kind in (ArtifactKind.COMMIT, ArtifactKind.CHANGED_PATH, ArtifactKind.COMPONENT):
        _, repository, algorithm, context, configuration, identifier = key
        return _ref_to_dict(ArtifactReference(kind, "source", "offline", "git", identifier,
                                               repository, context, configuration, algorithm))
    _, provider, instance, scope, repository, context, configuration, identifier = key
    return _ref_to_dict(ArtifactReference(kind, provider, instance, scope, identifier,
                                           repository, context, configuration))


def _identity_from_dict(value: Any) -> LinkKey:
    data = _object(value, {"source", "target", "type", "origin"})
    source = _ref_from_dict(data["source"])
    target = _ref_from_dict(data["target"])
    return (source.key, target.key, _enum(TraceLinkType, data["type"]),
            _enum(TraceLinkOrigin, data["origin"]))


def _observation_to_dict(value: Observation) -> dict[str, Any]:
    return {"identifier": value.identifier, "boundary": value.boundary,
            "observed_at": _iso(value.observed_at), "basis": value.basis}


def _observation_from_dict(value: Any) -> Observation:
    data = _object(value, {"identifier", "boundary", "observed_at", "basis"})
    return Observation(data["identifier"], data["boundary"], _required_datetime(data["observed_at"]), data["basis"])


def _boundary_to_dict(value: EvidenceBoundary) -> dict[str, Any]:
    return {
        "identifier": value.identifier, "provider": value.provider, "instance": value.instance,
        "project": value.project, "repository": value.repository,
        "collected_at": _iso(value.collected_at), "snapshot": value.snapshot, "query": value.query,
        "identity_mapping": value.identity_mapping, "filter_policy": value.filter_policy,
        "revision": value.revision, "time_field": value.time_field, "start": _iso(value.start),
        "end": _iso(value.end), "normalization_version": value.normalization_version,
        "join_contract": value.join_contract,
    }


def _boundary_from_dict(value: Any) -> EvidenceBoundary:
    data = _object(value, {"identifier", "provider", "instance", "project", "repository", "collected_at",
                           "snapshot", "query", "identity_mapping", "filter_policy", "revision", "time_field",
                           "start", "end", "normalization_version", "join_contract"})
    return EvidenceBoundary(
        data["identifier"], data["provider"], data["instance"], data["project"], data["repository"],
        _required_datetime(data["collected_at"]), data["snapshot"], data["query"], data["identity_mapping"],
        data["filter_policy"], data["revision"], data["time_field"], _datetime(data["start"], optional=True),
        _datetime(data["end"], optional=True), data["normalization_version"], data["join_contract"],
    )


def _link_to_dict(value: TraceLink) -> dict[str, Any]:
    return {
        "source": _ref_to_dict(value.source), "target": _ref_to_dict(value.target),
        "type": value.type.value, "origin": value.origin.value,
        "observations": [_observation_to_dict(item) for item in value.observations],
        "supports": [_identity_to_dict(item) for item in value.supports],
    }


def _link_from_dict(value: Any) -> TraceLink:
    data = _object(value, {"source", "target", "type", "origin", "observations", "supports"})
    if not isinstance(data["observations"], list) or not isinstance(data["supports"], list):
        raise ValueError("invalid traceability link")
    return TraceLink(_ref_from_dict(data["source"]), _ref_from_dict(data["target"]),
                     _enum(TraceLinkType, data["type"]), _enum(TraceLinkOrigin, data["origin"]),
                     tuple(_observation_from_dict(item) for item in data["observations"]),
                     tuple(_identity_from_dict(item) for item in data["supports"]))


def _gap_to_dict(value: TraceGap) -> dict[str, Any]:
    return {"endpoint": _ref_to_dict(value.endpoint), "relationship": value.relationship.value,
            "direction": value.direction.value, "status": value.status.value, "reason": value.reason.value}


def _gap_from_dict(value: Any) -> TraceGap:
    data = _object(value, {"endpoint", "relationship", "direction", "status", "reason"})
    return TraceGap(_ref_from_dict(data["endpoint"]), _enum(TraceLinkType, data["relationship"]),
                    _enum(Direction, data["direction"]), _enum(TraceStatus, data["status"]),
                    _enum(GapReason, data["reason"]))


def _diagnostic_to_dict(value: TraceDiagnostic) -> dict[str, Any]:
    return {"reason": value.reason.value, "endpoint": _ref_to_dict(value.endpoint) if value.endpoint else None,
            "relationship": value.relationship.value if value.relationship else None}


def _diagnostic_from_dict(value: Any) -> TraceDiagnostic:
    data = _object(value, {"reason", "endpoint", "relationship"})
    return TraceDiagnostic(_enum(GapReason, data["reason"]),
                           _ref_from_dict(data["endpoint"]) if data["endpoint"] is not None else None,
                           _enum(TraceLinkType, data["relationship"])
                           if data["relationship"] is not None else None)


def _collection_to_dict(value: TraceabilityEvidenceCollection) -> dict[str, Any]:
    def refs(values: tuple[ArtifactReference, ...]) -> list[dict[str, str]]:
        result = [_ref_to_dict(item) for item in values]
        result.sort(key=_canonical)
        return result
    work_items = []
    for item in value.work_items:
        work_items.append({
            "reference": _ref_to_dict(item.reference), "type": item.type.value, "state": item.state.value,
            "provenance": _observation_to_dict(item.provenance),
        })
    work_items.sort(key=lambda item: _canonical(item["reference"]))
    populations = {
        "pull_requests": refs(value.pull_requests), "merged_pull_requests": refs(value.merged_pull_requests),
        "commits": refs(value.commits), "changed_paths": refs(value.changed_paths),
    }
    observed_links = [_link_to_dict(item) for item in value.links]
    observed_links.sort(key=_canonical)
    lookups = [{
        "boundary": item.boundary, "capability": item.capability.value, "status": item.status.value,
        "endpoint": _ref_to_dict(item.endpoint) if item.endpoint else None,
        "relationship": item.relationship.value if item.relationship else None,
        "direction": item.direction.value, "population": item.population.value if item.population else None,
    } for item in value.lookups]
    lookups.sort(key=_canonical)
    diagnostics = [_diagnostic_to_dict(item) for item in value.diagnostics]
    diagnostics.sort(key=_canonical)
    boundaries = [_boundary_to_dict(item) for item in value.boundaries]
    boundaries.sort(key=lambda item: item["identifier"])
    return {
        "status": value.status.value,
        "component_strategy": {"name": value.component_strategy, "configuration": value.component_configuration},
        "boundaries": boundaries,
        "work_items": work_items,
        "populations": populations,
        "observed_links": observed_links,
        "lookups": lookups,
        "diagnostics": diagnostics,
    }


def _collection_from_dict(value: Any) -> TraceabilityEvidenceCollection:
    data = _object(value, {"status", "component_strategy", "boundaries", "work_items", "populations",
                           "observed_links", "lookups", "diagnostics"})
    strategy = _object(data["component_strategy"], {"name", "configuration"})
    populations = _object(data["populations"], {"pull_requests", "merged_pull_requests", "commits", "changed_paths"})
    for name in ("boundaries", "work_items", "observed_links", "lookups", "diagnostics"):
        if not isinstance(data[name], list):
            raise ValueError("invalid traceability collection")
    for name in populations:
        if not isinstance(populations[name], list):
            raise ValueError("invalid traceability population")
    items = []
    item_keys = {"reference", "type", "state", "provenance"}
    for item_value in data["work_items"]:
        item = _object(item_value, item_keys)
        items.append(WorkItemEvidence(
            _ref_from_dict(item["reference"]), _enum(WorkItemType, item["type"]),
            _enum(WorkItemState, item["state"]), _observation_from_dict(item["provenance"]),
        ))
    lookups = []
    lookup_keys = {"boundary", "capability", "status", "endpoint", "relationship", "direction", "population"}
    for lookup_value in data["lookups"]:
        lookup = _object(lookup_value, lookup_keys)
        lookups.append(LookupEvidence(
            lookup["boundary"], _enum(TraceabilityCapability, lookup["capability"]),
            _enum(CollectionStatus, lookup["status"]),
            _ref_from_dict(lookup["endpoint"]) if lookup["endpoint"] is not None else None,
            _enum(TraceLinkType, lookup["relationship"]) if lookup["relationship"] is not None else None,
            _enum(Direction, lookup["direction"]),
            _enum(Population, lookup["population"]) if lookup["population"] is not None else None,
        ))
    evidence = TraceabilityEvidenceCollection(
        tuple(_boundary_from_dict(item) for item in data["boundaries"]), tuple(items),
        tuple(_ref_from_dict(item) for item in populations["pull_requests"]),
        tuple(_ref_from_dict(item) for item in populations["merged_pull_requests"]),
        tuple(_ref_from_dict(item) for item in populations["commits"]),
        tuple(_ref_from_dict(item) for item in populations["changed_paths"]),
        tuple(_link_from_dict(item) for item in data["observed_links"]), tuple(lookups),
        _enum(CollectionStatus, data["status"]),
        tuple(_diagnostic_from_dict(item) for item in data["diagnostics"]),
        strategy["name"], strategy["configuration"],
    )
    boundary_ids = {boundary.identifier for boundary in evidence.boundaries}
    if any(lookup.boundary not in boundary_ids for lookup in evidence.lookups):
        raise ValueError("unresolved lookup boundary")
    grammar = {
        TraceLinkType.WI_PR: ((ArtifactKind.WORK_ITEM,), ArtifactKind.PULL_REQUEST),
        TraceLinkType.WI_COMMIT: ((ArtifactKind.WORK_ITEM,), ArtifactKind.COMMIT),
        TraceLinkType.PR_COMMIT: ((ArtifactKind.PULL_REQUEST,), ArtifactKind.COMMIT),
        TraceLinkType.COMMIT_PATH: ((ArtifactKind.COMMIT,), ArtifactKind.CHANGED_PATH),
        TraceLinkType.PR_PATH: ((ArtifactKind.PULL_REQUEST,), ArtifactKind.PR_PATH),
        TraceLinkType.PATH_COMPONENT: ((ArtifactKind.CHANGED_PATH, ArtifactKind.PR_PATH), ArtifactKind.COMPONENT),
        TraceLinkType.WI_COMPONENT: ((ArtifactKind.WORK_ITEM,), ArtifactKind.COMPONENT),
    }
    for parsed_lookup in evidence.lookups:
        if parsed_lookup.endpoint is not None and parsed_lookup.relationship is not None:
            sources, target = grammar[parsed_lookup.relationship]
            if (parsed_lookup.endpoint.kind not in sources if parsed_lookup.direction == Direction.OUTBOUND
                    else parsed_lookup.endpoint.kind != target):
                raise ValueError("invalid lookup endpoint kind")
    # Compare the submitted wire collection, not a pre-sorted reserialization.
    # Timestamp spellings may differ within the supported ISO grammar.
    if not _strict_equal(_timestamp_spellings(data), _collection_to_dict(evidence)):
        raise ValueError("noncanonical traceability collection")
    return evidence


def _timestamp_spellings(item: Any) -> Any:
    if isinstance(item, dict):
        return {key: _iso(_datetime(child, optional=True))
                if key in {"collected_at", "observed_at", "start", "end"}
                else _timestamp_spellings(child) for key, child in item.items()}
    if isinstance(item, list):
        return [_timestamp_spellings(child) for child in item]
    return item


def trace_path_to_dict(item: TracePath) -> dict[str, Any]:
    """Serialize one exact path using the existing public traceability allowlist."""
    return {
        "nodes": [_ref_to_dict(node) for node in item.nodes],
        "supports": [_identity_to_dict(support) for support in item.supports],
        "boundaries": sorted(item.boundaries), "status": item.status.value,
        "gaps": sorted((_gap_to_dict(gap) for gap in item.gaps), key=_canonical),
        "rule_version": item.rule_version,
    }


def _result_to_dict(value: TraceabilityReport) -> dict[str, Any]:
    direct = [_link_to_dict(item) for item in value.direct_links]
    derived = [_link_to_dict(item) for item in value.derived_links]
    direct.sort(key=_canonical)
    derived.sort(key=_canonical)
    paths = [trace_path_to_dict(item) for item in value.paths]
    paths.sort(key=_canonical)
    gaps = [_gap_to_dict(item) for item in value.gaps]
    gaps.sort(key=_canonical)
    artifacts = [{"artifact": _ref_to_dict(item.artifact), "status": item.status.value} for item in value.artifacts]
    artifacts.sort(key=lambda item: _canonical(item["artifact"]))
    metrics = [{
        "dimension": item.dimension, "numerator": item.numerator, "denominator": item.denominator,
        "value": item.value, "status": item.status.value, "collection_status": item.collection_status.value,
        "boundaries": sorted(item.boundaries), "sources": sorted(item.sources),
        "unknown_count": item.unknown_count, "excluded_count": item.excluded_count,
        "reason": item.reason.value if item.reason else None,
        "component": _ref_to_dict(item.component) if item.component else None,
    } for item in value.metrics]
    metrics.sort(key=_canonical)
    diagnostics = [_diagnostic_to_dict(item) for item in value.diagnostics]
    diagnostics.sort(key=_canonical)
    return {"derivation_version": value.derivation_version, "summary": value.summary.value,
            "direct_links": direct, "derived_links": derived, "paths": paths, "gaps": gaps,
            "artifacts": artifacts, "metrics": metrics, "diagnostics": diagnostics}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _strict_equal(left: Any, right: Any, field: str | None = None) -> bool:
    if type(left) is not type(right):
        if field == "value" and type(left) in (int, float) and type(right) in (int, float):
            return float(left) == float(right)
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_strict_equal(left[key], right[key], key) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _strategy(evidence: TraceabilityEvidenceCollection) -> DirectoryComponents:
    match = re.fullmatch(r"depth-([1-9][0-9]*)", evidence.component_configuration)
    if evidence.component_strategy != "directory" or match is None:
        raise ValueError("unsupported traceability component strategy")
    return DirectoryComponents(depth=int(match.group(1)))


def traceability_to_dict(report: TraceabilityReport) -> dict[str, Any]:
    """Serialize an already-derived result through the v1 traceability contract."""
    normalized = normalize(report.evidence)
    if not _strict_equal(_collection_to_dict(report.evidence), _collection_to_dict(normalized)):
        raise ValueError("traceability collection is not normalized")
    strategy = _strategy(normalized)
    recomputed = derive(normalized, strategy)
    result = _result_to_dict(report)
    if not _strict_equal(result, _result_to_dict(recomputed)):
        raise ValueError("traceability result does not match its evidence")
    section = {"schema_version": SCHEMA_VERSION, "collection": _collection_to_dict(normalized),
               "result": result}
    # Export must pass the same wire checks as import, including boundary ownership.
    _public_values(section)
    _collection_from_dict(section["collection"])
    return section


def traceability_from_dict(value: Any) -> TraceabilityReport:
    """Validate and reconstruct a traceability report from its explicit JSON contract."""
    try:
        _public_values(value)
        section = _object(value, {"schema_version", "collection", "result"})
        if section["schema_version"] != SCHEMA_VERSION:
            raise ValueError("unsupported traceability schema")
        evidence = _collection_from_dict(section["collection"])
        normalized = normalize(evidence)
        if not _strict_equal(_collection_to_dict(evidence), _collection_to_dict(normalized)):
            raise ValueError("traceability collection is not normalized")
        report = derive(normalized, _strategy(normalized))
        expected = _result_to_dict(report)
        if not _strict_equal(_timestamp_spellings(section["result"]), expected):
            raise ValueError("traceability result contradicts its evidence")
        return report
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("invalid traceability report") from None


def traceability_to_json(report: TraceabilityReport) -> str:
    """Return deterministic compact JSON for a derived traceability report."""
    return _canonical(traceability_to_dict(report))


def traceability_from_json(value: str) -> TraceabilityReport:
    """Parse and validate deterministic traceability JSON without reflecting input."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = item
        return result
    try:
        parsed = json.loads(value, object_pairs_hook=unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (json.JSONDecodeError, TypeError, ValueError, RecursionError):
        raise ValueError("invalid traceability JSON") from None
    return traceability_from_dict(parsed)


def validate_report_envelope(value: Any) -> dict[str, Any]:
    """Validate version ownership and any additive traceability section."""
    if not isinstance(value, dict) or value.get("model") not in ("experimental-v0.1", "experimental-v0.2"):
        raise ValueError("invalid continuity report envelope")
    if (not isinstance(value.get("components"), list) or not isinstance(value.get("revision"), str)
            or not isinstance(value.get("as_of"), str) or not isinstance(value.get("commit_count"), int)
            or isinstance(value.get("commit_count"), bool) or value["commit_count"] < 0):
        raise ValueError("invalid continuity report envelope")
    try:
        datetime.fromisoformat(value["as_of"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("invalid continuity report envelope") from None
    version = value.get("report_version")
    if "report_version" in value and version not in ("1.0", "2.0", "3.0"):
        raise ValueError("unsupported report version")
    if version == "3.0" and value["model"] != "experimental-v0.1":
        raise ValueError("report version 3.0 requires the experimental-v0.1 model")
    if "review_evidence" in value and version not in ("2.0", "3.0"):
        raise ValueError("review evidence requires report version 2.0 or 3.0")
    if "traceability_evidence" in value:
        if version != "3.0" or value["model"] != "experimental-v0.1":
            raise ValueError("traceability evidence requires report version 3.0")
        traceability_from_dict(value["traceability_evidence"])
    return value


def with_traceability(value: Mapping[str, Any], report: TraceabilityReport) -> dict[str, Any]:
    """Return a v3 copy of an existing Git report without changing owned fields."""
    if value.get("model") != "experimental-v0.1":
        raise ValueError("traceability requires the experimental-v0.1 Git report")
    result = dict(value)
    result["report_version"] = "3.0"
    result["traceability_evidence"] = traceability_to_dict(report)
    return validate_report_envelope(result)
