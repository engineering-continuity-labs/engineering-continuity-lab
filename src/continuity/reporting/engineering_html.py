"""Self-contained manager presentation of a recomputed offline assessment."""
from html import escape
from fractions import Fraction
from base64 import b64encode
from typing import Any

from continuity.reporting.engineering_review import import_package
from continuity.reporting.portable import canonical

SECTIONS = ('Executive Summary', 'Components', 'Engineering Details', 'Evidence & Methodology')
NAVIGATION_LABELS = ('Review', 'Components', 'Engineering Details', 'Evidence')

CSS = '''
:root{color-scheme:light;--navy:#10283d;--ink:#142f3a;--muted:#627586;--line:#dce5eb;--surface:#fff;--canvas:#f4f7fa;--teal:#15847e;--red:#b8344f;--amber:#a96813;--gray:#6c7782}
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.report-shell{display:grid;grid-template-columns:238px minmax(0,1180px);max-width:1500px;margin:auto;min-height:100vh}.report-nav{background:var(--navy);color:#e8f0f6;padding:30px 22px;position:sticky;top:0;height:100vh}.report-nav .eyebrow{color:#75d2c8}.report-nav strong{display:block;font-size:1.1rem;margin:8px 0 26px;overflow-wrap:anywhere}.report-nav nav{display:grid;gap:4px}.report-nav a{color:#d7e3ed;padding:10px 12px;border-radius:7px;text-decoration:none}.report-nav a:hover,.report-nav a:focus-visible{background:#1d405d;color:#fff}main{max-width:1180px;background:var(--surface);padding:30px 48px 56px;box-shadow:0 0 40px #10283d12}header{border-bottom:1px solid var(--line);padding-bottom:18px}
h1{font-size:clamp(2.15rem,3.5vw,3rem);line-height:1.06;letter-spacing:-.035em;margin:5px 0 6px}h2{font-size:1.55rem;letter-spacing:-.02em;margin-top:0}h3{font-size:.92rem;letter-spacing:.01em;margin-top:0;text-transform:uppercase}h4{font-size:.82rem;margin:16px 0 0;color:var(--muted)}
.eyebrow{letter-spacing:.14em;font-size:.72rem;font-weight:800;color:var(--teal);margin:0}.muted{color:var(--muted)}.review-subtitle{font-size:1.08rem;margin:8px 0;max-width:760px}.system-name{font-size:1.12rem;font-weight:700;margin:0 0 6px}.source-label{font-size:.94rem;margin:8px 0 0;color:var(--ink)}.actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px}.actions a,button{background:#fff;border:1px solid var(--line);padding:9px 12px;border-radius:7px;color:var(--ink);font:inherit}.actions a{color:var(--teal);font-weight:700}
a{color:var(--teal)}a:focus-visible,summary:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #6dcfc5;outline-offset:3px}
section{background:var(--surface);border:1px solid var(--line);border-radius:12px;margin:22px 0;padding:28px;scroll-margin-top:16px}.executive-summary{border:0;padding:20px 0 28px;margin-top:0}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.card{padding:18px;background:#f8fafc;border:1px solid var(--line);border-radius:10px;min-height:154px}.card h3{color:var(--muted)}.card p{margin:.45rem 0}.card p:first-of-type{font-size:1.05rem;font-weight:700;color:var(--ink)}
.badge{display:inline-block;font-size:.72rem;letter-spacing:.05em;font-weight:800;padding:5px 8px;border-radius:5px;background:#e3f5f1;color:#076b65}.assessment-window{font-size:.9rem;color:var(--muted)}
details{border:1px solid var(--line);border-radius:9px;padding:14px;margin:12px 0;background:#fff}summary{cursor:pointer;font-weight:700}.component-detail{border-left:4px solid var(--teal)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem;background:#f5f8f8;padding:14px}table{width:100%;border-collapse:collapse}.component-search{width:min(100%,420px);padding:10px 12px;border:1px solid var(--line);border-radius:7px;margin:0 0 12px;color:var(--ink);font:inherit}
th,td{text-align:left;padding:11px 10px;border-bottom:1px solid var(--line);vertical-align:top}.table{overflow-x:auto}.table th{font-size:.78rem;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.finding-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:0;list-style:none;margin:12px 0}.finding-list li{margin:0}.attention{border-left:4px solid var(--amber);padding:13px 15px;background:#fff8ed;border-radius:0 8px 8px 0}.attention-high{border-left-color:var(--red);background:#fff4f6}.attention strong{display:block}.attention a{font-size:.85rem;font-weight:700}footer{color:var(--muted);font-size:.85rem;margin:30px 0}
@media(max-width:960px){.report-shell{display:block}.report-nav{height:auto;position:static;padding:18px 20px}.report-nav strong{margin:4px 0 12px}.report-nav nav{display:flex;flex-wrap:wrap}.report-nav a{padding:7px 9px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}main{max-width:none;padding:28px 26px}}@media(max-width:600px){main{padding:24px 16px 34px}section{padding:20px}.executive-summary{padding:20px 0}.cards,.finding-list{grid-template-columns:1fr}h1{font-size:2.25rem}.card{min-height:0}.assessment-window{overflow-wrap:anywhere}.actions{align-items:flex-start}.actions a,button{max-width:100%}}
@media print{.technical{display:none!important}.report-nav{display:none!important}body{background:white}.report-shell{display:block}.executive-summary{padding:0}main{max-width:none;padding:0;box-shadow:none}.actions,button,script{display:none!important}section{break-inside:avoid;border-radius:0}details{break-inside:avoid}details> :not(summary){display:block!important}a{color:inherit}h2{break-after:avoid}}
'''

