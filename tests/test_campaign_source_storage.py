"""New opt-in campaign setup never adopts v1 or an existing save."""
import pytest

from api.campaign_source_storage import (
    CampaignSourceStorageError, create_campaign_source_session,
    read_campaign_source_snapshot, claim_campaign_source_input,
    finalize_campaign_source_input,
    claim_campaign_narrative,
)
from api.campaign_progression_service import CampaignProgressionRequest, resolve_campaign_progression
from api.campaign_source_capsule import CampaignSourceConfig, create_campaign_source_capsule
from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_preparation import DeclaredActionPreparation, prepare_source_turn_draft
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.llm.contract import CancellationToken, utc_now
from datetime import timedelta
from test_narrative_source_input_service import state as eligible_state
from api.persistence import SQLitePersistence


@pytest.mark.asyncio
async def test_new_campaign_source_setup_and_read(tmp_path):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    created = await create_campaign_source_session(
        store, "campaign-1", initial_state={"player_sheet": {"attributes": {"Wits": 3}}},
    )
    assert created.current_turn == created.state_revision == 0
    assert created.progression.record == "threatened"
    assert await read_campaign_source_snapshot(store, "campaign-1") == created
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_campaign_exists"):
        await create_campaign_source_session(store, "campaign-1", initial_state={})
    stored = await store.load_campaign("campaign-1")
    assert stored["state"]["campaign_progression"]["record"] == "threatened"
    assert "narrative_source_origin" not in stored["metadata"]


def config():
    return CampaignSourceConfig(
        target=LLMTarget(profile="synthetic-local", provider="fake", model="authored"),
        system_prompt="Narrador de ensaio",
        parameters=GenerationParameters(temperature=0.65, max_output_tokens=768, seed=None),
    )


@pytest.mark.asyncio
async def test_claim_and_atomic_preparation_survive_reentry(tmp_path):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state={})
    first = await claim_campaign_source_input(
        store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config(),
    )
    assert first.newly_claimed and first.status == "pending"
    again = await claim_campaign_source_input(
        store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config(),
    )
    assert not again.newly_claimed and again.request == first.request
    request = first.request
    base = prepare_source_turn_draft(
        request.snapshot, operation_id=request.operation_id,
        created_at=request.created_at, player_input=request.player_input,
        preparation=DeclaredActionPreparation(),
    )
    causal = CampaignProgressionRequest(
        session_id="campaign-1", operation_id="action-1", turn_id=base.turn_id,
        base_revision=0, player_input="Aguardo", state=request.snapshot.progression,
    )
    capsule = create_campaign_source_capsule(
        snapshot=request.snapshot, operation_id=request.operation_id,
        created_at=request.created_at, player_input=request.player_input,
        action_preparation=DeclaredActionPreparation(), campaign_request=causal,
        campaign_effect=resolve_campaign_progression(causal), state=request.state,
        relationships=request.relationships, config=request.config,
    )
    completed = await finalize_campaign_source_input(
        store, session_id="campaign-1", operation_id="action-1",
        request_sha256=request.fingerprint_sha256, capsule=capsule,
    )
    assert completed.status == "completed" and completed.capsule == capsule
    replay = await claim_campaign_source_input(
        store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config(),
    )
    assert not replay.newly_claimed and replay.capsule == capsule
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "threatened"
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_session_busy"):
        await claim_campaign_source_input(
            store, session_id="campaign-1", operation_id="action-2",
            player_input="Aguardo", config=config(),
        )


@pytest.mark.asyncio
async def test_producer_claims_once_and_retains_no_roll_effect(tmp_path, monkeypatch):
    import api.rules_service as rules
    monkeypatch.setattr(rules, "calculate_resolution", lambda *_a, **_kw: pytest.fail("RNG"))
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    kwargs = dict(store=store, session_id="campaign-1", operation_id="action-1",
                  player_input="Aguardo", config=config(),
                  deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken())
    first = await prepare_campaign_source_player_action(**kwargs)
    assert first.status == "completed" and first.capsule is not None
    assert first.capsule.campaign_effect.after_state.record == "warned"
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "threatened"
    again = await prepare_campaign_source_player_action(**kwargs)
    assert not again.newly_claimed and again.capsule == first.capsule
    h = await claim_campaign_narrative(store, capsule=first.capsule, operation_id="action-1")
    assert h.newly_claimed and h.status == "pending"
    same = await claim_campaign_narrative(store, capsule=first.capsule, operation_id="action-1")
    assert not same.newly_claimed and same.invocation_id == h.invocation_id
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_session_busy"):
        await claim_campaign_narrative(
            store, capsule=first.capsule, operation_id="resume-1",
            resumes_operation_id="action-1",
        )


@pytest.mark.asyncio
async def test_restart_recovery_of_pending_p_does_not_fabricate_k_or_block_forever(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    first = await claim_campaign_source_input(
        store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config(),
    )
    assert first.newly_claimed
    reopened = SQLitePersistence(db)
    assert await reopened.recover_pending_attempts(started_before=utc_now() + timedelta(seconds=5)) == 1
    retry = await claim_campaign_source_input(
        reopened, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config(),
    )
    assert retry.status == "cancelled" and not retry.newly_claimed and retry.capsule is None
    assert retry.error_code == "process_interrupted"
    new = await claim_campaign_source_input(
        reopened, session_id="campaign-1", operation_id="action-2",
        player_input="Aguardo", config=config(),
    )
    assert new.newly_claimed
    assert (await read_campaign_source_snapshot(reopened, "campaign-1")).current_turn == 0
