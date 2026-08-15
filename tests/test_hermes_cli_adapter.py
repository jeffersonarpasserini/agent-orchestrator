import asyncio
from pathlib import Path
import unittest

from orchestrator.adapters.hermes_cli import (
    AgentLimits, HermesCliAdapter, HermesFallbackError, HermesProcessError,
    HermesSecurityError, HermesTimeoutError, ProcessOutput,
)

# Literal independente do aviso Tirith: espelha o texto exato sem importar a
# constante de produção, para que os testes quebrem se qualquer lado divergir.
_TIRITH_WARNING = (
    "⚠ tirith security scanner enabled but not available"
    " — command scanning will use pattern matching only."
)


class HermesCliAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_normalizes_response_and_session(self):
        captured = {}
        async def runner(command, environment, cwd, timeout):
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            captured.update(command=list(command), environment=environment, cwd=cwd, timeout=timeout)
            return ProcessOutput(0, "done\nSession ID: abc_123\n", "")
        adapter = HermesCliAdapter(runner=runner, base_environment={"OPENAI_API_KEY": "no", "PATH": "/bin"})
        result = await adapter.run_agent(
            "spock", "classify", {"correlation_id": "run-7"},
            AgentLimits(timeout_seconds=9, max_turns=3, working_directory=Path("/tmp")),
        )
        self.assertEqual(result.text, "done")
        self.assertEqual(result.session_id, "abc_123")
        self.assertRegex(result.correlation_id, r"^[0-9a-f]{12}$")
        self.assertNotIn("OPENAI_API_KEY", captured["environment"])
        self.assertNotIn("--yolo", captured["command"])
        self.assertEqual(captured["timeout"], 9)
        self.assertIn('"correlation_id": "run-7"', captured["command"][5])

    async def test_resolves_session_by_unique_marker(self):
        chat_prompt = None
        async def runner(command, *_):
            nonlocal chat_prompt
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            if "sessions" in command:
                marker = chat_prompt.split("]", 1)[0] + "]"
                return ProcessOutput(0, f"{marker} task  now  20260810_160000_abc123\n", "")
            chat_prompt = command[5]
            return ProcessOutput(0, "done", "")
        result = await HermesCliAdapter(runner=runner).run_agent("spock", "task")
        self.assertEqual(result.session_id, "20260810_160000_abc123")

    async def test_nonzero_exit_is_normalized(self):
        async def runner(command, *_):
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            return ProcessOutput(7, "", "provider unavailable")
        with self.assertRaises(HermesProcessError) as raised:
            await HermesCliAdapter(runner=runner).run_agent("spock", "task")
        self.assertEqual(raised.exception.returncode, 7)

    async def test_timeout_is_normalized(self):
        async def runner(command, *_):
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            raise asyncio.TimeoutError
        with self.assertRaises(HermesTimeoutError):
            await HermesCliAdapter(runner=runner).run_agent("spock", "task", limits=AgentLimits(timeout_seconds=1))

    async def test_cancellation_is_not_swallowed(self):
        async def runner(command, *_):
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            raise asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await HermesCliAdapter(runner=runner).run_agent("spock", "task")

    async def test_subprocess_does_not_inherit_provider_tokens_or_database_urls(self):
        captured = {}

        async def runner(command, environment, *_):
            captured.update(environment)
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            return ProcessOutput(0, "ok", "")

        adapter = HermesCliAdapter(
            runner=runner,
            base_environment={
                "PATH": "/bin",
                "DEEPSEEK_API_KEY": "direct-secret",
                "ALIBABA_ACCESS_TOKEN": "primary-secret",
                "TASK_INTAKE_BEARER_TOKEN": "intake-secret",
                "ORCHESTRATOR_DATABASE_URL": "postgresql://private",
            },
        )

        await adapter.run_agent("spock", "task")

        self.assertEqual(captured["PATH"], "/bin")
        for secret in (
            "DEEPSEEK_API_KEY",
            "ALIBABA_ACCESS_TOKEN",
            "TASK_INTAKE_BEARER_TOKEN",
            "ORCHESTRATOR_DATABASE_URL",
        ):
            self.assertNotIn(secret, captured)

    def test_rejects_profile_argument_injection(self):
        with self.assertRaises(HermesSecurityError):
            HermesCliAdapter().build_command("spock --yolo", "task", None, AgentLimits())

    async def test_rejects_configured_fallback(self):
        async def runner(*_):
            return ProcessOutput(0, "1. openai/gpt-4o", "")
        with self.assertRaises(HermesFallbackError):
            await HermesCliAdapter(runner=runner).run_agent("spock", "task")

    async def _run_with_stdout(self, stdout):
        async def runner(command, *_):
            if "fallback" in command:
                return ProcessOutput(0, "No fallback providers configured.", "")
            return ProcessOutput(0, stdout, "")
        return await HermesCliAdapter(runner=runner).run_agent("spock", "task")

    async def test_removes_leading_tirith_warning_before_json(self):
        payload = '{"answer": "ok"}'
        result = await self._run_with_stdout(f"{_TIRITH_WARNING}\n{payload}\n")
        self.assertEqual(result.text, payload)

    async def test_removes_leading_tirith_warning_before_json_with_crlf(self):
        payload = '{"answer": "ok"}'
        result = await self._run_with_stdout(f"{_TIRITH_WARNING}\r\n{payload}\r\n")
        self.assertEqual(result.text, payload)

    async def test_removes_multiple_leading_tirith_warning_lines(self):
        payload = '{"answer": "ok"}'
        result = await self._run_with_stdout(
            f"{_TIRITH_WARNING}\n{_TIRITH_WARNING}\n{payload}\n"
        )
        self.assertEqual(result.text, payload)

    def test_warning_only_stdout_normalizes_to_empty_text(self):
        for stdout in (f"{_TIRITH_WARNING}\n", f"{_TIRITH_WARNING}\r\n"):
            text, session_id = HermesCliAdapter._normalize_stdout(stdout)
            self.assertEqual(text, "")
            self.assertIsNone(session_id)

    async def test_warning_only_stdout_raises_empty_response(self):
        with self.assertRaises(HermesProcessError):
            await self._run_with_stdout(f"{_TIRITH_WARNING}\n{_TIRITH_WARNING}\n")

    async def test_output_without_tirith_warning_is_unchanged(self):
        result = await self._run_with_stdout("done\nSession ID: abc_123\n")
        self.assertEqual(result.text, "done")
        self.assertEqual(result.session_id, "abc_123")

    async def test_normalizes_session_id_surrounded_by_backticks(self):
        result = await self._run_with_stdout("done\nSession ID: `abc_123`\n")
        self.assertEqual(result.text, "done")
        self.assertEqual(result.session_id, "abc_123")

    async def test_tirith_warning_after_payload_start_is_preserved(self):
        stdout = f'{{"answer": "ok"}}\n{_TIRITH_WARNING}\n'
        result = await self._run_with_stdout(stdout)
        self.assertEqual(result.text, stdout.strip())

    async def test_tirith_warning_removed_with_session_id_present(self):
        result = await self._run_with_stdout(
            f"{_TIRITH_WARNING}\ndone\nSession ID: abc_123\n"
        )
        self.assertEqual(result.text, "done")
        self.assertEqual(result.session_id, "abc_123")


if __name__ == "__main__":
    unittest.main()
