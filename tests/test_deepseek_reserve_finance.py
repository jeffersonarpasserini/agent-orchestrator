import unittest
from unittest.mock import MagicMock, patch

from orchestrator.deepseek_reserve_finance import (
    DeepSeekCostEstimator,
    DeepSeekDirectBalanceReader,
    DeepSeekDirectChatProvider,
    DeepSeekReserveExecutor,
    DeepSeekUsage,
    ManualReconciliationResolution,
    ManualReserveReconciliation,
    PostgresReserveCostStore,
    ReserveCostCommitment,
    ReserveOutcomeUnknownError,
    ReserveProviderResult,
    UrllibJsonPostTransport,
    UrllibJsonTransport,
)
from orchestrator.reserve_budget import (
    ReserveBudgetEvidenceError,
    ReserveBudgetExceededError,
)
from orchestrator.technical_reserve import BillingRoute


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_json(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        return self.payload


class FakePostTransport:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def post_json(self, url, headers, payload, timeout):
        self.calls.append((url, headers, payload, timeout))
        if self.error:
            raise self.error
        return self.payload


class DeepSeekTransportSafetyTest(unittest.TestCase):
    def test_transports_reject_urls_outside_exact_provider_routes(self):
        invalid_urls = (
            "http://api.deepseek.com/user/balance",
            "https://evil.example/user/balance",
            "https://api.deepseek.com/unknown",
            "https://api.deepseek.com/user/balance?redirect=evil",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "not allowed"):
                UrllibJsonTransport().get_json(url, {}, 1)
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "not allowed"):
                UrllibJsonPostTransport().post_json(url, {}, {}, 1)

    def test_transport_failure_does_not_reflect_direct_credential(self):
        provider = DeepSeekDirectChatProvider(
            "private-direct-key",
            ({"role": "user", "content": "hello"},),
            max_output_tokens=8,
            transport=FakePostTransport(error=RuntimeError("network failed")),
        )

        with self.assertRaises(Exception) as raised:
            provider.invoke_once("deepseek-v4-flash")

        self.assertNotIn("private-direct-key", str(raised.exception))


class DeepSeekDirectBalanceReaderTest(unittest.TestCase):
    def test_reads_usd_balance_without_exposing_key(self):
        transport = FakeTransport({
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "10.00"},
                {"currency": "USD", "total_balance": "2.50"},
            ],
        })
        reader = DeepSeekDirectBalanceReader("private-key", transport=transport)

        snapshot = reader.read()

        self.assertTrue(snapshot.is_available)
        self.assertEqual(snapshot.total_balance_usd, 2.5)
        url, headers, timeout = transport.calls[0]
        self.assertEqual(url, "https://api.deepseek.com/user/balance")
        self.assertEqual(headers["Authorization"], "Bearer private-key")
        self.assertEqual(timeout, 10.0)
        self.assertNotIn("private-key", repr(snapshot))

    def test_rejects_unsafe_endpoint_and_invalid_or_missing_usd(self):
        with self.assertRaisesRegex(ValueError, "not allowed"):
            DeepSeekDirectBalanceReader("key", base_url="http://api.deepseek.com")
        with self.assertRaisesRegex(ValueError, "not allowed"):
            DeepSeekDirectBalanceReader("key", base_url="https://evil.example")

        invalid = (
            {},
            {"is_available": "true", "balance_infos": []},
            {"is_available": True, "balance_infos": []},
            {"is_available": True, "balance_infos": [
                {"currency": "USD", "total_balance": "NaN"}
            ]},
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ReserveBudgetEvidenceError):
                DeepSeekDirectBalanceReader("key", transport=FakeTransport(payload)).read()

    def test_transport_failure_is_normalized_without_secret(self):
        transport = MagicMock()
        transport.get_json.side_effect = RuntimeError("private-key network detail")
        with self.assertRaises(ReserveBudgetEvidenceError) as raised:
            DeepSeekDirectBalanceReader("private-key", transport=transport).read()
        self.assertNotIn("private-key", str(raised.exception))


class DeepSeekCostEstimatorTest(unittest.TestCase):
    def test_estimates_maximum_with_cache_miss_rate(self):
        estimator = DeepSeekCostEstimator()

        flash = estimator.maximum_cost(
            "deepseek-v4-flash", max_input_tokens=1_000_000,
            max_output_tokens=1_000_000,
        )
        pro = estimator.maximum_cost(
            "deepseek-v4-pro", max_input_tokens=1_000_000,
            max_output_tokens=1_000_000,
        )

        self.assertEqual(flash, 0.42)
        self.assertEqual(pro, 1.305)

    def test_reconciles_cache_hit_miss_and_output_separately(self):
        usage = DeepSeekUsage(1_000_000, 1_000_000, 1_000_000)

        cost = DeepSeekCostEstimator().actual_cost("deepseek-v4-flash", usage)

        self.assertEqual(cost, 0.4228)

    def test_unknown_model_and_negative_tokens_fail_closed(self):
        with self.assertRaises(ReserveBudgetEvidenceError):
            DeepSeekCostEstimator().maximum_cost(
                "unpriced", max_input_tokens=1, max_output_tokens=1
            )
        with self.assertRaises(ValueError):
            DeepSeekUsage(-1, 0, 0)


