from orchestrator.api.app import create_app
from orchestrator.settings import Settings
from orchestrator.telemetry import configure_telemetry


settings = Settings.from_env()
configure_telemetry(settings)
app = create_app(settings)
