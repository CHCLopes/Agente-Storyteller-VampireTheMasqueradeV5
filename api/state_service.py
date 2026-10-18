import os
import time
import asyncio
from pydantic import BaseModel, Field
from typing import List, Optional

from .core.config import settings
from .persistence import LegacyMigrationError, SQLitePersistence
from .scene_service import SceneState, scene_from_context

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

_session_locks: dict[str, asyncio.Lock] = {}
_session_processing_locks: dict[str, asyncio.Lock] = {}

def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]

def acquire_session_lock(session_id: str) -> asyncio.Lock:
    """Adquire lock exclusivo para sessão"""
    if session_id not in _session_processing_locks:
        _session_processing_locks[session_id] = asyncio.Lock()
    return _session_processing_locks[session_id]

# --- SCHEMAS PYDANTIC DO CONTRATO ALVO ---

class TrackerDetail(BaseModel):
    superficial: int = 0
    aggravated: int = 0
    max: int

class TrackersModel(BaseModel):
    health: Optional[TrackerDetail] = None
    willpower: Optional[TrackerDetail] = None
    humanity: int = 7
    stains: int = 0

class CharacterAttributes(BaseModel):
    self_control: int = 3
    resolve: int = 3

class CharacterModel(BaseModel):
    id: str
    trackers: TrackersModel
    attributes: CharacterAttributes
    fome: int = Field(default=0, ge=0, le=5)
    status: str = "ACTIVE"  # "ACTIVE", "FRENZY_CHECK", "TORPOR"

class PendingRollModel(BaseModel):
    type: str = "FRENZY_RESISTANCE"
    pool: List[str] = ["self_control", "resolve"]
    difficulty: int = 3

class EnvironmentalFlagsModel(BaseModel):
    fire_exposure: bool = False
    blood_stimulus: bool = False

class ContextModel(BaseModel):
    current_state: str = "ACTIVE"
    blocking: bool = False
    pending_roll: Optional[PendingRollModel] = None
    environmental_flags: EnvironmentalFlagsModel = Field(default_factory=EnvironmentalFlagsModel)
    scene: Optional[SceneState] = None

class StateUpdateEvent(BaseModel):
    event: str = "state_update"
    action: str = "state_update"  # Compatibilidade com client/app.js (Foundation V1)
    session_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    character: CharacterModel
    context: ContextModel
    player_sheet: Optional[dict] = None  # Metadados de compatibilidade com o front passivo
    relationships: Optional[list] = None  # Motor relacional — Camada 2
    turn_number: int = Field(default=0, ge=0)
    state_revision: int = Field(default=0, ge=0, exclude=True)
    narrative_history: list[dict] = Field(default_factory=list)

# --- PROJEÇÃO DE COMPATIBILIDADE SOBRE O REPOSITÓRIO TRANSACIONAL ---


def _configured_db_path() -> str:
    path = settings.storyteller_db_path
    if os.path.isabs(path):
        return path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, path)


_persistence = SQLitePersistence(_configured_db_path())


def get_persistence() -> SQLitePersistence:
    return _persistence


def configure_persistence_for_tests(persistence: SQLitePersistence) -> None:
    """Replace the process repository explicitly in isolated tests only."""

    global _persistence
    _persistence = persistence

def sync_event_from_context(
    session_id: str,
    context: dict,
    status_override: Optional[str] = None,
    *,
    turn_number: int = 0,
    state_revision: int = 0,
    narrative_history: Optional[list[dict]] = None,
) -> StateUpdateEvent:
    scene = scene_from_context(context)
    player_sheet = context.get("player_sheet", {})
    status_data = player_sheet.get("status", {})
    
    health_data = status_data.get("health_tracker", {"size": 7, "superficial": 0, "aggravated": 0})
    willpower_data = status_data.get("willpower_tracker", {"size": 5, "superficial": 0, "aggravated": 0})
    fome = status_data.get("current_hunger", 0)
    humanity = status_data.get("humanity", 7)
    stains = status_data.get("stains", 0)
    
    attributes = player_sheet.get("attributes", {})
    self_control = attributes.get("Composure", 3)  # Composure mapeado para self_control no V5
    resolve = attributes.get("Resolve", 3)
    
    character_status = "ACTIVE"
    if health_data.get("aggravated", 0) >= health_data.get("size", 7):
        character_status = "TORPOR"
        
    if status_override:
        character_status = status_override
        
    character = CharacterModel(
        id=session_id,
        trackers=TrackersModel(
            health=TrackerDetail(
                superficial=health_data.get("superficial", 0),
                aggravated=health_data.get("aggravated", 0),
                max=health_data.get("size", 7)
            ),
            willpower=TrackerDetail(
                superficial=willpower_data.get("superficial", 0),
                aggravated=willpower_data.get("aggravated", 0),
                max=willpower_data.get("size", 5)
            ),
            humanity=humanity,
            stains=stains
        ),
        attributes=CharacterAttributes(
            self_control=self_control,
            resolve=resolve
        ),
        fome=fome,
        status=character_status
    )
    
    current_state = character_status
    blocking = False
    pending_roll = None
    
    if character_status == "FRENZY_CHECK":
        blocking = True
        pending_roll = PendingRollModel(
            type="FRENZY_RESISTANCE",
            pool=["self_control", "resolve"],
            difficulty=3
        )
    elif character_status == "TORPOR":
        blocking = True
        
    env_flags_data = context.get("environmental_flags", {})
    environmental_flags = EnvironmentalFlagsModel(
        fire_exposure=env_flags_data.get("fire_exposure", False),
        blood_stimulus=env_flags_data.get("blood_stimulus", False)
    )
    
    context_model = ContextModel(
        current_state=current_state,
        blocking=blocking,
        pending_roll=pending_roll,
        environmental_flags=environmental_flags,
        scene=scene,
    )
    
    return StateUpdateEvent(
        session_id=session_id,
        character=character,
        context=context_model,
        player_sheet=context,
        turn_number=turn_number,
        state_revision=state_revision,
        narrative_history=narrative_history or [],
    )

