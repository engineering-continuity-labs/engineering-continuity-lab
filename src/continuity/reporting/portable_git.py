"""v4-owned validation of preserved Git/review fields; legacy import stays unchanged."""
import math
from typing import Any

SIGNALS = ('change_ownership','recency','change_frequency','code_area_breadth','unique_contribution','historical_persistence')


def finite(value: Any) -> bool:
    return type(value) in (int,float) and math.isfinite(value) and 0 <= value <= 1


def count(value: Any) -> bool:
    return type(value) in (int,float) and math.isfinite(value) and value == int(value) and 0 <= value <= 9007199254740991


def text(value: Any) -> bool:
    return isinstance(value,str) and bool(value.strip())


def strings(value: Any) -> bool:
    return isinstance(value,list) and all(text(v) for v in value) and len(set(value)) == len(value)


def risk(value: float) -> str:
    return 'CRITICAL' if value >= .8 else 'HIGH' if value >= .6 else 'MEDIUM' if value >= .4 else 'LOW'


def validate_git(value: dict[str, Any]) -> None:
    from continuity.reporting.portable import instant
    instant(value['as_of'])
    for k in ('source','warning','review_evidence_error'):
        if k in value and not isinstance(value[k],str): raise ValueError('invalid report text')
    if 'shallow' in value and type(value['shallow']) is not bool: raise ValueError('invalid shallow state')
    config=value.get('configuration', {})
    if 'component_depth' in config and (not count(config['component_depth']) or config['component_depth'] < 1): raise ValueError('invalid component depth')
    for n in ([config['half_life_days']] if 'half_life_days' in config else []) + list(config.get('weights', {}).values()):
        if type(n) not in (int,float) or not math.isfinite(n) or n < 0: raise ValueError('invalid scoring configuration')
    if not count(value['commit_count']):
        raise ValueError('invalid Git report')
    names = set()
    for c in value['components']:
        if not isinstance(c,dict) or not isinstance(c.get('component'),str) or c['component'] in names or not finite(c.get('concentration')) or c.get('risk') != risk(c['concentration']) or not isinstance(c.get('contributors'),list) or not c['contributors']:
            raise ValueError('invalid Git component')
        names.add(c['component']); people=set(); shares=0.0
        for p in c['contributors']:
            if not isinstance(p,dict) or not text(p.get('contributor')) or p['contributor'] in people or not isinstance(p.get('name'),str) or not finite(p.get('share')) or not finite(p.get('score')) or not count(p.get('commits')) or not strings(p.get('files')) or not p['files'] or not isinstance(p.get('signals'),dict) or not all(finite(p['signals'].get(s)) for s in SIGNALS):
                raise ValueError('invalid Git contributor')
            for k in ('additions','deletions','unknown_line_changes'):
                if k in p and not count(p[k]): raise ValueError('invalid file counts')
            activity=p.get('file_activity', {})
            if not isinstance(activity,dict): raise ValueError('invalid file activity')
            for path,a in activity.items():
                if not text(path) or not isinstance(a,dict) or any(not count(a.get(k)) for k in ('additions','deletions','unknown_line_changes')) or not strings(a.get('commits')): raise ValueError('invalid file activity')
                instant(a['first_activity']);instant(a['last_activity'])
            people.add(p['contributor']);shares+=p['share']
        if abs(shares-1)>1e-6 or abs(sum(p['share']**2 for p in c['contributors'])-c['concentration'])>1e-6:
            raise ValueError('invalid Git arithmetic')
        file_people=c.get('file_contributors', {})
        if not isinstance(file_people,dict) or any(not text(k) or not strings(v) for k,v in file_people.items()): raise ValueError('invalid file contributor map')
    if 'filters' in value:
        f=value['filters']
        if not isinstance(f,dict) or any(k in f and (not isinstance(f[k],list) or any(not isinstance(v,str) for v in f[k])) for k in ('paths','authors')):
            raise ValueError('invalid Git filters')
        if any(k in f and type(f[k]) is not bool for k in ('exclude_bots','exclude_generated')): raise ValueError('invalid filter state')
    if 'filter_evidence' in value:
        f=value['filter_evidence']
        if not isinstance(f,dict) or any(not count(f.get(k)) for k in ('excluded_file_changes','input_file_changes')):
            raise ValueError('invalid Git filters')
    if 'review_evidence' in value:
        validate_reviews(value['review_evidence'])


