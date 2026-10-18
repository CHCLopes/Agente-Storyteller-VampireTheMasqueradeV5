"""Deterministic, visibility-safe assembly of layered narrative context."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from typing import Annotated

from .turn_models import EntityReference, RecordReference, Visibility


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenContextModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContextLayer(str, Enum):
    CANONICAL_FACTS = "canonical_facts"
    HOT_SCENE = "hot_scene"
    EPISODIC_MEMORY = "episodic_memory"
    WORLD_STATE = "world_state"
    OPEN_THREADS = "open_threads"


class ContextItem(FrozenContextModel):
    item_id: NonEmptyStr
    layer: ContextLayer
    content: NonEmptyStr
    visibility: Visibility = Visibility.PLAYER
    occurred_at: datetime | None = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    required: bool = False
    selection_priority: int | None = Field(default=None, ge=1)
    pending: bool = False
    tags: tuple[NonEmptyStr, ...] = ()
    actors: tuple[EntityReference, ...] = ()
    place: EntityReference | None = None
    source_refs: tuple[RecordReference, ...] = ()

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include timezone information")
        return value


class ContextScoringWeights(FrozenContextModel):
    """Explicit weights avoid hiding product policy in the scoring function."""

    relevance: float = Field(default=1.0, ge=0.0)
    recency: float = Field(default=1.0, ge=0.0)
    importance: float = Field(default=1.0, ge=0.0)
    pending: float = Field(default=1.0, ge=0.0)

    def total(self) -> float:
        return self.relevance + self.recency + self.importance + self.pending


class ContextQuery(FrozenContextModel):
    query_text: str = ""
    tags: tuple[NonEmptyStr, ...] = ()
    actor_ids: tuple[NonEmptyStr, ...] = ()
    place_id: NonEmptyStr | None = None
    allowed_visibilities: frozenset[Visibility] = Field(
        default_factory=lambda: frozenset({Visibility.PUBLIC, Visibility.PLAYER})
    )
    now: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    token_budget: int = Field(ge=0)
    chars_per_token: float = Field(default=4.0, gt=0.0)
    recency_half_life_days: float = Field(default=30.0, gt=0.0)
    weights: ContextScoringWeights = Field(default_factory=ContextScoringWeights)

    @field_validator("now")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include timezone information")
        return value

    @field_validator("allowed_visibilities")
    @classmethod
    def require_visible_scope(
        cls, value: frozenset[Visibility]
    ) -> frozenset[Visibility]:
        if not value:
            raise ValueError("allowed_visibilities cannot be empty")
        return value


class ScoreBreakdown(FrozenContextModel):
    relevance: float = Field(ge=0.0, le=1.0)
    recency: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    pending: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)


class SelectedContextItem(FrozenContextModel):
    item: ContextItem
    score: ScoreBreakdown
    estimated_tokens: int = Field(ge=1)


class LayeredContext(FrozenContextModel):
    selected: tuple[SelectedContextItem, ...] = ()
    estimated_tokens: int = Field(default=0, ge=0)
    omitted_item_ids: tuple[NonEmptyStr, ...] = ()

    def by_layer(self) -> dict[ContextLayer, tuple[SelectedContextItem, ...]]:
        """Return selected items grouped without changing their ranked order."""

        grouped: dict[ContextLayer, list[SelectedContextItem]] = {}
        for selected_item in self.selected:
            grouped.setdefault(selected_item.item.layer, []).append(selected_item)
        return {layer: tuple(items) for layer, items in grouped.items()}


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """Conservative deterministic estimate; exact tokenizer is provider-specific."""

    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be greater than zero")
    normalized = text.strip()
    if not normalized:
        return 1
    return max(1, math.ceil(len(normalized) / chars_per_token))


def score_context_item(item: ContextItem, query: ContextQuery) -> ScoreBreakdown:
    """Score an already-authorized item using four explicit product signals."""

    relevance = _relevance_score(item, query)
    recency = _recency_score(item.occurred_at, query)
    pending = 1.0 if item.pending else 0.0
    weight_total = query.weights.total()
    if weight_total == 0:
        total = 0.0
    else:
        total = (
            relevance * query.weights.relevance
            + recency * query.weights.recency
            + item.importance * query.weights.importance
            + pending * query.weights.pending
        ) / weight_total

    return ScoreBreakdown(
        relevance=relevance,
        recency=recency,
        importance=item.importance,
        pending=pending,
        total=max(0.0, min(1.0, total)),
    )


def assemble_context(
    items: list[ContextItem] | tuple[ContextItem, ...], query: ContextQuery
) -> LayeredContext:
    """Select authorized context under budget with deterministic ranking.

    Visibility is checked before token estimation and scoring so secret content
    cannot influence rankings, omissions, or budget consumption for an audience
    that is not allowed to know it.
    """

    visible_items = [
        item for item in items if item.visibility in query.allowed_visibilities
    ]
    visible_ids = [item.item_id for item in visible_items]
    if len(visible_ids) != len(set(visible_ids)):
        raise ValueError("visible context item_id values must be unique")

    ranked: list[SelectedContextItem] = []
    for item in visible_items:
        token_count = estimate_tokens(item.content, query.chars_per_token)
        ranked.append(
            SelectedContextItem(
                item=item,
                score=score_context_item(item, query),
                estimated_tokens=token_count,
            )
        )

    required = sorted(
        (candidate for candidate in ranked if candidate.item.required),
        key=lambda candidate: candidate.item.item_id,
    )
    optional = sorted(
        (candidate for candidate in ranked if not candidate.item.required),
        key=lambda candidate: (
            candidate.item.selection_priority is not None,
            (
                -candidate.score.total
                if candidate.item.selection_priority is None
                else 0.0
            ),
            candidate.item.selection_priority or 0,
            candidate.item.item_id,
        ),
    )
    required_tokens = sum(candidate.estimated_tokens for candidate in required)
    if required_tokens > query.token_budget:
        raise ValueError(
            "required canonical context exceeds the configured token budget"
        )

    selected: list[SelectedContextItem] = list(required)
    omitted: list[str] = []
    consumed = required_tokens
    for candidate in optional:
        if consumed + candidate.estimated_tokens <= query.token_budget:
            selected.append(candidate)
            consumed += candidate.estimated_tokens
        else:
            omitted.append(candidate.item.item_id)

    return LayeredContext(
        selected=tuple(selected),
        estimated_tokens=consumed,
        omitted_item_ids=tuple(omitted),
    )


def _relevance_score(item: ContextItem, query: ContextQuery) -> float:
    query_tokens = _tokens(query.query_text)
    query_tokens.update(_tokens(" ".join(query.tags)))
    query_tokens.update(_tokens(" ".join(query.actor_ids)))
    if query.place_id:
        query_tokens.update(_tokens(query.place_id))

    if not query_tokens:
        return 0.0

    item_tokens = _tokens(item.content)
    item_tokens.update(_tokens(" ".join(item.tags)))
    item_tokens.update(_tokens(" ".join(actor.entity_id for actor in item.actors)))
    item_tokens.update(
        _tokens(" ".join(actor.label or "" for actor in item.actors))
    )
    if item.place:
        item_tokens.update(_tokens(item.place.entity_id))
        item_tokens.update(_tokens(item.place.label or ""))

    return len(query_tokens & item_tokens) / len(query_tokens)


def _recency_score(occurred_at: datetime | None, query: ContextQuery) -> float:
    if occurred_at is None:
        return 0.0
    age_seconds = max(0.0, (query.now - occurred_at).total_seconds())
    age_days = age_seconds / 86_400.0
    return 1.0 / (1.0 + age_days / query.recency_half_life_days)


def _tokens(value: str) -> set[str]:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return set(re.findall(r"[a-z0-9_]+", without_accents))
