# Agent Drift 탐지·평가에 활용 가능한 대표 오픈소스 정리

이 문서는 DriftGuard의 `Agent Drift Detection & Judge Architecture` 발표 및 구현에 참고할 수 있는 대표 오픈소스 프로젝트를 정리한 자료다. 초점은 다음 네 가지다.

1. **LLM-as-a-Judge / 평가 프레임워크**: 응답 품질, 목표 달성, 도구 사용, RAG 품질 등을 자동 채점
2. **Agent-as-a-Judge / 에이전트 실행 과정 평가**: 최종 답변뿐 아니라 계획, 중간 단계, 도구 호출, 증거 수집 과정을 평가
3. **Observability / Trace / LLMOps**: 에이전트 실행 로그, 비용, 지연시간, 프롬프트, 평가 결과를 수집·분석
4. **Guardrails / Safety / Policy Enforcement**: 입력·출력·도구 호출 전후에 정책 위반, 위험 행동, 프롬프트 인젝션을 차단
5. **Agent Benchmark / Testbed**: Agent Drift 평가용 시나리오·벤치마크·실험 환경으로 활용

---

## 1. 요약 추천

DriftGuard 관점에서 바로 연결하기 좋은 조합은 다음과 같다.

| 목적 | 우선 검토 오픈소스 | DriftGuard 활용 포인트 |
|---|---|---|
| Agent Drift 단위 테스트 | DeepEval, promptfoo, Inspect AI | 목표 달성, 도구 정확성, 계획 준수, 회귀 테스트 |
| LLM-as-a-Judge 운영 평가 | Langfuse, Phoenix, DeepEval | trace 기반 judge score 저장, 대시보드, 실험 비교 |
| Agent-as-a-Judge 연구/확장 | metauto-ai/agent-as-a-judge, Microsoft AgentAsJudge | 중간 실행 단계 평가, multi-agent judge pipeline 설계 참고 |
| Trace/Observability | Langfuse, Phoenix, AgentOps, OpenLLMetry, Helicone | Agent Drift 원인 분석을 위한 trace/event 수집 |
| Guardrails/Policy | Guardrails AI, NVIDIA NeMo Guardrails, OpenAI Guardrails | drift 발생 전·중·후 정책 enforcement 구조 참고 |
| 벤치마크/평가셋 | AgentBench, SWE-bench, BrowserGym, agentic-benchmarks | DriftGuard 평가 시나리오와 benchmark validity 설계 참고 |

**가장 현실적인 초기 통합안**:

- DriftGuard CLI의 `review-agent` 결과를 **DeepEval 스타일 metric**으로 확장
- 실행 로그는 **Langfuse 또는 Phoenix trace schema**에 맞춰 내보내기
- 위험 도구 호출은 **Guardrails AI / NeMo Guardrails**처럼 validator 체인으로 모델링
- 발표 자료에서는 **Agent-as-a-Judge** 논문/구현을 DriftGuard의 judge-agent 방향성과 연결

---

## 2. LLM-as-a-Judge / Evaluation Framework

### 2.1 DeepEval

- Repository: <https://github.com/confident-ai/deepeval>
- 성격: LLM 애플리케이션용 오픈소스 평가 프레임워크. “Pytest for LLMs”에 가까운 개발자 경험 제공.
- 주요 기능:
  - G-Eval 기반 LLM-as-a-Judge
  - RAG 평가: answer relevancy, faithfulness, contextual precision/recall 등
  - Agentic metrics: task completion, tool correctness, goal accuracy, step efficiency, plan adherence, plan quality, tool use, argument correctness
  - pytest와 유사한 테스트 실행 경험
- DriftGuard 관련성:
  - DriftGuard의 핵심 평가 항목인 **목표 유지**, **도구 사용 적절성**, **계획 준수**, **불필요한 단계 탐지**와 직접적으로 겹친다.
  - DriftGuard의 `goal_score`, `tool_score`, `memory_score`, `overall_score`를 DeepEval metric 스타일로 재구성할 수 있다.
  - “Agent Drift를 테스트 코드처럼 회귀 테스트한다”는 메시지에 적합하다.
