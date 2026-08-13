import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tuvok-nvd-update.sh"


class TuvokNvdUpdateScriptTests(unittest.TestCase):
    def run_script(self, fake_dependency_check: str, *, key: str = "test-secret", timeout: str = "5"):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            profile_env = temp / "profile.env"
            profile_env.write_text(f"NVD_API_KEY={key}\n", encoding="utf-8")
            dependency_check = temp / "dependency-check"
            dependency_check.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\n" + textwrap.dedent(fake_dependency_check),
                encoding="utf-8",
            )
            dependency_check.chmod(dependency_check.stat().st_mode | stat.S_IXUSR)
            data_dir = temp / "data"
            environment = {
                **os.environ,
                "TUVOK_ENV_FILE": str(profile_env),
                "DEPENDENCY_CHECK_BIN": str(dependency_check),
                "DEPENDENCY_CHECK_DATA_DIR": str(data_dir),
                "NVD_UPDATE_TIMEOUT_SECONDS": timeout,
            }
            return subprocess.run(
                ["bash", str(SCRIPT)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

    def test_passes_key_by_environment_not_command_line(self):
        result = self.run_script(
            """
            [[ "${NVD_API_KEY:-}" == "test-secret" ]]
            [[ " $* " != *" test-secret "* ]]
            [[ " $* " == *" --updateonly "* ]]
            """
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "NVD local database update completed successfully\n")
        self.assertNotIn("test-secret", result.stdout + result.stderr)

    def test_reports_timeout_without_exposing_key(self):
        result = self.run_script("sleep 2\n", key="do-not-log", timeout="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeded 1s", result.stderr)
        self.assertNotIn("do-not-log", result.stdout + result.stderr)

    def test_rejects_missing_key(self):
        result = self.run_script(":\n", key="")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NVD_API_KEY is not configured", result.stderr)


if __name__ == "__main__":
    unittest.main()
