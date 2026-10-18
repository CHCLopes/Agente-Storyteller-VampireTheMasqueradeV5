from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import main, orchestrator_service
from api.context_service import LayeredContext
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    LLMInvocationError,
    LLMTarget,
)
from api.llm.runtime import LLMRuntime, LLMRuntimeConfigurationError
from api.llm.testing import FakeLLMAdapter
from api.orchestrator_service import TurnPipelineResult
from api.persistence import SQLitePersistence
from api.relationship_service import RelationshipState
from api.scene_director_service import (
    ProposedSceneFact,
    SceneContinuationProposal,
    SceneFactKind,
)
from api.state_service import configure_persistence_for_tests, get_persistence
from api.turn_models import CanonicalEvent, CanonicalFact, StateChange, TurnDraft


VALID_SCENE_NARRATIVE = (
    "A passagem cede diante da pressão, e o corredor se abre para uma antessala "
    "tomada por lâmpadas vacilantes; passos apressados ressoam atrás de uma "
    "porta metálica marcada com o brasão da cidade, fazendo a ameaça avançar."
)
VALID_PLAYER_PROMPT = (
    "Os passos param atrás da porta; como você pretende reagir?"
)
VALID_NARRATIVE = f"{VALID_SCENE_NARRATIVE}\n\n{VALID_PLAYER_PROMPT}"


def test_narration_commands_are_explicit_and_bounded() -> None:
    command = main._decode_narration_command(json.dumps({
        "command": "resume_narration", "capsule_id": "capsule-1",
        "operation_id": "op-resume", "expected_state_revision": 3,
    }))
    assert command == {
        "command": "resume_narration", "capsule_id": "capsule-1",
        "operation_id": "op-resume", "expected_state_revision": 3,
    }
    assert main._decode_narration_command(json.dumps({
        "operation_id": "op-normal", "input": "Continuo.",
    })) is None
    with pytest.raises(ValueError, match="inválido"):
        main._decode_narration_command(json.dumps({
            "command": "resume_narration", "capsule_id": "capsule-1",
            "operation_id": "op-resume", "expected_state_revision": -1,
        }))


def test_public_pause_projection_does_not_expose_frozen_context_or_scope_key() -> None:
    public = main._pause_payload({
        "capsule_id": "capsule-1",
        "payload": {
            "capsule_id": "capsule-1", "source_operation_id": "op-source",
            "state_revision": 0, "action": "Examino a porta.",
            "resolution": {"display": "3 sucessos", "secret": "omit"},
            "normalized_reason": {"category": "timeout", "safe_message": "Tempo esgotado.", "retryable": True},
            "frozen_context": {"prompt": "SECRET"}, "scope_key": "SECRET-SCOPE",
            "requested_target": {"provider": "private"},
        },
    })
    serialized = json.dumps(public)
    assert "SECRET" not in serialized
    assert "requested_target" not in public
    assert set(public) == {
        "action", "status", "capsule_id", "source_operation_id",
        "expected_state_revision", "action_summary", "resolution_summary",
            "category", "safe_message", "retryable", "retry_not_before",
            "server_now", "rate_limit_origin", "gate_scope", "evidence_scope",
            "allowed_actions",
    }


def _scene_proposal(
    *,
    outcome: str = "success",
    narrative: str = VALID_SCENE_NARRATIVE,
    player_prompt: str = VALID_PLAYER_PROMPT,
) -> SceneContinuationProposal:
    return SceneContinuationProposal(
        narrative=narrative,
        outcome=outcome,
        location="Elysium",
        scene_summary=(
            "Uma passagem recém-aberta conduz a uma antessala, enquanto passos "
            "desconhecidos mantêm a tensão da cena."
        ),
        npcs_present=("Príncipe", "Xerife"),
        new_facts=(
            ProposedSceneFact(
                kind=SceneFactKind.OBSERVATION,
                summary=(
                    "Uma porta metálica com o brasão da cidade bloqueia a "
                    "continuação do corredor."
                ),
                importance=0.7,
            ),
        ),
        open_threads=("Descobrir quem se move atrás da porta metálica.",),
        player_prompt=player_prompt,
    )


def test_generation_truncation_is_localized_before_reaching_the_player() -> None:
    error_payload, terminal = main._turn_failure_payloads(
        operation_id="op-truncated",
        attempt={
            "status": "failed",
            "error": {
                "code": "generation_truncated",
                "safe_message": (
                    "LLM generation stopped before producing a complete response."
                ),
            },
            "partial_narrative": "texto provisório",
            "metadata": {},
        },
        expose_operation=True,
    )

    assert error_payload["message"] == (
        "A resposta do Narrador ultrapassou o limite e foi descartada com "
        "segurança. Tente novamente."
    )
    assert terminal == {
        "action": "stream_end",
        "operation_id": "op-truncated",
        "status": "failed",
        "partial": True,
    }


