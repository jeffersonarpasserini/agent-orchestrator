"""Request parameters required by GLM-5.2 on Alibaba OpenAI-compatible APIs."""

from __future__ import annotations

from typing import Any, Mapping


_GLM_MODEL = "glm-5.2"
_REASONING_EFFORTS = {
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
}


def glm_request_parameters(
    model: str | None,
    reasoning_config: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return candidate-only body and top-level parameters for GLM-5.2.

    ``tool_stream`` is harmless on calls without tools and only takes effect
    when streaming is active. Preserved thinking is explicit so a second turn
    cannot silently discard provider-native reasoning.
    """

    if (model or "").strip().lower() != _GLM_MODEL:
        return {}, {}

    config = dict(reasoning_config or {})
    extra_body: dict[str, Any] = {
        "tool_stream": True,
        "clear_thinking": False,
    }
    top_level: dict[str, Any] = {}

    effort = str(config.get("effort") or "").strip().lower()
    if config.get("enabled") is False or effort == "none":
        extra_body["enable_thinking"] = False
        extra_body["response_format"] = {"type": "json_object"}
    elif effort in _REASONING_EFFORTS:
        top_level["reasoning_effort"] = effort

    return extra_body, top_level
