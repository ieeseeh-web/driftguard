import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from driftguard.api import create_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.host, cls.port = cls.server.server_address
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, payload=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, data

    def request_raw(self, method, path):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
        conn.close()
        return response.status, content_type, body

    def test_health(self):
        status, data = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("POST /v1/evaluations", data["endpoints"])
        self.assertIn("GET /docs", data["endpoints"])
        self.assertIn("GET /v1/agents", data["endpoints"])
        self.assertIn("POST /v1/agents", data["endpoints"])
        self.assertIn("POST /v1/agent-runs", data["endpoints"])

    def test_openapi_schema(self):
        status, data = self.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(data["openapi"], "3.0.3")
        self.assertIn("/v1/evaluations", data["paths"])
        self.assertIn("/v1/agent-reviews", data["paths"])
        self.assertIn("/v1/agents", data["paths"])
        self.assertIn("/v1/agent-runs", data["paths"])
        self.assertIn("/v1/sample-agent/runs", data["paths"])

    def test_agent_registry_endpoint(self):
        status, data = self.request("GET", "/v1/agents")
        self.assertEqual(status, 200)
        self.assertTrue(data["agents"])
        self.assertEqual(data["agents"][0]["id"], "sample-travel-assistant")

    def test_agent_registration_creates_agent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_registry = os.environ.get("DRIFTGUARD_AGENT_REGISTRY")
            os.environ["DRIFTGUARD_AGENT_REGISTRY"] = str(Path(tmp_dir) / "registry.json")
            try:
                payload = {
                    "id": "custom-agent",
                    "name": "Custom Agent",
                    "runtime": "python_module",
                    "working_directory": "sample_agent",
                    "python": ".venv/bin/python",
                    "module": "sample_agent.travel_agent",
                    "scenarios": [
                        {"id": "demo", "label": "Demo", "input": "scenarios/seoul_weekend.json"}
                    ],
                    "drift_modes": ["none", "tool"],
                }
                status, data = self.request("POST", "/v1/agents", payload)
                self.assertEqual(status, 200)
                self.assertTrue(data["created"])
                self.assertEqual(data["agent"]["id"], "custom-agent")

                status, data = self.request("GET", "/v1/agents")
                self.assertEqual(status, 200)
                self.assertEqual(len(data["agents"]), 1)
                self.assertEqual(data["agents"][0]["name"], "Custom Agent")
            finally:
                if previous_registry is None:
                    os.environ.pop("DRIFTGUARD_AGENT_REGISTRY", None)
                else:
                    os.environ["DRIFTGUARD_AGENT_REGISTRY"] = previous_registry

    def test_agent_registration_rejects_parent_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_registry = os.environ.get("DRIFTGUARD_AGENT_REGISTRY")
            os.environ["DRIFTGUARD_AGENT_REGISTRY"] = str(Path(tmp_dir) / "registry.json")
            try:
                status, data = self.request("POST", "/v1/agents", {
                    "id": "unsafe-agent",
                    "name": "Unsafe Agent",
                    "runtime": "python_module",
                    "working_directory": "../outside",
                    "module": "sample_agent.travel_agent",
                    "scenarios": [
                        {"id": "demo", "input": "scenarios/seoul_weekend.json"}
                    ],
                })
                self.assertEqual(status, 400)
                self.assertEqual(data["error"]["code"], "bad_request")
            finally:
                if previous_registry is None:
                    os.environ.pop("DRIFTGUARD_AGENT_REGISTRY", None)
                else:
                    os.environ["DRIFTGUARD_AGENT_REGISTRY"] = previous_registry

    def test_swagger_docs_html(self):
        status, content_type, body = self.request_raw("GET", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("SwaggerUIBundle", body)
        self.assertIn("/openapi.json", body)

    def test_swagger_docs_head(self):
        status, content_type, body = self.request_raw("HEAD", "/docs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertEqual(body, "")

    def test_evaluation_endpoint(self):
        status, data = self.request("POST", "/v1/evaluations", {
            "evaluation_type": "tool",
            "user_request": "문서를 정리해줘",
            "current_goal": "문서 정리",
            "tool_name": "exec",
            "tool_args": {"command": "rm -rf docs"},
            "expected_side_effects": ["파일 삭제"],
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["evaluation_type"], "tool")
        self.assertIn(data["recommendation"], {"ask_user", "stop"})

    def test_agent_review_endpoint(self):
        status, data = self.request("POST", "/v1/agent-reviews?mode=deterministic", {
            "review_type": "tool_call",
            "user_request": "README만 정리해줘",
            "constraints": ["삭제 금지"],
            "artifact": {
                "current_goal": "README 정리",
                "tool_name": "exec",
                "tool_args": {"command": "rm -rf README.md"},
                "expected_side_effects": ["파일 삭제"],
            },
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["review_type"], "tool_call")
        self.assertTrue(data["requires_human_confirmation"])
        self.assertIn("tool", data["drift_types"])

    def test_invalid_json_returns_400(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        conn.request("POST", "/v1/evaluations", body=b"{", headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        conn.close()
        self.assertEqual(response.status, 400)
        self.assertIn("error", data)

    def test_sample_agent_invalid_scenario_returns_400(self):
        status, data = self.request("POST", "/v1/sample-agent/runs", {
            "scenario": "unknown",
            "drift_mode": "tool",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["code"], "bad_request")

    def test_registered_agent_unknown_agent_returns_400(self):
        status, data = self.request("POST", "/v1/agent-runs", {
            "agent_id": "missing-agent",
            "scenario": "seoul_weekend",
            "drift_mode": "tool",
        })
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["code"], "bad_request")


if __name__ == "__main__":
    unittest.main()
