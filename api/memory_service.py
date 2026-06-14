"""
api/memory_service.py
Memória de curto prazo (cena) e longo prazo (campanha).
Camada de persistência narrativa — complementa o estado mecânico do state_service.
"""
import os
import json
import re
import aiofiles
from pydantic import BaseModel, Field

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")


class SceneMemory(BaseModel):
    """Memória de curto prazo — contexto da cena atual."""
    current_location: str = "Desconhecido"
    scene_summary: str = ""
    npcs_present: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    mood: str = "neutral"
    last_updated_turn: int = 0


class CampaignMemory(BaseModel):
    """Memória de longo prazo — fatos acumulados da campanha."""
    key_decisions: list[dict] = Field(default_factory=list)
    chronicle_arcs: list[str] = Field(default_factory=list)
    masquerade_breaches: int = 0
    total_kills: int = 0
    notable_npcs_encountered: list[str] = Field(default_factory=list)
    last_updated_turn: int = 0


class SessionMemory(BaseModel):
    """Container de memória completa da sessão."""
    session_id: str
    scene: SceneMemory = Field(default_factory=SceneMemory)
    campaign: CampaignMemory = Field(default_factory=CampaignMemory)


async def load_memory(session_id: str) -> SessionMemory:
    """Carrega memória da sessão do disco. Retorna nova instância se inexistente."""
    path = os.path.join(SAVE_DIR, f"{session_id}_memory.json")
    if not os.path.exists(path):
        return SessionMemory(session_id=session_id)
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return SessionMemory(**data)
    except Exception:
        return SessionMemory(session_id=session_id)


async def save_memory(memory: SessionMemory):
    """Persiste memória da sessão em disco."""
    path = os.path.join(SAVE_DIR, f"{memory.session_id}_memory.json")
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(memory.model_dump(), indent=4, ensure_ascii=False))


def update_scene_memory(
    memory: SessionMemory,
    system_log: str,
    user_input: str,
    turn: int
) -> SessionMemory:
    """Atualiza memória de cena com base na ação do turno atual."""
    scene = memory.scene

    # Registra evento recente (máximo 10)
    event_summary = f"T{turn}: {user_input[:80]}"
    scene.recent_events.append(event_summary)
    if len(scene.recent_events) > 10:
        scene.recent_events = scene.recent_events[-10:]

    scene.last_updated_turn = turn

    # Detecta NPCs mencionados no input
    from .npc_service import get_all_npcs
    npcs = get_all_npcs()
    normalized = user_input.lower().replace('í', 'i').replace('ç', 'c')
    for npc_key in npcs.keys():
        if re.search(r'\b' + re.escape(npc_key) + r'\b', normalized):
            if npc_key not in scene.npcs_present:
                scene.npcs_present.append(npc_key)

    # Atualiza contadores de campanha
    campaign = memory.campaign
    if "Alimentação fatal" in system_log:
        campaign.total_kills += 1
    if "Máscara" in system_log or "masquerade" in system_log.lower():
        campaign.masquerade_breaches += 1

    campaign.last_updated_turn = turn

    # Registra NPCs notáveis na campanha
    for npc in scene.npcs_present:
        if npc not in campaign.notable_npcs_encountered:
            campaign.notable_npcs_encountered.append(npc)

    return memory


def build_memory_prompt_fragment(memory: SessionMemory) -> str:
    """Gera fragmento de prompt com contexto de memória para o narrador H6."""
    parts = []

    scene = memory.scene
    if scene.recent_events:
        events_text = "; ".join(scene.recent_events[-5:])
        parts.append(f"Eventos recentes: {events_text}")
    if scene.npcs_present:
        parts.append(f"NPCs na cena: {', '.join(scene.npcs_present)}")
    if scene.current_location != "Desconhecido":
        parts.append(f"Local atual: {scene.current_location}")

    campaign = memory.campaign
    if campaign.masquerade_breaches > 0:
        parts.append(f"Quebras de Máscara na campanha: {campaign.masquerade_breaches}")
    if campaign.total_kills > 0:
        parts.append(f"Mortes causadas na campanha: {campaign.total_kills}")
    if campaign.key_decisions:
        recent = campaign.key_decisions[-3:]
        parts.append(f"Decisões-chave: {'; '.join(d.get('summary', '') for d in recent)}")

    if not parts:
        return ""

    return "[MEMÓRIA DA SESSÃO]:\n" + "\n".join(f"- {p}" for p in parts)
