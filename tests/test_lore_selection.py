from api.catalog_models import CatalogDomain
from api.catalog_selection_service import select_catalog_context
from api.lore_service import get_contextual_lore_candidates
from api.rules_service import PlayerSheetModel, V5ActionPayload


def sheet() -> PlayerSheetModel:
    return PlayerSheetModel(
        clan="brujah", predator_type="alleycat",
        attributes={"Strength": 3, "Wits": 3},
        skills={"Brawl": 2, "Investigation": 2},
        disciplines={"feral_weapons": 2},
        status={"blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}},
    )


def test_combined_catalog_context_is_ranked_before_budget_omission() -> None:
    payload = V5ActionPayload(
        intent="Ataco", attribute="Strength", skill="Brawl",
        power_used="feral_weapons", weapon_category="unarmed", is_aggressive=True,
    )
    candidates = get_contextual_lore_candidates(
        "Ataco o príncipe diante do xerife", payload, sheet()
    )
    assert {(item.domain, item.entry_id) for item in candidates} == {
        (CatalogDomain.CLAN, "brujah"),
        (CatalogDomain.DISCIPLINE_POWER, "feral_weapons"),
        (CatalogDomain.WEAPON, "unarmed"),
        (CatalogDomain.NPC_ARCHETYPE, "prince"),
        (CatalogDomain.NPC_ARCHETYPE, "sheriff"),
    }
    first = select_catalog_context(candidates, token_budget=45, chars_per_token=4.0)
    second = select_catalog_context(tuple(reversed(candidates)), token_budget=45, chars_per_token=4.0)
    assert [item.entry_id for item in first.selected] == [item.entry_id for item in second.selected]
    assert [(item.item_id, item.priority_position) for item in first.omissions] == [
        (item.item_id, item.priority_position) for item in second.omissions
    ]


def test_irrelevant_default_unarmed_is_excluded_but_aggressive_unarmed_competes() -> None:
    investigation = V5ActionPayload(
        intent="Investigo", attribute="Wits", skill="Investigation", is_aggressive=False
    )
    quiet = get_contextual_lore_candidates("Investigo a sala", investigation, sheet())
    quiet_result = select_catalog_context(quiet, token_budget=1000)
    assert all(item.entry_id != "unarmed" for item in quiet_result.selected)

    combat = V5ActionPayload(
        intent="Ataco", attribute="Strength", skill="Brawl",
        weapon_category="unarmed", is_aggressive=True,
    )
    active = get_contextual_lore_candidates("Ataco desarmado", combat, sheet())
    active_result = select_catalog_context(active, token_budget=1000)
    assert any(item.entry_id == "unarmed" for item in active_result.selected)
