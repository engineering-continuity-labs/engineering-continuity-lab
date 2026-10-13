"""Self-contained manager presentation of a recomputed offline assessment."""
from html import escape
from fractions import Fraction
from base64 import b64encode
import json
from typing import Any

from continuity.reporting.engineering_review import import_package
from continuity.reporting.portable import canonical

SECTIONS = ('Executive Engineering Snapshot', 'System / Component Landscape', 'Engineering Continuity',
            'Change Traceability', 'Review Health', 'Requirements & Verification', 'Delivery Flow',
            'Quality / Defect Evidence', 'Build Health', 'Engineering Risks / Findings',
            'Evidence Completeness & Limitations', 'Recommended Investigation / Management Actions')

CSS = '''
:root{color-scheme:light;--ink:#142f3a;--muted:#526871;--line:#d3e0e3;--accent:#147a74}
*{box-sizing:border-box}body{margin:0;background:#eff4f4;color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1160px;margin:auto;padding:40px 28px}header{border-top:6px solid var(--accent);padding:24px 0}
h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.05;margin:12px 0}h2{font-size:1.5rem}h3{font-size:1.1rem}
.eyebrow{letter-spacing:.14em;font-size:.75rem;font-weight:700;color:var(--accent)}.muted{color:var(--muted)}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}nav a,button{background:white;border:1px solid var(--line);padding:8px 12px;border-radius:6px;color:var(--ink)}
a{color:var(--accent)}a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #edaa42;outline-offset:3px}
section{background:white;border:1px solid var(--line);border-radius:12px;margin:20px 0;padding:24px;scroll-margin-top:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}.card{padding:18px;background:#f4f8f8;border-radius:8px}
.value{font-size:2rem;font-weight:700}.label{color:var(--muted);font-size:.85rem}.badge{font-size:.75rem;padding:3px 8px;border:1px solid var(--line);border-radius:20px}
details{border:1px solid var(--line);border-radius:8px;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:600}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem;background:#f5f8f8;padding:14px}table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}.table{overflow-x:auto}
.attention{border-left:4px solid #bd752b;padding:10px 16px;background:#fff8ed}footer{color:var(--muted);font-size:.85rem;margin:30px 0}
@media(max-width:600px){main{padding:16px}section{padding:16px}h1{font-size:2.2rem}.cards{grid-template-columns:1fr}header,.card,h2{overflow-wrap:anywhere}}
@media print{body{background:white}main{max-width:none;padding:0}nav,button{display:none}section{break-inside:avoid;border-radius:0}details{break-inside:avoid}details> :not(summary){display:block!important}a{color:inherit}h2{break-after:avoid}}
'''

PRINT_SCRIPT = '''(()=>{let states=[];window.addEventListener('beforeprint',()=>{
states=Array.from(document.querySelectorAll('details'),d=>[d,d.open]);
for(const[d]of states)d.open=true;});window.addEventListener('afterprint',()=>{
for(const[d,open]of states)d.open=open;states=[];});})();'''


def text(value: Any) -> str:
    return escape(str(value), quote=True)


def inspector(title: str, value: Any) -> str:
    return f'<details><summary>{text(title)}</summary><pre>{text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2))}</pre></details>'


def number(value: Any) -> str:
    return 'Unavailable' if value is None else text(value)


def table(rows: list[tuple[str, Any]]) -> str:
    return '<div class="table"><table><thead><tr><th>Evidence</th><th>Observed value</th></tr></thead><tbody>' + ''.join(
        f'<tr><th scope="row">{text(k)}</th><td>{number(v)}</td></tr>' for k, v in rows) + '</tbody></table></div>'


