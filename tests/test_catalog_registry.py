import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.catalog_models import CatalogDomain, CatalogEntryIdentity
from api.catalog_service import CatalogRegistry, CatalogRegistryError, normalize_catalog_id


def test_registry_loads_exactly_the_seven_catalogs_and_66_entries() -> None:
    registry = CatalogRegistry()

    counts = {domain: len(registry.entries(domain)) for domain in CatalogDomain}
    assert counts == {
        CatalogDomain.BLOOD_POTENCY: 11,
        CatalogDomain.CLAN: 16,
        CatalogDomain.DISCIPLINE_POWER: 8,
        CatalogDomain.NPC_ARCHETYPE: 9,
        CatalogDomain.PREDATOR_TYPE: 5,
        CatalogDomain.PROGRESSION_CATEGORY: 7,
        CatalogDomain.WEAPON: 10,
    }


def test_lookup_normalizes_localized_alias_without_changing_canonical_id() -> None:
    registry = CatalogRegistry()

    assert normalize_catalog_id(" Príncipe ") == "principe"
    assert registry.require(CatalogDomain.NPC_ARCHETYPE, "Príncipe").identity.entry_id == "prince"
    assert registry.get(CatalogDomain.NPC_ARCHETYPE, "desconhecido") is None


def test_returned_payload_is_a_deep_copy() -> None:
    registry = CatalogRegistry()
    first = registry.require(CatalogDomain.CLAN, "brujah")
    first.payload["engine_data"]["compulsion_dice_penalty"] = 99

    second = registry.require(CatalogDomain.CLAN, "brujah")
    assert second.payload["engine_data"]["compulsion_dice_penalty"] == 2


def test_identity_contract_forbids_extra_fields_and_duplicate_aliases() -> None:
    with pytest.raises(ValidationError):
        CatalogEntryIdentity(
            domain=CatalogDomain.CLAN,
            entry_id="brujah",
            aliases=("ralé", "ralé"),
        )
    with pytest.raises(ValidationError):
        CatalogEntryIdentity.model_validate(
            {"domain": "clan", "entry_id": "brujah", "unexpected": True}
        )


def test_registry_fails_closed_when_catalog_hash_changes(tmp_path: Path) -> None:
    source = Path("data/catalogs")
    for item in source.glob("*.json"):
        (tmp_path / item.name).write_bytes(item.read_bytes())
    clans = json.loads((tmp_path / "clans.json").read_text(encoding="utf-8"))
    clans["brujah"]["engine_data"]["compulsion_dice_penalty"] = 99
    (tmp_path / "clans.json").write_text(json.dumps(clans), encoding="utf-8")

    with pytest.raises(CatalogRegistryError, match="hash mismatch"):
        CatalogRegistry(tmp_path)


def test_every_manifest_records_an_approved_project_source() -> None:
    registry = CatalogRegistry()

    assert all(item.verification_status == "verified" for item in registry.manifest.files)
    assert all(
        item.source_title
        in {
            "Organizando Regras de Vampiro para IA",
            "Vampire: The Masquerade 5th Edition",
        }
        for item in registry.manifest.files
    )
    assert all(
        item.source_locator
        and (
            "notebook.google.com" in item.source_locator
            if item.source_title == "Organizando Regras de Vampiro para IA"
            else "Vampire the Masquerade.pdf" in item.source_locator
        )
        for item in registry.manifest.files
    )


def test_manifest_classifies_user_provided_base_pdfs_by_authority() -> None:
    registry = CatalogRegistry()
    sources = {item.source_id: item for item in registry.manifest.source_inventory}

    assert len(sources) == 6
    assert sources["v5_core_rulebook"].source_role == "v5_rules"
    assert CatalogDomain.PREDATOR_TYPE in sources["v5_core_rulebook"].authority_scope
    assert sources["vtm_third_edition"].source_role == "legacy_rules"
    assert sources["vtm_third_edition"].authority_scope == ()
    assert sources["narrative_rpg_engine_v2_4"].source_role == "engine_design"
    assert sources["aldi_sanguine_adventure"].source_role == "scenario"


