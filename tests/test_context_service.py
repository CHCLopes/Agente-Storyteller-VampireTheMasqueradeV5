from datetime import datetime, timedelta, timezone

import pytest

import api.context_service as context_service
from api.context_service import (
    ContextItem,
    ContextLayer,
    ContextQuery,
    ContextScoringWeights,
    assemble_context,
    estimate_tokens,
    score_context_item,
)
from api.orchestrator_service import _stored_memory_context_item
from api.turn_models import EntityReference, EpisodicMemory, Visibility


NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def item(
    item_id: str,
    content: str,
    *,
    layer: ContextLayer = ContextLayer.EPISODIC_MEMORY,
    visibility: Visibility = Visibility.PLAYER,
    occurred_at: datetime | None = NOW,
    importance: float = 0.5,
    required: bool = False,
    pending: bool = False,
    selection_priority: int | None = None,
) -> ContextItem:
    return ContextItem(
        item_id=item_id,
        layer=layer,
        content=content,
        visibility=visibility,
        occurred_at=occurred_at,
        importance=importance,
        required=required,
        pending=pending,
        selection_priority=selection_priority,
    )


def query(**updates: object) -> ContextQuery:
    values: dict[str, object] = {
        "query_text": "xerife cais",
        "allowed_visibilities": frozenset(
            {Visibility.PUBLIC, Visibility.PLAYER}
        ),
        "now": NOW,
        "token_budget": 100,
    }
    values.update(updates)
    return ContextQuery(**values)


def test_visibility_is_filtered_before_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visible = item("visible", "O xerife observou o cais.")
    secret = item(
        "secret",
        "O xerife é o traidor do cais.",
        visibility=Visibility.STORYTELLER,
        importance=1.0,
        pending=True,
    )
    original_score = context_service.score_context_item

    def guarded_score(candidate: ContextItem, context_query: ContextQuery):
        assert candidate.visibility is not Visibility.STORYTELLER
        return original_score(candidate, context_query)

    monkeypatch.setattr(context_service, "score_context_item", guarded_score)
    result = assemble_context([secret, visible], query())

    assert [entry.item.item_id for entry in result.selected] == ["visible"]
    # Hidden identifiers are not reported as budget omissions either.
    assert "secret" not in result.omitted_item_ids


def test_score_exposes_all_four_signals() -> None:
    candidate = ContextItem(
        item_id="pending-recent",
        layer=ContextLayer.OPEN_THREADS,
        content="O xerife deixou uma pendência no cais.",
        occurred_at=NOW - timedelta(days=30),
        importance=0.75,
        pending=True,
        tags=("dívida",),
        actors=(EntityReference(entity_id="xerife", entity_type="npc"),),
    )
    context_query = query(
        weights=ContextScoringWeights(
            relevance=1.0, recency=1.0, importance=1.0, pending=1.0
        ),
        recency_half_life_days=30.0,
    )

    score = score_context_item(candidate, context_query)

    assert score.relevance == 1.0
    assert score.recency == pytest.approx(0.5)
    assert score.importance == 0.75
    assert score.pending == 1.0
    assert score.total == pytest.approx((1.0 + 0.5 + 0.75 + 1.0) / 4.0)


def test_selection_respects_budget_and_can_skip_an_oversized_item() -> None:
    high_score_large = item(
        "large",
        "xerife cais " * 20,
        importance=1.0,
        pending=True,
    )
    lower_score_small = item("small", "cais", importance=0.2)
    context_query = query(token_budget=2, chars_per_token=4.0)

    result = assemble_context((lower_score_small, high_score_large), context_query)

    assert [entry.item.item_id for entry in result.selected] == ["small"]
    assert result.estimated_tokens <= 2
    assert result.omitted_item_ids == ("large",)


def test_equal_scores_use_item_id_as_deterministic_tie_breaker() -> None:
    a = item("a-item", "sem correspondência", occurred_at=None)
    b = item("b-item", "sem correspondência", occurred_at=None)
    context_query = query(query_text="outro", token_budget=100)

    forward = assemble_context([b, a], context_query)
    reverse = assemble_context([a, b], context_query)

    assert [entry.item.item_id for entry in forward.selected] == [
        "a-item",
        "b-item",
    ]
    assert [entry.item.item_id for entry in reverse.selected] == [
        "a-item",
        "b-item",
    ]


