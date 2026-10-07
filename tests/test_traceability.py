"""Offline acceptance evidence; SYNTHETIC values only, no transport or schema v3."""
from dataclasses import asdict, fields, replace
from datetime import datetime, timezone
import json
import random
import unittest
from unittest.mock import patch

from continuity.analysis.traceability import aggregate_status, derive, normalize, project_history, project_reviews
from continuity.domain.models import Author, Change, Commit, DirectoryComponents, History
from continuity.domain.reviews import (CollectionStatus, ProviderProvenance, PullRequestEvidence,
                                       ReviewEvidenceCollection, ReviewIdentity)
from continuity.domain.traceability import (
    ArtifactKind as K, ArtifactReference as Ref, Direction as D, EvidenceBoundary,
    GapReason as R, LookupEvidence, Observation, Population as P, TraceDiagnostic,
    TraceLink, TraceLinkOrigin as O, TraceLinkType as T, TraceStatus as S,
    TraceabilityCapability as C, WorkItemEvidence, WorkItemState, WorkItemType,
)
from continuity.traceability_providers.synthetic import (
    SYNTHETIC, STAMP, SyntheticTraceabilityProvider, base_fixture,
    isolate_invalid_fixture_record, observation, reference,
)


def metric(report, name, component=None):
    return next(m for m in report.metrics if m.dimension == name and
                (component is None or m.component.identifier == component))


def encoded(report):
    return json.dumps(asdict(report), sort_keys=True, default=lambda v: v.isoformat(), separators=(",", ":"))


class TraceabilityDomainTests(unittest.TestCase):
    def test_ac301_minimum_immutable_work_item(self):
        item = base_fixture().work_items[0]
        self.assertEqual(item.reference.identifier, "1001")
        self.assertEqual(item.type, WorkItemType.STORY)
        self.assertEqual(item.state, WorkItemState.ACTIVE)
        self.assertEqual({f.name for f in fields(item)}, {"reference", "type", "state", "provenance", "title",
                                                        "title_approved", "created_at", "changed_at", "closed_at"})
        with self.assertRaises(AttributeError):
            item.title = "changed"

    def test_ac317_invalid_scoped_identifiers_are_safe_errors(self):
        for value in ("", "  ", "https://user:SECRET@example.invalid", "../tmp/SECRET", "id\nSECRET", "a" * 129):
            with self.subTest(value=value), self.assertRaises(ValueError) as caught:
                reference(K.WORK_ITEM, value)
            self.assertNotIn("SECRET", str(caught.exception))

    def test_ac324_valid_pr_and_exact_commit_scope(self):
        pr = reference(K.PULL_REQUEST, "51")
        self.assertEqual(pr.repository, "demo-system")
        self.assertNotEqual(pr, replace(pr, instance="another-instance"))
        self.assertNotEqual(pr, replace(pr, repository="another-repository", scope="another-repository"))
        wi = reference(K.WORK_ITEM, "1001")
        self.assertNotEqual(wi, replace(wi, scope="another-project"))
        commit = reference(K.COMMIT, "a" * 40)
        self.assertEqual(commit, replace(commit, provider="another-observer"))
        self.assertEqual(hash(commit), hash(replace(commit, provider="another-observer")))
        self.assertNotEqual(commit, replace(commit, repository="another-repository"))
        for value in ("abc123", "A" * 40, "g" * 40, ""):
            with self.assertRaises(ValueError):
                reference(K.COMMIT, value)
        self.assertEqual(replace(commit, identifier="a" * 64, algorithm="sha256").algorithm, "sha256")

    def test_ac317_invalid_paths_and_context(self):
        for value in ("/tmp/secret", "../secret", "src/../secret", "src//file", "C:\\secret", "file\x00x"):
            with self.assertRaises(ValueError):
                reference(K.CHANGED_PATH, value, "a" * 40)
        with self.assertRaises(ValueError):
            reference(K.CHANGED_PATH, "src/file.py", "abc123")
        a = reference(K.CHANGED_PATH, "src/file.py", "a" * 40)
        self.assertNotEqual(a, replace(a, context="b" * 40))

    def test_ac317_invalid_timestamp_and_interval(self):
        with self.assertRaises(ValueError):
            Observation("safe", "safe", datetime(2026, 1, 1), "safe")
        boundary = base_fixture().boundaries[0]
        with self.assertRaises(ValueError):
            replace(boundary, start=STAMP, end=STAMP, time_field="created")
        with self.assertRaises(ValueError):
            replace(boundary, start=STAMP)
        with self.assertRaises(ValueError):
            replace(base_fixture().work_items[0], changed_at=datetime(2026, 1, 1))

    def test_ac319_missing_optional_fields_do_not_change_links(self):
        report = derive(SyntheticTraceabilityProvider("OPTIONAL").acquire())
        self.assertEqual(metric(report, "commit_intent").value, 1)
        self.assertEqual(report.evidence.status, CollectionStatus.COMPLETE)
        self.assertTrue(all(w.title is None and w.type == WorkItemType.UNKNOWN for w in report.evidence.work_items))

    def test_ac331_title_requires_explicit_approval(self):
        with self.assertRaises(ValueError) as caught:
            replace(base_fixture().work_items[0], title="SYNTHETIC_SECRET", title_approved=False)
        self.assertNotIn("SYNTHETIC_SECRET", str(caught.exception))
        with self.assertRaises(TypeError):
            WorkItemEvidence(reference(K.WORK_ITEM, "1001"), WorkItemType.STORY, WorkItemState.OPEN,
                             observation("wi"), assignee="SYNTHETIC_SECRET")

    def test_ac331_safe_provenance_and_diagnostics(self):
        boundary = base_fixture().boundaries[0]
        for field in ("identifier", "provider", "instance", "repository", "query", "identity_mapping", "snapshot"):
            with self.assertRaises(ValueError) as caught:
                replace(boundary, **{field: "https://user:SYNTHETIC_SECRET@invalid/?token=SECRET"})
            self.assertNotIn("SECRET", str(caught.exception))
        with self.assertRaises(ValueError):
            TraceDiagnostic("SYNTHETIC_SECRET")
        self.assertFalse({"headers", "raw_response", "token", "password", "cookies", "local_path"} &
                         {f.name for f in fields(boundary)})


