from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Mapping

@dataclass(frozen=True)
class SessionDetails:
    usage: Mapping[str, object]
    tool_calls: tuple[Mapping[str, object], ...]

class SQLiteHermesSessionStore:
    def __init__(self, profiles_root: Path) -> None:
        self.profiles_root = profiles_root.resolve()

    def read(self, profile: str, session_id: str) -> SessionDetails:
        database = ((self.profiles_root.parent / "state.db") if profile == "default" else (self.profiles_root / profile / "state.db")).resolve()
        if (profile != "default" and self.profiles_root not in database.parents) or not database.is_file():
            raise FileNotFoundError(f"Hermes state database not found for {profile!r}")
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            session = connection.execute("""
                SELECT model, billing_provider, billing_mode, api_call_count,
                       input_tokens, output_tokens, cache_read_tokens,
                       cache_write_tokens, reasoning_tokens, estimated_cost_usd,
                       actual_cost_usd, cost_status, cost_source, tool_call_count
                  FROM sessions WHERE id = ?
            """, (session_id,)).fetchone()
            if session is None:
                return SessionDetails({}, ())
            calls = []
            rows = connection.execute("""
                SELECT tool_calls FROM messages
                 WHERE session_id = ? AND tool_calls IS NOT NULL ORDER BY id
            """, (session_id,))
            for row in rows:
                decoded = json.loads(row["tool_calls"])
                if isinstance(decoded, list):
                    calls.extend(item for item in decoded if isinstance(item, dict))
                elif isinstance(decoded, dict):
                    calls.append(decoded)
            return SessionDetails(dict(session), tuple(calls))
        finally:
            connection.close()