async def save_session_state(
    session_id: str,
    event_data: StateUpdateEvent | dict,
    chronicle_name: Optional[str] = None,
    turn: Optional[int] = None
):
    """Persist a control snapshot without advancing a narrated turn."""
    if isinstance(event_data, dict):
        event_data = sync_event_from_context(session_id, event_data)
        
    serialized_data = event_data.model_dump(mode="json")
    lock = get_session_lock(session_id)
    async with lock:
        campaign = await _persistence.update_campaign_snapshot(
            session_id,
            state=serialized_data,
            # `StateUpdateEvent.relationships` is a frontend projection, not
            # the canonical relationship aggregate.
            relationships=None,
            chronicle_name=chronicle_name,
            expected_turn=(event_data.turn_number if turn is None else turn),
            expected_revision=event_data.state_revision,
        )
        event_data.state_revision = int(campaign["state_revision"])

async def load_session_state(session_id: str) -> Optional[StateUpdateEvent]:
    """Load the canonical snapshot and narrative history from SQLite.

    Legacy JSON is audited and imported lazily. Corruption is intentionally
    surfaced instead of being converted into an empty campaign.
    """

    lock = get_session_lock(session_id)
    async with lock:
        try:
            await _persistence.migrate_legacy_session(session_id, SAVE_DIR)
        except ValueError:
            # SQLite accepts broader IDs safely through bound parameters; only
            # the legacy filename importer needs the strict filename alphabet.
            pass
        except LegacyMigrationError:
            raise

        campaign = await _persistence.load_campaign(session_id)
        if campaign is None:
            return None
        data = campaign.get("state") or {}
        if not data:
            return None
        event = StateUpdateEvent(**data)
        event.state_revision = int(campaign.get("state_revision") or 0)
        relationships = campaign.get("relationships")
        if isinstance(relationships, dict) and "relationships" in relationships:
            from .relationship_service import get_relationships_for_frontend, RelationshipState

            event.relationships = get_relationships_for_frontend(
                RelationshipState(**relationships)
            )
        elif isinstance(relationships, list):
            event.relationships = relationships
        event.turn_number = int(campaign.get("current_turn") or 0)

        history = await _persistence.list_latest_turns(session_id, limit=100)
        event.narrative_history = []
        for turn in history:
            turn_context = turn.get("context") or {}
            receipt = (
                turn_context.get("resolution_receipt")
                if isinstance(turn_context, dict)
                else None
            )
            if (
                isinstance(receipt, dict)
                and isinstance(receipt.get("receipt_id"), str)
                and isinstance(receipt.get("display"), str)
            ):
                event.narrative_history.append(
                    {
                        "id": receipt["receipt_id"],
                        "turn_id": turn["turn_id"],
                        "turn_number": turn["turn_number"],
                        "type": "mechanics",
                        "content": receipt["display"],
                        "narrative_mode": receipt.get("narrative_mode", "llm"),
                        "timestamp": turn["committed_at"],
                    }
                )
            event.narrative_history.append({
                "id": (turn.get("narrative") or {}).get("narrative_id", turn["turn_id"]),
                "turn_id": turn["turn_id"],
                "turn_number": turn["turn_number"],
                "type": "narrator",
                "content": turn["narrative_text"],
                "timestamp": turn["committed_at"],
            })
        return event
