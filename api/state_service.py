import os
import json
import time
import asyncio
import aiofiles
from pydantic import BaseModel, Field
from typing import List, Optional

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

# Lock global para operações de longa duração do LLM
global_llm_operation_lock = asyncio.Lock()

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

class StateUpdateEvent(BaseModel):
    event: str = "state_update"
    action: str = "state_update"  # Compatibilidade com client/app.js (Foundation V1)
    session_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    character: CharacterModel
    context: ContextModel
    player_sheet: Optional[dict] = None  # Metadados de compatibilidade com o front passivo
    relationships: Optional[list] = None  # Motor relacional — Camada 2

# --- FUNÇÕES DE PERSISTÊNCIA ASSÍNCRONA SEGURA ---

def sync_event_from_context(session_id: str, context: dict, status_override: Optional[str] = None) -> StateUpdateEvent:
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
        environmental_flags=environmental_flags
    )
    
    return StateUpdateEvent(
        session_id=session_id,
        character=character,
        context=context_model,
        player_sheet=context
    )

async def save_session_state(
    session_id: str,
    event_data: StateUpdateEvent | dict,
    chronicle_name: Optional[str] = None,
    turn: Optional[int] = None
):
    """
    Salva o estado validado pelo Pydantic de forma atômica utilizando asyncio.Lock.
    Permite assinatura antiga com dicionário e argumentos adicionais para compatibilidade.
    """
    if isinstance(event_data, dict):
        event_data = sync_event_from_context(session_id, event_data)
        
    safe_filename = os.path.basename(f"{session_id}.json")
    path = os.path.join(SAVE_DIR, safe_filename)
    
    # Valida e serializa para dict/json
    serialized_data = event_data.model_dump()
    
    lock = get_session_lock(session_id)
    async with lock:
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(serialized_data, indent=4, ensure_ascii=False))

async def load_session_state(session_id: str) -> Optional[StateUpdateEvent]:
    """
    Carrega o estado validando contra o Pydantic StateUpdateEvent.
    Retorna None se o save não existir ou estiver corrompido.
    """
    safe_filename = os.path.basename(f"{session_id}.json")
    path = os.path.join(SAVE_DIR, safe_filename)
    
    lock = get_session_lock(session_id)
    async with lock:
        if not os.path.exists(path):
            return None
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return StateUpdateEvent(**data)
        except Exception:
            return None
