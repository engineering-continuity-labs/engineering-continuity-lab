"""Allowlisted v0.4-demo-1 artifact; intentionally not a Git report envelope."""
from datetime import timezone
import json
from typing import Any

from continuity.analysis.verification import Report
from continuity.domain.verification import Association, Endpoint, Reference, Snapshot
from continuity.reporting.traceability import traceability_to_dict, trace_path_to_dict


def reference(value: Endpoint) -> dict[str, str]:
    if isinstance(value, Reference):
        return {key:str(getattr(value,key)) for key in ('kind','instance','scope','identifier','version','document_kind')}
    return {key:str(getattr(value,key)) for key in ('kind','provider','instance','scope','identifier','repository','context','configuration','algorithm')}


def snapshot(value: Snapshot) -> dict[str, str]:
    return {key:str(getattr(value,key)) for key in ('alias','repository','revision','fingerprint')}


def association(value: Association) -> dict[str, Any]:
    return {'source':reference(value.source),'target':reference(value.target),'relation':value.relation,
            'origin':value.origin,'boundary':value.boundary}


def to_dict(report: Report) -> dict[str, Any]:
    code = traceability_to_dict(report.collection.code)
    collection = report.collection
    return {
        'schema_version':'v0.4-demo-1','synthetic':True,'rule_version':report.rule_version,
        'warning':'Synthetic declared historical evidence; no real tests were executed. No business correctness or readiness claim.',
        'collection_status':collection.status,'boundary':collection.boundary,
        'collected_at':collection.collected_at.astimezone(timezone.utc).isoformat(),
        'snapshot':snapshot(collection.snapshot),'snapshot_valid':report.snapshot_valid,
        'artifacts':[reference(a) for a in collection.artifacts],
        'associations':[association(a) for a in report.associations],
        'lookups':[{'endpoint':reference(l.endpoint) if l.endpoint else None,'relation':l.relation,'population':l.population,
                    'direction':l.direction,'status':l.status,'capability':l.capability} for l in collection.lookups],
        'requirements':[{'reference':reference(r.reference),'implementation':r.implementation,'tests':r.tests,
                         'architecture':r.architecture} for r in report.requirements],
        'paths':[{'association':association(p.association),'code_path':trace_path_to_dict(p.code_path)} for p in report.projections],
        'runs':[{'reference':reference(r.run.reference),'test':reference(r.run.test),'target':snapshot(r.run.target),
                 'observed_at':r.run.observed_at.astimezone(timezone.utc).isoformat(),'outcome':r.run.outcome,
                 'boundary':r.run.boundary,'group':r.run.group,'qualified':r.qualified,'reason':r.reason} for r in report.runs],
        'metrics':[{'dimension':m.dimension,'numerator':m.numerator,'denominator':m.denominator,'value':m.value,
                    'status':m.status,'unknown_count':m.unknown_count,'excluded_count':m.excluded_count,'reason':m.reason,
                    'collection_status':collection.status,'boundaries':[collection.boundary,*[b['identifier'] for b in code['collection']['boundaries']]]} for m in report.metrics],
        'outcomes':dict(report.outcomes),
        'gaps':[{'endpoint':reference(g.endpoint),'relation':g.relation,'direction':g.direction,'status':g.status,'reason':g.reason} for g in report.gaps],
        'diagnostics':[{'reason':d.reason,'endpoint':reference(d.endpoint) if d.endpoint else None,'relation':d.relation} for d in report.diagnostics],
        'dropped':dict(report.dropped),'code_traceability':code,
    }


def to_json(report: Report) -> str:
    return json.dumps(to_dict(report),sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
