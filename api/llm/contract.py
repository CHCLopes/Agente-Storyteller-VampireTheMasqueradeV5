"""Stable, provider-neutral contract for all LLM interactions.

This module deliberately contains no transport or provider SDK imports.  It
defines the product-owned vocabulary exchanged with adapters and the
invariants that every adapter must preserve.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import (
    BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator,
)


CAPABILITY_TEXT_GENERATION = "text_generation"
CAPABILITY_STRUCTURED_GENERATION = "structured_generation"
CAPABILITY_STREAMING = "streaming"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)


class CapabilitySupport(str, Enum):
    """How a target supplies a capability; emulation is never called native."""

    NATIVE = "native"
    EMULATED = "emulated"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class MeasurementStatus(str, Enum):
    REPORTED = "reported"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class ProvenanceSource(str, Enum):
    REPORTED = "reported"
    OBSERVED = "observed"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ErrorCategory(str, Enum):
    INVALID_REQUEST = "invalid_request"
    CONFIGURATION_INVALID = "configuration_invalid"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    PAYMENT_REQUIRED = "payment_required"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    CONTENT_REJECTED = "content_rejected"
    CONTEXT_LIMIT_EXCEEDED = "context_limit_exceeded"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    TRANSPORT_FAILURE = "transport_failure"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"
    MALFORMED_RESPONSE = "malformed_response"
    TARGET_MISMATCH = "target_mismatch"
    ADAPTER_FAILURE = "adapter_failure"
    UNKNOWN = "unknown"


class RateLimitOrigin(str, Enum):
    """Where a rate limit was observed without exposing provider internals."""

    GATEWAY = "gateway"
    UPSTREAM = "upstream"
    UNKNOWN = "unknown"


class OperationPhase(str, Enum):
    VALIDATION = "validation"
    DISPATCH = "dispatch"
    CONNECT = "connect"
    RESPONSE = "response"
    STREAM = "stream"
    STRUCTURE_VALIDATION = "structure_validation"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class StreamEventKind(str, Enum):
    DELTA = "delta"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class InvocationStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def _require_non_blank(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("value must not be blank")
    return cleaned


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone information")
    return value


class LLMTarget(_FrozenModel):
    """The exact requested target.  Frozen fields prevent in-flight rerouting."""

    profile: str
    provider: str
    model: str

    _profile_non_blank = field_validator("profile")(_require_non_blank)
    _provider_non_blank = field_validator("provider")(_require_non_blank)
    _model_non_blank = field_validator("model")(_require_non_blank)


class CapabilityDescriptor(_FrozenModel):
    name: str
    support: CapabilitySupport = CapabilitySupport.UNKNOWN
    constraints: tuple[str, ...] = ()
    source: str | None = None

    _name_non_blank = field_validator("name")(_require_non_blank)

    @model_validator(mode="after")
    def validate_source(self) -> "CapabilityDescriptor":
        if self.support is CapabilitySupport.EMULATED and not self.source:
            raise ValueError("emulated capability must identify its source")
        return self


class CapabilityRequirement(_FrozenModel):
    name: str
    allow_emulated: bool = False

    _name_non_blank = field_validator("name")(_require_non_blank)


class CapabilitySet(_FrozenModel):
    target: LLMTarget
    descriptors: tuple[CapabilityDescriptor, ...]

    @model_validator(mode="after")
    def descriptor_names_are_unique(self) -> "CapabilitySet":
        names = [descriptor.name for descriptor in self.descriptors]
        if len(names) != len(set(names)):
            raise ValueError("capability names must be unique")
        return self

    def support_for(self, name: str) -> CapabilitySupport:
        for descriptor in self.descriptors:
            if descriptor.name == name:
                return descriptor.support
        return CapabilitySupport.UNKNOWN

    def unmet(
        self, requirements: Sequence[CapabilityRequirement]
    ) -> tuple[tuple[str, CapabilitySupport], ...]:
        failures: list[tuple[str, CapabilitySupport]] = []
        for requirement in requirements:
            support = self.support_for(requirement.name)
            accepted = support is CapabilitySupport.NATIVE or (
                support is CapabilitySupport.EMULATED and requirement.allow_emulated
            )
            if not accepted:
                failures.append((requirement.name, support))
        return tuple(failures)


class CancellationToken:
    """Cooperative cancellation signal that is intentionally not serializable."""

    __slots__ = ("_event", "_reason")

    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str | None:
        return self._reason

    def cancel(self, reason: str = "cancelled by caller") -> None:
        if not self._event.is_set():
            self._reason = reason
            self._event.set()

    async def wait(self) -> None:
        await self._event.wait()

    def __repr__(self) -> str:
        return f"CancellationToken(cancelled={self.is_cancelled})"


class LLMMessage(_FrozenModel):
    role: MessageRole
    content: str = Field(min_length=1)


class GenerationParameters(_FrozenModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    seed: int | None = None


def _text_requirements() -> tuple[CapabilityRequirement, ...]:
    return (CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),)


def _structured_requirements() -> tuple[CapabilityRequirement, ...]:
    return (
        CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
        CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION),
    )


def _stream_requirements() -> tuple[CapabilityRequirement, ...]:
    return (
        CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
        CapabilityRequirement(name=CAPABILITY_STREAMING),
    )


class GenerationRequest(_FrozenModel):
    invocation_id: str = Field(default_factory=lambda: str(uuid4()))
    operation: str
    target: LLMTarget
    messages: tuple[LLMMessage, ...] = Field(min_length=1)
    deadline: datetime
    cancellation: CancellationToken = Field(default_factory=CancellationToken, exclude=True)
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    required_capabilities: tuple[CapabilityRequirement, ...] = Field(
        default_factory=_text_requirements
    )

    _operation_non_blank = field_validator("operation")(_require_non_blank)
    _invocation_non_blank = field_validator("invocation_id")(_require_non_blank)
    _deadline_aware = field_validator("deadline")(_require_aware)

    @model_validator(mode="after")
    def capability_requirements_are_unique(self) -> "GenerationRequest":
        names = [requirement.name for requirement in self.required_capabilities]
        if len(names) != len(set(names)):
            raise ValueError("required capability names must be unique")
        if CAPABILITY_TEXT_GENERATION not in names:
            raise ValueError("all generation requests require text_generation")
        return self


class StructuredGenerationRequest(GenerationRequest):
    response_model: type[BaseModel]
    required_capabilities: tuple[CapabilityRequirement, ...] = Field(
        default_factory=_structured_requirements
    )

    @model_validator(mode="after")
    def structured_capability_is_explicit(self) -> "StructuredGenerationRequest":
        if CAPABILITY_STRUCTURED_GENERATION not in {
            requirement.name for requirement in self.required_capabilities
        }:
            raise ValueError("structured requests require structured_generation")
        return self


class StreamingGenerationRequest(GenerationRequest):
    required_capabilities: tuple[CapabilityRequirement, ...] = Field(
        default_factory=_stream_requirements
    )

    @model_validator(mode="after")
    def streaming_capability_is_explicit(self) -> "StreamingGenerationRequest":
        if CAPABILITY_STREAMING not in {
            requirement.name for requirement in self.required_capabilities
        }:
            raise ValueError("streaming requests require streaming")
        return self


class AdapterIdentity(_FrozenModel):
    name: str
    version: str

    _name_non_blank = field_validator("name")(_require_non_blank)
    _version_non_blank = field_validator("version")(_require_non_blank)


class ProvenanceValue(_FrozenModel):
    value: str | None = None
    source: ProvenanceSource = ProvenanceSource.UNKNOWN

    @field_validator("value")
    @classmethod
    def normalize_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_blank(value)

    @model_validator(mode="after")
    def source_matches_value(self) -> "ProvenanceValue":
        if self.source is ProvenanceSource.UNKNOWN and self.value is not None:
            raise ValueError("unknown provenance must not contain an inferred value")
        if self.source is not ProvenanceSource.UNKNOWN and not self.value:
            raise ValueError("reported or observed provenance requires a value")
        return self

    @classmethod
    def unknown(cls) -> "ProvenanceValue":
        return cls()

    @classmethod
    def reported(cls, value: str) -> "ProvenanceValue":
        return cls(value=value, source=ProvenanceSource.REPORTED)

    @classmethod
    def observed(cls, value: str) -> "ProvenanceValue":
        return cls(value=value, source=ProvenanceSource.OBSERVED)


class Provenance(_FrozenModel):
    invocation_id: str
    requested_target: LLMTarget
    adapter: AdapterIdentity
    effective_provider: ProvenanceValue = Field(default_factory=ProvenanceValue.unknown)
    effective_model: ProvenanceValue = Field(default_factory=ProvenanceValue.unknown)
    started_at: datetime
    finished_at: datetime

    _invocation_non_blank = field_validator("invocation_id")(_require_non_blank)
    _started_aware = field_validator("started_at")(_require_aware)
    _finished_aware = field_validator("finished_at")(_require_aware)

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> "Provenance":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


class TokenUsage(_FrozenModel):
    status: MeasurementStatus = MeasurementStatus.UNAVAILABLE
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    source: str | None = None

    @model_validator(mode="after")
    def status_matches_values(self) -> "TokenUsage":
        values = (self.input_tokens, self.output_tokens, self.total_tokens)
        if self.status is MeasurementStatus.UNAVAILABLE:
            if any(value is not None for value in values) or self.source is not None:
                raise ValueError("unavailable usage must remain unknown, never zero")
        elif all(value is None for value in values) or not self.source:
            raise ValueError("reported or estimated usage requires values and source")
        return self

    @classmethod
    def unavailable(cls) -> "TokenUsage":
        return cls()


class CostMeasurement(_FrozenModel):
    status: MeasurementStatus = MeasurementStatus.UNAVAILABLE
    amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency: str | None = None
    source: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @model_validator(mode="after")
    def status_matches_value(self) -> "CostMeasurement":
        if self.status is MeasurementStatus.UNAVAILABLE:
            if self.amount is not None or self.currency is not None or self.source is not None:
                raise ValueError("unavailable cost must remain unknown, never zero")
        elif self.amount is None or not self.currency or not self.source:
            raise ValueError("reported or estimated cost requires amount, currency and source")
        return self

    @classmethod
    def unavailable(cls) -> "CostMeasurement":
        return cls()


class InvocationEvidence(_FrozenModel):
    provenance: Provenance
    usage: TokenUsage = Field(default_factory=TokenUsage.unavailable)
    cost: CostMeasurement = Field(default_factory=CostMeasurement.unavailable)


_SAFE_RATE_LIMIT_HEADER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9 .,:;_+/=\-]*\Z")
_SAFE_PROVIDER_CODE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:\-]*\Z")


def _sanitize_rate_limit_header(value: object) -> str | None:
    """Keep only compact scalar rate-limit metadata, never arbitrary headers."""

    if not isinstance(value, str):
        return None
    cleaned = value.strip()[:128]
    if not cleaned or _SAFE_RATE_LIMIT_HEADER.fullmatch(cleaned) is None:
        return None
    return cleaned


def _sanitize_provider_code(value: object) -> str | None:
    """Accept only a short machine code, never a provider message or body."""

    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        return None
    cleaned = value.strip()[:64]
    if not cleaned or _SAFE_PROVIDER_CODE.fullmatch(cleaned) is None:
        return None
    return cleaned


class RateLimitQuota(_FrozenModel):
    """One reported quota window, not a claim that this quota caused rejection."""

    resource: Literal["requests", "tokens"]
    window_seconds: int = Field(gt=0, le=31_536_000, strict=True)
    limit: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    remaining: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    reset_after_seconds: float | None = Field(
        default=None, ge=0, le=31_536_000, allow_inf_nan=False, strict=True
    )


class RateLimitEvidence(_FrozenModel):
    """Allowlisted operational evidence associated with one rate-limit error."""

    origin: RateLimitOrigin = RateLimitOrigin.UNKNOWN
    limit: str | None = None
    remaining: str | None = None
    reset: str | None = None
    provider_code: str | None = None
    # Optional additions preserve the legacy unqualified metadata. A resource
    # is reported only when the provider explicitly identifies it; quota
    # balances alone must never be used to infer the cause of a rejection.
    resource: Literal["requests", "tokens"] | None = None
    quotas: tuple[RateLimitQuota, ...] = Field(default=(), max_length=8)

    _limit_safe = field_validator("limit", mode="before")(
        _sanitize_rate_limit_header
    )
    _remaining_safe = field_validator("remaining", mode="before")(
        _sanitize_rate_limit_header
    )
    _reset_safe = field_validator("reset", mode="before")(
        _sanitize_rate_limit_header
    )
    _provider_code_safe = field_validator("provider_code", mode="before")(
        _sanitize_provider_code
    )


StructureIssueCode = Literal[
    "json_invalid", "missing", "extra_forbidden", "string_type",
    "string_too_short", "string_too_long", "enum", "literal_error",
    "bool_type", "bool_parsing", "int_type", "int_parsing", "int_from_float",
    "float_type", "float_parsing", "finite_number", "greater_than",
    "greater_than_equal", "less_than", "less_than_equal", "list_type",
    "tuple_type", "dict_type", "model_type", "model_attributes_type",
    "too_short", "too_long", "value_error", "assertion_error", "validation_error",
]


class StructureValidationIssue(_FrozenModel):
    """A bounded machine issue; names must be selected from the product schema."""

    path: tuple[StrictStr | StrictInt, ...] = Field(default=(), max_length=8)
    code: StructureIssueCode

    @field_validator("path")
    @classmethod
    def bound_path_tokens(cls, value: tuple[str | int, ...]) -> tuple[str | int, ...]:
        for token in value:
            if isinstance(token, int):
                if not 0 <= token <= 10_000:
                    raise ValueError("structure path index is outside the safe bound")
            elif token != "?" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", token) is None:
                raise ValueError("structure path requires a declared identifier or marker")
        return value


class StructureValidationEvidence(_FrozenModel):
    """No input, messages, context, schema values or raw exception references."""

    stage: Literal["json_parse", "schema_validation"]
    issues: tuple[StructureValidationIssue, ...] = Field(min_length=1, max_length=8)
    truncated: bool = Field(default=False, strict=True)


class NormalizedError(_FrozenModel):
    category: ErrorCategory
    code: str
    phase: OperationPhase
    invocation_id: str
    target: LLMTarget
    safe_message: str
    evidence: InvocationEvidence
    partial_output: bool = False
    external_id: str | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)
    retryable: bool | None = None
    retry_after_seconds: float | None = Field(default=None, ge=0)
    rate_limit: RateLimitEvidence | None = None
    structure_validation: StructureValidationEvidence | None = None

    _code_non_blank = field_validator("code")(_require_non_blank)
    _invocation_non_blank = field_validator("invocation_id")(_require_non_blank)
    _message_non_blank = field_validator("safe_message")(_require_non_blank)

    @model_validator(mode="after")
    def evidence_matches_error(self) -> "NormalizedError":
        provenance = self.evidence.provenance
        if provenance.invocation_id != self.invocation_id:
            raise ValueError("error evidence must use the same invocation_id")
        if provenance.requested_target != self.target:
            raise ValueError("error evidence must use the same requested target")
        if self.rate_limit is not None and self.category is not ErrorCategory.RATE_LIMITED:
            raise ValueError("rate-limit evidence requires a rate-limited error")
        if self.structure_validation is not None and (
            self.category is not ErrorCategory.INVALID_STRUCTURED_OUTPUT
            or self.phase is not OperationPhase.STRUCTURE_VALIDATION
        ):
            raise ValueError("structure evidence requires a structured-output validation error")
        return self


class InvocationRecord(_FrozenModel):
    """One auditable call across the product-owned LLM boundary."""

    operation: str
    status: InvocationStatus
    evidence: InvocationEvidence
    error: NormalizedError | None = None

    _operation_non_blank = field_validator("operation")(_require_non_blank)

    @model_validator(mode="after")
    def status_matches_error(self) -> "InvocationRecord":
        if self.status is InvocationStatus.COMPLETED:
            if self.error is not None:
                raise ValueError("completed invocation cannot contain an error")
            return self
        if self.error is None:
            raise ValueError("failed invocation requires a normalized error")
        if self.error.evidence != self.evidence:
            raise ValueError("invocation record and error must share evidence")
        return self

    @classmethod
    def completed(
        cls,
        operation: str,
        evidence: InvocationEvidence,
    ) -> "InvocationRecord":
        return cls(
            operation=operation,
            status=InvocationStatus.COMPLETED,
            evidence=evidence,
        )

    @classmethod
    def failed(
        cls,
        operation: str,
        error: NormalizedError,
    ) -> "InvocationRecord":
        status = {
            ErrorCategory.CANCELLED: InvocationStatus.CANCELLED,
            ErrorCategory.TIMEOUT: InvocationStatus.TIMED_OUT,
        }.get(error.category, InvocationStatus.FAILED)
        return cls(
            operation=operation,
            status=status,
            evidence=error.evidence,
            error=error,
        )


class LLMInvocationError(Exception):
    """Only normalized failures cross the adapter boundary."""

    def __init__(self, error: NormalizedError):
        super().__init__(error.safe_message)
        self.error = error


class TextGenerationResult(_FrozenModel):
    content: str = Field(min_length=1)
    evidence: InvocationEvidence

    @field_validator("content")
    @classmethod
    def content_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("generated content must not be blank")
        return value


class StructuredGenerationResult(_FrozenModel):
    value: BaseModel
    evidence: InvocationEvidence


class StreamEvent(_FrozenModel):
    sequence: int = Field(ge=0)
    kind: StreamEventKind
    delta: str | None = None
    evidence: InvocationEvidence | None = None
    error: NormalizedError | None = None
    partial_output: bool = False

    @model_validator(mode="after")
    def fields_match_kind(self) -> "StreamEvent":
        if self.kind is StreamEventKind.DELTA:
            if not self.delta or self.evidence is not None or self.error is not None:
                raise ValueError("delta events contain only a non-empty delta")
            if self.partial_output:
                raise ValueError("partial_output belongs to terminal events")
            return self

        if self.delta is not None or self.evidence is None:
            raise ValueError("terminal events require evidence and cannot contain a delta")
        if self.kind is StreamEventKind.COMPLETED and self.error is not None:
            raise ValueError("completed event cannot contain an error")
        if self.kind is not StreamEventKind.COMPLETED and self.error is None:
            raise ValueError("non-success terminal event requires a normalized error")
        if self.error is not None and self.error.evidence != self.evidence:
            raise ValueError("terminal error and event must carry the same evidence")
        if self.error is not None and self.error.partial_output != self.partial_output:
            raise ValueError("terminal error and event must agree on partial output")
        return self

    @property
    def is_terminal(self) -> bool:
        return self.kind is not StreamEventKind.DELTA


class StreamEventBuilder:
    """Assigns ordered sequence numbers and rejects emission after termination."""

    def __init__(self) -> None:
        self._next_sequence = 0
        self._terminated = False

    def _claim(self, terminal: bool) -> int:
        if self._terminated:
            raise RuntimeError("stream already terminated")
        sequence = self._next_sequence
        self._next_sequence += 1
        if terminal:
            self._terminated = True
        return sequence

    def delta(self, content: str) -> StreamEvent:
        return StreamEvent(
            sequence=self._claim(terminal=False),
            kind=StreamEventKind.DELTA,
            delta=content,
        )

    def complete(self, evidence: InvocationEvidence) -> StreamEvent:
        return StreamEvent(
            sequence=self._claim(terminal=True),
            kind=StreamEventKind.COMPLETED,
            evidence=evidence,
        )

    def fail(
        self,
        kind: StreamEventKind,
        error: NormalizedError,
        *,
        partial_output: bool,
    ) -> StreamEvent:
        if kind not in {
            StreamEventKind.FAILED,
            StreamEventKind.CANCELLED,
            StreamEventKind.TIMED_OUT,
        }:
            raise ValueError("failure terminal must use a failure event kind")
        return StreamEvent(
            sequence=self._claim(terminal=True),
            kind=kind,
            evidence=error.evidence,
            error=error,
            partial_output=partial_output,
        )


def validate_stream_events(events: Sequence[StreamEvent]) -> None:
    """Validate the cross-event invariants that one model cannot enforce alone."""

    if not events:
        raise ValueError("stream must contain a terminal event")
    expected_sequences = list(range(len(events)))
    if [event.sequence for event in events] != expected_sequences:
        raise ValueError("stream sequence numbers must be contiguous and ordered")
    terminals = [event for event in events if event.is_terminal]
    if len(terminals) != 1:
        raise ValueError("stream must contain exactly one terminal event")
    if not events[-1].is_terminal:
        raise ValueError("no event may follow the terminal event")


class ConnectionTestRequest(_FrozenModel):
    invocation_id: str = Field(default_factory=lambda: str(uuid4()))
    target: LLMTarget
    deadline: datetime
    cancellation: CancellationToken = Field(default_factory=CancellationToken, exclude=True)

    _invocation_non_blank = field_validator("invocation_id")(_require_non_blank)
    _deadline_aware = field_validator("deadline")(_require_aware)


class ConnectionTestResult(_FrozenModel):
    probe_version: str
    success: bool
    target: LLMTarget
    evidence: InvocationEvidence
    error: NormalizedError | None = None

    _probe_non_blank = field_validator("probe_version")(_require_non_blank)

    @model_validator(mode="after")
    def status_matches_error(self) -> "ConnectionTestResult":
        if self.success == (self.error is not None):
            raise ValueError("successful probe has no error; failed probe has one error")
        if self.error is not None and self.error.evidence != self.evidence:
            raise ValueError("probe error and result must carry the same evidence")
        if self.evidence.provenance.requested_target != self.target:
            raise ValueError("probe evidence must use the tested target")
        return self


SYNTHETIC_PROBE_VERSION = "storyteller-llm-probe-v1"
SYNTHETIC_PROBE_PROMPT = "Reply with exactly: STORYTELLER_CONNECTION_OK"
SYNTHETIC_PROBE_EXPECTED = "STORYTELLER_CONNECTION_OK"
# The connection check is a small, fixed operation, not an unbounded generation.
# Leave room for low-effort reasoning while keeping provider defaults out of it.
SYNTHETIC_PROBE_MAX_OUTPUT_TOKENS = 128


@runtime_checkable
class LLMGateway(Protocol):
    """Adapter contract.  Implementations execute, but never choose, a target."""

    def capabilities(self, target: LLMTarget) -> CapabilitySet:
        ...

    async def generate_text(self, request: GenerationRequest) -> TextGenerationResult:
        ...

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        ...

    def stream_text(self, request: StreamingGenerationRequest) -> AsyncIterator[StreamEvent]:
        ...

    async def test_connection(self, request: ConnectionTestRequest) -> ConnectionTestResult:
        ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def seconds_until(deadline: datetime) -> float:
    return (deadline - utc_now()).total_seconds()
