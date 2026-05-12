# PRD: Agent Drift 탐지·평가·가이드 제공 AI 에이전트

## 1. 문서 목적
이 문서는 기존 `agent-drift-llm-judge-prd.md`의 내용을 바탕으로, Agent Drift를 탐지하는 기능을 “시스템 레이어”가 아니라 **AI 에이전트 방식**으로 구현하기 위한 제품 요구사항을 정의한다.

기존 PRD는 LLM as a Judge를 Agent Runtime 안의 검증 레이어로 설계했다. 본 PRD는 이를 확장하여, 독립 실행 가능한 **DriftGuard Agent**가 에이전트의 행동 기록을 검토하고 Drift를 평가한 뒤, 수정 가이드와 다음 행동 권고를 제공하는 형태를 목표로 한다.

## 2. 배경
AI 에이전트는 장기 작업, 도구 호출, 메모리 저장, 다중 에이전트 협업 과정에서 원래 사용자 목표·역할·정책·맥락으로부터 점진적으로 벗어날 수 있다. 기존 DriftGuard MVP는 rule-based 평가와 CLI 중심의 평가 시스템으로 시작되어 있다.

하지만 실제 운영 환경에서는 다음과 같은 요구가 있다.

- 전체 런타임에 바로 통합하지 않고도 에이전트 로그를 사후/중간 평가하고 싶다.
- 단순 점수보다 “무엇이 drift인지, 왜 위험한지, 어떻게 고칠지”가 필요하다.
- 개발자 또는 상위 에이전트가 호출할 수 있는 평가 전문가 에이전트가 필요하다.
- 다중 에이전트 작업에서 Planner/Worker/Reviewer 간 목표 변형을 사람이 이해할 수 있게 설명해야 한다.

## 3. 제품 개요
DriftGuard Agent는 에이전트 실행 흔적을 입력받아 Agent Drift를 진단하는 AI 평가 에이전트다.

주요 역할:
1. 원본 요청과 현재 행동의 목표 일치성 평가
2. 역할·정책·명시 지시 준수 여부 평가
3. 위험한 도구 호출의 필요성·승인 필요성 판단
4. 메모리 저장 후보의 장기 저장 적합성 판단
5. Drift Score와 위험도 산출
6. 에이전트에게 재계획/수정/사용자 확인/중단 가이드 제공
7. 평가 결과를 감사 가능한 형태로 기록

## 4. 목표
- Agent Drift 현상을 독립적인 AI 에이전트가 평가할 수 있게 한다.
- 평가 결과를 점수, 근거, 수정 가이드로 구조화한다.
- 기존 DriftGuard CLI/평가 로직과 연동 가능한 입력·출력 형식을 정의한다.
- MVP에서는 로컬 문서/JSON/로그 기반 평가부터 지원한다.
- 향후 OpenClaw 하위 에이전트, CI, AgentOps 워크플로우와 연동 가능하게 설계한다.

## 5. 비목표
- 모든 Agent Drift를 100% 자동 탐지한다고 보장하지 않는다.
- 처음부터 실시간 대시보드나 중앙 서버를 만들지 않는다.
- 처음부터 모든 에이전트 런타임에 강제 삽입하지 않는다.
- 사용자의 승인 없이 외부 배포, 메시지 발송, 공개 발행을 수행하지 않는다.
- Judge 모델 하나의 판단을 절대적 진실로 취급하지 않는다.

## 6. 주요 사용자
### 6.1 AI 에이전트 개발자
에이전트 응답, 계획, 도구 호출이 원래 의도와 일치하는지 평가하고 개선점을 얻는다.

### 6.2 AgentOps/LLMOps 운영자
운영 로그에서 Drift 발생 패턴, 고위험 작업, 반복 위반을 추적한다.

### 6.3 상위 오케스트레이터 에이전트
Worker 에이전트의 중간 산출물이나 도구 호출 후보를 DriftGuard Agent에게 검토시킨다.

### 6.4 보안/거버넌스 담당자
승인 누락, 민감정보 저장, 위험 도구 사용 등 정책 위반 가능성을 검토한다.

