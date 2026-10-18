"""Pure, opt-in staging of a campaign effect beside the original B action.

The returned draft is deliberately not accepted by source-local-ordinary-v1.
No caller may commit or narrate it until the versioned B capsule, admission and
storage transaction validate the same retained operation and campaign state.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from .campaign_progression_service import (
    CampaignPreparedEffect, CampaignProgressionRequest,
    verify_campaign_prepared_effect,
)
from .narrative_source_context import SourceContextSnapshot
from .campaign_source_context import CampaignSourceSnapshot
from .narrative_source_preparation import (
    DeclaredActionPreparation, ResolvedActionPreparation, prepare_source_turn_draft,
)
from .scene_resolution_service import mechanical_resolution_from_result
from .turn_models import (
    CanonicalEvent, CanonicalFact, RecordReference, StateChange, TurnDraft, Visibility,
)

PROTOCOL = "campaign-source-preparation-v1"
PRODUCER = "campaign_source_preparation.prepare_campaign_source_turn_draft"


class CampaignSourcePreparationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _id(session_id: str, operation_id: str, role: str) -> str:
    encoded = json.dumps([PROTOCOL, session_id, operation_id, role],
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return role + "-" + hashlib.sha256(encoded).hexdigest()


def prepare_campaign_source_turn_draft(
    snapshot: SourceContextSnapshot | CampaignSourceSnapshot, *, operation_id: str, created_at: datetime,
    player_input: str,
    action_preparation: DeclaredActionPreparation | ResolvedActionPreparation,
    campaign_request: CampaignProgressionRequest,
    campaign_effect: CampaignPreparedEffect,
) -> TurnDraft:
    """Bind an already prepared effect; never classify, roll, or mutate state."""
    try:
        base = prepare_source_turn_draft(
            snapshot, operation_id=operation_id, created_at=created_at,
            player_input=player_input, preparation=action_preparation,
        )
        request = CampaignProgressionRequest.model_validate(campaign_request)
        effect = verify_campaign_prepared_effect(request, campaign_effect)
        if (request.session_id != base.session_id
                or request.operation_id != operation_id
                or request.turn_id != base.turn_id
                or request.player_input != player_input
                or request.base_revision != request.state.revision
                or request.base_revision != snapshot.current_turn
                or effect.after_state.revision != snapshot.current_turn + 1):
            raise ValueError
        if type(action_preparation) is ResolvedActionPreparation:
            expected = mechanical_resolution_from_result(
                action_preparation.resolution, source_fact_id=base.facts[0].fact_id,
            )
            if request.mechanical != expected or effect.mechanical != expected:
                raise ValueError
        elif type(action_preparation) is DeclaredActionPreparation:
            if request.mechanical is not None or effect.mechanical is not None:
                raise ValueError
        else:
            raise ValueError
        fact = CanonicalFact(
            fact_id=_id(base.session_id, operation_id, "campaign-fact"),
            fact_type="campaign.progression", predicate="resolved_campaign_effect",
            value=effect.model_dump(mode="json"), occurred_at=created_at,
            visibility=Visibility.PLAYER, tags=("campaign", "progression"),
            source_refs=(RecordReference(record_id=PRODUCER,
                                         record_type="deterministic_module", relation="produced_by"),),
        )
        event = CanonicalEvent(
            event_id=_id(base.session_id, operation_id, "campaign-event"),
            session_id=base.session_id, turn_id=base.turn_id, sequence=1,
            event_type="campaign_progressed", occurred_at=created_at,
            summary="Consequência de campanha determinada pela ação do jogador.",
            fact_ids=(fact.fact_id,), tags=("campaign", "progression"),
            visibility=Visibility.PLAYER,
        )
        payload = base.model_dump(mode="json")
        payload["facts"].append(fact.model_dump(mode="json"))
        payload["events"].append(event.model_dump(mode="json"))
        payload["state_changes"] = [StateChange(
            path=("campaign_progression",),
            value=effect.after_state.model_dump(mode="json"),
        ).model_dump(mode="json")]
        return TurnDraft.model_validate(payload)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise CampaignSourcePreparationError("campaign_source_preparation_invalid") from None