- 장점:
  - Agentic metric이 이미 잘 분류되어 있음
  - CI/CD와 결합하기 쉬움
  - custom metric 확장이 자연스러움
- 한계/주의:
  - Judge model 품질과 프롬프트 설계에 따라 평가 편차가 생길 수 있음
  - 운영 trace 저장/대시보드는 별도 플랫폼과 결합하는 편이 좋음

### 2.2 promptfoo

- Repository: <https://github.com/promptfoo/promptfoo>
- 성격: 프롬프트, 모델, RAG, agent를 테스트하고 red teaming/vulnerability scanning까지 지원하는 CLI·라이브러리.
- 주요 기능:
  - YAML 기반 평가 설정
  - 모델 비교: OpenAI, Anthropic, Azure, Bedrock, Ollama 등
  - LLM-as-a-Judge 평가
  - Red teaming 및 취약점 스캔
  - CI/CD 통합
  - MIT licensed, OpenAI에 합류 후에도 오픈소스 유지
- DriftGuard 관련성:
  - DriftGuard의 “정책 위반/목표 이탈 시나리오”를 promptfoo test case로 표현 가능
  - DriftGuard CLI 결과를 promptfoo assertion 또는 provider output으로 연결 가능
  - 발표에서 **개발자 친화적 eval-as-code** 사례로 소개하기 좋다.
- 장점:
  - 설정 파일 기반이라 재현성과 공유가 좋음
  - red team과 eval을 함께 다룸
  - PR/CI에서 drift regression gate로 쓰기 좋음
- 한계/주의:
  - 복잡한 multi-step trace 평가보다는 prompt/model 비교와 시나리오 테스트에 더 강함

### 2.3 Ragas

- Repository: <https://github.com/vibrantlabsai/ragas>
- 성격: LLM/RAG 애플리케이션 평가와 테스트셋 생성을 위한 오픈소스 툴킷.
- 주요 기능:
  - LLM 기반 및 전통적 metric
  - RAG 평가: faithfulness, context relevance 등
  - production-aligned test set generation
  - LangChain 및 observability 도구와 통합
  - 향후 agent evals 템플릿 예고
- DriftGuard 관련성:
  - Agent Drift 중 **memory/retrieval drift** 또는 RAG 기반 agent의 grounding 저하 평가에 적합
  - DriftGuard의 `memory_update`, `context_use`, `evidence_grounding` 평가를 확장할 때 참고 가능
- 장점:
  - RAG 품질 평가 분야에서 대표성이 높음
  - 테스트셋 생성과 feedback loop를 강조
- 한계/주의:
  - 순수 agent tool-use drift 평가는 DeepEval/promptfoo보다 직접성은 낮음

### 2.4 OpenAI Evals

- Repository: <https://github.com/openai/evals>
- 성격: LLM 및 LLM 기반 시스템 평가 프레임워크와 benchmark registry.
- 주요 기능:
  - custom eval 작성
  - 기존 eval registry 활용
  - private eval 구성
  - prompt chain/tool-using agent용 Completion Function Protocol 지원
- DriftGuard 관련성:
  - DriftGuard의 평가 schema를 OpenAI Evals 형식의 custom eval로 포팅 가능
  - 발표에서 “eval 없이 모델/agent 변경 영향 파악이 어렵다”는 근거 사례로 사용 가능
- 장점:
  - 평가 체계와 registry 개념이 명확
  - custom eval 작성 관점에서 참고하기 좋음
- 한계/주의:
  - 최신 운영형 LLMOps/trace 대시보드는 별도 도구가 필요

### 2.5 Inspect AI

