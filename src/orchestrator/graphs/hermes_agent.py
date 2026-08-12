from __future__ import annotations
import asyncio
from typing import Mapping, TypedDict
from langgraph.graph import END, START, StateGraph
from orchestrator.adapters.hermes_cli import AgentLimits, HermesCliAdapter
from orchestrator.budget import BudgetError
from orchestrator.reserve_grants import (
    PostgresReserveGrantStore,
    ReserveGrantScope,
)
from orchestrator.reserve_budget import DirectReserveBudgetGuard, ReserveBudgetError
from orchestrator.deepseek_reserve_finance import (
    DeepSeekReserveExecutor,
    ReserveCostCommitment,
    ReserveOutcomeUnknownError,
)
from orchestrator.technical_reserve import (
    PrimaryRouteError,
    ReserveDecision,
    TechnicalReserveConfig,
    ReserveMode,
    build_reserve_request,
)

class HermesAgentState(TypedDict):
    profile: str
    task: str
    context: Mapping[str, object]
    limits: AgentLimits
    text: str
    session_id: str | None
    correlation_id: str
    usage: Mapping[str, object]
    tool_calls: tuple[Mapping[str, object], ...]
    status: str
    error: str
    task_id: str
    reserve_role: str
    reserve_decision: str
    reserve_request: Mapping[str, object]
    reserve_grant_id: str
    reserve_grant_scope: ReserveGrantScope | None
    reserve_commitment: ReserveCostCommitment | None
    reserve_max_input_tokens: int
    reserve_max_output_tokens: int

