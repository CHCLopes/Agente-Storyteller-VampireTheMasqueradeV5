from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

app = FastAPI(title="Agente Storyteller Motor V5")

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

class GameState(BaseModel):
    session_id: str
    chronicle_name: str
    turn: int
    context: dict

@app.get("/health")
async def health_check():
    return {"status": "ok", "system": "Agente Storyteller Motor V5"}

@app.post("/state")
async def save_state(state: GameState):
    # AppSec: Prevenção básica de path traversal
    safe_filename = os.path.basename(f"{state.session_id}.json")
    save_path = os.path.join(SAVE_DIR, safe_filename)
    
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, indent=4)
        return {"status": "saved", "file": safe_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state/{session_id}")
async def load_state(session_id: str):
    safe_filename = os.path.basename(f"{session_id}.json")
    load_path = os.path.join(SAVE_DIR, safe_filename)
    
    if not os.path.exists(load_path):
        raise HTTPException(status_code=404, detail="Save state not found")
        
    with open(load_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
