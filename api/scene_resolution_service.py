"""Pure, deterministic resolution of one local scene beat.

The resolver chooses among rule-authored consequences.  It never calls an LLM,
rolls dice, mutates campaign state or turns its output into canon.  A later
integration layer may stage the returned beat in a ``TurnDraft`` and commit it
only after narrative admission succeeds.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .scene_service import SceneState
from .turn_models import Visibility


RESOLUTION_POLICY = "scene-beat-resolution.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SceneResolutionError(ValueError):
    """A safe, structured refusal to resolve the requested scene beat."""

    def __init__(self, code: str, *, evidence: dict[str, object] | None = None):
        super().__init__(code)
        self.code = code
        self.evidence = dict(evidence or {})


class SceneTurnKind(str, Enum):
    FICTION_ACTION = "fiction_action"
    DIALOGUE = "dialogue"
    WAIT = "wait"
    QUERY = "query"
    COMMAND = "command"
    CLARIFICATION = "clarification"
    TECHNICAL_FAILURE = "technical_failure"


class SceneIntentOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNRESOLVED = "unresolved"


class SceneBeatKind(str, Enum):
    RESPONSE = "response"
    CHANGE = "change"
    CONSEQUENCE = "consequence"
    COMPLICATION = "complication"
    TRANSITION = "transition"
    THREAD_UPDATE = "thread_update"


class ScenePressure(str, Enum):
    CALM = "calm"
    WATCHFUL = "watchful"
    TENSE = "tense"
    IMMEDIATE = "immediate"


class NpcPosture(str, Enum):
    OPEN = "open"
    GUARDED = "guarded"
    RESISTANT = "resistant"
    HOSTILE = "hostile"
    SUPPORTIVE = "supportive"


class FrozenResolutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MechanicalResolutionInput(FrozenResolutionModel):
    """Exact immutable copy of an already-produced mechanical result."""

    source_fact_id: str = Field(min_length=1, max_length=200)
    successes: int = Field(ge=0)
    is_success: bool
    bestial_failure: bool = False
    messy_critical: bool = False
    summary: str = Field(min_length=1, max_length=400)
    normal_rolls: tuple[int, ...] = ()
    hunger_rolls: tuple[int, ...] = ()
    margin: int = 0

    @field_validator("normal_rolls", "hunger_rolls")
    @classmethod
    def validate_dice(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value < 1 or value > 10 for value in values):
            raise ValueError("mechanical dice must be between 1 and 10")
        return values

    @model_validator(mode="after")
    def validate_flags(self) -> "MechanicalResolutionInput":
        if self.bestial_failure and self.is_success:
            raise ValueError("bestial failure cannot be a success")
        if self.is_success != (self.margin >= 0):
            raise ValueError("mechanical success must agree with margin")
        return self


class SceneNpcProfile(FrozenResolutionModel):
    """Minimum internal NPC profile needed for one local beat."""

    npc_id: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    capabilities: tuple[str, ...] = ()
    limits: tuple[str, ...] = ()
    local_goal: str = Field(min_length=1, max_length=240)
    posture: NpcPosture
    relationship_id: str | None = Field(default=None, max_length=120)
    relationship_disposition: str | None = Field(default=None, max_length=80)
    relationship_trust: int | None = Field(default=None, ge=1, le=5)
    base_dice_pool: int = Field(ge=0)
    threat_level: int = Field(ge=1, le=5)
    is_supernatural: bool
    has_true_faith: bool
    corruption_index: int = Field(ge=1, le=5)
    secret_constraints: tuple[str, ...] = ()

    @field_validator("npc_id", "display_name", "local_goal")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("capabilities", "limits", "secret_constraints")
    @classmethod
    def normalize_labels(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(" ".join(value.split()) for value in values if value.strip())
        if len(normalized) != len(set(value.casefold() for value in normalized)):
            raise ValueError("NPC profile labels must be unique")
        if any(len(value) > 120 for value in normalized):
            raise ValueError("NPC profile label is too long")
        return normalized


class NpcBeatMove(FrozenResolutionModel):
    npc_id: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=3, max_length=240)
    posture_after: NpcPosture | None = None

    @field_validator("action")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        return " ".join(value.split())


class NarrativeBeatConstraint(FrozenResolutionModel):
    """A statement H6 must preserve, with an explicit audience."""

    kind: Literal["must_show", "must_not_claim", "cause", "uncertainty"]
    summary: str = Field(min_length=3, max_length=240)
    visibility: Visibility = Visibility.PLAYER

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())


class SceneConsequenceOption(FrozenResolutionModel):
    """One rule-authored consequence that may be eligible for the beat."""

    option_id: str = Field(min_length=1, max_length=160)
    priority: int = Field(default=0, ge=-1000, le=1000)
    beat_kind: SceneBeatKind
    turn_kinds: tuple[SceneTurnKind, ...] = Field(min_length=1)
    outcomes: tuple[SceneIntentOutcome, ...] = Field(min_length=1)
    required_npc_id: str | None = Field(default=None, max_length=120)
    required_capabilities: tuple[str, ...] = ()
    forbidden_limits: tuple[str, ...] = ()
    effect_keys: tuple[str, ...] = ()
    guidance_keys: tuple[str, ...] = ()
    observable_change: str | None = Field(default=None, max_length=300)
    npc_move: NpcBeatMove | None = None
    open_threads: tuple[str, ...] = ()
    resolve_threads: tuple[str, ...] = ()
    transition_to: str | None = Field(default=None, max_length=160)
    pressure_after: ScenePressure | None = None
    constraints: tuple[NarrativeBeatConstraint, ...] = ()

    @field_validator(
        "required_capabilities", "forbidden_limits", "effect_keys", "guidance_keys", "open_threads", "resolve_threads"
    )
    @classmethod
    def normalize_lists(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(" ".join(value.split()) for value in values if value.strip())
        if len(normalized) != len(set(value.casefold() for value in normalized)):
            raise ValueError("scene consequence labels must be unique")
        if any(len(value) > 240 for value in normalized):
            raise ValueError("scene consequence label is too long")
        return normalized

    @field_validator("observable_change", "transition_to")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @model_validator(mode="after")
    def require_meaningful_beat(self) -> "SceneConsequenceOption":
        if not any(
            (
                self.observable_change,
                self.npc_move,
                self.effect_keys,
                self.open_threads,
                self.resolve_threads,
                self.transition_to,
                self.pressure_after,
            )
        ):
            raise ValueError("scene consequence must change or answer something")
        if self.required_npc_id is None and (
            self.required_capabilities or self.forbidden_limits or self.npc_move
        ):
            raise ValueError("NPC requirements need required_npc_id")
        if self.npc_move is not None and self.npc_move.npc_id != self.required_npc_id:
            raise ValueError("NPC move must belong to required_npc_id")
        if self.beat_kind is SceneBeatKind.TRANSITION and self.transition_to is None:
            raise ValueError("transition beat requires transition_to")
        if self.transition_to is not None and self.beat_kind is not SceneBeatKind.TRANSITION:
            raise ValueError("transition_to requires a transition beat")
        return self


class SceneResolutionInput(FrozenResolutionModel):
    session_id: str = Field(min_length=1, max_length=200)
    operation_id: str = Field(min_length=1, max_length=200)
    turn_id: str = Field(min_length=1, max_length=200)
    base_revision: int = Field(ge=0)
    player_action: str = Field(min_length=1, max_length=2000)
    turn_kind: SceneTurnKind
    scene: SceneState
    pressure: ScenePressure = ScenePressure.CALM
    mechanical: MechanicalResolutionInput | None = None
    npc_profiles: tuple[SceneNpcProfile, ...] = ()
    options: tuple[SceneConsequenceOption, ...] = Field(min_length=1)

    @field_validator("player_action")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_scene_profiles(self) -> "SceneResolutionInput":
        ids = [profile.npc_id for profile in self.npc_profiles]
        if len(ids) != len(set(value.casefold() for value in ids)):
            raise ValueError("NPC profile ids must be unique")
        present = {value.casefold() for value in self.scene.npcs_present}
        missing = [
            profile.npc_id
            for profile in self.npc_profiles
            if profile.display_name.casefold() not in present
            and profile.npc_id.casefold() not in present
        ]
        if missing:
            raise ValueError("NPC profiles must belong to actors present in the scene")
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("scene consequence option ids must be unique")
        return self


class SceneBeatResolution(FrozenResolutionModel):
    protocol: Literal["scene-beat-resolution-v1"] = "scene-beat-resolution-v1"
    policy: Literal["scene-beat-resolution.v1"] = RESOLUTION_POLICY
    session_id: str
    operation_id: str
    turn_id: str
    base_revision: int
    selected_option_id: str
    beat_kind: SceneBeatKind
    outcome: SceneIntentOutcome
    effect_keys: tuple[str, ...] = ()
    guidance_keys: tuple[str, ...] = ()
    observable_change: str | None = None
    npc_move: NpcBeatMove | None = None
    open_threads: tuple[str, ...] = ()
    resolve_threads: tuple[str, ...] = ()
    transition_to: str | None = None
    pressure_before: ScenePressure
    pressure_after: ScenePressure
    constraints: tuple[NarrativeBeatConstraint, ...] = ()
    mechanical: MechanicalResolutionInput | None = None
    input_sha256: str
    resolution_sha256: str

    @field_validator("input_sha256", "resolution_sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("resolution hashes must be lowercase SHA-256")
        return value


_NON_FICTIONAL_TURNS = {
    SceneTurnKind.QUERY,
    SceneTurnKind.COMMAND,
    SceneTurnKind.CLARIFICATION,
    SceneTurnKind.TECHNICAL_FAILURE,
}


def _canonical_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(value: BaseModel | dict[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def mechanical_resolution_from_result(
    result: object, *, source_fact_id: str
) -> MechanicalResolutionInput:
    """Copy an existing ``ResolutionResult`` without invoking the rules engine."""

    from .rules_service import ResolutionResult

    validated = ResolutionResult.model_validate(result)
    return MechanicalResolutionInput(
        source_fact_id=source_fact_id,
        successes=validated.successes,
        is_success=validated.is_success,
        bestial_failure=validated.bestial_failure,
        messy_critical=validated.messy_critical,
        summary=validated.summary,
        normal_rolls=tuple(validated.normal_rolls),
        hunger_rolls=tuple(validated.hunger_rolls),
        margin=validated.margin,
    )


def scene_npc_profile_from_models(
    *,
    npc_id: str,
    display_name: str,
    npc: object,
    relationship: object | None,
    local_goal: str,
    posture: NpcPosture,
    capabilities: tuple[str, ...] = (),
    limits: tuple[str, ...] = (),
    secret_constraints: tuple[str, ...] = (),
) -> SceneNpcProfile:
    """Adapt existing NPC/relationship records without inventing policy fields."""

    from .npc_service import NpcModel
    from .relationship_service import NpcRelationship

    validated_npc = NpcModel.model_validate(npc)
    validated_relationship = (
        NpcRelationship.model_validate(relationship)
        if relationship is not None
        else None
    )
    return SceneNpcProfile(
        npc_id=npc_id,
        display_name=display_name,
        capabilities=capabilities,
        limits=limits,
        local_goal=local_goal,
        posture=posture,
        relationship_id=(
            validated_relationship.npc_id
            if validated_relationship is not None
            else None
        ),
        relationship_disposition=(
            validated_relationship.disposition
            if validated_relationship is not None
            else None
        ),
        relationship_trust=(
            validated_relationship.trust_level
            if validated_relationship is not None
            else None
        ),
        base_dice_pool=validated_npc.engine_data.base_dice_pool,
        threat_level=validated_npc.engine_data.threat_level,
        is_supernatural=validated_npc.engine_data.is_supernatural,
        has_true_faith=validated_npc.engine_data.has_true_faith,
        corruption_index=validated_npc.engine_data.corruption_index,
        secret_constraints=secret_constraints,
    )


def _outcome(value: SceneResolutionInput) -> SceneIntentOutcome:
    if value.mechanical is None:
        return SceneIntentOutcome.UNRESOLVED
    return (
        SceneIntentOutcome.SUCCESS
        if value.mechanical.is_success
        else SceneIntentOutcome.FAILURE
    )


def _profile_map(value: SceneResolutionInput) -> dict[str, SceneNpcProfile]:
    return {profile.npc_id: profile for profile in value.npc_profiles}


def _option_is_eligible(
    option: SceneConsequenceOption,
    *,
    value: SceneResolutionInput,
    outcome: SceneIntentOutcome,
    profiles: dict[str, SceneNpcProfile],
) -> bool:
    if value.turn_kind not in option.turn_kinds or outcome not in option.outcomes:
        return False
    if any(thread not in value.scene.open_threads for thread in option.resolve_threads):
        return False
    if any(thread in value.scene.open_threads for thread in option.open_threads):
        return False
    if option.transition_to == value.scene.location:
        return False
    if option.required_npc_id is None:
        return True
    profile = profiles.get(option.required_npc_id)
    if profile is None:
        return False
    capabilities = {item.casefold() for item in profile.capabilities}
    limits = {item.casefold() for item in profile.limits}
    if not {item.casefold() for item in option.required_capabilities}.issubset(capabilities):
        return False
    if {item.casefold() for item in option.forbidden_limits} & limits:
        return False
    return True


def resolve_scene_beat(value: SceneResolutionInput) -> SceneBeatResolution:
    """Resolve one beat with stable priority and option-id tie breaking."""

    if value.turn_kind in _NON_FICTIONAL_TURNS:
        raise SceneResolutionError(
            "scene_turn_does_not_require_beat",
            evidence={"turn_kind": value.turn_kind.value},
        )
    outcome = _outcome(value)
    profiles = _profile_map(value)
    eligible = [
        option
        for option in value.options
        if _option_is_eligible(
            option, value=value, outcome=outcome, profiles=profiles
        )
    ]
    if not eligible:
        raise SceneResolutionError(
            "scene_no_eligible_consequence",
            evidence={
                "turn_kind": value.turn_kind.value,
                "outcome": outcome.value,
                "option_count": len(value.options),
            },
        )
    selected = sorted(eligible, key=lambda item: (-item.priority, item.option_id))[0]
    input_sha256 = _sha256(value)
    payload = {
        "protocol": "scene-beat-resolution-v1",
        "policy": RESOLUTION_POLICY,
        "session_id": value.session_id,
        "operation_id": value.operation_id,
        "turn_id": value.turn_id,
        "base_revision": value.base_revision,
        "selected_option_id": selected.option_id,
        "beat_kind": selected.beat_kind.value,
        "outcome": outcome.value,
        "effect_keys": list(selected.effect_keys),
        "guidance_keys": list(selected.guidance_keys),
        "observable_change": selected.observable_change,
        "npc_move": (
            selected.npc_move.model_dump(mode="json")
            if selected.npc_move is not None
            else None
        ),
        "open_threads": list(selected.open_threads),
        "resolve_threads": list(selected.resolve_threads),
        "transition_to": selected.transition_to,
        "pressure_before": value.pressure.value,
        "pressure_after": (selected.pressure_after or value.pressure).value,
        "constraints": [
            constraint.model_dump(mode="json") for constraint in selected.constraints
        ],
        "mechanical": (
            value.mechanical.model_dump(mode="json")
            if value.mechanical is not None
            else None
        ),
        "input_sha256": input_sha256,
    }
    resolution_sha256 = _sha256(payload)
    return SceneBeatResolution.model_validate(
        {**payload, "resolution_sha256": resolution_sha256}
    )


def verify_scene_beat_resolution(
    value: SceneResolutionInput, resolution: SceneBeatResolution
) -> SceneBeatResolution:
    """Recompute a provisional beat and reject any altered field or hash."""

    expected = resolve_scene_beat(value)
    if resolution != expected:
        raise SceneResolutionError(
            "scene_resolution_mismatch",
            evidence={
                "expected_sha256": expected.resolution_sha256,
                "received_sha256": resolution.resolution_sha256,
            },
        )
    return resolution


def validate_scene_proposal_against_beat(
    proposal: object, resolution: SceneBeatResolution
) -> None:
    """Validate deterministic fields without pretending to solve free semantics."""

    from .scene_director_service import SceneFactKind, SceneContinuationProposal

    candidate = SceneContinuationProposal.model_validate(proposal)
    if candidate.outcome != resolution.outcome.value:
        raise SceneResolutionError("scene_beat_outcome_mismatch")
    if resolution.effect_keys:
        required_effects = {value.casefold() for value in resolution.effect_keys}
        realized_effects = {value.casefold() for value in candidate.realized_effects}
        if not required_effects.issubset(realized_effects):
            raise SceneResolutionError("scene_beat_effect_omitted")
        if not realized_effects.issubset(required_effects):
            raise SceneResolutionError("scene_beat_unapproved_effect_claimed")
    if not set(resolution.open_threads).issubset(candidate.open_threads):
        raise SceneResolutionError("scene_beat_open_thread_omitted")
    if not set(resolution.resolve_threads).issubset(candidate.resolved_threads):
        raise SceneResolutionError("scene_beat_resolved_thread_omitted")
    if resolution.transition_to is not None:
        if candidate.location.casefold() != resolution.transition_to.casefold():
            raise SceneResolutionError("scene_beat_transition_mismatch")
        if not any(
            fact.kind is SceneFactKind.TRANSITION for fact in candidate.new_facts
        ):
            raise SceneResolutionError("scene_beat_transition_fact_omitted")

    visible_text = "\n".join(
        (
            candidate.narrative,
            candidate.scene_summary,
            candidate.player_prompt,
            *(fact.summary for fact in candidate.new_facts),
            *candidate.open_threads,
            *candidate.resolved_threads,
        )
    ).casefold()
    normalized_facts = {fact.summary.casefold() for fact in candidate.new_facts}
    if resolution.observable_change is not None:
        if resolution.effect_keys:
            if not candidate.new_facts:
                raise SceneResolutionError("scene_beat_observable_change_omitted")
        elif resolution.observable_change.casefold() not in normalized_facts:
            raise SceneResolutionError("scene_beat_observable_change_omitted")
    if resolution.npc_move is not None:
        if (
            not resolution.effect_keys
            and resolution.npc_move.action.casefold() not in normalized_facts
        ):
            raise SceneResolutionError("scene_beat_npc_move_omitted")
        matching_npc_action = any(
            fact.kind is SceneFactKind.NPC_ACTION
            and (
                bool(resolution.effect_keys)
                or fact.summary.casefold() == resolution.npc_move.action.casefold()
            )
            for fact in candidate.new_facts
        )
        if not matching_npc_action:
            raise SceneResolutionError("scene_beat_npc_action_fact_omitted")

    for constraint in resolution.constraints:
        normalized = constraint.summary.casefold()
        if constraint.kind == "must_show" and normalized not in visible_text:
            raise SceneResolutionError("scene_beat_required_content_omitted")
        if constraint.kind == "must_not_claim" and normalized in visible_text:
            raise SceneResolutionError("scene_beat_forbidden_content_claimed")
