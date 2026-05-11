# Memory Risk Judge Prompt

Evaluate whether a candidate memory should be stored long-term.
Return strict JSON with: memory_risk_score, should_store, sensitivity, ttl_recommendation, reason.
Reject sensitive, temporary, speculative, duplicate, or over-generalized memories.