## 7. 대표 사용 시나리오
### S1. 최종 응답 리뷰
사용자 요청과 에이전트 최종 응답 초안을 입력하면 DriftGuard Agent가 목표 일치성, 누락 지시, 범위 확장을 평가하고 수정안을 제안한다.

### S2. 도구 호출 전 리뷰
에이전트가 파일 삭제, 메시지 전송, 배포 등 부작용 있는 도구를 호출하려 할 때, DriftGuard Agent가 필요성·위험도·승인 필요 여부를 판단한다.

### S3. 메모리 저장 전 리뷰
에이전트가 장기 메모리 후보를 제안하면, DriftGuard Agent가 저장 가치, 민감도, 일시성, 과도한 일반화 여부를 평가한다.

### S4. 다중 에이전트 전달 검토
Planner가 Worker에게 전달한 목표가 원본 요청에서 왜곡되었는지 평가하고, Worker에게 보완해야 할 제약사항을 알려준다.

### S5. 작업 로그 사후 감사
완료된 에이전트 작업 로그를 입력하면 DriftGuard Agent가 Drift 발생 구간, 원인, 재발 방지 가이드를 요약한다.

## 8. 기능 요구사항
### FR-1. 평가 입력 수집
시스템은 다음 필드를 포함하는 평가 입력을 받을 수 있어야 한다.

- `user_request`
- `agent_role`
- `constraints`
- `agent_plan`
- `agent_output`
- `candidate_action`
- `candidate_memory`
- `tool_calls`
- `execution_log`
- `handoff_messages`

### FR-2. Drift 유형 분류
DriftGuard Agent는 Drift를 아래 유형으로 분류해야 한다.

- Goal Drift
- Role Drift
- Instruction Drift
- Context Drift
- Tool Use Drift
- Memory Drift
- Multi-Agent Drift
- Safety/Policy Drift

### FR-3. Drift Score 산출
각 평가 결과는 `0.0 ~ 1.0` 범위의 Drift Score를 포함해야 한다.

권장 기준:
- `0.0 ~ 0.2`: 낮음, 계속 진행 가능
- `0.2 ~ 0.5`: 중간, 자체 수정 또는 재계획 권고
- `0.5 ~ 0.8`: 높음, 사용자 확인 권고
- `0.8 ~ 1.0`: 매우 높음, 중단 권고

### FR-4. 수정 가이드 생성
단순히 위험하다고 말하는 것이 아니라, 에이전트가 원래 목표로 돌아가기 위한 구체적 가이드를 제공해야 한다.

예:
- 누락된 사용자 제약 재반영
- 범위 축소
- 도구 호출 전 승인 요청
- 메모리 저장 생략
- Planner 지시문 재작성

### FR-5. 구조화 출력
평가 결과는 Markdown 설명과 JSON 구조를 모두 지원해야 한다.

최소 JSON 필드:
```json
{
  "drift_types": ["goal"],
  "overall_drift_score": 0.35,
  "risk_level": "medium",
  "recommendation": "revise",
  "reason": "원본 요청보다 범위가 확장되었습니다.",
  "guidance": ["사용자가 요청한 파일만 수정하도록 계획을 축소하세요."],
  "requires_human_confirmation": false
}
```

### FR-6. 기존 DriftGuard 평가 로직 연동
기존 `backend/src/driftguard/evaluator.py`, `policy.py`, CLI 결과를 DriftGuard Agent의 보조 신호로 사용할 수 있어야 한다.

- Rule-based 점수는 빠른 1차 필터로 사용
- AI Agent 평가는 설명, 맥락 판단, 가이드 생성에 사용
- 둘의 결과가 충돌하면 고위험 작업에서는 보수적으로 판단

### FR-7. 평가 로그 저장
평가 결과는 JSONL 또는 Markdown 리포트 형태로 저장할 수 있어야 한다.

저장 정보:
- 평가 시각
- 평가 대상 요약 또는 해시
- Drift 유형
- 점수/위험도
- 권고 대응
- 가이드
- 실제 후속 조치

