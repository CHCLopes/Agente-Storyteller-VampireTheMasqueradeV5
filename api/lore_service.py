from __future__ import annotations

from .catalog_models import CatalogContextCandidate, CatalogDomain, CatalogRelevanceSignals
from .rules_service import PlayerSheetModel, V5ActionPayload
from .turn_models import RecordReference, Visibility


def _source_ref(domain: CatalogDomain, entry_id: str) -> tuple[RecordReference, ...]:
    return (RecordReference(record_id=f"catalog:{domain.value}/{entry_id}", record_type="catalog_entry", relation="derived_from"),)


def get_contextual_lore_candidates(user_input: str, payload: V5ActionPayload, player_sheet: PlayerSheetModel) -> tuple[CatalogContextCandidate, ...]:
    """Produce typed candidates before ranking, budgeting, or truncation."""
    candidates: list[CatalogContextCandidate] = []
    if payload.is_feeding:
        from .physiology_service import get_predator_model
        pred = get_predator_model(player_sheet.predator_type)
        if pred:
            entry_id = player_sheet.predator_type
            candidates.append(CatalogContextCandidate(domain=CatalogDomain.PREDATOR_TYPE, entry_id=entry_id, minimal_text=f"Predador ({entry_id}): {pred.narrative_data.hunting_method}", visibility=Visibility.PLAYER, signals=CatalogRelevanceSignals(rule_triggered=True), importance=0.8, source_refs=_source_ref(CatalogDomain.PREDATOR_TYPE, entry_id)))

    from .clan_service import get_clan_narrative
    clan_data = get_clan_narrative(player_sheet.clan)
    if clan_data:
        entry_id = player_sheet.clan
        candidates.append(CatalogContextCandidate(domain=CatalogDomain.CLAN, entry_id=entry_id, minimal_text=f"Clã ({entry_id}): {clan_data.lore_summary} Perdição: {clan_data.bane_description} Compulsão: {clan_data.compulsion_description} {clan_data.narrator_enforcement}", visibility=Visibility.PLAYER, signals=CatalogRelevanceSignals(text_relevant=True), importance=0.6, source_refs=_source_ref(CatalogDomain.CLAN, entry_id)))

    if payload.power_used:
        from .discipline_service import get_discipline_model
        power_data = get_discipline_model(payload.power_used)
        if power_data:
            entry_id = payload.power_used
            candidates.append(CatalogContextCandidate(domain=CatalogDomain.DISCIPLINE_POWER, entry_id=entry_id, minimal_text=f"Disciplina ({entry_id}): {power_data.narrative_data.visual_manifestation} Risco: {power_data.narrative_data.masquerade_threat}", visibility=Visibility.PLAYER, signals=CatalogRelevanceSignals(explicitly_selected=True, rule_triggered=True), importance=0.9, source_refs=_source_ref(CatalogDomain.DISCIPLINE_POWER, entry_id)))

    if payload.weapon_category:
        from .combat_service import get_weapon_model
        entry_id = payload.weapon_category.value
        weapon_data = get_weapon_model(entry_id)
        if weapon_data:
            candidates.append(CatalogContextCandidate(domain=CatalogDomain.WEAPON, entry_id=entry_id, minimal_text=f"Arma ({entry_id}): {weapon_data.narrative_data.description} Impacto: {weapon_data.narrative_data.impact_flavor} Máscara: {weapon_data.narrative_data.masquerade_threat}", visibility=Visibility.PLAYER, signals=CatalogRelevanceSignals(explicitly_selected="weapon_category" in payload.model_fields_set, rule_triggered=payload.is_aggressive), importance=0.7, source_refs=_source_ref(CatalogDomain.WEAPON, entry_id)))

    from .npc_service import find_npc_ids, get_npc_model
    for entry_id in find_npc_ids(user_input):
        npc_data = get_npc_model(entry_id)
        if npc_data:
            candidates.append(CatalogContextCandidate(domain=CatalogDomain.NPC_ARCHETYPE, entry_id=entry_id, minimal_text=f"NPC ({entry_id}): {npc_data.narrative_data.social_standing} Tática: {npc_data.narrative_data.combat_tactics}", visibility=Visibility.PLAYER, signals=CatalogRelevanceSignals(explicitly_mentioned=True), importance=npc_data.engine_data.threat_level / 5, source_refs=_source_ref(CatalogDomain.NPC_ARCHETYPE, entry_id)))
    return tuple(candidates)


def project_contextual_lore(candidates: tuple[CatalogContextCandidate, ...]) -> str:
    """Temporary textual compatibility projection; selection happens later."""
    if not candidates:
        return ""
    return "[CONTEXTO DE MUNDO]:\n" + "".join(f"- {candidate.minimal_text}\n" for candidate in candidates)


def get_contextual_lore(user_input: str, payload: V5ActionPayload, player_sheet: PlayerSheetModel) -> str:
    return project_contextual_lore(get_contextual_lore_candidates(user_input, payload, player_sheet))