PRINT_SCRIPT = '''(()=>{let states=[];window.addEventListener('beforeprint',()=>{
states=Array.from(document.querySelectorAll('details:not(.technical)'),d=>[d,d.open]);
for(const[d]of states)d.open=true;});window.addEventListener('afterprint',()=>{
for(const[d,open]of states)d.open=open;states=[];});})();'''


def text(value: Any) -> str:
    return escape(str(value), quote=True)


def number(value: Any) -> str:
    return 'Unavailable' if value is None else text(value)


def table(rows: list[tuple[str, Any]]) -> str:
    return '<div class="table"><table><thead><tr><th>Evidence</th><th>Observed value</th></tr></thead><tbody>' + ''.join(
        f'<tr><th scope="row">{text(k)}</th><td>{number(v)}</td></tr>' for k, v in rows) + '</tbody></table></div>'


NAMES = {'ER01': 'Continuity concentration requires attention', 'ER02': 'Low review coverage',
         'ER03': 'Traceability gaps detected', 'ER04': 'Verification evidence gap',
         'ER05': 'Aging delivery items detected', 'ER06': 'Delivery duration increased',
         'ER07': 'Aged defect detected', 'ER08': 'Defect inflow exceeded resolutions',
         'ER09': 'Build failures require attention'}


def display_fraction(value: Any, divisor: int = 1, suffix: str = '', signed: bool = False) -> str:
    if value is None:
        return 'Unavailable'
    fraction = Fraction(value['numerator'], value['denominator']) / divisor
    formatted = f'{float(fraction):+,.1f}' if signed else f'{float(fraction):,.1f}'
    if fraction != 0 and formatted.lstrip('+-') == '0.0':
        sign = '-' if fraction < 0 else '+' if signed else ''
        return sign + '<0.1' + suffix
    return formatted + suffix


