from .rules_service import (
    BloodPotencyModel,
    PredatorHuntProfile,
    PredatorTypeModel,
    V5Attribute,
    V5Skill,
)
from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry

def load_physiology_catalogs():
    get_catalog_registry()

def get_predator_model(predator_type: str) -> PredatorTypeModel | None:
    record = get_catalog_registry().get(CatalogDomain.PREDATOR_TYPE, predator_type)
    return PredatorTypeModel.model_validate(record.payload) if record else None


def get_supported_predator_hunt_profile(predator_type: str) -> PredatorHuntProfile:
    record = get_catalog_registry().require(CatalogDomain.PREDATOR_TYPE, predator_type)
    if record.mvp_scope != "base_reachable":
        raise ValueError(f"predator type is outside the approved MVP scope: {predator_type}")
    model = PredatorTypeModel.model_validate(record.payload)
    pool = model.engine_data.hunting_pool
    if len(pool) != 2:
        raise ValueError(f"predator hunting pool must contain two traits: {predator_type}")
    try:
        attribute = next(
            item for item in V5Attribute if item.value.casefold() == pool[0].casefold()
        )
        skill = next(
            item for item in V5Skill if item.value.casefold() == pool[1].casefold()
        )
    except StopIteration as exc:
        raise ValueError(f"predator hunting pool contains an unknown trait: {predator_type}") from exc
    return PredatorHuntProfile(
        predator_type=record.identity.entry_id,
        attribute=attribute,
        skill=skill,
        blood_resonance_preference=model.engine_data.blood_resonance_preference,
    )

def get_blood_potency_model(potency_level: int) -> BloodPotencyModel | None:
    record = get_catalog_registry().get(CatalogDomain.BLOOD_POTENCY, str(potency_level))
    return BloodPotencyModel.model_validate(record.payload) if record else None


def get_supported_blood_potency_model(potency_level: int) -> BloodPotencyModel:
    record = get_catalog_registry().require(
        CatalogDomain.BLOOD_POTENCY, str(potency_level)
    )
    if record.mvp_scope != "base_reachable":
        raise ValueError(
            f"blood potency is outside the approved MVP scope: {potency_level}"
        )
    return BloodPotencyModel.model_validate(record.payload)

def get_blood_surge_bonus(potency_level: int) -> int:
    return get_supported_blood_potency_model(
        potency_level
    ).engine_data.blood_surge_bonus

def get_healing_amount(potency_level: int) -> int:
    return get_supported_blood_potency_model(
        potency_level
    ).engine_data.damage_healed_per_rouse
