# Agent Review Audit Logging

DriftGuard supports two JSONL logging styles for `review-agent`.

## Full result log

Use `--log` when you want the full `AgentReviewResult` object.

```bash
driftguard review-agent --input examples/agent-review-execution-log.json --log logs/agent-review-full.jsonl
```

This is useful for debugging, replay, and detailed review, but it can be too large for dashboards.

## Compact audit log

Use `--audit-log` when you want an observability-friendly summary record.

```bash
driftguard review-agent \
  --input examples/agent-review-execution-log.json \
  --audit-log logs/agent-review-audit.jsonl
```

The compact audit record is produced by `src/driftguard/audit.py` and includes stable fields for filtering and later exporter adapters.

## Audit record fields

| Field | Meaning |
|---|---|
| `event_type` | Always `agent_review.audit` |
| `schema_version` | Audit schema version |
| `review_id` | Agent review identifier |
| `timestamp` | Review timestamp |
| `session_id` / `agent_id` | Optional session/agent metadata |
| `review_type` | Review type such as `tool_call`, `execution_log`, `handoff` |
| `judge_mode` | `deterministic` or `hybrid` |
| `judge_mode_status` | Mode execution status, e.g. `completed` or `deterministic_fallback` |
| `verification_status` | `not_required`, `read_only`, `blocked`, or evidence-related status |
| `sandbox_status` | Sandbox boundary status when available |
| `risk_level` | `low`, `medium`, `high`, `critical` |
| `recommendation` | `continue`, `revise`, `ask_user`, `stop`, `skip_memory` |
| `requires_human_confirmation` | Whether human confirmation is required |
| `overall_drift_score` | Final drift score |
| `confidence` | Evaluation confidence |
| `drift_types` | Detected drift categories |
| `scores` | Component scores |
| `judge_count` | Number of judge findings |
| `evidence_count` | Number of evidence items |
| `guidance_count` | Number of guidance items |
| `top_judge` | Highest scoring judge finding |
| `latency_ms` | CLI-measured review latency |
| `request_context` | Non-sensitive request shape summary |

## Design notes

- The compact audit log avoids storing the full artifact body.
- `request_context.artifact_keys` records shape, not raw content.
- External exporters should use this audit record as their first integration target.
- Full logs are still available separately for local debugging when explicitly requested.
