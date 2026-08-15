from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import signal
from typing import Awaitable, Callable, Mapping, Sequence
import uuid
from orchestrator.adapters.hermes_session import SQLiteHermesSessionStore
from orchestrator.budget import DeepSeekBudgetGuard

_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
TIRITH_WARNING_LINE = (
    "⚠ tirith security scanner enabled but not available"
    " — command scanning will use pattern matching only."
)
_SESSION_PATTERNS = (
    re.compile(
        r"(?:session[_ ]id|session):\s*[`\[]?([A-Za-z0-9_-]+)[`\]]?",
        re.I,
    ),
    re.compile(r"\[session:\s*([A-Za-z0-9_-]+)\]", re.I),
)


class HermesAdapterError(RuntimeError):
    pass


class HermesSecurityError(HermesAdapterError):
    pass


class HermesFallbackError(HermesSecurityError):
    pass


class HermesTimeoutError(HermesAdapterError):
    pass


class HermesProcessError(HermesAdapterError):
    def __init__(self, message: str, *, returncode: int, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


@dataclass(frozen=True)
class AgentLimits:
    timeout_seconds: float = 120.0
    max_turns: int = 12
    toolsets: tuple[str, ...] = ()
    working_directory: Path | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 1 <= self.max_turns <= 500:
            raise ValueError("max_turns must be between 1 and 500")


@dataclass(frozen=True)
class ProcessOutput:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class HermesRunResult:
    profile: str
    text: str
    session_id: str | None
    correlation_id: str
    status: str = "completed"
    tool_calls: tuple[Mapping[str, object], ...] = ()
    usage: Mapping[str, object] = field(default_factory=dict)


Runner = Callable[[Sequence[str], Mapping[str, str], Path | None, float], Awaitable[ProcessOutput]]


async def _subprocess_runner(command, environment, cwd, timeout_seconds):
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=dict(environment),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        if process.returncode is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
            except asyncio.TimeoutError:
                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
        raise
    return ProcessOutput(
        process.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


class HermesCliAdapter:
    def __init__(self, executable="hermes", *, runner=_subprocess_runner, base_environment=None, session_store: SQLiteHermesSessionStore | None = None, budget_guard: DeepSeekBudgetGuard | None = None):
        self.executable = executable
        self._runner = runner
        self._base_environment = dict(base_environment or os.environ)
        self._session_store = session_store
        self._budget_guard = budget_guard

    async def run_agent(self, profile, task, context=None, limits=None):
        limits = limits or AgentLimits()
        if self._budget_guard is not None:
            await asyncio.to_thread(self._budget_guard.check, profile)
        environment = self._safe_environment()
        await self._assert_no_fallback(profile, environment, limits)
        correlation_id = uuid.uuid4().hex[:12]
        command = self.build_command(profile, task, context, limits, correlation_id)
        try:
            output = await self._runner(command, environment, limits.working_directory, limits.timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise HermesTimeoutError(
                f"Hermes profile {profile!r} exceeded {limits.timeout_seconds:g}s"
            ) from exc
        if output.returncode != 0:
            raise HermesProcessError(
                f"Hermes profile {profile!r} exited with code {output.returncode}",
                returncode=output.returncode,
                stderr=output.stderr.strip(),
            )
        text, session_id = self._normalize_stdout(output.stdout)
        if not text:
            raise HermesProcessError(
                f"Hermes profile {profile!r} returned an empty response",
                returncode=output.returncode,
                stderr=output.stderr.strip(),
            )
        if session_id is None:
            session_id = await self._resolve_session(profile, correlation_id, environment, limits)
        usage = {}
        tool_calls = ()
        if session_id is not None and self._session_store is not None:
            details = await asyncio.to_thread(self._session_store.read, profile, session_id)
            usage = details.usage
            tool_calls = details.tool_calls
        return HermesRunResult(profile, text, session_id, correlation_id, usage=usage, tool_calls=tool_calls)

    def build_command(self, profile, task, context, limits, correlation_id=None):
        if not _PROFILE_RE.fullmatch(profile):
            raise HermesSecurityError("invalid Hermes profile name")
        if not task.strip():
            raise ValueError("task must not be empty")
        prompt = task.strip()
        if correlation_id:
            prompt = f"[ao:{correlation_id}] {prompt}"
        if context:
            prompt += "\n\nOrchestration context (JSON):\n" + json.dumps(
                context, ensure_ascii=False, sort_keys=True
            )
        command = [
            self.executable, "-p", profile, "chat", "-q", prompt, "-Q",
            "--source", "tool", "--max-turns", str(limits.max_turns),
            "--pass-session-id",
        ]
        if limits.toolsets:
            command.extend(["--toolsets", ",".join(limits.toolsets)])
        return command

    async def _assert_no_fallback(self, profile, environment, limits):
        if not _PROFILE_RE.fullmatch(profile):
            raise HermesSecurityError("invalid Hermes profile name")
        output = await self._runner(
            [self.executable, "-p", profile, "fallback", "list"],
            environment,
            limits.working_directory,
            min(limits.timeout_seconds, 15.0),
        )
        combined = f"{output.stdout}\n{output.stderr}"
        if output.returncode != 0 or "No fallback providers configured" not in combined:
            raise HermesFallbackError(
                f"Hermes profile {profile!r} has an active or unverifiable fallback chain"
            )

    async def _resolve_session(self, profile, correlation_id, environment, limits):
        output = await self._runner(
            [self.executable, "-p", profile, "sessions", "list", "--source", "tool", "--limit", "20"],
            environment,
            limits.working_directory,
            min(limits.timeout_seconds, 15.0),
        )
        if output.returncode != 0:
            return None
        marker = f"[ao:{correlation_id}]"
        for line in output.stdout.splitlines():
            if marker in line:
                match = re.search(r"([0-9]{8}_[0-9]{6}_[A-Za-z0-9]+)\s*$", line)
                if match:
                    return match.group(1)
        return None

    def _safe_environment(self):
        environment = dict(self._base_environment)
        for key in list(environment):
            normalized = key.upper()
            if (
                normalized == "OPENAI_API_KEY"
                or normalized.endswith("_API_KEY")
                or normalized.endswith("_ACCESS_TOKEN")
                or normalized.endswith("_BEARER_TOKEN")
                or normalized.endswith("_DATABASE_URL")
            ):
                environment.pop(key, None)
        environment["HERMES_INTERACTIVE"] = "0"
        environment.pop("HERMES_YOLO_MODE", None)
        return environment

    @staticmethod
    def _normalize_stdout(stdout):
        normalized = stdout.replace("\r\n", "\n").strip()
        lines = normalized.split("\n")
        leading = 0
        while leading < len(lines) and lines[leading] == TIRITH_WARNING_LINE:
            leading += 1
        if leading:
            normalized = "\n".join(lines[leading:]).strip()
        session_id = None
        for pattern in _SESSION_PATTERNS:
            match = pattern.search(normalized)
            if match:
                session_id = match.group(1)
                normalized = pattern.sub("", normalized).strip(" \n-[]")
                break
        return normalized, session_id
