"""Pure, bounded signal calculation; scores are proxies, not probabilities."""
from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Mapping

SIGNALS = ("change_ownership", "recency", "change_frequency", "code_area_breadth",
           "unique_contribution", "historical_persistence")


@dataclass(frozen=True)
class ScoringConfig:
    weights: Mapping[str, float] = field(default_factory=lambda: {
        "change_ownership": .25, "recency": .20, "change_frequency": .20,
        "code_area_breadth": .15, "unique_contribution": .10, "historical_persistence": .10,
    })
    half_life_days: float = 180

    def __post_init__(self) -> None:
        if set(self.weights) != set(SIGNALS):
            raise ValueError("weights must specify exactly: " + ", ".join(SIGNALS))
        if any(not math.isfinite(w) or w < 0 for w in self.weights.values()):
            raise ValueError("weights must be finite and nonnegative")
        if sum(self.weights.values()) <= 0:
            raise ValueError("at least one weight must be positive")
        if not math.isfinite(self.half_life_days) or self.half_life_days <= 0:
            raise ValueError("half_life_days must be finite and positive")


def score(signals: Mapping[str, float], config: ScoringConfig) -> float:
    if set(signals) != set(SIGNALS) or any(not math.isfinite(v) or not 0 <= v <= 1 for v in signals.values()):
        raise ValueError("six finite signals in [0, 1] are required")
    return sum(signals[k] * config.weights[k] for k in SIGNALS) / sum(config.weights.values())


def recency(latest: datetime, as_of: datetime, half_life_days: float) -> float:
    age = max(0.0, (as_of - latest).total_seconds() / 86400)
    return 2 ** (-age / half_life_days)


def risk(concentration: float) -> str:
    if not math.isfinite(concentration) or not 0 <= concentration <= 1:
        raise ValueError("concentration must be in [0, 1]")
    if concentration >= .8:
        return "CRITICAL"
    if concentration >= .6:
        return "HIGH"
    if concentration >= .4:
        return "MEDIUM"
    return "LOW"
