import unittest

from orchestrator.adapters.hermes_cli import HermesCliAdapter, ProcessOutput


class BudgetAdapterIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_budget_guard_runs_before_provider_checks(self):
        calls = []

        class Guard:
            def check(self, profile):
                calls.append(("budget", profile))
                raise RuntimeError("budget blocked")

        async def runner(*_):
            calls.append(("runner",))
            return ProcessOutput(0, "No fallback providers configured.", "")

        with self.assertRaisesRegex(RuntimeError, "budget blocked"):
            await HermesCliAdapter(runner=runner, budget_guard=Guard()).run_agent(
                "rutherford", "task"
            )
        self.assertEqual(calls, [("budget", "rutherford")])


if __name__ == "__main__":
    unittest.main()
