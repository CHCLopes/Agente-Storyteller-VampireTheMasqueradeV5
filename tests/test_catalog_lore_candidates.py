from api.catalog_models import CatalogDomain
from api.lore_service import get_contextual_lore_candidates, project_contextual_lore
from api.rules_service import PlayerSheetModel, V5ActionPayload


def _sheet() -> PlayerSheetModel:
    return PlayerSheetModel(clan="brujah", predator_type="alleycat", attributes={"Strength": 3}, skills={"Brawl": 2}, disciplines={"feral_weapons": 2}, status={"blood_potency": 1, "current_hunger": 1, "humanity": 7, "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0}, "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}})


def test_candidates_are_produced_before_any_cut() -> None:
    payload = V5ActionPayload(intent="Ataco o prince diante do sheriff", attribute="Strength", skill="Brawl", power_used="feral_weapons", weapon_category="unarmed", is_aggressive=True)
    candidates = get_contextual_lore_candidates("Ataco o prince diante do sheriff", payload, _sheet())
    assert [(item.domain, item.entry_id) for item in candidates] == [(CatalogDomain.CLAN, "brujah"), (CatalogDomain.DISCIPLINE_POWER, "feral_weapons"), (CatalogDomain.WEAPON, "unarmed"), (CatalogDomain.NPC_ARCHETYPE, "prince"), (CatalogDomain.NPC_ARCHETYPE, "sheriff")]
    assert all(candidate.source_refs for candidate in candidates)
    projected = project_contextual_lore(candidates)
    assert "NPC (prince)" in projected and "NPC (sheriff)" in projected


def test_candidate_signals_preserve_reason_without_selecting() -> None:
    payload = V5ActionPayload(intent="Ativo Armas Ferais", attribute="Strength", skill="Brawl", power_used="feral_weapons", is_aggressive=True)
    candidates = get_contextual_lore_candidates("Ativo Armas Ferais", payload, _sheet())
    power = next(item for item in candidates if item.domain is CatalogDomain.DISCIPLINE_POWER)
    assert power.signals.explicitly_selected is True
    assert power.signals.rule_triggered is True
