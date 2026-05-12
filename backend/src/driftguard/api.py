from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .agent_review import AgentReviewRequest, result_to_dict, review_agent
from .audit import append_jsonl, build_agent_review_audit_record
from .evaluator import evaluate
from .logger import append_log
from .models import EvaluationRequest

JsonDict = dict[str, Any]


def openapi_schema() -> JsonDict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "DriftGuard API",
            "version": "0.1.0",
            "description": "Agent Drift evaluation and Agent Review backend API.",
        },
        "servers": [{"url": "http://127.0.0.1:17321"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "Server health and available endpoints",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}},
                        }
                    },
                }
            },
            "/v1/evaluations": {
                "post": {
                    "summary": "Run a drift evaluation",
                    "parameters": [
                        {"$ref": "#/components/parameters/EvaluationTypeQuery"},
                        {"$ref": "#/components/parameters/LogQuery"},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EvaluationRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Evaluation result",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EvaluationResult"}}},
                        },
                        "400": {"$ref": "#/components/responses/Error"},
                        "415": {"$ref": "#/components/responses/Error"},
                    },
                }
            },
            "/v1/agent-reviews": {
                "post": {
                    "summary": "Run an Agent Review",
                    "parameters": [
                        {"$ref": "#/components/parameters/JudgeModeQuery"},
                        {"$ref": "#/components/parameters/LogQuery"},
                        {"$ref": "#/components/parameters/AuditLogQuery"},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentReviewRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Agent Review result",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentReviewResult"}}},
                        },
                        "400": {"$ref": "#/components/responses/Error"},
                        "415": {"$ref": "#/components/responses/Error"},
                    },
                }
            },
            "/v1/agents": {
                "get": {
                    "summary": "List registered runnable agents",
                    "responses": {
                        "200": {
                            "description": "Registered agent list",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentRegistryResponse"}}},
                        }
                    },
                },
                "post": {
                    "summary": "Register or update a runnable agent",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentRegistrationRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Registered agent",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentRegistrationResponse"}}},
                        },
                        "400": {"$ref": "#/components/responses/Error"},
                    },
                }
            },
            "/v1/agent-runs": {
                "post": {
                    "summary": "Run a registered agent and review it",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisteredAgentRunRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Registered agent run plus DriftGuard review",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisteredAgentRunResult"}}},
                        },
                        "400": {"$ref": "#/components/responses/Error"},
                        "500": {"$ref": "#/components/responses/Error"},
                    },
                }
            },
            "/v1/sample-agent/runs": {
                "post": {
                    "summary": "Run the bundled sample agent and review it",
                    "deprecated": True,
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SampleAgentRunRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "Sample agent run plus DriftGuard review",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SampleAgentRunResult"}}},
                        },
                        "400": {"$ref": "#/components/responses/Error"},
                        "500": {"$ref": "#/components/responses/Error"},
                    },
                }
            },
        },
        "components": {
            "parameters": {
                "EvaluationTypeQuery": {
                    "name": "type",
                    "in": "query",
                    "required": False,
                    "schema": {"$ref": "#/components/schemas/EvaluationType"},
                    "description": "Optional evaluation type when the body omits evaluation_type.",
                },
                "JudgeModeQuery": {
                    "name": "mode",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["deterministic", "hybrid"], "default": "deterministic"},
                },
                "LogQuery": {
                    "name": "log",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                    "description": "Optional JSONL log path on the server filesystem.",
                },
                "AuditLogQuery": {
                    "name": "audit_log",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                    "description": "Optional compact audit JSONL log path on the server filesystem.",
                },
            },
            "responses": {
                "Error": {
                    "description": "Error response",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                }
            },
            "schemas": {
                "EvaluationType": {
                    "type": "string",
                    "enum": ["goal", "instruction", "tool", "memory", "final"],
                },
                "RiskLevel": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "Recommendation": {
                    "type": "string",
                    "enum": ["continue", "revise", "ask_user", "stop", "store_memory", "skip_memory"],
                },
                "EvaluationRequest": {
                    "type": "object",
                    "required": ["evaluation_type"],
                    "properties": {
                        "evaluation_type": {"$ref": "#/components/schemas/EvaluationType"},
                        "user_request": {"type": "string"},
                        "agent_output": {"type": "string"},
                        "agent_plan": {"type": "string", "nullable": True},
                        "current_goal": {"type": "string", "nullable": True},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "explicit_instructions": {"type": "array", "items": {"type": "string"}},
                        "tool_name": {"type": "string", "nullable": True},
                        "tool_args": {"type": "object", "additionalProperties": True},
                        "expected_side_effects": {"type": "array", "items": {"type": "string"}},
                        "candidate_memory": {"type": "string", "nullable": True},
                        "source_message": {"type": "string", "nullable": True},
                        "existing_memories": {"type": "array", "items": {"type": "string"}},
                        "user_explicitly_asked_to_remember": {"type": "boolean"},
                        "agent_state": {"type": "object", "additionalProperties": True},
                    },
                    "example": {
                        "evaluation_type": "goal",
                        "user_request": "Agent Drift PRD 작성",
                        "agent_output": "Agent Drift PRD를 작성했습니다.",
                        "constraints": ["PRD"],
                    },
                },
                "EvaluationResult": {
                    "type": "object",
                    "required": ["evaluation_id", "timestamp", "evaluation_type", "scores", "risk_level", "recommendation", "reason"],
                    "properties": {
                        "evaluation_id": {"type": "string", "format": "uuid"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "evaluation_type": {"$ref": "#/components/schemas/EvaluationType"},
                        "scores": {"type": "object", "additionalProperties": {"type": "number"}},
                        "risk_level": {"$ref": "#/components/schemas/RiskLevel"},
                        "recommendation": {"$ref": "#/components/schemas/Recommendation"},
                        "reason": {"type": "string"},
                        "violations": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "ReviewType": {
                    "type": "string",
                    "enum": ["final_response", "tool_call", "memory_update", "plan", "handoff", "execution_log"],
                },
                "AgentReviewRequest": {
                    "type": "object",
                    "required": ["review_type", "user_request", "artifact"],
                    "properties": {
                        "review_type": {"$ref": "#/components/schemas/ReviewType"},
                        "user_request": {"type": "string"},
                        "artifact": {"type": "object", "additionalProperties": True},
                        "session_id": {"type": "string", "nullable": True},
                        "agent_id": {"type": "string", "nullable": True},
                        "agent_role": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "explicit_instructions": {"type": "array", "items": {"type": "string"}},
                        "context_summary": {"type": "string"},
                        "policy": {"type": "object", "additionalProperties": True},
                        "output_preferences": {"type": "object", "additionalProperties": True},
                    },
                    "example": {
                        "review_type": "tool_call",
                        "user_request": "README만 정리해줘",
                        "constraints": ["삭제 금지"],
                        "artifact": {
                            "current_goal": "README 정리",
                            "tool_name": "exec",
                            "tool_args": {"command": "rm -rf README.md"},
                            "expected_side_effects": ["파일 삭제"],
                        },
                    },
                },
                "AgentReviewResult": {
                    "type": "object",
                    "properties": {
                        "review_id": {"type": "string", "format": "uuid"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "review_type": {"$ref": "#/components/schemas/ReviewType"},
                        "drift_types": {"type": "array", "items": {"type": "string"}},
                        "scores": {"type": "object", "additionalProperties": {"type": "number"}},
                        "overall_drift_score": {"type": "number"},
                        "risk_level": {"$ref": "#/components/schemas/RiskLevel"},
                        "recommendation": {"type": "string"},
                        "requires_human_confirmation": {"type": "boolean"},
                        "reason": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "guidance": {"type": "array", "items": {"type": "string"}},
                        "evaluation_plan": {"type": "object", "nullable": True, "additionalProperties": True},
                        "judge_results": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "confidence": {"type": "number"},
                        "verification_status": {"type": "string"},
                        "suggested_user_confirmation_message": {"type": "string"},
                        "safe_rewrite": {"type": "string"},
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                },
                "SampleAgentRunRequest": {
                    "type": "object",
                    "properties": {
                        "scenario": {
                            "type": "string",
                            "enum": ["seoul_weekend", "short_answer_today"],
                            "default": "seoul_weekend",
                        },
                        "drift_mode": {
                            "type": "string",
                            "enum": ["none", "goal", "tool", "memory", "handoff"],
                            "default": "tool",
                        },
                        "judge_mode": {
                            "type": "string",
                            "enum": ["deterministic", "hybrid"],
                            "default": "deterministic",
                        },
                    },
                },
                "RegisteredAgentRunRequest": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "default": "sample-travel-assistant"},
                        "scenario": {"type": "string", "default": "seoul_weekend"},
                        "drift_mode": {
                            "type": "string",
                            "enum": ["none", "goal", "tool", "memory", "handoff"],
                            "default": "tool",
                        },
                        "judge_mode": {
                            "type": "string",
                            "enum": ["deterministic", "hybrid"],
                            "default": "deterministic",
                        },
                        "timeout_seconds": {"type": "number", "default": 20},
                    },
                },
                "RegisteredAgentRunResult": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "object", "additionalProperties": True},
                        "scenario": {"type": "string"},
                        "drift_mode": {"type": "string"},
                        "agent_result": {"type": "object", "additionalProperties": True},
                        "review_request": {"type": "object", "additionalProperties": True},
                        "review_result": {"$ref": "#/components/schemas/AgentReviewResult"},
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                    },
                },
                "AgentRegistryResponse": {
                    "type": "object",
                    "properties": {
                        "agents": {
                            "type": "array",
                            "items": {"type": "object", "additionalProperties": True},
                        }
                    },
                },
                "AgentRegistrationRequest": {
                    "type": "object",
                    "required": ["id", "name", "working_directory", "module", "scenarios"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "runtime": {"type": "string", "enum": ["python_module"], "default": "python_module"},
                        "working_directory": {"type": "string"},
                        "python": {"type": "string", "default": ".venv/bin/python"},
                        "module": {"type": "string"},
                        "scenarios": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "input"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "input": {"type": "string"},
                                },
                            },
                        },
                        "drift_modes": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["none", "goal", "tool", "memory", "handoff"]},
                        },
                    },
                },
                "AgentRegistrationResponse": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "object", "additionalProperties": True},
                        "created": {"type": "boolean"},
                    },
                },
                "SampleAgentRunResult": {
                    "type": "object",
                    "properties": {
                        "scenario": {"type": "string"},
                        "drift_mode": {"type": "string"},
                        "agent_result": {"type": "object", "additionalProperties": True},
                        "review_request": {"type": "object", "additionalProperties": True},
                        "review_result": {"$ref": "#/components/schemas/AgentReviewResult"},
                        "stdout": {"type": "string"},
                        "stderr": {"type": "string"},
                    },
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "service": {"type": "string"},
                        "endpoints": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "details": {"type": "object", "additionalProperties": True},
                            },
                        }
                    },
                },
            },
        },
    }


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str, details: JsonDict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: JsonDict, include_body: bool = True) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    if include_body:
        handler.wfile.write(body)


