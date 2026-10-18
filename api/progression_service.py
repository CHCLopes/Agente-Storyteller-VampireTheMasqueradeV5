from __future__ import annotations

from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry, normalize_catalog_id
from .rules_service import PlayerSheetModel


class ProgressionValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

def load_progression_costs():
    get_catalog_registry()

def award_session_xp(player_sheet: PlayerSheetModel, amount: int = 1) -> PlayerSheetModel:
    player_sheet.available_xp += amount
    return player_sheet


def _category_record(trait_category: str):
    record = get_catalog_registry().get(
        CatalogDomain.PROGRESSION_CATEGORY, trait_category
    )
    if record is None:
        raise ProgressionValidationError(
            "unknown_category", f"unknown progression category: {trait_category}"
        )
    return record


def calculate_upgrade_cost(trait_category: str, new_level: int) -> int:
    record = _category_record(trait_category)
    if new_level < 1:
        raise ProgressionValidationError(
            "invalid_level", "upgrade level must be greater than zero"
        )
    cost_data = record.payload
    return cost_data["base_cost"] + (cost_data["cost_multiplier"] * new_level)


def _current_level(
    player_sheet: PlayerSheetModel, trait_category: str, trait_name: str
) -> int:
    normalized_name = normalize_catalog_id(trait_name)
    if trait_category == "attribute":
        if trait_name not in player_sheet.attributes:
            raise ProgressionValidationError("unknown_trait", f"unknown attribute: {trait_name}")
        return player_sheet.attributes[trait_name]
    if trait_category == "skill":
        if trait_name not in player_sheet.skills:
            raise ProgressionValidationError("unknown_trait", f"unknown skill: {trait_name}")
        return player_sheet.skills[trait_name]
    if trait_category in {"clan_discipline", "out_of_clan_discipline", "caitiff_discipline"}:
        registry = get_catalog_registry()
        known_power = registry.get(CatalogDomain.DISCIPLINE_POWER, trait_name)
        if known_power is None and normalized_name not in registry.discipline_family_ids():
            raise ProgressionValidationError(
                "unknown_trait", f"unknown discipline or power: {trait_name}"
            )
        return player_sheet.disciplines.get(trait_name, 0)
    if trait_category == "blood_potency":
        if normalized_name != "blood_potency":
            raise ProgressionValidationError(
                "unknown_trait", f"unknown blood potency trait: {trait_name}"
            )
        return player_sheet.status.blood_potency
    raise ProgressionValidationError(
        "unsupported_category",
        f"progression category has no implemented mutation: {trait_category}",
    )


def purchase_upgrade(
    player_sheet: PlayerSheetModel,
    trait_category: str,
    trait_name: str,
    new_level: int,
) -> tuple[bool, PlayerSheetModel]:
    _category_record(trait_category)
    current_level = _current_level(player_sheet, trait_category, trait_name)
    maximum = 10 if trait_category == "blood_potency" else 5
    if not 1 <= new_level <= maximum:
        raise ProgressionValidationError(
            "invalid_level", f"new level must be between 1 and {maximum}"
        )
    if new_level != current_level + 1:
        raise ProgressionValidationError(
            "invalid_transition",
            f"upgrade must advance exactly one level from {current_level}",
        )

    cost = calculate_upgrade_cost(trait_category, new_level)
    if player_sheet.available_xp < cost:
        return False, player_sheet

    updated = player_sheet.model_copy(deep=True)
    updated.available_xp -= cost
    updated.spent_xp += cost
    if trait_category == "attribute":
        updated.attributes[trait_name] = new_level
    elif trait_category == "skill":
        updated.skills[trait_name] = new_level
    elif trait_category in {"clan_discipline", "out_of_clan_discipline", "caitiff_discipline"}:
        updated.disciplines[trait_name] = new_level
    else:
        updated.status.blood_potency = new_level
    return True, updated
