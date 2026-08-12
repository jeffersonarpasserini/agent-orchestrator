import unittest
from unittest.mock import patch

from orchestrator.reserve_reconcile import build_parser, reconcile_from_args


class ReserveReconcileCliTest(unittest.TestCase):
    def args(self, *extra):
        return build_parser().parse_args([
            "--grant-id", "grant-1",
            "--resolved-by", "spock",
            "--evidence-reference", "incident/DS-001",
            *extra,
        ])

    @patch("orchestrator.reserve_reconcile.PostgresReserveCostStore")
    def test_charged_requires_tokens_and_calls_store(self, store_type):
        store_type.return_value.reconcile_unknown.return_value = 0.001
        args = self.args(
            "--resolution", "confirmed_charged",
            "--cache-hit-tokens", "10",
            "--cache-miss-tokens", "20",
            "--completion-tokens", "30",
        )

        actual = reconcile_from_args(args, "postgresql://private")

        self.assertEqual(actual, 0.001)
        value = store_type.return_value.reconcile_unknown.call_args.args[0]
        self.assertEqual(value.usage.completion_tokens, 30)
        self.assertEqual(value.resolved_by, "spock")

    @patch("orchestrator.reserve_reconcile.PostgresReserveCostStore")
    def test_not_charged_rejects_tokens(self, store_type):
        args = self.args(
            "--resolution", "confirmed_not_charged",
            "--completion-tokens", "1",
        )

        with self.assertRaisesRegex(ValueError, "rejects token counts"):
            reconcile_from_args(args, "postgresql://private")
        store_type.assert_not_called()

    @patch("orchestrator.reserve_reconcile.PostgresReserveCostStore")
    def test_charged_rejects_partial_usage(self, store_type):
        args = self.args(
            "--resolution", "confirmed_charged",
            "--completion-tokens", "1",
        )

        with self.assertRaisesRegex(ValueError, "all token counts"):
            reconcile_from_args(args, "postgresql://private")
        store_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
