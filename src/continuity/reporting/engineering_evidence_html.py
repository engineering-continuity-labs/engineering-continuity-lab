"""Readable presentation of accepted evidence; no analysis or source inference."""
from hashlib import sha256
from typing import Any

from continuity.reporting.portable import canonical
from continuity.reporting.engineering_html import text, number, table, display_fraction


def fields(value: Any, prefix: str = '') -> list[tuple[str, Any]]:
    """Exact technical fields as labeled rows, never JSON text or inferred links."""
    if isinstance(value, dict):
        return [row for key, child in value.items() for row in fields(child, (prefix + ' / ' if prefix else '') + key.replace('_', ' '))]
    if isinstance(value, list):
        return [row for index, child in enumerate(value) for row in fields(child, f'{prefix} / {index + 1}')]
    return [(prefix or 'Value', value)]


def disclosure(title: str, body: str, *, technical: bool = False) -> str:
    return '<details' + (' class="technical"' if technical else '') + '><summary>' + text(title) + '</summary>' + body + '</details>'


def reference(value: Any) -> str:
    if isinstance(value, list) and len(value) == 5 and all(isinstance(v, str) for v in value):
        return text(value[0].replace('_', ' ').title() + ' ' + value[4])
    if isinstance(value, dict) and 'identifier' in value:
        label = value.get('kind', 'Record').replace('_', ' ').title() + ' ' + value['identifier']
        if value.get('version'):
            label += ' @' + value['version']
        return text(label)
    return 'Supporting observation'


def exact_reference(value: Any) -> str:
    if isinstance(value, list) and len(value) == 5 and all(isinstance(v, str) for v in value):
        return table(list(zip(('Kind', 'Provider', 'Instance', 'Scope', 'Identifier'), value)))
    return table(fields(value))


def duration(value: Any, *, minutes: bool = False) -> str:
    if value is None:
        return 'Unavailable'
    rational = value if isinstance(value, dict) else {'numerator': value, 'denominator': 1}
    return display_fraction(rational, 60000000 if minutes else 86400000000, ' minutes' if minutes else ' days')


def continuity(component: dict[str, Any]) -> str:
    return table([('Risk · historical', component.get('risk')), ('Historical contributors', len(component.get('contributors', []))),
                  ('Concentration', component.get('concentration'))]) + '<p>Historic Git activity supports this observation. Git activity is a proxy for engineering knowledge.</p>'


def reviews(component: dict[str, Any]) -> str:
    coverage = component.get('coverage')
    return table([('Mapped PRs', component.get('mapped_pull_requests')), ('PRs with qualifying review evidence', component.get('covered_pull_requests')),
                  ('Coverage', None if coverage is None else f'{coverage * 100:.1f}%'), ('Evidence status', component.get('coverage_status')),
                  ('Reviewer concentration', component.get('concentration')), ('Concentration band', component.get('risk'))]) + '<h4>Unreviewed PRs</h4><p>' + text(', '.join(component.get('unreviewed_pull_requests', [])) or 'None listed; inspect completeness') + '</p><h4>Excluded interactions</h4>' + table([(k.replace('_', ' ').title(), v) for k, v in component.get('excluded_reasons', {}).items()])


def trace_view(legacy: dict[str, Any]) -> str:
    result = legacy.get('traceability_evidence', {}).get('result')
    if result is None:
        return '<p>Traceability evidence unavailable.</p>'
    body = '<h4>Observed implementation paths</h4>'
    for path in result.get('paths', []):
        body += '<p>' + ' → '.join(reference(n) for n in path['nodes']) + ' · ' + text(path['status']) + '</p>'
        body += disclosure('Exact path identities and support', table(fields({'nodes': path['nodes'], 'supports': path.get('supports'), 'boundaries': path.get('boundaries'), 'rule_version': path.get('rule_version')})), technical=True)
    body += '<h4>Observed gaps and uncertainty</h4>'
    for gap in result.get('gaps', []):
        body += '<p>' + reference(gap['endpoint']) + ' → ' + text(gap['relationship'].replace('_', ' ')) + ' · ' + text(gap['status']) + ' · ' + text(gap['reason'].replace('_', ' ').lower()) + '</p>'
    body += disclosure('Technical trace collection, selections and exact gap references', table(fields({'gaps': result.get('gaps'), 'collection_status': legacy['traceability_evidence']['collection'].get('status'), 'populations': legacy['traceability_evidence']['collection'].get('populations'), 'lookups': legacy['traceability_evidence']['collection'].get('lookups'), 'boundaries': legacy['traceability_evidence']['collection'].get('boundaries')})), technical=True)
    return body


