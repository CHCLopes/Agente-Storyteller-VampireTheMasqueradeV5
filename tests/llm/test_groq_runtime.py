"""Explicit Groq composition; all credentials and HTTP responses are synthetic."""
import asyncio
from datetime import timedelta
import json

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from api.core.config import Settings
from api.llm.adapters.groq import (
    GROQ_GPT_OSS_MODEL_ID, GROQ_OFFICIAL_BASE_URL, GROQ_PROVIDER_LABEL,
    GROQ_QWEN_MODEL_ID, GroqAdapter,
)
from api.llm.contract import (
    CAPABILITY_STREAMING, CAPABILITY_STRUCTURED_GENERATION, CapabilitySupport,
    ErrorCategory, GenerationParameters, LLMInvocationError, LLMMessage,
    MessageRole, ProvenanceSource, StructuredGenerationRequest, utc_now,
)
from api.llm.runtime import LLMRuntimeConfigurationError, build_llm_runtime


SECRET = "synthetic-groq-runtime-secret"


def _settings(**overrides):
    values = dict(
        llm_target_id="explicit-groq-runtime-test",
        llm_adapter_kind="groq", llm_provider_label=GROQ_PROVIDER_LABEL,
        llm_base_url=GROQ_OFFICIAL_BASE_URL, llm_model=GROQ_QWEN_MODEL_ID,
        llm_api_key=SecretStr(SECRET), llm_reasoning_effort="none",
        llm_structured_generation="native", llm_streaming="native",
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("model,effort", [
    (GROQ_QWEN_MODEL_ID, "none"), (GROQ_GPT_OSS_MODEL_ID, "low"),
])
def test_explicit_groq_target_uses_existing_adapter_without_product_approval(model, effort):
    config = _settings(llm_model=model, llm_reasoning_effort=effort)
    assert config.llm_is_configured is True
    assert config.llm_campaign_data_allowed is False
    runtime = build_llm_runtime(config)
    assert type(runtime.gateway) is GroqAdapter
    assert runtime.target.profile == "explicit-groq-runtime-test"
    assert runtime.target.model == model and runtime.target.provider == GROQ_PROVIDER_LABEL
    assert runtime.gateway._reasoning_effort == effort
    assert runtime.gateway.capabilities(runtime.target).support_for(CAPABILITY_STRUCTURED_GENERATION) is CapabilitySupport.NATIVE
    assert SECRET not in repr(config)


@pytest.mark.parametrize("overrides", [
    {"llm_api_key": None},
    {"llm_api_key": SecretStr(" ")},
    {"llm_provider_label": "OpenRouter"},
    {"llm_base_url": "https://proxy.invalid/openai/v1"},
    {"llm_base_url": "http://api.groq.com/openai/v1"},
    {"llm_model": "qwen/latest"},
    {"llm_model": "qwen/qwen3-32b"},
    {"llm_reasoning_effort": None},
    {"llm_reasoning_effort": "low"},
    {"llm_reasoning_effort": "medium"},
    {"llm_model": GROQ_GPT_OSS_MODEL_ID, "llm_reasoning_effort": "none"},
])
def test_groq_configuration_and_composition_reject_the_same_invalid_target(overrides):
    config = _settings(**overrides)
    assert config.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError) as caught:
        build_llm_runtime(config)
    assert SECRET not in str(caught.value)


def test_groq_does_not_infer_capabilities_or_replace_default_adapter():
    config = _settings(llm_structured_generation="unknown", llm_streaming="unknown")
    runtime = build_llm_runtime(config)
    for capability in (CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_STREAMING):
        assert runtime.gateway.capabilities(runtime.target).support_for(capability) is CapabilitySupport.UNKNOWN
    assert Settings(_env_file=None).llm_adapter_kind == "openai-compatible"
    assert Settings(_env_file=None).llm_target_id is None


def test_runtime_reads_only_explicit_llm_key_not_evaluator_alias(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-evaluator-key-not-a-runtime-alias")
    values = dict(
        LLM_TARGET_ID="env-explicit-groq", LLM_PROVIDER_LABEL=GROQ_PROVIDER_LABEL,
        LLM_MODEL=GROQ_QWEN_MODEL_ID, LLM_BASE_URL=GROQ_OFFICIAL_BASE_URL,
        LLM_ADAPTER_KIND="groq", LLM_REASONING_EFFORT="none",
    )
    config = Settings(_env_file=None, **values)
    assert config.llm_api_key is None and config.llm_is_configured is False
    with pytest.raises(LLMRuntimeConfigurationError):
        build_llm_runtime(config)
    monkeypatch.setenv("LLM_API_KEY", SECRET)
    explicit = Settings(_env_file=None, **values)
    assert explicit.llm_is_configured is True
    assert explicit.llm_api_key.get_secret_value() == SECRET
    assert SECRET not in repr(explicit)


class _Reply(BaseModel):
    answer: str
    tags: tuple[str, ...] = ()


@pytest.mark.parametrize("status", [200, 429])
def test_composed_groq_uses_strict_provider_payload_and_never_retries(status):
    runtime = build_llm_runtime(_settings())
    requests = []
    def handler(request):
        requests.append(request)
        assert str(request.url) == GROQ_OFFICIAL_BASE_URL + "/chat/completions"
        assert request.headers["Authorization"] == "Bearer " + SECRET
        payload = json.loads(request.content)
        assert payload["model"] == GROQ_QWEN_MODEL_ID
        assert payload["reasoning_effort"] == "none"
        assert payload["max_completion_tokens"] == 768 and "max_tokens" not in payload
        assert payload["temperature"] == .65 and payload["stream"] is False
        assert "stream_options" not in payload and "include_reasoning" not in payload
        schema = payload["response_format"]["json_schema"]
        assert schema["strict"] is True
        assert set(schema["schema"]["required"]) == {"answer", "tags"}
        assert schema["schema"]["additionalProperties"] is False
        if status == 429:
            return httpx.Response(429, json={"error": {
                "message": SECRET + " provider prose", "code": "rate_limit_exceeded", "type": "tokens",
            }})
        return httpx.Response(200, json={
            "model": GROQ_QWEN_MODEL_ID,
            "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"ok","tags":[]}'}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 5, "total_tokens": 13},
        })
    runtime.gateway._transport = httpx.MockTransport(handler)
    request = StructuredGenerationRequest(
        target=runtime.target, operation="runtime.synthetic-check",
        messages=(LLMMessage(role=MessageRole.USER, content="Dados sintéticos."),),
        response_model=_Reply, deadline=utc_now()+timedelta(seconds=5),
        parameters=GenerationParameters(max_output_tokens=768, temperature=.65),
    )
    if status == 200:
        response = asyncio.run(runtime.gateway.generate_structured(request))
        assert response.value.answer == "ok" and response.value.tags == ()
        assert response.evidence.provenance.effective_provider.value == GROQ_PROVIDER_LABEL
        assert response.evidence.provenance.effective_provider.source is ProvenanceSource.OBSERVED
        assert response.evidence.provenance.effective_model.value == GROQ_QWEN_MODEL_ID
        assert response.evidence.provenance.adapter.name == "groq-chat-completions"
    else:
        with pytest.raises(LLMInvocationError) as caught:
            asyncio.run(runtime.gateway.generate_structured(request))
        assert caught.value.error.category is ErrorCategory.RATE_LIMITED
        assert caught.value.error.status_code == 429
        assert SECRET not in caught.value.error.model_dump_json()
    assert len(requests) == 1
