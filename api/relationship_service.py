"""
api/relationship_service.py
Motor Relacional — Camada 2.
Gerencia relacionamentos políticos com NPCs da campanha.
Persiste em JSON por sessão, evolui com base em ações, gera fragmento de prompt.
"""
import os
import json
import re
import aiofiles
from pydantic import BaseModel, Field

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")


class NpcRelationship(BaseModel):
    """Estado de relacionamento com um NPC."""
    npc_id: str
    disposition: str = "neutral"  # hostile, unfavorable, neutral, favorable, allied
    favor_balance: int = 0       # negativo = dívidas, positivo = favores a receber
    trust_level: int = 3         # 1-5
    last_interaction_turn: int = 0
    history: list[str] = Field(default_factory=list)


class RelationshipState(BaseModel):
    """Estado de todos os relacionamentos de uma sessão."""
    session_id: str
    relationships: dict[str, NpcRelationship] = Field(default_factory=dict)


# Relacionamentos iniciais padrão da campanha
_DEFAULT_RELATIONSHIPS = {
    "xerife": NpcRelationship(
        npc_id="xerife",
        disposition="neutral",
        favor_balance=-1,
        trust_level=2,
        history=["Dívida: ocultou uma quebra de Máscara no cais"]
    ),
    "primogenito_brujah": NpcRelationship(
        npc_id="primogenito_brujah",
        disposition="favorable",
        favor_balance=0,
        trust_level=3,
        history=["Aliança de sangue proposta em troca de lealdade"]
    ),
    "principe": NpcRelationship(
        npc_id="principe",
        disposition="unfavorable",
        favor_balance=0,
        trust_level=1,
        history=["Vigilância constante sobre suas atividades"]
    ),
}


async def load_relationships(session_id: str) -> RelationshipState:
    """Carrega relacionamentos da sessão. Inicializa com defaults se inexistente."""
    path = os.path.join(SAVE_DIR, f"{session_id}_relationships.json")
    if not os.path.exists(path):
        state = RelationshipState(
            session_id=session_id,
            relationships={k: v.model_copy() for k, v in _DEFAULT_RELATIONSHIPS.items()}
        )
        await save_relationships(state)
        return state
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return RelationshipState(**data)
    except Exception:
        return RelationshipState(
            session_id=session_id,
            relationships={k: v.model_copy() for k, v in _DEFAULT_RELATIONSHIPS.items()}
        )


async def save_relationships(state: RelationshipState):
    """Persiste relacionamentos em disco."""
    path = os.path.join(SAVE_DIR, f"{state.session_id}_relationships.json")
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(state.model_dump(), indent=4, ensure_ascii=False))


_DISPOSITION_LADDER = ["hostile", "unfavorable", "neutral", "favorable", "allied"]


def _shift_disposition_up(rel: NpcRelationship):
    idx = _DISPOSITION_LADDER.index(rel.disposition) if rel.disposition in _DISPOSITION_LADDER else 2
    if idx < len(_DISPOSITION_LADDER) - 1:
        rel.disposition = _DISPOSITION_LADDER[idx + 1]


def _shift_disposition_down(rel: NpcRelationship):
    idx = _DISPOSITION_LADDER.index(rel.disposition) if rel.disposition in _DISPOSITION_LADDER else 2
    if idx > 0:
        rel.disposition = _DISPOSITION_LADDER[idx - 1]


def update_relationships_from_action(
    state: RelationshipState,
    user_input: str,
    system_log: str,
    action_is_aggressive: bool,
    turn: int
) -> RelationshipState:
    """Atualiza relacionamentos com base nas ações do jogador (Camada 2 programática)."""
    from .npc_service import get_all_npcs

    npcs = get_all_npcs()
    normalized = user_input.lower().replace('í', 'i').replace('ç', 'c')

    involved_npcs = []
    for npc_key in npcs.keys():
        if re.search(r'\b' + re.escape(npc_key) + r'\b', normalized):
            involved_npcs.append(npc_key)

    for npc_key in involved_npcs:
        # Cria relacionamento se NPC é encontrado pela primeira vez
        if npc_key not in state.relationships:
            npc_data = npcs.get(npc_key)
            initial_trust = 2 if (npc_data and npc_data.engine_data.is_supernatural) else 3
            state.relationships[npc_key] = NpcRelationship(
                npc_id=npc_key,
                trust_level=initial_trust
            )

        rel = state.relationships[npc_key]
        rel.last_interaction_turn = turn

        is_success = "sucesso" in system_log.lower() or "Ação executada" in system_log

        if action_is_aggressive:
            # Agressão deteriora o relacionamento
            rel.trust_level = max(1, rel.trust_level - 1)
            _shift_disposition_down(rel)

            event = f"T{turn}: Ação agressiva"
            if "Messy Critical" in system_log:
                event += " (violenta e descontrolada)"
                rel.trust_level = max(1, rel.trust_level - 1)
            rel.history.append(event)
        else:
            # Interações sociais bem-sucedidas melhoram
            social_skills = [
                "persuasion", "persuasão", "etiquette", "etiqueta",
                "subterfuge", "subterfúgio", "intimidation", "intimidação"
            ]
            is_social = any(s in system_log.lower() or s in user_input.lower() for s in social_skills)

            if is_success and is_social:
                rel.trust_level = min(5, rel.trust_level + 1)
                _shift_disposition_up(rel)
                rel.history.append(f"T{turn}: Interação social bem-sucedida")
            else:
                rel.history.append(f"T{turn}: Encontro neutro")

        # Limita histórico a 5 entradas
        if len(rel.history) > 5:
            rel.history = rel.history[-5:]

    return state


def build_relationship_prompt_fragment(state: RelationshipState) -> str:
    """Gera fragmento de prompt para o narrador H6."""
    if not state.relationships:
        return ""

    disp_pt = {
        "hostile": "Hostil",
        "unfavorable": "Desfavorável",
        "neutral": "Neutro",
        "favorable": "Favorável",
        "allied": "Aliado",
    }

    parts = []
    for npc_id, rel in state.relationships.items():
        d = disp_pt.get(rel.disposition, rel.disposition)
        latest = rel.history[-1] if rel.history else "Sem histórico"
        parts.append(f"{npc_id.replace('_', ' ').title()}: {d} (Confiança {rel.trust_level}/5). {latest}")

    return "[MOTOR RELACIONAL — ESTADO POLÍTICO]:\n" + "\n".join(f"- {p}" for p in parts)


def get_relationships_for_frontend(state: RelationshipState) -> list[dict]:
    """Formata relacionamentos para envio ao frontend via WebSocket."""
    disp_titles = {
        "hostile": "Inimigo declarado",
        "unfavorable": "Relação tensa",
        "neutral": "Relação neutra",
        "favorable": "Aliança tática",
        "allied": "Aliado de sangue",
    }

    result = []
    for npc_id, rel in state.relationships.items():
        npc_label = npc_id.replace("_", " ").title()
        title = f"{disp_titles.get(rel.disposition, 'Desconhecido')} — {npc_label}"
        desc = rel.history[-1] if rel.history else "Sem interações registradas."
        result.append({
            "id": npc_id,
            "titulo": title,
            "desc": desc,
            "disposition": rel.disposition,
            "trust_level": rel.trust_level,
            "favor_balance": rel.favor_balance,
        })

    return result
