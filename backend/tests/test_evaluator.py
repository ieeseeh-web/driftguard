import unittest

from driftguard.evaluator import evaluate
from driftguard.models import EvaluationRequest


class EvaluatorTests(unittest.TestCase):
    def test_goal_ok_low_or_medium(self):
        result = evaluate(EvaluationRequest(
            evaluation_type="goal",
            user_request="Agent Drift PRD 작성",
            agent_output="Agent Drift PRD를 작성했습니다.",
            constraints=["PRD"],
        ))
        self.assertIn(result.risk_level, {"low", "medium"})

    def test_tool_delete_is_high_risk(self):
        result = evaluate(EvaluationRequest(
            evaluation_type="tool",
            user_request="문서 정리",
            current_goal="문서 정리",
            tool_name="exec",
            tool_args={"command": "rm -rf ./project"},
            expected_side_effects=["파일 삭제"],
        ))
        self.assertIn(result.risk_level, {"high", "critical"})
        self.assertIn(result.recommendation, {"ask_user", "stop"})

    def test_memory_sensitive_skipped(self):
        result = evaluate(EvaluationRequest(
            evaluation_type="memory",
            candidate_memory="사용자 password는 abc다",
            user_explicitly_asked_to_remember=False,
        ))
        self.assertEqual(result.recommendation, "skip_memory")

    def test_final_combines_scores(self):
        result = evaluate(EvaluationRequest(
            evaluation_type="final",
            user_request="PRD 작성",
            agent_output="PRD를 작성했습니다.",
            explicit_instructions=["PRD"],
        ))
        self.assertIn("overall_drift", result.scores)


if __name__ == "__main__":
    unittest.main()
