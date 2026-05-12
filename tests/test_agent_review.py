import unittest

from driftguard.agent_review import AgentReviewRequest, result_to_markdown, review_agent


class AgentReviewTests(unittest.TestCase):
    def test_tool_call_requires_confirmation(self):
        result = review_agent(AgentReviewRequest.from_dict({
            "review_type": "tool_call",
            "user_request": "문서를 정리하되 삭제하지 마",
            "constraints": ["삭제 금지"],
            "explicit_instructions": ["삭제하지 마"],
            "artifact": {
                "current_goal": "문서 정리",
                "tool_name": "exec",
                "tool_args": {"command": "rm -rf docs/old"},
                "expected_side_effects": ["파일 삭제"],
            },
        }))
        self.assertTrue(result.requires_human_confirmation)
        self.assertIn(result.recommendation, {"ask_user", "stop"})
        self.assertIn("tool", result.drift_types)

    def test_memory_update_skipped(self):
        result = review_agent(AgentReviewRequest.from_dict({
            "review_type": "memory_update",
            "user_request": "오늘은 짧게 답해줘",
            "artifact": {
                "candidate_memory": "사용자는 항상 짧은 답변만 선호한다.",
                "source_message": "오늘은 짧게 답해줘",
                "existing_memories": [],
            },
        }))
        self.assertEqual(result.recommendation, "skip_memory")
        self.assertIn("memory", result.drift_types)

    def test_markdown_contains_structured_result(self):
        result = review_agent(AgentReviewRequest.from_dict({
            "review_type": "final_response",
            "user_request": "PRD 작성",
            "constraints": ["PRD"],
            "artifact": {"agent_output": "PRD를 작성했습니다."},
        }))
        markdown = result_to_markdown(result)
        self.assertIn("DriftGuard Agent Review", markdown)
        self.assertIn("Structured Result", markdown)


if __name__ == "__main__":
    unittest.main()
