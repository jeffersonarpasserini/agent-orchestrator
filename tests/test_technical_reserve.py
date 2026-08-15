import os
import unittest
from unittest.mock import patch

from orchestrator.technical_reserve import (
    MODEL_ROUTES,
    PrimaryFailureReason,
    PrimaryRouteError,
    QwenCloudErrorEvidence,
    ReserveDisposition,
    ReserveMode,
    TechnicalReserveConfig,
    build_shadow_request,
    reserve_disposition,
    normalize_qwencloud_error,
)


class TechnicalReserveConfigTest(unittest.TestCase):
    def test_normalizes_only_structured_qwencloud_quota_evidence(self):
        cases = (
            (QwenCloudErrorEvidence(401, "InvalidApiKey", "Invalid API-key"),
             PrimaryFailureReason.AUTHENTICATION_FAILED),
            (QwenCloudErrorEvidence(400, "InvalidParameter", "bad input"),
             PrimaryFailureReason.INVALID_REQUEST),
            (QwenCloudErrorEvidence(429, "", "hour allocated quota exceeded"),
             PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED),
            (QwenCloudErrorEvidence(429, "", "concurrency allocated quota exceeded"),
             PrimaryFailureReason.SUBSCRIPTION_CAPACITY_UNAVAILABLE),
            (QwenCloudErrorEvidence(
                429, "insufficient_quota", "You exceeded your current quota",
                quota_depleted_confirmed=True,
            ), PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED),
        )
        for evidence, expected in cases:
            with self.subTest(evidence=evidence):
                self.assertEqual(normalize_qwencloud_error(evidence), expected)

    def test_bare_429_and_ambiguous_quota_never_authorize_reserve(self):
        for evidence in (
            QwenCloudErrorEvidence(http_status=429),
            QwenCloudErrorEvidence(
                429, "insufficient_quota", "You exceeded your current quota"
            ),
        ):
            reason = normalize_qwencloud_error(evidence)
            self.assertEqual(
                reason, PrimaryFailureReason.FINANCIAL_EVIDENCE_UNAVAILABLE
            )
            self.assertEqual(reserve_disposition(reason), ReserveDisposition.BLOCKED)
    def test_defaults_to_off_with_kill_switch(self):
        with patch.dict(os.environ, {}, clear=True):
            config = TechnicalReserveConfig.from_env()

        self.assertEqual(config.mode, ReserveMode.OFF)
        self.assertTrue(config.kill_switch_active)
        self.assertFalse(config.can_call_provider)
        self.assertFalse(config.permits_profile("barclay"))

    def test_shadow_mode_never_permits_provider_call(self):
        environment = {
            "DEEPSEEK_RESERVE_MODE": "shadow",
            "DEEPSEEK_RESERVE_KILL_SWITCH": "true",
            "DEEPSEEK_RESERVE_PROFILES": "barclay,tuvok",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = TechnicalReserveConfig.from_env()

        self.assertEqual(config.enabled_profiles, frozenset({"barclay", "tuvok"}))
        self.assertFalse(config.permits_profile("barclay"))

    def test_enforced_mode_requires_kill_switch_off_profiles_and_budgets(self):
        environment = {
            "DEEPSEEK_RESERVE_MODE": "enforced",
            "DEEPSEEK_RESERVE_KILL_SWITCH": "false",
            "DEEPSEEK_RESERVE_PROFILES": "barclay",
            "DEEPSEEK_RESERVE_DAILY_BUDGET_USD": "1.00",
            "DEEPSEEK_RESERVE_MONTHLY_BUDGET_USD": "10.00",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = TechnicalReserveConfig.from_env()

        self.assertTrue(config.can_call_provider)
        self.assertTrue(config.permits_profile("barclay"))
        self.assertFalse(config.permits_profile("tuvok"))

    def test_enforced_mode_fails_closed_when_incomplete(self):
        environment = {
            "DEEPSEEK_RESERVE_MODE": "enforced",
            "DEEPSEEK_RESERVE_KILL_SWITCH": "false",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "technical reserve configuration"):
                TechnicalReserveConfig.from_env()

    def test_rejects_ambiguous_boolean(self):
        environment = {"DEEPSEEK_RESERVE_KILL_SWITCH": "yes"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "must be true or false"):
                TechnicalReserveConfig.from_env()

    def test_model_routes_do_not_infer_flash_equivalence(self):
        flash = MODEL_ROUTES["flash"]
        pro = MODEL_ROUTES["pro"]

        self.assertEqual(flash.primary_model, "deepseek-v4-flash-0731")
        self.assertEqual(flash.reserve_model, "deepseek-v4-flash")
        self.assertNotEqual(flash.primary_model, flash.reserve_model)
        self.assertEqual(pro.primary_model, "deepseek-v4-pro")
        self.assertEqual(pro.reserve_model, "deepseek-v4-pro")

    def test_only_subscription_quota_failures_request_reserve_by_default(self):
        self.assertEqual(
            reserve_disposition(
                PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED
            ),
            ReserveDisposition.RESERVE_REQUIRED,
        )
        self.assertEqual(
            reserve_disposition(
                PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED
            ),
            ReserveDisposition.RESERVE_REQUIRED,
        )
        blocked = set(PrimaryFailureReason) - {
            PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
            PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        }
        for reason in blocked:
            with self.subTest(reason=reason):
                self.assertEqual(
                    reserve_disposition(reason), ReserveDisposition.BLOCKED
                )

    def test_capacity_contingency_requires_explicit_policy(self):
        reason = PrimaryFailureReason.SUBSCRIPTION_CAPACITY_UNAVAILABLE

        self.assertEqual(
            reserve_disposition(reason), ReserveDisposition.BLOCKED
        )
        self.assertEqual(
            reserve_disposition(reason, allow_capacity_contingency=True),
            ReserveDisposition.RESERVE_REQUIRED,
        )

    def test_shadow_request_contains_only_public_routing_metadata(self):
        config = TechnicalReserveConfig(
            mode=ReserveMode.SHADOW,
            kill_switch_active=False,
            enabled_profiles=frozenset({"barclay"}),
        )

        request = build_shadow_request(
            config,
            task_id="FUTURE-01",
            profile="barclay",
            role="flash",
            reason=PrimaryFailureReason.SUBSCRIPTION_CREDITS_EXHAUSTED,
        )

        self.assertIsNotNone(request)
        self.assertEqual(
            set(request.as_public_dict()),
            {
                "task_id",
                "profile",
                "role",
                "primary_model",
                "reserve_model",
                "reason",
            },
        )
        self.assertNotIn("prompt", request.as_public_dict())
        self.assertNotIn("api_key", request.as_public_dict())

    def test_shadow_request_is_absent_for_noneligible_or_disabled_profile(self):
        config = TechnicalReserveConfig(
            mode=ReserveMode.SHADOW,
            kill_switch_active=False,
            enabled_profiles=frozenset({"barclay"}),
        )

        self.assertIsNone(build_shadow_request(
            config,
            task_id="FUTURE-01",
            profile="barclay",
            role="flash",
            reason=PrimaryFailureReason.AUTHENTICATION_FAILED,
        ))
        self.assertIsNone(build_shadow_request(
            config,
            task_id="FUTURE-01",
            profile="tuvok",
            role="pro",
            reason=PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
        ))

    def test_primary_route_error_preserves_normalized_reason(self):
        error = PrimaryRouteError(
            PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
            "Token Plan window exhausted",
            session_id="qwen-session-1",
        )

        self.assertEqual(
            error.reason,
            PrimaryFailureReason.SUBSCRIPTION_WINDOW_EXHAUSTED,
        )
        self.assertEqual(str(error), "Token Plan window exhausted")
        self.assertEqual(error.session_id, "qwen-session-1")


if __name__ == "__main__":
    unittest.main()