def _runtime(
    *,
    structured_payload: object | None = None,
    failure_category: ErrorCategory | None = None,
    step_delay_seconds: float = 0.0,
) -> tuple[LLMRuntime, FakeLLMAdapter]:
    target = LLMTarget(profile="websocket-test", provider="fake", model="fake-model")
    capabilities = CapabilitySet(
        target=target,
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport.EMULATED,
                source="local test validation",
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )
    adapter = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=(
            _scene_proposal().model_dump(mode="json")
            if structured_payload is None
            else structured_payload
        ),
        failure_category=failure_category,
        step_delay_seconds=step_delay_seconds,
    )
    return LLMRuntime(target=target, gateway=adapter), adapter


def _prepared_turn(
    *,
    operation_id: str,
    session_id: str,
    player_input: str,
    context: dict,
    base_revision: int,
    base_state_revision: int = 0,
) -> TurnPipelineResult:
    occurred_at = datetime.now(timezone.utc)
    turn_id = f"turn-{operation_id}"
    fact = CanonicalFact(
        fact_id=f"fact-{operation_id}",
        fact_type="mechanics.resolution",
        predicate="resolved",
        value={"successes": 2, "outcome": "success", "is_success": True},
        occurred_at=occurred_at,
    )
    event = CanonicalEvent(
        event_id=f"event-{operation_id}",
        session_id=session_id,
        turn_id=turn_id,
        sequence=0,
        event_type="player_action_resolved",
        occurred_at=occurred_at,
        summary="O personagem venceu o obstáculo.",
        fact_ids=(fact.fact_id,),
    )
    draft = TurnDraft(
        draft_id=f"draft-{operation_id}",
        session_id=session_id,
        turn_id=turn_id,
        attempt_id=f"attempt-{operation_id}",
        player_input=player_input,
        base_revision=base_revision,
        base_state_revision=base_state_revision,
        facts=(fact,),
        events=(event,),
        state_changes=(
            StateChange(path=("player_sheet",), value=context["player_sheet"]),
        ),
    )
    return TurnPipelineResult(
        kind="action",
        system_log="[SYSTEM LOG]: Resultado mecânico: sucesso.",
        updated_context=context,
        relationships_state=RelationshipState(session_id=session_id),
        relationships_for_frontend=[],
        draft=draft,
        context_packet=LayeredContext(),
    )


def _pipeline_stub():
    async def prepare(**kwargs) -> TurnPipelineResult:
        return _prepared_turn(
            operation_id=kwargs["operation_id"],
            session_id=kwargs["session_id"],
            player_input=kwargs["user_input"],
            context=kwargs["context"],
            base_revision=kwargs["turn"] - 1,
            base_state_revision=kwargs["state_revision"],
        )

    return prepare


def _canonical_counts(database_path: Path, session_id: str) -> tuple[int, int, int]:
    """Read committed state without sharing an asyncio lock with TestClient."""

    with sqlite3.connect(database_path) as connection:
        current_turn = connection.execute(
            "SELECT current_turn FROM campaigns WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        turns = connection.execute(
            "SELECT COUNT(*) FROM turns WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        narratives = connection.execute(
            """SELECT COUNT(*) FROM turns
               WHERE session_id=? AND TRIM(narrative_text) <> ''""",
            (session_id,),
        ).fetchone()[0]
    return current_turn, turns, narratives


def _attempts(database_path: Path, session_id: str) -> list[dict]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM attempts WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
    decoded = []
    for row in rows:
        item = dict(row)
        item["error"] = json.loads(item.pop("error_json")) if item["error_json"] else None
        decoded.append(item)
    return decoded


@pytest.fixture
def isolated_websocket_store(tmp_path):
    previous_store = get_persistence()
    previous_sessions = dict(main.active_sessions)
    database_path = tmp_path / "websocket.sqlite3"
    store = SQLitePersistence(database_path)
    configure_persistence_for_tests(store)
    main.active_sessions.clear()
    try:
        yield store, database_path
    finally:
        main.active_sessions.clear()
        main.active_sessions.update(previous_sessions)
        configure_persistence_for_tests(previous_store)