def render(package: dict[str, Any], *, synthetic: bool = False) -> str:
    """Present the accepted assessment; conversions never replace normative values."""
    if type(synthetic) is not bool:
        raise ValueError('invalid presentation provenance')
    validated = import_package(canonical(package))
    a, evidence = validated['assessment'], validated['evidence']
    legacy = evidence.get('ecl_report', {})
    dims = a['dimension_results']
    delivery = dims.get('delivery', {})
    quality = dims.get('quality', {})
    dc, qc = delivery.get('current', {}), quality.get('current', {})
    wi, pr, bugs, builds = dc.get('work_items', {}), dc.get('pull_requests', {}), qc.get('work_items', {}), dc.get('builds', {})
    findings = sorted(a['findings'], key=lambda f: (0 if f['severity'] == 'HIGH' else 1, f['rule_id'], f['id']))
    investigations = {i['finding_id']: i['text'] for i in a['investigations']}

    def median(sample: dict[str, Any], unit: str = 'days') -> str:
        return display_fraction(sample.get('median'), 86400000000 if unit == 'days' else 60000000, ' ' + unit)

    def percent(value: Any) -> str:
        return display_fraction(value, suffix='%') if value is None else display_fraction({'numerator': value['numerator'] * 100, 'denominator': value['denominator']}, suffix='%')

    def trend(dimension: dict[str, Any], population: str, sample: str, unit: str = 'days') -> str:
        now = dimension.get('current', {}).get(population, {}).get(sample, {})
        previous = dimension.get('previous', {}).get(population, {}).get(sample, {})
        comparison = dimension.get('duration_trends', {}).get(population, {})
        result = f'<p>Current: {median(now, unit)} · Previous: {median(previous, unit)}</p>'
        if comparison.get('absolute') is not None and comparison.get('reason') in (None, 'BASELINE_ZERO'):
            divisor = 86400000000 if unit == 'days' else 60000000
            absolute = display_fraction(comparison['absolute'], divisor, ' ' + unit, True)
            relative = comparison.get('relative')
            change = display_fraction({'numerator': relative['numerator'] * 100, 'denominator': relative['denominator']}, suffix='%', signed=True) if relative is not None else 'Relative change unavailable'
            result += f'<p>Observed change: {absolute} / {change}</p>'
        else:
            result += '<details><summary>Trend unavailable</summary><p>Comparable complete samples are required. Inspect the exact reason in Evidence &amp; Methodology.</p></details>'
        return result

    def card(label: str, value: str) -> str:
        return f'<div class="card"><h3>{text(label)}</h3>{value}</div>'

    def coverage(name: str) -> str:
        if name in ('delivery', 'quality'):
            current = dims.get(name, {}).get('current', {})
            if current.get('capability') != 'SUPPORTED' or current.get('collection_status') == 'FAILED':
                return 'Unavailable'
            statuses = [v.get('status') for v in current.get('population_coverage', {}).values() if v.get('capability') == 'SUPPORTED']
            if not statuses:
                return 'Unavailable'
            return 'Complete' if current.get('collection_status') == 'COMPLETE' and all(v == 'COMPLETE' for v in statuses) else 'Partial'
        if name not in legacy:
            return 'Unavailable'
        value = legacy[name]
        if name == 'components':
            return 'Available · historical'
        status = value.get('provenance', {}).get('status') if name == 'review_evidence' else value.get('result', {}).get('collection_status', value.get('collection', {}).get('status'))
        if name == 'traceability_evidence':
            status = value.get('collection', {}).get('status')
        return {'COMPLETE': 'Complete · historical', 'PARTIAL': 'Partial · historical', 'FAILED': 'Unavailable'}.get(status, 'Uncertain · historical')

    source_summary = [('Continuity', coverage('components')), ('Reviews', coverage('review_evidence')),
                      ('Traceability', coverage('traceability_evidence')), ('Verification', coverage('verification_evidence')),
                      ('Delivery', coverage('delivery')), ('Quality', coverage('quality')),
                      ('Builds', {'OBSERVED': 'Available', 'PARTIAL': 'Partial'}.get(builds.get('availability'), 'Unavailable')),
                      ('Deployment', 'Unavailable')]
    provenance = 'SYNTHETIC DEMO PROJECT · fictional Atlas Commerce example' if synthetic else 'OFFLINE DECLARED · source owner assertions'
    source_label = 'Synthetic demo data — Atlas Commerce (fictional)' if synthetic else 'Locally generated validated evidence package'
    window = a['windows']['current']
    snapshot = ''
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for finding in findings:
        groups.setdefault((finding['severity'], finding['rule_id']), []).append(finding)
    continuity_count = len([f for f in findings if f['rule_id'] == 'ER01']) if 'components' in legacy else None
    snapshot += '<h3>Executive indicators</h3><div class="cards">'
    snapshot += card('Continuity', f'<p>{number(continuity_count)} attention areas · historical</p>')
    snapshot += card('Delivery', trend(delivery, 'work_items', 'durations') + '<h4>PR flow</h4>' + trend(delivery, 'pull_requests', 'lead'))
    snapshot += card('Defects', f'<p>Opened: {number(bugs.get("opened"))} · Resolved: {number(bugs.get("completed"))}<br>Open: {number(bugs.get("open_inventory"))} · Aged ≥30d: {number(bugs.get("aged"))} · Reopened: {number(bugs.get("reopened"))}</p>')
    snapshot += card('Builds', f'<p>{number(builds.get("known_terminal"))} qualified terminal builds<br>Success: {percent(builds.get("success_fraction"))} · Failure: {percent(builds.get("failure_fraction"))}</p>')
    snapshot += '</div><p class="muted">Historical continuity, reviews, traceability and verification are from ' + text(legacy.get('as_of', 'Unavailable')) + '; they are not observations of the assessment period.</p><h3>What needs attention?</h3><ul class="finding-list">'
    attention_order = {'ER01': 0, 'ER06': 1, 'ER08': 2, 'ER03': 3, 'ER09': 4, 'ER05': 5, 'ER07': 6, 'ER02': 7, 'ER04': 8}
    for (severity, rule), group in sorted(groups.items(), key=lambda item: (attention_order.get(item[0][1], 99), item[0][0]))[:6]:
        label = NAMES[rule]
        detail = f'{len(group)} component observations' if rule == 'ER01' else f'{len(group)} supported observation(s)'
        if rule == 'ER03':
            detail = f'{group[0]["value"]} explicit evidence gaps'
        elif rule == 'ER05':
            detail = f'{group[0]["value"]} aged work items and PRs'
        elif rule == 'ER06':
            changes = []
            for population, population_label, sample in (('work_items', 'Work-item median', 'durations'), ('pull_requests', 'PR median', 'lead')):
                comparison = group[0]['value'].get(population, {})
                relative = comparison.get('relative')
                if relative is not None and Fraction(relative['numerator'], relative['denominator']) >= Fraction(1, 4):
                    changes.append(population_label + ': ' + median(delivery.get('previous', {}).get(population, {}).get(sample, {})) + ' → ' + median(dc.get(population, {}).get(sample, {})))
            detail = '; '.join(changes)
        elif rule == 'ER07':
            detail = f'{group[0]["value"]} aged unresolved defects'
        elif rule == 'ER08':
            detail = f'{bugs.get("opened")} opened; {bugs.get("completed")} resolved'
        elif rule == 'ER09':
            detail = percent(group[0]['value']) + ' of qualified builds failed'
        severity_class = ' attention-high' if severity == 'HIGH' else ''
        snapshot += f'<li class="attention{severity_class}"><strong>{text(severity)} · {text(label)}</strong>{text(detail)} <a href="#finding-{text(group[0]["id"])}">Inspect evidence</a></li>'
    snapshot += '</ul>'
    if not findings:
        snapshot += '<p>No eligible attention finding. Missing evidence does not establish absence of issues.</p>'
    snapshot += f'<a href="#all-findings">View all findings ({len(findings)})</a><h3>Evidence coverage</h3><p>' + ' · '.join(text(k) + ': ' + text(v) for k, v in source_summary) + '</p>'
    snapshot += '<p>Major unavailable evidence: ' + text(', '.join(k for k, v in source_summary if v == 'Unavailable') or 'None at source level; field limits remain inspectable') + '.</p>'

    historical = {c['component']: c for c in legacy.get('components', [])}
    review_rows = {c['component']: c for c in legacy.get('review_evidence', {}).get('components', [])}
    depth = legacy.get('configuration', {}).get('component_depth')
    review_depth = legacy.get('review_evidence', {}).get('component_depth')
    reviews = review_rows if type(depth) is int and depth == review_depth else {}
    mapped_groups: dict[str, list[dict[str, Any]]] = {}
    for row in a['component_results']:
        mapped_groups.setdefault(row['component_ref']['identifier'], []).append(row)
    # Ambiguous short identifiers cannot merge distinct typed component scopes.
    mapped = {name: rows[0] for name, rows in mapped_groups.items() if len(rows) == 1 and type(depth) is int and rows[0]['component_ref'].get('configuration') == f'depth-{depth}'}
    component_names = sorted(set(historical) | set(reviews) | set(mapped_groups))
    def scoped(name: str) -> list[dict[str, Any]]:
        return [f for f in findings if (f['rule_id'] == 'ER01' or f['rule_id'] == 'ER02' and name in reviews) and f['scope'].get('legacy') == name]
    component_names.sort(key=lambda name: (min((0 if f['severity'] == 'HIGH' else 1 for f in scoped(name)), default=2), name))
    snapshot += '<h3>Components requiring attention</h3><ul>' + ''.join(f'<li><a href="#component-{component_names.index(name)}">{text(name)}</a> · ' + ' / '.join(text(NAMES[f['rule_id']]) for f in scoped(name)) + '</li>' for name in [n for n in component_names if scoped(n)][:10]) + '</ul>'
    snapshot += '<p class="muted">Global delivery, defect and build findings stay global. Component observations require explicit scope. No finding does not mean Normal.</p>'

    components = '<p>Historical measures keep their source date. Unbound or mismatched component strategies are Unavailable; component counts overlap and must not be summed.</p><label for="component-search">Find a component</label><input id="component-search" class="component-search" type="search" placeholder="Search components" data-component-search><div class="table"><table><thead><tr><th>Component</th><th>Continuity</th><th>Review</th><th>Delivery</th><th>Quality</th><th>Traceability</th><th>Verification</th></tr></thead><tbody>'
    component_details = ''
    for index, name in enumerate(component_names):
        old = historical.get(name, {})
        review = reviews.get(name, {})
        row = mapped.get(name, {})
        cd = row.get('dimensions', {}).get('delivery', {}).get('current', {}).get('work_items', {})
        cq = row.get('dimensions', {}).get('quality', {}).get('current', {}).get('work_items', {})
        review_value = 'Unavailable' if review.get('coverage') is None else f'{review["coverage"] * 100:.1f}% · {text(review.get("coverage_status"))}'
        values = [old.get('risk', 'Unavailable'), review_value, 'Completed: ' + number(cd.get('completed')) if cd.get('availability') in ('OBSERVED', 'PARTIAL') else 'Unavailable', 'Open: ' + number(cq.get('open_inventory')) if cq.get('availability') in ('OBSERVED', 'PARTIAL') else 'Unavailable', 'Unavailable', 'Unavailable']
        components += f'<tr data-component-row><th scope="row"><a href="#component-{index}">{text(name)}</a></th>' + ''.join(f'<td>{text(v)}</td>' for v in values) + '</tr>'
        component_details += f'<details class="component-detail" id="component-{index}"><summary>{text(name)} · {len(scoped(name))} scoped attention observations</summary><h3>{text(name)}</h3><p class="muted">Independent evidence is shown only where this component has an exact accepted binding.</p>'
        component_details += table([('Continuity · historical', old.get('risk')), ('Review coverage · historical', review_value), ('Delivery completed', cd.get('completed')), ('Delivery median', median(cd.get('durations', {}))), ('Defects opened', cq.get('opened')), ('Defects resolved', cq.get('completed')), ('Defects open', cq.get('open_inventory')), ('Defects aged ≥30d', cq.get('aged')), ('Component traceability evidence', 'Unavailable'), ('Verification', 'Unavailable')])
        component_details += f'<a href="#component-evidence-{index}">Inspect evidence</a></details>'
    components += '</tbody></table></div>' + component_details
    if not component_names:
        components += '<p>Component membership unavailable. No explicit binding exists.</p>'

    details = '<details><summary>Continuity</summary>' + table([(name, c.get('risk')) for name, c in historical.items()]) + '<p>Historical concentration observations; inspect source support and any stress evidence in methodology.</p></details>'
    details += '<details><summary>Delivery</summary>' + table([('Completed work items', wi.get('completed')), ('Open work items', wi.get('open_inventory')), ('Aged work items ≥30d', wi.get('aged')), ('Merged PRs', pr.get('merged')), ('Open PRs', pr.get('open_inventory'))]) + '<h3>Work-item cycle duration</h3>' + trend(delivery, 'work_items', 'durations') + '<h3>PR lead duration</h3>' + trend(delivery, 'pull_requests', 'lead') + '</details>'
    details += '<details><summary>Quality / Defect Evidence</summary>' + table([('Opened', bugs.get('opened')), ('Resolved · distinct defects', bugs.get('completed')), ('Open', bugs.get('open_inventory')), ('Aged ≥30d', bugs.get('aged')), ('Reopened', bugs.get('reopened')), ('Resolution median', median(bugs.get('durations', {})))]) + '<p>Opened minus resolved does not establish backlog growth; reopens and removals are separate.</p></details>'
    details += '<details><summary>Build Evidence</summary>' + table([('Qualified terminal builds', builds.get('known_terminal'))] + [(name.replace('_', ' ').title(), count) for name, count in (builds.get('categories') or [])] + [('Success fraction', percent(builds.get('success_fraction'))), ('Failure fraction', percent(builds.get('failure_fraction'))), ('Duration median', median(builds.get('durations', {}), 'minutes')), ('Unfinished', builds.get('unfinished')), ('Undated', builds.get('undated'))]) + '<p>Build success is not a software-quality score. Deployment evidence is unavailable.</p></details>'
    details += trend(delivery, 'builds', 'durations', 'minutes')
    details += '<details><summary>Reviews</summary>' + table([(name, 'Unavailable' if c.get('coverage') is None else f'{c["coverage"] * 100:.1f}% · {c.get("coverage_status")}') for name, c in review_rows.items()]) + '<p>Independent review source; original component depth: ' + number(review_depth) + '. Qualifying review interaction, not review quality. Concentration, unreviewed PRs and exclusions remain inspectable.</p></details>'
    details += '<details><summary>Traceability &amp; Verification</summary><p>' + text(coverage('traceability_evidence')) + ' / ' + text(coverage('verification_evidence')) + '</p>' + table([(m['dimension'], 'Unavailable' if m['value'] is None else str(m['value']) + ' · ' + m['status']) for m in legacy.get('verification_evidence', {}).get('result', {}).get('metrics', [])]) + '<a href="#legacy-evidence">Inspect paths, linkage, gaps and qualified verification observations</a></details>'

    from continuity.reporting.engineering_evidence_html import render_evidence
    methodology = render_evidence(validated, NAMES, findings, investigations, source_summary, component_names, historical, review_rows, reviews, mapped_groups)
    content = [snapshot, components, details, methodology]
    data = canonical(validated).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    download = b64encode(canonical(validated).encode('utf-8')).decode('ascii')
    output = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Engineering System Review · ' + text(a['system']) + '</title><style>' + CSS + '</style></head><body><div class="report-shell"><aside class="report-nav"><p class="eyebrow">ENGINEERING CONTINUITY LAB</p><strong>' + text(a['system']) + '</strong><nav aria-label="Manager report">' + ''.join(f'<a href="#section-{i}">{text(label)}</a>' for i, label in enumerate(NAVIGATION_LABELS)) + '</nav></aside><main>'
    output += '<header><p class="eyebrow">ENGINEERING CONTINUITY LAB</p><h1>Engineering System Review</h1><p class="system-name">' + text(a['system']) + '</p><p class="source-label"><strong>Data source:</strong> ' + text(source_label) + '</p><p class="badge">' + text(provenance) + '</p><p class="assessment-window">Assessment UTC: ' + text(window['start']) + ' to ' + text(window['end']) + ' (end excluded).</p><p class="review-subtitle">Understand engineering continuity, delivery flow, quality and traceability in one review.</p><div class="actions"><button type="button" onclick="window.print()">Print / Save as PDF</button> <a download="engineering-review.json" href="data:application/json;base64,' + download + '">Download evidence package (.json)</a></div><p class="muted">Machine-readable evidence used to reproduce and audit this review.</p></header>'
    output += ''.join(f'<section class="executive-summary" id="section-{i}" aria-labelledby="title-{i}"><h2 id="title-{i}">{text(title)}</h2>{body}</section>' if i == 0 else f'<section id="section-{i}" aria-labelledby="title-{i}"><h2 id="title-{i}">{text(title)}</h2>{body}</section>' for i, (title, body) in enumerate(zip(SECTIONS, content)))
    output += '<footer>Offline evidence. No network access or execution is performed by this document.</footer></main></div><script id="engineering-package" type="application/json">' + data + '</script><script>' + PRINT_SCRIPT + ''';(()=>{const input=document.querySelector('[data-component-search]');const reveal=()=>{if(!location.hash)return;const detail=document.querySelector(location.hash);if(detail&&detail.tagName==='DETAILS'){detail.open=true;detail.scrollIntoView({block:'start'});}};if(input)input.addEventListener('input',()=>{const query=input.value.trim().toLocaleLowerCase();document.querySelectorAll('[data-component-row]').forEach(row=>{row.hidden=!row.textContent.toLocaleLowerCase().includes(query);});});window.addEventListener('hashchange',reveal);reveal();})();''' + '</script></body></html>'
    if len(output.encode('utf-8')) > 32 * 1024 * 1024:
        raise ValueError('invalid engineering HTML size')
    return output
