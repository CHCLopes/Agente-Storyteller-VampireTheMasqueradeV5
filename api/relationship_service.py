"""
api/relationship_service.py
Motor Relacional — Camada 2.
Gerencia relacionamentos políticos com NPCs da campanha.
Projeta o agregado transacional da campanha, evolui com base em ações e gera
um fragmento estruturado para o contexto narrativo.
"""
from pydantic import BaseModel, Field


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
    """Load the canonical relationship aggregate without write side effects."""

    from .state_service import get_persistence

    campaign = await get_persistence().load_campaign(session_id)
    raw = campaign.get("relationships") if campaign else None
    if isinstance(raw, dict) and "relationships" in raw:
        return RelationshipState(**raw)
    if isinstance(raw, list):
        restored: dict[str, NpcRelationship] = {}
        for item in raw:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            restored[str(item["id"])] = NpcRelationship(
                npc_id=str(item["id"]),
                disposition=str(item.get("disposition", "neutral")),
                favor_balance=int(item.get("favor_balance", 0)),
                trust_level=int(item.get("trust_level", 3)),
                history=[str(item["desc"])] if item.get("desc") else [],
            )
        if restored:
            return RelationshipState(session_id=session_id, relationships=restored)
    return RelationshipState(
        session_id=session_id,
        relationships={
            key: value.model_copy(deep=True)
            for key, value in _DEFAULT_RELATIONSHIPS.items()
        },
    )


async def save_relationships(state: RelationshipState):
    """Persist a control-operation relationship snapshot.

    Narrated turns pass the aggregate directly to ``commit_turn`` and must not
    call this compatibility function before narrative validation.
    """

    from .state_service import get_persistence

    store = get_persistence()
    campaign = await store.load_campaign(state.session_id)
    if campaign is None:
        await store.ensure_campaign(
            state.session_id,
            initial_state={},
            relationships=state.model_dump(mode="json"),
        )
        return
    await store.update_campaign_snapshot(
        state.session_id,
        state=campaign.get("state") or {},
        relationships=state.model_dump(mode="json"),
        expected_turn=int(campaign.get("current_turn") or 0),
        expected_revision=int(campaign.get("state_revision") or 0),
    )


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
    action_is_aggressive: bool,
    turn: int,
    *,
    resolution_success: bool | None,
    action_skill: str | None,
    messy_critical: bool = False,
) -> RelationshipState:
    """Update relationships only from structured deterministic outcomes."""
    from .npc_service import find_npc_ids, get_all_npcs

    npcs = get_all_npcs()
    relationship_ids = {"sheriff": "xerife", "prince": "principe"}
    involved_npcs = [
        (relationship_ids.get(npc_id, npc_id), npc_id)
        for npc_id in find_npc_ids(user_input)
    ]

    for npc_key, catalog_id in involved_npcs:
        # Cria relacionamento se NPC é encontrado pela primeira vez
        if npc_key not in state.relationships:
            npc_data = npcs.get(catalog_id)
            initial_trust = 2 if (npc_data and npc_data.engine_data.is_supernatural) else 3
            state.relationships[npc_key] = NpcRelationship(
                npc_id=npc_key,
                trust_level=initial_trust
            )

        rel = state.relationships[npc_key]
        rel.last_interaction_turn = turn

        if action_is_aggressive:
            # Agressão deteriora o relacionamento
            rel.trust_level = max(1, rel.trust_level - 1)
            _shift_disposition_down(rel)

            event = f"T{turn}: Ação agressiva"
            if messy_critical:
                event += " (violenta e descontrolada)"
                rel.trust_level = max(1, rel.trust_level - 1)
            rel.history.append(event)
        else:
            # Interações sociais bem-sucedidas melhoram
            social_skills = {
                "Persuasion",
                "Etiquette",
                "Subterfuge",
                "Intimidation",
            }
            is_social = action_skill in social_skills

            if resolution_success is True and is_social:
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
    """Return a player-safe projection, never storyteller-only counters."""
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
        })

    return result
