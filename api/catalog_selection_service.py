from __future__ import annotations

from .catalog_models import (
    CatalogContextCandidate,
    CatalogContextOmission,
    CatalogContextSelection,
    CatalogDomain,
)
from .context_service import estimate_tokens


POLICY_VERSION = "catalog-context-selection.v1"


def _item_id(candidate: CatalogContextCandidate) -> str:
    return f"catalog:{candidate.domain.value}/{candidate.entry_id}"


def _priority(candidate: CatalogContextCandidate) -> tuple:
    signals = candidate.signals
    return (
        not candidate.required,
        not (signals.explicitly_mentioned or signals.explicitly_selected),
        not signals.rule_triggered,
        not signals.active_in_scene,
        not signals.text_relevant,
        -candidate.importance,
        candidate.domain.value,
        candidate.entry_id,
    )


def _ranked_and_excluded(
    candidates: tuple[CatalogContextCandidate, ...],
) -> tuple[tuple[CatalogContextCandidate, ...], tuple[CatalogContextCandidate, ...]]:
    unique_ids = [_item_id(candidate) for candidate in candidates]
    if len(unique_ids) != len(set(unique_ids)):
        raise ValueError("catalog candidate IDs must be unique")

    eligible: list[CatalogContextCandidate] = []
    excluded: list[CatalogContextCandidate] = []
    for candidate in candidates:
        signals = candidate.signals
        irrelevant_unarmed = (
            candidate.domain is CatalogDomain.WEAPON
            and candidate.entry_id == "unarmed"
            and not signals.explicitly_selected
            and not signals.rule_triggered
        )
        (excluded if irrelevant_unarmed else eligible).append(candidate)
    return tuple(sorted(eligible, key=_priority)), tuple(sorted(excluded, key=_priority))


def rank_catalog_context_candidates(
    candidates: tuple[CatalogContextCandidate, ...],
) -> tuple[CatalogContextCandidate, ...]:
    """Return every eligible candidate in policy order without applying a budget."""

    ranked, _ = _ranked_and_excluded(candidates)
    return ranked


def select_catalog_context(
    candidates: tuple[CatalogContextCandidate, ...],
    *,
    token_budget: int,
    chars_per_token: float = 4.0,
) -> CatalogContextSelection:
    if token_budget < 0:
        raise ValueError("token_budget must be non-negative")

    ranked, excluded = _ranked_and_excluded(candidates)
    required_tokens = sum(
        estimate_tokens(candidate.minimal_text, chars_per_token)
        for candidate in ranked
        if candidate.required
    )
    if required_tokens > token_budget:
        raise ValueError("required catalog context exceeds the configured token budget")

    selected: list[CatalogContextCandidate] = []
    omissions: list[CatalogContextOmission] = []
    consumed = 0
    for position, candidate in enumerate(ranked, start=1):
        tokens = estimate_tokens(candidate.minimal_text, chars_per_token)
        if candidate.required or consumed + tokens <= token_budget:
            selected.append(candidate)
            consumed += tokens
        else:
            omissions.append(CatalogContextOmission(item_id=_item_id(candidate), reason="budget", estimated_tokens=tokens, priority_position=position))

    offset = len(ranked)
    for index, candidate in enumerate(excluded, start=1):
        omissions.append(CatalogContextOmission(item_id=_item_id(candidate), reason="irrelevant_default_weapon", estimated_tokens=estimate_tokens(candidate.minimal_text, chars_per_token), priority_position=offset + index))

    return CatalogContextSelection(
        policy_version=POLICY_VERSION,
        selected=tuple(selected),
        omissions=tuple(omissions),
        estimated_tokens=consumed,
    )