def test_discipline_metadata_preserves_identified_values_and_explicit_gaps() -> None:
    registry = CatalogRegistry()

    feral = registry.require(CatalogDomain.DISCIPLINE_POWER, "armas ferais")
    assert feral.identity.entry_id == "feral_weapons"
    assert feral.payload["catalog_metadata"]["discipline_family_id"] == "protean"
    assert feral.payload["catalog_metadata"]["level"] == 2

    dementation = registry.require(CatalogDomain.DISCIPLINE_POWER, "demência")
    assert dementation.payload["catalog_metadata"]["level"] is None
    assert dementation.payload["catalog_metadata"]["amalgam_requirements"] == [
        {"discipline_family_id": "obfuscate", "level": 2}
    ]


def _sheet_data() -> dict:
    return {
        "attributes": {"Strength": 3},
        "skills": {"Brawl": 2},
        "disciplines": {},
        "status": {
            "blood_potency": 1,
            "current_hunger": 1,
            "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0},
        },
    }


def test_player_sheet_accepts_and_preserves_legacy_catalog_aliases() -> None:
    from api.rules_service import PlayerSheetModel

    sheet = PlayerSheetModel(
        **{
            **_sheet_data(),
            "clan": "BRUJAH",
            "disciplines": {"armas_ferais": 2, "potence": 1},
        }
    )

    assert sheet.clan == "BRUJAH"
    assert sheet.disciplines == {"armas_ferais": 2, "potence": 1}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("clan", "unknown_clan", "unknown clan"),
        ("predator_type", "unknown_predator", "unknown predator type"),
        ("disciplines", {"unknown_power": 1}, "unknown discipline or power"),
    ],
)
def test_player_sheet_rejects_unknown_catalog_references(
    field: str, value: object, message: str
) -> None:
    from api.rules_service import PlayerSheetModel

    with pytest.raises(ValidationError, match=message):
        PlayerSheetModel(**{**_sheet_data(), field: value})


def test_player_sheet_rejects_unknown_blood_potency_and_invalid_level() -> None:
    from api.rules_service import PlayerSheetModel

    unknown_potency = _sheet_data()
    unknown_potency["status"] = {**unknown_potency["status"], "blood_potency": 11}
    with pytest.raises(ValidationError, match="unknown blood potency"):
        PlayerSheetModel(**unknown_potency)

    with pytest.raises(ValidationError, match="between 0 and 5"):
        PlayerSheetModel(**{**_sheet_data(), "disciplines": {"potence": 6}})


def test_alleycat_hunt_profile_is_typed_and_resonance_is_narrative_only() -> None:
    from api.physiology_service import get_supported_predator_hunt_profile
    from api.rules_service import V5Attribute, V5Skill

    profile = get_supported_predator_hunt_profile("alleycat")

    assert profile.attribute is V5Attribute.Strength
    assert profile.skill is V5Skill.BRAWL
    assert profile.blood_resonance_preference == "choleric"
    assert profile.resonance_role == "narrative_targeting_hint"


def test_deferred_predator_hunt_profile_fails_closed() -> None:
    from api.physiology_service import get_supported_predator_hunt_profile

    with pytest.raises(ValueError, match="outside the approved MVP scope"):
        get_supported_predator_hunt_profile("siren")


def test_feeding_action_uses_approved_predator_pool() -> None:
    from api.orchestrator_service import _mechanical_action_from_intent
    from api.rules_service import DeterministicTurnInputs, PlayerSheetModel, V5Attribute, V5Skill

    sheet = PlayerSheetModel(**_sheet_data())
    payload = _mechanical_action_from_intent(
        None,
        DeterministicTurnInputs(),
        sheet,
        "Eu me alimento da vítima.",
        [],
    )

    assert payload.is_feeding is True
    assert payload.attribute is V5Attribute.Strength
    assert payload.skill is V5Skill.BRAWL


