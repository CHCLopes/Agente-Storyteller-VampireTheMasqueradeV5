from pydantic import BaseModel
import math
from enum import Enum

from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry

class WeaponTypeEnum(str, Enum):
    BRAWL = "BRAWL"
    MELEE = "MELEE"
    RANGED = "RANGED"

class WeaponEngineData(BaseModel):
    damage_modifier: int
    is_concealable: bool
    weapon_type: WeaponTypeEnum
    is_aggravated_to_vampires: bool

class WeaponNarrativeData(BaseModel):
    description: str
    impact_flavor: str
    masquerade_threat: str

class WeaponModel(BaseModel):
    engine_data: WeaponEngineData
    narrative_data: WeaponNarrativeData

class TrackerResult(BaseModel):
    superficial_damage: int
    aggravated_damage: int
    is_incapacitated: bool

class DamageResult(BaseModel):
    total_damage: int
    damage_type: str

def load_weapons_catalog():
    get_catalog_registry()

def get_weapon_model(category: str) -> WeaponModel | None:
    record = get_catalog_registry().get(CatalogDomain.WEAPON, category)
    return WeaponModel.model_validate(record.payload) if record else None

def calculate_damage(margin: int, weapon_category: str, is_bane: bool, is_supernatural_target: bool, weapon_damage_bonus: int = 0, is_true_faith_active: bool = False, unhalved_superficial_to_vampires: bool = False) -> DamageResult:
    weapon = get_weapon_model(weapon_category)
    if weapon is None:
        raise ValueError(f"unknown weapon catalog entry: {weapon_category}")
    weapon_val = weapon.engine_data.damage_modifier
    is_aggravated_to_vampires = weapon.engine_data.is_aggravated_to_vampires
    
    if weapon_category.lower() == "holy_artifact" and is_true_faith_active:
        is_aggravated_to_vampires = True
        weapon_val += 2

    total_base_damage = margin + weapon_val + weapon_damage_bonus
    
    if is_supernatural_target:
        if is_bane or is_aggravated_to_vampires:
            return DamageResult(total_damage=total_base_damage, damage_type="aggravated")
        elif not unhalved_superficial_to_vampires:
            reduced = math.ceil(total_base_damage / 2)
            return DamageResult(total_damage=reduced, damage_type="superficial")
        else:
            return DamageResult(total_damage=total_base_damage, damage_type="superficial")
    else:
        return DamageResult(total_damage=total_base_damage, damage_type="superficial")

def apply_damage_to_tracker(tracker_size: int, superficial: int, aggravated: int, incoming_damage: int, damage_type: str) -> TrackerResult:
    sup = superficial
    agg = aggravated
    is_incapacitated = False
    
    for _ in range(incoming_damage):
        if agg >= tracker_size:
            is_incapacitated = True
            break
            
        if damage_type == "superficial":
            if sup + agg < tracker_size:
                sup += 1
            else:
                if sup > 0:
                    sup -= 1
                    agg += 1
                else:
                    is_incapacitated = True
                    break
        elif damage_type == "aggravated":
            if sup + agg < tracker_size:
                agg += 1
            else:
                if sup > 0:
                    sup -= 1
                    agg += 1
                else:
                    is_incapacitated = True
                    break
                    
    return TrackerResult(
        superficial_damage=sup,
        aggravated_damage=agg,
        is_incapacitated=is_incapacitated
    )