def test_completed_stream_is_provisional_until_atomic_commit_and_rehydrates(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-transaction-success"
    runtime, adapter = _runtime(step_delay_seconds=0.5)
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", _pipeline_stub())

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            initial = websocket.receive_json()
            created = websocket.receive_json()
            assert initial["event"] == "state_update"
            assert initial["turn_number"] == 0
            assert initial["narrative_history"] == []
            assert created["action"] == "chat_response"
            assert "A crônica começa em Elysium." in created["message"]
            assert "Príncipe e Xerife" in created["message"]
            assert created["message"].endswith("O que você faz?")
            assert adapter.external_call_count == 0

            websocket.send_text("Eu avanço.")
            stream_start = websocket.receive_json()
            assert stream_start["action"] == "stream_start"
            assert stream_start["status"] == "provisional"
            assert _canonical_counts(database_path, session_id) == (0, 0, 0)

            validated_chunk = websocket.receive_json()
            committed_state = websocket.receive_json()
            stream_end = websocket.receive_json()

            assert validated_chunk["action"] == "stream_chunk"
            assert validated_chunk["chunk"] == VALID_NARRATIVE
            assert validated_chunk["provisional"] is True
            assert committed_state["action"] == "state_update", (
                committed_state,
                stream_end,
                _attempts(database_path, session_id),
            )
            assert committed_state["turn_number"] == 1
            assert committed_state["narrative_history"][0]["content"] == (
                VALID_NARRATIVE
            )
            assert _canonical_counts(database_path, session_id) == (1, 1, 1)
            assert stream_end["action"] == "stream_end"
            assert stream_end["status"] == "completed"
            assert stream_end["narrative"]["text"] == VALID_NARRATIVE

        # Simulate losing all process-local session state before reconnecting.
        main.active_sessions.clear()
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            restored = websocket.receive_json()
            assert restored["event"] == "state_update"
            assert restored["turn_number"] == 1
            assert len(restored["narrative_history"]) == 1
            assert restored["narrative_history"][0]["content"] == VALID_NARRATIVE

    assert adapter.external_call_count == 1


def test_pause_reconnect_resume_and_duplicate_replay_commit_once(
    isolated_websocket_store,
    monkeypatch,
):
    store, database_path = isolated_websocket_store
    session_id = "ws-pause-resume"
    source_operation_id = "op-source-paused"
    failed_resume_operation_id = "op-resume-failed"
    resume_operation_id = "op-resume-once"
    runtime, base_adapter = _runtime(failure_category=ErrorCategory.TIMEOUT)

    class RetryableAdapter(FakeLLMAdapter):
        async def generate_structured(self, request):
            try:
                return await super().generate_structured(request)
            except LLMInvocationError as exc:
                raise LLMInvocationError(exc.error.model_copy(
                    update={"retryable": True},
                )) from exc

    adapter = RetryableAdapter(
        capability_set=base_adapter.capabilities(runtime.target),
        structured_payload=_scene_proposal().model_dump(mode="json"),
        failure_category=ErrorCategory.TIMEOUT,
    )
    runtime = LLMRuntime(target=runtime.target, gateway=adapter)
    preparation_calls: list[str] = []

    async def prepare(**kwargs):
        preparation_calls.append(kwargs["operation_id"])
        return await _pipeline_stub()(**kwargs)

    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", prepare)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json({
                "operation_id": source_operation_id,
                "input": "Eu avanço.",
            })
            started = websocket.receive_json()
            paused = websocket.receive_json()
            assert started["action"] == "stream_start"
            assert paused["action"] == "narration_paused"
            assert paused["source_operation_id"] == source_operation_id
            assert _canonical_counts(database_path, session_id) == (0, 0, 0)

        main.active_sessions.clear()
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            restored = websocket.receive_json()
            rehydrated_pause = websocket.receive_json()
            assert restored["turn_number"] == 0
            assert rehydrated_pause["capsule_id"] == paused["capsule_id"]
            assert rehydrated_pause["resolution_summary"] == paused["resolution_summary"]

            websocket.send_json({
                "operation_id": "op-blocked-by-pause",
                "input": "Tento outra ação.",
            })
            blocked = websocket.receive_json()
            same_pause = websocket.receive_json()
            assert blocked["action"] == "error"
            assert same_pause["capsule_id"] == paused["capsule_id"]

            failed_resume_command = {
                "command": "resume_narration",
                "capsule_id": paused["capsule_id"],
                "operation_id": failed_resume_operation_id,
                "expected_state_revision": paused["expected_state_revision"],
            }
            websocket.send_json(failed_resume_command)
            failed_start = websocket.receive_json()
            paused_again = websocket.receive_json()
            assert failed_start["resumes_operation_id"] == source_operation_id
            assert paused_again["action"] == "narration_paused"
            assert paused_again["source_operation_id"] == source_operation_id
            assert _canonical_counts(database_path, session_id) == (0, 0, 0)

            websocket.send_json(failed_resume_command)
            replayed_error = websocket.receive_json()
            replayed_failure = websocket.receive_json()
            replayed_pause = websocket.receive_json()
            assert replayed_error["operation_id"] == failed_resume_operation_id
            assert replayed_failure["status"] == "timeout"
            assert replayed_pause["capsule_id"] == paused["capsule_id"]
            assert adapter.external_call_count == 2

            adapter.failure_category = None
            resume_command = {
                **failed_resume_command,
                "operation_id": resume_operation_id,
            }
            websocket.send_json(resume_command)
            resume_start = websocket.receive_json()
            resume_chunk = websocket.receive_json()
            committed = websocket.receive_json()
            completed = websocket.receive_json()
            assert resume_start["resumes_operation_id"] == source_operation_id
            assert resume_chunk["action"] == "stream_chunk"
            assert committed["turn_number"] == 1
            assert completed["status"] == "completed"

            websocket.send_json(resume_command)
            replayed_state = websocket.receive_json()
            replayed_terminal = websocket.receive_json()
            assert replayed_state["turn_number"] == 1
            assert replayed_terminal["status"] == "completed"
            assert replayed_terminal["replayed"] is True

    assert preparation_calls == [source_operation_id]
    assert adapter.external_call_count == 3
    assert _canonical_counts(database_path, session_id) == (1, 1, 1)
    attempts = asyncio.run(store.list_attempts(session_id))
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (source_operation_id, "timeout"),
        (failed_resume_operation_id, "timeout"),
        (resume_operation_id, "completed"),
    ]
    assert attempts[1]["metadata"]["resumes_operation_id"] == source_operation_id
    assert attempts[2]["metadata"]["resumes_operation_id"] == source_operation_id


