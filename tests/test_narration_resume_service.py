import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from api.llm.contract import (
    ErrorCategory,
    GenerationRequest,
    LLMTarget,
    NormalizedError,
    OperationPhase,
    RateLimitEvidence,
    RateLimitOrigin,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
)
from api.narration_resume_service import (
    AvailabilityGatedGateway,
    NarratorGateBlockedError,
    PauseEligibility,
    applicable_gates_allow,
    can_dispatch_or_roll,
    classify_pause_eligibility,
    gate_from_error,
    normalize_gate_timing,
    scope_key_for_target,
    transition_narration_state,
    validate_resume_preconditions,
)
from api.turn_models import (
    NarrationResumeState,
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
)


NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
TARGET = LLMTarget(profile="narrator", provider="groq", model="fixed")


def error(
    category: ErrorCategory,
    *,
    retryable=True,
    partial=False,
    retry_after=None,
    origin: RateLimitOrigin | None = None,
):
    return NormalizedError.model_construct(
        category=category, code="bounded", phase=OperationPhase.RESPONSE,
        invocation_id="inv-1", target=TARGET, safe_message="safe", evidence=None,
        partial_output=partial, retryable=retryable,
        retry_after_seconds=retry_after,
        rate_limit=(RateLimitEvidence(origin=origin) if origin is not None else None),
    )


@pytest.mark.parametrize("category", [
    ErrorCategory.MODEL_UNAVAILABLE, ErrorCategory.PROVIDER_UNAVAILABLE,
    ErrorCategory.RATE_LIMITED, ErrorCategory.TRANSPORT_FAILURE, ErrorCategory.TIMEOUT,
])
def test_transient_retryable_errors_are_pause_eligible(category):
    assert classify_pause_eligibility(error(category)) is PauseEligibility.TRANSIENT


def test_partial_or_non_retryable_failure_is_not_transient():
    assert classify_pause_eligibility(error(ErrorCategory.TIMEOUT, partial=True)) is PauseEligibility.TERMINAL
    assert classify_pause_eligibility(error(ErrorCategory.TIMEOUT, retryable=False)) is PauseEligibility.TERMINAL


def test_timing_never_invents_cooldown():
    timing = normalize_gate_timing(error(ErrorCategory.TIMEOUT), server_now=NOW)
    assert timing.retry_not_before is None
    assert timing.confidence == "unknown"
    observed = normalize_gate_timing(
        error(ErrorCategory.TIMEOUT, retry_after=30), server_now=NOW,
    )
    assert observed.retry_not_before == NOW + timedelta(seconds=30)


def test_only_available_exact_target_allows_dispatch_or_roll():
    gate = NarratorAvailabilityGate(
        gate_id="gate-1", state=NarratorGateState.AVAILABLE,
        scope=NarratorGateScope.EXACT_TARGET, scope_key="opaque-1",
        target=TARGET.model_dump(mode="json"), observed_at=NOW,
    )
    assert can_dispatch_or_roll(gate, server_now=NOW, exact_target=TARGET.model_dump(mode="json"))
    assert not can_dispatch_or_roll(gate, server_now=NOW, exact_target={"model": "other"})


@pytest.mark.parametrize(
    ("origin", "scope", "evidence_scope"),
    (
        (RateLimitOrigin.GATEWAY, NarratorGateScope.GATEWAY_ACCOUNT, "gateway"),
        (RateLimitOrigin.UPSTREAM, NarratorGateScope.UPSTREAM_TARGET, "upstream"),
        (RateLimitOrigin.UNKNOWN, NarratorGateScope.UNKNOWN_CONSERVATIVE, "unknown"),
    ),
)
def test_rate_limit_origin_maps_to_the_smallest_enforcement_scope(
    origin, scope, evidence_scope,
):
    gate = gate_from_error(
        error(ErrorCategory.RATE_LIMITED, retry_after=30, origin=origin),
        server_now=NOW,
    )
    assert gate is not None
    assert gate.scope is scope
    assert gate.rate_limit_origin == origin.value
    assert gate.evidence_scope == evidence_scope
    assert gate.retry_not_before == NOW + timedelta(seconds=30)
    assert gate.scope_key == scope_key_for_target(scope, TARGET)


