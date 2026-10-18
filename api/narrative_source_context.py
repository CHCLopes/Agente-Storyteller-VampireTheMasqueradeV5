"""Pure origin and selection contracts for an explicitly created source context.

Fingerprints establish identity and consistency, not authentication of the
server or semantic truth. No legacy save is made eligible by these factories.
The persistence boundary owns new-campaign creation, history and producer checks.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from .narrative_source_turn import NarrativeSourceTurnEnvelope
from .scene_service import SceneState

ORIGIN_PROTOCOL = "narrative-source-context-origin-v1"
ORIGIN_KEY = "narrative_source_origin"
SELECTION_PROTOCOL = "narrative-source-context-selection-v1"
SELECTION_KEY = "narrative_source_context"
SELECTION_POLICY = "required_recent_two"
MAX_SOURCES = 2
_Identifier = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceContextCode(str, Enum):
    INVALID = "source_context_invalid"
    ORIGIN_INVALID = "source_context_origin_invalid"
    ORIGIN_MISSING = "source_context_origin_missing"
    IDENTITY_MISMATCH = "source_context_identity_mismatch"
    SCENE_INVALID = "source_context_scene_invalid"
    SCENE_MISMATCH = "source_context_scene_mismatch"
    STATE_INCOMPATIBLE = "source_context_state_incompatible"
    SNAPSHOT_INVALID = "source_context_snapshot_invalid"
    SELECTION_INVALID = "source_context_selection_invalid"
    CAMPAIGN_EXISTS = "source_context_campaign_exists"
    CAMPAIGN_MISSING = "source_context_campaign_missing"
    QUERY_INVALID = "source_context_query_invalid"
    REVISION_MISMATCH = "source_context_revision_mismatch"
    HISTORY_INCOMPATIBLE = "source_context_history_incompatible"
    STORED_PAIR_MISMATCH = "source_context_stored_pair_mismatch"
    DEPENDENCIES_FORBIDDEN = "source_context_dependencies_forbidden"
    ORIGIN_MUTATION_FORBIDDEN = "source_context_origin_mutation_forbidden"
    COMMIT_CONTRACT_REQUIRED = "source_context_commit_contract_required"


class SourceContextError(ValueError):
    def __init__(self, code: SourceContextCode | str):
        try:
            self.code = SourceContextCode(code).value
        except (ValueError, TypeError):
            self.code = SourceContextCode.INVALID.value
        super().__init__(self.code)


def _unpack(value: object) -> object:
    if isinstance(value, BaseModel):
        raw = dict(value.__dict__)
        raw.update(value.__pydantic_extra__ or {})
        return {key: _unpack(item) for key, item in raw.items()}
    if isinstance(value, Mapping):
        return {key: _unpack(item) for key, item in value.items()}
    if type(value) in (list, tuple):
        return [_unpack(item) for item in value]
    return value


def _identifier(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or value != value.strip():
        raise SourceContextError(SourceContextCode.IDENTITY_MISMATCH)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SourceContextError(SourceContextCode.IDENTITY_MISMATCH) from None
    return value


def _ordered_ids(value: object) -> tuple[str, ...]:
    if type(value) not in (list, tuple):
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    ids = tuple(_identifier(item) for item in value)
    if len(ids) != len(set(ids)):
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    return ids


def _strict_scene(value: object) -> SceneState:
    try:
        if type(value) not in (SceneState, dict):
            raise ValueError
        raw = _unpack(value)
        if type(raw) is not dict or type(raw.get("location")) is not str:
            raise ValueError
        if type(raw.get("npcs_present", ())) not in (list, tuple):
            raise ValueError
        if (raw.get("summary", "") != ""
                or raw.get("details", ()) not in ([], ())
                or raw.get("open_threads", ()) not in ([], ())
                or type(raw.get("last_turn", 0)) is not int
                or raw.get("last_turn", 0) != 0):
            raise ValueError
        scene = SceneState.model_validate(raw)
        if (raw["location"] != scene.location
                or tuple(raw.get("npcs_present", ())) != scene.npcs_present):
            raise ValueError
        # Exact labels and order belong to this seed's identity. Casefold
        # membership used by a gameplay policy does not rewrite the seed.
        for label in (scene.location, *scene.npcs_present):
            _identifier(label)
        return scene
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceContextError(SourceContextCode.SCENE_INVALID) from None


def _fingerprint(session_id: str, scene: SceneState) -> str:
    payload = {
        "protocol": ORIGIN_PROTOCOL, "creator": "explicit_server_seed",
        "session_id": session_id, "seed_scene": scene.model_dump(mode="json"),
    }
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
    except (ValueError, TypeError, UnicodeError):
        raise SourceContextError(SourceContextCode.ORIGIN_INVALID) from None


class _Immutable(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        return _unpack(value)


class SourceContextOrigin(_Immutable):
    protocol: Literal["narrative-source-context-origin-v1"] = ORIGIN_PROTOCOL
    creator: Literal["explicit_server_seed"] = "explicit_server_seed"
    session_id: _Identifier
    seed_scene: SceneState
    fingerprint_sha256: _Digest

    @field_validator("session_id")
    @classmethod
    def literal_session(cls, value: str) -> str:
        return _identifier(value)

    @field_validator("seed_scene", mode="before")
    @classmethod
    def eligible_scene(cls, value: object) -> SceneState:
        return _strict_scene(value)

    @model_validator(mode="after")
    def fingerprint_matches(self) -> "SourceContextOrigin":
        if self.fingerprint_sha256 != _fingerprint(self.session_id, self.seed_scene):
            raise SourceContextError(SourceContextCode.ORIGIN_INVALID)
        return self


def create_source_context_origin(session_id: str, scene: SceneState) -> SourceContextOrigin:
    identity = _identifier(session_id)
    seed = _strict_scene(scene)
    return validate_source_context_origin({
        "session_id": identity, "seed_scene": seed,
        "fingerprint_sha256": _fingerprint(identity, seed),
    }, session_id=identity)


def validate_source_context_origin(value: object, *, session_id: str) -> SourceContextOrigin:
    identity = _identifier(session_id)
    if value is None:
        raise SourceContextError(SourceContextCode.ORIGIN_MISSING)
    try:
        checked = SourceContextOrigin.model_validate(value)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceContextError(SourceContextCode.ORIGIN_INVALID) from None
    if checked.session_id != identity:
        raise SourceContextError(SourceContextCode.IDENTITY_MISMATCH)
    return checked


def _origin(value: SourceContextOrigin) -> SourceContextOrigin:
    if type(value) is not SourceContextOrigin or not hasattr(value, "session_id"):
        raise SourceContextError(SourceContextCode.ORIGIN_INVALID)
    return validate_source_context_origin(value, session_id=value.session_id)


def validate_source_scene(scene: object, origin: SourceContextOrigin) -> SceneState:
    checked_origin = _origin(origin)
    checked = _strict_scene(scene)
    if checked.model_dump(mode="json") != checked_origin.seed_scene.model_dump(mode="json"):
        raise SourceContextError(SourceContextCode.SCENE_MISMATCH)
    return checked_origin.seed_scene


# Only these established state envelopes are inspected. Character attributes,
# equipment and other opaque state are neither interpreted nor exported to H6.
_NARRATIVE_KEYS = frozenset({
    "narrative_source", "narrative_source_context", "narrative_history",
    "summary", "scene_summary", "details", "open_threads", "resolved_threads",
    "memory_context", "context_packet", "packet", "episodic_memories",
    "memory_candidates", "consolidations", "facts", "new_facts",
    "attributed_sources",
})


def validate_source_state_context(state: object, origin: SourceContextOrigin) -> None:
    checked_origin = _origin(origin)
    if type(state) is not dict:
        raise SourceContextError(SourceContextCode.STATE_INCOMPATIBLE)
    nodes = [state]
    for name in ("context", "player_sheet"):
        if name in state:
            if type(state[name]) is not dict:
                raise SourceContextError(SourceContextCode.STATE_INCOMPATIBLE)
            nodes.append(state[name])
    for node in nodes:
        if "scene" in node:
            validate_source_scene(node["scene"], checked_origin)
        if "location" in node and (
            type(node["location"]) is not str
            or node["location"] != checked_origin.seed_scene.location
        ):
            raise SourceContextError(SourceContextCode.SCENE_MISMATCH)
        if "npcs_present" in node and (
            type(node["npcs_present"]) not in (list, tuple)
            or any(type(item) is not str for item in node["npcs_present"])
            or tuple(node["npcs_present"]) != checked_origin.seed_scene.npcs_present
        ):
            raise SourceContextError(SourceContextCode.SCENE_MISMATCH)
        for key in _NARRATIVE_KEYS & node.keys():
            value = node[key]
            # Only literal empty containers/text count as absent dependencies.
            if not ((type(value) in (dict, list, tuple, str)) and len(value) == 0):
                raise SourceContextError(SourceContextCode.STATE_INCOMPATIBLE)


def _selection(origin: SourceContextOrigin, current_turn: int, state_revision: int,
               history_turn_ids: object) -> dict[str, object]:
    checked = _origin(origin)
    if (type(current_turn) is not int or current_turn < 0
            or type(state_revision) is not int or state_revision < 0):
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    history = _ordered_ids(history_turn_ids)
    if len(history) != current_turn:
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    return {
        "protocol": SELECTION_PROTOCOL, "session_id": checked.session_id,
        "current_turn": current_turn, "state_revision": state_revision,
        "origin_sha256": checked.fingerprint_sha256,
        "selected_turn_ids": list(history[-MAX_SOURCES:]),
        "omitted_turn_ids": list(history[:-MAX_SOURCES]),
        "selection_policy": SELECTION_POLICY,
    }


def validate_source_selection(value: object, *, origin: SourceContextOrigin,
                              current_turn: int, state_revision: int,
                              history_turn_ids: object) -> dict[str, object]:
    expected = _selection(origin, current_turn, state_revision, history_turn_ids)
    if type(value) is not dict or set(value) != set(expected):
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    # JSON equality alone would accept True == 1 or tuples in a persisted list.
    if any(type(value[key]) is not type(expected[key]) for key in expected):
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    for key in ("selected_turn_ids", "omitted_turn_ids"):
        _ordered_ids(value[key])
    if value != expected:
        raise SourceContextError(SourceContextCode.SELECTION_INVALID)
    return expected


class SourceContextSnapshot(_Immutable):
    origin: SourceContextOrigin
    current_turn: Annotated[StrictInt, Field(ge=0)]
    state_revision: Annotated[StrictInt, Field(ge=0)]
    sources: tuple[NarrativeSourceTurnEnvelope, ...] = Field(max_length=MAX_SOURCES)
    selected_turn_ids: tuple[_Identifier, ...] = Field(max_length=MAX_SOURCES)
    omitted_turn_ids: tuple[_Identifier, ...]

    @field_validator("sources", mode="before")
    @classmethod
    def ordered_sources(cls, value: object) -> object:
        if type(value) not in (list, tuple):
            raise SourceContextError(SourceContextCode.SNAPSHOT_INVALID)
        return value

    @field_validator("selected_turn_ids", "omitted_turn_ids", mode="before")
    @classmethod
    def ordered_ids(cls, value: object) -> tuple[str, ...]:
        return _ordered_ids(value)

    @model_validator(mode="after")
    def match_selection(self) -> "SourceContextSnapshot":
        history = self.omitted_turn_ids + self.selected_turn_ids
        expected = _selection(self.origin, self.current_turn, self.state_revision, history)
        actual_ids = tuple(item.projection.source.turn_id for item in self.sources)
        if (actual_ids != self.selected_turn_ids
                or list(self.selected_turn_ids) != expected["selected_turn_ids"]
                or any(item.projection.source.session_id != self.origin.session_id
                       for item in self.sources)):
            raise SourceContextError(SourceContextCode.SNAPSHOT_INVALID)
        for field in ("source_id", "invocation_id"):
            ids = [getattr(item.projection.source, field) for item in self.sources]
            if len(ids) != len(set(ids)):
                raise SourceContextError(SourceContextCode.SNAPSHOT_INVALID)
        return self

    @property
    def canonical_scene(self) -> SceneState:
        return _origin(self.origin).seed_scene

    def audit_payload(self) -> dict[str, object]:
        checked = SourceContextSnapshot.model_validate(self)
        return _selection(checked.origin, checked.current_turn, checked.state_revision,
                          checked.omitted_turn_ids + checked.selected_turn_ids)
