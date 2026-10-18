"""Inactive selector contract only: no route/accept or authenticated boundary."""
import ast
import asyncio
from copy import deepcopy
import hashlib
from pathlib import Path
import sqlite3

import pytest
from pydantic import ValidationError

from api import narrative_source_local_selection as selection
from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_input import create_source_producer_config
from api.narrative_source_setup import create_source_setup_manifest
from api.narrative_source_setup_service import create_source_trial_setup
from api.persistence import SQLitePersistence

SESSION = "synthetic-local-selection"
HOST = "127.0.0.1:8000"
ORIGIN = "http://127.0.0.1:8000"
HEADERS = [(b"host", HOST.encode()), (b"origin", ORIGIN.encode())]
SETUP = {"location": "Oficina", "npcs_present": ["Nina"], "declared_objective": "Conhecer a oficina."}


def config():
    # An explicit synthetic target fixture, not a runtime/model recommendation.
    return create_source_producer_config(target=LLMTarget(profile="synthetic-fixture", provider="Fixture", model="fixture-model"),
        system_prompt="PRIVATE_SYSTEM_SENTINEL", parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        npc_aliases=("Nina",))


def binding(tmp_path, **updates):
    values = dict(session_id=SESSION, store=SQLitePersistence(tmp_path/"trial.sqlite3"),
        expected_manifest=create_source_setup_manifest(SETUP, session_id=SESSION),
        producer_config=config(), expected_host=HOST, expected_origin=ORIGIN)
    values.update(updates)
    return selection.create_source_local_trial_binding(**values)


async def choose(value, **updates):
    kwargs = dict(destination="source_local_trial", enabled=True, binding=value,
        received_session_id=SESSION, raw_headers=HEADERS)
    kwargs.update(updates)
    return await selection.select_source_local_entry(**kwargs)


def forbid_reader(monkeypatch, value):
    async def forbidden(*args, **kwargs):
        pytest.fail("Selection reached a reader before its request filters")
    monkeypatch.setattr(value.store, "read_source_setup_manifest", forbidden)


