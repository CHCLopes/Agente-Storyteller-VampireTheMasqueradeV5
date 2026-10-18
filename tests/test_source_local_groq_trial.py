"""Bounded interactive runner: local SQLite and HTTPX MockTransport only."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import io
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from scripts import run_source_local_groq_trial as trial
from api.llm.contract import GenerationParameters, LLMTarget, utc_now
from api.narrative_source_capsule import create_source_turn_capsule
from api.narrative_source_context import SourceContextSnapshot
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_preparation import DeclaredActionPreparation
from tests.test_source_player_probe import response
from tests.test_narrative_source_setup_flow import REPLY, WAIT_REPLY, table_counts
from tests.test_narrative_source_local_handler import command

KEY = "synthetic-source-local-trial-credential-not-for-retention"


@pytest.fixture
def prepared(tmp_path):
    spec = trial.TrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    return spec, trial.prepare(spec)


def control(prepared, clock=None):
    spec, frozen = prepared
    clock = clock if clock is not None else [0.0]
    return trial.TrialControl(spec, frozen, clock=lambda: clock[0], key=SecretStr(KEY)), clock


def public(text="Aguardo.", operation="action-1"):
    return SourcePlayerActionRequest(operation_id=operation, player_input=text)


def request(prepared, *, seconds=30):
    spec, frozen = prepared
    manifest = trial.create_source_setup_manifest(trial.SETUP, session_id=spec.session_id)
    snapshot = SourceContextSnapshot(origin=manifest.origin, current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=())
    capsule = create_source_turn_capsule(snapshot, operation_id="action-1", created_at=utc_now(),
        player_input="Aguardo.", preparation=DeclaredActionPreparation(), state=trial.player._state(),
        relationships={}, target=frozen.target, system_prompt=frozen.prompt,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Mara",))
    return trial.retained._request(capsule, utc_now() + timedelta(seconds=seconds))


def gateway(prepared, behavior=None, *, clock=None, writer=None):
    ctrl, timer = control(prepared, clock)
    timer[0] = 60
    seen, rows = [], []
    def handle(req):
        seen.append(req)
        return behavior(req) if behavior is not None else response()
    value = trial.TrialGateway(*prepared, ctrl, SecretStr(KEY),
        transport=httpx.MockTransport(handle), record=writer if writer is not None else rows.append)
    return value, ctrl, timer, seen, rows


def test_preflight_is_readonly_and_has_no_credential_provider_or_sqlite(prepared, monkeypatch, capsys):
    spec, frozen = prepared
    monkeypatch.setattr(trial, "configuration", lambda argv: (spec, SimpleNamespace(preflight_only=True)))
    monkeypatch.setattr(trial.os.environ, "pop", lambda *args: pytest.fail("Preflight read a credential"))
    monkeypatch.setattr(trial, "SQLitePersistence", lambda *args: pytest.fail("Preflight opened SQLite"))
    monkeypatch.setattr(httpx.AsyncClient, "send", lambda *args: pytest.fail("Preflight made HTTP"))
    assert trial.main([]) == 0
    output = capsys.readouterr()
    document = json.loads(output.out)
    assert output.err == "" and KEY not in output.out
    assert not spec.run_directory.exists() and not spec.status_directory.exists()
    assert document == frozen.metadata
    assert document["producer_context"]["npc_aliases"] == ["Mara"]
    assert document["budget"]["max_calls"] == 4 and document["budget"]["max_total_output_tokens"] == 3072
    assert document["target"]["model"] == "qwen/qwen3.8-27b"
    assert document["generation_parameters"]["reasoning_effort"] == "none"
    files = {row["file"] for row in document["inputs"]}
    assert {"client/src/index.css", "client/vite.source-player-trial.config.ts",
        "client/src/components/SourcePlayerTrial.tsx"} <= files


@pytest.mark.parametrize("extra", [[], ["--preflight-only", "--managed-stdin-stop"],
    ["--live"], ["--preflight-only", "--api-key-env", trial.KEY_ENV], ["--preflight-only", "--port", "9999"]])
def test_cli_rejects_nonexplicit_mode_ports_and_live_options(extra):
    with pytest.raises(trial.TrialError):
        trial.configuration(["--run-id", str(uuid4()), "--port", "8018", "--origin-port", "5178", *extra])


def test_preflight_detects_metadata_source_and_prompt_drift(prepared, tmp_path, monkeypatch):
    _, frozen = prepared
    trial.check_prepared(frozen)
    frozen.metadata["budget"]["max_calls"] = 5
    with pytest.raises(trial.TrialError, match="preflight_mutated"):
        trial.check_prepared(frozen)
    frozen.metadata["budget"]["max_calls"] = 4
    changed = replace(frozen, prompt=frozen.prompt + "changed")
    with pytest.raises(trial.TrialError, match="target_drift"):
        trial.check_prepared(changed)
    real = trial.sha_file
    monkeypatch.setattr(trial, "sha_file", lambda p: "0"*64 if p.name == "run_source_local_groq_trial.py" else real(p))
    with pytest.raises(trial.TrialError, match="input_drift"):
        trial.check_prepared(frozen)


@pytest.mark.parametrize("text", ["Aguardo.", "Espero a reação de Mara.", "Permaneço aqui em silêncio.",
    "Eu permaneço no lugar e aguardo, sem tocar em nada.", "Converso com Mara.", "Falo com Mara!",
    'Pergunto a Mara: "Como é este lugar?"', "Digo a Mara: «Bom dia.»", "Digo a Mara: “Vamos conversar.”"])
def test_declared_scope_reuses_existing_grammar_without_rng(prepared, monkeypatch, text):
    from api import rules_service
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Admission rolled"))
    assert trial.declared_input(*prepared, public(text))


@pytest.mark.parametrize("text", ["Investigo a galeria.", "Examino o ambiente.", "Analiso o local sem tocar em nada.",
    "Aguardo e ataco Mara.", "Falo com Bela.", "Pergunto.", "Observo a galeria.", 'Digo a Mara: " "'])
def test_non_declared_inputs_are_unavailable_before_production(prepared, text):
    ctrl, timer = control(prepared)
    timer[0] = 60
    assert ctrl.admit(public(text)) is False
    assert ctrl.calls == 0 and not ctrl.eligible and ctrl.denied_operation == "action-1"


def test_initial_quiet_and_negative_admission_are_not_retryable_cooldown(prepared):
    ctrl, timer = control(prepared)
    timer[0] = 59.999
    assert ctrl.admit(public()) is False
    assert not ctrl.stop.is_set()
    ctrl.delivered({"event": "unavailable", "operation_id": "unrelated"})
    assert not ctrl.stop.is_set()
    ctrl.delivered({"event": "unavailable", "operation_id": "action-1"})
    assert ctrl.stop.is_set()
    timer[0] = 120
    assert ctrl.admit(public(operation="second")) is False and ctrl.calls == 0


def test_known_key_echo_in_user_input_or_identity_is_refused_before_p(prepared):
    for value in (public('Digo a Mara: "'+KEY+'"'), public(operation=KEY)):
        ctrl, timer = control(prepared)
        timer[0] = 60
        assert ctrl.admit(value) is False and ctrl.calls == 0


@pytest.mark.asyncio
async def test_four_http_dispatches_keep_exact_request_body_and_original_deadline(prepared):
    gw, ctrl, timer, seen, rows = gateway(prepared)
    for index in range(4):
        timer[0] = 60*(index+1)
        original = request(prepared)
        result = await gw.generate_structured(original)
        assert result.value.narrative == REPLY
        assert rows[-1]["deadline"] == original.deadline.isoformat()
    timer[0] += 60
    with pytest.raises(Exception):
        await gw.generate_structured(request(prepared))
    assert ctrl.calls == len(seen) == 4 and not ctrl.eligible
    for seen_request, row in zip(seen, rows):
        body = json.loads(seen_request.content)
        assert row["request"]["body_sha256"] == trial.retained._sha(body)
        assert body["model"] == "qwen/qwen3.8-27b" and body["reasoning_effort"] == "none"
        assert body["temperature"] == .65 and body["max_completion_tokens"] == 768
        assert KEY not in trial.encoded(row)
    assert rows[-1]["call_made"] is False


@pytest.mark.asyncio
async def test_concurrent_requests_share_last_http_time_and_never_sleep(prepared, monkeypatch):
    gw, ctrl, _, seen, _ = gateway(prepared)
    async def no_sleep(*args): pytest.fail("Gateway pacing slept")
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    results = await asyncio.gather(gw.generate_structured(request(prepared)),
        gw.generate_structured(request(prepared)), return_exceptions=True)
    assert len(seen) == ctrl.calls == 1
    assert sum(isinstance(r, BaseException) for r in results) == 1
    assert not ctrl.eligible


@pytest.mark.parametrize("mutation", ["target", "parameters", "schema", "system", "expired", "long_deadline"])
@pytest.mark.asyncio
async def test_request_drift_never_reaches_http(prepared, mutation):
    gw, ctrl, _, seen, rows = gateway(prepared)
    req = request(prepared)
    if mutation == "target": req = req.model_copy(update={"target": LLMTarget(profile="wrong", provider="Groq", model="other")})
    if mutation == "parameters": req = req.model_copy(update={"parameters": GenerationParameters(temperature=.5, max_output_tokens=900)})
    if mutation == "schema": req = req.model_copy(update={"response_model": SourcePlayerActionRequest})
    if mutation == "system": req = req.model_copy(update={"messages": (req.messages[0].model_copy(update={"content": "other"}), req.messages[1])})
    if mutation == "expired": req = req.model_copy(update={"deadline": utc_now()-timedelta(seconds=1)})
    if mutation == "long_deadline": req = req.model_copy(update={"deadline": utc_now()+timedelta(seconds=61)})
    with pytest.raises(trial.TrialError): await gw.generate_structured(req)
    assert not seen and ctrl.calls == 0 and not ctrl.eligible and rows[0]["call_made"] is False


@pytest.mark.parametrize("mutation", ["body", "url", "method", "expired"])
@pytest.mark.asyncio
async def test_final_http_hook_rechecks_body_route_and_deadline(prepared, mutation):
    ctrl, timer = control(prepared)
    timer[0] = 60
    req = request(prepared)
    adapter = trial.TrialAdapter(prepared=prepared[1], request=req, api_key=SecretStr(KEY), budget=ctrl)
    body = dict(adapter.approved["request"])
    if mutation == "body": body["max_completion_tokens"] = 900
    if mutation == "expired": adapter.deadline = utc_now()-timedelta(seconds=1)
    wire = httpx.Request("GET" if mutation == "method" else "POST",
        "https://example.invalid" if mutation == "url" else trial.retained.GROQ_OFFICIAL_BASE_URL+"/chat/completions", json=body)
    with pytest.raises(trial.TrialError): await adapter._dispatch(wire)
    assert ctrl.calls == 0 and adapter.http_sent is False


@pytest.mark.parametrize("location", ["n", "q", "metadata", "header", "error"])
@pytest.mark.asyncio
async def test_provider_key_echo_never_reaches_capture_or_return(prepared, location):
    reply = response()
    if location == "n": reply = response(n=REPLY+KEY)
    if location == "q": reply = response(q=KEY+"?")
    if location == "metadata": reply = response(extra={"request_id": KEY})
    if location == "header": reply.headers["x-request-id"] = KEY
    if location == "error": reply = httpx.Response(429, json={"error": {"message": KEY}})
    gw, ctrl, _, seen, rows = gateway(prepared, lambda req: reply)
    with pytest.raises(Exception): await gw.generate_structured(request(prepared))
    assert ctrl.calls == len(seen) == 1 and not ctrl.eligible
    assert rows[0]["credential_echo_blocked"] is True and rows[0]["capture"] == {}
    assert KEY not in trial.encoded(rows)


@pytest.mark.parametrize("failure", ["rate_limit", "transport", "cancel", "reported_overrun", "record"])
@pytest.mark.asyncio
async def test_operational_failures_preserve_attempt_count_and_close_eligibility(prepared, failure):
    def behavior(req):
        if failure == "rate_limit": return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
        if failure == "transport": raise httpx.ConnectError("synthetic transport", request=req)
        if failure == "cancel": raise asyncio.CancelledError()
        if failure == "reported_overrun": return response(extra={"usage": {"completion_tokens": 900, "total_tokens": 900}})
        return response()
    def broken(row): raise OSError(KEY)
    gw, ctrl, _, seen, rows = gateway(prepared, behavior, writer=broken if failure == "record" else None)
    with pytest.raises(BaseException) as error:
        await gw.generate_structured(request(prepared))
    assert KEY not in str(error.value) and ctrl.calls == len(seen) == 1 and not ctrl.eligible
    if failure != "record": assert rows[0]["call_made"] is True


def test_delivery_stops_only_current_terminal_and_preserves_policy_rejection(prepared):
    ctrl, timer = control(prepared)
    timer[0] = 60
    assert ctrl.admit(public())
    ctrl.calls = 1
    ctrl.delivered({"event": "narrative_rejected", "code": "narrative_rejected", "operation_id": "action-1"})
    assert ctrl.eligible and not ctrl.stop.is_set()
    ctrl.calls = 4
    ctrl.delivered({"event": "narrative_complete", "operation_id": "old"})
    assert ctrl.eligible and not ctrl.stop.is_set()
    ctrl.delivered({"event": "narrative_complete", "operation_id": "action-1"})
    assert not ctrl.eligible and ctrl.stop.is_set() and ctrl.reason == "budget_completed"


async def create_store(prepared):
    spec, frozen = prepared
    store = trial.SQLitePersistence(spec.database)
    await store.initialize()
    await trial.create_source_trial_setup(session_id=spec.session_id, request=trial.SETUP,
        store=store, initial_state=trial.player._state(), relationships={})
    return store


def next_event(socket, name):
    while True:
        value = socket.receive_json()
        if value["event"] == name: return value
        assert value["event"] not in {"unavailable", "narrative_rejected", "preparation_rejected"}, value


def test_composed_four_turns_real_p_k_h_and_query_reconnect_without_http(prepared, monkeypatch):
    from api import rules_service
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Declared path rolled"))
    spec, frozen = prepared
    store = asyncio.run(create_store(prepared))
    index = [0]
    def behavior(req):
        index[0] += 1
        return response(n=REPLY if index[0] == 1 else WAIT_REPLY)
    gw, ctrl, timer, seen, rows = gateway(prepared, behavior)
    app = trial.application(spec, store, frozen, ctrl, gw)
    url = "/ws/source-local/"+spec.session_id
    with TestClient(app, base_url="http://127.0.0.1:8018") as client:
        with client.websocket_connect(url, headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            assert next_event(socket, "briefing")["origin"] == "authored_trial_setup"
            for i in range(4):
                timer[0] = 60*(i+1)
                socket.send_text(command(operation="action-"+str(i), text="Aguardo."))
                event = next_event(socket, "narrative_complete")
                assert event["operation_id"] == "action-"+str(i)
                socket.send_text(command("query", "action-"+str(i)))
                assert next_event(socket, "narrative_complete") == event
                assert len(seen) == i+1
            assert ctrl.stop.is_set() and ctrl.reason == "budget_completed"
        before = table_counts(store)
        with client.websocket_connect(url, headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            next_event(socket, "briefing")
            assert next_event(socket, "narrative_complete") == event
    assert before == table_counts(store) == {"attempts": 12, "turns": 4, "events": 4}
    assert len(seen) == ctrl.calls == len(rows) == 4
    assert trial.config(frozen).npc_aliases == ("Mara",)
    assert all(KEY not in trial.encoded(row) for row in rows)


def test_composed_investigation_is_unavailable_without_p_k_h_or_rng(prepared, monkeypatch):
    from api import rules_service
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Scope guard rolled"))
    spec, frozen = prepared
    store = asyncio.run(create_store(prepared))
    gw, ctrl, _, seen, _ = gateway(prepared)
    with TestClient(trial.application(spec, store, frozen, ctrl, gw), base_url="http://127.0.0.1:8018") as client:
        with client.websocket_connect("/ws/source-local/"+spec.session_id, headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            next_event(socket, "briefing")
            socket.send_text(command(text="Investigo a galeria."))
            event = next_event(socket, "unavailable")
            assert event["phase"] == "preparation" and ctrl.stop.is_set()
    assert not seen and table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}


@pytest.mark.parametrize("line", ["stop\n", "stop\r\n", "", "malformed-private-value\n"])
@pytest.mark.asyncio
async def test_managed_stdin_only_requests_shutdown_without_echo(prepared, line):
    ctrl, _ = control(prepared)
    trial.stdin_shutdown(ctrl, io.StringIO(line), asyncio.get_running_loop())
    await asyncio.wait_for(ctrl.stop.wait(), 2)
    assert ctrl.stdin_failed is (line.startswith("malformed"))
    assert ctrl.calls == 0 and not ctrl.eligible
    assert ctrl.reason == ("managed_stdin_invalid" if line.startswith("malformed") else "operator_stop")


def test_unavailable_for_admitted_operation_closes_eligibility_after_delivery(prepared):
    ctrl, timer = control(prepared)
    timer[0] = 60
    assert ctrl.admit(public())
    ctrl.delivered({"event": "unavailable", "operation_id": "unknown-query"})
    assert ctrl.eligible and not ctrl.stop.is_set()
    ctrl.delivered({"event": "unavailable", "operation_id": "action-1"})
    assert not ctrl.eligible and ctrl.stop.is_set()
    assert ctrl.calls == 0 and ctrl.reason == "operation_unavailable"


@pytest.mark.parametrize("condition", ["clean", "force_exit", "tasks", "connections", "shutdown_failed", "error_occured", "exception", "stdin_invalid"])
@pytest.mark.asyncio
async def test_server_settlement_conditions_never_promote_failed_shutdown(prepared, monkeypatch, condition):
    import uvicorn
    spec, _ = prepared
    spec.status_directory.mkdir()
    ctrl, _ = control(prepared)
    ctrl.stop.set()
    class Server:
        def __init__(self, configuration):
            assert configuration.timeout_graceful_shutdown == 65
            self.started = False
            self.should_exit = False
            self.force_exit = condition == "force_exit"
            self.server_state = SimpleNamespace(tasks={"pending"} if condition == "tasks" else set(),
                connections={"socket"} if condition == "connections" else set())
            self.lifespan = SimpleNamespace(shutdown_failed=condition == "shutdown_failed", error_occured=condition == "error_occured")
        async def serve(self):
            if condition == "exception": raise RuntimeError("server failure")
            self.started = True
            while not self.should_exit: await asyncio.sleep(.001)
    monkeypatch.setattr(uvicorn, "Server", Server)
    ctrl.stdin_failed = condition == "stdin_invalid"
    if condition == "clean": await trial.serve(spec, object(), ctrl)
    else:
        with pytest.raises((trial.TrialError, RuntimeError)):
            await trial.serve(spec, object(), ctrl)
    document = json.loads((spec.status_directory/"status.json").read_text()) if condition != "exception" else {}
    assert document.get("status") != "stopped"


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.asyncio
async def test_run_status_stopped_only_after_serve_returns_successfully(prepared, monkeypatch, failure):
    spec, frozen = prepared
    async def fake_serve(spec, app, ctrl, **kwargs):
        assert json.loads((spec.status_directory/"status.json").read_text())["status"] == "prepared"
        if failure: raise RuntimeError(KEY)
    monkeypatch.setattr(trial, "serve", fake_serve)
    if failure:
        with pytest.raises(RuntimeError): await trial.run(spec, frozen, SecretStr(KEY))
    else: await trial.run(spec, frozen, SecretStr(KEY))
    document = json.loads((spec.status_directory/"status.json").read_text())
    assert document["status"] == ("failed" if failure else "stopped")
    assert document["calls_started"] == 0
    assert all(KEY.encode() not in p.read_bytes() for p in spec.run_directory.iterdir() if p.is_file())
    assert KEY not in trial.encoded(document)
