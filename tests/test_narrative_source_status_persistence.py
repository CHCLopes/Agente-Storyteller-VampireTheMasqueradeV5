"""Read-only retained B lifecycle observations from synthetic SQLite and FakeLLM."""
import asyncio
from datetime import timedelta
import json
import sqlite3
import threading

import pytest

from api import narrative_source_execution_service, rules_service
from api.llm.contract import CancellationToken, ErrorCategory, utc_now
from api.narrative_source_capsule import source_preparation_operation_id
from api.narrative_source_preparation import ResolvedActionPreparation
from api.narrative_source_status import SourceOperationStatusError, expected_source_attempt_metadata
from api.persistence import SQLitePersistence
from test_narrative_source_capsule_persistence import ledger
from test_narrative_source_coordinator import SESSION, make_store, prepare, run
from test_narrative_source_bridge import FIRST, SECOND, THIRD, _gateway
from test_narrative_source_preparation_bridge import (
    INVESTIGATION, INVESTIGATION_SUCCESS, INVESTIGATION_FAILURE, resolve_investigation,
)


class SimulatedCrash(BaseException):
    pass


async def pending(store, monkeypatch, operation="first"):
    """Let the actual executor reserve its actual metadata, then lose its process."""
    original = store.start_attempt
    async def crash(**kwargs):
        await original(**kwargs)
        raise SimulatedCrash()
    with monkeypatch.context() as context:
        context.setattr(store, "start_attempt", crash)
        with pytest.raises(SimulatedCrash):
            await run(store, operation)


def forbid(*args, **kwargs):
    pytest.fail("Status observation attempted initialization, execution, write or RNG")


async def observe(store, monkeypatch, operation="first"):
    before = ledger(store)
    reader = SQLitePersistence(store.db_path)
    with monkeypatch.context() as context:
        for name in ("initialize", "_connect", "start_attempt", "record_failed_attempt", "commit_turn",
                     "recover_pending_attempts", "save_source_preparation", "load_source_preparation",
                     "read_source_context_snapshot", "load_campaign", "load_attempt_by_operation",
                     "load_turn_by_operation"):
            context.setattr(reader, name, forbid)
        context.setattr(narrative_source_execution_service, "execute_source_turn", forbid)
        context.setattr(rules_service.random, "randint", forbid)
        result = await reader.read_source_operation_status(SESSION, operation)
    assert ledger(store) == before
    assert not reader._initialized and not reader._session_locks
    if result is not None:
        assert set(result.model_dump()) == {
            "protocol", "session_id", "operation_id", "capsule_sha256", "base_turn",
            "base_state_revision", "current_turn", "current_state_revision", "status",
            "committed_turn_id", "failure",
        }
    return result


