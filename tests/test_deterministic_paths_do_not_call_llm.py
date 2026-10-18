from api.catalog_models import CatalogContextCandidate, CatalogDomain
from api.catalog_selection_service import select_catalog_context
from api.catalog_service import get_catalog_registry, lookup_catalog_lore
from api.combat_service import calculate_damage
from api.core.config import settings
from api.progression_service import calculate_upgrade_cost
from api.rules_service import PlayerSheetModel


def test_catalog_rules_progression_and_selection_never_resolve_llm_runtime(monkeypatch) -> None:
    def forbidden_runtime():
        raise AssertionError("deterministic path attempted to resolve an LLM runtime")

    monkeypatch.setattr("api.llm.runtime.get_llm_runtime", forbidden_runtime)
    registry = get_catalog_registry()
    assert registry.require(CatalogDomain.CLAN, "brujah")
    assert lookup_catalog_lore("O que devo saber sobre os Brujah?").status == "covered"
    assert calculate_damage(3, "unarmed", False, False).total_damage == 3
    assert calculate_upgrade_cost("attribute", 3) == 15
    assert select_catalog_context(
        (CatalogContextCandidate(domain=CatalogDomain.CLAN, entry_id="brujah", minimal_text="Brujah"),),
        token_budget=10,
    ).selected
    assert PlayerSheetModel(
        clan="brujah", predator_type="alleycat", attributes={"Strength": 2},
        skills={"Brawl": 2}, disciplines={},
        status={"blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}},
    )


def test_default_topology_keeps_h0_h1_local_and_h4_action_disabled() -> None:
    assert settings.llm_h0_enabled is False
    assert settings.llm_h1_enabled is False
    assert settings.llm_h4_action_enrichment_enabled is False
