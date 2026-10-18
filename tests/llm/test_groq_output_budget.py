"""A smaller Groq completion budget is explicit and never admits truncation."""

import asyncio
import json

import httpx
import pytest

from api.llm.adapters.groq import (
    GROQ_GPT_OSS_MODEL_ID,
    GROQ_OFFICIAL_BASE_URL,
    GROQ_QWEN_MODEL_ID,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement,
    ErrorCategory,
    GenerationParameters,
    LLMInvocationError,
    LLMMessage,
    MessageRole,
    StructuredGenerationRequest,
)

from .test_groq_adapter import _Route, _SECRET, _adapter, _request, _success_payload, _target


_MESSAGES = (
    LLMMessage(role=MessageRole.SYSTEM, content="Return the synthetic route schema."),
    LLMMessage(role=MessageRole.USER, content="Preserve this synthetic scene context."),
)
_VALID_JSON = json.dumps(
    {
        "route": "synthetic-route-do-not-echo-on-error",
        "detail": {"note": "synthetic scene detail", "visible": True},
        "tags": [],
    }
)


def _structured_request(model: str) -> StructuredGenerationRequest:
    values = _request(
        model=model,
        messages=_MESSAGES,
        parameters=GenerationParameters(temperature=0.65, max_output_tokens=768),
    ).model_dump()
    values.pop("required_capabilities")
    return StructuredGenerationRequest(
        **values,
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION),
        ),
    )


@pytest.mark.parametrize("model", [GROQ_QWEN_MODEL_ID, GROQ_GPT_OSS_MODEL_ID])
def test_768_budget_reaches_wire_without_changing_target_messages_or_schema(model: str) -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{GROQ_OFFICIAL_BASE_URL}/chat/completions"
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=_success_payload(_VALID_JSON, model=model), request=request)

    request = _structured_request(model)
    result = asyncio.run(_adapter(handler, target=_target(model=model)).generate_structured(request))

    assert len(captured) == 1
    payload = captured[0]
    assert payload["model"] == model
    assert payload["max_completion_tokens"] == 768
    assert "max_tokens" not in payload
    assert payload["temperature"] == 0.65
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": message.role.value, "content": message.content}
        for message in _MESSAGES
    ]
    assert payload["response_format"]["type"] == "json_schema"
    envelope = payload["response_format"]["json_schema"]
    assert envelope["name"] == "_Route"
    assert envelope["strict"] is True
    assert set(envelope["schema"]["properties"]) == {"route", "detail", "tags"}
    assert set(envelope["schema"]["required"]) == {"route", "detail", "tags"}
    assert envelope["schema"]["additionalProperties"] is False
    assert payload["reasoning_effort"] == (
        "none" if model == GROQ_QWEN_MODEL_ID else "low"
    )
    if model == GROQ_GPT_OSS_MODEL_ID:
        assert payload["include_reasoning"] is False
    assert result.value == _Route.model_validate_json(_VALID_JSON)
    assert result.evidence.provenance.requested_target == request.target
    assert result.evidence.provenance.effective_model.value == model


@pytest.mark.parametrize("model", [GROQ_QWEN_MODEL_ID, GROQ_GPT_OSS_MODEL_ID])
def test_length_finish_rejects_even_complete_valid_json_without_retry_or_repair(model: str) -> None:
    captured: list[dict] = []
    # A parseable, model-valid answer still cannot override the provider's
    # declaration that the requested generation was truncated.
    _Route.model_validate_json(_VALID_JSON)

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        response = _success_payload(_VALID_JSON, model=model)
        response["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=response, request=request)

    request = _structured_request(model)
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler, target=_target(model=model)).generate_structured(request))

    assert len(captured) == 1
    assert captured[0]["max_completion_tokens"] == 768
    error = caught.value.error
    assert error.category is ErrorCategory.MALFORMED_RESPONSE
    assert error.code == "generation_truncated"
    assert error.target == request.target
    assert error.partial_output is False
    serialized = error.model_dump_json()
    assert _VALID_JSON not in serialized
    assert "synthetic-route-do-not-echo-on-error" not in serialized
    assert _SECRET not in serialized
