from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.reserve_budget import (
    ReserveBudgetExceededError,
    ReserveBudgetSnapshot,
)
from orchestrator.deepseek_reserve_finance import ReserveCostCommitment
from orchestrator.reserve_grants import (
    PostgresReserveGrantStore,
    ReserveGrant,
    ReserveGrantScope,
)
from orchestrator.reserve_ledger import (
    ReserveAttempt,
    ReserveAttemptStatus,
)
from orchestrator.technical_reserve import PrimaryFailureReason


def grant() -> ReserveGrant:
    return ReserveGrant(
        grant_id="grant-1",
        task_id="FUTURE-01",
        profile="barclay",
        role="flash",
        primary_model="deepseek-v4-flash-0731",
        reserve_model="deepseek-v4-flash",
        primary_failure_reason=(
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
        ),
        approved_by="spock",
        max_cost_usd=0.05,
        max_calls=1,
        expires_at=datetime(2026, 8, 12, 18, 0, tzinfo=timezone.utc),
    )


class ReserveGrantTest(unittest.TestCase):
    def budget_snapshot(self):
        return ReserveBudgetSnapshot(
            balance_usd=1.0,
            daily_committed_usd=0.1,
            monthly_committed_usd=0.8,
            requested_usd=0.04,
            day_started_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
            month_started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )

    def test_rejects_naive_expiration_and_multiple_calls(self):
        values = grant().__dict__
        with self.assertRaisesRegex(ValueError, "timezone"):
            ReserveGrant(**{
                **values,
                "expires_at": datetime(2026, 8, 12, 18, 0),
            })
        with self.assertRaisesRegex(ValueError, "exactly one call"):
            ReserveGrant(**{**values, "max_calls": 2})

    def test_rejects_grant_above_cap_and_unauthorized_approver(self):
        values = grant().__dict__
        with self.assertRaisesRegex(ValueError, "USD 0.10 cap"):
            ReserveGrant(**{**values, "max_cost_usd": 0.101})
        with self.assertRaisesRegex(PermissionError, "not authorized"):
            ReserveGrant(**{**values, "approved_by": "alfred"})

    def test_rejects_scope_above_grant_cap(self):
        values = {
            key: value for key, value in grant().__dict__.items()
            if key not in {"approved_by", "max_calls"}
        }
        with self.assertRaisesRegex(ValueError, "USD 0.10 cap"):
            ReserveGrantScope(**{**values, "max_cost_usd": 0.101})

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_creates_approved_grant_without_database_url_in_payload(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        PostgresReserveGrantStore("postgresql://private").create_approved(grant())

        statement, parameters = cursor.execute.call_args.args
        self.assertIn("INSERT INTO orchestrator.deepseek_reserve_grants", statement)
        self.assertIn("'approved'", statement)
        self.assertNotIn("postgresql://private", parameters)
        self.assertNotIn("api_key", str(parameters).lower())
        connection.commit.assert_called_once_with()
        connection.close.assert_called_once_with()

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_consumes_grant_atomically_for_exact_scope(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("grant-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        scope = ReserveGrantScope(
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )

        consumed = PostgresReserveGrantStore("postgresql://private").consume(scope)

        self.assertTrue(consumed)
        statement, parameters = cursor.execute.call_args.args
        normalized = " ".join(statement.split())
        self.assertIn("status = 'approved'", normalized)
        self.assertIn("expires_at > now()", normalized)
        self.assertIn("max_cost_usd >= %s", normalized)
        self.assertIn("RETURNING grant_id", normalized)
        self.assertEqual(parameters, (
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash",
            "subscription_credits_exhausted", 0.04,
        ))
        connection.commit.assert_called_once_with()

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_reused_expired_or_wrong_scope_grant_is_not_consumed(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        scope = ReserveGrantScope(
            "grant-1", "OTHER", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )

        self.assertFalse(
            PostgresReserveGrantStore("postgresql://private").consume(scope)
        )

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_budget_and_grant_consumption_share_locked_transaction(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(0.10, 0.80), (0,), ("grant-1",)]
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        scope = ReserveGrantScope(
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )

        consumed = PostgresReserveGrantStore(
            "postgresql://private"
        ).consume_with_budget(
            scope, self.budget_snapshot(),
            daily_limit_usd=1.0, monthly_limit_usd=10.0,
        )

        self.assertTrue(consumed)
        statements = [" ".join(call.args[0].split()) for call in cursor.execute.call_args_list]
        self.assertIn("pg_advisory_xact_lock", statements[0])
        self.assertIn("sum(max_cost_usd)", statements[1])
        self.assertIn("task_id = %s", statements[2])
        self.assertIn("status = 'approved'", statements[3])
        connection.commit.assert_called_once_with()

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_atomic_budget_recheck_blocks_without_consuming_grant(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (0.22, 0.80)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        scope = ReserveGrantScope(
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )

        with self.assertRaisesRegex(ReserveBudgetExceededError, "daily budget"):
            PostgresReserveGrantStore(
                "postgresql://private"
            ).consume_with_budget(
                scope, self.budget_snapshot(),
                daily_limit_usd=0.25, monthly_limit_usd=2.0,
            )

        self.assertEqual(cursor.execute.call_count, 2)
        connection.commit.assert_not_called()

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_consumes_grant_and_commits_cost_in_same_transaction(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (0.10, 0.80), (0,), ("grant-1",), ("grant-1",), ("attempt-1",),
        ]
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        scope = ReserveGrantScope(
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )
        commitment = ReserveCostCommitment(
            "grant-1", "FUTURE-01", "deepseek-v4-flash",
            "official-2026-08-12", 0.001,
        )
        attempt = ReserveAttempt(
            "attempt-1", "FUTURE-01", "grant-1",
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
            "deepseek-v4-flash",
        )

        consumed = PostgresReserveGrantStore(
            "postgresql://private"
        ).consume_with_budget_and_cost(
            scope, self.budget_snapshot(), commitment,
            daily_limit_usd=1.0, monthly_limit_usd=10.0,
            attempt=attempt,
        )

        self.assertTrue(consumed)
        statements = [" ".join(call.args[0].split()) for call in cursor.execute.call_args_list]
        self.assertIn("pg_advisory_xact_lock", statements[0])
        self.assertIn("task_id = %s", statements[2])
        self.assertIn("UPDATE orchestrator.deepseek_reserve_grants", statements[3])
        self.assertIn("INSERT INTO orchestrator.deepseek_reserve_costs", statements[4])
        self.assertIn("INSERT INTO orchestrator.deepseek_reserve_attempts", statements[5])
        connection.commit.assert_called_once_with()

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_finishes_attempt_from_reconciled_cost_idempotently(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("attempt-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        PostgresReserveGrantStore("postgresql://private").finish_attempt(
            "attempt-1",
            ReserveAttemptStatus.COMPLETED,
            effective_model="deepseek-v4-flash",
        )

        statement, parameters = cursor.execute.call_args.args
        self.assertIn("FROM orchestrator.deepseek_reserve_costs", statement)
        self.assertIn("cost.status = 'reconciled'", statement)
        self.assertEqual(parameters, (
            "completed", "deepseek-v4-flash", None, None,
            "attempt-1", "completed",
        ))
        connection.commit.assert_called_once_with()

    def test_rejects_cost_commitment_outside_grant_without_database(self):
        scope = ReserveGrantScope(
            "grant-1", "FUTURE-01", "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )
        wrong = ReserveCostCommitment(
            "other", "FUTURE-01", "deepseek-v4-flash", "snapshot", 0.001
        )

        with self.assertRaisesRegex(ReserveBudgetExceededError, "outside grant"):
            PostgresReserveGrantStore(
                "postgresql://private"
            ).consume_with_budget_and_cost(
                scope, self.budget_snapshot(), wrong,
                daily_limit_usd=0.25, monthly_limit_usd=2.0,
            )

    @patch("orchestrator.reserve_grants.psycopg.connect")
    def test_revokes_only_approved_grant(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("grant-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        revoked = PostgresReserveGrantStore("postgresql://private").revoke("grant-1")

        self.assertTrue(revoked)
        statement, parameters = cursor.execute.call_args.args
        self.assertIn("status = 'approved'", " ".join(statement.split()))
        self.assertEqual(parameters, ("grant-1",))


if __name__ == "__main__":
    unittest.main()
