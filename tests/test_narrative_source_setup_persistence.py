"""Atomic public setup metadata and read-only reconnect, all on synthetic SQLite."""
import asyncio
from copy import deepcopy
import json
import sqlite3
import threading

import pytest

from api import rules_service
from api.narrative_source_context import ORIGIN_KEY, create_source_context_origin
from api.narrative_source_setup import MANIFEST_KEY, create_source_setup_manifest
from api.persistence import SQLitePersistence, SourceSetupPersistenceError
from api.scene_service import SceneState
from test_narrative_source_context_persistence import SESSION, commit, rows


def request(objective="Conhecer melhor o lugar conversando com Mara."):
    return {"location": "Galeria", "npcs_present": ["Mara"], "declared_objective": objective}


def manifest(**kwargs):
    return create_source_setup_manifest(request(**kwargs), session_id=SESSION)


async def initialized(tmp_path):
    store = SQLitePersistence(tmp_path / "setup.sqlite3")
    await store.initialize()
    return store


async def create(store, value=None, **kwargs):
    return await store.create_source_setup_campaign(SESSION, manifest=value or manifest(),
        initial_state=kwargs.pop("initial_state", {"counter": 0}), **kwargs)


def metadata(store):
    with sqlite3.connect(store.db_path) as connection:
        return json.loads(connection.execute(
            "SELECT metadata_json FROM campaigns WHERE session_id=?", (SESSION,)).fetchone()[0])


def set_metadata(store, value):
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE campaigns SET metadata_json=? WHERE session_id=?",
                           (json.dumps(value), SESSION))


def forbid(*args, **kwargs):
    pytest.fail("Setup attempted initialization, old write operations, RNG or narration")


def tracked_connections(monkeypatch):
    original = sqlite3.connect
    connections, statements = [], []
    def connect(*args, **kwargs):
        if kwargs.get("uri"):
            kwargs["check_same_thread"] = False
        connection = original(*args, **kwargs)
        if kwargs.get("uri"):
            connections.append(connection)
            connection.set_trace_callback(statements.append)
        return connection
    monkeypatch.setattr(sqlite3, "connect", connect)
    return connections, statements


def assert_closed(connections):
    assert connections
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connection.execute("SELECT 1")


