from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

import psycopg

from orchestrator.deepseek_reserve_finance import DeepSeekUsage
from orchestrator.technical_reserve import BillingRoute, PrimaryFailureReason


class ReserveAttemptStatus(StrEnum):
    RUNNING = "reserve_running"
    COMPLETED = "completed"
    FAILED = "reserve_failed"
    OUTCOME_UNKNOWN = "reserve_outcome_unknown"
    BUDGET_BLOCKED = "budget_blocked"


@dataclass(frozen=True)
class ReserveAttempt:
    attempt_id: str
    task_id: str
    grant_id: str
    primary_failure_reason: PrimaryFailureReason
    requested_model: str
    primary_session_id: str | None = None
    billing_route: BillingRoute = BillingRoute.DEEPSEEK_RESERVE

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.attempt_id,
                self.task_id,
                self.grant_id,
                self.requested_model,
            )
        ):
            raise ValueError("reserve attempt identifiers must not be empty")
        if self.billing_route is not BillingRoute.DEEPSEEK_RESERVE:
            raise ValueError("reserve attempt must use the direct reserve route")


@dataclass(frozen=True)
class ReserveAttemptResult:
    attempt_id: str
    status: ReserveAttemptStatus
    effective_model: str | None = None
    usage: DeepSeekUsage | None = None
    direct_cost_usd: float | None = None
    reserve_session_id: str | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.attempt_id.strip():
            raise ValueError("reserve attempt id must not be empty")
        if self.status is ReserveAttemptStatus.RUNNING:
            raise ValueError("reserve result must be terminal")
        if self.direct_cost_usd is not None and self.direct_cost_usd < 0:
            raise ValueError("reserve direct cost must not be negative")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("reserve latency must not be negative")
        if self.status is ReserveAttemptStatus.COMPLETED:
            if (
                not self.effective_model
                or self.usage is None
                or self.direct_cost_usd is None
            ):
                raise ValueError("completed reserve result requires model, usage and cost")


@dataclass(frozen=True)
class ReserveMetricsSnapshot:
    total_activations: int
    status_counts: Mapping[str, int]
    model_counts: Mapping[str, int]
    direct_cost_usd: float
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int
    completion_tokens: int

    def __post_init__(self) -> None:
        numeric = (
            self.total_activations,
            self.direct_cost_usd,
            self.prompt_cache_hit_tokens,
            self.prompt_cache_miss_tokens,
            self.completion_tokens,
            *self.status_counts.values(),
            *self.model_counts.values(),
        )
        if any(value < 0 for value in numeric):
            raise ValueError("reserve metrics must not be negative")


class PostgresReserveLedger:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database URL must not be empty")
        self.database_url = database_url

    def start(self, attempt: ReserveAttempt) -> None:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orchestrator.deepseek_reserve_attempts (
                        attempt_id, task_id, grant_id, approved_by,
                        billing_route, primary_failure_reason, requested_model,
                        primary_session_id, status
                    ) SELECT %s, %s, %s, grant_row.approved_by, %s, %s, %s, %s,
                             'reserve_running'
                        FROM orchestrator.deepseek_reserve_grants AS grant_row
                       WHERE grant_row.grant_id = %s
                    ON CONFLICT (attempt_id) DO NOTHING
                    """,
                    (
                        attempt.attempt_id,
                        attempt.task_id,
                        attempt.grant_id,
                        attempt.billing_route.value,
                        attempt.primary_failure_reason.value,
                        attempt.requested_model,
                        attempt.primary_session_id,
                        attempt.grant_id,
                    ),
                )
                cursor.execute(
                    """
                    SELECT task_id, grant_id, billing_route,
                           primary_failure_reason, requested_model,
                           primary_session_id
                      FROM orchestrator.deepseek_reserve_attempts
                     WHERE attempt_id = %s
                     FOR UPDATE
                    """,
                    (attempt.attempt_id,),
                )
                row = cursor.fetchone()
                expected = (
                    attempt.task_id,
                    attempt.grant_id,
                    attempt.billing_route.value,
                    attempt.primary_failure_reason.value,
                    attempt.requested_model,
                    attempt.primary_session_id,
                )
                if row != expected:
                    raise ValueError("reserve attempt id conflicts with existing scope")
            connection.commit()

    def finish(self, result: ReserveAttemptResult) -> None:
        usage = result.usage
        values = (
            result.status.value,
            result.effective_model,
            usage.prompt_cache_hit_tokens if usage else None,
            usage.prompt_cache_miss_tokens if usage else None,
            usage.completion_tokens if usage else None,
            result.direct_cost_usd,
            result.reserve_session_id,
            result.latency_ms,
        )
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status, effective_model, prompt_cache_hit_tokens,
                           prompt_cache_miss_tokens, completion_tokens,
                           direct_cost_usd, reserve_session_id, latency_ms
                      FROM orchestrator.deepseek_reserve_attempts
                     WHERE attempt_id = %s
                     FOR UPDATE
                    """,
                    (result.attempt_id,),
                )
                current = cursor.fetchone()
                if current is None:
                    raise ValueError("reserve attempt does not exist")
                normalized = tuple(
                    float(value) if index == 5 and value is not None else value
                    for index, value in enumerate(current)
                )
                if normalized == values:
                    connection.commit()
                    return
                if current[0] != ReserveAttemptStatus.RUNNING.value:
                    raise ValueError("reserve attempt already has a different result")
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_attempts
                       SET status = %s, effective_model = %s,
                           prompt_cache_hit_tokens = %s,
                           prompt_cache_miss_tokens = %s,
                           completion_tokens = %s, direct_cost_usd = %s,
                           reserve_session_id = %s, latency_ms = %s,
                           finished_at = now()
                     WHERE attempt_id = %s AND status = 'reserve_running'
                    """,
                    (*values, result.attempt_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("reserve attempt changed during finalization")
            connection.commit()

    def metrics_snapshot(self) -> ReserveMetricsSnapshot:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*),
                           count(*) FILTER (WHERE status = 'reserve_running'),
                           count(*) FILTER (WHERE status = 'completed'),
                           count(*) FILTER (WHERE status = 'reserve_failed'),
                           count(*) FILTER (WHERE status = 'reserve_outcome_unknown'),
                           count(*) FILTER (WHERE status = 'budget_blocked'),
                           COALESCE(sum(direct_cost_usd), 0),
                           COALESCE(sum(prompt_cache_hit_tokens), 0),
                           COALESCE(sum(prompt_cache_miss_tokens), 0),
                           COALESCE(sum(completion_tokens), 0)
                      FROM orchestrator.deepseek_reserve_attempts
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("reserve metrics are unavailable")
                cursor.execute(
                    """
                    SELECT COALESCE(effective_model, requested_model), count(*)
                      FROM orchestrator.deepseek_reserve_attempts
                     GROUP BY COALESCE(effective_model, requested_model)
                     ORDER BY COALESCE(effective_model, requested_model)
                    """
                )
                model_counts = {model: int(count) for model, count in cursor.fetchall()}
        return ReserveMetricsSnapshot(
            total_activations=int(row[0]),
            status_counts={
                "reserve_running": int(row[1]),
                "completed": int(row[2]),
                "reserve_failed": int(row[3]),
                "reserve_outcome_unknown": int(row[4]),
                "budget_blocked": int(row[5]),
            },
            model_counts=model_counts,
            direct_cost_usd=float(row[6]),
            prompt_cache_hit_tokens=int(row[7]),
            prompt_cache_miss_tokens=int(row[8]),
            completion_tokens=int(row[9]),
        )
