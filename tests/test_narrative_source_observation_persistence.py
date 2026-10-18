"""Single-snapshot producer-backed observations with synthetic stores/FakeLLM."""
import asyncio
from datetime import timedelta
import json
import sqlite3
import threading

import pytest

from api import narrative_source_input_service as input_service, rules_service
from api.llm.contract import CancellationToken, ErrorCategory, utc_now
from api.narrative_source_capsule import source_preparation_operation_id
from api.narrative_source_coordinator import execute_retained_source_turn
from api.narrative_source_input import source_input_operation_id
from api.narrative_source_observation import SourceObservationError, validate_source_player_observation
from api.narrative_source_setup_service import create_source_trial_setup
from api.narrative_source_transport import project_source_operation, project_source_preparation
from api.persistence import SQLitePersistence
from test_narrative_source_bridge import FIRST, SECOND, THIRD, _gateway
from test_narrative_source_capsule_persistence import ledger
from test_narrative_source_input_service import config, state

SESSION = "observation-synthetic"
SETUP = {"location": "Galeria", "npcs_present": ["Mara"], "declared_objective": "Conhecer a galeria."}


async def make_store(tmp_path):
    store = SQLitePersistence(tmp_path/"observation.sqlite3")
    await store.initialize()
    await create_source_trial_setup(session_id=SESSION, request=SETUP, store=store,
        initial_state=state(), relationships={})
    return store


async def prepare(store, operation="first", text="Aguardo.", **updates):
    args = dict(session_id=SESSION, request={"operation_id": operation, "player_input": text},
        store=store, producer_config=config(), deadline=utc_now()+timedelta(seconds=30),
        cancellation=CancellationToken())
    args.update(updates)
    return await input_service.prepare_source_player_action(**args)


async def run(store, operation="first", text=FIRST, **updates):
    _, gateway = _gateway(text)
    async def collect(_text): pass
    args = dict(session_id=SESSION, operation_id=operation, store=store, gateway=gateway,
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=collect)
    args.update(updates)
    return await execute_retained_source_turn(**args)


def forbid(*args, **kwargs):
    pytest.fail("Observation attempted initialization, execution, write or RNG")


async def observed(store, monkeypatch, operation="first"):
    before = ledger(store), store.db_path.read_bytes()
    reader = SQLitePersistence(store.db_path)
    connections, statements = [], []
    real_connect = sqlite3.connect
    def traced(*args, **kwargs):
        connections.append((args, kwargs))
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection
    with monkeypatch.context() as patch:
        for method in ("initialize", "_connect", "claim_source_input", "finalize_source_input",
                "load_source_preparation", "read_source_context_snapshot", "load_campaign",
                "load_turn_by_operation", "start_attempt", "commit_turn", "recover_pending_attempts"):
            patch.setattr(reader, method, forbid)
        patch.setattr(input_service, "produce_source_player_action", forbid)
        patch.setattr(rules_service.random, "randint", forbid)
        patch.setattr(sqlite3, "connect", traced)
        result = await reader.read_source_player_observation(SESSION, operation_id=operation)
    assert len(connections) == 1
    assert connections[0][1]["uri"] is True and connections[0][0][0].endswith("?mode=ro")
    assert sum(sql == "BEGIN" for sql in statements) == 1
    assert not any(sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER")) for sql in statements)
    assert (ledger(store), store.db_path.read_bytes()) == before
    assert not reader._initialized and not reader._session_locks
    return validate_source_player_observation(result, session_id=SESSION, operation_id=operation)


class LostProcess(BaseException):
    pass


async def h_pending(store, monkeypatch):
    original = store.start_attempt
    async def lost(**kwargs):
        await original(**kwargs)
        raise LostProcess()
    with monkeypatch.context() as patch:
        patch.setattr(store, "start_attempt", lost)
        with pytest.raises(LostProcess): await run(store)


@pytest.mark.anyio
async def test_zero_turn_and_unknown_request_do_not_invent_pending_or_write(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    empty = await observed(store, monkeypatch, None)
    assert empty.manifest.request.location == "Galeria"
    assert empty.latest_completed is empty.requested is None
    missing = await observed(store, monkeypatch)
    assert missing.requested.operation_id == "first"
    assert missing.requested.preparation is missing.requested.narrative is missing.requested.confirmed is None


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["pending", "failed", "cancelled", "timeout"])
async def test_preparation_before_k_is_visible_after_restart_without_claim(tmp_path, monkeypatch, kind):
    store = await make_store(tmp_path)
    if kind == "pending":
        await store.claim_source_input(SESSION, {"operation_id": "first", "player_input": "Aguardo."},
                                       producer_config=config())
    elif kind == "failed":
        await prepare(store, text="Voo através da parede.")
    elif kind == "cancelled":
        token = CancellationToken(); token.cancel("PRIVATE_CANCEL_DETAIL")
        await prepare(store, cancellation=token)
    else:
        await prepare(store, deadline=utc_now()-timedelta(seconds=1))
    result = await observed(store, monkeypatch)
    assert result.requested.preparation.status == kind
    assert result.requested.preparation.newly_claimed is False
    assert result.requested.narrative is result.requested.confirmed is result.latest_completed is None
    public = project_source_preparation(result.requested.preparation, session_id=SESSION, operation_id="first")
    assert "PRIVATE" not in public.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["retained_unstarted", "pending", "completed", "failed", "timeout", "cancelled"])
