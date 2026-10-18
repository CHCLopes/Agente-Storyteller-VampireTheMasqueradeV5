from pydantic import BaseModel, Field
import re
import unicodedata

from .catalog_models import CatalogDomain
from .catalog_service import get_catalog_registry

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

def load_npc_catalog():
    get_catalog_registry()

def get_npc_model(npc_id: str) -> NpcModel | None:
    record = get_catalog_registry().get(CatalogDomain.NPC_ARCHETYPE, npc_id)
    return NpcModel.model_validate(record.payload) if record else None


def get_supported_npc_model(npc_id: str) -> NpcModel:
    record = get_catalog_registry().require(CatalogDomain.NPC_ARCHETYPE, npc_id)
    if record.mvp_scope != "base_reachable":
        raise ValueError(f"NPC archetype is outside the approved MVP scope: {npc_id}")
    return NpcModel.model_validate(record.payload)

def get_all_npcs() -> dict[str, NpcModel]:
    return {
        record.identity.entry_id: NpcModel.model_validate(record.payload)
        for record in get_catalog_registry().entries(CatalogDomain.NPC_ARCHETYPE)
    }


def find_npc_ids(text: str) -> tuple[str, ...]:
    """Resolve localized, explicit NPC mentions to canonical catalog IDs."""

    decomposed = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    found: list[str] = []
    for record in get_catalog_registry().entries(CatalogDomain.NPC_ARCHETYPE):
        npc_id = record.identity.entry_id
        aliases = (npc_id, *record.identity.aliases)
        if any(re.search(r"\b" + re.escape(alias) + r"\b", normalized) for alias in aliases):
            found.append(npc_id)
    return tuple(found)
