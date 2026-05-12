from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from .evaluator import evaluate
from .models import EvaluationRequest, EvaluationResult
from .policy import recommendation, risk_level, weighted_drift_score

ReviewType = Literal["final_response", "tool_call", "memory_update", "plan", "handoff", "execution_log"]
AgentRecommendation = Literal["continue", "revise", "ask_user", "stop", "skip_memory"]


@dataclass
class AgentReviewRequest:
    review_type: ReviewType
    user_request: str
    artifact: dict[str, Any]
    session_id: str | None = None
    agent_id: str | None = None
    agent_role: str = ""
    constraints: list[str] = field(default_factory=list)
    explicit_instructions: list[str] = field(default_factory=list)
    context_summary: str = ""
    policy: dict[str, Any] = field(default_factory=dict)
    output_preferences: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentReviewRequest":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class EvidenceItem:
    type: str
    description: str
    source: str = "artifact"


@dataclass
class AgentReviewPlan:
    review_type: ReviewType
    evaluation_steps: list[str]
    required_checks: list[str]
    required_evidence: list[str] = field(default_factory=list)
    rubric: dict[str, float] = field(default_factory=dict)
    max_depth: str = "standard"


@dataclass
class JudgeFinding:
    judge_name: str
    score: float
    confidence: float
    finding: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    recommendation: AgentRecommendation = "continue"


@dataclass
class AgentReviewResult:
    review_id: str
    timestamp: str
    review_type: ReviewType
    drift_types: list[str]
    scores: dict[str, float]
    overall_drift_score: float
    risk_level: str
    recommendation: AgentRecommendation
    requires_human_confirmation: bool
    reason: str
    evidence: list[EvidenceItem]
    guidance: list[str]
    evaluation_plan: AgentReviewPlan | None = None
    judge_results: list[JudgeFinding] = field(default_factory=list)
    confidence: float = 0.0
    verification_status: str = "not_run"
    suggested_user_confirmation_message: str = ""
    safe_rewrite: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _result_score(result: EvaluationResult, *keys: str) -> float:
    for key in keys:
        if key in result.scores:
            return result.scores[key]
    return result.scores.get("overall_drift", 0.0)


def _artifact_text(artifact: dict[str, Any]) -> str:
    parts = [
        artifact.get("agent_plan") or "",
        artifact.get("agent_output") or "",
        artifact.get("current_goal") or "",
        "\n".join(artifact.get("execution_log", []) or []),
        json.dumps(artifact.get("handoff_messages", []) or [], ensure_ascii=False),
    ]
    return "\n".join(part for part in parts if part)


def _eval_goal_like(request: AgentReviewRequest) -> EvaluationResult:
    artifact = request.artifact
    return evaluate(EvaluationRequest(
        evaluation_type="goal",
        user_request=request.user_request,
        agent_plan=artifact.get("agent_plan"),
        agent_output=_artifact_text(artifact),
        current_goal=artifact.get("current_goal"),
        constraints=request.constraints,
    ))


def _eval_instruction(request: AgentReviewRequest) -> EvaluationResult | None:
    if not request.explicit_instructions:
        return None
    artifact = request.artifact
    return evaluate(EvaluationRequest(
        evaluation_type="instruction",
        agent_plan=artifact.get("agent_plan"),
        agent_output=_artifact_text(artifact),
        explicit_instructions=request.explicit_instructions,
    ))


def _eval_tool(request: AgentReviewRequest) -> EvaluationResult:
    artifact = request.artifact
    return evaluate(EvaluationRequest(
        evaluation_type="tool",
        user_request=request.user_request,
        current_goal=artifact.get("current_goal"),
        tool_name=artifact.get("tool_name"),
        tool_args=artifact.get("tool_args") or {},
        expected_side_effects=artifact.get("expected_side_effects") or [],
    ))


def _eval_memory(request: AgentReviewRequest) -> EvaluationResult:
    artifact = request.artifact
    return evaluate(EvaluationRequest(
        evaluation_type="memory",
        candidate_memory=artifact.get("candidate_memory"),
        source_message=artifact.get("source_message"),
        existing_memories=artifact.get("existing_memories") or [],
        user_explicitly_asked_to_remember=bool(artifact.get("user_explicitly_asked_to_remember", False)),
    ))


