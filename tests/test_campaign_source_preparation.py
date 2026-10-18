"""Offline staging only; the B executor/commit does not accept this draft yet."""
from datetime import datetime, timezone

import pytest

from api.campaign_progression_service import (
    CampaignProgressState, CampaignProgressionRequest, resolve_campaign_progression,
)
from api.campaign_source_preparation import (
    CampaignSourcePreparationError, prepare_campaign_source_turn_draft,
)
from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_preparation import (
    DeclaredActionPreparation, ResolvedActionPreparation, prepare_source_turn_draft,
)
from api.rules_service import ResolutionResult, V5ActionPayload, V5Attribute, V5Skill
from api.scene_resolution_service import mechanical_resolution_from_result
from api.scene_service import SceneState

NOW = datetime(2026, 9, 29, tzinfo=timezone.utc)


def snapshot() -> SourceContextSnapshot:
    return SourceContextSnapshot(
        origin=create_source_context_origin("campaign-session", SceneState(
            location="Arquivo", npcs_present=("Mara",))),
        current_turn=0, state_revision=0, sources=(),
        selected_turn_ids=(), omitted_turn_ids=(),
    )


def inputs(text="Aguardo", preparation=None):
    snap = snapshot()
    prep = preparation or DeclaredActionPreparation()
    base = prepare_source_turn_draft(
        snap, operation_id="operation-1", created_at=NOW,
        player_input=text, preparation=prep,
    )
    mechanical = (mechanical_resolution_from_result(
        prep.resolution, source_fact_id=base.facts[0].fact_id,
    ) if type(prep) is ResolvedActionPreparation else None)
    request = CampaignProgressionRequest(
        session_id="campaign-session", operation_id="operation-1",
        turn_id=base.turn_id, base_revision=0, player_input=text,
        state=CampaignProgressState(revision=0), mechanical=mechanical,
    )
    return dict(
        snapshot=snap, operation_id="operation-1", created_at=NOW,
        player_input=text, action_preparation=prep,
        campaign_request=request, campaign_effect=resolve_campaign_progression(request),
    )


def resolved():
    text = "Examino o registro"
    action = V5ActionPayload(
        intent=text, attribute=V5Attribute.Wits, skill=V5Skill.INVESTIGATION,
        requires_roll=True, is_aggressive=False, inferred_difficulty=3,
    )
    result = ResolutionResult(
        successes=3, is_success=True, bestial_failure=False, messy_critical=False,
        summary="Recibo original de investigação.", normal_rolls=[8, 7, 9],
        hunger_rolls=[], margin=0,
    )
    return ResolvedActionPreparation(action=action, resolution=result)


def test_declaration_stages_exact_effect_without_committing_it():
    values = inputs()
    draft = prepare_campaign_source_turn_draft(**values)
    assert len(draft.facts) == len(draft.events) == 2
    assert draft.facts[0].fact_type == "action.declaration"
    assert draft.facts[1].fact_type == "campaign.progression"
    assert draft.facts[1].value == values["campaign_effect"].model_dump(mode="json")
    assert draft.events[1].fact_ids == (draft.facts[1].fact_id,)
    assert draft.events[1].sequence == 1
    assert draft.state_changes[0].path == ("campaign_progression",)
    assert draft.state_changes[0].value["record"] == "warned"
    assert draft.base_revision == 0 and draft.base_state_revision == 0
    assert prepare_campaign_source_turn_draft(**values) == draft


def test_investigation_stages_same_original_mechanical_receipt():
    values = inputs("Examino o registro", resolved())
    draft = prepare_campaign_source_turn_draft(**values)
    assert draft.facts[0].fact_type == "mechanics.resolution"
    assert draft.facts[1].value["mechanical"]["source_fact_id"] == draft.facts[0].fact_id
    assert draft.state_changes[0].value["outcome"] == "partial"


@pytest.mark.parametrize("change", [
    {"operation_id": "other"},
    {"player_input": "Espero"},
])
def test_mismatched_binding_fails_closed(change):
    values = inputs()
    values.update(change)
    with pytest.raises(CampaignSourcePreparationError, match="campaign_source_preparation_invalid"):
        prepare_campaign_source_turn_draft(**values)


def test_tampered_effect_or_receipt_fails_closed():
    values = inputs()
    values["campaign_effect"] = values["campaign_effect"].model_copy(update={"rule_id": "R-04"})
    with pytest.raises(CampaignSourcePreparationError):
        prepare_campaign_source_turn_draft(**values)
    values = inputs("Examino o registro", resolved())
    values["campaign_request"] = values["campaign_request"].model_copy(update={"mechanical": None})
    with pytest.raises(CampaignSourcePreparationError):
        prepare_campaign_source_turn_draft(**values)


def test_staging_never_calls_rng(monkeypatch):
    import api.rules_service as rules
    values = inputs("Examino o registro", resolved())
    monkeypatch.setattr(rules, "calculate_resolution", lambda *_a, **_kw: pytest.fail("RNG invoked"))
    monkeypatch.setattr(rules.random, "randint", lambda *_a, **_kw: pytest.fail("RNG invoked"))
    prepare_campaign_source_turn_draft(**values)
