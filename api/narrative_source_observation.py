"""Internal producer-backed session observation; never a wire payload or authority.

The new reader binds setup, a requested P/K/H chain and the latest confirmed turn
in one read transaction. These pure models only check detached consistency.
They cannot authenticate a caller, prove a commit, or authorize execution.
No previous reader adopts the stricter producer-backed policy from this module.

Only existing public projection functions may expose these observations. Default
serialization/repr excludes the retained claim, configuration, source and IDs.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from .narrative_source_input import SourceInputClaim
from .narrative_source_setup import SourceSetupManifest, validate_source_setup_manifest
from .narrative_source_status import SourceOperationSnapshot
from .narrative_source_turn import NarrativeSourceTurnEnvelope


class SourceObservationError(ValueError):
    """A closed diagnostic without database paths, inputs or exception prose."""
    def __init__(self, code: str = "source_observation_invalid"):
        self.code = code if type(code) is str and code in {
            "source_observation_invalid", "source_observation_query_invalid",
            "source_observation_database_unavailable", "source_observation_stored_pair_invalid",
        } else "source_observation_invalid"
        super().__init__(self.code)


def _raw(value: object) -> object:
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
        raise SourceObservationError()
    value.encode("utf-8")
    return value


class _InternalObservation(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
        revalidate_instances="always", hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def preserve_fields(cls, value: object) -> object:
        return _raw(value)


def _confirmed_pair(operation: SourceOperationSnapshot, envelope: NarrativeSourceTurnEnvelope) -> None:
    source = envelope.projection.source
    if (operation.status != "completed"
            or operation.session_id != source.session_id
            or operation.operation_id != envelope.operation_id
            or operation.committed_turn_id != source.turn_id):
        raise SourceObservationError()


class SourceConfirmedObservation(_InternalObservation):
    operation: SourceOperationSnapshot = Field(exclude=True, repr=False)
    envelope: NarrativeSourceTurnEnvelope = Field(exclude=True, repr=False)

    @model_validator(mode="after")
    def bound_pair(self) -> "SourceConfirmedObservation":
        _confirmed_pair(self.operation, self.envelope)
        return self


class SourceRequestedObservation(_InternalObservation):
    operation_id: StrictStr = Field(exclude=True, repr=False)
    preparation: SourceInputClaim | None = Field(default=None, exclude=True, repr=False)
    narrative: SourceOperationSnapshot | None = Field(default=None, exclude=True, repr=False)
    confirmed: NarrativeSourceTurnEnvelope | None = Field(default=None, exclude=True, repr=False)

    @field_validator("operation_id", mode="before")
    @classmethod
    def literal_operation(cls, value: object) -> str:
        return _identity(value)

    @model_validator(mode="after")
    def consistent_chain(self) -> "SourceRequestedObservation":
        claim = self.preparation
        if claim is None:
            if self.narrative is not None or self.confirmed is not None:
                raise SourceObservationError()
            return self
        if claim.newly_claimed or claim.request.operation_id != self.operation_id:
            raise SourceObservationError()
        if claim.status != "completed":
            if self.narrative is not None or self.confirmed is not None:
                raise SourceObservationError()
            return self
        operation = self.narrative
        request = claim.request
        if (operation is None or operation.operation_id != self.operation_id
                or operation.session_id != request.session_id
                or operation.base_turn != request.snapshot.current_turn
                or operation.base_state_revision != request.snapshot.state_revision
                or operation.capsule_sha256 != claim.completion.capsule_sha256):
            raise SourceObservationError()
        if operation.status == "completed":
            if self.confirmed is None:
                raise SourceObservationError()
            _confirmed_pair(operation, self.confirmed)
        elif self.confirmed is not None:
            raise SourceObservationError()
        return self


class SourcePlayerObservation(_InternalObservation):
    protocol: Literal["source-player-observation-v1"] = "source-player-observation-v1"
    session_id: StrictStr = Field(exclude=True, repr=False)
    manifest: SourceSetupManifest = Field(exclude=True, repr=False)
    latest_completed: SourceConfirmedObservation | None = Field(default=None, exclude=True, repr=False)
    requested: SourceRequestedObservation | None = Field(default=None, exclude=True, repr=False)

    @field_validator("session_id", mode="before")
    @classmethod
    def literal_session(cls, value: object) -> str:
        return _identity(value)

    @model_validator(mode="after")
    def consistent_session(self) -> "SourcePlayerObservation":
        validate_source_setup_manifest(self.manifest, session_id=self.session_id)
        latest, requested = self.latest_completed, self.requested
        if latest is not None:
            operation = latest.operation
            if (operation.session_id != self.session_id
                    or operation.current_turn != operation.base_turn + 1):
                raise SourceObservationError()
        if requested is not None and requested.preparation is not None:
            claim = requested.preparation
            if (claim.request.session_id != self.session_id
                    or claim.request.snapshot.origin != self.manifest.origin):
                raise SourceObservationError()
            latest_turn = 0 if latest is None else latest.operation.current_turn
            if claim.request.snapshot.current_turn > latest_turn:
                raise SourceObservationError()
            operation = requested.narrative
            if operation is not None:
                if operation.current_turn != latest_turn:
                    raise SourceObservationError()
                if latest is not None and operation.current_state_revision != latest.operation.current_state_revision:
                    raise SourceObservationError()
                if latest is not None and operation.operation_id == latest.operation.operation_id:
                    if operation != latest.operation or requested.confirmed != latest.envelope:
                        raise SourceObservationError()
        return self


def validate_source_player_observation(value: object, *, session_id: str,
        operation_id: str | None = None) -> SourcePlayerObservation:
    """Revalidate an internal observation against the server's query, never execute."""
    try:
        if type(value) not in (dict, SourcePlayerObservation):
            raise ValueError
        checked = SourcePlayerObservation.model_validate(_raw(value))
        if checked.session_id != _identity(session_id):
            raise ValueError
        if operation_id is None:
            if checked.requested is not None:
                raise ValueError
        elif checked.requested is None or checked.requested.operation_id != _identity(operation_id):
            raise ValueError
        return checked
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceObservationError() from None
