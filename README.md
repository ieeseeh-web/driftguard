# DriftGuard

DriftGuard는 AI 에이전트가 장기 작업, 도구 호출, 메모리 업데이트, 다중 에이전트 협업 과정에서 원래 목표와 정책으로부터 벗어나는 **Agent Drift**를 탐지하고 완화하기 위한 평가/가드레일 시스템입니다.

핵심 아이디어는 **LLM as a Judge**를 단순한 사후 평가 도구가 아니라, 에이전트 런타임 중간중간에 삽입되는 **검증 레이어**로 사용하는 것입니다.

---

## 1. 문제 정의

AI 에이전트는 단순 응답 생성 모델과 달리 다음과 같은 행동을 수행합니다.

- 작업 계획 수립
- 여러 단계의 실행
- 외부 도구 호출
- 파일, API, 메시지, 배포 등 외부 상태 변경
- 장기 메모리 저장 및 재사용
- 다른 에이전트와 협업

이 과정에서 에이전트가 사용자의 원래 의도, 시스템 역할, 정책, 제약사항에서 점진적으로 벗어나는 문제가 발생할 수 있습니다. 이를 **Agent Drift**라고 부릅니다.

---

## 2. 제품 목표

DriftGuard의 목표는 다음과 같습니다.

1. 에이전트의 목표 일치성 평가
2. 역할 및 지시사항 준수 여부 평가
3. 도구 호출의 필요성과 위험도 평가
4. 메모리 업데이트의 적절성 평가
5. 다중 에이전트 간 목표 왜곡 감시
6. Drift Score 기반 운영 모니터링
7. 위험도 기반 Human-in-the-loop 연결

---

## 3. 핵심 기능

- **Goal Alignment Judge**
  - 에이전트의 계획/응답이 원래 사용자 요청과 일치하는지 평가합니다.

- **Role Consistency Judge**
  - 에이전트가 부여된 역할을 유지하는지 평가합니다.

- **Tool Guard**
  - 파일 수정, 메시지 전송, 배포, 결제 등 위험 도구 호출 전 적절성을 평가합니다.

- **Memory Guard**
  - 장기 메모리 저장 전 정보의 가치, 민감도, 충돌 여부를 평가합니다.

- **Drift Score**
  - Agent Drift 가능성을 정량화하여 운영 지표로 관리합니다.

- **Policy Engine**
  - Judge 결과에 따라 계속 진행, 재계획, 사용자 확인, 작업 중단을 결정합니다.

---

## 4. 문서 구조

| 문서 | 설명 |
|---|---|
| `agent-drift-llm-judge-prd.md` | Agent Drift 대응을 위한 PRD |
| `feature-spec.md` | 기능 상세 명세 |
| `architecture.md` | 시스템 아키텍처 및 Mermaid 다이어그램 |
| `mvp-tasks.md` | MVP 개발 태스크 목록 |

---

## 5. MVP 범위

MVP에서는 다음 기능을 우선 구현합니다.

- 최종 응답 전 Goal Alignment 평가
- 도구 호출 전 Tool Risk 평가
- 메모리 업데이트 전 Memory Risk 평가
- Drift Score 산출
- 위험도별 대응 정책
- Judge 평가 로그 저장

---

## 6. 권장 사용 흐름

```text
User Request
  ↓
Agent Planning
  ↓
Judge Evaluation
  ↓
Agent Execution
  ↓
Tool Guard / Memory Guard
  ↓
Final Judge Evaluation
  ↓
Policy Decision
  ↓
Continue / Revise / Ask User / Stop
```

---

## 7. 설계 원칙

- Judge는 사후 평가기가 아니라 런타임 가드레일이어야 합니다.
- 모든 고위험 작업은 도구 실행 전에 평가되어야 합니다.
- 메모리 업데이트는 별도 검증 단계를 거쳐야 합니다.
- Drift Score는 운영 지표로 누적되어야 합니다.
- 높은 위험도에서는 Human-in-the-loop를 기본값으로 사용해야 합니다.

---

## 8. 다음 단계

1. MVP 인터페이스 정의
2. Judge 루브릭 구체화
3. 샘플 평가 데이터셋 작성
4. 간단한 CLI 또는 API 프로토타입 구현
5. 에이전트 런타임 연동
---

## 9. MVP CLI 사용법

현재 MVP는 표준 라이브러리만 사용하는 Python CLI로 구현되어 있습니다.

```bash
# Goal 평가
PYTHONPATH=src python3 -m driftguard.cli evaluate --type goal --input examples/goal-ok.json

# Tool Risk 평가 + 로그 저장
PYTHONPATH=src python3 -m driftguard.cli evaluate --type tool --input examples/tool-risky.json --log logs/evaluations.jsonl

# Memory Risk 평가
PYTHONPATH=src python3 -m driftguard.cli evaluate --type memory --input examples/memory-risky.json

# Agent 방식 리뷰: Markdown + JSON 리포트
PYTHONPATH=src python3 -m driftguard.cli review-agent --input examples/agent-review-final-response.json

# Agent 방식 리뷰: JSON만 출력
PYTHONPATH=src python3 -m driftguard.cli review-agent --input examples/agent-review-tool-call.json --format json

# Agent 방식 리뷰 + JSONL 로그 저장
PYTHONPATH=src python3 -m driftguard.cli review-agent --input examples/agent-review-execution-log.json --log logs/agent-reviews.jsonl

# Handoff / execution log 리뷰
PYTHONPATH=src python3 -m driftguard.cli review-agent --input examples/agent-review-handoff.json --format json
PYTHONPATH=src python3 -m driftguard.cli review-agent --input examples/agent-review-execution-log.json --format json

# 테스트 실행
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

대체 실행 파일:

```bash
./bin/driftguard evaluate --type goal --input examples/goal-ok.json
```

---

## 10. 구현 구조

| 경로 | 설명 |
|---|---|
| `src/driftguard/models.py` | 평가 요청/결과 데이터 모델 |
| `src/driftguard/evaluator.py` | Goal/Tool/Memory/Final 평가 로직 |
| `src/driftguard/agent_review.py` | Agent 방식 Drift 리뷰와 Markdown/JSON 리포트 생성 |
| `src/driftguard/policy.py` | Drift Score 및 대응 정책 |
| `src/driftguard/logger.py` | JSONL 평가 로그 저장 |
| `src/driftguard/cli.py` | CLI 엔트리포인트 |
| `schema/` | 요청/응답 JSON Schema |
| `prompts/` | 향후 LLM Judge 연동용 프롬프트 초안 |
| `examples/` | 샘플 평가 입력 |
| `tests/` | unittest 기반 테스트 |