def _html_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, html: str, include_body: bool = True) -> None:
    body = html.encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    if include_body:
        handler.wfile.write(body)


def swagger_ui_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>DriftGuard API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
      body { margin: 0; background: #fafafa; }
      .topbar { display: none; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
        layout: "BaseLayout"
      });
    </script>
  </body>
</html>"""


def _read_json_body(handler: BaseHTTPRequestHandler) -> JsonDict:
    content_type = handler.headers.get("Content-Type", "")
    if content_type and "application/json" not in content_type:
        raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json")
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body is required")
    raw = handler.rfile.read(content_length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid JSON body", {"error": str(exc)}) from exc
    if not isinstance(data, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
    return data


def _first_query_value(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def handle_evaluation(data: JsonDict, query: dict[str, list[str]] | None = None) -> JsonDict:
    query = query or {}
    if "evaluation_type" not in data and "type" not in data:
        query_type = _first_query_value(query, "type")
        if query_type:
            data = {**data, "evaluation_type": query_type}
    request = EvaluationRequest.from_dict(data)
    result = evaluate(request)
    log_path = _first_query_value(query, "log") or os.environ.get("DRIFTGUARD_EVALUATION_LOG")
    if log_path:
        append_log(result, log_path)
    return asdict(result)


def handle_agent_review(data: JsonDict, query: dict[str, list[str]] | None = None) -> JsonDict:
    query = query or {}
    request = AgentReviewRequest.from_dict(data)
    mode = _first_query_value(query, "mode") or request.output_preferences.get("judge_mode", "deterministic")
    start = time.perf_counter()
    result = review_agent(request, mode=mode)
    latency_ms = int((time.perf_counter() - start) * 1000)
    result_dict = result_to_dict(result)

    log_path = _first_query_value(query, "log") or os.environ.get("DRIFTGUARD_AGENT_REVIEW_LOG")
    if log_path:
        append_jsonl(result_dict, log_path)
    audit_log_path = _first_query_value(query, "audit_log") or os.environ.get("DRIFTGUARD_AUDIT_LOG")
    if audit_log_path:
        append_jsonl(build_agent_review_audit_record(result, request, latency_ms=latency_ms), audit_log_path)
    return result_dict


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def agent_registry_path() -> Path:
    configured = os.environ.get("DRIFTGUARD_AGENT_REGISTRY")
    if configured:
        return Path(configured).expanduser()
    return backend_root() / "agents" / "registry.json"


def load_agent_registry() -> list[JsonDict]:
    registry_path = agent_registry_path()
    if not registry_path.exists():
        return []
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    agents = data.get("agents", [])
    if not isinstance(agents, list):
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "Agent registry must contain an agents list")
    return agents


def save_agent_registry(agents: list[JsonDict]) -> None:
    registry_path = agent_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"agents": agents}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def public_agent(agent: JsonDict) -> JsonDict:
    return {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "description": agent.get("description", ""),
        "runtime": agent.get("runtime", "python_module"),
        "scenarios": agent.get("scenarios", []),
        "drift_modes": agent.get("drift_modes", []),
    }


def handle_agent_list() -> JsonDict:
    return {"agents": [public_agent(agent) for agent in load_agent_registry()]}


def _validate_relative_path(value: str, field: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{field} must be a relative path inside backend")


def validate_agent_registration(data: JsonDict) -> JsonDict:
    required = ["id", "name", "working_directory", "module", "scenarios"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Missing required agent fields", {"missing": missing})

    agent_id = str(data["id"]).strip()
    name = str(data["name"]).strip()
    module = str(data["module"]).strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{1,63}", agent_id):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Agent id must be 2-64 chars using letters, numbers, dot, underscore, or dash")
    if not name:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Agent name is required")
    if not module:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Agent module is required")
    runtime = str(data.get("runtime", "python_module"))
    if runtime != "python_module":
        raise ApiError(HTTPStatus.BAD_REQUEST, "Only python_module runtime is supported")

    working_directory = str(data["working_directory"]).strip()
    python = str(data.get("python", ".venv/bin/python")).strip()
    _validate_relative_path(working_directory, "working_directory")
    _validate_relative_path(python, "python")

    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ApiError(HTTPStatus.BAD_REQUEST, "scenarios must be a non-empty list")
    normalized_scenarios: list[JsonDict] = []
    seen_scenarios: set[str] = set()
    for item in scenarios:
        if not isinstance(item, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Each scenario must be an object")
        scenario_id = str(item.get("id", "")).strip()
        scenario_input = str(item.get("input", "")).strip()
        if not scenario_id or not scenario_input:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Each scenario requires id and input")
        if scenario_id in seen_scenarios:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Scenario ids must be unique", {"scenario": scenario_id})
        _validate_relative_path(scenario_input, "scenario input")
        seen_scenarios.add(scenario_id)
        normalized_scenarios.append({
            "id": scenario_id,
            "label": str(item.get("label") or scenario_id),
            "input": scenario_input,
        })

    allowed_drift_modes = {"none", "goal", "tool", "memory", "handoff"}
    drift_modes = data.get("drift_modes") or ["none", "goal", "tool", "memory", "handoff"]
    if not isinstance(drift_modes, list) or not drift_modes:
        raise ApiError(HTTPStatus.BAD_REQUEST, "drift_modes must be a non-empty list")
    invalid_modes = [mode for mode in drift_modes if mode not in allowed_drift_modes]
    if invalid_modes:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Unsupported drift_modes", {"invalid": invalid_modes})

    return {
        "id": agent_id,
        "name": name,
        "description": str(data.get("description", "")).strip(),
        "runtime": runtime,
        "working_directory": working_directory,
        "python": python,
        "module": module,
        "scenarios": normalized_scenarios,
        "drift_modes": list(dict.fromkeys(str(mode) for mode in drift_modes)),
    }


def handle_agent_registration(data: JsonDict) -> JsonDict:
    agent = validate_agent_registration(data)
    agents = load_agent_registry()
    created = True
    for idx, existing in enumerate(agents):
        if existing.get("id") == agent["id"]:
            agents[idx] = agent
            created = False
            break
    if created:
        agents.append(agent)
    save_agent_registry(agents)
    return {"agent": public_agent(agent), "created": created}


def _find_agent(agent_id: str) -> JsonDict:
    for agent in load_agent_registry():
        if agent.get("id") == agent_id:
            return agent
    raise ApiError(HTTPStatus.BAD_REQUEST, "Unknown agent_id", {"agent_id": agent_id})


def _find_scenario(agent: JsonDict, scenario_id: str) -> JsonDict:
    for scenario in agent.get("scenarios", []):
        if scenario.get("id") == scenario_id:
            return scenario
    raise ApiError(HTTPStatus.BAD_REQUEST, "Unsupported scenario for agent", {
        "agent_id": agent.get("id"),
        "scenario": scenario_id,
    })


def handle_registered_agent_run(data: JsonDict) -> JsonDict:
    drift_modes = {"none", "goal", "tool", "memory", "handoff"}
    judge_modes = {"deterministic", "hybrid"}

    agent_id = str(data.get("agent_id", "sample-travel-assistant"))
    agent = _find_agent(agent_id)
    scenario = str(data.get("scenario", "seoul_weekend"))
    drift_mode = str(data.get("drift_mode", "tool"))
    judge_mode = str(data.get("judge_mode", "deterministic"))
    timeout_seconds = float(data.get("timeout_seconds", 20))
    scenario_config = _find_scenario(agent, scenario)

    if drift_mode not in drift_modes:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Unsupported drift_mode", {"drift_mode": drift_mode})
    if drift_mode not in set(agent.get("drift_modes", [])):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Drift mode is not supported by this agent", {
            "agent_id": agent_id,
            "drift_mode": drift_mode,
        })
    if judge_mode not in judge_modes:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Unsupported judge_mode", {"judge_mode": judge_mode})
    if agent.get("runtime", "python_module") != "python_module":
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "Unsupported agent runtime", {
            "agent_id": agent_id,
            "runtime": agent.get("runtime"),
        })

    root = backend_root()
    agent_root = (root / str(agent.get("working_directory", ""))).resolve()
    try:
        agent_root.relative_to(root)
    except ValueError as exc:
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "Agent working_directory must stay inside backend", {
            "agent_id": agent_id,
            "working_directory": str(agent_root),
        }) from exc
    scenario_path = (agent_root / str(scenario_config.get("input", ""))).resolve()
    try:
        scenario_path.relative_to(agent_root)
    except ValueError as exc:
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "Scenario input must stay inside agent directory", {
            "agent_id": agent_id,
            "scenario": scenario,
        }) from exc
    if not scenario_path.exists():
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "Sample scenario file is missing", {"path": str(scenario_path)})

    python_bin = agent_root / str(agent.get("python", ".venv/bin/python"))
    python = str(python_bin if python_bin.exists() else Path(sys.executable))

    with tempfile.TemporaryDirectory(prefix="driftguard-sample-agent-") as tmp:
        tmp_path = Path(tmp)
        agent_output = tmp_path / "agent_result.json"
        review_output = tmp_path / "review_request.json"
        cmd = [
            python,
            "-m",
            str(agent.get("module")),
            "--input",
            str(scenario_path),
            "--drift-mode",
            drift_mode,
            "--output",
            str(agent_output),
            "--review-output",
            str(review_output),
        ]
        try:
            completed = subprocess.run(
                cmd,
                cwd=agent_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ApiError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Sample agent execution timed out",
                {"timeout_seconds": timeout_seconds, "stdout": exc.stdout, "stderr": exc.stderr},
            ) from exc
        if completed.returncode != 0:
            raise ApiError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Sample agent execution failed",
                {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "command": cmd,
                },
            )
        agent_result = json.loads(agent_output.read_text(encoding="utf-8"))
        review_request = json.loads(review_output.read_text(encoding="utf-8"))

    request_obj = AgentReviewRequest.from_dict(review_request)
    review_result = review_agent(request_obj, mode=judge_mode)
    return {
        "agent": public_agent(agent),
        "scenario": scenario,
        "drift_mode": drift_mode,
        "judge_mode": judge_mode,
        "agent_result": agent_result,
        "review_request": review_request,
        "review_result": result_to_dict(review_result),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def handle_sample_agent_run(data: JsonDict) -> JsonDict:
    return handle_registered_agent_run({"agent_id": "sample-travel-assistant", **data})


class DriftGuardRequestHandler(BaseHTTPRequestHandler):
    server_version = "DriftGuardAPI/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        self._handle_get(include_body=True)

    def do_HEAD(self) -> None:
        self._handle_get(include_body=False)

    def _handle_get(self, include_body: bool) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/health":
            _json_response(self, HTTPStatus.OK, {
                "status": "ok",
                "service": "driftguard",
                "endpoints": [
                    "GET /health",
                    "GET /docs",
                    "GET /openapi.json",
                    "GET /v1/agents",
                    "POST /v1/agents",
                    "POST /v1/agent-runs",
                    "POST /v1/evaluations",
                    "POST /v1/agent-reviews",
                    "POST /v1/sample-agent/runs",
                ],
            }, include_body=include_body)
            return
        if parsed.path == "/openapi.json":
            _json_response(self, HTTPStatus.OK, openapi_schema(), include_body=include_body)
            return
        if parsed.path == "/docs":
            _html_response(self, HTTPStatus.OK, swagger_ui_html(), include_body=include_body)
            return
        if parsed.path == "/v1/agents":
            _json_response(self, HTTPStatus.OK, handle_agent_list(), include_body=include_body)
            return
        self._send_error(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {parsed.path}")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            data = _read_json_body(self)
            if parsed.path == "/v1/evaluations":
                _json_response(self, HTTPStatus.OK, handle_evaluation(data, query))
                return
            if parsed.path == "/v1/agent-reviews":
                _json_response(self, HTTPStatus.OK, handle_agent_review(data, query))
                return
            if parsed.path == "/v1/sample-agent/runs":
                _json_response(self, HTTPStatus.OK, handle_sample_agent_run(data))
                return
            if parsed.path == "/v1/agent-runs":
                _json_response(self, HTTPStatus.OK, handle_registered_agent_run(data))
                return
            if parsed.path == "/v1/agents":
                _json_response(self, HTTPStatus.OK, handle_agent_registration(data))
                return
            raise ApiError(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {parsed.path}")
        except ApiError as exc:
            self._send_error(exc.status, exc.message, exc.details)
        except (TypeError, ValueError) as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, "Invalid request payload", {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        # Keep default server logs concise and JSON API responses uncluttered.
        if os.environ.get("DRIFTGUARD_API_ACCESS_LOG") == "1":
            super().log_message(format, *args)

    def _send_error(self, status: HTTPStatus, message: str, details: JsonDict | None = None) -> None:
        _json_response(self, status, {
            "error": {
                "code": status.name.lower(),
                "message": message,
                "details": details or {},
            }
        })


DEFAULT_API_PORT = 17321


def create_server(host: str = "127.0.0.1", port: int = DEFAULT_API_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), DriftGuardRequestHandler)


def run_server(host: str = "127.0.0.1", port: int = DEFAULT_API_PORT) -> None:
    server = create_server(host, port)
    print(f"DriftGuard API listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down DriftGuard API.", flush=True)
    finally:
        server.server_close()


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
