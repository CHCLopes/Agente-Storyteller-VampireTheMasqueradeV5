from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.memory_service import (
    CampaignMemory,
    SceneMemory,
    SessionMemory,
    build_grounded_consolidation_summary,
    build_memory_prompt_fragment,
    create_consolidation,
    derive_memory_candidate,
    promote_memory_candidate,
    update_scene_memory,
    validate_memory_candidate,
)
from api.turn_models import (
    CandidateProposer,
    CandidateValidationStatus,
    CanonicalEvent,
    CanonicalFact,
    ConsolidationScope,
    EpisodicMemory,
    NarrativeRecord,
    Visibility,
)


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def fact(
    fact_id: str = "fact-1", visibility: Visibility = Visibility.PLAYER
) -> CanonicalFact:
    return CanonicalFact(
        fact_id=fact_id,
        fact_type="mechanical_result",
        predicate="roll.successes",
        value=3,
        occurred_at=NOW,
        visibility=visibility,
    )


def event(
    *,
    event_id: str = "event-1",
    session_id: str = "session-1",
    turn_id: str = "turn-1",
    fact_ids: tuple[str, ...] = ("fact-1",),
    summary: str | None = "Karl venceu o confronto no cais.",
    visibility: Visibility = Visibility.PLAYER,
) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=event_id,
        session_id=session_id,
        turn_id=turn_id,
        sequence=1,
        event_type="conflict_resolved",
        occurred_at=NOW,
        summary=summary,
        fact_ids=fact_ids,
        tags=("cais", "confronto"),
        importance=0.8,
        visibility=visibility,
        pending=True,
    )


def narrative(
    *,
    source_event_ids: tuple[str, ...] = ("event-1",),
    session_id: str = "session-1",
    turn_id: str = "turn-1",
    text: str = "A noite guardará a marca desse confronto.",
    visibility: Visibility = Visibility.PLAYER,
) -> NarrativeRecord:
    return NarrativeRecord(
        narrative_id="narrative-1",
        session_id=session_id,
        turn_id=turn_id,
        created_at=NOW,
        text=text,
        source_event_ids=source_event_ids,
        visibility=visibility,
    )


def accepted_memory(
    memory_id: str,
    *,
    source_event_ids: tuple[str, ...],
    visibility: Visibility = Visibility.PLAYER,
    summary: str = "Memória validada.",
) -> EpisodicMemory:
    return EpisodicMemory(
        memory_id=memory_id,
        session_id="session-1",
        created_at=NOW,
        summary=summary,
        source_event_ids=source_event_ids,
        tags=("cais",),
        visibility=visibility,
    )


def test_legacy_models_and_prompt_api_remain_available() -> None:
    memory = SessionMemory(
        session_id="legacy",
        scene=SceneMemory(recent_events=["T1: entrada"], npcs_present=["xerife"]),
        campaign=CampaignMemory(total_kills=1),
    )

    updated = update_scene_memory(memory, "Ação comum", "Continuo a cena", 2)
    fragment = build_memory_prompt_fragment(updated)

    assert updated.scene.recent_events[-1] == "T2: Continuo a cena"
    assert "Eventos recentes" in fragment
    assert "Mortes causadas na campanha: 1" in fragment


@pytest.mark.parametrize("summary", [None, ""], ids=["none", "empty"])
def test_derivation_uses_a_semantic_unit_without_character_truncation(
    summary: str | None,
) -> None:
    long_semantic_text = "Consequência persistente. " * 20
    source_event = event(summary=None)
    source_narrative = narrative(text=long_semantic_text)

    candidate = derive_memory_candidate(
        source_event, source_narrative, candidate_id="candidate-1", summary=summary
    )

    # NonEmptyStr normalizes surrounding whitespace, but keeps the full unit.
    assert candidate.summary == long_semantic_text.strip()
    assert len(candidate.summary) > 80
    assert candidate.source_event_ids == (source_event.event_id,)
    assert candidate.validation_status is CandidateValidationStatus.PENDING
    assert candidate.proposed_by is CandidateProposer.LLM
    assert candidate.tags == source_event.tags

    still_pending = validate_memory_candidate(
        candidate,
        events=(source_event,),
        narratives=(source_narrative,),
        facts=(fact(),),
    )
    assert still_pending.validation_status is CandidateValidationStatus.PENDING
    with pytest.raises(ValueError, match="only an accepted"):
        promote_memory_candidate(still_pending, memory_id="memory-from-prose")


