import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import BaseModel

from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    CancellationToken,
    ConnectionTestRequest,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    SYNTHETIC_PROBE_PROMPT,
    SYNTHETIC_PROBE_VERSION,
    TokenUsage,
    validate_stream_events,
)
from api.llm.testing import FakeLLMAdapter


class _Route(BaseModel):
    route: str


def _target(model: str = "model-a") -> LLMTarget:
    return LLMTarget(profile="test", provider="synthetic", model=model)


def _capabilities(
    target: LLMTarget | None = None,
    *,
    structured: CapabilitySupport = CapabilitySupport.NATIVE,
    streaming: CapabilitySupport = CapabilitySupport.NATIVE,
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
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=streaming,
            ),
        ),
    )


def _deadline(seconds: float = 5) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _messages() -> tuple[LLMMessage, ...]:
    return (LLMMessage(role=MessageRole.USER, content="synthetic input"),)


def _text_request(
    *,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline: datetime | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        operation="test-text",
        target=target or _target(),
        messages=_messages(),
        deadline=deadline or _deadline(),
        cancellation=cancellation or CancellationToken(),
    )


def _stream_request(
    *,
    cancellation: CancellationToken | None = None,
    deadline: datetime | None = None,
) -> StreamingGenerationRequest:
    return StreamingGenerationRequest(
        operation="test-stream",
        target=_target(),
        messages=_messages(),
        deadline=deadline or _deadline(),
        cancellation=cancellation or CancellationToken(),
    )


def test_text_and_structured_generation_return_product_owned_models() -> None:
    usage = TokenUsage(
        status=MeasurementStatus.REPORTED,
        input_tokens=4,
        output_tokens=2,
        total_tokens=6,
        source="synthetic report",
    )
    cost = CostMeasurement(
        status=MeasurementStatus.ESTIMATED,
        amount=Decimal("0.001"),
        currency="USD",
        source="synthetic price fixture v1",
    )
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        text="plain result",
        structured_payload={"route": "action"},
        usage=usage,
        cost=cost,
        effective_provider="synthetic-provider",
        effective_model="model-a",
    )

    async def exercise() -> None:
        text_result = await adapter.generate_text(_text_request())
        structured_result = await adapter.generate_structured(
            StructuredGenerationRequest(
                operation="test-structured",
                target=_target(),
                messages=_messages(),
                deadline=_deadline(),
                response_model=_Route,
            )
        )

        assert text_result.content == "plain result"
        assert structured_result.value == _Route(route="action")
        assert text_result.evidence.usage.total_tokens == 6
        assert text_result.evidence.cost.amount == Decimal("0.001")
        assert text_result.evidence.provenance.effective_model.value == "model-a"

    asyncio.run(exercise())
    assert adapter.external_call_count == 2


def test_unknown_capability_fails_before_dispatch() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(
            structured=CapabilitySupport.UNKNOWN,
        ),
        structured_payload={"route": "action"},
    )

    async def exercise() -> None:
        request = StructuredGenerationRequest(
            operation="test-structured",
            target=_target(),
            messages=_messages(),
            deadline=_deadline(),
            response_model=_Route,
        )
        with pytest.raises(LLMInvocationError) as caught:
            await adapter.generate_structured(request)
        assert caught.value.error.category is ErrorCategory.UNSUPPORTED_CAPABILITY

    asyncio.run(exercise())
    assert adapter.external_call_count == 0


def test_successful_stream_has_ordered_deltas_and_one_terminal() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        stream_deltas=("one", "two"),
    )

    async def collect():
        return [event async for event in adapter.stream_text(_stream_request())]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    assert adapter.external_call_count == 1


def test_stream_failure_after_delta_is_terminal_and_partial() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        stream_deltas=("visible", "never emitted"),
        failure_category=ErrorCategory.PROVIDER_UNAVAILABLE,
        fail_after_deltas=1,
    )

    async def collect():
        return [event async for event in adapter.stream_text(_stream_request())]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert events[-1].kind is StreamEventKind.FAILED
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.partial_output is True


def test_cancellation_before_dispatch_is_distinct_and_makes_no_call() -> None:
    cancellation = CancellationToken()
    cancellation.cancel("synthetic cancellation")
    adapter = FakeLLMAdapter(capability_set=_capabilities())

    async def exercise() -> None:
        with pytest.raises(LLMInvocationError) as caught:
            await adapter.generate_text(_text_request(cancellation=cancellation))
        assert caught.value.error.category is ErrorCategory.CANCELLED

    asyncio.run(exercise())
    assert adapter.external_call_count == 0


def test_cancellation_during_stream_yields_one_cancelled_terminal() -> None:
    cancellation = CancellationToken()
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        stream_deltas=("partial",),
    )

    async def collect():
        stream = adapter.stream_text(_stream_request(cancellation=cancellation))
        first = await stream.__anext__()
        cancellation.cancel()
        rest = [event async for event in stream]
        return [first, *rest]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert events[-1].kind is StreamEventKind.CANCELLED
    assert events[-1].partial_output is True


def test_expired_deadline_is_timeout_not_cancellation() -> None:
    adapter = FakeLLMAdapter(capability_set=_capabilities())
    expired = datetime.now(timezone.utc) - timedelta(milliseconds=1)

    async def collect():
        return [
            event
            async for event in adapter.stream_text(_stream_request(deadline=expired))
        ]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert events[0].kind is StreamEventKind.TIMED_OUT
    assert events[0].error is not None
    assert events[0].error.category is ErrorCategory.TIMEOUT
    assert adapter.external_call_count == 0


def test_reported_model_mismatch_is_not_a_success() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        effective_model="different-model",
    )

    async def exercise() -> None:
        with pytest.raises(LLMInvocationError) as caught:
            await adapter.generate_text(_text_request())
        assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
        assert (
            caught.value.error.evidence.provenance.effective_model.value
            == "different-model"
        )

    asyncio.run(exercise())


def test_connection_probe_uses_only_fixed_versioned_synthetic_content() -> None:
    adapter = FakeLLMAdapter(capability_set=_capabilities())

    async def exercise():
        return await adapter.test_connection(
            ConnectionTestRequest(target=_target(), deadline=_deadline())
        )

    result = asyncio.run(exercise())
    assert result.success is True
    assert result.probe_version == SYNTHETIC_PROBE_VERSION
    assert len(adapter.requests) == 1
    probe = adapter.requests[0]
    assert probe.operation == SYNTHETIC_PROBE_VERSION
    assert [message.content for message in probe.messages] == [SYNTHETIC_PROBE_PROMPT]
    assert "campaign" not in probe.model_dump_json().lower()
    assert "player" not in probe.model_dump_json().lower()
