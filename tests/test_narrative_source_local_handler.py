"""Local synthetic socket composition: explicit action, committed text, readonly replay."""
import asyncio
import json

import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from api import narrative_source_input_service, narrative_source_local_handler as handler, rules_service
from api.narrative_source_local_selection import create_source_local_trial_binding, select_source_local_entry
from api.narrative_source_local_app import create_source_local_app
from test_narrative_source_bridge import FIRST, QUESTION, _gateway
from test_narrative_source_setup_flow import SESSION, config, setup, table_counts

HOST = "127.0.0.1:8000"
ORIGIN = "http://127.0.0.1:8000"


def command(kind="submit", operation="action-1", text="Aguardo."):
    data = {"protocol": handler.COMMAND_PROTOCOL, "command": kind, "operation_id": operation}
    if kind == "submit": data["player_input"] = text
    return json.dumps(data, ensure_ascii=False)


class Socket:
    def __init__(self):
        self.incoming, self.outgoing = asyncio.Queue(), asyncio.Queue()
        self.sent, self.closes, self.disconnected = [], [], False

    async def send_json(self, value):
        if self.disconnected: raise WebSocketDisconnect(1001)
        self.sent.append(value)
        await self.outgoing.put(value)

    async def receive_text(self):
        value = await self.incoming.get()
        if value is None: raise WebSocketDisconnect(1001)
        if type(value) is bytes: raise KeyError("text")
        return value

    async def close(self, code):
        self.closes.append(code)
        self.disconnected = True

    async def disconnect(self):
        self.disconnected = True
        await self.incoming.put(None)


async def selected(tmp_path):
    store, manifest = await setup(tmp_path)
    binding = create_source_local_trial_binding(session_id=SESSION, store=store,
        expected_manifest=manifest, producer_config=config(), expected_host=HOST, expected_origin=ORIGIN)
    result = await select_source_local_entry(destination="source_local_trial", enabled=True,
        binding=binding, received_session_id=SESSION,
        raw_headers=[(b"host", HOST.encode()), (b"origin", ORIGIN.encode())])
    assert result.destination == "source_local_trial"
    return store, result


async def next_event(socket, name, *, operation=None):
    async with asyncio.timeout(5):
        while True:
            value = await socket.outgoing.get()
            if value["event"] == name and (operation is None or value.get("operation_id") == operation):
                return value


async def start(selected, gateway, *, seconds=5):
    socket = Socket()
    task = asyncio.create_task(handler.create_source_local_handler(gateway=gateway,
        action_timeout_seconds=seconds)(socket, selected))
    assert (await next_event(socket, "briefing"))["origin"] == "authored_trial_setup"
    return socket, task


async def finish(socket, task):
    await socket.disconnect()
    await asyncio.wait_for(task, 5)


@pytest.mark.parametrize("raw", [
    None, {}, "null", "[]", "{", '{"protocol":NaN}',
    '{"protocol":"narrative-source-command-v1","command":"query","operation_id":"a","operation_id":"b"}',
    command().replace(handler.COMMAND_PROTOCOL, "v1"),
    command().replace('"submit"', '"retry"'),
    command().replace('"Aguardo."', 'null'),
    command().replace('"Aguardo."', '" padded "'),
    command(operation=" "), command(operation="a"*241), command(text="x"*501),
    json.dumps({**json.loads(command()), "session_id": "private"}),
    json.dumps({**json.loads(command()), "target": {"model": "private"}}),
    json.dumps({**json.loads(command("query")), "player_input": "Aguardo."}),
    command()+" "*handler.MAX_COMMAND_BYTES,
])
def test_commands_reject_ambiguous_or_privileged_frames_without_echo(raw):
    with pytest.raises(handler.SourceLocalHandlerError, match="^source_local_handler_invalid$"):
        handler.decode_source_local_command(raw)


def test_literal_submit_query_and_unicode_limits_are_preserved():
    kind, request = handler.decode_source_local_command(command(operation="id-ç", text="Olá, Mara?"))
    assert kind == "submit" and request.operation_id == "id-ç" and request.player_input == "Olá, Mara?"
    assert handler.decode_source_local_command(command("query", "id-ç")) == ("query", "id-ç")
    assert handler.decode_source_local_command(command(text="🦇"*500))[1].player_input == "🦇"*500


