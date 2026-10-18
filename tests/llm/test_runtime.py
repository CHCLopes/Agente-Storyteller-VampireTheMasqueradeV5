import os

import pytest
from pydantic import SecretStr

import api.llm.runtime as runtime_module
from api.core import config as config_module
from api.core.config import DOTENV_DISABLE_ENV_VAR, Settings
from api.llm.adapters import GeminiAdapter, NvidiaNimAdapter, OpenRouterAdapter
from api.llm.adapters.gemini import (
    GEMINI_OFFICIAL_BASE_URL,
    GEMINI_PROVIDER_LABEL,
)
from api.llm.adapters.nvidia import (
    NVIDIA_NIM_MODEL_ID,
    NVIDIA_NIM_OFFICIAL_BASE_URL,
    NVIDIA_NIM_PROVIDER_LABEL,
)
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilitySupport,
)
from api.llm.runtime import LLMRuntimeConfigurationError, build_llm_runtime


def _settings(**overrides) -> Settings:
    values = {
        "llm_target_id": "explicit-profile",
        "llm_provider_label": "explicit-provider",
        "llm_model": "explicit-model",
        "llm_base_url": "https://llm.invalid/v1",
        "llm_api_key": SecretStr("synthetic-secret"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_pytest_process_disables_dotenv_before_application_import() -> None:
    assert os.environ[DOTENV_DISABLE_ENV_VAR] == "1"
    assert Settings.model_config["env_file"] is None


def test_dotenv_switch_preserves_the_normal_default(monkeypatch) -> None:
    monkeypatch.delenv(DOTENV_DISABLE_ENV_VAR, raising=False)
    assert config_module._configured_dotenv_file() == ".env"

    monkeypatch.setenv(DOTENV_DISABLE_ENV_VAR, "true")
    assert config_module._configured_dotenv_file() is None


@pytest.mark.parametrize(
    ("field", "missing_value"),
    [
        ("llm_target_id", None),
        ("llm_provider_label", " "),
        ("llm_model", None),
        ("llm_base_url", ""),
    ],
)
def test_runtime_rejects_each_missing_target_identity_component(
    field: str, missing_value: str | None
) -> None:
    configuration = _settings(**{field: missing_value})

    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError) as caught:
        build_llm_runtime(configuration)

    assert "LLM_TARGET_ID" in str(caught.value)
    assert "LLM_PROVIDER_LABEL" in str(caught.value)
    assert "synthetic-secret" not in str(caught.value)


def test_runtime_preserves_the_exact_explicit_target_without_defaults() -> None:
    runtime = build_llm_runtime(_settings())

    assert runtime.target.profile == "explicit-profile"
    assert runtime.target.provider == "explicit-provider"
    assert runtime.target.model == "explicit-model"
    assert runtime.gateway.capabilities(runtime.target).target == runtime.target


def test_capabilities_default_to_unknown_until_explicitly_declared() -> None:
    configuration = _settings()
    assert configuration.llm_structured_generation == "unknown"
    assert configuration.llm_streaming == "unknown"
    assert configuration.llm_reasoning_effort is None
    assert configuration.llm_campaign_data_allowed is False
    assert configuration.llm_h0_timeout_seconds == 15.0
    assert configuration.llm_h1_timeout_seconds == 30.0
    assert configuration.llm_h4_timeout_seconds == 20.0
    assert configuration.llm_h6_max_output_tokens == 96
    assert configuration.llm_h0_enabled is False
    assert configuration.llm_h1_enabled is False
    assert configuration.llm_h4_action_enrichment_enabled is False
    assert configuration.narrator_context_token_budget == 192

    runtime = build_llm_runtime(configuration)
    capabilities = runtime.gateway.capabilities(runtime.target)

    assert (
        capabilities.support_for(CAPABILITY_TEXT_GENERATION)
        is CapabilitySupport.NATIVE
    )
    assert (
        capabilities.support_for(CAPABILITY_STRUCTURED_GENERATION)
        is CapabilitySupport.UNKNOWN
    )
    assert capabilities.support_for(CAPABILITY_STREAMING) is CapabilitySupport.UNKNOWN
    structured = next(
        descriptor
        for descriptor in capabilities.descriptors
        if descriptor.name == CAPABILITY_STRUCTURED_GENERATION
    )
    streaming = next(
        descriptor
        for descriptor in capabilities.descriptors
        if descriptor.name == CAPABILITY_STREAMING
    )
    assert structured.source is None
    assert streaming.source is None


def test_explicit_capability_declarations_keep_native_and_emulated_distinct() -> None:
    runtime = build_llm_runtime(
        _settings(
            llm_structured_generation="emulated",
            llm_streaming="native",
        )
    )
    capabilities = runtime.gateway.capabilities(runtime.target)

    assert (
        capabilities.support_for(CAPABILITY_STRUCTURED_GENERATION)
        is CapabilitySupport.EMULATED
    )
    assert capabilities.support_for(CAPABILITY_STREAMING) is CapabilitySupport.NATIVE


def test_settings_do_not_build_http_headers_or_protocol_endpoints() -> None:
    configuration = _settings()

    assert not hasattr(configuration, "llm_headers")
    assert not hasattr(configuration, "llm_endpoint")
    assert "synthetic-secret" not in repr(configuration)


def test_explicit_reasoning_effort_is_bound_to_the_adapter() -> None:
    runtime = build_llm_runtime(_settings(llm_reasoning_effort="none"))

    assert runtime.gateway._reasoning_effort == "none"


def test_openrouter_runtime_requires_and_preserves_one_pinned_upstream() -> None:
    runtime = build_llm_runtime(
        _settings(
            llm_adapter_kind="openrouter",
            llm_provider_label="OpenRouter",
            llm_model="z-ai/glm-5.2:free",
            llm_base_url="https://openrouter.ai/api/v1",
            llm_openrouter_provider="decart",
            llm_structured_generation="native",
            llm_streaming="native",
        )
    )

    assert isinstance(runtime.gateway, OpenRouterAdapter)
    assert runtime.target.provider == "OpenRouter"
    assert runtime.target.model == "z-ai/glm-5.2:free"
    assert runtime.gateway._upstream_provider == "decart"


@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_openrouter_provider": None},
        {"llm_provider_label": "misleading-provider", "llm_openrouter_provider": "decart"},
        {"llm_api_key": None, "llm_openrouter_provider": "decart"},
        {
            "llm_base_url": "https://proxy.invalid/v1",
            "llm_openrouter_provider": "decart",
        },
    ],
)
def test_openrouter_runtime_rejects_incomplete_or_misleading_profiles(
    overrides: dict,
) -> None:
    values = {
        "llm_adapter_kind": "openrouter",
        "llm_provider_label": "OpenRouter",
        "llm_model": "z-ai/glm-5.2:free",
        "llm_base_url": "https://openrouter.ai/api/v1",
        "llm_openrouter_provider": "decart",
    }
    values.update(overrides)

    with pytest.raises(LLMRuntimeConfigurationError):
        build_llm_runtime(_settings(**values))


