from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

VerificationStatus = Literal["not_required", "read_only", "blocked"]


@dataclass
class VerificationPolicy:
    """Fail-closed policy for future tool verification.

    DriftGuard does not execute candidate code or external actions yet. This
    policy records the controls required before such verifiers can be enabled.
    """

    allow_code_execution: bool = False
    allow_network: bool = False
    filesystem_mode: str = "read_only"
    timeout_ms: int = 5000
    resource_quota: dict[str, Any] = field(default_factory=lambda: {
        "cpu_seconds": 2,
        "memory_mb": 128,
        "max_output_bytes": 20000,
    })


@dataclass
class SandboxVerificationResult:
    status: VerificationStatus
    reason: str
    verifier: str = "sandbox_boundary"
    required_controls: list[str] = field(default_factory=list)
    policy: VerificationPolicy = field(default_factory=VerificationPolicy)


_CODE_EXECUTION_TOOL_NAMES = {
    "exec",
    "shell",
    "bash",
    "sh",
    "terminal",
    "python",
    "python_executor",
    "subprocess",
    "code_runner",
    "sql_runner",
    "api_caller",
    "browser_agent",
}

_CODE_EXECUTION_KEYWORDS = [
    "python -c",
    "python3 -c",
    "subprocess",
    "os.system",
    "eval(",
    "exec(",
    "curl ",
    "wget ",
    "rm ",
    "rm-",
    "rm -",
    "drop table",
    "truncate table",
]

_READ_ONLY_TOOL_NAMES = {
    "read",
    "file_reader",
    "log_analyzer",
    "json_reader",
    "grep",
    "cat",
}


def assess_verification_boundary(review_type: str, artifact: dict[str, Any], policy: VerificationPolicy | None = None) -> SandboxVerificationResult:
    """Assess whether a requested verification would cross the safe sandbox boundary.

    This function is intentionally non-executing. It only classifies whether a
    verifier would be safe as read-only, not needed, or blocked until sandbox
    controls exist.
    """

    policy = policy or VerificationPolicy()
    tool_name = str(artifact.get("tool_name") or "").lower()
    tool_args_blob = json.dumps(artifact.get("tool_args") or {}, ensure_ascii=False).lower()
    side_effects_blob = " ".join(artifact.get("expected_side_effects") or []).lower()
    combined = f"{tool_name} {tool_args_blob} {side_effects_blob}"

    code_or_external = (
        tool_name in _CODE_EXECUTION_TOOL_NAMES
        or any(keyword in combined for keyword in _CODE_EXECUTION_KEYWORDS)
        or "network" in side_effects_blob
        or "api" in side_effects_blob
    )

    if code_or_external:
        return SandboxVerificationResult(
            status="blocked",
            reason="Verification would require code execution, network access, or external side effects; sandbox controls are required before execution.",
            required_controls=[
                "container_or_microvm_isolation",
                "network_disabled_by_default",
                "read_only_filesystem",
                "cpu_memory_timeout_quotas",
                "explicit_user_opt_in",
                "audit_log",
            ],
            policy=policy,
        )

    if tool_name in _READ_ONLY_TOOL_NAMES or review_type in {"execution_log", "handoff", "memory_update", "final_response", "plan"}:
        return SandboxVerificationResult(
            status="read_only",
            reason="Only read-only/local artifact analysis is required for this review.",
            required_controls=["no_external_side_effects", "audit_log"],
            policy=policy,
        )

    return SandboxVerificationResult(
        status="not_required",
        reason="No executable verifier is required for this review.",
        required_controls=[],
        policy=policy,
    )
