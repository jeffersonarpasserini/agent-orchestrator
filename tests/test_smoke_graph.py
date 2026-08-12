import unittest

from orchestrator.graphs.smoke import run_smoke_workflow


class SmokeGraphTest(unittest.TestCase):
    def test_normalizes_and_completes(self):
        result = run_smoke_workflow("  Phase THREE  ")

        self.assertEqual(result["normalized"], "phase three")
        self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
