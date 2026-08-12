from datetime import datetime, timezone
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from orchestrator.api.app import create_app
from orchestrator.budget import (
    BudgetEvidenceError,
    BudgetExceededError,
    BudgetSnapshot,
)
from orchestrator.pilot_metrics import PilotTaskMetrics
from orchestrator.settings import Settings


class FakeBudgetGuard:
    daily_limit_usd = 1.0
    pilot_limit_usd = 10.0

    def snapshot(self):
        return BudgetSnapshot(.25, .5)

    def check(self, profile):
        if profile == "tuvok":
            raise BudgetExceededError(
                "DeepSeek daily budget exhausted for profile 'tuvok'"
            )
        return None


class FakeMetricsStore:
    def list_all(self):
        return (
            PilotTaskMetrics("O01", "operation", "approved", (), 1, 2, 3.0, .01, ()),
        )


class UnavailableBudgetGuard(FakeBudgetGuard):
    def snapshot(self):
        raise BudgetEvidenceError("cannot read /private/path/state.db")


class ApiAppTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            environment="test",
            database_url="postgresql://unused",
            otlp_endpoint="http://unused",
            service_name="test",
            hermes_profiles_root=Path("/unused"),
            deepseek_daily_budget_usd=1.0,
            deepseek_pilot_budget_usd=10.0,
            deepseek_pilot_started_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        )
        app = create_app(
            self.settings,
            budget_guard=FakeBudgetGuard(),
            metrics_store=FakeMetricsStore(),
            database_checker=lambda _: {"database": "test", "user": "test"},
        )
        self.client = TestClient(app)

    def test_exposes_budget_without_credentials(self):
        response = self.client.get("/pilot/budget")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "daily_spend_usd": .25,
                "pilot_spend_usd": .5,
                "daily_limit_usd": 1.0,
                "pilot_limit_usd": 10.0,
            },
        )
        self.assertNotIn("database_url", response.text)

    def test_budget_evidence_error_returns_generic_503(self):
        app = create_app(
            self.settings,
            budget_guard=UnavailableBudgetGuard(),
            metrics_store=FakeMetricsStore(),
            database_checker=lambda _: {"database": "test", "user": "test"},
        )

        response = TestClient(app).get("/pilot/budget")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "budget evidence unavailable"})
        self.assertNotIn("/private/path", response.text)

    def test_exposes_budget_blocked_state(self):
        response = self.client.get("/pilot/budget/check/tuvok")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "budget_blocked")
        self.assertIn("profile 'tuvok'", response.json()["error"])

    def test_exposes_pilot_summary(self):
        response = self.client.get("/pilot/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recorded_tasks"], 1)
        self.assertEqual(response.json()["api_calls"], 2)
        self.assertEqual(response.json()["simulated_cost_usd"], .01)
        self.assertEqual(response.json()["billed_cost_usd"], .01)
        self.assertEqual(response.json()["subscription_savings_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
