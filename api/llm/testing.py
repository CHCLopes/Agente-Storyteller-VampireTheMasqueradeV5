"""Deterministic, network-free adapter used by the LLM conformance suite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

from pydantic import ValidationError

from .contract import (
    AdapterIdentity,
    CapabilitySet,
    ConnectionTestRequest,
    ConnectionTestResult,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    InvocationEvidence,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceValue,
    StreamEvent,
    StreamEventBuilder,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    StructuredGenerationResult,
    SYNTHETIC_PROBE_PROMPT,
    SYNTHETIC_PROBE_VERSION,
    TextGenerationResult,
    TokenUsage,
    seconds_until,
    utc_now,
)


class FakeLLMAdapter:
    """Scriptable adapter whose calls are explicit and observable."""

    def __init__(
        self,
        *,
        capability_set: CapabilitySet,
        text: str = "synthetic response",
        structured_payload: object | None = None,
        stream_deltas: tuple[str, ...] = ("synthetic ", "response"),
        usage: TokenUsage | None = None,
        cost: CostMeasurement | None = None,
        effective_provider: str | None = None,
        effective_model: str | None = None,
        failure_category: ErrorCategory | None = None,
        fail_after_deltas: int | None = None,
        step_delay_seconds: float = 0.0,
    ) -> None:
        self._capability_set = capability_set
        self.text = text
        self.structured_payload = structured_payload
        self.stream_deltas = stream_deltas
        self.usage = usage or TokenUsage.unavailable()
        self.cost = cost or CostMeasurement.unavailable()
        self.effective_provider = effective_provider
        self.effective_model = effective_model
        if fail_after_deltas is not None and fail_after_deltas < 0:
            raise ValueError("fail_after_deltas must be non-negative")
        if fail_after_deltas is not None and failure_category is None:
            raise ValueError("fail_after_deltas requires a failure_category")
        self.failure_category = failure_category
        self.fail_after_deltas = fail_after_deltas
        self.step_delay_seconds = step_delay_seconds
        self.requests: list[GenerationRequest] = []
        self.external_call_count = 0
        self._identity = AdapterIdentity(name="deterministic-fake", version="1.0")

    def capabilities(self, target: LLMTarget) -> CapabilitySet:
        if target == self._capability_set.target:
            return self._capability_set
        return CapabilitySet(target=target, descriptors=())

    async def generate_text(self, request: GenerationRequest) -> TextGenerationResult:
        started_at = utc_now()
        self._validate(request, started_at)
        self._record(request)
        await self._step(request, started_at)
        self._raise_scripted_failure(request, started_at)
        evidence = self._evidence(request, started_at)
        self._raise_target_mismatch(request, evidence)
        return TextGenerationResult(content=self.text, evidence=evidence)

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        started_at = utc_now()
        self._validate(request, started_at)
        self._record(request)
        await self._step(request, started_at)
        self._raise_scripted_failure(request, started_at)
        evidence = self._evidence(request, started_at)
        self._raise_target_mismatch(request, evidence)
        validation_error: NormalizedError | None = None
        try:
            value = request.response_model.model_validate(self.structured_payload)
        except (ValidationError, TypeError, ValueError):
            validation_error = self._error(
                request,
                evidence,
                ErrorCategory.INVALID_STRUCTURED_OUTPUT,
                "structured_output_schema_mismatch",
                OperationPhase.STRUCTURE_VALIDATION,
                "LLM output did not match the requested product schema.",
            )
        if validation_error is not None:
            raise LLMInvocationError(validation_error)
        self._ensure_active(request, evidence, OperationPhase.STRUCTURE_VALIDATION)
        return StructuredGenerationResult(value=value, evidence=evidence)

    async def stream_text(
        self, request: StreamingGenerationRequest
    ) -> AsyncIterator[StreamEvent]:
        builder = StreamEventBuilder()
        started_at = utc_now()
        emitted = False
        try:
            self._validate(request, started_at)
            self._record(request)
            if self.fail_after_deltas is None:
                self._raise_scripted_failure(request, started_at)
            emitted_count = 0
            for delta in self.stream_deltas:
                if (
                    self.fail_after_deltas is not None
                    and emitted_count >= self.fail_after_deltas
                ):
                    self._raise_scripted_failure(request, started_at)
                await self._step(request, started_at)
                if delta:
                    emitted = True
                    emitted_count += 1
                    yield builder.delta(delta)
            evidence = self._evidence(request, started_at)
            self._ensure_active(request, evidence, OperationPhase.STREAM)
            self._raise_target_mismatch(request, evidence)
            yield builder.complete(evidence)
        except LLMInvocationError as exc:
            if exc.error.category is ErrorCategory.CANCELLED:
                kind = StreamEventKind.CANCELLED
            elif exc.error.category is ErrorCategory.TIMEOUT:
                kind = StreamEventKind.TIMED_OUT
            else:
                kind = StreamEventKind.FAILED
            error = exc.error.model_copy(update={"partial_output": emitted})
            yield builder.fail(kind, error, partial_output=emitted)

    async def test_connection(
        self, request: ConnectionTestRequest
    ) -> ConnectionTestResult:
        probe_request = GenerationRequest(
            invocation_id=request.invocation_id,
            operation=SYNTHETIC_PROBE_VERSION,
            target=request.target,
            messages=(
                LLMMessage(role=MessageRole.USER, content=SYNTHETIC_PROBE_PROMPT),
            ),
            deadline=request.deadline,
            cancellation=request.cancellation,
        )
        try:
            started_at = utc_now()
            self._validate(probe_request, started_at)
            self._record(probe_request)
            await self._step(probe_request, started_at)
            self._raise_scripted_failure(probe_request, started_at)
            evidence = self._evidence(probe_request, started_at)
            self._ensure_active(probe_request, evidence, OperationPhase.RESPONSE)
            self._raise_target_mismatch(probe_request, evidence)
            return ConnectionTestResult(
                probe_version=SYNTHETIC_PROBE_VERSION,
                success=True,
                target=request.target,
                evidence=evidence,
            )
        except LLMInvocationError as exc:
            return ConnectionTestResult(
                probe_version=SYNTHETIC_PROBE_VERSION,
                success=False,
                target=request.target,
                evidence=exc.error.evidence,
                error=exc.error,
            )

    def _record(self, request: GenerationRequest) -> None:
        self.requests.append(request)
        self.external_call_count += 1

    async def _step(self, request: GenerationRequest, started_at: datetime) -> None:
        if self.step_delay_seconds:
            await asyncio.sleep(self.step_delay_seconds)
        if request.cancellation.is_cancelled:
            evidence = self._evidence(request, started_at)
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.CANCELLED,
                    "operation_cancelled",
                    OperationPhase.CANCELLATION,
                    "LLM operation was cancelled.",
                )
            )
        if seconds_until(request.deadline) <= 0:
            evidence = self._evidence(request, started_at)
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.TIMEOUT,
                    "operation_deadline_exceeded",
                    OperationPhase.RESPONSE,
                    "LLM operation exceeded its deadline.",
                )
            )

    def _validate(self, request: GenerationRequest, started_at: datetime) -> None:
        evidence = self._evidence(request, started_at)
        if request.target != self._capability_set.target:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.CONFIGURATION_INVALID,
                    "adapter_target_not_bound",
                    OperationPhase.VALIDATION,
                    "The adapter is not bound to the requested LLM target.",
                )
            )
        if request.cancellation.is_cancelled:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.CANCELLED,
                    "operation_cancelled",
                    OperationPhase.CANCELLATION,
                    "LLM operation was cancelled.",
                )
            )
        if seconds_until(request.deadline) <= 0:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.TIMEOUT,
                    "operation_deadline_exceeded",
                    OperationPhase.VALIDATION,
                    "LLM operation exceeded its deadline.",
                )
            )
        unmet = self._capability_set.unmet(request.required_capabilities)
        if unmet:
            name, support = unmet[0]
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.UNSUPPORTED_CAPABILITY,
                    f"capability_{name}_{support.value}",
                    OperationPhase.VALIDATION,
                    f"Required LLM capability '{name}' is not available.",
                )
            )

    def _raise_scripted_failure(
        self, request: GenerationRequest, started_at: datetime
    ) -> None:
        if self.failure_category is None:
            return
        evidence = self._evidence(request, started_at)
        raise LLMInvocationError(
            self._error(
                request,
                evidence,
                self.failure_category,
                "scripted_failure",
                OperationPhase.RESPONSE,
                "Synthetic adapter returned its configured failure.",
            )
        )

    def _raise_target_mismatch(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        reported = evidence.provenance.effective_model.value
        if reported and reported != request.target.model:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.TARGET_MISMATCH,
                    "reported_model_mismatch",
                    OperationPhase.RESPONSE,
                    "LLM target reported a different model than requested.",
                )
            )

    def _ensure_active(
        self,
        request: GenerationRequest,
        evidence: InvocationEvidence,
        phase: OperationPhase,
    ) -> None:
        if request.cancellation.is_cancelled:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.CANCELLED,
                    "operation_cancelled",
                    OperationPhase.CANCELLATION,
                    "LLM operation was cancelled.",
                )
            )
        if seconds_until(request.deadline) <= 0:
            raise LLMInvocationError(
                self._error(
                    request,
                    evidence,
                    ErrorCategory.TIMEOUT,
                    "operation_deadline_exceeded",
                    phase,
                    "LLM operation exceeded its deadline.",
                )
            )

    def _evidence(
        self, request: GenerationRequest, started_at: datetime
    ) -> InvocationEvidence:
        return InvocationEvidence(
            provenance=Provenance(
                invocation_id=request.invocation_id,
                requested_target=request.target,
                adapter=self._identity,
                effective_provider=(
                    ProvenanceValue.reported(self.effective_provider)
                    if self.effective_provider
                    else ProvenanceValue.unknown()
                ),
                effective_model=(
                    ProvenanceValue.reported(self.effective_model)
                    if self.effective_model
                    else ProvenanceValue.unknown()
                ),
                started_at=started_at,
                finished_at=utc_now(),
            ),
            usage=self.usage,
            cost=self.cost,
        )

    @staticmethod
    def _error(
        request: GenerationRequest,
        evidence: InvocationEvidence,
        category: ErrorCategory,
        code: str,
        phase: OperationPhase,
        safe_message: str,
    ) -> NormalizedError:
        return NormalizedError(
            category=category,
            code=code,
            phase=phase,
            invocation_id=request.invocation_id,
            target=request.target,
            safe_message=safe_message,
            evidence=evidence,
        )
