"""Authored browser fixture preparation; no listener or real provider in tests."""
import ast
import asyncio
import json
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from scripts import run_source_local_fixture as fixture
from api.llm.testing import FakeLLMAdapter


@pytest.fixture
def environment(tmp_path, monkeypatch):
    project, temp = tmp_path / "project", tmp_path / "temp"
    project.mkdir(); temp.mkdir()
    monkeypatch.setattr(fixture, "PROJECT_ROOT", project)
    monkeypatch.setattr(fixture.tempfile, "gettempdir", lambda: str(temp))
    return project, temp


def arguments(*extra, run_id=None):
    return ["--run-id", run_id or str(uuid4()), "--port", "8123", "--origin-port", "5178", *extra]


def test_preflight_validates_pure_components_and_prints_safe_urls_without_side_effects(environment, monkeypatch, capsys):
    async def forbidden(*args, **kwargs): pytest.fail("Preflight reached bootstrap, serving or generation")
    monkeypatch.setattr(fixture.SQLitePersistence, "initialize", forbidden)
    monkeypatch.setattr(fixture, "create_source_trial_setup", forbidden)
    monkeypatch.setattr(fixture, "serve", forbidden)
    monkeypatch.setattr(fixture, "create_source_local_app", lambda **kwargs: pytest.fail("Preflight mounted an app"))
    for name in ("generate_text", "generate_structured", "test_connection"):
        monkeypatch.setattr(FakeLLMAdapter, name, forbidden)
    project, temp = environment
    identity = str(uuid4())
    assert fixture.main(arguments("--preflight-only", run_id=identity)) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "preflight_passed" and output["synthetic_only"]
    assert output["external_provider_calls"] == 0
    assert output["session_id"] == "source-fixture." + identity
    url = urlsplit(output["frontend_url"])
    assert (url.scheme, url.hostname, url.port, url.path) == ("http", "127.0.0.1", 5178, "/source-trial.html")
    assert parse_qs(url.query) == {"backendPort": ["8123"], "session": [output["session_id"]]}
    assert output["expected_origin"] == "http://127.0.0.1:5178"
    assert output["websocket_url"] == "ws://127.0.0.1:8123/ws/source-local/" + output["session_id"]
    assert output["database"] == str(project / "eval-results" / ("source-local-fixture-" + identity) / "storyteller.sqlite3")
    assert output["suggested_actions"] == [fixture.DIALOGUE, "Aguardo."]
    assert output["after_script"] == "repeat_last_authored_reply"
    assert list(project.iterdir()) == [] and list(temp.iterdir()) == []


@pytest.mark.parametrize("changes", [
    ["--run-id", "PRIVATE_INVALID_ID"], ["--port", "0"], ["--port", "65536"],
    ["--port", "80"], ["--origin-port", "80"], ["--port", "5178"],
    ["--origin-port", "-1"], ["--origin-port", "65536"], ["--port", "1.5"],
    ["--api-key", "PRIVATE_CREDENTIAL_SENTINEL"], ["--db-path", "PRIVATE_SAVE_PATH"],
    ["--host", "0.0.0.0"], ["--model", "external-model"],
])
def test_invalid_cli_configuration_fails_closed_before_creating_files(environment, capsys, changes):
    assert fixture.main(arguments("--preflight-only", *changes)) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "failed" and "PRIVATE" not in output
    assert all(list(directory.iterdir()) == [] for directory in environment)


@pytest.mark.parametrize("port,origin", [(1, 65535), (65535, 1)])
def test_nondefault_boundary_ports_are_valid_without_binding(environment, port, origin):
    spec, preflight = fixture.configuration(arguments("--port", str(port), "--origin-port", str(origin), "--preflight-only"))
    assert (spec.port, spec.origin_port, preflight) == (port, origin, True)
    assert all(list(directory.iterdir()) == [] for directory in environment)


