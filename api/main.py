from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from enum import Enum
import json
import os
import uuid
import asyncio
from .rules_service import PlayerSheetModel
from .orchestrator_service import process_turn_pipeline, run_narrator_stream
from .state_service import SAVE_DIR

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

def create_new_campaign() -> str:
    new_session = f"chronicle_{uuid.uuid4().hex[:8]}"
    return new_session

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in active_sessions:
        active_sessions[session_id] = SessionData()
    
    session = active_sessions[session_id]
    
    if session.state == StateEnum.MENU:
        session.active_campaign_id = create_new_campaign()
        session.state = StateEnum.PLAYING
        await websocket.send_json({"action": "chat_response", "message": "Iniciado."})

    try:
        while True:
            data = await websocket.receive_text()
            user_input = data.strip()
            
            if session.state == StateEnum.PLAYING:
                system_log, updated_context = await process_turn_pipeline(
                    user_input=user_input, 
                    session_id=session_id, 
                    context=session.context,
                    turn=session.turn,
                    chronicle_name=session.chronicle_name
                )
                session.context = updated_context
                session.turn += 1
                
                # Send updated PlayerSheet state back to client
                await websocket.send_json({"action": "state_update", "player_sheet": session.context.get("player_sheet", {})})
                
                # If pipeline resulted in error, send error and stop turn processing
                if system_log.startswith("[ERROR"):
                    await websocket.send_json({"action": "error", "message": system_log})
                    continue
                
                # Stream narrative back to client
                await websocket.send_json({"action": "stream_start"})
                try:
                    async for chunk in run_narrator_stream(user_input, system_log):
                        await websocket.send_json({"action": "stream_chunk", "chunk": chunk})
                except Exception as e:
                    await websocket.send_json({"action": "error", "message": f"[H6 Error] {str(e)}"})
                    
                await websocket.send_json({"action": "stream_end"})
            else:
                await websocket.send_json({"action": "error", "message": "Estado Inválido."})
                
    except WebSocketDisconnect:
        # Cleanup
        pass
