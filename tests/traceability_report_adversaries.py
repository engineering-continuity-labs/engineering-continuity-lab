"""Project-owned adversarial mutations shared by Python and browser QA."""
from copy import deepcopy
from traceability_report_fixture import synthetic_v3_report


def adversarial_reports():
    base = synthetic_v3_report()
    cases = {}

    def add(name, mutate):
        value = deepcopy(base)
        mutate(value['traceability_evidence'])
        cases[name] = value

    add('source-alias', lambda t: t['collection']['populations']['commits'][0].update(provider='secret'))
    add('source-algorithm', lambda t: t['collection']['work_items'][0]['reference'].update(algorithm='sha256'))
    add('source-field-type', lambda t: t['collection']['populations']['commits'][0].update(provider=7))
    add('unsafe-path', lambda t: t['collection']['populations']['changed_paths'][0].update(identifier='../private'))
    add('bad-hash', lambda t: t['collection']['populations']['commits'][0].update(identifier='abcdef'))
    add('lookup-boundary', lambda t: t['collection']['lookups'][0].update(boundary='ghost'))
    add('lookup-endpoint-kind', lambda t: t['collection']['lookups'][0].update(
        endpoint=t['collection']['populations']['commits'][0], relationship='WI_PR', population=None))
    add('lookup-scope', lambda t: next(l for l in t['collection']['lookups'] if l['endpoint'] and l['endpoint']['kind']=='WORK_ITEM')['endpoint'].update(instance='other'))
    for field in ['boundaries', 'work_items', 'observed_links', 'lookups']:
        add('duplicate-'+field, lambda t, f=field: t['collection'][f].append(deepcopy(t['collection'][f][0])))
    for field in ['work_items', 'observed_links', 'lookups']:
        add('reverse-'+field, lambda t, f=field: t['collection'][f].reverse())
    for field in ['pull_requests', 'merged_pull_requests', 'commits', 'changed_paths']:
        add('duplicate-'+field, lambda t, f=field: t['collection']['populations'][f].append(deepcopy(t['collection']['populations'][f][0])))
        add('reverse-'+field, lambda t, f=field: t['collection']['populations'][f].reverse())
    for field in ['derived_links', 'paths', 'gaps', 'artifacts', 'metrics']:
        add('reverse-result-'+field, lambda t, f=field: t['result'][f].reverse())
        add('duplicate-result-'+field, lambda t, f=field: t['result'][f].append(deepcopy(t['result'][f][0])))
    add('shortcut-support-order', lambda t: t['result']['derived_links'][0]['supports'].reverse())
    add('unresolved-support', lambda t: t['result']['paths'][0]['supports'][0]['source'].update(identifier='unknown'))
    add('path-support-order', lambda t: next(p for p in t['result']['paths'] if p['status']=='VERIFIED')['supports'].reverse())
    add('path-cycle', lambda t: t['result']['paths'][0]['nodes'].append(deepcopy(t['result']['paths'][0]['nodes'][0])))
    add('fake-verified', lambda t: next(p for p in t['result']['paths'] if p['status']=='PARTIAL').update(status='VERIFIED'))
    add('derived-as-direct', lambda t: t['collection']['observed_links'].append(deepcopy(t['result']['derived_links'][0])))
    for capability in ['UNSUPPORTED', 'UNKNOWN']:
        def missing(t, capability=capability):
            gap = next(g for g in t['result']['gaps'] if g['status']=='MISSING')
            lookup = next(l for l in t['collection']['lookups'] if l['endpoint']==gap['endpoint'] and l['relationship']==gap['relationship'] and l['direction']==gap['direction'])
            lookup['capability'] = capability
        add('unsupported-missing-'+capability, missing)
    for timestamp in ['2026-02-30T00:00:00Z', '2025-02-29T00:00:00Z', '2026-01-01T24:00:00Z',
                      '2026-01-01T00:60:00Z', '2026-01-01T00:00:60Z', '20260101T000000+0000',
                      '2026-01-01 00:00:00+00:00', '2026-01-01T00:00:00+00:99',
                      '2026-01-01T00:00:00.1234567Z', '0000-01-01T00:00:00Z']:
        add('timestamp-'+timestamp, lambda t, v=timestamp: t['collection']['boundaries'][0].update(collected_at=v))
    # Each string-bearing field of each wire record category, not just one query field.
    samples = [(['collection', 'boundaries', 0], base['traceability_evidence']['collection']['boundaries'][0]),
               (['collection', 'component_strategy'], base['traceability_evidence']['collection']['component_strategy']),
               (['collection', 'work_items', 0, 'reference'], base['traceability_evidence']['collection']['work_items'][0]['reference']),
               (['collection', 'work_items', 0, 'provenance'], base['traceability_evidence']['collection']['work_items'][0]['provenance']),
               (['collection', 'observed_links', 0, 'source'], base['traceability_evidence']['collection']['observed_links'][0]['source']),
               (['collection', 'observed_links', 0, 'target'], base['traceability_evidence']['collection']['observed_links'][0]['target']),
               (['collection', 'observed_links', 0, 'observations', 0], base['traceability_evidence']['collection']['observed_links'][0]['observations'][0]),
               (['collection', 'lookups', 0], base['traceability_evidence']['collection']['lookups'][0])]
    for path, sample in samples:
        for field, value in sample.items():
            if isinstance(value, str):
                def inject(t, path=path, field=field):
                    target = t
                    for part in path:
                        target = target[part]
                    target[field] = 'ghp_'+'A'*36
                add('credential-'+'/'.join(map(str, path))+'/'+field, inject)
    for sentinel in ['github_pat_SYNTHETIC', 'PAT_SENTINEL', 'Authorization=Bearer.SYNTHETIC',
                     'password=SYNTHETIC', 'cookie=SYNTHETIC', '/Users/synthetic/private',
                     'tmp/synthetic/private', 'https://user:SYNTHETIC@example.invalid', 'file:///tmp/SYNTHETIC', '\ud800']:
        add('unsafe-provenance-'+repr(sentinel), lambda t, v=sentinel: t['collection']['boundaries'][0].update(snapshot=v))
    add('future-schema', lambda t: t.update(schema_version='2.0'))
    add('extra-field', lambda t: t['collection'].update(raw_response='SYNTHETIC'))
    for field, value in [('numerator', -1), ('numerator', 999), ('unknown_count', -1), ('excluded_count', -1),
                         ('numerator', True), ('value', .123), ('value', None), ('denominator', 0)]:
        add('metric-'+field+'-'+str(value), lambda t, f=field, v=value: t['result']['metrics'][0].update({f:v}))
    return cases