def test_stable_envelope_preclaims_before_preparation_and_replays_terminal(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-idempotent-envelope"
    operation_id = "op-client-stable"
    envelope = {"operation_id": operation_id, "input": "Eu avanço."}
    runtime, adapter = _runtime()
    preparation_calls: list[str] = []

    async def prepare(**kwargs):
        attempts = _attempts(database_path, session_id)
        assert [(row["operation_id"], row["status"]) for row in attempts] == [
            (operation_id, "pending")
        ]
        preparation_calls.append(kwargs["operation_id"])
        return _prepared_turn(
            operation_id=kwargs["operation_id"],
            session_id=kwargs["session_id"],
            player_input=kwargs["user_input"],
            context=kwargs["context"],
            base_revision=kwargs["turn"] - 1,
            base_state_revision=kwargs["state_revision"],
        )

    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", prepare)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(envelope)

            assert websocket.receive_json()["action"] == "stream_start"
            assert websocket.receive_json()["action"] == "stream_chunk"
            committed = websocket.receive_json()
            terminal = websocket.receive_json()
            assert committed["turn_number"] == 1
            assert terminal["status"] == "completed"
            assert terminal["operation_id"] == operation_id

            websocket.send_json(envelope)
            replayed_state = websocket.receive_json()
            replayed_terminal = websocket.receive_json()

    assert replayed_state["action"] == "state_update"
    assert replayed_state["turn_number"] == 1
    assert replayed_terminal["action"] == "stream_end"
    assert replayed_terminal["status"] == "completed"
    assert replayed_terminal["operation_id"] == operation_id
    assert replayed_terminal["replayed"] is True
    assert preparation_calls == [operation_id]
    assert adapter.external_call_count == 1
    assert _canonical_counts(database_path, session_id) == (1, 1, 1)
    attempts = _attempts(database_path, session_id)
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (operation_id, "completed")
    ]


