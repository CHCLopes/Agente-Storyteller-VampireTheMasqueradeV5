"""Versioned, opt-in context for the synthetic record campaign.

This is not an alias for the ordinary source v1 history. A snapshot is
consistent data; only the persistence reader can establish its provenance.
"""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from .campaign_progression_catalog import CONTENT_VERSION
from .campaign_progression_service import CampaignState
from .narrative_grounding import SourceProjection
from .narrative_source_context import SourceContextOrigin, validate_source_context_origin

ORIGIN_KEY = "campaign_source_origin"
ORIGIN_PROTOCOL = "campaign-source-origin-v1"
CONTEXT_PROTOCOL = "campaign-source-context-v1"
SOURCE_POLICY = "campaign-source-application-v1"
_Id = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_Sha = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class CampaignSourceContextError(ValueError):
    def __init__(self, code: str = "campaign_source_context_invalid"):
        self.code = code
        super().__init__(code)


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


class CampaignSourceOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    protocol: Literal["campaign-source-origin-v1"] = ORIGIN_PROTOCOL
    scene_origin: SourceContextOrigin
    content_version: Literal["record-at-risk.v1", "record-at-risk.v2"] = CONTENT_VERSION
    fingerprint_sha256: _Sha

    @model_validator(mode="after")
    def valid(self) -> "CampaignSourceOrigin":
        checked = validate_source_context_origin(self.scene_origin,
                                                 session_id=self.scene_origin.session_id)
        if (checked.seed_scene.location != "Arquivo"
                or checked.seed_scene.npcs_present != ("Mara",)
                or self.fingerprint_sha256 != _hash({
                    "protocol": self.protocol,
                    "scene_origin": checked.model_dump(mode="json"),
                    "content_version": self.content_version,
                })):
            raise ValueError("campaign source origin mismatch")
        return self


def create_campaign_source_origin(scene_origin: SourceContextOrigin, *,
                                 content_version: str = CONTENT_VERSION) -> CampaignSourceOrigin:
    checked = validate_source_context_origin(scene_origin, session_id=scene_origin.session_id)
    payload = {"protocol": ORIGIN_PROTOCOL, "scene_origin": checked.model_dump(mode="json"),
               "content_version": content_version}
    return CampaignSourceOrigin.model_validate({**payload, "fingerprint_sha256": _hash(payload)})


class CampaignSourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    origin: CampaignSourceOrigin
    current_turn: Annotated[StrictInt, Field(ge=0)]
    state_revision: Annotated[StrictInt, Field(ge=0)]
    progression: CampaignState
    sources: tuple[SourceProjection, ...] = Field(max_length=2)
    selected_turn_ids: tuple[_Id, ...] = Field(max_length=2)
    omitted_turn_ids: tuple[_Id, ...]

    @model_validator(mode="after")
    def valid(self) -> "CampaignSourceSnapshot":
        history = self.omitted_turn_ids + self.selected_turn_ids
        if (self.state_revision < self.current_turn
                or self.origin.content_version != self.progression.content_version
                or self.progression.revision != self.current_turn
                or len(history) != self.current_turn
                or len(set(history)) != len(history)
                or self.selected_turn_ids != history[-2:]
                or self.omitted_turn_ids != history[:-2]
                or tuple(item.source.turn_id for item in self.sources) != self.selected_turn_ids
                or any(item.source.session_id != self.origin.scene_origin.session_id
                       or item.source.source_policy != SOURCE_POLICY
                       or item.source.visibility.value not in {"public", "player"}
                       for item in self.sources)):
            raise ValueError("campaign source snapshot mismatch")
        return self

    @property
    def canonical_scene(self):
        return self.origin.scene_origin.seed_scene

    def audit_payload(self) -> dict[str, object]:
        return {"protocol": CONTEXT_PROTOCOL,
                "session_id": self.origin.scene_origin.session_id,
                "current_turn": self.current_turn,
                "state_revision": self.state_revision,
                "origin_sha256": self.origin.fingerprint_sha256,
                "selected_turn_ids": list(self.selected_turn_ids),
                "omitted_turn_ids": list(self.omitted_turn_ids)}