class DeepSeekDirectChatProviderTest(unittest.TestCase):
    def response(self):
        return {
            "id": "chatcmpl-reserve-1",
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {
                "prompt_cache_hit_tokens": 10,
                "prompt_cache_miss_tokens": 20,
                "completion_tokens": 30,
            },
        }

    def test_posts_exact_nonstreaming_request_with_fake_transport(self):
        transport = FakePostTransport(self.response())
        provider = DeepSeekDirectChatProvider(
            "private-key", ({"role": "user", "content": "test"},),
            max_output_tokens=1000, transport=transport,
        )

        result = provider.invoke_once("deepseek-v4-flash")

        self.assertEqual(result.output, "ok")
        self.assertEqual(result.provider_request_id, "chatcmpl-reserve-1")
        self.assertEqual(result.usage.completion_tokens, 30)
        self.assertEqual(result.billing_route, BillingRoute.DEEPSEEK_RESERVE)
        url, headers, payload, timeout = transport.calls[0]
        self.assertEqual(url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer private-key")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["thinking"], {"type": "enabled"})
        self.assertEqual(payload["max_tokens"], 1000)
        self.assertEqual(timeout, 120.0)

    def test_transport_or_invalid_response_becomes_unknown_without_secret(self):
        provider = DeepSeekDirectChatProvider(
            "private-key", ({"role": "user", "content": "test"},),
            max_output_tokens=1,
            transport=FakePostTransport(error=RuntimeError("private-key timeout")),
        )
        with self.assertRaises(ReserveOutcomeUnknownError) as raised:
            provider.invoke_once("deepseek-v4-flash")
        self.assertNotIn("private-key", str(raised.exception))

        invalid = DeepSeekDirectChatProvider(
            "key", ({"role": "user", "content": "test"},),
            max_output_tokens=1, transport=FakePostTransport({}),
        )
        with self.assertRaises(ReserveOutcomeUnknownError):
            invalid.invoke_once("deepseek-v4-flash")

    def test_unknown_model_is_blocked_before_transport(self):
        transport = FakePostTransport(self.response())
        provider = DeepSeekDirectChatProvider(
            "key", ({"role": "user", "content": "test"},),
            max_output_tokens=1, transport=transport,
        )

        with self.assertRaises(ReserveBudgetEvidenceError):
            provider.invoke_once("unapproved-model")
        self.assertEqual(transport.calls, [])


class PostgresReserveCostStoreTest(unittest.TestCase):
    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_records_unique_commitment(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("grant-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        value = ReserveCostCommitment(
            "grant-1", "FUTURE-01", "deepseek-v4-flash",
            "official-2026-08-12", 0.04,
        )

        PostgresReserveCostStore("postgresql://private").commit(value)

        statement, parameters = cursor.execute.call_args.args
        self.assertIn("ON CONFLICT (grant_id) DO NOTHING", statement)
        self.assertEqual(parameters[-1], 0.04)
        self.assertNotIn("postgresql://private", parameters)
        connection.commit.assert_called_once_with()

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_reconciles_once_with_actual_usage(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("grant-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        usage = DeepSeekUsage(10, 20, 30)

        PostgresReserveCostStore("postgresql://private").reconcile(
            "grant-1", usage, 0.001
        )

        statement, parameters = cursor.execute.call_args.args
        self.assertIn("status = 'committed'", " ".join(statement.split()))
        self.assertEqual(parameters, (0.001, 10, 20, 30, "grant-1"))

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_duplicate_commit_or_reconciliation_fails_closed(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        store = PostgresReserveCostStore("postgresql://private")

        with self.assertRaises(ReserveBudgetEvidenceError):
            store.commit(ReserveCostCommitment(
                "grant-1", "task", "deepseek-v4-flash", "snapshot", 0.04
            ))
        with self.assertRaises(ReserveBudgetEvidenceError):
            store.reconcile("grant-1", DeepSeekUsage(0, 0, 1), 0.01)

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_marks_only_committed_cost_as_outcome_unknown(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("grant-1",)
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        PostgresReserveCostStore(
            "postgresql://private"
        ).mark_outcome_unknown("grant-1")

        statement, parameters = cursor.execute.call_args.args
        self.assertIn("status = 'committed'", " ".join(statement.split()))
        self.assertEqual(parameters, ("grant-1",))

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_manually_reconciles_unknown_charged_outcome_once(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("deepseek-v4-flash",), ("grant-1",), ("grant-1",),
        ]
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        value = ManualReserveReconciliation(
            grant_id="grant-1",
            resolved_by="spock",
            evidence_reference="incident/DS-001",
            resolution=ManualReconciliationResolution.CHARGED,
            usage=DeepSeekUsage(1_000_000, 0, 0),
        )

        actual = PostgresReserveCostStore(
            "postgresql://private"
        ).reconcile_unknown(value)

        self.assertEqual(actual, 0.0028)
        statements = [" ".join(call.args[0].split()) for call in cursor.execute.call_args_list]
        self.assertIn("FOR UPDATE", statements[0])
        self.assertIn("status = 'outcome_unknown'", statements[1])
        self.assertIn("deepseek_reserve_manual_reconciliations", statements[2])
        self.assertEqual(cursor.execute.call_args_list[2].args[1][1], "confirmed_charged")
        connection.commit.assert_called_once_with()

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_manually_reconciles_confirmed_not_charged_as_zero(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("deepseek-v4-pro",), ("grant-1",), ("grant-1",),
        ]
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        value = ManualReserveReconciliation(
            grant_id="grant-1",
            resolved_by="spock",
            evidence_reference="provider-console/2026-08-12",
            resolution=ManualReconciliationResolution.NOT_CHARGED,
        )

        actual = PostgresReserveCostStore(
            "postgresql://private"
        ).reconcile_unknown(value)

        self.assertEqual(actual, 0.0)
        update_parameters = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(update_parameters[:4], (0.0, 0, 0, 0))

    @patch("orchestrator.deepseek_reserve_finance.psycopg.connect")
    def test_manual_reconciliation_rejects_non_unknown_or_reused(self, connect):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection
        value = ManualReserveReconciliation(
            "grant-1", "spock", "incident/DS-001",
            ManualReconciliationResolution.NOT_CHARGED,
        )

        with self.assertRaisesRegex(ReserveBudgetEvidenceError, "not available"):
            PostgresReserveCostStore(
                "postgresql://private"
            ).reconcile_unknown(value)

        self.assertEqual(cursor.execute.call_count, 1)
        connection.commit.assert_not_called()

    def test_manual_reconciliation_requires_consistent_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires usage"):
            ManualReserveReconciliation(
                "grant", "spock", "evidence",
                ManualReconciliationResolution.CHARGED,
            )
        with self.assertRaisesRegex(ValueError, "must not include usage"):
            ManualReserveReconciliation(
                "grant", "spock", "evidence",
                ManualReconciliationResolution.NOT_CHARGED,
                DeepSeekUsage(0, 0, 0),
            )


class FakeReserveProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke_once(self, model):
        self.calls.append(model)
        if self.error:
            raise self.error
        return self.result


class DeepSeekReserveExecutorTest(unittest.TestCase):
    def test_commits_calls_once_and_reconciles_fake_provider(self):
        result = ReserveProviderResult(
            "deepseek-v4-flash", DeepSeekUsage(10, 20, 30), {"text": "ok"}
        )
        provider = FakeReserveProvider(result=result)
        store = MagicMock()
        executor = DeepSeekReserveExecutor(provider, store)

        returned = executor.execute(
            grant_id="grant-1", task_id="task-1",
            model="deepseek-v4-flash", grant_max_cost_usd=0.01,
            max_input_tokens=1000, max_output_tokens=1000,
        )

        self.assertIs(returned, result)
        self.assertEqual(provider.calls, ["deepseek-v4-flash"])
        commitment = store.commit.call_args.args[0]
        self.assertEqual(commitment.price_snapshot, "official-2026-08-12")
        self.assertLessEqual(commitment.estimated_max_cost_usd, 0.01)
        store.reconcile.assert_called_once()
        store.mark_outcome_unknown.assert_not_called()

    def test_estimate_over_grant_blocks_before_commit_and_provider(self):
        provider = FakeReserveProvider()
        store = MagicMock()
        executor = DeepSeekReserveExecutor(provider, store)

        with self.assertRaises(ReserveBudgetExceededError):
            executor.execute(
                grant_id="grant-1", task_id="task-1",
                model="deepseek-v4-pro", grant_max_cost_usd=0.000001,
                max_input_tokens=1000, max_output_tokens=1000,
            )

        self.assertEqual(provider.calls, [])
        store.commit.assert_not_called()

    def test_ambiguous_provider_result_marks_unknown_without_retry(self):
        provider = FakeReserveProvider(error=ReserveOutcomeUnknownError("timeout"))
        store = MagicMock()
        executor = DeepSeekReserveExecutor(provider, store)

        with self.assertRaises(ReserveOutcomeUnknownError):
            executor.execute(
                grant_id="grant-1", task_id="task-1",
                model="deepseek-v4-flash", grant_max_cost_usd=0.01,
                max_input_tokens=1000, max_output_tokens=1000,
            )

        self.assertEqual(provider.calls, ["deepseek-v4-flash"])
        store.mark_outcome_unknown.assert_called_once_with("grant-1")
        store.reconcile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
