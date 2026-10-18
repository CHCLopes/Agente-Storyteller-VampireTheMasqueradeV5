"""Pure preparation of one causal beat for the synthetic record campaign.

This module neither commits state nor rolls dice or calls a narrator. The caller
must obtain the original operation claim, retain this preparation with it and
commit the proposed state only after narrative admission and revision CAS.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from .campaign_progression_catalog import (
    CAMPAIGN_ID, CONTENT_VERSION, RECOVERED_CONTENT, SAFE_SURFACE,
    CampaignIntentKind, campaign_options, campaign_rule_id, classify_campaign_intent,
)
from .scene_direction_catalog import mara_profile
from .scene_resolution_service import (
    MechanicalResolutionInput, SceneBeatResolution, ScenePressure,
    SceneResolutionInput, SceneTurnKind, resolve_scene_beat,
)
from .scene_service import SceneState

POLICY_VERSION = "campaign-progression.v2"
_SHA = re.compile(r"^[0-9a-f]{64}$")
Record = Literal["threatened", "warned", "wet", "preserved", "partial", "lost"]
Outcome = Literal["preserved", "partial", "lost", "abandoned"]


class CampaignProgressionError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class LegacyCampaignProgressState(_Frozen):
    """Retain the exact v1 shape for existing saves and retained capsules."""
    campaign_id: Literal["record-at-risk"] = CAMPAIGN_ID
    content_version: Literal["record-at-risk.v1"] = "record-at-risk.v1"
    policy_version: Literal["campaign-progression.v1"] = "campaign-progression.v1"
    revision: int = Field(ge=0)
    location: Literal["Arquivo", "Galeria"] = "Arquivo"
    record: Record = "threatened"
    outcome: Outcome | None = None
    known_information: tuple[str, ...] = ()
    resolved_objectives: tuple[str, ...] = ()

    @field_validator("known_information", "resolved_objectives")
    @classmethod
    def known_ids_only(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)) or any(not value or value != value.strip() for value in values):
            raise ValueError("campaign ids must be unique and normalized")
        return values

    @model_validator(mode="after")
    def terminal_is_consistent(self) -> "LegacyCampaignProgressState":
        if any(value not in {SAFE_SURFACE, RECOVERED_CONTENT} for value in self.known_information):
            raise ValueError("unknown campaign information id")
        if any(value not in {"record_rescue", "content_recovery"} for value in self.resolved_objectives):
            raise ValueError("unknown campaign objective id")
        if self.outcome is None and self.record in {"preserved", "partial", "lost"}:
            raise ValueError("terminal record needs outcome")
        if self.outcome in {"preserved", "partial", "lost"} and self.record != self.outcome:
            raise ValueError("outcome and record disagree")
        if self.outcome == "abandoned" and self.record not in {"threatened", "warned", "wet"}:
            raise ValueError("abandonment does not resolve the record")
        if self.outcome in {"preserved", "partial"} and "record_rescue" not in self.resolved_objectives:
            raise ValueError("successful ending needs resolved objective")
        if self.outcome is None and self.resolved_objectives:
            raise ValueError("active campaign cannot have resolved objective")
        if self.outcome in {"lost", "abandoned"} and self.resolved_objectives:
            raise ValueError("unsuccessful ending cannot resolve objective")
        if "content_recovery" in self.resolved_objectives and self.outcome != "partial":
            raise ValueError("content recovery needs partial ending")
        if RECOVERED_CONTENT in self.known_information and "content_recovery" not in self.resolved_objectives:
            raise ValueError("recovered content needs resolved objective")
        return self


class CampaignProgressState(LegacyCampaignProgressState):
    """V2 records object position independently of the player's scene location."""
    content_version: Literal["record-at-risk.v2"] = CONTENT_VERSION
    policy_version: Literal["campaign-progression.v2"] = POLICY_VERSION
    record_location: Literal["bench", "dry_surface"] = "bench"

    @model_validator(mode="before")
    @classmethod
    def retained_position_is_required(cls, value: object) -> object:
        if (type(value) is dict and value.get("content_version") == CONTENT_VERSION
                and "record_location" not in value):
            raise ValueError("retained v2 campaign requires record position")
        return value

    @model_validator(mode="after")
    def position_is_consistent(self) -> "CampaignProgressState":
        rescued = self.outcome == "preserved" or (
            self.outcome == "partial" and "content_recovery" not in self.resolved_objectives)
        expected = "dry_surface" if rescued else "bench"
        if self.record_location != expected:
            raise ValueError("campaign record position contradicts resolved action")
        return self


CampaignState = Annotated[
    CampaignProgressState | LegacyCampaignProgressState,
    Field(discriminator="content_version"),
]
_STATE_ADAPTER = TypeAdapter(CampaignState)


