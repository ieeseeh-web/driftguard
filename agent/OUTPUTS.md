# Outputs: DriftGuard Agent 작업 기록

## Execution Log
| Date | Task | Result | Verification |
|---|---|---|---|
| 2026-05-12 | 기존 PRD 기반 Agent 방식 문서 작성 | `agent/AGENT.md`, `agent/PRD.md`, `agent/CONTEXT.md`, `agent/TASKS.md`, `agent/RUNBOOK.md`, `agent/OUTPUTS.md` 작성 | 파일 생성 및 라인 수 확인 |
| 2026-05-12 | Agent Review 스키마/프롬프트/샘플 작성 | request/result JSON Schema, DriftGuard Agent 프롬프트, 샘플 3종 생성 | JSON 파싱 확인 및 기존 unittest 8개 통과 |
| 2026-05-12 | `review-agent` CLI 구현 | `src/driftguard/agent_review.py`, CLI subcommand, 테스트 3개, README 사용법 추가 | 샘플 CLI 실행 확인 및 unittest 11개 통과 |
| 2026-05-12 | JSONL 로그와 handoff/execution_log 평가 강화 | `review-agent --log`, 샘플 2종, 위험 로그/handoff 감지 로직, 테스트 2개 추가 | JSON 파싱, 로그 1줄 저장/파싱, unittest 13개 통과 |
| 2026-05-12 | Agent 아키텍처와 발표용 문서 작성 | `agent/ARCHITECTURE.md`, `agent/PRESENTATION.md` 작성 | 문서 라인 수 확인 및 unittest 13개 통과 |

## Decisions
- 기존 “LLM as a Judge 평가 시스템” 방향은 유지하되, 이번 개발 단위는 독립적인 **DriftGuard Agent**로 정의한다.
- DriftGuard Agent는 단순 점수 산출보다 **진단, 설명, 수정 가이드**를 핵심 가치로 한다.
- 기존 rule-based evaluator는 빠른 보조 신호로 활용하고, AI Agent는 맥락 판단과 가이드 생성을 담당한다.
- MVP는 런타임 강제 통합보다 로컬 문서/JSON/로그 기반 평가를 우선한다.

## Generated Artifacts
- `agent/AGENT.md`
- `agent/PRD.md`
- `agent/CONTEXT.md`
- `agent/TASKS.md`
- `agent/RUNBOOK.md`
- `agent/OUTPUTS.md`
- `agent/ARCHITECTURE.md`
- `agent/PRESENTATION.md`
- `agent/memory/`
- `agent/templates/`
- `schema/agent-review-request.schema.json`
- `schema/agent-review-result.schema.json`
- `prompts/driftguard-agent-review.md`
- `examples/agent-review-final-response.json`
- `examples/agent-review-tool-call.json`
- `examples/agent-review-memory-update.json`
- `examples/agent-review-handoff.json`
- `examples/agent-review-execution-log.json`
- `src/driftguard/agent_review.py`
- `tests/test_agent_review.py`

## Open Issues
- 실제 LLM 호출을 MVP에 포함할지 결정 필요
- CLI 명령 이름 확정 필요
- 평가 로그의 원문 저장 vs 해시/요약 저장 정책 결정 필요
- 실제 LLM 기반 Judge 연동 여부 결정 필요
- Agent Review 결과 JSON Schema 검증 테스트 추가 가능
