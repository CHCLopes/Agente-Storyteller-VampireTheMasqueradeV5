import os
import json
from .rules_service import PlayerSheetModel

_PROGRESSION_COSTS_CACHE = {}

def load_progression_costs():
    global _PROGRESSION_COSTS_CACHE
    if not _PROGRESSION_COSTS_CACHE:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "data", "catalogs", "progression_costs.json")
        with open(path, "r", encoding="utf-8") as f:
            _PROGRESSION_COSTS_CACHE = json.load(f)

def award_session_xp(player_sheet: PlayerSheetModel, amount: int = 1) -> PlayerSheetModel:
    player_sheet.available_xp += amount
    return player_sheet

def calculate_upgrade_cost(trait_category: str, new_level: int) -> int:
    load_progression_costs()
    cost_data = _PROGRESSION_COSTS_CACHE.get(trait_category)
    if not cost_data:
        return 0
    
    return cost_data["base_cost"] + (cost_data["cost_multiplier"] * new_level)

def purchase_upgrade(player_sheet: PlayerSheetModel, trait_category: str, trait_name: str, new_level: int) -> tuple[bool, PlayerSheetModel]:
    cost = calculate_upgrade_cost(trait_category, new_level)
    
    if player_sheet.available_xp < cost:
        return False, player_sheet
        
    player_sheet.available_xp -= cost
    player_sheet.spent_xp += cost
    
    if trait_category == "attribute":
        player_sheet.attributes[trait_name] = new_level
    elif trait_category == "skill":
        player_sheet.skills[trait_name] = new_level
    elif trait_category in ["clan_discipline", "out_of_clan_discipline", "caitiff_discipline"]:
        player_sheet.disciplines[trait_name] = new_level
    elif trait_category == "blood_potency":
        player_sheet.status.blood_potency = new_level
        
    return True, player_sheet