def test_unarmed_damage_uses_zero_modifier_and_brawl_type() -> None:
    from api.combat_service import calculate_damage, get_weapon_model, WeaponTypeEnum

    weapon = get_weapon_model("unarmed")
    assert weapon is not None
    assert weapon.engine_data.damage_modifier == 0
    assert weapon.engine_data.weapon_type is WeaponTypeEnum.BRAWL
    assert weapon.engine_data.is_concealable is True
    result = calculate_damage(3, "unarmed", False, False)
    assert result.total_damage == 3
    assert result.damage_type == "superficial"


def test_unknown_weapon_never_falls_back_to_zero_damage_modifier() -> None:
    from api.combat_service import calculate_damage

    with pytest.raises(ValueError, match="unknown weapon catalog entry"):
        calculate_damage(3, "unknown_weapon", False, False)


def test_supported_power_metadata_matches_v5_source() -> None:
    registry = CatalogRegistry()

    feral = registry.require(CatalogDomain.DISCIPLINE_POWER, "feral_weapons").payload
    assert feral["catalog_metadata"]["level"] == 2
    assert feral["engine_data"]["rouse_cost"] == 1
    assert feral["engine_data"]["weapon_damage_bonus"] == 2
    assert feral["engine_data"]["is_aggravated"] is False
    assert feral["engine_data"]["unhalved_superficial_to_vampires"] is True

    leap = registry.require(CatalogDomain.DISCIPLINE_POWER, "soaring_leap").payload
    assert leap["catalog_metadata"]["level"] == 1
    assert leap["engine_data"]["action_roll_policy"] == "no_roll"
    assert leap["engine_data"]["vertical_leap_multiplier"] == 3
    assert leap["engine_data"]["horizontal_leap_multiplier"] == 5

    awe = registry.require(CatalogDomain.DISCIPLINE_POWER, "awe").payload
    assert awe["catalog_metadata"]["level"] == 1
    assert awe["catalog_metadata"]["rules_origin"] == "v5"
    assert awe["engine_data"]["action_roll_policy"] == "contextual"


def test_supported_power_modifiers_are_catalog_driven_and_target_aware() -> None:
    from api.combat_service import calculate_damage
    from api.discipline_service import apply_power_modifiers

    sheet = {"disciplines": {"presence": 3, "potence": 2, "protean": 2}}
    feral = apply_power_modifiers(
        "feral_weapons", False, sheet, action_attribute="Strength"
    )
    assert feral.dice_bonus == 0
    assert feral.weapon_damage_bonus == 2
    assert feral.is_bane is False
    assert feral.unhalved_superficial_to_vampires is True
    damage = calculate_damage(
        3,
        "unarmed",
        False,
        True,
        weapon_damage_bonus=feral.weapon_damage_bonus,
        unhalved_superficial_to_vampires=feral.unhalved_superficial_to_vampires,
    )
    assert damage.total_damage == 5
    assert damage.damage_type == "superficial"

    assert apply_power_modifiers(
        "awe", False, sheet, action_attribute="Charisma"
    ).dice_bonus == 3
    assert apply_power_modifiers(
        "awe", False, sheet, action_attribute="Manipulation"
    ).dice_bonus == 0
    assert apply_power_modifiers(
        "soaring_leap", False, sheet, action_attribute="Strength"
    ).dice_bonus == 0


def test_only_approved_npcs_are_mechanically_reachable() -> None:
    from api.npc_service import get_supported_npc_model

    assert get_supported_npc_model("prince").engine_data.threat_level == 5
    assert get_supported_npc_model("sheriff").engine_data.threat_level == 4
    with pytest.raises(ValueError, match="outside the approved MVP scope"):
        get_supported_npc_model("politician")


def test_only_approved_blood_potency_drives_runtime_effects() -> None:
    from api.catalog_service import CatalogRegistryError
    from api.physiology_service import get_blood_surge_bonus, get_healing_amount

    assert get_blood_surge_bonus(1) == 1
    assert get_healing_amount(1) == 1
    with pytest.raises(ValueError, match="outside the approved MVP scope"):
        get_blood_surge_bonus(2)
    with pytest.raises(CatalogRegistryError, match="unknown catalog entry"):
        get_healing_amount(11)
