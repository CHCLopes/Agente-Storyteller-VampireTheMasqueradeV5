"""Setup service captures caller values and settles one local creation."""
import asyncio
from copy import deepcopy
import threading

import pytest

from api import narrative_source_setup_service as service
from api.persistence import SQLitePersistence, SourceSetupPersistenceError
from test_narrative_source_setup_persistence import SESSION, initialized, request, rows
from test_narrative_source_input_service import state


@pytest.mark.anyio
async def test_service_keeps_public_manifest_separate_from_server_state(tmp_path):
    store = await initialized(tmp_path)
    server_state = state()
    server_state["server_marker"] = "synthetic-private"
    value = await service.create_source_trial_setup(session_id=SESSION, request=request(),
        store=store, initial_state=server_state, relationships={"links": []},
        chronicle_name="Ensaio")
    assert value == await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION)
    assert "synthetic-private" not in value.model_dump_json()
    assert "player_sheet" not in value.model_dump_json()
    assert all(not content for table, content in rows(store).items() if table != "campaigns")


@pytest.mark.anyio
async def test_repeated_cancellation_settles_same_commit_without_second_creation(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    entered, release = threading.Event(), threading.Event()
    original = store._create_source_setup_campaign_sync
    calls = []
    def paused(*args):
        calls.append(True)
        entered.set()
        assert release.wait(10)
        return original(*args)
    monkeypatch.setattr(store, "_create_source_setup_campaign_sync", paused)
    creation = asyncio.create_task(service.create_source_trial_setup(session_id=SESSION,
        request=request(), store=store, initial_state=state()))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        creation.cancel()
        await asyncio.sleep(0)
        creation.cancel()
        await asyncio.sleep(0)
        assert not creation.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError): await creation
    assert calls == [True]
    assert await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION)
    assert len(rows(store)["campaigns"]) == 1
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_campaign_exists"):
        await service.create_source_trial_setup(session_id=SESSION,
            request=request(), store=store, initial_state=state())


@pytest.mark.anyio
async def test_caller_mutation_after_dispatch_does_not_change_retained_setup(tmp_path, monkeypatch):
    store = await initialized(tmp_path)
    entered, release = threading.Event(), threading.Event()
    original = store._create_source_setup_campaign_sync
    def paused(*args):
        entered.set()
        assert release.wait(10)
        return original(*args)
    monkeypatch.setattr(store, "_create_source_setup_campaign_sync", paused)
    public, server_state, relations = request(), state(), {"links": []}
    before = deepcopy((public, server_state, relations))
    creation = asyncio.create_task(service.create_source_trial_setup(session_id=SESSION,
        request=public, store=store, initial_state=server_state, relationships=relations))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        public["declared_objective"] = "Alterado"
        public["npcs_present"].append("Outra pessoa")
        server_state["player_sheet"]["status"]["current_hunger"] = 5
        relations["links"].append("alterado")
    finally:
        release.set()
    value = await creation
    assert value.request.declared_objective == before[0]["declared_objective"]
    assert tuple(value.request.npcs_present) == tuple(before[0]["npcs_present"])
    campaign = await store.load_campaign(SESSION)
    assert campaign["state"] == before[1] and campaign["relationships"] == before[2]


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["public_privilege", "store", "state", "relationships", "chronicle"])
async def test_invalid_service_arguments_are_closed_before_storage(tmp_path, monkeypatch, kind):
    store = await initialized(tmp_path)
    args = dict(session_id=SESSION, request=request(), store=store, initial_state=state())
    if kind == "public_privilege": args["request"]["player_sheet"] = {"authority": "forged"}
    elif kind == "store": args["store"] = object()
    elif kind == "state": args["initial_state"] = []
    elif kind == "relationships": args["relationships"] = []
    else: args["chronicle_name"] = object()
    async def forbidden(*args, **kwargs): pytest.fail("Invalid setup reached persistence")
    monkeypatch.setattr(store, "create_source_setup_campaign", forbidden)
    before = rows(store)
    with pytest.raises(service.SourceSetupServiceError, match="^source_setup_service_arguments_invalid$"):
        await service.create_source_trial_setup(**args)
    assert rows(store) == before


@pytest.mark.anyio
async def test_service_does_not_bootstrap_a_missing_database(tmp_path):
    store = SQLitePersistence(tmp_path/"missing"/"setup.sqlite3")
    with pytest.raises(SourceSetupPersistenceError, match="source_setup_database_unavailable"):
        await service.create_source_trial_setup(session_id=SESSION, request=request(),
            store=store, initial_state=state())
    assert not store.db_path.parent.exists()