def _plan_for(request: AgentReviewRequest) -> AgentReviewPlan:
    common_steps = [
        "원본 사용자 요청과 평가 대상 artifact를 분리해 읽는다.",
        "명시 지시, 제약, 정책을 평가 기준으로 고정한다.",
    ]
    if request.review_type == "tool_call":
        return AgentReviewPlan(
            review_type=request.review_type,
            evaluation_steps=common_steps + [
                "도구 호출 목적과 원본 요청의 관련성을 확인한다.",
                "도구 부작용과 되돌리기 어려운 변경 여부를 확인한다.",
                "사용자 확인 필요 여부를 결정한다.",
            ],
            required_checks=["tool", "safety", "goal"],
            required_evidence=["tool_name", "tool_args", "expected_side_effects"],
            rubric={"tool": 0.45, "safety": 0.35, "goal": 0.20},
        )
    if request.review_type == "memory_update":
        return AgentReviewPlan(
            review_type=request.review_type,
            evaluation_steps=common_steps + [
                "메모리 후보가 장기 저장 가치가 있는지 확인한다.",
                "민감정보, 일시적 선호, 과도한 일반화 여부를 확인한다.",
            ],
            required_checks=["memory", "safety"],
            required_evidence=["candidate_memory", "source_message"],
            rubric={"memory": 0.75, "safety": 0.25},
        )
    if request.review_type == "handoff":
        return AgentReviewPlan(
            review_type=request.review_type,
            evaluation_steps=common_steps + [
                "handoff 메시지가 원본 요청과 핵심 제약을 보존하는지 확인한다.",
                "하위 에이전트에게 위험하거나 범위를 벗어난 행동을 지시하는지 확인한다.",
            ],
            required_checks=["goal", "instruction", "multi_agent", "safety"],
            required_evidence=["handoff_messages", "constraints"],
            rubric={"goal": 0.30, "instruction": 0.25, "multi_agent": 0.30, "safety": 0.15},
        )
    if request.review_type == "execution_log":
        return AgentReviewPlan(
            review_type=request.review_type,
            evaluation_steps=common_steps + [
                "실행 로그에서 목표 이탈과 위험 도구 사용을 확인한다.",
                "로그의 행동이 사용자 승인 범위 안에 있었는지 확인한다.",
            ],
            required_checks=["goal", "instruction", "tool", "safety", "evidence"],
            required_evidence=["execution_log"],
            rubric={"goal": 0.25, "instruction": 0.20, "tool": 0.30, "safety": 0.25},
        )
    return AgentReviewPlan(
        review_type=request.review_type,
        evaluation_steps=common_steps + [
            "산출물이 원본 목표와 명시 지시를 충족하는지 확인한다.",
            "수정 또는 사용자 확인이 필요한 drift 신호를 정리한다.",
        ],
        required_checks=["goal", "instruction"],
        required_evidence=["agent_plan", "agent_output", "current_goal"],
        rubric={"goal": 0.60, "instruction": 0.40},
    )


def _guidance_for(drift_types: list[str], rec: str, request: AgentReviewRequest) -> list[str]:
    guidance: list[str] = []
    if "goal" in drift_types:
        guidance.append("원본 사용자 요청과 현재 계획/응답을 다시 비교하고, 요청 범위를 벗어난 작업을 제거하세요.")
    if "instruction" in drift_types:
        guidance.append("명시적 지시사항과 제약조건을 체크리스트로 재반영한 뒤 산출물을 수정하세요.")
    if "tool" in drift_types:
        guidance.append("도구 호출의 필요성과 부작용을 설명하고, 삭제·전송·배포 등 되돌리기 어려운 작업은 사용자 확인을 받으세요.")
    if "memory" in drift_types:
        guidance.append("민감정보, 일시적 선호, 추론성 정보, 과도한 일반화는 장기 메모리에 저장하지 마세요.")
    if "multi_agent" in drift_types:
        guidance.append("하위 에이전트에게 원본 요청과 핵심 제약사항을 함께 전달하도록 handoff 메시지를 재작성하세요.")
    if "safety" in drift_types:
        guidance.append("외부 영향 또는 민감정보가 포함된 행동은 fail-closed로 처리하고 사용자 승인을 요청하세요.")
    if not guidance:
        guidance.append("현재 산출물은 큰 Drift 신호가 낮습니다. 기존 계획대로 진행하되 결과를 검증하세요.")
    if rec == "revise":
        guidance.append("수정 후 같은 입력 형식으로 DriftGuard Agent Review를 다시 실행하세요.")
    return guidance


