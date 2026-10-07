"""Deterministic derivation of component-level pull-request review evidence."""
from collections import Counter, defaultdict
from dataclasses import dataclass

from continuity.domain.models import ComponentStrategy, DirectoryComponents
from continuity.domain.reviews import (
    PullRequestEvidence,
    ReviewEvidenceCollection,
    ReviewEvent,
    ReviewIdentity,
    ReviewState,
)


REVIEW_RISK_THRESHOLDS = ((0.40, "LOW"), (0.60, "MEDIUM"), (0.80, "HIGH"))


@dataclass(frozen=True)
class EffectiveReview:
    pull_request: str
    reviewer: ReviewIdentity | None
    event: ReviewEvent
    qualifying: bool
    exclusion_reason: str | None


@dataclass(frozen=True)
class ComponentReviewReport:
    component: str
    covered_pull_requests: int
    mapped_pull_requests: int
    coverage: float | None
    coverage_status: str
    reviewer_units: dict[str, int]
    reviewer_shares: dict[str, float]
    concentration: float | None
    risk: str | None
    unreviewed_pull_requests: tuple[str, ...]
    excluded_reasons: dict[str, int]


@dataclass(frozen=True)
class ReviewReport:
    provenance: ReviewEvidenceCollection
    components: tuple[ComponentReviewReport, ...]
    component_depth: int | None = None


def _event_order(event: ReviewEvent) -> tuple[float, int, str]:
    """Newest timestamp wins, then provider order, then stable provider id."""
    timestamp = event.submitted_at.timestamp() if event.submitted_at else float("-inf")
    order = event.provider_order if event.provider_order is not None else -1
    return timestamp, order, event.identifier


def effective_reviews(pull_request: PullRequestEvidence) -> tuple[EffectiveReview, ...]:
    """Choose one effective provider event per reviewer without losing event history."""
    unique_events: dict[str, ReviewEvent] = {}
    for event in pull_request.reviews:
        retained = unique_events.get(event.identifier)
        if retained is not None and _event_order(event) == _event_order(retained) and retained != event:
            raise ValueError("conflicting duplicate review event evidence")
        if retained is None or _event_order(event) > _event_order(retained):
            unique_events[event.identifier] = event
    grouped: dict[str, list[ReviewEvent]] = defaultdict(list)
    anonymous: list[ReviewEvent] = []
    for event in unique_events.values():
        if event.reviewer is None:
            anonymous.append(event)
        else:
            grouped[event.reviewer.identifier.casefold()].append(event)
    results: list[EffectiveReview] = []
    for key, events in grouped.items():
        event = max(events, key=_event_order)
        reviewer = event.reviewer
        assert reviewer is not None
        reason = _exclusion_reason(event, reviewer, pull_request.author)
        results.append(EffectiveReview(pull_request.identifier, reviewer, event, reason is None, reason))
    for event in anonymous:
        results.append(EffectiveReview(pull_request.identifier, None, event, False, "missing_reviewer"))
    return tuple(sorted(results, key=lambda review: ((review.reviewer.identifier if review.reviewer else ""), review.event.identifier)))


def _exclusion_reason(event: ReviewEvent, reviewer: ReviewIdentity, author: ReviewIdentity) -> str | None:
    if event.dismissed or event.state is ReviewState.DISMISSED:
        return "dismissed"
    if reviewer.identifier.casefold() == author.identifier.casefold():
        return "self_review"
    if reviewer.is_bot:
        return "provider_declared_bot"
    if event.state is ReviewState.COMMENTED:
        return "commented"
    if event.state not in (ReviewState.APPROVED, ReviewState.CHANGES_REQUESTED):
        return "unsupported_state"
    return None


def _risk(concentration: float) -> str:
    for threshold, label in REVIEW_RISK_THRESHOLDS:
        if concentration < threshold:
            return label
    return "CRITICAL"


def analyze_reviews(evidence: ReviewEvidenceCollection, strategy: ComponentStrategy) -> ReviewReport:
    """Map merged PR review evidence to components using the existing strategy."""
    mapped: dict[str, dict[str, list[EffectiveReview]]] = defaultdict(lambda: defaultdict(list))
    unique_pull_requests: dict[str, PullRequestEvidence] = {}
    for pull_request in evidence.pull_requests:
        existing = unique_pull_requests.get(pull_request.identifier)
        if existing is not None:
            if existing != pull_request:
                raise ValueError(f"conflicting duplicate pull request evidence: {pull_request.identifier}")
            continue
        unique_pull_requests[pull_request.identifier] = pull_request
    for pull_request in unique_pull_requests.values():
        if pull_request.merged_at is None:
            continue
        components = {strategy.component(path) for path in pull_request.changed_paths}
        derived = effective_reviews(pull_request)
        for component in components:
            mapped[component][pull_request.identifier].extend(derived)
    reports: list[ComponentReviewReport] = []
    for component, pull_requests in sorted(mapped.items()):
        units: Counter[str] = Counter()
        uncovered: list[str] = []
        exclusions: Counter[str] = Counter()
        covered = 0
        for identifier, reviews in sorted(pull_requests.items()):
            qualifying = [review for review in reviews if review.qualifying and review.reviewer is not None]
            if qualifying:
                covered += 1
                units.update(review.reviewer.identifier.casefold() for review in qualifying if review.reviewer is not None)
            else:
                uncovered.append(identifier)
            exclusions.update(review.exclusion_reason for review in reviews if review.exclusion_reason)
        total_units = sum(units.values())
        shares = {reviewer: count / total_units for reviewer, count in sorted(units.items())} if total_units else {}
        concentration = sum(share ** 2 for share in shares.values()) if shares else None
        denominator = len(pull_requests)
        reports.append(ComponentReviewReport(
            component=component,
            covered_pull_requests=covered,
            mapped_pull_requests=denominator,
            coverage=covered / denominator if denominator else None,
            coverage_status=evidence.status.value,
            reviewer_units=dict(sorted(units.items())),
            reviewer_shares=shares,
            concentration=concentration,
            risk=_risk(concentration) if concentration is not None else None,
            unreviewed_pull_requests=tuple(uncovered),
            excluded_reasons=dict(sorted(exclusions.items())),
        ))
    return ReviewReport(evidence, tuple(reports), strategy.depth if isinstance(strategy, DirectoryComponents) else None)
