from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from typing import Mapping


class ReserveMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"
    ENFORCED = "enforced"


class BillingRoute(StrEnum):
    QWENCLOUD_PRIMARY = "qwencloud_primary"
    DEEPSEEK_RESERVE = "deepseek_reserve"


class PrimaryFailureReason(StrEnum):
    SUBSCRIPTION_WINDOW_EXHAUSTED = "subscription_window_exhausted"
    SUBSCRIPTION_CREDITS_EXHAUSTED = "subscription_credits_exhausted"
    SUBSCRIPTION_CAPACITY_UNAVAILABLE = "subscription_capacity_unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    ACCOUNT_SUSPENDED = "account_suspended"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    TOOL_ERROR = "tool_error"
    POLICY_VIOLATION = "policy_violation"
    AMBIGUOUS_TIMEOUT = "ambiguous_timeout"
    LOCAL_ERROR = "local_error"
    FINANCIAL_EVIDENCE_UNAVAILABLE = "financial_evidence_unavailable"
    LOW_QUALITY_RESPONSE = "low_quality_response"


class ReserveDisposition(StrEnum):
    RESERVE_REQUIRED = "reserve_required"
    BLOCKED = "blocked"


class ReserveDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class PrimaryRouteError(RuntimeError):
    def __init__(
        self,
        reason: PrimaryFailureReason,
        message: str,
        *,
        session_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.session_id = session_id


@dataclass(frozen=True)
class QwenCloudErrorEvidence:
    http_status: int | None = None
    provider_code: str = ""
    provider_message: str = ""
    quota_depleted_confirmed: bool = False


def normalize_qwencloud_error(
    evidence: QwenCloudErrorEvidence,
) -> PrimaryFailureReason:
    code = evidence.provider_code.strip().lower()
    message = " ".join(evidence.provider_message.strip().lower().split())
    if code in {"invalidapikey", "invalid_access_token"} or (
        evidence.http_status == 401
        and ("api key" in message or "access token" in message)
    ):
        return PrimaryFailureReason.AUTHENTICATION_FAILED
    if code in {"accessdenied", "access_denied", "accessdenied.unpurchased"}:
        return PrimaryFailureReason.AUTHORIZATION_FAILED
    if "model not exist" in message or "not found or not supported" in message:
        return PrimaryFailureReason.MODEL_UNAVAILABLE
    if code == "invalidparameter" or evidence.http_status == 400:
        return PrimaryFailureReason.INVALID_REQUEST
    if any(
        marker in message
        for marker in (
            "hour allocated quota exceeded",
            "week allocated quota exceeded",
            "month allocated quota exceeded",
        )
    ):
        return PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED
    if evidence.quota_depleted_confirmed and (
        code in {"throttling.allocationquota", "insufficient_quota"}
        or "allocated quota exceeded" in message
        or "exceeded your current quota" in message
    ):
        return PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
    if (
        "concurrency allocated quota exceeded" in message
        or "usage allocated quota exceeded" in message
        or "requests rate limit exceeded" in message
    ):
        return PrimaryFailureReason.SUBSCRIPTION_CAPACITY_UNAVAILABLE
    if evidence.http_status == 429:
        return PrimaryFailureReason.FINANCIAL_EVIDENCE_UNAVAILABLE
    return PrimaryFailureReason.LOCAL_ERROR


@dataclass(frozen=True)
class ModelRoute:
    role: str
    primary_model: str
    reserve_model: str


MODEL_ROUTES: Mapping[str, ModelRoute] = {
    "flash": ModelRoute(
        role="flash",
        primary_model="deepseek-v4-flash-0731",
        reserve_model="deepseek-v4-flash",
    ),
    "pro": ModelRoute(
        role="pro",
        primary_model="deepseek-v4-pro",
        reserve_model="deepseek-v4-pro",
    ),
}


def reserve_disposition(
    reason: PrimaryFailureReason,
    *,
    allow_capacity_contingency: bool = False,
) -> ReserveDisposition:
    if reason in {
        PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
        PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
    }:
        return ReserveDisposition.RESERVE_REQUIRED
    if (
        reason is PrimaryFailureReason.SUBSCRIPTION_CAPACITY_UNAVAILABLE
        and allow_capacity_contingency
    ):
        return ReserveDisposition.RESERVE_REQUIRED
    return ReserveDisposition.BLOCKED


@dataclass(frozen=True)
class TechnicalReserveConfig:
    mode: ReserveMode = ReserveMode.OFF
    kill_switch_active: bool = True
    enabled_profiles: frozenset[str] = frozenset()
    daily_budget_usd: float | None = None
    monthly_budget_usd: float | None = None
    max_calls_per_grant: int = 1
    max_attempts_per_task: int = 1

    def __post_init__(self) -> None:
        if self.max_calls_per_grant != 1 or self.max_attempts_per_task != 1:
            raise ValueError("technical reserve permits exactly one call and attempt")
        if self.mode is ReserveMode.ENFORCED:
            if self.kill_switch_active:
                raise ValueError("enforced reserve requires the kill switch to be off")
            if not self.enabled_profiles:
                raise ValueError("enforced reserve requires at least one profile")
            if self.daily_budget_usd is None or self.daily_budget_usd <= 0:
                raise ValueError("enforced reserve requires a positive daily budget")
            if self.monthly_budget_usd is None or self.monthly_budget_usd <= 0:
                raise ValueError("enforced reserve requires a positive monthly budget")

    @property
    def can_call_provider(self) -> bool:
        return self.mode is ReserveMode.ENFORCED and not self.kill_switch_active

    def permits_profile(self, profile: str) -> bool:
        return self.can_call_provider and profile in self.enabled_profiles

    def observes_profile(self, profile: str) -> bool:
        return (
            self.mode is ReserveMode.SHADOW
            and not self.kill_switch_active
            and profile in self.enabled_profiles
        )

    def requests_profile(self, profile: str) -> bool:
        return (
            self.mode in {ReserveMode.SHADOW, ReserveMode.ENFORCED}
            and not self.kill_switch_active
            and profile in self.enabled_profiles
        )

    @classmethod
    def from_env(cls) -> "TechnicalReserveConfig":
        raw_mode = os.environ.get("DEEPSEEK_RESERVE_MODE", ReserveMode.OFF.value)
        try:
            mode = ReserveMode(raw_mode.strip().lower())
        except ValueError as exc:
            raise RuntimeError("invalid DeepSeek technical reserve mode") from exc

        kill_switch = _parse_bool(
            os.environ.get("DEEPSEEK_RESERVE_KILL_SWITCH", "true"),
            name="DEEPSEEK_RESERVE_KILL_SWITCH",
        )
        profiles = frozenset(
            item.strip()
            for item in os.environ.get("DEEPSEEK_RESERVE_PROFILES", "").split(",")
            if item.strip()
        )
        daily = _optional_positive_float("DEEPSEEK_RESERVE_DAILY_BUDGET_USD")
        monthly = _optional_positive_float("DEEPSEEK_RESERVE_MONTHLY_BUDGET_USD")
        try:
            return cls(
                mode=mode,
                kill_switch_active=kill_switch,
                enabled_profiles=profiles,
                daily_budget_usd=daily,
                monthly_budget_usd=monthly,
            )
        except ValueError as exc:
            raise RuntimeError("invalid DeepSeek technical reserve configuration") from exc


@dataclass(frozen=True)
class ReserveRequest:
    task_id: str
    profile: str
    role: str
    primary_model: str
    reserve_model: str
    reason: PrimaryFailureReason

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.profile.strip():
            raise ValueError("reserve request requires task and profile")

    def as_public_dict(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "profile": self.profile,
            "role": self.role,
            "primary_model": self.primary_model,
            "reserve_model": self.reserve_model,
            "reason": self.reason.value,
        }


def build_shadow_request(
    config: TechnicalReserveConfig,
    *,
    task_id: str,
    profile: str,
    role: str,
    reason: PrimaryFailureReason,
    allow_capacity_contingency: bool = False,
) -> ReserveRequest | None:
    if not config.observes_profile(profile):
        return None
    if reserve_disposition(
        reason,
        allow_capacity_contingency=allow_capacity_contingency,
    ) is not ReserveDisposition.RESERVE_REQUIRED:
        return None
    try:
        route = MODEL_ROUTES[role]
    except KeyError as exc:
        raise ValueError(f"unknown reserve model role {role!r}") from exc
    return ReserveRequest(
        task_id=task_id,
        profile=profile,
        role=route.role,
        primary_model=route.primary_model,
        reserve_model=route.reserve_model,
        reason=reason,
    )


def build_reserve_request(
    config: TechnicalReserveConfig,
    **kwargs,
) -> ReserveRequest | None:
    profile = kwargs["profile"]
    if not config.requests_profile(profile):
        return None
    shadow_compatible = TechnicalReserveConfig(
        mode=ReserveMode.SHADOW,
        kill_switch_active=False,
        enabled_profiles=frozenset({profile}),
    )
    return build_shadow_request(shadow_compatible, **kwargs)

def _parse_bool(value: str, *, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"{name} must be true or false")


def _optional_positive_float(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be numeric") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value
