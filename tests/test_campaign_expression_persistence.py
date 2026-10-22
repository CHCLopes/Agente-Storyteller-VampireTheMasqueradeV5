"""V2 persistence boundary counterproofs, adapted from the v1 contract suite."""
import asyncio
import sqlite3
from datetime import timedelta
import pytest
from api.campaign_expression_execution_service import execute_campaign_expression_turn
from api.campaign_expression_input_service import prepare_campaign_expression_player_action
from api.campaign_expression_storage import (
    create_campaign_expression_session, read_campaign_expression_snapshot, claim_campaign_expression_input,
    read_campaign_expression_status, claim_campaign_narrative,
    load_campaign_expression_capsule, CampaignExpressionStorageError,
)
from api.llm.contract import CancellationToken, ErrorCategory, utc_now
from api.persistence import SQLitePersistence
from api.rules_service import ResolutionResult
from api.narrative_source_preparation import DeclaredActionPreparation, prepare_source_turn_draft
from test_campaign_source_integration import N
from api.turn_models import NarrativeRecord, Visibility
from test_narrative_source_input_service import state as eligible_state
from test_campaign_expression_v2 import setup

# All authored valid responses are composed from each retained v2 plan.
def config_and_gateway(*_args):
    return setup()
RECOVERED = None

@pytest.mark.asyncio
async def test_concurrent_claims_and_generic_commit_cannot_bypass_campaign_contract(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, _ = config_and_gateway()
    async def claim(name):
        return await claim_campaign_expression_input(
            SQLitePersistence(db), session_id="campaign-1", operation_id=name,
            player_input="Aguardo", config=config,
        )
    outcomes = await asyncio.gather(claim("action-1"), claim("action-2"),
                                    return_exceptions=True)
    assert sum(getattr(item, "newly_claimed", False) for item in outcomes) == 1
    assert sum(isinstance(item, CampaignExpressionStorageError)
               and item.code == "campaign_expression_session_busy" for item in outcomes) == 1
    accepted = next(item for item in outcomes if getattr(item, "newly_claimed", False))
    assert accepted.request.snapshot.current_turn == 0
    draft = prepare_source_turn_draft(
        accepted.request.snapshot, operation_id=accepted.request.operation_id,
        created_at=accepted.request.created_at, player_input="Aguardo",
        preparation=DeclaredActionPreparation(),
    )
    with pytest.raises(CampaignExpressionStorageError, match="campaign_expression_commit_contract_required"):
        await store.commit_turn(
            session_id="campaign-1", operation_id="bypass", turn_id=draft.turn_id,
            attempt_id="bypass-attempt", turn_number=1, base_revision=0,
            base_state_revision=0, state=accepted.request.state,
            narrative=NarrativeRecord(
                narrative_id="bypass-narrative", session_id="campaign-1",
                turn_id=draft.turn_id, created_at=utc_now(), text=N,
                source_event_ids=(draft.events[0].event_id,), invocation_id="bypass-invocation",
                visibility=Visibility.PLAYER,
            ),
            facts=draft.facts, events=draft.events, user_input="Aguardo", relationships={},
        )
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 0

@pytest.mark.asyncio
async def test_second_gate_blocks_rng_and_leaves_no_campaign_effect(tmp_path, monkeypatch):
    import api.campaign_expression_input_service as service
    import api.rules_service as rules
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    checks = []
    async def gate(*_args):
        checks.append(1)
        return len(checks) == 1
    monkeypatch.setattr(service, "_gate_allows", gate)
    monkeypatch.setattr(rules, "calculate_resolution", lambda *_a, **_kw: pytest.fail("RNG"))
    config, _ = config_and_gateway()
    result = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert len(checks) == 2
    assert result.status == "failed" and result.error_code == "campaign_expression_gate_blocked"
    assert result.capsule is None
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).progression.record == "threatened"

