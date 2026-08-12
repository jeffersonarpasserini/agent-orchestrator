import json
from pathlib import Path
import tempfile
import unittest

from orchestrator.reserve_smoke import load_existing_deepseek_key


class ReserveSmokeTest(unittest.TestCase):
    def test_loads_exactly_one_existing_key(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "auth.json"
            path.write_text(json.dumps({
                "credential_pool": {"deepseek": [{"access_token": "secret"}]}
            }))
            self.assertEqual(load_existing_deepseek_key(path), "secret")

    def test_rejects_missing_or_ambiguous_key(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "auth.json"
            for credentials in ([], [{"access_token": "a"}, {"access_token": "b"}]):
                path.write_text(json.dumps({
                    "credential_pool": {"deepseek": credentials}
                }))
                with self.assertRaises(RuntimeError):
                    load_existing_deepseek_key(path)


if __name__ == "__main__":
    unittest.main()