@pytest.mark.anyio
async def test_absent_retained_and_pending_after_restart_have_no_execution_authority(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    assert await observe(store, monkeypatch) is None
    capsule = await prepare(store)
    retained = await observe(store, monkeypatch)
    assert retained.status == "retained_unstarted" and retained.failure is None
    assert retained.capsule_sha256 == capsule.fingerprint_sha256
    assert retained.base_turn == retained.current_turn == 0
    await pending(store, monkeypatch)
    actual = await store.load_attempt_by_operation(SESSION, "first")
    assert actual["metadata"] == expected_source_attempt_metadata(capsule)
    snapshot = await observe(store, monkeypatch)
    assert snapshot.status == "pending" and snapshot.committed_turn_id is None
    assert snapshot.failure is None


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["provider", "timeout", "policy", "delivery", "cancelled", "recovered"])
async def test_actual_terminal_paths_restore_original_safe_cause(tmp_path, monkeypatch, kind):
    store = await make_store(tmp_path)
    await prepare(store)
    _, gateway = _gateway()
    kwargs = {}
    if kind == "provider":
        _, gateway = _gateway(failure_category=ErrorCategory.PROVIDER_UNAVAILABLE)
    elif kind == "timeout":
        kwargs["deadline"] = utc_now() - timedelta(seconds=1)
    elif kind == "policy":
        _, gateway = _gateway(FIRST, "Qual é a cor da janela?")
    elif kind == "delivery":
        async def reject_chunk(value):
            raise RuntimeError("synthetic callback detail must not escape")
        kwargs["on_chunk"] = reject_chunk
    elif kind == "cancelled":
        cancellation = CancellationToken()
        cancellation.cancel("synthetic cancellation detail")
        kwargs["cancellation"] = cancellation
    if kind == "recovered":
        await pending(store, monkeypatch)
        assert await store.recover_pending_attempts(started_before=utc_now()) == 1
    else:
        result, _, _ = await run(store, gateway=gateway, **kwargs)
        assert result.status in {"failed", "timeout", "cancelled"}, result.error
    original = await store.load_attempt_by_operation(SESSION, "first")
    count = len(gateway.requests)
    snapshot = await observe(store, monkeypatch)
    assert snapshot.status == original["status"] and snapshot.committed_turn_id is None
    assert snapshot.failure.code == original["error"]["code"]
    assert snapshot.failure.stage == original["error"].get("stage")
    assert len(gateway.requests) == count
    if kind == "recovered":
        assert snapshot.failure.code == "process_interrupted" and snapshot.failure.stage is None
    assert "synthetic callback" not in snapshot.model_dump_json()
    assert "safe_message" not in snapshot.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("error,expected", [
    ({"code": "source_turn_cancelled"}, "source_turn_cancelled"),
    ({"code": "source_turn_provider_failure", "stage": "generation", "detail": "private synthetic text"},
     "source_turn_provider_failure"),
    ({"code": "unlisted private synthetic text", "stage": "generation"}, None),
    ({"code": "source_turn_cancelled", "stage": "private synthetic text"}, None),
    ("private synthetic text", None),
])
async def test_terminal_projection_discards_free_text_with_valid_result_hash(tmp_path, monkeypatch, error, expected):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    await pending(store, monkeypatch)
    await store.record_failed_attempt(
        session_id=SESSION, operation_id="first", attempt_id=capsule.draft.attempt_id,
        requested_turn=1, user_input=capsule.player_input, status="cancelled",
        error=error, metadata=expected_source_attempt_metadata(capsule),
    )
    snapshot = await observe(store, monkeypatch)
    if expected is None:
        assert snapshot.failure is None
    else:
        assert snapshot.failure.code == expected
    assert "private synthetic text" not in snapshot.model_dump_json()


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["declared", "resolved_success", "resolved_failure", "old_history"])
async def test_completed_snapshot_matches_retained_commit_with_controls_receipts_and_old_history(
    tmp_path, monkeypatch, mode,
):
    store = await make_store(tmp_path)
    await store.update_campaign_snapshot(SESSION, state={"counter": 0}, expected_turn=0, expected_revision=0)
    kwargs, text = {}, FIRST
    if mode.startswith("resolved"):
        success = mode == "resolved_success"
        action, receipt, rolls = resolve_investigation(monkeypatch, forbid, success=success)
        kwargs.update(preparation=ResolvedActionPreparation(action=action, resolution=receipt),
                      player_input=INVESTIGATION)
        text = INVESTIGATION_SUCCESS if success else INVESTIGATION_FAILURE
    capsule = await prepare(store, **kwargs)
    result, gateway, chunks = await run(store, text=text)
    assert result.status == "completed", result.error
    assert len(gateway.requests) == len(chunks) == 1
    if mode == "old_history":
        await store.update_campaign_snapshot(SESSION, state={"counter": 2}, expected_turn=1, expected_revision=2)
        for index, later_text in enumerate((SECOND, THIRD, THIRD), 2):
            await prepare(store, str(index), state={"counter": index})
            later, _, _ = await run(store, str(index), text=later_text)
            assert later.status == "completed", later.error
    snapshot = await observe(store, monkeypatch)
    assert snapshot.status == "completed" and snapshot.failure is None
    assert snapshot.committed_turn_id == capsule.draft.turn_id
    assert snapshot.base_turn == 0 and snapshot.base_state_revision == 1
    assert snapshot.current_turn == (4 if mode == "old_history" else 1)
    assert snapshot.current_state_revision == (6 if mode == "old_history" else 2)
    if mode.startswith("resolved"):
        assert len(rolls) == 5


