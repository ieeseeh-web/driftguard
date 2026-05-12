# Agent-as-a-Judge 기반 DriftGuard 확장 계획

## 1. 목적

이 문서는 저장된 Agent-as-a-Judge 참고 자료를 DriftGuard 제품 방향으로 재구성한 실행 계획이다.

참고 자료:

- `agent/references/agent-as-a-judge-paper-summary.md`
- `agent/references/agent-as-a-judge-prd.md`
- `agent/references/agent-as-a-judge-development-guide.md`

DriftGuard의 현재 기능은 rule-based evaluator와 `review-agent` CLI를 통해 Agent Drift를 탐지하고 설명하는 MVP다. 다음 단계는 이를 **Agent-as-a-Judge 방식의 근거 기반 평가 에이전트**로 확장하는 것이다.

---

## 2. 핵심 방향

### 2.1 기존 LLM-as-a-Judge의 한계

Agent Drift 평가에서는 단일 LLM Judge만으로 부족하다.

- 최종 답변만 보고 평가하면 중간 단계 drift를 놓칠 수 있다.
- 그럴듯한 설명과 실제 검증 결과를 구분하기 어렵다.
- 위험 도구 호출, memory update, handoff 왜곡은 trace가 있어야 판단 가능하다.
- 긴 작업에서는 평가 기준과 문맥이 단계별로 변할 수 있다.

### 2.2 DriftGuard의 Agent-as-a-Judge 정의

DriftGuard에서 Agent-as-a-Judge는 다음 역할을 수행한다.

> 원본 사용자 의도, 실행 로그, 도구 결과, 메모리 후보, handoff 메시지를 분석해 목표 이탈과 정책 위험을 근거 기반으로 평가하고, 다음 행동을 권고하는 평가 에이전트.

핵심은 “점수 산출”이 아니라 **계획 → 검증 → 판단 → 권고** 흐름이다.

---

## 3. 목표 아키텍처

```text
Agent Review Request
  ↓
Evaluation Orchestrator
  ↓
Planner
  ↓
Tool / Evidence Router
  ├─ Rule-based Evaluator
  ├─ Execution Log Analyzer
  ├─ Tool Result Verifier
  ├─ Memory Policy Checker
  └─ Handoff Consistency Checker
  ↓
Judge Agents
  ├─ Goal Judge
  ├─ Instruction Judge
  ├─ Tool Judge
  ├─ Memory Judge
  ├─ Safety Judge
  └─ Evidence Judge
  ↓
Aggregator / Policy Engine
  ↓
Agent Review Result
  ├─ score
  ├─ confidence
  ├─ evidence
  ├─ recommendation
  └─ remediation guidance
```

---

## 4. 컴포넌트 설계

### 4.1 Evaluation Orchestrator

역할:

- review type 식별
- 평가 depth 결정
- planner, verifier, judge, aggregator 실행 순서 제어
- timeout/retry/fallback 관리

초기 구현 방향:

- 현재 `backend/src/driftguard/agent_review.py`의 단일 평가 흐름을 내부 함수 단위로 분리한다.
- 외부 API 서버는 아직 만들지 않고 CLI-first로 유지한다.

### 4.2 Planner

역할:

- 평가 대상에 필요한 기준과 도구를 결정한다.
- 평가 단계를 생성한다.

예시:

```json
{
  "evaluation_steps": [
    "Check original user goal",
    "Compare candidate action against explicit constraints",
    "Inspect tool calls for external side effects",
    "Verify whether human confirmation is required"
  ],
  "required_checks": ["goal", "instruction", "tool", "safety"],
  "rubric": {
    "goal": 0.35,
    "instruction": 0.25,
    "tool": 0.25,
    "safety": 0.15
  }
}
```

MVP에서는 LLM planner가 아니라 deterministic planner로 시작한다.

### 4.3 Tool / Evidence Router

역할:

- 실행 로그와 도구 결과를 평가 가능한 evidence로 변환한다.
- 위험 도구 호출, 실패한 도구 실행, 승인 누락을 수집한다.

초기 대상:

- `execution_log` 분석
- `tool_calls` 분석
- `candidate_memory` 분석
- `handoff_messages` 분석

보안 원칙:

- DriftGuard는 평가 도구를 실행하더라도 기본적으로 읽기 전용이어야 한다.
- Python/code execution은 별도 sandbox 설계 전까지 직접 실행하지 않는다.
- 외부 API 호출은 명시적 opt-in으로 제한한다.

### 4.4 Judge Agents

초기에는 실제 sub-agent 분리가 아니라 모듈형 judge 함수로 구현한다.

