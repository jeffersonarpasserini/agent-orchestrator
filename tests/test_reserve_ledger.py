from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.deepseek_reserve_finance import DeepSeekUsage
from orchestrator.reserve_ledger import (
    PostgresReserveLedger,
    ReserveAttempt,
    ReserveAttemptResult,
    ReserveAttemptStatus,
)
from orchestrator.technical_reserve import BillingRoute, PrimaryFailureReason


def attempt() -> ReserveAttempt:
    return ReserveAttempt(
        attempt_id="attempt-1",
        task_id="FUTURE-01",
        grant_id="grant-1",
        primary_failure_reason=(
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
        ),
        requested_model="deepseek-v4-flash",
    )


def completed_result() -> ReserveAttemptResult:
    return ReserveAttemptResult(
        attempt_id="attempt-1",
        status=ReserveAttemptStatus.COMPLETED,
        effective_model="deepseek-v4-flash",
        usage=DeepSeekUsage(1, 2, 3),
        direct_cost_usd=0.02,
    )


class ReserveLedgerTest(unittest.TestCase):
    def database(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        return connection, cursor

    def test_attempt_requires_direct_reserve_route(self):
        with self.assertRaisesRegex(ValueError, "direct reserve route"):
            ReserveAttempt(
                **{
                    **attempt().__dict__,
                    "billing_route": BillingRoute.QWENCLOUD_PRIMARY,
                }
            )

    def test_completed_result_requires_model_usage_and_cost(self):
        with self.assertRaisesRegex(ValueError, "requires model, usage and cost"):
            ReserveAttemptResult(
                attempt_id="attempt-1",
                status=ReserveAttemptStatus.COMPLETED,
            )

    @patch("orchestrator.reserve_ledger.psycopg.connect")
    def test_start_is_idempotent_for_the_exact_scope(self, connect):
        connection, cursor = self.database(connect)
        cursor.fetchone.return_value = (
            "FUTURE-01",
            "grant-1",
            "deepseek_reserve",
            "subscription_credits_exhausted",
            "deepseek-v4-flash",
            None,
        )

        PostgresReserveLedger("postgresql://private").start(attempt())

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("ON CONFLICT (attempt_id) DO NOTHING", statements[0])
        self.assertIn("FOR UPDATE", statements[1])
        self.assertNotIn("postgresql://private", str(cursor.execute.call_args_list))
        connection.commit.assert_called_once_with()

    @patch("orchestrator.reserve_ledger.psycopg.connect")
    def test_start_rejects_attempt_id_reused_for_another_scope(self, connect):
        _, cursor = self.database(connect)
        cursor.fetchone.return_value = (
            "OTHER",
            "grant-1",
            "deepseek_reserve",
            "subscription_credits_exhausted",
            "deepseek-v4-flash",
            None,
        )

        with self.assertRaisesRegex(ValueError, "conflicts with existing scope"):
            PostgresReserveLedger("postgresql://private").start(attempt())

    @patch("orchestrator.reserve_ledger.psycopg.connect")
    def test_finish_records_terminal_result_once(self, connect):
        connection, cursor = self.database(connect)
        cursor.fetchone.return_value = (
            "reserve_running", None, None, None, None, None, None, None,
        )
        cursor.rowcount = 1

        PostgresReserveLedger("postgresql://private").finish(completed_result())

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("FOR UPDATE", statements[0])
        self.assertIn("status = %s", statements[1])
        parameters = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(parameters[:6], (
            "completed", "deepseek-v4-flash", 1, 2, 3, 0.02,
        ))
        connection.commit.assert_called_once_with()

    @patch("orchestrator.reserve_ledger.psycopg.connect")
    def test_finish_replay_is_idempotent_but_conflict_fails(self, connect):
        connection, cursor = self.database(connect)
        cursor.fetchone.return_value = (
            "completed", "deepseek-v4-flash", 1, 2, 3, 0.02, None, None,
        )

        ledger = PostgresReserveLedger("postgresql://private")
        ledger.finish(completed_result())

        self.assertEqual(cursor.execute.call_count, 1)
        connection.commit.assert_called_once_with()

        cursor.reset_mock()
        cursor.fetchone.return_value = (
            "completed", "deepseek-v4-flash", 1, 2, 3, 0.03, None, None,
        )
        with self.assertRaisesRegex(ValueError, "different result"):
            ledger.finish(completed_result())

    def test_migration_contains_route_scope_result_and_cost_constraints(self):
        migration = Path("migrations/0008_deepseek_reserve_attempts.sql").read_text()

        for field in (
            "attempt_id",
            "grant_id",
            "approved_by",
            "billing_route",
            "primary_failure_reason",
            "requested_model",
            "effective_model",
            "primary_session_id",
            "reserve_session_id",
            "latency_ms",
            "direct_cost_usd",
        ):
            self.assertIn(field, migration)
        self.assertIn("grant_id text NOT NULL UNIQUE", migration)
        self.assertIn("billing_route = 'deepseek_reserve'", migration)

    @patch("orchestrator.reserve_ledger.psycopg.connect")
    def test_metrics_snapshot_uses_bounded_route_status_and_model_dimensions(
        self, connect
    ):
        _, cursor = self.database(connect)
        cursor.fetchone.return_value = (7, 1, 3, 1, 1, 1, 0.12, 10, 20, 30)
        cursor.fetchall.return_value = [
            ("deepseek-v4-flash", 5),
            ("deepseek-v4-pro", 2),
        ]

        snapshot = PostgresReserveLedger(
            "postgresql://private"
        ).metrics_snapshot()

        self.assertEqual(snapshot.total_activations, 7)
        self.assertEqual(snapshot.status_counts["completed"], 3)
        self.assertEqual(snapshot.model_counts["deepseek-v4-flash"], 5)
        self.assertEqual(snapshot.direct_cost_usd, 0.12)
        statements = " ".join(
            call.args[0] for call in cursor.execute.call_args_list
        ).lower()
        self.assertNotIn("prompt", statements.replace("prompt_cache", ""))
        self.assertNotIn("task_id", statements)
        self.assertNotIn("grant_id", statements)


if __name__ == "__main__":
    unittest.main()
