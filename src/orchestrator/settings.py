from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path

from orchestrator.technical_reserve import TechnicalReserveConfig


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    otlp_endpoint: str
    service_name: str
    hermes_profiles_root: Path
    deepseek_daily_budget_usd: float
    deepseek_pilot_budget_usd: float
    deepseek_pilot_started_at: datetime
    technical_reserve: TechnicalReserveConfig = field(
        default_factory=TechnicalReserveConfig
    )

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get("ORCHESTRATOR_DATABASE_URL", "")
        if not database_url:
            raise RuntimeError("ORCHESTRATOR_DATABASE_URL is required")
        profiles_root = os.environ.get("HERMES_PROFILES_ROOT", "").strip()
        if not profiles_root:
            raise RuntimeError("HERMES_PROFILES_ROOT is required")
        try:
            daily_budget = float(os.environ["DEEPSEEK_DAILY_BUDGET_USD"])
            pilot_budget = float(os.environ["DEEPSEEK_PILOT_BUDGET_USD"])
            pilot_started_at = datetime.fromisoformat(
                os.environ["DEEPSEEK_PILOT_STARTED_AT"]
            )
        except (KeyError, ValueError) as exc:
            raise RuntimeError("invalid DeepSeek pilot configuration") from exc
        if daily_budget <= 0 or pilot_budget <= 0:
            raise RuntimeError("DeepSeek budget limits must be positive")
        if pilot_started_at.tzinfo is None:
            raise RuntimeError("DeepSeek pilot start must include a timezone")
        return cls(
            environment=os.environ.get("ORCHESTRATOR_ENV", "development"),
            database_url=database_url,
            otlp_endpoint=os.environ.get(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "http://phoenix:6006/v1/traces",
            ),
            service_name=os.environ.get(
                "OTEL_SERVICE_NAME",
                "agent-orchestrator",
            ),
            hermes_profiles_root=Path(profiles_root).expanduser(),
            deepseek_daily_budget_usd=daily_budget,
            deepseek_pilot_budget_usd=pilot_budget,
            deepseek_pilot_started_at=pilot_started_at,
            technical_reserve=TechnicalReserveConfig.from_env(),
        )