def test_factory_is_pure_and_copies_nested_models_but_retains_store_identity(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Binding factory performed I/O")
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    source = create_source_setup_manifest(SETUP, session_id=SESSION)
    supplied = config()
    store = SQLitePersistence(tmp_path/"missing"/"trial.sqlite3")
    value = binding(tmp_path, store=store, expected_manifest=source, producer_config=supplied)
    assert value.store is store and value.store_identity == id(store)
    assert value.expected_manifest == source and value.expected_manifest is not source
    assert value.producer_config == supplied and value.producer_config is not supplied
    assert value.database_path == str(store.db_path)
    assert not store.db_path.parent.exists()
    with pytest.raises(ValidationError):
        value.session_id = "changed"
    assert "PRIVATE" not in repr(value) and "trial.sqlite3" not in repr(value)
    assert value.model_dump(mode="json") == {"protocol": "source-local-trial-binding-v1"}


@pytest.mark.parametrize("field,value", [
    ("session_id", ""), ("session_id", " padded "), ("store", object()),
    ("expected_manifest", {}), ("producer_config", {}),
    ("expected_host", "localhost:8000"), ("expected_host", "127.0.0.1:0"),
    ("expected_host", "127.0.0.1:65536"), ("expected_host", "127.0.0.1:08000"),
    ("expected_host", "127.0.0.1:8000/"), ("expected_host", "127.0.0.1:8000\n"),
    ("expected_origin", "null"), ("expected_origin", "https://127.0.0.1:8000"),
    ("expected_origin", "http://localhost:8000"), ("expected_origin", "http://127.0.0.1:8000/path"),
    ("expected_origin", "http://127.0.0.1:8000?x=1"), ("expected_origin", "http://user@127.0.0.1:8000"),
])
def test_factory_refuses_incomplete_or_outside_fixed_local_scope(tmp_path, field, value):
    with pytest.raises(selection.SourceLocalSelectionError, match="^source_local_selection_invalid$"):
        binding(tmp_path, **{field: value})


@pytest.mark.parametrize("path", ["relative.sqlite3", "../relative.sqlite3"])
def test_factory_requires_absolute_lexical_store_path(tmp_path, path):
    with pytest.raises(selection.SourceLocalSelectionError):
        binding(tmp_path, store=SQLitePersistence(path))


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_only_server_destination_selects_legacy_without_consulting_binding(tmp_path, monkeypatch, enabled):
    value = binding(tmp_path)
    forbid_reader(monkeypatch, value)
    result = await choose(value, destination="legacy", enabled=enabled,
        received_session_id=SESSION, raw_headers=HEADERS+[(b"x-storyteller-mode", b"source_local_trial")])
    assert result.model_dump(mode="json") == {"destination": "legacy", "reason": None}
    assert result.binding is result.manifest is None


@pytest.mark.asyncio
@pytest.mark.parametrize("destination,enabled", [("b", True), (True, True), ("source_local_trial", "true"), ("legacy", 1)])
async def test_invalid_server_dispatch_arguments_never_fall_back(tmp_path, monkeypatch, destination, enabled):
    value = binding(tmp_path)
    forbid_reader(monkeypatch, value)
    with pytest.raises(selection.SourceLocalSelectionError):
        await choose(value, destination=destination, enabled=enabled)


@pytest.mark.asyncio
@pytest.mark.parametrize("change,reason", [
    ({"enabled": False}, "disabled"), ({"binding": None}, "binding_invalid"),
    ({"received_session_id": "other"}, "request_mismatch"), ({"received_session_id": None}, "request_mismatch"),
    ({"received_session_id": SESSION+" "}, "request_mismatch"), ({"raw_headers": []}, "request_mismatch"),
    ({"raw_headers": dict(HEADERS)}, "request_mismatch"),
    ({"raw_headers": HEADERS+[HEADERS[0]]}, "request_mismatch"),
    ({"raw_headers": HEADERS+[(b"Origin", ORIGIN.encode())]}, "request_mismatch"),
    ({"raw_headers": [(b"host", HOST.encode())]}, "request_mismatch"),
    ({"raw_headers": [(b"host", b"localhost:8000"), HEADERS[1]]}, "request_mismatch"),
    ({"raw_headers": [HEADERS[0], (b"origin", b"null")]}, "request_mismatch"),
    ({"raw_headers": [HEADERS[0], (b"origin", b"http://127.0.0.1:8001")]}, "request_mismatch"),
    ({"raw_headers": [HEADERS[0], (b"origin", b"http://127.0.0.1:8000/")]}, "request_mismatch"),
    ({"raw_headers": [HEADERS[0], (b"origin", b"http://127.0.0.1:8000,http://evil.invalid")]}, "request_mismatch"),
    ({"raw_headers": [HEADERS[0], (b"origin", b"http://127.0.0.1:8000\r\n")]}, "request_mismatch"),
    ({"raw_headers": [(b"host", b"wrong"), (b"x-forwarded-host", HOST.encode()), HEADERS[1]]}, "request_mismatch"),
    ({"raw_headers": [("host", HOST), ("origin", ORIGIN)]}, "request_mismatch"),
])
async def test_initial_b_filters_reject_before_any_reader_or_fallback(tmp_path, monkeypatch, change, reason):
    value = binding(tmp_path)
    forbid_reader(monkeypatch, value)
    result = await choose(value, **change)
    assert result.model_dump(mode="json") == {"destination": "rejected", "reason": reason}
    assert result.binding is result.manifest is None


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", [
    "deepcopy", "model_deepcopy", "session", "store", "path", "store_path",
    "host", "origin", "fingerprint", "extra", "nested_manifest", "nested_origin",
    "nested_config", "nested_target", "nested_parameters", "forged_extra",
])
async def test_inconsistent_binding_copies_fail_before_read(tmp_path, monkeypatch, kind):
    original = binding(tmp_path)
    if kind == "deepcopy": value = deepcopy(original)
    elif kind == "model_deepcopy": value = original.model_copy(deep=True)
    else: value = original.model_copy()
    if kind == "session": value = value.model_copy(update={"session_id": "foreign"})
    elif kind == "store": value = value.model_copy(update={"store": SQLitePersistence(original.store.db_path)})
    elif kind == "path": value = value.model_copy(update={"database_path": str(tmp_path/"other.sqlite3")})
    elif kind == "store_path": value.store.db_path = tmp_path/"other.sqlite3"
    elif kind == "host": value = value.model_copy(update={"expected_host": "127.0.0.1:9000"})
    elif kind == "origin": value = value.model_copy(update={"expected_origin": "http://127.0.0.1:9000"})
    elif kind == "fingerprint": value = value.model_copy(update={"fingerprint_sha256": "0"*64})
    elif kind == "extra": value = value.model_copy(update={"PRIVATE_EXTRA": True})
    elif kind == "nested_manifest": value.expected_manifest.__dict__["PRIVATE_EXTRA"] = "PRIVATE"
    elif kind == "nested_origin": value.expected_manifest.origin.__dict__["PRIVATE_EXTRA"] = "PRIVATE"
    elif kind == "nested_config": value.producer_config.__dict__["PRIVATE_EXTRA"] = "PRIVATE"
    elif kind == "nested_target": value.producer_config.target.__dict__["PRIVATE_EXTRA"] = "PRIVATE"
    elif kind == "nested_parameters": value.producer_config.parameters.__dict__["PRIVATE_EXTRA"] = "PRIVATE"
    elif kind == "forged_extra": object.__setattr__(value, "__pydantic_extra__", {"PRIVATE_EXTRA": True})
    forbid_reader(monkeypatch, value)
    result = await choose(value)
    assert result.destination == "rejected" and result.reason == "binding_invalid"
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["missing", "foreign_session", "changed_setup", "forged_origin", "exception", "sqlite_error", "os_error"])
async def test_reader_is_single_bound_b_query_and_bad_setup_never_falls_back(tmp_path, monkeypatch, kind):
    value, calls = binding(tmp_path), []
    async def reader(session_id):
        calls.append(session_id)
        if kind == "missing": return None
        if kind == "foreign_session": return create_source_setup_manifest(SETUP, session_id="foreign")
        if kind == "changed_setup": return create_source_setup_manifest({**SETUP, "location": "Arquivo"}, session_id=SESSION)
        if kind == "exception": raise ValueError("PRIVATE_READER_DETAIL")
        if kind == "sqlite_error": raise sqlite3.OperationalError("PRIVATE_ROLLBACK_DETAIL")
        if kind == "os_error": raise OSError("PRIVATE_OS_DETAIL")
        return value.expected_manifest.model_copy(update={"origin": value.expected_manifest.origin.model_copy(update={"fingerprint_sha256": "0"*64})})
    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    result = await choose(value)
    assert calls == [SESSION]
    assert result.destination == "rejected" and result.reason == "setup_unavailable"
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_store_path_change_during_read_is_rejected(tmp_path, monkeypatch):
    value = binding(tmp_path)
    async def reader(session_id):
        value.store.db_path = tmp_path/"different.sqlite3"
        return value.expected_manifest
    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    assert (await choose(value)).reason == "setup_unavailable"


