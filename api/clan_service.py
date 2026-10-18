from pydantic import BaseModel

from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry

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

def load_clans_catalog():
    get_catalog_registry()


def _get_clan(clan_id: str) -> ClanModel | None:
    record = get_catalog_registry().get(CatalogDomain.CLAN, clan_id)
    return ClanModel.model_validate(record.payload) if record else None

def get_clan_engine(clan_id: str) -> ClanEngineData | None:
    model = _get_clan(clan_id)
    return model.engine_data if model else None

def get_clan_narrative(clan_id: str) -> ClanNarrativeData | None:
    model = _get_clan(clan_id)
    return model.narrative_data if model else None
