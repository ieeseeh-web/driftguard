# DriftGuard

DriftGuard는 AI 에이전트의 목표 이탈, 위험 도구 호출, 메모리 저장 위험, 다중 에이전트 handoff 왜곡을 평가하는 Agent Drift 가드레일 시스템입니다.

현재 구현된 실행 시스템은 백엔드 API이며, 프론트엔드는 추후 `frontend/` 폴더로 추가할 예정입니다.

## 구조

| 경로 | 설명 |
|---|---|
| `backend/` | Python 백엔드 API, CLI, 테스트, 스키마, 샘플 입력 |
| `agent/` | Agent-as-a-Judge 관련 설계/운영 문서 |
| `DESIGN.md` | 향후 프론트엔드 디자인 참고 자료 |
| `agent-drift-llm-judge-prd.md` | 제품 요구사항 문서 |
| `feature-spec.md` | 기능 명세 |
| `mvp-tasks.md` | MVP 태스크 |

## 백엔드 실행

```bash
cd backend
./bin/driftguard serve
```

기본 포트는 일반 충돌이 적은 `17321`입니다.

```bash
curl http://127.0.0.1:17321/health
open http://127.0.0.1:17321/docs
```

## 백엔드 테스트

```bash
cd backend
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
