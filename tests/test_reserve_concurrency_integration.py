from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import unittest
from uuid import uuid4

from orchestrator.deepseek_reserve_finance import ReserveCostCommitment
from orchestrator.reserve_budget import ReserveBudgetSnapshot
from orchestrator.reserve_grants import (
    PostgresReserveGrantStore,
    ReserveGrant,
    ReserveGrantScope,
)
from orchestrator.reserve_ledger import ReserveAttempt
from orchestrator.technical_reserve import PrimaryFailureReason


@unittest.skipUnless(
    os.environ.get("ORCHESTRATOR_TEST_DATABASE_URL"),
    "ORCHESTRATOR_TEST_DATABASE_URL is required",
)
class ReserveConcurrencyIntegrationTest(unittest.TestCase):
    def test_two_consumers_produce_exactly_one_attempt(self):
        database_url = os.environ["ORCHESTRATOR_TEST_DATABASE_URL"]
        store = PostgresReserveGrantStore(database_url)
        suffix = uuid4().hex
        grant_id = f"concurrency-{suffix}"
        task_id = f"CONCURRENCY-{suffix}"
        reason = PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
        store.create_approved(ReserveGrant(
            grant_id=grant_id,
            task_id=task_id,
            profile="barclay",
            role="flash",
            primary_model="deepseek-v4-flash-0731",
            reserve_model="deepseek-v4-flash",
            primary_failure_reason=reason,
            approved_by="integration-test",
            max_cost_usd=0.04,
            max_calls=1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))
        scope = ReserveGrantScope(
            grant_id, task_id, "barclay", "flash",
            "deepseek-v4-flash-0731", "deepseek-v4-flash", 0.04, reason,
        )
        snapshot = ReserveBudgetSnapshot(
            balance_usd=1.0,
            daily_committed_usd=0.0,
            monthly_committed_usd=0.0,
            requested_usd=0.04,
            day_started_at=datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            month_started_at=datetime.now(timezone.utc).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            ),
        )
        commitment = ReserveCostCommitment(
            grant_id, task_id, "deepseek-v4-flash", "integration", 0.001,
        )
        attempt = ReserveAttempt(
            f"reserve:{grant_id}", task_id, grant_id, reason,
            "deepseek-v4-flash",
        )

        def consume():
            return store.consume_with_budget_and_cost(
                scope, snapshot, commitment,
                daily_limit_usd=1.0,
                monthly_limit_usd=2.0,
                attempt=attempt,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: consume(), range(2)))

        self.assertEqual(sorted(results), [False, True])


if __name__ == "__main__":
    unittest.main()