@pytest.mark.parametrize("summary", [None, ""], ids=["none", "empty"])
def test_empty_summary_uses_existing_canonical_event_summary(summary: str | None) -> None:
    source_event = event()
    source_narrative = narrative(text="Uma versão narrativa diferente da fonte canônica.")
    candidate = derive_memory_candidate(
        source_event, source_narrative, candidate_id="event-summary", summary=summary
    )
    assert candidate.summary == source_event.summary
    assert candidate.proposed_by is CandidateProposer.DETERMINISTIC

    accepted = validate_memory_candidate(
        candidate, events=(source_event,), narratives=(source_narrative,), facts=(fact(),)
    )
    memory = promote_memory_candidate(accepted, memory_id="event-memory")
    assert memory.summary == source_event.summary
    assert memory.source_event_ids == (source_event.event_id,)


@pytest.mark.parametrize("event_summary", [None, "O resultado canônico permanece válido."])
def test_whitespace_summary_still_fails_normal_validation(event_summary: str | None) -> None:
    with pytest.raises(ValidationError):
        derive_memory_candidate(
            event(summary=event_summary), narrative(),
            candidate_id="whitespace-summary", summary=" \t\n ",
        )


def test_derivation_rejects_mismatched_session_turn_or_source() -> None:
    with pytest.raises(ValueError, match="session and turn"):
        derive_memory_candidate(
            event(), narrative(session_id="other"), candidate_id="candidate-1"
        )

    with pytest.raises(ValueError, match="does not reference"):
        derive_memory_candidate(
            event(), narrative(source_event_ids=("event-other",)), candidate_id="candidate-1"
        )


def test_validation_checks_sources_facts_and_visibility_then_accepts() -> None:
    source_fact = fact(visibility=Visibility.STORYTELLER)
    source_event = event(visibility=Visibility.PLAYER)
    source_narrative = narrative(visibility=Visibility.PLAYER)
    candidate = derive_memory_candidate(
        source_event, source_narrative, candidate_id="candidate-1"
    )

    with pytest.raises(ValueError, match="broaden source visibility"):
        validate_memory_candidate(
            candidate,
            events=(source_event,),
            narratives=(source_narrative,),
            facts=(source_fact,),
        )

    restricted_candidate = candidate.model_copy(
        update={"visibility": Visibility.STORYTELLER}
    )
    accepted = validate_memory_candidate(
        restricted_candidate,
        events=(source_event,),
        narratives=(source_narrative,),
        facts=(source_fact,),
    )

    assert accepted.validation_status is CandidateValidationStatus.ACCEPTED
    assert accepted.visibility is Visibility.STORYTELLER
    assert accepted.validation_notes


def test_validation_rejects_unknown_fact_and_missing_narrative_coverage() -> None:
    source_event = event(fact_ids=("missing-fact",))
    source_narrative = narrative()
    candidate = derive_memory_candidate(
        source_event, source_narrative, candidate_id="candidate-1"
    )

    with pytest.raises(ValueError, match="unknown fact"):
        validate_memory_candidate(
            candidate,
            events=(source_event,),
            narratives=(source_narrative,),
            facts=(),
        )

    with pytest.raises(ValueError, match="lack completed narrative"):
        validate_memory_candidate(
            candidate,
            events=(source_event,),
            narratives=(),
            facts=(),
        )


def test_only_accepted_candidate_can_be_promoted() -> None:
    source_event = event()
    source_narrative = narrative()
    pending = derive_memory_candidate(
        source_event, source_narrative, candidate_id="candidate-1"
    )

    with pytest.raises(ValueError, match="only an accepted"):
        promote_memory_candidate(pending, memory_id="memory-1")

    accepted = validate_memory_candidate(
        pending,
        events=(source_event,),
        narratives=(source_narrative,),
        facts=(fact(),),
    )
    memory = promote_memory_candidate(accepted, memory_id="memory-1", version=2)

    assert memory.summary == accepted.summary
    assert memory.source_event_ids == accepted.source_event_ids
    assert memory.version == 2


