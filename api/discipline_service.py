from pydantic import BaseModel, Field
from typing import Optional
import os
import json

class DisciplineEngineData(BaseModel):
    rouse_cost: int = Field(ge=0, le=3)
    scaling_stat: Optional[str] = None
    dice_bonus_stat: Optional[str] = None
    is_aggravated: bool
    amalgam_req: list[str]

class DisciplineNarrativeData(BaseModel):
    visual_manifestation: str
    masquerade_threat: str

class DisciplineModel(BaseModel):
    engine_data: DisciplineEngineData
    narrative_data: DisciplineNarrativeData

class PowerModifiers(BaseModel):
    dice_bonus: int
    is_bane: bool
    weapon_damage_bonus: int

_DISCIPLINES_CACHE: dict[str, DisciplineModel] = {}

def load_disciplines_catalog():
    global _DISCIPLINES_CACHE
    if _DISCIPLINES_CACHE: return
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalogs", "disciplines.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for key, val in data.items():
            _DISCIPLINES_CACHE[key] = DisciplineModel(**val)

def get_discipline_model(power_name: str) -> DisciplineModel | None:
    load_disciplines_catalog()
    return _DISCIPLINES_CACHE.get(power_name.lower())

def _sanitize_power_name(power_name: str | None) -> str | None:
    if not power_name:
        return None
    return power_name.strip().lower().replace(" ", "_")

def get_power_cost(power_name: str | None) -> int:
    sanitized = _sanitize_power_name(power_name)
    if not sanitized: return 0
    power = get_discipline_model(sanitized)
    if power:
        return power.engine_data.rouse_cost
    return 0

def apply_power_modifiers(power_name: str | None, current_is_bane: bool, player_sheet: dict) -> PowerModifiers:
    sanitized = _sanitize_power_name(power_name)
    if not sanitized:
        return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)

    power = get_discipline_model(sanitized)
    if not power:
        return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)
        
    for req in power.engine_data.amalgam_req:
        if req.lower() not in [d.lower() for d in player_sheet.get("disciplines", {}).keys()]:
            return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)
            
    is_bane = current_is_bane
    if power.engine_data.is_aggravated:
        is_bane = True
        
    dice_bonus = 0
    if power.engine_data.scaling_stat:
        # Some scale with attribute, some with discipline. 
        # V5 usually scales with discipline. But awe scales with presence.
        dice_bonus += player_sheet.get("disciplines", {}).get(power.engine_data.scaling_stat.capitalize(), player_sheet.get("disciplines", {}).get(power.engine_data.scaling_stat.lower(), 0))
        if dice_bonus == 0:
            dice_bonus += player_sheet.get("attributes", {}).get(power.engine_data.scaling_stat.capitalize(), 0)
            
    weapon_bonus = 0
    # Add flat weapon damage bonus depending on the power. Feral Weapons usually gives +2.
    if sanitized == "feral_weapons": weapon_bonus = 2
    elif sanitized == "soaring_leap": dice_bonus = player_sheet.get("disciplines", {}).get("potence", 2)
    elif sanitized == "awe": dice_bonus = player_sheet.get("disciplines", {}).get("presence", 2)

    return PowerModifiers(dice_bonus=dice_bonus, is_bane=is_bane, weapon_damage_bonus=weapon_bonus)