def _risky_text_hits(text: str) -> list[str]:
    lowered = text.lower()
    keywords = [
        "delete", "rm", "drop", "truncate", "삭제", "send", "email", "deploy", "publish",
        "pay", "purchase", "결제", "배포", "password", "secret", "token", "api key", "비밀번호", "토큰",
    ]
    return [keyword for keyword in keywords if keyword in lowered]


def _requires_confirmation(request: AgentReviewRequest, overall: float, drift_types: list[str], rec: str) -> bool:
    artifact = request.artifact
    side_effects = " ".join(artifact.get("expected_side_effects") or []).lower()
    tool_blob = f"{artifact.get('tool_name', '')} {artifact.get('tool_args', {})}".lower()
    execution_blob = "\n".join(artifact.get("execution_log", []) or [])
    handoff_blob = json.dumps(artifact.get("handoff_messages", []) or [], ensure_ascii=False)
    external_or_destructive = bool(_risky_text_hits(f"{side_effects} {tool_blob} {execution_blob} {handoff_blob}"))
    return rec in {"ask_user", "stop"} or overall >= 0.5 or external_or_destructive or "safety" in drift_types


def review_agent(request: AgentReviewRequest) -> AgentReviewResult:
    plan = _plan_for(request)
    evidence: list[EvidenceItem] = []
    scores: dict[str, float] = {}
    drift_types: list[str] = []
    component_results: list[EvaluationResult] = []

    if request.review_type in {"final_response", "plan", "execution_log", "handoff"}:
        goal = _eval_goal_like(request)
        component_results.append(goal)
        scores["goal_drift"] = _result_score(goal, "goal_alignment_risk")
        if scores["goal_drift"] >= 0.2:
            drift_types.append("goal")
            evidence.append(EvidenceItem(type="goal", description=goal.reason, source="artifact"))
        instruction = _eval_instruction(request)
        if instruction:
            component_results.append(instruction)
            scores["instruction_drift"] = _result_score(instruction, "instruction_risk")
            if scores["instruction_drift"] >= 0.2:
                drift_types.append("instruction")
                evidence.append(EvidenceItem(type="instruction", description=instruction.reason, source="explicit_instructions"))
        if request.review_type == "handoff":
            handoff_text = json.dumps(request.artifact.get("handoff_messages", []), ensure_ascii=False)
            missing_constraints = [c for c in request.constraints if c and c.lower() not in handoff_text.lower()]
            risky_hits = _risky_text_hits(handoff_text)
            if missing_constraints:
                scores["multi_agent_drift"] = max(scores.get("multi_agent_drift", 0.0), 0.45)
                drift_types.append("multi_agent")
                evidence.append(EvidenceItem(
                    type="multi_agent",
                    description=f"handoff 메시지에 원본 제약사항 일부가 포함되지 않았습니다: {', '.join(missing_constraints)}.",
                    source="handoff_messages",
                ))
            if risky_hits:
                scores["safety_risk"] = max(scores.get("safety_risk", 0.0), 0.65)
                drift_types.append("safety")
                evidence.append(EvidenceItem(
                    type="safety",
                    description=f"handoff 중 고위험 행동 또는 민감정보 키워드가 감지되었습니다: {', '.join(risky_hits)}.",
                    source="handoff_messages",
                ))

        if request.review_type == "execution_log":
            execution_text = "\n".join(request.artifact.get("execution_log", []) or [])
            risky_hits = _risky_text_hits(execution_text)
            if risky_hits:
                scores["tool_risk"] = max(scores.get("tool_risk", 0.0), 0.70)
                scores["safety_risk"] = max(scores.get("safety_risk", 0.0), 0.65)
                drift_types.extend(["tool", "safety"])
                evidence.append(EvidenceItem(
                    type="tool",
                    description=f"실행 로그에서 고위험 도구/외부 영향/민감정보 키워드가 감지되었습니다: {', '.join(risky_hits)}.",
                    source="execution_log",
                ))

    if request.review_type == "tool_call":
        tool = _eval_tool(request)
        component_results.append(tool)
        scores["tool_risk"] = _result_score(tool, "tool_risk")
        if scores["tool_risk"] >= 0.2:
            drift_types.append("tool")
            evidence.append(EvidenceItem(type="tool", description=tool.reason, source="artifact.tool"))
        if scores["tool_risk"] >= 0.5:
            drift_types.append("safety")

    if request.review_type == "memory_update":
        memory = _eval_memory(request)
        component_results.append(memory)
        scores["memory_risk"] = _result_score(memory, "memory_risk")
        source_message = (request.artifact.get("source_message") or request.user_request or "").lower()
        candidate_memory = (request.artifact.get("candidate_memory") or "").lower()
        temporary_source = any(word in source_message for word in ["오늘", "이번만", "잠깐", "지금은", "today", "for now", "temporarily"])
        overgeneralized_candidate = any(word in candidate_memory for word in ["항상", "늘", "무조건", "always", "only"])
        if temporary_source and overgeneralized_candidate:
            scores["memory_risk"] = max(scores["memory_risk"], 0.65)
            evidence.append(EvidenceItem(
                type="memory",
                description="일시적 요청을 영구 선호처럼 과도하게 일반화했습니다.",
                source="artifact.source_message",
            ))
        if scores["memory_risk"] >= 0.2:
            drift_types.append("memory")
            if not any(item.type == "memory" for item in evidence):
                evidence.append(EvidenceItem(type="memory", description=memory.reason, source="artifact.candidate_memory"))
        if scores["memory_risk"] >= 0.7:
            drift_types.append("safety")

    drift_types = sorted(set(drift_types), key=drift_types.index)
    if not drift_types:
        drift_types = ["none"]

    # Map agent-review score keys to the existing weighted policy keys where possible.
    policy_scores = {
        "goal_alignment_risk": scores.get("goal_drift", 0.0),
        "instruction_risk": scores.get("instruction_drift", 0.0),
        "tool_risk": scores.get("tool_risk", 0.0),
        "memory_risk": scores.get("memory_risk", 0.0),
        "safety_risk": scores.get("safety_risk", 0.0),
    }
    non_zero_policy_scores = {k: v for k, v in policy_scores.items() if v > 0}
    overall = weighted_drift_score(non_zero_policy_scores) if non_zero_policy_scores else 0.0
    if scores:
        overall = max(overall, max(scores.values()) if request.review_type in {"tool_call", "memory_update"} else overall)
    overall = round(min(1.0, overall), 4)

    rec = recommendation(overall, evaluation_type="memory" if request.review_type == "memory_update" else "final")
    if rec == "store_memory":
        rec = "continue"
    if rec == "skip_memory":
        rec = "skip_memory"
    requires_confirmation = _requires_confirmation(request, overall, drift_types, rec)

    if request.review_type == "memory_update" and rec in {"revise", "ask_user", "stop", "skip_memory"} and overall >= 0.5:
        rec = "skip_memory"
        requires_confirmation = False
    if requires_confirmation and rec == "continue":
        rec = "ask_user"

    reason_parts = [r.reason for r in component_results]
    reason = " ".join(reason_parts) if reason_parts else "평가 가능한 산출물을 기준으로 Agent Drift 신호를 검토했습니다."
    guidance = _guidance_for(drift_types, rec, request)
    judge_results = _judge_findings(scores, evidence, rec)  # type: ignore[arg-type]
    confidence = _confidence_for(judge_results, evidence, request)
    verification_status = "evidence_collected" if evidence else "not_run"

    confirmation = ""
    if requires_confirmation:
        confirmation = "현재 작업은 원본 요청 범위, 안전 정책, 또는 외부/파괴적 부작용 측면에서 확인이 필요합니다. 계속 진행할까요?"

    return AgentReviewResult(
        review_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        review_type=request.review_type,
        drift_types=drift_types,
        scores=scores,
        overall_drift_score=overall,
        risk_level=risk_level(overall),
        recommendation=rec,  # type: ignore[arg-type]
        requires_human_confirmation=requires_confirmation,
        reason=reason,
        evidence=evidence,
        guidance=guidance,
        evaluation_plan=plan,
        judge_results=judge_results,
        confidence=confidence,
        verification_status=verification_status,
        suggested_user_confirmation_message=confirmation,
        metadata={"session_id": request.session_id, "agent_id": request.agent_id},
    )


