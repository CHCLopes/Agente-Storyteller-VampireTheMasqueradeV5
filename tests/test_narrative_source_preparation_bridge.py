"""Real local rules -> server preparation -> B bridge; no runtime classifiers."""
from datetime import timedelta
import json
import sqlite3

import pytest

from api import orchestrator_service, rules_service
from api.llm.contract import CancellationToken, GenerationParameters, utc_now
from api.narrative_source_context import SELECTION_KEY
from api.narrative_source_execution_service import execute_source_turn
from api.narrative_source_preparation import (
    DeclaredActionPreparation, ResolvedActionPreparation, prepare_source_turn_draft,
)
from api.persistence import SQLitePersistence
from api.rules_service import V5ActionPayload, V5Attribute, V5Skill
from test_narrative_source_bridge import FIRST, SECOND, QUESTION, SCENE, NOW, SYSTEM, _gateway


SESSION = "prepared-source-session"
DECLARATION = "Observo a galeria sem tocar em nada."
INVESTIGATION = "Examino os detalhes da galeria."


# Separate authored positives; FIRST remains the original neutral negative control.
INVESTIGATION_SUCCESS = (
    "O exame da galeria identifica uma marca retangular na poeira da prateleira inferior. "
    "No centro dessa marca, a madeira está mais clara, cercada por partículas acumuladas "
    "nas bordas. A diferença permanece visível sob a luz que atravessa a janela, e um "
    "pequeno fragmento de papel repousa junto ao canto esquerdo. A chuva continua soando "
    "do lado de fora."
)
INVESTIGATION_FAILURE = (
    "O exame da galeria falha em distinguir um padrão conclusivo entre as marcas da poeira. "
    "A iluminação irregular e as manchas antigas se sobrepõem na prateleira inferior, "
    "deixando o detalhe incerto. O fragmento de papel junto à borda continua dobrado, "
    "sem informação legível nesta observação. A chuva persiste além da janela e o rangido "
    "discreto da madeira interrompe o silêncio."
)


