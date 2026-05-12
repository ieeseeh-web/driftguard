# MVP 개발 태스크: DriftGuard

## 1. MVP 목표

DriftGuard MVP는 에이전트의 최종 응답, 도구 호출, 메모리 업데이트 과정에서 Agent Drift 가능성을 평가하고 위험도에 따라 대응 결정을 반환하는 최소 기능 제품이다.

---

## 2. 마일스톤

| 마일스톤 | 목표 | 산출물 |
|---|---|---|
| M1 | 요구사항 확정 | PRD, 기능 명세, 아키텍처 |
| M2 | 평가 스키마 정의 | EvaluationRequest/Result 타입 |
| M3 | Judge 프롬프트 작성 | Goal/Tool/Memory Judge Prompt |
| M4 | Policy Engine 구현 | 위험도별 대응 로직 |
| M5 | 로그 저장 구현 | JSONL 또는 SQLite 로그 |
| M6 | 샘플 테스트 작성 | 테스트 케이스 10개 이상 |
| M7 | CLI/API 프로토타입 | 로컬 실행 가능한 MVP |
| M8 | 프론트엔드 콘솔 | 백엔드 API 실행 UI |
| M9 | Agent Registry | 에이전트 등록/실행 연동 |

---

## 3. 상세 태스크

### M1. 문서 정리

- [x] PRD 작성
- [x] README 작성
- [x] 기능 명세 작성
- [x] 아키텍처 문서 작성
- [ ] 용어집 작성

---

### M2. 평가 스키마 정의

- [x] `EvaluationType` 정의
  - `goal`
  - `instruction`
  - `tool`
  - `memory`
  - `final`
- [x] `EvaluationRequest` 타입 정의
- [x] `EvaluationResult` 타입 정의
- [x] `PolicyDecision` 타입 정의
- [x] JSON Schema 작성

완료 기준:

- 모든 평가 요청/응답이 구조화된 JSON으로 표현 가능해야 한다.

---

### M3. Judge 프롬프트 작성

- [x] Goal Alignment Judge 프롬프트 작성
- [x] Instruction Following Judge 프롬프트 작성
- [x] Tool Risk Judge 프롬프트 작성
- [x] Memory Risk Judge 프롬프트 작성
- [x] Final Response Judge 프롬프트 작성
- [x] Judge 출력 JSON 형식 고정
- [ ] JSON 파싱 실패 시 재시도 프롬프트 작성

완료 기준:

- 각 Judge가 점수, 위험도, 근거, 추천 대응을 반환해야 한다.

---

### M4. Policy Engine 구현

- [x] Drift Score 계산 함수 구현
- [x] 위험도 분류 함수 구현
- [x] 대응 결정 함수 구현
- [x] 고위험 도구 fail-closed 정책 구현
- [x] Memory 저장 거부 정책 구현

정책 초안:

```text
score < 0.2        -> continue
0.2 <= score < 0.5 -> revise
0.5 <= score < 0.8 -> ask_user
score >= 0.8       -> stop
```

완료 기준:

- Judge 결과를 입력받아 일관된 정책 결정을 반환해야 한다.

---

### M5. Evaluation Log 구현

- [x] 로그 포맷 정의
- [x] JSONL 저장 구현
- [x] 평가 ID 생성
- [x] timestamp 기록
- [ ] 입력 원문 또는 해시 저장 정책 결정
- [x] 평가 결과와 최종 대응 저장

완료 기준:

- 모든 평가 결과가 추적 가능해야 한다.

---

### M6. 샘플 테스트 작성

필수 테스트 케이스:

- [x] 정상적인 목표 일치 응답
- [x] 사용자 목표에서 벗어난 응답
- [x] 명시적 지시사항 누락
- [x] 불필요한 도구 호출
- [x] 승인 필요한 도구 호출
- [x] 안전한 도구 호출
- [x] 저장하면 안 되는 메모리
- [x] 저장해도 되는 사용자 선호
- [x] 다소 모호한 요청
- [x] 최종 응답 품질 부족

완료 기준:

- 최소 10개 테스트 케이스가 통과해야 한다.

---

### M7. CLI/API 프로토타입

#### CLI 후보

```bash
driftguard evaluate --type goal --input sample.json
driftguard evaluate --type tool --input tool-call.json
driftguard evaluate --type memory --input memory.json
```

#### API 구현

```http
GET /health
GET /docs
GET /openapi.json
GET /v1/agents
POST /v1/agents
POST /v1/agent-runs
POST /v1/evaluations
POST /v1/agent-reviews
```

완료 기준:

- 로컬에서 샘플 입력을 넣고 평가 결과를 확인할 수 있어야 한다.

---

### M8. 프론트엔드 콘솔

- [x] 정적 프론트엔드 구조 생성
- [x] 백엔드 API base URL 설정
- [x] `/health` 상태 확인
- [x] Agent Review/Evaluation 샘플 로드
- [x] JSON 포맷팅
- [x] 요청 실행 및 결과 요약 표시
- [x] Swagger 링크 연결

완료 기준:

- `python3 -m http.server 5173`으로 실행하고 백엔드 API와 연동되어야 한다.

---

### M9. Agent Registry

- [x] 에이전트 레지스트리 파일 구조 정의
- [x] `GET /v1/agents` 구현
- [x] `POST /v1/agents` 등록/갱신 구현
- [x] `POST /v1/agent-runs` 등록 에이전트 실행 구현
- [x] 샘플 LangGraph 에이전트 등록
- [x] 프론트엔드 Agent Registry 페이지 구현
- [x] 등록 샘플/템플릿/연동 요구사항 표시
- [x] 등록 API 테스트 추가

완료 기준:

- 사용자가 화면에서 연결 가능한 에이전트를 등록하고, 등록된 에이전트를 선택해 DriftGuard 리뷰까지 실행할 수 있어야 한다.

---

## 4. 우선순위

### P0

- 평가 스키마
- Goal Alignment Judge
- Tool Risk Judge
- Memory Risk Judge
- Policy Engine
- 로그 저장

### P1

- Instruction Following Judge
- Final Response Judge
- CLI
- 테스트 케이스 확장

### P2

- Multi-Agent Drift 평가
- 대시보드
- 다중 Judge 앙상블
- AgentOps 연동

---

## 5. 추천 구현 순서

1. 타입/스키마부터 작성한다.
2. Rule-based Policy Engine을 먼저 만든다.
3. Judge 프롬프트를 붙인다.
4. JSONL 로그를 저장한다.
5. CLI로 샘플 평가를 실행한다.
6. 테스트 케이스를 늘린다.
7. 실제 에이전트 런타임에 Hook 형태로 연결한다.

---

## 6. 리스크

| 리스크 | 대응 |
|---|---|
| Judge 출력이 불안정함 | JSON Schema 검증 및 재시도 |
| 비용/지연 증가 | 위험도 기반 선택적 평가 |
| 오탐 증가 | 샘플 데이터셋 기반 루브릭 개선 |
| 미탐 발생 | 고위험 도구 fail-closed 정책 |
| 민감정보 로그 저장 | 마스킹/해시 저장 정책 |

---

## 7. 다음 액션

- [x] `backend/schema/` 디렉터리 생성
- [x] `backend/prompts/` 디렉터리 생성
- [x] `backend/examples/` 디렉터리 생성
- [x] `backend/src/` 디렉터리 생성
- [x] 개발 언어 결정
- [x] CLI 우선 구현 여부 결정
- [x] 백엔드 API 방식으로 전환
- [x] 프론트엔드 콘솔 추가
- [x] Agent Registry 추가
