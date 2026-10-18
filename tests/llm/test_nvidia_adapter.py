import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from api.llm.adapters import NvidiaNimAdapter
from api.llm.adapters.nvidia import (
    NVIDIA_NIM_MODEL_ID,
    NVIDIA_NIM_OFFICIAL_BASE_URL,
    NVIDIA_NIM_PROVIDER_LABEL,
)
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    GenerationParameters,
    GenerationRequest,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    ProvenanceSource,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    validate_stream_events,
)


_SECRET = "synthetic-nvidia-secret-never-log"


class _Route(BaseModel):
    route: str


class _SSEStream(httpx.AsyncByteStream):
    def __init__(self, rows: list[str]) -> None:
        self._content = "".join(f"data: {row}\n\n" for row in rows).encode()

    async def __aiter__(self):
        yield self._content

    async def aclose(self) -> None:
        return None


def _target(
    *,
    provider: str = NVIDIA_NIM_PROVIDER_LABEL,
    model: str = NVIDIA_NIM_MODEL_ID,
) -> LLMTarget:
    return LLMTarget(profile="nvidia-trial-synthetic", provider=provider, model=model)


def _capabilities(
    target: LLMTarget | None = None,
    *,
    structured: CapabilitySupport = CapabilitySupport.EMULATED,
) -> CapabilitySet:
    return CapabilitySet(
        target=target or _target(),
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=structured,
                source="NVIDIA JSON mode with local Pydantic validation",
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )


def _adapter(handler, *, target: LLMTarget | None = None) -> NvidiaNimAdapter:
    selected = target or _target()
    return NvidiaNimAdapter(
        base_url=NVIDIA_NIM_OFFICIAL_BASE_URL,
        capability_set=_capabilities(selected),
        api_key=SecretStr(_SECRET),
        transport=httpx.MockTransport(handler),
    )


def _deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=5)


def _request(**overrides) -> GenerationRequest:
    values = {
        "operation": "nvidia-text",
        "target": _target(),
        "messages": (LLMMessage(role=MessageRole.USER, content="entrada sintética"),),
        "deadline": _deadline(),
    }
    values.update(overrides)
    return GenerationRequest(**values)


def _success_payload(text: str = "resultado", *, include_model: bool = True) -> dict:
    payload = {
        "id": "synthetic-nvidia-response",
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
    }
    if include_model:
        payload["model"] = NVIDIA_NIM_MODEL_ID
    return payload


@pytest.mark.parametrize(
    ("base_url", "provider", "model", "secret"),
    [
        ("http://integrate.api.nvidia.com/v1", NVIDIA_NIM_PROVIDER_LABEL, NVIDIA_NIM_MODEL_ID, _SECRET),
        ("https://integrate.api.nvidia.com.evil.test/v1", NVIDIA_NIM_PROVIDER_LABEL, NVIDIA_NIM_MODEL_ID, _SECRET),
        (NVIDIA_NIM_OFFICIAL_BASE_URL, "misleading-provider", NVIDIA_NIM_MODEL_ID, _SECRET),
        (NVIDIA_NIM_OFFICIAL_BASE_URL, NVIDIA_NIM_PROVIDER_LABEL, "nvidia/nemotron-latest", _SECRET),
        (NVIDIA_NIM_OFFICIAL_BASE_URL, NVIDIA_NIM_PROVIDER_LABEL, NVIDIA_NIM_MODEL_ID, " "),
    ],
)
def test_constructor_rejects_unbound_or_incomplete_target(
    base_url: str, provider: str, model: str, secret: str
) -> None:
    target = _target(provider=provider, model=model)
    with pytest.raises(ValueError):
        NvidiaNimAdapter(
            base_url=base_url,
            capability_set=_capabilities(target),
            api_key=SecretStr(secret),
        )


def test_constructor_rejects_unimplemented_reasoning_levels() -> None:
    with pytest.raises(ValueError, match="reasoning effort"):
        NvidiaNimAdapter(
            base_url=NVIDIA_NIM_OFFICIAL_BASE_URL,
            capability_set=_capabilities(),
            api_key=SecretStr(_SECRET),
            reasoning_effort="low",
        )


def test_text_request_uses_bearer_fixed_route_and_auditable_provenance() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_success_payload(), request=request)

    result = asyncio.run(
        _adapter(handler).generate_text(
            _request(
                parameters=GenerationParameters(
                    temperature=0.65,
                    max_output_tokens=256,
                    seed=7,
                )
            )
        )
    )

    assert captured["url"] == f"{NVIDIA_NIM_OFFICIAL_BASE_URL}/chat/completions"
    assert captured["headers"]["authorization"] == f"Bearer {_SECRET}"
    payload = captured["payload"]
    assert payload["model"] == NVIDIA_NIM_MODEL_ID
    assert payload["temperature"] == 0.65
    assert payload["max_tokens"] == 256
    assert payload["seed"] == 7
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "reasoning_effort" not in payload
    assert result.content == "resultado"
    assert result.evidence.provenance.effective_provider.value == NVIDIA_NIM_PROVIDER_LABEL
    assert result.evidence.provenance.effective_provider.source is ProvenanceSource.OBSERVED
    assert result.evidence.provenance.effective_model.value == NVIDIA_NIM_MODEL_ID
    assert result.evidence.provenance.effective_model.source is ProvenanceSource.REPORTED
    assert result.evidence.usage.status is MeasurementStatus.REPORTED
    assert result.evidence.cost.status is MeasurementStatus.UNAVAILABLE


def test_structured_request_uses_json_mode_and_validates_locally() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_success_payload('{"route":"galpão"}'),
            request=request,
        )

    values = _request().model_dump()
    values.pop("required_capabilities")
    request = StructuredGenerationRequest(
        **values,
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )
    result = asyncio.run(_adapter(handler).generate_structured(request))

    assert captured["response_format"] == {"type": "json_object"}
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}
    assert result.value == _Route(route="galpão")


def test_missing_reported_model_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_success_payload(include_model=False),
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_request()))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.code == "nvidia_nim_unverified_target_provenance"
    assert _SECRET not in str(caught.value)


def test_stream_uses_documented_sse_without_unverified_stream_options() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        chunks = [
            json.dumps(
                {
                    "model": NVIDIA_NIM_MODEL_ID,
                    "choices": [
                        {"delta": {"content": "STORY"}, "finish_reason": None}
                    ],
                }
            ),
            json.dumps(
                {
                    "model": NVIDIA_NIM_MODEL_ID,
                    "choices": [{"delta": {}, "finish_reason": "stop"}],
                }
            ),
            "[DONE]",
        ]
        return httpx.Response(
            200,
            stream=_SSEStream(chunks),
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    async def collect():
        values = _request().model_dump()
        values.pop("required_capabilities")
        request = StreamingGenerationRequest(**values)
        return [event async for event in _adapter(handler).stream_text(request)]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    assert captured["stream"] is True
    assert "stream_options" not in captured
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}
    assert events[-1].evidence is not None
    assert (
        events[-1].evidence.provenance.effective_provider.source
        is ProvenanceSource.OBSERVED
    )
