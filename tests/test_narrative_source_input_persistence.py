"""Synthetic SQLite producer P reservation, atomic P/K completion, and old H6 compatibility."""
import asyncio
from copy import deepcopy
import json
import sqlite3

import pytest

from api import rules_service
from api.llm.contract import GenerationParameters, utc_now
from api.narrative_source_capsule import create_source_turn_capsule, source_preparation_operation_id
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_input import (
    REQUEST_KEY, COMPLETION_KEY, SourceInputClaim, SourceInputFailure, SourceInputRequest,
    create_source_input_completion, create_source_producer_config, source_input_operation_id,
    source_input_attempt_id, source_input_request_hash, source_input_request_metadata,
    source_input_result_hash,
)
from api.narrative_source_preparation import DeclaredActionPreparation
from api.persistence import SQLitePersistence, SourceInputPersistenceError, _payload_hash
from test_narrative_source_capsule_persistence import ledger
from test_narrative_source_coordinator import SESSION, ACTION, make_store, run, prepare
from test_narrative_source_bridge import FIRST, SECOND, THIRD, SYSTEM, _gateway
from test_narrative_source_status_persistence import pending


def config(**overrides):
    target, _ = _gateway()
    values = dict(target=target, system_prompt=SYSTEM,
                  parameters=GenerationParameters(temperature=.65, max_output_tokens=768))
    values.update(overrides)
    return create_source_producer_config(**values)


def public(operation="first", player_input=ACTION):
    return SourcePlayerActionRequest(operation_id=operation, player_input=player_input)


async def claim(store, operation="first", *, producer_config=None, player_input=ACTION):
    return await store.claim_source_input(SESSION, public(operation, player_input), producer_config=producer_config or config())


def capsule_for(request):
    return create_source_turn_capsule(request.snapshot, operation_id=request.operation_id,
        created_at=request.created_at, player_input=request.player_input,
        preparation=DeclaredActionPreparation(), state=request.state, relationships=request.relationships,
        target=request.config.target, system_prompt=request.config.system_prompt, parameters=request.config.parameters,
        player_aliases=request.config.player_aliases, npc_aliases=request.config.npc_aliases,
        chronicle_name=request.config.chronicle_name)


async def finish(store, value, *, capsule=None, status="completed", failure=None):
    request = value.request
    capsule = capsule if capsule is not None else (capsule_for(request) if status == "completed" else None)
    completion = create_source_input_completion(request, status=status, capsule=capsule, failure=failure)
    result = await store.finalize_source_input(SESSION, request.operation_id,
        request_sha256=source_input_request_hash(request), completion=completion, capsule=capsule)
    return result, capsule


def forbid(*args, **kwargs):
    pytest.fail("Producer persistence called initialization, old public operations, RNG or gateway")


def assert_only_attempts_changed(before, after):
    assert all(after[table] == before[table] for table in before if table != "attempts")


