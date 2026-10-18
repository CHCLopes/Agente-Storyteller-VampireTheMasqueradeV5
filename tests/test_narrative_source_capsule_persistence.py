"""Durable source preparation controls; no H6, provider, or production save."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3

import pytest

from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_capsule import (
    CAPSULE_KEY, SourceCapsuleError, create_source_turn_capsule,
    source_preparation_operation_id, source_preparation_attempt_id,
)
from api.narrative_source_context import SourceContextError
from api.narrative_source_preparation import DeclaredActionPreparation
from api.persistence import IdempotencyConflictError, SQLitePersistence
from api.scene_service import SceneState
from test_narrative_source_context_persistence import commit as commit_existing_source
from test_narrative_source_persistence import TEXT


SESSION = "source-session"
OPERATION = "retained-operation"
SCENE = SceneState(location="Galeria")
NOW = datetime(2026, 9, 10, 23, 0, tzinfo=timezone.utc)


def capsule(snapshot, *, operation=OPERATION, state=None):
    return create_source_turn_capsule(
        snapshot, operation_id=operation, created_at=NOW,
        player_input="Observo a galeria sem tocar em nada.", preparation=DeclaredActionPreparation(),
        state={"counter": 1} if state is None else state, relationships={},
        target=LLMTarget(profile="retained-test", provider="fake", model="synthetic"),
        system_prompt="Fixture pública de preparação retida.",
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
    )


async def create(tmp_path, *, name="retained.sqlite3", session=SESSION):
    store = SQLitePersistence(tmp_path / name)
    await store.create_narrative_source_campaign(session, initial_scene=SCENE, initial_state={"counter": 0})
    return store


def ledger(store):
    with sqlite3.connect(store.db_path) as connection:
        return {table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("campaigns", "attempts", "turns", "events", "memory_candidates",
                              "episodic_memories", "consolidations", "legacy_imports")}


@pytest.mark.anyio
async def test_retention_restart_and_recovery_preserve_capsule_without_h6_or_campaign_change(tmp_path):
    store = await create(tmp_path)
    assert await store.load_source_preparation(SESSION, OPERATION) is None
    item = capsule(await store.read_source_context_snapshot(SESSION))
    before = ledger(store)
    saved = await store.save_source_preparation(item)
    assert saved.status == "completed" and not saved.idempotent and saved.state_revision == 0
    assert saved.operation_id == source_preparation_operation_id(SESSION, OPERATION)
    assert saved.attempt_id == source_preparation_attempt_id(SESSION, OPERATION)
    after = ledger(store)
    assert all(after[key] == before[key] for key in before if key != "attempts")
    assert len(after["attempts"]) == 1
    assert await store.load_attempt_by_operation(SESSION, OPERATION) is None
    restarted = SQLitePersistence(store.db_path)
    assert await restarted.load_source_preparation(SESSION, OPERATION) == item
    assert await restarted.recover_pending_attempts(started_before=datetime.now(timezone.utc)) == 0
    assert await restarted.load_source_preparation(SESSION, OPERATION) == item
    assert (await restarted.save_source_preparation(item)).idempotent
    assert ledger(store) == after
    assert (await store.database_info())["schema_version"] == 4


@pytest.mark.anyio
@pytest.mark.parametrize("different", [False, True])
async def test_concurrent_capsules_are_atomic_idempotent_or_conflicting(tmp_path, different):
    first = await create(tmp_path)
    second = SQLitePersistence(first.db_path)
    snapshot = await first.read_source_context_snapshot(SESSION)
    one = capsule(snapshot)
    two = capsule(snapshot, state={"counter": 8}) if different else capsule(snapshot)
    results = await asyncio.gather(first.save_source_preparation(one), second.save_source_preparation(two),
                                   return_exceptions=True)
    if different:
        assert sum(isinstance(value, IdempotencyConflictError) for value in results) == 1
        assert await first.load_source_preparation(SESSION, OPERATION) in (one, two)
    else:
        assert sorted(value.idempotent for value in results) == [False, True]
    assert len(ledger(first)["attempts"]) == 1 and not ledger(first)["turns"]
    assert (await first.load_campaign(SESSION))["state_revision"] == 0


@pytest.mark.anyio
async def test_equal_capsule_load_and_save_after_controls_and_more_than_two_turns(tmp_path):
    store = await create(tmp_path)
    await commit_existing_source(store, 1, narrative_text=TEXT + " O reflexo permanece imóvel sobre o vidro.")
    old = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(old)
    await store.update_campaign_snapshot(SESSION, state={"counter": 2}, expected_turn=1, expected_revision=1)
    for index in (2,3,4): await commit_existing_source(store,index)
    before = ledger(store)
    restarted = SQLitePersistence(store.db_path)
    loaded = await restarted.load_source_preparation(SESSION, OPERATION)
    assert loaded == old and loaded.snapshot.selected_turn_ids == ("turn-1",)
    assert len(loaded.snapshot.sources[0].projection.text) > 600
    assert (await restarted.save_source_preparation(old)).idempotent
    assert ledger(store) == before


@pytest.mark.anyio
async def test_new_capsule_checks_base_under_transaction_and_does_not_replace_stale_input(tmp_path):
    store = await create(tmp_path)
    stale = capsule(await store.read_source_context_snapshot(SESSION))
    await store.update_campaign_snapshot(SESSION, state={"counter": 1}, expected_turn=0, expected_revision=0)
    before = ledger(store)
    with pytest.raises(SourceCapsuleError, match="source_capsule_base_mismatch"):
        await store.save_source_preparation(stale)
    assert ledger(store) == before
    assert await store.load_source_preparation(SESSION, OPERATION) is None


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["pending", "failed", "completed"])
async def test_new_capsule_cannot_capture_an_existing_h6_operation(tmp_path, status):
    store = await create(tmp_path)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.start_attempt(session_id=SESSION, operation_id=OPERATION, requested_turn=1, user_input=item.player_input)
    if status == "failed":
        await store.record_failed_attempt(session_id=SESSION, operation_id=OPERATION, requested_turn=1,
                                          user_input=item.player_input, error={"code":"local"})
    elif status == "completed":
        await store.complete_control_attempt(session_id=SESSION, operation_id=OPERATION, requested_turn=1,
                                             user_input=item.player_input)
    before = ledger(store)
    with pytest.raises(SourceCapsuleError, match="source_capsule_operation_already_started"):
        await store.save_source_preparation(item)
    assert ledger(store) == before


@pytest.mark.anyio
async def test_existing_capsule_is_not_invalidated_by_a_later_pending_h6(tmp_path):
    store = await create(tmp_path)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(item)
    await store.start_attempt(session_id=SESSION, operation_id=OPERATION, attempt_id=item.draft.attempt_id,
                              requested_turn=1, user_input=item.player_input)
    before = ledger(store)
    assert await store.load_source_preparation(SESSION, OPERATION) == item
    assert (await store.save_source_preparation(item)).idempotent
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [
    "attempt_id", "status", "requested_turn", "user_input", "partial_narrative", "error_json",
    "provenance_json", "usage_json", "request_hash", "payload_hash", "result_hash",
    "metadata_json", "started_at", "completed_at", "committed_turn_id",
])
async def test_mutated_control_row_is_refused_on_load_and_idempotent_save(tmp_path, mutation):
    store = await create(tmp_path)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(item)
    replacements = {"status":"pending", "requested_turn":7, "error_json":"{}", "provenance_json":"{}",
                    "usage_json":"{}", "metadata_json":json.dumps({CAPSULE_KEY:item.model_dump(mode="json"),"extra":True}),
                    "started_at":"invalid", "completed_at":NOW.isoformat()}
    with sqlite3.connect(store.db_path) as connection:
        connection.execute(f"UPDATE attempts SET {mutation}=? WHERE operation_id=?",
                           (replacements.get(mutation,"altered"), source_preparation_operation_id(SESSION, OPERATION)))
    before = ledger(store)
    with pytest.raises(SourceCapsuleError): await store.load_source_preparation(SESSION, OPERATION)
    with pytest.raises(SourceCapsuleError): await store.save_source_preparation(item)
    assert ledger(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["origin", "legacy_older", "dependency"])
async def test_load_and_replay_validate_entire_current_history_not_only_the_capsule(tmp_path, mutation):
    store = await create(tmp_path)
    for index in (1,2,3): await commit_existing_source(store,index)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(item)
    with sqlite3.connect(store.db_path) as connection:
        if mutation == "origin": connection.execute("UPDATE campaigns SET metadata_json='{}'")
        elif mutation == "legacy_older": connection.execute("UPDATE turns SET context_json='{}' WHERE turn_number=1")
        else:
            connection.execute("""INSERT INTO legacy_imports(session_id,source_kind,source_path,content_fingerprint,
                                parse_status,audited_at) VALUES (?,?,?,?,?,?)""",
                               (SESSION,"synthetic","fixture","fixture","missing",NOW.isoformat()))
    before = ledger(store)
    with pytest.raises(SourceContextError): await store.load_source_preparation(SESSION, OPERATION)
    with pytest.raises(SourceContextError): await store.save_source_preparation(item)
    assert ledger(store) == before


@pytest.mark.anyio
async def test_capsule_snapshot_sources_are_checked_against_retained_historical_prefix(tmp_path):
    store = await create(tmp_path)
    await commit_existing_source(store,1)
    original = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(original)
    other = await create(tmp_path,name="different-source.sqlite3")
    await commit_existing_source(other,1,narrative_text=TEXT + " A chuva continua distante.")
    forged = capsule(await other.read_source_context_snapshot(SESSION))
    # Recompute a coherent control hash as an adversarial setup: a valid capsule
    # still must match actual historical sources, not only its own fingerprint.
    metadata, request_hash, result_hash = store._source_preparation_payloads(forged)
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE attempts SET metadata_json=?,request_hash=?,payload_hash=?,result_hash=? WHERE operation_id=?",
                           (json.dumps(metadata),request_hash,request_hash,result_hash,source_preparation_operation_id(SESSION,OPERATION)))
    before = ledger(store)
    with pytest.raises(SourceCapsuleError, match="source_capsule_history_mismatch"):
        await store.load_source_preparation(SESSION, OPERATION)
    assert ledger(store) == before


@pytest.mark.anyio
async def test_control_transplanted_to_other_session_cannot_rebind_capsule(tmp_path):
    store = await create(tmp_path)
    await store.create_narrative_source_campaign("other-session", initial_scene=SCENE)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(item)
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE attempts SET session_id=?,operation_id=?,attempt_id=? WHERE operation_id=?",
                           ("other-session",source_preparation_operation_id("other-session",OPERATION),
                            source_preparation_attempt_id("other-session",OPERATION),source_preparation_operation_id(SESSION,OPERATION)))
    before = ledger(store)
    with pytest.raises(SourceCapsuleError): await store.load_source_preparation("other-session",OPERATION)
    assert ledger(store) == before


@pytest.mark.anyio
async def test_reader_uses_one_transaction_when_campaign_revision_changes_concurrently(tmp_path, monkeypatch):
    store = await create(tmp_path)
    item = capsule(await store.read_source_context_snapshot(SESSION))
    await store.save_source_preparation(item)
    original = store._restore_source_preparation_row
    changed = False
    def concurrent(connection,row,session_id,operation_id,current):
        nonlocal changed
        if not changed:
            changed = True
            with sqlite3.connect(store.db_path) as writer:
                writer.execute("UPDATE campaigns SET state_revision=state_revision+1 WHERE session_id=?",(SESSION,))
        assert current.state_revision == 0
        return original(connection,row,session_id,operation_id,current)
    monkeypatch.setattr(store,"_restore_source_preparation_row",concurrent)
    assert await store.load_source_preparation(SESSION,OPERATION) == item
    assert changed and (await store.load_campaign(SESSION))["state_revision"] == 1
