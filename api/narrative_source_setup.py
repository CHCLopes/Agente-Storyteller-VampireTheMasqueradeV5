"""Pure setup intention and authored briefing for the bounded internal B trial.

The public request names a place, cast and declared objective. The server owns
session identity, eligible sheet/state, relationships and producer configuration;
those remain separate service arguments and are never included in this manifest.
The briefing is presentation, not model output, a historical fact or an action
chosen on the player's behalf. It is not projected into H6 as a narrative source.

Factories perform no I/O, RNG, clock read, reservation or campaign creation.
Origin/hash checks establish consistency, not authentication of the client,
authorship or database provenance. Persistence owns atomic creation and recovery.
"""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from .narrative_source_context import (
    SourceContextOrigin, create_source_context_origin,
    validate_source_context_origin, validate_source_scene,
)
from .narrative_source_entry import MAX_PLAYER_INPUT_CHARS
from .scene_service import SceneState

REQUEST_PROTOCOL = "narrative-source-setup-request-v1"
MANIFEST_PROTOCOL = "narrative-source-setup-manifest-v1"
MANIFEST_KEY = "narrative_source_setup_manifest"
MAX_LOCATION_CHARS = 160
MAX_NPC_NAME_CHARS = 80
MAX_NPCS = 8
MAX_OBJECTIVE_CHARS = MAX_PLAYER_INPUT_CHARS
_Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceSetupError(ValueError):
    """Closed diagnostic: never interpolate setup text or validation details."""

    def __init__(self, code: str = "source_setup_request_invalid"):
        self.code = code if type(code) is str and code in {
            "source_setup_request_invalid", "source_setup_manifest_invalid",
        } else "source_setup_request_invalid"
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


def _literal(value: object, maximum: int) -> str:
    if (type(value) is not str or not 1 <= len(value) <= maximum
            or not value.strip() or value != value.strip()):
        raise SourceSetupError()
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SourceSetupError() from None
    return value


def _fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _SetupModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
                              revalidate_instances="always", hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def preserve_forged_fields(cls, value: object) -> object:
        return _raw(value)


class SourceSetupRequest(_SetupModel):
    """Public setup only; an objective is intent, never evidence of success."""

    protocol: Literal["narrative-source-setup-request-v1"] = REQUEST_PROTOCOL
    location: Annotated[StrictStr, Field(min_length=1, max_length=MAX_LOCATION_CHARS)]
    npcs_present: tuple[StrictStr, ...] = Field(max_length=MAX_NPCS)
    declared_objective: Annotated[StrictStr, Field(min_length=1, max_length=MAX_OBJECTIVE_CHARS)]

    @field_validator("location", mode="before")
    @classmethod
    def literal_location(cls, value: object) -> str:
        return _literal(value, MAX_LOCATION_CHARS)

    @field_validator("npcs_present", mode="before")
    @classmethod
    def literal_cast(cls, value: object) -> tuple[str, ...]:
        if type(value) not in (tuple, list):
            raise SourceSetupError()
        return tuple(_literal(item, MAX_NPC_NAME_CHARS) for item in value)

    @field_validator("declared_objective", mode="before")
    @classmethod
    def literal_objective(cls, value: object) -> str:
        return _literal(value, MAX_OBJECTIVE_CHARS)

    @model_validator(mode="after")
    def exact_scene_labels(self) -> "SourceSetupRequest":
        scene = _seed_scene(self)
        # SceneState otherwise trims/deduplicates labels. Reject incompatible
        # input rather than silently changing the player's authored setup.
        if scene.location != self.location or scene.npcs_present != self.npcs_present:
            raise SourceSetupError()
        return self


def _seed_scene(request: SourceSetupRequest) -> SceneState:
    return SceneState(location=request.location, npcs_present=request.npcs_present,
                      summary="", details=(), open_threads=(), last_turn=0)


def _briefing(request: SourceSetupRequest) -> str:
    cast = "; ".join(request.npcs_present) if request.npcs_present else "nenhum NPC indicado"
    return (
        "Preparação autorada deste ensaio.\n"
        f"Local: {request.location}\n"
        f"Elenco presente: {cast}\n"
        "Objetivo declarado pelo jogador (intenção, não fato estabelecido):\n"
        f"{request.declared_objective}\n\n"
        "Recorte do ensaio interno: cena e elenco fixos, ficha sintética elegível; "
        "espera, conversa enquadrada e investigação ordinária. "
        "Escolha e envie sua própria ação para continuar."
    )


class SourceSetupManifest(_SetupModel):
    """Revalidatable authored presentation, separate from narrative attribution."""

    protocol: Literal["narrative-source-setup-manifest-v1"] = MANIFEST_PROTOCOL
    kind: Literal["authored_trial_setup"] = "authored_trial_setup"
    request: SourceSetupRequest
    origin: SourceContextOrigin
    briefing: StrictStr
    fingerprint_sha256: _Digest

    @field_validator("origin", mode="before")
    @classmethod
    def copied_origin(cls, value: object) -> SourceContextOrigin:
        # Its own contract checks the complete empty seed and origin fingerprint.
        return SourceContextOrigin.model_validate(value)

    @model_validator(mode="after")
    def bind_presentation(self) -> "SourceSetupManifest":
        validate_source_scene(_seed_scene(self.request), self.origin)
        if self.briefing != _briefing(self.request):
            raise SourceSetupError("source_setup_manifest_invalid")
        if self.fingerprint_sha256 != _fingerprint(
                self.model_dump(mode="json", exclude={"fingerprint_sha256"})):
            raise SourceSetupError("source_setup_manifest_invalid")
        return self


def validate_source_setup_request(value: object) -> SourceSetupRequest:
    """Validate decoded public fields without admitting server-owned extras."""
    try:
        if type(value) not in (dict, SourceSetupRequest):
            raise ValueError
        return SourceSetupRequest.model_validate(value)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceSetupError() from None


def validate_source_setup_manifest(value: object, *, session_id: str) -> SourceSetupManifest:
    """Copy/revalidate against the expected server session, without authenticating it."""
    try:
        if type(value) not in (dict, SourceSetupManifest):
            raise ValueError
        checked = SourceSetupManifest.model_validate(value)
        validate_source_context_origin(checked.origin, session_id=session_id)
        return checked
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceSetupError("source_setup_manifest_invalid") from None


def create_source_setup_manifest(request: SourceSetupRequest | dict[str, object], *,
                                 session_id: str) -> SourceSetupManifest:
    """Build an authored manifest only; the service supplies state/config separately."""
    checked = validate_source_setup_request(request)
    try:
        origin = create_source_context_origin(session_id, _seed_scene(checked))
        payload = {
            "protocol": MANIFEST_PROTOCOL, "kind": "authored_trial_setup",
            "request": checked.model_dump(mode="json"), "origin": origin.model_dump(mode="json"),
            "briefing": _briefing(checked),
        }
        return validate_source_setup_manifest(
            {**payload, "fingerprint_sha256": _fingerprint(payload)}, session_id=session_id,
        )
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceSetupError("source_setup_manifest_invalid") from None
