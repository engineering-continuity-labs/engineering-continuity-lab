"""Deliberate v4 public boundary, strict JSON and offline manifest parsing."""
from dataclasses import fields
from datetime import datetime, timezone
import json
import math
from typing import Any
import tomllib
from continuity.reporting.portable_public import validate_public

from continuity.analysis.verification import Report, derive
from continuity.domain.verification import (Reference, Kind, Snapshot, Association, Relation, Run, Outcome,
                                            Lookup, Limits, Collection)
from continuity.domain.traceability import (ArtifactReference, ArtifactKind, Direction, TraceabilityCapability,
                                            TraceLinkOrigin, TraceabilityReport)
from continuity.domain.reviews import CollectionStatus
from continuity.reporting.traceability import traceability_from_dict, traceability_to_dict, validate_report_envelope
from continuity.reporting.verification import reference, snapshot, association, to_dict

MAX_BYTES = 8 * 1024 * 1024
COLLECTION_KEYS = {'artifacts','associations','runs','lookups','snapshot','boundary','collected_at','status','limits'}
RESULT_KEYS = {'rule_version','snapshot_valid','requirements','paths','runs','metrics','outcomes','gaps','diagnostics','dropped','associations','collection_status'}
ENVELOPE_KEYS = {'model','report_version','warning','configuration','filters','filter_evidence','revision','as_of',
                 'shallow','commit_count','components','source','review_evidence','review_evidence_error',
                 'traceability_evidence','verification_evidence'}


