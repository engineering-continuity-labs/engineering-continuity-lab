"""Fixture tests for v0.2 provider-neutral review evidence derivation."""
from datetime import UTC, datetime, timedelta
import unittest

from continuity.analysis.reviews import analyze_reviews, effective_reviews
from continuity.domain.models import DirectoryComponents
from continuity.domain.reviews import (
    CollectionStatus,
    ProviderProvenance,
    PullRequestEvidence,
    ReviewEvidenceCollection,
    ReviewEvidenceRequest,
    ReviewEvent,
    ReviewIdentity,
    ReviewState,
)


NOW = datetime(2026, 10, 7, tzinfo=UTC)
AUTHOR = ReviewIdentity("author", "Author")
ALICE = ReviewIdentity("alice", "Alice")
BOB = ReviewIdentity("bob", "Bob")
BOT = ReviewIdentity("dependabot[bot]", "Dependabot", is_bot=True)


def event(identifier: str, state: ReviewState, reviewer: ReviewIdentity | None, offset: int = 0,
          *, dismissed: bool = False, order: int | None = None) -> ReviewEvent:
    return ReviewEvent(identifier, state, reviewer, NOW + timedelta(minutes=offset), order, dismissed)


def collection(*pull_requests: PullRequestEvidence, complete: bool = True,
               failures: tuple[str, ...] = ()) -> ReviewEvidenceCollection:
    return ReviewEvidenceCollection(
        ProviderProvenance("fixture", "public/example", "merged through 2026-10-07", NOW),
        pull_requests,
        CollectionStatus.COMPLETE if complete else CollectionStatus.PARTIAL,
        failures,
    )


def pull(identifier: str, paths: tuple[str, ...], reviews: tuple[ReviewEvent, ...],
         *, merged: bool = True) -> PullRequestEvidence:
    return PullRequestEvidence(identifier, AUTHOR, NOW if merged else None, paths, reviews)


