from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import json
from typing import Mapping, Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import psycopg

from orchestrator.reserve_budget import (
    DirectBalanceSnapshot,
    ReserveBudgetEvidenceError,
    ReserveBudgetExceededError,
)
from orchestrator.technical_reserve import BillingRoute


MILLION = Decimal("1000000")
_ALLOWED_DEEPSEEK_PATHS = {"/chat/completions", "/user/balance"}


def _require_allowed_deepseek_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.deepseek.com"
        or parsed.path not in _ALLOWED_DEEPSEEK_PATHS
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("DeepSeek URL is not allowed")


class JsonTransport(Protocol):
    def get_json(self, url: str, headers: Mapping[str, str], timeout: float) -> object: ...


class UrllibJsonTransport:
    def get_json(self, url: str, headers: Mapping[str, str], timeout: float) -> object:
        _require_allowed_deepseek_url(url)
        request = Request(url, headers=dict(headers), method="GET")
        # URL is constrained above to HTTPS and the exact provider host/path.
        with urlopen(request, timeout=timeout) as response:  # nosec B310
            if response.status != 200:
                raise ReserveBudgetEvidenceError("DeepSeek balance endpoint unavailable")
            return json.loads(response.read())


class JsonPostTransport(Protocol):
    def post_json(
        self, url: str, headers: Mapping[str, str], payload: Mapping[str, object],
        timeout: float,
    ) -> object: ...


class UrllibJsonPostTransport:
    def post_json(
        self, url: str, headers: Mapping[str, str], payload: Mapping[str, object],
        timeout: float,
    ) -> object:
        _require_allowed_deepseek_url(url)
        request = Request(
            url,
            headers=dict(headers),
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        # URL is constrained above to HTTPS and the exact provider host/path.
        with urlopen(request, timeout=timeout) as response:  # nosec B310
            if response.status != 200:
                raise ReserveOutcomeUnknownError(
                    "DeepSeek reserve request outcome is unknown"
                )
            return json.loads(response.read())


class DeepSeekDirectBalanceReader:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 10.0,
        transport: JsonTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("DeepSeek reserve API key must not be empty")
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "api.deepseek.com"
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("DeepSeek reserve base URL is not allowed")
        if timeout_seconds <= 0:
            raise ValueError("DeepSeek balance timeout must be positive")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibJsonTransport()

    def read(self) -> DirectBalanceSnapshot:
        try:
            payload = self._transport.get_json(
                f"{self._base_url}/user/balance",
                {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                self._timeout_seconds,
            )
            return self._parse(payload)
        except ReserveBudgetEvidenceError:
            raise
        except Exception as exc:
            raise ReserveBudgetEvidenceError(
                "cannot validate DeepSeek direct balance"
            ) from exc

    @staticmethod
    def _parse(payload: object) -> DirectBalanceSnapshot:
        if not isinstance(payload, dict) or type(payload.get("is_available")) is not bool:
            raise ReserveBudgetEvidenceError("invalid DeepSeek balance response")
        infos = payload.get("balance_infos")
        if not isinstance(infos, list):
            raise ReserveBudgetEvidenceError("invalid DeepSeek balance response")
        usd = [item for item in infos if isinstance(item, dict) and item.get("currency") == "USD"]
        if len(usd) != 1:
            raise ReserveBudgetEvidenceError("USD DeepSeek balance is unavailable")
        try:
            total = Decimal(usd[0]["total_balance"])
        except (KeyError, InvalidOperation, TypeError) as exc:
            raise ReserveBudgetEvidenceError("invalid DeepSeek USD balance") from exc
        if not total.is_finite() or total < 0:
            raise ReserveBudgetEvidenceError("invalid DeepSeek USD balance")
        return DirectBalanceSnapshot(payload["is_available"], float(total))


@dataclass(frozen=True)
class DeepSeekPrice:
    cache_hit_per_million_usd: Decimal
    cache_miss_per_million_usd: Decimal
    output_per_million_usd: Decimal


PRICE_SNAPSHOT_2026_08_12 = {
    "deepseek-v4-flash": DeepSeekPrice(
        Decimal("0.0028"), Decimal("0.14"), Decimal("0.28")
    ),
    "deepseek-v4-pro": DeepSeekPrice(
        Decimal("0.003625"), Decimal("0.435"), Decimal("0.87")
    ),
}


@dataclass(frozen=True)
class DeepSeekUsage:
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int
    completion_tokens: int

    def __post_init__(self) -> None:
        if min(
            self.prompt_cache_hit_tokens,
            self.prompt_cache_miss_tokens,
            self.completion_tokens,
        ) < 0:
            raise ValueError("DeepSeek usage tokens must be non-negative")


class DeepSeekCostEstimator:
    snapshot_id = "official-2026-08-12"

    def __init__(self, prices: Mapping[str, DeepSeekPrice] | None = None) -> None:
        self.prices = dict(prices or PRICE_SNAPSHOT_2026_08_12)

    def maximum_cost(self, model: str, *, max_input_tokens: int, max_output_tokens: int) -> float:
        if min(max_input_tokens, max_output_tokens) < 0:
            raise ValueError("token ceilings must be non-negative")
        price = self._price(model)
        cost = (
            Decimal(max_input_tokens) * price.cache_miss_per_million_usd
            + Decimal(max_output_tokens) * price.output_per_million_usd
        ) / MILLION
        return float(cost)

    def actual_cost(self, model: str, usage: DeepSeekUsage) -> float:
        price = self._price(model)
        cost = (
            Decimal(usage.prompt_cache_hit_tokens) * price.cache_hit_per_million_usd
            + Decimal(usage.prompt_cache_miss_tokens) * price.cache_miss_per_million_usd
            + Decimal(usage.completion_tokens) * price.output_per_million_usd
        ) / MILLION
        return float(cost)

    def _price(self, model: str) -> DeepSeekPrice:
        try:
            return self.prices[model]
        except KeyError as exc:
            raise ReserveBudgetEvidenceError("DeepSeek reserve price is not configured") from exc


@dataclass(frozen=True)
class ReserveCostCommitment:
    grant_id: str
    task_id: str
    model: str
    price_snapshot: str
    estimated_max_cost_usd: float

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.grant_id, self.task_id, self.model, self.price_snapshot)):
            raise ValueError("reserve commitment identifiers must not be empty")
        if self.estimated_max_cost_usd <= 0:
            raise ValueError("reserve estimated cost must be positive")


