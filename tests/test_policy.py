import unittest

from driftguard.policy import recommendation, risk_level, weighted_drift_score


class PolicyTests(unittest.TestCase):
    def test_risk_level_thresholds(self):
        self.assertEqual(risk_level(0.1), "low")
        self.assertEqual(risk_level(0.3), "medium")
        self.assertEqual(risk_level(0.6), "high")
        self.assertEqual(risk_level(0.9), "critical")

    def test_recommendation_thresholds(self):
        self.assertEqual(recommendation(0.1, evaluation_type="goal"), "continue")
        self.assertEqual(recommendation(0.3, evaluation_type="goal"), "revise")
        self.assertEqual(recommendation(0.6, evaluation_type="goal"), "ask_user")
        self.assertEqual(recommendation(0.9, evaluation_type="goal"), "stop")

    def test_memory_recommendation(self):
        self.assertEqual(recommendation(0.2, evaluation_type="memory"), "store_memory")
        self.assertEqual(recommendation(0.5, evaluation_type="memory"), "skip_memory")

    def test_weighted_score(self):
        score = weighted_drift_score({"goal_alignment_risk": 0.2, "tool_risk": 0.8})
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
