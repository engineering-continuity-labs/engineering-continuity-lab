"""V4-only public allowlists. Legacy import contracts remain unchanged."""
from typing import Any
import re
from continuity.reporting.traceability import _public_values

SIGNALS = {'change_ownership','recency','change_frequency','code_area_breadth','unique_contribution','historical_persistence'}
SCHEMAS = {
    'envelope': {'model','report_version','warning','configuration','filters','filter_evidence','revision','as_of','shallow','commit_count','components','source','review_evidence','review_evidence_error','traceability_evidence','verification_evidence'},
    'configuration': {'component_depth','weights','half_life_days'},
    'filters': {'paths','authors','exclude_bots','exclude_generated'},
    'filter_evidence': {'excluded_file_changes','input_file_changes'},
    'component': {'component','concentration','risk','contributors','file_contributors'},
    'person': {'contributor','name','share','score','commits','files','signals','additions','deletions','unknown_line_changes','file_activity'},
    'activity': {'additions','deletions','commits','first_activity','last_activity','unknown_line_changes'},
    'review': {'provenance','components','component_depth'},
    'collection': {'provenance','pull_requests','status','diagnostics','closed_pull_requests_inspected','merged_pull_requests_observed'},
    'provenance': {'provider','repository','evidence_boundary','retrieved_at'},
    'pr': {'identifier','author','merged_at','changed_paths','reviews'},
    'identity': {'identifier','display_name','is_bot'},
    'event': {'identifier','state','reviewer','submitted_at','provider_order','dismissed'},
    'review_component': {'component','mapped_pull_requests','covered_pull_requests','coverage','coverage_status','reviewer_units','reviewer_shares','concentration','risk','unreviewed_pull_requests','excluded_reasons'},
}

def allowed(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) - keys:
        raise ValueError('invalid public report fields')

def validate_public(value: dict[str, Any]) -> None:
    _public_values(value)
    public_paths(value)
    allowed(value, SCHEMAS['envelope'])
    for name in ('configuration','filters','filter_evidence'):
        if name in value:
            allowed(value[name], SCHEMAS[name])
    if 'weights' in value.get('configuration', {}):
        allowed(value['configuration']['weights'], SIGNALS)
    for c in value['components']:
        allowed(c, SCHEMAS['component'])
        for p in c['contributors']:
            allowed(p, SCHEMAS['person'])
            allowed(p['signals'], SIGNALS)
            activities=p.get('file_activity', {})
            if not isinstance(activities,dict): raise ValueError('invalid public activity map')
            for activity in activities.values():
                allowed(activity, SCHEMAS['activity'])
    if 'review_evidence' not in value:
        return
    review = value['review_evidence']
    allowed(review, SCHEMAS['review'])
    collection = review['provenance']
    allowed(collection, SCHEMAS['collection'])
    allowed(collection['provenance'], SCHEMAS['provenance'])
    for pr in collection['pull_requests']:
        allowed(pr, SCHEMAS['pr'])
        allowed(pr['author'], SCHEMAS['identity'])
        for event in pr['reviews']:
            allowed(event, SCHEMAS['event'])
            if event['reviewer'] is not None:
                allowed(event['reviewer'], SCHEMAS['identity'])
    for row in review['components']:
        allowed(row, SCHEMAS['review_component'])


def public_paths(value: Any) -> None:
    if isinstance(value,str) and (value.startswith('/') or re.search(r'(?:[A-Za-z]:[\\/]|\\\\)',value)):
        raise ValueError('invalid public local path')
    if isinstance(value,dict):
        for k,v in value.items(): public_paths(k); public_paths(v)
    elif isinstance(value,list):
        for v in value: public_paths(v)
