"""Campaign P/K producer: one claimed action, one retained causal preparation."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from . import rules_service as rules
from .campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent
from .campaign_progression_service import CampaignProgressionRequest, resolve_campaign_progression
from .campaign_expression_capsule import CampaignExpressionConfig, create_campaign_expression_capsule
from .campaign_expression_storage import (
    CampaignExpressionClaim, claim_campaign_expression_input, finalize_campaign_expression_input,
)
from .llm.contract import CancellationToken
from .narration_resume_service import applicable_gates_allow
from .narrative_source_action_producer import _eligible_sheet
from .narrative_source_input_service import _settle_local_transaction
from .narrative_source_preparation import (
    DeclaredActionPreparation, ResolvedActionPreparation, prepare_source_turn_draft,
)
from .persistence import SQLitePersistence
from .scene_resolution_service import mechanical_resolution_from_result
from .turn_models import NarratorAvailabilityGate


class CampaignExpressionInputError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


async def _gate_allows(store: SQLitePersistence, session_id: str,
                       config: CampaignExpressionConfig) -> bool:
    rows = await store.load_narrator_availability_gates(session_id)
    if any(type(row.get("payload")) is not dict for row in rows):
        return False
    gates = tuple(NarratorAvailabilityGate.model_validate(row["payload"])
                  for row in rows)
    return applicable_gates_allow(gates, server_now=datetime.now(timezone.utc),
                                  exact_target=config.target)


async def prepare_campaign_expression_player_action(
    *, store: SQLitePersistence, session_id: str, operation_id: str,
    player_input: str, config: CampaignExpressionConfig,
    deadline: datetime, cancellation: CancellationToken,
) -> CampaignExpressionClaim:
    """No caller-provided receipt/classification; only P's new claim can roll."""
    if (type(deadline) is not datetime or deadline.utcoffset() is None
            or type(cancellation) is not CancellationToken
            or type(config) is not CampaignExpressionConfig):
        raise CampaignExpressionInputError("campaign_expression_input_arguments_invalid")
    observed, interrupted = await _settle_local_transaction(claim_campaign_expression_input(
        store, session_id=session_id, operation_id=operation_id,
        player_input=player_input, config=config,
    ))
    if not observed.newly_claimed:
        if interrupted:
            raise asyncio.CancelledError
        return observed
    original = observed.request
    capsule = None
    failure = "campaign_expression_cancelled" if interrupted else None
    try:
        if failure is None and (cancellation.is_cancelled or datetime.now(timezone.utc) >= deadline):
            failure = ("campaign_expression_cancelled" if cancellation.is_cancelled
                       else "campaign_expression_deadline_exceeded")
        if failure is None and not await _gate_allows(store, session_id, original.config):
            failure = "campaign_expression_gate_blocked"
        intent = classify_campaign_intent(original.player_input) if failure is None else None
        if failure is None and intent is None:
            failure = "campaign_expression_out_of_scope"
        sheet = _eligible_sheet(original.state, original.session_id) if failure is None else None
        if failure is None and sheet is None:
            failure = "campaign_expression_out_of_scope"
        preparation = None
        if failure is None and intent is CampaignIntentKind.INSPECT:
            wits, investigation = sheet.attributes.get("Wits"), sheet.skills.get("Investigation")
            if (type(wits) is not int or not 1 <= wits <= 5
                    or type(investigation) is not int or not 0 <= investigation <= 5):
                failure = "campaign_expression_out_of_scope"
            if failure is None and (cancellation.is_cancelled or datetime.now(timezone.utc) >= deadline):
                failure = ("campaign_expression_cancelled" if cancellation.is_cancelled
                           else "campaign_expression_deadline_exceeded")
            # This is the second persisted P0 check, immediately before RNG.
            if failure is None and not await _gate_allows(store, session_id, original.config):
                failure = "campaign_expression_gate_blocked"
            if failure is None:
                action = rules.V5ActionPayload(
                    intent=original.player_input, attribute=rules.V5Attribute.Wits,
                    skill=rules.V5Skill.INVESTIGATION, requires_roll=True,
                    is_aggressive=False, inferred_difficulty=3,
                    action_target=rules.V5ActionTarget.UNOPPOSED,
                    weapon_category=rules.V5WeaponCategory.UNARMED,
                )
                receipt = rules.calculate_resolution(
                    action, current_hunger=0, dice_pool=wits + investigation,
                )
                preparation = ResolvedActionPreparation(action=action, resolution=receipt)
        elif failure is None:
            preparation = DeclaredActionPreparation()
        if failure is None:
            base = prepare_source_turn_draft(
                original.snapshot, operation_id=original.operation_id,
                created_at=original.created_at, player_input=original.player_input,
                preparation=preparation,
            )
            mechanical = (mechanical_resolution_from_result(
                preparation.resolution, source_fact_id=base.facts[0].fact_id,
            ) if type(preparation) is ResolvedActionPreparation else None)
            causal = CampaignProgressionRequest(
                session_id=original.session_id, operation_id=original.operation_id,
                turn_id=base.turn_id, base_revision=original.snapshot.current_turn,
                player_input=original.player_input, state=original.snapshot.progression,
                mechanical=mechanical,
            )
            effect = resolve_campaign_progression(causal)
            capsule = create_campaign_expression_capsule(
                snapshot=original.snapshot, operation_id=original.operation_id,
                created_at=original.created_at, player_input=original.player_input,
                action_preparation=preparation, campaign_request=causal,
                campaign_effect=effect, state=original.state,
                relationships=original.relationships, config=original.config,
            )
    except asyncio.CancelledError:
        interrupted = True
        failure = "campaign_expression_cancelled"
        capsule = None
    except Exception:
        # A failed RNG is never re-run for this claimed operation.
        failure = "campaign_expression_production_failed"
        capsule = None
    if failure is None and (cancellation.is_cancelled or datetime.now(timezone.utc) >= deadline):
        failure = ("campaign_expression_cancelled" if cancellation.is_cancelled
                   else "campaign_expression_deadline_exceeded")
        capsule = None
    finished, final_interrupted = await _settle_local_transaction(finalize_campaign_expression_input(
        store, session_id=session_id, operation_id=operation_id,
        request_sha256=original.fingerprint_sha256, capsule=capsule,
        failure_code=failure,
    ))
    if interrupted or final_interrupted:
        raise asyncio.CancelledError
    return finished
