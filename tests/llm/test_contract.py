from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    AdapterIdentity,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    CapabilitySupport,
    CostMeasurement,
    GenerationRequest,
    InvocationEvidence,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    Provenance,
    ProvenanceSource,
    ProvenanceValue,
    StreamEventBuilder,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    TokenUsage,
    validate_stream_events,
)


class _StructuredAnswer(BaseModel):
    route: str


def _target() -> LLMTarget:
    return LLMTarget(profile="test", provider="synthetic", model="model-a")


def _deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=5)


def _messages() -> tuple[LLMMessage, ...]:
    return (LLMMessage(role=MessageRole.USER, content="synthetic input"),)


def _evidence() -> InvocationEvidence:
    now = datetime.now(timezone.utc)
    return InvocationEvidence(
        provenance=Provenance(
            invocation_id="invocation-1",
            requested_target=_target(),
            adapter=AdapterIdentity(name="fake", version="1"),
            started_at=now,
            finished_at=now,
        )
    )


def test_target_is_immutable() -> None:
    target = _target()

    with pytest.raises(ValidationError):
        target.model = "silently-rerouted"  # type: ignore[misc]


def test_capability_support_distinguishes_native_emulated_and_unknown() -> None:
    capabilities = CapabilitySet(
        target=_target(),
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport.EMULATED,
                source="local schema validation",
            ),
        ),
    )

    assert capabilities.support_for(CAPABILITY_TEXT_GENERATION) is CapabilitySupport.NATIVE
    assert capabilities.support_for("not_declared") is CapabilitySupport.UNKNOWN
    assert capabilities.unmet(
        [CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION)]
    ) == ((CAPABILITY_STRUCTURED_GENERATION, CapabilitySupport.EMULATED),)
    assert capabilities.unmet(
        [
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION, allow_emulated=True
            )
        ]
    ) == ()


def test_emulated_capability_must_identify_its_source() -> None:
    with pytest.raises(ValidationError):
        CapabilityDescriptor(
            name=CAPABILITY_STRUCTURED_GENERATION,
            support=CapabilitySupport.EMULATED,
        )


def test_unknown_usage_and_cost_are_not_encoded_as_zero() -> None:
    usage = TokenUsage.unavailable()
    cost = CostMeasurement.unavailable()

    assert usage.input_tokens is None
    assert usage.total_tokens is None
    assert cost.amount is None

    with pytest.raises(ValidationError):
        TokenUsage(status=MeasurementStatus.UNAVAILABLE, total_tokens=0)
    with pytest.raises(ValidationError):
        CostMeasurement(
            status=MeasurementStatus.UNAVAILABLE,
            amount=Decimal("0"),
            currency="USD",
        )

    reported_zero = TokenUsage(
        status=MeasurementStatus.REPORTED,
        input_tokens=0,
        source="synthetic provider report",
    )
    assert reported_zero.input_tokens == 0


def test_unknown_provenance_cannot_copy_the_requested_model() -> None:
    with pytest.raises(ValidationError):
        ProvenanceValue(value=_target().model, source=ProvenanceSource.UNKNOWN)


def test_generation_deadline_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            operation="test",
            target=_target(),
            messages=_messages(),
            deadline=datetime.now(),
        )


def test_modal_requests_always_require_their_explicit_capability() -> None:
    structured = StructuredGenerationRequest(
        operation="structured",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
        response_model=_StructuredAnswer,
    )
    streaming = StreamingGenerationRequest(
        operation="stream",
        target=_target(),
        messages=_messages(),
        deadline=_deadline(),
    )

    assert CAPABILITY_STRUCTURED_GENERATION in {
        requirement.name for requirement in structured.required_capabilities
    }
    assert CAPABILITY_STREAMING in {
        requirement.name for requirement in streaming.required_capabilities
    }

    with pytest.raises(ValidationError):
        StructuredGenerationRequest(
            operation="structured",
            target=_target(),
            messages=_messages(),
            deadline=_deadline(),
            response_model=_StructuredAnswer,
            required_capabilities=(
                CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            ),
        )


def test_stream_builder_and_validator_enforce_one_final_terminal() -> None:
    builder = StreamEventBuilder()
    events = [
        builder.delta("first"),
        builder.delta("second"),
        builder.complete(_evidence()),
    ]

    validate_stream_events(events)
    with pytest.raises(RuntimeError):
        builder.delta("too late")

    misordered = [events[0], events[1].model_copy(update={"sequence": 3}), events[2]]
    with pytest.raises(ValueError, match="contiguous"):
        validate_stream_events(misordered)
