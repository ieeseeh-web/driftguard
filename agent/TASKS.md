# Tasks: DriftGuard Agent 개발 계획

## Priority Rules
1. 기존 구현을 깨지 않는 문서/스키마 작업
2. 평가 에이전트 입력·출력 프로토콜 정의
3. 프롬프트/샘플/테스트 작성
4. CLI 연동
5. 실제 LLM 또는 OpenClaw sub-agent 연동

## Current Tasks
| ID | Status | Priority | Task | Acceptance Criteria |
|---|---|---:|---|---|
| A-001 | done | 1 | 기존 PRD/문서/구현 분석 | `agent/CONTEXT.md`에 분석 결과 기록 |
| A-002 | done | 1 | AI 에이전트 방식 PRD 작성 | `agent/PRD.md` 작성 |
| A-003 | done | 1 | DriftGuard Agent 운영 지침 작성 | `agent/AGENT.md` 작성 |
| A-004 | done | 1 | Agent Review 입력 스키마 정의 | `schema/agent-review-request.schema.json` 생성 |
| A-005 | done | 1 | Agent Review 출력 스키마 정의 | `schema/agent-review-result.schema.json` 생성 |
| A-006 | done | 2 | DriftGuard Agent 프롬프트 작성 | `prompts/driftguard-agent-review.md` 생성 |
| A-007 | done | 2 | Markdown 리포트 템플릿 작성 | `agent/templates/drift-report-template.md` 생성 |
| A-008 | done | 2 | 샘플 평가 입력 작성 | `examples/agent-review-*.json` 3개 생성 |
| A-009 | done | 3 | CLI 명령 설계/구현 | `driftguard review-agent --input ...` 구현 |
| A-010 | done | 3 | 기존 evaluator 결과를 보조 신호로 통합 | rule score + agent guidance 결합 |
| A-011 | done | 4 | 테스트 케이스 추가 | agent review 테스트 3개 추가 |
| A-012 | done | 3 | Agent Review JSONL 로그 저장 옵션 추가 | `review-agent --log` 구현 및 로그 파싱 확인 |
| A-013 | done | 3 | Handoff / execution_log 샘플 추가 | 샘플 2개와 평가 로직/테스트 추가 |

## Backlog
- PR/코드리뷰용 Drift 평가 모드
- OpenClaw sub-agent 실행 예시
- JSON Schema 검증 테스트 추가
- Drift 유형별 개선 가이드 라이브러리
- Judge 결과와 rule evaluator 결과 불일치 처리 정책

## Blocked / Open Questions
- 실제 LLM 호출을 포함할지, 우선 프롬프트/리포트 생성까지만 할지 결정 필요
- CLI 명령 이름 확정 필요: `review-agent`, `judge-agent`, `audit-agent` 후보
- 평가 로그에 원문 저장 vs 해시/요약 저장 정책 결정 필요
