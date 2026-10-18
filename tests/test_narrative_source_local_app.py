"""In-process ASGI boundary proofs with a stub, not a live B handler/listener."""
import ast
import asyncio
import gc
import hashlib
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import httpx
import pytest
from starlette.websockets import WebSocketDisconnect, WebSocketState

from api import narrative_source_local_app as local_app
from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_input import create_source_producer_config
from api.narrative_source_local_selection import create_source_local_trial_binding
from api.narrative_source_setup import create_source_setup_manifest
from api.narrative_source_setup_service import create_source_trial_setup
from api.narrative_source_transport import project_source_briefing
from api.persistence import SQLitePersistence

SESSION = "synthetic-local-app"
HOST = "127.0.0.1:8000"
ORIGIN = "http://127.0.0.1:8000"
URL = f"ws://{HOST}/ws/source-local/{SESSION}"
SETUP = {"location": "Oficina", "npcs_present": ["Nina"], "declared_objective": "Conhecer a oficina."}


def make_binding(tmp_path, *, store=None, manifest=None):
    return create_source_local_trial_binding(
        session_id=SESSION, store=store if store is not None else SQLitePersistence(tmp_path / "trial.sqlite3"),
        expected_manifest=manifest if manifest is not None else create_source_setup_manifest(SETUP, session_id=SESSION),
        producer_config=create_source_producer_config(
            target=LLMTarget(profile="synthetic-fixture", provider="Fixture", model="fixture-model"),
            system_prompt="PRIVATE_SYSTEM_SENTINEL",
            parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Nina",)),
        expected_host=HOST, expected_origin=ORIGIN,
    )


class TraceASGI:
    """Observe real ASGI sends, including whether rejection preceded accept."""
    def __init__(self, app, trace):
        self.app, self.trace = app, trace

    async def __call__(self, scope, receive, send):
        async def observed(message):
            if scope["type"] == "websocket":
                self.trace.append((message["type"], dict(message)))
            await send(message)
        await self.app(scope, receive, observed)


def forbid_mutations(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Inactive app reached bootstrap, migration, recovery or reservation")
    for name in ("initialize", "recover_pending_attempts", "migrate_legacy_session",
                 "create_source_setup_campaign", "claim_source_input", "save_source_preparation", "start_attempt"):
        monkeypatch.setattr(SQLitePersistence, name, forbidden)


async def unused_handler(websocket, selected):
    pytest.fail("Rejected connection reached the handler")


def test_factory_and_lifespan_are_inactive_and_have_only_the_reserved_ws_route(tmp_path, monkeypatch):
    value = make_binding(tmp_path)
    forbid_mutations(monkeypatch)
    async def forbidden_reader(*args):
        pytest.fail("Factory/lifespan/default-disabled app read a manifest")
    monkeypatch.setattr(value.store, "read_source_setup_manifest", forbidden_reader)
    before = set(tmp_path.iterdir())
    app = local_app.create_source_local_app(binding=value, handler=unused_handler)
    assert not hasattr(local_app, "app")
    assert app.docs_url is app.redoc_url is app.openapi_url is None
    assert [route.path for route in app.routes] == ["/ws/source-local/{session_id}"]
    trace = []
    with TestClient(TraceASGI(app, trace)) as client:
        for path in ("/", "/health", "/docs", "/redoc", "/openapi.json", "/api/llm/test-connection"):
            assert client.get(path).status_code == 404
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect(URL, headers={"origin": ORIGIN}):
                pytest.fail("Disabled trial accepted a connection")
        assert caught.value.code == 1008
    assert [item[0] for item in trace] == ["websocket.close"]
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("enabled,handler", [
    (1, unused_handler), ("true", unused_handler), (None, unused_handler),
    (False, None), (True, lambda *_: None), (True, object()),
])
def test_factory_rejects_nonliteral_configuration(enabled, handler):
    with pytest.raises(ValueError, match="^source_local_app_configuration_invalid$"):
        local_app.create_source_local_app(binding=None, handler=handler, enabled=enabled)


@pytest.mark.parametrize("case", ["missing_binding", "forged_binding", "foreign_session", "missing_origin",
    "wrong_origin", "wrong_host", "duplicate_host", "duplicate_origin", "forwarded_host", "client_enable"])
def test_invalid_selection_closes_before_accept_or_any_b_read(tmp_path, monkeypatch, case):
    value = make_binding(tmp_path)
    forbid_mutations(monkeypatch)
    async def forbidden_reader(*args):
        pytest.fail("Rejected selection read the store")
    monkeypatch.setattr(value.store, "read_source_setup_manifest", forbidden_reader)
    chosen, enabled, url = value, True, URL
    headers = httpx.Headers({"origin": ORIGIN})
    if case == "missing_binding": chosen = None
    elif case == "forged_binding": chosen = value.model_copy(update={"expected_host": "127.0.0.1:9000"})
    elif case == "foreign_session": url = URL.replace(SESSION, "foreign")
    elif case == "missing_origin": headers = httpx.Headers()
    elif case == "wrong_origin": headers["origin"] = "http://127.0.0.1:9000"
    elif case == "wrong_host": headers["host"] = "localhost:8000"
    elif case == "duplicate_host": headers = httpx.Headers([("host", HOST), ("Host", HOST), ("origin", ORIGIN)])
    elif case == "duplicate_origin": headers = httpx.Headers([("origin", ORIGIN), ("Origin", ORIGIN)])
    elif case == "forwarded_host": headers.update({"host": "untrusted.invalid", "x-forwarded-host": HOST})
    elif case == "client_enable":
        enabled = False
        url += "?enabled=true&destination=source_local_trial"
        headers["x-source-enabled"] = "true"
    app = local_app.create_source_local_app(binding=chosen, handler=unused_handler, enabled=enabled)
    trace = []
    with TestClient(TraceASGI(app, trace)) as client:
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect(url, headers=headers):
                pytest.fail("Invalid selection accepted")
    assert caught.value.code == 1008
    assert [item[0] for item in trace] == ["websocket.close"]
    assert "PRIVATE" not in repr(trace)


@pytest.mark.parametrize("case", ["missing", "corrupt", "io_error"])
def test_unavailable_setup_closes_before_accept_after_one_read(tmp_path, monkeypatch, case):
    value, trace = make_binding(tmp_path), []
    forbid_mutations(monkeypatch)
    async def reader(session_id):
        trace.append(("manifest", session_id))
        if case == "missing": return None
        if case == "corrupt": return value.expected_manifest.model_copy(update={"fingerprint_sha256": "0" * 64})
        raise sqlite3.OperationalError("PRIVATE_DATABASE_DETAIL")
    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    app = local_app.create_source_local_app(binding=value, handler=unused_handler, enabled=True)
    with TestClient(TraceASGI(app, trace)) as client:
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect(URL, headers={"origin": ORIGIN}):
                pytest.fail("Unavailable setup accepted")
    assert caught.value.code == 1008
    assert [item[0] for item in trace] == ["manifest", "websocket.close"]
    assert trace[0][1] == SESSION and "PRIVATE" not in repr(trace)


@pytest.mark.parametrize("handler_closes", [False, True])
def test_selected_connection_accepts_once_before_internal_handler_and_closes_once(tmp_path, monkeypatch, handler_closes):
    value, trace = make_binding(tmp_path), []
    forbid_mutations(monkeypatch)
    async def reader(session_id):
        trace.append(("manifest", session_id))
        return value.expected_manifest
    async def handler(websocket, selected):
        trace.append(("handler", selected.destination))
        assert websocket.application_state == WebSocketState.CONNECTED
        assert selected.binding.store is value.store
        assert selected.binding.producer_config == value.producer_config
        assert selected.manifest == value.expected_manifest
        await websocket.send_json(project_source_briefing(selected.manifest, session_id=SESSION).model_dump(mode="json"))
        if handler_closes:
            await websocket.close(code=1000)
    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    app = local_app.create_source_local_app(binding=value, handler=handler, enabled=True)
    with TestClient(TraceASGI(app, trace)) as client:
        with client.websocket_connect(URL, headers={"origin": ORIGIN}) as websocket:
            event = websocket.receive_json()
            assert event == project_source_briefing(value.expected_manifest, session_id=SESSION).model_dump(mode="json")
            with pytest.raises(WebSocketDisconnect) as caught:
                websocket.receive_json()
            assert caught.value.code == 1000
    assert [item[0] for item in trace] == ["manifest", "websocket.accept", "handler", "websocket.send", "websocket.close"]
    assert "PRIVATE" not in repr(trace) and str(value.store.db_path) not in repr(trace)


def test_consecutive_connections_revalidate_existing_setup_without_mutations(tmp_path, monkeypatch):
    store = SQLitePersistence(tmp_path / "existing-synthetic.sqlite3")
    async def explicit_setup():
        await store.initialize()
        return await create_source_trial_setup(session_id=SESSION, request=SETUP, store=store,
            initial_state={"synthetic_marker": "PRIVATE_STATE"}, relationships={})
    manifest = asyncio.run(explicit_setup())
    # Finish fixture-owned connection finalization/WAL checkpoint before taking
    # the physical baseline; later ASGI reads must still preserve these bytes.
    gc.collect()
    value = make_binding(tmp_path, store=store, manifest=manifest)
    before = hashlib.sha256(store.db_path.read_bytes()).hexdigest()
    forbid_mutations(monkeypatch)
    trace, calls, real_reader = [], [], store.read_source_setup_manifest
    async def reader(session_id):
        calls.append(session_id)
        return await real_reader(session_id)
    async def handler(websocket, selected):
        await websocket.send_json(project_source_briefing(selected.manifest, session_id=SESSION).model_dump(mode="json"))
    monkeypatch.setattr(store, "read_source_setup_manifest", reader)
    app = local_app.create_source_local_app(binding=value, handler=handler, enabled=True)
    with TestClient(TraceASGI(app, trace)) as client:
        for _ in range(2):
            with client.websocket_connect(URL, headers={"origin": ORIGIN}) as websocket:
                assert websocket.receive_json()["event"] == "briefing"
                with pytest.raises(WebSocketDisconnect): websocket.receive_json()
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(URL.replace(SESSION, "foreign"), headers={"origin": ORIGIN}): pass
        assert calls == [SESSION, SESSION]
        store.db_path = tmp_path / "changed.sqlite3"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(URL, headers={"origin": ORIGIN}): pass
        assert calls == [SESSION, SESSION]
        store.db_path = Path(value.database_path)
        with client.websocket_connect(URL, headers={"origin": ORIGIN}) as websocket:
            assert websocket.receive_json()["event"] == "briefing"
            with pytest.raises(WebSocketDisconnect): websocket.receive_json()
    assert calls == [SESSION] * 3
    assert hashlib.sha256(store.db_path.read_bytes()).hexdigest() == before
    with sqlite3.connect(store.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM campaigns").fetchone() == (1,)
        for table in ("attempts", "turns", "events", "memory_candidates"):
            assert connection.execute("SELECT count(*) FROM " + table).fetchone() == (0,)


def test_legacy_websocket_path_is_not_mounted_or_redirected(tmp_path, monkeypatch):
    value = make_binding(tmp_path)
    forbid_mutations(monkeypatch)
    async def forbidden(*args): pytest.fail("Legacy URL reached B reader")
    monkeypatch.setattr(value.store, "read_source_setup_manifest", forbidden)
    app = local_app.create_source_local_app(binding=value, handler=unused_handler, enabled=True)
    trace = []
    with TestClient(TraceASGI(app, trace)) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"ws://{HOST}/ws/session/{SESSION}", headers={"origin": ORIGIN}): pass
    assert [item[0] for item in trace] == ["websocket.close"]


def test_factory_has_no_legacy_runtime_bootstrap_or_background_task_wiring():
    tree = ast.parse(Path(local_app.__file__).read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {"main", "state_service", "core.config", "llm.runtime", "narrative_source_coordinator",
        "narrative_source_input_service", "narrative_source_setup_service"}.intersection(imports)
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not {"create_task", "initialize", "recover_pending_attempts", "migrate_legacy_session",
        "start_attempt", "create_source_setup_campaign", "generate_structured"}.intersection(calls)


async def run_installed_uvicorn_protocol(app, trace, *, server_closing=False):
    """Exercise installed ASGI receive/send without opening a transport/listener."""
    from uvicorn import Config
    from uvicorn.protocols.websockets.websockets_impl import WebSocketProtocol
    from uvicorn.server import ServerState
    from websockets.exceptions import ConnectionClosedOK
    from websockets.frames import Close

    protocol = WebSocketProtocol(Config(app, log_config=None, lifespan="off"), ServerState(), {})
    protocol.scope = {
        "type": "websocket", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "scheme": "ws", "http_version": "1.1", "path": f"/ws/source-local/{SESSION}",
        "raw_path": f"/ws/source-local/{SESSION}".encode(), "root_path": "",
        "query_string": b"", "headers": [(b"host", HOST.encode()), (b"origin", ORIGIN.encode())],
        "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 8000), "subprotocols": [],
    }
    protocol.ws_server.closing = server_closing

    async def closed_peer():
        raise ConnectionClosedOK(Close(1000, ""), Close(1000, ""), True)

    async def send(message):
        trace.append((message["type"], dict(message)))
        await protocol.asgi_send(message)
        if message["type"] == "websocket.accept":
            protocol.handshake_completed_event.set()

    protocol.recv = closed_peer
    await app(protocol.scope, protocol.asgi_receive, send)
    return protocol


@pytest.mark.parametrize("server_closing, expected_code", [(False, 1000), (True, 1012)])
def test_consumed_uvicorn_disconnect_does_not_send_a_second_close(tmp_path, monkeypatch, server_closing, expected_code):
    value, trace, calls = make_binding(tmp_path), [], []
    forbid_mutations(monkeypatch)

    async def reader(session_id):
        assert session_id == SESSION
        return value.expected_manifest

    async def handler(websocket, selected):
        calls.append(selected.destination)
        try:
            await websocket.receive_text()
        except WebSocketDisconnect as exc:
            assert exc.code == expected_code
            assert websocket.client_state == WebSocketState.DISCONNECTED
            assert websocket.application_state == WebSocketState.CONNECTED
        finally:
            # The boundary must wait for handler settlement before returning.
            await asyncio.sleep(0)
            trace.append(("handler_settled", {}))

    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    app = local_app.create_source_local_app(binding=value, handler=handler, enabled=True)
    protocol = asyncio.run(run_installed_uvicorn_protocol(app, trace, server_closing=server_closing))
    assert protocol.closed_event.is_set()
    assert calls == ["source_local_trial"]
    assert [item[0] for item in trace] == ["websocket.accept", "handler_settled"]


@pytest.mark.parametrize("error", [RuntimeError("handler_failure_sentinel"), asyncio.CancelledError()])
def test_handler_failure_or_cancellation_propagates_without_boundary_close(tmp_path, monkeypatch, error):
    value, trace, calls = make_binding(tmp_path), [], []
    forbid_mutations(monkeypatch)

    async def reader(session_id):
        return value.expected_manifest

    async def handler(websocket, selected):
        calls.append(selected.destination)
        try:
            raise error
        finally:
            await asyncio.sleep(0)
            trace.append(("handler_settled", {}))

    monkeypatch.setattr(value.store, "read_source_setup_manifest", reader)
    app = local_app.create_source_local_app(binding=value, handler=handler, enabled=True)
    with pytest.raises(type(error)) as caught:
        asyncio.run(run_installed_uvicorn_protocol(app, trace))
    assert caught.value is error
    assert calls == ["source_local_trial"]
    assert [item[0] for item in trace] == ["websocket.accept", "handler_settled"]
