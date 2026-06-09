from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

# --- GERENCIADOR DE INICIALIZAÇÃO (WS & LOGS) ---
class InitializationManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

initialization_manager = InitializationManager()

class InitLogPayload(BaseModel):
    status: str
    message: str
    phase: int
    timestamp: float

@app.post("/api/initialization/logs")
async def receive_init_log(payload: InitLogPayload):
    data = payload.model_dump()
    data["id"] = f"{payload.timestamp}-{hash(payload.message)}"
    await initialization_manager.broadcast(data)
    return {"status": "ok", "log_id": data["id"]}

@app.websocket("/ws/initialization")
async def websocket_initialization(websocket: WebSocket):
    await initialization_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        initialization_manager.disconnect(websocket)
    except Exception:
        initialization_manager.disconnect(websocket)

@app.post("/api/initialization/retry")
async def retry_initialization():
    import subprocess
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(project_root, "scripts", "initialize_game.py")
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe") if os.name == 'nt' else os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = "python"
        
    cmd = [venv_python, script_path, "--no-browser"]
    try:
        subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
            
            from .state_service import acquire_session_lock
            lock = acquire_session_lock(session_id)
            async with lock:
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
                    from .state_service import global_llm_operation_lock
                    await websocket.send_json({"action": "stream_start"})
                    try:
                        async with global_llm_operation_lock:
                            async for chunk in run_narrator_stream(user_input, system_log, player_sheet=session.context):
                                await websocket.send_json({"action": "stream_chunk", "chunk": chunk})
                    except Exception as e:
                        await websocket.send_json({"action": "error", "message": f"[H6 Error] {str(e)}"})
                        
                    await websocket.send_json({"action": "stream_end"})
                else:
                    await websocket.send_json({"action": "error", "message": "Estado Inválido."})
                    
    except WebSocketDisconnect:
        pass


class UpgradeRequest(BaseModel):
    trait_category: str
    trait_name: str
    new_level: int

@app.post("/session/{session_id}/xp/award")
async def award_xp(session_id: str, amount: int = 1):
    event_data = await load_session_state(session_id)
    if not event_data:
        return {"error": "Sessão não encontrada"}
    
    if not event_data.player_sheet:
        return {"error": "Ficha do jogador ausente"}
        
    from .rules_service import PlayerSheetModel
    from .progression_service import award_session_xp
    
    # Suporte ao envelope herdado do player_sheet
    player_sheet_dict = event_data.player_sheet.get("player_sheet", {}) if "player_sheet" in event_data.player_sheet else event_data.player_sheet
    sheet = PlayerSheetModel(**player_sheet_dict)
    sheet = award_session_xp(sheet, amount)
    
    new_context = event_data.player_sheet
    new_context["player_sheet"] = sheet.model_dump()
    
    event_data = sync_event_from_context(session_id, new_context)
    await save_session_state(session_id, event_data)
    
    # Atualiza em memória se a sessão estiver ativa
    if session_id in active_sessions:
        active_sessions[session_id].context = event_data.player_sheet or {}
        
    return event_data.model_dump()

@app.post("/session/{session_id}/xp/upgrade")
async def upgrade_trait(session_id: str, req: UpgradeRequest):
    event_data = await load_session_state(session_id)
    if not event_data:
        return {"success": False, "error": "Sessão não encontrada"}
        
    if not event_data.player_sheet:
        return {"success": False, "error": "Ficha do jogador ausente"}
        
    from .rules_service import PlayerSheetModel
    from .progression_service import purchase_upgrade
    
    player_sheet_dict = event_data.player_sheet.get("player_sheet", {}) if "player_sheet" in event_data.player_sheet else event_data.player_sheet
    sheet = PlayerSheetModel(**player_sheet_dict)
    success, updated_sheet = purchase_upgrade(sheet, req.trait_category, req.trait_name, req.new_level)
    
    if not success:
        return {"success": False, "error": "XP insuficiente ou melhoria inválida"}
        
    new_context = event_data.player_sheet
    new_context["player_sheet"] = updated_sheet.model_dump()
    
    event_data = sync_event_from_context(session_id, new_context)
    await save_session_state(session_id, event_data)
    
    # Atualiza em memória se a sessão estiver ativa
    if session_id in active_sessions:
        active_sessions[session_id].context = event_data.player_sheet or {}
        
    return {"success": True, "state": event_data.model_dump()}


# --- SERVIR FRONTEND E ARQUIVOS ESTÁTICOS COMPILADOS ---

DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client", "dist")

# Rota para o index.html principal
@app.get("/")
async def serve_index():
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Agente Storyteller V5</h1><p>Aguardando compilação do frontend React...</p>")

# Montar a pasta de assets se ela existir
assets_dir = os.path.join(DIST_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Rota curinga para arquivos avulsos no dist (favicon, etc) ou index.html para SPA router
@app.get("/{catchall:path}")
async def serve_static_or_spa(catchall: str):
    # Ignora caminhos que começam com rotas da api ou ws
    if catchall.startswith("api/") or catchall.startswith("ws/") or catchall.startswith("session/"):
        return {"error": "Not Found"}
        
    file_path = os.path.join(DIST_DIR, catchall)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Agente Storyteller V5</h1><p>Arquivo não encontrado.</p>", status_code=404)