def build_hermes_agent_graph(
    adapter: HermesCliAdapter,
    reserve_config: TechnicalReserveConfig | None = None,
    reserve_grant_store: PostgresReserveGrantStore | None = None,
    reserve_budget_guard: DirectReserveBudgetGuard | None = None,
    reserve_executor: DeepSeekReserveExecutor | None = None,
):
    reserve_config = reserve_config or TechnicalReserveConfig()

    async def invoke_agent(state: HermesAgentState) -> dict[str, object]:
        try:
            result = await adapter.run_agent(
                state["profile"], state["task"], state["context"], state["limits"]
            )
        except PrimaryRouteError as exc:
            request = build_reserve_request(
                reserve_config,
                task_id=state["task_id"],
                profile=state["profile"],
                role=state["reserve_role"],
                reason=exc.reason,
            )
            if request is None:
                return {"status": "budget_blocked", "error": exc.reason.value}
            if state["reserve_decision"] == ReserveDecision.DENIED.value:
                return {
                    "status": "reserve_denied",
                    "error": "technical reserve denied by operator",
                    "reserve_request": request.as_public_dict(),
                }
            if state["reserve_decision"] == ReserveDecision.APPROVED.value:
                scope = state["reserve_grant_scope"]
                if reserve_config.mode is not ReserveMode.ENFORCED:
                    return {
                        "status": "reserve_denied",
                        "error": "technical reserve approval is disabled in shadow mode",
                        "reserve_request": request.as_public_dict(),
                    }
                if (
                    reserve_grant_store is None
                    or reserve_budget_guard is None
                    or reserve_executor is None
                    or scope is None
                    or not scope.matches(request)
                ):
                    return {
                        "status": "reserve_denied",
                        "error": "technical reserve grant is unavailable or out of scope",
                        "reserve_request": request.as_public_dict(),
                    }
                try:
                    commitment = reserve_executor.prepare(
                        grant_id=scope.grant_id,
                        task_id=scope.task_id,
                        model=scope.reserve_model,
                        grant_max_cost_usd=scope.max_cost_usd,
                        max_input_tokens=state["reserve_max_input_tokens"],
                        max_output_tokens=state["reserve_max_output_tokens"],
                    )
                    budget_snapshot = await asyncio.to_thread(
                        reserve_budget_guard.check, scope.max_cost_usd
                    )
                except ReserveBudgetError as budget_error:
                    return {
                        "status": "budget_blocked",
                        "error": str(budget_error),
                        "reserve_request": request.as_public_dict(),
                    }
                try:
                    consumed = await asyncio.to_thread(
                        reserve_grant_store.consume_with_budget_and_cost,
                        scope,
                        budget_snapshot,
                        commitment,
                        daily_limit_usd=reserve_budget_guard.daily_limit_usd,
                        monthly_limit_usd=reserve_budget_guard.monthly_limit_usd,
                    )
                except ReserveBudgetError as budget_error:
                    return {
                        "status": "budget_blocked",
                        "error": str(budget_error),
                        "reserve_request": request.as_public_dict(),
                    }
                if not consumed:
                    return {
                        "status": "reserve_denied",
                        "error": "technical reserve grant is invalid or no longer available",
                        "reserve_request": request.as_public_dict(),
                    }
                return {
                    "status": "reserve_approved",
                    "error": "",
                    "reserve_request": request.as_public_dict(),
                    "reserve_grant_id": scope.grant_id,
                    "reserve_commitment": commitment,
                }
            return {
                "status": "reserve_required",
                "error": exc.reason.value,
                "reserve_request": request.as_public_dict(),
            }
        except BudgetError as exc:
            return {"status": "budget_blocked", "error": str(exc)}
        return {"text": result.text, "session_id": result.session_id,
                "correlation_id": result.correlation_id, "usage": result.usage,
                "tool_calls": result.tool_calls, "status": result.status,
                "error": ""}

    async def invoke_reserve(state: HermesAgentState) -> dict[str, object]:
        commitment = state["reserve_commitment"]
        if reserve_executor is None or commitment is None:
            return {
                "status": "budget_blocked",
                "error": "technical reserve executor is unavailable",
            }
        try:
            result = await asyncio.to_thread(
                reserve_executor.execute_committed, commitment
            )
        except ReserveOutcomeUnknownError:
            return {
                "status": "reserve_outcome_unknown",
                "error": "technical reserve outcome requires reconciliation",
            }
        except ReserveBudgetError as exc:
            return {"status": "budget_blocked", "error": str(exc)}
        except Exception:
            return {
                "status": "reserve_failed",
                "error": "technical reserve provider failed",
            }
        return {
            "text": result.output if isinstance(result.output, str) else str(result.output),
            "usage": {
                "prompt_cache_hit_tokens": result.usage.prompt_cache_hit_tokens,
                "prompt_cache_miss_tokens": result.usage.prompt_cache_miss_tokens,
                "completion_tokens": result.usage.completion_tokens,
            },
            "status": "completed",
            "error": "",
        }

    def route_after_primary(state: HermesAgentState):
        return "reserve" if state["status"] == "reserve_approved" else END

    builder = StateGraph(HermesAgentState)
    builder.add_node("hermes_agent", invoke_agent)
    builder.add_node("deepseek_reserve", invoke_reserve)
    builder.add_edge(START, "hermes_agent")
    builder.add_conditional_edges(
        "hermes_agent", route_after_primary, {"reserve": "deepseek_reserve", END: END}
    )
    builder.add_edge("deepseek_reserve", END)
    return builder.compile()

async def run_hermes_workflow(
    adapter,
    profile,
    task,
    context=None,
    limits=None,
    *,
    task_id="untracked",
    reserve_role="flash",
    reserve_decision=ReserveDecision.PENDING.value,
    reserve_config=None,
    reserve_grant_store=None,
    reserve_grant_scope=None,
    reserve_budget_guard=None,
    reserve_executor=None,
    reserve_max_input_tokens=0,
    reserve_max_output_tokens=0,
):
    normalized_decision = ReserveDecision(reserve_decision).value
    return await build_hermes_agent_graph(
        adapter, reserve_config, reserve_grant_store, reserve_budget_guard,
        reserve_executor,
    ).ainvoke({
        "profile": profile, "task": task, "context": context or {},
        "limits": limits or AgentLimits(), "text": "", "session_id": None,
        "correlation_id": "", "usage": {}, "tool_calls": (), "status": "pending",
        "error": "",
        "task_id": task_id,
        "reserve_role": reserve_role,
        "reserve_decision": normalized_decision,
        "reserve_request": {},
        "reserve_grant_id": "",
        "reserve_grant_scope": reserve_grant_scope,
        "reserve_commitment": None,
        "reserve_max_input_tokens": reserve_max_input_tokens,
        "reserve_max_output_tokens": reserve_max_output_tokens,
    })
