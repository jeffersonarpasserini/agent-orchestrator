from datetime import datetime, timezone
from pathlib import Path
import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from orchestrator.api.app import create_app
from orchestrator.settings import Settings
from orchestrator.task_intake import (
    InvalidTaskTransitionError,
    TaskConflictError,
    TaskEnvelope,
    TaskNotFoundError,
    TaskRecord,
)
from tests.test_api_app import FakeBudgetGuard, FakeMetricsStore, route_endpoint


def valid_payload() -> dict[str, object]:
    return {
        "request_id": "O4:test-001",
        "objective": "Validate canonical task intake",
        "scope": ["task intake"],
        "priority": "normal",
        "owner": "operations",
        "due_at": "2026-08-20T12:00:00-03:00",
        "budget": {"currency": "USD", "limit": 0, "paid_calls": "forbidden"},
        "approval_policy": ["No material action without approval"],
        "acceptance_criteria": ["Request is persisted idempotently"],
    }


class FakeTaskStore:
    def __init__(self):
        self.records: dict[str, tuple[str, str, str]] = {}
        self.events: list[str] = []

    def submit(self, envelope, principal, origin):
        digest = envelope.canonical_hash()
        existing = self.records.get(envelope.request_id)
        replay = False
        if existing:
            if existing != (principal, origin, digest):
                raise TaskConflictError("request_id already exists with different content")
            replay = True
        else:
            self.records[envelope.request_id] = (principal, origin, digest)
            self.events.append("received")
        now = datetime.now(timezone.utc)
        return TaskRecord(envelope.request_id, principal, origin, "received", now, now, replay)

    def transition(self, request_id, principal, event):
        existing = self.records.get(request_id)
        if not existing or existing[0] != principal:
            raise TaskNotFoundError(request_id)
        if event == "resumed" and (not self.events or self.events[-1] != "cancelled"):
            raise InvalidTaskTransitionError("cannot resume active task")
        self.events.append(event)
        state = "cancelled" if event == "cancelled" else "awaiting_approval"
        now = datetime.now(timezone.utc)
        return TaskRecord(request_id, principal, existing[1], state, now, now)


class TaskEnvelopeTest(unittest.TestCase):
    def test_hash_is_stable_for_equivalent_payload(self):
        left = TaskEnvelope.model_validate(valid_payload())
        right_payload = dict(reversed(list(valid_payload().items())))
        right = TaskEnvelope.model_validate(right_payload)
        self.assertEqual(left.canonical_hash(), right.canonical_hash())

    def test_rejects_identity_extra_naive_due_date_and_empty_material_fields(self):
        for mutation in (
            {"principal": "forged"},
            {"due_at": "2026-08-20T12:00:00"},
            {"owner": ""},
            {"acceptance_criteria": []},
        ):
            payload = valid_payload()
            payload.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                TaskEnvelope.model_validate(payload)


class TaskIntakeApiTest(unittest.TestCase):
    def setUp(self):
        self.store = FakeTaskStore()
        settings = Settings(
            environment="test",
            database_url="postgresql://unused",
            otlp_endpoint="http://unused",
            service_name="test",
            hermes_profiles_root=Path("/unused"),
            deepseek_daily_budget_usd=1,
            deepseek_pilot_budget_usd=10,
            deepseek_pilot_started_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
            task_intake_bearer_token="secret-test-token",
            task_intake_principal="owner:test",
            task_intake_origin="api:test",
        )
        app = create_app(
            settings,
            budget_guard=FakeBudgetGuard(),
            metrics_store=FakeMetricsStore(),
            task_store=self.store,
            database_checker=lambda _: {"database": "test", "user": "test"},
        )
        self.app = app
        self.submit = route_endpoint(app, "/tasks")
        self.principal = "owner:test"
        task_route = next(route for route in app.routes if getattr(route, "path", None) == "/tasks")
        self.authenticate = task_route.dependant.dependencies[0].call

    def test_authentication_fails_closed_without_persisting(self):
        for credentials in (
            None,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong"),
        ):
            with self.assertRaises(HTTPException) as raised:
                self.authenticate(credentials)
            self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual({}, self.store.records)

    def test_submit_is_idempotent_and_conflicting_reuse_is_rejected(self):
        first = self.submit(TaskEnvelope.model_validate(valid_payload()), self.principal)
        replay = self.submit(TaskEnvelope.model_validate(valid_payload()), self.principal)
        changed = valid_payload()
        changed["objective"] = "Different objective"
        with self.assertRaises(HTTPException) as conflict:
            self.submit(TaskEnvelope.model_validate(changed), self.principal)

        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(conflict.exception.status_code, 409)
        self.assertEqual(self.store.events, ["received"])

    def test_cancel_and_resume_require_auth_and_return_to_approval(self):
        self.submit(TaskEnvelope.model_validate(valid_payload()), self.principal)
        cancel = route_endpoint(self.app, "/tasks/{request_id}/cancel")
        resume = route_endpoint(self.app, "/tasks/{request_id}/resume")
        cancelled = cancel("O4:test-001", self.principal)
        resumed = resume("O4:test-001", self.principal)

        self.assertEqual(cancelled["state"], "cancelled")
        self.assertEqual(resumed["state"], "awaiting_approval")
        self.assertEqual(self.store.events, ["received", "cancelled", "resumed"])


if __name__ == "__main__":
    unittest.main()