def exact(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('invalid evidence schema')
    return value


def safe_json(value: Any, depth: int = 0) -> None:
    if depth > 64:
        raise ValueError('invalid evidence JSON')
    if isinstance(value, str):
        value.encode('utf-8', errors='strict')
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('invalid evidence JSON')
    elif isinstance(value, dict):
        for key, item in value.items():
            safe_json(key, depth + 1)
            safe_json(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            safe_json(item, depth + 1)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def loads(value: str | bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ValueError('invalid evidence JSON')
            result[key] = item
        return result
    try:
        raw = value.encode('utf-8') if isinstance(value, str) else value
        if len(raw) > MAX_BYTES:
            raise ValueError('invalid evidence JSON')
        parsed = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        safe_json(parsed)
        return parsed
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('invalid evidence JSON') from None


def instant(value: Any) -> datetime:
    import re
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])', value):
        raise ValueError('invalid evidence timestamp')
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:
        raise ValueError('invalid evidence timestamp')
    return result.astimezone(timezone.utc)


def ref_from(value: Any) -> Reference | ArtifactReference:
    if isinstance(value, dict) and value.get('kind') in [k.value for k in Kind]:
        data = exact(value, {'kind','instance','scope','identifier','version','document_kind'})
        return Reference(Kind(data['kind']),data['instance'],data['scope'],data['identifier'],data['version'],data['document_kind'])
    data = exact(value, {f.name for f in fields(ArtifactReference)})
    return ArtifactReference(ArtifactKind(data['kind']),data['provider'],data['instance'],data['scope'],data['identifier'],
                             data['repository'],data['context'],data['configuration'],data['algorithm'])


def new_ref(value: Any) -> Reference:
    result = ref_from(value)
    if not isinstance(result, Reference):
        raise ValueError('invalid evidence reference')
    return result


def snapshot_from(value: Any) -> Snapshot:
    data = exact(value, {'alias','repository','revision','fingerprint'})
    return Snapshot(**data)


def collection_from(value: Any, code: TraceabilityReport) -> Collection:
    data = exact(value, COLLECTION_KEYS)
    for key, maximum in (('artifacts',10000),('associations',40000),('runs',10000),('lookups',40000)):
        if not isinstance(data[key], list) or len(data[key]) > maximum:
            raise ValueError('invalid evidence population')
    associations = []
    for item in data['associations']:
        a = exact(item, {'source','target','relation','origin','boundary'})
        associations.append(Association(new_ref(a['source']),ref_from(a['target']),Relation(a['relation']),a['boundary'],TraceLinkOrigin(a['origin'])))
    runs = []
    for item in data['runs']:
        r = exact(item, {'reference','test','target','observed_at','outcome','boundary','group'})
        runs.append(Run(new_ref(r['reference']),new_ref(r['test']),snapshot_from(r['target']),instant(r['observed_at']),Outcome(r['outcome']),r['boundary'],r['group']))
    lookups = []
    for item in data['lookups']:
        l = exact(item, {'endpoint','relation','population','direction','status','capability'})
        lookups.append(Lookup(new_ref(l['endpoint']) if l['endpoint'] is not None else None,
                             Relation(l['relation']) if l['relation'] is not None else None,
                             Kind(l['population']) if l['population'] is not None else None,
                             Direction(l['direction']),CollectionStatus(l['status']),TraceabilityCapability(l['capability'])))
    limits = exact(data['limits'], {'artifacts','associations','runs','paths'})
    limits = {k: integral(v) for k,v in limits.items()}
    return Collection(tuple(new_ref(a) for a in data['artifacts']),tuple(associations),tuple(runs),tuple(lookups),
                      snapshot_from(data['snapshot']),code,data['boundary'],instant(data['collected_at']),CollectionStatus(data['status']),Limits(**limits))


def unique_sorted(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [json.loads(key) for key in sorted({canonical(value) for value in values})]


def collection_to_dict(value: Collection) -> dict[str, Any]:
    return {'artifacts':unique_sorted([reference(a) for a in value.artifacts]),
            'associations':unique_sorted([association(a) for a in value.associations]),
            'runs':unique_sorted([{'reference':reference(r.reference),'test':reference(r.test),'target':snapshot(r.target),
                    'observed_at':r.observed_at.astimezone(timezone.utc).isoformat(),'outcome':r.outcome,'boundary':r.boundary,'group':r.group} for r in value.runs]),
            'lookups':unique_sorted([{'endpoint':reference(l.endpoint) if l.endpoint else None,'relation':l.relation,
                    'population':l.population,'direction':l.direction,'status':l.status,'capability':l.capability} for l in value.lookups]),
            'snapshot':snapshot(value.snapshot),'boundary':value.boundary,
            'collected_at':value.collected_at.astimezone(timezone.utc).isoformat(),'status':value.status,
            'limits':{f.name:getattr(value.limits,f.name) for f in fields(Limits)}}


def result_to_dict(report: Report) -> dict[str, Any]:
    demo = to_dict(report)
    result = {key:demo[key] for key in RESULT_KEYS}
    for key, value in result.items():
        if isinstance(value, list):
            result[key] = sorted(value, key=canonical)
    return result


def verification_to_dict(collection: Collection) -> dict[str, Any]:
    # Keep raw bounded input to reproduce conflict/limit diagnostics on re-import.
    raw = collection_to_dict(collection)
    parsed = collection_from(raw, collection.code)
    return {'schema_version':'1.0','collection':raw,'result':result_to_dict(derive(parsed))}


def _verification_from_dict(value: Any, code: TraceabilityReport) -> Collection:
    safe_json(value)
    data = exact(value, {'schema_version','collection','result'})
    if data['schema_version'] != '1.0':
        raise ValueError('unsupported evidence schema')
    collection = collection_from(data['collection'], code)
    normalized = collection_to_dict(collection)
    for key in ('artifacts','associations','runs','lookups'):
        if len(normalized[key]) != len(data['collection'][key]):
            raise ValueError('duplicate portable evidence')
    expected = result_to_dict(derive(collection))
    supplied = exact(data['result'], RESULT_KEYS).copy()
    for key, item in supplied.items():
        if isinstance(item, list):
            supplied[key] = sorted(item,key=canonical)
    if not semantic_equal(expected, supplied):
        raise ValueError('evidence result does not match input')
    return collection


def manifest_from_json(value: str | bytes, code: TraceabilityReport) -> Collection:
    try:
        data = exact(loads(value), {'manifest_version','publication_approved','collection'})
        if data['manifest_version'] != '1.0' or data['publication_approved'] is not True:
            raise ValueError('publication approval required')
        return collection_from(data['collection'], code)
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError):
        raise ValueError('invalid or unapproved evidence manifest') from None


def validate_v4(value: Any) -> dict[str, Any]:
    try:
        safe_json(value)
        if not isinstance(value, dict) or set(value) - ENVELOPE_KEYS or value.get('report_version') != '4.0' or value.get('model') != 'experimental-v0.1':
            raise ValueError('invalid report version')
        validate_public(value)
        legacy = {k:v for k,v in value.items() if k != 'verification_evidence'}
        legacy['report_version'] = '3.0'
        legacy['commit_count'] = integral(legacy['commit_count'])
        validate_report_envelope(legacy)
        from continuity.reporting.portable_git import validate_git
        validate_git(legacy)
        if 'verification_evidence' in value:
            code = traceability_from_dict(value['traceability_evidence']) if 'traceability_evidence' in value else absent_code()
            if code.evidence.boundaries and any(b.revision != value['revision'] for b in code.evidence.boundaries):
                raise ValueError('invalid enclosing snapshot')
            depth = value.get('configuration', {}).get('component_depth')
            if depth is not None and code.evidence.boundaries and code.evidence.component_configuration != f'depth-{integral(depth)}':
                raise ValueError('invalid enclosing component configuration')
            verification_from_dict(value['verification_evidence'], code)
        return value
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError):
        raise ValueError('invalid portable evidence report') from None


