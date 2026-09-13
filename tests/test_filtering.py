from datetime import datetime, timezone
import unittest

from continuity.analysis.filtering import FilterConfig, filter_history
from continuity.analysis.service import analyze
from continuity.domain.models import Author, Change, Commit, DirectoryComponents, History
from continuity.scoring.model import ScoringConfig


class FilteringTests(unittest.TestCase):
    def setUp(self):
        self.old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.new = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.history = History("head", (
            Commit("human", Author("Alice", "alice@example.com"), self.old, (
                Change("src/a.py", 1, 0), Change("src/client.g.cs", 100, 0),
                Change("vendor/library.py", 50, 0))),
            Commit("bot", Author("dependabot[bot]", "bot@example.com"), self.new,
                   (Change("src/a.py", 1000, 0),)),
        ), True)

    def test_disabled_is_identity(self):
        history, evidence = filter_history(self.history, FilterConfig())
        self.assertEqual(history, self.history)
        self.assertEqual(evidence.retained_file_changes, 4)
        self.assertEqual(evidence.excluded_file_changes, 0)

    def test_combined_filters_preserve_metadata_and_audit(self):
        history, evidence = filter_history(self.history, FilterConfig(True, True, ("vendor/*",)))
        self.assertEqual(history.revision, "head")
        self.assertTrue(history.shallow)
        self.assertEqual(len(history.commits), 2)
        self.assertEqual(history.commits[1].changes, ())
        self.assertEqual(evidence.retained_file_changes, 1)
        self.assertEqual(evidence.reasons, {"bot_marker": 1, "generated_path": 1, "path_pattern": 1})
        self.assertEqual(evidence.excluded_authors, ("bot@example.com",))
        report = analyze(history, DirectoryComponents(), ScoringConfig())
        self.assertEqual(report.as_of, self.new)
        self.assertEqual(len(report.components), 1)
        self.assertEqual(report.components[0].contributors[0].additions, 1)
        self.assertEqual(report.components[0].risk, "CRITICAL")
        self.assertLess(report.components[0].contributors[0].signals['recency'], .5)

    def test_explicit_author_case_and_reason_precedence(self):
        history, evidence = filter_history(self.history, FilterConfig(True, True, ("*",), ("ALICE@*",)))
        self.assertEqual(evidence.excluded_file_changes, 4)
        self.assertEqual(evidence.reasons, {"author_pattern": 3, "bot_marker": 1})
        report = analyze(history, DirectoryComponents(), ScoringConfig())
        self.assertEqual(report.components, ())

    def test_paths_case_sensitive_and_glob_matches_slashes(self):
        _, evidence = filter_history(self.history, FilterConfig(paths=("SRC/*",)))
        self.assertEqual(evidence.excluded_file_changes, 0)
        _, evidence = filter_history(self.history, FilterConfig(paths=("*.g.cs",)))
        self.assertEqual(evidence.excluded_file_changes, 1)