def _judge_findings(scores: dict[str, float], evidence: list[EvidenceItem], rec: AgentRecommendation) -> list[JudgeFinding]:
    mapping = {
        "goal_drift": "goal_judge",
        "instruction_drift": "instruction_judge",
        "tool_risk": "tool_judge",
        "memory_risk": "memory_judge",
        "multi_agent_drift": "handoff_judge",
        "safety_risk": "safety_judge",
    }
    findings: list[JudgeFinding] = []
    for score_key, judge_name in mapping.items():
        if score_key not in scores:
            continue
        score = round(scores[score_key], 4)
        evidence_type = score_key.replace("_drift", "").replace("_risk", "")
        if evidence_type == "multi_agent":
            related = [item for item in evidence if item.type == "multi_agent"]
        elif evidence_type == "safety":
            related = [item for item in evidence if item.type == "safety"]
        else:
            related = [item for item in evidence if item.type == evidence_type]
        finding = related[0].description if related else f"{judge_name}가 {score_key}={score} 신호를 산출했습니다."
        judge_rec: AgentRecommendation = rec if score >= 0.5 else ("revise" if score >= 0.2 else "continue")
        findings.append(JudgeFinding(
            judge_name=judge_name,
            score=score,
            confidence=round(0.9 if related else 0.65, 2),
            finding=finding,
            evidence=related,
            recommendation=judge_rec,
        ))
    if not findings:
        findings.append(JudgeFinding(
            judge_name="overall_judge",
            score=0.0,
            confidence=0.75,
            finding="큰 Agent Drift 신호가 감지되지 않았습니다.",
            evidence=[],
            recommendation="continue",
        ))
    return findings