class ReviewEvidenceTests(unittest.TestCase):
    def test_effective_review_is_newest_and_commented_does_not_qualify(self) -> None:
        evidence = pull("42", ("src/core/a.py",), (
            event("one", ReviewState.APPROVED, ALICE, 1),
            event("two", ReviewState.COMMENTED, ALICE, 2),
            event("three", ReviewState.CHANGES_REQUESTED, BOB, 1),
        ))
        reviews = effective_reviews(evidence)
        self.assertEqual([(r.reviewer.identifier if r.reviewer else None, r.event.state, r.qualifying) for r in reviews], [
            ("alice", ReviewState.COMMENTED, False), ("bob", ReviewState.CHANGES_REQUESTED, True),
        ])
        self.assertEqual(reviews[0].exclusion_reason, "commented")

    def test_component_report_maps_multiple_components_and_calculates_coverage(self) -> None:
        report = analyze_reviews(collection(
            pull("one", ("src/core/a.py", "docs/readme.md"), (event("a", ReviewState.APPROVED, ALICE),)),
            pull("two", ("src/core/b.py",), (event("b", ReviewState.COMMENTED, BOB),)),
        ), DirectoryComponents(depth=1))
        components = {item.component: item for item in report.components}
        self.assertEqual(set(components), {"docs", "src"})
        self.assertEqual((components["src"].covered_pull_requests, components["src"].mapped_pull_requests), (1, 2))
        self.assertEqual(components["src"].coverage, 0.5)
        self.assertEqual(components["src"].unreviewed_pull_requests, ("two",))
        self.assertEqual(components["src"].excluded_reasons, {"commented": 1})
        self.assertEqual(components["docs"].coverage, 1.0)

    def test_nonqualifying_reasons_and_no_units_are_explicit(self) -> None:
        report = analyze_reviews(collection(pull("one", ("src/a.py",), (
            event("self", ReviewState.APPROVED, AUTHOR),
            event("bot", ReviewState.APPROVED, BOT),
            event("dismissed", ReviewState.APPROVED, BOB, dismissed=True),
            event("unknown", ReviewState.UNKNOWN, None),
        ))), DirectoryComponents())
        item = report.components[0]
        self.assertEqual(item.coverage, 0.0)
        self.assertIsNone(item.concentration)
        self.assertIsNone(item.risk)
        self.assertEqual(item.excluded_reasons, {
            "dismissed": 1, "missing_reviewer": 1, "provider_declared_bot": 1, "self_review": 1,
        })

    def test_distribution_and_hhi_use_one_unit_per_reviewer_per_pr_component(self) -> None:
        report = analyze_reviews(collection(
            pull("one", ("src/a.py",), (event("a1", ReviewState.APPROVED, ALICE), event("a2", ReviewState.APPROVED, ALICE, 1))),
            pull("two", ("src/b.py",), (event("b1", ReviewState.APPROVED, ALICE), event("b2", ReviewState.APPROVED, BOB))),
        ), DirectoryComponents())
        item = report.components[0]
        self.assertEqual(item.reviewer_units, {"alice": 2, "bob": 1})
        self.assertAlmostEqual(item.concentration or 0, 5 / 9)
        self.assertEqual(item.risk, "MEDIUM")

    def test_unmerged_prs_do_not_contribute_and_partial_is_explicit(self) -> None:
        report = analyze_reviews(collection(
            pull("merged", ("src/a.py",), (event("a", ReviewState.APPROVED, ALICE),)),
            pull("open", ("src/b.py",), (event("b", ReviewState.APPROVED, BOB),), merged=False),
            complete=False,
            failures=("page two unavailable",),
        ), DirectoryComponents())
        self.assertEqual([item.component for item in report.components], ["src"])
        self.assertEqual(report.components[0].coverage_status, "PARTIAL")

    def test_duplicate_identifiers_do_not_multiply_and_result_is_deterministic(self) -> None:
        events = (
            event("same", ReviewState.APPROVED, ALICE, 1),
            event("same", ReviewState.COMMENTED, ALICE, 2),
            event("b", ReviewState.APPROVED, BOB, 2),
        )
        first = analyze_reviews(collection(pull("one", ("src/a.py",), events)), DirectoryComponents())
        second = analyze_reviews(collection(pull("one", ("src/a.py",), tuple(reversed(events)))), DirectoryComponents())
        self.assertEqual(first.components, second.components)
        self.assertEqual(first.components[0].reviewer_units, {"bob": 1})

    def test_duplicate_pull_requests_do_not_multiply_reviewer_units(self) -> None:
        evidence = pull("one", ("src/a.py",), (event("a", ReviewState.APPROVED, ALICE),))
        report = analyze_reviews(collection(evidence, evidence), DirectoryComponents())
        self.assertEqual(report.components[0].reviewer_units, {"alice": 1})

    def test_conflicting_duplicate_pull_requests_are_rejected(self) -> None:
        first = pull("one", ("src/a.py",), (event("a", ReviewState.APPROVED, ALICE),))
        second = pull("one", ("src/b.py",), (event("b", ReviewState.APPROVED, BOB),))
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            analyze_reviews(collection(first, second), DirectoryComponents())

    def test_provider_references_cannot_contain_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain credentials"):
            ProviderProvenance("fixture", "https://token@example.test/repo", "now", NOW)
        with self.assertRaisesRegex(ValueError, "must not contain credentials"):
            ReviewEvidenceRequest("https://user:secret@example.test/repo", "now")
        with self.assertRaisesRegex(ValueError, "must not contain credentials"):
            ProviderProvenance("fixture", "https://example.test/repo?access_token=secret", "now", NOW)
        with self.assertRaisesRegex(ValueError, "must not contain credentials"):
            ReviewEvidenceRequest("https://example.test/repo#token", "now")

    def test_failed_collection_is_not_reported_as_partial(self) -> None:
        evidence = collection(
            pull("one", ("src/a.py",), (event("a", ReviewState.APPROVED, ALICE),)),
            complete=False,
            failures=("authentication failed",),
        )
        failed = ReviewEvidenceCollection(
            evidence.provenance, evidence.pull_requests, CollectionStatus.FAILED, evidence.diagnostics,
        )
        self.assertEqual(analyze_reviews(evidence, DirectoryComponents()).components[0].coverage_status, "PARTIAL")
        self.assertEqual(analyze_reviews(failed, DirectoryComponents()).components[0].coverage_status, "FAILED")


if __name__ == "__main__":
    unittest.main()
