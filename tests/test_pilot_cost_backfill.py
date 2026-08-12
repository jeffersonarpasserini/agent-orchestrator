from pathlib import Path
import sqlite3
import tempfile
import unittest

from orchestrator.pilot_cost_backfill import calculate_evidence_costs, with_recalculated_costs
from orchestrator.pilot_metrics import PilotTaskMetrics


class PilotCostBackfillTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        profile = self.root / "spock"
        profile.mkdir()
        with sqlite3.connect(profile / "state.db") as connection:
            connection.execute("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY, model TEXT, billing_provider TEXT,
                    billing_mode TEXT, input_tokens INTEGER, output_tokens INTEGER,
                    cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                    reasoning_tokens INTEGER
                )
            """)
            connection.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?)",
                ("20260812_120000_abcdef", "gpt-5.6-luna", "openai-codex",
                 "subscription_included", 1_000_000, 1_000_000, 0, 0, 500_000),
            )

    def tearDown(self):
        self.temporary.cleanup()

    def test_recalculates_task_without_double_counting_reasoning(self):
        metrics = PilotTaskMetrics(
            "T01", "test", "approved", ("spock/luna",), 1, 1, 1.0, 0.0,
            ("20260812_120000_abcdef", "cost_scope:ledger"),
        )
        updated = with_recalculated_costs(metrics, self.root)
        self.assertEqual(updated.simulated_cost_usd, 1.4)
        self.assertEqual(updated.billed_cost_usd, 0.0)
        self.assertEqual(updated.cost_usd, 0.0)

    def test_missing_session_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "evidence unavailable"):
            calculate_evidence_costs(self.root, ("20260812_120001_deadbeef",))


if __name__ == "__main__":
    unittest.main()
