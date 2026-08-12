from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json

import psycopg


@dataclass(frozen=True)
class PilotTaskMetrics:
    task_id: str
    task_class: str
    result: str
    profiles_models: tuple[str, ...]
    attempts: int
    api_calls: int
    latency_seconds: float
    cost_usd: float
    evidence: tuple[str, ...]
    simulated_cost_usd: float | None = None
    billed_cost_usd: float | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.task_class.strip() or not self.result.strip():
            raise ValueError("task id, class and result must not be empty")
        if self.attempts <= 0 or self.api_calls < 0:
            raise ValueError("attempts must be positive and api calls non-negative")
        simulated = self.cost_usd if self.simulated_cost_usd is None else self.simulated_cost_usd
        billed = self.cost_usd if self.billed_cost_usd is None else self.billed_cost_usd
        if self.latency_seconds < 0 or min(self.cost_usd, simulated, billed) < 0:
            raise ValueError("latency and cost must be non-negative")
        if billed > simulated:
            raise ValueError("billed cost must not exceed simulated cost")
        if self.billed_cost_usd is not None and self.cost_usd != billed:
            raise ValueError("legacy cost must equal billed cost")
        object.__setattr__(self, "simulated_cost_usd", simulated)
        object.__setattr__(self, "billed_cost_usd", billed)


class PostgresPilotMetricsStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database URL must not be empty")
        self.database_url = database_url

    def record(self, metrics: PilotTaskMetrics) -> None:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orchestrator.pilot_task_metrics (
                        task_id, task_class, result, profiles_models, attempts,
                        api_calls, latency_seconds, cost_usd, evidence,
                        simulated_cost_usd, billed_cost_usd
                    ) VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                              %s::jsonb, %s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET
                        task_class = EXCLUDED.task_class,
                        result = EXCLUDED.result,
                        profiles_models = EXCLUDED.profiles_models,
                        attempts = EXCLUDED.attempts,
                        api_calls = EXCLUDED.api_calls,
                        latency_seconds = EXCLUDED.latency_seconds,
                        cost_usd = EXCLUDED.cost_usd,
                        evidence = EXCLUDED.evidence,
                        simulated_cost_usd = EXCLUDED.simulated_cost_usd,
                        billed_cost_usd = EXCLUDED.billed_cost_usd,
                        recorded_at = now()
                    """,
                    (
                        metrics.task_id,
                        metrics.task_class,
                        metrics.result,
                        json.dumps(metrics.profiles_models),
                        metrics.attempts,
                        metrics.api_calls,
                        metrics.latency_seconds,
                        metrics.cost_usd,
                        json.dumps(metrics.evidence),
                        metrics.simulated_cost_usd,
                        metrics.billed_cost_usd,
                    ),
                )
            connection.commit()

    def list_all(self) -> tuple[PilotTaskMetrics, ...]:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT task_id, task_class, result, profiles_models,
                           attempts, api_calls, latency_seconds, cost_usd,
                           evidence, simulated_cost_usd, billed_cost_usd
                      FROM orchestrator.pilot_task_metrics
                     ORDER BY task_id
                    """
                )
                rows = cursor.fetchall()
        return tuple(
            PilotTaskMetrics(
                task_id=row[0],
                task_class=row[1],
                result=row[2],
                profiles_models=tuple(row[3]),
                attempts=row[4],
                api_calls=row[5],
                latency_seconds=float(row[6]),
                cost_usd=float(row[7]),
                evidence=tuple(row[8]),
                simulated_cost_usd=float(row[9]),
                billed_cost_usd=float(row[10]),
            )
            for row in rows
        )
