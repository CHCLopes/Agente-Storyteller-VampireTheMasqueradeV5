"""Retained preparation for the opt-in campaign B profile; never a commit grant."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictStr, model_validator

from .campaign_progression_service import (
    CampaignPreparedEffect, CampaignProgressionRequest, verify_campaign_prepared_effect,
)
from .campaign_source_context import CampaignSourceSnapshot
from .campaign_source_preparation import prepare_campaign_source_turn_draft
from .llm.contract import GenerationParameters, LLMTarget
from .narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation
from .narrative_source_context import validate_source_state_context
from .turn_models import TurnDraft

PROTOCOL = "campaign-source-capsule-v1"
CAPSULE_KEY = "campaign_source_capsule"
PROFILE = "campaign-source-local-v1"
_Sha = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class CampaignSourceCapsuleError(ValueError):
    def __init__(self, code: str = "campaign_source_capsule_invalid"):
        self.code = code
        super().__init__(code)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class CampaignSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    profile: Literal["campaign-source-local-v1"] = PROFILE
    target: LLMTarget
    system_prompt: StrictStr = Field(repr=False)
    parameters: GenerationParameters
    player_aliases: tuple[StrictStr, ...] = ()
    npc_aliases: tuple[StrictStr, ...] = ()
    chronicle_name: StrictStr = ""

    @model_validator(mode="after")
    def valid(self) -> "CampaignSourceConfig":
        if not self.system_prompt.strip() or any(not value.strip() for value in
                                                 (*self.player_aliases, *self.npc_aliases)):
            raise ValueError("campaign source config invalid")
        return self


class CampaignSourceCapsule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always",
                              hide_input_in_errors=True)
    protocol: Literal["campaign-source-capsule-v1"] = PROTOCOL
    snapshot: CampaignSourceSnapshot = Field(repr=False)
    operation_id: StrictStr
    created_at: datetime
    player_input: StrictStr = Field(repr=False)
    action_preparation: DeclaredActionPreparation | ResolvedActionPreparation = Field(repr=False)
    campaign_request: CampaignProgressionRequest = Field(repr=False)
    campaign_effect: CampaignPreparedEffect = Field(repr=False)
    draft: TurnDraft = Field(repr=False)
    state: dict[str, JsonValue] = Field(repr=False)
    relationships: dict[str, JsonValue] = Field(repr=False)
    config: CampaignSourceConfig = Field(repr=False)
    fingerprint_sha256: _Sha

    @model_validator(mode="after")
    def bind_all(self) -> "CampaignSourceCapsule":
        try:
            if (not self.operation_id or self.operation_id != self.operation_id.strip()
                    or not self.player_input or self.player_input != self.player_input.strip()
                    or self.created_at.utcoffset() is None
                    or self.campaign_request.state != self.snapshot.progression
                    or self.campaign_request.session_id != self.snapshot.origin.scene_origin.session_id
                    or self.campaign_request.operation_id != self.operation_id
                    or self.campaign_request.player_input != self.player_input
                    or self.state.get("campaign_progression") != self.snapshot.progression.model_dump(mode="json")
                    or self.snapshot.current_turn != self.campaign_request.base_revision):
                raise ValueError
            verify_campaign_prepared_effect(self.campaign_request, self.campaign_effect)
            validate_source_state_context(self.state, self.snapshot.origin.scene_origin)
            expected = prepare_campaign_source_turn_draft(
                self.snapshot, operation_id=self.operation_id,
                created_at=self.created_at, player_input=self.player_input,
                action_preparation=self.action_preparation,
                campaign_request=self.campaign_request,
                campaign_effect=self.campaign_effect,
            )
            if (self.draft != expected
                    or self.fingerprint_sha256 != _sha(self.model_dump(mode="json", exclude={"fingerprint_sha256"}))):
                raise ValueError
        except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
            raise CampaignSourceCapsuleError() from None
        return self

    @property
    def session_id(self) -> str:
        return self.snapshot.origin.scene_origin.session_id


def create_campaign_source_capsule(
    *, snapshot: CampaignSourceSnapshot, operation_id: str, created_at: datetime,
    player_input: str, action_preparation: DeclaredActionPreparation | ResolvedActionPreparation,
    campaign_request: CampaignProgressionRequest, campaign_effect: CampaignPreparedEffect,
    state: dict, relationships: dict, config: CampaignSourceConfig,
) -> CampaignSourceCapsule:
    draft = prepare_campaign_source_turn_draft(
        snapshot, operation_id=operation_id, created_at=created_at,
        player_input=player_input, action_preparation=action_preparation,
        campaign_request=campaign_request, campaign_effect=campaign_effect,
    )
    payload = dict(protocol=PROTOCOL, snapshot=snapshot,
                   operation_id=operation_id, created_at=created_at,
                   player_input=player_input,
                   action_preparation=action_preparation,
                   campaign_request=campaign_request,
                   campaign_effect=campaign_effect,
                   draft=draft, state=state,
                   relationships=relationships, config=config)
    serialized = CampaignSourceCapsule.model_construct(
        **payload, fingerprint_sha256="0" * 64,
    ).model_dump(mode="json", exclude={"fingerprint_sha256"})
    return CampaignSourceCapsule.model_validate({**serialized, "fingerprint_sha256": _sha(serialized)})