def test_unspecified_roll_returns_guidance_without_runtime_or_canonical_turn(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-roll-guidance"
    envelope = {
        "operation_id": "op-roll-guidance",
        "input": "Quero rolar os dados.",
    }

    def runtime_must_not_run():
        raise AssertionError("generic roll guidance must not resolve the LLM runtime")

    monkeypatch.setattr(main, "get_llm_runtime", runtime_must_not_run)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(envelope)
            guidance = websocket.receive_json()
            terminal = websocket.receive_json()

            websocket.send_json(envelope)
            replayed_guidance = websocket.receive_json()
            replayed_terminal = websocket.receive_json()

    assert guidance == {
        "action": "clarification",
        "message": (
            "Descreva o que o personagem tenta fazer ou informe atributo e "
            "perícia para a rolagem."
        ),
        "code": "roll_pool_required",
        "operation_id": "op-roll-guidance",
        "terminal": True,
    }
    assert terminal == {
        "action": "stream_end",
        "operation_id": "op-roll-guidance",
        "status": "failed",
        "partial": False,
    }
    assert replayed_guidance == guidance
    assert replayed_terminal == terminal
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    attempts = _attempts(database_path, session_id)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error"]["category"] == "clarification"


def test_scene_query_uses_h6_and_commits_an_advanced_scene(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-direct-scene"
    envelope = {
        "operation_id": "op-direct-scene",
        "input": "Onde estou?",
    }
    scene_narrative = (
        "O salão principal do Elysium permanece sob a luz vermelha dos lustres, "
        "com o Príncipe e o Xerife próximos ao estrado; um mensageiro deixa um "
        "envelope lacrado sobre a mesa e desaparece pela saída lateral."
    )
    scene_prompt = (
        "O envelope permanece ao seu alcance; como você pretende reagir?"
    )
    scene_proposal = _scene_proposal(
        outcome="unresolved",
        narrative=scene_narrative,
        player_prompt=scene_prompt,
    )
    runtime, adapter = _runtime(
        structured_payload=scene_proposal.model_dump(mode="json")
    )
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(envelope)
            started = websocket.receive_json()
            chunk = websocket.receive_json()
            committed = websocket.receive_json()
            terminal = websocket.receive_json()

    expected_narrative = scene_proposal.player_text
    assert started["action"] == "stream_start"
    assert started["status"] == "provisional"
    assert chunk["action"] == "stream_chunk"
    assert chunk["chunk"] == expected_narrative
    assert committed["action"] == "state_update"
    assert committed["turn_number"] == 1
    assert committed["context"]["scene"]["location"] == "Elysium"
    assert committed["context"]["scene"]["summary"] == scene_proposal.scene_summary
    assert committed["context"]["scene"]["last_turn"] == 1
    assert committed["narrative_history"][0]["content"] == expected_narrative
    assert terminal["action"] == "stream_end"
    assert terminal["status"] == "completed"
    assert terminal["narrative"]["text"] == expected_narrative
    assert adapter.external_call_count == 1
    assert [request.operation for request in adapter.requests] == ["H6.direct_scene"]
    assert _canonical_counts(database_path, session_id) == (1, 1, 1)


def test_pending_envelope_is_explicit_and_never_executes(
    isolated_websocket_store,
    monkeypatch,
):
    store, database_path = isolated_websocket_store
    session_id = "ws-idempotent-pending"
    operation_id = "op-client-pending"

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()

    asyncio.run(
        store.start_attempt(
            session_id=session_id,
            operation_id=operation_id,
            requested_turn=1,
            user_input="Eu aguardo.",
        )
    )

    def must_not_run():
        raise AssertionError("runtime must not be resolved for a pending operation")

    async def preparation_must_not_run(**_kwargs):
        raise AssertionError("pipeline must not run for a pending operation")

    monkeypatch.setattr(main, "get_llm_runtime", must_not_run)
    monkeypatch.setattr(main, "prepare_turn_pipeline", preparation_must_not_run)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.send_json(
                {"operation_id": operation_id, "input": "Eu aguardo."}
            )
            pending = websocket.receive_json()
            websocket.send_json(
                {"operation_id": operation_id, "input": "Outra ação."}
            )
            conflict = websocket.receive_json()

    assert pending == {
        "action": "operation_pending",
        "operation_id": operation_id,
        "status": "pending",
        "message": "Esta ação já está em processamento.",
    }
    assert conflict["action"] == "error"
    assert conflict["operation_id"] == operation_id
    assert conflict["terminal"] is True
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    attempts = _attempts(database_path, session_id)
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (operation_id, "pending")
    ]


@pytest.mark.parametrize(
    "failure_stage",
    ("runtime_configuration", "preparation_exception", "pipeline_rejected"),
)
def test_prestream_failure_sequence_is_identical_on_replay(
    isolated_websocket_store,
    monkeypatch,
    failure_stage,
):
    _store, database_path = isolated_websocket_store
    session_id = f"ws-prestream-{failure_stage}"
    operation_id = f"op-{failure_stage}"
    envelope = {"operation_id": operation_id, "input": "Eu observo a rua."}
    calls: list[str] = []

    if failure_stage == "runtime_configuration":
        def missing_runtime():
            calls.append("runtime")
            raise LLMRuntimeConfigurationError("Alvo LLM de teste ausente.")

        monkeypatch.setattr(main, "get_llm_runtime", missing_runtime)
    else:
        runtime, _adapter = _runtime()
        monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

        async def prepare(**kwargs):
            calls.append("prepare")
            if failure_stage == "preparation_exception":
                raise RuntimeError("unsafe internal detail")
            return TurnPipelineResult(
                kind="error",
                system_log="[ERROR H1]: ação rejeitada com segurança",
                updated_context=kwargs["context"],
            )

        monkeypatch.setattr(main, "prepare_turn_pipeline", prepare)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
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
    assert calls == [
        "runtime" if failure_stage == "runtime_configuration" else "prepare"
    ]
    attempts = _attempts(database_path, session_id)
    assert [(row["operation_id"], row["status"]) for row in attempts] == [
        (operation_id, "failed")
    ]
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)


