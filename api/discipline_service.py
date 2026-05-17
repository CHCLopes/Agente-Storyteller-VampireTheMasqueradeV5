from pydantic import BaseModel

POWER_CATALOG = {
    "feral_weapons": {"rouse_cost": 1, "scaling_stat": None, "weapon_damage_bonus": 2, "is_bane": True},
    "soaring_leap": {"rouse_cost": 1, "scaling_stat": None, "weapon_damage_bonus": 0, "is_bane": False},
    "awe": {"rouse_cost": 0, "scaling_stat": "Charisma", "weapon_damage_bonus": 0, "is_bane": False}
}

class PowerModifiers(BaseModel):
    dice_bonus: int
    weapon_damage_bonus: int
    is_bane: bool

def _sanitize_power_name(power_name: str | None) -> str | None:
    if not power_name:
        return None
    return power_name.strip().lower().replace(" ", "_")

def get_power_cost(power_name: str | None) -> int:
    sanitized = _sanitize_power_name(power_name)
    if not sanitized or sanitized not in POWER_CATALOG:
        return 0
    return POWER_CATALOG[sanitized].get("rouse_cost", 0)

def apply_power_modifiers(power_name: str | None, current_is_bane: bool, player_sheet: dict) -> PowerModifiers:
    sanitized = _sanitize_power_name(power_name)
    if not sanitized or sanitized not in POWER_CATALOG:
        return PowerModifiers(dice_bonus=0, weapon_damage_bonus=0, is_bane=current_is_bane)
    
    catalog_entry = POWER_CATALOG[sanitized]
    
    dice_bonus = 0
    scaling_stat = catalog_entry.get("scaling_stat")
    if scaling_stat and player_sheet:
        dice_bonus = player_sheet.get("attributes", {}).get(scaling_stat, 0)
    
    power_is_bane = catalog_entry.get("is_bane", False)
    final_is_bane = True if power_is_bane else current_is_bane
    
    return PowerModifiers(
        dice_bonus=dice_bonus,
        weapon_damage_bonus=catalog_entry.get("weapon_damage_bonus", 0),
        is_bane=final_is_bane
    )
