import http.client
import json
import threading
import unittest

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

    def test_openapi_schema(self):
        status, data = self.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(data["openapi"], "3.0.3")
        self.assertIn("/v1/evaluations", data["paths"])
        self.assertIn("/v1/agent-reviews", data["paths"])
        self.assertIn("/v1/sample-agent/runs", data["paths"])

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


if __name__ == "__main__":
    unittest.main()
