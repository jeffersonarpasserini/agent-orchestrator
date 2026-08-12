from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Mapping


MILLION = Decimal("1000000")


class CostEstimateStatus(StrEnum):
    OFFICIAL = "official_estimate"
    PROXY = "proxy_estimate"


@dataclass(frozen=True)
class ModelPrice:
    input_per_million_usd: Decimal
    cached_input_per_million_usd: Decimal
    output_per_million_usd: Decimal
    cache_write_per_million_usd: Decimal
    snapshot: str
    source: str
    status: CostEstimateStatus = CostEstimateStatus.OFFICIAL
    pricing_model: str | None = None


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __post_init__(self) -> None:
        if min(
            self.input_tokens,
            self.output_tokens,
            self.cache_read_tokens,
            self.cache_write_tokens,
        ) < 0:
            raise ValueError("usage tokens must be non-negative")


@dataclass(frozen=True)
class CostBreakdown:
    model: str
    pricing_model: str
    simulated_cost_usd: float
    billed_cost_usd: float
    pricing_snapshot: str
    pricing_source: str
    status: CostEstimateStatus

    @property
    def subscription_savings_usd(self) -> float:
        return self.simulated_cost_usd - self.billed_cost_usd


# Prices are immutable snapshots. Updating a price requires a new snapshot ID.
PRICE_SNAPSHOT_2026_08_12: Mapping[str, ModelPrice] = {
    "gpt-5.6-sol": ModelPrice(
        Decimal("5"), Decimal("0.5"), Decimal("30"), Decimal("6.25"),
        "openai-2026-08-12", "developers.openai.com/api/docs/models/compare",
    ),
    "gpt-5.6-terra": ModelPrice(
        Decimal("2"), Decimal("0.2"), Decimal("12"), Decimal("2.5"),
        "openai-2026-08-12", "developers.openai.com/api/docs/models/compare",
    ),
    "gpt-5.6-luna": ModelPrice(
        Decimal("0.2"), Decimal("0.02"), Decimal("1.2"), Decimal("0.25"),
        "openai-2026-08-12", "developers.openai.com/api/docs/models/compare",
    ),
    "qwen3.8-max": ModelPrice(
        Decimal("2"), Decimal("2"), Decimal("6"), Decimal("2"),
        "openrouter-2026-08-12", "openrouter.ai/qwen/qwen3.8-2.4t-a95b",
        CostEstimateStatus.PROXY, "qwen/qwen3.8-2.4t-a95b",
    ),
    "deepseek-v4-flash": ModelPrice(
        Decimal("0.14"), Decimal("0.0028"), Decimal("0.28"), Decimal("0.14"),
        "deepseek-official-2026-08-12", "api-docs.deepseek.com/quick_start/pricing",
    ),
    "deepseek-v4-pro": ModelPrice(
        Decimal("0.435"), Decimal("0.003625"), Decimal("0.87"), Decimal("0.435"),
        "deepseek-official-2026-08-12", "api-docs.deepseek.com/quick_start/pricing",
    ),
}


class ModelCostEstimator:
    def __init__(self, prices: Mapping[str, ModelPrice] | None = None) -> None:
        self.prices = dict(prices or PRICE_SNAPSHOT_2026_08_12)

    def estimate(
        self,
        model: str,
        usage: ModelUsage,
        *,
        billing_provider: str,
        billing_mode: str | None,
    ) -> CostBreakdown:
        try:
            price = self.prices[model]
        except KeyError as exc:
            raise ValueError(f"price is not configured for model {model!r}") from exc
        simulated = (
            Decimal(usage.input_tokens) * price.input_per_million_usd
            + Decimal(usage.cache_read_tokens) * price.cached_input_per_million_usd
            + Decimal(usage.cache_write_tokens) * price.cache_write_per_million_usd
            + Decimal(usage.output_tokens) * price.output_per_million_usd
        ) / MILLION
        subscription = (
            billing_mode == "subscription_included"
            or billing_provider == "openai-codex"
            or billing_provider == "alibaba-coding-plan"
        )
        billed = Decimal("0") if subscription else simulated
        return CostBreakdown(
            model=model,
            pricing_model=price.pricing_model or model,
            simulated_cost_usd=float(simulated),
            billed_cost_usd=float(billed),
            pricing_snapshot=price.snapshot,
            pricing_source=price.source,
            status=price.status,
        )

    def estimate_session(self, usage: Mapping[str, object]) -> CostBreakdown:
        return self.estimate(
            str(usage["model"]),
            ModelUsage(
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                cache_read_tokens=int(usage.get("cache_read_tokens") or 0),
                cache_write_tokens=int(usage.get("cache_write_tokens") or 0),
            ),
            billing_provider=str(usage.get("billing_provider") or ""),
            billing_mode=(str(usage["billing_mode"]) if usage.get("billing_mode") else None),
        )
