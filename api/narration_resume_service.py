"""Pure pause/resume policy. No transport, persistence, RNG or provider calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from .llm.contract import (
    ConnectionTestRequest,
    ErrorCategory,
    GenerationRequest,
    LLMGateway,
    LLMInvocationError,
    LLMTarget,
    NormalizedError,
    RateLimitOrigin,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
)
from .turn_models import (
    NarrationResumeState,
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
)


class PauseEligibility(str, Enum):
    TRANSIENT = "transient"
    CONFIGURATION_BLOCKED = "configuration_blocked"
    CORRECTION_REQUIRED = "correction_required"
    OUTPUT_FAILURE = "output_failure"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class GateTiming:
    server_now: datetime
    retry_not_before: datetime | None
    source: str
    confidence: str


class NarratorGateBlockedError(RuntimeError):
    """A local persisted gate refused a provider dispatch or a dice roll."""


def _opaque_key(*parts: str) -> str:
    encoded = json.dumps(parts, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def exact_target_scope_key(target: LLMTarget | dict[str, Any]) -> str:
    payload = target.model_dump(mode="json") if isinstance(target, LLMTarget) else target
    # Preserve the key emitted by the first implementation for existing saves.
    return hashlib.sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()


def scope_key_for_target(scope: NarratorGateScope, target: LLMTarget) -> str:
    if scope is NarratorGateScope.GATEWAY_ACCOUNT:
        return _opaque_key("gateway", target.provider)
    if scope is NarratorGateScope.UPSTREAM_TARGET:
        return _opaque_key("upstream", target.provider, target.model)
    if scope is NarratorGateScope.UNKNOWN_CONSERVATIVE:
        return _opaque_key("unknown", exact_target_scope_key(target))
    return exact_target_scope_key(target)


def gate_from_error(error: NormalizedError, *, server_now: datetime) -> NarratorAvailabilityGate | None:
    """Project only availability/configuration failures into a safe local gate."""

    eligibility = classify_pause_eligibility(error)
    if eligibility not in {PauseEligibility.TRANSIENT, PauseEligibility.CONFIGURATION_BLOCKED}:
        return None
    origin = (
        error.rate_limit.origin
        if error.category is ErrorCategory.RATE_LIMITED and error.rate_limit is not None
        else RateLimitOrigin.UNKNOWN
        if error.category is ErrorCategory.RATE_LIMITED
        else None
    )
    if origin is RateLimitOrigin.GATEWAY:
        scope = NarratorGateScope.GATEWAY_ACCOUNT
        evidence_scope = "gateway"
    elif origin is RateLimitOrigin.UPSTREAM:
        scope = NarratorGateScope.UPSTREAM_TARGET
        evidence_scope = "upstream"
    elif error.category is ErrorCategory.RATE_LIMITED:
        scope = NarratorGateScope.UNKNOWN_CONSERVATIVE
        evidence_scope = "unknown"
    else:
        scope = NarratorGateScope.EXACT_TARGET
        evidence_scope = "exact_target"
    timing = normalize_gate_timing(error, server_now=server_now)
    state = (
        NarratorGateState.CONFIGURATION_BLOCKED
        if eligibility is PauseEligibility.CONFIGURATION_BLOCKED
        else NarratorGateState.COOLDOWN
        if timing.retry_not_before is not None
        else NarratorGateState.UNAVAILABLE
    )
    key = scope_key_for_target(scope, error.target)
    return NarratorAvailabilityGate(
        gate_id=f"gate-{scope.value}-{key[:20]}",
        state=state,
        scope=scope,
        scope_key=key,
        target=error.target.model_dump(mode="json"),
        observed_at=timing.server_now,
        retry_not_before=timing.retry_not_before,
        evidence_scope=evidence_scope,
        timing_source=timing.source,
        timing_confidence=timing.confidence,
        rate_limit_origin=origin.value if origin is not None else None,
    )


def gate_is_applicable(gate: NarratorAvailabilityGate, target: LLMTarget) -> bool:
    return gate.scope_key == scope_key_for_target(gate.scope, target)


def applicable_gates_allow(
    gates: Iterable[NarratorAvailabilityGate],
    *,
    server_now: datetime,
    exact_target: LLMTarget,
    direct_resume_operation_id: str | None = None,
) -> bool:
    """Evaluate every applicable persisted scope without performing network I/O."""

    applicable = tuple(gate for gate in gates if gate_is_applicable(gate, exact_target))
    if not applicable:
        # Absence means no observed local block. UNKNOWN/STALE rows still fail closed.
        return True
    for gate in applicable:
        if gate.state is NarratorGateState.AVAILABLE:
            continue
        if (
            gate.state is NarratorGateState.DIRECT_RESUME_TRIAL
            and direct_resume_operation_id is not None
            and gate.lease_operation_id == direct_resume_operation_id
        ):
            continue
        if direct_resume_operation_id is not None and gate.state in {
            NarratorGateState.UNAVAILABLE,
            NarratorGateState.COOLDOWN,
            NarratorGateState.CONFIGURATION_BLOCKED,
        }:
            if (
                gate.state is NarratorGateState.CONFIGURATION_BLOCKED
                or gate.retry_not_before is None
                or server_now >= gate.retry_not_before
            ):
                continue
        return False
    return True


_TRANSIENT = {
    ErrorCategory.MODEL_UNAVAILABLE, ErrorCategory.PROVIDER_UNAVAILABLE,
    ErrorCategory.RATE_LIMITED, ErrorCategory.TRANSPORT_FAILURE, ErrorCategory.TIMEOUT,
}
_CONFIGURATION = {
    ErrorCategory.AUTHENTICATION_FAILED, ErrorCategory.PERMISSION_DENIED,
    ErrorCategory.PAYMENT_REQUIRED, ErrorCategory.QUOTA_EXCEEDED,
    ErrorCategory.CONFIGURATION_INVALID, ErrorCategory.UNSUPPORTED_CAPABILITY,
    ErrorCategory.TARGET_MISMATCH,
}
_CORRECTION = {
    ErrorCategory.INVALID_REQUEST, ErrorCategory.CONTENT_REJECTED,
    ErrorCategory.CONTEXT_LIMIT_EXCEEDED,
}
_OUTPUT = {ErrorCategory.INVALID_STRUCTURED_OUTPUT, ErrorCategory.MALFORMED_RESPONSE}


def classify_pause_eligibility(error: NormalizedError) -> PauseEligibility:
    if error.partial_output or error.category is ErrorCategory.CANCELLED:
        return PauseEligibility.TERMINAL
    if error.category in _TRANSIENT and error.retryable is True:
        return PauseEligibility.TRANSIENT
    if error.category in _CONFIGURATION:
        return PauseEligibility.CONFIGURATION_BLOCKED
    if error.category in _CORRECTION:
        return PauseEligibility.CORRECTION_REQUIRED
    if error.category in _OUTPUT:
        return PauseEligibility.OUTPUT_FAILURE
    return PauseEligibility.TERMINAL


def normalize_gate_timing(error: NormalizedError, *, server_now: datetime) -> GateTiming:
    if server_now.tzinfo is None or server_now.utcoffset() is None:
        raise ValueError("server_now must be timezone-aware")
    now = server_now.astimezone(timezone.utc)
    if error.retry_after_seconds is None:
        return GateTiming(now, None, "none", "unknown")
    return GateTiming(
        now, now + timedelta(seconds=error.retry_after_seconds),
        "normalized_error", "reported" if error.rate_limit is not None else "observed",
    )


def can_dispatch_or_roll(
    gate: NarratorAvailabilityGate | None, *, server_now: datetime, exact_target: object,
) -> bool:
    if gate is None:
        return True
    if gate.state is not NarratorGateState.AVAILABLE:
        return False
    if gate.target != exact_target:
        return False
    if gate.retry_not_before and server_now < gate.retry_not_before:
        return False
    return True


def validate_resume_preconditions(
    *, state: NarrationResumeState, capsule_revision: int, expected_revision: int,
    source_target: object, requested_target: object, retry_not_before: datetime | None,
    server_now: datetime,
) -> None:
    if state is not NarrationResumeState.PAUSED:
        raise ValueError("resume capsule is not paused")
    if capsule_revision != expected_revision:
        raise ValueError("resume capsule has a stale state revision")
    if source_target != requested_target:
        raise ValueError("resume target must match the frozen target")
    if retry_not_before is not None and server_now < retry_not_before:
        raise ValueError("resume is not eligible yet")


def transition_narration_state(
    current: NarrationResumeState, requested: NarrationResumeState,
) -> NarrationResumeState:
    allowed = {
        NarrationResumeState.PAUSED: {
            NarrationResumeState.DIRECT_RESUME_TRIAL, NarrationResumeState.ABANDONED,
        },
        NarrationResumeState.DIRECT_RESUME_TRIAL: {
            NarrationResumeState.PAUSED, NarrationResumeState.COMPLETED,
        },
    }
    if requested not in allowed.get(current, set()):
        raise ValueError(f"invalid narration transition: {current.value}->{requested.value}")
    return requested


def public_rate_limit_origin(error: NormalizedError) -> str | None:
    if error.category is not ErrorCategory.RATE_LIMITED:
        return None
    return (error.rate_limit.origin if error.rate_limit else RateLimitOrigin.UNKNOWN).value


BeforeDispatch = Callable[[str, LLMTarget], Awaitable[None]]
AfterSuccess = Callable[[LLMTarget], Awaitable[None]]
AfterFailure = Callable[[NormalizedError], Awaitable[None]]


class AvailabilityGatedGateway:
    """Decorator that applies the persisted gate to every real LLM dispatch."""

    def __init__(
        self,
        delegate: LLMGateway,
        *,
        before_dispatch: BeforeDispatch,
        after_success: AfterSuccess,
        after_failure: AfterFailure,
    ) -> None:
        self._delegate = delegate
        self._before_dispatch = before_dispatch
        self._after_success = after_success
        self._after_failure = after_failure

    def capabilities(self, target: LLMTarget):
        return self._delegate.capabilities(target)

    async def generate_text(self, request: GenerationRequest):
        await self._before_dispatch(request.operation, request.target)
        try:
            result = await self._delegate.generate_text(request)
        except LLMInvocationError as exc:
            await self._after_failure(exc.error)
            raise
        await self._after_success(request.target)
        return result

    async def generate_structured(self, request: StructuredGenerationRequest):
        await self._before_dispatch(request.operation, request.target)
        try:
            result = await self._delegate.generate_structured(request)
        except LLMInvocationError as exc:
            await self._after_failure(exc.error)
            raise
        await self._after_success(request.target)
        return result

    async def stream_text(self, request: StreamingGenerationRequest):
        await self._before_dispatch(request.operation, request.target)
        completed = False
        async for event in self._delegate.stream_text(request):
            if event.error is not None:
                await self._after_failure(event.error)
            elif event.is_terminal:
                completed = True
            yield event
        if completed:
            await self._after_success(request.target)

    async def test_connection(self, request: ConnectionTestRequest):
        # Diagnostics are a distinct explicit flow, not a campaign dispatch.
        return await self._delegate.test_connection(request)
