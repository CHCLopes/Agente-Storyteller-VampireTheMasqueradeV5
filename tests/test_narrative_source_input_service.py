"""Internal action service lifecycle with temporary stores and authored LLM."""
import asyncio
from datetime import timedelta
import json
import sqlite3

import pytest

from api import narrative_source_input_service as service, rules_service
from api.llm.contract import CancellationToken, GenerationParameters, utc_now
from api.narrative_source_coordinator import execute_retained_source_turn
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_input import SourceInputFailure, create_source_producer_config
from api.narrative_source_preparation import DeclaredActionPreparation
from api.persistence import SQLitePersistence, SourceInputPersistenceError
from api.rules_service import PlayerSheetModel, StatusModel, TrackerModel
from api.scene_service import SceneState
from test_narrative_source_bridge import FIRST, SECOND, SYSTEM, _gateway
from test_narrative_source_preparation_bridge import INVESTIGATION_SUCCESS, INVESTIGATION_FAILURE

SESSION = "input-service-synthetic"


def state():
    sheet = PlayerSheetModel(
        attributes={"Wits": 3}, skills={"Investigation": 2}, disciplines={},
        status=StatusModel(blood_potency=1, current_hunger=0, humanity=7,
            health_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0)),
    )
    return {"player_sheet": sheet.model_dump(mode="json")}


def config():
    target, _ = _gateway()
    return create_source_producer_config(target=target, system_prompt=SYSTEM,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768))


def public(operation="first", text="Aguardo."):
    return SourcePlayerActionRequest(operation_id=operation, player_input=text)


async def make_store(tmp_path):
    store = SQLitePersistence(tmp_path/"service.sqlite3")
    await store.create_narrative_source_campaign(SESSION,
        initial_scene=SceneState(location="Galeria", npcs_present=("Mara",)),
        initial_state=state(), relationships={})
    return store


async def prepare(store, operation="first", text="Aguardo.", **updates):
    args = dict(session_id=SESSION, request=public(operation, text), store=store,
        producer_config=config(), deadline=utc_now()+timedelta(seconds=30),
        cancellation=CancellationToken())
    args.update(updates)
    return await service.prepare_source_player_action(**args)


async def narrate(store, operation="first", text=FIRST):
    _, gateway = _gateway(text)
    chunks = []
    async def collect(chunk): chunks.append(chunk)
    result = await execute_retained_source_turn(session_id=SESSION, operation_id=operation,
        store=store, gateway=gateway, deadline=utc_now()+timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect)
    assert result.status == "completed", result.error
    return result, gateway, chunks


