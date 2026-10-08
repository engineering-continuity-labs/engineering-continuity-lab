"""Shared synthetic report-v3 fixture factory for Python and browser tests."""
from continuity.analysis.traceability import derive
from continuity.reporting.traceability import with_traceability
from continuity.traceability_providers.synthetic import SyntheticTraceabilityProvider


def synthetic_v3_report(variant="BASE"):
    git_report = {
        "model": "experimental-v0.1",
        "revision": "synthetic-report-v3",
        "as_of": "2026-10-07T00:00:00+00:00",
        "commit_count": 0,
        "components": [],
    }
    return with_traceability(git_report, derive(SyntheticTraceabilityProvider(variant).acquire()))