# Sample Agent: LangGraph Travel Assistant

이 폴더는 DriftGuard의 Agent Drift 테스트를 위한 **실제로 실행 가능한 LangGraph 기반 여행 비서 에이전트** 샘플입니다.

목적은 완벽한 여행 서비스를 만드는 것이 아니라, 다음 Drift 유형을 재현하고 DriftGuard로 평가할 수 있는 테스트 대상 에이전트를 제공하는 것입니다.

- Goal Drift: 사용자가 요청하지 않은 범위까지 여행 계획을 확장
- Instruction Drift: 예산/기간/금지 조건 누락
- Tool Drift: 승인 없이 예약/결제성 도구 호출 시도
- Memory Drift: 일시적 여행 선호를 영구 선호로 저장하려는 후보 생성
- Multi-Agent Drift: Planner가 Worker에게 원본 제약을 누락해 전달

## 1. 설치

프로젝트 루트에서 별도 venv 사용을 권장합니다.

```bash
cd ~/workspaces/driftguard/backend/sample_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 현재 샘플은 외부 LLM API 없이 동작합니다. LangGraph는 workflow 실행에 사용하고, 여행 계획 생성은 deterministic rule 기반으로 구현했습니다.

## 2. 실행

```bash
python -m sample_agent.travel_agent \
  --input scenarios/seoul_weekend.json \
  --output outputs/seoul_weekend_result.json \
  --review-output outputs/seoul_weekend_review.json
```

Drift를 의도적으로 발생시키려면 `--drift-mode`를 사용합니다.

```bash
# Tool Drift: 승인 없이 예약성 도구 호출 후보 생성
python -m sample_agent.travel_agent \
  --input scenarios/seoul_weekend.json \
  --drift-mode tool \
  --output outputs/tool_drift_result.json \
  --review-output outputs/tool_drift_review.json

# Memory Drift: 일시적 요청을 영구 선호로 저장하려는 후보 생성
python -m sample_agent.travel_agent \
  --input scenarios/short_answer_today.json \
  --drift-mode memory \
  --output outputs/memory_drift_result.json \
  --review-output outputs/memory_drift_review.json

# Handoff Drift: Planner → Worker 전달 메시지에서 제약 누락
python -m sample_agent.travel_agent \
  --input scenarios/seoul_weekend.json \
  --drift-mode handoff \
  --output outputs/handoff_drift_result.json \
  --review-output outputs/handoff_drift_review.json
```

## 3. DriftGuard로 평가

샘플 에이전트가 만든 `--review-output` 파일은 DriftGuard `review-agent` 입력 스키마와 호환됩니다.

백엔드 루트에서 실행:

```bash
cd ~/workspaces/driftguard/backend
PYTHONPATH=src python3 -m driftguard.cli review-agent \
  --input sample_agent/outputs/tool_drift_review.json \
  --format json \
  --log logs/sample-agent-reviews.jsonl
```

## 4. DriftGuard API 직접 연동

백엔드 API가 실행 중이면 샘플 에이전트가 실행 직후 DriftGuard API로 직접 리뷰 요청을 보낼 수 있습니다.

터미널 1:

```bash
cd ~/workspaces/driftguard/backend
./bin/driftguard serve
```

터미널 2:

```bash
cd ~/workspaces/driftguard/backend/sample_agent
source .venv/bin/activate

python -m sample_agent.travel_agent \
  --input scenarios/seoul_weekend.json \
  --drift-mode tool \
  --output outputs/tool_drift_result.json \
  --review-output outputs/tool_drift_review.json \
  --driftguard-api http://127.0.0.1:17321 \
  --review-api-output outputs/tool_drift_api_result.json
```

출력에는 DriftGuard 평가 요약이 함께 표시됩니다.

```text
--- driftguard review ---
risk_level: critical
overall_drift_score: 1.0
recommendation: stop
requires_human_confirmation: true
```

## 5. Backend Agent Registry로 실행

샘플 에이전트는 기본 레지스트리 `backend/agents/registry.json`에 `sample-travel-assistant`로 등록되어 있습니다.

백엔드와 프론트엔드를 실행하면 화면에서 바로 선택해 실행할 수 있습니다.

```bash
cd ~/workspaces/driftguard/backend
./bin/driftguard serve
```

```bash
cd ~/workspaces/driftguard/frontend
python3 -m http.server 5173
open http://127.0.0.1:5173
```

프론트엔드 `Console` 화면의 `Registered Agent` 영역에서 `Sample Travel Assistant`를 선택하고 `Run Agent`를 누르면 백엔드가 다음 흐름을 수행합니다.

```text
GET /v1/agents
POST /v1/agent-runs
  -> python -m sample_agent.travel_agent
  -> --review-output JSON 생성
  -> DriftGuard Agent Review 실행
```

새 에이전트는 `Agent Registry` 화면 또는 `POST /v1/agents` API로 등록할 수 있습니다. 등록 대상 에이전트는 샘플 에이전트와 같은 CLI 계약을 지원해야 합니다.

```bash
python -m <module> \
  --input <scenario-json> \
  --drift-mode <mode> \
  --output <agent-result-json> \
  --review-output <driftguard-review-request-json>
```

## 6. 구조

```text
sample_agent/
  README.md
  requirements.txt
  sample_agent/
    __init__.py
    travel_agent.py
  scenarios/
    seoul_weekend.json
    short_answer_today.json
  outputs/
    .gitkeep
```

## 7. LangGraph 노드

```text
intake
  ↓
planner
  ↓
handoff
  ↓
research
  ↓
tool_decision
  ↓
memory_candidate
  ↓
final
```

각 노드는 실행 로그를 남기며, Drift 테스트 모드에 따라 일부 노드가 의도적으로 위험하거나 부정확한 산출물을 생성합니다.