def test_llm_candidate_requires_explicit_grounding_before_acceptance() -> None:
    source_event = event()
    source_narrative = narrative()
    proposal = derive_memory_candidate(
        source_event,
        source_narrative,
        candidate_id="candidate-llm",
        summary="O príncipe morreu e legou a cidade ao personagem.",
        proposed_by=CandidateProposer.LLM,
    )

    still_pending = validate_memory_candidate(
        proposal,
        events=(source_event,),
        narratives=(source_narrative,),
        facts=(fact(),),
    )
    assert still_pending.validation_status is CandidateValidationStatus.PENDING
    assert "requires explicit" in still_pending.validation_notes[0]
    with pytest.raises(ValueError, match="only an accepted"):
        promote_memory_candidate(still_pending, memory_id="memory-llm")

    reviewed = validate_memory_candidate(
        proposal,
        events=(source_event,),
        narratives=(source_narrative,),
        facts=(fact(),),
        semantic_grounding_confirmed=True,
    )
    assert reviewed.validation_status is CandidateValidationStatus.ACCEPTED


def test_consolidation_is_versioned_idempotent_grounded_and_preserves_sources() -> None:
    first_memory = accepted_memory(
        "memory-1",
        source_event_ids=("event-1",),
        summary="O Xerife confirmou a dívida.",
    )
    second_memory = accepted_memory(
        "memory-2",
        source_event_ids=("event-1", "event-2"),
        summary="A porta do cais foi aberta.",
    )
    third_memory = accepted_memory(
        "memory-3",
        source_event_ids=("event-3",),
        summary="O Príncipe permanece vivo.",
    )

    first = create_consolidation(
        (second_memory, first_memory),
        consolidation_id="consolidation-1",
        scope=ConsolidationScope.SCENE,
        proposed_summary="O Xerife morreu e perdoou a dívida.",
    )
    repeated = create_consolidation(
        (first_memory, second_memory),
        consolidation_id="ignored-id",
        scope=ConsolidationScope.SCENE,
        proposed_summary="Outra versão livre e contraditória.",
        previous=first,
    )
    revised = create_consolidation(
        (first_memory, second_memory, third_memory),
        consolidation_id="consolidation-2",
        scope=ConsolidationScope.SCENE,
        proposed_summary="O Príncipe morreu.",
        previous=first,
    )

    assert first.source_memory_ids == ("memory-1", "memory-2")
    assert first.source_event_ids == ("event-1", "event-2")
    assert first.summary == (
        "- O Xerife confirmou a dívida.\n- A porta do cais foi aberta."
    )
    assert "morreu" not in first.summary
    assert repeated == first
    assert revised.version == 2
    assert revised.supersedes_consolidation_id == first.consolidation_id
    assert revised.source_event_ids == ("event-1", "event-2", "event-3")
    assert revised.summary.endswith("- O Príncipe permanece vivo.")
    assert "O Príncipe morreu" not in revised.summary


def test_grounded_consolidation_summary_rejects_conflicting_source_identity() -> None:
    with pytest.raises(ValueError, match="conflicting summaries"):
        build_grounded_consolidation_summary(
            (("memory-1", "O Xerife vive."), ("memory-1", "O Xerife morreu."))
        )


def test_consolidation_cannot_widen_visibility() -> None:
    secret = accepted_memory(
        "memory-secret",
        source_event_ids=("event-secret",),
        visibility=Visibility.STORYTELLER,
    )

    with pytest.raises(ValueError, match="broaden source visibility"):
        create_consolidation(
            (secret,),
            consolidation_id="consolidation-public",
            scope=ConsolidationScope.SESSION,
            proposed_summary="Segredo indevidamente público.",
            visibility=Visibility.PUBLIC,
        )