class TraceabilityDerivationTests(unittest.TestCase):
    def setUp(self):
        self.e = base_fixture()
        self.r = derive(self.e)

    def variant(self, name):
        return derive(SyntheticTraceabilityProvider(name).acquire())

    def test_ac302_direct_association_provenance(self):
        link = next(l for l in self.r.direct_links if l.source == self.e.work_items[0].reference
                    and l.target == self.e.pull_requests[0])
        self.assertEqual(link.type, T.WI_PR)
        self.assertEqual(link.origin, O.DIRECT_PROVIDER_LINK)
        self.assertEqual(link.observations[0].boundary, "synthetic-base")
        self.assertEqual(link.observations[0].observed_at, STAMP)

    def test_ac303_multiple_work_items_and_prs(self):
        wi_links = [l for l in self.r.direct_links if l.type == T.WI_PR]
        self.assertEqual(len([l for l in wi_links if l.source == self.e.work_items[0].reference]), 2)
        self.assertEqual(len([l for l in wi_links if l.target == self.e.pull_requests[0]]), 2)
        self.assertEqual(metric(self.r, "merged_pr_intent").numerator, 3)

    def test_ac304_pr_multiple_commits(self):
        links = [l for l in self.r.direct_links if l.type == T.PR_COMMIT and l.source == self.e.pull_requests[0]]
        self.assertEqual({l.target for l in links}, set(self.e.commits[:2]))

    def test_ac305_direct_commit_does_not_backfill_pr(self):
        self.assertEqual(metric(self.r, "commit_intent").numerator, 4)
        self.assertFalse(any(l.type == T.WI_PR and l.target == self.e.pull_requests[1] for l in self.r.direct_links))
        paths = [p for p in self.r.paths if p.nodes[0] == self.e.work_items[1].reference and self.e.commits[2] in p.nodes]
        self.assertTrue(paths)
        self.assertTrue(all(p.status == S.PARTIAL for p in paths))
        self.assertTrue(all(p.gaps for p in paths))

    def test_ac306_existing_component_strategy_and_origins(self):
        self.assertTrue(all(l.origin == O.DIRECT_SOURCE_LINK for l in self.r.direct_links if l.type == T.COMMIT_PATH))
        mapping = next(l for l in self.r.derived_links if l.source == self.e.changed_paths[0])
        self.assertEqual(mapping.target.identifier, DirectoryComponents(depth=2).component(mapping.source.identifier))
        self.assertEqual(mapping.target.configuration, "depth-2")
        self.assertEqual(mapping.origin, O.DERIVED_LINK)
        self.assertTrue(mapping.supports)
        self.assertTrue(all(l.supports for l in self.r.derived_links if l.type == T.WI_COMPONENT))

    def test_ac307_multiple_components_distinct_occurrences(self):
        r = self.variant("MULTIPATH")
        self.assertEqual((metric(r, "component_change_intent", "src/catalog").numerator,
                          metric(r, "component_change_intent", "src/catalog").denominator), (2, 2))
        self.assertEqual(metric(r, "commit_intent").denominator, 4)
        self.assertEqual(len({l.target for l in r.derived_links if l.source.context == "a" * 40}), 2)

    def test_ac308_full_verified_path_has_ordered_support(self):
        full = next(p for p in self.r.paths if p.status == S.VERIFIED)
        self.assertEqual(tuple(n.kind for n in full.nodes), (K.WORK_ITEM, K.PULL_REQUEST, K.COMMIT, K.CHANGED_PATH, K.COMPONENT))
        self.assertEqual(len(full.supports), 4)
        self.assertEqual(full.boundaries, ("synthetic-base",))
        self.assertFalse(full.gaps)
        origins = tuple(key[-1] for key in full.supports)
        self.assertEqual(origins, (O.DIRECT_PROVIDER_LINK, O.DIRECT_PROVIDER_LINK, O.DIRECT_SOURCE_LINK, O.DERIVED_LINK))

    def test_ac309_pr_missing_work_item_despite_commit_intent(self):
        gap = next(g for g in self.r.gaps if g.endpoint == self.e.pull_requests[1] and g.relationship == T.WI_PR)
        self.assertEqual((gap.status, gap.reason), (S.MISSING, R.NO_OBSERVED_LINK))
        self.assertEqual(metric(self.r, "commit_intent").value, 1)

    def test_ac310_direct_only_path_has_missing_pr_segment(self):
        r = self.variant("DIRECT_ONLY")
        path = next(p for p in r.paths if p.nodes[0].kind == K.WORK_ITEM and p.nodes[-1].kind == K.COMPONENT)
        self.assertEqual(path.status, S.PARTIAL)
        self.assertTrue(any(g.relationship == T.WI_PR and g.status == S.MISSING for g in path.gaps))
        self.assertFalse(any(p.status == S.VERIFIED for p in r.paths))
        self.assertEqual(r.summary, S.MISSING)

    def test_ac311_linked_pr_without_commits(self):
        path = next(p for p in self.r.paths if p.nodes[0] == self.e.work_items[0].reference and p.nodes[-1] == self.e.pull_requests[3])
        self.assertEqual(path.status, S.PARTIAL)
        self.assertTrue(any(g.relationship == T.PR_COMMIT and g.status == S.MISSING for g in path.gaps))
        self.assertEqual(sum(m.denominator for m in self.r.metrics if m.component), 4)

    def test_ac312_independently_enumerated_unimplemented_work_item(self):
        result = next(a for a in self.r.artifacts if a.artifact == self.e.work_items[2].reference)
        self.assertEqual(result.status, S.MISSING)
        self.assertEqual({g.relationship for g in result.gaps}, {T.WI_PR, T.WI_COMMIT})
        self.assertEqual(metric(self.r, "work_item_implementation").denominator, 3)

    def test_ac313_missing_commit_intent_retains_denominator(self):
        r = self.variant("NO_INTENT")
        self.assertEqual((metric(r, "commit_intent").numerator, metric(r, "commit_intent").denominator), (3, 4))
        self.assertEqual(metric(r, "component_change_intent", "src/catalog").value, 0)
        self.assertTrue(any(g.endpoint == self.e.commits[2] and g.status == S.MISSING for g in r.gaps))

    def test_ac314_duplicates_and_alternate_routes_do_not_inflate_metrics(self):
        r = self.variant("DUPLICATES")
        self.assertEqual([(m.numerator, m.denominator) for m in r.metrics], [(m.numerator, m.denominator) for m in self.r.metrics])
        self.assertGreater(len(r.paths), len(self.r.paths))
        link = next(l for l in r.direct_links if l.key == self.e.links[0].key)
        self.assertEqual(len(link.observations), 2)
        self.assertEqual(normalize(r.evidence), r.evidence)

    def test_ac315_conflicts_quarantined_order_independently(self):
        e = SyntheticTraceabilityProvider("CONFLICT").acquire()
        r = derive(e)
        self.assertFalse(any(l.observations[0].identifier == "link-0" for l in r.direct_links))
        self.assertTrue(any(d.reason == R.CONFLICTING_OBSERVATION for d in r.diagnostics))
        lookup = next(l for l in r.evidence.lookups if l.endpoint == e.work_items[0].reference and l.relationship == T.WI_PR)
        self.assertEqual(lookup.status, CollectionStatus.PARTIAL)
        self.assertEqual(encoded(r), encoded(derive(replace(e, links=tuple(reversed(e.links))))))

    def test_ac316_cycles_cannot_create_authoritative_paths(self):
        e = self.e
        reverse = TraceLink(e.pull_requests[0], e.work_items[0].reference, T.WI_PR, O.DIRECT_PROVIDER_LINK, (observation("reverse"),))
        self_link = replace(reverse, source=e.work_items[0].reference)
        r = derive(replace(e, links=e.links + (reverse, self_link)))
        self.assertTrue(r.diagnostics)
        self.assertTrue(all(len(p.nodes) <= 5 and len(set(p.nodes)) == len(p.nodes) for p in r.paths))
        self.assertEqual([(m.numerator, m.denominator) for m in r.metrics], [(m.numerator, m.denominator) for m in self.r.metrics])

    def test_ac317_malformed_endpoint_isolated(self):
        bad = replace(self.e.links[0], target=self.e.commits[0])
        r = derive(replace(self.e, links=self.e.links + (bad,)))
        self.assertNotIn(bad, r.direct_links)
        self.assertTrue(any(d.reason == R.INVALID_OBSERVATION for d in r.diagnostics))
        self.assertEqual(r.evidence.status, CollectionStatus.PARTIAL)
        isolated = isolate_invalid_fixture_record(self.e, endpoint=self.e.work_items[0].reference, relationship=T.WI_PR)
        self.assertEqual(derive(isolated).evidence.status, CollectionStatus.PARTIAL)

    def test_ac318_unsupported_and_derived_input_rejected(self):
        r = self.variant("UNSUPPORTED_TYPE")
        self.assertTrue(any(d.reason == R.UNSUPPORTED_RELATION for d in r.diagnostics))
        self.assertFalse(any(l.type == T.WI_COMPONENT for l in r.direct_links))
        forged = replace(self.e.links[0], origin=O.DERIVED_LINK)
        r = derive(replace(self.e, links=(forged,)))
        self.assertFalse(r.direct_links)
        self.assertFalse(any(p.status == S.VERIFIED for p in r.paths))

    def test_ac320_interrupted_lookup_is_partial_not_missing(self):
        r = self.variant("PARTIAL")
        gap = next(g for g in r.gaps if g.endpoint == self.e.pull_requests[3] and g.relationship == T.PR_COMMIT)
        self.assertEqual((gap.status, gap.reason), (S.PARTIAL, R.INCOMPLETE_LOOKUP))
        self.assertEqual(metric(r, "commit_intent").status, S.PARTIAL)
        self.assertEqual(metric(r, "commit_intent").value, 1)

    def test_ac321_failed_population_unavailable_no_zero_ratio(self):
        r = self.variant("FAILED")
        self.assertEqual(r.evidence.status, CollectionStatus.FAILED)
        self.assertEqual(r.summary, S.UNAVAILABLE)
        self.assertTrue(all(m.value is None and m.status == S.UNAVAILABLE for m in r.metrics))
        late = derive(replace(self.e, status=CollectionStatus.FAILED))
        self.assertEqual(late.evidence.status, CollectionStatus.PARTIAL)
        self.assertTrue(any(p.status == S.VERIFIED for p in late.paths))

    def test_ac322_capability_unsupported_and_unknown(self):
        for capability in (C.UNSUPPORTED, C.UNKNOWN):
            e = replace(self.e, lookups=tuple(replace(l, capability=capability) if l.relationship == T.PR_COMMIT else l for l in self.e.lookups))
            r = derive(e)
            self.assertIsNone(metric(r, "commit_intent").value)
            gap = next(g for g in r.gaps if g.endpoint == self.e.pull_requests[3] and g.relationship == T.PR_COMMIT)
            self.assertEqual((gap.status, gap.reason), (S.UNAVAILABLE, R.CAPABILITY_UNAVAILABLE))
            self.assertTrue(any(p.status == S.VERIFIED for p in r.paths))
        self.assertIsNone(metric(self.variant("CAPABILITY"), "commit_intent").value)

    def test_ac323_all_input_permutations_are_canonical(self):
        original = encoded(self.r)
        rng = random.Random(301)
        for _ in range(12):
            changed = {}
            for name in ("work_items", "pull_requests", "merged_pull_requests", "commits", "changed_paths", "links", "lookups", "boundaries"):
                values = list(getattr(self.e, name))
                rng.shuffle(values)
                changed[name] = tuple(values)
            self.assertEqual(encoded(derive(replace(self.e, **changed))), original)

    def test_ac324_other_instance_cannot_join_by_native_id(self):
        wrong = replace(self.e.links[0], source=replace(self.e.work_items[0].reference, instance="another-instance"))
        r = derive(replace(self.e, links=(wrong,) + self.e.links[1:]))
        self.assertNotIn(wrong, r.direct_links)
        self.assertTrue(any(d.reason == R.INCOMPATIBLE_BOUNDARY for d in r.diagnostics))

    def test_ac325_outside_git_boundary_keeps_ref_excludes_counts(self):
        r = self.variant("BOUNDARY")
        self.assertTrue(any(l.target == self.e.commits[3] for l in r.direct_links))
        self.assertFalse(any(self.e.commits[3] in p.nodes for p in r.paths))
        self.assertEqual(metric(r, "commit_intent").denominator, 3)
        self.assertGreater(metric(r, "commit_intent").excluded_count, 0)
        self.assertTrue(any(d.reason == R.OUTSIDE_BOUNDARY for d in r.diagnostics))

    def test_ac325_incompatible_alias_mapping_disables_joins(self):
        boundary = replace(self.e.boundaries[0], identifier="other-snapshot", identity_mapping="other-alias-map")
        r = derive(replace(self.e, boundaries=self.e.boundaries + (boundary,)))
        self.assertIsNone(metric(r, "commit_intent").value)
        self.assertFalse(any(p.status == S.VERIFIED for p in r.paths))
        with self.assertRaises(ValueError):
            derive(self.e, DirectoryComponents(depth=1))

    def test_ac326_exact_base_coverage_oracles(self):
        expected = {"merged_pr_intent": (3, 4), "commit_intent": (4, 4), "work_item_implementation": (2, 3)}
        for name, counts in expected.items():
            m = metric(self.r, name)
            self.assertEqual((m.numerator, m.denominator), counts)
            self.assertEqual(m.value, counts[0] / counts[1])
            self.assertEqual(m.collection_status, CollectionStatus.COMPLETE)
            self.assertEqual(m.boundaries, ("synthetic-base",))
            self.assertEqual(m.sources, ("synthetic",))
            self.assertEqual((m.unknown_count, m.excluded_count), (0, 0))
        for component, counts in (("src/payments", (2, 2)), ("tests/payments", (1, 1)), ("src/catalog", (1, 1))):
            m = metric(self.r, "component_change_intent", component)
            self.assertEqual((m.numerator, m.denominator), counts)

    def test_ac327_empty_and_linked_only_are_null(self):
        self.assertTrue(all(m.value is None for m in self.variant("EMPTY").metrics))
        m = metric(self.variant("LINKED_ONLY"), "work_item_implementation")
        self.assertEqual(m.denominator, 3)
        self.assertIsNone(m.value)
        self.assertEqual(m.status, S.UNAVAILABLE)

    def test_ac330_synthetic_origin_and_hashes(self):
        self.assertIn("SYNTHETIC", SYNTHETIC)
        self.assertEqual(SyntheticTraceabilityProvider().acquire(), self.e)
        self.assertEqual({c.identifier for c in self.e.commits}, {char * 40 for char in "abcd"})
        self.assertEqual(self.e.work_items[1].title, "Fix synthetic catalog timeout")
        self.assertNotIn("azure", self.e.boundaries[0].provider)

    def test_ac331_safe_rejection_never_retains_exception_body(self):
        sentinel = "SYNTHETIC_SECRET_DO_NOT_RETAIN"
        try:
            reference(K.WORK_ITEM, "https://user:" + sentinel + "@example.invalid")
        except ValueError:
            e = isolate_invalid_fixture_record(self.e)
        r = derive(e)
        self.assertNotIn(sentinel, encoded(r))
        self.assertTrue(all(d.reason == R.INVALID_OBSERVATION for d in r.diagnostics))

    def test_ac333_boundaries_retained_and_no_text_inference(self):
        r = self.variant("NO_INFERENCE")
        self.assertEqual(metric(r, "merged_pr_intent").numerator, 0)
        self.assertEqual(metric(r, "commit_intent").numerator, 0)
        changed = replace(self.e.boundaries[0], start=datetime(2025, 1, 1, tzinfo=timezone.utc), end=STAMP,
                          time_field="created_at")
        r = derive(replace(self.e, boundaries=(changed,)))
        self.assertEqual(r.evidence.boundaries[0], changed)
        self.assertEqual(metric(r, "merged_pr_intent").numerator, 3)

    def test_ac334_pr_snapshot_shortcut_never_invents_commit(self):
        r = self.variant("PR_PATH_ONLY")
        path = next(p for p in r.paths if p.nodes[0].kind == K.WORK_ITEM and any(n.kind == K.PR_PATH for n in p.nodes))
        self.assertEqual(path.status, S.PARTIAL)
        self.assertFalse(any(n.kind == K.COMMIT for n in path.nodes))
        self.assertTrue(any(g.relationship == T.PR_COMMIT and g.status == S.MISSING for g in path.gaps))
        self.assertEqual(metric(r, "commit_intent").denominator, 4)
        self.assertEqual(sum(m.denominator for m in r.metrics if m.component), 4)
        self.assertEqual(metric(r, "work_item_implementation").numerator, 2)

    def test_ac335_positive_paths_verified_collection_and_summary_partial(self):
        r = self.variant("POSITIVE_PARTIAL")
        self.assertTrue(any(p.status == S.VERIFIED for p in r.paths))
        self.assertEqual(r.evidence.status, CollectionStatus.PARTIAL)
        self.assertEqual(r.summary, S.PARTIAL)
        self.assertEqual(next(a.status for a in r.artifacts if a.artifact.kind == K.COMPONENT and a.artifact.identifier == "src/payments"), S.PARTIAL)

    def test_ac339_cardinality_precedence_and_alternate_routes(self):
        cases = [(0, 0, True, True, S.UNAVAILABLE), (4, 0, False, True, S.UNAVAILABLE),
                 (4, 0, True, False, S.PARTIAL), (4, 4, True, False, S.PARTIAL),
                 (4, 0, True, True, S.MISSING), (4, 3, True, True, S.PARTIAL),
                 (4, 4, True, True, S.VERIFIED)]
        for n, f, available, complete, expected in cases:
            self.assertEqual(aggregate_status(n, f, available=available, complete=complete), expected)
        self.assertEqual(self.variant("DUPLICATES").summary, self.r.summary)
        self.assertEqual(self.variant("NO_INFERENCE").summary, S.MISSING)
        self.assertEqual(next(a.status for a in self.r.artifacts if a.artifact.kind == K.COMPONENT and a.artifact.identifier == "src/catalog"), S.MISSING)
        with self.assertRaises(ValueError):
            aggregate_status(1, 2)

    def test_ac312_scoped_missing_work_item_is_not_global_absence(self):
        wi = self.e.work_items[2].reference
        partial = replace(self.e, lookups=tuple(replace(l, status=CollectionStatus.PARTIAL)
                          if l.endpoint == wi and l.relationship == T.WI_COMMIT else l for l in self.e.lookups))
        r = derive(partial)
        self.assertNotEqual(next(a.status for a in r.artifacts if a.artifact == wi), S.MISSING)
        self.assertTrue(any(g.endpoint == wi and g.status == S.PARTIAL for g in r.gaps))

    def test_ac325_explicit_join_contract_and_revision_must_agree(self):
        for change in ({"join_contract": "incompatible-query-contract"}, {"revision": "a" * 40},
                       {"filter_policy": "different-filter"}):
            boundary = replace(self.e.boundaries[0], identifier="second-boundary", **change)
            r = derive(replace(self.e, boundaries=self.e.boundaries + (boundary,)))
            self.assertIsNone(metric(r, "commit_intent").value)
            self.assertTrue(any(d.reason == R.INCOMPATIBLE_BOUNDARY for d in r.diagnostics))

    def test_ac310_every_short_path_explains_omitted_segment(self):
        short = [p for p in self.r.paths if p.status == S.PARTIAL]
        self.assertTrue(short)
        self.assertTrue(all(p.gaps for p in short))

    def test_ac315_conflicting_observation_metadata_is_not_last_write_wins(self):
        original = self.e.links[0]
        conflict = replace(original, observations=(replace(original.observations[0], basis="different_basis"),))
        r = derive(replace(self.e, links=self.e.links + (conflict,)))
        self.assertFalse(any(l.key == original.key for l in r.direct_links))
        self.assertTrue(any(d.reason == R.CONFLICTING_OBSERVATION for d in r.diagnostics))

    def test_ac317_changed_path_must_match_exact_commit(self):
        link = next(l for l in self.e.links if l.type == T.COMMIT_PATH)
        wrong = replace(link, target=replace(link.target, context="b" * 40))
        r = derive(replace(self.e, links=self.e.links + (wrong,)))
        self.assertNotIn(wrong, r.direct_links)
        self.assertTrue(any(d.reason == R.INVALID_OBSERVATION for d in r.diagnostics))

    def test_ac334_snapshot_on_pr_with_commits_has_unresolved_not_missing_segment(self):
        pr = self.e.pull_requests[0]
        snapshot = reference(K.PR_PATH, "src/payments/snapshot.py", pr.identifier)
        link = TraceLink(pr, snapshot, T.PR_PATH, O.DIRECT_PROVIDER_LINK, (observation("snapshot-known-membership"),))
        r = derive(replace(self.e, links=self.e.links + (link,)))
        snapshot_paths = [p for p in r.paths if snapshot in p.nodes]
        self.assertTrue(snapshot_paths)
        for path in snapshot_paths:
            gaps = [g for g in path.gaps if g.endpoint == pr and g.relationship == T.PR_COMMIT]
            self.assertTrue(gaps)
            self.assertTrue(all(g.status == S.PARTIAL and g.reason == R.UNRESOLVED_NORMATIVE_SEGMENT for g in gaps))
        self.assertEqual(metric(r, "commit_intent").denominator, 4)

    def test_ac313_wrong_scope_lookup_cannot_prove_negative(self):
        pr = self.e.pull_requests[3]
        boundary = replace(self.e.boundaries[0], identifier="wrong-scope", provider="another-provider",
                           instance="another-instance", project="another-project")
        e = replace(self.e, boundaries=self.e.boundaries + (boundary,), lookups=tuple(
            replace(l, boundary=boundary.identifier) if l.endpoint == pr and l.relationship == T.PR_COMMIT else l
            for l in self.e.lookups))
        r = derive(e)
        gap = next(g for g in r.gaps if g.endpoint == pr and g.relationship == T.PR_COMMIT)
        self.assertEqual(gap.status, S.UNAVAILABLE)
        self.assertNotEqual(gap.reason, R.NO_OBSERVED_LINK)
        self.assertIsNone(metric(r, "commit_intent").value)
        self.assertTrue(any(d.reason == R.INCOMPATIBLE_BOUNDARY for d in r.diagnostics))
        self.assertEqual(encoded(r), encoded(derive(replace(e, lookups=tuple(reversed(e.lookups))))))

    def test_ac326_excluded_counts_are_dimension_specific_distinct_artifacts(self):
        e = SyntheticTraceabilityProvider("BOUNDARY").acquire()
        # Extra PR route to excluded d is a legitimate extra link, never another commit.
        route = TraceLink(e.pull_requests[0], self.e.commits[3], T.PR_COMMIT, O.DIRECT_PROVIDER_LINK,
                          (observation("excluded-extra-route"),))
        r = derive(replace(e, links=e.links + (route, route)))
        self.assertEqual(metric(r, "merged_pr_intent").excluded_count, 0)
        self.assertEqual(metric(r, "work_item_implementation").excluded_count, 0)
        self.assertEqual(metric(r, "commit_intent").excluded_count, 1)
        self.assertEqual(metric(r, "component_change_intent", "src/payments").excluded_count, 1)
        self.assertEqual(metric(r, "component_change_intent", "src/catalog").excluded_count, 0)
        open_pr = derive(replace(self.e, merged_pull_requests=self.e.merged_pull_requests[:-1]))
        self.assertEqual(metric(open_pr, "merged_pr_intent").excluded_count, 1)
        self.assertEqual(metric(open_pr, "commit_intent").excluded_count, 0)

    def test_ac325_different_query_windows_require_explicit_compatible_contract(self):
        boundary = replace(self.e.boundaries[0], identifier="another-query", query="different-query")
        r = derive(replace(self.e, boundaries=self.e.boundaries + (boundary,)))
        self.assertIsNone(metric(r, "commit_intent").value)
        declared = tuple(replace(b, join_contract="approved-fixture-cross-query-v1") for b in (self.e.boundaries[0], boundary))
        joined = derive(replace(self.e, boundaries=declared))
        self.assertEqual(metric(joined, "commit_intent").value, 1)
        self.assertEqual(joined.evidence.boundaries[0].join_contract, "approved-fixture-cross-query-v1")

    def test_nfr312_offline_provider_and_analysis_never_network(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            r = derive(SyntheticTraceabilityProvider().acquire())
        self.assertEqual(metric(r, "commit_intent").numerator, 4)

    def test_nfr310_missing_lookup_cannot_claim_negative(self):
        lookups = tuple(l for l in self.e.lookups if not (l.endpoint == self.e.pull_requests[3] and l.relationship == T.PR_COMMIT))
        r = derive(replace(self.e, lookups=lookups))
        gap = next(g for g in r.gaps if g.endpoint == self.e.pull_requests[3] and g.relationship == T.PR_COMMIT)
        self.assertEqual(gap.status, S.UNAVAILABLE)
        self.assertIsNone(metric(r, "commit_intent").value)

    def test_open_prs_excluded_from_merged_population(self):
        e = replace(self.e, merged_pull_requests=self.e.merged_pull_requests[:-1])
        r = derive(e)
        self.assertEqual((metric(r, "merged_pr_intent").numerator, metric(r, "merged_pr_intent").denominator), (2, 3))


class TraceabilityProjectionTests(unittest.TestCase):
    def test_ac328_history_projection_is_nonmutating(self):
        boundary = base_fixture().boundaries[0]
        history = History("d" * 40, (Commit("a" * 40, Author("Synthetic", "synthetic@example.invalid"), STAMP,
                                          (Change("src/payments/retry.py", 3, 1),)),))
        original = asdict(history)
        commits, paths, links = project_history(history, boundary)
        self.assertEqual(asdict(history), original)
        self.assertEqual(commits[0].identifier, "a" * 40)
        self.assertEqual(paths[0].context, commits[0].identifier)
        self.assertEqual(links[0].origin, O.DIRECT_SOURCE_LINK)
        self.assertFalse(hasattr(commits[0], "author"))

    def test_ac329_review_projection_reuses_owner_without_commit_fabrication(self):
        boundary = base_fixture().boundaries[0]
        reviews = ReviewEvidenceCollection(ProviderProvenance("synthetic", "demo-system", "all-fixture-artifacts", STAMP),
                  (PullRequestEvidence("51", ReviewIdentity("synthetic-author"), STAMP,
                                       ("src/payments/retry.py",), ()),))
        original = asdict(reviews)
        refs, merged, links = project_reviews(reviews, boundary)
        self.assertEqual(asdict(reviews), original)
        self.assertEqual(refs, merged)
        self.assertEqual(links[0].type, T.PR_PATH)
        self.assertEqual(links[0].target.kind, K.PR_PATH)
        self.assertFalse(any(l.type == T.PR_COMMIT for l in links))
        self.assertFalse(hasattr(refs[0], "reviews"))

    def test_ac325_history_projection_rejects_revision_relabelling(self):
        boundary = base_fixture().boundaries[0]
        history = History("a" * 40, ())
        with self.assertRaisesRegex(ValueError, "incompatible Git source revision"):
            project_history(history, boundary)
        with self.assertRaises(ValueError):
            project_history(History(boundary.revision, ()), replace(boundary, revision=None))

    def test_ac333_review_projection_rejects_source_provenance_relabelling(self):
        boundary = base_fixture().boundaries[0]
        source = ProviderProvenance("synthetic", "demo-system", "all-fixture-artifacts", STAMP)
        reviews = ReviewEvidenceCollection(source, ())
        for change in ({"provider": "another-provider"}, {"repository": "another-repository"},
                       {"evidence_boundary": "another-query"},
                       {"retrieved_at": datetime(2026, 1, 2, tzinfo=timezone.utc)}):
            with self.assertRaisesRegex(ValueError, "incompatible review source provenance"):
                project_reviews(replace(reviews, provenance=replace(source, **change)), boundary)
        original = asdict(reviews)
        self.assertEqual(project_reviews(reviews, boundary), ((), (), ()))
        self.assertEqual(asdict(reviews), original)


if __name__ == "__main__":
    unittest.main()
