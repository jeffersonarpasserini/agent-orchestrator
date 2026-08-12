from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.pilot_metrics import PilotTaskMetrics, PostgresPilotMetricsStore
from orchestrator.pilot_summary import summarize_pilot


class PilotTaskMetricsTest(unittest.TestCase):
    def test_rejects_negative_aggregates(self):
        with self.assertRaisesRegex(ValueError, "latency and cost"):
            PilotTaskMetrics(
                "F02", "feature", "approved", (), 1, 0, -0.1, 0.0, ()
            )

    @patch("orchestrator.pilot_metrics.psycopg.connect")
    def test_records_aggregates_without_credentials_in_payload(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        metrics = PilotTaskMetrics(
            task_id="F02",
            task_class="feature",
            result="approved",
            profiles_models=("spock/sol", "tuvok/deepseek-pro"),
            attempts=1,
            api_calls=2,
            latency_seconds=12.5,
            cost_usd=0.01,
            evidence=("session-1", "session-2"),
        )

        PostgresPilotMetricsStore("postgresql://private").record(metrics)

        connect.assert_called_once_with("postgresql://private")
        statement, parameters = cursor.execute.call_args.args
        normalized_statement = " ".join(statement.split())
        self.assertIn("ON CONFLICT (task_id) DO UPDATE SET", normalized_statement)
        self.assertIn("attempts = EXCLUDED.attempts", normalized_statement)
        self.assertIn("evidence = EXCLUDED.evidence", normalized_statement)
        self.assertIn("simulated_cost_usd = EXCLUDED.simulated_cost_usd", normalized_statement)
        self.assertEqual(parameters[0:3], ("F02", "feature", "approved"))
        self.assertNotIn("postgresql://private", parameters)
        connection.commit.assert_called_once_with()

    def test_summarizes_and_renders_local_ledger(self):
        entries = (
            PilotTaskMetrics("O01", "operation", "approved", (), 1, 2, 4.5, .01, ()),
            PilotTaskMetrics("O02", "operation", "approved", (), 2, 1, 5.5, .02, ()),
        )

        summary = summarize_pilot(entries)

        self.assertEqual(summary.recorded_tasks, 2)
        self.assertEqual(summary.first_attempt_tasks, 1)
        self.assertEqual(summary.api_calls, 3)
        self.assertAlmostEqual(summary.cost_usd, .03)
        self.assertAlmostEqual(summary.simulated_cost_usd, .03)
        self.assertAlmostEqual(summary.billed_cost_usd, .03)
        rendered = summary.to_markdown()
        self.assertIn("| Tarefas registradas | 2/20 |", rendered)
        self.assertIn("| Conclusão | 10.0% |", rendered)
        self.assertIn("| Custo simulado | US$ 0.030000000 |", rendered)
        self.assertIn("| Custo cobrado | US$ 0.030000000 |", rendered)

    @patch("orchestrator.pilot_metrics.psycopg.connect")
    def test_reads_metrics_for_local_summary(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("O01", "operation", "approved", ["spock/sol"], 1, 2, 4.5,
             Decimal("0.010000000000"), ["session-1"],
             Decimal("0.020000000000"), Decimal("0.010000000000")),
        ]
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        entries = PostgresPilotMetricsStore("postgresql://private").list_all()

        self.assertEqual(entries[0].task_id, "O01")
        self.assertEqual(entries[0].profiles_models, ("spock/sol",))
        self.assertEqual(entries[0].cost_usd, .01)
        self.assertEqual(entries[0].simulated_cost_usd, .02)
        self.assertEqual(entries[0].billed_cost_usd, .01)
        self.assertEqual(entries[0].evidence, ("session-1",))

    @patch("orchestrator.pilot_metrics.psycopg.connect")
    def test_closes_connection_without_commit_when_upsert_fails(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = RuntimeError("database unavailable")
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        metrics = PilotTaskMetrics(
            "F02", "feature", "approved", (), 1, 0, 0.0, 0.0, ()
        )

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            PostgresPilotMetricsStore("postgresql://private").record(metrics)

        connection.commit.assert_not_called()
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
