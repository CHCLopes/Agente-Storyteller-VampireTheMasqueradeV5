import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from api.llm.adapters import OpenRouterAdapter
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    GenerationRequest,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    ProvenanceSource,
    RateLimitOrigin,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    validate_stream_events,
)


class _Answer(BaseModel):
    answer: str


class _UnreadJSONStream(httpx.AsyncByteStream):
    def __init__(self, payload: dict) -> None:
        self._content = json.dumps(payload).encode("utf-8")
        self.closed = False

    async def __aiter__(self):
        yield self._content

    async def aclose(self) -> None:
        self.closed = True


_NVIDIA_LOGICAL_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
_NVIDIA_PHYSICAL_MODEL = "nvidia/nemotron-3-super-120b-a12b-20230311:free"


def _target(model: str = "z-ai/glm-5.2:free") -> LLMTarget:
    return LLMTarget(profile="openrouter-eval", provider="OpenRouter", model=model)


def _capabilities(
    target: LLMTarget | None = None,
    *,
    structured: CapabilitySupport = CapabilitySupport.NATIVE,
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
                source=(
                    "local Pydantic validation over OpenRouter JSON mode"
                    if structured is CapabilitySupport.EMULATED
                    else None
                ),
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )


def _deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=5)


def _metadata(
    *,
    requested: str = "z-ai/glm-5.2:free",
    provider: str = "Decart",
    strategy: str = "direct",
    attempt: int = 1,
    selected_model: str | None = None,
    successful_model: str | None = None,
) -> dict:
    selected_model = requested if selected_model is None else selected_model
    successful_model = requested if successful_model is None else successful_model
    return {
        "requested": requested,
        "strategy": strategy,
        "attempt": attempt,
        "endpoints": {
            "available": [
                {
                    "provider": provider,
                    "model": selected_model,
                    "selected": True,
                }
            ]
        },
        "attempts": [
            {"provider": provider, "model": successful_model, "status": 200}
        ],
    }


def _adapter(
    handler,
    *,
    structured=CapabilitySupport.NATIVE,
    target: LLMTarget | None = None,
    upstream_provider: str = "decart",
) -> OpenRouterAdapter:
    return OpenRouterAdapter(
        base_url="https://openrouter.ai/api/v1",
        capability_set=_capabilities(target, structured=structured),
        upstream_provider=upstream_provider,
        api_key=SecretStr("test-secret"),
        transport=httpx.MockTransport(handler),
    )


def _structured_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        operation="test.openrouter.structured",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
        response_model=_Answer,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )


def _text_request(
    operation: str = "test.openrouter.route",
    *,
    target: LLMTarget | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        operation=operation,
        target=target or _target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )


def _stream_request(
    *, target: LLMTarget | None = None
) -> StreamingGenerationRequest:
    return StreamingGenerationRequest(
        operation="test.openrouter.stream",
        target=target or _target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )


def test_openrouter_request_is_pinned_private_and_observable() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [
                    {
                        "message": {"content": '{"answer":"ok"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 5,
                    "total_tokens": 16,
                    "cost": 0,
                },
                "openrouter_metadata": _metadata(),
            },
        )

    result = asyncio.run(_adapter(handler).generate_structured(_structured_request()))

    assert captured["headers"]["x-openrouter-metadata"] == "enabled"
    assert captured["headers"]["x-openrouter-cache"] == "false"
    assert captured["headers"]["authorization"] == "Bearer test-secret"
    assert captured["body"]["model"] == _target().model
    assert captured["body"]["provider"] == {
        "only": ["decart"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "zdr": True,
    }
    assert captured["body"]["plugins"] == [
        {"id": "web", "enabled": False},
        {"id": "response-healing", "enabled": False},
        {"id": "context-compression", "enabled": False},
    ]
    assert "stream_options" not in captured["body"]
    assert captured["body"]["response_format"]["type"] == "json_schema"
    assert result.value.answer == "ok"
    assert result.evidence.provenance.effective_provider.value == "Decart"
    assert result.evidence.cost.status is MeasurementStatus.REPORTED
    assert result.evidence.cost.amount == Decimal("0")
    assert result.evidence.cost.currency == "OPENROUTER_CREDITS"


def test_emulated_structure_asks_openrouter_for_json_object_then_validates_locally() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [
                    {
                        "message": {"content": '{"answer":"emulated"}'},
                        "finish_reason": "stop",
                    }
                ],
                "openrouter_metadata": _metadata(),
            },
        )

    adapter = _adapter(handler, structured=CapabilitySupport.EMULATED)
    result = asyncio.run(adapter.generate_structured(_structured_request()))

    assert captured["response_format"] == {"type": "json_object"}
    assert result.value.answer == "emulated"


