"""Pure preparation of source-only drafts from trusted server decisions.

This adapter neither classifies player text nor rolls/recalculates dice. A typed
receipt and producer label establish consistency, not server authentication or
proof that the caller invoked the rules engine. The caller retains the prepared
receipt/draft across failed generation; this module does not manage retry state.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .narrative_source_context import SourceContextSnapshot
from .campaign_source_context import CampaignSourceSnapshot
from .rules_service import (
    ResolutionResult, V5ActionPayload, V5ActionTarget, V5Attribute,
    V5Skill, V5WeaponCategory,
)
from .turn_models import CanonicalEvent, CanonicalFact, RecordReference, TurnDraft, Visibility

PROTOCOL = "narrative-source-preparation-v1"
PRODUCER = "narrative_source_preparation.prepare_source_turn_draft"
_EFFECT_FLAGS = (
    "is_aggressive", "is_feeding", "is_healing", "target_killed",
    "is_bane_damage", "is_blood_surge", "is_willpower_reroll",
    "is_compulsion_active", "is_true_faith_active",
)


class SourcePreparationCode(str, Enum):
    INVALID = "source_preparation_invalid"
    SNAPSHOT_INVALID = "source_preparation_snapshot_invalid"
    IDENTITY_INVALID = "source_preparation_identity_invalid"
    TIMESTAMP_INVALID = "source_preparation_timestamp_invalid"
    INPUT_INVALID = "source_preparation_input_invalid"
    ACTION_INVALID = "source_preparation_action_invalid"
    RECEIPT_INVALID = "source_preparation_receipt_invalid"
    OUT_OF_SCOPE = "source_preparation_out_of_scope"
    INPUT_MISMATCH = "source_preparation_input_mismatch"


class SourcePreparationError(ValueError):
    def __init__(self, code: SourcePreparationCode | str):
        try:
            self.code = SourcePreparationCode(code).value
        except (TypeError, ValueError):
            self.code = SourcePreparationCode.INVALID.value
        super().__init__(self.code)


def _raw(value: object) -> object:
    # Keep fields introduced by model_construct/model_copy; model_dump could
    # silently discard them on the legacy models used by the rules engine.
    if isinstance(value, BaseModel):
        payload = dict(value.__dict__)
        payload.update(value.__pydantic_extra__ or {})
        return payload
    return value


def _literal(value: object, code: SourcePreparationCode, *, limit: int | None = None) -> str:
    if (type(value) is not str or not value or value != value.strip()
            or (limit is not None and len(value) > limit)):
        raise SourcePreparationError(code)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SourcePreparationError(code) from None
    return value


def _action(value: object) -> V5ActionPayload:
    try:
        if type(value) not in (dict, V5ActionPayload):
            raise ValueError
        raw = dict(_raw(value))
        if set(raw) != set(V5ActionPayload.model_fields):
            raise ValueError
        for name, enum in (
            ("attribute", V5Attribute), ("skill", V5Skill),
            ("weapon_category", V5WeaponCategory), ("action_target", V5ActionTarget),
        ):
            if type(raw[name]) is str:
                raw[name] = enum(raw[name])
        checked = V5ActionPayload.model_validate(raw, strict=True)
        _literal(checked.intent, SourcePreparationCode.ACTION_INVALID)
    except (ValueError, TypeError, AttributeError):
        raise SourcePreparationError(SourcePreparationCode.ACTION_INVALID) from None
    if (checked.requires_roll is not True
            or checked.action_target is not V5ActionTarget.UNOPPOSED
            or checked.weapon_category is not V5WeaponCategory.UNARMED
            or checked.power_used is not None
            or any(getattr(checked, name) for name in _EFFECT_FLAGS)):
        raise SourcePreparationError(SourcePreparationCode.OUT_OF_SCOPE)
    return checked


def _receipt(value: object) -> ResolutionResult:
    try:
        if type(value) not in (dict, ResolutionResult):
            raise ValueError
        raw = dict(_raw(value))
        if set(raw) != set(ResolutionResult.model_fields):
            raise ValueError
        checked = ResolutionResult.model_validate(raw, strict=True)
        checked.summary.encode("utf-8")
        rolls = checked.normal_rolls + checked.hunger_rolls
        if (not rolls or any(not 1 <= die <= 10 for die in rolls)
                or checked.successes < 0):
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise SourcePreparationError(SourcePreparationCode.RECEIPT_INVALID) from None
    if checked.messy_critical or checked.bestial_failure:
        raise SourcePreparationError(SourcePreparationCode.OUT_OF_SCOPE)
    return checked


class _Preparation(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @model_validator(mode="before")
    @classmethod
    def preserve_fields(cls, value: object) -> object:
        return _raw(value)


class DeclaredActionPreparation(_Preparation):
    """Explicit server classification; never inferred from player_input here."""
    kind: Literal["declared_action"] = "declared_action"


class ResolvedActionPreparation(_Preparation):
    """An ordinary, already resolved server action; nested values are copied."""
    kind: Literal["ordinary_resolution"] = "ordinary_resolution"
    action: V5ActionPayload
    resolution: ResolutionResult

    @field_validator("action", mode="before")
    @classmethod
    def ordinary_action(cls, value: object) -> V5ActionPayload:
        return _action(value)

    @field_validator("resolution", mode="before")
    @classmethod
    def ordinary_receipt(cls, value: object) -> ResolutionResult:
        return _receipt(value)


def _stable_id(session_id: str, operation_id: str, role: str) -> str:
    encoded = json.dumps([PROTOCOL, session_id, operation_id, role],
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return role + "-" + hashlib.sha256(encoded).hexdigest()


def prepare_source_turn_draft(
    snapshot: SourceContextSnapshot | CampaignSourceSnapshot, *, operation_id: str, created_at: datetime,
    player_input: str,
    preparation: DeclaredActionPreparation | ResolvedActionPreparation,
) -> TurnDraft:
    """Return a copied, bound draft without I/O, RNG, classification or effects.

    Only structural receipt validity is checked. Dice arithmetic and semantic
    claims in an externally supplied receipt are not authenticated/recalculated.
    SQLite eligibility and freshness remain enforced by the execution boundary.
    """
    try:
        from .campaign_expression_context import CampaignExpressionSnapshot
        if type(snapshot) not in (SourceContextSnapshot, CampaignSourceSnapshot, CampaignExpressionSnapshot):
            raise ValueError
        checked = type(snapshot).model_validate(snapshot)
        if checked.state_revision < checked.current_turn:
            raise ValueError
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourcePreparationError(SourcePreparationCode.SNAPSHOT_INVALID) from None
    operation = _literal(operation_id, SourcePreparationCode.IDENTITY_INVALID, limit=240)
    text = _literal(player_input, SourcePreparationCode.INPUT_INVALID)
    try:
        if type(created_at) is not datetime or created_at.utcoffset() is None:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise SourcePreparationError(SourcePreparationCode.TIMESTAMP_INVALID) from None
    try:
        if type(preparation) not in (DeclaredActionPreparation, ResolvedActionPreparation):
            raise ValueError
        prepared = type(preparation).model_validate(preparation)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourcePreparationError(SourcePreparationCode.INVALID) from None

    if isinstance(prepared, ResolvedActionPreparation):
        action, receipt = prepared.action, prepared.resolution
        if action.intent != text:
            raise SourcePreparationError(SourcePreparationCode.INPUT_MISMATCH)
        value = {
            **receipt.model_dump(mode="json"),
            "attribute": action.attribute.value, "skill": action.skill.value,
            "dice_pool": len(receipt.normal_rolls) + len(receipt.hunger_rolls),
            "hunger_dice": len(receipt.hunger_rolls),
            "difficulty": action.inferred_difficulty,
            "outcome": "success" if receipt.is_success else "failure",
            "messy": receipt.messy_critical, "bestial": receipt.bestial_failure,
        }
        fact_type, predicate = "mechanics.resolution", "resolved_player_action"
        event_type, tags = "player_action_resolved", ("mechanics", "resolution")
    else:
        value = {"player_input": text, "requires_roll": False,
                 "summary": "A ação foi declarada sem teste mecânico."}
        fact_type, predicate = "action.declaration", "declared_player_action"
        event_type, tags = "player_action_declared", ("action", "declaration")
    session = (checked.origin.session_id if type(checked) is SourceContextSnapshot
               else checked.origin.scene_origin.session_id)
    turn_id = _stable_id(session, operation, "turn")
    fact = CanonicalFact(
        fact_id=_stable_id(session, operation, "fact"), fact_type=fact_type,
        predicate=predicate, value=value, occurred_at=created_at,
        visibility=Visibility.PLAYER, tags=tags,
        source_refs=(RecordReference(record_id=PRODUCER,
                                     record_type="deterministic_module", relation="produced_by"),),
    )
    event = CanonicalEvent(
        event_id=_stable_id(session, operation, "event"), session_id=session,
        turn_id=turn_id, sequence=0, event_type=event_type, occurred_at=created_at,
        summary="Ação declarada pelo jogador: " + text, fact_ids=(fact.fact_id,),
        tags=tags, visibility=Visibility.PLAYER,
    )
    return TurnDraft(
        draft_id=_stable_id(session, operation, "draft"), session_id=session,
        turn_id=turn_id, attempt_id=_stable_id(session, operation, "attempt"),
        created_at=created_at, player_input=text, base_revision=checked.current_turn,
        base_state_revision=checked.state_revision, facts=(fact,), events=(event,),
        state_changes=(), context_references=(),
    )