@pytest.mark.anyio
async def test_creation_retains_manifest_and_origin_in_one_campaign_with_zero_actions(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    restarted = SQLitePersistence(store.db_path)
    value = manifest()
    state = {"counter": 0, "private_server_marker": "synthetic-server-only"}
    relationships = {"links": []}
    before = rows(store)
    with monkeypatch.context() as patch:
        for name in ("initialize", "_connect", "create_narrative_source_campaign", "load_campaign",
                     "update_campaign_snapshot", "read_source_context_snapshot", "start_attempt"):
            patch.setattr(restarted, name, forbid)
        patch.setattr(rules_service, "calculate_resolution", forbid)
        patch.setattr(rules_service.random, "randint", forbid)
        created = await create(restarted, value, initial_state=state, relationships=relationships,
                               chronicle_name="Ensaio sintético")
        read = await restarted.read_source_setup_manifest(SESSION)
    assert not restarted._initialized
    assert created == read == value
    assert read is not value and read.request is not value.request
    raw = metadata(store)
    assert raw == {ORIGIN_KEY: value.origin.model_dump(mode="json"),
                   MANIFEST_KEY: value.model_dump(mode="json")}
    campaign = await store.load_campaign(SESSION)
    assert campaign["current_turn"] == campaign["state_revision"] == 0
    assert campaign["state"] == state and campaign["relationships"] == relationships
    assert "synthetic-server-only" not in created.model_dump_json()
    after = rows(store)
    assert all(after[table] == before[table] == [] for table in after if table != "campaigns")
    snapshot = await store.read_source_context_snapshot(SESSION)
    assert snapshot.sources == () and snapshot.selected_turn_ids == ()
    assert snapshot.canonical_scene.location == "Galeria"


@pytest.mark.anyio
@pytest.mark.parametrize("existing", ["same", "different", "legacy", "source_without_manifest"])
async def test_existing_session_always_refuses_without_overwrite(tmp_path, existing):
    store = await initialized(tmp_path)
    if existing in {"same", "different"}:
        await create(store)
    elif existing == "legacy":
        await store.ensure_campaign(SESSION, initial_state={"legacy_marker": True})
    else:
        await store.create_narrative_source_campaign(SESSION, initial_scene=SceneState(location="Galeria"))
    before = rows(store)
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_campaign_exists"):
        await create(store, manifest(objective="Outra intenção.") if existing == "different" else None)
    assert rows(store) == before


@pytest.mark.anyio
async def test_two_creators_share_one_atomic_winner(tmp_path):
    store = await initialized(tmp_path)
    first, second = manifest(), manifest(objective="Conversar sem assumir informações.")
    results = await asyncio.gather(create(store, first), create(SQLitePersistence(store.db_path), second),
                                   return_exceptions=True)
    winners = [item for item in results if not isinstance(item, BaseException)]
    failures = [item for item in results if isinstance(item, SourceSetupPersistenceError)]
    assert len(winners) == len(failures) == 1
    assert failures[0].code == "source_setup_campaign_exists"
    assert await store.read_source_setup_manifest(SESSION) == winners[0]
    assert len(rows(store)["campaigns"]) == 1


@pytest.mark.anyio
async def test_failure_after_insert_rolls_back_entire_creation_and_closes(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    before = rows(store)
    insert = store._insert_campaign_if_missing
    def interrupted(connection, *args):
        insert(connection, *args)
        raise ValueError("synthetic private failure")
    monkeypatch.setattr(store, "_insert_campaign_if_missing", interrupted)
    connections, _ = tracked_connections(monkeypatch)
    with pytest.raises(SourceSetupPersistenceError, match="^source_setup_manifest_invalid$"):
        await create(store)
    assert rows(store) == before
    assert_closed(connections)


@pytest.mark.anyio
async def test_uncommitted_setup_never_exposes_partial_campaign(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    inserted, release = threading.Event(), threading.Event()
    insert = store._insert_campaign_if_missing
    def paused(connection, *args):
        insert(connection, *args)
        inserted.set()
        assert release.wait(10)
    monkeypatch.setattr(store, "_insert_campaign_if_missing", paused)
    writer = asyncio.create_task(create(store))
    try:
        assert await asyncio.to_thread(inserted.wait, 5)
        with pytest.raises(SourceSetupPersistenceError, match="source_setup_campaign_missing"):
            await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION)
    finally:
        release.set()
    value = await writer
    assert await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION) == value


@pytest.mark.anyio
async def test_read_is_one_read_only_snapshot_during_an_independent_commit(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    initial = await create(store)
    replacement = manifest(objective="Intenção sintética alterada por escritor externo.")
    original = store._source_context_snapshot_in_connection
    writes = []
    def while_reading(connection, *args, **kwargs):
        # The generic metadata writer is outside this flow. This independent
        # commit demonstrates a stable read snapshot, not tamper authentication.
        raw = {ORIGIN_KEY: replacement.origin.model_dump(mode="json"),
               MANIFEST_KEY: replacement.model_dump(mode="json")}
        set_metadata(store, raw)
        writes.append(True)
        return original(connection, *args, **kwargs)
    monkeypatch.setattr(store, "_source_context_snapshot_in_connection", while_reading)
    connections, statements = tracked_connections(monkeypatch)
    assert await store.read_source_setup_manifest(SESSION) == initial
    assert writes == [True]
    assert statements[0] == "BEGIN"
    assert all(not text.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"))
               for text in statements)
    assert_closed(connections)
    monkeypatch.setattr(store, "_source_context_snapshot_in_connection", original)
    assert await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION) == replacement


@pytest.mark.anyio
async def test_reconnect_after_control_and_old_turns_keeps_original_briefing(tmp_path):
    store = await initialized(tmp_path)
    value = await create(store)
    for index in (1, 2, 3, 4):
        await commit(store, index)
    campaign = await store.load_campaign(SESSION)
    await store.update_campaign_snapshot(SESSION, state={"counter": 8},
        expected_turn=4, expected_revision=campaign["state_revision"])
    await store.start_attempt(session_id=SESSION, operation_id="pending-next", requested_turn=5, user_input="Aguardo.")
    before = rows(store)
    reader = SQLitePersistence(store.db_path)
    assert await reader.read_source_setup_manifest(SESSION) == value
    assert not reader._initialized and rows(store) == before
    snapshot = await store.read_source_context_snapshot(SESSION)
    assert snapshot.current_turn == 4 and len(snapshot.omitted_turn_ids) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [
    "missing", "none", "briefing", "hash", "protocol", "origin_other_session",
    "origin_other_scene", "outer_extra", "request_extra", "default_omitted", "origin_default_omitted",
    "malformed_json", "deep_json",
])
async def test_corrupt_or_missing_manifest_is_closed_without_repair(tmp_path, mutation):
    store = await initialized(tmp_path)
    await create(store)
    raw = metadata(store)
    if mutation == "missing": raw.pop(MANIFEST_KEY)
    elif mutation == "none": raw[MANIFEST_KEY] = None
    elif mutation == "briefing": raw[MANIFEST_KEY]["briefing"] += " Synthetic private leak."
    elif mutation == "hash": raw[MANIFEST_KEY]["fingerprint_sha256"] = "0" * 64
    elif mutation == "protocol": raw[MANIFEST_KEY]["protocol"] = "unknown"
    elif mutation == "origin_other_session":
        raw[ORIGIN_KEY] = create_source_context_origin("other-session", SceneState(location="Galeria", npcs_present=("Mara",))).model_dump(mode="json")
    elif mutation == "origin_other_scene":
        raw[ORIGIN_KEY] = create_source_context_origin(SESSION, SceneState(location="Outra cena", npcs_present=("Mara",))).model_dump(mode="json")
    elif mutation == "outer_extra": raw[MANIFEST_KEY]["private"] = "must not appear"
    elif mutation == "request_extra": raw[MANIFEST_KEY]["request"]["provider"] = "must not appear"
    elif mutation == "default_omitted": raw[MANIFEST_KEY].pop("kind")
    elif mutation == "origin_default_omitted": raw[ORIGIN_KEY].pop("creator")
    set_metadata(store, raw)
    if mutation in {"malformed_json", "deep_json"}:
        with sqlite3.connect(store.db_path) as connection:
            text = "{" if mutation == "malformed_json" else '{"x":' + "[" * 2000 + "0" + "]" * 2000 + "}"
            connection.execute("UPDATE campaigns SET metadata_json=?", (text,))
    before = rows(store)
    code = "source_setup_manifest_missing" if mutation == "missing" else "source_setup_manifest_invalid"
    with pytest.raises(SourceSetupPersistenceError, match=f"^{code}$"):
        await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["old_history", "state", "campaign_schema"])