@pytest.mark.parametrize(
    "response_model",
    [_NVIDIA_LOGICAL_MODEL, _NVIDIA_PHYSICAL_MODEL],
)
def test_free_alias_records_the_coherent_physical_model_nonstream(
    response_model: str,
) -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": response_model,
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ],
                "openrouter_metadata": metadata,
            },
        )

    result = asyncio.run(
        _adapter(
            handler,
            target=target,
            upstream_provider="nvidia",
        ).generate_text(_text_request(target=target))
    )

    assert result.content == "ok"
    assert result.evidence.provenance.requested_target.model == _NVIDIA_LOGICAL_MODEL
    assert (
        result.evidence.provenance.effective_model.value == _NVIDIA_PHYSICAL_MODEL
    )
    assert (
        result.evidence.provenance.effective_model.source
        is ProvenanceSource.REPORTED
    )
    assert result.evidence.provenance.effective_provider.value == "Nvidia"


def test_free_alias_records_the_coherent_physical_model_in_stream() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        chunks = [
            {
                "model": target.model,
                "choices": [{"delta": {"content": "olá"}, "finish_reason": None}],
            },
            {
                "model": _NVIDIA_PHYSICAL_MODEL,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "openrouter_metadata": metadata,
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, text=body + "data: [DONE]\n\n")

    async def collect():
        return [
            event
            async for event in _adapter(
                handler,
                target=target,
                upstream_provider="nvidia",
            ).stream_text(_stream_request(target=target))
        ]

    events = asyncio.run(collect())

    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    assert events[-1].evidence is not None
    assert (
        events[-1].evidence.provenance.effective_model.value
        == _NVIDIA_PHYSICAL_MODEL
    )


def test_stream_accepts_final_openrouter_metadata_and_usage_trailer() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        chunks = [
            {
                "model": target.model,
                "choices": [
                    {"delta": {"content": "STORYTELLER_STREAM_OK"}}
                ],
            },
            {
                "model": target.model,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
            },
            {
                "model": _NVIDIA_PHYSICAL_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": ""},
                        "finish_reason": "stop",
                        "native_finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 28,
                    "completion_tokens": 91,
                    "total_tokens": 119,
                    "cost": 0,
                },
                "openrouter_metadata": metadata,
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, text=body + "data: [DONE]\n\n")

    async def collect():
        return [
            event
            async for event in _adapter(
                handler,
                target=target,
                upstream_provider="nvidia",
            ).stream_text(_stream_request(target=target))
        ]

    events = asyncio.run(collect())

    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    assert events[0].delta == "STORYTELLER_STREAM_OK"
    assert events[-1].evidence is not None
    assert events[-1].evidence.usage.total_tokens == 119
    assert events[-1].evidence.cost.amount == Decimal("0")
    assert events[-1].evidence.provenance.effective_provider.value == "Nvidia"
    assert (
        events[-1].evidence.provenance.effective_model.value
        == _NVIDIA_PHYSICAL_MODEL
    )


def test_stream_rejects_content_in_post_stop_openrouter_trailer() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        chunks = [
            {
                "model": target.model,
                "choices": [{"delta": {"content": "ok"}}],
            },
            {
                "model": target.model,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
            },
            {
                "model": _NVIDIA_PHYSICAL_MODEL,
                "choices": [{"delta": {"content": "late"}}],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 2,
                    "total_tokens": 3,
                    "cost": 0,
                },
                "openrouter_metadata": metadata,
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, text=body + "data: [DONE]\n\n")

    async def collect():
        return [
            event
            async for event in _adapter(
                handler,
                target=target,
                upstream_provider="nvidia",
            ).stream_text(_stream_request(target=target))
        ]

    events = asyncio.run(collect())

    assert events[-1].kind is StreamEventKind.FAILED
    assert events[-1].error is not None
    assert events[-1].error.code == "stream_data_after_stop"


def test_stream_normalizes_in_band_provider_error_before_route_metadata() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )
    metadata["endpoints"]["available"][0]["selected"] = False
    metadata["attempts"][0]["status"] = 529

    def handler(request: httpx.Request) -> httpx.Response:
        chunk = {
            "id": "gen-sensitive-provider-error",
            "model": target.model,
            "provider": "Nvidia",
            "error": {
                "code": 529,
                "message": "sensitive upstream overload detail",
                "metadata": {
                    "error_type": "provider_overloaded",
                    "provider_code": "sensitive-native-code",
                },
            },
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": ""},
                    "finish_reason": "error",
                }
            ],
            "openrouter_metadata": metadata,
        }
        body = f"data: {json.dumps(chunk)}\n\n"
        return httpx.Response(
            200,
            text=body,
            headers={"X-Generation-Id": "gen-safe-external-id"},
        )

    async def collect():
        return [
            event
            async for event in _adapter(
                handler,
                target=target,
                upstream_provider="nvidia",
            ).stream_text(_stream_request(target=target))
        ]

    events = asyncio.run(collect())

    assert [event.kind for event in events] == [StreamEventKind.FAILED]
    error = events[-1].error
    assert error is not None
    assert error.category is ErrorCategory.PROVIDER_UNAVAILABLE
    assert error.code == "openrouter_provider_overloaded"
    assert error.status_code == 529
    assert error.retryable is True
    assert error.external_id == "gen-safe-external-id"
    assert error.evidence.provenance.effective_provider.value == "Nvidia"
    assert "sensitive" not in error.safe_message