- Repository: <https://github.com/UKGovernmentBEIS/inspect_ai>
- 성격: UK AI Security Institute가 만든 대규모 언어 모델 평가 프레임워크.
- 주요 기능:
  - prompt engineering, tool usage, multi-turn dialog, model-graded evaluation 지원
  - 200개 이상의 pre-built evaluations
  - Python package로 scoring/elicitation 확장 가능
- DriftGuard 관련성:
  - Agent Drift를 안전성 평가와 연결할 때 좋은 reference
  - multi-turn/tool-use 평가 프레임워크 설계 참고 가능
- 장점:
  - AI safety/evaluation 쪽 신뢰도 있는 출처
  - model-graded evaluation과 tool usage를 함께 다룸
- 한계/주의:
  - 제품형 observability보다는 평가 프레임워크에 가깝다.

---

## 3. Agent-as-a-Judge / Agentic Evaluation

### 3.1 metauto-ai/agent-as-a-judge

- Repository: <https://github.com/metauto-ai/agent-as-a-judge>
- Paper: “Agent-as-a-Judge: Evaluate Agents with Agents”
- 성격: 에이전트가 다른 에이전트의 작업 실행 과정을 관찰하고 평가하는 Agent-as-a-Judge 구현/연구 프로젝트.
- 주요 기능/개념:
  - task execution 중 또는 이후 자동 평가
  - step-by-step feedback 제공
  - reward signal로 활용 가능한 중간 평가
  - DevAI benchmark: 55개 현실적 AI 개발 태스크와 365개 계층형 요구사항
- DriftGuard 관련성:
  - DriftGuard의 핵심 메시지인 “최종 답변만 보면 drift를 놓친다”와 가장 직접적으로 연결된다.
  - `Agent Review` 기능을 단순 LLM judge에서 **observing judge agent**로 확장하는 방향의 핵심 reference.
  - `Goal → Plan → Tool → Evidence → Final` 실행 경로별 judge 설계에 참고 가능.
- 장점:
  - Agent Drift 연구 배경으로 설득력이 높음
  - 실행 과정 기반 평가라는 점이 DriftGuard와 잘 맞음
- 한계/주의:
  - 연구/PoC 성격이 강하며 운영 시스템에 바로 붙이려면 schema/trace adapter 설계가 필요

### 3.2 Microsoft AgentAsJudge

- Repository: <https://github.com/microsoft/AgentAsJudge>
- 성격: multi-agent reasoning pipeline으로 텍스트 샘플의 agentic quality를 평가하는 프레임워크.
- 주요 기능:
  - reviewer, critic, ranker agent 구조
  - custom prompt 교체 가능
  - score와 detailed feedback 산출
  - Azure OpenAI 기반 inference 사용
- DriftGuard 관련성:
  - DriftGuard judge pipeline을 **Reviewer → Critic → Ranker/Aggregator** 구조로 확장할 때 참고 가능
  - 단일 judge보다 multi-agent judge가 왜 필요한지 설명하는 발표 슬라이드에 적합
- 장점:
  - multi-agent judge pipeline 구조가 명확
  - prompt directory와 metrics directory를 분리한 구조 참고 가능
- 한계/주의:
  - Azure OpenAI 의존성이 있어 그대로 쓰기보다는 아키텍처 패턴을 참고하는 편이 좋음

---

## 4. Observability / Trace / LLMOps

### 4.1 Langfuse

- Repository: <https://github.com/langfuse/langfuse>
- 성격: 오픈소스 LLM engineering platform. observability, tracing, evals, prompt management, datasets 제공.
- 주요 기능:
  - LLM application tracing
  - prompt management/versioning
  - LLM-as-a-Judge, user feedback, manual labeling, custom eval pipeline
  - datasets 및 dataset runs
  - playground
  - OpenTelemetry, LangChain, OpenAI SDK, LiteLLM 등과 통합
  - self-host 가능
