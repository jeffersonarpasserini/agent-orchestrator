from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from orchestrator.budget import (
    BudgetEvidenceError,
    BudgetExceededError,
    DeepSeekBudgetGuard,
)

class DeepSeekBudgetGuardTest(unittest.TestCase):
    profiles = ("barclay", "rutherford")
    now = datetime(2026, 8, 11, 15, tzinfo=timezone.utc)

    def _guard(self, root, *, daily=1.0, pilot=10.0):
        return DeepSeekBudgetGuard(Path(root), daily_limit_usd=daily,
            pilot_limit_usd=pilot,
            pilot_started_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
            profiles=self.profiles, now=lambda: self.now)

    def _database(self, root, profile, rows=()):
        directory = Path(root) / profile
        directory.mkdir()
        connection = sqlite3.connect(directory / "state.db")
        connection.execute("CREATE TABLE sessions (billing_provider TEXT, started_at REAL, estimated_cost_usd REAL, actual_cost_usd REAL)")
        connection.executemany("INSERT INTO sessions VALUES (?,?,?,?)", rows)
        connection.commit()
        connection.close()

    def test_allows_spend_below_both_limits(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (("deepseek", self.now.timestamp(), .2, None),))
            self._database(root, "rutherford")
            self.assertAlmostEqual(self._guard(root).check("barclay").daily_spend_usd, .2)

    def test_exposes_snapshot_without_profile_or_credentials(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (
                ("deepseek", self.now.timestamp(), .2, None),
            ))
            self._database(root, "rutherford", (
                ("deepseek", self.now.timestamp(), .3, None),
            ))
            snapshot = self._guard(root).snapshot()
            self.assertAlmostEqual(snapshot.daily_spend_usd, .5)
            self.assertAlmostEqual(snapshot.pilot_spend_usd, .5)

    def test_blocks_at_daily_limit(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (("deepseek", self.now.timestamp(), 1.0, None),))
            self._database(root, "rutherford")
            with self.assertRaisesRegex(
                BudgetExceededError, "daily budget exhausted for profile 'rutherford'"
            ):
                self._guard(root).check("rutherford")

    def test_blocks_at_pilot_limit(self):
        with tempfile.TemporaryDirectory() as root:
            yesterday = datetime(2026, 8, 10, 12, tzinfo=timezone.utc).timestamp()
            self._database(root, "barclay", (("deepseek", yesterday, 10.0, None),))
            self._database(root, "rutherford")
            with self.assertRaisesRegex(
                BudgetExceededError, "pilot budget exhausted for profile 'barclay'"
            ):
                self._guard(root).check("barclay")

    def test_daily_limit_boundary_vectors(self):
        for cost, blocked in ((.999999, False), (1.0, True), (1.000001, True)):
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as root:
                self._database(root, "barclay", (
                    ("deepseek", self.now.timestamp(), cost, None),
                ))
                self._database(root, "rutherford")
                guard = self._guard(root)
                if blocked:
                    with self.assertRaises(BudgetExceededError):
                        guard.check("barclay")
                else:
                    self.assertAlmostEqual(
                        guard.check("barclay").daily_spend_usd, cost
                    )

    def test_pilot_limit_boundary_vectors(self):
        started_at = datetime(2026, 8, 10, 12, tzinfo=timezone.utc).timestamp()
        for cost, blocked in ((9.999999, False), (10.0, True), (10.000001, True)):
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as root:
                self._database(root, "barclay", (
                    ("deepseek", started_at, cost, None),
                ))
                self._database(root, "rutherford")
                guard = self._guard(root)
                if blocked:
                    with self.assertRaises(BudgetExceededError):
                        guard.check("barclay")
                else:
                    self.assertAlmostEqual(
                        guard.check("barclay").pilot_spend_usd, cost
                    )

    def test_actual_cost_takes_precedence(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (("deepseek", self.now.timestamp(), 9.0, .25),))
            self._database(root, "rutherford")
            self.assertAlmostEqual(self._guard(root).check("barclay").daily_spend_usd, .25)

    def test_zero_actual_cost_takes_precedence_over_estimate(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (("deepseek", self.now.timestamp(), 9.0, 0.0),))
            self._database(root, "rutherford")
            self.assertEqual(self._guard(root).check("barclay").daily_spend_usd, 0.0)

    def test_daily_spend_uses_pilot_operational_timezone(self):
        with tempfile.TemporaryDirectory() as root:
            before_utc_midnight = datetime(
                2026, 8, 10, 23, 30, tzinfo=timezone.utc
            ).timestamp()
            after_utc_midnight = datetime(
                2026, 8, 11, 1, tzinfo=timezone.utc
            ).timestamp()
            self._database(root, "barclay", (
                ("deepseek", before_utc_midnight, .25, None),
                ("deepseek", after_utc_midnight, .75, None),
            ))
            self._database(root, "rutherford")
            operational_timezone = timezone(timedelta(hours=-3))
            guard = DeepSeekBudgetGuard(
                Path(root),
                daily_limit_usd=2.0,
                pilot_limit_usd=10.0,
                pilot_started_at=datetime(
                    2026, 8, 10, tzinfo=operational_timezone
                ),
                profiles=self.profiles,
                now=lambda: datetime(2026, 8, 11, 2, tzinfo=timezone.utc),
            )
            self.assertEqual(guard.check("barclay").daily_spend_usd, 1.0)

    def test_missing_database_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay")
            with self.assertRaises(BudgetEvidenceError):
                self._guard(root).check("rutherford")

    def test_unknown_cost_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            self._database(root, "barclay", (("deepseek", self.now.timestamp(), None, None),))
            self._database(root, "rutherford")
            with self.assertRaises(BudgetEvidenceError):
                self._guard(root).check("barclay")

    def test_non_deepseek_profile_skips_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(self._guard(root).check("spock"))

if __name__ == "__main__":
    unittest.main()