@pytest.mark.anyio
async def test_wait_retains_without_rng_or_h6_and_reentry_survives_restart(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    before = await store.load_campaign(SESSION)
    calls = []
    original = service.produce_source_player_action
    def counted(request):
        calls.append(request)
        return original(request)
    monkeypatch.setattr(service, "produce_source_player_action", counted)
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Wait rolled dice"))
    result = await prepare(store)
    assert result.status == "completed" and not result.newly_claimed
    assert len(calls) == 1
    assert await store.load_campaign(SESSION) == before
    retained = await store.load_source_preparation(SESSION, "first")
    assert retained.preparation.kind == "declared_action" and retained.state == state()
    assert await store.load_attempt_by_operation(SESSION, "first") is None
    restarted = SQLitePersistence(store.db_path)
    assert await prepare(restarted, deadline=utc_now()-timedelta(seconds=1)) == result
    assert len(calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_real_receipt_reaches_h6_and_replays_without_second_resolution(tmp_path, monkeypatch, success):
    store = await make_store(tmp_path)
    faces, calls = ([6, 7, 8, 2, 3] if success else [1, 2, 3, 4, 5]), []
    def dice(low, high):
        assert (low, high) == (1, 10)
        value = faces[len(calls)]
        calls.append(value)
        return value
    monkeypatch.setattr(rules_service.random, "randint", dice)
    prepared = await prepare(store, text="Investigo a galeria.")
    assert prepared.status == "completed"
    capsule = await store.load_source_preparation(SESSION, "first")
    assert capsule.preparation.action.attribute.value == "Wits"
    assert capsule.preparation.action.skill.value == "Investigation"
    assert capsule.preparation.resolution.normal_rolls == faces
    assert capsule.preparation.resolution.is_success is success
    assert capsule.preparation.resolution.hunger_rolls == []
    result, gateway, chunks = await narrate(store, text=INVESTIGATION_SUCCESS if success else INVESTIGATION_FAILURE)
    assert len(gateway.requests) == 1 and len(chunks) == 1 and len(calls) == 5
    replay = await prepare(SQLitePersistence(store.db_path), text="Investigo a galeria.")
    assert replay == prepared and len(calls) == 5
    assert (await store.load_source_preparation(SESSION, "first")) == capsule
    packet = json.loads(gateway.requests[0].messages[1].content)
    assert packet["server_facts"] == [fact.model_dump(mode="json") for fact in capsule.draft.facts]
    assert result.turn_number == 1


@pytest.mark.anyio
async def test_same_id_pending_and_second_id_busy_never_produce_again(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    entered, release = asyncio.Event(), asyncio.Event()
    finalize = store.finalize_source_input
    produced = []
    def counted(request):
        produced.append(request)
        return DeclaredActionPreparation()
    async def delayed(*args, **kwargs):
        entered.set()
        await release.wait()
        return await finalize(*args, **kwargs)
    monkeypatch.setattr(service, "produce_source_player_action", counted)
    monkeypatch.setattr(store, "finalize_source_input", delayed)
    first = asyncio.create_task(prepare(store))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        second = await prepare(SQLitePersistence(store.db_path))
        assert second.status == "pending" and not second.newly_claimed
        with pytest.raises(SourceInputPersistenceError, match="source_input_session_busy"):
            await prepare(SQLitePersistence(store.db_path), operation="other")
        assert len(produced) == 1
    finally:
        release.set()
    assert (await first).status == "completed"


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["token", "deadline"])
async def test_preproduction_stop_is_terminal_without_rng_or_retry(tmp_path, monkeypatch, mode):
    store = await make_store(tmp_path)
    token = CancellationToken()
    if mode == "token": token.cancel("PRIVATE_SENTINEL")
    deadline = utc_now()+timedelta(seconds=30) if mode == "token" else utc_now()-timedelta(seconds=1)
    monkeypatch.setattr(service, "produce_source_player_action", lambda req: pytest.fail("Stopped input produced"))
    result = await prepare(store, cancellation=token, deadline=deadline)
    assert result.status == ("cancelled" if mode == "token" else "timeout")
    assert "PRIVATE_SENTINEL" not in result.model_dump_json()
    assert await store.load_source_preparation(SESSION, "first") is None
    assert await prepare(store) == result


@pytest.mark.anyio
@pytest.mark.parametrize("boundary", ["claim", "finalize"])
async def test_repeated_task_cancellation_settles_one_database_operation(tmp_path, monkeypatch, boundary):
    store = await make_store(tmp_path)
    entered, release = asyncio.Event(), asyncio.Event()
    produced = []
    def counted(req):
        produced.append(req)
        return DeclaredActionPreparation()
    monkeypatch.setattr(service, "produce_source_player_action", counted)
    method = "claim_source_input" if boundary == "claim" else "finalize_source_input"
    original = getattr(store, method)
    async def delayed(*args, **kwargs):
        # Claim is already durable before cancellation; finalize is still waiting.
        value = await original(*args, **kwargs) if boundary == "claim" else None
        entered.set()
        await release.wait()
        return value if boundary == "claim" else await original(*args, **kwargs)
    monkeypatch.setattr(store, method, delayed)
    task = asyncio.create_task(prepare(store))
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    observed = await prepare(SQLitePersistence(store.db_path))
    assert observed.status == ("cancelled" if boundary == "claim" else "completed")
    assert len(produced) == (0 if boundary == "claim" else 1)
    retained = await store.load_source_preparation(SESSION, "first")
    assert (retained is None) is (boundary == "claim")


@pytest.mark.anyio
async def test_uncertain_crash_remains_pending_and_never_reenters_producer(tmp_path, monkeypatch):
    class SimulatedCrash(BaseException): pass
    store = await make_store(tmp_path)
    calls = []
    def crash(req):
        calls.append(req)
        raise SimulatedCrash
    monkeypatch.setattr(service, "produce_source_player_action", crash)
    with pytest.raises(SimulatedCrash):
        await prepare(store)
    assert (await prepare(SQLitePersistence(store.db_path))).status == "pending"
    assert len(calls) == 1 and await store.load_source_preparation(SESSION, "first") is None


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["error", "wrong_type", "forged"])
async def test_producer_failures_are_closed_without_partial_capsule(tmp_path, monkeypatch, mode):
    store = await make_store(tmp_path)
    def invalid(req):
        if mode == "error": raise RuntimeError("PRIVATE_SENTINEL")
        if mode == "wrong_type": return {"receipt": "PRIVATE_SENTINEL"}
        return SourceInputFailure(code="source_input_out_of_scope").model_copy(update={"code": "PRIVATE_SENTINEL"})
    monkeypatch.setattr(service, "produce_source_player_action", invalid)
    result = await prepare(store)
    assert result.status == "failed" and result.completion.failure.code == "source_input_production_failed"
    assert "PRIVATE_SENTINEL" not in result.model_dump_json()
    assert await store.load_source_preparation(SESSION, "first") is None
    assert await prepare(store) == result


@pytest.mark.anyio
async def test_producer_copy_cannot_change_retained_original_state(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    def mutate(req):
        req.state["player_sheet"]["attributes"]["Wits"] = 5
        req.relationships["unexpected"] = 1
        return DeclaredActionPreparation()
    monkeypatch.setattr(service, "produce_source_player_action", mutate)
    result = await prepare(store)
    assert result.status == "completed"
    capsule = await store.load_source_preparation(SESSION, "first")
    assert capsule.state == state() and capsule.relationships == {}


@pytest.mark.anyio
@pytest.mark.parametrize("updates", [
    {"request": {"operation_id": "op", "player_input": "Aguardo.", "receipt": {}}},
    {"producer_config": {}}, {"deadline": "tomorrow"}, {"cancellation": None},
])
async def test_invalid_entry_never_calls_store(tmp_path, monkeypatch, updates):
    store = await make_store(tmp_path)
    async def forbidden(*args, **kwargs): pytest.fail("Invalid request reached claim")
    monkeypatch.setattr(store, "claim_source_input", forbidden)
    with pytest.raises(service.SourceInputServiceError):
        await prepare(store, **updates)


@pytest.mark.anyio
async def test_second_action_uses_new_base_while_first_replays_original(tmp_path):
    store = await make_store(tmp_path)
    first = await prepare(store)
    await narrate(store)
    second = await prepare(store, operation="second")
    assert second.request.snapshot.current_turn == 1
    assert second.request.snapshot.sources[0].projection.source.text == FIRST
    assert first.request.snapshot.current_turn == 0
    result, gateway, _ = await narrate(store, operation="second", text=SECOND)
    assert result.turn_number == 2 and FIRST in gateway.requests[0].messages[1].content
    assert await prepare(SQLitePersistence(store.db_path)) == first
    with sqlite3.connect(store.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 2