async def test_retained_and_h_states_remain_observations_not_execution(tmp_path, monkeypatch, kind):
    store = await make_store(tmp_path)
    await prepare(store)
    if kind == "pending":
        await h_pending(store, monkeypatch)
    elif kind == "failed":
        _, gateway = _gateway(failure_category=ErrorCategory.PROVIDER_UNAVAILABLE)
        await run(store, gateway=gateway)
    elif kind == "timeout":
        await run(store, deadline=utc_now()-timedelta(seconds=1))
    elif kind == "cancelled":
        token = CancellationToken(); token.cancel("PRIVATE_CANCEL_DETAIL")
        await run(store, cancellation=token)
    elif kind == "completed":
        assert (await run(store)).status == "completed"
    result = await observed(store, monkeypatch)
    assert result.requested.preparation.status == "completed"
    assert result.requested.narrative.status == kind
    if kind == "completed":
        assert result.requested.confirmed == result.latest_completed.envelope
        assert result.requested.narrative == result.latest_completed.operation
        assert result.requested.confirmed.projection.text == FIRST
    else:
        assert result.requested.confirmed is result.latest_completed is None
    event = project_source_operation(result.requested.narrative, session_id=SESSION,
        operation_id="first", confirmed_envelope=result.requested.confirmed)
    assert "PRIVATE" not in event.model_dump_json()


@pytest.mark.anyio
async def test_old_operation_and_latest_stay_distinct_outside_history_window(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    for operation, text in (("first", FIRST), ("second", SECOND), ("third", THIRD)):
        await prepare(store, operation)
        assert (await run(store, operation, text)).status == "completed"
    old = await observed(store, monkeypatch)
    assert old.requested.narrative.base_turn == 0 and old.requested.narrative.current_turn == 3
    assert old.requested.confirmed.projection.text == FIRST
    assert old.latest_completed.operation.operation_id == "third"
    assert old.latest_completed.operation.base_turn == 2
    assert old.latest_completed.envelope.projection.text == THIRD
    latest = await observed(store, monkeypatch, "third")
    assert latest.requested.confirmed == latest.latest_completed.envelope
    presentation = await observed(store, monkeypatch, None)
    assert presentation.requested is None and presentation.latest_completed == latest.latest_completed


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [
    "missing_p", "p_displaced", "p_hash", "p_extra", "missing_k", "k_displaced",
    "capsule_hash", "h_displaced", "h_hash", "turn_displaced", "turn_text",
])
async def test_corrupt_producer_chain_is_closed_without_repair(tmp_path, mutation):
    store = await make_store(tmp_path)
    await prepare(store)
    assert (await run(store)).status == "completed"
    p_id, k_id = source_input_operation_id(SESSION, "first"), source_preparation_operation_id(SESSION, "first")
    with sqlite3.connect(store.db_path) as db:
        if mutation == "missing_p": db.execute("DELETE FROM attempts WHERE operation_id=?", (p_id,))
        elif mutation == "p_displaced": db.execute("UPDATE attempts SET operation_id='displaced' WHERE operation_id=?", (p_id,))
        elif mutation == "p_hash": db.execute("UPDATE attempts SET request_hash=? WHERE operation_id=?", ("0"*64, p_id))
        elif mutation == "p_extra":
            raw = json.loads(db.execute("SELECT metadata_json FROM attempts WHERE operation_id=?", (p_id,)).fetchone()[0])
            raw["narrative_source_input"]["PRIVATE_EXTRA"] = True
            db.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", (json.dumps(raw), p_id))
        elif mutation == "missing_k": db.execute("DELETE FROM attempts WHERE operation_id=?", (k_id,))
        elif mutation == "k_displaced": db.execute("UPDATE attempts SET operation_id='displaced' WHERE operation_id=?", (k_id,))
        elif mutation == "capsule_hash":
            raw = json.loads(db.execute("SELECT metadata_json FROM attempts WHERE operation_id=?", (k_id,)).fetchone()[0])
            raw["narrative_source_capsule"]["fingerprint_sha256"] = "0"*64
            db.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", (json.dumps(raw), k_id))
        elif mutation == "h_displaced": db.execute("UPDATE attempts SET operation_id='displaced' WHERE operation_id='first'")
        elif mutation == "h_hash": db.execute("UPDATE attempts SET result_hash=? WHERE operation_id='first'", ("0"*64,))
        elif mutation == "turn_displaced": db.execute("UPDATE turns SET operation_id='displaced' WHERE operation_id='first'")
        else: db.execute("UPDATE turns SET narrative_text='PRIVATE_FALSE_TEXT' WHERE operation_id='first'")
    before = ledger(store), store.db_path.read_bytes()
    with pytest.raises(SourceObservationError, match="^source_observation_stored_pair_invalid$"):
        await SQLitePersistence(store.db_path).read_source_player_observation(SESSION, operation_id="first")
    assert (ledger(store), store.db_path.read_bytes()) == before