def test_hierarchical_gates_apply_only_to_their_proven_scope():
    other_model = LLMTarget(profile="narrator", provider="groq", model="other")
    other_provider = LLMTarget(profile="narrator", provider="other", model="fixed")
    gateway_gate = gate_from_error(
        error(ErrorCategory.RATE_LIMITED, origin=RateLimitOrigin.GATEWAY),
        server_now=NOW,
    )
    upstream_gate = gate_from_error(
        error(ErrorCategory.RATE_LIMITED, origin=RateLimitOrigin.UPSTREAM),
        server_now=NOW,
    )
    assert gateway_gate is not None and upstream_gate is not None
    assert not applicable_gates_allow(
        (gateway_gate,), server_now=NOW, exact_target=other_model,
    )
    assert applicable_gates_allow(
        (gateway_gate,), server_now=NOW, exact_target=other_provider,
    )
    assert applicable_gates_allow(
        (upstream_gate,), server_now=NOW, exact_target=other_model,
    )


def test_direct_resume_is_the_only_bypass_for_a_blocked_or_corrected_gate():
    gate = gate_from_error(
        error(ErrorCategory.CONFIGURATION_INVALID, retryable=False),
        server_now=NOW,
    )
    assert gate is not None
    assert not applicable_gates_allow((gate,), server_now=NOW, exact_target=TARGET)
    assert applicable_gates_allow(
        (gate,), server_now=NOW, exact_target=TARGET,
        direct_resume_operation_id="resume-after-config-fix",
    )


@pytest.mark.parametrize("method_name", ["generate_text", "generate_structured", "stream_text"])
def test_gateway_decorator_checks_the_local_gate_before_every_delegate_dispatch(method_name):
    class Delegate:
        calls = 0

        async def generate_text(self, request):
            self.calls += 1
            raise AssertionError("delegate must not be called")

        async def generate_structured(self, request):
            self.calls += 1
            raise AssertionError("delegate must not be called")

        async def stream_text(self, request):
            self.calls += 1
            raise AssertionError("delegate must not be called")
            yield

    delegate = Delegate()

    async def blocked(_operation, _target):
        raise NarratorGateBlockedError("blocked")

    async def unexpected(*_args):
        raise AssertionError("no outcome callback is expected")

    gateway = AvailabilityGatedGateway(
        delegate,
        before_dispatch=blocked,
        after_success=unexpected,
        after_failure=unexpected,
    )
    request_types = {
        "generate_text": GenerationRequest,
        "generate_structured": StructuredGenerationRequest,
        "stream_text": StreamingGenerationRequest,
    }
    request = request_types[method_name].model_construct(operation="stage", target=TARGET)

    async def invoke():
        result = getattr(gateway, method_name)(request)
        if method_name == "stream_text":
            async for _ in result:
                pass
        else:
            await result

    with pytest.raises(NarratorGateBlockedError):
        asyncio.run(invoke())
    assert delegate.calls == 0


def test_resume_requires_paused_matching_revision_target_and_time():
    validate_resume_preconditions(
        state=NarrationResumeState.PAUSED, capsule_revision=4,
        expected_revision=4, source_target={"model": "fixed"},
        requested_target={"model": "fixed"}, retry_not_before=None,
        server_now=NOW,
    )
    with pytest.raises(ValueError, match="stale"):
        validate_resume_preconditions(
            state=NarrationResumeState.PAUSED, capsule_revision=4,
            expected_revision=3, source_target={}, requested_target={},
            retry_not_before=None, server_now=NOW,
        )


def test_state_machine_is_single_flight_and_terminal():
    assert transition_narration_state(
        NarrationResumeState.PAUSED, NarrationResumeState.DIRECT_RESUME_TRIAL,
    ) is NarrationResumeState.DIRECT_RESUME_TRIAL
    with pytest.raises(ValueError):
        transition_narration_state(
            NarrationResumeState.COMPLETED, NarrationResumeState.PAUSED,
        )
