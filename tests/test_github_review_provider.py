"""ECL-AC-201/202/214/215/218/219/220: real Link and public failure fixtures."""
from io import BytesIO
from email.message import Message
from unittest.mock import patch, MagicMock
import unittest
from urllib.error import HTTPError

from continuity.domain.models import DirectoryComponents
from continuity.analysis.reviews import analyze_reviews
from continuity.domain.reviews import CollectionStatus, ReviewEvidenceRequest, ReviewState
from continuity.review_providers.github import GitHubPublicReviewEvidence, github_repository, RATE_LIMIT

REQUEST = ReviewEvidenceRequest("https://github.com/org/repo", "requested public history")
PULL = {"number": 4, "merged_at": "2026-01-01T00:00:00Z", "user": {"login": "author"}}
FILE = {"filename": "src/core/a.py"}
REVIEW = {"id": 1, "state": "APPROVED", "user": {"login": "reviewer"}, "submitted_at": "2026-01-02T00:00:00Z"}


def link(endpoint: str, page: int, query: str = "per_page=100") -> str:
    return f'<https://api.github.com/repos/org/repo/{endpoint}?{query}&page={page}>; rel="next", <https://api.github.com/repos/org/repo/{endpoint}?{query}&page=9>; rel="last"'


def limited(code: int = 403) -> HTTPError:
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    return HTTPError("https://api.github.com/private?secret", code, "secret", headers, BytesIO(b"secret"))