def test_catalog_priority_is_stable_without_displacing_general_context() -> None:
    catalog_first = item(
        "catalog:first",
        "fato de catálogo",
        selection_priority=1,
        importance=0.0,
        occurred_at=None,
    )
    generic_high_score = item(
        "memory:high-score",
        "xerife cais",
        importance=1.0,
        pending=True,
    )

    catalog_second = item(
        "catalog:second",
        "segundo fato",
        selection_priority=2,
        importance=1.0,
        occurred_at=None,
    )
    result = assemble_context(
        [catalog_second, catalog_first, generic_high_score],
        query(token_budget=100, chars_per_token=4.0),
    )

    assert [entry.item.item_id for entry in result.selected] == [
        "memory:high-score",
        "catalog:first",
        "catalog:second",
    ]


def test_required_canonical_context_is_reserved_before_optional_ranking() -> None:
    required_fact = item(
        "required-fact",
        "fato mecânico",
        layer=ContextLayer.CANONICAL_FACTS,
        required=True,
        importance=0.0,
        occurred_at=None,
    )
    tempting_memory = item(
        "tempting-memory",
        "xerife cais",
        importance=1.0,
        pending=True,
    )

    result = assemble_context(
        [tempting_memory, required_fact],
        query(token_budget=4, chars_per_token=4.0),
    )

    assert [entry.item.item_id for entry in result.selected] == ["required-fact"]
    assert result.omitted_item_ids == ("tempting-memory",)


def test_required_context_fails_instead_of_being_silently_omitted() -> None:
    required_fact = item(
        "required-fact",
        "fato canônico obrigatório",
        layer=ContextLayer.CANONICAL_FACTS,
        required=True,
    )

    with pytest.raises(ValueError, match="required canonical context"):
        assemble_context(
            [required_fact],
            query(token_budget=1, chars_per_token=4.0),
        )


def test_duplicate_visible_ids_are_rejected() -> None:
    first = item("duplicate", "cais")
    second = item("duplicate", "xerife")

    with pytest.raises(ValueError, match="item_id"):
        assemble_context([first, second], query())


def test_selected_context_remains_layered() -> None:
    hot = item("hot", "cais", layer=ContextLayer.HOT_SCENE)
    world = item("world", "xerife", layer=ContextLayer.WORLD_STATE)

    result = assemble_context([hot, world], query())
    grouped = result.by_layer()

    assert grouped[ContextLayer.HOT_SCENE][0].item.item_id == "hot"
    assert grouped[ContextLayer.WORLD_STATE][0].item.item_id == "world"


def test_token_estimate_is_deterministic_and_never_zero() -> None:
    assert estimate_tokens("", chars_per_token=4.0) == 1
    assert estimate_tokens("12345", chars_per_token=4.0) == 2
    with pytest.raises(ValueError):
        estimate_tokens("texto", chars_per_token=0)


def test_persisted_memory_restores_actor_place_and_time_before_final_ranking() -> None:
    recent = EpisodicMemory(
        memory_id="recent-matching",
        session_id="session",
        summary="Encontro político.",
        source_event_ids=("event-recent",),
        actors=(
            EntityReference(entity_id="xerife", entity_type="npc", label="Xerife"),
        ),
        place=EntityReference(entity_id="cais", entity_type="place", label="Cais"),
        occurred_at=NOW - timedelta(hours=1),
        importance=0.5,
    )
    old = EpisodicMemory(
        memory_id="old-unrelated",
        session_id="session",
        summary="Encontro político.",
        source_event_ids=("event-old",),
        actors=(EntityReference(entity_id="principe", entity_type="npc"),),
        place=EntityReference(entity_id="elysium", entity_type="place"),
        occurred_at=NOW - timedelta(days=90),
        importance=0.5,
    )

    recent_item = _stored_memory_context_item(
        {"payload": recent.model_dump(mode="json")}
    )
    old_item = _stored_memory_context_item({"payload": old.model_dump(mode="json")})
    assert recent_item is not None
    assert old_item is not None
    assert recent_item.occurred_at == recent.occurred_at
    assert recent_item.actors == recent.actors
    assert recent_item.place == recent.place

    result = assemble_context(
        [old_item, recent_item],
        ContextQuery(
            query_text="xerife cais",
            actor_ids=("xerife",),
            place_id="cais",
            now=NOW,
            token_budget=estimate_tokens(recent.summary),
        ),
    )
    assert [selected.item.item_id for selected in result.selected] == [
        "recent-matching"
    ]