def read_campaign_progress_state(value: object) -> CampaignState:
    """Validate the retained version without inventing or migrating old fields."""
    return _STATE_ADAPTER.validate_python(value)


class CampaignProgressionRequest(_Frozen):
    session_id: str = Field(min_length=1, max_length=200)
    operation_id: str = Field(min_length=1, max_length=200)
    turn_id: str = Field(min_length=1, max_length=200)
    base_revision: int = Field(ge=0)
    player_input: str = Field(min_length=1, max_length=2000)
    state: CampaignState
    mechanical: MechanicalResolutionInput | None = None

    @field_validator("session_id", "operation_id", "turn_id", "player_input")
    @classmethod
    def literal_nonblank(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("campaign identity and input must be literal and nonblank")
        return value


class CampaignPreparedEffect(_Frozen):
    protocol: Literal["campaign-prepared-effect-v1"] = "campaign-prepared-effect-v1"
    session_id: str
    operation_id: str
    turn_id: str
    base_revision: int
    rule_id: str
    content_version: Literal["record-at-risk.v1", "record-at-risk.v2"] = CONTENT_VERSION
    policy_version: Literal["campaign-progression.v1", "campaign-progression.v2"] = POLICY_VERSION
    before_sha256: str
    after_state: CampaignState
    beat: SceneBeatResolution
    mechanical: MechanicalResolutionInput | None = None
    effect_sha256: str

    @field_validator("before_sha256", "effect_sha256")
    @classmethod
    def sha256_only(cls, value: str) -> str:
        if not _SHA.fullmatch(value):
            raise ValueError("campaign hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def bind_effect(self) -> "CampaignPreparedEffect":
        if (self.after_state.revision != self.base_revision + 1
                or self.content_version != self.after_state.content_version
                or self.policy_version != self.after_state.policy_version
                or self.beat.session_id != self.session_id
                or self.beat.operation_id != self.operation_id
                or self.beat.turn_id != self.turn_id
                or self.beat.base_revision != self.base_revision
                or not self.beat.selected_option_id.startswith(self.rule_id + ".")
                or self.effect_sha256 != _sha(self.model_dump(mode="json", exclude={"effect_sha256"}))):
            raise ValueError("campaign prepared effect is inconsistent")
        return self


class CampaignNarratorPacket(_Frozen):
    """Player-visible causal obligation for a future, explicitly selected B profile."""

    protocol: Literal["campaign-narrator-packet-v1"] = "campaign-narrator-packet-v1"
    session_id: str
    operation_id: str
    turn_id: str
    base_revision: int
    player_input: str
    state_before: CampaignState
    state_after: CampaignState
    required_effects: tuple[str, ...]
    beat: SceneBeatResolution
    protected_boundary: Literal["do_not_reveal_founder_identity"] = "do_not_reveal_founder_identity"
    preparation_sha256: str

    @field_validator("preparation_sha256")
    @classmethod
    def preparation_hash(cls, value: str) -> str:
        if not _SHA.fullmatch(value):
            raise ValueError("packet preparation hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def bind_packet(self) -> "CampaignNarratorPacket":
        if (self.state_before.revision != self.base_revision
                or self.state_before.content_version != self.state_after.content_version
                or self.state_after.revision != self.base_revision + 1
                or self.beat.session_id != self.session_id
                or self.beat.operation_id != self.operation_id
                or self.beat.turn_id != self.turn_id
                or self.beat.base_revision != self.base_revision
                or self.required_effects != self.beat.effect_keys):
            raise ValueError("campaign narrator packet is inconsistent")
        return self


def _sha(value: BaseModel | dict[str, object]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _after(state: CampaignState, rule_id: str,
           intent: CampaignIntentKind) -> CampaignState:
    record: Record = state.record
    outcome: Outcome | None = None
    known = list(state.known_information)
    objectives = list(state.resolved_objectives)
    if rule_id == "R-01" and intent is CampaignIntentKind.TASK and SAFE_SURFACE not in known:
        known.append(SAFE_SURFACE)
    elif rule_id in {"R-03", "R-03B", "R-04"}:
        record = {"R-03": "warned", "R-03B": "wet", "R-04": "lost"}[rule_id]
        if record == "lost":
            outcome = "lost"
    elif rule_id == "R-05":
        record, outcome = "preserved", "preserved"
        objectives.append("record_rescue")
    elif rule_id in {"R-06", "R-07"}:
        record, outcome = "partial", "partial"
        objectives.append("record_rescue")
        if rule_id == "R-07":
            known.append(RECOVERED_CONTENT)
            objectives.append("content_recovery")
    elif rule_id == "R-08":
        record = {"threatened": "wet", "warned": "wet", "wet": "lost"}[record]
        if record == "lost":
            outcome = "lost"
    elif rule_id == "R-09":
        outcome = "abandoned"
    retained = state.model_dump(mode="json")
    if isinstance(state, CampaignProgressState) and rule_id in {"R-05", "R-06"}:
        retained["record_location"] = "dry_surface"
    return type(state).model_validate({
        **retained, "revision": state.revision + 1,
        "record": record, "outcome": outcome,
        "known_information": known, "resolved_objectives": objectives,
    })


def resolve_campaign_progression(request: CampaignProgressionRequest) -> CampaignPreparedEffect:
    """Prepare exactly one deterministic effect for an already claimed operation."""
    checked = CampaignProgressionRequest.model_validate(request)
    state = checked.state
    if checked.base_revision != state.revision:
        raise CampaignProgressionError("campaign_revision_mismatch")
    if state.outcome is not None:
        raise CampaignProgressionError("campaign_already_ended")
    intent = classify_campaign_intent(checked.player_input)
    if intent is None:
        raise CampaignProgressionError("campaign_action_out_of_scope")
    if intent is CampaignIntentKind.INSPECT and checked.mechanical is None:
        raise CampaignProgressionError("campaign_mechanical_receipt_required")
    if intent is not CampaignIntentKind.INSPECT and checked.mechanical is not None:
        raise CampaignProgressionError("campaign_unexpected_mechanical_receipt")
    success = checked.mechanical.is_success if checked.mechanical is not None else None
    rule_id = campaign_rule_id(intent, state.record, success)
    if rule_id is None:
        raise CampaignProgressionError("campaign_no_eligible_rule")
    turn_kind = (SceneTurnKind.DIALOGUE if intent in {CampaignIntentKind.TASK, CampaignIntentKind.HELP_REQUEST, CampaignIntentKind.FOUNDER}
                 else SceneTurnKind.WAIT if intent is CampaignIntentKind.WAIT
                 else SceneTurnKind.FICTION_ACTION)
    pressure = {"threatened": ScenePressure.CALM, "warned": ScenePressure.WATCHFUL,
                "wet": ScenePressure.TENSE}[state.record]
    scene = SceneState(location=state.location, npcs_present=("Mara",), last_turn=state.revision)
    beat = resolve_scene_beat(SceneResolutionInput(
        session_id=checked.session_id, operation_id=checked.operation_id,
        turn_id=checked.turn_id, base_revision=checked.base_revision,
        player_action=checked.player_input, turn_kind=turn_kind, scene=scene,
        pressure=pressure, mechanical=checked.mechanical,
        npc_profiles=(mara_profile(),),
        options=campaign_options(rule_id, record=state.record,
                                 known_information=state.known_information, intent=intent),
    ))
    after = _after(state, rule_id, intent)
    payload = {
        "protocol": "campaign-prepared-effect-v1",
        "session_id": checked.session_id, "operation_id": checked.operation_id,
        "turn_id": checked.turn_id, "base_revision": checked.base_revision,
        "rule_id": rule_id, "content_version": state.content_version,
        "policy_version": state.policy_version, "before_sha256": _sha(state),
        "after_state": after.model_dump(mode="json"), "beat": beat.model_dump(mode="json"),
        "mechanical": checked.mechanical.model_dump(mode="json") if checked.mechanical is not None else None,
    }
    return CampaignPreparedEffect.model_validate({**payload, "effect_sha256": _sha(payload)})


def verify_campaign_prepared_effect(
    request: CampaignProgressionRequest, prepared: CampaignPreparedEffect,
) -> CampaignPreparedEffect:
    """Check retained bytes against original input and receipt, without RNG."""
    expected = resolve_campaign_progression(request)
    try:
        checked = CampaignPreparedEffect.model_validate(prepared)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise CampaignProgressionError("campaign_preparation_mismatch") from None
    if checked != expected:
        raise CampaignProgressionError("campaign_preparation_mismatch")
    return checked


def build_campaign_narrator_packet(
    request: CampaignProgressionRequest, prepared: CampaignPreparedEffect,
) -> CampaignNarratorPacket:
    """Project a retained effect; never use this as a commit/admission grant."""
    checked = CampaignProgressionRequest.model_validate(request)
    effect = verify_campaign_prepared_effect(checked, prepared)
    return CampaignNarratorPacket(
        session_id=checked.session_id, operation_id=checked.operation_id,
        turn_id=checked.turn_id, base_revision=checked.base_revision,
        player_input=checked.player_input, state_before=checked.state,
        state_after=effect.after_state, required_effects=effect.beat.effect_keys,
        beat=effect.beat, preparation_sha256=effect.effect_sha256,
    )
