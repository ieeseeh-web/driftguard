from __future__ import annotations

from typing import Literal

RiskLevel = Literal["low", "medium", "high", "critical"]
Recommendation = Literal["continue", "revise", "ask_user", "stop", "store_memory", "skip_memory"]


def risk_level(score: float) -> RiskLevel:
    if score < 0.2:
        return "low"
    if score < 0.5:
        return "medium"
    if score < 0.8:
        return "high"
    return "critical"


def recommendation(score: float, *, evaluation_type: str, hard_stop: bool = False) -> Recommendation:
    if hard_stop:
        return "stop"
    if evaluation_type == "memory":
        return "store_memory" if score < 0.5 else "skip_memory"
    if score < 0.2:
        return "continue"
    if score < 0.5:
        return "revise"
    if score < 0.8:
        return "ask_user"
    return "stop"


def weighted_drift_score(scores: dict[str, float]) -> float:
    weights = {
        "goal_alignment_risk": 0.30,
        "instruction_risk": 0.25,
        "tool_risk": 0.20,
        "memory_risk": 0.15,
        "safety_risk": 0.10,
    }
    total_weight = 0.0
    total = 0.0
    for key, weight in weights.items():
        if key in scores:
            total += scores[key] * weight
            total_weight += weight
    if total_weight == 0:
        return max(scores.values(), default=0.0)
    return round(total / total_weight, 4)
