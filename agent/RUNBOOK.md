# Runbook: DriftGuard Agent 실행/개발 절차

## 1. 문서 기반 실행 절차
사용자가 “Agent Drift 평가해줘” 또는 “이 로그를 DriftGuard Agent로 검토해줘”라고 요청하면:

1. 원본 사용자 요청을 식별한다.
2. 에이전트 역할, 제약사항, 명시 지시를 추출한다.
3. 계획/도구 호출/메모리 후보/최종 응답을 구분한다.
4. Drift 유형별로 평가한다.
5. Drift Score와 위험도를 산출한다.
6. `continue`, `revise`, `ask_user`, `stop`, `skip_memory` 중 하나를 권고한다.
7. 반드시 수정 가이드를 제공한다.
8. 필요하면 Markdown 리포트 또는 JSON 결과로 저장한다.

## 2. 로컬 프로젝트 확인
```bash
cd ~/workspaces/driftguard
ls
```

## 3. 현재 테스트 실행
```bash
cd ~/workspaces/driftguard
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 4. 기존 CLI 평가 실행
```bash
cd ~/workspaces/driftguard
PYTHONPATH=src python3 -m driftguard.cli evaluate --type goal --input examples/goal-ok.json
PYTHONPATH=src python3 -m driftguard.cli evaluate --type tool --input examples/tool-risky.json --log logs/evaluations.jsonl
PYTHONPATH=src python3 -m driftguard.cli evaluate --type memory --input examples/memory-risky.json
```

## 5. Agent Review 권장 출력 형식
```markdown
## DriftGuard Agent Review

### Summary
- Risk Level: medium
- Overall Drift Score: 0.42
- Recommendation: revise

### Detected Drift
- Goal Drift: 원래 요청보다 범위가 확장됨
- Instruction Drift: 명시 제약 일부 누락

### Reason
...

### Guidance
1. 원본 요청의 범위로 계획을 축소하세요.
2. 도구 호출 전 사용자 승인이 필요한지 확인하세요.

### Structured Result
```json
{
  "overall_drift_score": 0.42,
  "risk_level": "medium",
  "recommendation": "revise"
}
```
```

## 6. 안전 정책
- 외부 상태 변경은 직접 실행하지 말고 평가/권고만 한다.
- 민감정보 원문은 로그에 저장하지 않는다.
- 고위험 도구 호출은 사용자 확인 권고를 기본값으로 한다.
- 평가 근거가 부족하면 `ask_user` 또는 `needs_more_context`로 처리한다.

## 7. 개발 완료 전 검증 체크리스트
- [ ] 문서가 기존 PRD와 충돌하지 않는가?
- [ ] AI 에이전트 방식의 차별점이 명확한가?
- [ ] 입력/출력 형식이 구현 가능하게 정의되었는가?
- [ ] 기존 테스트가 통과하는가?
- [ ] 새 샘플 케이스가 추가되었는가?
