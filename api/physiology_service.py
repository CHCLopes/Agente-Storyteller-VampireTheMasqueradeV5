import os
import json
from .rules_service import PredatorTypeModel, BloodPotencyModel

_PREDATOR_CACHE: dict[str, PredatorTypeModel] = {}
_POTENCY_CACHE: dict[str, BloodPotencyModel] = {}

def load_physiology_catalogs():
    global _PREDATOR_CACHE, _POTENCY_CACHE
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if not _PREDATOR_CACHE:
        path = os.path.join(base_dir, "data", "catalogs", "predator_types.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in data.items():
                _PREDATOR_CACHE[k] = PredatorTypeModel(**v)
                
    if not _POTENCY_CACHE:
        path = os.path.join(base_dir, "data", "catalogs", "blood_potency.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in data.items():
                _POTENCY_CACHE[k] = BloodPotencyModel(**v)

def get_predator_model(predator_type: str) -> PredatorTypeModel | None:
    load_physiology_catalogs()
    return _PREDATOR_CACHE.get(predator_type.lower())

def get_blood_potency_model(potency_level: int) -> BloodPotencyModel | None:
    load_physiology_catalogs()
    return _POTENCY_CACHE.get(str(potency_level))

def get_blood_surge_bonus(potency_level: int) -> int:
    model = get_blood_potency_model(potency_level)
    if model:
        return model.engine_data.blood_surge_bonus
    return 1

def get_healing_amount(potency_level: int) -> int:
    model = get_blood_potency_model(potency_level)
    if model:
        return model.engine_data.damage_healed_per_rouse
    return 1
