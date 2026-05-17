from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
import json
import os
import uuid
from .rules_service import PlayerSheetModel
from .orchestrator_service import process_turn_pipeline, SAVE_DIR

app = FastAPI(title="Agente Storyteller Motor V5")

SHEETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sheets")
os.makedirs(SHEETS_DIR, exist_ok=True)

def load_player_sheet(character_id: str) -> PlayerSheetModel:
    path = os.path.join(SHEETS_DIR, f"{character_id}.json")
    if not os.path.exists(path):
        path = os.path.join(SHEETS_DIR, "base_player.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return PlayerSheetModel(**data)
    except Exception as e:
        raise ValueError(f"Ficha de jogador corrompida: {str(e)}")

class StateEnum(Enum):
    MENU = "MENU"
    PLAYING = "PLAYING"

class SessionData:
    def __init__(self):
        self.state = StateEnum.MENU
        self.active_campaign_id = None
        self.turn = 1
        self.chronicle_name = "Noites de Sangue"
        
        try:
            sheet_model = load_player_sheet("base_player")
            self.context = {
                "player_sheet": sheet_model.model_dump(),
                "last_action_cache": None,
                "pre_roll_snapshot": None
            }
        except Exception:
            self.context = {}

active_sessions = {}

class ActionRequest(BaseModel):
    user_input: str
    session_id: str = "local_player"

def create_new_campaign() -> str:
    new_session = f"chronicle_{uuid.uuid4().hex[:8]}"
    return new_session

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/chat")
async def process_chat(action: ActionRequest):
    user_input = action.user_input.strip().lower()
    session_id = action.session_id
    
    if session_id not in active_sessions:
        active_sessions[session_id] = SessionData()
    
    session = active_sessions[session_id]
    
    if session.state == StateEnum.MENU:
        session.active_campaign_id = create_new_campaign()
        session.state = StateEnum.PLAYING
        return {"action": "chat_response", "message": "Iniciado."}

    elif session.state == StateEnum.PLAYING:
        reply, updated_context = await process_turn_pipeline(
            user_input=action.user_input, 
            session_id=session_id, 
            context=session.context,
            turn=session.turn,
            chronicle_name=session.chronicle_name
        )
        session.context = updated_context
        session.turn += 1
        return {"action": "chat_response", "message": reply}

    return {"action": "error", "message": "Estado Inválido."}
