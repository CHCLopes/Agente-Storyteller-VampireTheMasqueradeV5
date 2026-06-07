import re
import os
import json
from .rules_service import PlayerSheetModel, V5ActionPayload

_CACHE = {}

def _load_catalog(name: str) -> dict:
    if name not in _CACHE:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalogs", f"{name}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _CACHE[name] = json.load(f)
        except Exception:
            _CACHE[name] = {}
    return _CACHE[name]

def get_contextual_lore(user_input: str, payload: V5ActionPayload, player_sheet: PlayerSheetModel) -> str:
    blocks = []
    
    if payload.is_feeding:
        from .physiology_service import get_predator_model
        pred = get_predator_model(player_sheet.predator_type)
        if pred:
            blocks.append(f"Predador ({player_sheet.predator_type}): {pred.narrative_data.hunting_method}")
            
    from .clan_service import get_clan_narrative
    clan_data = get_clan_narrative(player_sheet.clan)
    if clan_data:
        blocks.append(f"Clã ({player_sheet.clan}): {clan_data.lore_summary} Perdição: {clan_data.bane_description} Compulsão: {clan_data.compulsion_description} {clan_data.narrator_enforcement}")
        
    if payload.power_used:
        from .discipline_service import get_discipline_model
        power_data = get_discipline_model(payload.power_used)
        if power_data:
            blocks.append(f"Disciplina ({payload.power_used}): {power_data.narrative_data.visual_manifestation} Risco: {power_data.narrative_data.masquerade_threat}")
            
    if payload.weapon_category:
        from .combat_service import get_weapon_model
        weapon_data = get_weapon_model(payload.weapon_category.value)
        if weapon_data:
            blocks.append(f"Arma ({payload.weapon_category.value}): {weapon_data.narrative_data.description} Impacto: {weapon_data.narrative_data.impact_flavor} Máscara: {weapon_data.narrative_data.masquerade_threat}")
            
    from .npc_service import get_all_npcs
    npcs = get_all_npcs()
    npc_keywords = []
    
    # Simple regex to find words like "principe", "xerife" without accents
    normalized_input = user_input.lower()
    normalized_input = normalized_input.replace('í', 'i').replace('ç', 'c')
    
    for npc_key in npcs.keys():
        if re.search(r'\b' + re.escape(npc_key) + r'\b', normalized_input):
            npc_keywords.append(npc_key)
            
    if npc_keywords:
        npc_keywords.sort(key=lambda k: npcs[k].engine_data.threat_level, reverse=True)
        top_npc = npc_keywords[0]
        npc_data = npcs[top_npc]
        blocks.append(f"NPC ({top_npc}): {npc_data.narrative_data.social_standing} Tática: {npc_data.narrative_data.combat_tactics}")
        
    limited_blocks = blocks[:3]
    if not limited_blocks:
        return ""
        
    lore_text = "[CONTEXTO DE MUNDO]:\n"
    for b in limited_blocks:
        lore_text += f"- {b}\n"
        
    return lore_text