@pytest.mark.parametrize("kind", ["empty_run", "file_run", "database", "status"])
def test_any_existing_run_or_status_is_preserved_and_never_adopted(environment, capsys, kind):
    args = arguments("--preflight-only")
    spec, _ = fixture.configuration(args)
    if kind == "file_run":
        spec.run_directory.parent.mkdir(parents=True)
        spec.run_directory.write_bytes(b"existing-sentinel")
    elif kind == "status":
        spec.status_directory.mkdir()
        (spec.status_directory / "status.json").write_bytes(b"existing-sentinel")
    else:
        spec.run_directory.mkdir(parents=True)
        if kind == "database": spec.database.write_bytes(b"existing-sentinel")
    before = {str(path): path.read_bytes() for root in environment for path in root.rglob("*") if path.is_file()}
    assert fixture.main(args) == 2
    assert json.loads(capsys.readouterr().out)["code"] == "source_local_fixture_run_exists"
    after = {str(path): path.read_bytes() for root in environment for path in root.rglob("*") if path.is_file()}
    assert after == before


def test_pure_target_is_fixed_fake_and_does_not_consult_runtime(environment, monkeypatch):
    spec, _ = fixture.configuration(arguments())
    store, gateway, manifest, state, producer = fixture.components(spec)
    assert isinstance(gateway, FakeLLMAdapter) and gateway.requests == []
    assert not store._initialized and not spec.database.exists()
    assert manifest.request.location == "Galeria" and manifest.request.npcs_present == ("Mara",)
    assert state["player_sheet"]["attributes"] == {"Wits": 3}
    assert producer.npc_aliases == ("Mara",)
    assert gateway._capability_set.target.provider == "synthetic"
    assert gateway._capability_set.target.model == "authored-mara-gallery-v1"


@pytest.mark.asyncio
async def test_explicit_bootstrap_then_real_asgi_two_authored_turns_and_readonly_reconnect(environment, monkeypatch):
    spec, _ = fixture.configuration(arguments())
    phases, captured = [], {}
    original_status = fixture.write_status
    def record_status(spec, status):
        phases.append(status)
        original_status(spec, status)
    monkeypatch.setattr(fixture, "write_status", record_status)
    real_components = fixture.components
    def capture_components(spec):
        result = real_components(spec)
        captured["store"], captured["gateway"] = result[0], result[1]
        return result
    monkeypatch.setattr(fixture, "components", capture_components)
    real_application = fixture.application
    def after_setup(spec, store, gateway, manifest, producer):
        assert store._initialized and spec.database.exists()
        with sqlite3.connect(spec.database) as connection:
            assert connection.execute("SELECT count(*) FROM campaigns").fetchone() == (1,)
        return real_application(spec, store, gateway, manifest, producer)
    monkeypatch.setattr(fixture, "application", after_setup)
    async def no_diagnostic(*args, **kwargs): pytest.fail("Fixture ran an implicit diagnostic")
    monkeypatch.setattr(FakeLLMAdapter, "test_connection", no_diagnostic)
    monkeypatch.setattr(FakeLLMAdapter, "generate_text", no_diagnostic)
    async def probe(spec, app):
        assert spec.database.exists() and captured["store"]._initialized
        assert phases == ["preparing", "prepared"] and captured["gateway"].requests == []
        url, origin = spec.metadata("test")["websocket_url"], spec.metadata("test")["expected_origin"]
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(url, headers={"origin": "http://127.0.0.1:5179"}): pass
            assert captured["gateway"].requests == []
            with client.websocket_connect(url, headers={"origin": origin}) as socket:
                assert socket.receive_json()["event"] == "briefing"
                for index, action in enumerate((fixture.DIALOGUE, "Aguardo.")):
                    socket.send_json({"protocol": "narrative-source-command-v1", "command": "submit",
                        "operation_id": f"fixture-action-{index}", "player_input": action})
                    assert socket.receive_json()["event"] == "preparation"
                    event = socket.receive_json()
                    assert event["event"] == "narrative_complete"
                    assert (event["n"], event["q"]) == (fixture.REPLIES[index], fixture.QUESTION)
            with client.websocket_connect(url, headers={"origin": origin}) as socket:
                assert socket.receive_json()["event"] == "briefing"
                assert socket.receive_json()["n"] == fixture.REPLIES[1]
        assert len(captured["gateway"].requests) == 2
        with sqlite3.connect(spec.database) as connection:
            assert connection.execute("SELECT count(*) FROM campaigns").fetchone() == (1,)
            assert connection.execute("SELECT count(*) FROM turns").fetchone() == (2,)
    monkeypatch.setattr(fixture, "serve", probe)
    await fixture.run_fixture(spec)
    assert phases == ["preparing", "prepared", "stopped"]
    assert json.loads((spec.status_directory / "status.json").read_text())["status"] == "stopped"
    before = spec.database.read_bytes()
    with pytest.raises(fixture.FixtureError, match="source_local_fixture_run_exists"):
        await fixture.run_fixture(spec)
    assert spec.database.read_bytes() == before


