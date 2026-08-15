from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

import psycopg

from orchestrator.agent_team import can_authorize
from orchestrator.technical_reserve import PrimaryFailureReason, ReserveRequest
from orchestrator.reserve_budget import (
    ReserveBudgetEvidenceError,
    ReserveBudgetExceededError,
    ReserveBudgetSnapshot,
)
from orchestrator.deepseek_reserve_finance import ReserveCostCommitment
from orchestrator.reserve_ledger import ReserveAttempt, ReserveAttemptStatus


class ReserveGrantStatus(StrEnum):
    APPROVED = "approved"
    CONSUMED = "consumed"
    REVOKED = "revoked"


MAX_RESERVE_GRANT_USD = 0.10
MAX_RESERVE_TASK_USD = 0.25


@dataclass(frozen=True)
class ReserveGrant:
    grant_id: str
    task_id: str
    profile: str
    role: str
    primary_model: str
    reserve_model: str
    primary_failure_reason: PrimaryFailureReason
    approved_by: str
    max_cost_usd: float
    max_calls: int
    expires_at: datetime

    def __post_init__(self) -> None:
        required = (
            self.grant_id,
            self.task_id,
            self.profile,
            self.role,
            self.primary_model,
            self.reserve_model,
            self.approved_by,
        )
        if any(not value.strip() for value in required):
            raise ValueError("reserve grant fields must not be empty")
        if self.max_cost_usd <= 0:
            raise ValueError("reserve grant cost must be positive")
        if self.max_cost_usd > MAX_RESERVE_GRANT_USD:
            raise ValueError("reserve grant cost exceeds the approved USD 0.10 cap")
        if self.max_calls != 1:
            raise ValueError("reserve grant permits exactly one call")
        if not can_authorize(self.approved_by, "approve_grant"):
            raise PermissionError("reserve grant approver is not authorized")
        if self.expires_at.tzinfo is None:
            raise ValueError("reserve grant expiration must include a timezone")


@dataclass(frozen=True)
class ReserveGrantScope:
    grant_id: str
    task_id: str
    profile: str
    role: str
    primary_model: str
    reserve_model: str
    max_cost_usd: float
    primary_failure_reason: PrimaryFailureReason
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.max_cost_usd <= 0:
            raise ValueError("reserve call cost must be positive")
        if self.max_cost_usd > MAX_RESERVE_GRANT_USD:
            raise ValueError("reserve call cost exceeds the approved USD 0.10 cap")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("reserve grant scope expiration must include a timezone")

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        observed_at = now or datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            raise ValueError("reserve expiration check must include a timezone")
        return self.expires_at <= observed_at

    def matches(self, request: ReserveRequest) -> bool:
        return (
            self.task_id == request.task_id
            and self.profile == request.profile
            and self.role == request.role
            and self.primary_model == request.primary_model
            and self.reserve_model == request.reserve_model
            and self.primary_failure_reason is request.reason
        )


class PostgresReserveGrantStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database URL must not be empty")
        self.database_url = database_url

    def create_approved(self, grant: ReserveGrant) -> None:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orchestrator.deepseek_reserve_grants (
                        grant_id, task_id, profile, role, primary_model,
                        reserve_model, primary_failure_reason, approved_by,
                        max_cost_usd, max_calls, expires_at, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              'approved')
                    """,
                    (
                        grant.grant_id,
                        grant.task_id,
                        grant.profile,
                        grant.role,
                        grant.primary_model,
                        grant.reserve_model,
                        grant.primary_failure_reason.value,
                        grant.approved_by,
                        grant.max_cost_usd,
                        grant.max_calls,
                        grant.expires_at,
                    ),
                )
            connection.commit()

    def consume(self, scope: ReserveGrantScope) -> bool:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_grants
                       SET status = 'consumed', consumed_at = now()
                     WHERE grant_id = %s
                       AND task_id = %s
                       AND profile = %s
                       AND role = %s
                       AND primary_model = %s
                       AND reserve_model = %s
                       AND primary_failure_reason = %s
                       AND status = 'approved'
                       AND expires_at > now()
                       AND max_calls = 1
                       AND max_cost_usd >= %s
                    RETURNING grant_id
                    """,
                    (
                        scope.grant_id,
                        scope.task_id,
                        scope.profile,
                        scope.role,
                        scope.primary_model,
                        scope.reserve_model,
                        scope.primary_failure_reason.value,
                        scope.max_cost_usd,
                    ),
                )
                consumed = cursor.fetchone() is not None
            connection.commit()
        return consumed

    def consume_with_budget(
        self,
        scope: ReserveGrantScope,
        snapshot: ReserveBudgetSnapshot,
        *,
        daily_limit_usd: float,
        monthly_limit_usd: float,
    ) -> bool:
        """Revalidate local budgets and consume a grant in one transaction.

        The transaction-scoped advisory lock serializes all reserve commitments.
        This closes the race where concurrent approvals could both observe the
        same spend total and then exceed a local daily or monthly limit.
        """
        if daily_limit_usd <= 0 or monthly_limit_usd <= 0:
            raise ValueError("reserve budget limits must be positive")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    ("deepseek_direct_reserve_budget",),
                )
                cursor.execute(
                    """
                    SELECT
                        COALESCE(sum(max_cost_usd) FILTER (
                            WHERE consumed_at >= %s
                        ), 0),
                        COALESCE(sum(max_cost_usd) FILTER (
                            WHERE consumed_at >= %s
                        ), 0)
                      FROM orchestrator.deepseek_reserve_grants
                     WHERE status = 'consumed' AND consumed_at >= %s
                    """,
                    (
                        snapshot.day_started_at,
                        snapshot.month_started_at,
                        snapshot.month_started_at,
                    ),
                )
                daily, monthly = (float(value) for value in cursor.fetchone())
                if daily + scope.max_cost_usd > daily_limit_usd:
                    raise ReserveBudgetExceededError(
                        "direct reserve daily budget exceeded"
                    )
                if monthly + scope.max_cost_usd > monthly_limit_usd:
                    raise ReserveBudgetExceededError(
                        "direct reserve monthly budget exceeded"
                    )
                cursor.execute(
                    """
                    SELECT COALESCE(sum(max_cost_usd), 0)
                      FROM orchestrator.deepseek_reserve_grants
                     WHERE task_id = %s AND status = 'consumed'
                    """,
                    (scope.task_id,),
                )
                task_total = float(cursor.fetchone()[0])
                if task_total + scope.max_cost_usd > MAX_RESERVE_TASK_USD:
                    raise ReserveBudgetExceededError(
                        "direct reserve task budget exceeded"
                    )
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_grants
                       SET status = 'consumed', consumed_at = now()
                     WHERE grant_id = %s
                       AND task_id = %s
                       AND profile = %s
                       AND role = %s
                       AND primary_model = %s
                       AND reserve_model = %s
                       AND primary_failure_reason = %s
                       AND status = 'approved'
                       AND expires_at > now()
                       AND max_calls = 1
                       AND max_cost_usd >= %s
                    RETURNING grant_id
                    """,
                    (
                        scope.grant_id,
                        scope.task_id,
                        scope.profile,
                        scope.role,
                        scope.primary_model,
                        scope.reserve_model,
                        scope.primary_failure_reason.value,
                        scope.max_cost_usd,
                    ),
                )
                consumed = cursor.fetchone() is not None
            connection.commit()
        return consumed

    def consume_with_budget_and_cost(
        self,
        scope: ReserveGrantScope,
        snapshot: ReserveBudgetSnapshot,
        commitment: ReserveCostCommitment,
        *,
        daily_limit_usd: float,
        monthly_limit_usd: float,
        attempt: ReserveAttempt | None = None,
    ) -> bool:
        if (
            commitment.grant_id != scope.grant_id
            or commitment.task_id != scope.task_id
            or commitment.model != scope.reserve_model
            or commitment.estimated_max_cost_usd > scope.max_cost_usd
        ):
            raise ReserveBudgetExceededError(
                "reserve cost commitment is outside grant scope"
            )
        if daily_limit_usd <= 0 or monthly_limit_usd <= 0:
            raise ValueError("reserve budget limits must be positive")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    ("deepseek_direct_reserve_budget",),
                )
                cursor.execute(
                    """
                    SELECT
                        COALESCE(sum(max_cost_usd) FILTER (
                            WHERE consumed_at >= %s
                        ), 0),
                        COALESCE(sum(max_cost_usd) FILTER (
                            WHERE consumed_at >= %s
                        ), 0)
                      FROM orchestrator.deepseek_reserve_grants
                     WHERE status = 'consumed' AND consumed_at >= %s
                    """,
                    (
                        snapshot.day_started_at,
                        snapshot.month_started_at,
                        snapshot.month_started_at,
                    ),
                )
                daily, monthly = (float(value) for value in cursor.fetchone())
                if daily + scope.max_cost_usd > daily_limit_usd:
                    raise ReserveBudgetExceededError(
                        "direct reserve daily budget exceeded"
                    )
                if monthly + scope.max_cost_usd > monthly_limit_usd:
                    raise ReserveBudgetExceededError(
                        "direct reserve monthly budget exceeded"
                    )
                cursor.execute(
                    """
                    SELECT COALESCE(sum(max_cost_usd), 0)
                      FROM orchestrator.deepseek_reserve_grants
                     WHERE task_id = %s AND status = 'consumed'
                    """,
                    (scope.task_id,),
                )
                task_total = float(cursor.fetchone()[0])
                if task_total + scope.max_cost_usd > MAX_RESERVE_TASK_USD:
                    raise ReserveBudgetExceededError(
                        "direct reserve task budget exceeded"
                    )
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_grants
                       SET status = 'consumed', consumed_at = now()
                     WHERE grant_id = %s AND task_id = %s AND profile = %s
                       AND role = %s AND primary_model = %s
                       AND reserve_model = %s AND primary_failure_reason = %s
                       AND status = 'approved' AND expires_at > now()
                       AND max_calls = 1 AND max_cost_usd >= %s
                    RETURNING grant_id
                    """,
                    (
                        scope.grant_id, scope.task_id, scope.profile, scope.role,
                        scope.primary_model, scope.reserve_model,
                        scope.primary_failure_reason.value, scope.max_cost_usd,
                    ),
                )
                if cursor.fetchone() is None:
                    return False
                cursor.execute(
                    """
                    INSERT INTO orchestrator.deepseek_reserve_costs (
                        grant_id, task_id, model, price_snapshot,
                        estimated_max_cost_usd, status
                    ) VALUES (%s, %s, %s, %s, %s, 'committed')
                    ON CONFLICT (grant_id) DO NOTHING
                    RETURNING grant_id
                    """,
                    (
                        commitment.grant_id, commitment.task_id,
                        commitment.model, commitment.price_snapshot,
                        commitment.estimated_max_cost_usd,
                    ),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError(
                        "reserve cost commitment already exists"
                    )
                if attempt is not None:
                    if (
                        attempt.grant_id != scope.grant_id
                        or attempt.task_id != scope.task_id
                        or attempt.requested_model != scope.reserve_model
                        or attempt.primary_failure_reason
                        is not scope.primary_failure_reason
                    ):
                        raise ReserveBudgetEvidenceError(
                            "reserve attempt is outside grant scope"
                        )
                    cursor.execute(
                        """
                        INSERT INTO orchestrator.deepseek_reserve_attempts (
                            attempt_id, task_id, grant_id, approved_by,
                            billing_route, primary_failure_reason,
                            requested_model, primary_session_id, status
                        ) SELECT %s, %s, %s, grant_row.approved_by, %s, %s, %s,
                                 %s, 'reserve_running'
                            FROM orchestrator.deepseek_reserve_grants AS grant_row
                           WHERE grant_row.grant_id = %s
                        ON CONFLICT (attempt_id) DO NOTHING
                        RETURNING attempt_id
                        """,
                        (
                            attempt.attempt_id, attempt.task_id,
                            attempt.grant_id, attempt.billing_route.value,
                            attempt.primary_failure_reason.value,
                            attempt.requested_model,
                            attempt.primary_session_id,
                            attempt.grant_id,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise ReserveBudgetEvidenceError(
                            "reserve attempt already exists"
                        )
            connection.commit()
        return True

    def finish_attempt(
        self,
        attempt_id: str,
        status: ReserveAttemptStatus,
        *,
        effective_model: str | None = None,
        reserve_session_id: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        if not attempt_id.strip() or status is ReserveAttemptStatus.RUNNING:
            raise ValueError("reserve attempt finalization requires a terminal state")
        if latency_ms is not None and latency_ms < 0:
            raise ValueError("reserve attempt latency must not be negative")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_attempts AS attempt
                       SET status = %s,
                           effective_model = %s,
                           prompt_cache_hit_tokens = cost.prompt_cache_hit_tokens,
                           prompt_cache_miss_tokens = cost.prompt_cache_miss_tokens,
                           completion_tokens = cost.completion_tokens,
                           direct_cost_usd = cost.actual_cost_usd,
                           reserve_session_id = %s,
                           latency_ms = %s,
                           finished_at = now()
                      FROM orchestrator.deepseek_reserve_costs AS cost
                     WHERE attempt.attempt_id = %s
                       AND attempt.grant_id = cost.grant_id
                       AND attempt.status = 'reserve_running'
                       AND (
                           %s <> 'completed'
                           OR cost.status = 'reconciled'
                       )
                    RETURNING attempt.attempt_id
                    """,
                    (
                        status.value, effective_model, reserve_session_id,
                        latency_ms, attempt_id, status.value,
                    ),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        """
                        SELECT status, effective_model, reserve_session_id,
                               latency_ms
                          FROM orchestrator.deepseek_reserve_attempts
                         WHERE attempt_id = %s
                        """,
                        (attempt_id,),
                    )
                    current = cursor.fetchone()
                    expected_model = effective_model if status is ReserveAttemptStatus.COMPLETED else None
                    if current != (
                        status.value, expected_model, reserve_session_id, latency_ms
                    ):
                        raise ReserveBudgetEvidenceError(
                            "reserve attempt cannot be finalized"
                        )
            connection.commit()

    def revoke(self, grant_id: str) -> bool:
        if not grant_id.strip():
            raise ValueError("grant id must not be empty")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_grants
                       SET status = 'revoked', revoked_at = now()
                     WHERE grant_id = %s AND status = 'approved'
                    RETURNING grant_id
                    """,
                    (grant_id,),
                )
                revoked = cursor.fetchone() is not None
            connection.commit()
        return revoked