@pytest.mark.asyncio
async def test_unmounted_selection_uses_existing_readonly_manifest_without_creating_turn(tmp_path, monkeypatch):
    store = SQLitePersistence(tmp_path/"synthetic.sqlite3")
    await store.initialize()
    manifest = await create_source_trial_setup(session_id=SESSION, request=SETUP, store=store,
        initial_state={"synthetic_marker": "PRIVATE_STATE"}, relationships={})
    value = binding(tmp_path, store=store, expected_manifest=manifest)
    before = hashlib.sha256(store.db_path.read_bytes()).hexdigest()
    calls, real = [], store.read_source_setup_manifest
    async def reader(session_id):
        calls.append(session_id)
        return await real(session_id)
    async def forbidden(*args, **kwargs):
        pytest.fail("Selection attempted bootstrap, migration or mutation")
    monkeypatch.setattr(store, "read_source_setup_manifest", reader)
    for name in ("initialize", "create_source_setup_campaign", "migrate_legacy_session",
                 "claim_source_input", "save_source_preparation", "start_attempt", "recover_pending_attempts"):
        monkeypatch.setattr(store, name, forbidden)
    result = await choose(value, raw_headers=[(b"Host", HOST.encode()), (b"Origin", ORIGIN.encode()),
        (b"x-forwarded-host", b"untrusted.invalid")])
    assert result.destination == "source_local_trial" and result.reason is None
    assert result.binding.store is store and result.binding.producer_config == value.producer_config
    assert result.manifest == manifest and calls == [SESSION]
    assert result.model_dump(mode="json") == {"destination": "source_local_trial", "reason": None}
    assert "PRIVATE" not in repr(result) and "PRIVATE" not in result.model_dump_json()
    assert hashlib.sha256(store.db_path.read_bytes()).hexdigest() == before
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM campaigns").fetchone() == (1,)
        for table in ("attempts", "turns", "events", "memory_candidates"):
            assert conn.execute("SELECT count(*) FROM "+table).fetchone() == (0,)


@pytest.mark.asyncio
async def test_missing_database_is_not_bootstrapped(tmp_path):
    value = binding(tmp_path, store=SQLitePersistence(tmp_path/"missing"/"trial.sqlite3"))
    result = await choose(value)
    assert result.destination == "rejected" and result.reason == "setup_unavailable"
    assert not value.store.db_path.parent.exists()


def test_selector_is_not_a_router_and_imports_no_legacy_entry_or_gateway():
    tree = ast.parse(Path(selection.__file__).read_text(encoding="utf-8"))
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {"main", "state_service", "narrative_source_input_service",
        "narrative_source_execution_service", "narrative_source_coordinator"}.intersection(modules)
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not {"accept", "start_attempt", "initialize", "create_source_setup_campaign", "migrate_legacy_session",
        "prepare_source_player_action", "execute_retained_source_turn", "generate_structured"}.intersection(calls)

@pytest.mark.asyncio
async def test_cancelled_single_read_propagates_without_retry_or_fallback(tmp_path, monkeypatch):
    value, calls = binding(tmp_path), []
    async def reader(session_id):
        calls.append(session_id)
        raise asyncio.CancelledError()
    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    with pytest.raises(asyncio.CancelledError):
        await choose(value)
    assert calls == [SESSION]


@pytest.mark.asyncio
async def test_corrupt_sqlite_remains_unchanged_without_bootstrap(tmp_path):
    value = binding(tmp_path)
    raw = b"synthetic-invalid-sqlite-file"
    value.store.db_path.write_bytes(raw)
    before = set(tmp_path.iterdir())
    result = await choose(value)
    assert result.destination == "rejected" and result.reason == "setup_unavailable"
    assert value.store.db_path.read_bytes() == raw
    assert set(tmp_path.iterdir()) == before