| Judge | 역할 | 현재 MVP와 연결 |
|---|---|---|
| Goal Judge | 원본 목표 대비 산출물/행동 비교 | goal score |
| Instruction Judge | 명시 지시와 제약 준수 확인 | instruction guidance |
| Tool Judge | 도구 호출 필요성·위험·승인 필요성 평가 | tool risk |
| Memory Judge | 장기 저장 가치와 민감도 평가 | memory policy |
| Safety Judge | 외부 영향, 민감정보, 되돌리기 어려운 행동 탐지 | policy recommendation |
| Evidence Judge | 근거 충분성, 로그·도구 결과와 결론 일치성 확인 | future extension |

### 4.5 Aggregator / Policy Engine

역할:

- judge 결과를 통합해 final score와 recommendation을 결정한다.
- score와 confidence를 분리한다.

권장 정책:

| 조건 | Recommendation |
|---|---|
| 낮은 drift, 충분한 근거 | `continue` |
| 경미한 누락/범위 확장 | `revise` |
| 외부 영향 또는 모호한 의도 | `ask_user` |
| 위험 도구/정책 위반 | `stop` |
| 부적절한 메모리 | `skip_memory` |

---

## 5. 데이터 모델 확장

### 5.1 Evaluation Plan

새 schema 후보: `backend/schema/agent-review-plan.schema.json`

```json
{
  "review_type": "tool_call",
  "evaluation_steps": [],
  "required_checks": ["goal", "tool", "safety"],
  "required_evidence": [],
  "rubric": {
    "goal": 0.3,
    "tool": 0.4,
    "safety": 0.3
  },
  "max_depth": "standard"
}
```

### 5.2 Judge Result

새 schema 후보: `backend/schema/agent-judge-result.schema.json`

```json
{
  "judge_name": "tool_judge",
  "score": 0.78,
  "confidence": 0.9,
  "finding": "High-risk external side effect requires confirmation.",
  "evidence": [],
  "recommendation": "ask_user"
}
```

### 5.3 Agent Review Result 확장

현재 결과에 다음 필드를 추가할 수 있다.

- `evaluation_plan`
- `judge_results`
- `evidence_items`
- `confidence`
- `verification_status`
- `evaluation_depth`

---

## 6. 구현 로드맵

### Phase 1. 문서·설계 정리

상태: 진행 중

- Agent-as-a-Judge reference 저장
- PRD/Architecture/Tasks에 방향성 통합
- 본 계획 문서 작성

### Phase 2. Deterministic Agent-as-a-Judge MVP

목표:

- 현재 `review-agent` 내부를 planner/checker/judge/aggregator 구조로 리팩터링
- 실제 LLM 호출 없이 재현 가능한 평가 유지
- judge별 결과를 JSON에 포함

작업:

1. `AgentReviewPlan` 모델 추가
2. `JudgeFinding` 또는 `AgentJudgeResult` 모델 추가
3. review type별 deterministic plan 생성
4. Goal/Tool/Memory/Safety judge 함수 분리
5. aggregator에서 confidence 계산
6. Markdown report에 judge breakdown 추가

성공 기준:

- 기존 13개 테스트 유지
- 기존 sample JSON 결과 호환
- 새 테스트에서 judge별 결과 확인

### Phase 3. Evidence 기반 검증 강화

목표:

- execution log와 tool result를 근거 단위로 정규화
- 평가 결과가 근거와 연결되도록 개선

작업:

1. `EvidenceItem` 모델 추가
2. execution log parser 개선
3. risky tool call evidence 추출
4. handoff consistency evidence 추출
5. Markdown에 Evidence 섹션 추가

성공 기준:

- `review-agent --input backend/examples/agent-review-execution-log.json` 결과에 evidence가 포함됨
- 고위험 tool call은 evidence와 함께 `ask_user` 또는 `stop`으로 분류됨

### Phase 4. Optional LLM Judge Adapter

상태: 기반 구현 완료

목표:

- deterministic 결과를 기본값으로 유지하면서 선택적으로 LLM Judge를 붙인다.

현재 구현:

- `review-agent --mode deterministic|hybrid` 옵션을 제공한다.
- `hybrid`는 아직 외부 LLM을 호출하지 않고 deterministic fallback으로 동작한다.
- 결과 metadata에 `judge_mode`, `judge_mode_status`, `llm_adapter`, `fallback_reason`을 기록해 운영자가 현재 평가 모드를 알 수 있게 한다.

원칙:

- LLM 판단은 보조 신호다.
- 고위험 상황에서 rule과 LLM이 충돌하면 보수적으로 판단한다.
- LLM 입력에는 system/evaluation policy와 user artifact를 명확히 분리한다.

작업:

1. `--mode deterministic|llm|hybrid` 옵션 검토
2. `backend/prompts/driftguard-agent-review.md`를 judge별 prompt로 분리
3. JSON repair/fallback 정책 추가
4. 모델 독립 adapter 정의

### Phase 5. Tool Verification / Sandbox

상태: 안전 경계 구현 완료

목표:

- 코드 평가나 로그 평가에서 실제 검증 도구를 안전하게 사용할 수 있게 한다.

현재 구현:

- `backend/src/driftguard/verifier.py`가 실행형/외부 영향 가능 verifier를 `blocked`로 분류한다.
- `python_executor`, `exec`, `shell`, `api_caller`, `browser_agent`, `sql_runner` 등은 sandbox 전까지 실행하지 않는다.
- 결과는 `verification_status`와 `metadata.sandbox_verification`에 기록된다.
- 상세 정책은 `agent/SANDBOX_VERIFICATION.md`에 문서화했다.

주의:

- Python executor는 sandbox 전까지 기본 비활성화
- 네트워크 차단, 파일 접근 제한, timeout, resource quota 필요

작업:

1. read-only file verifier
2. local JSON/log verifier
3. sandbox design 문서
4. Python executor PoC는 별도 explicit flag 필요

### Phase 6. Observability / Integration

상태: JSONL audit log 확장 완료

목표:

- Langfuse/Phoenix/OpenTelemetry와 연결 가능한 export 구조 제공

현재 구현:

- `review-agent --audit-log` 옵션을 제공한다.
- `backend/src/driftguard/audit.py`가 compact observability record를 생성한다.
- full result log(`--log`)와 compact audit log(`--audit-log`)를 분리했다.
- 상세 필드는 `agent/AUDIT_LOGGING.md`에 문서화했다.

작업:

1. JSONL audit log 확장 — 완료
2. OpenTelemetry span attribute 매핑 문서
3. Langfuse/Phoenix exporter PoC
4. promptfoo/DeepEval integration example

---

## 7. 보안 원칙

1. 판단보다 검증을 우선한다.
2. 평가 기준은 사용자 입력과 분리한다.
3. 고위험 도구 실행은 기본적으로 사용자 확인이 필요하다.
4. LLM judge의 판단은 절대적 진실이 아니다.
5. 외부 시스템에 영향을 주는 검증 도구는 opt-in이어야 한다.
6. sandbox 없는 code execution은 금지한다.
7. score와 confidence는 별도로 관리한다.
8. 모든 평가 결과는 감사 가능해야 한다.

---

## 8. 현재 DriftGuard와의 차이

| 항목 | 현재 DriftGuard | Agent-as-a-Judge 확장 |
|---|---|---|
| 평가 흐름 | 단일 rule/템플릿 중심 | planner + multi-judge + aggregator |
| 근거 | reason/guidance 중심 | evidence item과 judge result 연결 |
| 도구 검증 | 로그 분석 중심 | 안전한 verifier/sandbox로 확장 |
| 출력 | Markdown/JSON/JSONL | plan, judge breakdown, confidence 포함 |
| 운영 연동 | CLI 중심 | observability/exporter로 확장 |
| 평가 방식 | deterministic MVP | deterministic → hybrid LLM judge |

---

## 9. 다음 구현 후보

우선순위가 높은 작업:

1. `AgentReviewPlan` 모델과 deterministic planner 추가
2. judge별 finding 구조 추가
3. Markdown report에 judge breakdown 추가
4. execution log evidence extraction 개선
5. confidence 필드 추가

권장 첫 PR 범위:

- 외부 LLM 호출 없이 내부 구조만 Agent-as-a-Judge 형태로 리팩터링
- 기존 CLI 인터페이스는 유지
- 기존 테스트를 깨지 않으면서 새 테스트 2~3개 추가

---

## 10. 결론

DriftGuard는 단순 LLM Judge가 아니라 Agent Drift를 평가하는 **Judgment Layer**가 되어야 한다. 이를 위해 현재의 rule-based MVP를 유지하면서, 내부 구조를 Agent-as-a-Judge 패턴으로 점진적으로 분리한다.

가장 안전한 경로는 다음이다.

```text
Rule-based review-agent
  → Deterministic planner/judge/aggregator
  → Evidence-based review
  → Optional hybrid LLM Judge
  → Sandbox verifier
  → Observability integration
```