def test_stream_in_band_rate_limit_preserves_partial_output() -> None:
    metadata = _metadata()
    metadata["endpoints"]["available"][0]["selected"] = False
    metadata["attempts"][0]["status"] = 429

    def handler(request: httpx.Request) -> httpx.Response:
        chunks = [
            {
                "model": _target().model,
                "choices": [{"delta": {"content": "partial"}}],
            },
            {
                "model": _target().model,
                "error": {
                    "code": 429,
                    "message": "sensitive rate-limit detail",
                    "metadata": {
                        "error_type": "rate_limit_exceeded",
                        "provider_code": "native_429",
                    },
                },
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": ""},
                        "finish_reason": "error",
                    }
                ],
                "openrouter_metadata": metadata,
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(
            200,
            text=body,
            headers={"X-Generation-Id": "gen-partial-rate-limit"},
        )

    async def collect():
        return [event async for event in _adapter(handler).stream_text(_stream_request())]

    events = asyncio.run(collect())

    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.FAILED,
    ]
    assert events[0].delta == "partial"
    assert events[-1].partial_output is True
    error = events[-1].error
    assert error is not None
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.code == "openrouter_rate_limit_exceeded"
    assert error.status_code == 429
    assert error.retryable is True
    assert error.external_id == "gen-partial-rate-limit"
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.UPSTREAM
    assert error.rate_limit.provider_code == "native_429"


