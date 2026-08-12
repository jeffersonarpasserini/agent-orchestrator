from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Iterable

from orchestrator.model_costs import CostBreakdown, ModelCostEstimator
from orchestrator.pilot_metrics import PilotTaskMetrics, PostgresPilotMetricsStore


SESSION_ID = re.compile(r"^\d{8}_\d{6}_[0-9a-f]+$")


def calculate_evidence_costs(
    profiles_root: Path,
    evidence: Iterable[str],
    estimator: ModelCostEstimator | None = None,
) -> tuple[CostBreakdown, ...]:
    estimator = estimator or ModelCostEstimator()
    wanted = {value for value in evidence if SESSION_ID.fullmatch(value)}
    found: dict[str, CostBreakdown] = {}
    for database in sorted(profiles_root.glob("*/state.db")):
        try:
            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            try:
                for session_id in wanted - found.keys():
                    row = connection.execute(
                        """
                        SELECT model, billing_provider, billing_mode,
                               input_tokens, output_tokens, cache_read_tokens,
                               cache_write_tokens, reasoning_tokens
                          FROM sessions WHERE id = ?
                        """,
                        (session_id,),
                    ).fetchone()
                    if row is not None:
                        found[session_id] = estimator.estimate_session(dict(row))
            finally:
                connection.close()
        except sqlite3.Error:
            # A profile can be concurrently rotating its WAL. Missing evidence
            # remains fail-closed below instead of producing a partial total.
            continue
    missing = wanted - found.keys()
    if missing:
        raise RuntimeError(f"session cost evidence unavailable: {sorted(missing)!r}")
    return tuple(found[value] for value in sorted(found))


def with_recalculated_costs(
    metrics: PilotTaskMetrics,
    profiles_root: Path,
    estimator: ModelCostEstimator | None = None,
) -> PilotTaskMetrics:
    costs = calculate_evidence_costs(profiles_root, metrics.evidence, estimator)
    simulated = sum(item.simulated_cost_usd for item in costs)
    billed = sum(item.billed_cost_usd for item in costs)
    return replace(
        metrics,
        cost_usd=billed,
        simulated_cost_usd=simulated,
        billed_cost_usd=billed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    database_url = os.environ.get("ORCHESTRATOR_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("ORCHESTRATOR_DATABASE_URL is required")
    store = PostgresPilotMetricsStore(database_url)
    updated = tuple(
        with_recalculated_costs(metrics, args.profiles_root)
        for metrics in store.list_all()
    )
    if args.apply:
        for metrics in updated:
            store.record(metrics)
    print(json.dumps([
        {
            "task_id": item.task_id,
            "simulated_cost_usd": item.simulated_cost_usd,
            "billed_cost_usd": item.billed_cost_usd,
            "subscription_savings_usd": (
                (item.simulated_cost_usd or 0) - (item.billed_cost_usd or 0)
            ),
        }
        for item in updated
    ], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
