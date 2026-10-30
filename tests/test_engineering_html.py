"""Presentation parity, escaping and offline artifact contracts (AC501/519–521)."""
from html.parser import HTMLParser
import json
from base64 import b64decode
from pathlib import Path
import unittest

from continuity.reporting.engineering_html import render, SECTIONS, display_fraction
from continuity.reporting.engineering_review import compose, import_package
from continuity.traceability_providers.engineering_synthetic import sources


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.package = ''
        self.in_package = False
        self.in_snapshot = False
        self.snapshot = ''

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        self.in_package = tag == 'script' and attributes.get('id') == 'engineering-package' or self.in_package
        if tag == 'section':
            self.in_snapshot = attributes.get('id') == 'section-0'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_package = False
        if tag == 'section':
            self.in_snapshot = False

    def handle_data(self, value):
        if self.in_package:
            self.package += value
        if self.in_snapshot:
            self.snapshot += value


class EngineeringHTMLTests(unittest.TestCase):
    def test_snapshot_contains_independent_legacy_dimensions_and_attention(self):
        from continuity.reporting.portable import with_verification_evidence
        from continuity.traceability_providers.verification_synthetic import fixture
        windows, delivery, quality = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        report = with_verification_evidence(report, fixture())
        package = compose(assessment_id='review', system='atlas', windows=windows,
                          delivery=delivery, quality=quality, ecl_report=report)
        document = Document()
        document.feed(render(package))
        for label in ('Continuity', 'Evidence status',
                      'Inspect 5 components with scoped attention evidence'):
            self.assertIn(label, document.snapshot)
        rendered = render(package)
        for label in ('Reviews', 'Traceability', 'Verification'):
            self.assertIn(label, rendered)
        self.assertIn('Aging delivery items detected', render(package))
        self.assertNotIn('ER05', document.snapshot)
        self.assertIn('Major unavailable evidence: Deployment', document.snapshot)
        download = next(a['href'] for tag, a in document.tags if tag == 'a' and 'download' in a)
        self.assertEqual(import_package(b64decode(download.split(',', 1)[1])), package)
    def test_provenance_is_explicit_not_alias_inference(self):
        windows, delivery, _ = sources()
        delivery['alias'] = 'synthetic-export'
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        self.assertIn('OFFLINE DECLARED · source owner assertions', render(package))
        self.assertIn('Data source:</strong> Locally generated validated evidence package', render(package))
        self.assertNotIn('explicitly declared demo evidence', render(package))
        self.assertIn('SYNTHETIC DEMO PROJECT', render(package, synthetic=True))

    def test_safe_local_source_overrides_are_escaped_presentation_only(self):
        windows, _, _ = sources()
        package = compose(assessment_id='review', system='local-git', windows=windows)
        html = render(package, source_label_override='Local Git history — repo&lt;safe&gt;',
                      provenance_override='LOCAL GIT ANALYSIS · Git history only')
        self.assertIn('Local Git history — repo&amp;lt;safe&amp;gt;', html)
        self.assertIn('LOCAL GIT ANALYSIS · Git history only', html)
        from continuity.reporting.portable import canonical
        self.assertEqual(import_package(canonical(package)), package)
    def test_sections_numeric_parity_and_offline_reopen(self):
        windows, delivery, quality = sources()
        package = compose(assessment_id='synthetic', system='atlas', windows=windows, delivery=delivery, quality=quality)
        html = render(package)
        document = Document()
        document.feed(html)
        self.assertEqual(len([t for t, _ in document.tags if t == 'section']), 4)
        for title in SECTIONS:
            self.assertIn(title.replace('&', '&amp;'), html)
        self.assertEqual(import_package(document.package), package)
        self.assertIn('10.0 days', html)
        self.assertIn('4.5 days', html)
        self.assertIn('5.0 minutes', html)
        self.assertEqual(render(package), html)
        self.assertFalse(any(t in ('iframe', 'img', 'link') for t, _ in document.tags))
        self.assertEqual([(t, a.get('type')) for t, a in document.tags if t == 'script'], [('script', 'application/json'), ('script', None)])
        self.assertIn("addEventListener('beforeprint'", html)
        self.assertIn("addEventListener('afterprint'", html)
        self.assertNotIn('fetch(', html)
        self.assertIn('@media print', html)
        self.assertIn(':focus-visible', html)

    def test_atlas_four_layers_human_labels_source_parity(self):
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        html = render(package, synthetic=True)
        document = Document()
        document.feed(html)
        self.assertEqual(import_package(document.package), package)
        self.assertLess(html.index('id="section-0"'), html.index('id="section-1"'))
        for rule in ('ER01', 'ER03', 'ER05', 'ER06', 'ER07', 'ER08', 'ER09'):
            self.assertNotIn(rule, document.snapshot)
            self.assertIn('Method: ' + rule, html)
        for value in ('10.0 days', '5.0 days', '+5.0 days / +100.0%', '50.0%', '25.0%', 'Opened: 4', 'Resolved: 2', 'Open: 2', 'Reopened: 1'):
            self.assertIn(value, document.snapshot)
        self.assertIn('Trend unavailable', html)
        self.assertIn('SYNTHETIC DEMO PROJECT', html)
        self.assertIn('Data source:', html)
        self.assertIn('Synthetic demo data — Atlas Commerce (fictional)', html)
        self.assertIn('Delivery duration increased', document.snapshot)
        for finding in package['assessment']['findings']:
            self.assertIn('id="finding-' + finding['id'] + '"', html)
        self.assertIn('View exact supporting evidence references', html)
        self.assertNotIn('Health =', html)
        self.assertIn('Quality / Defect Evidence', html)
        self.assertIn('Component traceability evidence', html)
        self.assertIn('Verification', html)

    def test_executive_shell_has_four_kpis_sidebar_and_component_search(self):
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        html = render(package, synthetic=True)
        snapshot = html.split('id="section-0"', 1)[1].split('id="section-1"', 1)[0]
        self.assertIn('class="report-nav"', html)
        self.assertIn('data-component-search', html)
        self.assertIn('data-component-row', html)
        for label in ('>Executive Review<', '>Components<', '>Engineering Details<', '>Evidence &amp; Methodology<'):
            self.assertIn(label, html)
        self.assertLess(snapshot.index('Start here'), snapshot.index('Historical continuity'))
        self.assertLess(snapshot.index('Historical continuity'), snapshot.index('At a glance'))
        self.assertLess(snapshot.index('At a glance'), snapshot.index('Executive indicators'))
        self.assertEqual(snapshot.count('<div class="card">'), 4)
        for label in ('Continuity', 'Delivery', 'Defects', 'Builds'):
            self.assertIn('<h3>' + label + '</h3>', snapshot)
        self.assertNotIn('<h3>PR Flow</h3>', snapshot)
        self.assertNotIn('<h3>Traceability</h3>', snapshot)
        self.assertNotIn('<h3>Reviews</h3>', snapshot)
        self.assertNotIn('<h3>Verification</h3>', snapshot)

    def test_executive_start_here_is_bounded_and_links_to_retained_evidence(self):
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        html = render(package, synthetic=True)
        snapshot = html.split('id="section-0"', 1)[1].split('id="section-1"', 1)[0]
        priority = snapshot.split('<ul class="finding-list priority-findings">', 1)[1].split('</ul>', 1)[0]
        self.assertLess(snapshot.index('Start here'), snapshot.index('At a glance'))
        self.assertLessEqual(priority.count('<li class="attention'), 3)
        self.assertEqual(priority.count('Inspect evidence'), priority.count('href="#finding-'))
        self.assertIn('View all findings', snapshot)
        self.assertIn('id="all-findings"', html)
        self.assertIn('unavailable evidence remains unavailable', snapshot)
        self.assertNotIn('Health =', snapshot)

    def test_executive_first_layer_defers_component_inventory_and_coverage_detail(self):
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        html = render(package, synthetic=True)
        snapshot = html.split('id="section-0"', 1)[1].split('id="section-1"', 1)[0]
        self.assertLess(snapshot.index('Evidence status:'), snapshot.index('At a glance'))
        self.assertNotIn('Evidence coverage', snapshot)
        self.assertNotIn('Components requiring attention', snapshot)
        self.assertIn('href="#section-1">Inspect 5 components with scoped attention evidence</a>', snapshot)
        evidence = html.split('id="all-findings"', 1)[1]
        self.assertIn('href="#section-0">Return to Executive Review</a>', evidence)

    def test_pr_only_duration_finding_explains_triggering_population(self):
        from datetime import datetime, timedelta
        windows, delivery, quality = sources()
        records = [r for r in delivery['work_items'] if r['reference'][-1].startswith('current-')]
        for index, record in enumerate(records):
            completed = datetime.fromisoformat(record['transitions'][-1]['occurred_at'].replace('Z', '+00:00'))
            start = completed - timedelta(days=(index + 1) * 2)
            record['created_at'] = record['history_start'] = start.isoformat()
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery, quality=quality)
        document = Document()
        document.feed(render(package))
        self.assertIn('PR median: 5.0 days → 10.0 days', document.snapshot)
        self.assertNotIn('Work-item median:', document.snapshot)

    def test_complete_zero_and_failed_source_stay_distinct(self):
        windows, delivery, _ = sources()
        delivery['builds'] = []
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        rendered = render(package)
        document = Document(); document.feed(rendered)
        self.assertIn('0 qualified terminal builds', document.snapshot)
        delivery['populations']['builds']['status'] = 'FAILED'
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        rendered = render(package)
        document = Document(); document.feed(rendered)
        self.assertIn('Unavailable qualified terminal builds', document.snapshot)
        self.assertNotIn('0 qualified terminal builds', document.snapshot)
        self.assertIn('<th scope="row">Delivery</th><td>Partial</td>', rendered)

    def test_display_precision_never_turns_nonzero_into_zero(self):
        self.assertEqual(display_fraction({'numerator': 60000000, 'denominator': 1}, 86400000000, ' days'), '<0.1 days')
        self.assertEqual(display_fraction({'numerator': -60000000, 'denominator': 1}, 86400000000, ' days', True), '-<0.1 days')
        self.assertEqual(display_fraction({'numerator': 1, 'denominator': 100}, suffix='%'), '<0.1%')
        self.assertEqual(display_fraction({'numerator': 0, 'denominator': 1}, suffix='%'), '0.0%')

    def test_no_supported_delivery_population_is_unavailable(self):
        windows, delivery, _ = sources()
        for population in delivery['populations'].values():
            population['capability'] = 'UNSUPPORTED'
        delivery['work_items'] = []; delivery['pull_requests'] = []; delivery['builds'] = []
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        rendered = render(package)
        document = Document(); document.feed(rendered)
        self.assertIn('<th scope="row">Delivery</th><td>Unavailable</td>', rendered)
        self.assertIn('Major unavailable evidence: ', document.snapshot)

    def test_global_namespace_cannot_become_component_attention(self):
        windows, _, _ = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        report['components'][0]['component'] = 'traceability'
        package = compose(assessment_id='review', system='atlas', windows=windows, ecl_report=report)
        document = Document(); document.feed(render(package))
        components = render(package).split('id="section-1"', 1)[1].split('id="section-2"', 1)[0]
        self.assertNotIn('Traceability gaps detected', components)
        self.assertIn('Traceability gaps detected', document.snapshot)

    def test_mismatched_component_depth_cannot_join_independent_dimensions(self):
        windows, delivery, quality = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        report['configuration']['component_depth'] = 1
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery, quality=quality, ecl_report=report)
        html = render(package)
        components = html.split('id="section-1"', 1)[1].split('id="section-2"', 1)[0]
        self.assertNotIn('75.0%', components)
        engineering_details = html.split('id="section-2"', 1)[1].split('id="section-3"', 1)[0]
        self.assertIn('75.0%', engineering_details)
        self.assertIn('original component depth: 2', engineering_details)
        component_evidence = html.split('id="component-evidence-', 1)[1].split('Independent review evidence', 1)[0]
        self.assertNotIn('75.0%', component_evidence)
        self.assertIn('Review evidence unavailable for this component binding', component_evidence)
        independent_reviews = html.split('Independent review evidence', 1)[1].split('id="legacy-evidence"', 1)[0]
        self.assertIn('75.0%', independent_reviews)
        self.assertIn('Excluded interactions', independent_reviews)
        self.assertIn('Original review component depth: 2', independent_reviews)
        self.assertIn('Unavailable', components)
        self.assertIn('75.0%', render(compose(assessment_id='review', system='atlas', windows=windows, ecl_report=json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text()))).split('id="section-1"', 1)[1].split('id="section-2"', 1)[0])

    def test_nonmidnight_window_keeps_exact_utc_bounds(self):
        from datetime import datetime, timezone
        from continuity.domain.engineering_review import Window, Windows
        previous = Window(datetime(2026, 9, 1, 6, tzinfo=timezone.utc), datetime(2026, 9, 1, 12, tzinfo=timezone.utc))
        current = Window(previous.end, datetime(2026, 9, 1, 18, tzinfo=timezone.utc))
        windows = Windows(current, previous, current.end)
        package = compose(assessment_id='review', system='atlas', windows=windows)
        html = render(package)
        self.assertIn('2026-09-01T12:00:00Z', html)
        self.assertIn('2026-09-01T18:00:00Z', html)

    def test_absent_mapping_never_receives_global_counts(self):
        windows, delivery, quality = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        package = compose(assessment_id='review', system='atlas', windows=windows,
                          delivery=delivery, quality=quality, ecl_report=report)
        html = render(package)
        components = html.split('id="section-1"', 1)[1].split('id="section-2"', 1)[0]
        self.assertNotIn('Completed: 4', components)
        self.assertIn('Unavailable', components)
        self.assertNotIn('Normal', components)

    def test_human_evidence_download_digest_and_no_inline_json(self):
        from hashlib import sha256
        from continuity.reporting.portable import canonical
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        html = render(package, synthetic=True)
        document = Document(); document.feed(html)
        self.assertIn('Download evidence package (.json)', html)
        self.assertIn('Machine-readable evidence used to reproduce and audit this review.', html)
        self.assertFalse(any(t == 'pre' for t, _ in document.tags))
        self.assertNotIn('Canonical package and schema metadata', html)
        download = next(attrs['href'] for tag, attrs in document.tags if tag == 'a' and 'download' in attrs)
        raw = b64decode(download.split(',', 1)[1])
        self.assertEqual(raw, canonical(package).encode('utf-8'))
        self.assertEqual(import_package(document.package), package)
        self.assertIn(sha256(raw).hexdigest(), html)
        self.assertIn('Technical method', html)
        self.assertIn('.technical{display:none!important}', html)
        self.assertIn("querySelectorAll('details:not(.technical)')", html)
        for label in ('Evidence Sources', 'Assessment Period', 'Evidence Completeness', 'Historical contributors', 'Mapped PRs',
                      'PRs with qualifying review evidence', 'Excluded interactions', 'Observed implementation paths', 'Historical test observations',
                      'Qualified current samples', 'Qualified previous samples', 'Evidence package'):
            self.assertIn(label, html)
        human_method = html.split('id="section-3"', 1)[1].split('id="engineering-package"', 1)[0]
        self.assertNotIn('&quot;assessment&quot;', human_method)
        self.assertIn('Current median', human_method)
        self.assertIn('Previous median', human_method)
        self.assertIn('Work Item 1001', human_method)
        self.assertIn('Test T1 @v1', human_method)
        self.assertIn('Path uncertainty:', human_method)
        self.assertIn('Exact requirement path qualification and support', human_method)

    def test_evidence_rule_ids_only_within_technical_disclosure(self):
        from continuity.reporting.engineering_html import NAMES
        package = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.5-engineering-review.json').read_text())
        class Visibility(HTMLParser):
            def __init__(self):
                super().__init__(); self.stack = []; self.technical = 0; self.in_script = False; self.normal = ''; self.audit = ''
            def handle_starttag(self, tag, attrs):
                if tag == 'details':
                    technical = 'technical' in dict(attrs).get('class', '').split()
                    self.stack.append(technical); self.technical += technical
                if tag == 'script': self.in_script = True
            def handle_endtag(self, tag):
                if tag == 'details': self.technical -= self.stack.pop()
                if tag == 'script': self.in_script = False
            def handle_data(self, value):
                if self.in_script: return
                if self.technical: self.audit += value
                else: self.normal += value
        parsed = Visibility(); parsed.feed(render(package))
        for finding in package['assessment']['findings']:
            self.assertNotIn(finding['rule_id'], parsed.normal)
            self.assertIn(finding['rule_id'], parsed.audit)
            self.assertIn(NAMES[finding['rule_id']], parsed.normal)
        self.assertNotIn('schema_version', parsed.normal)

    def test_missing_data_and_forgery_are_not_synthetic_fallback(self):
        windows, _, _ = sources()
        package = compose(assessment_id='review', system='approved', windows=windows)
        html = render(package)
        self.assertIn('Unavailable', html)
        self.assertNotIn('fictional source example', html)
        package['assessment']['findings'] = [{'rule_id': 'ER09'}]
        with self.assertRaises(ValueError):
            render(package)

    def test_markup_and_script_breakout_remain_data(self):
        windows, _, _ = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        report['warning'] = '</script><img src=x onerror=alert(1)>'
        package = compose(assessment_id='review', system='approved', windows=windows, ecl_report=report)
        document = Document()
        html = render(package)
        document.feed(html)
        self.assertFalse(any(t == 'img' for t, _ in document.tags))
        self.assertEqual(import_package(document.package), package)