def test_startup_recovers_only_attempts_from_before_process_start(
    isolated_websocket_store,
):
    store, database_path = isolated_websocket_store
    session_id = "ws-process-recovery"

    async def seed_attempts():
        await store.start_attempt(
            session_id=session_id,
            operation_id="op-prior-process",
            requested_turn=1,
            user_input="Ação interrompida.",
        )
        await store.start_attempt(
            session_id=session_id,
            operation_id="op-current-process",
            requested_turn=1,
            user_input="Ação atual.",
        )

    asyncio.run(seed_attempts())
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE attempts SET started_at=? WHERE operation_id=?",
            ("2000-01-01T00:00:00+00:00", "op-prior-process"),
        )

    with TestClient(main.app):
        pass

    statuses = {
        row["operation_id"]: row["status"]
        for row in _attempts(database_path, session_id)
    }
    assert statuses == {
        "op-prior-process": "cancelled",
        "op-current-process": "pending",
    }


def test_legacy_raw_lore_keeps_chat_response_after_committed_state(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-legacy-lore"
    runtime, adapter = _runtime()
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    async def prepare(**kwargs):
        prepared = _prepared_turn(
            operation_id=kwargs["operation_id"],
            session_id=kwargs["session_id"],
            player_input=kwargs["user_input"],
            context=kwargs["context"],
            base_revision=kwargs["turn"] - 1,
            base_state_revision=kwargs["state_revision"],
        )
        prepared.kind = "lore"
        prepared.system_log = "[LORE_RESPONSE] A Camarilla guarda seus segredos."
        return prepared

    monkeypatch.setattr(main, "prepare_turn_pipeline", prepare)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("O que é a Camarilla?")
            committed_state = websocket.receive_json()
            legacy_response = websocket.receive_json()

    assert committed_state["action"] == "state_update"
    assert committed_state["turn_number"] == 1
    assert legacy_response == {
        "action": "chat_response",
        "message": "📜 A Camarilla guarda seus segredos.",
    }
    assert _canonical_counts(database_path, session_id) == (1, 1, 1)
    assert adapter.external_call_count == 0


def test_oversized_action_is_rejected_before_llm_or_attempt(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-oversized-action"
    runtime, adapter = _runtime()
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("x" * (main.MAX_PLAYER_INPUT_CHARS + 1))
            response = websocket.receive_json()

    assert response["action"] == "error"
    assert str(main.MAX_PLAYER_INPUT_CHARS) in response["message"]
    assert adapter.external_call_count == 0
    assert _attempts(database_path, session_id) == []
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)


def test_structured_h6_failure_does_not_advance_or_persist_narrative(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-transaction-failure"
    runtime, adapter = _runtime(
        failure_category=ErrorCategory.PROVIDER_UNAVAILABLE,
    )
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", _pipeline_stub())

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("Eu avanço.")

            start = websocket.receive_json()
            error = websocket.receive_json()
            terminal = websocket.receive_json()

            assert start["action"] == "stream_start"
            assert error["action"] == "error"
            assert terminal["action"] == "stream_end"
            assert terminal["status"] == "failed"
            assert terminal["partial"] is False
            assert _canonical_counts(database_path, session_id) == (0, 0, 0)

        main.active_sessions.clear()
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            restored = websocket.receive_json()
            assert restored["turn_number"] == 0
            assert restored["narrative_history"] == []

    attempts = _attempts(database_path, session_id)
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["partial_narrative"] == ""
    metadata = json.loads(attempts[0]["metadata_json"])
    assert metadata["discarded_output_chars"] == 0
    assert metadata["discarded_output_sha256"] is None
    assert [request.operation for request in adapter.requests] == ["H6.direct_scene"]


def test_slow_structured_h6_deadline_is_terminally_audited(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-h6-real-deadline"
    operation_id = "op-h6-real-deadline"
    runtime, adapter = _runtime(step_delay_seconds=1.05)
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", _pipeline_stub())
    monkeypatch.setattr(orchestrator_service.settings, "llm_timeout_seconds", 1)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(
                {"operation_id": operation_id, "input": "Eu avanço."}
            )

            started = websocket.receive_json()
            error = websocket.receive_json()
            terminal = websocket.receive_json()

    assert started["action"] == "stream_start"
    assert error == {
        "action": "error",
        "message": (
            "O Narrador demorou além do limite; este turno não foi salvo. "
            "Tente novamente."
        ),
        "operation_id": operation_id,
        "terminal": True,
    }
    assert terminal["action"] == "stream_end"
    assert terminal["status"] == "timeout"
    assert terminal["partial"] is False
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    assert adapter.external_call_count == 1

    attempts = _attempts(database_path, session_id)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "timeout"
    assert attempts[0]["error"]["code"] == "operation_deadline_exceeded"
    provenance = json.loads(attempts[0]["provenance_json"])
    assert [
        (row["operation"], row["status"])
        for row in provenance["invocations"]
    ] == [("H6.direct_scene", "timed_out")]


def test_unexpected_turn_execution_failure_is_terminal_safe_and_replayable(
    isolated_websocket_store,
    monkeypatch,
):
    store, database_path = isolated_websocket_store
    session_id = "ws-unexpected-turn-execution"
    operation_id = "op-unexpected-turn-execution"
    envelope = {"operation_id": operation_id, "input": "Eu avanço."}
    runtime, _adapter = _runtime()
    calls: list[str] = []
    sensitive_detail = "provider-prompt-and-secret-must-not-escape"

    async def fail_unexpectedly(*_args, **_kwargs):
        calls.append(operation_id)
        raise RuntimeError(sensitive_detail)

    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main, "prepare_turn_pipeline", _pipeline_stub())
    monkeypatch.setattr(main, "execute_prepared_turn", fail_unexpectedly)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(envelope)

            started = websocket.receive_json()
            error = websocket.receive_json()
            terminal = websocket.receive_json()

            websocket.send_json(envelope)
            replay_error = websocket.receive_json()
            replay_terminal = websocket.receive_json()

    assert started["action"] == "stream_start"
    assert error == {
        "action": "error",
        "message": "A execução do turno falhou; o estado confirmado foi preservado.",
        "operation_id": operation_id,
        "terminal": True,
    }
    assert terminal == {
        "action": "stream_end",
        "operation_id": operation_id,
        "turn_id": f"turn-{operation_id}",
        "status": "failed",
        "partial": False,
    }
    assert (replay_error, replay_terminal) == (error, terminal)
    assert calls == [operation_id]
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)

    attempts = _attempts(database_path, session_id)
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt["status"] == "failed"
    assert attempt["error"] == {
        "category": "application",
        "code": "unexpected_turn_execution_failure",
        "safe_message": (
            "A execução do turno falhou; o estado confirmado foi preservado."
        ),
    }
    metadata = json.loads(attempt["metadata_json"])
    assert metadata == {
        "boundary": "websocket_turn_execution",
        "turn_id": f"turn-{operation_id}",
    }
    safe_audit = json.dumps(
        {
            "error": attempt["error"],
            "metadata": metadata,
            "provenance": attempt["provenance_json"],
            "usage": attempt["usage_json"],
        },
        ensure_ascii=False,
    )
    assert sensitive_detail not in safe_audit
    assert sensitive_detail not in json.dumps(
        [started, error, terminal, replay_error, replay_terminal],
        ensure_ascii=False,
    )

    preserved = asyncio.run(
        main._terminalize_unexpected_claimed_turn(
            session_id=session_id,
            operation_id=operation_id,
            attempt_id=f"attempt-{operation_id}",
            requested_turn=1,
            user_input="Eu avanço.",
            chronicle_name="Teste",
            turn_id=f"turn-{operation_id}",
            store=store,
            status="timeout",
        )
    )
    assert preserved is not None
    assert preserved["status"] == "failed"
    assert preserved["error"]["code"] == "unexpected_turn_execution_failure"


def test_disconnect_during_structured_h6_is_terminally_audited(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-disconnect-after-chunk"
    runtime, base_adapter = _runtime()
    h6_started = threading.Event()

    class BlockingSceneAdapter(FakeLLMAdapter):
        async def _step(self, request, started_at):
            if request.operation == "H6.direct_scene":
                h6_started.set()
                await request.cancellation.wait()
            await super()._step(request, started_at)

    adapter = BlockingSceneAdapter(
        capability_set=base_adapter._capability_set,
        structured_payload=_scene_proposal().model_dump(mode="json"),
    )
    monkeypatch.setattr(
        main,
        "get_llm_runtime",
        lambda: LLMRuntime(target=runtime.target, gateway=adapter),
    )
    monkeypatch.setattr(main, "prepare_turn_pipeline", _pipeline_stub())

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("Eu avanço.")
            assert websocket.receive_json()["action"] == "stream_start"
            assert h6_started.wait(timeout=2)
            websocket.close()

        deadline = time.monotonic() + 3.0
        attempts = _attempts(database_path, session_id)
        while (
            (not attempts or attempts[-1]["status"] == "pending")
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
            attempts = _attempts(database_path, session_id)

    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    assert adapter.external_call_count == 1
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt["status"] == "cancelled"
    assert attempt["partial_narrative"] == ""
    metadata = json.loads(attempt["metadata_json"])
    assert metadata["discarded_output_sha256"] is None
    assert metadata["discarded_output_chars"] == 0
    provenance = json.loads(attempt["provenance_json"])
    assert [
        (row["operation"], row["status"])
        for row in provenance["invocations"]
    ] == [("H6.direct_scene", "cancelled")]


@pytest.mark.parametrize("cancelled_stage", ("h0", "h1"))
def test_disconnect_during_structured_stages_is_terminally_audited(
    isolated_websocket_store,
    monkeypatch,
    cancelled_stage,
):
    monkeypatch.setattr(orchestrator_service.settings, "llm_h0_enabled", True)
    monkeypatch.setattr(orchestrator_service.settings, "llm_h1_enabled", True)
    _store, database_path = isolated_websocket_store
    session_id = f"ws-disconnect-{cancelled_stage}"
    runtime, base_adapter = _runtime()
    stage_started = threading.Event()

    class StagedAdapter(FakeLLMAdapter):
        async def generate_structured(self, request):
            if request.operation == "h0.triage":
                self.structured_payload = {
                    "route": "action",
                    "scene_notes": "",
                    "lore_keywords": [],
                }
            else:
                self.structured_payload = {"intent": "Observar a rua"}
            return await super().generate_structured(request)

        async def _step(self, request, started_at):
            target_operation = (
                "h0.triage"
                if cancelled_stage == "h0"
                else "h1.extract_intent.attempt_1"
            )
            if request.operation == target_operation:
                stage_started.set()
                await request.cancellation.wait()
            await super()._step(request, started_at)

    adapter = StagedAdapter(capability_set=base_adapter._capability_set)
    monkeypatch.setattr(
        main,
        "get_llm_runtime",
        lambda: LLMRuntime(target=runtime.target, gateway=adapter),
    )

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("Observo a rua.")
            assert stage_started.wait(timeout=2)
            websocket.close()

        deadline = time.monotonic() + 3.0
        attempts = _attempts(database_path, session_id)
        while (
            (not attempts or attempts[-1]["status"] == "pending")
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
            attempts = _attempts(database_path, session_id)

    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "cancelled"
    provenance = json.loads(attempts[0]["provenance_json"])
    operations = [
        (row["operation"], row["status"])
        for row in provenance["invocations"]
    ]
    if cancelled_stage == "h0":
        assert operations == [("h0.triage", "cancelled")]
    else:
        assert operations == [
            ("h0.triage", "completed"),
            ("h1.extract_intent.attempt_1", "cancelled"),
        ]


def test_unconfigured_target_is_audited_without_starting_or_advancing_turn(
    isolated_websocket_store,
    monkeypatch,
):
    _store, database_path = isolated_websocket_store
    session_id = "ws-target-missing"

    def target_missing():
        raise LLMRuntimeConfigurationError("Configure um alvo LLM explícito.")

    monkeypatch.setattr(main, "get_llm_runtime", target_missing)

    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_text("Eu avanço.")
            error = websocket.receive_json()

            assert error == {
                "action": "error",
                "message": "Configure um alvo LLM explícito.",
            }
            assert _canonical_counts(database_path, session_id) == (0, 0, 0)

    attempts = _attempts(database_path, session_id)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error"]["code"] == "llm_target_not_configured"


def test_context_budget_failure_is_visible_stored_and_replayed_without_generation(
    isolated_websocket_store, monkeypatch,
):
    from api.orchestrator_service import NarratorContextBudgetError, NARRATOR_CONTEXT_BUDGET_MESSAGE
    _store, database_path = isolated_websocket_store
    runtime, adapter = _runtime()
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    calls = []

    async def over_budget(**kwargs):
        calls.append(kwargs["operation_id"])
        raise NarratorContextBudgetError()

    monkeypatch.setattr(main, "prepare_turn_pipeline", over_budget)
    session_id = "ws-context-budget-failure"
    envelope = {"operation_id": "op-budget", "input": "Cumprimento Lia."}
    with TestClient(main.app) as client:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(envelope)
            error, terminal = websocket.receive_json(), websocket.receive_json()
            assert error["action"] == "error"
            assert error["message"] == NARRATOR_CONTEXT_BUDGET_MESSAGE
            assert terminal["status"] == "failed"
            websocket.send_json(envelope)
            assert websocket.receive_json() == error
            assert websocket.receive_json() == terminal
    assert calls == ["op-budget"]
    assert adapter.external_call_count == 0
    assert _canonical_counts(database_path, session_id) == (0, 0, 0)
    assert _attempts(database_path, session_id)[0]["error"]["code"] == "narrator_context_budget_exceeded"
