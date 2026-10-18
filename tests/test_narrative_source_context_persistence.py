"""Eligibility of the new B campaign boundary; historical v1 fixtures stay unchanged."""
import asyncio
from copy import deepcopy
import json
import sqlite3

import pytest

from api.narrative_source_context import (
    ORIGIN_KEY, ORIGIN_PROTOCOL, SELECTION_KEY, SourceContextError,
    create_source_context_origin,
)
from api.persistence import SQLitePersistence, StateRevisionError
from api.scene_service import SceneState
from test_narrative_source_persistence import TEXT, _turn, _reserve


SESSION = "source-session"
SCENE = SceneState(location="Galeria")


async def create(tmp_path, session=SESSION):
    store = SQLitePersistence(tmp_path / "eligible.sqlite3")
    await store.create_narrative_source_campaign(
        session, initial_scene=SCENE, initial_state={"counter": 0}, relationships={},
    )
    return store


async def commit(store, index=1, *, narrative_text=TEXT):
    snapshot = await store.read_source_context_snapshot(SESSION)
    kwargs, metadata, envelope = _turn(index, narrative_text=narrative_text)
    kwargs["base_state_revision"] = snapshot.state_revision
    kwargs["context"][SELECTION_KEY] = snapshot.audit_payload()
    metadata.update(source_context_protocol=ORIGIN_PROTOCOL,
                    source_context_base_state_revision=snapshot.state_revision)
    await _reserve(store, kwargs, metadata)
    result = await store.commit_turn(**kwargs)
    return result, kwargs, metadata, envelope


def rows(store):
    with sqlite3.connect(store.db_path) as connection:
        return {table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("campaigns", "attempts", "turns", "events", "memory_candidates",
                              "episodic_memories", "consolidations", "legacy_imports")}


@pytest.mark.anyio
async def test_new_origin_and_restart_recover_full_sources_and_explicit_omissions(tmp_path):
    store = await create(tmp_path)
    initial = await store.read_source_context_snapshot(SESSION, expected_turn=0, expected_revision=0)
    assert initial.canonical_scene == SCENE and initial.sources == ()
    assert initial.audit_payload()["selected_turn_ids"] == []
    envelopes = []
    for index in (1, 2, 3):
        _, kwargs, metadata, envelope = await commit(store, index, narrative_text=TEXT + " O reflexo permanece imóvel sobre o vidro.")
        envelopes.append(envelope)
        assert kwargs["context"][SELECTION_KEY]["state_revision"] == metadata["source_context_base_state_revision"]
    before = rows(store)
    restarted = SQLitePersistence(store.db_path)
    snapshot = await restarted.read_source_context_snapshot(SESSION, expected_turn=3, expected_revision=3)
    assert snapshot.sources == tuple(envelopes[-2:])
    assert all(len(item.projection.text) > 600 for item in snapshot.sources)
    assert snapshot.selected_turn_ids == ("turn-2", "turn-3")
    assert snapshot.omitted_turn_ids == ("turn-1",)
    assert snapshot.audit_payload()["omitted_turn_ids"] == ["turn-1"]
    assert rows(store) == before
    assert (await store.database_info())["schema_version"] == 4


@pytest.mark.anyio
@pytest.mark.parametrize("existing", ["empty_v1", "source"])
async def test_origin_creation_refuses_any_existing_campaign_atomically(tmp_path, existing):
    store = SQLitePersistence(tmp_path / "existing.sqlite3")
    if existing == "empty_v1":
        await store.ensure_campaign(SESSION, initial_state={"keep": True})
    else:
        await store.create_narrative_source_campaign(SESSION, initial_scene=SCENE)
    before = rows(store)
    with pytest.raises(SourceContextError, match="source_context_campaign_exists"):
        await store.create_narrative_source_campaign(SESSION, initial_scene=SceneState(location="Outra sala"))
    assert rows(store) == before


