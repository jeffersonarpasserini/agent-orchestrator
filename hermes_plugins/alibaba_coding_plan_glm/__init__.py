"""Candidate-only Alibaba Token Plan overrides for GLM-5.2."""

from .protocol import glm_request_parameters

try:
    from providers import register_provider
    from providers.base import ProviderProfile
except ModuleNotFoundError:  # Imported by Agent Orchestrator's unit tests.
    register_provider = None
else:
    class AlibabaCodingPlanGlmProfile(ProviderProfile):
        def build_extra_body(self, *, model=None, reasoning_config=None, **context):
            extra_body, _ = glm_request_parameters(model, reasoning_config)
            return extra_body

        def build_api_kwargs_extras(
            self, *, reasoning_config=None, model=None, **context
        ):
            _, top_level = glm_request_parameters(model, reasoning_config)
            return {}, top_level


    register_provider(
        AlibabaCodingPlanGlmProfile(
            name="alibaba-coding-plan",
            aliases=("alibaba_coding", "alibaba-coding", "dashscope-coding"),
            display_name="Alibaba Cloud Token Plan (GLM pilot)",
            description="Candidate-only GLM-5.2 protocol overrides",
            env_vars=(
                "ALIBABA_CODING_PLAN_API_KEY",
                "DASHSCOPE_API_KEY",
                "ALIBABA_CODING_PLAN_BASE_URL",
            ),
            base_url=(
                "https://token-plan.ap-southeast-1.maas.aliyuncs.com/"
                "compatible-mode/v1"
            ),
            auth_type="api_key",
        )
    )
