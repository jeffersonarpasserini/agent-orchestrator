from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import psycopg

from orchestrator.technical_reserve import PrimaryFailureReason, ReserveRequest
from orchestrator.reserve_budget import (
    ReserveBudgetEvidenceError,
    ReserveBudgetExceededError,
    ReserveBudgetSnapshot,
)
from orchestrator.deepseek_reserve_finance import ReserveCostCommitment


class ReserveGrantStatus(StrEnum):
    APPROVED = "approved"
    CONSUMED = "consumed"
    REVOKED = "revoked"


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
        if self.max_calls != 1:
            raise ValueError("reserve grant permits exactly one call")
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

    def __post_init__(self) -> None:
        if self.max_cost_usd <= 0:
            raise ValueError("reserve call cost must be positive")

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
            connection.commit()
        return True

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