@pytest.mark.anyio
async def test_concurrent_creators_cannot_overwrite_the_winning_seed(tmp_path):
    store = SQLitePersistence(tmp_path / "race.sqlite3")
    await store.initialize()
    other = SQLitePersistence(store.db_path)
    outcomes = await asyncio.gather(
        store.create_narrative_source_campaign(SESSION, initial_scene=SCENE),
        other.create_narrative_source_campaign(SESSION, initial_scene=SCENE),
        return_exceptions=True,
    )
    assert sum(isinstance(value, dict) for value in outcomes) == 1
    assert sum(isinstance(value, SourceContextError) for value in outcomes) == 1
    assert (await store.read_source_context_snapshot(SESSION)).current_turn == 0


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["ensure", "update"])
@pytest.mark.parametrize("existing", [False, True])
async def test_generic_writes_cannot_install_origin(tmp_path, method, existing):
    store = SQLitePersistence(tmp_path / "generic.sqlite3")
    await store.initialize()
    if existing:
        await store.ensure_campaign(SESSION, initial_state={"keep": True})
    before = rows(store)
    metadata = {ORIGIN_KEY: create_source_context_origin(SESSION, SCENE).model_dump(mode="json")}
    with pytest.raises(SourceContextError, match="source_context_origin_mutation_forbidden"):
        if method == "ensure":
            await store.ensure_campaign(SESSION, metadata=metadata)
        else:
            await store.update_campaign_snapshot(SESSION, state={}, metadata=metadata,
                                                 expected_turn=0, expected_revision=0)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["remove", "replace", "false"])
async def test_generic_snapshot_cannot_remove_or_change_origin(tmp_path, mutation):
    store = await create(tmp_path)
    campaign = await store.load_campaign(SESSION)
    metadata = deepcopy(campaign["metadata"])
    if mutation == "remove": metadata = {}
    elif mutation == "replace": metadata[ORIGIN_KEY]["seed_scene"]["location"] = "Outra sala"
    else: metadata[ORIGIN_KEY] = False
    before = rows(store)
    with pytest.raises(SourceContextError):
        await store.update_campaign_snapshot(SESSION, state={"counter": 4}, metadata=metadata,
                                             expected_turn=0, expected_revision=0)
    assert rows(store) == before


@pytest.mark.anyio
async def test_opaque_control_state_change_preserves_origin_and_binds_actual_base_revision(tmp_path):
    store = await create(tmp_path)
    original = (await store.load_campaign(SESSION))["metadata"]
    await store.update_campaign_snapshot(SESSION, state={"counter": 10}, expected_turn=0, expected_revision=0)
    first, kwargs, metadata, _ = await commit(store)
    assert kwargs["base_state_revision"] == metadata["source_context_base_state_revision"] == 1
    assert (await store.commit_turn(**kwargs)).idempotent is True
    snapshot = await store.read_source_context_snapshot(SESSION, expected_turn=1, expected_revision=2)
    assert snapshot.current_turn == first.turn_number == 1
    assert (await store.load_campaign(SESSION))["metadata"] == original
    with pytest.raises(StateRevisionError):
        await store.update_campaign_snapshot(SESSION, state={}, expected_turn=1, expected_revision=1)


@pytest.mark.anyio
@pytest.mark.parametrize("state", [
    {"scene": {"location": "Outra sala"}},
    {"player_sheet": {"summary": "Memória antiga aceita."}},
    {"context": {"scene": {"location": "Galeria", "details": ["Detalhe não avaliado."]}}},
])
async def test_incompatible_state_is_refused_on_creation_control_update_and_commit(tmp_path, state):
    bad = SQLitePersistence(tmp_path / "invalid.sqlite3")
    with pytest.raises(SourceContextError):
        await bad.create_narrative_source_campaign(SESSION, initial_scene=SCENE, initial_state=state)
    assert not bad.db_path.exists()
    store = await create(tmp_path)
    before = rows(store)
    with pytest.raises(SourceContextError):
        await store.update_campaign_snapshot(SESSION, state=state, expected_turn=0, expected_revision=0)
    assert rows(store) == before
    snapshot = await store.read_source_context_snapshot(SESSION)
    kwargs, metadata, _ = _turn()
    metadata.update(source_context_protocol=ORIGIN_PROTOCOL, source_context_base_state_revision=0)
    kwargs["context"][SELECTION_KEY] = snapshot.audit_payload()
    kwargs["state"] = state
    await _reserve(store, kwargs, metadata)
    before = rows(store)
    with pytest.raises(SourceContextError): await store.commit_turn(**kwargs)
    assert rows(store) == before


@pytest.mark.anyio
async def test_v1_commit_cannot_enter_marked_campaign_even_without_attempt_marker(tmp_path):
    store = await create(tmp_path)
    kwargs, _, _ = _turn()
    kwargs.pop("narrative_contract"); kwargs["context"] = {}
    await _reserve(store, kwargs, {})
    before = rows(store)
    with pytest.raises(SourceContextError, match="source_context_commit_contract_required"):
        await store.commit_turn(**kwargs)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["receipt_missing", "selected", "origin", "base_revision", "protocol", "context_extra"])
