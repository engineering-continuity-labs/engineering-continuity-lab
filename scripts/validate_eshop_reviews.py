"""Manual public-provider validation; writes only normalized evidence and counts."""
from collections import Counter
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from continuity.analysis.reviews import analyze_reviews, effective_reviews
from continuity.domain.models import DirectoryComponents
from continuity.domain.reviews import ReviewEvidenceRequest
from continuity.review_providers.github import BOUNDARY, GitHubPublicReviewEvidence


def main() -> None:
    evidence = GitHubPublicReviewEvidence().acquire(
        ReviewEvidenceRequest("https://github.com/dotnet/eShop", BOUNDARY))
    report = analyze_reviews(evidence, DirectoryComponents())
    effective = [r for pr in evidence.pull_requests for r in effective_reviews(pr)]
    summary = {
        "retrieved_at": evidence.provenance.retrieved_at.isoformat(),
        "evidence_boundary": evidence.provenance.evidence_boundary,
        "status": evidence.status.value,
        "closed_pull_requests_inspected": evidence.closed_pull_requests_inspected,
        "merged_pull_requests_observed": evidence.merged_pull_requests_observed,
        "merged_pull_requests_retained": len(evidence.pull_requests),
        "review_events": sum(len(pr.reviews) for pr in evidence.pull_requests),
        "qualifying_effective_reviews": sum(r.qualifying for r in effective),
        "components_with_review_evidence": len(report.components),
        "coverage": {c.component: {"covered": c.covered_pull_requests, "mapped": c.mapped_pull_requests,
                                   "coverage": c.coverage} for c in report.components},
        "concentration": {c.component: {"hhi": c.concentration, "risk": c.risk} for c in report.components},
        "excluded_review_reasons": dict(Counter(r.exclusion_reason for r in effective if r.exclusion_reason)),
        "diagnostics": evidence.diagnostics,
        "public_api_limitations": evidence.status.value != "COMPLETE",
    }
    def encode(value: object) -> str:
        return value.isoformat() if isinstance(value, datetime) else str(value)
    Path("docs/validation/eshop-v0.2-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    normalized = json.dumps(asdict(report), indent=2, default=encode)
    Path("ui/dist/eshop-reviews.js").write_text("// Normalized public validation snapshot; see docs/validation/eshop-v0.2-summary.json\nexport default " + normalized + ";\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("coverage", "concentration")}, indent=2))


if __name__ == "__main__":
    main()
