"""Pure client-intention contract and guard for an explicit B entry.

Acceptance does not classify an action, authorize mechanics, reserve an operation
or prove that a database produced a snapshot. The server must first obtain its
eligible snapshot from persistence and supply the expected session separately.
No transport, runtime selection, rules engine or gateway is invoked here.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from .narrative_source_context import (
    SourceContextSnapshot, validate_source_context_origin, validate_source_scene,
)

# Matches the existing transport's text ceiling without importing main/config.
# B operation identities retain the capsule limit, independently of legacy v1.
MAX_PLAYER_INPUT_CHARS = 500
MAX_OPERATION_ID_CHARS = 240


class SourceEntryError(ValueError):
    """Closed boundary diagnostic without caller content or validation prose."""

    def __init__(self, code: str = "source_entry_request_invalid"):
        self.code = code if code in {
            "source_entry_request_invalid", "source_entry_snapshot_invalid",
        } else "source_entry_request_invalid"
        super().__init__(self.code)


class SourcePlayerActionRequest(BaseModel):
    """Only public intent and stable identity; session belongs to the server."""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always",
        hide_input_in_errors=True,
    )
    operation_id: Annotated[StrictStr, Field(min_length=1, max_length=MAX_OPERATION_ID_CHARS)]
    player_input: Annotated[StrictStr, Field(min_length=1, max_length=MAX_PLAYER_INPUT_CHARS)]

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            raw = dict(value.__dict__)
            raw.update(value.__pydantic_extra__ or {})
            return raw
        return value

    @field_validator("operation_id", "player_input", mode="before")
    @classmethod
    def literal_utf8(cls, value: object) -> str:
        if type(value) is not str or not value.strip():
            raise SourceEntryError()
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise SourceEntryError() from None
        return value

    @field_validator("operation_id", "player_input")
    @classmethod
    def literal_boundaries(cls, value: str) -> str:
        # The retained preparer requires these same literal outer boundaries.
        # Reject unsupported padding; never silently strip player intent.
        if value != value.strip():
            raise SourceEntryError()
        return value


def validate_source_player_action_request(value: object) -> SourcePlayerActionRequest:
    """Copy/revalidate a decoded request; never trust an existing model blindly."""
    try:
        if type(value) not in (dict, SourcePlayerActionRequest):
            raise ValueError
        return SourcePlayerActionRequest.model_validate(value)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceEntryError() from None


def validate_source_entry_snapshot(
    snapshot: SourceContextSnapshot, *, session_id: str,
) -> SourceContextSnapshot:
    """Check a server-read snapshot against its expected session and known scene.

    This detached consistency check grants no readiness, retry or mechanical
    authority. It cannot authenticate the caller or reconstruct database history.
    """
    try:
        if type(snapshot) is not SourceContextSnapshot:
            raise ValueError
        checked = SourceContextSnapshot.model_validate(snapshot)
        origin = validate_source_context_origin(checked.origin, session_id=session_id)
        validate_source_scene(checked.canonical_scene, origin)
        return checked
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceEntryError("source_entry_snapshot_invalid") from None
