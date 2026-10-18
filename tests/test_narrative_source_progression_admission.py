"""Offline admission proof: observed synthetic source plus authored continuation.

The second reply is an authored fixture, never a new Groq observation. These
checks establish admission and retention, not model ability or semantic truth.
"""
from datetime import timedelta
from pathlib import Path
import json
import sqlite3

import pytest

from api import orchestrator_service, rules_service
from api.llm.contract import CancellationToken, GenerationParameters, utc_now
from api.narrative_source_coordinator import (
    prepare_retained_source_turn, execute_retained_source_turn,
)
from api.narrative_source_preparation import DeclaredActionPreparation
from api.persistence import SQLitePersistence
from test_narrative_source_bridge import NOW, SCENE, _gateway


SESSION = "authored-progression-admission"
ACTIONS = ("Observo a galeria sem tocar em nada.", "Aguardo no mesmo lugar sem tocar em nada.")
# Copied literally from synthetic batch 19b93f22, first response; now FakeLLM data.
OBSERVED_FIRST = (
    "O silêncio da galeria parece espesso, quebrado apenas pelo zumbido abafado de um "
    "ar-condicionado distante. Luzes frias e direcionadas caem sobre as superfícies das "
    "obras, criando um jogo de sombras nítidas no piso de mármore polido. Não há movimento "
    "nas molduras; apenas o próprio reflexo seu, distorcido e pálido, acompanha o seu olhar "
    "ao longo da parede. Uma pequena poeira flutua lentamente no feixe de luz central, "
    "um ponto solitário contra a escuridão do canto da sala."
)
OBSERVED_QUESTION = "O que você faz agora?"
# Authored by the independent reviewer: a substantive environmental change with
# an uncertain cause; no action, thought, emotion or mechanical result for the PC.
AUTHORED_CONTINUATION = (
    "O zumbido do ar-condicionado se interrompe. Por um instante, a luz central enfraquece, "
    "e a partícula de poeira desaparece no escuro. Quando o feixe retorna, pulsa duas vezes; "
    "seu brilho descontínuo recorta as molduras e faz o reflexo no mármore surgir e sumir. "
    "O ar-condicionado continua silencioso. Após uma pausa, as duas pulsações se repetem, "
    "enquanto o restante da galeria conserva a iluminação fria. A causa dessas pulsações "
    "permanece incerta."
)
AUTHORED_QUESTION = "O que você faz diante dessas pulsações?"
PROMPT = Path(__file__).resolve().parents[1] / "evals/narrator/prompts/narrative-source-progress-v1.md"
SYSTEM = PROMPT.read_text(encoding="utf-8").split("---", 2)[2].strip()