def test_failure_metadata_never_echoes_exception_detail(environment, monkeypatch, capsys):
    args = arguments()
    spec, _ = fixture.configuration(args)
    async def fail(*args): raise RuntimeError("PRIVATE_FAILURE_DETAIL")
    monkeypatch.setattr(fixture, "serve", fail)
    assert fixture.main(args) == 2
    output = capsys.readouterr().out
    assert "PRIVATE" not in output and json.loads(output)["code"] == "source_local_fixture_failed"
    persisted = (spec.status_directory / "status.json").read_text()
    assert "PRIVATE" not in persisted and json.loads(persisted)["status"] == "failed"
    assert spec.database.exists()


@pytest.mark.asyncio
async def test_uvicorn_configuration_is_single_loopback_without_opening_listener(environment, monkeypatch):
    import uvicorn
    spec, _ = fixture.configuration(arguments())
    captured, statuses = [], []
    class FakeServer:
        def __init__(self, config):
            from types import SimpleNamespace
            captured.append(config)
            self.started, self.should_exit, self.force_exit = False, False, False
            self.server_state = SimpleNamespace(tasks=set(), connections=set())
            self.lifespan = SimpleNamespace(shutdown_failed=False, error_occured=False)
        async def serve(self):
            self.started = True
            await asyncio.sleep(.08)
    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    monkeypatch.setattr(fixture, "write_status", lambda spec, status: statuses.append(status))
    await fixture.serve(spec, object())
    config = captured[0]
    assert config.host == "127.0.0.1" and config.port == spec.port
    assert config.workers == 1 and config.reload is False and config.proxy_headers is False
    assert config.access_log is False and config.lifespan == "on"
    assert statuses == ["running"]
    assert all(list(directory.iterdir()) == [] for directory in environment)


def test_dotenv_is_disabled_before_api_imports_and_no_runtime_or_real_adapter_is_wired():
    tree = ast.parse(Path(fixture.__file__).read_text(encoding="utf-8"))
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
        and ast.unparse(node.targets[0]) == "os.environ['STORYTELLER_DISABLE_DOTENV']")
    assert ast.literal_eval(assignment.value) == "1"
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert all(node.lineno > assignment.lineno for node in imports if (node.module or "").startswith("api."))
    assert not any((node.module or "").startswith(("api.main", "api.state_service", "api.core.config",
        "api.llm.runtime", "api.llm.adapters")) for node in imports)



