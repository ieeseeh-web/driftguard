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
상단의 `Agent Registry` 페이지에서는 연결 가능한 Python 모듈 에이전트를 화면에서 바로 등록할 수 있습니다.

등록 페이지는 다음 정보를 분리해서 입력합니다.

| 분류 | 입력 내용 |
|---|---|
| Basic | Agent ID, 이름, 설명 |
| Runtime | backend 기준 작업 폴더, Python 실행 파일, `python -m` 모듈 |
| Scenario | 테스트 시나리오 ID와 입력 JSON 경로 |
| Policy Coverage | 테스트할 drift mode 목록 |

오른쪽 패널에는 registry JSON 샘플, CLI 실행 계약, DriftGuard review request 템플릿이 함께 표시됩니다.

호출 흐름:

```text
Frontend
  -> GET /v1/agents
  -> POST /v1/agents, 필요 시 신규 등록
  -> POST /v1/agent-runs
  -> registry.json에 등록된 에이전트 실행
  -> DriftGuard Agent Review
  -> Result 패널 표시
```

에이전트 등록 정보는 기본적으로 `backend/agents/registry.json`에 저장됩니다.

연동 대상 에이전트는 다음 실행 계약을 지원해야 합니다.

```bash
python -m <module> \
  --input <scenario-json> \
  --drift-mode <mode> \
  --output <agent-result-json> \
  --review-output <driftguard-review-request-json>
```

## 구성

| 파일 | 설명 |
|---|---|
| `index.html` | DriftGuard API 콘솔 마크업 |
| `styles.css` | `DESIGN.md` 기반 디자인 토큰과 컴포넌트 스타일 |
| `app.js` | 백엔드 API 연동, 샘플 요청, 결과 렌더링 |
