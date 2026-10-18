"""Pure observation of a retained B operation; no execution or retry authority.

The persistence boundary validates the capsule/attempt/turn pair in one read
transaction. This module limits its returned data and independently rebuilds
the executor's existing static identity without importing the executor.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from .narrative_source_capsule import SourceTurnCapsule, validate_source_turn_capsule
from .narrative_source_context import ORIGIN_PROTOCOL
from .narrative_source_turn import INVOCATION_OPERATION, PROTOCOL as TURN_PROTOCOL

PROTOCOL = "narrative-source-operation-status-v1"
SourceOperationState = Literal[
    "retained_unstarted", "pending", "completed", "failed", "timeout", "cancelled",
]
SourceFailureStage = Literal["preflight", "generation", "policy", "admission", "delivery", "commit"]
_TERMINALS = frozenset({"failed", "timeout", "cancelled"})

# Deliberately literal: new producer codes require an explicit review here.
# Never accept a prefix, exception prose, provider text or diagnostic evidence.
_SAFE_FAILURE_CODES = frozenset({
    "process_interrupted",
    "source_turn_cancelled", "source_turn_antecedents_invalid",
    "source_turn_user_size_exceeded", "source_turn_deadline_exceeded",
    "source_turn_invocation_mismatch", "source_turn_provider_failure",
    "source_turn_preflight_failed", "source_turn_generation_failed",
    "source_turn_policy_failed", "source_turn_admission_failed",
    "source_turn_delivery_failed", "source_turn_commit_failed",
    "source_context_invalid", "source_context_origin_invalid",
    "source_context_origin_missing", "source_context_identity_mismatch",
    "source_context_scene_invalid", "source_context_scene_mismatch",
    "source_context_state_incompatible", "source_context_snapshot_invalid",
    "source_context_selection_invalid", "source_context_campaign_exists",
    "source_context_campaign_missing", "source_context_query_invalid",
    "source_context_revision_mismatch", "source_context_history_incompatible",
    "source_context_stored_pair_mismatch", "source_context_dependencies_forbidden",
    "source_context_origin_mutation_forbidden", "source_context_commit_contract_required",
    "source_profile_current_scene_required", "source_profile_scene_invalid",
    "source_profile_scene_requires_location_and_npcs_only", "source_profile_facts_invalid",
    "source_profile_resolution_invalid", "source_profile_resolution_ambiguous",
    "source_profile_proposal_invalid", "source_profile_player_input_invalid",
    "source_profile_policy_context_invalid", "source_profile_visibility_forbidden",
    "source_profile_session_invalid", "source_profile_sources_limit",
    "source_profile_projection_invalid", "source_profile_source_text_bounds",
    "source_profile_source_context_mismatch", "source_profile_source_duplicate",
    "source_profile_context_size_exceeded",
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
})


class SourceOperationStatusCode(str, Enum):
    INVALID = "source_operation_status_invalid"
    CAPSULE_INVALID = "source_operation_status_capsule_invalid"
    STORED_PAIR_INVALID = "source_operation_status_stored_pair_invalid"
    DATABASE_UNAVAILABLE = "source_operation_status_database_unavailable"
    QUERY_INVALID = "source_operation_status_query_invalid"
    SCHEMA_INCOMPATIBLE = "source_operation_status_schema_incompatible"
    HISTORY_INVALID = "source_operation_status_history_invalid"


class SourceOperationStatusError(ValueError):
    def __init__(self, code: SourceOperationStatusCode | str = SourceOperationStatusCode.INVALID):
        try:
            self.code = SourceOperationStatusCode(code).value
        except (TypeError, ValueError):
            self.code = SourceOperationStatusCode.INVALID.value
        super().__init__(self.code)


class _Observed(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            raw = dict(value.__dict__)
            raw.update(value.__pydantic_extra__ or {})
            return raw
        return value


class SourceOperationFailure(_Observed):
    code: StrictStr
    stage: SourceFailureStage | None = None

    @field_validator("code")
    @classmethod
    def closed_code(cls, value: str) -> str:
        if value not in _SAFE_FAILURE_CODES:
            raise SourceOperationStatusError()
        return value


def safe_source_failure(error: object) -> SourceOperationFailure | None:
    """Project known persisted code/stage; unknown diagnostics remain unavailable.

    An early cancellation or process recovery legitimately has no stage. Extra
    diagnostic fields are discarded, even when the code itself is recognized.
    """
    if type(error) is not dict:
        return None
    try:
        return SourceOperationFailure(code=error.get("code"), stage=error.get("stage"))
    except (ValueError, TypeError):
        return None


_Counter = Annotated[StrictInt, Field(ge=0)]
_Identity = Annotated[StrictStr, Field(min_length=1, max_length=240)]


class SourceOperationSnapshot(_Observed):
    protocol: Literal["narrative-source-operation-status-v1"] = PROTOCOL
    session_id: _Identity
    operation_id: _Identity
    capsule_sha256: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
    base_turn: _Counter
    base_state_revision: _Counter
    current_turn: _Counter
    current_state_revision: _Counter
    status: SourceOperationState
    committed_turn_id: _Identity | None = None
    failure: SourceOperationFailure | None = None

    @field_validator("session_id", "operation_id", "committed_turn_id")
    @classmethod
    def literal_identity(cls, value: str | None) -> str | None:
        if value is not None:
            if value != value.strip():
                raise SourceOperationStatusError()
            value.encode("utf-8")
        return value

    @model_validator(mode="after")
    def consistent_observation(self) -> "SourceOperationSnapshot":
        if (self.base_state_revision < self.base_turn
                or self.current_state_revision < self.current_turn
                or self.current_turn < self.base_turn
                or self.current_state_revision < self.base_state_revision):
            raise SourceOperationStatusError()
        if self.status == "completed":
            if (self.committed_turn_id is None or self.current_turn <= self.base_turn
                    or self.current_state_revision <= self.base_state_revision):
                raise SourceOperationStatusError()
        elif self.committed_turn_id is not None:
            raise SourceOperationStatusError()
        if self.failure is not None and self.status not in _TERMINALS:
            raise SourceOperationStatusError()
        return self


def _checked_capsule(capsule: object) -> SourceTurnCapsule:
    try:
        if type(capsule) is not SourceTurnCapsule:
            raise ValueError
        return validate_source_turn_capsule(
            capsule, session_id=capsule.session_id, operation_id=capsule.operation_id,
        )
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        raise SourceOperationStatusError(SourceOperationStatusCode.CAPSULE_INVALID) from None


def create_source_operation_snapshot(
    capsule: SourceTurnCapsule, *, current_turn: int, current_state_revision: int,
    status: SourceOperationState, committed_turn_id: str | None = None, error: object = None,
) -> SourceOperationSnapshot:
    """Build the restricted view after persistence validates the stored pair."""
    checked = _checked_capsule(capsule)
    try:
        if status not in _TERMINALS and error is not None:
            raise ValueError
        if status == "completed" and committed_turn_id != checked.draft.turn_id:
            raise ValueError
        return SourceOperationSnapshot(
            session_id=checked.session_id, operation_id=checked.operation_id,
            capsule_sha256=checked.fingerprint_sha256,
            base_turn=checked.snapshot.current_turn,
            base_state_revision=checked.snapshot.state_revision,
            current_turn=current_turn, current_state_revision=current_state_revision,
            status=status, committed_turn_id=committed_turn_id,
            failure=safe_source_failure(error),
        )
    except (ValueError, TypeError, AttributeError):
        raise SourceOperationStatusError() from None


def expected_source_attempt_metadata(capsule: SourceTurnCapsule) -> dict[str, str | int]:
    """Reconstruct the current executor identity; no state, deadline or I/O changes."""
    checked = _checked_capsule(capsule)
    def canonical(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    draft = checked.draft
    invocation_id = str(uuid5(NAMESPACE_URL, canonical([TURN_PROTOCOL, checked.session_id, checked.operation_id])))
    static_payload = {
        "draft": draft.model_dump(mode="json"),
        "scene": checked.canonical_scene.model_dump(mode="json"),
        "state": checked.state, "relationships": checked.relationships, "context": {},
        "system_prompt": checked.system_prompt, "target": checked.target.model_dump(mode="json"),
        "parameters": checked.parameters.model_dump(mode="json"), "protected_secrets": (),
        "player_aliases": checked.player_aliases, "npc_aliases": checked.npc_aliases,
        "chronicle_name": checked.chronicle_name,
    }
    return {
        "narrative_contract": TURN_PROTOCOL,
        "source_context_protocol": ORIGIN_PROTOCOL,
        "source_context_base_state_revision": draft.base_state_revision,
        "expected_invocation_id": invocation_id,
        "expected_invocation_operation": INVOCATION_OPERATION,
        "source_turn_static_sha256": hashlib.sha256(canonical(static_payload).encode("utf-8")).hexdigest(),
        "draft_id": draft.draft_id, "turn_id": draft.turn_id,
    }