def test_http_gateway_rate_limit_keeps_only_allowlisted_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "sensitive gateway diagnostic"}},
            headers={
                "X-RateLimit-Limit": "20",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1788561200",
                "X-Internal-Trace": "must-not-cross-boundary",
            },
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_text_request()))

    error = caught.value.error
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.GATEWAY
    assert error.rate_limit.limit == "20"
    assert error.rate_limit.remaining == "0"
    assert error.rate_limit.reset == "1788561200"
    assert error.rate_limit.provider_code is None
    serialized = error.model_dump_json()
    assert "sensitive gateway diagnostic" not in serialized
    assert "must-not-cross-boundary" not in serialized


def test_http_upstream_rate_limit_keeps_only_sanitized_provider_code() -> None:
    provider_message = "sensitive upstream diagnostic"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": provider_message,
                    "metadata": {
                        "provider_code": "native-limit-code",
                        "private": "must-not-cross-boundary",
                    },
                }
            },
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_text_request()))

    error = caught.value.error
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.UPSTREAM
    assert error.rate_limit.provider_code == "native-limit-code"
    serialized = error.model_dump_json()
    assert provider_message not in serialized
    assert "must-not-cross-boundary" not in serialized
    assert "sensitive" not in error.safe_message


def test_stream_http_upstream_rate_limit_reads_body_before_normalizing() -> None:
    provider_message = "sensitive unread upstream diagnostic"
    body_stream = _UnreadJSONStream(
        {
            "error": {
                "message": provider_message,
                "metadata": {
                    "provider_code": "native-limit-code",
                    "private": "must-not-cross-boundary",
                },
            }
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={
                "content-type": "application/json",
                "retry-after": "1",
                "x-generation-id": "gen-unread-rate-limit",
                "x-ratelimit-limit": "20",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1788561200",
                "x-private-diagnostic": "must-not-cross-boundary",
            },
            stream=body_stream,
            request=request,
        )

    async def collect():
        return [
            event
            async for event in _adapter(handler).stream_text(_stream_request())
        ]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert len(events) == 1
    assert events[0].kind is StreamEventKind.FAILED
    error = events[0].error
    assert error is not None
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.status_code == 429
    assert error.retryable is True
    assert error.retry_after_seconds == 1.0
    assert error.external_id == "gen-unread-rate-limit"
    assert error.partial_output is False
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.UPSTREAM
    assert error.rate_limit.limit == "20"
    assert error.rate_limit.remaining == "0"
    assert error.rate_limit.reset == "1788561200"
    assert error.rate_limit.provider_code == "native-limit-code"
    assert body_stream.closed is True
    serialized = error.model_dump_json()
    assert provider_message not in serialized
    assert "must-not-cross-boundary" not in serialized


def test_stream_http_rate_limit_oversized_body_keeps_status_and_headers() -> None:
    body_stream = _UnreadJSONStream(
        {"error": {"message": "must-not-cross-boundary"}}
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={
                "content-type": "application/json",
                "content-length": str(64 * 1024 + 1),
                "x-ratelimit-limit": "20",
                "x-ratelimit-remaining": "0",
            },
            stream=body_stream,
            request=request,
        )

    async def collect():
        return [
            event
            async for event in _adapter(handler).stream_text(_stream_request())
        ]

    events = asyncio.run(collect())

    assert len(events) == 1
    assert events[0].kind is StreamEventKind.FAILED
    error = events[0].error
    assert error is not None
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.status_code == 429
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.GATEWAY
    assert error.rate_limit.limit == "20"
    assert error.rate_limit.remaining == "0"
    assert error.rate_limit.provider_code is None
    assert body_stream.closed is True
    assert "must-not-cross-boundary" not in error.model_dump_json()


def test_http_rate_limit_rejects_provider_message_disguised_as_code() -> None:
    unsafe_code = "native 429; bearer private-token"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "metadata": {"provider_code": unsafe_code},
                }
            },
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_text_request()))

    rate_limit = caught.value.error.rate_limit
    assert rate_limit is not None
    assert rate_limit.origin is RateLimitOrigin.UNKNOWN
    assert rate_limit.provider_code is None
    assert unsafe_code not in caught.value.error.model_dump_json()