- DriftGuard 관련성:
  - DriftGuard가 생성한 Agent Review 결과를 Langfuse score/evaluation으로 저장 가능
  - agent trace를 수집해 drift 원인을 “어느 단계에서 목표가 틀어졌는가”로 분석 가능
  - presentation에서 운영형 DriftGuard의 대시보드 후보로 소개 가능
- 장점:
  - trace, prompt, eval, dataset을 한 플랫폼에서 다룸
  - self-host와 협업 워크플로우가 좋음
- 한계/주의:
  - 자체 평가 로직을 DriftGuard에 둘지, Langfuse eval pipeline에 둘지 경계 설계 필요

### 4.2 Arize Phoenix

- Repository: <https://github.com/Arize-ai/phoenix>
- 성격: 오픈소스 AI observability & evaluation platform.
- 주요 기능:
  - OpenTelemetry 기반 tracing
  - LLM evals: response/retrieval evals
  - versioned datasets
  - experiments
  - playground와 prompt management
  - OpenAI Agents SDK, Claude Agent SDK, LangGraph, CrewAI, LlamaIndex, DSPy 등과 통합
- DriftGuard 관련성:
  - DriftGuard의 sample LangGraph agent와 연결하기 좋음
  - OpenTelemetry 기반 trace export/import 설계에 참고 가능
  - Agent Drift 평가 결과를 experiment 단위로 비교하는 데 적합
- 장점:
  - local/Jupyter/container/cloud 등 실행 옵션이 다양
  - OpenInference/OpenTelemetry 생태계와 잘 맞음
- 한계/주의:
  - 정책 enforcement보다는 관측·평가·실험에 초점

### 4.3 AgentOps

- Repository: <https://github.com/AgentOps-AI/agentops>
- 성격: AI agent monitoring, LLM cost tracking, benchmarking을 위한 Python SDK 및 dashboard.
- 주요 기능:
  - step-by-step agent execution graph
  - session replay
  - LLM cost management
  - CrewAI, LangGraph, AutoGen/AG2, OpenAI Agents SDK 등 통합
  - self-host 지원
- DriftGuard 관련성:
  - DriftGuard가 “Agent Drift는 trace 없이는 재현하기 어렵다”는 주장을 할 때 좋은 사례
  - decorator 기반으로 agent/session/operation span을 만드는 방식은 DriftGuard logger 확장에 참고 가능
- 장점:
  - agent 중심 observability에 특화
  - session replay와 cost tracking 메시지가 직관적
- 한계/주의:
  - DriftGuard의 judge/policy score와 연결하려면 custom span attribute 또는 event schema가 필요

### 4.4 OpenLLMetry / Traceloop

- Repository: <https://github.com/traceloop/openllmetry>
- 성격: OpenTelemetry 기반 GenAI/LLM observability instrumentation.
- 주요 기능:
  - LLM provider, vector DB instrumentation
  - standard OpenTelemetry data export
  - Datadog, Honeycomb, Grafana, New Relic, Sentry, SigNoz 등과 연결
  - Apache 2.0 license
- DriftGuard 관련성:
  - DriftGuard가 vendor-neutral trace schema를 만들 때 강력한 reference
  - 기존 APM/observability stack에 DriftGuard drift events를 흘려보내는 구조 설계에 적합
- 장점:
  - 표준 OpenTelemetry 기반이라 lock-in이 낮음
  - 운영 인프라와 붙이기 좋음
- 한계/주의:
  - 자체 대시보드/평가 UX보다는 instrumentation layer에 가깝다.

### 4.5 Helicone

- Repository: <https://github.com/Helicone/helicone>
- 성격: LLM observability, AI gateway, routing, cost/latency tracking 플랫폼.
- 주요 기능:
  - request/session trace
  - cost & latency tracking
  - prompt management
  - model routing/fallback
  - dataset/fine-tuning workflow
  - self-host 지원
- DriftGuard 관련성:
  - DriftGuard를 AI gateway 앞뒤의 policy/evaluation layer로 배치하는 아키텍처 설명에 활용 가능
  - 모델 라우팅과 fallback이 drift risk와 어떻게 연결되는지 논의할 때 유용
