# Sandbox Verification Policy

DriftGuard의 Agent-as-a-Judge 확장은 도구 기반 검증을 목표로 하지만, 현재 구현은 **코드 실행을 하지 않는 fail-closed 안전 경계**를 먼저 제공한다.

## 원칙

1. 기본 검증은 read-only artifact analysis다.
2. Python/code execution은 sandbox 구현 전까지 실행하지 않는다.
3. 네트워크, API 호출, 브라우저 자동화, DB mutation은 기본 차단한다.
4. 실행형 verifier는 명시적 사용자 opt-in, 격리, quota, audit log가 갖춰진 뒤에만 도입한다.
5. 차단은 실패가 아니라 안전한 평가 결과로 기록한다.

## 현재 구현

- 구현 파일: `src/driftguard/verifier.py`
- 통합 지점: `src/driftguard/agent_review.py`
- 결과 위치:
  - `verification_status`
  - `metadata.sandbox_verification`
  - safety evidence

`python_executor`, `exec`, `shell`, `api_caller`, `browser_agent`, `sql_runner` 등 실행형/외부 영향 가능 도구는 현재 `blocked`로 분류된다.

## Required Controls

실행형 verifier를 실제로 활성화하려면 최소한 다음 통제가 필요하다.

- container 또는 microVM isolation
- network disabled by default
- read-only filesystem
- CPU/memory/timeout quota
- explicit user opt-in
- audit log

## 상태값

| status | 의미 |
|---|---|
| `not_required` | 실행형 verifier가 필요하지 않음 |
| `read_only` | 로컬 artifact/read-only 분석만 수행 |
| `blocked` | sandbox 전제 조건이 없어 실행형 검증 차단 |

## 다음 단계

1. read-only file verifier 추가
2. local JSON/log verifier 추가
3. sandbox runner 설계 구체화
4. explicit flag 기반 Python executor PoC 검토
