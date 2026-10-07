from unittest.mock import patch
import unittest

from continuity.domain.reviews import CollectionStatus, ReviewEvidenceRequest, ReviewState
from continuity.review_providers.github import GitHubPublicReviewEvidence, github_repository


class GitHubReviewProviderTests(unittest.TestCase):
    def test_public_url_normalization_and_rejection(self) -> None:
        self.assertEqual(github_repository("https://github.com/org/repo.git"), "org/repo")
        self.assertEqual(github_repository("git@github.com:org/repo.git"), "org/repo")
        with self.assertRaises(ValueError):
            github_repository("https://gitlab.com/org/repo")

    def test_acquires_all_pages_of_merged_review_evidence(self) -> None:
        provider = GitHubPublicReviewEvidence()
        responses = [
            ([{"number": 4, "merged_at": "2026-01-01T00:00:00Z", "user": {"login": "author"}}], True),
            ([], False),
            ([{"filename": "src/core/a.py"}], False),
            ([
                {"id": 1, "state": "APPROVED", "user": {"login": "reviewer"}, "submitted_at": "2026-01-02T00:00:00Z"},
                {"id": 2, "state": "COMMENTED", "user": {"login": "reviewer"}, "submitted_at": "2026-01-03T00:00:00Z"},
            ], False),
        ]
        with patch.object(provider, "_get", side_effect=responses):
            result = provider.acquire(ReviewEvidenceRequest("https://github.com/org/repo", "first page"))
        self.assertEqual(result.status, CollectionStatus.COMPLETE)
        self.assertEqual(result.provenance.repository, "org/repo")
        self.assertEqual(result.pull_requests[0].changed_paths, ("src/core/a.py",))
        self.assertEqual(result.pull_requests[0].reviews[-1].state, ReviewState.COMMENTED)

    def test_provider_failure_is_explicit_and_does_not_leak_detail(self) -> None:
        provider = GitHubPublicReviewEvidence()
        with patch.object(provider, "_get", side_effect=OSError("token=secret")):
            result = provider.acquire(ReviewEvidenceRequest("https://github.com/org/repo", "first page"))
        self.assertEqual(result.status, CollectionStatus.FAILED)
        self.assertEqual(result.pull_requests, ())
        self.assertNotIn("secret", result.diagnostics[0])

    def test_malformed_optional_review_fields_keep_valid_pr_evidence(self) -> None:
        provider = GitHubPublicReviewEvidence()
        responses = [
            ([{"number": 4, "merged_at": "2026-01-01T00:00:00Z", "user": {"login": "author"}}], False),
            ([{"filename": "src/core/a.py"}], False),
            ([{"id": 1, "state": "APPROVED", "user": {"login": " "}, "submitted_at": "not-a-time"}], False),
        ]
        with patch.object(provider, "_get", side_effect=responses):
            result = provider.acquire(ReviewEvidenceRequest("https://github.com/org/repo", "first page"))
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual(len(result.pull_requests), 1)
        self.assertIsNone(result.pull_requests[0].reviews[0].reviewer)
        self.assertIsNone(result.pull_requests[0].reviews[0].submitted_at)
        self.assertEqual(len(result.diagnostics), 2)


if __name__ == "__main__":
    unittest.main()
