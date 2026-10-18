"""Pure campaign context and retained preparation; no database or provider."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from api.campaign_progression_service import (
    CampaignProgressState, CampaignProgressionRequest, resolve_campaign_progression,
)
from api.campaign_source_capsule import (
    CampaignSourceCapsule, CampaignSourceCapsuleError, CampaignSourceConfig,
    create_campaign_source_capsule,
)
from api.campaign_source_context import (
    CampaignSourceSnapshot, create_campaign_source_origin,
)
from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_context import create_source_context_origin
from api.narrative_source_preparation import DeclaredActionPreparation, prepare_source_turn_draft
from api.scene_service import SceneState


def capsule():
    progression = CampaignProgressState(revision=0)
    snapshot = CampaignSourceSnapshot(
        origin=create_campaign_source_origin(create_source_context_origin(
            "campaign-session", SceneState(location="Arquivo", npcs_present=("Mara",)))),
        current_turn=0, state_revision=0, progression=progression,
        sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    base = prepare_source_turn_draft(
        snapshot, operation_id="operation-1", created_at=now,
        player_input="Aguardo", preparation=DeclaredActionPreparation(),
    )
    request = CampaignProgressionRequest(
        session_id="campaign-session", operation_id="operation-1",
        turn_id=base.turn_id, base_revision=0, player_input="Aguardo",
        state=progression,
    )
    return create_campaign_source_capsule(
        snapshot=snapshot, operation_id="operation-1", created_at=now,
        player_input="Aguardo", action_preparation=DeclaredActionPreparation(),
        campaign_request=request, campaign_effect=resolve_campaign_progression(request),
        state={"campaign_progression": progression.model_dump(mode="json")},
        relationships={}, config=CampaignSourceConfig(
            target=LLMTarget(profile="synthetic-local", provider="fake", model="authored"),
            system_prompt="Narrador de ensaio", parameters=GenerationParameters(
                temperature=0.65, max_output_tokens=768, seed=None,
            ),
        ),
    )


def test_capsule_roundtrip_and_no_early_state_effect():
    value = capsule()
    assert CampaignSourceCapsule.model_validate(value.model_dump(mode="json")) == value
    assert value.draft.state_changes[0].value["record"] == "warned"
    assert value.state["campaign_progression"]["record"] == "threatened"
    assert value.snapshot.current_turn == 0


def test_tampered_effect_and_state_fail_closed():
    value = capsule()
    raw = deepcopy(value.model_dump(mode="json"))
    raw["campaign_effect"]["rule_id"] = "R-04"
    with pytest.raises((CampaignSourceCapsuleError, ValueError)):
        CampaignSourceCapsule.model_validate(raw)
    raw = deepcopy(value.model_dump(mode="json"))
    raw["state"]["campaign_progression"]["record"] = "wet"
    with pytest.raises((CampaignSourceCapsuleError, ValueError)):
        CampaignSourceCapsule.model_validate(raw)


def test_snapshot_refuses_missing_or_reordered_history():
    value = capsule()
    raw = value.snapshot.model_dump(mode="json")
    raw.update(current_turn=2, state_revision=2, omitted_turn_ids=["turn-1", "turn-2"])
    with pytest.raises(ValueError):
        CampaignSourceSnapshot.model_validate(raw)
