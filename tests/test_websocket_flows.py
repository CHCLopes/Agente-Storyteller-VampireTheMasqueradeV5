from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api import main
from api.llm.contract import LLMTarget
from api.narration_resume_service import exact_target_scope_key
from api.persistence import SQLitePersistence, StateRevisionError
from api.rules_service import ResolutionResult
from api.state_service import (
    configure_persistence_for_tests,
    get_persistence,
    sync_event_from_context,
)
from api.turn_models import (
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
)


def _successful_frenzy_roll() -> ResolutionResult:
    return ResolutionResult(
        successes=3,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="3 sucessos",
        normal_rolls=[8, 7],
        hunger_rolls=[6],
        margin=0,
    )


def _runtime_target_only():
    """Frenzy consults the local gate for this target but never calls a gateway."""

    return SimpleNamespace(
        target=LLMTarget(profile="narrator", provider="fake", model="fixed")
    )


def _context(*, hunger: int, aggravated_health: int = 0) -> dict:
    return {
        "player_sheet": {
            "clan": "brujah",
            "predator_type": "alleycat",
            "attributes": {"Strength": 3, "Composure": 3, "Resolve": 3},
            "skills": {},
            "disciplines": {},
            "status": {
                "blood_potency": 1,
                "current_hunger": hunger,
                "humanity": 7,
                "health_tracker": {
                    "size": 7,
                    "superficial": 0,
                    "aggravated": aggravated_health,
                },
                "willpower_tracker": {
                    "size": 5,
                    "superficial": 0,
                    "aggravated": 0,
                },
            },
        },
        "last_action_cache": None,
        "pre_roll_snapshot": None,
    }


@pytest.fixture
def isolated_store(tmp_path):
    previous_store = get_persistence()
    previous_sessions = dict(main.active_sessions)
    store = SQLitePersistence(tmp_path / "websocket-control.sqlite3")
    configure_persistence_for_tests(store)
    main.active_sessions.clear()
    try:
        yield store
    finally:
        main.active_sessions.clear()
        main.active_sessions.update(previous_sessions)
        configure_persistence_for_tests(previous_store)


def _seed(store: SQLitePersistence, session_id: str, event) -> None:
    asyncio.run(
        store.ensure_campaign(
            session_id,
            initial_state=event.model_dump(mode="json"),
        )
    )


def test_torpor_blocks_before_any_llm_operation(isolated_store, monkeypatch):
    session_id = f"ws-torpor-{uuid4().hex}"
    context = _context(hunger=1, aggravated_health=7)
    event = sync_event_from_context(session_id, context, status_override="TORPOR")
    _seed(isolated_store, session_id, event)

    def unexpected_runtime():
        raise AssertionError("TORPOR must be handled before resolving an LLM target")

    monkeypatch.setattr(main, "get_llm_runtime", unexpected_runtime)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            restored = websocket.receive_json()
            assert restored["character"]["status"] == "TORPOR"

            websocket.send_text("Tento socar o inimigo.")
            blocked = websocket.receive_json()
            unchanged = websocket.receive_json()

            assert blocked["action"] == "error"
            assert "personagem está em TORPOR" in blocked["message"]
            assert unchanged["event"] == "state_update"
            assert unchanged["character"]["status"] == "TORPOR"
            assert unchanged["turn_number"] == 0


def test_pending_frenzy_resolution_is_deterministic_and_persisted(
    isolated_store,
    monkeypatch,
):
    session_id = f"ws-frenzy-{uuid4().hex}"
    context = _context(hunger=5)
    event = sync_event_from_context(
        session_id,
        context,
        status_override="FRENZY_CHECK",
    )
    _seed(isolated_store, session_id, event)
    monkeypatch.setattr(
        "api.rules_service._roll_v5_dice",
        lambda **_: _successful_frenzy_roll(),
    )

    monkeypatch.setattr(main, "get_llm_runtime", _runtime_target_only)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            restored = websocket.receive_json()
            assert restored["context"]["blocking"] is True
            assert restored["context"]["pending_roll"]["type"] == (
                "FRENZY_RESISTANCE"
            )

            websocket.send_text("Tento resistir ao frenesi.")
            result = websocket.receive_json()
            updated = websocket.receive_json()

            assert result["action"] == "chat_response"
            assert "[TESTE DE FRENESI] Sucesso!" in result["message"]
            assert updated["character"]["status"] == "ACTIVE"
            assert updated["context"]["blocking"] is False
            assert updated["turn_number"] == 0

        main.active_sessions.clear()
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            rehydrated = websocket.receive_json()
            assert rehydrated["character"]["status"] == "ACTIVE"
            assert rehydrated["context"]["blocking"] is False
            assert rehydrated["turn_number"] == 0