@pytest.mark.parametrize("seconds", [False, None, "60", -1, 0, 61, float("inf"), float("nan")])
def test_deadline_is_explicit_bounded_server_configuration(seconds):
    _, gateway = _gateway()
    with pytest.raises(handler.SourceLocalHandlerError):
        handler.create_source_local_handler(gateway=gateway, action_timeout_seconds=seconds)


@pytest.mark.asyncio
@pytest.mark.parametrize("binary", [False, True])
async def test_query_unknown_and_invalid_command_never_prepare_or_generate(tmp_path, monkeypatch, binary):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    async def forbidden(**kwargs): pytest.fail("Observation invoked producer/coordinator")
    monkeypatch.setattr(handler, "prepare_source_player_action", forbidden)
    monkeypatch.setattr(handler, "execute_retained_source_turn", forbidden)
    socket, task = await start(value, gateway)
    await socket.incoming.put(command("query", "unknown"))
    assert (await next_event(socket, "unavailable"))["phase"] == "preparation"
    await socket.incoming.put(b"binary" if binary else json.dumps({**json.loads(command()), "state": {"private": True}}))
    await asyncio.wait_for(task, 5)
    assert socket.closes == [1008] and gateway.requests == []
    assert table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}


@pytest.mark.asyncio
async def test_no_provisional_text_query_during_commit_and_readonly_reconnect(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    entered, release = asyncio.Event(), asyncio.Event()
    real_commit = store.commit_turn
    async def held_commit(**kwargs):
        entered.set()
        await release.wait()
        return await real_commit(**kwargs)
    monkeypatch.setattr(store, "commit_turn", held_commit)
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Wait/query rolled"))
    socket, task = await start(value, gateway)
    await socket.incoming.put(command())
    assert (await next_event(socket, "preparation"))["status"] == "ready"
    await asyncio.wait_for(entered.wait(), 5)
    assert not any(item["event"] == "narrative_complete" for item in socket.sent)
    assert FIRST not in json.dumps(socket.sent, ensure_ascii=False) and table_counts(store)["turns"] == 0
    await socket.incoming.put(command("query"))
    assert (await next_event(socket, "narrative_pending"))["status"] == "pending"
    assert len(gateway.requests) == 1
    release.set()
    event = await next_event(socket, "narrative_complete")
    assert (event["n"], event["q"]) == (FIRST, QUESTION)
    assert table_counts(store)["turns"] == 1
    await finish(socket, task)
    counts = table_counts(store)
    async def forbidden(**kwargs): pytest.fail("Reconnect/query executed an action")
    monkeypatch.setattr(handler, "prepare_source_player_action", forbidden)
    monkeypatch.setattr(handler, "execute_retained_source_turn", forbidden)
    again, resumed = await start(value, gateway)
    assert await next_event(again, "narrative_complete") == event
    await again.incoming.put(command("query"))
    assert await next_event(again, "narrative_complete") == event
    await finish(again, resumed)
    assert len(gateway.requests) == 1 and table_counts(store) == counts


@pytest.mark.asyncio
async def test_refused_preparation_preserves_identity_without_h6(tmp_path):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    socket, task = await start(value, gateway)
    await socket.incoming.put(command(text="Ataco Mara."))
    event = await next_event(socket, "preparation_rejected")
    assert event["operation_id"] == "action-1" and event["code"] == "out_of_scope"
    await socket.incoming.put(command("query"))
    assert await next_event(socket, "preparation_rejected") == event
    await finish(socket, task)
    assert gateway.requests == [] and table_counts(store)["turns"] == 0


@pytest.mark.asyncio
async def test_disconnect_before_preparation_does_not_start_rng_or_h6(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    entered = asyncio.Event()
    async def held_prepare(**kwargs):
        entered.set()
        await asyncio.Event().wait()
        pytest.fail("Disconnected action resumed")
    monkeypatch.setattr(handler, "prepare_source_player_action", held_prepare)
    socket, task = await start(value, gateway)
    await socket.incoming.put(command())
    await asyncio.wait_for(entered.wait(), 5)
    await finish(socket, task)
    assert gateway.requests == [] and table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}


@pytest.mark.asyncio
async def test_disconnect_during_generation_cancels_once_and_query_never_restarts(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    entered, calls = asyncio.Event(), []
    async def held_generate(request):
        calls.append(request)
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(gateway, "generate_structured", held_generate)
    socket, task = await start(value, gateway)
    await socket.incoming.put(command())
    await asyncio.wait_for(entered.wait(), 5)
    await socket.incoming.put(command(operation="another"))
    assert (await next_event(socket, "unavailable", operation="another"))["phase"] == "preparation"
    await finish(socket, task)
    observed = await store.read_source_player_observation(SESSION, operation_id="action-1")
    assert observed.requested.narrative.status == "cancelled"
    assert len(calls) == 1 and calls[0].cancellation.is_cancelled and table_counts(store)["turns"] == 0
    again, resumed = await start(value, gateway)
    await again.incoming.put(command("query"))
    assert (await next_event(again, "narrative_rejected"))["status"] == "cancelled"
    await finish(again, resumed)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_disconnect_after_commit_keeps_complete_and_reconnect_recovers(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    committed = asyncio.Event()
    real_read = store.read_source_player_observation
    async def held_read(session_id, *, operation_id=None):
        observed = await real_read(session_id, operation_id=operation_id)
        if operation_id is not None and observed.requested.confirmed is not None:
            committed.set()
            await asyncio.Event().wait()
        return observed
    monkeypatch.setattr(store, "read_source_player_observation", held_read)
    socket, task = await start(value, gateway)
    await socket.incoming.put(command())
    await asyncio.wait_for(committed.wait(), 5)
    await finish(socket, task)
    assert not any(event["event"] == "narrative_complete" for event in socket.sent)
    assert table_counts(store)["turns"] == 1 and len(gateway.requests) == 1
    monkeypatch.setattr(store, "read_source_player_observation", real_read)
    again, resumed = await start(value, gateway)
    assert (await next_event(again, "narrative_complete"))["n"] == FIRST
    await finish(again, resumed)
    assert len(gateway.requests) == 1 and table_counts(store)["turns"] == 1


@pytest.mark.asyncio
async def test_repeated_transport_cancellation_settles_child_without_repeated_cancel(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    entered, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    cancelled = []
    async def held_prepare(**kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append("once")
            cleaning.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                pytest.fail("Transport cancelled child cleanup twice")
            raise
    monkeypatch.setattr(handler, "prepare_source_player_action", held_prepare)
    socket, task = await start(value, gateway)
    await socket.incoming.put(command())
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    await asyncio.wait_for(cleaning.wait(), 5)
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError): await task
    assert cancelled == ["once"] and table_counts(store)["turns"] == 0


@pytest.mark.asyncio
async def test_absolute_deadline_covers_gateway_without_retry(tmp_path, monkeypatch):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    calls = []
    async def held_generate(request):
        calls.append(request)
        await asyncio.Event().wait()
    monkeypatch.setattr(gateway, "generate_structured", held_generate)
    socket, task = await start(value, gateway, seconds=.5)
    await socket.incoming.put(command())
    event = await next_event(socket, "narrative_rejected")
    assert event["status"] == "timeout" and event["code"] == "timeout"
    await finish(socket, task)
    assert len(calls) == 1 and table_counts(store)["turns"] == 0


def test_actual_asgi_handler_composition_replays_without_new_generation(tmp_path):
    store, value = asyncio.run(selected(tmp_path))
    _, gateway = _gateway()
    app = create_source_local_app(binding=value.binding,
        handler=handler.create_source_local_handler(gateway=gateway, action_timeout_seconds=5), enabled=True)
    url = f"ws://{HOST}/ws/source-local/{SESSION}"
    with TestClient(app) as client:
        with client.websocket_connect(url, headers={"origin": ORIGIN}) as socket:
            assert socket.receive_json()["event"] == "briefing"
            socket.send_text(command())
            assert socket.receive_json()["event"] == "preparation"
            complete = socket.receive_json()
            assert complete["event"] == "narrative_complete" and complete["n"] == FIRST
        with client.websocket_connect(url, headers={"origin": ORIGIN}) as socket:
            assert socket.receive_json()["event"] == "briefing"
            assert socket.receive_json() == complete
            socket.send_text(command("query"))
            assert socket.receive_json()["event"] == "preparation"
            assert socket.receive_json() == complete
            socket.send_bytes(b"invalid binary command")
            with pytest.raises(WebSocketDisconnect) as closed: socket.receive_json()
            assert closed.value.code == 1008
    assert len(gateway.requests) == 1 and table_counts(store)["turns"] == 1


@pytest.mark.parametrize("answer", [False, None, 1, "yes", "raise"])
@pytest.mark.asyncio
async def test_optional_admission_refuses_before_token_deadline_preparation_and_rng(tmp_path, monkeypatch, answer):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    calls = []
    def admission(request):
        calls.append(request.model_dump())
        if answer == "raise": raise RuntimeError("PRIVATE_CALLBACK_FAILURE")
        return answer
    def forbidden(*args, **kwargs): pytest.fail("Refused admission entered execution")
    monkeypatch.setattr(handler, "CancellationToken", forbidden)
    monkeypatch.setattr(handler, "datetime", type("NoClock", (), {"now": forbidden}))
    monkeypatch.setattr(handler, "prepare_source_player_action", forbidden)
    monkeypatch.setattr(handler, "execute_retained_source_turn", forbidden)
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    socket = Socket()
    task = asyncio.create_task(handler.create_source_local_handler(gateway=gateway,
        action_timeout_seconds=60, admit_submit=admission)(socket, value))
    await next_event(socket, "briefing")
    await socket.incoming.put(command(text="Investigo o ambiente."))
    event = await next_event(socket, "unavailable")
    assert event == {"protocol": "narrative-source-public-event-v1", "event": "unavailable",
        "operation_id": "action-1", "phase": "preparation", "code": "unavailable"}
    await socket.incoming.put(command("query"))
    await next_event(socket, "unavailable")
    await finish(socket, task)
    assert len(calls) == 1 and calls[0]["player_input"] == "Investigo o ambiente."
    assert table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}
    assert gateway.requests == [] and "PRIVATE" not in json.dumps(socket.sent)


@pytest.mark.asyncio
async def test_optional_admission_true_preserves_action_and_query_reconnect_never_calls_hook(tmp_path):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    calls = []
    def admission(request): calls.append(request.model_dump()); return True
    socket = Socket()
    task = asyncio.create_task(handler.create_source_local_handler(gateway=gateway,
        action_timeout_seconds=5, admit_submit=admission)(socket, value))
    await next_event(socket, "briefing")
    await socket.incoming.put(command())
    await next_event(socket, "narrative_complete")
    await socket.incoming.put(command("query"))
    await next_event(socket, "narrative_complete")
    await finish(socket, task)
    assert calls == [{"operation_id": "action-1", "player_input": "Aguardo."}]
    again = Socket()
    resumed = asyncio.create_task(handler.create_source_local_handler(gateway=gateway,
        action_timeout_seconds=5, admit_submit=admission)(again, value))
    await next_event(again, "narrative_complete")
    await finish(again, resumed)
    assert len(calls) == len(gateway.requests) == table_counts(store)["turns"] == 1


@pytest.mark.parametrize("kind", ["async_function", "async_callable", "non_callable"])
def test_optional_admission_requires_synchronous_server_callable(kind):
    async def callback(request): return True
    class AsyncCallable:
        async def __call__(self, request): return True
    candidate = {"async_function": callback, "async_callable": AsyncCallable(), "non_callable": object()}[kind]
    _, gateway = _gateway()
    with pytest.raises(handler.SourceLocalHandlerError):
        handler.create_source_local_handler(gateway=gateway, action_timeout_seconds=60, admit_submit=candidate)


@pytest.mark.asyncio
async def test_optional_admission_cancellation_propagates_without_production(tmp_path):
    store, value = await selected(tmp_path)
    _, gateway = _gateway()
    def cancelled(request): raise asyncio.CancelledError
    socket = Socket()
    task = asyncio.create_task(handler.create_source_local_handler(gateway=gateway,
        action_timeout_seconds=60, admit_submit=cancelled)(socket, value))
    await next_event(socket, "briefing")
    await socket.incoming.put(command())
    with pytest.raises(asyncio.CancelledError): await asyncio.wait_for(task, 5)
    assert table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}
    assert gateway.requests == []
