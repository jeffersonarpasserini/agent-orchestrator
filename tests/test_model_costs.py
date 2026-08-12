import unittest

from orchestrator.model_costs import CostEstimateStatus, ModelCostEstimator, ModelUsage


class ModelCostEstimatorTest(unittest.TestCase):
    def test_openai_subscription_has_simulated_cost_and_zero_billed(self):
        result = ModelCostEstimator().estimate(
            "gpt-5.6-sol", ModelUsage(1_000_000, 100_000),
            billing_provider="openai-codex", billing_mode="subscription_included",
        )
        self.assertEqual(result.simulated_cost_usd, 8.0)
        self.assertEqual(result.billed_cost_usd, 0.0)
        self.assertEqual(result.subscription_savings_usd, 8.0)
        self.assertEqual(result.status, CostEstimateStatus.OFFICIAL)

    def test_qwen_subscription_uses_declared_openrouter_proxy(self):
        result = ModelCostEstimator().estimate(
            "qwen3.8-max", ModelUsage(1_000_000, 1_000_000, 100_000),
            billing_provider="alibaba-coding-plan", billing_mode=None,
        )
        self.assertEqual(result.simulated_cost_usd, 8.2)
        self.assertEqual(result.billed_cost_usd, 0.0)
        self.assertEqual(result.pricing_model, "qwen/qwen3.8-2.4t-a95b")
        self.assertEqual(result.status, CostEstimateStatus.PROXY)

    def test_pay_per_token_has_equal_simulated_and_billed_cost(self):
        result = ModelCostEstimator().estimate(
            "deepseek-v4-flash", ModelUsage(1_000_000, 1_000_000),
            billing_provider="deepseek", billing_mode="pay_per_token",
        )
        self.assertEqual(result.simulated_cost_usd, 0.42)
        self.assertEqual(result.billed_cost_usd, result.simulated_cost_usd)

    def test_reasoning_is_not_added_on_top_of_output(self):
        result = ModelCostEstimator().estimate_session({
            "model": "gpt-5.6-luna", "billing_provider": "openai-codex",
            "billing_mode": "subscription_included", "input_tokens": 0,
            "output_tokens": 1_000_000, "reasoning_tokens": 900_000,
        })
        self.assertEqual(result.simulated_cost_usd, 1.2)

    def test_unknown_model_is_not_silently_treated_as_free(self):
        with self.assertRaisesRegex(ValueError, "price is not configured"):
            ModelCostEstimator().estimate(
                "unknown", ModelUsage(1, 1), billing_provider="subscription",
                billing_mode="subscription_included",
            )


if __name__ == "__main__":
    unittest.main()