def test_frenzy_envelope_replays_without_a_second_roll(
    isolated_store,
    monkeypatch,
):
    session_id = f"ws-frenzy-idempotent-{uuid4().hex}"
    operation_id = "op-frenzy-stable"
    player_input = "Tento resistir ao frenesi."
    context = _context(hunger=5)
    event = sync_event_from_context(
        session_id,
        context,
        status_override="FRENZY_CHECK",
    )
    _seed(isolated_store, session_id, event)
    roll_calls: list[int] = []

    def roll_once(**_kwargs):
        roll_calls.append(1)
        return _successful_frenzy_roll()

    monkeypatch.setattr("api.rules_service._roll_v5_dice", roll_once)

    monkeypatch.setattr(main, "get_llm_runtime", _runtime_target_only)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            envelope = {"operation_id": operation_id, "input": player_input}
            websocket.send_json(envelope)
            first_result = websocket.receive_json()
            first_state = websocket.receive_json()

            websocket.send_json(envelope)
            replayed_result = websocket.receive_json()
            replayed_state = websocket.receive_json()

    assert roll_calls == [1]
    assert replayed_result == first_result
    assert first_result["operation_id"] == operation_id
    assert first_result["terminal"] is True
    assert first_state["character"]["status"] == "ACTIVE"
    assert replayed_state["character"]["status"] == "ACTIVE"
    attempts = asyncio.run(isolated_store.list_attempts(session_id))
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (operation_id, "completed")
    ]


def test_frenzy_gate_blocks_immediately_before_rng_without_mutating_state(
    isolated_store,
    monkeypatch,
):
    session_id = f"ws-frenzy-gated-{uuid4().hex}"
    operation_id = "op-frenzy-gated"
    event = sync_event_from_context(
        session_id,
        _context(hunger=5),
        status_override="FRENZY_CHECK",
    )
    _seed(isolated_store, session_id, event)
    runtime = _runtime_target_only()
    key = exact_target_scope_key(runtime.target)
    asyncio.run(isolated_store.upsert_narrator_availability_gate(
        session_id=session_id,
        gate=NarratorAvailabilityGate(
            gate_id=f"gate-{key[:24]}",
            state=NarratorGateState.UNAVAILABLE,
            scope=NarratorGateScope.EXACT_TARGET,
            scope_key=key,
            target=runtime.target.model_dump(mode="json"),
            observed_at=datetime.now(timezone.utc),
        ),
    ))
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    roll_calls: list[int] = []
    monkeypatch.setattr(
        "api.rules_service._roll_v5_dice",
        lambda **_: roll_calls.append(1),
    )

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.send_json({
                "operation_id": operation_id,
                "input": "Tento resistir ao frenesi.",
            })
            error = websocket.receive_json()
            terminal = websocket.receive_json()

    assert roll_calls == []
    assert error["action"] == "error"
    assert terminal["action"] == "stream_end"
    campaign = asyncio.run(isolated_store.load_campaign(session_id))
    assert campaign is not None
    assert campaign["state"]["character"]["status"] == "FRENZY_CHECK"
    assert campaign["state_revision"] == 0


def test_frenzy_completion_error_is_terminal_and_replayable(
    isolated_store,
    monkeypatch,
):
    session_id = f"ws-frenzy-error-{uuid4().hex}"
    operation_id = "op-frenzy-error"
    player_input = "Tento resistir ao frenesi."
    event = sync_event_from_context(
        session_id,
        _context(hunger=5),
        status_override="FRENZY_CHECK",
    )
    _seed(isolated_store, session_id, event)
    monkeypatch.setattr(
        "api.rules_service._roll_v5_dice",
        lambda **_: _successful_frenzy_roll(),
    )
    monkeypatch.setattr(main, "get_llm_runtime", _runtime_target_only)

    async def reject_stale_completion(**_kwargs):
        raise StateRevisionError("simulated concurrent control update")

    monkeypatch.setattr(
        isolated_store,
        "complete_control_attempt",
        reject_stale_completion,
    )

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            envelope = {"operation_id": operation_id, "input": player_input}
            websocket.send_json(envelope)
            first_delivery = (websocket.receive_json(), websocket.receive_json())
            websocket.send_json(envelope)
            replay = (websocket.receive_json(), websocket.receive_json())

    assert replay == first_delivery
    error, terminal = first_delivery
    assert error["action"] == "error"
    assert error["operation_id"] == operation_id
    assert error["terminal"] is True
    assert terminal == {
        "action": "stream_end",
        "operation_id": operation_id,
        "status": "failed",
        "partial": False,
    }
    attempts = asyncio.run(isolated_store.list_attempts(session_id))
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (operation_id, "failed")
    ]
    campaign = asyncio.run(isolated_store.load_campaign(session_id))
    assert campaign is not None
    assert campaign["current_turn"] == 0
    assert campaign["state"]["character"]["status"] == "FRENZY_CHECK"
