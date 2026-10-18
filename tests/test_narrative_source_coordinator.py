"""Retained server preparation and H6 lifecycle; SQLiteTemp and authored FakeLLM."""
import asyncio
from datetime import timedelta
import json
import sqlite3

import pytest

from api import orchestrator_service, rules_service
from api.llm.contract import CancellationToken, GenerationParameters, utc_now
from api.narrative_source_coordinator import (
    SourceCoordinatorError, prepare_retained_source_turn, execute_retained_source_turn,
)
from api.narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation
from api.persistence import SQLitePersistence, IdempotencyConflictError
from test_narrative_source_bridge import FIRST, SECOND, THIRD, QUESTION, SCENE, NOW, SYSTEM, _gateway
from test_narrative_source_preparation_bridge import (
    INVESTIGATION, INVESTIGATION_SUCCESS, INVESTIGATION_FAILURE,
    resolve_investigation, assert_receipt,
)

SESSION = "retained-source"
ACTION = "Observo a galeria sem tocar em nada."


@pytest.fixture(autouse=True)
def forbid_old_producers(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Retained B coordinator entered a producer or legacy reader")
    for name in ("prepare_turn_pipeline", "_restore_narrator_context_items", "_assemble_narrator_context"):
        monkeypatch.setattr(orchestrator_service, name, forbidden)
    for name in ("load_or_migrate_campaign", "get_recent_narrative_source_turns", "list_latest_turns",
                 "list_events", "list_memory_candidates", "list_episodic_memories",
                 "list_consolidations", "list_legacy_imports"):
        monkeypatch.setattr(SQLitePersistence, name, forbidden)
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    return forbidden


async def make_store(tmp_path):
    store = SQLitePersistence(tmp_path / "retained.sqlite3")
    await store.create_narrative_source_campaign(
        SESSION, initial_scene=SCENE, initial_state={"counter": 0}, relationships={},
    )
    return store


async def prepare(store, operation="first", **overrides):
    target, _ = _gateway()
    args = dict(
        session_id=SESSION, operation_id=operation, created_at=NOW,
        player_input=ACTION, preparation=DeclaredActionPreparation(),
        state={"counter": 1}, relationships={}, store=store, target=target,
        system_prompt=SYSTEM, parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
    )
    args.update(overrides)
    return await prepare_retained_source_turn(**args)


async def run(store, operation="first", *, gateway=None, text=FIRST, **overrides):
    if gateway is None:
        _, gateway = _gateway(text)
    chunks = []
    async def collect(value): chunks.append(value)
    args = dict(
        session_id=SESSION, operation_id=operation, store=store, gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=collect,
    )
    args.update(overrides)
    result = await execute_retained_source_turn(**args)
    return result, gateway, chunks


@pytest.mark.anyio
async def test_retention_survives_restart_before_h6_and_commits_exact_static_input(tmp_path):
    store = await make_store(tmp_path)
    before = await store.load_campaign(SESSION)
    capsule = await prepare(store)
    assert await store.load_campaign(SESSION) == before
    assert await store.load_attempt_by_operation(SESSION, "first") is None
    restarted = SQLitePersistence(store.db_path)
    assert await restarted.load_source_preparation(SESSION, "first") == capsule
    result, gateway, chunks = await run(restarted)
    assert result.status == "completed", result.error
    assert len(gateway.requests) == 1 and chunks == [FIRST + "\n\n" + QUESTION]
    request = gateway.requests[0]
    assert request.target == capsule.target and request.parameters == capsule.parameters
    assert request.messages[0].content == capsule.system_prompt
    packet = json.loads(request.messages[1].content)
    assert packet["player_input"] == capsule.player_input
    assert packet["server_facts"] == [fact.model_dump(mode="json") for fact in capsule.draft.facts]
    assert await restarted.load_source_preparation(SESSION, "first") == capsule
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_real_resolved_receipt_is_retained_and_replayed_without_reroll(
    tmp_path, monkeypatch, forbid_old_producers, success,
):
    store = await make_store(tmp_path)
    action, receipt, rng_calls = resolve_investigation(monkeypatch, forbid_old_producers, success=success)
    capsule = await prepare(store, preparation=ResolvedActionPreparation(action=action, resolution=receipt),
                            player_input=INVESTIGATION)
    retained = await SQLitePersistence(store.db_path).load_source_preparation(SESSION, "first")
    assert_receipt(retained.draft.facts[0].value, receipt, success=success)
    text = INVESTIGATION_SUCCESS if success else INVESTIGATION_FAILURE
    result, gateway, chunks = await run(store, text=text)
    assert result.status == "completed", result.error
    assert chunks == [text + "\n\n" + QUESTION]
    replay, _, chunks = await run(SQLitePersistence(store.db_path), gateway=gateway, deadline=NOW)
    assert replay.status == "completed" and replay.envelope == result.envelope and chunks == []
    assert len(gateway.requests) == 1 and len(rng_calls) == 5
    assert await store.load_source_preparation(SESSION, "first") == capsule


@pytest.mark.anyio
async def test_rejection_preserves_capsule_but_never_authorizes_terminal_retry(tmp_path):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    _, gateway = _gateway(FIRST, "Qual é a cor da janela?")
    result, _, chunks = await run(store, gateway=gateway)
    assert result.status == "failed" and chunks == []
    assert await store.load_turn_by_operation(SESSION, "first") is None
    replay, _, chunks = await run(SQLitePersistence(store.db_path), gateway=gateway)
    assert replay.status == "failed" and replay.error["code"] == "source_turn_operation_terminal"
    assert len(gateway.requests) == 1 and chunks == []
    assert await store.load_source_preparation(SESSION, "first") == capsule


@pytest.mark.anyio
async def test_two_callers_share_one_h6_reservation(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    await prepare(store)
    _, gateway = _gateway()
    entered, release = asyncio.Event(), asyncio.Event()
    original = gateway.generate_structured
    calls = []
    async def delayed(request):
        calls.append(request)
        entered.set()
        await release.wait()
        return await original(request)
    monkeypatch.setattr(gateway, "generate_structured", delayed)
    first = asyncio.create_task(run(store, gateway=gateway))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        second, _, chunks = await run(SQLitePersistence(store.db_path), gateway=gateway)
        assert second.status == "pending" and chunks == []
        assert second.error["code"] == "source_turn_operation_pending" and len(calls) == 1
    finally:
        release.set()
    completed, _, chunks = await first
    assert completed.status == "completed" and len(chunks) == 1
    assert len(gateway.requests) == len(calls) == 1


@pytest.mark.anyio
async def test_crash_after_h6_reservation_remains_uncertain_without_takeover(tmp_path, monkeypatch):
    class SimulatedCrash(BaseException): pass
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    original = store.start_attempt
    async def crash_after_reservation(**kwargs):
        await original(**kwargs)
        raise SimulatedCrash()
    monkeypatch.setattr(store, "start_attempt", crash_after_reservation)
    _, gateway = _gateway()
    with pytest.raises(SimulatedCrash):
        await run(store, gateway=gateway)
    restarted = SQLitePersistence(store.db_path)
    result, _, chunks = await run(restarted, gateway=gateway)
    assert result.status == "pending" and not chunks and not gateway.requests
    assert await restarted.load_source_preparation(SESSION, "first") == capsule
    assert await restarted.recover_pending_attempts(started_before=utc_now()) == 1
    terminal, _, chunks = await run(SQLitePersistence(store.db_path), gateway=gateway)
    assert terminal.status == "cancelled" and not chunks and not gateway.requests
    assert await restarted.load_source_preparation(SESSION, "first") == capsule


@pytest.mark.anyio
async def test_completed_replay_uses_original_capsule_after_history_window_moves(tmp_path):
    store = await make_store(tmp_path)
    original = await prepare(store)
    first, gateway, _ = await run(store)
    for index, text in enumerate((SECOND, THIRD, THIRD), 2):
        await prepare(store, str(index), state={"counter": index})
        result, _, _ = await run(store, str(index), text=text)
        assert result.status == "completed", result.error
    restarted = SQLitePersistence(store.db_path)
    assert (await restarted.read_source_context_snapshot(SESSION)).current_turn == 4
    assert await restarted.load_source_preparation(SESSION, "first") == original
    assert await prepare(restarted) == original
    replay, _, chunks = await run(restarted, gateway=gateway, deadline=NOW)
    assert replay.status == "completed" and replay.envelope == first.envelope
    assert len(gateway.requests) == 1 and chunks == []


@pytest.mark.anyio
async def test_captured_arguments_cannot_change_during_snapshot_io(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    state, relationships = {"counter": 1}, {"public": {"value": 2}}
    original = store.read_source_context_snapshot
    async def mutate(*args, **kwargs):
        state["counter"] = 999
        relationships["public"]["value"] = 999
        return await original(*args, **kwargs)
    monkeypatch.setattr(store, "read_source_context_snapshot", mutate)
    capsule = await prepare(store, state=state, relationships=relationships)
    assert capsule.state == {"counter": 1} and capsule.relationships == {"public": {"value": 2}}


@pytest.mark.anyio
@pytest.mark.parametrize("change", ["created_at", "system_prompt", "player_input", "state"])
async def test_changed_preparation_arguments_do_not_replace_retained_operation(tmp_path, change):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    values = {"created_at": NOW + timedelta(seconds=1), "system_prompt": SYSTEM + " Alterado.",
              "player_input": "Aguardo em silêncio.", "state": {"counter": 2}}
    with pytest.raises(IdempotencyConflictError):
        await prepare(store, **{change: values[change]})
    assert await store.load_source_preparation(SESSION, "first") == capsule
    assert await store.load_attempt_by_operation(SESSION, "first") is None


@pytest.mark.anyio
async def test_missing_capsule_never_dispatches_or_creates_h6_attempt(tmp_path):
    store = await make_store(tmp_path)
    _, gateway = _gateway()
    with pytest.raises(SourceCoordinatorError, match="capsule_missing"):
        await run(store, gateway=gateway)
    assert not gateway.requests and await store.load_attempt_by_operation(SESSION, "first") is None


@pytest.mark.anyio
@pytest.mark.parametrize("cancel_count", [1, 2])
async def test_cancellation_finishes_retention_without_dispatch(tmp_path, monkeypatch, cancel_count):
    store = await make_store(tmp_path)
    entered, release = asyncio.Event(), asyncio.Event()
    original = store.save_source_preparation
    async def delayed(capsule):
        entered.set()
        await release.wait()
        return await original(capsule)
    monkeypatch.setattr(store, "save_source_preparation", delayed)
    task = asyncio.create_task(prepare(store))
    await asyncio.wait_for(entered.wait(), 5)
    for _ in range(cancel_count):
        task.cancel()
        await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await SQLitePersistence(store.db_path).load_source_preparation(SESSION, "first") is not None
    assert await store.load_attempt_by_operation(SESSION, "first") is None


@pytest.mark.anyio
async def test_stale_retained_base_fails_before_gateway_without_replacing_capsule(tmp_path):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    await prepare(store, "competitor")
    result, _, _ = await run(store, "competitor")
    assert result.status == "completed", result.error
    stale, gateway, chunks = await run(store)
    assert stale.status == "failed" and not gateway.requests and not chunks
    assert await store.load_source_preparation(SESSION, "first") == capsule
    assert await store.load_turn_by_operation(SESSION, "first") is None
