"""Transactional boundaries of the opt-in source turn, without model calls."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3

import pytest

from api.llm.contract import AdapterIdentity, LLMTarget, Provenance, ProvenanceValue
from api.narrative_source_profile import NarrativeSourceProposal, create_source_projection
from api.narrative_source_turn import (
    INVOCATION_OPERATION, PROTOCOL, SourceTurnContractError, create_source_turn_envelope,
)
from api.persistence import IdempotencyConflictError, SQLitePersistence
from api.scene_service import SceneState
from api.turn_models import CanonicalEvent, CanonicalFact, NarrativeRecord


NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)
BASE_TEXT = (
    "A chuva tamborila nas janelas da galeria enquanto a luminária oscila sobre o balcão. "
    "Um ruído seco atravessa o corredor vazio; sobre a mesa, um mapa dobrado repousa "
    "ao lado de uma caixa fechada."
)
TEXT = " ".join([BASE_TEXT] * 3)
QUESTION = "O que fazes agora?"


def _turn(index=1, *, session="source-session", question=QUESTION, narrative_text=TEXT):
    turn_id, operation_id, attempt_id = f"turn-{index}", f"operation-{index}", f"attempt-{index}"
    invocation_id = f"invocation-{index}"
    fact = CanonicalFact(
        fact_id=f"fact-{index}", fact_type="action.declaration", predicate="declared_player_action",
        value={"player_input": "Observo a galeria.", "requires_roll": False}, occurred_at=NOW,
    )
    event = CanonicalEvent(
        event_id=f"event-{index}", session_id=session, turn_id=turn_id, sequence=0,
        event_type="player_action_declared", occurred_at=NOW,
        summary="O jogador declara observar a galeria.", fact_ids=(fact.fact_id,),
    )
    proposal = NarrativeSourceProposal.model_validate({"n": narrative_text, "q": question})
    projection = create_source_projection(
        proposal, source_id=f"source-{index}", session_id=session, turn_id=turn_id,
        invocation_id=invocation_id, current_scene=SceneState(location="Galeria"),
        facts=(fact,), player_input="Observo a galeria.",
    )
    narrative = NarrativeRecord(
        narrative_id=f"narrative-{index}", session_id=session, turn_id=turn_id,
        created_at=NOW, text=proposal.player_text, source_event_ids=(event.event_id,),
        invocation_id=invocation_id,
    )
    provenance = Provenance(
        invocation_id=invocation_id, requested_target=LLMTarget(
            profile="synthetic-source", provider="fake", model="fake-model",
        ), adapter=AdapterIdentity(name="fake", version="1"),
        effective_provider=ProvenanceValue.observed("fake"),
        effective_model=ProvenanceValue.reported("fake-model"), started_at=NOW, finished_at=NOW,
    )
    audit = {"invocations": [{
        "invocation_id": invocation_id, "operation": INVOCATION_OPERATION,
        "status": "completed", "provenance": provenance.model_dump(mode="json"), "error": None,
    }]}
    envelope = create_source_turn_envelope(
        projection=projection, narrative=narrative, question=question,
        operation_id=operation_id, attempt_id=attempt_id, provenance=audit,
    )
    metadata = {
        "narrative_contract": PROTOCOL, "expected_invocation_id": invocation_id,
        "expected_invocation_operation": INVOCATION_OPERATION,
    }
    kwargs = dict(
        session_id=session, operation_id=operation_id, attempt_id=attempt_id, turn_id=turn_id,
        turn_number=index, base_revision=index-1, base_state_revision=index-1,
        state={"turn": index}, relationships={}, narrative=narrative, facts=(fact,), events=(event,),
        memory_candidates=(), episodic_memories=(), user_input="Observo a galeria.",
        context={"narrative_source": envelope.model_dump(mode="json")},
        provenance=audit, narrative_contract=PROTOCOL,
    )
    return kwargs, metadata, envelope


async def _reserve(store, kwargs, metadata):
    return await store.start_attempt(
        session_id=kwargs["session_id"], operation_id=kwargs["operation_id"],
        attempt_id=kwargs["attempt_id"], requested_turn=kwargs["turn_number"],
        user_input=kwargs["user_input"], metadata=metadata,
    )


async def _commit(store, index=1, *, legacy=False, **changes):
    kwargs, metadata, envelope = _turn(index, **changes)
    if legacy:
        kwargs.pop("narrative_contract")
        kwargs["context"] = {}
        metadata = {}
    await _reserve(store, kwargs, metadata)
    return await store.commit_turn(**kwargs), kwargs, envelope


def test_source_roundtrip_restart_and_chronological_window_preserve_literal_text(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        assert await store.get_recent_narrative_source_turns("source-session") == ()
        expected = []
        long_text = TEXT + " O reflexo permanece imóvel sobre o vidro."
        for index in (1, 2, 3):
            _, _, envelope = await _commit(store, index, narrative_text=long_text)
            expected.append(envelope)
        restarted = SQLitePersistence(store.db_path)
        restored = await restarted.get_recent_narrative_source_turns("source-session")
        assert restored == tuple(expected[-2:])
        assert len(long_text) > 600
        assert all(item.projection.text == long_text and QUESTION not in item.projection.text for item in restored)
        assert await restarted.list_memory_candidates("source-session") == []
        assert await restarted.list_episodic_memories("source-session") == []
        assert (await restarted.load_campaign("source-session"))["current_turn"] == 3
        assert (await restarted.database_info())["schema_version"] == 4
    asyncio.run(scenario())


@pytest.mark.parametrize("mutation", [
    "remove_envelope", "remove_argument_and_envelope", "wrong_contract", "wrong_invocation",
    "wrong_operation", "wrong_attempt", "changed_question", "changed_audit", "unreserved",
])
def test_commit_cannot_remove_or_rebind_the_reserved_source_obligation(tmp_path, mutation):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        kwargs, metadata, _ = _turn()
        if mutation != "unreserved":
            await _reserve(store, kwargs, metadata)
        if mutation == "remove_envelope":
            kwargs["context"] = {}
        elif mutation == "remove_argument_and_envelope":
            kwargs.pop("narrative_contract")
            kwargs["context"] = {}
        elif mutation == "wrong_contract":
            kwargs["narrative_contract"] = True
        elif mutation == "wrong_invocation":
            kwargs["context"]["narrative_source"]["projection"]["source"]["invocation_id"] = "foreign"
        elif mutation == "wrong_operation":
            kwargs["operation_id"] = "foreign"
        elif mutation == "wrong_attempt":
            kwargs["attempt_id"] = "foreign"
        elif mutation == "changed_question":
            kwargs["context"]["narrative_source"]["question"] = "O que fazes a seguir?"
        elif mutation == "changed_audit":
            kwargs["provenance"]["invocations"][0]["invocation_id"] = "foreign"
        with pytest.raises(SourceTurnContractError):
            await store.commit_turn(**kwargs)
        assert await store.list_turns("source-session") == []
        assert await store.list_events("source-session") == []
        assert await store.get_recent_narrative_source_turns("source-session") == ()
        campaign = await store.load_campaign("source-session")
        assert campaign is None or (campaign["current_turn"], campaign["state_revision"]) == (0, 0)
    asyncio.run(scenario())


def test_idempotent_source_commit_still_checks_obligation_and_digest(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        _, kwargs, envelope = await _commit(store)
        assert (await store.commit_turn(**kwargs)).idempotent is True
        removed = deepcopy(kwargs)
        removed.pop("narrative_contract")
        removed["context"] = {}
        with pytest.raises(SourceTurnContractError):
            await store.commit_turn(**removed)
        changed, _, _ = _turn(question="O que fazes a seguir?")
        with pytest.raises(IdempotencyConflictError):
            await store.commit_turn(**changed)
        assert await store.get_recent_narrative_source_turns("source-session") == (envelope,)
    asyncio.run(scenario())


@pytest.mark.parametrize("field", ["context", "narrative_text", "result_hash", "expected_invocation", "audit"])
def test_recovery_revalidates_stored_turn_and_attempt_pairs(tmp_path, field):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        _, kwargs, _ = await _commit(store)
        with sqlite3.connect(store.db_path) as connection:
            if field == "context":
                context = deepcopy(kwargs["context"])
                context["narrative_source"]["question"] = "O que fazes a seguir?"
                connection.execute("UPDATE turns SET context_json=?", (json.dumps(context),))
            elif field == "narrative_text":
                connection.execute("UPDATE turns SET narrative_text='Outra apresentação.'")
            elif field == "result_hash":
                connection.execute("UPDATE attempts SET result_hash=?", ("0"*64,))
            elif field == "expected_invocation":
                row = connection.execute("SELECT metadata_json FROM attempts").fetchone()
                metadata = json.loads(row[0]); metadata["expected_invocation_id"] = "foreign"
                connection.execute("UPDATE attempts SET metadata_json=?", (json.dumps(metadata),))
            else:
                connection.execute("UPDATE attempts SET provenance_json='{}'")
        with pytest.raises(SourceTurnContractError):
            await SQLitePersistence(store.db_path).get_recent_narrative_source_turns("source-session")
    asyncio.run(scenario())


def test_required_recent_legacy_turn_is_not_hidden_by_filtering_for_sources(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        await _commit(store, 1)
        await _commit(store, 2, legacy=True)
        _, _, latest = await _commit(store, 3)
        with pytest.raises(SourceTurnContractError, match="source_turn_history_incompatible"):
            await store.get_recent_narrative_source_turns("source-session")
        assert await store.get_recent_narrative_source_turns("source-session", limit=1) == (latest,)
        assert len(await store.list_turns("source-session")) == 3
    asyncio.run(scenario())


def test_required_player_source_is_not_omitted_for_public_only_reader(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        await _commit(store)
        with pytest.raises(SourceTurnContractError, match="source_turn_visibility_forbidden"):
            await store.get_recent_narrative_source_turns("source-session", allowed_visibilities=("public",))
        assert await store.get_recent_narrative_source_turns("another-session") == ()
    asyncio.run(scenario())


@pytest.mark.parametrize("limit", [0, 3, True, "2", 1.5, None])
def test_source_query_limit_is_strict_and_never_clipped(tmp_path, limit):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        with pytest.raises(SourceTurnContractError, match="source_turn_query_invalid"):
            await store.get_recent_narrative_source_turns("source-session", limit=limit)
        assert not store.db_path.exists()
    asyncio.run(scenario())


def test_late_sql_failure_leaves_no_committed_source_or_partial_state(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        kwargs, metadata, _ = _turn()
        await _reserve(store, kwargs, metadata)
        with sqlite3.connect(store.db_path) as connection:
            connection.execute("""CREATE TRIGGER reject_source_commit
                BEFORE UPDATE OF current_turn ON campaigns WHEN NEW.current_turn > 0
                BEGIN SELECT RAISE(ABORT, 'synthetic late failure'); END""")
        with pytest.raises(sqlite3.IntegrityError, match="synthetic late failure"):
            await store.commit_turn(**kwargs)
        assert await store.list_turns("source-session") == []
        assert await store.list_events("source-session") == []
        assert await store.get_recent_narrative_source_turns("source-session") == ()
        attempt = await store.load_attempt_by_operation("source-session", "operation-1")
        assert attempt["status"] == "pending" and attempt["committed_turn_id"] is None
        campaign = await store.load_campaign("source-session")
        assert (campaign["current_turn"], campaign["state_revision"], campaign["state"]) == (0, 0, {})
    asyncio.run(scenario())


@pytest.mark.parametrize("field,value", [
    ("status", "pending"),
    ("committed_turn_id", "foreign-turn"),
    ("result_hash", "0" * 64),
    ("provenance_json", "{}"),
])
def test_idempotent_source_replay_rejects_torn_terminal_attempt(tmp_path, field, value):
    async def scenario():
        store = SQLitePersistence(tmp_path / "source.sqlite3")
        _, kwargs, _ = await _commit(store)
        assert field in {"status", "committed_turn_id", "result_hash", "provenance_json"}
        with sqlite3.connect(store.db_path) as connection:
            connection.execute(
                f"UPDATE attempts SET {field}=? WHERE session_id=? AND operation_id=?",
                (value, kwargs["session_id"], kwargs["operation_id"]),
            )
        campaign = await store.load_campaign("source-session")
        with pytest.raises(SourceTurnContractError, match="source_turn_stored_pair_mismatch"):
            await store.commit_turn(**kwargs)
        assert await store.load_campaign("source-session") == campaign
        assert len(await store.list_turns("source-session")) == 1
        with sqlite3.connect(store.db_path) as connection:
            assert connection.execute(f"SELECT {field} FROM attempts").fetchone()[0] == value
    asyncio.run(scenario())