@pytest.mark.parametrize("mode", ["graceful", "forced", "unsettled", "failure", "cancelled", "connection", "lifespan", "lifespan_exception"])
def test_installed_uvicorn_signals_in_subprocess_preserve_shutdown_outcome(tmp_path, mode):
    """Real signal capture in a child; only the network-serving body is replaced."""
    import os
    import subprocess
    import sys

    child = r"""
import asyncio, json, signal, sys
from pathlib import Path
from uuid import uuid4
import uvicorn
from scripts import run_source_local_fixture as fixture

mode, output = sys.argv[1], Path(sys.argv[2])
project, temporary = output / 'project', output / 'temporary'
project.mkdir(); temporary.mkdir()
fixture.PROJECT_ROOT = project
fixture.tempfile.gettempdir = lambda: str(temporary)
phases = []
real_status = fixture.write_status
def status(spec, value):
    phases.append('status:' + value)
    real_status(spec, value)
fixture.write_status = status

async def synthetic_server_body(self, sockets=None):
    from types import SimpleNamespace
    self.lifespan = SimpleNamespace(shutdown_failed=False, error_occured=False)
    self.started = True
    await asyncio.sleep(.08)
    if mode == 'cancelled':
        phases.append('external_cancellation')
        raise asyncio.CancelledError()
    if mode == 'failure':
        raise RuntimeError('PRIVATE_SERVER_FAILURE_SENTINEL')
    signal.raise_signal(signal.SIGINT)
    await asyncio.sleep(0)
    assert self.should_exit
    phases.append('shutdown_started')
    if mode == 'forced':
        signal.raise_signal(signal.SIGINT)
        await asyncio.sleep(0)
        assert self.force_exit
        phases.append('forced_exit')
        return
    if mode == 'unsettled':
        pending = asyncio.create_task(asyncio.sleep(30))
        self.server_state.tasks.add(pending)
        phases.append('shutdown_has_pending_task')
        return
    if mode == 'connection':
        self.server_state.connections.add(object())
        phases.append('shutdown_has_registered_connection')
        return
    if mode == 'lifespan':
        self.lifespan.shutdown_failed = True
        phases.append('shutdown_lifespan_failed')
        return
    if mode == 'lifespan_exception':
        from uvicorn.lifespan.on import LifespanOn
        async def broken_lifespan(scope, receive, send):
            assert scope['type'] == 'lifespan'
            assert (await receive())['type'] == 'lifespan.startup'
            await send({'type': 'lifespan.startup.complete'})
            assert (await receive())['type'] == 'lifespan.shutdown'
            raise RuntimeError('lifespan shutdown probe')
        self.lifespan = LifespanOn(uvicorn.Config(broken_lifespan, lifespan='on', log_config=None))
        await self.lifespan.startup()
        await self.lifespan.shutdown()
        assert self.lifespan.error_occured and not self.lifespan.shutdown_failed
        phases.append('shutdown_lifespan_exception')
        return
    await asyncio.sleep(.02)
    phases.append('shutdown_finished')

uvicorn.Server._serve = synthetic_server_body
arguments = ['--run-id', str(uuid4()), '--port', '8123', '--origin-port', '5178']
spec, _ = fixture.configuration(arguments)
before = signal.getsignal(signal.SIGINT)
exception_type = None
try:
    code = fixture.main(arguments)
except BaseException as error:
    exception_type = type(error).__name__
    code = 3
result = {
    'status': json.loads((spec.status_directory / 'status.json').read_text())['status'],
    'phases': phases, 'exit_code': code, 'exception_type': exception_type,
    'signal_restored': signal.getsignal(signal.SIGINT) is before,
}
(output / 'result.json').write_text(json.dumps(result))
raise SystemExit(code)
"""
    child_env = {name: os.environ[name] for name in (
        "SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP",
    ) if name in os.environ}
    child_env.update(STORYTELLER_DISABLE_DOTENV="1", PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, "-B", "-c", child, mode, str(tmp_path)],
        cwd=Path(fixture.__file__).resolve().parents[1], env=child_env,
        capture_output=True, text=True, timeout=15)
    observed = json.loads((tmp_path / "result.json").read_text())
    assert observed["signal_restored"]
    assert "PRIVATE" not in result.stdout + result.stderr
    if mode == "graceful":
        assert result.returncode == 0, observed
        assert observed["status"] == "stopped" and observed["exception_type"] is None
        assert observed["phases"] == ["status:preparing", "status:prepared", "status:running",
            "shutdown_started", "shutdown_finished", "status:stopped"]
    else:
        assert result.returncode != 0
        assert observed["status"] == "failed"
        assert "status:stopped" not in observed["phases"]
        if mode == "cancelled":
            assert observed["exception_type"] == "CancelledError"