async def test_valid_manifest_does_not_hide_invalid_current_campaign_or_old_history(tmp_path, mutation):
    store = await initialized(tmp_path)
    await create(store)
    for index in (1, 2, 3): await commit(store, index)
    with sqlite3.connect(store.db_path) as connection:
        if mutation == "old_history": connection.execute("UPDATE turns SET context_json='{}' WHERE turn_number=1")
        elif mutation == "state": connection.execute("UPDATE campaigns SET state_json=?", (json.dumps({"summary": "foreign"}),))
        else: connection.execute("UPDATE campaigns SET schema_version=2")
    before = rows(store)
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_history_invalid"):
        await store.read_source_setup_manifest(SESSION)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("invalid", ["foreign_manifest", "forged_extra", "nested_extra", "state_scene", "state_narrative", "relations", "nan"])
async def test_creation_rejects_invalid_server_arguments_before_sql(tmp_path, monkeypatch, invalid):
    store = await initialized(tmp_path)
    value, state, relations = manifest(), {"counter": 0}, {}
    if invalid == "foreign_manifest": value = create_source_setup_manifest(request(), session_id="other-session")
    elif invalid == "forged_extra": value = value.model_copy(update={"unexpected": "private"})
    elif invalid == "nested_extra": value = value.model_copy(update={"request": value.request.model_copy(update={"unexpected": "private"})})
    elif invalid == "state_scene": state = {"location": "Outra cena"}
    elif invalid == "state_narrative": state = {"summary": "Narrativa que não foi produzida"}
    elif invalid == "relations": relations = ["not", "mapping"]
    else: state = {"counter": float("nan")}
    before = rows(store)
    monkeypatch.setattr(store, "_source_setup_transaction", forbid)
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_arguments_invalid"):
        await create(store, value, initial_state=state, relationships=relations)
    assert rows(store) == before


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["missing", "directory", "empty", "old", "shape"])
async def test_existing_current_database_required_without_initialization_or_migration(tmp_path, kind):
    path = tmp_path / "absent-parent" / "setup.sqlite3" if kind == "missing" else tmp_path / "setup.sqlite3"
    store = SQLitePersistence(path)
    if kind == "directory": path.mkdir()
    elif kind == "empty": path.touch()
    elif kind in {"old", "shape"}:
        await store.initialize()
        with sqlite3.connect(path) as connection:
            if kind == "old": connection.execute("UPDATE schema_meta SET value='2'")
            else: connection.execute("DROP TABLE legacy_imports")
    before = path.read_bytes() if path.is_file() else None
    code = "source_setup_database_unavailable" if kind in {"missing", "directory"} else "source_setup_schema_incompatible"
    for action in (lambda: create(store), lambda: store.read_source_setup_manifest(SESSION)):
        with pytest.raises(SourceSetupPersistenceError, match=code): await action()
    if before is not None: assert path.read_bytes() == before
    if kind == "missing": assert not path.parent.exists()


@pytest.mark.anyio
async def test_creation_refuses_orphaned_attempts_without_adopting_them(tmp_path):
    store = await initialized(tmp_path)
    await store.ensure_campaign(SESSION)
    await store.start_attempt(session_id=SESSION, operation_id="orphan", requested_turn=1, user_input="Synthetic")
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DELETE FROM campaigns WHERE session_id=?", (SESSION,))
    before = rows(store)
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_history_invalid"):
        await create(store)
    assert rows(store) == before and rows(store)["campaigns"] == []


@pytest.mark.anyio
@pytest.mark.parametrize("session", [None, "", " ", " padded", "x"*241, "\ud800", 7])
async def test_invalid_reader_identity_never_opens_connection(tmp_path, monkeypatch, session):
    store = SQLitePersistence(tmp_path/"missing.sqlite3")
    monkeypatch.setattr(store, "_source_setup_transaction", forbid)
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_query_invalid"):
        await store.read_source_setup_manifest(session)
    assert not store.db_path.exists()
