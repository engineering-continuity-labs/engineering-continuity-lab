from datetime import datetime, timedelta, timezone
import unittest

from continuity.analysis.service import analyze, resolve_person, simulate_departure
from continuity.domain.models import Author, Change, Commit, DirectoryComponents, History
from continuity.scoring.model import SIGNALS, ScoringConfig, recency, risk, score

NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def commit(who: str, path: str = "src/a.py", days: int = 0) -> Commit:
    return Commit(who + path + str(days), Author(who, who + "@example.com"),
                  NOW - timedelta(days=days), (Change(path, 10, 0),))


class ScoringTests(unittest.TestCase):
    def test_score_endpoints_and_weight_normalization(self):
        for value in (0., .5, 1.):
            self.assertAlmostEqual(score(dict.fromkeys(SIGNALS, value), ScoringConfig()), value)
        weights = dict.fromkeys(SIGNALS, 0.)
        weights["recency"] = 8
        self.assertEqual(score({**dict.fromkeys(SIGNALS, 0.), "recency": .7}, ScoringConfig(weights)), .7)

    def test_invalid_config_and_signals(self):
        for weights in ({}, dict.fromkeys(SIGNALS, 0.), dict.fromkeys(SIGNALS, -1.), dict.fromkeys(SIGNALS, float("nan"))):
            with self.assertRaises(ValueError):
                ScoringConfig(weights)
        with self.assertRaises(ValueError):
            ScoringConfig(half_life_days=0)
        with self.assertRaises(ValueError):
            score(dict.fromkeys(SIGNALS, 2.), ScoringConfig())

    def test_recency(self):
        self.assertEqual(recency(NOW - timedelta(days=180), NOW, 180), .5)

    def test_thresholds(self):
        self.assertEqual([risk(v) for v in (0, .4, .6, .8, 1)], ["LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL"])

    def test_balanced_and_single_contributor(self):
        for people, expected in ((["a"], "CRITICAL"), (["a", "b"], "MEDIUM"), (["a", "b", "c"], "LOW")):
            report = analyze(History("head", tuple(commit(p) for p in people)), DirectoryComponents(), ScoringConfig())
            c = report.components[0]
            self.assertEqual(c.risk, expected)
            self.assertAlmostEqual(c.concentration, 1 / len(people))
            self.assertAlmostEqual(sum(p.share for p in c.contributors), 1)

    def test_unique_and_departure(self):
        report = analyze(History("head", (commit("a"), commit("a", "src/b.py"), commit("b"))), DirectoryComponents(), ScoringConfig())
        a = next(p for p in report.components[0].contributors if p.name == "a")
        self.assertEqual(a.signals["unique_contribution"], .5)
        impact = simulate_departure(report, resolve_person(report, "a"))[0]
        self.assertEqual(impact.best_successor_candidate, "b@example.com")
        self.assertEqual(impact.successor_file_overlap, .5)
        self.assertEqual(impact.uncovered_files, ("src/b.py",))
        self.assertEqual(impact.estimated_knowledge_loss, a.share)

    def test_no_successor_and_invalid_person(self):
        report = analyze(History("head", (commit("a"),)), DirectoryComponents(), ScoringConfig())
        self.assertIsNone(simulate_departure(report, "a@example.com")[0].best_successor_candidate)
        for query in ("", "unknown"):
            with self.assertRaises(ValueError):
                resolve_person(report, query)

    def test_component_depth_and_root(self):
        self.assertEqual(DirectoryComponents(2).component("src/api/a.py"), "src/api")
        self.assertEqual(DirectoryComponents().component("README.md"), "(root)")
        with self.assertRaises(ValueError):
            DirectoryComponents(0)

    def test_persistence_and_as_of(self):
        report = analyze(History("head", (commit("a"), commit("a", days=100), commit("b"))), DirectoryComponents(), ScoringConfig())
        b = next(p for p in report.components[0].contributors if p.name == "b")
        self.assertEqual(b.signals["historical_persistence"], .5)
        with self.assertRaises(ValueError):
            analyze(History("head", (commit("a"),)), DirectoryComponents(), ScoringConfig(), NOW - timedelta(days=1))

    def test_binary_only_fallback_and_file_evidence(self):
        c = Commit("binary", Author("a", "a@example.com"), NOW, (Change("src/a", None, None),))
        report = analyze(History("head", (c,)), DirectoryComponents(), ScoringConfig())
        p = report.components[0].contributors[0]
        self.assertEqual(p.signals["change_ownership"], 1)
        self.assertEqual(p.file_activity["src/a"].commits, ["binary"])
        self.assertEqual(p.file_activity["src/a"].unknown_line_changes, 1)

    def test_nonoverlapping_successor_and_zero_score(self):
        history = History("head", (commit("a"), commit("b", "src/b.py")))
        report = analyze(history, DirectoryComponents(), ScoringConfig())
        self.assertIsNone(simulate_departure(report, "a@example.com")[0].best_successor_candidate)
        weights = dict.fromkeys(SIGNALS, 0.)
        weights["unique_contribution"] = 1.
        with self.assertRaises(ValueError):
            analyze(History("head", (commit("a"), commit("b"))), DirectoryComponents(), ScoringConfig(weights))
