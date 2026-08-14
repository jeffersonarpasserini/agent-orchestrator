import importlib
import sys
import types
import unittest
from unittest.mock import patch

from hermes_plugins.alibaba_coding_plan_glm.protocol import glm_request_parameters


class GlmProtocolTest(unittest.TestCase):
    def test_glm_enables_streamed_tools_and_preserves_thinking(self):
        extra_body, top_level = glm_request_parameters(
            "glm-5.2", {"enabled": True, "effort": "high"}
        )

        self.assertEqual(
            extra_body,
            {"tool_stream": True, "clear_thinking": False},
        )
        self.assertEqual(top_level, {"reasoning_effort": "high"})

    def test_glm_can_disable_thinking_for_structured_output(self):
        extra_body, top_level = glm_request_parameters(
            "glm-5.2", {"enabled": False, "effort": "none"}
        )

        self.assertEqual(
            extra_body,
            {
                "tool_stream": True,
                "clear_thinking": False,
                "enable_thinking": False,
                "response_format": {"type": "json_object"},
            },
        )
        self.assertEqual(top_level, {})

    def test_other_models_are_unchanged(self):
        self.assertEqual(glm_request_parameters("qwen3.8-max", {"effort": "high"}), ({}, {}))
        self.assertEqual(glm_request_parameters("deepseek-v4-pro"), ({}, {}))

    def test_unknown_reasoning_effort_is_not_forwarded(self):
        extra_body, top_level = glm_request_parameters(
            "glm-5.2", {"enabled": True, "effort": "unsupported"}
        )

        self.assertEqual(
            extra_body,
            {"tool_stream": True, "clear_thinking": False},
        )
        self.assertEqual(top_level, {})

    def test_provider_registration_is_pinned_to_token_plan(self):
        registered = []

        class FakeProviderProfile:
            def __init__(self, **values):
                self.__dict__.update(values)

        providers = types.ModuleType("providers")
        providers.register_provider = registered.append
        providers_base = types.ModuleType("providers.base")
        providers_base.ProviderProfile = FakeProviderProfile

        package_name = "hermes_plugins.alibaba_coding_plan_glm"
        package = sys.modules[package_name]
        with patch.dict(
            sys.modules,
            {"providers": providers, "providers.base": providers_base},
        ):
            importlib.reload(package)

        self.assertEqual(len(registered), 1)
        profile = registered[0]
        self.assertEqual(profile.name, "alibaba-coding-plan")
        self.assertEqual(
            profile.base_url,
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        )
        self.assertNotIn("coding-intl.dashscope.aliyuncs.com", profile.base_url)
        self.assertIn("ALIBABA_CODING_PLAN_API_KEY", profile.env_vars)
        self.assertEqual(
            profile.build_extra_body(model="qwen3.8-max"),
            {},
        )


if __name__ == "__main__":
    unittest.main()