def validate_reviews(review: Any) -> None:
    from continuity.reporting.portable import instant
    from continuity.domain.reviews import (ReviewIdentity, ReviewEvent, ReviewState, PullRequestEvidence,
                                           ProviderProvenance, ReviewEvidenceCollection, CollectionStatus)
    from continuity.domain.models import DirectoryComponents
    from continuity.analysis.reviews import analyze_reviews
    from dataclasses import asdict
    if not isinstance(review,dict) or not isinstance(review.get('provenance'),dict) or not isinstance(review.get('components'),list):
        raise ValueError('invalid reviews')
    collection=review['provenance'];p=collection['provenance']
    if not isinstance(p,dict) or not all(text(p.get(k)) for k in ('provider','repository','evidence_boundary')) or any(c in p['repository'] for c in ('?','#','@')) or collection.get('status') not in ('COMPLETE','PARTIAL','FAILED') or not isinstance(collection.get('diagnostics'),list) or not all(text(v) for v in collection['diagnostics']) or not isinstance(collection.get('pull_requests'),list):
        raise ValueError('invalid review provenance')
    for k in ('closed_pull_requests_inspected','merged_pull_requests_observed'):
        if k in collection and not count(collection[k]):
            raise ValueError('invalid review counts')
    def identity(v: Any) -> ReviewIdentity:
        if not isinstance(v,dict) or not text(v.get('identifier')) or not (v.get('display_name') is None or isinstance(v['display_name'],str)) or type(v.get('is_bot')) is not bool:
            raise ValueError('invalid review identity')
        return ReviewIdentity(v['identifier'],v['display_name'],v['is_bot'])
    ids=set();prs=[]
    for pr in collection['pull_requests']:
        if not isinstance(pr,dict) or not text(pr.get('identifier')) or pr['identifier'] in ids or not strings(pr.get('changed_paths')) or not pr['changed_paths'] or not isinstance(pr.get('reviews'),list):
            raise ValueError('invalid PR')
        ids.add(pr['identifier']);events=[];event_ids=set()
        for e in pr['reviews']:
            if not isinstance(e,dict) or not text(e.get('identifier')) or e['identifier'] in event_ids or type(e.get('dismissed')) is not bool or not (e.get('provider_order') is None or count(e['provider_order'])):
                raise ValueError('invalid review event')
            event_ids.add(e['identifier'])
            events.append(ReviewEvent(e['identifier'],ReviewState(e['state']),identity(e['reviewer']) if e['reviewer'] is not None else None,instant(e['submitted_at']) if e['submitted_at'] is not None else None,e['provider_order'],e['dismissed']))
        prs.append(PullRequestEvidence(pr['identifier'],identity(pr['author']),instant(pr['merged_at']),tuple(pr['changed_paths']),tuple(events)))
    evidence=ReviewEvidenceCollection(ProviderProvenance(p['provider'],p['repository'],p['evidence_boundary'],instant(p['retrieved_at'])),tuple(prs),CollectionStatus(collection['status']),tuple(collection['diagnostics']))
    depth=review.get('component_depth')
    if depth is not None and (not count(depth) or depth < 1):
        raise ValueError('invalid review depth')
    if depth is not None:
        expected=asdict(analyze_reviews(evidence,DirectoryComponents(int(depth))))['components']
        rows={c['component']:c for c in expected}
        if len(rows)!=len(review['components']):
            raise ValueError('invalid review components')
        for actual in review['components']:
            target=rows.get(actual['component'])
            if target is None:
                raise ValueError('invalid review component')
            for k,v in target.items():
                if k=='reviewer_shares' and k not in actual:
                    continue
                given=actual.get(k)
                if isinstance(v,float):
                    if not finite(given) or abs(v-given)>1e-6:
                        raise ValueError('invalid review aggregate')
                elif isinstance(v,tuple):
                    if sorted(v)!=sorted(given):
                        raise ValueError('invalid review aggregate')
                elif v != given:
                    raise ValueError('invalid review aggregate')
    else:
        # Unknown historic mapping cannot be reconstructed; verify bounded counts.
        from continuity.analysis.reviews import effective_reviews
        units: dict[str,int]={};covered=0
        for pr in prs:
            q=[r for r in effective_reviews(pr) if r.qualifying]
            covered+=bool(q)
            for r in q:
                assert r.reviewer is not None
                k=r.reviewer.identifier.casefold();units[k]=units.get(k,0)+1
        names=set()
        for c in review['components']:
            if not isinstance(c,dict) or not text(c.get('component')) or c['component'] in names or not count(c.get('mapped_pull_requests')) or not count(c.get('covered_pull_requests')) or c['mapped_pull_requests']>len(prs) or c['covered_pull_requests']>min(covered,c['mapped_pull_requests']) or c.get('coverage_status')!=collection['status'] or not isinstance(c.get('reviewer_units'),dict) or any(not count(n) or n<=0 or n>units.get(k,0) for k,n in c['reviewer_units'].items()):
                raise ValueError('invalid review aggregate')
            names.add(c['component']);denominator=c['mapped_pull_requests'];total=sum(c['reviewer_units'].values())
            if (denominator==0 and c.get('coverage') is not None) or (denominator>0 and (not finite(c.get('coverage')) or abs(c['coverage']-c['covered_pull_requests']/denominator)>1e-6)) or bool(total)!=bool(c['covered_pull_requests']):
                raise ValueError('invalid review coverage')
            if not strings(c.get('unreviewed_pull_requests')) or len(c['unreviewed_pull_requests'])!=denominator-c['covered_pull_requests'] or any(i not in ids for i in c['unreviewed_pull_requests']) or not isinstance(c.get('excluded_reasons'),dict) or any(not text(k) or not count(n) for k,n in c['excluded_reasons'].items()):
                raise ValueError('invalid review aggregate')
            hhi=sum((n/total)**2 for n in c['reviewer_units'].values()) if total else None
            if hhi is None:
                if c.get('concentration') is not None or c.get('risk') is not None:
                    raise ValueError('invalid review aggregate')
            elif not finite(c.get('concentration')) or abs(c['concentration']-hhi)>1e-6 or c.get('risk')!=risk(c['concentration']):
                raise ValueError('invalid review aggregate')