@pytest.mark.asyncio
async def test_mechanical_receipt_is_not_rolled_again_after_h_failure_or_resume(tmp_path, monkeypatch):
    import api.rules_service as rules
    calls = []
    def calculate(_action, *, current_hunger, dice_pool):
        calls.append((current_hunger, dice_pool))
        return ResolutionResult(
            successes=3, is_success=True, bestial_failure=False,
            messy_critical=False, summary="Investigação bem-sucedida.",
            normal_rolls=[8, 8, 8, 5, 4], hunger_rolls=[], margin=0,
        )
    monkeypatch.setattr(rules, "calculate_resolution", calculate)
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, bad = config_and_gateway(RECOVERED, ("campaign.content.recovered",), "")
    bad.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert calls == [(0, 5)] and prepared.capsule.campaign_effect.rule_id == "R-07"
    async def collect(_text):
        pass
    failed = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="inspect-1", gateway=bad,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert failed.status == "failed"
    assert (await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )).capsule == prepared.capsule
    store = SQLitePersistence(db)
    _, good = config_and_gateway(RECOVERED, ("campaign.content.recovered",), "")
    resumed = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="inspect-1", gateway=good,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert calls == [(0, 5)]
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).progression.outcome == "partial"

@pytest.mark.asyncio
async def test_delivery_failure_rolls_back_source_effect_and_can_resume(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def broken(_text):
        assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 0
        raise RuntimeError("transport disconnected")
    failed = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=broken,
    )
    assert failed.status == "failed" and failed.error_code == "campaign_expression_delivery_failed"
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).progression.record == "threatened"
    assert await store.list_turns("campaign-1") == []
    store = SQLitePersistence(db)
    _, retry_gateway = config_and_gateway()
    chunks = []
    async def collect(text):
        chunks.append(text)
    resumed = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=retry_gateway,
        deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).progression.record == "warned"
    assert len(chunks) == 1

