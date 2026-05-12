# DriftGuard

DriftGuard는 AI 에이전트의 목표 이탈, 위험 도구 호출, 메모리 저장 위험, 다중 에이전트 handoff 왜곡을 평가하는 Agent Drift 가드레일 시스템입니다.

현재 구현된 실행 시스템은 백엔드 API이며, `frontend/` 폴더에 백엔드와 연동되는 콘솔 UI가 포함되어 있습니다.

## 구조

| 경로 | 설명 |
|---|---|
| `backend/` | Python 백엔드 API, CLI, 테스트, 스키마, 샘플 입력 |
| `frontend/` | DriftGuard API 콘솔 UI |
| `agent/` | Agent-as-a-Judge 관련 설계/운영 문서 |
| `DESIGN.md` | 프론트엔드 디자인 시스템 참고 자료 |
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

## 프론트엔드 실행

백엔드 서버를 먼저 실행한 뒤 별도 터미널에서 정적 서버를 실행합니다.

```bash
cd frontend
python3 -m http.server 5173
```

```bash
open http://127.0.0.1:5173
```

프론트엔드 사이드바의 `Sample Agent` 영역에서 번들된 LangGraph 샘플 에이전트를 실행할 수 있습니다. 실행 결과는 백엔드의 `POST /v1/sample-agent/runs`를 통해 DriftGuard 리뷰 결과로 바로 표시됩니다.