def verification_view(legacy: dict[str, Any]) -> str:
    result = legacy.get('verification_evidence', {}).get('result')
    if result is None:
        return '<p>Requirement / verification evidence unavailable.</p>'
    body = '<h4>Requirement linkage</h4>'
    for req in result.get('requirements', []):
        body += '<h4>' + reference(req['reference']) + '</h4>' + table([(label, req.get(key)) for label, key in [('Implementation', 'implementation'), ('Declared tests', 'tests'), ('Architecture', 'architecture')]])
    body += '<h4>Historical test observations</h4>'
    for run in result.get('runs', []):
        body += '<h4>' + reference(run['test']) + '</h4>' + table([('Observation', run.get('outcome')), ('Observed at', run.get('observed_at')), ('Target revision', run.get('target', {}).get('revision')),
                  ('Qualification', 'Qualified against accepted test version and target' if run.get('qualified') else 'Unqualified'), ('Reason', run.get('reason'))])
        body += disclosure('Exact test, observation and target identities', table(fields(run)), technical=True)
    for path in result.get('paths', []):
        association = path.get('association', {})
        code_path = path.get('code_path', {})
        body += '<p>' + reference(association.get('source')) + ' → ' + ' → '.join(reference(n) for n in code_path.get('nodes', [])) + ' · ' + text(code_path.get('status', 'Unavailable')) + '</p>'
        for gap in code_path.get('gaps', []):
            body += '<p>Path uncertainty: ' + text(gap.get('status', 'Unavailable')) + ' · ' + text(gap.get('reason', 'Unavailable')) + '</p>'
        body += disclosure('Exact requirement path qualification and support', table(fields(path)), technical=True)
    body += '<p>PASS is a historical observation and does not prove requirement correctness.</p>'
    body += disclosure('Technical associations, gaps, outcomes and qualification limits', table(fields({k: result.get(k) for k in ('associations', 'gaps', 'outcomes', 'collection_status', 'snapshot_valid', 'diagnostics', 'dropped', 'rule_version')})), technical=True)
    return body


def population_view(dimension: dict[str, Any], population: str, sample: str, *, minutes: bool = False) -> str:
    body = ''
    for window in ('current', 'previous'):
        selected = dimension.get(window, {})
        values = selected.get(population, {})
        body += '<h4>' + window.title() + '</h4>' + table([('Evidence status', values.get('availability')), ('Collection', selected.get('population_coverage', {}).get(population, {}).get('status')),
                    ('Qualified duration samples', values.get(sample, {}).get('count')), ('Median', duration(values.get(sample, {}).get('median'), minutes=minutes)),
                    ('Excluded conflicting identities', len(values['conflicts']) if 'conflicts' in values else None)])
        for row in values.get('results', []):
            body += '<p>' + reference(row['reference']) + ' · duration: ' + text(duration(row.get('duration_microseconds'))) + ' · open age: ' + text(duration(row.get('age_microseconds'))) + ' · ' + text(row.get('inventory')) + '</p>'
        if population == 'pull_requests':
            for ref, age in values.get('open_ages', []):
                body += '<p>' + reference(ref) + ' · open age: ' + text(duration(age)) + '</p>'
        body += disclosure('Technical samples, exclusions and exact identities', table(fields(values)), technical=True)
    return body