class ManualReconciliationResolution(StrEnum):
    CHARGED = "confirmed_charged"
    NOT_CHARGED = "confirmed_not_charged"


@dataclass(frozen=True)
class ManualReserveReconciliation:
    grant_id: str
    resolved_by: str
    evidence_reference: str
    resolution: ManualReconciliationResolution
    usage: DeepSeekUsage | None = None

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.grant_id, self.resolved_by, self.evidence_reference
        )):
            raise ValueError("manual reconciliation evidence must not be empty")
        if (
            self.resolution is ManualReconciliationResolution.CHARGED
            and self.usage is None
        ):
            raise ValueError("charged reconciliation requires usage")
        if (
            self.resolution is ManualReconciliationResolution.NOT_CHARGED
            and self.usage is not None
        ):
            raise ValueError("not-charged reconciliation must not include usage")


class PostgresReserveCostStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database URL must not be empty")
        self.database_url = database_url

    def commit(self, value: ReserveCostCommitment) -> None:
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orchestrator.deepseek_reserve_costs (
                        grant_id, task_id, model, price_snapshot,
                        estimated_max_cost_usd, status
                    ) VALUES (%s, %s, %s, %s, %s, 'committed')
                    ON CONFLICT (grant_id) DO NOTHING
                    RETURNING grant_id
                    """,
                    (
                        value.grant_id, value.task_id, value.model,
                        value.price_snapshot, value.estimated_max_cost_usd,
                    ),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError("reserve cost commitment already exists")
            connection.commit()

    def reconcile(self, grant_id: str, usage: DeepSeekUsage, actual_cost_usd: float) -> None:
        if not grant_id.strip() or actual_cost_usd < 0:
            raise ValueError("invalid reserve reconciliation")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_costs
                       SET status = 'reconciled', actual_cost_usd = %s,
                           prompt_cache_hit_tokens = %s,
                           prompt_cache_miss_tokens = %s,
                           completion_tokens = %s, reconciled_at = now()
                     WHERE grant_id = %s AND status = 'committed'
                    RETURNING grant_id
                    """,
                    (
                        actual_cost_usd, usage.prompt_cache_hit_tokens,
                        usage.prompt_cache_miss_tokens, usage.completion_tokens,
                        grant_id,
                    ),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError("reserve cost cannot be reconciled")
            connection.commit()

    def mark_outcome_unknown(self, grant_id: str) -> None:
        if not grant_id.strip():
            raise ValueError("grant id must not be empty")
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_costs
                       SET status = 'outcome_unknown'
                     WHERE grant_id = %s AND status = 'committed'
                    RETURNING grant_id
                    """,
                    (grant_id,),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError(
                        "reserve outcome cannot be marked unknown"
                    )
            connection.commit()

    def reconcile_unknown(
        self,
        value: ManualReserveReconciliation,
        estimator: DeepSeekCostEstimator | None = None,
    ) -> float:
        estimator = estimator or DeepSeekCostEstimator()
        with closing(psycopg.connect(self.database_url)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT model
                      FROM orchestrator.deepseek_reserve_costs
                     WHERE grant_id = %s AND status = 'outcome_unknown'
                     FOR UPDATE
                    """,
                    (value.grant_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ReserveBudgetEvidenceError(
                        "reserve outcome is not available for reconciliation"
                    )
                if value.resolution is ManualReconciliationResolution.CHARGED:
                    usage = value.usage
                    assert usage is not None
                    actual_cost = estimator.actual_cost(row[0], usage)
                else:
                    usage = DeepSeekUsage(0, 0, 0)
                    actual_cost = 0.0
                cursor.execute(
                    """
                    UPDATE orchestrator.deepseek_reserve_costs
                       SET status = 'reconciled', actual_cost_usd = %s,
                           prompt_cache_hit_tokens = %s,
                           prompt_cache_miss_tokens = %s,
                           completion_tokens = %s, reconciled_at = now()
                     WHERE grant_id = %s AND status = 'outcome_unknown'
                    RETURNING grant_id
                    """,
                    (
                        actual_cost, usage.prompt_cache_hit_tokens,
                        usage.prompt_cache_miss_tokens, usage.completion_tokens,
                        value.grant_id,
                    ),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError(
                        "reserve outcome changed during reconciliation"
                    )
                cursor.execute(
                    """
                    INSERT INTO orchestrator.deepseek_reserve_manual_reconciliations (
                        grant_id, resolution, resolved_by, evidence_reference,
                        actual_cost_usd, prompt_cache_hit_tokens,
                        prompt_cache_miss_tokens, completion_tokens
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (grant_id) DO NOTHING
                    RETURNING grant_id
                    """,
                    (
                        value.grant_id, value.resolution.value,
                        value.resolved_by, value.evidence_reference, actual_cost,
                        usage.prompt_cache_hit_tokens,
                        usage.prompt_cache_miss_tokens,
                        usage.completion_tokens,
                    ),
                )
                if cursor.fetchone() is None:
                    raise ReserveBudgetEvidenceError(
                        "reserve outcome was already reconciled manually"
                    )
            connection.commit()
        return actual_cost


class ReserveOutcomeUnknownError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReserveProviderResult:
    model: str
    usage: DeepSeekUsage
    output: object
    provider_request_id: str | None = None
    billing_route: BillingRoute = BillingRoute.DEEPSEEK_RESERVE


class ReserveProvider(Protocol):
    def invoke_once(self, model: str) -> ReserveProviderResult: ...


class DeepSeekDirectChatProvider:
    """Single non-streaming Chat Completions call with injected transport."""

    def __init__(
        self,
        api_key: str,
        messages: tuple[Mapping[str, object], ...],
        *,
        max_output_tokens: int,
        thinking_enabled: bool = True,
        timeout_seconds: float = 120.0,
        transport: JsonPostTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("DeepSeek reserve API key must not be empty")
        if not messages:
            raise ValueError("DeepSeek reserve messages must not be empty")
        if max_output_tokens <= 0 or timeout_seconds <= 0:
            raise ValueError("DeepSeek reserve limits must be positive")
        self._api_key = api_key
        self._messages = messages
        self._max_output_tokens = max_output_tokens
        self._thinking_enabled = thinking_enabled
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibJsonPostTransport()

    def invoke_once(self, model: str) -> ReserveProviderResult:
        if model not in PRICE_SNAPSHOT_2026_08_12:
            raise ReserveBudgetEvidenceError(
                "DeepSeek reserve model is not allowed"
            )
        try:
            payload = self._transport.post_json(
                "https://api.deepseek.com/chat/completions",
                {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                {
                    "model": model,
                    "messages": list(self._messages),
                    "max_tokens": self._max_output_tokens,
                    "stream": False,
                    "thinking": {
                        "type": "enabled" if self._thinking_enabled else "disabled"
                    },
                },
                self._timeout_seconds,
            )
            return self._parse(payload)
        except ReserveBudgetEvidenceError:
            raise
        except ReserveOutcomeUnknownError:
            raise
        except Exception as exc:
            raise ReserveOutcomeUnknownError(
                "DeepSeek reserve request outcome is unknown"
            ) from exc

    @staticmethod
    def _parse(payload: object) -> ReserveProviderResult:
        try:
            if not isinstance(payload, dict):
                raise TypeError
            model = payload["model"]
            provider_request_id = payload.get("id")
            usage = payload["usage"]
            choices = payload["choices"]
            if (
                not isinstance(model, str)
                or not isinstance(usage, dict)
                or not isinstance(choices, list)
                or len(choices) != 1
                or (
                    provider_request_id is not None
                    and not isinstance(provider_request_id, str)
                )
            ):
                raise TypeError
            output = choices[0]["message"]["content"]
            if not isinstance(output, str):
                raise TypeError
            parsed_usage = DeepSeekUsage(
                prompt_cache_hit_tokens=int(usage["prompt_cache_hit_tokens"]),
                prompt_cache_miss_tokens=int(usage["prompt_cache_miss_tokens"]),
                completion_tokens=int(usage["completion_tokens"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ReserveOutcomeUnknownError(
                "DeepSeek reserve response requires reconciliation"
            ) from exc
        return ReserveProviderResult(
            model, parsed_usage, output, provider_request_id=provider_request_id
        )


class DeepSeekReserveExecutor:
    """Financial envelope for one already-approved direct provider attempt."""

    def __init__(
        self,
        provider: ReserveProvider,
        cost_store: PostgresReserveCostStore,
        estimator: DeepSeekCostEstimator | None = None,
    ) -> None:
        self.provider = provider
        self.cost_store = cost_store
        self.estimator = estimator or DeepSeekCostEstimator()

    def prepare(
        self,
        *,
        grant_id: str,
        task_id: str,
        model: str,
        grant_max_cost_usd: float,
        max_input_tokens: int,
        max_output_tokens: int,
    ) -> ReserveCostCommitment:
        estimated = self.estimator.maximum_cost(
            model,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )
        if estimated <= 0 or estimated > grant_max_cost_usd:
            raise ReserveBudgetExceededError(
                "DeepSeek reserve estimate exceeds grant"
            )
        return ReserveCostCommitment(
            grant_id=grant_id,
            task_id=task_id,
            model=model,
            price_snapshot=self.estimator.snapshot_id,
            estimated_max_cost_usd=estimated,
        )

    def execute_committed(
        self, commitment: ReserveCostCommitment
    ) -> ReserveProviderResult:
        try:
            result = self.provider.invoke_once(commitment.model)
        except ReserveOutcomeUnknownError:
            self.cost_store.mark_outcome_unknown(commitment.grant_id)
            raise
        if result.model != commitment.model:
            self.cost_store.mark_outcome_unknown(commitment.grant_id)
            raise ReserveOutcomeUnknownError(
                "DeepSeek reserve returned an unexpected model"
            )
        actual = self.estimator.actual_cost(commitment.model, result.usage)
        self.cost_store.reconcile(commitment.grant_id, result.usage, actual)
        return result

    def execute(self, **kwargs) -> ReserveProviderResult:
        """Standalone helper; graph integrations should commit atomically."""
        commitment = self.prepare(**kwargs)
        self.cost_store.commit(commitment)
        return self.execute_committed(commitment)
