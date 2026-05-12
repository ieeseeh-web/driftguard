# DriftGuard Architecture

이 문서는 루트에서 빠르게 찾기 위한 아키텍처 요약입니다. 상세 아키텍처와 Mermaid 다이어그램은 `backend/architecture.md`를 기준 문서로 관리합니다.

## 현재 구현 구조

```text
DriftGuard
  backend/
    src/driftguard/        Python API, CLI, 평가/리뷰 로직
    agents/registry.json   실행 가능한 에이전트 등록 정보
    sample_agent/          LangGraph 기반 샘플 에이전트
    schema/                요청/응답 JSON Schema
    tests/                 unittest 테스트
  frontend/
    index.html             Console + Agent Registry UI
    app.js                 API 연동과 결과 렌더링
    styles.css             DESIGN.md 기반 화면 스타일
```

## 실행 흐름

```text
Frontend Console
  -> DriftGuard Backend API
  -> Evaluation / Agent Review Engine
  -> Policy Engine
  -> Result JSON
```

등록 에이전트 실행 흐름:

```text
Agent Registry
  -> POST /v1/agents
  -> backend/agents/registry.json

Registered Agent Runner
  -> GET /v1/agents
  -> POST /v1/agent-runs
  -> python -m <registered module>
  -> --review-output JSON
  -> POST-equivalent Agent Review Engine
  -> UI Result
```

## 주요 API

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI 3.0 스펙 |
| `GET` | `/v1/agents` | 등록 에이전트 목록 |
| `POST` | `/v1/agents` | 에이전트 등록 또는 갱신 |
| `POST` | `/v1/agent-runs` | 등록 에이전트 실행 및 DriftGuard 리뷰 |
| `POST` | `/v1/agent-reviews` | Agent Review 평가 |
| `POST` | `/v1/evaluations` | Goal/Tool/Memory/Final 평가 |

## 에이전트 연동 계약

현재 등록 가능한 에이전트 런타임은 `python_module`입니다. 등록된 에이전트는 다음 CLI 계약을 지원해야 합니다.

```bash
python -m <module> \
  --input <scenario-json> \
  --drift-mode <mode> \
  --output <agent-result-json> \
  --review-output <driftguard-review-request-json>
```

경로는 backend 폴더 기준 상대경로를 사용합니다.