- 장점:
  - gateway와 observability를 함께 제공
  - 빠른 통합에 강점
- 한계/주의:
  - 세밀한 agent step 평가보다는 request/session 관측에 더 가까움

---

## 5. Guardrails / Safety / Policy Enforcement

### 5.1 Guardrails AI

- Repository: <https://github.com/guardrails-ai/guardrails>
- 성격: LLM 애플리케이션에 input/output guard와 structured output validation을 추가하는 Python framework.
- 주요 기능:
  - Guardrails Hub validator
  - 입력/출력 risk detection, quantification, mitigation
  - 여러 validator 조합
  - Pydantic 기반 structured output validation
  - standalone server/API로 실행 가능
- DriftGuard 관련성:
  - DriftGuard의 policy engine을 validator chain으로 표현할 때 직접적인 reference
  - 예: `RiskyToolCallValidator`, `GoalDeviationValidator`, `SensitiveMemoryValidator`, `MissingConfirmationValidator`
  - Agent Drift 결과를 “차단/경고/허용”으로 바꾸는 enforcement layer 설계에 적합
- 장점:
  - validator 개념이 명확하고 확장성이 좋음
  - Python 기반 DriftGuard와 통합하기 쉬움
- 한계/주의:
  - agent 내부 plan/tool trace 평가보다는 input/output validation에 초점이 있음

### 5.2 NVIDIA NeMo Guardrails

- Repository: <https://github.com/NVIDIA-NeMo/Guardrails>
- 성격: LLM conversational application에 programmable guardrails를 추가하는 오픈소스 toolkit.
- 주요 기능:
  - Rails/Colang 기반 대화 흐름 제어
  - topical moderation, output moderation, dialog path enforcement
  - tool/service 연결 보안
  - jailbreak/prompt injection 방어 시나리오
  - Python API 및 guardrails server
- DriftGuard 관련성:
  - DriftGuard의 “Intent Contract + Guard + Policy” 구조를 설명할 때 매우 좋은 reference
  - 특히 agent가 사용자 목표에서 벗어나거나, 허용되지 않은 주제로 이동하거나, SOP를 따르지 않는 문제를 guardrail로 표현 가능
- 장점:
  - programmable guardrail 개념이 발표에서 설명하기 좋음
  - domain assistant/SOP enforcement에 강함
- 한계/주의:
  - Colang/rails 설정 학습 비용이 있음
  - DriftGuard의 judge score와 직접 결합하려면 adapter 필요

### 5.3 OpenAI Agents SDK Guardrails / OpenAI Guardrails

- Docs: <https://openai.github.io/openai-agents-python/guardrails/>
- Repository: <https://github.com/openai/openai-guardrails-python>
- 성격: Agent input/output/tool guardrails와 safety/compliance guardrails 패턴.
- 주요 기능:
  - input guardrails
  - output guardrails
  - tool guardrails
  - blocking 또는 parallel guardrails 패턴
- DriftGuard 관련성:
  - DriftGuard 발표에서 “agent-level guardrail만으로는 tool call drift를 막기 어렵고, tool guardrail이 필요하다”는 메시지에 활용 가능
  - `review-agent --log`가 발견하는 risky tool call/missing confirmation과 직접 연결됨
- 장점:
  - 최신 agent SDK의 guardrail 구조와 맞닿아 있음
  - tool-level guardrail 개념이 DriftGuard와 매우 잘 맞음
- 한계/주의:
  - 특정 SDK 생태계와 결합되어 있으므로 범용 DriftGuard 구현은 추상화 계층이 필요

---

## 6. Agent Benchmark / Testbed

### 6.1 AgentBench

- Repository: <https://github.com/THUDM/AgentBench>
- 성격: LLM-as-Agent를 다양한 환경에서 평가하기 위한 종합 benchmark.
- 주요 환경:
  - Operating System
  - Database
  - Knowledge Graph
  - Digital Card Game
  - Lateral Thinking Puzzle
  - ALFWorld
  - WebShop
  - Web Browsing/Mind2Web
  - function-calling 버전에서는 Docker Compose 기반 worker 제공
