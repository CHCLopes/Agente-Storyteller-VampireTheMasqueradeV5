"""
api/memory_service.py
Memória de curto prazo (cena) e longo prazo (campanha).
Camada de persistência narrativa — complementa o estado mecânico do state_service.
"""
import os
import json
import re
from collections.abc import Iterable, Sequence
from datetime import datetime

import aiofiles
from pydantic import BaseModel, Field

from .turn_models import (
    CandidateProposer,
    CandidateValidationStatus,
    CanonicalEvent,
    CanonicalFact,
    Consolidation,
    ConsolidationScope,
    EpisodicMemory,
    MemoryCandidate,
    NarrativeRecord,
    Visibility,
)

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


# --- MEMÓRIA SEMÂNTICA VERSIONADA ---

# A ordem expressa somente restrição de divulgação: uma derivação pode ficar
# mais restrita que suas fontes, mas nunca menos restrita. A autorização de
# leitura continua sendo responsabilidade explícita da montagem de contexto.
_VISIBILITY_RESTRICTION = {
    Visibility.PUBLIC: 0,
    Visibility.PLAYER: 1,
    Visibility.STORYTELLER: 2,
    Visibility.SYSTEM: 3,
}


def derive_memory_candidate(
    event: CanonicalEvent,
    narrative: NarrativeRecord,
    *,
    candidate_id: str,
    summary: str | None = None,
    proposed_by: CandidateProposer = CandidateProposer.DETERMINISTIC,
) -> MemoryCandidate:
    """Derive one semantic candidate without arbitrary character slicing.

    An explicit semantic summary wins; otherwise the event summary is used and,
    if unavailable, the complete narrative is kept. Validation and promotion
    remain separate operations so an LLM proposal can never become memory merely
    by being generated.
    """

    _validate_event_narrative_pair(event, narrative)
    semantic_summary = summary or event.summary or narrative.text
    effective_proposer = proposed_by
    if not summary and not event.summary:
        # Narrative prose is model output, even when this helper is called from
        # deterministic application code.  It must remain pending until an
        # explicit grounding step confirms it against canonical facts.
        effective_proposer = CandidateProposer.LLM
    visibility = _most_restrictive_visibility(
        (event.visibility, narrative.visibility)
    )

    return MemoryCandidate(
        candidate_id=candidate_id,
        session_id=event.session_id,
        turn_id=event.turn_id,
        created_at=narrative.created_at,
        summary=semantic_summary,
        source_event_ids=(event.event_id,),
        tags=event.tags,
        actors=event.actors,
        place=event.place,
        occurred_at=event.occurred_at,
        importance=event.importance,
        visibility=visibility,
        pending=event.pending,
        proposed_by=effective_proposer,
        validation_status=CandidateValidationStatus.PENDING,
    )


