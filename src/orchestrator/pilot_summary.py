from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from orchestrator.pilot_metrics import PilotTaskMetrics


@dataclass(frozen=True)
class PilotSummary:
    sample_size: int
    recorded_tasks: int
    first_attempt_tasks: int
    api_calls: int
    latency_seconds: float
    cost_usd: float
    simulated_cost_usd: float
    billed_cost_usd: float

    @property
    def subscription_savings_usd(self) -> float:
        return self.simulated_cost_usd - self.billed_cost_usd

    @property
    def completion_rate(self) -> float:
        return self.recorded_tasks / self.sample_size

    @property
    def first_attempt_rate(self) -> float:
        return self.first_attempt_tasks / self.sample_size

    def to_markdown(self) -> str:
        return "\n".join((
            "# Resumo local do piloto",
            "",
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Tarefas registradas | {self.recorded_tasks}/{self.sample_size} |",
            f"| Conclusão | {self.completion_rate:.1%} |",
            f"| Sucesso na primeira tentativa | {self.first_attempt_rate:.1%} |",
            f"| Chamadas de API | {self.api_calls} |",
            f"| Latência acumulada | {self.latency_seconds:.3f} s |",
            f"| Custo simulado | US$ {self.simulated_cost_usd:.9f} |",
            f"| Custo cobrado | US$ {self.billed_cost_usd:.9f} |",
            f"| Economia da assinatura | US$ {self.subscription_savings_usd:.9f} |",
        ))


def summarize_pilot(
    metrics: Iterable[PilotTaskMetrics], *, sample_size: int = 20
) -> PilotSummary:
    if sample_size <= 0:
        raise ValueError("sample size must be positive")
    entries = tuple(metrics)
    if len(entries) > sample_size:
        raise ValueError("recorded tasks exceed sample size")
    return PilotSummary(
        sample_size=sample_size,
        recorded_tasks=len(entries),
        first_attempt_tasks=sum(entry.attempts == 1 for entry in entries),
        api_calls=sum(entry.api_calls for entry in entries),
        latency_seconds=sum(entry.latency_seconds for entry in entries),
        cost_usd=sum(entry.cost_usd for entry in entries),
        simulated_cost_usd=sum(entry.simulated_cost_usd or 0 for entry in entries),
        billed_cost_usd=sum(entry.billed_cost_usd or 0 for entry in entries),
    )
