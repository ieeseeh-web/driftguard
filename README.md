# DriftGuard

DriftGuard는 AI 에이전트의 목표 이탈, 위험 도구 호출, 메모리 저장 위험, 다중 에이전트 handoff 왜곡을 평가하는 Agent Drift 가드레일 시스템입니다.

현재 구현된 실행 시스템은 Python 백엔드 API이며, `frontend/` 폴더에 백엔드와 연동되는 콘솔 UI와 에이전트 등록 화면이 포함되어 있습니다.

## 구조

| 경로 | 설명 |
|---|---|
| `backend/` | Python 백엔드 API, CLI, 테스트, 스키마, 샘플 입력, 에이전트 레지스트리 |
| `frontend/` | DriftGuard API 콘솔 UI 및 Agent Registry 화면 |
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

프론트엔드에서 제공하는 주요 화면은 다음과 같습니다.

| 화면 | 설명 |
|---|---|
| `Console` | Agent Review/Evaluation 샘플 JSON 실행, 등록된 에이전트 실행, 결과 요약/JSON 표시 |
| `Agent Registry` | 연결 가능한 Python 모듈 에이전트 등록, 샘플/템플릿/연동 요구사항 확인 |
| `Swagger` | 백엔드 OpenAPI 문서 |

프론트엔드 사이드바의 `Registered Agent` 영역에서 `backend/agents/registry.json`에 등록된 에이전트를 선택해 실행할 수 있습니다. 실행 결과는 백엔드의 `POST /v1/agent-runs`를 통해 DriftGuard 리뷰 결과로 바로 표시됩니다.

## 에이전트 등록과 실행

에이전트는 `Agent Registry` 화면 또는 백엔드 `POST /v1/agents` API로 등록합니다. 등록 정보는 기본적으로 `backend/agents/registry.json`에 저장됩니다.

등록 가능한 에이전트는 현재 `python_module` 런타임을 사용하며, 다음 CLI 계약을 지원해야 합니다.

```bash
python -m <module> \
  --input <scenario-json> \
  --drift-mode <mode> \
  --output <agent-result-json> \
  --review-output <driftguard-review-request-json>
```

지원 API 요약:

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/v1/agents` | 등록된 에이전트 목록 |
| `POST` | `/v1/agents` | 에이전트 등록 또는 갱신 |
| `POST` | `/v1/agent-runs` | 등록된 에이전트 실행 및 DriftGuard 리뷰 |
| `POST` | `/v1/agent-reviews` | Agent Review 요청 평가 |
| `POST` | `/v1/evaluations` | Goal/Tool/Memory/Final 평가 |
