from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import Callable, Protocol

import psycopg


class ReserveBudgetError(RuntimeError):
    pass


class ReserveBudgetEvidenceError(ReserveBudgetError):
    pass


class ReserveBudgetExceededError(ReserveBudgetError):
    pass


@dataclass(frozen=True)
class DirectBalanceSnapshot:
    is_available: bool
    total_balance_usd: float

    def __post_init__(self) -> None:
        if self.total_balance_usd < 0:
            raise ValueError("direct balance must not be negative")


@dataclass(frozen=True)
class ReserveBudgetSnapshot:
    balance_usd: float
    daily_committed_usd: float
    monthly_committed_usd: float
    requested_usd: float
    day_started_at: datetime
    month_started_at: datetime


class DirectBalanceReader(Protocol):
    def read(self) -> DirectBalanceSnapshot: ...


class ReserveSpendEvidence(Protocol):
    def committed_since(self, started_at: datetime) -> float: ...


class PostgresReserveSpendEvidence:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database URL must not be empty")
        self.database_url = database_url

    def committed_since(self, started_at: datetime) -> float:
        if started_at.tzinfo is None:
            raise ValueError("spend evidence start must include a timezone")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(sum(max_cost_usd), 0)
                      FROM orchestrator.deepseek_reserve_grants
                     WHERE status = 'consumed' AND consumed_at >= %s
                    """,
                    (started_at,),
                )
                value = cursor.fetchone()[0]
        committed = float(value)
        if committed < 0:
            raise ReserveBudgetEvidenceError("invalid reserve spend evidence")
        return committed


class DirectReserveBudgetGuard:
    def __init__(
        self,
        balance_reader: DirectBalanceReader,
        spend_evidence: ReserveSpendEvidence,
        *,
        daily_limit_usd: float,
        monthly_limit_usd: float,
        operational_timezone: tzinfo = timezone.utc,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if daily_limit_usd <= 0 or monthly_limit_usd <= 0:
            raise ValueError("reserve budget limits must be positive")
        self.balance_reader = balance_reader
        self.spend_evidence = spend_evidence
        self.daily_limit_usd = daily_limit_usd
        self.monthly_limit_usd = monthly_limit_usd
        self.operational_timezone = operational_timezone
        self._now = now or (lambda: datetime.now(timezone.utc))

    def check(self, requested_usd: float) -> ReserveBudgetSnapshot:
        if requested_usd <= 0:
            raise ValueError("requested reserve cost must be positive")
        now = self._now()
        if now.tzinfo is None:
            raise ReserveBudgetEvidenceError("reserve clock must include a timezone")
        local_now = now.astimezone(self.operational_timezone)
        day_start = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
        month_start = local_now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
        try:
            balance = self.balance_reader.read()
            daily = self.spend_evidence.committed_since(day_start)
            monthly = self.spend_evidence.committed_since(month_start)
        except ReserveBudgetError:
            raise
        except Exception as exc:
            raise ReserveBudgetEvidenceError(
                "cannot validate direct reserve evidence"
            ) from exc
        if not balance.is_available:
            raise ReserveBudgetExceededError("direct reserve balance unavailable")
        if daily < 0 or monthly < 0:
            raise ReserveBudgetEvidenceError("invalid reserve spend evidence")
        if balance.total_balance_usd < requested_usd:
            raise ReserveBudgetExceededError("direct reserve balance insufficient")
        if daily + requested_usd > self.daily_limit_usd:
            raise ReserveBudgetExceededError("direct reserve daily budget exceeded")
        if monthly + requested_usd > self.monthly_limit_usd:
            raise ReserveBudgetExceededError("direct reserve monthly budget exceeded")
        return ReserveBudgetSnapshot(
            balance_usd=balance.total_balance_usd,
            daily_committed_usd=daily,
            monthly_committed_usd=monthly,
            requested_usd=requested_usd,
            day_started_at=day_start,
            month_started_at=month_start,
        )