class GitHubReviewProviderTests(unittest.TestCase):
    def acquire(self, responses: list[object], maximum_pages: int = 1000):
        provider = GitHubPublicReviewEvidence(maximum_pages)
        with patch.object(provider, "_get", side_effect=responses) as get:
            result = provider.acquire(REQUEST)
        return result, get

    def test_public_url_normalization_and_rejection(self) -> None:
        for value in ("https://github.com/org/repo.git", "git@github.com:org/repo.git"):
            self.assertEqual(github_repository(value), "org/repo")
        for value in ("https://gitlab.com/org/repo", "https://secret@github.com/org/repo", "https://github.com/org/repo?secret"):
            with self.assertRaises(ValueError):
                github_repository(value)

    def test_real_get_preserves_link_and_detects_noncollection(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'[{"number":4},null]'
        header = link("pulls", 3)
        response.headers = {"Link": header}
        with patch("continuity.review_providers.github.urlopen", return_value=response) as open_url:
            self.assertEqual(GitHubPublicReviewEvidence()._get("/repos/org/repo/pulls"), ([{"number": 4}, None], header))
            self.assertNotIn("Authorization", open_url.call_args.args[0].headers)
            response.read.return_value = b'{}'
            with self.assertRaises(ValueError):
                GitHubPublicReviewEvidence()._get("/repos/org/repo/pulls")

    def test_all_three_endpoints_follow_exact_link_not_invented_page(self) -> None:
        query = "state=closed&sort=updated&direction=desc&per_page=100"
        result, get = self.acquire([
            ([PULL], link("pulls", 3, query)), ([{**PULL, "number": 5, "merged_at": None}], ""),
            ([FILE], link("pulls/4/files", 7)), ([{"filename": "docs/a.md"}], ""),
            ([REVIEW], link("pulls/4/reviews", 6)), ([{**REVIEW, "id": 2, "user": {"login": "bob"}}], ""),
        ])
        self.assertEqual(result.status, CollectionStatus.COMPLETE)
        self.assertEqual(result.diagnostics, ())
        self.assertEqual(result.closed_pull_requests_inspected, 2)
        self.assertEqual(result.merged_pull_requests_observed, 1)
        self.assertTrue(get.call_args_list[1].args[0].endswith("page=3"))
        self.assertTrue(get.call_args_list[3].args[0].endswith("page=7"))
        self.assertTrue(get.call_args_list[5].args[0].endswith("page=6"))
        self.assertEqual(result.pull_requests[0].changed_paths, ("docs/a.md", "src/core/a.py"))
        self.assertEqual(len(analyze_reviews(result, DirectoryComponents()).components), 2)

    def test_safety_limit_retains_pr_and_marks_partial(self) -> None:
        result, _ = self.acquire([([PULL], link("pulls", 2, "state=closed&sort=updated&direction=desc&per_page=100")), ([FILE], ""), ([REVIEW], "")], 1)
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual(len(result.pull_requests), 1)
        self.assertIn("safety page limit", " ".join(result.diagnostics))

    def test_unsafe_links_never_requested_and_partial_items_retained(self) -> None:
        for target in ("https://evil.test/repo?page=2", "https://secret@api.github.com/repos/org/repo/pulls?page=2", "https://api.github.com/repos/org/repo/pulls?access_token=secret&page=2", "https://api.github.com/repos/other/repo/pulls?page=2"):
            with self.subTest(target=target):
                result, get = self.acquire([([PULL], f'<{target}>; rel="next"'), ([FILE], ""), ([REVIEW], "")])
                self.assertEqual(result.status, CollectionStatus.PARTIAL)
                self.assertEqual(get.call_count, 3)
                self.assertNotIn("secret", str(result))

    def test_cycle_is_explicit(self) -> None:
        provider = GitHubPublicReviewEvidence()
        with patch.object(provider, "_get", return_value=([], link("pulls/4/files", 2))) as get:
            pages = provider._all("/repos/org/repo/pulls/4/files?per_page=100")
        self.assertTrue(pages.interrupted)
        self.assertEqual(get.call_count, 2)
        self.assertIn("cycle", pages.diagnostics[0])

    def test_failure_before_evidence_is_failed_and_safe(self) -> None:
        for error in (OSError("token=secret"), limited(403), limited(429), HTTPError("secret", 500, "secret", Message(), None)):
            with self.subTest(error=type(error)):
                result, _ = self.acquire([error])
                self.assertEqual(result.status, CollectionStatus.FAILED)
                self.assertFalse(result.pull_requests)
                self.assertNotIn("secret", str(result))
                if isinstance(error, HTTPError) and error.code in (403, 429):
                    self.assertEqual(result.diagnostics, (RATE_LIMIT,))

    def test_later_pr_page_failure_keeps_valid_evidence(self) -> None:
        result, _ = self.acquire([([PULL], link("pulls", 2, "state=closed&sort=updated&direction=desc&per_page=100")), limited(), ([FILE], ""), ([REVIEW], "")])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual(len(result.pull_requests), 1)
        self.assertIn(RATE_LIMIT, result.diagnostics)

    def test_secondary_rate_limit_body_is_detected_but_never_exposed(self) -> None:
        error = HTTPError("secret", 403, "secret", Message(), BytesIO(b'{"message":"secondary rate limit secret"}'))
        result, _ = self.acquire([error])
        self.assertEqual(result.diagnostics, (RATE_LIMIT,))
        self.assertNotIn("secret", str(result))

    def test_file_and_review_page_safety_limits_are_partial(self) -> None:
        for endpoint in ("files", "reviews"):
            responses = [([PULL], ""), ([FILE], link("pulls/4/files", 2) if endpoint == "files" else "")]
            if endpoint == "reviews":
                responses += [([REVIEW], link("pulls/4/reviews", 2))]
            result, _ = self.acquire(responses, 1)
            self.assertEqual(result.status, CollectionStatus.PARTIAL)
            self.assertEqual(len(result.pull_requests), 1)
            self.assertIn("safety page limit", " ".join(result.diagnostics))

    def test_ordinary_forbidden_is_safe_generic_failure(self) -> None:
        result, _ = self.acquire([HTTPError("secret", 403, "secret", Message(), BytesIO(b'forbidden secret'))])
        self.assertEqual(result.status, CollectionStatus.FAILED)
        self.assertNotIn(RATE_LIMIT, result.diagnostics)
        self.assertNotIn("secret", str(result))

    def test_later_file_or_review_failure_preserves_progress(self) -> None:
        for endpoint in ("files", "reviews"):
            responses = [([PULL], "")]
            if endpoint == "files":
                responses += [([FILE], link("pulls/4/files", 2)), limited()]
            else:
                responses += [([FILE], ""), ([REVIEW], link("pulls/4/reviews", 2)), limited()]
            result, _ = self.acquire(responses)
            self.assertEqual(result.status, CollectionStatus.PARTIAL)
            self.assertEqual(result.pull_requests[0].changed_paths, (FILE["filename"],))
            self.assertEqual(len(result.pull_requests[0].reviews), int(endpoint == "reviews"))

    def test_failure_after_completed_pr_does_not_erase_it(self) -> None:
        result, _ = self.acquire([([PULL, {**PULL, "number": 5}], ""), ([FILE], ""), ([REVIEW], ""), limited()])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual([pr.identifier for pr in result.pull_requests], ["4"])

    def test_no_usable_paths_on_failure_is_failed(self) -> None:
        result, _ = self.acquire([([PULL], ""), limited()])
        self.assertEqual(result.status, CollectionStatus.FAILED)

    def test_valid_empty_and_unmerged_collection_are_complete(self) -> None:
        for pulls in ([], [{**PULL, "merged_at": None}]):
            result, get = self.acquire([(pulls, "")])
            self.assertEqual(result.status, CollectionStatus.COMPLETE)
            self.assertFalse(result.pull_requests)
            self.assertEqual(get.call_count, 1)

    def test_malformed_required_pr_fields_are_isolated(self) -> None:
        for pull in ({"number": 4}, {**PULL, "number": True}, {**PULL, "user": None}, {**PULL, "merged_at": "2026-01-01"}, None):
            result, _ = self.acquire([([pull], "")])
            self.assertEqual(result.status, CollectionStatus.PARTIAL)
            self.assertFalse(result.pull_requests)

    def test_malformed_optional_fields_keep_valid_event_nonqualifying(self) -> None:
        result, _ = self.acquire([([PULL], ""), ([FILE], ""), ([{**REVIEW, "user": {"login": " "}, "submitted_at": "bad"}], "")])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        event = result.pull_requests[0].reviews[0]
        self.assertIsNone(event.reviewer)
        self.assertIsNone(event.submitted_at)

    def test_absent_optional_timestamp_uses_recorded_provider_order(self) -> None:
        result, _ = self.acquire([([PULL], ""), ([FILE], ""), ([{**REVIEW, "submitted_at": None}], "")])
        self.assertEqual(result.status, CollectionStatus.COMPLETE)
        self.assertEqual(result.pull_requests[0].reviews[0].provider_order, 1)
        self.assertIn("provider ordering", result.diagnostics[0])

    def test_duplicate_pr_and_event_ids_do_not_multiply_units(self) -> None:
        result, get = self.acquire([([PULL, PULL], ""), ([FILE], ""), ([REVIEW, REVIEW], "")])
        self.assertEqual(get.call_count, 3)
        self.assertEqual(len(result.pull_requests[0].reviews), 1)
        self.assertEqual(analyze_reviews(result, DirectoryComponents()).components[0].reviewer_units, {"reviewer": 1})

    def test_conflicting_review_duplicates_never_qualify(self) -> None:
        result, _ = self.acquire([([PULL], ""), ([FILE], ""), ([REVIEW, {**REVIEW, "state": "COMMENTED"}], "")])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual(result.pull_requests[0].reviews[0].state, ReviewState.UNKNOWN)

    def test_malformed_files_and_review_ids_mark_partial(self) -> None:
        result, _ = self.acquire([([PULL], ""), ([FILE, {"filename": "../secret"}], ""), ([{**REVIEW, "id": True}, REVIEW], "")])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertEqual(len(result.pull_requests[0].reviews), 1)

    def test_github_file_ceiling_never_claims_complete(self) -> None:
        result, _ = self.acquire([([PULL], ""), ([{"filename": f"src/{i}.py"} for i in range(3000)], ""), ([], "")])
        self.assertEqual(result.status, CollectionStatus.PARTIAL)
        self.assertIn("ceiling", " ".join(result.diagnostics))


if __name__ == "__main__":
    unittest.main()