@pytest.mark.anyio
async def test_stale_retained_base_is_observed_without_claiming_readiness(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    await prepare(store)
    await prepare(store, "competitor")
    completed, _, _ = await run(store, "competitor")
    assert completed.status == "completed"
    await store.update_campaign_snapshot(SESSION, state={"counter": 3}, expected_turn=1, expected_revision=1)
    stale = await observe(store, monkeypatch)
    assert stale.status == "retained_unstarted"
    assert (stale.base_turn, stale.base_state_revision) == (0, 0)
    assert (stale.current_turn, stale.current_state_revision) == (1, 2)
    result, gateway, _ = await run(store)
    assert result.status == "failed" and not gateway.requests
    failed = await observe(store, monkeypatch)
    assert failed.failure.code == "source_context_revision_mismatch"


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [
    "missing_control", "control_identity", "capsule_hash", "request_hash", "static_metadata",
    "pending_terminal_fields", "displaced_attempt", "completed_without_turn", "failure_hash",
    "completed_result_pair", "committed_state", "turn_without_attempt", "displaced_turn", "deep_metadata",
])
async def test_orphans_and_corrupt_capsule_attempt_turn_pairs_fail_closed(tmp_path, monkeypatch, mutation):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    if mutation in {"completed_result_pair", "committed_state", "turn_without_attempt", "displaced_turn"}:
        result, _, _ = await run(store)
        assert result.status == "completed"
    else:
        await pending(store, monkeypatch)
    with sqlite3.connect(store.db_path) as connection:
        control = source_preparation_operation_id(SESSION, "first")
        if mutation == "missing_control":
            connection.execute("DELETE FROM attempts WHERE operation_id=?", (control,))
        elif mutation == "control_identity":
            connection.execute("UPDATE attempts SET operation_id='displaced-control' WHERE operation_id=?", (control,))
        elif mutation == "capsule_hash":
            row = connection.execute("SELECT metadata_json FROM attempts WHERE operation_id=?", (control,)).fetchone()
            data = json.loads(row[0]); data["narrative_source_capsule"]["fingerprint_sha256"] = "0" * 64
            connection.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", (json.dumps(data), control))
        elif mutation == "deep_metadata":
            connection.execute("UPDATE attempts SET metadata_json=? WHERE operation_id='first'",
                               ("[" * 2000 + "0" + "]" * 2000,))
        elif mutation == "request_hash":
            connection.execute("UPDATE attempts SET request_hash=? WHERE operation_id='first'", ("0" * 64,))
        elif mutation == "static_metadata":
            # Matching row hashes still cannot substitute the retained SYSTEM identity.
            from api.persistence import _payload_hash, _attempt_request_payload
            metadata = expected_source_attempt_metadata(capsule)
            metadata["source_turn_static_sha256"] = "0" * 64
            digest = _payload_hash(_attempt_request_payload(1, capsule.player_input, metadata))
            connection.execute("UPDATE attempts SET metadata_json=?, request_hash=?, payload_hash=? WHERE operation_id='first'",
                               (json.dumps(metadata), digest, digest))
        elif mutation == "pending_terminal_fields":
            connection.execute("UPDATE attempts SET result_hash=? WHERE operation_id='first'", ("0" * 64,))
        elif mutation == "displaced_attempt":
            connection.execute("UPDATE attempts SET operation_id='displaced' WHERE operation_id='first'")
        elif mutation == "completed_without_turn":
            connection.execute("UPDATE attempts SET status='completed', committed_turn_id=? WHERE operation_id='first'",
                               (capsule.draft.turn_id,))
        elif mutation == "failure_hash":
            connection.execute("UPDATE attempts SET status='failed', error_json='{}', result_hash=?, completed_at=started_at WHERE operation_id='first'",
                               ("0" * 64,))
        elif mutation == "completed_result_pair":
            connection.execute("UPDATE attempts SET result_hash=? WHERE operation_id='first'", ("0" * 64,))
            connection.execute("UPDATE turns SET payload_hash=? WHERE operation_id='first'", ("0" * 64,))
        elif mutation == "committed_state":
            connection.execute("UPDATE turns SET state_json='{}' WHERE operation_id='first'")
        elif mutation == "turn_without_attempt":
            connection.execute("DELETE FROM attempts WHERE operation_id='first'")
        elif mutation == "displaced_turn":
            connection.execute("UPDATE turns SET operation_id='displaced' WHERE operation_id='first'")
    before = ledger(store)
    with pytest.raises(SourceOperationStatusError, match="^source_operation_status_"):
        await SQLitePersistence(store.db_path).read_source_operation_status(SESSION, "first")
    assert ledger(store) == before


