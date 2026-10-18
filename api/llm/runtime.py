"""Composition root for one explicitly configured, immutable LLM target."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from ..core.config import Settings, settings
from .adapters.gemini import (
    GEMINI_OFFICIAL_BASE_URL,
    GEMINI_PROVIDER_LABEL,
    GeminiAdapter,
)
from .adapters.nvidia import (
    NVIDIA_NIM_MODEL_ID,
    NVIDIA_NIM_OFFICIAL_BASE_URL,
    NVIDIA_NIM_PROVIDER_LABEL,
    NvidiaNimAdapter,
)
from .adapters.groq import GroqAdapter
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .adapters.openrouter import OpenRouterAdapter
from .contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    LLMGateway,
    LLMTarget,
)


class LLMRuntimeConfigurationError(RuntimeError):
    """A real invocation was requested without a complete explicit target."""


@dataclass(frozen=True)
class LLMRuntime:
    target: LLMTarget
    gateway: LLMGateway


def build_llm_runtime(configuration: Settings) -> LLMRuntime:
    identity = (
        configuration.llm_target_id,
        configuration.llm_provider_label,
        configuration.llm_model,
        configuration.llm_base_url,
    )
    if not all(value is not None and bool(value.strip()) for value in identity):
        raise LLMRuntimeConfigurationError(
            "Configure LLM_TARGET_ID, LLM_PROVIDER_LABEL, LLM_MODEL and "
            "LLM_BASE_URL before invoking an LLM target."
        )

    target_id = configuration.llm_target_id
    provider_label = configuration.llm_provider_label
    model = configuration.llm_model
    base_url = configuration.llm_base_url
    assert target_id is not None
    assert provider_label is not None
    assert model is not None
    assert base_url is not None

    target = LLMTarget(
        profile=target_id,
        provider=provider_label,
        model=model,
    )
    protocol_source = (
        "Gemini GenerateContent REST protocol"
        if configuration.llm_adapter_kind == "gemini"
        else "openai-compatible chat completions protocol"
    )
    capabilities = CapabilitySet(
        target=target,
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
                source=protocol_source,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport(
                    configuration.llm_structured_generation
                ),
                source=_capability_source(
                    configuration.llm_structured_generation,
                    native="explicit runtime configuration",
                    emulated="local Pydantic validation over JSON text",
                ),
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport(configuration.llm_streaming),
                source=_capability_source(
                    configuration.llm_streaming,
                    native="explicit runtime configuration",
                    emulated="explicit runtime configuration",
                ),
            ),
        ),
    )
    if configuration.llm_adapter_kind == "openrouter":
        upstream_provider = configuration.llm_openrouter_provider
        if upstream_provider is None or not upstream_provider.strip():
            raise LLMRuntimeConfigurationError(
                "Configure LLM_OPENROUTER_PROVIDER with one exact provider slug."
            )
        if provider_label.strip().casefold() != "openrouter":
            raise LLMRuntimeConfigurationError(
                "LLM_PROVIDER_LABEL must be OpenRouter for the OpenRouter adapter."
            )
        try:
            adapter: LLMGateway = OpenRouterAdapter(
                base_url=base_url,
                capability_set=capabilities,
                upstream_provider=upstream_provider,
                api_key=configuration.llm_api_key,
                reasoning_effort=configuration.llm_reasoning_effort,
            )
        except ValueError as exc:
            raise LLMRuntimeConfigurationError(str(exc)) from None
    elif configuration.llm_adapter_kind == "groq":
        try:
            adapter = GroqAdapter(
                base_url=base_url,
                capability_set=capabilities,
                api_key=configuration.llm_api_key,
                reasoning_effort=configuration.llm_reasoning_effort,
            )
        except ValueError as exc:
            raise LLMRuntimeConfigurationError(str(exc)) from None
    elif configuration.llm_adapter_kind == "gemini":
        if not configuration.llm_campaign_data_allowed:
            raise LLMRuntimeConfigurationError(
                "Gemini is blocked from the campaign runtime until "
                "LLM_CAMPAIGN_DATA_ALLOWED=true is explicitly set after reviewing "
                "the target project's data policy. Use the isolated evaluator for "
                "synthetic-only profiles."
            )
        if provider_label.strip().casefold() != GEMINI_PROVIDER_LABEL.casefold():
            raise LLMRuntimeConfigurationError(
                f"LLM_PROVIDER_LABEL must be {GEMINI_PROVIDER_LABEL} for the Gemini adapter."
            )
        if base_url.strip().rstrip("/") != GEMINI_OFFICIAL_BASE_URL:
            raise LLMRuntimeConfigurationError(
                "LLM_BASE_URL must be the exact official Gemini v1beta endpoint."
            )
        try:
            adapter = GeminiAdapter(
                base_url=base_url,
                capability_set=capabilities,
                api_key=configuration.llm_api_key,
                reasoning_effort=configuration.llm_reasoning_effort,
            )
        except ValueError as exc:
            raise LLMRuntimeConfigurationError(str(exc)) from None
    elif configuration.llm_adapter_kind == "nvidia":
        if not configuration.llm_campaign_data_allowed:
            raise LLMRuntimeConfigurationError(
                "NVIDIA NIM is blocked from the campaign runtime until "
                "LLM_CAMPAIGN_DATA_ALLOWED=true is explicitly set after reviewing "
                "the target project's data policy. The hosted trial profile is "
                "synthetic-only and must use the isolated evaluator."
            )
        if provider_label.strip().casefold() != NVIDIA_NIM_PROVIDER_LABEL.casefold():
            raise LLMRuntimeConfigurationError(
                f"LLM_PROVIDER_LABEL must be {NVIDIA_NIM_PROVIDER_LABEL} for the "
                "NVIDIA NIM adapter."
            )
        if base_url.strip().rstrip("/") != NVIDIA_NIM_OFFICIAL_BASE_URL:
            raise LLMRuntimeConfigurationError(
                "LLM_BASE_URL must be the exact official NVIDIA hosted NIM endpoint."
            )
        if model.strip() != NVIDIA_NIM_MODEL_ID:
            raise LLMRuntimeConfigurationError(
                f"LLM_MODEL must be the fixed evaluated model {NVIDIA_NIM_MODEL_ID}."
            )
        try:
            adapter = NvidiaNimAdapter(
                base_url=base_url,
                capability_set=capabilities,
                api_key=configuration.llm_api_key,
                reasoning_effort=configuration.llm_reasoning_effort,
            )
        except ValueError as exc:
            raise LLMRuntimeConfigurationError(str(exc)) from None
    else:
        adapter = OpenAICompatibleAdapter(
            base_url=base_url,
            capability_set=capabilities,
            api_key=configuration.llm_api_key,
            reasoning_effort=configuration.llm_reasoning_effort,
        )
    return LLMRuntime(target=target, gateway=adapter)


def _capability_source(
    mode: str,
    *,
    native: str,
    emulated: str,
) -> str | None:
    if mode == "native":
        return native
    if mode == "emulated":
        return emulated
    if mode == "unsupported":
        return "explicit runtime configuration"
    return None


_default_runtime: LLMRuntime | None = None
_runtime_guard = threading.Lock()


def get_llm_runtime() -> LLMRuntime:
    global _default_runtime
    if _default_runtime is None:
        with _runtime_guard:
            if _default_runtime is None:
                _default_runtime = build_llm_runtime(settings)
    return _default_runtime


def reset_llm_runtime_for_tests() -> None:
    """Clear only the composition cache; this performs no external action."""

    global _default_runtime
    with _runtime_guard:
        _default_runtime = None