RULE_EXPLANATIONS = {
    'ER01': 'Historical concentration meets the accepted high-attention band.',
    'ER02': 'Qualifying review coverage is below 50%, with at least four mapped PRs and complete evidence.',
    'ER03': 'At least one explicit qualified missing association was observed.',
    'ER04': 'At least one selected test has no qualified observation under the accepted completeness boundary.',
    'ER05': 'At least one qualifying open work item or PR is aged at least 30 days; 90 days triggers high attention.',
    'ER06': 'A qualified current median is at least 25% greater than the previous median, with at least four complete samples in both periods.',
    'ER07': 'At least one qualifying unresolved defect is aged at least 30 days; 90 days triggers high attention.',
    'ER08': 'Observed openings exceed distinct resolutions in complete comparable defect evidence; this is not backlog growth.',
    'ER09': 'At least 25% of four or more qualified known terminal builds failed; 50% triggers high attention.'}


def finding_observation(finding: dict[str, Any], dims: dict[str, Any]) -> str:
    rule, value = finding['rule_id'], finding['value']
    if rule == 'ER06':
        result = ''
        delivery = dims.get('delivery', {})
        for population, sample, label in (('work_items', 'durations', 'Work-item cycle'), ('pull_requests', 'lead', 'PR lead')):
            comparison = value.get(population, {})
            result += '<h5>' + label + '</h5>'
            samples = {w: delivery.get(w, {}).get(population, {}).get(sample, {}) for w in ('current', 'previous')}
            result += table([('Current median', duration(samples['current'].get('median'))), ('Previous median', duration(samples['previous'].get('median'))),
                             ('Qualified current samples', samples['current'].get('count')), ('Qualified previous samples', samples['previous'].get('count')),
                             ('Comparison', 'Qualified' if comparison.get('absolute') is not None else 'Unavailable'),
                             ('Absolute change', duration(comparison.get('absolute')))])
        return result
    if rule == 'ER09':
        return table([('Observed failure fraction', display_fraction({'numerator': value['numerator'] * 100, 'denominator': value['denominator']}, suffix='%'))])
    return table([('Observed value', value)])