def _confidence_for(judge_results: list[JudgeFinding], evidence: list[EvidenceItem], request: AgentReviewRequest) -> float:
    if not judge_results:
        return 0.0
    base = sum(item.confidence for item in judge_results) / len(judge_results)
    if request.review_type in {"execution_log", "handoff", "tool_call", "memory_update"} and evidence:
        base += 0.05
    if request.review_type in {"final_response", "plan"} and not evidence:
        base -= 0.05
    return round(max(0.0, min(1.0, base)), 2)


def result_to_markdown(result: AgentReviewResult) -> str:
    detected = "\n".join(
        f"- {item.type}: {item.description}" for item in result.evidence
    ) or "- none: 큰 Drift 신호가 감지되지 않았습니다."
    guidance = "\n".join(f"{idx}. {text}" for idx, text in enumerate(result.guidance, 1))
    plan_steps = "\n".join(
        f"{idx}. {step}" for idx, step in enumerate(result.evaluation_plan.evaluation_steps, 1)
    ) if result.evaluation_plan else "- not planned"
    judges = "\n".join(
        f"- {judge.judge_name}: score={judge.score}, confidence={judge.confidence}, recommendation={judge.recommendation} — {judge.finding}"
        for judge in result.judge_results
    ) or "- none"
    json_blob = json.dumps(asdict(result), ensure_ascii=False, indent=2)
    return f"""## DriftGuard Agent Review

### Summary
- Risk Level: {result.risk_level}
- Overall Drift Score: {result.overall_drift_score}
- Confidence: {result.confidence}
- Verification Status: {result.verification_status}
- Recommendation: {result.recommendation}
- Requires Human Confirmation: {str(result.requires_human_confirmation).lower()}

### Evaluation Plan
{plan_steps}

### Judge Breakdown
{judges}

### Detected Drift
{detected}

### Reason
{result.reason}

### Guidance
{guidance}

### Structured Result
```json
{json_blob}
```
"""


def result_to_dict(result: AgentReviewResult) -> dict[str, Any]:
    return asdict(result)
