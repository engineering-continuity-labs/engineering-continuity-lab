"""Source-based v0.5 composition, uncertainty, boundary and privacy regressions."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import json
import unittest

from continuity.analysis.engineering_review import Lifecycle, State, Transition, analyze_population
from continuity.reporting.engineering_review import compose, import_package, public
from continuity.reporting.portable import canonical
from continuity.traceability_providers.engineering_synthetic import sources


class EngineeringPackageTests(unittest.TestCase):
    def test_legacy_rules_use_derived_sources_and_suppress_partial_lookup(self) -> None:
        from continuity.analysis.reviews import analyze_reviews
        from continuity.analysis.traceability import derive
        from continuity.domain.models import DirectoryComponents
        from continuity.domain.reviews import CollectionStatus, ProviderProvenance, PullRequestEvidence, ReviewEvidenceCollection, ReviewIdentity
        from continuity.domain.traceability import TraceabilityCapability
        from continuity.domain.verification import Relation
        from continuity.reporting.portable import with_verification_evidence
        from continuity.reporting.traceability import traceability_to_dict
        from continuity.traceability_providers.verification_synthetic import fixture
        from traceability_report_fixture import synthetic_v3_report
        windows, _, _ = sources()
        stamp = windows.previous.start
        owner = ReviewIdentity('approved-author')
        prs = tuple(PullRequestEvidence(str(i), owner, stamp, ('src/payments/a.py',), ()) for i in range(4))
        review_source = ReviewEvidenceCollection(ProviderProvenance('synthetic', 'demo-system', 'approved-review', stamp), prs)
        base = synthetic_v3_report()
        base['as_of'] = public(stamp)
        base['review_evidence'] = public(analyze_reviews(review_source, DirectoryComponents(2)))
        def rules(report):
            return {f['rule_id'] for f in compose(assessment_id='synthetic', system='atlas', windows=windows,
                                                 ecl_report=report)['assessment']['findings']}
        self.assertIn('ER02', rules(base))
        partial_reviews = replace(review_source, status=CollectionStatus.PARTIAL)
        base['review_evidence'] = public(analyze_reviews(partial_reviews, DirectoryComponents(2)))
        self.assertNotIn('ER02', rules(base))
        self.assertIn('ER03', rules(base))
        evidence = fixture()
        raw_code = evidence.code.evidence
        code = derive(replace(raw_code, status=CollectionStatus.PARTIAL,
                              lookups=tuple(replace(l, status=CollectionStatus.PARTIAL) for l in raw_code.lookups)))
        base['traceability_evidence'] = traceability_to_dict(code)
        self.assertNotIn('ER03', rules(base))
        # Remove declared observations and association supports, then derive
        # from the remaining real selected tests and their lookup assertions.
        missing = replace(evidence, runs=(), associations=tuple(a for a in evidence.associations if a.relation != Relation.VERIFICATION_TEST))
        base['traceability_evidence'] = traceability_to_dict(evidence.code)
        base['revision'] = evidence.snapshot.revision
        report = with_verification_evidence(base, missing)
        self.assertIn('ER04', rules(report))
        unsupported = replace(missing, lookups=tuple(replace(l, capability=TraceabilityCapability.UNSUPPORTED)
                                                     if l.relation == Relation.VERIFICATION_TEST else l for l in missing.lookups))
        self.assertNotIn('ER04', rules(with_verification_evidence(base, unsupported)))
        partial = replace(missing, status=CollectionStatus.PARTIAL,
                          lookups=tuple(replace(l, status=CollectionStatus.PARTIAL) for l in missing.lookups))
        self.assertNotIn('ER04', rules(with_verification_evidence(base, partial)))

    def test_findings_exact_bound_and_excess(self) -> None:
        windows, _, _ = sources()
        from continuity.reporting.portable_git import SIGNALS
        person = {'contributor': 'approved-alias', 'name': 'Approved', 'score': 1, 'share': 1,
                  'commits': 1, 'files': ['src/a'], 'signals': {s: 1 for s in SIGNALS}}
        report = {'report_version': '1.0', 'model': 'experimental-v0.1', 'revision': 'synthetic',
                  'as_of': public(windows.assessment_as_of), 'commit_count': 1,
                  'components': [{'component': f'component-{i}', 'concentration': 1, 'risk': 'CRITICAL',
                                  'contributors': [person]} for i in range(10000)]}
        result = compose(assessment_id='synthetic', system='atlas', windows=windows, ecl_report=report)
        self.assertEqual(len(result['assessment']['findings']), 10000)
        report['components'].append({**report['components'][0], 'component': 'excess'})
        with self.assertRaisesRegex(ValueError, '^invalid engineering evidence$'):
            compose(assessment_id='synthetic', system='atlas', windows=windows, ecl_report=report)

    def test_full_source_oracle_roundtrip(self) -> None:
        windows, delivery, quality = sources()
        package = compose(assessment_id='synthetic', system='atlas', windows=windows, delivery=delivery, quality=quality)
        self.assertEqual(import_package(canonical(package)), package)
        result = package['assessment']['dimension_results']
        wi = result['delivery']['current']['work_items']
        self.assertEqual(wi['completed'], 4)
        self.assertEqual(wi['durations']['median']['numerator'], 10 * 86400000000)
        self.assertEqual(result['delivery']['median_trend']['relative'], {'numerator': 1, 'denominator': 1})
        bugs = result['quality']['current']['work_items']
        self.assertEqual((bugs['opened'], bugs['completed'], bugs['reopened'], bugs['open_inventory'], bugs['aged']),
                         (4, 2, 1, 2, 1))
        self.assertEqual(bugs['age_buckets'], [0, 1, 1, 0])
        self.assertEqual([f['rule_id'] for f in package['assessment']['findings']], ['ER05', 'ER06', 'ER07', 'ER08', 'ER09'])
        for source in (delivery, quality):
            for name in ('work_items', 'pull_requests', 'builds'):
                source[name].reverse()
        self.assertEqual(compose(assessment_id='synthetic', system='atlas', windows=windows,
                                 delivery=delivery, quality=quality), package)

    def test_failed_empty_and_unsupported_are_not_zero(self) -> None:
        windows, delivery, quality = sources()
        for source in (delivery, quality):
            source.update(work_items=[], pull_requests=[], builds=[], status='FAILED')
        assessment = compose(assessment_id='synthetic', system='atlas', windows=windows,
                             delivery=delivery, quality=quality)['assessment']
        self.assertFalse(assessment['findings'])
        for name in ('delivery', 'quality'):
            current = assessment['dimension_results'][name]['current']
            self.assertIsNone(current['work_items']['completed'])
            self.assertIsNone(current['builds']['categories'])
            self.assertIsNone(current['builds']['known_terminal'])
            self.assertIsNone(current['categories']['priority']['counts'])
            self.assertIsNone(current['categories']['priority']['unknown'])
        quality['status'] = 'COMPLETE'
        current = compose(assessment_id='synthetic', system='atlas', windows=windows,
                          quality=quality)['assessment']['dimension_results']['quality']['current']
        self.assertEqual(current['work_items']['completed'], 0)
        self.assertEqual(current['categories']['priority']['counts'], {'P1': 0, 'P2': 0})
        self.assertIsNone(current['builds']['known_terminal'])

    def test_category_boundaries_and_legitimate_history_extensions(self) -> None:
        windows, _, quality = sources()
        b4 = deepcopy(quality['work_items'][3])
        b4.update(observation='previous-observation', history_end=public(windows.previous.end),
                  category_as_of=public(windows.previous.end), priority='P2')
        quality['work_items'].append(b4)
        result = compose(assessment_id='synthetic', system='atlas', windows=windows,
                         quality=quality)['assessment']['dimension_results']['quality']
        self.assertEqual(result['current']['categories']['priority']['counts'], {'P1': 3, 'P2': 3})
        self.assertEqual(result['previous']['categories']['priority']['counts'], {'P1': 0, 'P2': 1})
        self.assertEqual(result['previous']['categories']['priority']['availability'], 'PARTIAL')
        self.assertFalse(result['current']['work_items']['conflicts'])
        self.assertEqual(result['current']['work_items']['open_inventory'], 2)

    def test_mapping_exact_boundary_and_repository(self) -> None:
        windows, delivery, _ = sources()
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root / 'examples/v0.4-traceability-v3.json').read_text())
        refs = [a['artifact'] for a in report['traceability_evidence']['result']['artifacts'] if a['artifact']['kind'] == 'COMPONENT']
        record = delivery['work_items'][0]['reference']
        delivery.update(mapping_complete=True, mapping_revision=report['revision'])
        delivery['mappings'] = [{'record_ref': record, 'component_ref': ref, 'mapping_id': f'map-{i}',
                                 'origin': 'DECLARED_MAPPING', 'boundary': 'synthetic-base', 'completeness': 'COMPLETE'}
                                for i, ref in enumerate(refs[:2])]
        package = compose(assessment_id='synthetic', system='atlas', windows=windows, delivery=delivery, ecl_report=report)
        self.assertEqual(package['assessment']['dimension_results']['delivery']['mapping']['mapped'], 1)
        self.assertEqual(package['assessment']['dimension_results']['delivery']['mapping']['overlapping'], 1)
        self.assertEqual(import_package(canonical(package)), package)
        delivery['mappings'][0]['boundary'] = 'missing-boundary'
        result = compose(assessment_id='synthetic', system='atlas', windows=windows,
                         delivery=delivery, ecl_report=report)['assessment']['dimension_results']['delivery']['mapping']
        self.assertEqual(result['unresolved'], 1)
        delivery['populations']['work_items']['repository'] = 'another-repo'
        result = compose(assessment_id='synthetic', system='atlas', windows=windows,
                         delivery=delivery, ecl_report=report)['assessment']['dimension_results']['delivery']['mapping']
        self.assertEqual(result['mapped'], 0)

    def test_limits_before_analysis_and_privacy_before_output(self) -> None:
        windows, delivery, _ = sources()
        for field, value in (('publication_approved', False), ('alias', 'token=private'),
                             ('alias', '/Users/private'), ('status', 'password=private')):
            bad = deepcopy(delivery)
            bad[field] = value
            with self.assertRaisesRegex(ValueError, '^invalid engineering evidence$'):
                compose(assessment_id='synthetic', system='atlas', windows=windows, delivery=bad)
        events = tuple(Transition(f'e{i}', i, windows.current.start, State.OPEN, State.OPEN) for i in range(20001))
        base = Lifecycle(('WORK_ITEM', 'synthetic', 'atlas', 'project', 'limit'), 'observation',
                         windows.current.start, State.OPEN, windows.current.start, windows.current.end, True, events[:20000])
        second = replace(base, reference=(*base.reference[:4], 'second'))
        self.assertEqual(analyze_population((base, second), windows.current, enumeration_complete=True,
                                            created_start=True).open_inventory, 2)
        with self.assertRaises(ValueError):
            analyze_population((base, replace(second, transitions=events)), windows.current,
                               enumeration_complete=True, created_start=True)

    def test_missing_duration_suppresses_trend_and_finding(self) -> None:
        windows, delivery, _ = sources()
        # A known completion with no known episode start must not turn a
        # selected subset's median into a population comparison.
        record = delivery['work_items'][4]
        record['history_start'] = public(windows.current.start)
        record['created_at'] = None
        delivery['created_start'] = False
        for pr in delivery['pull_requests']:
            pr['created_at'] = None
        result = compose(assessment_id='synthetic', system='atlas', windows=windows,
                         delivery=delivery)['assessment']
        self.assertIsNone(result['dimension_results']['delivery']['median_trend']['relative'])
        self.assertNotIn('ER06', [f['rule_id'] for f in result['findings']])