def test_stream_error_finish_requires_error_envelope() -> None:
    metadata = _metadata()
    metadata["endpoints"]["available"][0]["selected"] = False

    def handler(request: httpx.Request) -> httpx.Response:
        chunk = {
            "model": _target().model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": ""},
                    "finish_reason": "error",
                }
            ],
            "openrouter_metadata": metadata,
        }
        return httpx.Response(200, text=f"data: {json.dumps(chunk)}\n\n")

    async def collect():
        return [event async for event in _adapter(handler).stream_text(_stream_request())]

    events = asyncio.run(collect())

    assert [event.kind for event in events] == [StreamEventKind.FAILED]
    error = events[-1].error
    assert error is not None
    assert error.category is ErrorCategory.MALFORMED_RESPONSE
    assert error.code == "openrouter_missing_error_envelope"


def test_incoherent_response_model_preserves_selected_route_for_diagnostics() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"X-Generation-Id": "gen-synthetic-route-mismatch"},
            json={
                "model": "other/model",
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ],
                "openrouter_metadata": metadata,
            },
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(
            _adapter(
                handler,
                target=target,
                upstream_provider="nvidia",
            ).generate_text(_text_request(target=target))
        )

    error = caught.value.error
    assert error.category is ErrorCategory.TARGET_MISMATCH
    assert error.code == "openrouter_effective_model_mismatch"
    assert error.external_id == "gen-synthetic-route-mismatch"
    assert (
        error.evidence.provenance.effective_model.value == _NVIDIA_PHYSICAL_MODEL
    )


def test_optional_attempt_details_may_be_omitted_for_first_attempt_success() -> None:
    target = _target(_NVIDIA_LOGICAL_MODEL)
    metadata = _metadata(
        requested=target.model,
        provider="Nvidia",
        selected_model=_NVIDIA_PHYSICAL_MODEL,
        successful_model=_NVIDIA_PHYSICAL_MODEL,
    )
    metadata.pop("attempts")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": target.model,
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ],
                "openrouter_metadata": metadata,
            },
        )

    result = asyncio.run(
        _adapter(
            handler,
            target=target,
            upstream_provider="nvidia",
        ).generate_text(_text_request(target=target))
    )

    assert result.content == "ok"
    assert (
        result.evidence.provenance.effective_model.value == _NVIDIA_PHYSICAL_MODEL
    )


@pytest.mark.parametrize(
    "model",
    [
        "openrouter/free",
        "openrouter/auto",
        "openrouter/bodybuilder",
        "openrouter/pareto-code",
        "openrouter/fusion",
        "openrouter/fusion-flash",
        "~openai/gpt-4o-mini",
        "meta-llama/llama-3.3-70b-instruct:nitro",
        "meta-llama/llama-3.3-70b-instruct:floor",
        "meta-llama/llama-3.3-70b-instruct:exacto",
        "meta-llama/llama-3.3-70b-instruct:online",
    ],
)
def test_dynamic_model_routes_are_rejected(model: str) -> None:
    target = _target(model)

    with pytest.raises(ValueError, match="fixed slug"):
        OpenRouterAdapter(
            base_url="https://openrouter.ai/api/v1",
            capability_set=_capabilities(target),
            upstream_provider="decart",
            api_key=SecretStr("test-secret"),
        )