- DriftGuard 관련성:
  - DriftGuard의 평가 범위를 “단일 답변”이 아니라 “환경과 상호작용하는 agent”로 확장할 때 reference
  - 도구 호출, 장기 작업, 환경 상태 변화가 포함된 drift scenario 설계에 활용 가능
- 장점:
  - 다양한 agent 환경을 포괄
  - benchmark/testbed 메시지가 명확
- 한계/주의:
  - 리소스 요구량이 높을 수 있음
  - 발표/PoC에서는 전체 실행보다 benchmark design reference로 활용하는 것이 현실적

### 6.2 SWE-bench

- Repository: <https://github.com/SWE-bench/SWE-bench>
- 성격: 실제 GitHub issue를 해결하는 patch generation benchmark.
- 주요 기능:
  - real-world software issue 기반 평가
  - Docker 기반 reproducible evaluation harness
  - SWE-bench Lite, Verified, Multimodal 등
- DriftGuard 관련성:
  - coding agent에서 목표 drift, test gaming, 잘못된 patch, 과도한 변경을 평가하는 데 활용 가능
  - DriftGuard의 Agent Review 예제를 coding task로 확장할 때 유용
- 장점:
  - 실제성 높은 software engineering benchmark
  - containerized evaluation으로 재현성 좋음
- 한계/주의:
  - 일반 agent drift보다는 coding agent 평가에 특화
  - benchmark gaming/validity 이슈를 함께 고려해야 함

### 6.3 BrowserGym

- Repository: <https://github.com/ServiceNow/BrowserGym>
- 성격: web task automation agent를 위한 Gym 환경.
- 포함 benchmark:
  - MiniWoB
  - WebArena
  - WebArenaVerified
  - VisualWebArena
  - WorkArena
  - AssistantBench
  - WebLINX
  - OpenApps
  - TimeWarp
- DriftGuard 관련성:
  - 웹 브라우징 agent의 목표 이탈, 잘못된 클릭, 정보 누락, 사용자 요청 미완료 등을 평가하는 환경으로 활용 가능
  - DriftGuard가 browser agent observability와 연결되는 시나리오를 만들 때 적합
- 장점:
  - web agent benchmark를 통합적으로 다룸
  - Gym interface라 agent loop 설계가 명확
- 한계/주의:
  - consumer product가 아닌 연구용 framework라는 점에 주의
  - 개별 benchmark별 setup 비용 존재

### 6.4 agentic-benchmarks / ABC Checklist

- Repository: <https://github.com/uiuc-kang-lab/agentic-benchmarks>
- 성격: agentic benchmark의 validity를 평가하기 위한 checklist와 사례 연구 모음.
- 주요 개념:
  - Outcome Validity: 성공 신호가 실제 task completion을 의미하는가
  - Task Validity: 목표 capability가 있어야만 풀 수 있는 task인가
  - Benchmark Reporting: benchmark 한계와 해석 방법을 정량 근거와 함께 제시하는가
- DriftGuard 관련성:
  - DriftGuard 자체 평가셋을 만들 때 반드시 참고해야 하는 benchmark 품질 기준
  - “Agent Drift 평가도 잘못 만들면 agent가 점수를 gaming할 수 있다”는 발표 메시지에 매우 적합
- 장점:
  - DriftGuard의 평가 신뢰성/한계 섹션에 직접 활용 가능
  - SWE-bench, WebArena, Tau-Bench 등 기존 benchmark의 취약점 사례 제공
- 한계/주의:
  - 평가 실행 프레임워크라기보다는 benchmark auditing/checklist에 가깝다.

---

## 7. DriftGuard 기능별 매핑