def test_gemini_runtime_requires_one_fixed_official_target() -> None:
    configuration = _settings(
        llm_adapter_kind="gemini",
        llm_provider_label=GEMINI_PROVIDER_LABEL,
        llm_model="gemini-3.7-flash",
        llm_base_url=GEMINI_OFFICIAL_BASE_URL,
        llm_structured_generation="native",
        llm_streaming="native",
        llm_reasoning_effort="low",
        llm_campaign_data_allowed=True,
    )

    assert configuration.llm_is_configured is True
    runtime = build_llm_runtime(configuration)

    assert isinstance(runtime.gateway, GeminiAdapter)
    assert runtime.target.provider == GEMINI_PROVIDER_LABEL
    assert runtime.target.model == "gemini-3.7-flash"
    assert runtime.gateway._reasoning_effort == "low"
    assert (
        runtime.gateway.capabilities(runtime.target).support_for(
            CAPABILITY_STRUCTURED_GENERATION
        )
        is CapabilitySupport.NATIVE
    )


def test_gemini_runtime_rejects_none_reasoning_effort() -> None:
    with pytest.raises(LLMRuntimeConfigurationError, match="reasoning effort"):
        build_llm_runtime(
            _settings(
                llm_adapter_kind="gemini",
                llm_provider_label=GEMINI_PROVIDER_LABEL,
                llm_model="gemini-3.7-flash",
                llm_base_url=GEMINI_OFFICIAL_BASE_URL,
                llm_structured_generation="native",
                llm_streaming="native",
                llm_reasoning_effort="none",
                llm_campaign_data_allowed=True,
            )
        )