@pytest.mark.parametrize(
    ("metadata", "code"),
    [
        (_metadata(requested="other/model"), "openrouter_requested_model_mismatch"),
        (_metadata(strategy="free"), "openrouter_dynamic_routing_detected"),
        (_metadata(attempt=2), "openrouter_fallback_attempt_detected"),
        (_metadata(provider="Another Cloud"), "openrouter_selected_provider_mismatch"),
        (
            {**_metadata(), "pipeline": [{"type": "response_healing"}]},
            "openrouter_pipeline_transformation_detected",
        ),
    ],
)
def test_route_drift_fails_closed(metadata: dict, code: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ],
                "openrouter_metadata": metadata,
            },
        )

    request = GenerationRequest(
        operation="test.openrouter.route",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(request))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.code == code


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("selected_missing", "openrouter_selected_endpoint_count_invalid"),
        ("selected_duplicate", "openrouter_selected_endpoint_count_invalid"),
        ("selected_provider_missing", "openrouter_selected_provider_missing"),
        ("selected_model_missing", "openrouter_selected_model_missing"),
        (
            "selected_model_mismatch",
            "openrouter_successful_attempt_model_mismatch",
        ),
        ("selected_model_not_exact", "openrouter_selected_model_mismatch"),
        ("attempts_null", "openrouter_successful_attempt_count_invalid"),
        ("success_missing", "openrouter_successful_attempt_count_invalid"),
        ("success_duplicate", "openrouter_successful_attempt_count_invalid"),
        ("attempt_count_mismatch", "openrouter_attempt_count_inconsistent"),
        (
            "successful_provider_missing",
            "openrouter_successful_attempt_provider_missing",
        ),
        (
            "successful_provider_mismatch",
            "openrouter_successful_attempt_provider_mismatch",
        ),
        (
            "successful_model_missing",
            "openrouter_successful_attempt_model_missing",
        ),
        (
            "successful_model_mismatch",
            "openrouter_successful_attempt_model_mismatch",
        ),
        (
            "successful_model_not_exact",
            "openrouter_successful_attempt_model_mismatch",
        ),
        (
            "successful_status_float",
            "openrouter_successful_attempt_count_invalid",
        ),
    ],
)
def test_adversarial_route_metadata_fails_closed_nonstream(
    case: str,
    code: str,
) -> None:
    metadata = _metadata()
    selected = metadata["endpoints"]["available"][0]
    successful = metadata["attempts"][0]

    if case == "selected_missing":
        selected["selected"] = False
    elif case == "selected_duplicate":
        metadata["endpoints"]["available"].append(dict(selected))
    elif case == "selected_provider_missing":
        selected.pop("provider")
    elif case == "selected_model_missing":
        selected.pop("model")
    elif case == "selected_model_mismatch":
        selected["model"] = "other/model"
    elif case == "selected_model_not_exact":
        selected["model"] = f" {_target().model} "
    elif case == "attempts_null":
        metadata["attempts"] = None
    elif case == "success_missing":
        successful["status"] = 500
    elif case == "success_duplicate":
        metadata["attempts"].append(dict(successful))
    elif case == "attempt_count_mismatch":
        metadata["attempts"].insert(
            0,
            {
                "provider": "Decart",
                "model": _target().model,
                "status": 500,
            },
        )
    elif case == "successful_provider_missing":
        successful.pop("provider")
    elif case == "successful_provider_mismatch":
        successful["provider"] = "Another Cloud"
    elif case == "successful_model_missing":
        successful.pop("model")
    elif case == "successful_model_mismatch":
        successful["model"] = "other/model"
    elif case == "successful_model_not_exact":
        successful["model"] = f" {_target().model} "
    elif case == "successful_status_float":
        successful["status"] = 200.0
    else:  # pragma: no cover - parametrization guard
        raise AssertionError(f"unknown case: {case}")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [
                    {"message": {"content": "ok"}, "finish_reason": "stop"}
                ],
                "openrouter_metadata": metadata,
            },
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_text_request()))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.code == code


@pytest.mark.parametrize(
    ("response_model", "code"),
    [
        (None, "openrouter_effective_model_missing"),
        ("other/model", "openrouter_effective_model_mismatch"),
    ],
)
def test_nonstream_requires_exact_effective_model(
    response_model: str | None,
    code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "choices": [
                {"message": {"content": "ok"}, "finish_reason": "stop"}
            ],
            "openrouter_metadata": _metadata(),
        }
        if response_model is not None:
            payload["model"] = response_model
        return httpx.Response(200, json=payload)

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_text_request()))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.code == code


