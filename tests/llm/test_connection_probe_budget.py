"""The tiny connection check must not delegate output budgeting to a provider."""

import asyncio
import json

import httpx
import pytest

from api.llm.adapters.groq import GROQ_GPT_OSS_MODEL_ID, GROQ_QWEN_MODEL_ID
from api.llm.contract import (
    ConnectionTestRequest,
    GenerationParameters,
    SYNTHETIC_PROBE_EXPECTED,
    SYNTHETIC_PROBE_PROMPT,
)
from .test_groq_adapter import _adapter, _deadline, _request, _success_payload, _target


@pytest.mark.parametrize("model", [GROQ_QWEN_MODEL_ID, GROQ_GPT_OSS_MODEL_ID])
@pytest.mark.parametrize("response_kind", ["success", "rate_limited", "truncated"])
def test_connection_probe_always_transmits_128_without_retry_or_route_change(model, response_kind):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        if response_kind == "rate_limited":
            return httpx.Response(429, json={"error": {
                "code": "rate_limit_exceeded", "type": "tokens",
            }}, request=request)
        response = _success_payload(SYNTHETIC_PROBE_EXPECTED, model=model)
        if response_kind == "truncated":
            response["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=response, request=request)

    target = _target(model=model)
    result = asyncio.run(_adapter(handler, target=target).test_connection(
        ConnectionTestRequest(target=target, deadline=_deadline()),
    ))
    assert len(captured) == 1
    payload = captured[0]
    assert payload["max_completion_tokens"] == 128
    assert "max_tokens" not in payload
    assert payload["model"] == model
    assert payload["stream"] is False
    assert payload["messages"] == [{"role": "user", "content": SYNTHETIC_PROBE_PROMPT}]
    assert payload["reasoning_effort"] == ("none" if model == GROQ_QWEN_MODEL_ID else "low")
    assert "response_format" not in payload
    assert "temperature" not in payload
    assert result.success is (response_kind == "success")
    if response_kind != "success":
        assert result.error.code == (
            "http_429" if response_kind == "rate_limited" else "generation_truncated"
        )


@pytest.mark.parametrize("ceiling", [None, 64, 768])
def test_connection_budget_does_not_clamp_normal_generation_parameters(ceiling):
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=_success_payload(), request=request)

    request = _request(parameters=GenerationParameters(max_output_tokens=ceiling))
    asyncio.run(_adapter(handler).generate_text(request))
    assert len(captured) == 1
    if ceiling is None:
        assert "max_completion_tokens" not in captured[0]
    else:
        assert captured[0]["max_completion_tokens"] == ceiling
