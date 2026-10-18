"""Provider-neutral, campaign-free readiness diagnostics for the LLM boundary.

Readiness is deliberately stronger than connectivity.  A configured target is
ready for the MVP only after it has completed the three operations the product
depends on: text generation, structured generation, and streaming.  Every
prompt in this module is fixed synthetic data; campaign state must never enter
these probes.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement,
    ConnectionTestRequest,
    ConnectionTestResult,
    ErrorCategory,
    GenerationParameters,
    InvocationEvidence,
    LLMGateway,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    NormalizedError,
    OperationPhase,
    StreamEvent,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    SYNTHETIC_PROBE_VERSION,
    validate_stream_events,
)


READINESS_DIAGNOSTIC_VERSION = "storyteller-llm-readiness-v1"
STRUCTURED_PROBE_OPERATION = "storyteller-llm-structured-probe-v1"
STRUCTURED_PROBE_PROMPT = (
    "Return only one JSON object whose status field is exactly "
    '"STORYTELLER_STRUCTURED_OK".'
)
STRUCTURED_PROBE_EXPECTED = "STORYTELLER_STRUCTURED_OK"
STREAMING_PROBE_OPERATION = "storyteller-llm-streaming-probe-v1"
STREAMING_PROBE_PROMPT = "Reply with exactly: STORYTELLER_STREAM_OK"
STREAMING_PROBE_EXPECTED = "STORYTELLER_STREAM_OK"


class ReadinessProbeName(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"
    STREAMING = "streaming"


class ReadinessProbeStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _StructuredProbePayload(_FrozenModel):
    status: Literal["STORYTELLER_STRUCTURED_OK"]


class ReadinessProbeResult(_FrozenModel):
    name: ReadinessProbeName
    status: ReadinessProbeStatus
    message: str = Field(min_length=1)
    evidence: InvocationEvidence | None = None
    error: NormalizedError | None = None

    @model_validator(mode="after")
    def fields_match_status(self) -> "ReadinessProbeResult":
        if self.status is ReadinessProbeStatus.PASSED:
            if self.evidence is None or self.error is not None:
                raise ValueError("passed probes require evidence and no error")
        elif self.status is ReadinessProbeStatus.SKIPPED:
            if self.evidence is not None or self.error is not None:
                raise ValueError("skipped probes cannot carry invocation evidence")
        elif self.error is not None and self.error.evidence != self.evidence:
            raise ValueError("failed probe error and evidence must match")
        return self


class ReadinessDiagnosticResult(_FrozenModel):
    version: str = READINESS_DIAGNOSTIC_VERSION
    target: LLMTarget
    success: bool
    message: str = Field(min_length=1)
    probes: tuple[ReadinessProbeResult, ...]
    # This preserves the endpoint's original ConnectionTestResult-shaped
    # top-level fields while the public diagnostic payload remains concise.
    connection_result: ConnectionTestResult | None = Field(
        default=None,
        exclude=True,
    )

    @model_validator(mode="after")
    def result_matches_probes(self) -> "ReadinessDiagnosticResult":
        expected_names = tuple(ReadinessProbeName)
        if tuple(probe.name for probe in self.probes) != expected_names:
            raise ValueError("readiness probes must be ordered text, structured, streaming")
        all_passed = all(
            probe.status is ReadinessProbeStatus.PASSED for probe in self.probes
        )
        if self.success != all_passed:
            raise ValueError("readiness succeeds only when every probe passes")
        if self.connection_result is not None:
            if self.connection_result.target != self.target:
                raise ValueError("connection result must use the diagnosed target")
            if self.connection_result.success != self.success:
                raise ValueError("connection result and readiness must agree")
        return self


def _skipped(name: ReadinessProbeName, reason: str) -> ReadinessProbeResult:
    return ReadinessProbeResult(
        name=name,
        status=ReadinessProbeStatus.SKIPPED,
        message=reason,
    )


def _passed(
    name: ReadinessProbeName,
    evidence: InvocationEvidence,
) -> ReadinessProbeResult:
    return ReadinessProbeResult(
        name=name,
        status=ReadinessProbeStatus.PASSED,
        message=f"Synthetic {name.value} probe passed.",
        evidence=evidence,
    )


def _failed(
    name: ReadinessProbeName,
    message: str,
    *,
    error: NormalizedError | None = None,
) -> ReadinessProbeResult:
    return ReadinessProbeResult(
        name=name,
        status=ReadinessProbeStatus.FAILED,
        message=message,
        evidence=error.evidence if error is not None else None,
        error=error,
    )


def _normalized_diagnostic_error(
    *,
    evidence: InvocationEvidence,
    category: ErrorCategory,
    code: str,
    phase: OperationPhase,
    safe_message: str,
) -> NormalizedError:
    provenance = evidence.provenance
    return NormalizedError(
        category=category,
        code=code,
        phase=phase,
        invocation_id=provenance.invocation_id,
        target=provenance.requested_target,
        safe_message=safe_message,
        evidence=evidence,
        retryable=False,
    )


def _evidence_matches_request(
    evidence: InvocationEvidence | None,
    request: ConnectionTestRequest
    | StructuredGenerationRequest
    | StreamingGenerationRequest,
) -> bool:
    """Trust evidence only when it identifies this exact invocation and target."""

    if not isinstance(evidence, InvocationEvidence):
        return False
    provenance = evidence.provenance
    return (
        provenance.requested_target == request.target
        and provenance.invocation_id == request.invocation_id
    )


def _failed_connection_result(
    target: LLMTarget,
    error: NormalizedError,
) -> ConnectionTestResult:
    return ConnectionTestResult(
        probe_version=SYNTHETIC_PROBE_VERSION,
        success=False,
        target=target,
        evidence=error.evidence,
        error=error,
    )


def _diagnostic_result(
    *,
    target: LLMTarget,
    probes: tuple[ReadinessProbeResult, ...],
    message: str,
    connection_result: ConnectionTestResult | None,
) -> ReadinessDiagnosticResult:
    return ReadinessDiagnosticResult(
        target=target,
        success=all(
            probe.status is ReadinessProbeStatus.PASSED for probe in probes
        ),
        message=message,
        probes=probes,
        connection_result=connection_result,
    )


async def run_readiness_diagnostics(
    gateway: LLMGateway,
    request: ConnectionTestRequest,
) -> ReadinessDiagnosticResult:
    """Exercise the MVP operations with fixed synthetic, campaign-free inputs.

    The probes are sequential on purpose.  A failure skips every later probe so
    an invalid target does not consume additional remote quota.
    """

    requirements = (
        CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
        CapabilityRequirement(
            name=CAPABILITY_STRUCTURED_GENERATION,
            allow_emulated=True,
        ),
        CapabilityRequirement(name=CAPABILITY_STREAMING),
    )
    capabilities = gateway.capabilities(request.target)
    if capabilities.target != request.target:
        message = "The LLM adapter declared capabilities for another target."
        return _diagnostic_result(
            target=request.target,
            probes=tuple(_skipped(name, message) for name in ReadinessProbeName),
            message=message,
            connection_result=None,
        )
    unmet = capabilities.unmet(requirements)
    if unmet:
        missing = ", ".join(f"{name}={support.value}" for name, support in unmet)
        message = f"Required MVP capabilities are unavailable: {missing}."
        return _diagnostic_result(
            target=request.target,
            probes=tuple(_skipped(name, message) for name in ReadinessProbeName),
            message=message,
            connection_result=None,
        )

    try:
        text_result = await gateway.test_connection(request)
    except Exception:
        # A provider adapter must normalize its own failures.  Keep this
        # defensive path secret-safe and do not reflect exception text.
        message = "The synthetic text probe failed inside the LLM adapter."
        return _diagnostic_result(
            target=request.target,
            probes=(
                _failed(ReadinessProbeName.TEXT, message),
                _skipped(ReadinessProbeName.STRUCTURED, message),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )

    if (
        text_result.target != request.target
        or not _evidence_matches_request(text_result.evidence, request)
    ):
        message = "The synthetic text probe returned incompatible invocation evidence."
        return _diagnostic_result(
            target=request.target,
            probes=(
                _failed(ReadinessProbeName.TEXT, message),
                _skipped(ReadinessProbeName.STRUCTURED, message),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )

    if not text_result.success:
        message = "The synthetic text probe failed; later probes were skipped."
        return _diagnostic_result(
            target=request.target,
            probes=(
                _failed(
                    ReadinessProbeName.TEXT,
                    "Synthetic text probe failed.",
                    error=text_result.error,
                ),
                _skipped(ReadinessProbeName.STRUCTURED, message),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=text_result,
        )

    text_probe = _passed(ReadinessProbeName.TEXT, text_result.evidence)
    structured_request = StructuredGenerationRequest(
        operation=STRUCTURED_PROBE_OPERATION,
        target=request.target,
        messages=(
            LLMMessage(role=MessageRole.USER, content=STRUCTURED_PROBE_PROMPT),
        ),
        deadline=request.deadline,
        cancellation=request.cancellation,
        parameters=GenerationParameters(temperature=0.0, max_output_tokens=32),
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
        response_model=_StructuredProbePayload,
    )

    try:
        structured_result = await gateway.generate_structured(structured_request)
    except LLMInvocationError as exc:
        if not _evidence_matches_request(exc.error.evidence, structured_request):
            message = (
                "The structured readiness probe returned incompatible "
                "invocation evidence."
            )
            return _diagnostic_result(
                target=request.target,
                probes=(
                    text_probe,
                    _failed(ReadinessProbeName.STRUCTURED, message),
                    _skipped(ReadinessProbeName.STREAMING, message),
                ),
                message=message,
                connection_result=None,
            )
        message = "The synthetic structured-output probe failed."
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                _failed(ReadinessProbeName.STRUCTURED, message, error=exc.error),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=_failed_connection_result(request.target, exc.error),
        )
    except Exception:
        # There is no trustworthy evidence for a call whose adapter escaped
        # the normalized-error contract.  Do not attach the preceding text
        # probe's provenance to this failure.
        message = "The structured readiness probe failed inside the LLM adapter."
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                _failed(ReadinessProbeName.STRUCTURED, message),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )

    if not _evidence_matches_request(structured_result.evidence, structured_request):
        message = (
            "The structured readiness probe returned incompatible invocation evidence."
        )
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                _failed(ReadinessProbeName.STRUCTURED, message),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )

    payload = structured_result.value
    if (
        not isinstance(payload, _StructuredProbePayload)
        or payload.status != STRUCTURED_PROBE_EXPECTED
    ):
        error = _normalized_diagnostic_error(
            evidence=structured_result.evidence,
            category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
            code="readiness_structured_content_mismatch",
            phase=OperationPhase.STRUCTURE_VALIDATION,
            safe_message="The structured readiness probe returned an unexpected payload.",
        )
        message = error.safe_message
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                _failed(ReadinessProbeName.STRUCTURED, message, error=error),
                _skipped(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=_failed_connection_result(request.target, error),
        )

    structured_probe = _passed(
        ReadinessProbeName.STRUCTURED,
        structured_result.evidence,
    )
    streaming_request = StreamingGenerationRequest(
        operation=STREAMING_PROBE_OPERATION,
        target=request.target,
        messages=(
            LLMMessage(role=MessageRole.USER, content=STREAMING_PROBE_PROMPT),
        ),
        deadline=request.deadline,
        cancellation=request.cancellation,
        parameters=GenerationParameters(temperature=0.0, max_output_tokens=32),
    )
    events: list[StreamEvent] = []
    try:
        async for event in gateway.stream_text(streaming_request):
            events.append(event)
    except LLMInvocationError as exc:
        if not _evidence_matches_request(exc.error.evidence, streaming_request):
            message = (
                "The streaming readiness probe returned incompatible "
                "invocation evidence."
            )
            return _diagnostic_result(
                target=request.target,
                probes=(
                    text_probe,
                    structured_probe,
                    _failed(ReadinessProbeName.STREAMING, message),
                ),
                message=message,
                connection_result=None,
            )
        message = "The synthetic streaming probe failed."
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(ReadinessProbeName.STREAMING, message, error=exc.error),
            ),
            message=message,
            connection_result=_failed_connection_result(request.target, exc.error),
        )
    except Exception:
        # As above, a non-normalized adapter exception has no evidence that can
        # safely be attributed to this streaming invocation.
        message = "The streaming readiness probe failed inside the LLM adapter."
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )

    try:
        validate_stream_events(events)
    except ValueError:
        terminal_evidence = next(
            (
                event.evidence
                for event in reversed(events)
                if event.evidence is not None
            ),
            None,
        )
        if terminal_evidence is None:
            message = "The streaming readiness probe violated the stream contract."
            return _diagnostic_result(
                target=request.target,
                probes=(
                    text_probe,
                    structured_probe,
                    _failed(ReadinessProbeName.STREAMING, message),
                ),
                message=message,
                connection_result=None,
            )
        if not _evidence_matches_request(terminal_evidence, streaming_request):
            message = (
                "The streaming readiness probe returned incompatible "
                "invocation evidence."
            )
            return _diagnostic_result(
                target=request.target,
                probes=(
                    text_probe,
                    structured_probe,
                    _failed(ReadinessProbeName.STREAMING, message),
                ),
                message=message,
                connection_result=None,
            )
        error = _normalized_diagnostic_error(
            evidence=terminal_evidence,
            category=ErrorCategory.MALFORMED_RESPONSE,
            code="readiness_stream_protocol_invalid",
            phase=OperationPhase.STREAM,
            safe_message="The streaming readiness probe violated the stream contract.",
        )
        message = error.safe_message
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(ReadinessProbeName.STREAMING, message, error=error),
            ),
            message=message,
            connection_result=_failed_connection_result(request.target, error),
        )

    terminal = events[-1]
    terminal_evidence = terminal.evidence
    if not _evidence_matches_request(terminal_evidence, streaming_request):
        message = (
            "The streaming readiness probe returned incompatible invocation evidence."
        )
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(ReadinessProbeName.STREAMING, message),
            ),
            message=message,
            connection_result=None,
        )
    if terminal.kind is not StreamEventKind.COMPLETED:
        assert terminal.error is not None
        message = "The synthetic streaming probe returned a failure terminal."
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(
                    ReadinessProbeName.STREAMING,
                    message,
                    error=terminal.error,
                ),
            ),
            message=message,
            connection_result=_failed_connection_result(
                request.target,
                terminal.error,
            ),
        )

    streamed_content = "".join(
        event.delta or "" for event in events if event.kind is StreamEventKind.DELTA
    ).strip()
    if streamed_content != STREAMING_PROBE_EXPECTED:
        assert terminal_evidence is not None
        error = _normalized_diagnostic_error(
            evidence=terminal_evidence,
            category=ErrorCategory.MALFORMED_RESPONSE,
            code="readiness_stream_content_mismatch",
            phase=OperationPhase.STREAM,
            safe_message="The streaming readiness probe returned unexpected content.",
        )
        message = error.safe_message
        return _diagnostic_result(
            target=request.target,
            probes=(
                text_probe,
                structured_probe,
                _failed(ReadinessProbeName.STREAMING, message, error=error),
            ),
            message=message,
            connection_result=_failed_connection_result(request.target, error),
        )

    assert terminal_evidence is not None
    probes = (
        text_probe,
        structured_probe,
        _passed(ReadinessProbeName.STREAMING, terminal_evidence),
    )
    return _diagnostic_result(
        target=request.target,
        probes=probes,
        message="All required synthetic LLM readiness probes passed.",
        connection_result=text_result,
    )


__all__ = [
    "READINESS_DIAGNOSTIC_VERSION",
    "STREAMING_PROBE_EXPECTED",
    "STREAMING_PROBE_OPERATION",
    "STREAMING_PROBE_PROMPT",
    "STRUCTURED_PROBE_EXPECTED",
    "STRUCTURED_PROBE_OPERATION",
    "STRUCTURED_PROBE_PROMPT",
    "ReadinessDiagnosticResult",
    "ReadinessProbeName",
    "ReadinessProbeResult",
    "ReadinessProbeStatus",
    "run_readiness_diagnostics",
]
