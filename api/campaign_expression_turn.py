"""Versioned binding of one admitted campaign source to a canonical turn."""
from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from .campaign_progression_service import build_campaign_narrator_packet
from .campaign_expression_capsule import CampaignExpressionCapsule
from .campaign_expression_context import SOURCE_POLICY
from .campaign_expression_profile import (
    CampaignExpressionProposal, create_campaign_expression_projection,
    validate_campaign_expression_proposal,
)
from .campaign_expression_rendering import ComposedProjection as SourceProjection, CampaignExpressionPresentation
from .narrative_source_turn import INVOCATION_OPERATION, _audit_digest
from .turn_models import CanonicalEvent, CanonicalFact, NarrativeRecord, Visibility

PROTOCOL = "campaign-expression-turn-v2"
CONTEXT_KEY = "campaign_expression"
_Id = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_Sha = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class CampaignExpressionTurnError(ValueError):
    def __init__(self, code: str = "campaign_expression_turn_invalid"):
        self.code = code
        super().__init__(code)


class CampaignExpressionTurnEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    protocol: Literal["campaign-expression-turn-v2"] = PROTOCOL
    operation_id: _Id
    original_operation_id: _Id
    attempt_id: _Id
    narrative_id: _Id
    question: StrictStr = Field(max_length=200)
    realized_effects: tuple[_Id, ...]
    projection: SourceProjection
    expression: CampaignExpressionProposal
    source_event_ids: tuple[_Id, ...]
    preparation_sha256: _Sha
    presentation_sha256: _Sha
    provenance_sha256: _Sha
    invocation_operation: Literal["H6.narrative_source"] = INVOCATION_OPERATION

    @model_validator(mode="after")
    def valid(self) -> "CampaignExpressionTurnEnvelope":
        if (self.projection.source.source_policy != SOURCE_POLICY
                or self.projection.source.visibility.value != "player"
                or self.presentation_sha256 != hashlib.sha256(
                    (self.projection.text + ("\n\n" + self.question if self.question else "")).encode("utf-8")
                ).hexdigest()
                or tuple(sorted(set(self.source_event_ids))) != self.source_event_ids
                or len(set(self.realized_effects)) != len(self.realized_effects)):
            raise ValueError("campaign source turn envelope mismatch")
        return self


def create_campaign_expression_turn_envelope(
    *, capsule: CampaignExpressionCapsule, proposal: CampaignExpressionPresentation,
    narrative: NarrativeRecord, invocation_id: str, provenance: Mapping,
    operation_id: str, attempt_id: str,
) -> CampaignExpressionTurnEnvelope:
    packet = build_campaign_narrator_packet(capsule.campaign_request, capsule.campaign_effect)
    projection = create_campaign_expression_projection(
        proposal, plan=capsule.realization_plan, packet=packet, facts=capsule.draft.facts,
        snapshot=capsule.snapshot, invocation_id=invocation_id,
        source_id="source-" + invocation_id,
        player_aliases=capsule.config.player_aliases,
        npc_aliases=capsule.config.npc_aliases,
    )
    return CampaignExpressionTurnEnvelope(
        operation_id=operation_id, original_operation_id=capsule.operation_id,
        attempt_id=attempt_id,
        narrative_id=narrative.narrative_id, question=proposal.player_prompt,
        realized_effects=proposal.realized_effects, projection=projection, expression=proposal.expression,
        source_event_ids=tuple(sorted(narrative.source_event_ids)),
        preparation_sha256=capsule.campaign_effect.effect_sha256,
        presentation_sha256=hashlib.sha256(proposal.player_text.encode("utf-8")).hexdigest(),
        provenance_sha256=_audit_digest(provenance, invocation_id, INVOCATION_OPERATION),
    )


def validate_campaign_expression_turn_commit(
    *, capsule: CampaignExpressionCapsule, envelope: CampaignExpressionTurnEnvelope | dict,
    narrative: NarrativeRecord | dict, provenance: Mapping,
    operation_id: str, attempt_id: str, expected_invocation_id: str,
    facts: object, events: object, memory_candidates: object = (),
    episodic_memories: object = (),
) -> CampaignExpressionTurnEnvelope:
    try:
        retained = CampaignExpressionCapsule.model_validate(capsule)
        checked = CampaignExpressionTurnEnvelope.model_validate(envelope)
        record = NarrativeRecord.model_validate(narrative)
        draft = retained.draft
        packet = build_campaign_narrator_packet(retained.campaign_request, retained.campaign_effect)
        if (checked.operation_id != operation_id
                or checked.original_operation_id != retained.operation_id
                or checked.attempt_id != attempt_id
                or checked.narrative_id != record.narrative_id
                or checked.projection.source.session_id != retained.session_id
                or checked.projection.source.turn_id != draft.turn_id
                or checked.projection.source.invocation_id != expected_invocation_id
                or record.invocation_id != expected_invocation_id
                or record.session_id != retained.session_id or record.turn_id != draft.turn_id
                or record.visibility is not Visibility.PLAYER
                or record.text != checked.projection.text + ("\n\n" + checked.question if checked.question else "")
                or tuple(sorted(record.source_event_ids)) != checked.source_event_ids
                or checked.source_event_ids != tuple(sorted(item.event_id for item in draft.events))
                or checked.preparation_sha256 != retained.campaign_effect.effect_sha256
                or checked.realized_effects != packet.required_effects
                or checked.question != retained.realization_plan.question
                or checked.provenance_sha256 != _audit_digest(
                    provenance, record.invocation_id, INVOCATION_OPERATION)
                or tuple(sorted((CanonicalFact.model_validate(item) for item in facts),
                                key=lambda item: item.fact_id)) != tuple(sorted(
                                    draft.facts, key=lambda item: item.fact_id))
                or tuple(CanonicalEvent.model_validate(item) for item in events) != draft.events
                or tuple(memory_candidates) or tuple(episodic_memories)):
            raise CampaignExpressionTurnError("campaign_expression_turn_mismatch")
        proposal = validate_campaign_expression_proposal(
            checked.expression, plan=retained.realization_plan, invocation_id=record.invocation_id,
            packet=packet, facts=draft.facts, snapshot=retained.snapshot,
            player_aliases=retained.config.player_aliases,
            npc_aliases=retained.config.npc_aliases,
        )
        if checked.projection != create_campaign_expression_projection(
                proposal, plan=retained.realization_plan, packet=packet, facts=draft.facts, snapshot=retained.snapshot,
                invocation_id=record.invocation_id, source_id="source-" + record.invocation_id,
                player_aliases=retained.config.player_aliases,
                npc_aliases=retained.config.npc_aliases):
            raise CampaignExpressionTurnError("campaign_expression_projection_mismatch")
        return checked
    except CampaignExpressionTurnError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, RecursionError, OverflowError):
        raise CampaignExpressionTurnError() from None
