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
        for label in ('Continuity', 'Reviews', 'Traceability', 'Verification',
                      'Aging delivery items detected', 'Evidence coverage', 'Components requiring attention'):
            self.assertIn(label, document.snapshot)
        self.assertNotIn('ER05', document.snapshot)
        self.assertIn('Unavailable', document.snapshot)
        download = next(a['href'] for tag, a in document.tags if tag == 'a' and 'download' in a)
        self.assertEqual(import_package(b64decode(download.split(',', 1)[1])), package)
    def test_provenance_is_explicit_not_alias_inference(self):
        windows, delivery, _ = sources()
        delivery['alias'] = 'synthetic-export'
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        self.assertIn('OFFLINE DECLARED · source owner assertions', render(package))
        self.assertNotIn('explicitly declared demo evidence', render(package))
        self.assertIn('SYNTHETIC MANAGER EXAMPLE', render(package, synthetic=True))
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
        self.assertIn('SYNTHETIC MANAGER EXAMPLE', document.snapshot)
        self.assertIn('Delivery duration increased', document.snapshot)
        for finding in package['assessment']['findings']:
            self.assertIn('id="finding-' + finding['id'] + '"', html)
        self.assertIn('Exact supporting evidence', html)
        self.assertNotIn('Health =', html)
        self.assertIn('Quality / Defect Evidence', html)
        self.assertIn('Traceability component binding', html)
        self.assertIn('Verification component binding', html)

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
        document = Document(); document.feed(render(package))
        self.assertIn('0 qualified terminal builds', document.snapshot)
        delivery['populations']['builds']['status'] = 'FAILED'
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        document = Document(); document.feed(render(package))
        self.assertIn('Unavailable qualified terminal builds', document.snapshot)
        self.assertNotIn('0 qualified terminal builds', document.snapshot)
        self.assertIn('Delivery: Partial', document.snapshot)

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
        document = Document(); document.feed(render(package))
        self.assertIn('Delivery: Unavailable', document.snapshot)
        self.assertIn('Major unavailable evidence: ', document.snapshot)

    def test_global_namespace_cannot_become_component_attention(self):
        windows, _, _ = sources()
        report = json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text())
        report['components'][0]['component'] = 'traceability'
        package = compose(assessment_id='review', system='atlas', windows=windows, ecl_report=report)
        document = Document(); document.feed(render(package))
        attention = document.snapshot.split('Components requiring attention', 1)[1]
        self.assertNotIn('Traceability gaps detected', attention)
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
        self.assertIn('Unavailable', components)
        self.assertIn('75.0%', render(compose(assessment_id='review', system='atlas', windows=windows, ecl_report=json.loads((Path(__file__).resolve().parents[1] / 'examples/v0.4-traceability-v3.json').read_text()))).split('id="section-1"', 1)[1].split('id="section-2"', 1)[0])

    def test_nonmidnight_window_keeps_exact_utc_bounds(self):
        from datetime import datetime, timezone
        from continuity.domain.engineering_review import Window, Windows
        previous = Window(datetime(2026, 9, 1, 6, tzinfo=timezone.utc), datetime(2026, 9, 1, 12, tzinfo=timezone.utc))
        current = Window(previous.end, datetime(2026, 9, 1, 18, tzinfo=timezone.utc))
        windows = Windows(current, previous, current.end)
        package = compose(assessment_id='review', system='atlas', windows=windows)
        document = Document(); document.feed(render(package))
        self.assertIn('2026-09-01T12:00:00Z', document.snapshot)
        self.assertIn('2026-09-01T18:00:00Z', document.snapshot)

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