def validate_memory_candidate(
    candidate: MemoryCandidate,
    *,
    events: Iterable[CanonicalEvent],
    narratives: Iterable[NarrativeRecord],
    facts: Iterable[CanonicalFact],
    semantic_grounding_confirmed: bool = False,
) -> MemoryCandidate:
    """Validate provenance and return the same candidate marked ``ACCEPTED``.

    Validation is intentionally structural and deterministic: every referenced
    event and fact must exist, narrative coverage must exist, session/turn must
    agree, and candidate visibility cannot be broader than any source. Semantic
    truth remains anchored in canonical facts rather than inferred from prose.
    """

    if candidate.validation_status is CandidateValidationStatus.REJECTED:
        raise ValueError("a rejected memory candidate cannot be accepted")
    if (
        candidate.proposed_by is CandidateProposer.LLM
        and not semantic_grounding_confirmed
    ):
        data = candidate.model_dump()
        data["validation_status"] = CandidateValidationStatus.PENDING
        data["validation_notes"] = (
            "LLM summary requires explicit deterministic or human grounding review",
        )
        return MemoryCandidate.model_validate(data)

    event_by_id = _unique_by_id(events, lambda event: event.event_id, "event")
    fact_by_id = _unique_by_id(facts, lambda fact: fact.fact_id, "fact")
    narrative_by_id = _unique_by_id(
        narratives, lambda narrative: narrative.narrative_id, "narrative"
    )

    source_events: list[CanonicalEvent] = []
    for event_id in candidate.source_event_ids:
        event = event_by_id.get(event_id)
        if event is None:
            raise ValueError(f"memory candidate references unknown event {event_id!r}")
        if event.session_id != candidate.session_id or event.turn_id != candidate.turn_id:
            raise ValueError("memory candidate, source events, session, and turn must agree")
        source_events.append(event)

    covered_event_ids: set[str] = set()
    source_narratives: list[NarrativeRecord] = []
    for narrative in narrative_by_id.values():
        matching_ids = set(narrative.source_event_ids) & set(candidate.source_event_ids)
        if not matching_ids:
            continue
        if (
            narrative.session_id != candidate.session_id
            or narrative.turn_id != candidate.turn_id
        ):
            raise ValueError(
                "memory candidate, source narratives, session, and turn must agree"
            )
        covered_event_ids.update(matching_ids)
        source_narratives.append(narrative)

    missing_narratives = set(candidate.source_event_ids) - covered_event_ids
    if missing_narratives:
        raise ValueError(
            "memory candidate events lack completed narrative sources: "
            f"{sorted(missing_narratives)}"
        )

    source_facts: list[CanonicalFact] = []
    for event in source_events:
        for fact_id in event.fact_ids:
            fact = fact_by_id.get(fact_id)
            if fact is None:
                raise ValueError(
                    f"canonical event {event.event_id!r} references unknown fact "
                    f"{fact_id!r}"
                )
            source_facts.append(fact)

    source_visibilities = [event.visibility for event in source_events]
    source_visibilities.extend(narrative.visibility for narrative in source_narratives)
    source_visibilities.extend(fact.visibility for fact in source_facts)
    required_visibility = _most_restrictive_visibility(source_visibilities)
    if (
        _VISIBILITY_RESTRICTION[candidate.visibility]
        < _VISIBILITY_RESTRICTION[required_visibility]
    ):
        raise ValueError("memory candidate cannot broaden source visibility")

    if candidate.validation_status is CandidateValidationStatus.ACCEPTED:
        return candidate

    data = candidate.model_dump()
    data["validation_status"] = CandidateValidationStatus.ACCEPTED
    data["validation_notes"] = (
        "sources, session, turn, facts, and visibility validated",
    )
    return MemoryCandidate.model_validate(data)


def promote_memory_candidate(
    candidate: MemoryCandidate,
    *,
    memory_id: str,
    version: int = 1,
) -> EpisodicMemory:
    """Promote an accepted candidate while preserving canonical source ids."""

    if candidate.validation_status is not CandidateValidationStatus.ACCEPTED:
        raise ValueError("only an accepted memory candidate can be promoted")

    return EpisodicMemory(
        memory_id=memory_id,
        session_id=candidate.session_id,
        created_at=candidate.created_at,
        summary=candidate.summary,
        source_event_ids=candidate.source_event_ids,
        tags=candidate.tags,
        actors=candidate.actors,
        place=candidate.place,
        occurred_at=candidate.occurred_at,
        importance=candidate.importance,
        visibility=candidate.visibility,
        pending=candidate.pending,
        version=version,
    )


def build_grounded_consolidation_summary(
    sources: Iterable[tuple[str, str]],
) -> str:
    """Project source memories without adding new claims or causal links."""

    summaries_by_id: dict[str, str] = {}
    for memory_id, summary in sources:
        normalized_id = memory_id.strip()
        normalized_summary = summary.strip()
        if not normalized_id or not normalized_summary:
            raise ValueError("consolidation sources require ids and summaries")
        previous_summary = summaries_by_id.get(normalized_id)
        if previous_summary is not None and previous_summary != normalized_summary:
            raise ValueError("one source memory id cannot have conflicting summaries")
        summaries_by_id[normalized_id] = normalized_summary
    if not summaries_by_id:
        raise ValueError("consolidation requires at least one grounded summary")
    return "\n".join(
        f"- {summaries_by_id[memory_id]}" for memory_id in sorted(summaries_by_id)
    )


