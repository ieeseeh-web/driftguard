# Context: DriftGuard Agent 개발 배경

## 1. 기존 문서 분석 요약
기존 `agent-drift-llm-judge-prd.md`는 Agent Drift를 탐지하기 위한 **LLM as a Judge 기반 평가 시스템**을 정의한다.

핵심 내용:
- Agent Drift는 목표, 역할, 지시, 맥락, 도구 사용, 메모리, 다중 에이전트 전달 과정에서 발생한다.
- Judge는 최종 응답뿐 아니라 계획, 도구 호출, 메모리 변경, 중간 산출물을 평가해야 한다.
- Drift Score에 따라 `continue`, `revise`, `ask_user`, `stop`을 결정한다.
- 위험 도구, 민감정보, 장기 메모리, 다중 에이전트 handoff는 특별 관리 대상이다.

## 2. 방향 전환: 시스템에서 AI 에이전트로
기존 문서는 런타임 내부의 시스템 레이어 관점이 강하다. 이번 개발 방향은 다음처럼 바뀐다.

| 기존 시스템 방식 | 새 AI 에이전트 방식 |
|---|---|
| 런타임 내부 guardrail | 독립 평가 에이전트 |
| 점수/정책 결정 중심 | 진단/설명/가이드 중심 |
| API/SDK 통합 우선 | 문서/로그/JSON 입력 기반 수동 실행 우선 |
| 시스템이 자동 차단 | 에이전트가 위험도와 다음 행동을 권고 |
| 운영 모니터링 중심 | 개발자/상위 에이전트의 리뷰 파트너 |

## 3. 현재 저장소 상태
현재 `~/workspaces/driftguard/`에는 이미 MVP 뼈대가 있다.

주요 파일:
- `README.md`: DriftGuard 개요와 CLI 사용법
- `agent-drift-llm-judge-prd.md`: 기존 PRD
- `architecture.md`: 시스템 아키텍처
- `feature-spec.md`: 기능 상세 명세
- `mvp-tasks.md`: MVP 개발 태스크
- `src/driftguard/evaluator.py`: rule-based evaluator
- `src/driftguard/policy.py`: 정책 결정 로직
- `src/driftguard/cli.py`: CLI 엔트리포인트
- `tests/`: unittest 기반 테스트

## 4. 현재 구현 특징
현재 구현은 LLM 호출 없이 rule-based 방식으로 평가한다.

장점:
- 빠름
- 로컬 실행 가능
- 테스트 가능
- 외부 API 의존 없음

한계:
- 맥락적 판단이 약함
- “왜/어떻게 고칠지” 설명이 제한적임
- 다중 에이전트 handoff 분석이 약함
- 실제 Agent Drift의 미묘한 목표 변형 탐지가 어려움

## 5. 개발해야 할 핵심 차별점
DriftGuard Agent는 기존 evaluator를 대체하기보다 상위 레이어로 활용한다.

- Rule evaluator: 빠른 위험 신호 계산
- AI DriftGuard Agent: 맥락 판단, Drift 유형 설명, 수정 가이드 생성
- Policy: 위험도별 다음 행동 결정
- Log/Report: 감사 가능한 기록

## 6. 핵심 설계 질문
- DriftGuard Agent 입력은 어떤 형식을 기본으로 할 것인가?
- Markdown 리포트와 JSON 출력 중 무엇을 우선할 것인가?
- 기존 CLI에 `agent-review` 같은 명령을 추가할 것인가?
- 실제 LLM Judge 연동 전, 프롬프트와 샘플만으로 MVP를 정의할 것인가?
- 평가 에이전트가 사용자 확인 메시지를 직접 작성해야 하는가?

## 7. 권장 MVP 전략
1. 기존 문서와 구현은 유지한다.
2. `agent/` 문서로 AI 에이전트 방식의 제품 방향을 분리한다.
3. 평가 입력/출력 스키마를 확장한다.
4. 프롬프트 기반 DriftGuard Agent 프로토콜을 작성한다.
5. 기존 CLI에 agent-style 리포트 출력을 추가한다.
6. 샘플 로그를 넣으면 Markdown+JSON 평가 결과가 나오게 한다.
