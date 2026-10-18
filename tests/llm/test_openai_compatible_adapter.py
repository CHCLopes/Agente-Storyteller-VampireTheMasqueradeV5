import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from api.llm.adapters import OpenAICompatibleAdapter
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    CapabilitySupport,
    ConnectionTestRequest,
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
    SYNTHETIC_PROBE_EXPECTED,
    SYNTHETIC_PROBE_PROMPT,
    TokenUsage,
    validate_stream_events,
)


class _Route(BaseModel):
    route: str


def _target(model: str = "caller-selected-model") -> LLMTarget:
    return LLMTarget(
        profile="explicit-test-profile",
        provider="caller-selected-provider",
        model=model,
    )


def _capabilities(
    target: LLMTarget | None = None,
    *,
    structured_support: CapabilitySupport = CapabilitySupport.NATIVE,
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
                support=structured_support,
                source=(
                    "local Pydantic validation over JSON text"
                    if structured_support is CapabilitySupport.EMULATED
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


def _messages() -> tuple[LLMMessage, ...]:
    return (LLMMessage(role=MessageRole.USER, content="synthetic input"),)


def _traceback_locals(exc: BaseException) -> str:
    rows: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        module_name = traceback.tb_frame.f_globals.get("__name__", "")
        if module_name.startswith("api.llm"):
            rows.extend(
                f"{name}={value!r}"
                for name, value in traceback.tb_frame.f_locals.items()
            )
        traceback = traceback.tb_next
    return "\n".join(rows)


def _adapter(handler, target: LLMTarget | None = None) -> OpenAICompatibleAdapter:
    selected_target = target or _target()
    return OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(selected_target),
        transport=httpx.MockTransport(handler),
    )


def test_text_generation_uses_exact_target_and_normalizes_evidence() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = GenerationRequest(
        operation="text",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    result = asyncio.run(adapter.generate_text(request))

    assert captured["model"] == request.target.model
    assert "provider" not in captured
    assert result.content == "result"
    assert result.evidence.usage == TokenUsage(
        status=MeasurementStatus.REPORTED,
        input_tokens=3,
        output_tokens=2,
        total_tokens=5,
        source="openai-compatible response.usage",
    )
    assert result.evidence.cost.status is MeasurementStatus.UNAVAILABLE
    assert (
        result.evidence.provenance.effective_provider.source
        is ProvenanceSource.UNKNOWN
    )
    assert result.evidence.provenance.effective_provider.value is None
    assert result.evidence.provenance.effective_model.value == request.target.model


def test_explicit_reasoning_effort_is_sent_without_changing_the_request_contract() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(),
        reasoning_effort="none",
        transport=httpx.MockTransport(handler),
    )
    request = GenerationRequest(
        operation="text-with-explicit-reasoning-effort",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    result = asyncio.run(adapter.generate_text(request))

    assert result.content == "result"
    assert captured["reasoning_effort"] == "none"


def test_reasoning_effort_is_omitted_by_default() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    request = GenerationRequest(
        operation="text-with-provider-default-reasoning",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    asyncio.run(_adapter(handler).generate_text(request))

    assert "reasoning_effort" not in captured


@pytest.mark.anyio
async def test_cancelling_caller_task_cancels_in_flight_transport() -> None:
    transport_started = asyncio.Event()
    transport_cancelled = asyncio.Event()
    private_prompt = "private cancellation prompt"
    synthetic_secret = "synthetic-cancellation-secret"

    async def handler(request: httpx.Request) -> httpx.Response:
        transport_started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            transport_cancelled.set()
            raise
        return httpx.Response(
            200,
            json={
                "model": _target().model,
                "choices": [{"message": {"content": "late result"}}],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(),
        api_key=SecretStr(synthetic_secret),
        transport=httpx.MockTransport(handler),
    )
    request = GenerationRequest(
        operation="caller-task-cancellation",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content=private_prompt),),
        deadline=_deadline(),
    )
    task = asyncio.create_task(adapter.generate_text(request))
    await asyncio.wait_for(transport_started.wait(), timeout=1)

    task.cancel()
    with pytest.raises(asyncio.CancelledError) as caught:
        await task

    await asyncio.wait_for(transport_cancelled.wait(), timeout=1)
    traceback_locals = _traceback_locals(caught.value)
    assert private_prompt not in traceback_locals
    assert synthetic_secret not in traceback_locals


@pytest.mark.anyio
async def test_cancelling_stream_task_cleans_transport_and_traceback() -> None:
    transport_started = asyncio.Event()
    transport_cancelled = asyncio.Event()
    private_prompt = "private streaming cancellation prompt"
    synthetic_secret = "synthetic-streaming-secret"

    async def handler(request: httpx.Request) -> httpx.Response:
        transport_started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            transport_cancelled.set()
            raise
        return httpx.Response(200, request=request)

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(),
        api_key=SecretStr(synthetic_secret),
        transport=httpx.MockTransport(handler),
    )
    request = StreamingGenerationRequest(
        operation="caller-stream-cancellation",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content=private_prompt),),
        deadline=_deadline(),
    )

    async def collect() -> list:
        return [event async for event in adapter.stream_text(request)]

    task = asyncio.create_task(collect())
    await asyncio.wait_for(transport_started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError) as caught:
        await task

    await asyncio.wait_for(transport_cancelled.wait(), timeout=1)
    traceback_locals = _traceback_locals(caught.value)
    assert private_prompt not in traceback_locals
    assert synthetic_secret not in traceback_locals


