from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel

from orchestrator.budget import BudgetError, DeepSeekBudgetGuard
from orchestrator.database import check_database
from orchestrator.graphs.smoke import run_smoke_workflow
from orchestrator.pilot_metrics import PostgresPilotMetricsStore
from orchestrator.pilot_summary import summarize_pilot
from orchestrator.settings import Settings
from orchestrator.telemetry import get_tracer


class SmokeRequest(BaseModel):
    message: str = "phase-3-smoke"


def create_app(
    settings: Settings,
    *,
    budget_guard: DeepSeekBudgetGuard | None = None,
    metrics_store: PostgresPilotMetricsStore | None = None,
    database_checker: Callable[[Settings], dict[str, str]] = check_database,
) -> FastAPI:
    guard = budget_guard or DeepSeekBudgetGuard(
        settings.hermes_profiles_root,
        daily_limit_usd=settings.deepseek_daily_budget_usd,
        pilot_limit_usd=settings.deepseek_pilot_budget_usd,
        pilot_started_at=settings.deepseek_pilot_started_at,
    )
    store = metrics_store or PostgresPilotMetricsStore(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database_checker(settings)
        guard.snapshot()
        yield

    app = FastAPI(
        title="Agent Orchestrator",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready() -> dict[str, object]:
        try:
            database = database_checker(settings)
            guard.snapshot()
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="runtime dependencies unavailable"
            ) from exc
        return {"status": "ready", "database": database}

    @app.get("/pilot/budget")
    def budget_snapshot() -> dict[str, float]:
        try:
            snapshot = guard.snapshot()
        except BudgetError as exc:
            raise HTTPException(
                status_code=503, detail="budget evidence unavailable"
            ) from exc
        return {
            "daily_spend_usd": snapshot.daily_spend_usd,
            "pilot_spend_usd": snapshot.pilot_spend_usd,
            "daily_limit_usd": guard.daily_limit_usd,
            "pilot_limit_usd": guard.pilot_limit_usd,
        }

    @app.get("/pilot/budget/check/{profile}")
    def budget_check(profile: str) -> dict[str, object]:
        try:
            snapshot = guard.check(profile)
        except BudgetError as exc:
            return {"status": "budget_blocked", "error": str(exc)}
        if snapshot is None:
            return {"status": "not_applicable", "profile": profile}
        return {
            "status": "available",
            "profile": profile,
            "daily_spend_usd": snapshot.daily_spend_usd,
            "pilot_spend_usd": snapshot.pilot_spend_usd,
        }

    @app.get("/pilot/summary")
    def pilot_summary() -> dict[str, object]:
        try:
            summary = summarize_pilot(store.list_all())
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="pilot ledger unavailable"
            ) from exc
        return {
            "sample_size": summary.sample_size,
            "recorded_tasks": summary.recorded_tasks,
            "first_attempt_tasks": summary.first_attempt_tasks,
            "completion_rate": summary.completion_rate,
            "first_attempt_rate": summary.first_attempt_rate,
            "api_calls": summary.api_calls,
            "latency_seconds": summary.latency_seconds,
            "cost_usd": summary.cost_usd,
            "simulated_cost_usd": summary.simulated_cost_usd,
            "billed_cost_usd": summary.billed_cost_usd,
            "subscription_savings_usd": summary.subscription_savings_usd,
        }

    @app.post("/workflows/smoke")
    def smoke(request: SmokeRequest) -> dict[str, str]:
        tracer = get_tracer()
        with tracer.start_as_current_span("workflow.smoke") as span:
            span.set_attribute("workflow.name", "smoke")
            span.set_attribute("workflow.has_model", False)
            try:
                result = run_smoke_workflow(request.message)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
            span.set_attribute("workflow.status", result["status"])
            return result

    return app
