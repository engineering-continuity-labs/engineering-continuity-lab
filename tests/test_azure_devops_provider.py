"""ECL-AC-350–355, using only project-owned SYNTHETIC REST fixtures."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from azure_rest_fixture import (FOREIGN, IDENTITIES, ISO, PROJECT, REPOSITORY, STAMP, RestFixture, artifact, profile)
from continuity.analysis.traceability import derive
from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import (
    ArtifactKind as K, Direction as D, Population as P, TraceLinkOrigin as O,
    TraceLinkType as T, TraceStatus as TS, TraceabilityCapability as C,
    WorkItemType as WT, WorkItemState as WS,
)
from continuity.reporting.traceability import (traceability_to_json, traceability_from_json, with_traceability, validate_report_envelope)
from continuity.traceability_providers.azure_devops import (
    AzureApiProfile as A, AzureDevOpsTraceabilityProvider, AzureIdentityMap, AzureLimits,
)
from continuity.traceability_providers.azure_dto import artifact as parse_artifact
from continuity.traceability_providers.azure_transport import AzureResponse


class AzureProviderTests(unittest.TestCase):
    def acquire(self, fixture=None, configured=None, identities=IDENTITIES):
        return AzureDevOpsTraceabilityProvider(configured or profile(), identities, STAMP,
                                              "synthetic-snapshot", fixture or RestFixture()).acquire()

    def lookup(self, evidence, *, kind=None, relationship=None, direction=D.OUTBOUND, population=None, identifier=None):
        return next(l for l in evidence.lookups if l.population == population and l.relationship == relationship
                    and l.direction == direction and (kind is None or l.endpoint.kind == kind)
                    and (identifier is None or l.endpoint.identifier == identifier))

    def test_base_provider_derivation_and_report_round_trip(self):
        evidence = self.acquire()
        report = derive(evidence)
        counts = {(m.dimension, m.component.identifier if m.component else None): (m.numerator, m.denominator) for m in report.metrics}
        self.assertEqual(counts, {("merged_pr_intent", None): (3, 4), ("commit_intent", None): (4, 4),
            ("work_item_implementation", None): (2, 3), ("component_change_intent", "src/payments"): (2, 2),
            ("component_change_intent", "tests/payments"): (1, 1), ("component_change_intent", "src/catalog"): (1, 1)})
        self.assertEqual(evidence.status, S.COMPLETE)
        self.assertEqual({w.type for w in evidence.work_items}, {WT.STORY, WT.BUG, WT.REQUIREMENT})
        self.assertEqual({w.state for w in evidence.work_items}, {WS.OPEN, WS.ACTIVE, WS.CLOSED})
        self.assertTrue(all(w.title is None and not w.title_approved for w in evidence.work_items))
        self.assertEqual({l.origin for l in evidence.links}, {O.DIRECT_PROVIDER_LINK})
        self.assertTrue(any(l.type == T.PATH_COMPONENT and l.origin == O.DERIVED_LINK for l in report.derived_links))
        encoded = traceability_to_json(report)
        self.assertEqual(traceability_to_json(traceability_from_json(encoded)), encoded)
        envelope = with_traceability({"model": "experimental-v0.1", "revision": "synthetic", "as_of": ISO,
            "commit_count": 0, "components": []}, report)
        self.assertEqual(validate_report_envelope(envelope), envelope)

    def test_profiles_normalize_the_same_evidence(self):
        results = [traceability_to_json(derive(self.acquire(configured=profile(kind)))) for kind in A]
        self.assertEqual(len(set(results)), 1)
        for kind, expected in ((A.SERVER_CURRENT, "7.2"), (A.SERVER_2022_1, "7.1"), (A.SERVER_2022, "7.0"), (A.SERVICES, "7.2")):
            p = profile(kind)
            self.assertEqual(p.api_version, expected)
            self.assertEqual(parse_qs(urlsplit(p.url(("wit", "workitems"))).query)["api-version"], [expected])

    def test_collection_encoding_and_url_shapes(self):
        p = replace(profile(), collection="SYNTHETIC Türkçe collection")
        self.assertIn("/tfs/SYNTHETIC%20T%C3%BCrk%C3%A7e%20collection/" + PROJECT + "/_apis/", p.url(("wit", "workitems")))
        self.assertTrue(profile(A.SERVICES).url(("wit", "wiql")).startswith("https://dev.azure.com/synthetic-collection/" + PROJECT))
        with self.assertRaises(FrozenInstanceError):
            p.collection = "other"
        self.assertEqual(profile(api_version="7.0").api_version, "7.0")
        for kind, version in ((A.SERVER_2022, "7.1"), (A.SERVER_2022_1, "7.2"), (A.SERVER_CURRENT, "6.0"), (A.SERVICES, "7.3")):
            with self.subTest(kind=kind, version=version), self.assertRaises(ValueError):
                profile(kind, api_version=version)

    def test_unsafe_native_config_and_aliases(self):
        for changes in ({"base_url": "https://user:secret@synthetic.invalid"}, {"base_url": "http://synthetic.invalid"},
                        {"base_url": "https://synthetic.invalid/tfs?secret=x"}, {"base_url": "https://synthetic.invalid/%2f"},
                        {"base_url": "https://synthetic.invalid/../tfs"}, {"collection": "../x"},
                        {"repository": "display-name"}, {"instance_alias": "PAT_SENTINEL"}, {"api_version": "7.2-preview"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(profile(), **changes)
        with self.assertRaises(ValueError):
            replace(profile(A.SERVICES), base_url="https://synthetic.invalid")

    def test_complete_populations_include_unlinked_artifacts(self):
        e = self.acquire()
        self.assertEqual(len(e.work_items), 3)
        self.assertEqual(len(e.pull_requests), 4)
        self.assertEqual(len(e.commits), 4)
        fixture = RestFixture()
        active = deepcopy(fixture.prs[0]); active.update(pullRequestId=55, status="active")
        fixture.prs.append(active)
        e = self.acquire(fixture)
        self.assertEqual(len(e.pull_requests), 4)
        self.assertEqual(self.lookup(e, population=P.PULL_REQUESTS).status, S.COMPLETE)

    def test_minimal_field_requests_and_no_inference(self):
        fixture = RestFixture()
        fixture.prs[0]["workItemRefs"] = []
        fixture.items[1]["relations"] = []
        fixture.prs[2]["workItemRefs"] = []
        fixture.prs[3]["workItemRefs"] = []
        e = self.acquire(fixture)
        self.assertFalse(any(l.type in (T.WI_PR, T.WI_COMMIT) for l in e.links))
        for endpoint, query, body in fixture.calls:
            if endpoint == ("wit", "workitems"):
                self.assertEqual(query["fields"], "System.Id,System.WorkItemType,System.State")
                self.assertEqual(query["asOf"], ISO)
                self.assertEqual(query["$expand"], "Relations")
            if endpoint[-1] == "commits" and len(endpoint) == 4:
                self.assertEqual(query["searchCriteria.itemVersion.version"], "d" * 40)

    def test_dedicated_pr_work_item_endpoint_when_refs_absent(self):
        fixture = RestFixture()
        for pr in fixture.prs:
            del pr["workItemRefs"]
        e = self.acquire(fixture)
        self.assertTrue(any(l.type == T.WI_PR and l.target.identifier == "pr-51" for l in e.links))
        self.assertEqual(len([c for c in fixture.calls if c[0][-1] == "workitems" and len(c[0]) == 6]), 4)

    def test_exact_artifact_grammar_and_scoping(self):
        for encoded in (False, True):
            self.assertEqual(parse_artifact(artifact("Commit", "a" * 40, encoded=encoded), PROJECT, REPOSITORY), ("Commit", "a" * 40))
            self.assertEqual(parse_artifact(artifact("PullRequestId", 51, encoded=encoded), PROJECT, REPOSITORY), ("PullRequestId", "51"))
        uri = artifact("PullRequestId", 51)
        bad = [artifact("Commit", "a" * 40, project=FOREIGN), artifact("Commit", "a" * 40, repository=FOREIGN),
               artifact("Branch", "a" * 40), uri + "/extra", uri + "?secret=x", uri + "#x", uri.replace("/51", "/0"),
               uri.replace(PROJECT + "/", PROJECT + "%2f"), uri.replace("/51", "%252f51"),
               "https://synthetic.invalid/pr/51", artifact("Commit", "a" * 39), uri.replace("PullRequestId", "pullrequestid")]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_artifact(value, PROJECT, REPOSITORY)

    def test_foreign_malformed_artifacts_make_scoped_negative_incomplete(self):
        for uri in (artifact("Commit", "a" * 40, repository=FOREIGN), artifact("PullRequestId", 51, project=FOREIGN),
                    artifact("Commit", "x"), artifact("Unexpected", "x")):
            fixture = RestFixture(); fixture.items[2]["relations"] = [{"rel": "ArtifactLink", "url": uri}]
            e = self.acquire(fixture)
            self.assertEqual(self.lookup(e, kind=K.WORK_ITEM, relationship=T.WI_PR, identifier="wi-1003").status, S.PARTIAL)
            self.assertFalse(any(l.source.identifier == "wi-1003" for l in e.links))
            gaps = [g for g in derive(e).gaps if g.endpoint.identifier == "wi-1003"]
            self.assertTrue(gaps)
            self.assertFalse(any(g.status == TS.MISSING for g in gaps))

    def test_explicit_pr_artifact_deduplicates_against_work_item_refs(self):
        fixture = RestFixture()
        fixture.items[0]["relations"] = [{"rel": "ArtifactLink", "url": artifact("PullRequestId", 51, encoded=True)}] * 2
        e = self.acquire(fixture)
        self.assertEqual(len([l for l in e.links if l.type == T.WI_PR and l.source.identifier == "wi-1001" and l.target.identifier == "pr-51"]), 1)

    def test_paging_batching_and_exact_duplicate_evidence(self):
        fixture = RestFixture()
        configured = replace(profile(), limits=AzureLimits(page_size=1, work_item_batch=1))
        e = self.acquire(fixture, configured)
        self.assertEqual(traceability_to_json(derive(e)), traceability_to_json(derive(self.acquire())))
        batches = [c[1]["ids"] for c in fixture.calls if c[0] == ("wit", "workitems")]
        self.assertEqual(batches, ["1001", "1002", "1003"])
        self.assertTrue(any("continuationToken" in c[1] for c in fixture.calls))
        fixture = RestFixture()
        fixture.prs += deepcopy(fixture.prs); fixture.commits += deepcopy(fixture.commits)
        fixture.members[51] += deepcopy(fixture.members[51]); fixture.items += deepcopy(fixture.items)
        self.assertEqual(traceability_to_json(derive(self.acquire(fixture))), traceability_to_json(derive(self.acquire())))

    def test_input_order_is_deterministic(self):
        fixture = RestFixture()
        fixture.prs.reverse(); fixture.items.reverse(); fixture.commits.reverse()
        for values in fixture.members.values(): values.reverse()
        self.assertEqual(traceability_to_json(derive(self.acquire(fixture))), traceability_to_json(derive(self.acquire())))

    def test_partial_pr_page_retains_positive_paths(self):
        fixture = RestFixture()
        fixture.fail[(("git", "repositories", REPOSITORY, "pullrequests"), 2)] = "failed"
        e = self.acquire(fixture, replace(profile(), limits=AzureLimits(page_size=2)))
        self.assertEqual(len(e.pull_requests), 2)
        self.assertEqual(self.lookup(e, population=P.PULL_REQUESTS).status, S.PARTIAL)
        self.assertEqual(e.status, S.PARTIAL)
        self.assertTrue(any(p.status == TS.VERIFIED for p in derive(e).paths))
        self.assertNotEqual(next(m for m in derive(e).metrics if m.dimension == "commit_intent").status, TS.VERIFIED)

    def test_first_pr_page_failure_is_failed_and_not_missing(self):
        fixture = RestFixture(); fixture.fail[("git", "repositories", REPOSITORY, "pullrequests")] = "failed"
        e = self.acquire(fixture)
        self.assertEqual(self.lookup(e, population=P.PULL_REQUESTS).status, S.FAILED)
        self.assertEqual(self.lookup(e, kind=K.WORK_ITEM, relationship=T.WI_PR).capability, C.UNKNOWN)
        self.assertFalse(any(g.status == TS.MISSING and g.relationship == T.WI_PR for g in derive(e).gaps))

    def test_failed_pr_commits_affect_only_that_outbound_lookup_and_all_inverses(self):
        fixture = RestFixture(); fixture.fail[("git", "repositories", REPOSITORY, "pullrequests", "52", "commits")] = "failed"
        e = self.acquire(fixture)
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, identifier="pr-52", relationship=T.PR_COMMIT).status, S.FAILED)
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, identifier="pr-51", relationship=T.PR_COMMIT).status, S.COMPLETE)
        self.assertEqual(self.lookup(e, kind=K.COMMIT, relationship=T.PR_COMMIT, direction=D.INBOUND).status, S.PARTIAL)
        self.assertTrue(e.links)

    def test_limits_repeated_or_missing_continuation_never_complete(self):
        for modification in ("max-pages", "max-items", "repeat", "missing", "requests"):
            fixture = RestFixture(); limits = AzureLimits(page_size=1)
            if modification == "max-pages": limits = replace(limits, max_pages=1)
            if modification == "max-items": limits = replace(limits, max_items=1)
            if modification == "repeat": fixture.repeat_token = True
            if modification == "missing": fixture.no_token = True
            if modification == "requests": limits = replace(limits, max_requests=2)
            e = self.acquire(fixture, replace(profile(), limits=limits))
            self.assertNotEqual(e.status, S.COMPLETE, modification)
            self.assertTrue(e.diagnostics)

    def test_unsupported_and_disabled_capabilities(self):
        fixture = RestFixture(); fixture.fail[("git", "repositories", REPOSITORY, "pullrequests", "51", "commits")] = "unsupported"
        e = self.acquire(fixture)
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, identifier="pr-51", relationship=T.PR_COMMIT).capability, C.UNSUPPORTED)
        fixture = RestFixture()
        e = self.acquire(fixture, replace(profile(), include_artifact_relations=False, include_changes=False))
        self.assertFalse(any(l.type in (T.WI_COMMIT, T.COMMIT_PATH) for l in e.links))
        self.assertEqual(self.lookup(e, kind=K.WORK_ITEM, relationship=T.WI_COMMIT).capability, C.UNSUPPORTED)
        self.assertEqual(self.lookup(e, population=P.CHANGES).capability, C.UNSUPPORTED)
        self.assertTrue(all("$expand" not in c[1] for c in fixture.calls if c[0] == ("wit", "workitems")))

    def test_malformed_pr_work_item_and_missing_batch_members_are_partial(self):
        for scenario in ("foreign-pr", "bad-pr", "bad-wi", "missing-wi", "unknown-id"):
            fixture = RestFixture()
            if scenario == "foreign-pr": fixture.prs[0]["repository"]["id"] = FOREIGN
            if scenario == "bad-pr": fixture.prs[0]["closedDate"] = "2026-02-30T00:00:00Z"
            if scenario == "bad-wi": fixture.items[0]["fields"]["System.State"] = None
            if scenario == "missing-wi": fixture.mutate[("wit", "workitems")] = lambda p: {"value": p["value"][1:]}
            if scenario == "unknown-id": fixture.items[0]["id"] = 99999
            e = self.acquire(fixture)
            self.assertEqual(e.status, S.PARTIAL, scenario)
            self.assertTrue(e.diagnostics)
            traceability_from_json(traceability_to_json(derive(e)))

    def test_complete_empty_and_zero_work_item_populations(self):
        fixture = RestFixture(); fixture.items = []; fixture.prs = []; fixture.commits = []
        e = self.acquire(fixture)
        self.assertEqual(e.status, S.COMPLETE)
        self.assertTrue(all(m.value is None and m.status == TS.UNAVAILABLE for m in derive(e).metrics))
        fixture = RestFixture(); fixture.items = []
        for pr in fixture.prs: pr["workItemRefs"] = []
        e = self.acquire(fixture)
        self.assertEqual(len(e.work_items), 0)
        self.assertEqual(next(m for m in derive(e).metrics if m.dimension == "work_item_implementation").denominator, 0)
        e = self.acquire()
        gap = next(g for g in derive(e).gaps if g.endpoint.identifier == "pr-54" and g.relationship == T.PR_COMMIT)
        self.assertEqual(gap.status, TS.MISSING)

    def test_no_usable_evidence_all_operations_failed(self):
        fixture = RestFixture()
        for endpoint in (("wit", "wiql"), ("git", "repositories", REPOSITORY, "pullrequests"), ("git", "repositories", REPOSITORY, "commits")):
            fixture.fail[endpoint] = "failed"
        e = self.acquire(fixture)
        self.assertEqual(e.status, S.FAILED)
        self.assertFalse(e.links)
        report = derive(e)
        self.assertFalse(any(g.status == TS.MISSING for g in report.gaps))
        traceability_from_json(traceability_to_json(report))

    def test_alias_map_quarantines_native_numeric_ids(self):
        identities = AzureIdentityMap("synthetic-mapping", tuple((i, f"w-{n}") for n, i in enumerate((1001, 1002, 1003))),
                                     tuple((i, f"p-{n}") for n, i in enumerate((51, 52, 53, 54))))
        evidence = self.acquire(identities=identities)
        encoded = traceability_to_json(derive(evidence))
        for raw in ("1001", "1002", "1003", PROJECT, REPOSITORY, "synthetic.invalid", "synthetic-collection",
                    "PERSON_SENTINEL", "TITLE_SENTINEL", "DESCRIPTION_SENTINEL", "MESSAGE_SENTINEL"):
            self.assertNotIn(raw, encoded)
        self.assertNotIn(PROJECT, repr(profile()))
        self.assertNotIn("1001", repr(identities))

    def test_commit_change_page_failure_keeps_changes_partial(self):
        fixture = RestFixture(); key = "a" * 40
        fixture.changes[key] += [{"item": {"path": "/src/payments/extra.py", "gitObjectType": "blob"}}]
        fixture.fail[(("git", "repositories", REPOSITORY, "commits", key, "changes"), 1)] = "failed"
        e = self.acquire(fixture, replace(profile(), limits=AzureLimits(page_size=1)))
        self.assertTrue(any(l.type == T.COMMIT_PATH and l.source.identifier == key for l in e.links))
        self.assertEqual(self.lookup(e, kind=K.COMMIT, relationship=T.COMMIT_PATH, identifier=key).status, S.PARTIAL)
        self.assertEqual(self.lookup(e, population=P.CHANGES).status, S.PARTIAL)

    def test_outside_revision_links_do_not_expand_commit_denominator(self):
        fixture = RestFixture(); fixture.members[51].append({"commitId": "e" * 40})
        e = self.acquire(fixture)
        self.assertEqual(len(e.commits), 4)
        self.assertTrue(any(l.target.identifier == "e" * 40 for l in e.links))
        self.assertTrue(derive(e).diagnostics)

    def test_malformed_ref_preserves_other_valid_refs_and_pr_population(self):
        fixture = RestFixture()
        fixture.prs[0]["workItemRefs"].append({"id": "invalid"})
        e = self.acquire(fixture)
        self.assertEqual(len(e.pull_requests), 4)
        self.assertTrue(any(l.type == T.WI_PR and l.target.identifier == "pr-51" for l in e.links))
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, relationship=T.WI_PR, direction=D.INBOUND, identifier="pr-51").status, S.PARTIAL)

    def test_disabled_wi_commit_keeps_pr_refs_capability_supported(self):
        e = self.acquire(configured=replace(profile(), include_artifact_relations=False))
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, relationship=T.WI_PR, direction=D.INBOUND).capability, C.SUPPORTED)
        self.assertEqual(self.lookup(e, kind=K.WORK_ITEM, relationship=T.WI_COMMIT).capability, C.UNSUPPORTED)

    def test_malformed_relations_and_conflicting_wi_records_never_crash(self):
        fixture = RestFixture(); fixture.items[0]["relations"] = None
        e = self.acquire(fixture)
        self.assertEqual(e.status, S.PARTIAL)
        traceability_from_json(traceability_to_json(derive(e)))
        fixture = RestFixture()
        other = deepcopy(fixture.items[0]); other["fields"]["System.State"] = "Closed"
        fixture.items.append(other)
        first = traceability_to_json(derive(self.acquire(fixture)))
        fixture.items.reverse()
        self.assertEqual(traceability_to_json(derive(self.acquire(fixture))), first)

    def test_short_commit_page_with_continuation_is_not_terminal(self):
        class ShortPages(RestFixture):
            def request(self, endpoint, query, body=None):
                if len(endpoint) == 6 and endpoint[3] == "pullrequests" and endpoint[-1] == "commits" and endpoint[4] == "51":
                    token = query.get("continuationToken")
                    return AzureResponse({"value": [self.commits[0 if token is None else 1]]}, "next" if token is None else None)
                return super().request(endpoint, query, body)
        e = self.acquire(ShortPages())
        self.assertEqual(len([l for l in e.links if l.type == T.PR_COMMIT and l.source.identifier == "pr-51"]), 2)
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, identifier="pr-51", relationship=T.PR_COMMIT).status, S.COMPLETE)

    def test_work_item_batch_size_boundary_and_dedup(self):
        fixture = RestFixture()
        fixture.items = [{"id": i, "fields": {"System.Id": i, "System.WorkItemType": "Task", "System.State": "New"}, "relations": []}
                         for i in range(1, 202)]
        fixture.prs = []; fixture.commits = []
        identities = AzureIdentityMap("synthetic-large-map", tuple((i, f"w-{i}") for i in range(1, 202)), ())
        e = self.acquire(fixture, identities=identities)
        self.assertEqual(len(e.work_items), 201)
        batches = [c[1]["ids"].split(",") for c in fixture.calls if c[0] == ("wit", "workitems")]
        self.assertEqual([len(b) for b in batches], [200, 1])
        self.assertEqual(len({i for b in batches for i in b}), 201)

    def test_work_item_query_bad_snapshot_or_nonprogress_is_partial(self):
        for mutation in (lambda p: dict(p, asOf="2025-12-31T00:00:00Z"), lambda p: dict(p, queryType="tree")):
            fixture = RestFixture(); fixture.mutate[("wit", "wiql")] = mutation
            e = self.acquire(fixture)
            self.assertNotEqual(self.lookup(e, population=P.WORK_ITEMS).status, S.COMPLETE)
        fixture = RestFixture()
        fixture.mutate[("wit", "wiql")] = lambda p: dict(p, workItems=[{"id": 1001}])
        e = self.acquire(fixture, replace(profile(), limits=AzureLimits(page_size=1)))
        self.assertEqual(self.lookup(e, population=P.WORK_ITEMS).status, S.PARTIAL)

    def test_scope_and_date_validation_even_if_population_query_ignored(self):
        for changes in ({"closedDate": "2027-01-01T00:00:00Z"}, {"status": "guessed-merged"},
                        {"repository": {"id": REPOSITORY, "project": {"id": FOREIGN}}}):
            fixture = RestFixture(); fixture.prs[0].update(changes)
            e = self.acquire(fixture)
            self.assertFalse(any(p.identifier == "pr-51" for p in e.pull_requests))
            self.assertEqual(e.status, S.PARTIAL)

    def test_changed_path_safety_and_folders(self):
        for path in ("/../private", "//src/file", "/home/user/secret", "/src/PAT_SENTINEL", "/src/a\\b"):
            fixture = RestFixture(); fixture.changes["a" * 40][0]["item"]["path"] = path
            e = self.acquire(fixture)
            self.assertEqual(self.lookup(e, kind=K.COMMIT, relationship=T.COMMIT_PATH, identifier="a" * 40).status, S.PARTIAL)
            self.assertFalse(any(p.context == "a" * 40 for p in e.changed_paths))
        fixture = RestFixture()
        fixture.changes["a" * 40].append({"item": {"path": "/src/payments", "isFolder": True, "gitObjectType": "tree"}})
        self.assertEqual(len(self.acquire(fixture).changed_paths), 4)

    def test_late_commit_membership_failure_preserves_first_page(self):
        from continuity.traceability_providers.azure_transport import AzureTransportError
        class LateFailure(RestFixture):
            def request(self, endpoint, query, body=None):
                if len(endpoint) == 6 and endpoint[3] == "pullrequests" and endpoint[4] == "51" and "continuationToken" in query:
                    raise AzureTransportError("request_failed")
                return super().request(endpoint, query, body)
        e = self.acquire(LateFailure(), replace(profile(), limits=AzureLimits(page_size=1)))
        self.assertEqual(self.lookup(e, kind=K.PULL_REQUEST, relationship=T.PR_COMMIT, identifier="pr-51").status, S.PARTIAL)
        self.assertTrue(any(l.type == T.PR_COMMIT and l.source.identifier == "pr-51" and l.target.identifier == "a" * 40 for l in e.links))
        self.assertFalse(any(g.status == TS.MISSING and g.endpoint.identifier == "pr-51" and g.relationship == T.PR_COMMIT for g in derive(e).gaps))


if __name__ == "__main__":
    unittest.main()