| DriftGuard 기능/개념 | 참고 오픈소스 | 구현 아이디어 |
|---|---|---|
| Intent Contract | NeMo Guardrails, Guardrails AI, promptfoo | 사용자 목표·금지사항·성공조건을 schema/validator/test case로 표현 |
| Agent Review | DeepEval, Agent-as-a-Judge, Microsoft AgentAsJudge | goal/tool/memory/final 단계별 judge와 reviewer/critic/ranker 구조 |
| Execution Log 평가 | AgentOps, Langfuse, Phoenix, OpenLLMetry | trace/span/event schema로 agent step 수집 |
| Risky Tool Call 탐지 | Guardrails AI, OpenAI Agents Guardrails | tool-level guardrail 및 confirmation requirement validator |
| Memory Drift 탐지 | Ragas, DeepEval, Langfuse | retrieval/context grounding, sensitive memory skip, memory update correctness 평가 |
| Policy Recommendation | Guardrails AI, NeMo Guardrails | score → allow/warn/block/escalate 정책 매핑 |
| Regression Test | promptfoo, DeepEval, OpenAI Evals, Inspect AI | CI에서 drift scenario suite 실행 |
| Benchmark 설계 | AgentBench, SWE-bench, BrowserGym, agentic-benchmarks | 실제 agent 환경과 benchmark validity checklist 반영 |

---

## 8. DriftGuard에 추가하면 좋은 문서/코드 산출물

### 8.1 문서

- `agent/OPEN_SOURCE_LANDSCAPE.md` — 현재 문서
- `agent/INTEGRATION_PLAN.md` — DeepEval/Langfuse/Phoenix/Guardrails 중 무엇을 먼저 붙일지 계획
- `agent/BENCHMARK_DESIGN.md` — Agent Drift benchmark 설계 원칙과 ABC checklist 반영
- `agent/JUDGE_PIPELINE.md` — LLM-as-a-Judge vs Agent-as-a-Judge pipeline 비교

### 8.2 코드

- `src/driftguard/exporters/langfuse.py`
  - DriftGuard review result를 Langfuse score/trace metadata로 export
- `src/driftguard/exporters/phoenix.py`
  - OpenTelemetry/OpenInference span attribute로 export
- `src/driftguard/metrics/deepeval_adapter.py`
  - DriftGuard score를 DeepEval custom metric으로 변환
- `src/driftguard/guards/validators.py`
  - Guardrails AI와 유사한 validator chain 구현
- `examples/promptfoo/driftguard.yaml`
  - promptfoo 기반 drift regression scenario

---

## 9. 발표에 넣기 좋은 비교 메시지

1. **LLM-as-a-Judge는 최종 답변 평가에 강하지만, Agent Drift는 실행 과정 평가가 필요하다.**
   - DeepEval, promptfoo, OpenAI Evals는 좋은 출발점이다.
   - 그러나 tool call, memory update, handoff, confirmation 누락은 trace 기반 평가가 필요하다.

2. **Agent-as-a-Judge는 DriftGuard의 핵심 방향성과 맞다.**
   - metauto-ai/agent-as-a-judge는 step-by-step feedback과 reward signal을 강조한다.
   - DriftGuard는 이를 제품/CLI 관점에서 `Agent Review`로 구현할 수 있다.

3. **관측 가능성 없이는 drift를 재현할 수 없다.**
   - Langfuse, Phoenix, AgentOps, OpenLLMetry는 trace와 span을 통해 agent의 실행 과정을 보존한다.
   - DriftGuard는 이 trace 위에 judge와 policy layer를 얹는 구조로 설명 가능하다.

4. **Guardrails는 drift를 사후 평가에서 사전 차단으로 확장한다.**
   - Guardrails AI와 NeMo Guardrails는 validator/rail 개념을 제공한다.
   - DriftGuard는 risk score를 allow/warn/block/escalate로 매핑할 수 있다.

5. **Benchmark 자체도 drift/gaming될 수 있다.**
   - agentic-benchmarks의 ABC checklist는 DriftGuard benchmark 설계의 품질 기준으로 활용할 수 있다.

