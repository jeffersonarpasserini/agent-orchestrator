from pathlib import Path
import sqlite3
import tempfile
import unittest

from orchestrator.pilot_record_task import session_metrics


class PilotRecordTaskTest(unittest.TestCase):
    def test_aggregates_complete_sessions_and_costs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = root / "spock"
            profile.mkdir()
            with sqlite3.connect(profile / "state.db") as connection:
                connection.execute("""
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY, model TEXT, billing_provider TEXT,
                        billing_mode TEXT, api_call_count INTEGER,
                        input_tokens INTEGER, output_tokens INTEGER,
                        cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                        reasoning_tokens INTEGER, started_at REAL, ended_at REAL,
                        last_activity_at REAL
                    )
                """)
                connection.execute(
                    "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("s1", "gpt-5.6-luna", "openai-codex",
                     "subscription_included", 2, 1_000_000, 1_000_000,
                     0, 0, 500_000, 10.0, 12.5, 12.5),
                )
            models, evidence, calls, latency, simulated, billed = session_metrics(
                root, ("spock/s1",)
            )
            self.assertEqual(models, ("spock/gpt-5.6-luna",))
            self.assertEqual(evidence, ("s1",))
            self.assertEqual(calls, 2)
            self.assertEqual(latency, 2.5)
            self.assertEqual(simulated, 1.4)
            self.assertEqual(billed, 0.0)

    def test_incomplete_session_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = root / "spock"
            profile.mkdir()
            with sqlite3.connect(profile / "state.db") as connection:
                connection.execute("""
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY, model TEXT, billing_provider TEXT,
                        billing_mode TEXT, api_call_count INTEGER,
                        input_tokens INTEGER, output_tokens INTEGER,
                        cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                        reasoning_tokens INTEGER, started_at REAL, ended_at REAL,
                        last_activity_at REAL
                    )
                """)
                connection.execute(
                    "INSERT INTO sessions VALUES ('s1','gpt-5.6-luna','openai-codex',"
                    "'subscription_included',1,1,1,0,0,0,10,NULL,NULL)"
                )
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                session_metrics(root, ("spock/s1",))


if __name__ == "__main__":
    unittest.main()