@pytest.mark.anyio
async def test_missing_capsule_with_h6_and_no_capsule_with_unstarted_orphan_control(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    capsule = await prepare(store)
    control = source_preparation_operation_id(SESSION, "first")
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE attempts SET operation_id='changed' WHERE operation_id=?", (control,))
    with pytest.raises(SourceOperationStatusError):
        await SQLitePersistence(store.db_path).read_source_operation_status(SESSION, "first")
    assert capsule is not None


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["missing_parent", "empty_database", "old_schema", "missing_table", "legacy_campaign", "absent_campaign"])
async def test_read_only_refusal_never_creates_migrates_or_initializes(tmp_path, monkeypatch, kind):
    path = tmp_path / "db.sqlite3"
    if kind == "missing_parent":
        path = tmp_path / "absent" / "db.sqlite3"
    elif kind == "empty_database":
        path.touch()
    else:
        store = await make_store(tmp_path)
        path = store.db_path
        with sqlite3.connect(path) as connection:
            if kind == "old_schema":
                connection.execute("UPDATE schema_meta SET value='2' WHERE key='schema_version'")
            elif kind == "missing_table":
                connection.execute("DROP TABLE consolidations")
            elif kind == "legacy_campaign":
                connection.execute("UPDATE campaigns SET metadata_json='{}'")
            elif kind == "absent_campaign":
                connection.execute("DELETE FROM campaigns")
    original = path.read_bytes() if path.exists() else None
    reader = SQLitePersistence(path)
    monkeypatch.setattr(reader, "initialize", forbid)
    monkeypatch.setattr(reader, "_connect", forbid)
    with pytest.raises(SourceOperationStatusError, match="^source_operation_status_"):
        await reader.read_source_operation_status(SESSION, "first")
    assert (path.read_bytes() if path.exists() else None) == original
    if kind == "missing_parent":
        assert not path.parent.exists()
    assert not reader._initialized


@pytest.mark.anyio
async def test_single_read_snapshot_survives_concurrent_commit_and_connection_closes(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    await prepare(store)
    _, gateway = _gateway()
    generation_entered, allow_generation = asyncio.Event(), asyncio.Event()
    generate = gateway.generate_structured
    async def delayed(request):
        generation_entered.set()
        await allow_generation.wait()
        return await generate(request)
    monkeypatch.setattr(gateway, "generate_structured", delayed)
    execution = asyncio.create_task(run(store, gateway=gateway))
    await asyncio.wait_for(generation_entered.wait(), 5)
    reader = SQLitePersistence(store.db_path)
    captured = threading.Event()
    committed = threading.Event()
    original = reader._source_context_snapshot_in_connection
    def interleave(connection, *args, **kwargs):
        snapshot = original(connection, *args, **kwargs)
        captured.set()
        assert committed.wait(5), "Writer did not commit while reader retained its snapshot"
        return snapshot
    monkeypatch.setattr(reader, "_source_context_snapshot_in_connection", interleave)
    connections, traces = [], []
    connect = sqlite3.connect
    def track(*args, **kwargs):
        if kwargs.get("uri"):
            kwargs["check_same_thread"] = False
        connection = connect(*args, **kwargs)
        if kwargs.get("uri"):
            assert args[0].endswith("?mode=ro")
            connections.append(connection)
            connection.set_trace_callback(traces.append)
        return connection
    monkeypatch.setattr(sqlite3, "connect", track)
    reading = asyncio.create_task(reader.read_source_operation_status(SESSION, "first"))
    assert await asyncio.to_thread(captured.wait, 5)
    try:
        allow_generation.set()
        result, _, _ = await asyncio.wait_for(execution, 5)
        assert result.status == "completed", result.error
    finally:
        committed.set()
    old = await asyncio.wait_for(reading, 5)
    assert old.status == "pending" and old.current_turn == old.current_state_revision == 0
    current = await SQLitePersistence(store.db_path).read_source_operation_status(SESSION, "first")
    assert current.status == "completed" and current.current_turn == current.current_state_revision == 1
    assert traces[0] == "BEGIN"
    assert all(sql.lstrip().upper().startswith(("BEGIN", "SELECT", "PRAGMA")) for sql in traces)
    assert len(connections) == 2
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connection.execute("SELECT 1")
    assert len(gateway.requests) == 1
