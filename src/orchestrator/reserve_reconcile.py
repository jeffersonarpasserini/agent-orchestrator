from __future__ import annotations

import argparse
import json
import os

from orchestrator.deepseek_reserve_finance import (
    DeepSeekUsage,
    ManualReconciliationResolution,
    ManualReserveReconciliation,
    PostgresReserveCostStore,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile one ambiguous DeepSeek reserve outcome"
    )
    parser.add_argument("--grant-id", required=True)
    parser.add_argument("--resolved-by", required=True)
    parser.add_argument("--evidence-reference", required=True)
    parser.add_argument(
        "--resolution",
        required=True,
        choices=[value.value for value in ManualReconciliationResolution],
    )
    parser.add_argument("--cache-hit-tokens", type=int)
    parser.add_argument("--cache-miss-tokens", type=int)
    parser.add_argument("--completion-tokens", type=int)
    return parser


def reconcile_from_args(args: argparse.Namespace, database_url: str) -> float:
    resolution = ManualReconciliationResolution(args.resolution)
    token_values = (
        args.cache_hit_tokens,
        args.cache_miss_tokens,
        args.completion_tokens,
    )
    if resolution is ManualReconciliationResolution.CHARGED:
        if any(value is None for value in token_values):
            raise ValueError("charged reconciliation requires all token counts")
        usage = DeepSeekUsage(*token_values)
    else:
        if any(value is not None for value in token_values):
            raise ValueError("not-charged reconciliation rejects token counts")
        usage = None
    value = ManualReserveReconciliation(
        grant_id=args.grant_id,
        resolved_by=args.resolved_by,
        evidence_reference=args.evidence_reference,
        resolution=resolution,
        usage=usage,
    )
    return PostgresReserveCostStore(database_url).reconcile_unknown(value)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.environ.get("ORCHESTRATOR_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("ORCHESTRATOR_DATABASE_URL is required")
    actual_cost = reconcile_from_args(args, database_url)
    print(json.dumps({
        "grant_id": args.grant_id,
        "resolution": args.resolution,
        "actual_cost_usd": actual_cost,
        "status": "reconciled",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
