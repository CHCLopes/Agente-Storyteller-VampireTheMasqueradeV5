from pydantic import BaseModel
import math

class TrackerResult(BaseModel):
    superficial_damage: int
    aggravated_damage: int
    is_incapacitated: bool

class DamageResult(BaseModel):
    total_damage: int
    damage_type: str

WEAPON_MODIFIERS = {
    "UNARMED": 0,
    "LIGHT": 1,
    "MEDIUM": 2,
    "HEAVY": 3,
    "DESTRUCTIVE": 4
}

def calculate_damage(margin: int, weapon_category: str, is_bane: bool, is_target_vampire: bool, weapon_damage_bonus: int = 0) -> DamageResult:
    weapon_val = WEAPON_MODIFIERS.get(weapon_category, 0)
    total_base_damage = margin + weapon_val + weapon_damage_bonus
    
    if is_target_vampire:
        if is_bane:
            return DamageResult(total_damage=total_base_damage, damage_type="aggravated")
        else:
            reduced = math.ceil(total_base_damage / 2)
            return DamageResult(total_damage=reduced, damage_type="superficial")
    else:
        if weapon_val > 0 or is_bane or weapon_damage_bonus > 0:
            return DamageResult(total_damage=total_base_damage, damage_type="aggravated")
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
