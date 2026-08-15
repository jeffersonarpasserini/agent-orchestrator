from datetime import datetime, timezone
from pathlib import Path
import unittest

from fastapi import HTTPException

from orchestrator.api.app import create_app
from orchestrator.budget import (
    BudgetEvidenceError,
    BudgetExceededError,
    BudgetSnapshot,
)
from orchestrator.pilot_metrics import PilotTaskMetrics
from orchestrator.reserve_ledger import ReserveMetricsSnapshot
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


class FakeReserveLedger:
    def metrics_snapshot(self):
        return ReserveMetricsSnapshot(
            total_activations=2,
            status_counts={"completed": 1, "reserve_outcome_unknown": 1},
            model_counts={"deepseek-v4-flash": 2},
            direct_cost_usd=0.02,
            prompt_cache_hit_tokens=1,
            prompt_cache_miss_tokens=2,
            completion_tokens=3,
        )


def route_endpoint(app, path: str):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)


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
            reserve_ledger=FakeReserveLedger(),
            database_checker=lambda _: {"database": "test", "user": "test"},
        )
        self.app = app

    def test_exposes_team_policy_without_dispatching_agents(self):
        agents = route_endpoint(self.app, "/team/agents")()
        workflows = route_endpoint(self.app, "/team/workflows")()

        profiles = {agent["profile"] for agent in agents["agents"]}
        self.assertTrue({"alfred", "spock", "b-elanna", "seven", "troi", "la-forge"} <= profiles)
        self.assertEqual(
            [step["profile"] for step in workflows["spec_review"]],
            ["seven", "troi", "b-elanna", "spock"],
        )
        self.assertFalse(workflows["dispatches_agents"])

    def test_exposes_budget_without_credentials(self):
        response = route_endpoint(self.app, "/pilot/budget")()

        self.assertEqual(
            response,
            {
                "daily_spend_usd": .25,
                "pilot_spend_usd": .5,
                "daily_limit_usd": 1.0,
                "pilot_limit_usd": 10.0,
            },
        )
        self.assertNotIn("database_url", str(response))

    def test_budget_evidence_error_returns_generic_503(self):
        app = create_app(
            self.settings,
            budget_guard=UnavailableBudgetGuard(),
            metrics_store=FakeMetricsStore(),
            database_checker=lambda _: {"database": "test", "user": "test"},
        )

        with self.assertRaises(HTTPException) as raised:
            route_endpoint(app, "/pilot/budget")()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "budget evidence unavailable")
        self.assertNotIn("/private/path", str(raised.exception.detail))

    def test_exposes_budget_blocked_state(self):
        response = route_endpoint(self.app, "/pilot/budget/check/{profile}")("tuvok")

        self.assertEqual(response["status"], "budget_blocked")
        self.assertIn("profile 'tuvok'", response["error"])

    def test_exposes_pilot_summary(self):
        response = route_endpoint(self.app, "/pilot/summary")()

        self.assertEqual(response["recorded_tasks"], 1)
        self.assertEqual(response["api_calls"], 2)
        self.assertEqual(response["simulated_cost_usd"], .01)
        self.assertEqual(response["billed_cost_usd"], .01)
        self.assertEqual(response["subscription_savings_usd"], 0.0)

    def test_exposes_only_aggregated_reserve_metrics(self):
        route = next(
            route for route in self.app.routes
            if getattr(route, "path", None) == "/reserve/metrics"
        )

        payload = route.endpoint()

        self.assertEqual(payload["billing_route"], "deepseek_reserve")
        self.assertEqual(payload["total_activations"], 2)
        self.assertTrue(payload["alert_required"])
        serialized = str(payload)
        self.assertNotIn("task_id", serialized)
        self.assertNotIn("grant_id", serialized)
        self.assertNotIn("prompt_text", serialized)
        self.assertNotIn("api_key", serialized)


if __name__ == "__main__":
    unittest.main()
