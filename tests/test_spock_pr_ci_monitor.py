import importlib.util
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
