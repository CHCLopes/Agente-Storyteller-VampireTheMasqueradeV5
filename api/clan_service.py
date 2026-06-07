from pydantic import BaseModel
import os
import json

class ClanEngineData(BaseModel):
    bane_severity_multiplier: int
    compulsion_dice_penalty: int
    favored_disciplines: list[str]

class ClanNarrativeData(BaseModel):
    faction_loyalty: str
    bane_description: str
    compulsion_description: str
    lore_summary: str
    narrator_enforcement: str
    behavioral_penalty: str

class ClanModel(BaseModel):
    engine_data: ClanEngineData
    narrative_data: ClanNarrativeData

_CLANS_CACHE: dict[str, ClanModel] = {}

def load_clans_catalog():
    global _CLANS_CACHE
    if _CLANS_CACHE: return
    
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalogs", "clans.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for key, val in data.items():
            _CLANS_CACHE[key] = ClanModel(**val)

def get_clan_engine(clan_id: str) -> ClanEngineData | None:
    load_clans_catalog()
    model = _CLANS_CACHE.get(clan_id.lower())
    return model.engine_data if model else None

def get_clan_narrative(clan_id: str) -> ClanNarrativeData | None:
    load_clans_catalog()
    model = _CLANS_CACHE.get(clan_id.lower())
    return model.narrative_data if model else None