### FR-8. Human-in-the-loop 권고
아래 조건에서는 사용자 확인을 권고해야 한다.

- 외부 상태 변경
- 대량 파일 수정/삭제
- 배포/게시/메시지 발송/결제
- 민감정보 처리
- Drift Score `0.5` 이상
- 원본 사용자 의도가 모호한 상태에서 되돌리기 어려운 작업

## 9. 비기능 요구사항
### NFR-1. 설명 가능성
점수만 반환하지 않고, 판단 근거와 수정 가이드를 제공해야 한다.

### NFR-2. 감사 가능성
나중에 왜 특정 권고를 했는지 추적 가능해야 한다.

### NFR-3. 모델 독립성
특정 LLM 벤더에 종속되지 않아야 한다.

### NFR-4. 보수적 안전성
민감하거나 되돌리기 어려운 작업은 기본적으로 `ask_user` 또는 `stop`을 권고한다.

### NFR-5. 점진적 통합
처음에는 수동/CLI/문서 기반으로 실행 가능해야 하며, 이후 런타임 hook, sub-agent, CI로 확장한다.

## 10. MVP 범위
### 포함
- DriftGuard Agent 운영 지침 문서
- 평가 입력/출력 JSON 스키마 초안
- Markdown 평가 리포트 형식
- Goal/Instruction/Tool/Memory 평가 프롬프트
- 기존 rule-based evaluator와 병행 사용 전략
- 샘플 입력 3~5개와 기대 결과
- 로컬 CLI 또는 스크립트를 통한 평가 실행

### 제외
- 실시간 대시보드
- 다중 Judge 앙상블
- SaaS 서버
- 모든 에이전트 런타임 자동 통합
- 조직별 정책 UI

## 11. 성공 기준
- 사용자가 에이전트 실행 로그를 입력하면 Drift 유형, 점수, 위험도, 수정 가이드를 받을 수 있다.
- 고위험 도구 호출은 사용자 확인 또는 중단으로 분류된다.
- 부적절한 장기 메모리 저장 후보는 `skip_memory` 또는 `ask_user`로 분류된다.
- 평가 결과가 Markdown/JSON으로 저장되어 재검토 가능하다.
- 기존 테스트와 샘플 평가가 깨지지 않는다.

## 12. 향후 확장
- OpenClaw sub-agent로 DriftGuard Agent 실행
- GitHub PR/Issue에서 에이전트 변경사항 리뷰
- Agent 작업 로그 자동 요약 및 Drift 감사
- 다중 에이전트 handoff 메시지 자동 검증
- CI에서 에이전트 회귀 테스트 실행
- Drift 발생 패턴별 프롬프트 개선 제안

## 13. Agent-as-a-Judge 확장 방향

최근 추가한 Agent-as-a-Judge 참고 자료를 기준으로 DriftGuard의 장기 방향은 단순 LLM Judge가 아니라 **계획·검증·근거·정책 판단을 수행하는 평가 에이전트**다.

핵심 확장 원칙:

- 최종 응답만 평가하지 않고 계획, 도구 호출, 실행 로그, 메모리 후보, handoff 메시지를 함께 본다.
- 단일 점수 대신 judge별 finding, evidence, confidence, recommendation을 분리한다.
- 가능한 경우 LLM 판단보다 실행 로그와 도구 결과 같은 검증 가능한 근거를 우선한다.
- 고위험 도구 호출, 외부 상태 변경, 민감정보 처리는 보수적으로 `ask_user` 또는 `stop`을 권고한다.
- MVP는 deterministic planner/judge/aggregator로 시작하고, LLM Judge는 선택적 hybrid mode로 도입한다.

목표 구조:

```text
Agent Review Request
  ↓
Evaluation Orchestrator
  ↓
Planner
  ↓
Evidence / Tool Result Router
  ↓
Goal · Instruction · Tool · Memory · Safety Judges
  ↓
Aggregator / Policy Engine
  ↓
Evidence-based Agent Review Result
```

상세 계획은 `agent/AGENT_AS_JUDGE_PLAN.md`를 기준 문서로 사용한다.

