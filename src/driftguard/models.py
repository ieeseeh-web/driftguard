from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

EvaluationType = Literal["goal", "instruction", "tool", "memory", "final"]
RiskLevel = Literal["low", "medium", "high", "critical"]
Recommendation = Literal["continue", "revise", "ask_user", "stop", "store_memory", "skip_memory"]


@dataclass
class EvaluationRequest:
    evaluation_type: EvaluationType
    user_request: str = ""
    agent_output: str = ""
    agent_plan: str | None = None
    current_goal: str | None = None
    constraints: list[str] = field(default_factory=list)
    explicit_instructions: list[str] = field(default_factory=list)
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    expected_side_effects: list[str] = field(default_factory=list)
    candidate_memory: str | None = None
    source_message: str | None = None
    existing_memories: list[str] = field(default_factory=list)
    user_explicitly_asked_to_remember: bool = False
    agent_state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationRequest":
        aliases = {
            "type": "evaluation_type",
        }
        normalized = {aliases.get(k, k): v for k, v in data.items()}
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in normalized.items() if k in allowed})


@dataclass
class EvaluationResult:
    evaluation_id: str
    timestamp: str
    evaluation_type: EvaluationType
    scores: dict[str, float]
    risk_level: RiskLevel
    recommendation: Recommendation
    reason: str
    violations: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        evaluation_type: EvaluationType,
        scores: dict[str, float],
        risk_level: RiskLevel,
        recommendation: Recommendation,
        reason: str,
        violations: list[str] | None = None,
    ) -> "EvaluationResult":
        return cls(
            evaluation_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            evaluation_type=evaluation_type,
            scores=scores,
            risk_level=risk_level,
            recommendation=recommendation,
            reason=reason,
            violations=violations or [],
        )
