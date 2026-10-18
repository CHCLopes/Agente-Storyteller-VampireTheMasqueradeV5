"""Inactive public projections for B; observation never grants execution authority.

The trusted server caller supplies already validated persistence/service results
and the expected session and operation separately. These pure functions recheck
shape, identity and consistency; they neither authenticate access nor prove a
database commit. A completed snapshot plus its confirmed envelope is required
before exposing narrative text. A constructed consistent pair proves no commit.

No handler, routing, I/O, clock, RNG, producer or gateway is called here. Public
events omit all claims, capsules, configuration, hashes and retry authority. The
client keeps its submitted action under operation_id; events do not resend it.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, TypeAdapter, field_validator, model_validator

from .narrative_source_input import SourceInputClaim
from .narrative_source_setup import SourceSetupManifest, validate_source_setup_manifest
from .narrative_source_status import SourceFailureStage, SourceOperationSnapshot
from .narrative_source_turn import NarrativeSourceTurnEnvelope

PROTOCOL = "narrative-source-public-event-v1"
_Identity = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_PreparationStage = Literal["preflight", "classification", "resolution", "production", "finalization"]
_Terminal = Literal["failed", "timeout", "cancelled"]


class SourceTransportError(ValueError):
    """Malformed or inconsistent inputs fail closed without echoing their data."""

    def __init__(self):
        super().__init__("source_transport_projection_invalid")


def _raw(value: object) -> object:
    # model_dump can erase forged extras in nested legacy models. Rebuild every
    # member, preserving even __pydantic_extra__, before revalidation.
    if isinstance(value, BaseModel):
        fields = dict(value.__dict__)
        fields.update(value.__pydantic_extra__ or {})
        return {key: _raw(item) for key, item in fields.items()}
    if type(value) is dict:
        return {key: _raw(item) for key, item in value.items()}
    if type(value) is list:
        return [_raw(item) for item in value]
    if type(value) is tuple:
        return tuple(_raw(item) for item in value)
    return value


def _identity(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or value != value.strip():
        raise SourceTransportError()
    value.encode("utf-8")
    return value


def _checked(model, value: object):
    if type(value) is not model:
        raise SourceTransportError()
    return model.model_validate(_raw(value))


class _PublicEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
                              revalidate_instances="always", hide_input_in_errors=True)
    protocol: Literal["narrative-source-public-event-v1"] = PROTOCOL

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        return _raw(value)


class _OperationEvent(_PublicEvent):
    operation_id: _Identity

    @field_validator("operation_id", mode="before")
    @classmethod
    def literal_operation(cls, value: object) -> str:
        return _identity(value)


class SourceBriefingEvent(_PublicEvent):
    event: Literal["briefing"] = "briefing"
    origin: Literal["authored_trial_setup"] = "authored_trial_setup"
    text: Annotated[StrictStr, Field(min_length=1)]

    @field_validator("text")
    @classmethod
    def literal_text(cls, value: str) -> str:
        value.encode("utf-8")
        if not value.strip():
            raise SourceTransportError()
        return value


class SourcePreparationEvent(_OperationEvent):
    """ready observes P completion only; it is not a serializable permission."""
    event: Literal["preparation"] = "preparation"
    status: Literal["pending", "ready"]


class SourcePreparationRejectedEvent(_OperationEvent):
    event: Literal["preparation_rejected"] = "preparation_rejected"
    status: _Terminal
    code: Literal["out_of_scope", "clarification_required", "preparation_failed", "cancelled", "timeout"]
    stage: _PreparationStage | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> "SourcePreparationRejectedEvent":
        if self.status != {"cancelled": "cancelled", "timeout": "timeout"}.get(self.code, "failed"):
            raise SourceTransportError()
        return self


class SourceNarrativePendingEvent(_OperationEvent):
    # Retention alone does not mean generation has started, including stale K.
    event: Literal["narrative_pending"] = "narrative_pending"
    status: Literal["retained_unstarted", "pending"]


class SourceNarrativeCompleteEvent(_OperationEvent):
    event: Literal["narrative_complete"] = "narrative_complete"
    n: Annotated[StrictStr, Field(min_length=40, max_length=1600)]
    q: Annotated[StrictStr, Field(min_length=3, max_length=200)]

    @field_validator("n", "q")
    @classmethod
    def literal_presentation(cls, value: str) -> str:
        value.encode("utf-8")
        if value != " ".join(value.split()):
            raise SourceTransportError()
        return value


class SourceNarrativeRejectedEvent(_OperationEvent):
    event: Literal["narrative_rejected"] = "narrative_rejected"
    status: _Terminal
    code: Literal["narrative_rejected", "narrative_failed", "cancelled", "timeout"]
    stage: SourceFailureStage | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> "SourceNarrativeRejectedEvent":
        if self.status != {"cancelled": "cancelled", "timeout": "timeout"}.get(self.code, "failed"):
            raise SourceTransportError()
        return self


class SourceUnavailableEvent(_OperationEvent):
    """No safe diagnostic is available; this does not declare retry eligibility."""
    event: Literal["unavailable"] = "unavailable"
    phase: Literal["preparation", "narrative"]
    code: Literal["unavailable"] = "unavailable"


SourcePublicEvent = Annotated[
    SourceBriefingEvent | SourcePreparationEvent | SourcePreparationRejectedEvent
    | SourceNarrativePendingEvent | SourceNarrativeCompleteEvent
    | SourceNarrativeRejectedEvent | SourceUnavailableEvent,
    Field(discriminator="event"),
]
_EVENT_ADAPTER = TypeAdapter(SourcePublicEvent)
_EVENT_MODELS = (SourceBriefingEvent, SourcePreparationEvent, SourcePreparationRejectedEvent,
                 SourceNarrativePendingEvent, SourceNarrativeCompleteEvent,
                 SourceNarrativeRejectedEvent, SourceUnavailableEvent)


def validate_source_public_event(value: object, *, operation_id: str | None) -> SourcePublicEvent:
    """Validate a public wire/model shape, not its authenticity or delivery."""
    try:
        if type(value) not in (dict, *_EVENT_MODELS):
            raise ValueError
        checked = _EVENT_ADAPTER.validate_python(_raw(value))
        if type(checked) is SourceBriefingEvent:
            if operation_id is not None:
                raise ValueError
        elif checked.operation_id != _identity(operation_id):
            raise ValueError
        return checked
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceTransportError() from None


def project_source_briefing(manifest: SourceSetupManifest, *, session_id: str) -> SourceBriefingEvent:
    """Re-present the validated authored briefing without creating a turn."""
    try:
        _identity(session_id)
        checked = validate_source_setup_manifest(_checked(SourceSetupManifest, manifest), session_id=session_id)
        return SourceBriefingEvent(text=checked.briefing)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceTransportError() from None


_INPUT_CODES = {
    "source_input_out_of_scope": "out_of_scope",
    "source_input_clarification_required": "clarification_required",
    "source_input_base_mismatch": "preparation_failed",
    "source_input_production_failed": "preparation_failed",
    "source_input_cancelled": "cancelled",
    "process_interrupted": "cancelled",
    "source_input_deadline_exceeded": "timeout",
}


def project_source_preparation(claim: SourceInputClaim, *, session_id: str,
                               operation_id: str) -> SourcePreparationEvent | SourcePreparationRejectedEvent | SourceUnavailableEvent:
    """Project only the observation; never export the request or newly_claimed."""
    try:
        checked = _checked(SourceInputClaim, claim)
        if (checked.request.session_id != _identity(session_id)
                or checked.request.operation_id != _identity(operation_id)):
            raise ValueError
        if checked.status in ("pending", "completed"):
            return SourcePreparationEvent(operation_id=operation_id,
                status="ready" if checked.status == "completed" else "pending")
        failure = checked.completion.failure
        code = _INPUT_CODES.get(failure.code)
        if code is None:
            return project_source_unavailable(operation_id=operation_id, phase="preparation")
        return SourcePreparationRejectedEvent(operation_id=operation_id, status=checked.status,
            code=code, stage=failure.stage)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceTransportError() from None


# Explicit reviewed codes only. A future internal safe code does not silently
# expand the public vocabulary, and exception prose is never accepted here.
_NARRATIVE_CODES = {
    "source_turn_cancelled": "cancelled",
    "process_interrupted": "cancelled",
    "source_turn_deadline_exceeded": "timeout",
    **dict.fromkeys((
        "source_turn_antecedents_invalid", "source_turn_user_size_exceeded",
        "source_turn_invocation_mismatch", "source_turn_provider_failure",
        "source_turn_preflight_failed", "source_turn_generation_failed",
        "source_turn_delivery_failed", "source_turn_commit_failed",
    ), "narrative_failed"),
    **dict.fromkeys((
        "source_turn_policy_failed", "source_turn_admission_failed",
        "scene_outcome_mismatch", "scene_internal_content", "scene_narrative_too_short",
        "scene_narrative_too_long", "scene_player_agency_violation",
        "scene_unknown_thread_resolution", "scene_thread_reopened_while_resolved",
        "scene_thread_resolution_without_evidence", "scene_location_changed_without_transition",
        "scene_player_movement_not_authorized", "scene_npc_roster_changed_without_event",
        "scene_duplicate_fact", "scene_open_thread_capacity_exceeded",
        "scene_output_not_portuguese", "scene_player_prompt_too_long",
        "scene_player_prompt_not_open", "scene_player_prompt_not_actionable",
        "scene_secret_disclosed", "scene_success_not_honored", "scene_failure_not_honored",
        "scene_failure_granted_conclusive_clue", "scene_failure_granted_conclusive_observation",
        "scene_failure_granted_goal",
    ), "narrative_rejected"),
}


# Actual executor paths can reuse these codes across terminal statuses. Match
# only observed pairs; do not infer status from provider category or free text.
_NARRATIVE_TERMINAL_PAIRS = {
    ("source_turn_provider_failure", "timeout"): "timeout",
    ("source_turn_provider_failure", "cancelled"): "cancelled",
    ("source_turn_delivery_failed", "cancelled"): "cancelled",
}


def project_source_unavailable(*, operation_id: str,
                               phase: Literal["preparation", "narrative"]) -> SourceUnavailableEvent:
    """Construct a cause-free event; no error payload can be supplied or echoed."""
    try:
        return SourceUnavailableEvent(operation_id=_identity(operation_id), phase=phase)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceTransportError() from None


def project_source_operation(snapshot: SourceOperationSnapshot, *, session_id: str,
        operation_id: str, confirmed_envelope: NarrativeSourceTurnEnvelope | None = None,
        ) -> SourceNarrativePendingEvent | SourceNarrativeCompleteEvent | SourceNarrativeRejectedEvent | SourceUnavailableEvent:
    """Project a server-read operation and, only when complete, its confirmed n/q.

    The reader must already have checked the stored aggregate. This detached
    pair check cannot certify persistence, capsule hashes, provider admission or
    semantic quality. Later current_turn/revision do not relabel historical text.
    """
    try:
        checked = _checked(SourceOperationSnapshot, snapshot)
        if checked.session_id != _identity(session_id) or checked.operation_id != _identity(operation_id):
            raise ValueError
        if checked.status == "completed":
            envelope = _checked(NarrativeSourceTurnEnvelope, confirmed_envelope)
            source = envelope.projection.source
            if (envelope.operation_id != operation_id or source.session_id != session_id
                    or source.turn_id != checked.committed_turn_id):
                raise ValueError
            return SourceNarrativeCompleteEvent(operation_id=operation_id,
                n=envelope.projection.text, q=envelope.question)
        if confirmed_envelope is not None:
            raise ValueError
        if checked.status in ("retained_unstarted", "pending"):
            return SourceNarrativePendingEvent(operation_id=operation_id, status=checked.status)
        code = None
        if checked.failure is not None:
            code = _NARRATIVE_TERMINAL_PAIRS.get(
                (checked.failure.code, checked.status), _NARRATIVE_CODES.get(checked.failure.code),
            )
        if code is None:
            return project_source_unavailable(operation_id=operation_id, phase="narrative")
        return SourceNarrativeRejectedEvent(operation_id=operation_id, status=checked.status,
            code=code, stage=checked.failure.stage)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceTransportError() from None