@pytest.mark.anyio
@pytest.mark.parametrize("phase", ["retained", "pending", "completed"])
async def test_missing_p_never_adopts_old_k_while_existing_status_reader_is_unchanged(tmp_path, monkeypatch, phase):
    store = await make_store(tmp_path)
    await prepare(store)
    if phase == "pending": await h_pending(store, monkeypatch)
    elif phase == "completed": assert (await run(store)).status == "completed"
    with sqlite3.connect(store.db_path) as db:
        db.execute("DELETE FROM attempts WHERE operation_id=?", (source_input_operation_id(SESSION, "first"),))
    earlier = await SQLitePersistence(store.db_path).read_source_operation_status(SESSION, "first")
    assert earlier.status == {"retained": "retained_unstarted", "pending": "pending", "completed": "completed"}[phase]
    with pytest.raises(SourceObservationError):
        await SQLitePersistence(store.db_path).read_source_player_observation(SESSION, operation_id="first")


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["missing", "corrupt", "old_schema", "missing_table", "no_manifest", "wrong_session"])
async def test_unavailable_or_incompatible_store_stays_unchanged(tmp_path, monkeypatch, kind):
    if kind == "missing":
        store = SQLitePersistence(tmp_path/"absent"/"db.sqlite3")
    elif kind == "corrupt":
        store = SQLitePersistence(tmp_path/"db.sqlite3")
        store.db_path.write_bytes(b"synthetic-corrupt-sqlite")
    else:
        store = await make_store(tmp_path)
        with sqlite3.connect(store.db_path) as db:
            if kind == "old_schema": db.execute("UPDATE schema_meta SET value='2' WHERE key='schema_version'")
            elif kind == "missing_table": db.execute("DROP TABLE episodic_memories")
            elif kind == "no_manifest":
                metadata = json.loads(db.execute("SELECT metadata_json FROM campaigns").fetchone()[0])
                del metadata["narrative_source_setup_manifest"]
                db.execute("UPDATE campaigns SET metadata_json=?", (json.dumps(metadata),))
    reader = SQLitePersistence(store.db_path)
    monkeypatch.setattr(reader, "initialize", forbid)
    before = store.db_path.read_bytes() if store.db_path.exists() else None
    paths = set(tmp_path.rglob("*"))
    with pytest.raises(SourceObservationError) as error:
        await reader.read_source_player_observation("other" if kind == "wrong_session" else SESSION)
    assert "PRIVATE" not in str(error.value) and str(store.db_path) not in str(error.value)
    assert (store.db_path.read_bytes() if store.db_path.exists() else None) == before
    assert set(tmp_path.rglob("*")) == paths