def test_gemini_runtime_blocks_campaign_data_without_explicit_opt_in() -> None:
    configuration = _settings(
        llm_adapter_kind="gemini",
        llm_provider_label=GEMINI_PROVIDER_LABEL,
        llm_model="gemini-3.7-flash",
        llm_base_url=GEMINI_OFFICIAL_BASE_URL,
        llm_structured_generation="native",
        llm_streaming="native",
        llm_reasoning_effort="low",
        llm_campaign_data_allowed=False,
    )

    assert configuration.llm_is_configured is False
    with pytest.raises(
        LLMRuntimeConfigurationError,
        match="LLM_CAMPAIGN_DATA_ALLOWED",
    ):
        build_llm_runtime(configuration)

@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_api_key": None},
        {"llm_provider_label": "Gemini"},
        {"llm_base_url": "https://proxy.invalid/v1beta"},
        {"llm_model": "gemini-flash-latest"},
        {"llm_model": "gemini-3.7-flash-preview"},
    ],
)
def test_gemini_runtime_rejects_incomplete_mutable_or_misleading_profiles(
    overrides: dict,
) -> None:
    values = {
        "llm_adapter_kind": "gemini",
        "llm_provider_label": GEMINI_PROVIDER_LABEL,
        "llm_model": "gemini-3.7-flash",
        "llm_base_url": GEMINI_OFFICIAL_BASE_URL,
        "llm_campaign_data_allowed": True,
    }
    values.update(overrides)
    configuration = _settings(**values)

    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError):
        build_llm_runtime(configuration)


def test_nvidia_runtime_requires_one_fixed_official_target() -> None:
    configuration = _settings(
        llm_adapter_kind="nvidia",
        llm_provider_label=NVIDIA_NIM_PROVIDER_LABEL,
        llm_model=NVIDIA_NIM_MODEL_ID,
        llm_base_url=NVIDIA_NIM_OFFICIAL_BASE_URL,
        llm_structured_generation="emulated",
        llm_streaming="native",
        llm_campaign_data_allowed=True,
    )

    assert configuration.llm_is_configured is True
    runtime = build_llm_runtime(configuration)

    assert isinstance(runtime.gateway, NvidiaNimAdapter)
    assert runtime.target.provider == NVIDIA_NIM_PROVIDER_LABEL
    assert runtime.target.model == NVIDIA_NIM_MODEL_ID
    assert (
        runtime.gateway.capabilities(runtime.target).support_for(
            CAPABILITY_STRUCTURED_GENERATION
        )
        is CapabilitySupport.EMULATED
    )


def test_nvidia_runtime_blocks_campaign_data_without_explicit_opt_in() -> None:
    configuration = _settings(
        llm_adapter_kind="nvidia",
        llm_provider_label=NVIDIA_NIM_PROVIDER_LABEL,
        llm_model=NVIDIA_NIM_MODEL_ID,
        llm_base_url=NVIDIA_NIM_OFFICIAL_BASE_URL,
        llm_structured_generation="emulated",
        llm_streaming="native",
        llm_campaign_data_allowed=False,
    )

    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError, match="synthetic-only"):
        build_llm_runtime(configuration)


@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_api_key": None},
        {"llm_provider_label": "NVIDIA"},
        {"llm_base_url": "https://proxy.invalid/v1"},
        {"llm_model": "nvidia/nemotron-latest"},
    ],
)
def test_nvidia_runtime_rejects_incomplete_or_misleading_profiles(
    overrides: dict,
) -> None:
    values = {
        "llm_adapter_kind": "nvidia",
        "llm_provider_label": NVIDIA_NIM_PROVIDER_LABEL,
        "llm_model": NVIDIA_NIM_MODEL_ID,
        "llm_base_url": NVIDIA_NIM_OFFICIAL_BASE_URL,
        "llm_campaign_data_allowed": True,
    }
    values.update(overrides)
    configuration = _settings(**values)

    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError):
        build_llm_runtime(configuration)


