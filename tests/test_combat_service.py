import pytest

from api.combat_service import calculate_damage, get_weapon_model


def test_unarmed_damage_uses_margin_and_vampire_halving() -> None:
    mortal = calculate_damage(3, "unarmed", False, False)
    vampire = calculate_damage(3, "unarmed", False, True)
    assert (mortal.total_damage, mortal.damage_type) == (3, "superficial")
    assert (vampire.total_damage, vampire.damage_type) == (2, "superficial")


def test_unknown_weapon_fails_closed_instead_of_becoming_unarmed() -> None:
    assert get_weapon_model("unknown_weapon") is None
    with pytest.raises(ValueError, match="unknown weapon catalog entry"):
        calculate_damage(3, "unknown_weapon", False, False)
