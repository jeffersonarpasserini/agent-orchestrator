import unittest

from orchestrator.reserve_dashboard import render_reserve_dashboard
from orchestrator.reserve_ledger import ReserveMetricsSnapshot


class ReserveDashboardTest(unittest.TestCase):
    def test_renders_only_aggregated_and_escaped_dimensions(self):
        html = render_reserve_dashboard(ReserveMetricsSnapshot(
            total_activations=2,
            status_counts={"completed": 1, "reserve_failed": 1},
            model_counts={"<model>": 2},
            direct_cost_usd=0.02,
            prompt_cache_hit_tokens=1,
            prompt_cache_miss_tokens=2,
            completion_tokens=3,
        ))

        self.assertIn("Ativações: 2", html)
        self.assertIn("&lt;model&gt;", html)
        self.assertNotIn("<model>", html)
        for forbidden in ("task_id", "grant_id", "api_key", "prompt_text"):
            self.assertNotIn(forbidden, html)


if __name__ == "__main__":
    unittest.main()