async def test_receipt_and_static_reservation_cannot_be_forged_before_commit(tmp_path, mutation):
    store = await create(tmp_path)
    kwargs, metadata, _ = _turn()
    metadata.update(source_context_protocol=ORIGIN_PROTOCOL, source_context_base_state_revision=0)
    kwargs["context"][SELECTION_KEY] = (await store.read_source_context_snapshot(SESSION)).audit_payload()
    if mutation == "receipt_missing": del kwargs["context"][SELECTION_KEY]
    elif mutation == "selected": kwargs["context"][SELECTION_KEY]["selected_turn_ids"] = ["foreign"]
    elif mutation == "origin": kwargs["context"][SELECTION_KEY]["origin_sha256"] = "0"*64
    elif mutation == "base_revision": metadata["source_context_base_state_revision"] = True
    elif mutation == "protocol": metadata["source_context_protocol"] = "legacy"
    else: kwargs["context"]["legacy_summary"] = "Texto não avaliado."
    await _reserve(store, kwargs, metadata)
    before = rows(store)
    with pytest.raises(SourceContextError): await store.commit_turn(**kwargs)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["origin_missing", "origin_foreign", "legacy_older", "gap", "pair", "receipt", "state"])
async def test_entire_history_and_current_origin_are_checked_before_recent_window(tmp_path, mutation):
    store = await create(tmp_path)
    for index in (1, 2, 3): await commit(store, index)
    with sqlite3.connect(store.db_path) as connection:
        if mutation.startswith("origin"):
            metadata = {} if mutation == "origin_missing" else {
                ORIGIN_KEY: create_source_context_origin("another-session", SCENE).model_dump(mode="json")}
            connection.execute("UPDATE campaigns SET metadata_json=?", (json.dumps(metadata),))
        elif mutation == "legacy_older": connection.execute("UPDATE turns SET context_json='{}' WHERE turn_number=1")
        elif mutation == "gap": connection.execute("UPDATE turns SET turn_number=5 WHERE turn_number=1")
        elif mutation == "pair": connection.execute("UPDATE attempts SET result_hash=? WHERE requested_turn=1", ("0"*64,))
        elif mutation == "state": connection.execute("UPDATE campaigns SET state_json=?", (json.dumps({"summary": "Antigo"}),))
        else:
            raw = connection.execute("SELECT context_json FROM turns WHERE turn_number=1").fetchone()[0]
            context = json.loads(raw);context[SELECTION_KEY]["state_revision"] = True
            connection.execute("UPDATE turns SET context_json=? WHERE turn_number=1", (json.dumps(context),))
    before = rows(store)
    with pytest.raises(SourceContextError): await store.read_source_context_snapshot(SESSION)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("table", ["memory_candidates", "episodic_memories", "consolidations", "legacy_imports"])
async def test_incompatible_dependency_is_not_hidden_by_visibility_or_empty_recent_window(tmp_path, table):
    store = await create(tmp_path)
    await commit(store)
    with sqlite3.connect(store.db_path) as connection:
        columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
        payload = {c[1]: (0 if c[2] == "INTEGER" else 0.0 if c[2] == "REAL" else "foreign")
                   for c in columns if c[3] and c[4] is None and not c[5]}
        payload.update(session_id=SESSION)
        for key in ("turn_id",):
            if key in payload: payload[key] = "turn-1"
        for key,value in {"visibility":"player", "validation_status":"accepted", "proposed_by":"deterministic",
                          "parse_status":"missing", "payload_json":"{}", "version":1}.items():
            if key in payload: payload[key] = value
        names=','.join(payload);marks=','.join('?' for _ in payload)
        connection.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(payload.values()))
    before = rows(store)
    with pytest.raises(SourceContextError, match="source_context_dependencies_forbidden"):
        await store.read_source_context_snapshot(SESSION)
    assert rows(store) == before


