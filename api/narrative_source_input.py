"""Pure, internal pre-receipt producer contracts; never a production authority.

The database must capture the original request and return a newly acquired claim
before server production. A validated/constructed claim cannot prove that event.
No transport, persistence, clock, RNG, classifier or gateway is invoked here.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictBool, StrictStr, field_validator, model_validator

from .llm.contract import GenerationParameters, LLMTarget
from .narrative_source_capsule import SourceTurnCapsule, source_preparation_operation_id, validate_source_turn_capsule
from .narrative_source_context import SourceContextSnapshot, validate_source_context_origin, validate_source_state_context
from .narrative_source_entry import validate_source_entry_snapshot, validate_source_player_action_request

PROTOCOL = "narrative-source-input-producer-v1"
REQUEST_KEY = "narrative_source_input"
COMPLETION_KEY = "narrative_source_input_completion"
_Identifier = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
_Status = Literal["pending", "completed", "failed", "timeout", "cancelled"]
_Terminal = Literal["completed", "failed", "timeout", "cancelled"]


class SourceInputError(ValueError):
    def __init__(self, code: str = "source_input_invalid"):
        self.code = code if type(code) is str and code in {
            "source_input_invalid", "source_input_config_invalid", "source_input_request_invalid",
            "source_input_completion_invalid", "source_input_claim_invalid", "source_input_secrets_forbidden",
        } else "source_input_invalid"
        super().__init__(self.code)


def _raw(value: object) -> object:
    if isinstance(value, BaseModel):
        raw = dict(value.__dict__)
        raw.update(value.__pydantic_extra__ or {})
        return {key: _raw(item) for key, item in raw.items()}
    if type(value) is dict:
        return {key: _raw(item) for key, item in value.items()}
    if type(value) is tuple:
        return tuple(_raw(item) for item in value)
    if type(value) is list:
        return [_raw(item) for item in value]
    return value


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identity(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or value != value.strip():
        raise SourceInputError()
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SourceInputError() from None
    return value


def source_input_operation_id(session_id: str, operation_id: str) -> str:
    return "source-input-operation-" + _sha([PROTOCOL, _identity(session_id), _identity(operation_id), "operation"])


def source_input_attempt_id(session_id: str, operation_id: str) -> str:
    return "source-input-attempt-" + _sha([PROTOCOL, _identity(session_id), _identity(operation_id), "attempt"])


def _json_copy(value: object) -> object:
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is str:
        value.encode("utf-8")
        return value
    if type(value) is list:
        return [_json_copy(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_json_copy(key): _json_copy(item) for key, item in value.items()}
    raise SourceInputError()


def _literal_model(model: type[BaseModel], value: object) -> BaseModel:
    raw = _raw(value)
    if type(raw) is not dict or set(raw) != set(model.model_fields):
        raise SourceInputError("source_input_config_invalid")
    checked = model.model_validate(raw, strict=True)
    if _canonical(raw) != _canonical(checked.model_dump(mode="json")):
        raise SourceInputError("source_input_config_invalid")
    return checked


class _InputModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", revalidate_instances="always", hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        return _raw(value)


class SourceProducerConfig(_InputModel):
    profile: Literal["source-local-ordinary-v1"] = "source-local-ordinary-v1"
    target: LLMTarget
    system_prompt: StrictStr = Field(repr=False)
    parameters: GenerationParameters
    player_aliases: tuple[StrictStr, ...] = ()
    npc_aliases: tuple[StrictStr, ...] = ()
    chronicle_name: StrictStr = ""

    @field_validator("target", mode="before")
    @classmethod
    def exact_target(cls, value: object) -> LLMTarget:
        return _literal_model(LLMTarget, value)

    @field_validator("parameters", mode="before")
    @classmethod
    def exact_parameters(cls, value: object) -> GenerationParameters:
        return _literal_model(GenerationParameters, value)

    @field_validator("player_aliases", "npc_aliases", mode="before")
    @classmethod
    def exact_aliases(cls, value: object) -> tuple[str, ...]:
        if type(value) not in (tuple, list):
            raise SourceInputError("source_input_config_invalid")
        return tuple(_identity(item) for item in value)

    @field_validator("system_prompt", "chronicle_name")
    @classmethod
    def utf8(cls, value: str) -> str:
        value.encode("utf-8")
        return value

    @model_validator(mode="after")
    def nonempty_system(self) -> "SourceProducerConfig":
        if not self.system_prompt.strip():
            raise SourceInputError("source_input_config_invalid")
        return self


def create_source_producer_config(*, target: LLMTarget, system_prompt: str,
        parameters: GenerationParameters, player_aliases: tuple[str, ...] = (),
        npc_aliases: tuple[str, ...] = (), chronicle_name: str = "",
        profile: str = "source-local-ordinary-v1", protected_secrets: tuple[str, ...] = ()) -> SourceProducerConfig:
    if type(protected_secrets) not in (tuple, list) or len(protected_secrets) != 0:
        raise SourceInputError("source_input_secrets_forbidden")
    try:
        return SourceProducerConfig(target=target, system_prompt=system_prompt, parameters=parameters,
            player_aliases=player_aliases, npc_aliases=npc_aliases, chronicle_name=chronicle_name, profile=profile)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceInputError("source_input_config_invalid") from None


class _RequestPayload(_InputModel):
    protocol: Literal["narrative-source-input-producer-v1"] = PROTOCOL
    session_id: _Identifier
    operation_id: _Identifier
    player_input: StrictStr = Field(repr=False)
    created_at: datetime
    snapshot: SourceContextSnapshot = Field(repr=False)
    state: dict[str, JsonValue] = Field(repr=False)
    relationships: dict[str, JsonValue] = Field(repr=False)
    config: SourceProducerConfig = Field(repr=False)

    @field_validator("created_at", mode="before")
    @classmethod
    def aware_time(cls, value: object) -> datetime:
        if type(value) is str:
            value = datetime.fromisoformat(value)
        if type(value) is not datetime or value.utcoffset() is None:
            raise SourceInputError("source_input_request_invalid")
        return value

    @field_validator("state", "relationships", mode="before")
    @classmethod
    def copied_json(cls, value: object) -> object:
        if type(value) is not dict:
            raise SourceInputError("source_input_request_invalid")
        return _json_copy(value)

    @model_validator(mode="after")
    def bind_request(self) -> "_RequestPayload":
        _identity(self.session_id)
        validate_source_player_action_request({"operation_id": self.operation_id, "player_input": self.player_input})
        origin = validate_source_context_origin(self.snapshot.origin, session_id=self.session_id)
        if self.snapshot.state_revision < self.snapshot.current_turn:
            raise SourceInputError("source_input_request_invalid")
        validate_source_state_context(self.state, origin)
        return self


class SourceInputRequest(_RequestPayload):
    fingerprint_sha256: _Digest

    @model_validator(mode="after")
    def fingerprint_matches(self) -> "SourceInputRequest":
        if self.fingerprint_sha256 != _sha(self.model_dump(mode="json", exclude={"fingerprint_sha256"})):
            raise SourceInputError("source_input_request_invalid")
        return self


def _checked_request(request: object) -> SourceInputRequest:
    try:
        if type(request) is not SourceInputRequest:
            raise ValueError
        return SourceInputRequest.model_validate(request)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceInputError("source_input_request_invalid") from None


def create_source_input_request(session_id: str, request: object, *, created_at: datetime,
        snapshot: SourceContextSnapshot, state: dict, relationships: dict,
        producer_config: SourceProducerConfig) -> SourceInputRequest:
    """The caller must supply base/time read by the future claim transaction."""
    try:
        public = validate_source_player_action_request(request)
        checked_snapshot = validate_source_entry_snapshot(snapshot, session_id=session_id)
        if type(producer_config) is not SourceProducerConfig:
            raise ValueError
        payload = _RequestPayload(session_id=session_id, operation_id=public.operation_id,
            player_input=public.player_input, created_at=created_at, snapshot=checked_snapshot,
            state=state, relationships=relationships, config=producer_config).model_dump(mode="json")
        return SourceInputRequest.model_validate({**payload, "fingerprint_sha256": _sha(payload)})
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceInputError("source_input_request_invalid") from None


class SourceInputFailure(_InputModel):
    code: Literal["source_input_out_of_scope", "source_input_clarification_required",
        "source_input_base_mismatch", "source_input_production_failed",
        "source_input_cancelled", "source_input_deadline_exceeded", "process_interrupted"]
    stage: Literal["preflight", "classification", "resolution", "production", "finalization"] | None = None


class SourceInputCompletion(_InputModel):
    """Bound to the attempts request hash, not the request-body fingerprint.

    The K hash here is consistency data; the database must still validate K.
    """
    request_sha256: _Digest
    status: _Terminal
    capsule_operation_id: _Identifier | None = None
    capsule_sha256: _Digest | None = None
    failure: SourceInputFailure | None = None

    @model_validator(mode="after")
    def terminal_shape(self) -> "SourceInputCompletion":
        if self.status == "completed":
            if self.capsule_operation_id is None or self.capsule_sha256 is None or self.failure is not None:
                raise SourceInputError("source_input_completion_invalid")
            _identity(self.capsule_operation_id)
        elif self.capsule_operation_id is not None or self.capsule_sha256 is not None or self.failure is None:
            raise SourceInputError("source_input_completion_invalid")
        else:
            expected = {"source_input_cancelled": "cancelled", "process_interrupted": "cancelled",
                        "source_input_deadline_exceeded": "timeout"}.get(self.failure.code, "failed")
            if self.status != expected:
                raise SourceInputError("source_input_completion_invalid")
        return self


def _checked_completion(request: SourceInputRequest, completion: object) -> SourceInputCompletion:
    try:
        if type(completion) is not SourceInputCompletion:
            raise ValueError
        checked = SourceInputCompletion.model_validate(completion)
        if checked.request_sha256 != source_input_request_hash(request):
            raise ValueError
        if checked.status == "completed" and checked.capsule_operation_id != source_preparation_operation_id(request.session_id, request.operation_id):
            raise ValueError
        return checked
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceInputError("source_input_completion_invalid") from None


def create_source_input_completion(request: SourceInputRequest, *, status: _Terminal,
        capsule: SourceTurnCapsule | None = None, failure: SourceInputFailure | None = None) -> SourceInputCompletion:
    checked = _checked_request(request)
    try:
        capsule_operation_id = capsule_sha256 = None
        if status == "completed":
            if type(capsule) is not SourceTurnCapsule or failure is not None:
                raise ValueError
            retained = validate_source_turn_capsule(capsule, session_id=checked.session_id, operation_id=checked.operation_id)
            bound = {"snapshot": checked.snapshot.model_dump(mode="json"), "created_at": checked.created_at.isoformat().replace("+00:00", "Z"),
                     "player_input": checked.player_input, "state": checked.state, "relationships": checked.relationships,
                     **checked.config.model_dump(mode="json", exclude={"profile"})}
            actual = retained.model_dump(mode="json")
            if _canonical(bound) != _canonical({key: actual[key] for key in bound}):
                raise ValueError
            capsule_operation_id = source_preparation_operation_id(checked.session_id, checked.operation_id)
            capsule_sha256 = retained.fingerprint_sha256
        elif capsule is not None:
            raise ValueError
        return SourceInputCompletion(request_sha256=source_input_request_hash(checked), status=status,
            capsule_operation_id=capsule_operation_id, capsule_sha256=capsule_sha256, failure=failure)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceInputError("source_input_completion_invalid") from None


class SourceInputClaim(_InputModel):
    """Observation of a claim response, not a serializable authorization token.

    The future service must consume only the direct database return of a new
    transaction. Validating or constructing newly_claimed=True proves nothing.
    """
    request: SourceInputRequest = Field(repr=False)
    status: _Status
    newly_claimed: StrictBool
    completion: SourceInputCompletion | None = None

    @model_validator(mode="after")
    def observed_state(self) -> "SourceInputClaim":
        if self.status == "pending":
            if self.completion is not None:
                raise SourceInputError("source_input_claim_invalid")
        elif (self.newly_claimed or self.completion is None or self.completion.status != self.status):
            raise SourceInputError("source_input_claim_invalid")
        if self.completion is not None:
            _checked_completion(self.request, self.completion)
        return self


def source_input_request_metadata(request: SourceInputRequest) -> dict:
    return {REQUEST_KEY: _checked_request(request).model_dump(mode="json")}


def source_input_request_hash(request: SourceInputRequest) -> str:
    checked = _checked_request(request)
    return _sha({"requested_turn": checked.snapshot.current_turn + 1,
                 "user_input": checked.player_input, "metadata": source_input_request_metadata(checked)})


def source_input_completion_metadata(request: SourceInputRequest, completion: SourceInputCompletion) -> dict:
    checked = _checked_request(request)
    result = _checked_completion(checked, completion)
    return {**source_input_request_metadata(checked), COMPLETION_KEY: result.model_dump(mode="json")}


def source_input_result_hash(request: SourceInputRequest, completion: SourceInputCompletion) -> str:
    """Hash a new P terminal result in the existing attempts payload formats.

    Existing process recovery preserves initial metadata and a legacy error
    payload. Persistence must separately verify that observed legacy format;
    this function never rewrites its historical metadata or diagnostic bytes.
    """
    checked = _checked_request(request)
    result = _checked_completion(checked, completion)
    payload = {"status": result.status, "requested_turn": checked.snapshot.current_turn + 1,
               "user_input": checked.player_input, "metadata": source_input_completion_metadata(checked, result),
               "provenance": None, "usage": None}
    if result.status == "completed":
        payload["snapshot"] = None
    else:
        payload.update(partial_narrative="", error=result.failure.model_dump(mode="json"))
    return _sha(payload)