@pytest.mark.anyio
@pytest.mark.parametrize("bad", ["", " padded ", 1, True, "x"*241, "\ud800"])
async def test_bad_query_fails_before_any_connection(tmp_path, monkeypatch, bad):
    reader = SQLitePersistence(tmp_path/"absent.sqlite3")
    monkeypatch.setattr(sqlite3, "connect", forbid)
    with pytest.raises(SourceObservationError, match="source_observation_query_invalid"):
        await reader.read_source_player_observation(SESSION, operation_id=bad)
    with pytest.raises(SourceObservationError, match="source_observation_query_invalid"):
        await reader.read_source_player_observation(bad)


@pytest.mark.anyio
@pytest.mark.parametrize("failure", [sqlite3.OperationalError, OSError])
async def test_connection_cleanup_errors_are_closed(tmp_path, monkeypatch, failure):
    store = await make_store(tmp_path)
    reader = SQLitePersistence(store.db_path)
    def broken(*args, **kwargs): raise failure("PRIVATE_PATH_AND_DRIVER_DETAIL")
    monkeypatch.setattr(reader, "_source_setup_transaction", broken)
    with pytest.raises(SourceObservationError, match="^source_observation_stored_pair_invalid$") as error:
        await reader.read_source_player_observation(SESSION)
    assert "PRIVATE" not in str(error.value)


@pytest.mark.anyio
async def test_concurrent_commit_does_not_mix_latest_with_requested_snapshot(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    await prepare(store)
    assert (await run(store)).status == "completed"
    reader = SQLitePersistence(store.db_path)
    entered, release = threading.Event(), threading.Event()
    original = reader._source_setup_manifest_in_connection
    def held(connection, session):
        result = original(connection, session)  # This SELECT pins the read snapshot.
        entered.set()
        assert release.wait(10)
        return result
    monkeypatch.setattr(reader, "_source_setup_manifest_in_connection", held)
    reading = asyncio.create_task(reader.read_source_player_observation(SESSION, operation_id="first"))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        await prepare(store, "second")
        assert (await run(store, "second", SECOND)).status == "completed"
    finally:
        release.set()
    result = await reading
    assert result.latest_completed.operation.operation_id == "first"
    assert result.requested.narrative.current_turn == 1
    fresh = await SQLitePersistence(store.db_path).read_source_player_observation(SESSION, operation_id="first")
    assert fresh.latest_completed.operation.operation_id == "second"
    assert fresh.requested.narrative.current_turn == 2


@pytest.mark.anyio
async def test_cancelled_reader_propagates_without_writes_or_second_worker(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    before = ledger(store)
    reader = SQLitePersistence(store.db_path)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []
    original = reader._read_source_player_observation_sync
    def held(*args):
        calls.append(True)
        entered.set()
        assert release.wait(10)
        try: return original(*args)
        finally: finished.set()
    monkeypatch.setattr(reader, "_read_source_player_observation_sync", held)
    reading = asyncio.create_task(reader.read_source_player_observation(SESSION))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        reading.cancel()
        with pytest.raises(asyncio.CancelledError): await reading
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 5)
    assert calls == [True] and ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("p_status", ["pending", "failed"])
async def test_noncompleted_p_cannot_hide_displaced_h_identity(tmp_path, p_status):
    from api.narrative_source_preparation import _stable_id
    store = await make_store(tmp_path)
    if p_status == "pending":
        await store.claim_source_input(SESSION, {"operation_id": "first", "player_input": "Aguardo."},
                                       producer_config=config())
    else:
        await prepare(store, text="Voo através da parede.")
    with sqlite3.connect(store.db_path) as db:
        db.execute(
            """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,user_input,
               metadata_json,payload_hash,request_hash,started_at) VALUES (?,?,?,1,'pending',?,?,?,?,?)""",
            (_stable_id(SESSION, "first", "attempt"), SESSION, "displaced-h", "Aguardo.",
             "{}", "0"*64, "0"*64, utc_now().isoformat()),
        )
    before = ledger(store), store.db_path.read_bytes()
    with pytest.raises(SourceObservationError, match="^source_observation_stored_pair_invalid$"):
        await SQLitePersistence(store.db_path).read_source_player_observation(SESSION, operation_id="first")
    assert (ledger(store), store.db_path.read_bytes()) == before