@pytest.mark.anyio
async def test_pending_and_failed_attempts_are_not_sources_and_public_reader_cannot_skip_player_history(tmp_path):
    store = await create(tmp_path)
    await store.start_attempt(session_id=SESSION, operation_id="pending", requested_turn=1, user_input="Pending")
    await store.record_failed_attempt(session_id=SESSION, operation_id="failed", requested_turn=1,
                                     user_input="Failed", status="failed", error={"code":"local"})
    assert (await store.read_source_context_snapshot(SESSION)).sources == ()
    for index in (1,2,3): await commit(store,index)
    with pytest.raises(SourceContextError):
        await store.read_source_context_snapshot(SESSION, allowed_visibilities=("public",))
    assert len((await store.read_source_context_snapshot(SESSION)).sources) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("options", [
    {"expected_turn":True}, {"expected_revision":-1}, {"allowed_visibilities":("storyteller",)},
    {"allowed_visibilities":()}, {"expected_turn":1}, {"expected_revision":1},
])
async def test_query_types_cas_and_audience_are_explicit(tmp_path, options):
    store = await create(tmp_path)
    before = rows(store)
    with pytest.raises(SourceContextError): await store.read_source_context_snapshot(SESSION, **options)
    assert rows(store) == before


@pytest.mark.anyio
async def test_snapshot_rows_share_one_sqlite_read_transaction(tmp_path, monkeypatch):
    store = await create(tmp_path)
    await commit(store)
    original = store._restore_narrative_source_row
    changed = False
    def concurrent_write(connection, row, session_id, allowed):
        nonlocal changed
        if not changed:
            changed = True
            with sqlite3.connect(store.db_path) as writer:
                writer.execute("UPDATE campaigns SET state_revision=state_revision+1 WHERE session_id=?", (SESSION,))
        return original(connection,row,session_id,allowed)
    monkeypatch.setattr(store,"_restore_narrative_source_row",concurrent_write)
    snapshot = await store.read_source_context_snapshot(SESSION, expected_revision=1)
    assert changed and snapshot.state_revision == 1 and len(snapshot.sources)==1
    assert (await store.load_campaign(SESSION))["state_revision"] == 2
    with pytest.raises(SourceContextError, match="source_context_revision_mismatch"):
        await store.read_source_context_snapshot(SESSION, expected_revision=1)


@pytest.mark.anyio
@pytest.mark.parametrize("already_committed,remaining_signal", [(False,"attempt"),(False,"receipt"),(False,"both"),(True,"both")])
async def test_origin_removed_after_reservation_cannot_downgrade_commit(tmp_path, remaining_signal, already_committed):
    store = await create(tmp_path)
    kwargs, metadata, _ = _turn()
    kwargs["context"][SELECTION_KEY] = (await store.read_source_context_snapshot(SESSION)).audit_payload()
    metadata.update(source_context_protocol=ORIGIN_PROTOCOL, source_context_base_state_revision=0)
    if remaining_signal == "receipt":
        metadata.pop("source_context_protocol")
    await _reserve(store, kwargs, metadata)
    if already_committed:
        await store.commit_turn(**kwargs)
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE campaigns SET metadata_json='{}' WHERE session_id=?", (SESSION,))
    if remaining_signal == "attempt":
        kwargs["context"].pop(SELECTION_KEY)
    before = rows(store)
    with pytest.raises(SourceContextError):
        await store.commit_turn(**kwargs)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("state", [{"scene": {"location": "Outra sala"}}, {"context": {"summary": "Resumo legado"}}])
async def test_control_completion_cannot_install_ineligible_narrative_state(tmp_path, state):
    store = await create(tmp_path)
    await store.start_attempt(session_id=SESSION, operation_id="control", requested_turn=1, user_input="Control")
    before = rows(store)
    with pytest.raises(SourceContextError):
        await store.complete_control_attempt(session_id=SESSION, operation_id="control", requested_turn=1,
                                             user_input="Control", state=state, expected_turn=0, expected_state_revision=0)
    assert rows(store) == before
    assert (await store.read_source_context_snapshot(SESSION)).state_revision == 0


@pytest.mark.anyio
async def test_control_completion_preserves_eligible_opaque_state_and_idempotency(tmp_path):
    store = await create(tmp_path)
    original = (await store.load_campaign(SESSION))["metadata"]
    await store.start_attempt(session_id=SESSION, operation_id="control", requested_turn=1, user_input="Control")
    kwargs = dict(session_id=SESSION, operation_id="control", requested_turn=1, user_input="Control",
                  state={"counter": 1, "scene": SCENE.model_dump(mode="json")}, expected_turn=0, expected_state_revision=0)
    first = await store.complete_control_attempt(**kwargs)
    assert first.state_revision == 1 and not first.idempotent
    assert (await store.complete_control_attempt(**kwargs)).idempotent
    assert (await store.load_campaign(SESSION))["metadata"] == original
    assert (await store.read_source_context_snapshot(SESSION)).state_revision == 1
