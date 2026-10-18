"""Local source-only turn proofs; all generated replies are authored fixtures."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import sqlite3
import json
import random

import pytest

from api import narrative_source_profile as profile
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor, CapabilitySet, CapabilitySupport,
    ErrorCategory, GenerationParameters, LLMTarget, utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.narrative_source_execution_service import SourceTurnExecutionError, execute_source_turn
from api.persistence import SQLitePersistence
from api.scene_service import SceneState
from api.turn_models import CanonicalEvent, CanonicalFact, RecordReference, TurnDraft
from scripts import narrator_source_profile as experimental


SCENE = SceneState(location="Galeria", npcs_present=())
QUESTION = "O que você faz agora?"
FIRST = (
    "A iluminação esverdeada atravessa as janelas estreitas da galeria, espalhando reflexos "
    "irregulares sobre os ladrilhos antigos. A madeira das prateleiras apresenta pequenas "
    "rachaduras, enquanto fragmentos de papel amarelado repousam entre recipientes de cerâmica "
    "cuidadosamente alinhados. Perto da janela entreaberta, uma cortina comprida oscila lentamente "
    "com a corrente de ar. O cheiro de papel envelhecido mistura-se à umidade que chega do "
    "pátio exterior. Um intervalo de silêncio permite distinguir o ruído suave da chuva distante, "
    "seguido pelo rangido discreto de uma dobradiça. Uma gota escorre pela borda inferior da "
    "vidraça e desaparece numa pequena fissura da moldura."
)
SECOND = (
    "A cortina da galeria continua oscilando diante da janela entreaberta. Outra gota percorre "
    "a vidraça e alcança a fissura da moldura. O rangido da dobradiça diminui, enquanto o ruído "
    "da chuva distante fica mais nítido. Os papéis amarelados permanecem entre os recipientes "
    "de cerâmica, sob os reflexos esverdeados que atravessam os ladrilhos."
)
THIRD = (
    "O movimento da cortina abranda quando a corrente de ar perde força. A chuva permanece "
    "audível além da janela entreaberta, e novas gotas se acumulam sobre a borda da vidraça. "
    "As prateleiras, os recipientes e os fragmentos de papel continuam sob a iluminação "
    "esverdeada, enquanto a dobradiça deixa de ranger por um instante."
)
NOW = datetime(2026, 9, 7, 22, 0, tzinfo=timezone.utc)
SYSTEM = "Fixture local: narre em português brasileiro com n e q, preservando fonte e agência."


def _draft(index=1, session="source-bridge"):
    action = "Observo a galeria sem tocar em nada." if index == 1 else "Permaneço no lugar e aguardo, sem tocar em nada."
    fact = CanonicalFact(
        fact_id=f"declaration-{session}-{index}", fact_type="action.declaration",
        predicate="declared_player_action", value={"player_input": action, "requires_roll": False,
                                                    "summary": "Ação declarada sem teste."},
        occurred_at=NOW,
        source_refs=(RecordReference(record_id="orchestrator.local_action_classification",
                                     record_type="deterministic_module", relation="produced_by"),),
    )
    turn_id = f"turn-{session}-{index}"
    event = CanonicalEvent(
        event_id=f"event-{session}-{index}", session_id=session, turn_id=turn_id, sequence=0,
        event_type="player_action_declared", occurred_at=NOW,
        summary=f"Ação narrativa declarada pelo jogador: {action}", fact_ids=(fact.fact_id,),
    )
    return TurnDraft(
        draft_id=f"draft-{session}-{index}", session_id=session, turn_id=turn_id,
        attempt_id=f"attempt-{session}-{index}", player_input=action, created_at=NOW,
        base_revision=index-1, base_state_revision=index-1, facts=(fact,), events=(event,),
    )


def _gateway(n=FIRST, q=QUESTION, **kwargs):
    target = LLMTarget(profile="source-bridge-test", provider="fake", model="synthetic")
    caps = CapabilitySet(target=target, descriptors=tuple(
        CapabilityDescriptor(name=name, support=CapabilitySupport.NATIVE)
        for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)
    ))
    return target, FakeLLMAdapter(capability_set=caps, structured_payload={"n": n, "q": q}, **kwargs)


async def _run(store, *, index=1, session="source-bridge", n=FIRST, q=QUESTION,
               gateway=None, callback=None, **overrides):
    target, default = _gateway(n, q)
    gateway = gateway or default
    chunks = []
    async def collect(text): chunks.append(text)
    args = dict(
        draft=_draft(index, session), operation_id=f"operation-{session}-{index}",
        current_scene=SCENE, state={"counter": index}, relationships={}, context={},
        store=store, gateway=gateway, target=target, system_prompt=SYSTEM,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=callback or collect,
    )
    args.update(overrides)
    result = await execute_source_turn(**args)
    return result, gateway, chunks


async def _store(tmp_path, session="source-bridge"):
    store = SQLitePersistence(tmp_path / "source-only.sqlite3")
    await store.create_narrative_source_campaign(
        session, initial_scene=SCENE, initial_state={"counter": 0}, relationships={},
    )
    return store


def test_application_schema_keeps_nq_contract_but_has_distinct_source_policy():
    assert profile.NarrativeSourceProposal.model_json_schema() == experimental.NarrativeSourceProposal.model_json_schema()
    assert profile.VERSION != experimental.VERSION
    assert profile.CONTEXT_PROTOCOL != experimental.CONTEXT_PROTOCOL
    foreign = experimental.create_source_projection(
        {"n": FIRST, "q": QUESTION}, source_id="experiment", session_id="source-bridge",
        turn_id="old-turn", invocation_id="old-call", current_scene=SCENE, facts=(),
        player_input="Observo a galeria.",
    )
    with pytest.raises(profile.SourceProfileError, match="context_mismatch"):
        profile.build_source_context(session_id="source-bridge", current_scene=SCENE,
                                     attributed_sources=(foreign,))


@pytest.mark.anyio
async def test_three_local_turns_restart_and_full_sources_never_become_canonical_memory(tmp_path, monkeypatch):
    store = await _store(tmp_path)
    monkeypatch.setattr(random, "randint", lambda *args: pytest.fail("Source bridge rerolled"))
    originals = [FIRST, SECOND, THIRD]
    assert 600 < len(FIRST) <= 1600
    envelopes = []
    for index, text in enumerate(originals, 1):
        # Every public operation opens/closes its own SQLite connection; fresh
        # persistence instances also eliminate an accidental in-memory source cache.
        if index > 1: store = SQLitePersistence(tmp_path / "source-only.sqlite3")
        result, gateway, chunks = await _run(store, index=index, n=text)
        assert result.status == "completed", result.error
        assert chunks == [text + "\n\n" + QUESTION]
        assert len(gateway.requests) == 1
        request = gateway.requests[0]
        user = json.loads(request.messages[1].content)
        carried = user["context"]["attributed_sources"]
        assert [source["text"] for source in carried] == originals[:index-1]
        assert QUESTION not in request.messages[1].content
        assert "CONHECIDO" not in request.messages[1].content
        assert user["context"]["canonical_scene"] == {"location": "Galeria", "npcs_present": []}
        assert user["context"]["metadata"]["semantic_truth_assessed"] is False
        assert result.envelope.projection.text == text
        assert result.envelope.question == QUESTION
        assert result.envelope.projection.source.source_policy == profile.VERSION
        envelopes.append(result.envelope)
        stored = await store.load_turn_by_operation("source-bridge", f"operation-source-bridge-{index}")
        assert stored["context"]["narrative_source"] == result.envelope.model_dump(mode="json")
        assert len(stored["facts"]) == 1 and stored["facts"][0]["fact_type"] == "action.declaration"
        assert stored["state"] == {"counter": index}
        assert all(text not in json.dumps(item, ensure_ascii=False) for item in stored["facts"])
        assert stored["narrative"]["text"] == text+"\n\n"+QUESTION
        assert not await store.list_memory_candidates("source-bridge")
        assert not await store.list_episodic_memories("source-bridge")
    restored = await store.get_recent_narrative_source_turns("source-bridge")
    assert [item.projection.text for item in restored] == [SECOND, THIRD]
    assert len(await store.list_turns("source-bridge")) == 3
    assert (await store.load_campaign("source-bridge"))["current_turn"] == 3


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["schema", "agency", "secret", "length", "question"])
async def test_policy_failures_deliver_no_chunk_or_source_and_preserve_snapshot(tmp_path, kind):
    store = await _store(tmp_path)
    before = await store.load_campaign("source-bridge")
    n = ("Você decide abrir a janela. " + FIRST) if kind == "agency" else (
        "A senha reservada é alvorada escarlate. " + FIRST) if kind == "secret" else (
        " ".join([FIRST] * 3)) if kind == "length" else FIRST
    q = "Qual é a cor da janela?" if kind == "question" else QUESTION
    target, gateway = _gateway(n, q)
    if kind == "schema": gateway.structured_payload = {"n": FIRST, "q": QUESTION, "s": "extra"}
    result, gateway, chunks = await _run(store, gateway=gateway,
                                        protected_secrets=("alvorada escarlate",))
    assert result.status == "failed" and result.narrative is None and result.envelope is None
    assert len(gateway.requests) == 1 and chunks == []
    assert not await store.list_turns("source-bridge")
    assert not await store.get_recent_narrative_source_turns("source-bridge")
    after = await store.load_campaign("source-bridge")
    for key in ("state", "relationships", "current_turn", "state_revision"):
        assert after[key] == before[key]
    attempt = await store.load_attempt_by_operation("source-bridge", "operation-source-bridge-1")
    assert attempt["status"] == "failed"
    assert "alvorada escarlate" not in json.dumps(result.error, ensure_ascii=False)


@pytest.mark.anyio
@pytest.mark.parametrize("scene", [None, SceneState(location="Galeria", summary="Resumo v1 não avaliado.")])
async def test_incompatible_scene_rejected_before_generation(tmp_path, scene):
    store = await _store(tmp_path)
    result, gateway, chunks = await _run(store, current_scene=scene)
    assert result.status == "failed" and not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_success_replay_with_original_draft_does_not_generate_or_deliver_again(tmp_path):
    store = await _store(tmp_path)
    first, gateway, chunks = await _run(store)
    assert first.status == "completed", first.error
    second, gateway, repeated_chunks = await _run(store, gateway=gateway,
                                                 deadline=utc_now()-timedelta(seconds=1))
    assert second.status == "completed", second.error
    assert second.envelope == first.envelope and second.narrative == first.narrative
    assert len(gateway.requests) == 1 and repeated_chunks == []
    assert len(await store.list_turns("source-bridge")) == 1


@pytest.mark.anyio
async def test_changed_static_request_cannot_replay_completed_operation(tmp_path):
    store = await _store(tmp_path)
    first, gateway, _ = await _run(store)
    assert first.status == "completed", first.error
    second, gateway, chunks = await _run(store, gateway=gateway, state={"counter": 888})
    assert second.status == "failed" and second.envelope is None
    assert len(gateway.requests) == 1 and not chunks
    assert (await store.load_campaign("source-bridge"))["state"] == {"counter": 1}


@pytest.mark.anyio
@pytest.mark.parametrize("after_delivery", ["callback", "cancellation", "cas"])
async def test_delivery_remains_provisional_until_commit_and_no_source_survives_failure(tmp_path, after_delivery):
    store = await _store(tmp_path)
    token = CancellationToken()
    chunks = []
    async def callback(text):
        chunks.append(text)
        assert not await store.list_turns("source-bridge")
        if after_delivery == "callback": raise RuntimeError("private transport diagnostic")
        if after_delivery == "cancellation": token.cancel("synthetic cancellation")
        if after_delivery == "cas":
            await store.update_campaign_snapshot("source-bridge", state={"counter": 73},
                                               expected_revision=0, expected_turn=0)
    result, gateway, _ = await _run(store, callback=callback, cancellation=token)
    assert result.status in {"failed", "cancelled"} and result.envelope is None
    assert len(chunks) == len(gateway.requests) == 1
    assert not await store.list_turns("source-bridge")
    assert not await store.get_recent_narrative_source_turns("source-bridge")
    campaign = await store.load_campaign("source-bridge")
    assert campaign["current_turn"] == 0
    assert campaign["state"] == {"counter": 73 if after_delivery == "cas" else 0}
    assert "private transport diagnostic" not in json.dumps(result.error)


@pytest.mark.anyio
async def test_caller_mutation_during_callback_does_not_modify_frozen_aggregate(tmp_path):
    store = await _store(tmp_path)
    state = {"counter": 1}; context = {}; relationships = {}
    async def callback(text):
        state["counter"] = 999
        context["narrative_source"] = {"projection": "forged"}
        relationships["unexpected"] = True
    result, _, _ = await _run(store, callback=callback, state=state, context=context, relationships=relationships)
    assert result.status == "completed", result.error
    stored = await store.load_turn_by_operation("source-bridge", "operation-source-bridge-1")
    assert stored["state"] == {"counter": 1} and stored["relationships"] == {}
    assert stored["context"]["narrative_source"] == result.envelope.model_dump(mode="json")


@pytest.mark.anyio
async def test_provider_failure_is_terminal_without_hidden_second_call(tmp_path):
    store = await _store(tmp_path)
    _, gateway = _gateway(failure_category=ErrorCategory.PROVIDER_UNAVAILABLE)
    first, _, chunks = await _run(store, gateway=gateway)
    second, _, more = await _run(store, gateway=gateway)
    assert first.status == second.status == "failed"
    assert len(gateway.requests) == 1 and not chunks and not more
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_unassessed_legacy_context_cannot_be_silently_dropped_before_generation(tmp_path):
    store = await _store(tmp_path)
    result, gateway, chunks = await _run(store, context={"legacy_summary": "Texto histórico sem avaliação B."})
    assert result.status == "failed" and not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_server_invocation_identity_is_unambiguous_when_identifiers_contain_colons(tmp_path):
    store = await _store(tmp_path, session="one:two")
    await store.create_narrative_source_campaign("one", initial_scene=SCENE, initial_state={"counter": 0})
    first, _, _ = await _run(store, session="one:two", operation_id="three")
    second, _, _ = await _run(store, session="one", operation_id="two:three")
    assert first.status == second.status == "completed", (first.error, second.error)
    assert first.envelope.projection.source.invocation_id != second.envelope.projection.source.invocation_id


@pytest.mark.anyio
@pytest.mark.parametrize("oversize", ["player_input", "server_fact"])
async def test_complete_user_budget_rejects_before_provider_without_clipping(tmp_path, oversize):
    store = await _store(tmp_path)
    raw = _draft().model_dump(mode="json")
    if oversize == "player_input": raw["player_input"] = "x" * 12001
    else: raw["facts"][0]["value"] = {"summary": "x" * 12001}
    draft = TurnDraft.model_validate(raw)
    result, gateway, chunks = await _run(store, draft=draft)
    assert result.status == "failed" and not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
@pytest.mark.parametrize("unsupported", ["fact", "event"])
async def test_unsupported_antecedents_are_rejected_before_generation(tmp_path, unsupported):
    store = await _store(tmp_path)
    raw = _draft().model_dump(mode="json")
    if unsupported == "fact": raw["facts"][0]["fact_type"] = "world.scene"
    else: raw["events"][0]["event_type"] = "player_scene_query"
    result, gateway, chunks = await _run(store, draft=TurnDraft.model_validate(raw))
    assert result.status == "failed" and not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_mechanical_failure_cannot_be_rewritten_as_success_before_delivery(tmp_path):
    store = await _store(tmp_path)
    raw = _draft().model_dump(mode="json")
    raw["facts"][0].update(fact_type="mechanics.resolution", predicate="resolved_player_action",
                           value={"is_success": False})
    raw["events"][0]["event_type"] = "player_action_resolved"
    raw["events"][0]["summary"] = "A tentativa de abrir a porta falhou."
    raw["player_input"] = "Abro a porta."
    result, gateway, chunks = await _run(
        store, draft=TurnDraft.model_validate(raw), n="A porta cede e revela a sala. " + SECOND)
    assert result.status == "failed" and result.error["code"] == "scene_failure_not_honored"
    assert len(gateway.requests) == 1 and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_same_operation_name_in_different_sessions_has_distinct_source_identities(tmp_path):
    store = await _store(tmp_path, session="first-session")
    await store.create_narrative_source_campaign("second-session", initial_scene=SCENE, initial_state={"counter": 0})
    first, _, _ = await _run(store, session="first-session", operation_id="same-operation")
    second, _, _ = await _run(store, session="second-session", operation_id="same-operation")
    assert first.status == second.status == "completed", (first.error, second.error)
    assert first.narrative.narrative_id != second.narrative.narrative_id
    assert first.envelope.projection.source.invocation_id != second.envelope.projection.source.invocation_id


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["committed_turn", "attempt_provenance", "presentation", "literal_id"])
async def test_completed_replay_rejects_corrupt_pair_without_another_call(tmp_path, mutation):
    store = await _store(tmp_path)
    first, gateway, _ = await _run(store)
    assert first.status == "completed", first.error
    with sqlite3.connect(store.db_path) as connection:
        if mutation == "committed_turn":
            # Corruption fixture bypasses FK checks only in this temporary database.
            connection.execute("UPDATE attempts SET committed_turn_id=?", ("foreign-turn",))
        elif mutation == "attempt_provenance":
            connection.execute("UPDATE attempts SET provenance_json=?", ('{}',))
        elif mutation == "presentation":
            connection.execute("UPDATE turns SET narrative_text=?", ("Changed presentation",))
        else:
            raw = json.loads(connection.execute("SELECT narrative_json FROM turns").fetchone()[0])
            raw["session_id"] = " source-bridge "
            connection.execute("UPDATE turns SET narrative_json=?", (json.dumps(raw),))
    with pytest.raises(SourceTurnExecutionError, match="source_turn_replay_invalid"):
        await _run(store, gateway=gateway)
    assert len(gateway.requests) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("commit_wins", [True, False])
async def test_task_cancellation_waits_for_commit_outcome_without_false_audit(tmp_path, monkeypatch, commit_wins):
    store = await _store(tmp_path)
    reached_commit = asyncio.Event(); release_commit = asyncio.Event()
    real_commit = store.commit_turn
    async def delayed_commit(**kwargs):
        reached_commit.set()
        await release_commit.wait()
        return await real_commit(**kwargs)
    monkeypatch.setattr(store, "commit_turn", delayed_commit)
    task = asyncio.create_task(_run(store))
    await asyncio.wait_for(reached_commit.wait(), timeout=5)
    task.cancel()
    # Let cancellation reach the shield while the transaction is still pending.
    await asyncio.sleep(0)
    if not commit_wins:
        await store.update_campaign_snapshot("source-bridge", state={"counter": 73},
                                             expected_revision=0, expected_turn=0)
    release_commit.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=5)
    attempt = await store.load_attempt_by_operation("source-bridge", "operation-source-bridge-1")
    campaign = await store.load_campaign("source-bridge")
    if commit_wins:
        assert attempt["status"] == "completed" and campaign["current_turn"] == 1
        assert len(await store.get_recent_narrative_source_turns("source-bridge")) == 1
    else:
        assert attempt["status"] == "cancelled" and campaign["current_turn"] == 0
        assert campaign["state"] == {"counter": 73}
        assert not await store.get_recent_narrative_source_turns("source-bridge")


@pytest.mark.anyio
async def test_word_budget_after_schema_keeps_courtyard_refusal_closed(tmp_path):
    store = await _store(tmp_path)
    # 33 x five-word sentence gives 165 words within the n character ceiling.
    text = " ".join(["A chuva continua na galeria."] * 33)
    assert len(text) <= 1600
    assert profile.NarrativeSourceProposal.model_validate({"n": text, "q": QUESTION}).narrative == text
    result, gateway, chunks = await _run(store, n=text)
    assert result.status == "failed" and result.error["code"] == "scene_narrative_too_long"
    assert len(gateway.requests) == 1 and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_unregistered_campaign_cannot_enter_source_bridge(tmp_path):
    store = SQLitePersistence(tmp_path / "legacy-unregistered.sqlite3")
    await store.ensure_campaign("source-bridge", initial_state={"counter": 0})
    before = await store.load_campaign("source-bridge")
    result, gateway, chunks = await _run(store)
    assert result.status == "failed"
    assert result.error["code"] == "source_context_origin_missing"
    assert not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")
    assert await store.load_campaign("source-bridge") == before


@pytest.mark.anyio
@pytest.mark.parametrize("scene", [SceneState(location="Pátio"),
                                  SceneState(location="Galeria", npcs_present=("Guarda",))])
async def test_caller_cannot_replace_registered_source_scene(tmp_path, scene):
    store = await _store(tmp_path)
    result, gateway, chunks = await _run(store, current_scene=scene)
    assert result.status == "failed" and result.error["code"] == "source_context_scene_mismatch"
    assert not gateway.requests and not chunks
    assert not await store.list_attempts("source-bridge")


@pytest.mark.anyio
async def test_caller_post_state_cannot_smuggle_unassessed_context(tmp_path):
    store = await _store(tmp_path)
    result, gateway, chunks = await _run(
        store, state={"counter": 1, "player_sheet": {"memory_context": "Resumo v1."}},
    )
    assert result.status == "failed" and result.error["code"] == "source_context_state_incompatible"
    assert not gateway.requests and not chunks
    assert not await store.list_attempts("source-bridge")


@pytest.mark.anyio
async def test_stored_incompatible_context_is_rejected_before_context_build_or_budget(tmp_path, monkeypatch):
    from api import narrative_source_execution_service as executor
    store = await _store(tmp_path)
    with sqlite3.connect(store.db_path) as connection:
        connection.execute("UPDATE campaigns SET state_json=?", (
            json.dumps({"counter": 0, "context": {"summary": "Dependência histórica."}}),
        ))
    before = await store.load_campaign("source-bridge")
    monkeypatch.setattr(executor, "build_source_context", lambda **kw: pytest.fail("Built before eligibility"))
    result, gateway, chunks = await _run(store)
    assert result.status == "failed" and result.error["code"] == "source_context_state_incompatible"
    assert not gateway.requests and not chunks
    assert not await store.list_turns("source-bridge")
    assert await store.load_campaign("source-bridge") == before


@pytest.mark.anyio
async def test_incompatible_old_turn_cannot_hide_outside_two_source_window(tmp_path, monkeypatch):
    from api import narrative_source_execution_service as executor
    store = await _store(tmp_path)
    for index, text in enumerate((FIRST, SECOND, THIRD), 1):
        result, _, _ = await _run(store, index=index, n=text)
        assert result.status == "completed", result.error
    with sqlite3.connect(store.db_path) as connection:
        raw = json.loads(connection.execute("SELECT context_json FROM turns WHERE turn_number=1").fetchone()[0])
        raw["legacy_summary"] = "História incompatível fora da janela recente."
        connection.execute("UPDATE turns SET context_json=? WHERE turn_number=1", (json.dumps(raw),))
    monkeypatch.setattr(executor, "build_source_context", lambda **kw: pytest.fail("Selected before eligibility"))
    result, gateway, chunks = await _run(store, index=4, n=THIRD)
    assert result.status == "failed" and result.error["code"] == "source_context_history_incompatible"
    assert not gateway.requests and not chunks
    assert len(await store.list_turns("source-bridge")) == 3


@pytest.mark.anyio
async def test_four_turn_window_receipts_and_direct_read_avoid_v1_readers(tmp_path, monkeypatch):
    from api import context_service, memory_service
    from api.narrative_source_context import SELECTION_KEY
    store = await _store(tmp_path)
    def forbidden(*args, **kwargs): pytest.fail("Source context used a v1 reader or RNG")
    for method in ("retrieve_memories", "list_episodic_memories", "list_memory_candidates",
                   "list_consolidations", "get_recent_narrative_source_turns", "list_events"):
        monkeypatch.setattr(SQLitePersistence, method, forbidden)
    for name in ("assemble_context", "score_context_item", "estimate_tokens"):
        monkeypatch.setattr(context_service, name, forbidden)
    for name in ("build_memory_prompt_fragment", "load_memory", "update_scene_memory"):
        monkeypatch.setattr(memory_service, name, forbidden)
    monkeypatch.setattr(random, "randint", forbidden)
    # Identical texts from distinct turns remain two distinct attributed sources.
    originals = (FIRST, FIRST, SECOND, THIRD)
    before_read_count = 0
    for index, text in enumerate(originals, 1):
        store = SQLitePersistence(tmp_path / "source-only.sqlite3")
        result, gateway, chunks = await _run(store, index=index, n=text)
        assert result.status == "completed", result.error
        assert chunks == [text + "\n\n" + QUESTION]
        assert len(gateway.requests) == 1
        packet = json.loads(gateway.requests[0].messages[1].content)
        carried = packet["context"]["attributed_sources"]
        assert [item["text"] for item in carried] == list(originals[max(0, index-3):index-1])
        assert QUESTION not in gateway.requests[0].messages[1].content
        turn = await store.load_turn_by_operation("source-bridge", f"operation-source-bridge-{index}")
        receipt = turn["context"][SELECTION_KEY]
        ids = [f"turn-source-bridge-{i}" for i in range(1, index)]
        assert receipt["selected_turn_ids"] == ids[-2:]
        assert receipt["omitted_turn_ids"] == ids[:-2]
        assert receipt["current_turn"] == receipt["state_revision"] == index - 1
        assert text not in json.dumps(receipt, ensure_ascii=False)
        before_read_count += len(gateway.requests)
    before = await store.load_campaign("source-bridge")
    with sqlite3.connect(store.db_path) as connection:
        dump_before = tuple(connection.iterdump())
    snapshot = await store.read_source_context_snapshot("source-bridge", expected_turn=4, expected_revision=4)
    assert snapshot.canonical_scene == SCENE
    assert snapshot.selected_turn_ids == ("turn-source-bridge-3", "turn-source-bridge-4")
    assert snapshot.omitted_turn_ids == ("turn-source-bridge-1", "turn-source-bridge-2")
    assert [item.projection.text for item in snapshot.sources] == [SECOND, THIRD]
    assert before_read_count == 4
    with sqlite3.connect(store.db_path) as connection:
        assert tuple(connection.iterdump()) == dump_before
    assert await store.load_campaign("source-bridge") == before
    # Replaying an older operation uses its original receipt, not today's window.
    replay, gateway, chunks = await _run(store)
    assert replay.status == "completed" and not gateway.requests and not chunks
    assert replay.envelope.projection.text == FIRST
    assert len(await store.list_turns("source-bridge")) == 4


@pytest.mark.anyio
async def test_selection_receipt_is_validated_before_delivery(tmp_path, monkeypatch):
    from api import narrative_source_execution_service as executor
    from api.narrative_source_context import SourceContextError
    store = await _store(tmp_path)
    real_validate = executor.validate_source_selection
    def corrupt_selection(value, **kwargs):
        value = dict(value, selected_turn_ids=["foreign-turn"])
        return real_validate(value, **kwargs)
    monkeypatch.setattr(executor, "validate_source_selection", corrupt_selection)
    result, gateway, chunks = await _run(store)
    assert result.status == "failed" and result.error["code"] == "source_context_selection_invalid"
    assert len(gateway.requests) == 1 and not chunks
    assert not await store.list_turns("source-bridge")


@pytest.mark.anyio
async def test_selection_receipt_is_revalidated_inside_commit(tmp_path, monkeypatch):
    from api.narrative_source_context import SELECTION_KEY
    store = await _store(tmp_path)
    real_commit = store.commit_turn
    async def corrupt_commit(**kwargs):
        kwargs["context"][SELECTION_KEY]["origin_sha256"] = "0" * 64
        return await real_commit(**kwargs)
    monkeypatch.setattr(store, "commit_turn", corrupt_commit)
    result, gateway, chunks = await _run(store)
    assert result.status == "failed" and result.error["code"] == "source_context_selection_invalid"
    assert len(gateway.requests) == len(chunks) == 1  # provisional delivery
    assert not await store.list_turns("source-bridge")
    assert (await store.load_campaign("source-bridge"))["current_turn"] == 0


@pytest.mark.anyio
async def test_revision_change_after_source_read_cannot_commit_stale_turn(tmp_path, monkeypatch):
    store = await _store(tmp_path)
    real_read = store.read_source_context_snapshot
    async def race_read(*args, **kwargs):
        snapshot = await real_read(*args, **kwargs)
        await store.update_campaign_snapshot("source-bridge", state={"counter": 91},
                                            expected_revision=0, expected_turn=0)
        return snapshot
    monkeypatch.setattr(store, "read_source_context_snapshot", race_read)
    result, gateway, chunks = await _run(store)
    assert result.status == "failed" and len(gateway.requests) == len(chunks) == 1
    assert not await store.list_turns("source-bridge")
    campaign = await store.load_campaign("source-bridge")
    assert campaign["current_turn"] == 0 and campaign["state_revision"] == 1
    assert campaign["state"] == {"counter": 91}
