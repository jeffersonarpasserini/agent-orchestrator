from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Callable, Iterable

DEEPSEEK_PROFILES = frozenset({"barclay", "obrien", "rutherford", "tuvok"})

class BudgetError(RuntimeError):
    pass

class BudgetEvidenceError(BudgetError):
    pass

class BudgetExceededError(BudgetError):
    pass

@dataclass(frozen=True)
class BudgetSnapshot:
    daily_spend_usd: float
    pilot_spend_usd: float

class DeepSeekBudgetGuard:
    def __init__(self, profiles_root: Path, *, daily_limit_usd: float,
                 pilot_limit_usd: float, pilot_started_at: datetime,
                 profiles: Iterable[str] = DEEPSEEK_PROFILES,
                 now: Callable[[], datetime] | None = None) -> None:
        if daily_limit_usd <= 0 or pilot_limit_usd <= 0:
            raise ValueError("budget limits must be positive")
        if pilot_started_at.tzinfo is None:
            raise ValueError("pilot start must include a timezone")
        self.profiles_root = profiles_root
        self.daily_limit_usd = daily_limit_usd
        self.pilot_limit_usd = pilot_limit_usd
        self.operational_timezone = pilot_started_at.tzinfo
        self.pilot_started_at = pilot_started_at.astimezone(timezone.utc)
        self.profiles = frozenset(profiles)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def check(self, profile: str) -> BudgetSnapshot | None:
        if profile not in self.profiles:
            return None
        snapshot = self.snapshot()
        if snapshot.daily_spend_usd >= self.daily_limit_usd:
            raise BudgetExceededError(
                f"DeepSeek daily budget exhausted for profile {profile!r}"
            )
        if snapshot.pilot_spend_usd >= self.pilot_limit_usd:
            raise BudgetExceededError(
                f"DeepSeek pilot budget exhausted for profile {profile!r}"
            )
        return snapshot

    def snapshot(self) -> BudgetSnapshot:
        now = self._now().astimezone(self.operational_timezone)
        day_start = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
        daily = self._spend_since(day_start)
        pilot = self._spend_since(self.pilot_started_at)
        return BudgetSnapshot(daily, pilot)

    def _spend_since(self, started_at: datetime) -> float:
        total = 0.0
        for profile in self.profiles:
            database = self.profiles_root / profile / "state.db"
            if not database.is_file():
                raise BudgetEvidenceError(f"missing cost database for {profile}")
            try:
                with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
                    rows = connection.execute(
                        "SELECT actual_cost_usd, estimated_cost_usd FROM sessions "
                        "WHERE billing_provider = 'deepseek' AND started_at >= ?",
                        (started_at.timestamp(),),
                    ).fetchall()
            except sqlite3.Error as exc:
                raise BudgetEvidenceError(f"cannot read cost evidence for {profile}") from exc
            for actual, estimated in rows:
                cost = actual if actual is not None else estimated
                if cost is None or cost < 0:
                    raise BudgetEvidenceError(f"invalid cost evidence for {profile}")
                total += float(cost)
        return total
