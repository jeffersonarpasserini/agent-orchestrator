from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3

from orchestrator.model_costs import ModelCostEstimator
from orchestrator.pilot_metrics import PilotTaskMetrics, PostgresPilotMetricsStore


def session_metrics(profiles_root: Path, references: tuple[str, ...]):
    estimator = ModelCostEstimator()
    profiles_models: list[str] = []
    evidence: list[str] = []
    api_calls = 0
    latency = 0.0
    simulated = 0.0
    billed = 0.0
    for reference in references:
        try:
            profile, session_id = reference.split("/", 1)
        except ValueError as exc:
            raise ValueError("session reference must be PROFILE/SESSION_ID") from exc
        database = profiles_root / profile / "state.db"
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT model, billing_provider, billing_mode, api_call_count,
                       input_tokens, output_tokens, cache_read_tokens,
                       cache_write_tokens, reasoning_tokens, started_at, ended_at
                       , last_activity_at
                  FROM sessions WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"session evidence unavailable: {reference}")
        finished_at = row["ended_at"] or row["last_activity_at"]
        if finished_at is None:
            raise RuntimeError(f"session is incomplete: {reference}")
        cost = estimator.estimate_session(dict(row))
        profiles_models.append(f"{profile}/{row['model']}")
        evidence.append(session_id)
        api_calls += int(row["api_call_count"] or 0)
        latency += max(0.0, float(finished_at) - float(row["started_at"]))
        simulated += cost.simulated_cost_usd
        billed += cost.billed_cost_usd
    return tuple(profiles_models), tuple(evidence), api_calls, latency, simulated, billed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--result", default="approved")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument("--session", action="append", required=True)
    args = parser.parse_args(argv)
    database_url = os.environ.get("ORCHESTRATOR_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("ORCHESTRATOR_DATABASE_URL is required")
    profiles_models, evidence, calls, latency, simulated, billed = session_metrics(
        args.profiles_root, tuple(args.session)
    )
    metrics = PilotTaskMetrics(
        task_id=args.task_id,
        task_class=args.task_class,
        result=args.result,
        profiles_models=profiles_models,
        attempts=args.attempts,
        api_calls=calls,
        latency_seconds=latency,
        cost_usd=billed,
        evidence=evidence,
        simulated_cost_usd=simulated,
        billed_cost_usd=billed,
    )
    PostgresPilotMetricsStore(database_url).record(metrics)
    print(
        f"{metrics.task_id} calls={calls} latency={latency:.3f} "
        f"simulated={simulated:.12f} billed={billed:.12f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
