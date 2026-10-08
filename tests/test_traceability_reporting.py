"""Public report-v3 serialization tests using project-owned synthetic evidence."""
from copy import deepcopy
from dataclasses import replace
import unittest

from continuity.analysis.traceability import derive
from continuity.domain.reviews import CollectionStatus
from continuity.domain.traceability import TraceStatus
from continuity.reporting.traceability import (
    traceability_from_dict,
    traceability_from_json,
    traceability_to_dict,
    traceability_to_json,
    validate_report_envelope,
    with_traceability,
)
from continuity.traceability_providers.synthetic import SyntheticTraceabilityProvider, base_fixture


class TraceabilityReportingTests(unittest.TestCase):
    def setUp(self):
        self.report = derive(base_fixture())

    def test_base_report_round_trips_canonically_and_reproduces_metrics(self):
        payload = traceability_to_json(self.report)
        restored = traceability_from_json(payload)
        self.assertEqual(traceability_to_json(restored), payload)
        self.assertEqual(traceability_to_dict(restored)["schema_version"], "1.0")
        metrics = {(item.dimension, item.component.identifier if item.component else None):
                   (item.numerator, item.denominator) for item in restored.metrics}
        self.assertEqual(metrics[("merged_pr_intent", None)], (3, 4))
        self.assertEqual(metrics[("commit_intent", None)], (4, 4))
        self.assertEqual(metrics[("work_item_implementation", None)], (2, 3))
        self.assertEqual(metrics[("component_change_intent", "src/payments")], (2, 2))
        self.assertEqual(metrics[("component_change_intent", "tests/payments")], (1, 1))
        self.assertEqual(metrics[("component_change_intent", "src/catalog")], (1, 1))

    def test_v3_envelope_adds_traceability_without_changing_git_fields(self):
        original = {"model": "experimental-v0.1", "revision": "synthetic",
                "as_of": "2026-10-07T00:00:00+00:00", "commit_count": 0, "components": []}
        upgraded = with_traceability(original, self.report)
        self.assertEqual(upgraded["report_version"], "3.0")
        self.assertEqual(upgraded["model"], original["model"])
        self.assertEqual(upgraded["revision"], original["revision"])
        self.assertEqual(upgraded["components"], original["components"])

    def test_rejects_derived_metric_contradiction(self):
        value = traceability_to_dict(self.report)
        value["result"]["metrics"][0]["numerator"] += 1
        with self.assertRaises(ValueError):
            traceability_from_dict(value)

    def test_normalized_input_permutations_have_identical_bytes(self):
        evidence = self.report.evidence
        shuffled = replace(
            evidence,
            boundaries=tuple(reversed(evidence.boundaries)),
            work_items=tuple(reversed(evidence.work_items)),
            pull_requests=tuple(reversed(evidence.pull_requests)),
            merged_pull_requests=tuple(reversed(evidence.merged_pull_requests)),
            commits=tuple(reversed(evidence.commits)),
            changed_paths=tuple(reversed(evidence.changed_paths)),
            links=tuple(reversed(evidence.links)),
            lookups=tuple(reversed(evidence.lookups)),
            diagnostics=tuple(reversed(evidence.diagnostics)),
        )
        self.assertEqual(traceability_to_json(derive(shuffled)), traceability_to_json(self.report))

    def test_direct_and_derived_links_keep_distinct_origins_and_supports(self):
        restored = traceability_from_dict(traceability_to_dict(self.report))
        self.assertTrue(all(link.origin.value != "DERIVED_LINK" for link in restored.direct_links))
        self.assertTrue(all(link.origin.value == "DERIVED_LINK" and link.supports
                            for link in restored.derived_links))
        self.assertTrue(any(link.type.value == "WI_COMPONENT" for link in restored.derived_links))
        self.assertTrue(all(path.supports for path in restored.paths if path.status == TraceStatus.VERIFIED))

    def test_partial_and_failed_collections_keep_independent_statuses(self):
        partial = derive(SyntheticTraceabilityProvider("PARTIAL").acquire())
        failed = derive(SyntheticTraceabilityProvider("FAILED").acquire())
        self.assertEqual(traceability_to_json(traceability_from_dict(traceability_to_dict(partial))),
                         traceability_to_json(partial))
        self.assertEqual(failed.evidence.status, CollectionStatus.FAILED)
        self.assertEqual(failed.summary, TraceStatus.UNAVAILABLE)
        self.assertEqual(traceability_to_json(traceability_from_dict(traceability_to_dict(failed))),
                         traceability_to_json(failed))

    def test_pr_snapshot_short_path_round_trips_without_commit_change_units(self):
        report = derive(SyntheticTraceabilityProvider("PR_PATH_ONLY").acquire())
        restored = traceability_from_dict(traceability_to_dict(report))
        self.assertEqual(traceability_to_json(restored), traceability_to_json(report))
        self.assertTrue(any(node.kind.value == "PR_PATH" for path in restored.paths for node in path.nodes))
        self.assertTrue(all(node.kind.value != "COMMIT" for path in restored.paths
                            if any(node.kind.value == "PR_PATH" for node in path.nodes)
                            for node in path.nodes))
        before = next(metric for metric in derive(base_fixture()).metrics if metric.dimension == "commit_intent")
        after = next(metric for metric in restored.metrics if metric.dimension == "commit_intent")
        self.assertEqual((after.numerator, after.denominator), (before.numerator, before.denominator))

    def test_rejects_unknown_schema_types_and_noncanonical_or_unsafe_evidence(self):
        mutations = (
            lambda value: value.update(schema_version="2.0"),
            lambda value: value.update(unknown_field=True),
            lambda value: value["collection"]["populations"]["commits"][0].update(kind="FUTURE_COMMIT"),
            lambda value: value["collection"]["observed_links"][0].update(type="FUTURE_RELATION"),
            lambda value: value["collection"]["observed_links"][0].update(origin="DERIVED_LINK"),
            lambda value: value["collection"]["observed_links"][0]["target"].update(
                value["collection"]["populations"]["commits"][0]),
            lambda value: value["collection"]["lookups"][0].update(capability="FUTURE_CAPABILITY"),
            lambda value: value["collection"]["boundaries"][0].update(identifier="missing-boundary"),
            lambda value: value["collection"]["boundaries"][0].update(
                query="https://user:SECRET@example.invalid/repo"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                value = deepcopy(traceability_to_dict(self.report))
                mutate(value)
                with self.assertRaises(ValueError) as caught:
                    traceability_from_dict(value)
                self.assertNotIn("SECRET", str(caught.exception))

    def test_private_optional_work_item_fields_are_not_serialized(self):
        evidence = base_fixture()
        private_item = replace(evidence.work_items[0], title="PRIVATE_CUSTOMER_SECRET", title_approved=True)
        report = derive(replace(evidence, work_items=(private_item, *evidence.work_items[1:])))
        payload = traceability_to_json(report)
        self.assertNotIn("PRIVATE_CUSTOMER_SECRET", payload)
        restored = traceability_from_json(payload)
        self.assertTrue(all(item.title is None and item.created_at is None for item in restored.evidence.work_items))

    def test_missing_gap_requires_a_qualified_complete_lookup(self):
        value = traceability_to_dict(self.report)
        missing = next(gap for gap in value["result"]["gaps"] if gap["status"] == "MISSING")
        value["collection"]["lookups"] = [lookup for lookup in value["collection"]["lookups"]
                                            if not (lookup["endpoint"] == missing["endpoint"]
                                                    and lookup["relationship"] == missing["relationship"]
                                                    and lookup["direction"] == missing["direction"])]
        with self.assertRaises(ValueError):
            traceability_from_dict(value)

    def test_rejects_duplicate_paths_bad_support_and_inconsistent_gaps(self):
        mutations = (
            lambda value: value["result"]["paths"].append(deepcopy(value["result"]["paths"][0])),
            lambda value: value["result"]["paths"][0]["nodes"].append(
                deepcopy(value["result"]["paths"][0]["nodes"][0])),
            lambda value: value["result"]["derived_links"][0]["supports"].clear(),
            lambda value: value["result"]["gaps"][0].update(status="VERIFIED"),
            lambda value: value["result"]["direct_links"][0].update(type="FUTURE_RELATION"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                value = deepcopy(traceability_to_dict(self.report))
                mutate(value)
                with self.assertRaises(ValueError):
                    traceability_from_dict(value)

    def test_rejects_metric_arithmetic_null_and_boundary_contradictions(self):
        mutations = (
            lambda metric: metric.update(numerator=metric["denominator"] + 1),
            lambda metric: metric.update(value=0.25),
            lambda metric: metric.update(denominator=0, value=0),
            lambda metric: metric.update(boundaries=["unknown-boundary"]),
            lambda metric: metric.update(unknown_count=-1),
            lambda metric: metric.update(excluded_count=-1),
        )
        for mutate in mutations:
            value = deepcopy(traceability_to_dict(self.report))
            mutate(value["result"]["metrics"][0])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                traceability_from_dict(value)

    def test_envelope_preserves_v1_v2_and_combined_v3_sections(self):
        git = {"model": "experimental-v0.1", "revision": "synthetic",
             "as_of": "2026-10-07T00:00:00+00:00", "commit_count": 0, "components": []}
        self.assertIs(validate_report_envelope(git), git)
        v2 = {**git, "report_version": "2.0", "review_evidence": {"unchanged": True}}
        self.assertIs(validate_report_envelope(v2), v2)
        combined = with_traceability(v2, self.report)
        self.assertEqual(combined["review_evidence"], v2["review_evidence"])
        self.assertEqual(combined["model"], "experimental-v0.1")
        self.assertIs(validate_report_envelope({**git, "report_version": "3.0"})["components"], git["components"])
        for invalid in (
            {**git, "report_version": "4.0"},
            {**git, "report_version": None},
            {**git, "model": "experimental-v0.2", "report_version": "3.0"},
            {**git, "report_version": "2.0", "traceability_evidence": traceability_to_dict(self.report)},
            {**git, "model": "experimental-v0.2", "report_version": "3.0",
             "traceability_evidence": traceability_to_dict(self.report)},
            {**git, "review_evidence": {}},
        ):
            with self.assertRaises(ValueError):
                validate_report_envelope(invalid)

    def test_json_rejects_nonfinite_values_without_reflecting_input(self):
        with self.assertRaisesRegex(ValueError, "invalid traceability JSON"):
            traceability_from_json('{"schema_version":"1.0","collection":NaN,"result":{}}')


if __name__ == "__main__":
    unittest.main()