def create_consolidation(
    memories: Sequence[EpisodicMemory],
    *,
    consolidation_id: str,
    scope: ConsolidationScope,
    proposed_summary: str | None = None,
    previous: Consolidation | None = None,
    created_at: datetime | None = None,
    tags: Sequence[str] | None = None,
    visibility: Visibility | None = None,
) -> Consolidation:
    """Create a source-grounded consolidation without deleting its memories.

    ``proposed_summary`` is deliberately non-canonical. It may be retained by a
    caller for review, but this factory never promotes it. The durable summary
    is a deterministic projection of the already validated episodic memories.
    """

    if not memories:
        raise ValueError("consolidation requires at least one episodic memory")

    session_ids = {memory.session_id for memory in memories}
    if len(session_ids) != 1:
        raise ValueError("all consolidation sources must belong to one session")
    session_id = next(iter(session_ids))

    source_memory_ids = tuple(sorted({memory.memory_id for memory in memories}))
    source_event_ids = tuple(
        sorted(
            {
                event_id
                for memory in memories
                for event_id in memory.source_event_ids
            }
        )
    )
    grounded_summary = build_grounded_consolidation_summary(
        (memory.memory_id, memory.summary) for memory in memories
    )
    source_visibility = _most_restrictive_visibility(
        memory.visibility for memory in memories
    )
    consolidation_visibility = visibility or source_visibility
    if (
        _VISIBILITY_RESTRICTION[consolidation_visibility]
        < _VISIBILITY_RESTRICTION[source_visibility]
    ):
        raise ValueError("consolidation cannot broaden source visibility")

    consolidated_tags = tuple(
        tags
        if tags is not None
        else sorted({tag for memory in memories for tag in memory.tags})
    )

    if previous is not None:
        if previous.session_id != session_id or previous.scope is not scope:
            raise ValueError(
                "previous consolidation must match the source session and scope"
            )
        if (
            previous.source_memory_ids == source_memory_ids
            and previous.source_event_ids == source_event_ids
            and previous.summary == grounded_summary
            and previous.tags == consolidated_tags
            and previous.visibility is consolidation_visibility
        ):
            return previous
        version = previous.version + 1
        supersedes = previous.consolidation_id
    else:
        version = 1
        supersedes = None

    consolidation_time = created_at or max(memory.created_at for memory in memories)
    return Consolidation(
        consolidation_id=consolidation_id,
        session_id=session_id,
        scope=scope,
        created_at=consolidation_time,
        version=version,
        summary=grounded_summary,
        source_memory_ids=source_memory_ids,
        source_event_ids=source_event_ids,
        tags=consolidated_tags,
        visibility=consolidation_visibility,
        supersedes_consolidation_id=supersedes,
    )


def _validate_event_narrative_pair(
    event: CanonicalEvent, narrative: NarrativeRecord
) -> None:
    if event.session_id != narrative.session_id or event.turn_id != narrative.turn_id:
        raise ValueError("canonical event and narrative must share session and turn")
    if event.event_id not in narrative.source_event_ids:
        raise ValueError("narrative does not reference the canonical event")


def _most_restrictive_visibility(
    visibilities: Iterable[Visibility],
) -> Visibility:
    values = tuple(visibilities)
    if not values:
        raise ValueError("at least one source visibility is required")
    return max(values, key=lambda value: _VISIBILITY_RESTRICTION[value])


def _unique_by_id(items, key, label: str):
    indexed = {}
    for item in items:
        item_id = key(item)
        if item_id in indexed:
            raise ValueError(f"duplicate {label} id {item_id!r}")
        indexed[item_id] = item
    return indexed
