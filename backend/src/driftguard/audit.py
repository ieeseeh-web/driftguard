from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agent_review import AgentReviewRequest, AgentReviewResult


def build_agent_review_audit_record(
    result: AgentReviewResult,
    request: AgentReviewRequest | None = None,
    *,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    """Build a compact JSONL-friendly audit record for observability.

    The full AgentReviewResult can be large and may include artifact-derived
    evidence. This record is intended for dashboards, filtering, and later
    exporter adapters without requiring external services.
    """

    metadata = result.metadata or {}
    sandbox = metadata.get("sandbox_verification") or {}
    top_judge = max(result.judge_results, key=lambda item: item.score, default=None)
    record: dict[str, Any] = {
        "event_type": "agent_review.audit",
        "schema_version": "1.0",
        "review_id": result.review_id,
        "timestamp": result.timestamp,
        "session_id": metadata.get("session_id"),
        "agent_id": metadata.get("agent_id"),
        "review_type": result.review_type,
        "judge_mode": metadata.get("judge_mode", "deterministic"),
        "judge_mode_status": metadata.get("judge_mode_status", "unknown"),
        "llm_adapter": metadata.get("llm_adapter"),
        "verification_status": result.verification_status,
        "sandbox_status": sandbox.get("status"),
        "risk_level": result.risk_level,
        "recommendation": result.recommendation,
        "requires_human_confirmation": result.requires_human_confirmation,
        "overall_drift_score": result.overall_drift_score,
        "confidence": result.confidence,
        "drift_types": result.drift_types,
        "scores": result.scores,
        "judge_count": len(result.judge_results),
        "evidence_count": len(result.evidence),
        "guidance_count": len(result.guidance),
        "top_judge": asdict(top_judge) if top_judge else None,
        "latency_ms": latency_ms,
    }
    if request is not None:
        record["request_context"] = {
            "has_constraints": bool(request.constraints),
            "constraints_count": len(request.constraints),
            "explicit_instructions_count": len(request.explicit_instructions),
            "artifact_keys": sorted(request.artifact.keys()),
            "output_format": request.output_preferences.get("format"),
        }
    return record


def append_jsonl(record: dict[str, Any], path: str | Path) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