def test_stream_terminal_carries_provider_usage_and_cost() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        chunks = [
            {
                "model": _target().model,
                "choices": [{"delta": {"content": "olá"}, "finish_reason": None}],
            },
            {
                "model": _target().model,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 1,
                    "total_tokens": 4,
                    "cost": 0.000001,
                },
                "openrouter_metadata": _metadata(),
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        body += "data: [DONE]\n\n"
        return httpx.Response(200, text=body)

    request = StreamingGenerationRequest(
        operation="test.openrouter.stream",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in _adapter(handler).stream_text(request)]

    events = asyncio.run(collect())
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    evidence = events[-1].evidence
    assert evidence is not None
    assert evidence.provenance.effective_provider.value == "Decart"
    assert evidence.usage.total_tokens == 4
    assert evidence.cost.amount == Decimal("0.000001")
    assert "stream_options" not in captured


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("selected_missing", "openrouter_selected_endpoint_count_invalid"),
        ("selected_duplicate", "openrouter_selected_endpoint_count_invalid"),
        (
            "successful_model_mismatch",
            "openrouter_successful_attempt_model_mismatch",
        ),
    ],
)
def test_adversarial_route_metadata_fails_closed_in_stream(
    case: str,
    code: str,
) -> None:
    metadata = _metadata()
    if case == "selected_missing":
        metadata["endpoints"]["available"][0]["selected"] = False
    elif case == "selected_duplicate":
        selected = metadata["endpoints"]["available"][0]
        metadata["endpoints"]["available"].append(dict(selected))
    elif case == "successful_model_mismatch":
        metadata["attempts"][0]["model"] = "other/model"
    else:  # pragma: no cover - parametrization guard
        raise AssertionError(f"unknown case: {case}")

    def handler(request: httpx.Request) -> httpx.Response:
        chunks = [
            {
                "model": _target().model,
                "choices": [{"delta": {"content": "partial"}}],
            },
            {
                "model": _target().model,
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "openrouter_metadata": metadata,
            },
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        body += "data: [DONE]\n\n"
        return httpx.Response(200, text=body)

    async def collect():
        return [
            event
            async for event in _adapter(handler).stream_text(_stream_request())
        ]

    events = asyncio.run(collect())
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.FAILED,
    ]
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.category is ErrorCategory.TARGET_MISMATCH
    assert events[-1].error.code == code


@pytest.mark.parametrize(
    ("response_model", "code"),
    [
        (None, "openrouter_effective_model_missing"),
        ("other/model", "openrouter_effective_model_mismatch"),
    ],
)
def test_stream_requires_exact_effective_model(
    response_model: str | None,
    code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        first_chunk = {"choices": [{"delta": {"content": "partial"}}]}
        final_chunk = {
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "openrouter_metadata": _metadata(),
        }
        if response_model is not None:
            first_chunk["model"] = response_model
            final_chunk["model"] = response_model
        chunks = [first_chunk, final_chunk]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        body += "data: [DONE]\n\n"
        return httpx.Response(200, text=body)

    async def collect():
        return [
            event
            async for event in _adapter(handler).stream_text(_stream_request())
        ]

    events = asyncio.run(collect())
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.FAILED,
    ]
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.category is ErrorCategory.TARGET_MISMATCH
    assert events[-1].error.code == code


def test_http_402_is_a_non_retryable_payment_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"error": {"message": "credits"}})

    request = GenerationRequest(
        operation="test.openrouter.credit",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(request))

    assert caught.value.error.category is ErrorCategory.PAYMENT_REQUIRED
    assert caught.value.error.status_code == 402
    assert caught.value.error.retryable is False


def test_cache_hit_without_router_metadata_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [
                    {"message": {"content": "cached"}, "finish_reason": "stop"}
                ],
                "usage": {"cost": 0},
            },
        )

    request = GenerationRequest(
        operation="test.openrouter.cache",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="synthetic"),),
        deadline=_deadline(),
    )
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(request))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.code == "openrouter_route_metadata_missing"
