# DriftGuard Frontend

정적 파일만으로 동작하는 DriftGuard API 콘솔입니다. 백엔드 API 기본 주소는 `http://127.0.0.1:17321`입니다.

## 실행

터미널 1:

```bash
cd backend
./bin/driftguard serve
```

터미널 2:

```bash
cd frontend
python3 -m http.server 5173
```

브라우저:

```bash
open http://127.0.0.1:5173
```

## 등록 에이전트 실행

화면 왼쪽 `Registered Agent` 영역에서 등록된 에이전트, 시나리오, drift 유형을 선택한 뒤 `Run Agent`를 누르면 백엔드가 해당 에이전트를 실행합니다.

호출 흐름:

```text
Frontend
  -> GET /v1/agents
  -> POST /v1/agent-runs
  -> registry.json에 등록된 에이전트 실행
  -> DriftGuard Agent Review
  -> Result 패널 표시
```

에이전트 등록 정보는 `backend/agents/registry.json`에 있습니다.

## 구성

| 파일 | 설명 |
|---|---|
| `index.html` | DriftGuard API 콘솔 마크업 |
| `styles.css` | `DESIGN.md` 기반 디자인 토큰과 컴포넌트 스타일 |
| `app.js` | 백엔드 API 연동, 샘플 요청, 결과 렌더링 |
