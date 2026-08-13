import importlib.util
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "spock_pr_ci_monitor.py"
SPEC = importlib.util.spec_from_file_location("spock_pr_ci_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(monitor)


class SpockPrCiMonitorTest(unittest.TestCase):
    def test_reports_missing_checks_as_pending(self):
        payload = monitor.normalize(
            [{
                "number": 2,
                "title": "test",
                "url": "https://example.test/pr/2",
                "headRefName": "agent/test",
                "headRefOid": "abc",
                "isDraft": True,
                "mergeStateStatus": "BLOCKED",
                "statusCheckRollup": [],
            }],
            "owner/repo",
        )
        self.assertEqual("pending", payload["prs"][0]["overall"])
        self.assertEqual(list(monitor.EXPECTED_CHECKS), payload["prs"][0]["missing_expected_checks"])

    def test_failure_takes_precedence(self):
        checks = [
            {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
            for name in monitor.EXPECTED_CHECKS
        ]
        checks[1]["conclusion"] = "FAILURE"
        payload = monitor.normalize(
            [{"number": 1, "statusCheckRollup": checks}], "owner/repo"
        )
        self.assertEqual("failure", payload["prs"][0]["overall"])

    def test_all_expected_checks_complete_successfully(self):
        checks = [
            {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
            for name in reversed(monitor.EXPECTED_CHECKS)
        ]
        payload = monitor.normalize(
            [{"number": 1, "statusCheckRollup": checks}], "owner/repo"
        )
        self.assertEqual("success", payload["prs"][0]["overall"])
        self.assertEqual([], payload["prs"][0]["missing_expected_checks"])
        self.assertEqual(sorted(monitor.EXPECTED_CHECKS), [item["name"] for item in payload["prs"][0]["checks"]])

    def test_persists_newest_pr_snapshot_with_explicit_arguments(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, "", "")

        payload = {
            "repository": "owner/repo",
            "expected_checks": list(monitor.EXPECTED_CHECKS),
            "prs": [
                {"number": 2, "head_sha": "old", "overall": "failure"},
                {"number": 3, "head_sha": "new", "overall": "success"},
            ],
        }

        error = monitor.persist_snapshot(payload, runner=runner, hermes_bin="/safe/hermes")

        self.assertIsNone(error)
        self.assertEqual(5, len(calls))
        values = {command[-2]: command[-1] for command, _ in calls}
        self.assertEqual("3", values["last_pr"])
        self.assertEqual("new", values["last_head_sha"])
        self.assertEqual("success", values["last_result"])
        self.assertTrue(all(command[0] == "/safe/hermes" for command, _ in calls))
        self.assertTrue(all(kwargs["timeout"] == 15 for _, kwargs in calls))

    def test_reports_notepad_subprocess_failure(self):
        def runner(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        error = monitor.persist_snapshot(
            {
                "repository": "owner/repo",
                "expected_checks": list(monitor.EXPECTED_CHECKS),
                "prs": [{"number": 2, "head_sha": "abc", "overall": "failure"}],
            },
            runner=runner,
            hermes_bin="/safe/hermes",
        )

        self.assertEqual("TimeoutExpired", error)


if __name__ == "__main__":
    unittest.main()
