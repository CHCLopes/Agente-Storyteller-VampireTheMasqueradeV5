import pytest
from pydantic import ValidationError

from api.progression_service import ProgressionValidationError, purchase_upgrade
from api.rules_service import PlayerSheetModel


def sheet() -> PlayerSheetModel:
    return PlayerSheetModel(
        clan="brujah", predator_type="alleycat",
        attributes={"Strength": 2}, skills={"Brawl": 2}, disciplines={},
        status={"blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}},
        available_xp=20,
    )


@pytest.mark.parametrize("field,value", (("clan", "unknown"), ("predator_type", "unknown")))
def test_sheet_rejects_unknown_catalog_references(field: str, value: str) -> None:
    payload = sheet().model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        PlayerSheetModel.model_validate(payload)


@pytest.mark.parametrize(
    "category,trait,level",
    (("unknown", "Strength", 3), ("attribute", "Unknown", 3), ("attribute", "Strength", 4)),
)
def test_invalid_progression_preserves_serialized_sheet(category: str, trait: str, level: int) -> None:
    original = sheet()
    before = original.model_dump_json()
    with pytest.raises(ProgressionValidationError):
        purchase_upgrade(original, category, trait, level)
    assert original.model_dump_json() == before


@pytest.mark.parametrize(
    "category,trait,level,target",
    (
        ("attribute", "Strength", 3, ("attributes", "Strength")),
        ("skill", "Brawl", 3, ("skills", "Brawl")),
        ("clan_discipline", "potence", 1, ("disciplines", "potence")),
        ("out_of_clan_discipline", "potence", 1, ("disciplines", "potence")),
        ("caitiff_discipline", "potence", 1, ("disciplines", "potence")),
        ("blood_potency", "blood_potency", 2, ("status", "blood_potency")),
    ),
)
def test_supported_progression_categories_purchase_one_level_without_mutating_input(
    category: str, trait: str, level: int, target: tuple[str, str]
) -> None:
    original = sheet().model_copy(update={"available_xp": 100})
    before = original.model_dump_json()

    purchased, updated = purchase_upgrade(original, category, trait, level)

    assert purchased is True
    assert original.model_dump_json() == before
    container, key = target
    value = getattr(updated, container)
    assert (getattr(value, key) if container == "status" else value[key]) == level
    assert updated.available_xp < original.available_xp


@pytest.mark.parametrize(
    "category,trait,level,code",
    (
        ("attribute", "Unknown", 3, "unknown_trait"),
        ("skill", "Unknown", 3, "unknown_trait"),
        ("clan_discipline", "unknown_power", 1, "unknown_trait"),
        ("out_of_clan_discipline", "unknown_power", 1, "unknown_trait"),
        ("caitiff_discipline", "unknown_power", 1, "unknown_trait"),
        ("blood_potency", "other", 2, "unknown_trait"),
        ("specialty", "Ambush", 1, "unsupported_category"),
    ),
)
def test_each_progression_category_fails_closed_and_preserves_input(
    category: str, trait: str, level: int, code: str
) -> None:
    original = sheet().model_copy(update={"available_xp": 100})
    before = original.model_dump_json()

    with pytest.raises(ProgressionValidationError) as captured:
        purchase_upgrade(original, category, trait, level)

    assert captured.value.code == code
    assert original.model_dump_json() == before
