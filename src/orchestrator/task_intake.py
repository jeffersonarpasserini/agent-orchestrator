from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Literal, Protocol

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator


TaskState = Literal[
    "received", "rejected", "planned", "awaiting_approval", "running",
    "cancelled", "blocked", "completed", "resumed",
]


class TaskBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: Literal["USD"] = "USD"
    limit: float = Field(ge=0, le=10_000)
    paid_calls: Literal["forbidden", "approval_required"]


class TaskEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    objective: str = Field(min_length=1, max_length=2_000)
    scope: list[str] = Field(min_length=1, max_length=50)
    priority: Literal["low", "normal", "high", "urgent"]
    owner: str = Field(min_length=1, max_length=200)
    due_at: datetime
    budget: TaskBudget
    approval_policy: list[str] = Field(min_length=1, max_length=50)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=50)

    @field_validator("due_at")
    @classmethod
    def due_at_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must include a timezone")
        return value

    @field_validator("scope", "approval_policy", "acceptance_criteria")
    @classmethod
    def list_items_are_bounded(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 500 for item in cleaned):
            raise ValueError("list items must contain 1 to 500 characters")
        return cleaned

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude_none=False)

    def canonical_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class TaskRecord:
    request_id: str
    principal: str
    origin: str
    state: TaskState
    created_at: datetime
    updated_at: datetime
    idempotent_replay: bool = False


class TaskConflictError(RuntimeError):
    pass


class InvalidTaskTransitionError(RuntimeError):
    pass


class TaskNotFoundError(RuntimeError):
    pass


class TaskStore(Protocol):
    def submit(self, envelope: TaskEnvelope, principal: str, origin: str) -> TaskRecord: ...

    def transition(self, request_id: str, principal: str, event: Literal["cancelled", "resumed"]) -> TaskRecord: ...


class PostgresTaskStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    @staticmethod
    def _record(row: tuple[object, ...], *, replay: bool = False) -> TaskRecord:
        return TaskRecord(
            request_id=str(row[0]), principal=str(row[1]), origin=str(row[2]),
            state=str(row[3]), created_at=row[4], updated_at=row[5],  # type: ignore[arg-type]
            idempotent_replay=replay,
        )

    def submit(self, envelope: TaskEnvelope, principal: str, origin: str) -> TaskRecord:
        digest = envelope.canonical_hash()
        payload = envelope.canonical_payload()
        with closing(psycopg.connect(self.database_url, connect_timeout=3)) as conn:
            with conn.transaction(), conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO orchestrator.tasks
                       (request_id, principal, origin, envelope_hash, envelope, state)
                       VALUES (%s, %s, %s, %s, %s, 'received')
                       ON CONFLICT (request_id) DO NOTHING
                       RETURNING request_id, principal, origin, state, created_at, updated_at""",
                    (envelope.request_id, principal, origin, digest, Jsonb(payload)),
                )
                inserted = cursor.fetchone()
                if inserted:
                    cursor.execute(
                        """INSERT INTO orchestrator.task_events
                           (request_id, principal, event, details)
                           VALUES (%s, %s, 'received', %s)""",
                        (envelope.request_id, principal, Jsonb({"origin": origin})),
                    )
                    return self._record(inserted)
                cursor.execute(
                    """SELECT request_id, principal, origin, state, created_at,
                              updated_at, envelope_hash
                         FROM orchestrator.tasks WHERE request_id=%s FOR UPDATE""",
                    (envelope.request_id,),
                )
                existing = cursor.fetchone()
                if existing is None or existing[1] != principal or existing[6] != digest:
                    raise TaskConflictError("request_id already exists with different content")
                return self._record(existing[:6], replay=True)

    def transition(
        self, request_id: str, principal: str, event: Literal["cancelled", "resumed"],
    ) -> TaskRecord:
        with closing(psycopg.connect(self.database_url, connect_timeout=3)) as conn:
            with conn.transaction(), conn.cursor() as cursor:
                cursor.execute(
                    """SELECT request_id, principal, origin, state, created_at, updated_at
                         FROM orchestrator.tasks WHERE request_id=%s FOR UPDATE""",
                    (request_id,),
                )
                existing = cursor.fetchone()
                if existing is None or existing[1] != principal:
                    raise TaskNotFoundError(request_id)
                current = str(existing[3])
                allowed = event == "cancelled" and current not in {"cancelled", "completed"}
                allowed = allowed or (event == "resumed" and current in {"cancelled", "blocked"})
                if not allowed:
                    raise InvalidTaskTransitionError(f"cannot transition {current} to {event}")
                next_state = "cancelled" if event == "cancelled" else "awaiting_approval"
                cursor.execute(
                    """UPDATE orchestrator.tasks SET state=%s, updated_at=now()
                         WHERE request_id=%s
                         RETURNING request_id, principal, origin, state, created_at, updated_at""",
                    (next_state, request_id),
                )
                updated = cursor.fetchone()
                cursor.execute(
                    """INSERT INTO orchestrator.task_events
                       (request_id, principal, event, details) VALUES (%s, %s, %s, %s)""",
                    (request_id, principal, event, Jsonb({"previous_state": current})),
                )
                assert updated is not None
                return self._record(updated)