@pytest.fixture(autouse=True)
def forbid_unrelated_producers(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline source admission entered a legacy producer or RNG")
    for name in ("prepare_turn_pipeline", "_restore_narrator_context_items", "_assemble_narrator_context"):
        monkeypatch.setattr(orchestrator_service, name, forbidden)
    monkeypatch.setattr(rules_service.random, "randint", forbidden)


async def new_store(tmp_path):
    store = SQLitePersistence(tmp_path / "authored-progression.sqlite3")
    await store.create_narrative_source_campaign(
        SESSION, initial_scene=SCENE, initial_state={}, relationships={},
    )
    return store


async def turn(store, index, text, question):
    target, gateway = _gateway(text, question)
    operation = f"authored-{index}"
    capsule = await prepare_retained_source_turn(
        session_id=SESSION, operation_id=operation, created_at=NOW,
        player_input=ACTIONS[index - 1], preparation=DeclaredActionPreparation(),
        state={}, relationships={}, store=store, target=target, system_prompt=SYSTEM,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
    )
    chunks = []
    async def collect(value): chunks.append(value)
    result = await execute_retained_source_turn(
        session_id=SESSION, operation_id=operation, store=store, gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert len(gateway.requests) == 1
    assert gateway.requests[0].messages[0].content == SYSTEM
    return capsule, result, gateway, chunks


async def replay(store, index):
    class NoCall:
        def __getattr__(self, name):
            pytest.fail("Replay accessed the gateway")
    async def no_chunk(value):
        pytest.fail("Replay delivered a new chunk")
    return await execute_retained_source_turn(
        session_id=SESSION, operation_id=f"authored-{index}", store=store,
        gateway=NoCall(), deadline=NOW, cancellation=CancellationToken(), on_chunk=no_chunk,
    )


async def assert_canonical_unchanged(store, initial, count):
    snapshot = await store.read_source_context_snapshot(SESSION)
    assert snapshot.current_turn == snapshot.state_revision == count
    assert snapshot.canonical_scene == SCENE and snapshot.canonical_scene.last_turn == 0
    campaign = await store.load_campaign(SESSION)
    for key in ("state", "relationships", "metadata"):
        assert campaign[key] == initial[key]
    with sqlite3.connect(store.db_path) as connection:
        facts = connection.execute("SELECT facts_json FROM turns ORDER BY turn_number").fetchall()
        events = connection.execute("SELECT event_type FROM events ORDER BY turn_number").fetchall()
        assert len(facts) == count
        assert events == [("player_action_declared",)] * count
        for index, (encoded,) in enumerate(facts):
            decoded = json.loads(encoded)
            assert len(decoded) == 1 and decoded[0]["fact_type"] == "action.declaration"
            assert decoded[0]["value"]["player_input"] == ACTIONS[index]
            assert decoded[0]["value"]["requires_roll"] is False
        for table in ("memory_candidates", "episodic_memories"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    return snapshot


@pytest.mark.anyio
async def test_authored_progression_commits_and_remains_an_integral_source(tmp_path):
    store = await new_store(tmp_path)
    initial = await store.load_campaign(SESSION)
    _, first, _, first_chunks = await turn(store, 1, OBSERVED_FIRST, OBSERVED_QUESTION)
    assert first.status == "completed", first.error
    second_capsule, second, gateway, chunks = await turn(
        SQLitePersistence(store.db_path), 2, AUTHORED_CONTINUATION, AUTHORED_QUESTION,
    )
    assert second.status == "completed", second.error
    assert first_chunks == [OBSERVED_FIRST + "\n\n" + OBSERVED_QUESTION]
    assert chunks == [AUTHORED_CONTINUATION + "\n\n" + AUTHORED_QUESTION]
    packet = json.loads(gateway.requests[0].messages[1].content)
    assert packet["player_input"] == ACTIONS[1]
    assert packet["context"]["attributed_sources"] == [first.envelope.projection.model_dump(mode="json")]
    assert packet["context"]["attributed_sources"][0]["text"] == OBSERVED_FIRST
    assert packet["server_facts"] == [fact.model_dump(mode="json") for fact in second_capsule.draft.facts]
    restarted = SQLitePersistence(store.db_path)
    snapshot = await assert_canonical_unchanged(restarted, initial, 2)
    assert snapshot.sources == (first.envelope, second.envelope)
    assert tuple(source.projection.text for source in snapshot.sources) == (OBSERVED_FIRST, AUTHORED_CONTINUATION)
    for source in snapshot.sources:
        assert source.projection.source.text == source.projection.text
        assert source.projection.assessment.decision.value == "source_only"
        assert source.projection.assessment.semantic_status == "not_assessed"
    for index, original in enumerate((first, second), 1):
        repeated = await replay(restarted, index)
        assert repeated.status == "completed" and repeated.envelope == original.envelope
        assert repeated.narrative == original.narrative
    assert await restarted.read_source_context_snapshot(SESSION) == snapshot


@pytest.mark.anyio
@pytest.mark.parametrize("prefix,code", [
    pytest.param("Você toca uma das molduras. ", "scene_player_agency_violation", id="forced-action"),
    pytest.param("Você sente-se apavorado. ", "scene_player_agency_violation", id="forced-emotion"),
    # Existing technical-content barrier; not a general invented-resource detector.
    pytest.param("O pool de dados aumenta para oito. ", "scene_internal_content", id="internal-mechanics"),
])
async def test_rejected_authored_continuation_never_commits_or_becomes_source(tmp_path, prefix, code):
    store = await new_store(tmp_path)
    initial = await store.load_campaign(SESSION)
    _, first, _, _ = await turn(store, 1, OBSERVED_FIRST, OBSERVED_QUESTION)
    assert first.status == "completed", first.error
    _, rejected, gateway, chunks = await turn(store, 2, prefix + AUTHORED_CONTINUATION, AUTHORED_QUESTION)
    assert rejected.status == "failed" and rejected.error["code"] == code
    assert rejected.error["stage"] == "policy"
    assert rejected.envelope is None and chunks == []
    assert await store.load_turn_by_operation(SESSION, "authored-2") is None
    snapshot = await assert_canonical_unchanged(store, initial, 1)
    assert snapshot.sources == (first.envelope,)
    terminal = await replay(SQLitePersistence(store.db_path), 2)
    assert terminal.status == "failed" and terminal.error["code"] == "source_turn_operation_terminal"
    assert len(gateway.requests) == 1
    assert await store.read_source_context_snapshot(SESSION) == snapshot
