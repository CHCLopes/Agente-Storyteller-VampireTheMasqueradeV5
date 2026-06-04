from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from enum import Enum
import json
import os
import uuid
import asyncio
import time
from .rules_service import PlayerSheetModel
from .orchestrator_service import process_turn_pipeline, run_narrator_stream
from .state_service import (
    SAVE_DIR,
    save_session_state,
    load_session_state,
    StateUpdateEvent,
    CharacterModel,
    TrackersModel,
    TrackerDetail,
    CharacterAttributes,
    ContextModel,
    PendingRollModel,
    sync_event_from_context
)

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
    
    # Carrega o estado inicial a partir do save ou cria um novo
    event_data = await load_session_state(session_id)
    if not event_data:
        try:
            sheet_model = load_player_sheet("base_player")
            initial_context = {
                "player_sheet": sheet_model.model_dump(),
                "last_action_cache": None,
                "pre_roll_snapshot": None
            }
        except Exception:
            initial_context = {}
        event_data = sync_event_from_context(session_id, initial_context)
        await save_session_state(session_id, event_data)
        
    if session_id not in active_sessions:
        active_sessions[session_id] = SessionData()
        
    session = active_sessions[session_id]
    session.context = event_data.player_sheet or {}
    
    if session.state == StateEnum.MENU:
        session.active_campaign_id = create_new_campaign()
        session.state = StateEnum.PLAYING
        await websocket.send_json(event_data.model_dump())
        await websocket.send_json({"action": "chat_response", "message": "Iniciado."})

    try:
        while True:
            data = await websocket.receive_text()
            user_input = data.strip()
            
            # Recarrega o estado em disco para garantir sincronização entre conexões/arquivos
            event_data = await load_session_state(session_id)
            if not event_data:
                event_data = sync_event_from_context(session_id, session.context)
                await save_session_state(session_id, event_data)
                
            session.context = event_data.player_sheet or {}
            
            # --- INTERCEPTOR DE TORPOR (Passo 2) ---
            if event_data.character.status == "TORPOR":
                await websocket.send_json({
                    "action": "error",
                    "message": "[BLOQUEIO DE FLUXO] O personagem está em TORPOR e não pode realizar ações físicas ou narrativas."
                })
                await websocket.send_json(event_data.model_dump())
                continue
                
            # --- INTERCEPTOR DE FRENZY CHECK (Passo 3) ---
            if event_data.character.status == "FRENZY_CHECK":
                pool_size = event_data.character.attributes.self_control + event_data.character.attributes.resolve
                hunger = event_data.character.fome
                
                from .rules_service import _roll_v5_dice
                roll_result = _roll_v5_dice(dice_pool=pool_size, hunger=hunger, difficulty=3)
                
                if roll_result.is_success:
                    # Sucesso! Restaura status para ACTIVE
                    event_data.character.status = "ACTIVE"
                    event_data.context.current_state = "ACTIVE"
                    event_data.context.blocking = False
                    event_data.context.pending_roll = None
                    
                    # Atualiza o player_sheet legado
                    if event_data.player_sheet and "player_sheet" in event_data.player_sheet:
                        # Reseta a fome para 4 após resistir ao Frenesi se o usuário desejar,
                        # mas por padrão mecânico mantemos como estava, apenas destravando o status.
                        pass
                        
                    await save_session_state(session_id, event_data)
                    
                    await websocket.send_json({
                        "action": "chat_response",
                        "message": f"[TESTE DE FRENESI] Sucesso! Você manteve o controle. Rolagem: {roll_result.normal_rolls} / dados de fome: {roll_result.hunger_rolls}. {roll_result.summary}"
                    })
                    await websocket.send_json(event_data.model_dump())
                else:
                    # Falha! Personagem sucumbe ao Frenesi
                    await websocket.send_json({
                        "action": "chat_response",
                        "message": f"[TESTE DE FRENESI] Falha! A Besta assume o controle. Você entrou em FRENESI. Rolagem: {roll_result.normal_rolls} / dados de fome: {roll_result.hunger_rolls}. {roll_result.summary}"
                    })
                    await websocket.send_json(event_data.model_dump())
                continue

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
                
                # Mapeamento dinâmico de status críticos após o processamento do pipeline de regras (Passo 3)
                current_hunger = updated_context.get("player_sheet", {}).get("status", {}).get("current_hunger", 0)
                status_override = None
                
                # Se a fome atingir 5 ou mais, força o status FRENZY_CHECK
                if current_hunger >= 5:
                    status_override = "FRENZY_CHECK"
                    
                # Se o dano agravado preencher a vida total, entra em TORPOR
                health_data = updated_context.get("player_sheet", {}).get("status", {}).get("health_tracker", {})
                if health_data.get("aggravated", 0) >= health_data.get("size", 7):
                    status_override = "TORPOR"
                    
                event_data = sync_event_from_context(session_id, updated_context, status_override=status_override)
                await save_session_state(session_id, event_data)
                
                # Envia o JSON estruturado do evento para o cliente
                await websocket.send_json(event_data.model_dump())
                
                # Se pipeline resultou em erro, envia erro e interrompe processamento
                if system_log.startswith("[ERROR"):
                    await websocket.send_json({"action": "error", "message": system_log})
                    continue
                    
                # Se o personagem entrou em estado de bloqueio (Frenesi ou Torpor), não prossegue para o LLM narrar
                if event_data.context.blocking:
                    continue
                
                # Stream narrative de volta para o cliente
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
        pass
