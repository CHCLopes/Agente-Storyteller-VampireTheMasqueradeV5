"""Versioned domain records for deterministic turns and narrative memory.

The models in this module are deliberately provider- and persistence-agnostic.
They describe durable product facts; adapters may serialize them, but SDK or
storage-specific values must not leak into these contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)


SchemaVersion = Literal["1.0"]
SCHEMA_VERSION: SchemaVersion = "1.0"
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for record factories."""

    return datetime.now(timezone.utc)


class FrozenRecord(BaseModel):
    """Common immutable and strict configuration for durable records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: SchemaVersion = SCHEMA_VERSION


class Visibility(str, Enum):
    """Independent audiences; callers must explicitly grant every audience."""

    PUBLIC = "public"
    PLAYER = "player"
    STORYTELLER = "storyteller"
    SYSTEM = "system"


class RecordReference(FrozenRecord):
    """Typed link to a source record without embedding or rewriting it."""

    record_id: NonEmptyStr
    record_type: NonEmptyStr
    relation: NonEmptyStr = "derived_from"


class EntityReference(FrozenRecord):
    """Stable reference to an actor, place, item, or other world entity."""

    entity_id: NonEmptyStr
    entity_type: NonEmptyStr
    label: NonEmptyStr | None = None


class CanonicalFact(FrozenRecord):
    """A deterministic, canonical assertion produced by product modules."""

    fact_id: NonEmptyStr
    fact_type: NonEmptyStr
    predicate: NonEmptyStr
    value: JsonValue
    subject: EntityReference | None = None
    occurred_at: datetime
    visibility: Visibility = Visibility.PLAYER
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: tuple[NonEmptyStr, ...] = ()
    source_refs: tuple[RecordReference, ...] = ()

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class CanonicalEvent(FrozenRecord):
    """Immutable event whose summary is derived from canonical facts."""

    event_id: NonEmptyStr
    session_id: NonEmptyStr
    turn_id: NonEmptyStr
    sequence: int = Field(ge=0)
    event_type: NonEmptyStr
    occurred_at: datetime
    summary: NonEmptyStr | None = None
    fact_ids: tuple[NonEmptyStr, ...] = ()
    tags: tuple[NonEmptyStr, ...] = ()
    actors: tuple[EntityReference, ...] = ()
    place: EntityReference | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: Visibility = Visibility.PLAYER
    references: tuple[RecordReference, ...] = ()
    pending: bool = False

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class StateChange(FrozenRecord):
    """A deterministic state mutation staged by a turn, never by narrative."""

    path: tuple[NonEmptyStr, ...] = Field(min_length=1)
    value: JsonValue


class TurnDraft(FrozenRecord):
    """A side-effect-free turn prepared for narrative generation and commit."""

    draft_id: NonEmptyStr
    session_id: NonEmptyStr
    turn_id: NonEmptyStr
    attempt_id: NonEmptyStr
    created_at: datetime = Field(default_factory=utc_now)
    player_input: NonEmptyStr
    base_revision: int = Field(default=0, ge=0)
    base_state_revision: int = Field(default=0, ge=0)
    facts: tuple[CanonicalFact, ...] = ()
    events: tuple[CanonicalEvent, ...] = ()
    state_changes: tuple[StateChange, ...] = ()
    context_references: tuple[RecordReference, ...] = ()

    @field_validator("created_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @model_validator(mode="after")
    def validate_internal_references(self) -> "TurnDraft":
        fact_ids = [fact.fact_id for fact in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("TurnDraft fact_id values must be unique")

        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("TurnDraft event_id values must be unique")

        available_fact_ids = set(fact_ids)
        for event in self.events:
            if event.session_id != self.session_id or event.turn_id != self.turn_id:
                raise ValueError("TurnDraft events must belong to its session and turn")
            missing = set(event.fact_ids) - available_fact_ids
            if missing:
                raise ValueError(
                    f"CanonicalEvent {event.event_id!r} references unknown facts: "
                    f"{sorted(missing)}"
                )
        return self


class NarrationResumeState(str, Enum):
    """Durable lifecycle for a frozen, non-canonical narration proposal."""

    PAUSED = "paused"
    DIRECT_RESUME_TRIAL = "direct_resume_trial"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class NarratorGateState(str, Enum):
    UNKNOWN = "unknown"
    PROBING = "probing"
    DIRECT_RESUME_TRIAL = "direct_resume_trial"
    AVAILABLE = "available"
    COOLDOWN = "cooldown"
    CONFIGURATION_BLOCKED = "configuration_blocked"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


class NarratorGateScope(str, Enum):
    EXACT_TARGET = "exact_target"
    GATEWAY_ACCOUNT = "gateway_account"
    UPSTREAM_TARGET = "upstream_target"
    UNKNOWN_CONSERVATIVE = "unknown_conservative"


class NarrationResumeCapsule(FrozenRecord):
    """Immutable server-side input for exactly one H6-only resume attempt."""

    capsule_id: NonEmptyStr
    session_id: NonEmptyStr
    source_operation_id: NonEmptyStr
    source_attempt_id: NonEmptyStr
    turn_id: NonEmptyStr
    requested_turn: int = Field(gt=0)
    state_revision: int = Field(ge=0)
    request_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    action: NonEmptyStr
    draft: TurnDraft
    resolution: JsonValue | None = None
    frozen_context: JsonValue
    requested_target: JsonValue
    normalized_reason: JsonValue
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None

    @field_validator("created_at", "expires_at")
    @classmethod
    def require_aware_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_datetime(value)

    @model_validator(mode="after")
    def matches_draft(self) -> "NarrationResumeCapsule":
        if (
            self.draft.session_id != self.session_id
            or self.draft.turn_id != self.turn_id
            or self.draft.attempt_id != self.source_attempt_id
            or self.draft.player_input != self.action
            or self.draft.base_state_revision != self.state_revision
        ):
            raise ValueError("resume capsule does not match its frozen draft")
        return self


class NarrationPauseProjection(FrozenRecord):
    """Player-safe paused state; secret scope keys and frozen context stay server-side."""

    capsule_id: NonEmptyStr
    source_operation_id: NonEmptyStr
    expected_state_revision: int = Field(ge=0)
    state: NarrationResumeState = NarrationResumeState.PAUSED
    action_summary: NonEmptyStr
    resolution_summary: NonEmptyStr | None = None
    category: NonEmptyStr
    safe_message: NonEmptyStr
    retryable: bool
    retry_not_before: datetime | None = None
    server_now: datetime = Field(default_factory=utc_now)
    rate_limit_origin: Literal["gateway", "upstream", "unknown"] | None = None
    gate_scope: Literal[
        "exact_target", "gateway_account", "upstream_target", "unknown_conservative"
    ] | None = None
    evidence_scope: NonEmptyStr | None = None
    allowed_actions: tuple[Literal["resume", "abandon"], ...] = ("abandon",)

    @field_validator("retry_not_before", "server_now")
    @classmethod
    def require_projection_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_datetime(value)


class NarrationResumeCommand(FrozenRecord):
    capsule_id: NonEmptyStr
    operation_id: NonEmptyStr
    expected_state_revision: int = Field(ge=0)


class NarratorAvailabilityGate(FrozenRecord):
    gate_id: NonEmptyStr
    state: NarratorGateState
    scope: NarratorGateScope
    scope_key: NonEmptyStr
    target: JsonValue
    observed_at: datetime
    retry_not_before: datetime | None = None
    evidence_scope: NonEmptyStr = "unknown"
    rate_limit_origin: Literal["gateway", "upstream", "unknown"] | None = None
    timing_source: NonEmptyStr = "none"
    timing_confidence: Literal["unknown", "reported", "observed", "policy"] = "unknown"
    lease_operation_id: NonEmptyStr | None = None

    @field_validator("observed_at", "retry_not_before")
    @classmethod
    def require_gate_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_datetime(value)


class NarrativeRecord(FrozenRecord):
    """Completed narrative persisted only after turn validation succeeds."""

    narrative_id: NonEmptyStr
    session_id: NonEmptyStr
    turn_id: NonEmptyStr
    created_at: datetime = Field(default_factory=utc_now)
    text: NonEmptyStr
    source_event_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    visibility: Visibility = Visibility.PLAYER
    invocation_id: NonEmptyStr | None = None
    complete: Literal[True] = True

    @field_validator("created_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class CandidateProposer(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HUMAN = "human"


class CandidateValidationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MemoryCandidate(FrozenRecord):
    """Small semantic memory proposal anchored to immutable source events."""

    candidate_id: NonEmptyStr
    session_id: NonEmptyStr
    turn_id: NonEmptyStr
    created_at: datetime = Field(default_factory=utc_now)
    summary: NonEmptyStr
    source_event_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tags: tuple[NonEmptyStr, ...] = ()
    actors: tuple[EntityReference, ...] = ()
    place: EntityReference | None = None
    occurred_at: datetime | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: Visibility = Visibility.PLAYER
    pending: bool = False
    proposed_by: CandidateProposer = CandidateProposer.DETERMINISTIC
    validation_status: CandidateValidationStatus = CandidateValidationStatus.PENDING
    validation_notes: tuple[NonEmptyStr, ...] = ()

    @field_validator("created_at", "occurred_at")
    @classmethod
    def require_aware_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_datetime(value)


class EpisodicMemory(FrozenRecord):
    """Validated derived memory; source canonical events remain authoritative."""

    memory_id: NonEmptyStr
    session_id: NonEmptyStr
    created_at: datetime = Field(default_factory=utc_now)
    summary: NonEmptyStr
    source_event_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tags: tuple[NonEmptyStr, ...] = ()
    actors: tuple[EntityReference, ...] = ()
    place: EntityReference | None = None
    occurred_at: datetime | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: Visibility = Visibility.PLAYER
    pending: bool = False
    version: int = Field(default=1, ge=1)

    @field_validator("created_at", "occurred_at")
    @classmethod
    def require_aware_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_datetime(value)


class ConsolidationScope(str, Enum):
    SCENE = "scene"
    SESSION = "session"


class Consolidation(FrozenRecord):
    """Versioned summary that preserves references to all source records."""

    consolidation_id: NonEmptyStr
    session_id: NonEmptyStr
    scope: ConsolidationScope
    created_at: datetime = Field(default_factory=utc_now)
    version: int = Field(default=1, ge=1)
    summary: NonEmptyStr
    source_memory_ids: tuple[NonEmptyStr, ...] = ()
    source_event_ids: tuple[NonEmptyStr, ...] = ()
    tags: tuple[NonEmptyStr, ...] = ()
    visibility: Visibility = Visibility.PLAYER
    supersedes_consolidation_id: NonEmptyStr | None = None

    @field_validator("created_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @model_validator(mode="after")
    def require_sources(self) -> "Consolidation":
        if not self.source_memory_ids and not self.source_event_ids:
            raise ValueError("Consolidation requires at least one source record")
        return self


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include timezone information")
    return value
