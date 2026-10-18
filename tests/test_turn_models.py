from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.turn_models import (
    CandidateValidationStatus,
    CanonicalEvent,
    CanonicalFact,
    Consolidation,
    ConsolidationScope,
    EntityReference,
    EpisodicMemory,
    MemoryCandidate,
    NarrativeRecord,
    RecordReference,
    StateChange,
    TurnDraft,
    Visibility,
)


def test_relationship_frontend_projection_does_not_expose_storyteller_counters() -> None:
    from api.relationship_service import (
        NpcRelationship,
        RelationshipState,
        get_relationships_for_frontend,
    )

    state = RelationshipState(
        session_id="session",
        relationships={
            "sheriff": NpcRelationship(
                npc_id="sheriff",
                disposition="hostile",
                trust_level=1,
                favor_balance=-3,
                history=["T1: Conflito aberto"],
            )
        },
    )

    projection = get_relationships_for_frontend(state)[0]
    assert set(projection) == {"id", "titulo", "desc"}
    assert "trust_level" not in projection
    assert "favor_balance" not in projection


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def make_fact(fact_id: str = "fact-1") -> CanonicalFact:
    return CanonicalFact(
        fact_id=fact_id,
        fact_type="mechanical_result",
        predicate="health.superficial",
        value=2,
        subject=EntityReference(
            entity_id="player-1", entity_type="character", label="Karl"
        ),
        occurred_at=NOW,
        visibility=Visibility.PLAYER,
        tags=("combat",),
    )


def make_event(*fact_ids: str) -> CanonicalEvent:
    return CanonicalEvent(
        event_id="event-1",
        session_id="session-1",
        turn_id="turn-1",
        sequence=1,
        event_type="attack_resolved",
        occurred_at=NOW,
        summary="O ataque causou dois pontos de dano superficial.",
        fact_ids=fact_ids,
        actors=(EntityReference(entity_id="player-1", entity_type="character"),),
        references=(RecordReference(record_id="roll-1", record_type="dice_roll"),),
    )


def test_records_are_versioned_strict_and_frozen() -> None:
    fact = make_fact()

    assert fact.schema_version == "1.0"
    assert fact.model_dump(mode="json")["visibility"] == "player"

    with pytest.raises(ValidationError):
        fact.importance = 0.9  # type: ignore[misc]

    with pytest.raises(ValidationError):
        CanonicalFact(
            fact_id="fact-extra",
            fact_type="mechanical_result",
            predicate="hunger",
            value=2,
            occurred_at=NOW,
            unexpected=True,  # type: ignore[call-arg]
        )


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        CanonicalEvent(
            event_id="event-naive",
            session_id="session-1",
            turn_id="turn-1",
            sequence=0,
            event_type="invalid",
            occurred_at=datetime(2026, 8, 24, 12, 0),
        )


def test_turn_draft_validates_event_fact_and_session_references() -> None:
    fact = make_fact()
    event = make_event(fact.fact_id)
    draft = TurnDraft(
        draft_id="draft-1",
        session_id="session-1",
        turn_id="turn-1",
        attempt_id="attempt-1",
        created_at=NOW,
        player_input="Ataco o agressor.",
        facts=(fact,),
        events=(event,),
        state_changes=(StateChange(path=("status", "health"), value=5),),
    )

    assert draft.events[0].fact_ids == ("fact-1",)
    assert draft.state_changes[0].path == ("status", "health")

    with pytest.raises(ValidationError, match="unknown facts"):
        draft.model_copy(update={"events": (make_event("missing-fact"),)}).model_validate(
            draft.model_copy(update={"events": (make_event("missing-fact"),)}).model_dump()
        )

    wrong_session = make_event("fact-1").model_copy(update={"session_id": "other"})
    with pytest.raises(ValidationError, match="session and turn"):
        TurnDraft(
            draft_id="draft-2",
            session_id="session-1",
            turn_id="turn-1",
            attempt_id="attempt-1",
            created_at=NOW,
            player_input="Ataco.",
            facts=(fact,),
            events=(wrong_session,),
        )


def test_completed_narrative_requires_canonical_sources() -> None:
    narrative = NarrativeRecord(
        narrative_id="narrative-1",
        session_id="session-1",
        turn_id="turn-1",
        created_at=NOW,
        text="A porta cede sob o impacto.",
        source_event_ids=("event-1",),
    )
    assert narrative.complete is True

    with pytest.raises(ValidationError):
        NarrativeRecord(
            narrative_id="narrative-partial",
            session_id="session-1",
            turn_id="turn-1",
            created_at=NOW,
            text="A porta...",
            source_event_ids=("event-1",),
            complete=False,  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        NarrativeRecord(
            narrative_id="narrative-orphan",
            session_id="session-1",
            turn_id="turn-1",
            created_at=NOW,
            text="Sem fonte.",
            source_event_ids=(),
        )


def test_memory_records_preserve_sources_and_validation_state() -> None:
    candidate = MemoryCandidate(
        candidate_id="candidate-1",
        session_id="session-1",
        turn_id="turn-1",
        created_at=NOW,
        summary="Karl feriu o agressor diante do xerife.",
        source_event_ids=("event-1",),
        importance=0.8,
        validation_status=CandidateValidationStatus.ACCEPTED,
    )
    memory = EpisodicMemory(
        memory_id="memory-1",
        session_id="session-1",
        created_at=NOW,
        summary=candidate.summary,
        source_event_ids=candidate.source_event_ids,
        importance=candidate.importance,
        version=1,
    )
    consolidation = Consolidation(
        consolidation_id="scene-summary-1",
        session_id="session-1",
        scope=ConsolidationScope.SCENE,
        created_at=NOW,
        version=2,
        summary="O confronto no cais terminou com uma dívida política.",
        source_memory_ids=(memory.memory_id,),
        source_event_ids=memory.source_event_ids,
        supersedes_consolidation_id="scene-summary-0",
    )

    assert memory.source_event_ids == ("event-1",)
    assert consolidation.source_memory_ids == ("memory-1",)
    assert consolidation.version == 2

    with pytest.raises(ValidationError, match="source record"):
        Consolidation(
            consolidation_id="orphan-summary",
            session_id="session-1",
            scope=ConsolidationScope.SESSION,
            created_at=NOW,
            summary="Resumo sem fontes.",
        )