@pytest.mark.anyio
async def test_claim_capture_and_atomic_completion_are_isolated_then_original_h6_runs(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    reader = SQLitePersistence(store.db_path)
    before = ledger(store)
    with monkeypatch.context() as context:
        for name in ("initialize", "_connect", "load_campaign", "start_attempt", "complete_control_attempt",
                     "save_source_preparation", "load_source_preparation", "read_source_context_snapshot",
                     "read_source_operation_status", "recover_pending_attempts", "record_failed_attempt"):
            context.setattr(reader, name, forbid)
        context.setattr(rules_service, "calculate_resolution", forbid)
        context.setattr(rules_service.random, "randint", forbid)
        fresh = await claim(reader)
        assert fresh.status == "pending" and fresh.newly_claimed
        assert fresh.request.snapshot.current_turn == fresh.request.snapshot.state_revision == 0
        assert fresh.request.state == {"counter": 0} and fresh.request.relationships == {}
        completed, capsule = await finish(reader, fresh)
        assert completed.status == "completed" and not completed.newly_claimed
    assert not reader._initialized
    after = ledger(store)
    assert_only_attempts_changed(before, after)
    assert len(after["attempts"]) == 2
    assert await store.load_source_preparation(SESSION, "first") == capsule
    assert (await store.read_source_operation_status(SESSION, "first")).status == "retained_unstarted"
    assert await store.load_attempt_by_operation(SESSION, "first") is None
    result, gateway, chunks = await run(store)
    assert result.status == "completed" and len(gateway.requests) == len(chunks) == 1
    before = ledger(store)
    replay, _ = await finish(SQLitePersistence(store.db_path), fresh, capsule=capsule)
    assert replay == completed
    assert ledger(store) == before
    assert (await claim(SQLitePersistence(store.db_path))).request == fresh.request


@pytest.mark.anyio
@pytest.mark.parametrize("same", [True, False])
async def test_atomic_claims_across_store_instances_reserve_only_one_producer(tmp_path, same):
    store = await make_store(tmp_path)
    result = await asyncio.gather(claim(store), claim(SQLitePersistence(store.db_path), "first" if same else "second"),
                                  return_exceptions=True)
    if same:
        assert sorted(value.newly_claimed for value in result) == [False, True]
        assert result[0].request == result[1].request
    else:
        assert sum(isinstance(value, SourceInputClaim) for value in result) == 1
        assert [value.code for value in result if isinstance(value, SourceInputPersistenceError)] == ["source_input_session_busy"]
    assert len(ledger(store)["attempts"]) == 1


@pytest.mark.anyio
async def test_idempotent_claim_uses_original_time_base_and_config_without_reinterpreting(tmp_path):
    store = await make_store(tmp_path)
    original = await claim(store)
    await store.update_campaign_snapshot(SESSION, state={"counter": 3}, expected_turn=0, expected_revision=0)
    before = ledger(store)
    replay = await claim(SQLitePersistence(store.db_path))
    assert replay.request == original.request and not replay.newly_claimed
    assert ledger(store) == before
    for kwargs in ({"player_input": "Aguardo."}, {"producer_config": config(system_prompt=SYSTEM + " Other.")}):
        with pytest.raises(SourceInputPersistenceError, match="source_input_operation_conflict"):
            await claim(store, **kwargs)
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("status,code", [
    ("failed", "source_input_clarification_required"), ("failed", "source_input_out_of_scope"),
    ("failed", "source_input_production_failed"), ("timeout", "source_input_deadline_exceeded"),
    ("cancelled", "source_input_cancelled"),
])
async def test_terminal_failures_without_capsule_are_durable_idempotent_and_release_guard(tmp_path, status, code):
    store = await make_store(tmp_path)
    value = await claim(store)
    await store.update_campaign_snapshot(SESSION, state={"counter": 1}, expected_turn=0, expected_revision=0)
    result, _ = await finish(store, value, status=status, failure=SourceInputFailure(code=code, stage="production"))
    assert result.status == status and result.completion.failure.code == code
    before = ledger(store)
    repeated, _ = await finish(SQLitePersistence(store.db_path), value, status=status,
                               failure=SourceInputFailure(code=code, stage="production"))
    assert repeated == result and ledger(store) == before
    observed = await claim(SQLitePersistence(store.db_path))
    assert observed.completion == result.completion and not observed.newly_claimed
    assert await store.load_source_preparation(SESSION, "first") is None
    assert (await claim(store, "second")).newly_claimed


@pytest.mark.anyio
async def test_stale_prepared_result_becomes_persisted_failure_without_k_or_rollback(tmp_path):
    store = await make_store(tmp_path)
    value = await claim(store)
    await store.update_campaign_snapshot(SESSION, state={"counter": 8}, expected_turn=0, expected_revision=0)
    before = ledger(store)
    result, capsule = await finish(store, value)
    assert result.status == "failed" and result.completion.failure.code == "source_input_base_mismatch"
    assert await store.load_source_preparation(SESSION, "first") is None
    assert_only_attempts_changed(before, ledger(store))
    assert (await claim(store)).completion == result.completion
    with pytest.raises(SourceInputPersistenceError, match="source_input_operation_conflict"):
        await finish(store, value, capsule=capsule)
    repeated = await store.finalize_source_input(SESSION, "first", request_sha256=source_input_request_hash(value.request),
                                                completion=result.completion)
    assert repeated == result
    assert (await claim(store, "second")).newly_claimed


@pytest.mark.anyio
async def test_recovery_uses_real_old_error_hash_and_never_rewrites_or_reopens_p(tmp_path):
    store = await make_store(tmp_path)
    original = await claim(store)
    assert await store.recover_pending_attempts(started_before=utc_now()) == 1
    before = ledger(store)
    row = await store.load_attempt_by_operation(SESSION, source_input_operation_id(SESSION, "first"))
    assert set(row["metadata"]) == {REQUEST_KEY}
    restored = await claim(SQLitePersistence(store.db_path))
    assert restored.status == "cancelled" and not restored.newly_claimed
    assert restored.completion.failure.code == "process_interrupted"
    assert restored.completion.failure.stage is None
    assert row["result_hash"] != source_input_result_hash(original.request, restored.completion)
    repeated = await store.finalize_source_input(SESSION, "first", request_sha256=source_input_request_hash(original.request),
                                                completion=restored.completion)
    assert repeated == restored and ledger(store) == before
    with pytest.raises(SourceInputPersistenceError, match="source_input_operation_conflict"):
        await finish(store, original)
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("h6", ["absent", "pending", "completed", "failed", "timeout", "cancelled"])
async def test_session_guard_revalidates_completed_producer_and_h6_terminal_state(tmp_path, monkeypatch, h6):
    store = await make_store(tmp_path)
    first = await claim(store)
    await finish(store, first)
    if h6 == "pending":
        await pending(store, monkeypatch)
    elif h6 in {"completed", "failed", "timeout", "cancelled"}:
        _, gateway = _gateway(FIRST, "Qual é a cor da janela?" if h6 == "failed" else "O que você faz agora?")
        kwargs = {}
        if h6 == "timeout":
            kwargs["deadline"] = first.request.created_at
        elif h6 == "cancelled":
            from api.llm.contract import CancellationToken
            token = CancellationToken(); token.cancel("synthetic")
            kwargs["cancellation"] = token
        result, _, _ = await run(store, gateway=gateway, **kwargs)
        assert result.status == h6
    before = ledger(store)
    if h6 in {"absent", "pending"}:
        with pytest.raises(SourceInputPersistenceError, match="source_input_session_busy"):
            await claim(SQLitePersistence(store.db_path), "second")
        assert ledger(store) == before
    else:
        assert (await claim(SQLitePersistence(store.db_path), "second")).newly_claimed


@pytest.mark.anyio
async def test_external_controls_are_not_producers_and_existing_internal_capsule_is_not_adopted(tmp_path):
    store = await make_store(tmp_path)
    await store.complete_control_attempt(session_id=SESSION, operation_id="old-control", user_input="control", metadata={"interceptor": "local"})
    value = await claim(store)
    await finish(store, value, status="failed", failure=SourceInputFailure(code="source_input_out_of_scope"))
    await prepare(store, "old-internal")
    before = ledger(store)
    with pytest.raises(SourceInputPersistenceError, match="source_input_stored_pair_invalid"):
        await claim(store, "old-internal")
    assert ledger(store) == before
    assert (await claim(store, "second")).newly_claimed


@pytest.mark.anyio
@pytest.mark.parametrize("producer_status", ["pending", "failed", "completed"])
async def test_old_prefix_remains_valid_outside_two_source_window_without_fake_capsule(tmp_path, producer_status):
    store = await make_store(tmp_path)
    await prepare(store, "before")
    assert (await run(store, "before"))[0].status == "completed"
    original = await claim(store)
    capsule = None
    if producer_status == "failed":
        await finish(store, original, status="failed", failure=SourceInputFailure(code="source_input_out_of_scope"))
    elif producer_status == "completed":
        _, capsule = await finish(store, original)
        assert (await run(store))[0].status == "completed"
    for index, text in enumerate((SECOND, THIRD, THIRD), 1):
        await prepare(store, "later-" + str(index))
        assert (await run(store, "later-" + str(index), text=text))[0].status == "completed"
    before = ledger(store)
    restored = await claim(SQLitePersistence(store.db_path))
    assert restored.request == original.request and restored.status == producer_status
    assert len(restored.request.snapshot.sources) == 1
    assert ledger(store) == before
    if capsule:
        again, _ = await finish(SQLitePersistence(store.db_path), original, capsule=capsule)
        assert again == restored


@pytest.mark.anyio
async def test_failure_between_insert_k_and_update_p_rolls_back_both_and_closes(tmp_path, monkeypatch):
    store = await make_store(tmp_path)
    value = await claim(store)
    before = ledger(store)
    closed = []
    class Interrupted(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("UPDATE attempts SET status=?,error_json=?,metadata_json=?"):
                raise sqlite3.OperationalError("synthetic interruption between K and P")
            return super().execute(sql, *args, **kwargs)
        def close(self):
            closed.append(True)
            return super().close()
    connect = sqlite3.connect
    def intercepted(*args, **kwargs):
        if kwargs.get("uri"):
            kwargs["factory"] = Interrupted
        return connect(*args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(sqlite3, "connect", intercepted)
        with pytest.raises(SourceInputPersistenceError, match="source_input_stored_pair_invalid"):
            await finish(store, value)
    assert closed == [True]
    assert ledger(store) == before
    replay = await claim(store)
    assert replay.status == "pending" and not replay.newly_claimed
    assert await store.load_source_preparation(SESSION, "first") is None


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [
    "request_hash", "payload_hash", "input", "displaced_operation", "missing_default_field",
    "deep_metadata", "pending_result", "orphan_k", "completed_k_missing", "completed_hash",
    "recovery_error", "forged_original_sources",
])
async def test_corrupt_controls_are_not_replayed_or_treated_as_free(tmp_path, mutation):
    store = await make_store(tmp_path)
    if mutation == "forged_original_sources":
        await prepare(store, "before")
        assert (await run(store, "before"))[0].status == "completed"
    original = await claim(store)
    if mutation == "forged_original_sources":
        await prepare(store, "after")
        assert (await run(store, "after", text=SECOND))[0].status == "completed"
        later = await store.read_source_context_snapshot(SESSION)
    if mutation.startswith("completed"):
        await finish(store, original)
    elif mutation == "recovery_error":
        await store.recover_pending_attempts(started_before=utc_now())
    elif mutation == "orphan_k":
        await store.save_source_preparation(capsule_for(original.request))
    with sqlite3.connect(store.db_path) as connection:
        pid = source_input_operation_id(SESSION, "first")
        if mutation in {"request_hash", "payload_hash"}:
            connection.execute(f"UPDATE attempts SET {mutation}=? WHERE operation_id=?", ("0"*64, pid))
        elif mutation == "input":
            connection.execute("UPDATE attempts SET user_input='altered' WHERE operation_id=?", (pid,))
        elif mutation == "displaced_operation":
            connection.execute("UPDATE attempts SET operation_id='displaced' WHERE operation_id=?", (pid,))
        elif mutation == "missing_default_field":
            metadata = source_input_request_metadata(original.request)
            metadata[REQUEST_KEY]["config"].pop("profile")
            connection.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", (json.dumps(metadata), pid))
        elif mutation == "deep_metadata":
            connection.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", ("["*2000+"0"+"]"*2000, pid))
        elif mutation == "pending_result":
            connection.execute("UPDATE attempts SET result_hash=? WHERE operation_id=?", ("0"*64, pid))
        elif mutation == "completed_k_missing":
            connection.execute("DELETE FROM attempts WHERE operation_id=?", (source_preparation_operation_id(SESSION, "first"),))
        elif mutation == "completed_hash":
            connection.execute("UPDATE attempts SET result_hash=? WHERE operation_id=?", ("0"*64, pid))
        elif mutation == "recovery_error":
            connection.execute("UPDATE attempts SET error_json=? WHERE operation_id=?", (json.dumps({"code":"process_interrupted","safe_message":"free synthetic text"}), pid))
        elif mutation == "forged_original_sources":
            # Another valid envelope, consistently rehashed, is not this request's historical prefix.
            metadata = source_input_request_metadata(original.request)
            data = metadata[REQUEST_KEY]
            data["snapshot"]["selected_turn_ids"] = [later.selected_turn_ids[-1]]
            data["snapshot"]["sources"] = [later.sources[-1].model_dump(mode="json")]
            data["snapshot"]["omitted_turn_ids"] = []
            payload = {key: value for key,value in data.items() if key != "fingerprint_sha256"}
            data["fingerprint_sha256"] = _payload_hash(payload)
            SourceInputRequest.model_validate(data)  # Pure consistency passes; DB prefix must reject.
            digest = _payload_hash({"requested_turn": original.request.snapshot.current_turn+1, "user_input": ACTION, "metadata":metadata})
            connection.execute("UPDATE attempts SET metadata_json=?,request_hash=?,payload_hash=? WHERE operation_id=?",
                               (json.dumps(metadata), digest, digest, pid))
    before = ledger(store)
    for operation in ("first", "second"):
        with pytest.raises(SourceInputPersistenceError) as error:
            await claim(SQLitePersistence(store.db_path), operation)
        assert error.value.code != "source_input_session_busy"
        assert "free synthetic text" not in str(error.value)
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("forgery", ["outer_extra", "nested_extra", "state_changed", "wrong_request_hash", "no_claim"])
async def test_finalization_refuses_forged_or_unbound_result_without_mutation(tmp_path, forgery):
    store = await make_store(tmp_path)
    value = await claim(store)
    capsule = capsule_for(value.request)
    completion = create_source_input_completion(value.request, status="completed", capsule=capsule)
    request_hash = source_input_request_hash(value.request)
    operation = "first"
    if forgery == "outer_extra":
        capsule = capsule.model_copy(update={"unexpected": "forged"})
    elif forgery == "nested_extra":
        capsule = capsule.model_copy(update={"draft": capsule.draft.model_copy(update={"unexpected":"forged"})})
    elif forgery == "state_changed":
        capsule = capsule.model_copy(update={"state": {"counter": 99}})
    elif forgery == "wrong_request_hash":
        request_hash = value.request.fingerprint_sha256
    else:
        operation = "absent"
        completion = create_source_input_completion(value.request, status="failed", failure=SourceInputFailure(code="source_input_out_of_scope"))
        capsule = None
    before = ledger(store)
    with pytest.raises(SourceInputPersistenceError):
        await store.finalize_source_input(SESSION, operation, request_sha256=request_hash, completion=completion, capsule=capsule)
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["absent", "empty", "old_schema", "legacy_campaign"])
async def test_existing_current_schema_required_without_creation_or_migration(tmp_path, kind, monkeypatch):
    path = tmp_path / "absent-parent" / "db.sqlite3"
    if kind == "empty":
        path = tmp_path / "empty.sqlite3"; path.touch()
    elif kind in {"old_schema", "legacy_campaign"}:
        store = await make_store(tmp_path); path = store.db_path
        with sqlite3.connect(path) as connection:
            if kind == "old_schema":
                connection.execute("UPDATE schema_meta SET value='2' WHERE key='schema_version'")
            else:
                connection.execute("UPDATE campaigns SET metadata_json='{}'")
    before = path.read_bytes() if path.exists() else None
    reader = SQLitePersistence(path)
    monkeypatch.setattr(reader, "initialize", forbid)
    monkeypatch.setattr(reader, "_connect", forbid)
    with pytest.raises(SourceInputPersistenceError):
        await claim(reader)
    assert (path.read_bytes() if path.exists() else None) == before
    if kind == "absent":
        assert not path.parent.exists()
    assert not reader._initialized


@pytest.mark.anyio
async def test_two_finalizers_share_one_atomic_k_and_terminal_p(tmp_path):
    store = await make_store(tmp_path)
    value = await claim(store)
    results = await asyncio.gather(finish(store, value), finish(SQLitePersistence(store.db_path), value))
    assert results[0][0] == results[1][0]
    assert results[0][1] == results[1][1]
    assert len(ledger(store)["attempts"]) == 2
    assert not ledger(store)["turns"]
    with pytest.raises(SourceInputPersistenceError, match="source_input_operation_conflict"):
        await finish(store, value, status="failed", failure=SourceInputFailure(code="source_input_out_of_scope"))
