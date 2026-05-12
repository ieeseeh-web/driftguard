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
| A-014 | done | 2 | Agent Architecture 문서 작성 | `agent/ARCHITECTURE.md` 작성 |
| A-015 | done | 2 | 발표용 PPT 내용 정리 | `agent/PRESENTATION.md` 작성 |
| A-016 | done | 2 | Drift 테스트용 LangGraph 여행 비서 샘플 작성 | `sample_agent/` 생성 및 tool drift 실행 검증 |

## Backlog
- PR/코드리뷰용 Drift 평가 모드
- OpenClaw sub-agent 실행 예시
- JSON Schema 검증 테스트 추가
- Drift 유형별 개선 가이드 라이브러리
- Judge 결과와 rule evaluator 결과 불일치 처리 정책

## Agent-as-a-Judge Expansion Tasks
| ID | Status | Priority | Task | Acceptance Criteria |
|---|---|---:|---|---|
| AAJ-001 | done | 1 | Agent-as-a-Judge 참고 자료 저장 | `agent/references/`에 논문 요약, PRD, 개발 가이드 저장 |
| AAJ-002 | done | 1 | Agent-as-a-Judge 구현 계획 문서 작성 | `agent/AGENT_AS_JUDGE_PLAN.md` 작성 |
| AAJ-003 | done | 1 | PRD/Architecture에 Agent-as-a-Judge 방향 통합 | `agent/PRD.md`, `agent/ARCHITECTURE.md` 업데이트 |
| AAJ-004 | done | 2 | AgentReviewPlan 모델 추가 | review type별 deterministic plan 생성 테스트 |
| AAJ-005 | done | 2 | JudgeFinding / judge_results 구조 추가 | JSON 결과에 judge별 score, confidence, evidence 포함 |
| AAJ-006 | done | 2 | Goal/Instruction/Tool/Memory/Safety judge 모듈 분리 | 기존 결과와 호환되며 judge별 unit test 통과 |
| AAJ-007 | done | 3 | EvidenceItem 추출 로직 추가 | execution log/tool call/handoff에서 evidence 추출 |
| AAJ-008 | done | 3 | Markdown report에 judge breakdown 추가 | 사람 검토용 보고서에 judge별 판단과 근거 표시 |
| AAJ-009 | todo | 4 | Optional LLM/hybrid judge adapter 설계 | deterministic 기본값 유지, LLM 판단은 보조 신호로 사용 |
| AAJ-010 | todo | 4 | Sandbox verifier 설계 | code execution 전 보안 요구사항과 opt-in 정책 문서화 |

## Blocked / Open Questions
- 실제 LLM 호출을 포함할지, 우선 프롬프트/리포트 생성까지만 할지 결정 필요
- CLI 명령 이름 확정 필요: `review-agent`, `judge-agent`, `audit-agent` 후보
- 평가 로그에 원문 저장 vs 해시/요약 저장 정책 결정 필요