def render(package: dict[str, Any], *, synthetic: bool = False) -> str:
    """Render only accepted, recomputed evidence; raw errors stay sanitized."""
    if type(synthetic) is not bool:
        raise ValueError('invalid presentation provenance')
    validated = import_package(canonical(package))
    a, evidence = validated['assessment'], validated['evidence']
    legacy = evidence.get('ecl_report', {})
    dims = a['dimension_results']
    window = a['windows']['current']
    def current(name: str) -> dict[str, Any]:
        value = dims.get(name, {}).get('current', {})
        return dict(value)
    def duration(sample: dict[str, Any], divisor: int, unit: str) -> str:
        value = sample.get('median')
        if value is None:
            return 'Unavailable'
        result = Fraction(value['numerator'], value['denominator']) / divisor
        return f'{result} {unit} · n={sample["count"]}'
    delivery, quality = current('delivery'), current('quality')
    wi, bugs, builds = delivery.get('work_items', {}), quality.get('work_items', {}), delivery.get('builds', {})
    cards = [('Completed work items', wi.get('completed'), wi.get('availability', 'UNAVAILABLE')),
             ('Open defects', bugs.get('open_inventory'), bugs.get('availability', 'UNAVAILABLE')),
             ('Aged defects', bugs.get('aged'), bugs.get('availability', 'UNAVAILABLE')),
             ('Known terminal builds', builds.get('known_terminal'), builds.get('availability', 'UNAVAILABLE'))]
    cards += [('Continuity component rows', len(legacy['components']) if 'components' in legacy else None,
               'SOURCE_BOUNDARY' if 'components' in legacy else 'UNAVAILABLE'),
              ('Review component rows', len(legacy['review_evidence']['components']) if 'review_evidence' in legacy else None,
               legacy.get('review_evidence', {}).get('provenance', {}).get('status', 'UNAVAILABLE')),
              ('Change traceability', legacy.get('traceability_evidence', {}).get('result', {}).get('summary'),
               'SOURCE_BOUNDARY' if 'traceability_evidence' in legacy else 'UNAVAILABLE'),
              ('Historical test observations', len(legacy['verification_evidence']['result']['runs']) if 'verification_evidence' in legacy else None,
               legacy.get('verification_evidence', {}).get('result', {}).get('collection_status', 'UNAVAILABLE'))]
    for metric in legacy.get('verification_evidence', {}).get('result', {}).get('metrics', []):
        cards.append((metric['dimension'], metric['value'], metric['status']))
    provenance = 'SYNTHETIC · explicitly declared demo evidence' if synthetic else 'OFFLINE DECLARED · source owner assertions'
    snapshot = f'<p class="badge">{text(provenance)}</p><p>Current UTC interval: {text(window["start"])} → {text(window["end"])} (end excluded).</p>'
    snapshot += '<div class="cards">' + ''.join(f'<div class="card"><div class="label">{text(label)}</div><div class="value">{number(value)}</div><span class="badge">{text(status)}</span></div>' for label, value, status in cards) + '</div>'
    snapshot += f'<p>{len(a["findings"])} evidence-backed attention findings. Finding counts are not a health score.</p>'
    names = {'ER01': 'Continuity concentration', 'ER02': 'Low review coverage', 'ER03': 'Traceability gap',
             'ER04': 'Verification gap', 'ER05': 'Aging delivery work', 'ER06': 'Increased delivery duration',
             'ER07': 'Aged defects', 'ER08': 'Defect inflow exceeds resolution', 'ER09': 'Build failure concentration'}
    snapshot += '<h3>Attention and affected scope</h3><ul>' + ''.join(
        f'<li><a href="#section-9">{text(f["severity"])} · {text(names[f["rule_id"]])}</a> · {text(f["scope"].get("legacy", f["scope"].get("dimension", a["system"])))}</li>'
        for f in a['findings'][:8]) + '</ul>'
    snapshot += f'<p class="muted">Showing {min(8, len(a["findings"]))} of {len(a["findings"])} findings. Full supporting evidence is in Engineering Risks / Findings.</p>'
    snapshot += '<h3>Historical component context</h3>'
    snapshot += table([(c['component'], f'{c["risk"]} · concentration {c["concentration"]}') for c in legacy.get('components', [])[:8]])
    snapshot += f'<p class="muted">Showing up to eight of {len(legacy.get("components", []))} historical component rows; source time {text(legacy.get("as_of", "Unavailable"))}. Full rows remain in Engineering Continuity. Delivery/defect component membership is separate.</p>'
    if not a['component_results'] or not any(d.get('mapping', {}).get('mapped', 0) for d in dims.values()):
        snapshot += '<p>Delivery/defect component mapping unavailable. Global findings do not establish component membership.</p>'
    snapshot += '<h3>Source boundaries</h3><ul>' + ''.join(f'<li>{text(s["role"])} · {text(s["alias"])} · {text(s["retrieved_at"])}</li>' for s in a['evidence_sources']) + '</ul>'
    snapshot += '<p>Unavailable dimensions: ' + text(', '.join(k for k, v in dims.items() if v.get('availability') == 'UNAVAILABLE') or 'inspect field and mapping completeness below') + '.</p>'
    snapshot += '<p class="muted">Missing evidence does not establish absence of problems. Historical observations do not establish cause or readiness.</p>'
    snapshot += inspector('Assessment sources and observation boundaries', a['evidence_sources'])
    landscape = '<p>Component rows overlap; do not sum their populations into a global total.</p>'
    if a['component_results']:
        for row in a['component_results']:
            component_dimensions = row['dimensions']
            cwi = component_dimensions.get('delivery', {}).get('current', {}).get('work_items', {})
            cq = component_dimensions.get('quality', {}).get('current', {}).get('work_items', {})
            landscape += '<h3>' + text(row['component_ref']['identifier']) + '</h3>'
            landscape += table([('Completed work items', cwi.get('completed')), ('Open defects', cq.get('open_inventory')),
                                ('Aged defects', cq.get('aged'))]) + inspector('Exact component scope, memberships and limitations', row)
    else:
        landscape += '<p>Component membership unavailable: no qualified explicit component mapping is present.</p>'
    landscape += inspector('Mapping coverage and unmapped populations', {k: v.get('mapping', {'availability': 'UNAVAILABLE'}) for k, v in dims.items() if k != 'legacy'})
    def old(title: str, key: str) -> str:
        if key not in legacy:
            return '<p>Unavailable for this source. No substitute or synthetic evidence was loaded.</p>'
        return '<p>Preserved historical evidence; source boundary: ' + text(legacy.get('as_of')) + '.</p>' + inspector(title, legacy[key])
    flow = table([('Completed work items', wi.get('completed')), ('Open work items', wi.get('open_inventory')),
                  ('Aged work items', wi.get('aged')), ('Merged PRs', delivery.get('pull_requests', {}).get('merged')),
                  ('Open PRs at boundary', delivery.get('pull_requests', {}).get('open_inventory')),
                  ('Work-item cycle median', duration(wi.get('durations', {}), 86400000000, 'days')),
                  ('PR lead median', duration(delivery.get('pull_requests', {}).get('lead', {}), 86400000000, 'days'))])
    flow += '<p>Duration samples exclude unfinished work. Units are exact microseconds; medians retain rational precision.</p>' + inspector('Delivery current/previous samples, comparisons and exclusions', dims.get('delivery'))
    defects = table([('Created defects', bugs.get('opened')), ('Distinct completed defects', bugs.get('completed')),
                     ('Open defects at boundary', bugs.get('open_inventory')), ('Aged defects', bugs.get('aged')), ('Reopened defects', bugs.get('reopened')),
                     ('Resolution median', duration(bugs.get('durations', {}), 86400000000, 'days'))])
    defects += '<p>Opened minus resolved is not backlog growth: reopens and removals remain separate evidence.</p>' + inspector('Defect histories, category boundaries and resolution samples', dims.get('quality'))
    build_section = table([('Known terminal runs', builds.get('known_terminal')), ('Unfinished runs', builds.get('unfinished')),
                           ('Undated terminal runs', builds.get('undated')),
                           ('Build duration median', duration(builds.get('durations', {}), 60000000, 'minutes'))]) + inspector('Build categories, fractions and qualified duration samples', builds)
    build_section += '<p>Build success is not product quality. Deployments are unsupported by this assessment scope.</p>'
    findings = ''.join(f'<details class="attention"><summary>{text(f["severity"])} · {text(f["rule_id"])}</summary>'
                       + inspector('Exact source support, threshold, scope and observed value', f) + '</details>' for f in a['findings']) or '<p>No eligible threshold finding. This does not prove absence of issues.</p>'
    limitations = inspector('Completeness, capability and acquisition state', a['completeness']) + inspector('Assessment limitations', a['limitations'])
    investigations = ''.join(f'<p><strong>{text(i["template_id"])}</strong> — {text(i["text"])}</p>' for i in a['investigations']) or '<p>No supported investigation template.</p>'
    content = [snapshot, landscape, old('Original component concentration and supports', 'components'), old('Validated paths, gaps and lookup provenance', 'traceability_evidence'),
               old('Historical qualifying review interactions', 'review_evidence'), old('Exact-version/target historical observations', 'verification_evidence'),
               flow, defects, build_section, findings, limitations, investigations]
    data = canonical(validated).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    download = b64encode(canonical(validated).encode('utf-8')).decode('ascii')
    output = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    output += '<title>Engineering System Review · ' + text(a['system']) + '</title><style>' + CSS + '</style></head><body><main>'
    output += '<header><p class="eyebrow">ENGINEERING CONTINUITY LAB · SYSTEM REVIEW</p><h1>' + text(a['system']) + '</h1><p class="muted">Independent evidence dimensions for a conservative engineering review.</p><button type="button" onclick="window.print()">Print / Save as PDF</button> <a download="engineering-review.json" href="data:application/json;base64,' + download + '">Download review JSON</a></header>'
    output += '<details><summary>Jump to a review section</summary><nav aria-label="Review sections">' + ''.join(f'<a href="#section-{i}">{text(title)}</a>' for i, title in enumerate(SECTIONS)) + '</nav></details>'
    output += ''.join(f'<section id="section-{i}" aria-labelledby="title-{i}"><h2 id="title-{i}">{text(title)}</h2>{body}</section>' for i, (title, body) in enumerate(zip(SECTIONS, content)))
    output += '<footer>Offline declared evidence. No network access or execution is performed by this document.</footer></main>'
    output += '<script id="engineering-package" type="application/json">' + data + '</script><script>' + PRINT_SCRIPT + '</script></body></html>'
    if len(output.encode('utf-8')) > 32 * 1024 * 1024:
        raise ValueError('invalid engineering HTML size')
    return output