@pytest.fixture(autouse=True)
def forbid_legacy_paths(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A preparação B entrou em RNG, classificador ou leitor legado inesperado")
    for name in ("prepare_turn_pipeline", "_restore_narrator_context_items", "_assemble_narrator_context"):
        monkeypatch.setattr(orchestrator_service, name, forbidden)
    for name in ("load_or_migrate_campaign", "get_recent_narrative_source_turns", "list_latest_turns",
                 "list_events", "list_memory_candidates", "list_episodic_memories",
                 "list_consolidations", "list_legacy_imports"):
        monkeypatch.setattr(SQLitePersistence, name, forbidden)
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    return forbidden


async def store_and_snapshot(tmp_path):
    store = SQLitePersistence(tmp_path / "prepared-source.sqlite3")
    await store.create_narrative_source_campaign(SESSION, initial_scene=SCENE,
                                                initial_state={"counter": 0}, relationships={})
    return store, await store.read_source_context_snapshot(SESSION)


def resolve_investigation(monkeypatch, forbidden, *, success):
    action = V5ActionPayload(intent=INVESTIGATION, attribute=V5Attribute.Intelligence,
                             skill=V5Skill.INVESTIGATION, is_aggressive=False, inferred_difficulty=3)
    values = (8, 7, 3, 5, 6) if success else (2, 3, 4, 5, 2)
    rolls = iter(values)
    calls = []
    def controlled(low, high):
        assert (low, high) == (1, 10)
        value = next(rolls)
        calls.append(value)
        return value
    monkeypatch.setattr(rules_service.random, "randint", controlled)
    receipt = rules_service.calculate_resolution(action, current_hunger=1, dice_pool=5)
    assert calls == list(values)
    assert receipt.is_success is success
    assert receipt.successes == (3 if success else 0)
    assert receipt.margin == (0 if success else -3)
    assert receipt.normal_rolls == list(values[:4]) and receipt.hunger_rolls == [values[4]]
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    monkeypatch.setattr(rules_service, "calculate_resolution", forbidden)
    return action, receipt, calls


async def execute(store, draft, operation_id, *, gateway=None, text=FIRST, question=QUESTION):
    target, fresh = _gateway(text, question)
    gateway = gateway or fresh
    chunks = []
    async def collect(value): chunks.append(value)
    result = await execute_source_turn(
        draft=draft, operation_id=operation_id, current_scene=SCENE,
        state={"counter": draft.base_revision + 1}, relationships={}, context={},
        store=store, gateway=gateway, target=target, system_prompt=SYSTEM,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=collect,
    )
    assert all(request.operation == "H6.narrative_source" for request in gateway.requests)
    return result, gateway, chunks


def assert_no_derived_memory(store):
    with sqlite3.connect(store.db_path) as connection:
        for table in ("memory_candidates", "episodic_memories", "consolidations"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def assert_receipt(value, receipt, *, success):
    raw = receipt.model_dump(mode="json")
    assert {key: value[key] for key in raw} == raw
    assert value["outcome"] == ("success" if success else "failure")
    assert (value["attribute"], value["skill"], value["dice_pool"], value["hunger_dice"], value["difficulty"]) == (
        "Intelligence", "Investigation", 5, 1, 3)


@pytest.mark.anyio
async def test_declared_preparation_commits_without_rng_or_mechanical_resolution(tmp_path):
    store, snapshot = await store_and_snapshot(tmp_path)
    draft = prepare_source_turn_draft(snapshot, operation_id="declared", created_at=NOW,
                                     player_input=DECLARATION, preparation=DeclaredActionPreparation())
    assert draft.base_revision == snapshot.current_turn == 0
    assert draft.base_state_revision == snapshot.state_revision == 0
    assert [fact.fact_type for fact in draft.facts] == ["action.declaration"]
    assert draft.facts[0].value["requires_roll"] is False
    assert draft.facts[0].value["player_input"] == DECLARATION
    assert [event.event_type for event in draft.events] == ["player_action_declared"]
    result, gateway, chunks = await execute(store, draft, "declared")
    assert result.status == "completed", result.error
    assert len(gateway.requests) == 1 and chunks == [FIRST + "\n\n" + QUESTION]
    stored = await store.load_turn_by_operation(SESSION, "declared")
    assert stored["context"][SELECTION_KEY] == snapshot.audit_payload()
    assert stored["facts"] == [item.model_dump(mode="json") for item in draft.facts]
    assert result.envelope.projection.text == FIRST and len(FIRST) > 600
    assert_no_derived_memory(store)


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_neutral_narrative_cannot_claim_real_ordinary_resolution(
    tmp_path, monkeypatch, forbid_legacy_paths, success,
):
    store, snapshot = await store_and_snapshot(tmp_path)
    action, receipt, rng_calls = resolve_investigation(monkeypatch, forbid_legacy_paths, success=success)
    draft = prepare_source_turn_draft(snapshot, operation_id="neutral", created_at=NOW,
                                     player_input=INVESTIGATION,
                                     preparation=ResolvedActionPreparation(action=action, resolution=receipt))
    result, gateway, chunks = await execute(store, draft, "neutral", text=FIRST)
    assert result.status == "failed" and result.envelope is None and not chunks
    assert result.error["code"] == ("scene_success_not_honored" if success else "scene_failure_not_honored")
    assert len(gateway.requests) == 1 and len(rng_calls) == 5
    assert_receipt(draft.facts[0].value, receipt, success=success)
    assert_receipt(json.loads(gateway.requests[0].messages[1].content)["server_facts"][0]["value"], receipt, success=success)
    assert (await store.read_source_context_snapshot(SESSION)).audit_payload() == snapshot.audit_payload()
    assert await store.load_turn_by_operation(SESSION, "neutral") is None
    assert_no_derived_memory(store)


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_authored_investigation_honors_ordinary_resolution_and_replays(
    tmp_path, monkeypatch, forbid_legacy_paths, success,
):
    store, snapshot = await store_and_snapshot(tmp_path)
    action, receipt, rng_calls = resolve_investigation(monkeypatch, forbid_legacy_paths, success=success)
    preparation = ResolvedActionPreparation(action=action, resolution=receipt)
    draft = prepare_source_turn_draft(snapshot, operation_id="investigate", created_at=NOW,
                                     player_input=INVESTIGATION, preparation=preparation)
    assert prepare_source_turn_draft(snapshot, operation_id="investigate", created_at=NOW,
                                    player_input=INVESTIGATION, preparation=preparation) == draft
    assert [fact.fact_type for fact in draft.facts] == ["mechanics.resolution"]
    assert [event.event_type for event in draft.events] == ["player_action_resolved"]
    assert_receipt(draft.facts[0].value, receipt, success=success)
    text = INVESTIGATION_SUCCESS if success else INVESTIGATION_FAILURE
    result, gateway, chunks = await execute(store, draft, "investigate", text=text)
    assert result.status == "completed", result.error
    assert chunks == [text + "\n\n" + QUESTION] and len(rng_calls) == 5
    user = json.loads(gateway.requests[0].messages[1].content)
    assert_receipt(user["server_facts"][0]["value"], receipt, success=success)
    stored = await store.load_turn_by_operation(SESSION, "investigate")
    assert_receipt(stored["facts"][0]["value"], receipt, success=success)
    assert stored["context"][SELECTION_KEY] == snapshot.audit_payload()
    assert result.envelope.projection.text == text
    restarted = SQLitePersistence(store.db_path)
    repeated, gateway, chunks = await execute(restarted, draft, "investigate", gateway=gateway)
    assert repeated.status == "completed" and repeated.envelope == result.envelope
    assert len(gateway.requests) == 1 and chunks == [] and len(rng_calls) == 5
    assert_no_derived_memory(store)


@pytest.mark.anyio
async def test_narrative_rejection_and_terminal_replay_do_not_reroll_or_commit_receipt(
    tmp_path, monkeypatch, forbid_legacy_paths,
):
    store, snapshot = await store_and_snapshot(tmp_path)
    action, receipt, rng_calls = resolve_investigation(monkeypatch, forbid_legacy_paths, success=False)
    draft = prepare_source_turn_draft(snapshot, operation_id="rejected", created_at=NOW,
                                     player_input=INVESTIGATION,
                                     preparation=ResolvedActionPreparation(action=action, resolution=receipt))
    before = draft.model_dump(mode="json")
    result, gateway, chunks = await execute(store, draft, "rejected", question="Qual é a cor da janela?")
    assert result.status == "failed" and result.envelope is None and not chunks
    assert_receipt(json.loads(gateway.requests[0].messages[1].content)["server_facts"][0]["value"], receipt, success=False)
    repeated, gateway, chunks = await execute(store, draft, "rejected", gateway=gateway)
    assert repeated.status == "failed" and repeated.error["code"] == "source_turn_operation_terminal"
    assert len(gateway.requests) == 1 and not chunks and len(rng_calls) == 5
    assert draft.model_dump(mode="json") == before
    assert (await store.read_source_context_snapshot(SESSION)).audit_payload() == snapshot.audit_payload()
    assert (await store.load_attempt_by_operation(SESSION, "rejected"))["status"] == "failed"
    assert await store.load_turn_by_operation(SESSION, "rejected") is None
    with sqlite3.connect(store.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    assert_no_derived_memory(store)


@pytest.mark.anyio
async def test_preparation_after_restart_keeps_previous_source_whole_and_server_receipt(
    tmp_path, monkeypatch, forbid_legacy_paths,
):
    store, initial = await store_and_snapshot(tmp_path)
    declaration = prepare_source_turn_draft(initial, operation_id="first", created_at=NOW,
                                           player_input=DECLARATION, preparation=DeclaredActionPreparation())
    first, _, _ = await execute(store, declaration, "first")
    assert first.status == "completed", first.error
    restarted = SQLitePersistence(store.db_path)
    snapshot = await restarted.read_source_context_snapshot(SESSION)
    assert snapshot.current_turn == snapshot.state_revision == 1
    assert snapshot.sources[0].projection.text == FIRST
    action, receipt, _ = resolve_investigation(monkeypatch, forbid_legacy_paths, success=True)
    investigation = prepare_source_turn_draft(snapshot, operation_id="second", created_at=NOW,
                                             player_input=INVESTIGATION,
                                             preparation=ResolvedActionPreparation(action=action, resolution=receipt))
    assert investigation.base_revision == investigation.base_state_revision == 1
    second, gateway, chunks = await execute(restarted, investigation, "second", text=SECOND)
    assert second.status == "completed", second.error
    assert chunks == [SECOND + "\n\n" + QUESTION]
    user = json.loads(gateway.requests[0].messages[1].content)
    assert [source["text"] for source in user["context"]["attributed_sources"]] == [FIRST]
    assert QUESTION not in gateway.requests[0].messages[1].content
    assert_receipt(user["server_facts"][0]["value"], receipt, success=True)
    stored = await restarted.load_turn_by_operation(SESSION, "second")
    assert stored["context"][SELECTION_KEY] == snapshot.audit_payload()
    assert [source.projection.text for source in (await restarted.read_source_context_snapshot(SESSION)).sources] == [FIRST, SECOND]
    assert_no_derived_memory(store)
