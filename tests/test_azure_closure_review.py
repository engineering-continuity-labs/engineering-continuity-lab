"""SYNTHETIC regressions for independently reproduced AZ-R01–04."""
from copy import deepcopy
from dataclasses import replace
import unittest

from azure_rest_fixture import IDENTITIES, REPOSITORY, STAMP, RestFixture, profile
from continuity.analysis.traceability import derive
from continuity.domain.reviews import CollectionStatus as S
from continuity.domain.traceability import (
    ArtifactKind as K, Direction as D, GapReason as G, Population as P,
    TraceLinkType as T, TraceStatus as TS,
)
from continuity.reporting.traceability import traceability_from_json, traceability_to_json
from continuity.traceability_providers.azure_devops import AzureDevOpsTraceabilityProvider, AzureLimits
from continuity.traceability_providers.azure_transport import AzureResponse


class AzureClosureReviewTests(unittest.TestCase):
    def acquire(self, fixture, limits=None):
        configured = replace(profile(), limits=limits) if limits else profile()
        return AzureDevOpsTraceabilityProvider(configured, IDENTITIES, STAMP, "synthetic-snapshot", fixture).acquire()

    def pr_lookup(self, evidence):
        return next(l for l in evidence.lookups if l.endpoint and l.endpoint.identifier == "pr-51"
                    and l.relationship == T.WI_PR and l.direction == D.INBOUND)

    def test_az_r01_conflicting_wi_is_quarantined_without_coverage_or_resurrection(self):
        for field, replacement in (("System.State", "Closed"), ("System.WorkItemType", "Bug"),
                                   ("System.WorkItemType", "SYNTHETIC-custom-second")):
            fixture = RestFixture()
            if replacement.startswith("SYNTHETIC"):
                fixture.items[0]["fields"][field] = "SYNTHETIC-custom-first"
            other = deepcopy(fixture.items[0]); other["fields"][field] = replacement
            fixture.items += [other, deepcopy(fixture.items[0])]
            e = self.acquire(fixture)
            report = derive(e)
            self.assertNotIn("wi-1001", {w.reference.identifier for w in e.work_items})
            self.assertTrue(any(d.reason == G.CONFLICTING_OBSERVATION and d.endpoint.identifier == "wi-1001" for d in e.diagnostics))
            self.assertFalse(any(any(n.kind == K.WORK_ITEM and n.identifier == "wi-1001" for n in p.nodes)
                                 and p.status == TS.VERIFIED for p in report.paths))
            metric = next(m for m in report.metrics if m.dimension == "work_item_implementation")
            self.assertEqual((metric.numerator, metric.denominator), (1, 2))
            encoded = traceability_to_json(report)
            fixture.items.reverse()
            self.assertEqual(traceability_to_json(derive(self.acquire(fixture))), encoded)
            self.assertEqual(traceability_to_json(traceability_from_json(encoded)), encoded)

    def test_az_r02_malformed_wiql_id_retains_valid_refs_at_any_position(self):
        for position in (0, 1, 3):
            fixture = RestFixture()
            def malformed(payload):
                payload["workItems"].insert(position, {"id": "bad"})
                return payload
            fixture.mutate[("wit", "wiql")] = malformed
            e = self.acquire(fixture)
            self.assertEqual({w.reference.identifier for w in e.work_items}, {"wi-1001", "wi-1002", "wi-1003"})
            self.assertEqual(next(l for l in e.lookups if l.population == P.WORK_ITEMS).status, S.PARTIAL)
            self.assertEqual([c[1]["ids"] for c in fixture.calls if c[0] == ("wit", "workitems")], ["1001,1002,1003"])
            self.assertEqual(len([c for c in fixture.calls if c[0] == ("wit", "wiql")]), 1)
            traceability_from_json(traceability_to_json(derive(e)))

    def test_az_r02_late_malformed_or_nonprogress_page_retains_new_valid_ids(self):
        for bad in ({"id": "bad"}, {"id": 1001}):
            fixture = RestFixture()
            pages = []
            def malformed(payload):
                pages.append(1)
                if len(pages) == 2:
                    payload["workItems"] = [payload["workItems"][0], bad]
                return payload
            fixture.mutate[("wit", "wiql")] = malformed
            e = self.acquire(fixture, AzureLimits(page_size=1))
            self.assertEqual({w.reference.identifier for w in e.work_items}, {"wi-1001", "wi-1002"})
            self.assertEqual(next(l for l in e.lookups if l.population == P.WORK_ITEMS).status, S.PARTIAL)
            self.assertEqual(len(pages), 2)

    def fallback(self, records):
        class Fallback(RestFixture):
            def request(self, endpoint, query, body=None):
                if endpoint == ("git", "repositories", REPOSITORY, "pullrequests", "51", "workitems"):
                    return AzureResponse({"value": deepcopy(records)})
                return super().request(endpoint, query, body)
        fixture = Fallback()
        del fixture.prs[0]["workItemRefs"]
        return fixture

    def test_az_r03_fallback_overlimit_is_partial_and_preserves_bounded_positive(self):
        e = self.acquire(self.fallback([{"id": "1001"}, {"id": "1002"}]), AzureLimits(max_relations=1))
        observed = [l for l in e.links if l.type == T.WI_PR and l.target.identifier == "pr-51"]
        self.assertEqual(len(observed), 1)
        self.assertEqual(self.pr_lookup(e).status, S.PARTIAL)
        self.assertTrue(any(d.endpoint and d.endpoint.identifier == "pr-51" and d.relationship == T.WI_PR for d in e.diagnostics))
        self.assertFalse(any(g.status == TS.MISSING and g.endpoint.identifier == "pr-51" for g in derive(e).gaps))

    def test_az_r03_exact_limit_complete_and_malformed_ref_keeps_positive(self):
        e = self.acquire(self.fallback([{"id": "1001"}]), AzureLimits(max_relations=1))
        self.assertEqual(self.pr_lookup(e).status, S.COMPLETE)
        for records in ([{"id": "bad"}, {"id": "1001"}], [{"id": "1001"}, {"id": "bad"}]):
            e = self.acquire(self.fallback(records))
            self.assertEqual(self.pr_lookup(e).status, S.PARTIAL)
            self.assertTrue(any(l.type == T.WI_PR and l.target.identifier == "pr-51" for l in e.links))

    def test_az_r04_recognizable_credentials_are_quarantined_before_evidence(self):
        sentinels = ["ghp_" + "A" * 36, "github_pat_" + "A" * 36, "glpat-" + "A" * 24,
                     "AKIA" + "A" * 16, "ASIA" + "A" * 16, "sk-" + "A" * 24,
                     "file://SYNTHETIC", "PAT_SENTINEL_SYNTHETIC", "Authorization=SYNTHETIC",
                     "password=SYNTHETIC", "bearer SYNTHETIC", "COOKIE_SENTINEL_SYNTHETIC"]
        for sentinel in sentinels:
            fixture = RestFixture()
            fixture.changes["a" * 40].append({"item": {"path": "/src/" + sentinel + ".txt"}})
            e = self.acquire(fixture)
            self.assertEqual(e.status, S.PARTIAL)
            self.assertNotIn(sentinel, repr(e))
            self.assertTrue(any(p.identifier == "src/payments/retry.py" for p in e.changed_paths))
            encoded = traceability_to_json(derive(e))
            self.assertNotIn(sentinel, encoded)
            self.assertEqual(traceability_to_json(traceability_from_json(encoded)), encoded)

    def test_az_r04_ordinary_paths_remain_supported(self):
        fixture = RestFixture()
        safe = ["src/tokens.py", "src/secrets.md", "src/authentication.py", "docs/cookie-policy.md", "src/鍵.py"]
        fixture.changes["a" * 40] += [{"item": {"path": "/" + p}} for p in safe]
        e = self.acquire(fixture)
        self.assertEqual(e.status, S.COMPLETE)
        self.assertTrue(set(safe) <= {p.identifier for p in e.changed_paths})
        traceability_from_json(traceability_to_json(derive(e)))


if __name__ == "__main__":
    unittest.main()
