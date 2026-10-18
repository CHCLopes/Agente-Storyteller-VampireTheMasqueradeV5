from pydantic import BaseModel, Field
from typing import Literal, Optional

from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry

class DisciplineEngineData(BaseModel):
    rouse_cost: int = Field(ge=0, le=3)
    scaling_stat: Optional[str] = None
    dice_bonus_stat: Optional[str] = None
    is_aggravated: bool
    amalgam_req: list[str]
    action_roll_policy: Literal["standard_action", "contextual", "no_roll"] = "standard_action"
    dice_bonus_discipline_family: Optional[str] = None
    dice_bonus_attribute: Optional[str] = None
    weapon_damage_bonus: int = 0
    unhalved_superficial_to_vampires: bool = False
    duration: Optional[str] = None
    vertical_leap_multiplier: int = 0
    horizontal_leap_multiplier: int = 0

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
    unhalved_superficial_to_vampires: bool = False

def load_disciplines_catalog():
    get_catalog_registry()

def get_discipline_model(power_name: str) -> DisciplineModel | None:
    record = get_catalog_registry().get(CatalogDomain.DISCIPLINE_POWER, power_name)
    return DisciplineModel.model_validate(record.payload) if record else None

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


def get_power_action_roll_policy(
    power_name: str | None,
) -> Literal["standard_action", "contextual", "no_roll"] | None:
    sanitized = _sanitize_power_name(power_name)
    power = get_discipline_model(sanitized) if sanitized else None
    return power.engine_data.action_roll_policy if power else None

def apply_power_modifiers(
    power_name: str | None,
    current_is_bane: bool,
    player_sheet: dict,
    *,
    action_attribute: str | None = None,
) -> PowerModifiers:
    sanitized = _sanitize_power_name(power_name)
    if not sanitized:
        return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)

    power = get_discipline_model(sanitized)
    if not power:
        return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)
        
    for req in power.engine_data.amalgam_req:
        if req.lower() not in [d.lower() for d in player_sheet.get("disciplines", {}).keys()]:
            return PowerModifiers(dice_bonus=0, is_bane=current_is_bane, weapon_damage_bonus=0)
            
    dice_bonus = 0
    if (
        power.engine_data.dice_bonus_discipline_family
        and power.engine_data.dice_bonus_attribute
        and action_attribute == power.engine_data.dice_bonus_attribute
    ):
        family = power.engine_data.dice_bonus_discipline_family
        dice_bonus = player_sheet.get("disciplines", {}).get(
            family,
            player_sheet.get("disciplines", {}).get(family.capitalize(), 0),
        )

    return PowerModifiers(
        dice_bonus=dice_bonus,
        is_bane=current_is_bane or power.engine_data.is_aggravated,
        weapon_damage_bonus=power.engine_data.weapon_damage_bonus,
        unhalved_superficial_to_vampires=(
            power.engine_data.unhalved_superficial_to_vampires
        ),
    )