def test_adapter_alone_builds_http_endpoint_and_bearer_authorization() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1/",
        capability_set=_capabilities(),
        api_key=SecretStr("synthetic-token"),
        transport=httpx.MockTransport(handler),
    )
    request = GenerationRequest(
        operation="authorization-isolation",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    result = asyncio.run(adapter.generate_text(request))

    assert result.content == "result"
    assert captured == {
        "url": "https://adapter.invalid/v1/chat/completions",
        "authorization": "Bearer synthetic-token",
    }


def test_empty_api_key_does_not_send_an_authorization_header() -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(),
        api_key=SecretStr("   "),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        adapter.generate_text(
            GenerationRequest(
                operation="empty-key",
                target=_target(),
                messages=_messages(),
                deadline=_deadline(),
            )
        )
    )

    assert result.content == "result"
    assert captured["authorization"] is None


def test_structured_generation_sends_schema_and_validates_without_repair() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {
                        "message": {"content": '{"route":"action"}'},
                        "finish_reason": "stop",
                    }
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = StructuredGenerationRequest(
        operation="structured",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
        response_model=_Route,
    )

    result = asyncio.run(adapter.generate_structured(request))

    assert result.value == _Route(route="action")
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert "route" in captured["response_format"]["json_schema"]["schema"]["properties"]


def test_emulated_structured_generation_accepts_one_complete_json_fence() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {
                        "message": {
                            "content": '```JSON\n{"route":"action"}\n```'
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(
            structured_support=CapabilitySupport.EMULATED
        ),
        transport=httpx.MockTransport(handler),
    )
    request = StructuredGenerationRequest(
        operation="structured-fenced-json",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )

    result = asyncio.run(adapter.generate_structured(request))

    assert result.value == _Route(route="action")
    assert "response_format" not in captured


def test_structured_generation_rejects_fenced_json_with_surrounding_prose() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {
                        "message": {
                            "content": (
                                "Here is the result:\n"
                                '```json\n{"route":"action"}\n```'
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(
            structured_support=CapabilitySupport.EMULATED
        ),
        transport=httpx.MockTransport(handler),
    )
    request = StructuredGenerationRequest(
        operation="structured-fenced-json-with-prose",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))

    assert caught.value.error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert calls == 1


def test_invalid_structured_output_is_normalized_without_a_second_call() -> None:
    calls = 0
    raw_output = "not-json-private-output"

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": raw_output}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = StructuredGenerationRequest(
        operation="structured",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
        response_model=_Route,
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))

    assert caught.value.error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert raw_output not in repr(caught.value)
    assert raw_output not in _traceback_locals(caught.value)
    assert calls == 1


@pytest.mark.parametrize(
    ("finish_reason", "expected_category", "expected_code"),
    [
        ("length", ErrorCategory.MALFORMED_RESPONSE, "generation_truncated"),
        (
            "content_filter",
            ErrorCategory.CONTENT_REJECTED,
            "generation_content_filtered",
        ),
    ],
)
def test_non_stream_generation_rejects_non_success_finish_reasons(
    finish_reason,
    expected_category,
    expected_code,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {
                        "message": {"content": "partial response"},
                        "finish_reason": finish_reason,
                    }
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = GenerationRequest(
        operation="non-success-finish",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_text(request))
    assert caught.value.error.category is expected_category
    assert caught.value.error.code == expected_code


def test_http_error_is_safe_normalized_and_keeps_retry_after() -> None:
    external_body = "sensitive provider diagnostic"
    synthetic_secret = "synthetic-private-bearer"
    private_prompt = "private campaign prompt"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            text=external_body,
            headers={
                "retry-after": "2.5",
                "x-request-id": "external-123",
                "x-ratelimit-limit": "20",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1788561200",
                "x-private-diagnostic": "must-not-cross-boundary",
            },
            request=request,
        )

    adapter = OpenAICompatibleAdapter(
        base_url="https://adapter.invalid/v1",
        capability_set=_capabilities(),
        api_key=SecretStr(synthetic_secret),
        transport=httpx.MockTransport(handler),
    )
    request = GenerationRequest(
        operation="rate-limit",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content=private_prompt),),
        deadline=_deadline(),
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_text(request))

    error = caught.value.error
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.status_code == 429
    assert error.retryable is True
    assert error.retry_after_seconds == 2.5
    assert error.external_id == "external-123"
    assert error.rate_limit is not None
    assert error.rate_limit.origin is RateLimitOrigin.UNKNOWN
    assert error.rate_limit.limit == "20"
    assert error.rate_limit.remaining == "0"
    assert error.rate_limit.reset == "1788561200"
    assert error.rate_limit.provider_code is None
    assert "must-not-cross-boundary" not in error.model_dump_json()
    assert external_body not in error.safe_message
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    public_exception = repr(caught.value)
    assert synthetic_secret not in public_exception
    assert private_prompt not in public_exception
    assert external_body not in public_exception
    traceback_locals = _traceback_locals(caught.value)
    assert synthetic_secret not in traceback_locals
    assert private_prompt not in traceback_locals
    assert external_body not in traceback_locals


