from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from orchestrator.deepseek_reserve_finance import (
    DeepSeekDirectBalanceReader,
    DeepSeekDirectChatProvider,
    DeepSeekReserveExecutor,
    PostgresReserveCostStore,
)
from orchestrator.graphs.hermes_agent import run_hermes_workflow
from orchestrator.reserve_budget import (
    DirectReserveBudgetGuard,
    PostgresReserveSpendEvidence,
)
from orchestrator.reserve_grants import (
    PostgresReserveGrantStore,
    ReserveGrant,
    ReserveGrantScope,
)
from orchestrator.technical_reserve import (
    PrimaryFailureReason,
    PrimaryRouteError,
    ReserveMode,
    TechnicalReserveConfig,
)


class SimulatedExhaustedPrimary:
    async def run_agent(self, profile, task, context, limits):
        raise PrimaryRouteError(
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
            "smoke-test simulated primary exhaustion",
        )


def load_existing_deepseek_key(path: Path) -> str:
    data = json.loads(path.read_text())
    credentials = data.get("credential_pool", {}).get("deepseek", [])
    if len(credentials) != 1:
        raise RuntimeError("exactly one existing DeepSeek credential is required")
    token = credentials[0].get("access_token", "")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("existing DeepSeek credential is unavailable")
    return token


async def execute_smoke(database_url: str, api_key: str) -> dict[str, object]:
    balance = DeepSeekDirectBalanceReader(api_key).read()
    if not balance.is_available or balance.total_balance_usd < 0.01:
        raise RuntimeError("DeepSeek reserve balance is below smoke-test gate")
    task_id = f"RESERVE-SMOKE-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    grant_id = f"reserve-smoke-{uuid4()}"
    reason = PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    scope = ReserveGrantScope(
        grant_id=grant_id,
        task_id=task_id,
        profile="barclay",
        role="flash",
        primary_model="deepseek-v4-flash-0731",
        reserve_model="deepseek-v4-flash",
        max_cost_usd=0.01,
        primary_failure_reason=reason,
        expires_at=expires_at,
    )
    grant_store = PostgresReserveGrantStore(database_url)
    grant_store.create_approved(ReserveGrant(
        grant_id=grant_id,
        task_id=task_id,
        profile="barclay",
        role="flash",
        primary_model="deepseek-v4-flash-0731",
        reserve_model="deepseek-v4-flash",
        primary_failure_reason=reason,
        approved_by="spock",
        max_cost_usd=0.01,
        max_calls=1,
        expires_at=expires_at,
    ))
    cost_store = PostgresReserveCostStore(database_url)
    executor = DeepSeekReserveExecutor(
        DeepSeekDirectChatProvider(
            api_key,
            ({
                "role": "user",
                "content": "Reply with exactly: RESERVE_SMOKE_OK",
            },),
            max_output_tokens=128,
            thinking_enabled=False,
            timeout_seconds=120,
        ),
        cost_store,
    )
    guard = DirectReserveBudgetGuard(
        DeepSeekDirectBalanceReader(api_key),
        PostgresReserveSpendEvidence(database_url),
        daily_limit_usd=1.0,
        monthly_limit_usd=10.0,
        operational_timezone=timezone(timedelta(hours=-3)),
    )
    result = await run_hermes_workflow(
        SimulatedExhaustedPrimary(),
        "barclay",
        "reserve smoke test",
        task_id=task_id,
        reserve_decision="approved",
        reserve_config=TechnicalReserveConfig(
            mode=ReserveMode.ENFORCED,
            kill_switch_active=False,
            enabled_profiles=frozenset({"barclay"}),
            daily_budget_usd=1.0,
            monthly_budget_usd=10.0,
        ),
        reserve_grant_store=grant_store,
        reserve_grant_scope=scope,
        reserve_budget_guard=guard,
        reserve_executor=executor,
        reserve_max_input_tokens=1000,
        reserve_max_output_tokens=128,
    )
    return {
        "task_id": task_id,
        "grant_id": grant_id,
        "status": result["status"],
        "text": result["text"],
        "usage": result["usage"],
        "balance_before_usd": balance.total_balance_usd,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ack-paid-call", action="store_true")
    parser.add_argument(
        "--credential-file",
        type=Path,
        default=Path("/run/secrets/hermes-auth.json"),
    )
    args = parser.parse_args(argv)
    if not args.ack_paid_call:
        raise RuntimeError("--ack-paid-call is required")
    database_url = os.environ.get("ORCHESTRATOR_DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("ORCHESTRATOR_DATABASE_URL is required")
    result = asyncio.run(execute_smoke(
        database_url, load_existing_deepseek_key(args.credential_file)
    ))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
