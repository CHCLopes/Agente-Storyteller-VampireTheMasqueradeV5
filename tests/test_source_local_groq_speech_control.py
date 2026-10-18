"""Literal speech control uses the frozen grammar; no new provider call or parser."""
import asyncio
import json

from fastapi.testclient import TestClient

from scripts import run_source_local_groq_trial as trial
from tests.test_source_local_groq_trial import prepared, control, public, gateway, create_store, next_event
from tests.test_narrative_source_local_handler import command
from tests.test_narrative_source_setup_flow import table_counts


UTTERANCE = "Mara, me fale sobre este lugar"
ENVELOPE = 'Digo a Mara: "' + UTTERANCE + '"'


def test_confirmed_player_utterance_raw_is_unsupported_but_literal_speech_envelope_is_declared(prepared, monkeypatch):
    from api import rules_service
    def forbidden(*args):
        raise AssertionError("Admission rolled")
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    for text, expected in ((UTTERANCE, False), (ENVELOPE, True)):
        ctrl, timer = control(prepared)
        timer[0] = 242
        value = public(text, operation="speech-control-cause")
        assert trial.declared_input(*prepared, value) is expected
        assert ctrl.admit(value) is expected
        assert ctrl.calls == 0
        assert ctrl.reason == (None if expected else "admission_unavailable")
    spec, frozen = prepared
    store = asyncio.run(create_store(prepared))
    gw, ctrl, timer, seen, rows = gateway(prepared)
    timer[0] = 242
    with TestClient(trial.application(spec, store, frozen, ctrl, gw), base_url="http://127.0.0.1:8018") as client:
        with client.websocket_connect("/ws/source-local/"+spec.session_id,
                headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            next_event(socket, "briefing")
            socket.send_text(command(operation="raw-speech", text=UTTERANCE))
            event = next_event(socket, "unavailable")
            assert event["phase"] == "preparation" and ctrl.stop.is_set()
    assert not seen and not rows and ctrl.calls == 0
    assert table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}


def test_literal_speech_envelope_reaches_user_and_commits_once_query_never_rolls_or_generates(prepared, monkeypatch):
    from api import rules_service, narrative_source_input_service
    def forbidden(*args):
        raise AssertionError("Dialogue rolled")
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    produced = []
    actual_producer = narrative_source_input_service.produce_source_player_action
    def counted(request):
        produced.append(request)
        return actual_producer(request)
    monkeypatch.setattr(narrative_source_input_service, "produce_source_player_action", counted)
    spec, frozen = prepared
    store = asyncio.run(create_store(prepared))
    gw, ctrl, timer, seen, rows = gateway(prepared)
    timer[0] = 242
    with TestClient(trial.application(spec, store, frozen, ctrl, gw), base_url="http://127.0.0.1:8018") as client:
        with client.websocket_connect("/ws/source-local/"+spec.session_id,
                headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            next_event(socket, "briefing")
            socket.send_text(command(operation="speech-control", text=ENVELOPE))
            event = next_event(socket, "narrative_complete")
            assert event["operation_id"] == "speech-control"
            before = table_counts(store)
            socket.send_text(command("query", "speech-control"))
            assert next_event(socket, "narrative_complete") == event
            assert table_counts(store) == before
    assert len(produced) == len(seen) == len(rows) == ctrl.calls == 1
    assert produced[0].player_input == ENVELOPE and produced[0].config.npc_aliases == ("Mara",)
    packet = json.loads(json.loads(seen[0].content)["messages"][1]["content"])
    assert packet["player_input"] == ENVELOPE
    assert packet["player_input"][len('Digo a Mara: "'):-1] == UTTERANCE
    assert before == table_counts(store) == {"attempts": 3, "turns": 1, "events": 1}
    assert ctrl.eligible and not ctrl.stop.is_set()