def test_stream_normalizes_deltas_usage_and_single_terminal() -> None:
    body = "\n".join(
        [
            'data: {"model":"caller-selected-model","choices":[{"delta":{"content":"one"}}]}',
            'data: {"model":"caller-selected-model","choices":[{"delta":{"content":"two"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":2,"total_tokens":4}}',
            "data: [DONE]",
            "",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body.encode(), request=request)

    adapter = _adapter(handler)
    request = StreamingGenerationRequest(
        operation="stream",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in adapter.stream_text(request)]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert [event.delta for event in events[:-1]] == ["one", "two"]
    assert events[-1].kind is StreamEventKind.COMPLETED
    assert events[-1].evidence is not None
    assert events[-1].evidence.usage.total_tokens == 4


@pytest.mark.parametrize(
    ("finish_reason", "expected_category"),
    [
        ("length", ErrorCategory.MALFORMED_RESPONSE),
        ("content_filter", ErrorCategory.CONTENT_REJECTED),
    ],
)
def test_stream_rejects_non_success_finish_reason_as_partial_failure(
    finish_reason,
    expected_category,
) -> None:
    body = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"partial"}}]}',
            (
                'data: {"choices":[{"delta":{},"finish_reason":"'
                + finish_reason
                + '"}]}'
            ),
            "data: [DONE]",
            "",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body.encode(), request=request)

    adapter = _adapter(handler)
    request = StreamingGenerationRequest(
        operation="stream-non-success-finish",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in adapter.stream_text(request)]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert [event.delta for event in events[:-1]] == ["partial"]
    assert events[-1].kind is StreamEventKind.FAILED
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.category is expected_category


def test_malformed_stream_after_delta_is_a_partial_failure() -> None:
    body = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"partial"}}]}',
            "data: not-json",
            "",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body.encode(), request=request)

    adapter = _adapter(handler)
    request = StreamingGenerationRequest(
        operation="stream",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in adapter.stream_text(request)]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert events[-1].kind is StreamEventKind.FAILED
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.category is ErrorCategory.MALFORMED_RESPONSE


def test_reported_model_mismatch_fails_instead_of_succeeding() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "silently-different-model",
                "choices": [
                    {"message": {"content": "result"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = GenerationRequest(
        operation="target-mismatch",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_text(request))
    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH


def test_connection_probe_is_fixed_and_synthetic() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {
                        "message": {"content": SYNTHETIC_PROBE_EXPECTED},
                        "finish_reason": "stop",
                    }
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    result = asyncio.run(
        adapter.test_connection(
            ConnectionTestRequest(target=_target(), deadline=_deadline())
        )
    )

    assert result.success is True
    assert captured["messages"] == [{"role": "user", "content": SYNTHETIC_PROBE_PROMPT}]
    assert captured["model"] == _target().model
    assert captured["max_tokens"] == 128


def test_whitespace_output_is_normalized_for_generation_and_probe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "caller-selected-model",
                "choices": [
                    {"message": {"content": "   \n"}, "finish_reason": "stop"}
                ],
            },
            request=request,
        )

    adapter = _adapter(handler)
    request = GenerationRequest(
        operation="whitespace",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_text(request))
    assert caught.value.error.category is ErrorCategory.MALFORMED_RESPONSE
    assert caught.value.error.code == "invalid_message_content"

    probe = asyncio.run(
        adapter.test_connection(
            ConnectionTestRequest(target=_target(), deadline=_deadline())
        )
    )
    assert probe.success is False
    assert probe.error is not None
    assert probe.error.category is ErrorCategory.MALFORMED_RESPONSE