def render_evidence(package: dict[str, Any], names: dict[str, str], findings: list[dict[str, Any]], investigations: dict[str, str], source_summary: list[tuple[str, str]], component_names: list[str], historical: dict[str, Any], review_rows: dict[str, Any], qualified_reviews: dict[str, Any], mapped_groups: dict[str, Any]) -> str:
    a, evidence = package['assessment'], package['evidence']
    dims, legacy = a['dimension_results'], evidence.get('ecl_report', {})
    body = '<p>Human evidence explains the same validated machine-readable package. Observations support investigation, not cause, readiness or employee performance.</p><h3>Evidence Sources</h3>'
    body += table([(s['role'].replace('_', ' ').title(), s['alias'] + ' · reference ' + s['retrieved_at']) for s in a['evidence_sources']])
    body += '<h3>Assessment Period</h3>' + table([('Current period · UTC, end excluded', a['windows']['current']['start'] + ' → ' + a['windows']['current']['end']), ('Previous period · UTC, end excluded', a['windows']['previous']['start'] + ' → ' + a['windows']['previous']['end']), ('Assessment as of', a['assessment_as_of'])])
    body += '<h3>Evidence Completeness</h3>' + table(source_summary)
    for role in ('delivery', 'quality'):
        source = evidence.get(role)
        body += '<h4>' + ('Delivery' if role == 'delivery' else 'Defect Evidence') + '</h4>'
        if source is None:
            body += '<p>Unavailable: no source supplied.</p>'
        else:
            body += table([('Selected work-item observations · all supplied windows', len(source['work_items'])), ('Selected PR observations · all supplied windows', len(source['pull_requests'])), ('Selected build observations · all supplied windows', len(source['builds']))])
            body += disclosure('Technical source and completeness', table(fields({k: source.get(k) for k in ('alias', 'retrieved_at', 'capability', 'status', 'populations', 'categories', 'selected_types', 'mapping_complete', 'mapping_revision', 'mappings', 'policy_fingerprint', 'selection_fingerprint')})), technical=True)
    body += disclosure('Technical completeness and source boundaries', table(fields({'sources': a['evidence_sources'], 'completeness': a['completeness'], 'policy': a['policy']})), technical=True)
    body += '<div id="all-findings"><h3>Finding evidence and suggested investigation</h3>'
    for finding in findings:
        rule = finding['rule_id']
        body += f'<article id="finding-{text(finding["id"])}"><h4>{text(finding["severity"])} · {text(names[rule])}</h4>'
        body += table([('Affected scope', finding['scope'].get('legacy', finding['scope'].get('dimension', a['system']))), ('Qualified supporting records', finding.get('sample_size')), ('Source time · historical where declared', finding['scope'].get('source_as_of'))])
        body += finding_observation(finding, dims) + '<p>Finding method: ' + text(RULE_EXPLANATIONS[rule]) + '</p>'
        body += '<p>Suggested investigation: ' + text(investigations.get(finding['id'], 'Inspect evidence and limitations.')) + '</p>'
        body += '<p>Limits: ' + text(', '.join(finding['limitations']) or 'Observed evidence does not establish cause or individual productivity.') + '</p>'
        body += disclosure('Technical method', '<p>Method: ' + text(rule) + ' · ' + text(finding['rule_version']) + '</p>' + table(fields({k: finding.get(k) for k in ('id', 'rule_id', 'rule_version', 'scope', 'threshold', 'value', 'sample_size', 'policy_fingerprint', 'limitations')})), technical=True)
        body += disclosure('View exact supporting evidence references', ''.join(exact_reference(r) for r in finding['references']) or '<p>No exact reference supplied.</p>', technical=True)
        body += '</article>'
    body += '</div><h3>Component evidence</h3>'
    for index, name in enumerate(component_names):
        body += f'<div id="component-evidence-{index}"><h4>{text(name)}</h4>'
        body += continuity(historical[name]) if name in historical else '<p>Continuity unavailable.</p>'
        body += reviews(qualified_reviews[name]) if name in qualified_reviews else '<p>Review evidence unavailable for this component binding.</p>'
        body += disclosure('Technical component sources and binding', table(fields({'historical_source_as_of': legacy.get('as_of'), 'git_component_depth': legacy.get('configuration', {}).get('component_depth'), 'review_component_depth': legacy.get('review_evidence', {}).get('component_depth'), 'typed_component_observations': mapped_groups.get(name)})), technical=True) + '</div>'
    body += '<h3>Independent review evidence</h3><p>Original review component depth: ' + number(legacy.get('review_evidence', {}).get('component_depth')) + '. These independent rows do not establish a shared Git component binding.</p>'
    for name, row in review_rows.items():
        body += disclosure('Review scope: ' + name, reviews(row))
    body += '<div id="legacy-evidence"><h3>Traceability evidence</h3>' + trace_view(legacy) + '<h3>Requirement / Verification evidence</h3>' + verification_view(legacy) + '</div>'
    body += '<h3>Delivery evidence and duration samples</h3>' + population_view(dims.get('delivery', {}), 'work_items', 'durations') + '<h3>PR evidence</h3>' + population_view(dims.get('delivery', {}), 'pull_requests', 'lead')
    body += '<h3>Quality / Defect Evidence</h3>' + population_view(dims.get('quality', {}), 'work_items', 'durations') + '<h3>Build Evidence</h3>' + population_view(dims.get('delivery', {}), 'builds', 'durations', minutes=True)
    body += '<h3>Evidence package</h3>' + table([('Schema', a['schema_version']), ('Assessment ID', a['assessment_id']), ('Canonical package', 'Available · embedded and downloadable'), ('Integrity digest · SHA256 of canonical package UTF8 bytes', sha256(canonical(package).encode('utf-8')).hexdigest()), ('Reproducible', 'Deterministic validation/recomputation on reimport; not an authenticity certificate')])
    body += '<p>Download evidence package (.json) using the header control. Machine-readable evidence used to reproduce and audit this review.</p>'
    body += disclosure('Technical assessment limitations and schema', table(fields({'schema': a['schema_version'], 'limitations': a['limitations']})), technical=True)
    return body