---

## 10. 우선순위 제안

### Phase 1: 빠른 문서/발표 강화

- DeepEval, promptfoo, Langfuse, Guardrails AI, Agent-as-a-Judge를 핵심 reference로 발표에 추가
- Agent Drift taxonomy를 기존 오픈소스 metric과 매핑
- benchmark validity 위험을 agentic-benchmarks로 보강

### Phase 2: 실용 통합

- DriftGuard JSON output → Langfuse/Phoenix metadata export
- DriftGuard scenario → promptfoo YAML 변환 예제
- DriftGuard scoring → DeepEval custom metric 예제

### Phase 3: 고급 연구/제품화

- Agent-as-a-Judge style observer agent 추가
- multi-judge aggregation: goal judge, tool judge, memory judge, policy judge
- guardrail enforcement: pre-tool, post-tool, final-output 단계별 차단
- benchmark suite: coding agent, browser agent, RAG agent, handoff agent scenario 구성

---

## 11. 참고 링크 모음

### Evaluation / LLM-as-a-Judge

- DeepEval: <https://github.com/confident-ai/deepeval>
- promptfoo: <https://github.com/promptfoo/promptfoo>
- Ragas: <https://github.com/vibrantlabsai/ragas>
- OpenAI Evals: <https://github.com/openai/evals>
- Inspect AI: <https://github.com/UKGovernmentBEIS/inspect_ai>

### Agent-as-a-Judge

- Agent-as-a-Judge: <https://github.com/metauto-ai/agent-as-a-judge>
- Microsoft AgentAsJudge: <https://github.com/microsoft/AgentAsJudge>

### Observability / LLMOps

- Langfuse: <https://github.com/langfuse/langfuse>
- Arize Phoenix: <https://github.com/Arize-ai/phoenix>
- AgentOps: <https://github.com/AgentOps-AI/agentops>
- OpenLLMetry: <https://github.com/traceloop/openllmetry>
- Helicone: <https://github.com/Helicone/helicone>

### Guardrails / Safety

- Guardrails AI: <https://github.com/guardrails-ai/guardrails>
- NVIDIA NeMo Guardrails: <https://github.com/NVIDIA-NeMo/Guardrails>
- OpenAI Agents SDK Guardrails: <https://openai.github.io/openai-agents-python/guardrails/>
- OpenAI Guardrails Python: <https://github.com/openai/openai-guardrails-python>

### Agent Benchmarks / Testbeds

- AgentBench: <https://github.com/THUDM/AgentBench>
- SWE-bench: <https://github.com/SWE-bench/SWE-bench>
- BrowserGym: <https://github.com/ServiceNow/BrowserGym>
- agentic-benchmarks / ABC Checklist: <https://github.com/uiuc-kang-lab/agentic-benchmarks>

## 12. Local Agent-as-a-Judge Reference Materials

DriftGuard repo에는 Agent-as-a-Judge 확장 방향을 구체화하기 위한 내부 참고 자료가 추가되어 있다.

| 파일 | 용도 |
|---|---|
| `agent/references/agent-as-a-judge-paper-summary.md` | Agent-as-a-Judge 개념, LLM-as-a-Judge 한계, 핵심 방법론 요약 |
| `agent/references/agent-as-a-judge-prd.md` | Agentic Evaluation Platform 제품 요구사항 참고 |
| `agent/references/agent-as-a-judge-development-guide.md` | Orchestrator, Planner, Tool Executor, Judge, Aggregator 구현 가이드 참고 |
| `agent/AGENT_AS_JUDGE_PLAN.md` | 위 자료를 DriftGuard 맥락에 맞게 재구성한 실행 계획 |

이 자료들은 외부 오픈소스 landscape와 별개로 DriftGuard의 자체 Agent-as-a-Judge 구현 방향을 정의하는 기준 문서로 사용한다.