def additional_valid_reports():
    """Derived edge fixtures; all expected outputs still come from actual evidence."""
    from dataclasses import replace
    from datetime import datetime, timezone
    from continuity.analysis.traceability import derive
    from continuity.domain.traceability import TraceDiagnostic, GapReason, TraceabilityCapability
    from continuity.reporting.traceability import with_traceability
    from continuity.traceability_providers.synthetic import base_fixture
    git = synthetic_v3_report()
    git.pop('traceability_evidence')
    evidence = base_fixture()
    reports = {}
    reports['UNKNOWN'] = with_traceability(git, derive(replace(evidence, lookups=tuple(replace(l, capability=TraceabilityCapability.UNKNOWN) for l in evidence.lookups))))
    diagnostic_evidence = replace(evidence, diagnostics=(TraceDiagnostic(GapReason.INVALID_OBSERVATION), TraceDiagnostic(GapReason.UNSUPPORTED_RELATION)))
    reports['DIAGNOSTICS'] = with_traceability(git, derive(diagnostic_evidence))
    start = datetime(2026, 1, 1, 0, 0, 0, 1, timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    boundary = replace(evidence.boundaries[0], start=start, end=end, time_field='merged_at')
    for name, second in [('COMPATIBLE_BOUNDARIES', boundary), ('MICROSECOND_BOUNDARIES', replace(boundary, start=start.replace(microsecond=2)))]:
        second = replace(second, identifier='synthetic-other')
        reports[name] = with_traceability(git, derive(replace(evidence, boundaries=(boundary, second))))
    refs = {evidence.changed_paths[i]:replace(evidence.changed_paths[i], identifier=path) for i, path in enumerate(['src/payments/😀.py', 'src/payments/\ue000.py'])}
    def ref(value):
        return refs.get(value, value)
    unicode_evidence = replace(evidence, changed_paths=tuple(ref(p) for p in evidence.changed_paths),
        links=tuple(replace(l, source=ref(l.source), target=ref(l.target)) for l in evidence.links),
        lookups=tuple(replace(l, endpoint=ref(l.endpoint)) if l.endpoint else l for l in evidence.lookups))
    reports['UNICODE'] = with_traceability(git, derive(unicode_evidence))
    mismatched_lookup = next(l for l in evidence.lookups if l.endpoint and l.endpoint.kind.value=='WORK_ITEM')
    scoped_evidence = replace(evidence, lookups=tuple(replace(l, endpoint=replace(l.endpoint, instance='another-instance')) if l==mismatched_lookup else l for l in evidence.lookups))
    reports['INCOMPATIBLE_LOOKUP'] = with_traceability(git, derive(scoped_evidence))
    approved_refs = {evidence.changed_paths[i]:replace(evidence.changed_paths[i], identifier=path) for i, path in enumerate(['src/payments/token-cache.py', 'src/payments/password-utils.py'])}
    approved = replace(evidence, changed_paths=tuple(approved_refs.get(p,p) for p in evidence.changed_paths), links=tuple(replace(l, target=approved_refs.get(l.target,l.target)) for l in evidence.links), lookups=tuple(replace(l, endpoint=approved_refs.get(l.endpoint,l.endpoint)) if l.endpoint else l for l in evidence.lookups))
    reports['APPROVED_PATH_NAMES'] = with_traceability(git, derive(approved))
    long_ref = replace(evidence.changed_paths[0], identifier='src/payments/'+'😀'*600+'.py')
    long_evidence = replace(evidence, changed_paths=(long_ref,*evidence.changed_paths[1:]), links=tuple(replace(l,target=long_ref) if l.target==evidence.changed_paths[0] else l for l in evidence.links), lookups=tuple(replace(l,endpoint=long_ref) if l.endpoint==evidence.changed_paths[0] else l for l in evidence.lookups))
    reports['LONG_UNICODE_PATH'] = with_traceability(git, derive(long_evidence))
    z_report = deepcopy(reports['UNKNOWN'])
    def z_times(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key=='observed_at':
                    value[key] = child.replace('+00:00','Z')
                else:
                    z_times(child)
        elif isinstance(value,list):
            for child in value:
                z_times(child)
    z_times(z_report)
    reports['ISO_Z'] = z_report
    reports['LEAP_DAY'] = with_traceability(git, derive(replace(evidence, boundaries=(replace(evidence.boundaries[0], collected_at=datetime(2024,2,29,23,59,59,123456,timezone.utc)),))))
    return reports


def normalization_adversaries():
    """Mutations of richer fixtures exposing canonical/normalization discrepancies."""
    cases = {}
    valid = additional_valid_reports()
    for field in ['boundaries']:
        value = deepcopy(valid['COMPATIBLE_BOUNDARIES'])
        value['traceability_evidence']['collection'][field].reverse()
        cases['reverse-'+field] = value
    for action in ['reverse', 'duplicate', 'complete', 'lookup']:
        value = deepcopy(valid['DIAGNOSTICS'])
        collection = value['traceability_evidence']['collection']
        if action=='reverse':
            collection['diagnostics'].reverse()
        elif action=='duplicate':
            collection['diagnostics'].append(deepcopy(collection['diagnostics'][0]))
        elif action=='complete':
            collection['status'] = 'COMPLETE'
        else:
            collection['lookups'][0]['status'] = 'COMPLETE'
        cases['diagnostic-'+action] = value
    value = deepcopy(valid['MICROSECOND_BOUNDARIES'])
    value['traceability_evidence']['collection']['boundaries'][1]['start'] = value['traceability_evidence']['collection']['boundaries'][0]['start']
    cases['contradictory-microsecond-join'] = value
    return cases
