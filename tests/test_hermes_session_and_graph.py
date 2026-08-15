import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import ANY, MagicMock
from orchestrator.adapters.hermes_cli import HermesRunResult
from orchestrator.adapters.hermes_session import SQLiteHermesSessionStore
from orchestrator.budget import BudgetEvidenceError, BudgetExceededError
from orchestrator.graphs.hermes_agent import run_hermes_workflow
from orchestrator.reserve_grants import ReserveGrantScope
from orchestrator.reserve_ledger import ReserveAttemptStatus
from orchestrator.reserve_budget import ReserveBudgetExceededError
from orchestrator.deepseek_reserve_finance import (
    DeepSeekReserveExecutor,
    DeepSeekUsage,
    ReserveOutcomeUnknownError,
    ReserveProviderResult,
)
from orchestrator.technical_reserve import (
    PrimaryFailureReason,
    PrimaryRouteError,
    ReserveMode,
    TechnicalReserveConfig,
)

class HermesSessionStoreTest(unittest.TestCase):
    def test_reads_usage_and_tool_calls(self):
        with tempfile.TemporaryDirectory() as root:
            profile_dir = Path(root) / "spock"
            profile_dir.mkdir()
            connection = sqlite3.connect(profile_dir / "state.db")
            connection.executescript("""
                CREATE TABLE sessions (id TEXT PRIMARY KEY, model TEXT, billing_provider TEXT,
                  billing_mode TEXT, api_call_count INTEGER, input_tokens INTEGER,
                  output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                  reasoning_tokens INTEGER, estimated_cost_usd REAL, actual_cost_usd REAL,
                  cost_status TEXT, cost_source TEXT, tool_call_count INTEGER);
                CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, tool_calls TEXT);
                INSERT INTO sessions VALUES ('s1','gpt-5.6-sol','openai-codex',
                  'subscription_included',1,10,2,3,0,1,0,NULL,'included','none',1);
            """)
            calls = [{"id": "call-1", "function": {"name": "search"}}]
            connection.execute("INSERT INTO messages VALUES (1,'s1',?)", (json.dumps(calls),))
            connection.commit()
            connection.close()
            details = SQLiteHermesSessionStore(Path(root)).read("spock", "s1")
            self.assertEqual(details.usage["input_tokens"], 10)
            self.assertEqual(details.tool_calls[0]["id"], "call-1")

    def test_default_uses_root_state_database(self):
        with tempfile.TemporaryDirectory() as root:
            profiles = Path(root) / "profiles"
            profiles.mkdir()
            connection = sqlite3.connect(Path(root) / "state.db")
            connection.executescript("""
                CREATE TABLE sessions (id TEXT PRIMARY KEY, model TEXT, billing_provider TEXT, billing_mode TEXT, api_call_count INTEGER, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER, estimated_cost_usd REAL, actual_cost_usd REAL, cost_status TEXT, cost_source TEXT, tool_call_count INTEGER);
                CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, tool_calls TEXT);
                INSERT INTO sessions VALUES ('s1','gpt-5.6-luna','openai-codex','subscription_included',1,4,1,0,0,0,0,NULL,'included','none',0);
            """)
            connection.close()
            details = SQLiteHermesSessionStore(profiles).read("default", "s1")
            self.assertEqual(details.usage["model"], "gpt-5.6-luna")

    def test_incompatible_sqlite_schema_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as root:
            profile_dir = Path(root) / "spock"
            profile_dir.mkdir()
            connection = sqlite3.connect(profile_dir / "state.db")
            connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
            connection.commit()
            connection.close()

            with self.assertRaisesRegex(sqlite3.OperationalError, "no such column"):
                SQLiteHermesSessionStore(Path(root)).read("spock", "s1")


class HermesAgentGraphTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _shadow_config():
        return TechnicalReserveConfig(
            mode=ReserveMode.SHADOW,
            kill_switch_active=False,
            enabled_profiles=frozenset({"barclay"}),
        )

    @staticmethod
    def _enforced_config():
        return TechnicalReserveConfig(
            mode=ReserveMode.ENFORCED,
            kill_switch_active=False,
            enabled_profiles=frozenset({"barclay"}),
            daily_budget_usd=0.25,
            monthly_budget_usd=2.0,
        )

    @staticmethod
    def _grant_scope(task_id="FUTURE-05", *, expires_at=None):
        return ReserveGrantScope(
            grant_id="grant-1",
            task_id=task_id,
            profile="barclay",
            role="flash",
            primary_model="deepseek-v4-flash-0731",
            reserve_model="deepseek-v4-flash",
            max_cost_usd=0.04,
            primary_failure_reason=(
                PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
            ),
            expires_at=expires_at or datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    @staticmethod
    def _budget_guard():
        guard = MagicMock()
        guard.check.return_value = MagicMock()
        return guard

    @staticmethod
    def _reserve_executor(error=None):
        provider = MagicMock()
        if error is not None:
            provider.invoke_once.side_effect = error
        else:
            provider.invoke_once.return_value = ReserveProviderResult(
                "deepseek-v4-flash", DeepSeekUsage(10, 20, 30), "reserve ok",
                provider_request_id="chatcmpl-reserve-1",
            )
        executor = DeepSeekReserveExecutor(provider, MagicMock())
        return executor, provider

    async def test_graph_invokes_adapter_and_propagates_metadata(self):
        class FakeAdapter:
            async def run_agent(self, profile, task, context, limits):
                return HermesRunResult(profile, "ok", "session-1", "corr-1",
                    usage={"input_tokens": 10}, tool_calls=({"id": "tool-1"},))
        result = await run_hermes_workflow(FakeAdapter(), "spock", "classify")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["session_id"], "session-1")
        self.assertEqual(result["usage"]["input_tokens"], 10)
        self.assertEqual(result["tool_calls"][0]["id"], "tool-1")

    async def test_graph_returns_budget_blocked_state(self):
        class BlockedAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise BudgetExceededError(
                    "DeepSeek daily budget exhausted for profile 'tuvok'"
                )

        result = await run_hermes_workflow(BlockedAdapter(), "tuvok", "review")

        self.assertEqual(result["status"], "budget_blocked")
        self.assertIn("profile 'tuvok'", result["error"])
        self.assertEqual(result["text"], "")
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["correlation_id"], "")
        self.assertEqual(result["usage"], {})
        self.assertEqual(result["tool_calls"], ())

    async def test_graph_blocks_when_budget_evidence_is_unavailable(self):
        class UnavailableEvidenceAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise BudgetEvidenceError(
                    f"cannot read cost evidence for {profile}"
                )

        result = await run_hermes_workflow(
            UnavailableEvidenceAdapter(), "barclay", "review"
        )

        self.assertEqual(result["status"], "budget_blocked")
        self.assertEqual(
            result["error"], "cannot read cost evidence for barclay"
        )
        self.assertEqual(result["text"], "")
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["correlation_id"], "")
        self.assertEqual(result["usage"], {})
        self.assertEqual(result["tool_calls"], ())

    async def test_graph_returns_shadow_reserve_required_without_provider_call(self):
        class ExhaustedPrimaryAdapter:
            calls = 0

            async def run_agent(self, profile, task, context, limits):
                self.calls += 1
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "Token Plan credits exhausted",
                )

        adapter = ExhaustedPrimaryAdapter()
        result = await run_hermes_workflow(
            adapter,
            "barclay",
            "sensitive prompt must not enter reserve request",
            task_id="FUTURE-01",
            reserve_role="flash",
            reserve_config=self._shadow_config(),
        )

        self.assertEqual(adapter.calls, 1)
        self.assertEqual(result["status"], "reserve_required")
        self.assertEqual(result["error"], "subscription_credits_exhausted")
        self.assertEqual(result["text"], "")
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["usage"], {})
        self.assertEqual(result["tool_calls"], ())
        self.assertEqual(result["reserve_request"]["task_id"], "FUTURE-01")
        self.assertEqual(
            result["reserve_request"]["reserve_model"], "deepseek-v4-flash"
        )
        self.assertNotIn("sensitive prompt", str(result["reserve_request"]))

    async def test_graph_returns_reserve_denied_after_explicit_denial(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
                    "Token Plan window exhausted",
                )

        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-02",
            reserve_decision="denied",
            reserve_config=self._shadow_config(),
        )

        self.assertEqual(result["status"], "reserve_denied")
        self.assertEqual(result["error"], "technical reserve denied by operator")
        self.assertEqual(result["reserve_request"]["task_id"], "FUTURE-02")
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["usage"], {})

    async def test_graph_keeps_security_and_local_failures_out_of_reserve(self):
        class InvalidPrimaryAdapter:
            def __init__(self, reason):
                self.reason = reason

            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    self.reason,
                    "provider detail must not authorize reserve",
                )

        blocked_reasons = (
            PrimaryFailureReason.AUTHENTICATION_FAILED,
            PrimaryFailureReason.AUTHORIZATION_FAILED,
            PrimaryFailureReason.INVALID_REQUEST,
            PrimaryFailureReason.TOOL_ERROR,
            PrimaryFailureReason.LOCAL_ERROR,
        )
        for reason in blocked_reasons:
            with self.subTest(reason=reason):
                result = await run_hermes_workflow(
                    InvalidPrimaryAdapter(reason),
                    "barclay",
                    "review",
                    task_id="FUTURE-03",
                    reserve_config=self._shadow_config(),
                )

                self.assertEqual(result["status"], "budget_blocked")
                self.assertEqual(result["error"], reason.value)
                self.assertEqual(result["reserve_request"], {})
                self.assertEqual(result["reserve_grant_id"], "")

    async def test_graph_kill_switch_prevents_shadow_request(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail must not be exposed",
                )

        config = TechnicalReserveConfig(
            mode=ReserveMode.SHADOW,
            kill_switch_active=True,
            enabled_profiles=frozenset({"barclay"}),
        )
        store = MagicMock()
        executor, provider = self._reserve_executor()
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-04",
            reserve_config=config,
            reserve_grant_store=store,
            reserve_budget_guard=self._budget_guard(),
            reserve_executor=executor,
        )

        self.assertEqual(result["status"], "budget_blocked")
        self.assertEqual(result["error"], "subscription_credits_exhausted")
        self.assertEqual(result["reserve_request"], {})
        store.consume_with_budget_and_cost.assert_not_called()
        provider.invoke_once.assert_not_called()

    async def test_graph_rejects_unknown_reserve_decision(self):
        class UnusedAdapter:
            async def run_agent(self, profile, task, context, limits):
                self.fail("adapter must not run")

        with self.assertRaisesRegex(ValueError, "not a valid ReserveDecision"):
            await run_hermes_workflow(
                UnusedAdapter(),
                "barclay",
                "review",
                reserve_decision="unknown",
                reserve_config=self._shadow_config(),
            )

    async def test_graph_consumes_grant_then_runs_fake_reserve_node(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                    session_id="qwen-session-1",
                )

        store = MagicMock()
        store.consume_with_budget_and_cost.return_value = True
        budget_guard = self._budget_guard()
        executor, provider = self._reserve_executor()
        scope = self._grant_scope()
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-05",
            reserve_decision="approved",
            reserve_config=self._enforced_config(),
            reserve_grant_store=store,
            reserve_grant_scope=scope,
            reserve_budget_guard=budget_guard,
            reserve_executor=executor,
            reserve_max_input_tokens=1000,
            reserve_max_output_tokens=1000,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["reserve_grant_id"], "grant-1")
        self.assertEqual(result["text"], "reserve ok")
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["usage"], {
            "prompt_cache_hit_tokens": 10,
            "prompt_cache_miss_tokens": 20,
            "completion_tokens": 30,
        })
        commitment = executor.prepare(
            grant_id="grant-1", task_id="FUTURE-05",
            model="deepseek-v4-flash", grant_max_cost_usd=0.04,
            max_input_tokens=1000, max_output_tokens=1000,
        )
        store.consume_with_budget_and_cost.assert_called_once_with(
            scope,
            budget_guard.check.return_value,
            commitment,
            daily_limit_usd=budget_guard.daily_limit_usd,
            monthly_limit_usd=budget_guard.monthly_limit_usd,
            attempt=store.consume_with_budget_and_cost.call_args.kwargs["attempt"],
        )
        attempt = store.consume_with_budget_and_cost.call_args.kwargs["attempt"]
        self.assertEqual(attempt.attempt_id, "reserve:grant-1")
        self.assertEqual(attempt.task_id, "FUTURE-05")
        self.assertEqual(attempt.primary_session_id, "qwen-session-1")
        store.finish_attempt.assert_called_once_with(
            "reserve:grant-1",
            ReserveAttemptStatus.COMPLETED,
            effective_model="deepseek-v4-flash",
            reserve_session_id="chatcmpl-reserve-1",
            latency_ms=ANY,
        )
        budget_guard.check.assert_called_once_with(0.04)
        provider.invoke_once.assert_called_once_with("deepseek-v4-flash")

    async def test_graph_denies_missing_reused_or_out_of_scope_grant(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                )

        store = MagicMock()
        store.consume_with_budget_and_cost.return_value = False
        budget_guard = self._budget_guard()
        executor, _ = self._reserve_executor()
        for scope in (None, self._grant_scope("OTHER"), self._grant_scope()):
            with self.subTest(scope=scope):
                result = await run_hermes_workflow(
                    ExhaustedPrimaryAdapter(),
                    "barclay",
                    "review",
                    task_id="FUTURE-05",
                    reserve_decision="approved",
                    reserve_config=self._enforced_config(),
                    reserve_grant_store=store,
                    reserve_grant_scope=scope,
                    reserve_budget_guard=budget_guard,
                    reserve_executor=executor,
                    reserve_max_input_tokens=1000,
                    reserve_max_output_tokens=1000,
                )
                self.assertEqual(result["status"], "reserve_denied")
        store.consume_with_budget_and_cost.assert_called_once()

    async def test_graph_reports_expired_grant_without_consuming_it(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                )

        store = MagicMock()
        executor, provider = self._reserve_executor()
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-05",
            reserve_decision="approved",
            reserve_config=self._enforced_config(),
            reserve_grant_store=store,
            reserve_grant_scope=self._grant_scope(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
            ),
            reserve_budget_guard=self._budget_guard(),
            reserve_executor=executor,
            reserve_max_input_tokens=1000,
            reserve_max_output_tokens=1000,
        )

        self.assertEqual(result["status"], "reserve_expired")
        self.assertEqual(result["error"], "technical reserve grant expired")
        store.consume_with_budget_and_cost.assert_not_called()
        provider.invoke_once.assert_not_called()

    async def test_budget_block_preserves_approved_grant(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                )

        store = MagicMock()
        budget_guard = self._budget_guard()
        executor, _ = self._reserve_executor()
        budget_guard.check.side_effect = ReserveBudgetExceededError(
            "direct reserve daily budget exceeded"
        )
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-05",
            reserve_decision="approved",
            reserve_config=self._enforced_config(),
            reserve_grant_store=store,
            reserve_grant_scope=self._grant_scope(),
            reserve_budget_guard=budget_guard,
            reserve_executor=executor,
            reserve_max_input_tokens=1000,
            reserve_max_output_tokens=1000,
        )

        self.assertEqual(result["status"], "budget_blocked")
        self.assertEqual(result["error"], "direct reserve daily budget exceeded")
        store.consume_with_budget_and_cost.assert_not_called()

    async def test_ambiguous_reserve_finishes_unknown_without_retry(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                )

        store = MagicMock()
        store.consume_with_budget_and_cost.return_value = True
        executor, provider = self._reserve_executor(
            ReserveOutcomeUnknownError("timeout")
        )
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(), "barclay", "review",
            task_id="FUTURE-05", reserve_decision="approved",
            reserve_config=self._enforced_config(),
            reserve_grant_store=store,
            reserve_grant_scope=self._grant_scope(),
            reserve_budget_guard=self._budget_guard(),
            reserve_executor=executor,
            reserve_max_input_tokens=1000,
            reserve_max_output_tokens=1000,
        )

        self.assertEqual(result["status"], "reserve_outcome_unknown")
        provider.invoke_once.assert_called_once_with("deepseek-v4-flash")
        store.finish_attempt.assert_called_once_with(
            "reserve:grant-1",
            ReserveAttemptStatus.OUTCOME_UNKNOWN,
            latency_ms=ANY,
        )

    async def test_shadow_approval_never_consumes_grant(self):
        class ExhaustedPrimaryAdapter:
            async def run_agent(self, profile, task, context, limits):
                raise PrimaryRouteError(
                    PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
                    "provider detail",
                )

        store = MagicMock()
        result = await run_hermes_workflow(
            ExhaustedPrimaryAdapter(),
            "barclay",
            "review",
            task_id="FUTURE-05",
            reserve_decision="approved",
            reserve_config=self._shadow_config(),
            reserve_grant_store=store,
            reserve_grant_scope=self._grant_scope(),
        )

        self.assertEqual(result["status"], "reserve_denied")
        store.consume.assert_not_called()

if __name__ == "__main__":
    unittest.main()
