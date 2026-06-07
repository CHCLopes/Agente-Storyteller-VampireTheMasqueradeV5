from pydantic import BaseModel, Field
import os
import json

class NpcEngineData(BaseModel):
    base_dice_pool: int
    threat_level: int = Field(ge=1, le=5)
    is_supernatural: bool
    has_true_faith: bool
    corruption_index: int = Field(ge=1, le=5)

class NpcNarrativeData(BaseModel):
    description: str
    combat_tactics: str
    social_standing: str

class NpcModel(BaseModel):
    engine_data: NpcEngineData
    narrative_data: NpcNarrativeData

_NPC_CACHE: dict[str, NpcModel] = {}

def load_npc_catalog():
    global _NPC_CACHE
    if _NPC_CACHE: return
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalogs", "npc_hierarchy.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for key, val in data.items():
            _NPC_CACHE[key] = NpcModel(**val)

def get_npc_model(npc_id: str) -> NpcModel | None:
    load_npc_catalog()
    return _NPC_CACHE.get(npc_id.lower())

def get_all_npcs() -> dict[str, NpcModel]:
    load_npc_catalog()
    return _NPC_CACHE
