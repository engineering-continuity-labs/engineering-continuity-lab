"""Presentation parity, escaping and offline artifact contracts (AC501/519–521)."""
from html.parser import HTMLParser
import json
from base64 import b64decode
from pathlib import Path
import unittest

from continuity.reporting.engineering_html import render, SECTIONS
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
        for label in ('Continuity component rows', 'Review component rows', 'Change traceability',
                      'Historical test observations', 'Aging delivery work', 'Source boundaries', 'Historical component context'):
            self.assertIn(label, document.snapshot)
        for metric in report['verification_evidence']['result']['metrics']:
            self.assertIn(metric['dimension'], document.snapshot)
        self.assertIn('Delivery/defect component mapping unavailable', document.snapshot)
        download = next(a['href'] for tag, a in document.tags if tag == 'a' and 'download' in a)
        self.assertEqual(import_package(b64decode(download.split(',', 1)[1])), package)
    def test_provenance_is_explicit_not_alias_inference(self):
        windows, delivery, _ = sources()
        delivery['alias'] = 'synthetic-export'
        package = compose(assessment_id='review', system='atlas', windows=windows, delivery=delivery)
        self.assertIn('OFFLINE DECLARED · source owner assertions', render(package))
        self.assertNotIn('explicitly declared demo evidence', render(package))
        self.assertIn('SYNTHETIC · explicitly declared demo evidence', render(package, synthetic=True))
    def test_sections_numeric_parity_and_offline_reopen(self):
        windows, delivery, quality = sources()
        package = compose(assessment_id='synthetic', system='atlas', windows=windows, delivery=delivery, quality=quality)
        html = render(package)
        document = Document()
        document.feed(html)
        self.assertEqual(len([t for t, _ in document.tags if t == 'section']), 12)
        for title in SECTIONS:
            self.assertIn(title.replace('&', '&amp;'), html)
        self.assertEqual(import_package(document.package), package)
        self.assertIn('10 days · n=4', html)
        self.assertIn('9/2 days · n=2', html)
        self.assertIn('5 minutes · n=4', html)
        self.assertEqual(render(package), html)
        self.assertFalse(any(t in ('iframe', 'img', 'link') for t, _ in document.tags))
        self.assertEqual([(t, a.get('type')) for t, a in document.tags if t == 'script'], [('script', 'application/json'), ('script', None)])
        self.assertIn("addEventListener('beforeprint'", html)
        self.assertIn("addEventListener('afterprint'", html)
        self.assertNotIn('fetch(', html)
        self.assertIn('@media print', html)
        self.assertIn(':focus-visible', html)

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
