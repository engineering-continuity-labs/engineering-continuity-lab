"""Strict offline normalized inputs and recomputable engineering JSON packages.

No provider access, implicit sample data, mutable legacy report or HTML renderer.
"""
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from fractions import Fraction
from hashlib import sha256
import json
from typing import Any

from continuity.analysis.delivery_runs import Build, BuildResult, PullRequest, PRState, analyze_builds, analyze_prs
from continuity.analysis.engineering_review import Lifecycle, State, Transition, analyze_population
from continuity.domain.engineering_review import Window, Windows
from continuity.domain.verification import approved
from continuity.reporting.portable import canonical, exact, instant, loads, safe_json, validate_v4, report_to_json
from continuity.reporting.portable_public import validate_public
from continuity.reporting.traceability import validate_report_envelope


def public(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace('+00:00', 'Z')
    if isinstance(value, Fraction):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: public(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [public(v) for v in value]
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items()}
    return value


def nullable_time(value: Any) -> datetime | None:
    return None if value is None else instant(value)


def lifecycle_from(value: Any) -> Lifecycle:
    d = exact(value, {f.name for f in fields(Lifecycle)})
    if not isinstance(d['reference'], list) or not isinstance(d['transitions'], list):
        raise ValueError('invalid engineering evidence')
    events = []
    for raw in d['transitions']:
        e = exact(raw, {f.name for f in fields(Transition)})
        events.append(Transition(e['identifier'], e['sequence'], instant(e['occurred_at']),
                                 State(e['previous']), State(e['next'])))
    return Lifecycle(tuple(d['reference']), d['observation'], nullable_time(d['created_at']), State(d['initial_state']),
                     instant(d['history_start']), instant(d['history_end']), d['history_complete'], tuple(events),
                     d['priority'], d['severity'], d['type_alias'], d['history_capability'], nullable_time(d['category_as_of']))


def pr_from(value: Any) -> PullRequest:
    d = exact(value, {f.name for f in fields(PullRequest)})
    if not isinstance(d['reference'], list):
        raise ValueError('invalid engineering evidence')
    return PullRequest(tuple(d['reference']), PRState(d['state']), instant(d['state_as_of']),
                       nullable_time(d['created_at']), nullable_time(d['merged_at']), d['observation'])


def build_from(value: Any) -> Build:
    d = exact(value, {f.name for f in fields(Build)})
    if not isinstance(d['reference'], list):
        raise ValueError('invalid engineering evidence')
    return Build(tuple(d['reference']), BuildResult(d['result']), d['terminal'],
                 nullable_time(d['start_at']), nullable_time(d['finish_at']), d['observation'])


def collection(value: Any, schema: str, windows: Windows, system: str) -> dict[str, Any]:
    safe_json(value)
    if len(canonical(value).encode('utf-8')) > 8 * 1024 * 1024:
        raise ValueError('invalid engineering input size')
    keys = {'schema_version', 'system', 'alias', 'retrieved_at', 'policy_fingerprint',
            'selection_fingerprint', 'capability', 'status', 'created_start', 'work_items', 'pull_requests', 'builds',
            'populations', 'categories', 'mappings', 'mapping_complete', 'mapping_revision',
            'selected_types', 'publication_approved'}
    d = exact(value, keys)
    if (d['schema_version'] != schema or d['system'] != system or d['publication_approved'] is not True
            or d['capability'] not in ('SUPPORTED', 'UNSUPPORTED', 'UNKNOWN')
            or d['status'] not in ('COMPLETE', 'PARTIAL', 'FAILED') or type(d['created_start']) is not bool):
        raise ValueError('invalid engineering collection')
    for name in ('system', 'alias', 'policy_fingerprint', 'selection_fingerprint'):
        approved(d[name])
    if type(d['mapping_complete']) is not bool or not isinstance(d['mappings'], list) or len(d['mappings']) > 40000:
        raise ValueError('invalid engineering mapping')
    approved(d['mapping_revision'])
    mappings = []
    for mapping in d['mappings']:
        m = exact(mapping, {'record_ref', 'component_ref', 'mapping_id', 'origin', 'boundary', 'completeness'})
        if (not isinstance(m['record_ref'], list) or len(m['record_ref']) != 5
                or m['origin'] != 'DECLARED_MAPPING' or m['completeness'] not in ('COMPLETE', 'PARTIAL')):
            raise ValueError('invalid engineering membership')
        for alias in [*m['record_ref'], m['mapping_id'], m['boundary']]:
            approved(alias)
        from continuity.reporting.portable import ref_from
        from continuity.domain.traceability import ArtifactReference, ArtifactKind
        component = ref_from(m['component_ref'])
        if not isinstance(component, ArtifactReference) or component.kind != ArtifactKind.COMPONENT:
            raise ValueError('invalid component reference')
        from continuity.reporting.portable_public import public_paths
        from continuity.reporting.traceability import _public_values
        _public_values(m['component_ref'])
        public_paths(m['component_ref'])
        for alias in (component.provider, component.instance, component.scope,
                      component.repository, component.context, component.configuration, component.algorithm):
            if alias:
                approved(alias)
        mappings.append(m)
    populations = exact(d['populations'], {'work_items', 'pull_requests', 'builds'})
    for name, coverage in populations.items():
        exact(coverage, {'capability', 'status', 'provider', 'instance', 'scope', 'repository'})
        for field in ('provider', 'instance', 'scope', 'repository'):
            approved(coverage[field])
        if coverage['capability'] not in ('SUPPORTED', 'UNSUPPORTED', 'UNKNOWN') or coverage['status'] not in ('COMPLETE', 'PARTIAL', 'FAILED'):
            raise ValueError('invalid engineering population coverage')
        if coverage['capability'] != 'SUPPORTED' and d[name]:
            raise ValueError('invalid unsupported population')
    categories = exact(d['categories'], {'priority', 'severity'})
    for name, category in categories.items():
        exact(category, {'capability', 'values', 'fingerprint'})
        if category['capability'] not in ('SUPPORTED', 'UNSUPPORTED', 'UNKNOWN') or not isinstance(category['values'], list):
            raise ValueError('invalid category capability')
        approved(category['fingerprint'])
        if len(category['values']) > 100 or len(set(category['values'])) != len(category['values']):
            raise ValueError('invalid category selection')
        for v in category['values']:
            approved(v)
    retrieved = instant(d['retrieved_at'])
    if retrieved < windows.assessment_as_of:
        raise ValueError('invalid engineering retrieval boundary')
    for name in ('work_items', 'pull_requests', 'builds'):
        if not isinstance(d[name], list) or len(d[name]) > 10000:
            raise ValueError('invalid engineering population')
    items = tuple(lifecycle_from(v) for v in d['work_items'])
    if not isinstance(d['selected_types'], list) or not d['selected_types'] or len(d['selected_types']) > 100:
        raise ValueError('invalid selected work-item types')
    for alias in d['selected_types']:
        approved(alias)
    if any(r.type_alias not in d['selected_types'] for r in items):
        raise ValueError('invalid selected work-item population')
    for name, config in categories.items():
        if config['capability'] != 'SUPPORTED' and any(getattr(r, name) is not None for r in items):
            raise ValueError('invalid unsupported category observation')
    prs = tuple(pr_from(v) for v in d['pull_requests'])
    builds = tuple(build_from(v) for v in d['builds'])
    for population, records in (('work_items', items), ('pull_requests', prs), ('builds', builds)):
        coverage = populations[population]
        if any(r.reference[1:4] != (coverage['provider'], coverage['instance'], coverage['scope']) for r in records):
            raise ValueError('invalid engineering population scope')
    if sum(len(r.transitions) for r in items) > 40000:
        raise ValueError('invalid engineering history limit')
    if (any(r.history_end > retrieved or r.created_at is not None and r.created_at > retrieved for r in items)
            or any(r.state_as_of > retrieved for r in prs)
            or any(r.finish_at is not None and r.finish_at > retrieved or
                   r.start_at is not None and r.start_at > retrieved for r in builds)):
        raise ValueError('invalid engineering observation boundary')
    if schema == 'quality-evidence-1' and (prs or builds or not d['created_start']):
        raise ValueError('invalid quality population')
    if d['capability'] != 'SUPPORTED' and (items or prs or builds):
        raise ValueError('invalid unsupported population')
    result = dict(d)
    result['selected_types'] = sorted(set(d['selected_types']))
    result['categories'] = {name: {**config, 'values': sorted(config['values'])} for name, config in categories.items()}
    result['mappings'] = sorted({canonical(m): m for m in mappings}.values(), key=canonical)
    result['retrieved_at'] = public(retrieved)
    # Duplicate equal observations are sets; ordered histories remain ordered.
    for name, records in (('work_items', items), ('pull_requests', prs), ('builds', builds)):
        result[name] = [public(r) for r in sorted(set(records), key=lambda r: canonical(public(r)))]
    safe_json(result)
    if len(canonical(result).encode('utf-8')) > 8 * 1024 * 1024:
        raise ValueError('invalid engineering input size')
    return result


def dimension(d: dict[str, Any], window: Window) -> dict[str, Any]:
    def complete(name: str) -> bool:
        c = d['populations'][name]
        return bool(d['capability'] == c['capability'] == 'SUPPORTED' and d['status'] == c['status'] == 'COMPLETE')
    wi = analyze_population(tuple(lifecycle_from(v) for v in d['work_items']), window,
                            enumeration_complete=complete('work_items'), created_start=d['created_start'])
    category_metrics = {}
    retained: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for r in d['work_items']:
        if tuple(r['reference']) not in wi.excluded_references:
            retained.setdefault(tuple(r['reference']), []).append(r)
    for name, config in d['categories'].items():
        inventory = [r for r in wi.results if r.inventory is not None]
        values = []
        for r in inventory:
            observed = {source[name] for source in retained[r.reference]
                        if source['category_as_of'] is not None and instant(source['category_as_of']) == window.end}
            values.append(next(iter(observed)) if len(observed) == 1 else None)
        counts = {v: values.count(v) for v in sorted(config['values'])}
        unknown = sum(v not in config['values'] for v in values)
        usable = config['capability'] == 'SUPPORTED' and (wi.availability == 'OBSERVED' or bool(values))
        if values and all(v is None for v in values):
            usable = False
        category_metrics[name] = {'capability': config['capability'], 'counts': counts if usable else None,
                                 'unknown': unknown if usable else None,
                                 'availability': 'UNAVAILABLE' if not usable else
                                 ('OBSERVED' if wi.availability == 'OBSERVED' and not unknown else 'PARTIAL')}
    result = {'capability': d['capability'], 'collection_status': d['status'], 'population_coverage': d['populations'],
            'categories': category_metrics,
            'work_items': public(wi),
            'pull_requests': public(analyze_prs(tuple(pr_from(v) for v in d['pull_requests']), window,
                                              enumeration_complete=complete('pull_requests'))),
            'builds': public(analyze_builds(tuple(build_from(v) for v in d['builds']), window,
                                           enumeration_complete=complete('builds')))}
    if (d['populations']['builds']['capability'] != 'SUPPORTED' or d['capability'] != 'SUPPORTED'
            or result['builds']['availability'] == 'UNAVAILABLE'):
        for field in ('categories', 'known_terminal', 'unfinished', 'undated'):
            result['builds'][field] = None
    return result


def median_trend(current: dict[str, Any], previous: dict[str, Any], metric: str) -> dict[str, Any]:
    a, b = current[metric], previous[metric]
    sample = 'lead' if metric == 'pull_requests' else 'durations'
    qualified = 'lead_complete' if metric == 'pull_requests' else 'duration_complete'
    if (a['availability'] != 'OBSERVED' or b['availability'] != 'OBSERVED'
            or not a[qualified] or not b[qualified]
            or a[sample]['count'] < 4 or b[sample]['count'] < 4):
        return {'absolute': None, 'relative': None, 'reason': 'INCOMPLETE_OR_SMALL_SAMPLE'}
    am, bm = a[sample]['median'], b[sample]['median']
    av, bv = Fraction(am['numerator'], am['denominator']), Fraction(bm['numerator'], bm['denominator'])
    return {'absolute': public(av - bv), 'relative': public((av - bv) / bv) if bv > 0 else None,
            'reason': None if bv > 0 else 'BASELINE_ZERO'}


def _compose(*, assessment_id: str, system: str, windows: Windows,
            delivery: dict[str, Any] | None = None, quality: dict[str, Any] | None = None,
            ecl_report: dict[str, Any] | None = None) -> dict[str, Any]:
    approved(assessment_id)
    approved(system)
    evidence: dict[str, Any] = {}
    dimensions: dict[str, Any] = {}
    sources = []
    components: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    def legacy_finding(rule: str, scope: Any, supports: Any, severity: str, value: Any, threshold: Any) -> None:
        full_scope = {'system': system, 'legacy': scope, 'source_as_of': ecl_report['as_of'] if ecl_report else None}
        finding_id = sha256(canonical({'rule': rule, 'scope': full_scope, 'supports': supports}).encode()).hexdigest()
        findings.append({'id': finding_id, 'rule_id': rule, 'rule_version': 'engineering-review-rules-1',
                         'scope': full_scope, 'severity': severity, 'references': supports, 'value': value,
                         'threshold': threshold, 'limitations': ['SOURCE_BOUNDARY'],
                         'investigation': 'INSPECT_' + rule + '_EVIDENCE_AND_LIMITATIONS'})
    legacy_limitations = []
    if ecl_report is not None:
        if ecl_report.get('report_version') == '4.0':
            ecl_report = loads(report_to_json(validate_v4(ecl_report)))
        else:
            validate_report_envelope(ecl_report)
            validate_public(ecl_report)
            from continuity.reporting.portable_git import validate_git
            validate_git(ecl_report)
            ecl_report = loads(canonical(ecl_report))
        if instant(ecl_report['as_of']) > windows.assessment_as_of:
            raise ValueError('invalid legacy source boundary')
        evidence['ecl_report'] = ecl_report
        sources.append({'role': 'ecl_report', 'alias': 'existing-report',
                        'digest': sha256(canonical(ecl_report).encode()).hexdigest(), 'retrieved_at': ecl_report['as_of']})
        dimensions['legacy'] = {'report_version': ecl_report.get('report_version', '1.0'),
                                'source_as_of': ecl_report['as_of'], 'report_reference': 'evidence.ecl_report',
                                'boundary': 'HISTORICAL_SOURCE_BOUNDARY' if instant(ecl_report['as_of']) < windows.current.start else 'SOURCE_BOUNDARY'}
        trace = ecl_report.get('traceability_evidence', {}).get('result', {})
        for artifact in trace.get('artifacts', []):
            ref = artifact.get('artifact', artifact)
            if isinstance(ref, dict) and ref.get('kind') == 'COMPONENT':
                components[canonical(ref)] = {'component_ref': ref, 'dimensions': {}}
        for component in ecl_report['components']:
            if component['risk'] in ('HIGH', 'CRITICAL'):
                legacy_finding('ER01', component['component'], [{'report_component': component['component']}],
                               'HIGH' if component['risk'] == 'CRITICAL' else 'ATTENTION', component['risk'], 'HIGH')
        reviews = ecl_report.get('review_evidence', {})
        for row in reviews.get('components', []):
            if (row['coverage_status'] == 'COMPLETE' and row['mapped_pull_requests'] >= 4
                    and row['coverage'] is not None and row['coverage'] < 0.5):
                legacy_finding('ER02', row['component'], [{'review_component': row['component']}],
                               'ATTENTION', row['coverage'], 0.5)
        missing = [g for g in trace.get('gaps', []) if g['status'] == 'MISSING']
        if missing:
            legacy_finding('ER03', 'traceability', missing, 'ATTENTION', len(missing), 1)
        verification_section = ecl_report.get('verification_evidence', {})
        verification = verification_section.get('result', {})
        verification_source = verification_section.get('collection', {})
        lookups = verification_source.get('lookups', [])
        selected_tests_complete = any(l['population'] == 'TEST' and l['status'] == 'COMPLETE'
                                      and l['capability'] == 'SUPPORTED' for l in lookups)
        missing = []
        if (verification_source.get('status') == 'COMPLETE' and verification.get('snapshot_valid')
                and selected_tests_complete):
            for test in verification_source.get('artifacts', []):
                if test['kind'] != 'TEST':
                    continue
                supported = any(l['endpoint'] == test and l['relation'] == 'VERIFICATION_TEST'
                                and l['direction'] == 'INBOUND' and l['status'] == 'COMPLETE'
                                and l['capability'] == 'SUPPORTED' for l in lookups)
                qualified = any(r['qualified'] and r['test'] == test for r in verification.get('runs', []))
                if supported and not qualified:
                    missing.append({'test': test, 'reason': 'NO_QUALIFIED_OBSERVATION',
                                    'target': verification_source['snapshot']})
        if missing:
            legacy_finding('ER04', 'verification', missing, 'ATTENTION', len(missing), 1)
    else:
        dimensions['legacy'] = {'availability': 'UNAVAILABLE', 'reason': 'MISSING_INPUT'}
        legacy_limitations.append('MISSING_LEGACY_REPORT')
    for name, raw in (('delivery', delivery), ('quality', quality)):
        if raw is None:
            dimensions[name] = {'availability': 'UNAVAILABLE', 'capability': 'UNKNOWN', 'reason': 'MISSING_INPUT'}
            continue
        normalized = collection(raw, name + '-evidence-1', windows, system)
        evidence[name] = normalized
        sources.append({'role': name, 'alias': normalized['alias'], 'digest': sha256(canonical(normalized).encode()).hexdigest(),
                        'retrieved_at': normalized['retrieved_at']})
        current, previous = dimension(normalized, windows.current), dimension(normalized, windows.previous)
        trend = median_trend(current, previous, 'work_items')
        dimensions[name] = {'current': current, 'previous': previous, 'median_trend': trend}
        dimensions[name]['duration_trends'] = {metric: median_trend(current, previous, metric)
                                               for metric in ('work_items', 'pull_requests', 'builds')}
        all_refs = {canonical(v['reference']) for population in ('work_items', 'pull_requests', 'builds')
                    for v in normalized[population]}
        mappings = normalized['mappings']
        if any(canonical(m['record_ref']) not in all_refs for m in mappings):
            raise ValueError('dangling engineering membership')
        revision_matches = ecl_report is not None and normalized['mapping_revision'] == ecl_report['revision']
        boundaries = {b['identifier']: b for b in (ecl_report or {}).get('traceability_evidence', {}).get('collection', {}).get('boundaries', [])}
        repositories = {canonical(v['reference']): normalized['populations'][population]['repository']
                        for population in ('work_items', 'pull_requests', 'builds') for v in normalized[population]}
        valid_mappings = [m for m in mappings if revision_matches and canonical(m['component_ref']) in components
                          and m['completeness'] == 'COMPLETE' and m['boundary'] in boundaries
                          and boundaries[m['boundary']]['revision'] == normalized['mapping_revision']
                          and boundaries[m['boundary']]['repository'] == m['component_ref']['repository']
                          and repositories[canonical(m['record_ref'])] == m['component_ref']['repository']]
        mapped_refs = {canonical(m['record_ref']) for m in valid_mappings}
        dimensions[name]['mapping'] = {'mapped': len(mapped_refs), 'unmapped': len(all_refs - mapped_refs),
                                      'unresolved': len(mappings) - len(valid_mappings),
                                      'overlapping': sum(sum(canonical(m['record_ref']) == ref for m in valid_mappings) > 1
                                                         for ref in mapped_refs)}
        for component_key, row in components.items():
            memberships = {canonical(m['record_ref']) for m in valid_mappings if canonical(m['component_ref']) == component_key}
            scoped = dict(normalized)
            for population in ('work_items', 'pull_requests', 'builds'):
                scoped[population] = [v for v in normalized[population] if canonical(v['reference']) in memberships]
                if not normalized['mapping_complete'] or not revision_matches or len(valid_mappings) != len(mappings):
                    scoped['populations'] = {k: {**v, 'status': 'PARTIAL'}
                                             for k, v in normalized['populations'].items()}
            row['dimensions'][name] = {'current': dimension(scoped, windows.current),
                                       'previous': dimension(scoped, windows.previous), 'memberships': sorted(memberships)}
        wi = current['work_items']
        def add(rule: str, refs: list[Any], severity: str, value: Any) -> None:
            scope = {'system': system, 'dimension': name, 'window': public(windows.current)}
            support = sorted(refs, key=canonical)
            identifier = sha256(canonical({'rule': rule, 'scope': scope, 'refs': support}).encode()).hexdigest()
            findings.append({'id': identifier, 'rule_id': rule, 'rule_version': 'engineering-review-rules-1',
                             'scope': scope, 'severity': severity, 'references': support, 'value': value,
                             'threshold': {'ER05': {'age_days_at_least': 30, 'high_age_days_at_least': 90, 'qualified_items_at_least': 1},
                                           'ER07': {'age_days_at_least': 30, 'high_age_days_at_least': 90, 'qualified_items_at_least': 1}, 'ER06': public(Fraction(1, 4)),
                                           'ER08': 1, 'ER09': public(Fraction(1, 4))}[rule],
                             'policy_fingerprint': normalized['policy_fingerprint'],
                             'sample_size': len(support), 'limitations': [],
                             'investigation': 'INSPECT_' + rule + '_EVIDENCE_AND_LIMITATIONS'})
        if wi['availability'] == 'OBSERVED':
            aged = [r for r in wi['results'] if r['age_microseconds'] is not None
                    and r['age_microseconds'] >= 30 * 86400000000]
            if aged:
                add('ER07' if name == 'quality' else 'ER05', [r['reference'] for r in aged],
                    'HIGH' if any(r['age_microseconds'] >= 90 * 86400000000 for r in aged) else 'ATTENTION', len(aged))
            if name == 'quality' and wi['opened'] is not None and wi['completed'] is not None and wi['opened'] > wi['completed']:
                add('ER08', [r['reference'] for r in wi['results']], 'ATTENTION', wi['opened'] - wi['completed'])
        prs = current['pull_requests']
        if name == 'delivery' and prs['inventory_complete']:
            aged_prs = [r for r in prs['open_ages'] if r[1] is not None and r[1] >= 30 * 86400000000]
            if aged_prs:
                # ER05 is deduplicated once per dimension/window; retain WI
                # and PR support together rather than overwrite either unit.
                existing = next((f for f in findings if f['rule_id'] == 'ER05' and f['scope'].get('dimension') == name), None)
                references = [r[0] for r in aged_prs] + (existing['references'] if existing else [])
                severity = 'HIGH' if any(r[1] >= 90 * 86400000000 for r in aged_prs) or existing and existing['severity'] == 'HIGH' else 'ATTENTION'
                if existing:
                    findings.remove(existing)
                add('ER05', references, severity, len(references))
        relative = trend['relative']
        if name == 'delivery' and relative is not None and Fraction(relative['numerator'], relative['denominator']) >= Fraction(1, 4):
            add('ER06', [r['reference'] for r in wi['results'] + previous['work_items']['results']
                         if r['duration_microseconds'] is not None], 'ATTENTION', trend)
        pr_trend = dimensions[name]['duration_trends']['pull_requests']
        pr_relative = pr_trend['relative']
        if name == 'delivery' and pr_relative is not None and Fraction(pr_relative['numerator'], pr_relative['denominator']) >= Fraction(1, 4):
            existing = next((f for f in findings if f['rule_id'] == 'ER06' and f['scope'].get('dimension') == name), None)
            refs = prs['merged_refs'] + previous['pull_requests']['merged_refs'] + (existing['references'] if existing else [])
            if existing:
                findings.remove(existing)
            add('ER06', refs, 'ATTENTION', {'work_items': trend, 'pull_requests': pr_trend})
        bm = current['builds']
        fraction = bm['failure_fraction']
        if name == 'delivery' and bm['availability'] == 'OBSERVED' and bm['known_terminal'] >= 4 and fraction is not None:
            rate = Fraction(fraction['numerator'], fraction['denominator'])
            if rate >= Fraction(1, 4):
                add('ER09', bm['references'], 'HIGH' if rate >= Fraction(1, 2) else 'ATTENTION', fraction)
    findings.sort(key=lambda f: ({'HIGH': 0, 'ATTENTION': 1, 'INFO': 2}[f['severity']], f['rule_id'], canonical(f['scope']), f['id']))
    if len(findings) > 10000 or sum(len(f['references']) for f in findings) > 40000:
        raise ValueError('invalid engineering finding limit')
    assessment = {'schema_version': 'engineering-review-1', 'assessment_id': assessment_id, 'system': system,
                  'assessment_as_of': public(windows.assessment_as_of),
                  'policy': {'rule_version': 'engineering-review-rules-1', 'duration_unit': 'microseconds',
                             'aged_days': 30, 'high_age_days': 90, 'comparison_minimum_sample': 4,
                             'median_minimum': 1, 'p75_minimum': 4, 'p90_minimum': 10},
                  'windows': public(windows), 'dimension_results': dimensions, 'evidence_sources': sources,
                  'component_results': [components[k] for k in sorted(components)],
                  'completeness': [{'dimension': name, 'availability': 'UNAVAILABLE', 'reason': 'MISSING_INPUT'}
                                   if 'current' not in dimension else
                                   {'dimension': name, 'capability': dimension['current']['capability'],
                                    'collection_status': dimension['current']['collection_status'],
                                    'populations': dimension['current']['population_coverage']}
                                   for name, dimension in dimensions.items() if name != 'legacy'],
                  'investigations': [{'finding_id': f['id'], 'template_id': f['investigation'],
                                      'text': {'ER01': 'Inspect concentration support and available handover documentation.',
                                               'ER02': 'Inspect qualifying and excluded review interactions and source scope.',
                                               'ER03': 'Inspect explicit associations, missing hops and source mapping coverage.',
                                               'ER04': 'Inspect exact test versions, targets and historical observations.',
                                               'ER05': 'Inspect oldest supporting work and PR records and selection limits.',
                                               'ER06': 'Inspect duration samples, policies, history coverage and changed work mix.',
                                               'ER07': 'Inspect explicit defect lifecycles, priority observations and mappings.',
                                               'ER08': 'Inspect opened and completed defect populations, reopens and removals.',
                                               'ER09': 'Inspect qualifying build runs, results and pipeline scope.'}[f['rule_id']]}
                                     for f in findings],
                  'findings': findings, 'limitations': ['OFFLINE_DECLARED', 'DEPLOYMENT_DEFERRED_BY_DESIGN'] + legacy_limitations}
    result = {'assessment': assessment, 'evidence': evidence}
    if len(canonical(result).encode()) > 32 * 1024 * 1024:
        raise ValueError('invalid engineering output size')
    return result


def compose(*, assessment_id: str, system: str, windows: Windows,
            delivery: dict[str, Any] | None = None, quality: dict[str, Any] | None = None,
            ecl_report: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        return _compose(assessment_id=assessment_id, system=system, windows=windows,
                        delivery=delivery, quality=quality, ecl_report=ecl_report)
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError, UnicodeError, RecursionError):
        raise ValueError('invalid engineering evidence') from None


def package_loads(raw: str | bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    encoded = raw.encode('utf-8') if isinstance(raw, str) else raw
    if len(encoded) > 32 * 1024 * 1024:
        raise ValueError()
    parsed = json.loads(encoded.decode('utf-8'), object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    safe_json(parsed)
    return parsed


def import_package(raw: str | bytes) -> dict[str, Any]:
    try:
        package = exact(package_loads(raw), {'assessment', 'evidence'})
        a = package['assessment']
        w = a['windows']
        windows = Windows(Window(instant(w['current']['start']), instant(w['current']['end'])),
                          Window(instant(w['previous']['start']), instant(w['previous']['end'])),
                          instant(w['assessment_as_of']))
        evidence = package['evidence']
        if not isinstance(evidence, dict) or set(evidence) - {'delivery', 'quality', 'ecl_report'}:
            raise ValueError()
        rebuilt = compose(assessment_id=a['assessment_id'], system=a['system'], windows=windows,
                          delivery=evidence.get('delivery'), quality=evidence.get('quality'), ecl_report=evidence.get('ecl_report'))
        if canonical(package) != canonical(rebuilt):
            raise ValueError()
        return rebuilt
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError, UnicodeError, RecursionError):
        raise ValueError('invalid engineering package') from None
