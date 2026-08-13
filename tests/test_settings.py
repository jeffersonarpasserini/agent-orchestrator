import os
from pathlib import Path
import unittest
from unittest.mock import patch

from orchestrator.settings import Settings


class SettingsTest(unittest.TestCase):
    valid_environment = {
        "ORCHESTRATOR_DATABASE_URL": "postgresql://local",
        "HERMES_PROFILES_ROOT": "/srv/hermes/profiles",
        "DEEPSEEK_DAILY_BUDGET_USD": "1.00",
        "DEEPSEEK_PILOT_BUDGET_USD": "10.00",
        "DEEPSEEK_PILOT_STARTED_AT": "2026-08-11T00:00:00-03:00",
    }

    def test_loads_valid_pilot_configuration(self):
        with patch.dict(os.environ, self.valid_environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.hermes_profiles_root, Path("/srv/hermes/profiles"))
        self.assertEqual(settings.deepseek_daily_budget_usd, 1.0)
        self.assertEqual(settings.deepseek_pilot_budget_usd, 10.0)
        self.assertIsNotNone(settings.deepseek_pilot_started_at.utcoffset())

    def test_rejects_missing_pilot_configuration(self):
        environment = dict(self.valid_environment)
        environment.pop("DEEPSEEK_DAILY_BUDGET_USD")
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "pilot configuration"):
                Settings.from_env()

    def test_rejects_pilot_start_without_timezone(self):
        environment = dict(self.valid_environment)
        environment["DEEPSEEK_PILOT_STARTED_AT"] = "2026-08-11T00:00:00"
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "include a timezone"):
                Settings.from_env()

    def test_task_intake_is_disabled_without_server_identity(self):
        with patch.dict(os.environ, self.valid_environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.task_intake_bearer_token, "")
        self.assertEqual(settings.task_intake_principal, "")
        self.assertEqual(settings.task_intake_origin, "")


if __name__ == "__main__":
    unittest.main()
