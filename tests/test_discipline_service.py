import pytest

from api.catalog_models import CatalogDomain
from api.catalog_service import get_catalog_registry
from api.discipline_service import (
    apply_power_modifiers,
    get_discipline_model,
    get_power_action_roll_policy,
    get_power_cost,
)


@pytest.mark.parametrize("power_id", ("feral_weapons", "soaring_leap", "awe"))
def test_supported_power_contract_is_complete(power_id: str) -> None:
    record = get_catalog_registry().require(CatalogDomain.DISCIPLINE_POWER, power_id)
    assert record.mvp_scope == "base_reachable"
    assert get_discipline_model(power_id) is not None
    assert get_power_cost(power_id) == record.payload["engine_data"]["rouse_cost"]
    assert get_power_action_roll_policy(power_id) == record.payload["engine_data"]["action_roll_policy"]


def test_supported_power_effects_match_catalog() -> None:
    feral = apply_power_modifiers("feral_weapons", False, {"disciplines": {"protean": 2}})
    assert feral.weapon_damage_bonus == 2
    assert feral.unhalved_superficial_to_vampires is True
    awe = apply_power_modifiers(
        "awe", False, {"disciplines": {"presence": 2}}, action_attribute="Charisma"
    )
    assert awe.dice_bonus == 2


def test_unknown_power_never_resolves_to_a_catalog_model() -> None:
    assert get_discipline_model("unknown_power") is None
    assert get_power_action_roll_policy("unknown_power") is None