def with_verification_evidence(value: dict[str, Any], collection: Collection) -> dict[str, Any]:
    validate_report_envelope(value)
    if value.get('report_version') != '3.0' or 'traceability_evidence' not in value:
        raise ValueError('a compatible report-v3 snapshot is required')
    if canonical(traceability_to_dict(collection.code)) != canonical(traceability_to_dict(traceability_from_dict(value['traceability_evidence']))):
        raise ValueError('invalid code snapshot input')
    return validate_v4({**value,'report_version':'4.0','verification_evidence':verification_to_dict(collection)})


def report_from_json(value: str | bytes) -> dict[str, Any]:
    return validate_v4(loads(value))


def report_to_json(value: dict[str, Any]) -> str:
    validated = validate_v4(value)
    normalized = dict(validated)
    code = absent_code()
    if 'traceability_evidence' in normalized:
        code = traceability_from_dict(normalized['traceability_evidence'])
        normalized['traceability_evidence'] = traceability_to_dict(code)
    if 'verification_evidence' in normalized:
        collection = verification_from_dict(normalized['verification_evidence'], code)
        normalized['verification_evidence'] = verification_to_dict(collection)
    public = wire_numbers({k:v for k,v in normalized.items() if k != 'traceability_evidence'})
    if 'traceability_evidence' in normalized:
        public['traceability_evidence'] = normalized['traceability_evidence']
    output = canonical(public)
    if len(output.encode('utf-8')) > MAX_BYTES:
        raise ValueError('invalid portable evidence report')
    return output


def verification_to_json(collection: Collection) -> str:
    return canonical(wire_numbers(verification_to_dict(collection)))


def verification_from_json(value: str | bytes, code: TraceabilityReport) -> Collection:
    try:
        return verification_from_dict(loads(value), code)
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError):
        raise ValueError('invalid portable evidence section') from None


def integral(value: Any) -> int:
    if type(value) not in (int, float) or not math.isfinite(value) or value != int(value) or not 0 <= value <= 9007199254740991:
        raise ValueError('invalid evidence count')
    return int(value)


def semantic_equal(left: Any, right: Any) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(semantic_equal(v, right[k]) for k,v in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(semantic_equal(a,b) for a,b in zip(left,right))
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    return bool(left == right)


def absent_code() -> TraceabilityReport:
    from continuity.domain.traceability import TraceabilityEvidenceCollection
    from continuity.analysis.traceability import derive as derive_code
    return derive_code(TraceabilityEvidenceCollection((),(),(),(),(),(),(),(),CollectionStatus.FAILED))


def manifest_from_toml(value: str | bytes, code: TraceabilityReport) -> Collection:
    try:
        raw = value.encode('utf-8') if isinstance(value,str) else value
        if len(raw) > MAX_BYTES:
            raise ValueError('invalid evidence manifest')
        data = tomllib.loads(raw.decode('utf-8',errors='strict'))
        safe_json(data)
        # TOML has no null; empty optional field strings explicitly map to absent.
        exact(data, {'manifest_version','publication_approved','collection'})
        c = exact(data['collection'], COLLECTION_KEYS)
        for name in ('artifacts','associations','runs','lookups'):
            if not isinstance(c[name],list):
                raise ValueError('invalid evidence manifest population')
        for r in c['runs']:
            exact(r, {'reference','test','target','observed_at','outcome','boundary','group'})
            if r.get('group') == '': r['group'] = None
        for l in c['lookups']:
            exact(l, {'endpoint','relation','population','direction','status','capability'})
            for key in ('endpoint','relation','population'):
                if l.get(key) == '': l[key] = None
        return manifest_from_json(canonical(data),code)
    except (ValueError,TypeError,KeyError,UnicodeError,OverflowError,RecursionError):
        raise ValueError('invalid or unapproved evidence manifest') from None


def verification_from_dict(value: Any, code: TraceabilityReport) -> Collection:
    try:
        return _verification_from_dict(value,code)
    except (ValueError,TypeError,KeyError,OverflowError,UnicodeError,RecursionError):
        raise ValueError('invalid portable evidence section') from None


def wire_numbers(value: Any) -> Any:
    if isinstance(value,float) and value.is_integer(): return int(value)
    if isinstance(value,list): return [wire_numbers(v) for v in value]
    if isinstance(value,dict):
        times={'as_of','retrieved_at','merged_at','submitted_at','first_activity','last_activity','collected_at','observed_at','start','end'}
        return {k:instant(v).isoformat() if k in times and isinstance(v,str) else wire_numbers(v) for k,v in value.items()}
    return value
