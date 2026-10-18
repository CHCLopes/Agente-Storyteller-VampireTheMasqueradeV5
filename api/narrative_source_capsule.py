"""Persistible preparation data for the explicit, public source-only coordinator.

No runtime handles or protected-secret input belong to this model. Fingerprints
prove consistency, not authentication, freshness or semantic truth. Frozen
models own copies; boundaries revalidate inherited mutable JSON/model members.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictStr, field_validator, model_validator

from .llm.contract import GenerationParameters, LLMTarget
from .narrative_source_context import SourceContextSnapshot, validate_source_state_context
from .narrative_source_preparation import (
    DeclaredActionPreparation, ResolvedActionPreparation, prepare_source_turn_draft,
)
from .turn_models import TurnDraft

PROTOCOL = "narrative-source-capsule-v1"
CAPSULE_KEY = "narrative_source_capsule"
_CONTROL_DOMAIN = "narrative-source-preparation-control-v1"
_Preparation = Annotated[
    DeclaredActionPreparation | ResolvedActionPreparation, Field(discriminator="kind"),
]


class SourceCapsuleCode(str, Enum):
    INVALID = "source_capsule_invalid"
    IDENTITY_INVALID = "source_capsule_identity_invalid"
    SECRETS_FORBIDDEN = "source_capsule_secrets_forbidden"
    JSON_INVALID = "source_capsule_json_invalid"
    CONFIG_INVALID = "source_capsule_config_invalid"
    DRAFT_MISMATCH = "source_capsule_draft_mismatch"
    FINGERPRINT_MISMATCH = "source_capsule_fingerprint_mismatch"
    STORED_PAIR_INVALID = "source_capsule_stored_pair_invalid"
    HISTORY_MISMATCH = "source_capsule_history_mismatch"
    BASE_MISMATCH = "source_capsule_base_mismatch"
    OPERATION_ALREADY_STARTED = "source_capsule_operation_already_started"


class SourceCapsuleError(ValueError):
    def __init__(self, code: SourceCapsuleCode | str):
        try:
            self.code = SourceCapsuleCode(code).value
        except (TypeError, ValueError):
            self.code = SourceCapsuleCode.INVALID.value
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


def _json_default(value: object) -> str:
    if type(value) is datetime:
        return value.isoformat().replace("+00:00", "Z")
    raise TypeError


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, default=_json_default)


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identity(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or value != value.strip():
        raise SourceCapsuleError(SourceCapsuleCode.IDENTITY_INVALID)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SourceCapsuleError(SourceCapsuleCode.IDENTITY_INVALID) from None
    return value


def source_preparation_operation_id(session_id: str, operation_id: str) -> str:
    return "source-preparation-operation-" + _sha([
        _CONTROL_DOMAIN, _identity(session_id), _identity(operation_id), "operation",
    ])


def source_preparation_attempt_id(session_id: str, operation_id: str) -> str:
    return "source-preparation-attempt-" + _sha([
        _CONTROL_DOMAIN, _identity(session_id), _identity(operation_id), "attempt",
    ])


def _json_value(value: object) -> object:
    # Do not stringify keys, coerce containers or serialize arbitrary handles.
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is str:
        value.encode("utf-8")
        return value
    if type(value) is list:
        return [_json_value(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_json_value(key): _json_value(item) for key, item in value.items()}
    raise SourceCapsuleError(SourceCapsuleCode.JSON_INVALID)


def _literal_model(model: type[BaseModel], value: object) -> BaseModel:
    raw = _raw(value)
    if type(raw) is not dict or set(raw) != set(model.model_fields):
        raise SourceCapsuleError(SourceCapsuleCode.CONFIG_INVALID)
    checked = model.model_validate(raw, strict=True)
    if _canonical(raw) != _canonical(checked.model_dump(mode="json")):
        raise SourceCapsuleError(SourceCapsuleCode.CONFIG_INVALID)
    return checked


class _CapsulePayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always",
                              hide_input_in_errors=True)
    protocol: Literal["narrative-source-capsule-v1"] = PROTOCOL
    snapshot: SourceContextSnapshot = Field(repr=False)
    operation_id: StrictStr
    created_at: datetime
    player_input: StrictStr = Field(repr=False)
    preparation: _Preparation = Field(repr=False)
    draft: TurnDraft = Field(repr=False)
    state: dict[str, JsonValue] = Field(repr=False)
    relationships: dict[str, JsonValue] = Field(repr=False)
    target: LLMTarget
    system_prompt: StrictStr = Field(repr=False)
    parameters: GenerationParameters
    player_aliases: tuple[StrictStr, ...] = Field(default=(), repr=False)
    npc_aliases: tuple[StrictStr, ...] = Field(default=(), repr=False)
    chronicle_name: StrictStr = Field(default="", repr=False)

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            raw = dict(value.__dict__)
            raw.update(value.__pydantic_extra__ or {})
            return raw
        return value

    @field_validator("operation_id")
    @classmethod
    def literal_operation(cls, value: str) -> str:
        return _identity(value)

    @field_validator("created_at", mode="before")
    @classmethod
    def aware_timestamp(cls, value: object) -> datetime:
        # ISO text is needed for persisted JSON, never numeric epoch coercion.
        if type(value) is str:
            value = datetime.fromisoformat(value)
        if type(value) is not datetime or value.utcoffset() is None:
            raise SourceCapsuleError(SourceCapsuleCode.INVALID)
        return value

    @field_validator("state", "relationships", mode="before")
    @classmethod
    def copied_json_object(cls, value: object) -> object:
        if type(value) is not dict:
            raise SourceCapsuleError(SourceCapsuleCode.JSON_INVALID)
        return _json_value(value)

    @field_validator("target", mode="before")
    @classmethod
    def literal_target(cls, value: object) -> LLMTarget:
        return _literal_model(LLMTarget, value)

    @field_validator("parameters", mode="before")
    @classmethod
    def literal_parameters(cls, value: object) -> GenerationParameters:
        return _literal_model(GenerationParameters, value)

    @field_validator("draft", mode="before")
    @classmethod
    def literal_draft(cls, value: object) -> TurnDraft:
        raw = _raw(value)
        if type(raw) is not dict:
            raise SourceCapsuleError(SourceCapsuleCode.DRAFT_MISMATCH)
        checked = TurnDraft.model_validate(raw)
        if _canonical(raw) != _canonical(checked.model_dump(mode="json")):
            raise SourceCapsuleError(SourceCapsuleCode.DRAFT_MISMATCH)
        return checked

    @field_validator("player_aliases", "npc_aliases", mode="before")
    @classmethod
    def ordered_aliases(cls, value: object) -> tuple[str, ...]:
        if type(value) not in (list, tuple):
            raise SourceCapsuleError(SourceCapsuleCode.CONFIG_INVALID)
        return tuple(_identity(item) for item in value)

    @field_validator("system_prompt", "chronicle_name")
    @classmethod
    def utf8_text(cls, value: str) -> str:
        value.encode("utf-8")
        return value

    @model_validator(mode="after")
    def bind_preparation(self) -> "_CapsulePayload":
        if not self.system_prompt.strip():
            raise SourceCapsuleError(SourceCapsuleCode.CONFIG_INVALID)
        expected = prepare_source_turn_draft(
            self.snapshot, operation_id=self.operation_id, created_at=self.created_at,
            player_input=self.player_input, preparation=self.preparation,
        )
        if _canonical(self.draft.model_dump(mode="json")) != _canonical(expected.model_dump(mode="json")):
            raise SourceCapsuleError(SourceCapsuleCode.DRAFT_MISMATCH)
        validate_source_state_context(self.state, self.snapshot.origin)
        return self


class SourceTurnCapsule(_CapsulePayload):
    fingerprint_sha256: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def fingerprint_matches(self) -> "SourceTurnCapsule":
        if self.fingerprint_sha256 != _sha(self.model_dump(mode="json", exclude={"fingerprint_sha256"})):
            raise SourceCapsuleError(SourceCapsuleCode.FINGERPRINT_MISMATCH)
        return self

    @property
    def session_id(self) -> str:
        return self.snapshot.origin.session_id

    @property
    def canonical_scene(self):
        return SourceContextSnapshot.model_validate(self.snapshot).canonical_scene


def validate_source_turn_capsule(value: object, *, session_id: str, operation_id: str) -> SourceTurnCapsule:
    session, operation = _identity(session_id), _identity(operation_id)
    try:
        checked = SourceTurnCapsule.model_validate(value)
        if checked.snapshot.origin.session_id != session or checked.operation_id != operation:
            raise SourceCapsuleError(SourceCapsuleCode.IDENTITY_INVALID)
        return checked
    except SourceCapsuleError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        raise SourceCapsuleError(SourceCapsuleCode.INVALID) from None


def create_source_turn_capsule(
    snapshot: SourceContextSnapshot, *, operation_id: str, created_at: datetime,
    player_input: str, preparation: DeclaredActionPreparation | ResolvedActionPreparation,
    state: dict, relationships: dict, target: LLMTarget, system_prompt: str,
    parameters: GenerationParameters, player_aliases: tuple[str, ...] = (),
    npc_aliases: tuple[str, ...] = (), chronicle_name: str = "",
    protected_secrets: tuple[str, ...] = (),
) -> SourceTurnCapsule:
    if type(protected_secrets) not in (tuple, list) or len(protected_secrets) != 0:
        raise SourceCapsuleError(SourceCapsuleCode.SECRETS_FORBIDDEN)
    try:
        draft = prepare_source_turn_draft(
            snapshot, operation_id=operation_id, created_at=created_at,
            player_input=player_input, preparation=preparation,
        )
        payload = _CapsulePayload(
            snapshot=snapshot, operation_id=operation_id, created_at=created_at,
            player_input=player_input, preparation=preparation, draft=draft,
            state=state, relationships=relationships, target=target,
            system_prompt=system_prompt, parameters=parameters,
            player_aliases=player_aliases, npc_aliases=npc_aliases, chronicle_name=chronicle_name,
        ).model_dump(mode="json")
        return validate_source_turn_capsule(
            {**payload, "fingerprint_sha256": _sha(payload)},
            session_id=snapshot.origin.session_id, operation_id=operation_id,
        )
    except SourceCapsuleError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        raise SourceCapsuleError(SourceCapsuleCode.INVALID) from None
