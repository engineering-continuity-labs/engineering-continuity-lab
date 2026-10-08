"""Corrective regression evidence for the independent report-v3 review."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import unittest

from continuity.analysis.traceability import derive
from continuity.domain.traceability import TraceabilityCapability, TraceDiagnostic, GapReason
from continuity.reporting.traceability import traceability_from_dict, traceability_from_json, traceability_to_dict, traceability_to_json
from continuity.traceability_providers.synthetic import base_fixture, SyntheticTraceabilityProvider
from traceability_report_adversaries import adversarial_reports, normalization_adversaries, additional_valid_reports

VARIANTS = ['BASE', 'NO_INTENT', 'DIRECT_ONLY', 'MULTIPATH', 'DUPLICATES', 'CONFLICT', 'CYCLE',
            'MALFORMED', 'UNSUPPORTED_TYPE', 'OPTIONAL', 'PARTIAL', 'POSITIVE_PARTIAL', 'LATE_FAILURE',
            'FAILED', 'CAPABILITY', 'EMPTY', 'LINKED_ONLY', 'BOUNDARY', 'PR_PATH_ONLY', 'NO_INFERENCE']


class IndependentReviewRegressionTests(unittest.TestCase):
    def test_shared_adversarial_wire_corpus_rejected_with_fixed_errors(self):
        for name, value in {**adversarial_reports(), **normalization_adversaries()}.items():
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, '^invalid traceability report$'):
                traceability_from_dict(value['traceability_evidence'])

    def test_all_synthetic_variants_reconstruct_their_evidence(self):
        for name in VARIANTS:
            with self.subTest(name=name):
                report = derive(SyntheticTraceabilityProvider(name).acquire())
                payload = traceability_to_json(report)
                self.assertEqual(traceability_to_json(traceability_from_json(payload)), payload)

    def test_export_rejects_unknown_boundary_even_when_derivation_accepts_it(self):
        evidence = base_fixture()
        report = derive(replace(evidence, lookups=tuple(replace(l, boundary='ghost', capability=TraceabilityCapability.UNSUPPORTED) for l in evidence.lookups)))
        with self.assertRaisesRegex(ValueError, 'unresolved lookup boundary'):
            traceability_to_dict(report)

    def test_export_rejects_credential_shaped_provenance_in_each_boundary_alias(self):
        evidence = base_fixture()
        for field in ['identifier', 'provider', 'instance', 'project', 'repository', 'snapshot', 'query',
                      'identity_mapping', 'filter_policy', 'time_field', 'normalization_version', 'join_contract']:
            with self.subTest(field=field):
                boundary = replace(evidence.boundaries[0], **{field:'ghp_'+'A'*36})
                # Empty population keeps all other references out of the privacy oracle.
                report = derive(replace(evidence, boundaries=(boundary,), work_items=(), pull_requests=(),
                                        merged_pull_requests=(), commits=(), changed_paths=(), links=(), lookups=()))
                with self.assertRaises(ValueError) as error:
                    traceability_to_dict(report)
                self.assertNotIn('ghp_', str(error.exception))

    def test_unknown_capability_and_diagnostics_round_trip(self):
        evidence = base_fixture()
        for value in [replace(evidence, lookups=tuple(replace(l, capability=TraceabilityCapability.UNKNOWN) for l in evidence.lookups)),
                      replace(evidence, diagnostics=(TraceDiagnostic(GapReason.INVALID_OBSERVATION),))]:
            payload = traceability_to_json(derive(value))
            self.assertEqual(traceability_to_json(traceability_from_json(payload)), payload)

    def test_canonical_bytes_for_individually_permuted_domain_collections(self):
        evidence = derive(SyntheticTraceabilityProvider('DUPLICATES').acquire()).evidence
        expected = traceability_to_json(derive(evidence))
        for field in ['boundaries', 'work_items', 'pull_requests', 'merged_pull_requests', 'commits',
                      'changed_paths', 'links', 'lookups', 'diagnostics']:
            with self.subTest(field=field):
                self.assertEqual(traceability_to_json(derive(replace(evidence, **{field:tuple(reversed(getattr(evidence, field)))}))), expected)
        report = derive(evidence)
        for field in ['direct_links', 'derived_links', 'paths', 'gaps', 'artifacts', 'metrics', 'diagnostics']:
            with self.subTest(field=field):
                self.assertEqual(traceability_to_json(replace(report, **{field:tuple(reversed(getattr(report, field)))})), expected)
        links = tuple(replace(link, observations=tuple(reversed(link.observations))) for link in evidence.links)
        self.assertEqual(traceability_to_json(derive(replace(evidence, links=links))), expected)

    def test_json_duplicate_fields_nonfinite_and_deep_input_have_sanitized_errors(self):
        payload = traceability_to_json(derive(base_fixture()))
        for value in [payload.replace('"schema_version":"1.0"', '"schema_version":"SECRET","schema_version":"1.0"'),
                      payload.replace('"schema_version":"1.0"', '"schema_version":"1.0","schema_vers\\u0069on":"1.0"'),
                      '{"SECRET":Infinity}', '['*2000+']'*2000, '{"SECRET":', '{"schema_version":NaN}']:
            with self.subTest(value=value[:40]), self.assertRaisesRegex(ValueError, '^invalid traceability (JSON|report)$'):
                traceability_from_json(value)

    def test_precise_valid_timestamps_and_dictionary_insertion_order(self):
        evidence = base_fixture()
        for stamp in [datetime(2024, 2, 29, 23, 59, 59, 123456, timezone.utc),
                      datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=5, minutes=30)))]:
            report = derive(replace(evidence, boundaries=(replace(evidence.boundaries[0], collected_at=stamp),)))
            payload = traceability_to_json(report)
            self.assertEqual(traceability_to_json(traceability_from_json(payload)), payload)
        def reverse_dict(value):
            if isinstance(value, dict):
                return {key:reverse_dict(child) for key, child in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse_dict(child) for child in value]
            return value
        section = traceability_to_dict(derive(evidence))
        self.assertEqual(traceability_to_json(traceability_from_dict(reverse_dict(section))), traceability_to_json(derive(evidence)))

    def test_multiboundary_diagnostics_and_timezone_representations_are_byte_stable(self):
        richer = additional_valid_reports()
        for name, field in [('COMPATIBLE_BOUNDARIES', 'boundaries'), ('DIAGNOSTICS', 'diagnostics')]:
            report = traceability_from_dict(richer[name]['traceability_evidence'])
            evidence = replace(report.evidence, **{field:tuple(reversed(getattr(report.evidence, field)))})
            self.assertEqual(traceability_to_json(derive(evidence)), traceability_to_json(report))
        evidence = base_fixture()
        boundary = evidence.boundaries[0]
        alternate = replace(boundary, collected_at=boundary.collected_at.astimezone(timezone(timedelta(hours=5, minutes=30))))
        self.assertEqual(traceability_to_json(derive(replace(evidence, boundaries=(boundary, alternate)))), traceability_to_json(derive(replace(evidence, boundaries=(alternate, boundary)))))
        self.assertEqual(traceability_to_json(derive(replace(evidence, boundaries=(alternate,)))), traceability_to_json(derive(evidence)))

    def test_richer_boundaries_unicode_and_calendar_fixtures_round_trip(self):
        for name, value in additional_valid_reports().items():
            with self.subTest(name=name):
                restored = traceability_from_dict(value['traceability_evidence'])
                expected = additional_valid_reports()['UNKNOWN']['traceability_evidence'] if name=='ISO_Z' else value['traceability_evidence']
                self.assertEqual(traceability_to_dict(restored), expected)

    def test_base_counts_reproduced_from_links_without_serialized_metrics(self):
        evidence = base_fixture()
        wi_pr = [l for l in evidence.links if l.type.value=='WI_PR']
        intent_prs = {l.target for l in wi_pr}
        intent_commits = {l.target for l in evidence.links if l.type.value=='WI_COMMIT'} | {l.target for l in evidence.links if l.type.value=='PR_COMMIT' and l.source in intent_prs}
        implemented = {l.source for l in evidence.links if l.type.value=='WI_COMMIT' and l.target in intent_commits}
        for link in wi_pr:
            if any(c.type.value=='PR_COMMIT' and c.source==link.target and any(p.type.value=='COMMIT_PATH' and p.source==c.target for p in evidence.links) for c in evidence.links):
                implemented.add(link.source)
        self.assertEqual((len(intent_prs & set(evidence.merged_pull_requests)), len(evidence.merged_pull_requests)), (3,4))
        self.assertEqual((len(intent_commits & set(evidence.commits)), len(evidence.commits)), (4,4))
        self.assertEqual((len(implemented), len(evidence.work_items)), (2,3))
        component_counts = {}
        for link in evidence.links:
            if link.type.value=='COMMIT_PATH':
                component = '/'.join(link.target.identifier.split('/')[:-1][:2])
                covered, total = component_counts.get(component, (0,0))
                component_counts[component] = (covered+int(link.source in intent_commits),total+1)
        self.assertEqual(component_counts, {'src/payments':(2,2),'tests/payments':(1,1),'src/catalog':(1,1)})

    def test_closure_configuration_token_length_boundary(self):
        from traceability_report_adversaries import closure_review_reports
        reports = closure_review_reports()
        traceability_from_dict(reports['valid']['RP-R11']['traceability_evidence'])
        with self.assertRaisesRegex(ValueError, '^invalid traceability report$'):
            traceability_from_dict(reports['invalid']['RP-R11']['traceability_evidence'])

    def test_closure_population_direction_preserves_unavailable_and_dual_states(self):
        from traceability_report_adversaries import closure_review_reports
        reports = closure_review_reports()
        for name in ('RP-R12', 'RP-R12-DUAL'):
            report = traceability_from_dict(reports['valid'][name]['traceability_evidence'])
            self.assertEqual(traceability_to_dict(report), reports['valid'][name]['traceability_evidence'])
        with self.assertRaisesRegex(ValueError, '^invalid traceability report$'):
            traceability_from_dict(reports['invalid']['RP-R12']['traceability_evidence'])

    def test_closure_scoped_incompatibility_does_not_invent_global_unavailability(self):
        from traceability_report_adversaries import closure_review_reports
        reports = closure_review_reports()
        traceability_from_dict(reports['valid']['RP-R13']['traceability_evidence'])
        with self.assertRaisesRegex(ValueError, '^invalid traceability report$'):
            traceability_from_dict(reports['invalid']['RP-R13']['traceability_evidence'])
