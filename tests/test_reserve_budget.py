from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.reserve_budget import (
    DirectBalanceSnapshot,
    DirectReserveBudgetGuard,
    PostgresReserveSpendEvidence,
    ReserveBudgetEvidenceError,
    ReserveBudgetExceededError,
)


class FakeBalanceReader:
    def __init__(self, balance=1.0, available=True):
        self.snapshot = DirectBalanceSnapshot(available, balance)

    def read(self):
        return self.snapshot


class FakeSpendEvidence:
    def __init__(self, daily=0.0, monthly=0.0):
        self.values = [daily, monthly]
        self.starts = []

    def committed_since(self, started_at):
        self.starts.append(started_at)
        return self.values[len(self.starts) - 1]


class DirectReserveBudgetGuardTest(unittest.TestCase):
    now = datetime(2026, 8, 12, 15, 0, tzinfo=timezone.utc)

    def guard(self, balance=1.0, daily=0.0, monthly=0.0):
        evidence = FakeSpendEvidence(daily, monthly)
        return DirectReserveBudgetGuard(
            FakeBalanceReader(balance),
            evidence,
            daily_limit_usd=0.25,
            monthly_limit_usd=2.0,
            operational_timezone=timezone(timedelta(hours=-3)),
            now=lambda: self.now,
        ), evidence

    def test_allows_request_below_balance_and_budgets(self):
        guard, evidence = self.guard(balance=0.50, daily=0.10, monthly=0.80)

        snapshot = guard.check(0.05)

        self.assertEqual(snapshot.balance_usd, 0.50)
        self.assertEqual(snapshot.daily_committed_usd, 0.10)
        self.assertEqual(snapshot.monthly_committed_usd, 0.80)
        self.assertEqual(evidence.starts[0].hour, 3)
        self.assertEqual(evidence.starts[0].day, 12)
        self.assertEqual(evidence.starts[1].day, 1)

    def test_blocks_insufficient_balance_and_exact_budget_overrun(self):
        with self.assertRaisesRegex(ReserveBudgetExceededError, "balance insufficient"):
            self.guard(balance=0.04)[0].check(0.05)
        with self.assertRaisesRegex(ReserveBudgetExceededError, "daily budget"):
            self.guard(daily=0.21)[0].check(0.05)
        with self.assertRaisesRegex(ReserveBudgetExceededError, "monthly budget"):
            self.guard(monthly=1.96)[0].check(0.05)

    def test_allows_request_that_reaches_limit_exactly(self):
        snapshot = self.guard(daily=0.20, monthly=1.95)[0].check(0.05)

        self.assertEqual(snapshot.daily_committed_usd + snapshot.requested_usd, 0.25)
        self.assertEqual(snapshot.monthly_committed_usd + snapshot.requested_usd, 2.0)

    def test_fails_closed_when_balance_or_spend_evidence_fails(self):
        balance = MagicMock()
        balance.read.side_effect = RuntimeError("network detail")
        guard = DirectReserveBudgetGuard(
            balance, FakeSpendEvidence(), daily_limit_usd=.25,
            monthly_limit_usd=2.0,
        )
        with self.assertRaisesRegex(ReserveBudgetEvidenceError, "cannot validate"):
            guard.check(0.05)

        evidence = MagicMock()
        evidence.committed_since.side_effect = RuntimeError("database detail")
        guard = DirectReserveBudgetGuard(
            FakeBalanceReader(), evidence, daily_limit_usd=.25,
            monthly_limit_usd=2.0,
        )
        with self.assertRaisesRegex(ReserveBudgetEvidenceError, "cannot validate"):
            guard.check(0.05)

    @patch("orchestrator.reserve_budget.psycopg.connect")
    def test_postgres_evidence_sums_consumed_grant_caps(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (Decimal("0.150000000000"),)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        started = datetime(2026, 8, 12, tzinfo=timezone.utc)

        value = PostgresReserveSpendEvidence(
            "postgresql://private"
        ).committed_since(started)

        self.assertEqual(value, 0.15)
        statement, parameters = cursor.execute.call_args.args
        self.assertIn("status = 'consumed'", " ".join(statement.split()))
        self.assertEqual(parameters, (started,))
        self.assertNotIn("postgresql://private", parameters)


if __name__ == "__main__":
    unittest.main()