@pytest.mark.asyncio
async def test_restart_recovers_pending_h_and_resumes_same_capsule(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    pending = await claim_campaign_narrative(
        store, capsule=prepared.capsule, operation_id="action-1",
    )
    assert pending.status == "pending"
    reopened = SQLitePersistence(db)
    assert await reopened.recover_pending_attempts(
        started_before=utc_now() + timedelta(seconds=5)) == 1
    status = await read_campaign_expression_status(reopened, "campaign-1", "action-1")
    assert status.narrative_status == "cancelled"
    assert status.resume_from_operation_id == "action-1"
    assert await load_campaign_expression_capsule(reopened, "campaign-1", "action-1") == prepared.capsule
    async def collect(_text):
        pass
    resumed = await execute_campaign_expression_turn(
        store=reopened, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert (await read_campaign_expression_snapshot(reopened, "campaign-1")).progression.record == "warned"

@pytest.mark.asyncio
async def test_sqlite_event_failure_rolls_back_turn_effect_and_source(tmp_path, monkeypatch):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    def fail_insert(*_args):
        raise RuntimeError("synthetic insert failure")
    monkeypatch.setattr(store, "_insert_event", fail_insert)
    chunks = []
    async def collect(text):
        chunks.append(text)
    result = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert result.status == "failed" and result.error_code == "campaign_expression_commit_failed"
    assert len(chunks) == 1  # provisional delivery, not canonical confirmation
    assert await store.list_turns("campaign-1") == []
    assert await store.list_events("campaign-1") == []
    snapshot = await read_campaign_expression_snapshot(store, "campaign-1")
    assert snapshot.current_turn == 0 and snapshot.progression.record == "threatened"
    status = await read_campaign_expression_status(store, "campaign-1", "action-1")
    assert status.narrative_status == "failed" and status.resume_from_operation_id == "action-1"

@pytest.mark.asyncio
async def test_competing_resume_clicks_obtain_at_most_one_h_claim(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    gateway.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def collect(_text):
        pass
    failed = await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert failed.status == "failed"
    async def resume(name):
        return await claim_campaign_narrative(
            SQLitePersistence(db), capsule=prepared.capsule,
            operation_id=name, resumes_operation_id="action-1",
        )
    results = await asyncio.gather(resume("resume-a"), resume("resume-b"),
                                   return_exceptions=True)
    assert sum(getattr(item, "newly_claimed", False) for item in results) == 1
    assert sum(isinstance(item, CampaignExpressionStorageError)
               and item.code == "campaign_expression_session_busy" for item in results) == 1
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 0

@pytest.mark.asyncio
async def test_repeated_h_failures_form_one_explicit_chain_without_repreparing(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, bad = config_and_gateway()
    bad.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def collect(_text):
        pass
    for operation, previous in (("action-1", None), ("resume-1", "action-1")):
        result = await execute_campaign_expression_turn(
            store=SQLitePersistence(db), capsule=prepared.capsule, operation_id=operation,
            resumes_operation_id=previous, gateway=bad,
            deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(), on_chunk=collect,
        )
        assert result.status == "failed"
        assert (await read_campaign_expression_status(store, "campaign-1", "action-1")).resume_from_operation_id == operation
        assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 0
    _, good = config_and_gateway()
    finished = await execute_campaign_expression_turn(
        store=SQLitePersistence(db), capsule=prepared.capsule, operation_id="resume-2",
        resumes_operation_id="resume-1", gateway=good,
        deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert finished.status == "completed"
    assert finished.envelope.original_operation_id == "action-1"
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 1
    assert len(bad.requests) == 2 and len(good.requests) == 1

@pytest.mark.asyncio
async def test_unknown_method_is_not_an_in_world_failure_and_source_cannot_grant_delta(tmp_path):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, _ = config_and_gateway()
    claim = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="unsupported-1",
        player_input="Uso uma lona para desviar a água", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert claim.status == "failed" and claim.error_code == "campaign_expression_out_of_scope"
    assert claim.capsule is None
    current = await store.load_campaign("campaign-1")
    changed = dict(current["state"])
    changed["campaign_progression"] = {
        **changed["campaign_progression"], "revision": 1,
        "record": "preserved", "outcome": "preserved",
        "resolved_objectives": ["record_rescue"],
    }
    with pytest.raises(CampaignExpressionStorageError, match="campaign_expression_snapshot_mutation_forbidden"):
        await store.update_campaign_snapshot(
            "campaign-1", state=changed, expected_turn=0, expected_revision=0,
        )
    assert (await read_campaign_expression_snapshot(store, "campaign-1")).current_turn == 0

@pytest.mark.asyncio
async def test_reconstruction_detects_turn_or_failed_h_hash_tampering(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    gateway.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    async def collect(_text):
        pass
    assert (await execute_campaign_expression_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )).status == "failed"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE attempts SET result_hash=? WHERE session_id=? AND operation_id=?",
            ("0" * 64, "campaign-1", "action-1"),
        )
    with pytest.raises(CampaignExpressionStorageError, match="campaign_expression_h_chain_invalid"):
        await read_campaign_expression_status(SQLitePersistence(db), "campaign-1", "action-1")
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE attempts SET result_hash=NULL WHERE session_id=? AND operation_id=?",
            ("campaign-1", "action-1"),
        )
    # A fresh, independent session proves the committed-turn digest path.
    await create_campaign_expression_session(store, "campaign-2", initial_state=eligible_state())
    _, good = config_and_gateway()
    retained = await prepare_campaign_expression_player_action(
        store=store, session_id="campaign-2", operation_id="action-2",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert (await execute_campaign_expression_turn(
        store=store, capsule=retained.capsule, operation_id="action-2",
        gateway=good, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )).status == "completed"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE turns SET usage_json=? WHERE session_id=?",
            ('{"untrusted":true}', "campaign-2"),
        )
    with pytest.raises(CampaignExpressionStorageError, match="campaign_expression_history_invalid"):
        await read_campaign_expression_snapshot(SQLitePersistence(db), "campaign-2")
