import pytest

from api.catalog_models import (
    CatalogContextCandidate,
    CatalogDomain,
    CatalogRelevanceSignals,
)
from api.catalog_selection_service import (
    POLICY_VERSION,
    rank_catalog_context_candidates,
    select_catalog_context,
)


def candidate(entry_id: str, *, domain=CatalogDomain.NPC_ARCHETYPE, required=False, importance=0.5, **signals):
    return CatalogContextCandidate(
        domain=domain,
        entry_id=entry_id,
        minimal_text=f"{entry_id} contexto",
        required=required,
        importance=importance,
        signals=CatalogRelevanceSignals(**signals),
    )


def test_policy_orders_explicit_rule_scene_text_importance_and_id() -> None:
    candidates = (
        candidate("zeta", importance=1.0),
        candidate("text", text_relevant=True),
        candidate("scene", active_in_scene=True),
        candidate("rule", rule_triggered=True),
        candidate("selected", explicitly_selected=True),
        candidate("mentioned", explicitly_mentioned=True, importance=0.7),
        candidate("required", required=True),
        candidate("alpha", importance=1.0),
    )
    result = select_catalog_context(candidates, token_budget=100)
    assert result.policy_version == POLICY_VERSION
    assert [item.entry_id for item in result.selected] == [
        "required", "mentioned", "selected", "rule", "scene", "text", "alpha", "zeta"
    ]

    ranked_without_budget = rank_catalog_context_candidates(candidates)
    assert [item.entry_id for item in ranked_without_budget] == [
        "required", "mentioned", "selected", "rule", "scene", "text", "alpha", "zeta"
    ]


def test_irrelevant_default_unarmed_is_omitted_even_with_budget() -> None:
    result = select_catalog_context(
        (candidate("unarmed", domain=CatalogDomain.WEAPON),), token_budget=100
    )
    assert result.selected == ()
    assert result.omissions[0].reason == "irrelevant_default_weapon"
    assert result.omissions[0].item_id == "catalog:weapon/unarmed"


@pytest.mark.parametrize("signal", ("explicitly_selected", "rule_triggered"))
def test_relevant_unarmed_can_compete_for_budget(signal) -> None:
    result = select_catalog_context(
        (candidate("unarmed", domain=CatalogDomain.WEAPON, **{signal: True}),),
        token_budget=100,
    )
    assert [item.entry_id for item in result.selected] == ["unarmed"]


def test_budget_omission_is_safe_auditable_and_stable() -> None:
    candidates = (candidate("beta"), candidate("alpha"))
    result = select_catalog_context(candidates, token_budget=4, chars_per_token=4.0)
    assert [item.entry_id for item in result.selected] == ["alpha"]
    assert [(item.item_id, item.reason, item.priority_position) for item in result.omissions] == [("catalog:npc_archetype/beta", "budget", 2)]
    assert result.omissions[0].estimated_tokens >= 1


def test_required_context_fails_closed_when_budget_is_too_small() -> None:
    with pytest.raises(ValueError, match="required catalog context"):
        select_catalog_context((candidate("required", required=True),), token_budget=0)


def test_duplicate_candidate_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        select_catalog_context((candidate("prince"), candidate("prince")), token_budget=100)