def test_nvidia_runtime_does_not_reuse_evaluator_secret_name(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "evaluator-secret-must-not-leak")
    configuration = Settings(
        _env_file=None,
        LLM_TARGET_ID="nvidia-explicit-profile",
        LLM_PROVIDER_LABEL=NVIDIA_NIM_PROVIDER_LABEL,
        LLM_MODEL=NVIDIA_NIM_MODEL_ID,
        LLM_BASE_URL=NVIDIA_NIM_OFFICIAL_BASE_URL,
        LLM_ADAPTER_KIND="nvidia",
        LLM_STRUCTURED_GENERATION="emulated",
        LLM_STREAMING="native",
        LLM_CAMPAIGN_DATA_ALLOWED="true",
    )

    assert configuration.llm_api_key is None
    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError) as caught:
        build_llm_runtime(configuration)
    assert "evaluator-secret-must-not-leak" not in str(caught.value)


def test_stage_timeouts_accept_explicit_environment_values() -> None:
    configuration = Settings(
        _env_file=None,
        LLM_H0_TIMEOUT_SECONDS="45.5",
        LLM_H1_TIMEOUT_SECONDS="70",
        LLM_H4_TIMEOUT_SECONDS="55.25",
    )

    assert configuration.llm_h0_timeout_seconds == 45.5
    assert configuration.llm_h1_timeout_seconds == 70.0
    assert configuration.llm_h4_timeout_seconds == 55.25


def test_narrator_budgets_accept_explicit_environment_values() -> None:
    configuration = Settings(
        _env_file=None,
        LLM_H6_MAX_OUTPUT_TOKENS="80",
        NARRATOR_CONTEXT_TOKEN_BUDGET="160",
    )

    assert configuration.llm_h6_max_output_tokens == 80
    assert configuration.narrator_context_token_budget == 160


def test_optional_llm_stages_accept_explicit_environment_switches() -> None:
    configuration = Settings(
        _env_file=None,
        LLM_H0_ENABLED="false",
        LLM_H1_ENABLED="false",
        LLM_H4_ACTION_ENRICHMENT_ENABLED="false",
    )

    assert configuration.llm_h0_enabled is False
    assert configuration.llm_h1_enabled is False
    assert configuration.llm_h4_action_enrichment_enabled is False


def test_legacy_gemini_secret_is_never_reused_for_an_explicit_target(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "legacy-secret-must-not-leak")
    configuration = Settings(
        _env_file=None,
        LLM_TARGET_ID="local-profile",
        LLM_PROVIDER_LABEL="openai-compatible",
        LLM_MODEL="local-model",
        LLM_BASE_URL="http://127.0.0.1:1234/v1",
    )

    assert configuration.llm_is_configured is True
    assert configuration.llm_api_key is None
    runtime = build_llm_runtime(configuration)
    assert runtime.gateway._api_key is None


def test_gemini_runtime_does_not_implicitly_reuse_legacy_secret_name(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "legacy-secret-must-not-leak")
    configuration = Settings(
        _env_file=None,
        LLM_TARGET_ID="gemini-explicit-profile",
        LLM_PROVIDER_LABEL=GEMINI_PROVIDER_LABEL,
        LLM_MODEL="gemini-3.7-flash",
        LLM_BASE_URL=GEMINI_OFFICIAL_BASE_URL,
        LLM_ADAPTER_KIND="gemini",
        LLM_STRUCTURED_GENERATION="native",
        LLM_STREAMING="native",
    )

    assert configuration.llm_api_key is None
    assert configuration.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError) as caught:
        build_llm_runtime(configuration)
    assert "legacy-secret-must-not-leak" not in str(caught.value)


def test_default_runtime_is_cached_without_reselecting_a_target(monkeypatch) -> None:
    configuration = _settings()
    runtime_module.reset_llm_runtime_for_tests()
    monkeypatch.setattr(runtime_module, "settings", configuration)

    try:
        first = runtime_module.get_llm_runtime()
        second = runtime_module.get_llm_runtime()
    finally:
        runtime_module.reset_llm_runtime_for_tests()

    assert first is second
    assert first.target.profile == "explicit-profile"
    assert first.target.provider == "explicit-provider"
    assert first.target.model == "explicit-model"
