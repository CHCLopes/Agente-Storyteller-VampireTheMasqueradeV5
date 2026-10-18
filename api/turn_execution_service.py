"""Transactional execution of a prepared deterministic narrative turn."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from anyio import CancelScope

from .llm.contract import (
    CancellationToken,
    ErrorCategory,
    InvocationEvidence,
    InvocationRecord,
    LLMGateway,
    LLMTarget,
    NormalizedError,
    OperationPhase,
    StreamEventKind,
    utc_now,
)
from .memory_service import (
    derive_memory_candidate,
    promote_memory_candidate,
    validate_memory_candidate,
)
from .narration_resume_service import (
    PauseEligibility,
    classify_pause_eligibility,
    gate_from_error,
    normalize_gate_timing,
)
from .orchestrator_service import TurnPipelineResult, run_narrator_events
from .persistence import AttemptResult, SQLitePersistence
from .scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    merge_scene_threads,
    project_scene,
    scene_thread_key,
    validate_scene_continuation,
    validate_mechanical_narrative,
)
from .scene_service import SceneState, scene_from_context
from .scene_resolution_service import SceneBeatResolution
from .state_service import StateUpdateEvent, sync_event_from_context
from .turn_models import (
    CandidateProposer,
    CanonicalEvent,
    CanonicalFact,
    EntityReference,
    NarrativeRecord,
    RecordReference,
    StateChange,
    Visibility,
    NarrationPauseProjection,
    NarrationResumeCapsule,
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
)


ChunkCallback = Callable[[str], Awaitable[None]]


def restore_prepared_turn_from_capsule(
    capsule_payload: Mapping[str, Any], *, resume_operation_id: str,
) -> TurnPipelineResult:
    """Restore only frozen deterministic inputs; this never invokes H0/H1/H4/RNG."""
    from .context_service import LayeredContext
    from .relationship_service import RelationshipState

    capsule = NarrationResumeCapsule.model_validate(capsule_payload)
    frozen = capsule.frozen_context
    if not isinstance(frozen, Mapping):
        raise ValueError("resume capsule context is invalid")
    context_packet = frozen.get("context_packet")
    relationships_state = frozen.get("relationships_state")
    return TurnPipelineResult(
        kind="action",
        system_log=str(frozen.get("system_log") or ""),
        updated_context=dict(frozen.get("updated_context") or {}),
        relationships_state=(
            RelationshipState.model_validate(relationships_state)
            if relationships_state is not None else None
        ),
        relationships_for_frontend=list(frozen.get("relationships_for_frontend") or []),
        draft=capsule.draft.model_copy(
            update={"attempt_id": f"attempt-{resume_operation_id}"},
        ),
        context_packet=(
            LayeredContext.model_validate(context_packet)
            if context_packet is not None else None
        ),
        llm_invocations=[],
    )


class ClientTurnCancelledError(Exception):
    pass


class NarrativeContractError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate_narrative_contract(
    text: str,
    *,
    facts: Iterable[Any] = (),
    min_words: int = 25,
    max_words: int = 150,
    scene_proposal: SceneContinuationProposal | None = None,
    player_input: str = "",
    current_scene: SceneState | None = None,
) -> str:
    """Validate player prose after its structured scene proposal was admitted."""

    normalized = text.strip()
    if not normalized:
        raise NarrativeContractError("narrative_empty")
    paragraphs = tuple(
        paragraph.strip()
        for paragraph in re.split(r"(?:\r?\n){2,}", normalized)
        if paragraph.strip()
    )
    if len(paragraphs) > 3:
        raise NarrativeContractError("narrative_paragraph_limit")
    if not re.search(r"[.!?][\"'»”)]*$", normalized):
        raise NarrativeContractError("narrative_not_declarative")
    if re.match(r"^(?:[#>*-]|\d+[.)]|\[[^\]]+\])", normalized):
        raise NarrativeContractError("narrative_internal_format")
    lowered = normalized.casefold()
    forbidden_fragments = (
        "fatos canônicos",
        "system log",
        "[ação]",
        "[resultado]",
        "pool de dados",
        "dificuldade ",
        "sucesso(s)",
        "normal_rolls",
        "hunger_rolls",
    )
    if any(fragment in lowered for fragment in forbidden_fragments):
        raise NarrativeContractError("narrative_internal_content")
    words = re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", normalized, flags=re.UNICODE)
    if len(words) < min_words:
        raise NarrativeContractError("narrative_word_minimum")
    if len(words) > max_words:
        raise NarrativeContractError("narrative_word_limit")

    fact_records = tuple(facts)
    resolution = next(
        iter(_fact_payloads(fact_records, "mechanics.resolution")), None
    )
    if resolution is not None and isinstance(resolution.get("is_success"), bool):
        if scene_proposal is not None and normalized != scene_proposal.player_text.strip():
            raise NarrativeContractError("narrative_proposal_mismatch")
        try:
            validate_mechanical_narrative(
                scene_proposal.narrative if scene_proposal else normalized,
                outcome="success" if resolution["is_success"] else "failure",
                proposal=scene_proposal, player_input=player_input, current_scene=current_scene,
            )
        except SceneProposalError as exc:
            raise NarrativeContractError("narrative_outcome_mismatch") from exc

    return normalized


_ATTRIBUTE_LABELS = {
    "Strength": "Força",
    "Dexterity": "Destreza",
    "Stamina": "Vigor",
    "Charisma": "Carisma",
    "Manipulation": "Manipulação",
    "Composure": "Autocontrole",
    "Intelligence": "Inteligência",
    "Wits": "Raciocínio",
    "Resolve": "Determinação",
}

_SKILL_LABELS = {
    "Athletics": "Atletismo",
    "Brawl": "Briga",
    "Craft": "Ofício",
    "Drive": "Condução",
    "Firearms": "Armas de Fogo",
    "Larceny": "Ladinagem",
    "Melee": "Armas Brancas",
    "Stealth": "Furtividade",
    "Survival": "Sobrevivência",
    "AnimalKen": "Trato com Animais",
    "Etiquette": "Etiqueta",
    "Insight": "Intuição",
    "Intimidation": "Intimidação",
    "Leadership": "Liderança",
    "Performance": "Performance",
    "Persuasion": "Persuasão",
    "Streetwise": "Manha",
    "Subterfuge": "Subterfúgio",
    "Academics": "Acadêmicos",
    "Awareness": "Percepção",
    "Finance": "Finanças",
    "Investigation": "Investigação",
    "Medicine": "Medicina",
    "Occult": "Ocultismo",
    "Politics": "Política",
    "Science": "Ciência",
    "Technology": "Tecnologia",
}


def _fact_payloads(
    facts: Iterable[Any], fact_type: str
) -> Iterable[Mapping[str, Any]]:
    for fact in facts:
        current_type = (
            fact.get("fact_type") if isinstance(fact, Mapping) else getattr(fact, "fact_type", None)
        )
        if current_type != fact_type:
            continue
        value = fact.get("value") if isinstance(fact, Mapping) else getattr(fact, "value", None)
        if isinstance(value, Mapping):
            yield value


def _explicit_authorized_narrative_texts(facts: Iterable[Any]) -> tuple[str, ...]:
    fact_records = tuple(facts)
    authorized: list[str] = []
    for fact in fact_records:
        if isinstance(fact, Mapping):
            fact_type = fact.get("fact_type")
            visibility = fact.get("visibility")
            value = fact.get("value")
        else:
            fact_type = getattr(fact, "fact_type", None)
            raw_visibility = getattr(fact, "visibility", None)
            visibility = getattr(raw_visibility, "value", raw_visibility)
            value = getattr(fact, "value", None)
        if fact_type != "narrative.authorized_text":
            continue
        if visibility not in {"public", "player"}:
            continue
        text = value.get("text") if isinstance(value, Mapping) else value
        if isinstance(text, str) and text.strip():
            authorized.append(text.strip())
    return tuple(dict.fromkeys(authorized))


def _authorized_narrative_texts(facts: Iterable[Any]) -> tuple[str, ...]:
    """Return only closed player-visible projections approved by the domain."""

    fact_records = tuple(facts)
    explicit = _explicit_authorized_narrative_texts(fact_records)
    deterministic = _deterministic_contract_fallback(fact_records)
    authorized = [deterministic] if deterministic is not None else []
    authorized.extend(explicit)
    return tuple(dict.fromkeys(authorized))


def build_resolution_receipt(
    facts: Iterable[Any],
    *,
    turn_id: str,
    narrative_mode: str = "llm",
) -> dict[str, Any] | None:
    """Project the player-visible mechanical fact without asking H6 to cite rules."""

    payload = next(iter(_fact_payloads(facts, "mechanics.resolution")), None)
    if payload is None:
        return None
    required = (
        "attribute",
        "skill",
        "dice_pool",
        "hunger_dice",
        "difficulty",
        "normal_rolls",
        "hunger_rolls",
        "successes",
        "margin",
        "is_success",
    )
    if any(key not in payload for key in required):
        return None
    attribute = str(payload["attribute"])
    skill = str(payload["skill"])
    normal_rolls = [int(value) for value in payload["normal_rolls"]]
    hunger_rolls = [int(value) for value in payload["hunger_rolls"]]
    outcome = "Sucesso" if bool(payload["is_success"]) else "Falha"
    if bool(payload.get("messy_critical")):
        outcome = "Crítico Bestial"
    elif bool(payload.get("bestial_failure")):
        outcome = "Falha Bestial"
    successes = int(payload["successes"])
    success_label = "sucesso" if successes == 1 else "sucessos"
    display = (
        f"{_ATTRIBUTE_LABELS.get(attribute, attribute)} + "
        f"{_SKILL_LABELS.get(skill, skill)} · {int(payload['dice_pool'])} dados "
        f"({int(payload['hunger_dice'])} de Fome) · dificuldade {int(payload['difficulty'])} "
        f"· normais {normal_rolls or '—'} · Fome {hunger_rolls or '—'} · "
        f"{successes} {success_label} · margem {int(payload['margin']):+d} · {outcome}"
    )
    if narrative_mode.startswith("deterministic_"):
        display += " · narração segura aplicada"
    return {
        "receipt_id": f"receipt-{turn_id}",
        "attribute": attribute,
        "skill": skill,
        "dice_pool": int(payload["dice_pool"]),
        "hunger_dice": int(payload["hunger_dice"]),
        "difficulty": int(payload["difficulty"]),
        "normal_rolls": normal_rolls,
        "hunger_rolls": hunger_rolls,
        "successes": successes,
        "margin": int(payload["margin"]),
        "outcome": outcome,
        "narrative_mode": narrative_mode,
        "display": display,
    }


def _deterministic_contract_fallback(facts: Iterable[Any]) -> str | None:
    fact_records = tuple(facts)
    explicit = _explicit_authorized_narrative_texts(fact_records)
    if explicit:
        return explicit[0]
    scene_payload = next(iter(_fact_payloads(fact_records, "world.scene")), None)
    if scene_payload is not None:
        location = scene_payload.get("location")
        if scene_payload.get("status") == "known" and isinstance(location, str):
            return (
                f"Você permanece em {location}, mas a direção improvisacional não "
                "conseguiu concluir este beat; os elementos já estabelecidos da cena "
                "foram preservados para que você possa tentar novamente."
            )
        return (
            "A abertura da cena não pôde ser concluída agora; nenhuma proposta parcial "
            "foi gravada, e você mantém a liberdade de tentar novamente quando o "
            "narrador estiver disponível."
        )
    payload = next(
        iter(_fact_payloads(fact_records, "mechanics.resolution")), None
    )
    if payload is None or not isinstance(payload.get("is_success"), bool):
        has_declaration = any(
            (
                fact.get("fact_type")
                if isinstance(fact, Mapping)
                else getattr(fact, "fact_type", None)
            )
            == "action.declaration"
            for fact in fact_records
        )
        if has_declaration:
            return (
                "A ação foi registrada, mas nenhum resultado, efeito adicional, "
                "detalhe observável, entidade ou mudança no mundo foi estabelecido "
                "canonicamente para esta campanha durante o turno presente."
            )
        return None
    if str(payload.get("skill")) == "Investigation":
        if payload["is_success"]:
            return (
                "A investigação é bem-sucedida, mas nenhum achado específico foi "
                "estabelecido pelos fatos disponíveis; a cena permanece sem novos "
                "detalhes canônicos confirmados ao fim deste turno."
            )
        return (
            "A investigação termina sem revelar nada conclusivo; nenhum novo "
            "detalhe do alvo é confirmado, e o estado canônico da cena permanece "
            "inalterado ao fim deste turno."
        )
    if payload["is_success"]:
        return (
            "A tentativa foi bem-sucedida, mas nenhum efeito adicional, detalhe "
            "observável, entidade ou mudança no mundo foi estabelecido canonicamente "
            "para a campanha presente até este momento."
        )
    return (
        "A tentativa falhou e nada conclusivo foi revelado; nenhum efeito adicional, "
        "detalhe observável, entidade ou mudança no mundo foi estabelecido "
        "canonicamente para a campanha até este momento."
    )


def _narrative_validation_error(
    exc: NarrativeContractError,
    *,
    evidence: InvocationEvidence,
    target: LLMTarget,
    partial_output: bool,
) -> NormalizedError:
    return NormalizedError(
        category=ErrorCategory.MALFORMED_RESPONSE,
        code=exc.code,
        phase=OperationPhase.STRUCTURE_VALIDATION,
        invocation_id=evidence.provenance.invocation_id,
        target=target,
        safe_message=(
            "A resposta do Narrador não cumpriu o contrato narrativo do produto."
        ),
        evidence=evidence,
        partial_output=partial_output,
        retryable=False,
    )


@dataclass(frozen=True, slots=True)
class TurnExecutionResult:
    status: str
    operation_id: str
    turn_id: str
    turn_number: int
    partial_narrative: str = ""
    state_event: StateUpdateEvent | None = None
    narrative: NarrativeRecord | None = None
    evidence: InvocationEvidence | None = None
    error: NormalizedError | dict[str, Any] | None = None
    invocations: tuple[InvocationRecord, ...] = ()
    resolution_receipt: dict[str, Any] | None = None
    scene_resolution_receipt: SceneBeatResolution | None = None
    narrative_mode: str | None = None
    narration_pause: NarrationPauseProjection | None = None


def _status_override(context: dict) -> str | None:
    status = context.get("player_sheet", {}).get("status", {})
    override = None
    if int(status.get("current_hunger", 0)) >= 5:
        override = "FRENZY_CHECK"
    health = status.get("health_tracker", {})
    if int(health.get("aggravated", 0)) >= int(health.get("size", 7)):
        override = "TORPOR"
    return override


def _scene_record_id(operation_id: str, record_type: str, index: int = 0) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"storyteller:{operation_id}:scene-director:{record_type}:{index}",
        )
    )


def _scene_beat_from_draft(
    draft: Any, *, operation_id: str
) -> SceneBeatResolution | None:
    records = tuple(
        fact
        for fact in draft.facts
        if fact.fact_type == "world.scene.beat_resolution"
    )
    if not records:
        return None
    if len(records) != 1:
        raise ValueError("turn draft must contain at most one scene beat")
    value = SceneBeatResolution.model_validate(records[0].value)
    if (
        value.session_id != draft.session_id
        or value.operation_id != operation_id
        or value.turn_id != draft.turn_id
        or value.base_revision != draft.base_revision
    ):
        raise ValueError("scene beat does not match its turn draft")
    return value


def _protected_storyteller_context(context_packet: Any) -> tuple[str, ...]:
    if context_packet is None:
        return ()
    protected: list[str] = []
    for selected in getattr(context_packet, "selected", ()):
        item = getattr(selected, "item", None)
        if item is None or getattr(item, "visibility", None) is not Visibility.STORYTELLER:
            continue
        tags = set(getattr(item, "tags", ()))
        if tags & {"catalog", "lore", "relationships", "system_log_projection"}:
            continue
        content = getattr(item, "content", None)
        if isinstance(content, str) and content.strip():
            protected.append(content.strip())
    return tuple(dict.fromkeys(protected))


def _scene_player_aliases(context: Mapping[str, Any]) -> tuple[str, ...]:
    sheet = context.get("player_sheet")
    if not isinstance(sheet, Mapping):
        return ()
    nested = sheet.get("player_sheet")
    if isinstance(nested, Mapping):
        sheet = nested
    aliases: list[str] = []
    for key in ("nome", "name"):
        value = sheet.get(key)
        if isinstance(value, str) and value.strip():
            aliases.append(value.strip())
    return tuple(dict.fromkeys(aliases))


def _scene_npc_aliases(
    context: Mapping[str, Any], proposal: SceneContinuationProposal
) -> tuple[str, ...]:
    scene = scene_from_context(context)
    values = (
        *(scene.npcs_present if scene is not None else ()),
        *proposal.npcs_present,
    )
    return tuple(dict.fromkeys(value for value in values if value.strip()))


def _admit_scene_continuation(
    draft: Any,
    proposal: SceneContinuationProposal,
    *,
    operation_id: str,
    turn_number: int,
    invocation_id: str,
    context: dict[str, Any],
    protected_secrets: Iterable[str] = (),
    scene_beat: SceneBeatResolution | None = None,
) -> tuple[Any, CanonicalEvent, tuple[CanonicalEvent, ...]]:
    """Convert one validated LLM proposal into product-owned canonical records."""

    previous_scene = scene_from_context(context)
    validate_scene_continuation(
        proposal,
        facts=draft.facts,
        current_scene=previous_scene,
        player_input=draft.player_input,
        protected_secrets=protected_secrets,
        player_aliases=_scene_player_aliases(context),
        npc_aliases=_scene_npc_aliases(context, proposal),
        scene_beat=scene_beat,
    )
    next_scene = project_scene(
        proposal,
        previous=previous_scene,
        turn_number=turn_number,
    )
    occurred_at = draft.created_at
    proposal_source = RecordReference(
        record_id=invocation_id,
        record_type="llm_invocation",
        relation="proposed_by",
    )
    policy_source = RecordReference(
        record_id="scene_director_admission.v1",
        record_type="admission_policy",
        relation="validated_by",
    )
    scene_fact = CanonicalFact(
        fact_id=_scene_record_id(operation_id, "scene-projection"),
        fact_type="world.scene",
        predicate="current_scene_after_admitted_beat",
        value=next_scene.model_dump(mode="json"),
        occurred_at=occurred_at,
        visibility=Visibility.PLAYER,
        importance=0.9,
        tags=("world", "scene", "projection", "admitted_fiction"),
        source_refs=(proposal_source, policy_source),
    )
    admitted_facts = tuple(
        CanonicalFact(
            fact_id=_scene_record_id(operation_id, "scene-fact", index),
            fact_type=f"world.scene.{item.kind.value}",
            predicate=f"admitted_{item.kind.value}",
            value={"summary": item.summary, "pending": item.pending},
            occurred_at=occurred_at,
            visibility=item.visibility,
            importance=item.importance,
            tags=(
                "world",
                "scene",
                "admitted_fiction",
                item.kind.value,
                *(('pending',) if item.pending else ()),
            ),
            source_refs=(proposal_source, policy_source),
        )
        for index, item in enumerate(proposal.new_facts)
    )
    previous_thread_keys = {
        scene_thread_key(value)
        for value in (previous_scene.open_threads if previous_scene is not None else ())
    }
    opened_threads = tuple(
        value
        for value in next_scene.open_threads
        if scene_thread_key(value) not in previous_thread_keys
    )
    resolved_thread_keys = {scene_thread_key(value) for value in proposal.resolved_threads}
    resolved_threads = tuple(
        value
        for value in merge_scene_threads(
            previous_scene.open_threads if previous_scene is not None else (), ()
        )
        if scene_thread_key(value) in resolved_thread_keys
    )
    thread_facts = tuple(
        CanonicalFact(
            fact_id=_scene_record_id(operation_id, "scene-thread-opened", index),
            fact_type="world.scene.thread_opened",
            predicate="narrative_thread_opened",
            value={"summary": summary, "pending": True},
            occurred_at=occurred_at,
            visibility=Visibility.PLAYER,
            importance=0.7,
            tags=("world", "scene", "thread", "opened", "pending"),
            source_refs=(proposal_source, policy_source),
        )
        for index, summary in enumerate(opened_threads)
    ) + tuple(
        CanonicalFact(
            fact_id=_scene_record_id(operation_id, "scene-thread-resolved", index),
            fact_type="world.scene.thread_resolved",
            predicate="narrative_thread_resolved",
            value={"summary": summary, "pending": False},
            occurred_at=occurred_at,
            visibility=Visibility.PLAYER,
            importance=0.7,
            tags=("world", "scene", "thread", "resolved"),
            source_refs=(proposal_source, policy_source),
        )
        for index, summary in enumerate(resolved_threads)
    )
    player_facts = tuple(
        fact
        for fact in (*admitted_facts, *thread_facts)
        if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
    )
    secret_facts = tuple(
        fact for fact in admitted_facts if fact.visibility is Visibility.STORYTELLER
    )
    actors = draft.events[0].actors if draft.events else ()
    place = EntityReference(
        entity_id=_scene_record_id(operation_id, "place"),
        entity_type="place",
        label=next_scene.location,
    )
    next_sequence = max((event.sequence for event in draft.events), default=-1) + 1
    visible_event = CanonicalEvent(
        event_id=_scene_record_id(operation_id, "scene-event"),
        session_id=draft.session_id,
        turn_id=draft.turn_id,
        sequence=next_sequence,
        event_type="scene_established" if previous_scene is None else "scene_advanced",
        occurred_at=occurred_at,
        summary=proposal.scene_summary,
        fact_ids=(scene_fact.fact_id, *(fact.fact_id for fact in player_facts)),
        tags=("turn", "scene", "admitted_fiction"),
        actors=actors,
        place=place,
        importance=0.9,
        visibility=Visibility.PLAYER,
        pending=bool(next_scene.open_threads),
        references=(proposal_source, policy_source),
    )
    added_events: list[CanonicalEvent] = [visible_event]
    if secret_facts:
        added_events.append(
            CanonicalEvent(
                event_id=_scene_record_id(operation_id, "secret-scene-event"),
                session_id=draft.session_id,
                turn_id=draft.turn_id,
                sequence=next_sequence + 1,
                event_type="storyteller_scene_thread_updated",
                occurred_at=occurred_at,
                summary="O Storyteller atualizou uma pendência reservada da cena.",
                fact_ids=tuple(fact.fact_id for fact in secret_facts),
                tags=("turn", "scene", "storyteller", "admitted_fiction"),
                actors=actors,
                place=place,
                importance=max(fact.importance for fact in secret_facts),
                visibility=Visibility.STORYTELLER,
                pending=any(bool(fact.value.get("pending")) for fact in secret_facts),
                references=(proposal_source, policy_source),
            )
        )

    next_scene_payload = next_scene.model_dump(mode="json")
    draft_type = type(draft)
    augmented = draft_type.model_validate(
        {
            **draft.model_dump(mode="json"),
            "facts": (*draft.facts, scene_fact, *admitted_facts, *thread_facts),
            "events": (*draft.events, *added_events),
            "state_changes": (
                *draft.state_changes,
                StateChange(path=("scene",), value=next_scene_payload),
            ),
        }
    )
    context["scene"] = next_scene_payload
    return augmented, visible_event, tuple(added_events)


def _safe_diagnostic(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if isinstance(value, (str, int, float, bool, dict, list, tuple)) or value is None:
        return value
    return {"category": "application", "code": type(value).__name__}


def _scene_validation_diagnostic(exc: SceneProposalError) -> dict[str, Any] | None:
    """Copy only closed structural evidence into the local attempt audit."""
    evidence = exc.evidence
    if type(evidence) is not dict or type(exc.code) is not str:
        return None

    def count(value: Any, maximum: int) -> bool:
        return type(value) is int and 0 <= value <= maximum

    if exc.code == "scene_npc_roster_changed_without_event":
        keys = {
            "previous_count", "proposed_count", "added_count", "removed_count",
            "fact_kind_counts", "has_change_fact",
        }
        kinds = {"observation", "clue", "npc_action", "complication", "transition", "hook"}
        if set(evidence) != keys or not all(
            count(evidence[key], 8)
            for key in ("previous_count", "proposed_count", "added_count", "removed_count")
        ):
            return None
        fact_counts = evidence["fact_kind_counts"]
        if (
            type(fact_counts) is not dict or set(fact_counts) != kinds
            or not all(count(value, 4) for value in fact_counts.values())
            or sum(fact_counts.values()) > 4
            or type(evidence["has_change_fact"]) is not bool
        ):
            return None
        safe = {**evidence, "fact_kind_counts": dict(fact_counts)}
    elif exc.code == "scene_secret_disclosed":
        keys = {
            "field", "field_index", "source", "comparison",
            "shared_token_count", "token_denominator", "shared_concept_count",
        }
        domains = {
            "field": {
                "narrative", "location", "scene_summary", "npcs_present",
                "open_threads", "resolved_threads", "player_prompt", "new_facts",
            },
            "source": {"in_proposal", "protected_context"},
            "comparison": {
                "normalized_substring", "shared_tokens",
                "shared_token_ratio", "shared_concepts",
            },
        }
        if set(evidence) != keys or any(
            type(evidence[key]) is not str or evidence[key] not in values
            for key, values in domains.items()
        ) or not count(evidence["field_index"], 23):
            return None
        for key, maximum in (
            ("shared_token_count", 1600), ("token_denominator", 1600),
            ("shared_concept_count", 7),
        ):
            if evidence[key] is not None and not count(evidence[key], maximum):
                return None
        safe = dict(evidence)
    elif exc.code == "scene_player_agency_violation":
        fields = {"narrative", "scene_summary", "player_prompt", "new_facts"}
        action_concepts = {
            "choice", "combat", "conceal", "consume", "inspect", "interact",
            "move", "social", "take", "wait", "wake",
        }
        action_rules = {
            "undeclared_player_action", "undeclared_player_contact",
            "undeclared_player_instrument_action",
            "undeclared_player_barrier_attempt", "undeclared_player_barrier_open",
            "undeclared_player_barrier_push", "undeclared_player_temporal_search",
            "undeclared_player_nominal_open_attempt",
            "presupposed_player_barrier_open",
        }
        field = evidence.get("field")
        rule = evidence.get("rule")
        if type(field) is not str or field not in fields or type(rule) is not str:
            return None
        if rule == "assigned_internal_state":
            if set(evidence) != {"field", "rule"}:
                return None
            safe = {"field": field, "rule": rule}
        elif rule == "unestablished_opening_history":
            concepts = evidence.get("history_concepts")
            if (
                set(evidence) != {"field", "rule", "history_concepts"}
                or type(concepts) is not list or not 1 <= len(concepts) <= 2
                or any(type(item) is not str or item not in {"wake", "memory_loss"}
                       for item in concepts)
            ):
                return None
            safe = {"field": field, "rule": rule, "history_concepts": list(concepts)}
        elif rule in action_rules:
            allowed_keys = {"field", "rule", "unauthorized_concepts"}
            subject_class = None
            if "subject" in evidence or "clause_index" in evidence:
                allowed_keys |= {"subject", "clause_index"}
                subject = evidence.get("subject")
                clause_index = evidence.get("clause_index")
                if type(subject) is not str or not count(clause_index, 63):
                    return None
                subject_class = (
                    subject if subject in {"player_alias", "ambiguous_pronoun"}
                    else "explicit_player_reference"
                )
            concepts = evidence.get("unauthorized_concepts")
            if (
                set(evidence) != allowed_keys
                or type(concepts) is not list or not 1 <= len(concepts) <= 12
                or any(type(item) is not str or item not in action_concepts
                       for item in concepts)
            ):
                return None
            safe = {
                "field": field, "rule": rule,
                "unauthorized_concepts": list(concepts),
            }
            if subject_class is not None:
                safe.update({"subject_class": subject_class, "clause_index": clause_index})
        else:
            return None
    else:
        return None
    return {
        "protocol": "scene-validation-diagnostic-v1",
        "code": exc.code,
        "evidence": safe,
    }


def build_invocation_audit(
    records: list[InvocationRecord] | tuple[InvocationRecord, ...],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Keep provenance and measurements per call; never invent aggregates."""

    if not records:
        return None, None
    provenance_rows: list[dict[str, Any]] = []
    usage_rows: list[dict[str, Any]] = []
    for record in records:
        evidence = record.evidence
        identity = {
            "invocation_id": evidence.provenance.invocation_id,
            "operation": record.operation,
            "status": record.status.value,
        }
        provenance_rows.append(
            {
                **identity,
                "provenance": evidence.provenance.model_dump(mode="json"),
                "error": (
                    record.error.model_dump(mode="json")
                    if record.error is not None
                    else None
                ),
            }
        )
        usage_rows.append(
            {
                **identity,
                "tokens": evidence.usage.model_dump(mode="json"),
                "cost": evidence.cost.model_dump(mode="json"),
            }
        )
    return {"invocations": provenance_rows}, {"invocations": usage_rows}


async def _await_under_shield(awaitable: Awaitable[Any]) -> Any:
    """Let a terminal audit finish even while the owning request is cancelled."""

    with CancelScope(shield=True):
        return await awaitable


async def _result_for_existing_attempt(
    attempt: Any,
    *,
    store: SQLitePersistence,
    session_id: str,
    operation_id: str,
    fallback_turn_id: str,
    fallback_turn_number: int,
) -> TurnExecutionResult | None:
    """Short-circuit terminal retries before any additional model invocation."""

    if not attempt.idempotent:
        return None
    if attempt.status == "pending":
        return TurnExecutionResult(
            status="pending",
            operation_id=operation_id,
            turn_id=fallback_turn_id,
            turn_number=fallback_turn_number,
            error={
                "category": "idempotency",
                "code": "operation_in_progress",
                "safe_message": "This operation is already in progress.",
            },
        )
    if attempt.status == "completed":
        stored = await _await_under_shield(
            store.load_turn_by_operation(session_id, operation_id)
        )
        if stored is None:
            raise RuntimeError("completed attempt has no canonical turn")
        stored_context = stored.get("context") or {}
        validation_metadata = (
            stored_context.get("narrative_validation")
            if isinstance(stored_context, Mapping)
            else None
        )
        narrative_mode = (
            str(validation_metadata.get("mode"))
            if isinstance(validation_metadata, Mapping)
            and validation_metadata.get("mode")
            else "llm"
        )
        return TurnExecutionResult(
            status="completed",
            operation_id=operation_id,
            turn_id=stored["turn_id"],
            turn_number=int(stored["turn_number"]),
            state_event=StateUpdateEvent.model_validate(stored["state"]),
            narrative=NarrativeRecord.model_validate(stored["narrative"]),
            resolution_receipt=build_resolution_receipt(
                stored.get("facts") or (),
                turn_id=stored["turn_id"],
                narrative_mode=narrative_mode,
            ),
            scene_resolution_receipt=(
                SceneBeatResolution.model_validate(stored_context["scene_resolution"])
                if isinstance(stored_context, Mapping)
                and isinstance(stored_context.get("scene_resolution"), Mapping)
                else None
            ),
            narrative_mode=narrative_mode,
        )
    return TurnExecutionResult(
        status=str(attempt.status),
        operation_id=operation_id,
        turn_id=fallback_turn_id,
        turn_number=fallback_turn_number,
        error={
            "category": "idempotency",
            "code": "operation_already_terminal",
            "safe_message": "This operation already has a terminal attempt.",
        },
    )


def _validate_preclaimed_attempt(
    attempt: AttemptResult,
    *,
    session_id: str,
    operation_id: str,
    attempt_id: str,
) -> None:
    if (
        attempt.session_id != session_id
        or attempt.operation_id != operation_id
        or attempt.attempt_id != attempt_id
    ):
        raise ValueError("preclaimed attempt does not match the prepared turn")


async def execute_prepared_turn(
    prepared: TurnPipelineResult,
    *,
    session_id: str,
    operation_id: str,
    user_input: str,
    chronicle_name: str,
    store: SQLitePersistence,
    gateway: LLMGateway,
    target: LLMTarget,
    cancellation: CancellationToken,
    on_chunk: ChunkCallback,
    preclaimed_attempt: AttemptResult | None = None,
    resumes_operation_id: str | None = None,
    resume_capsule_id: str | None = None,
) -> TurnExecutionResult:
    """Stream provisionally, validate derivations, then commit one transaction."""

    draft = prepared.draft
    if prepared.kind != "action" or draft is None:
        raise ValueError("execute_prepared_turn requires an action TurnDraft")
    if draft.session_id != session_id:
        raise ValueError("prepared turn belongs to a different session")

    scene_beat = _scene_beat_from_draft(
        draft, operation_id=resumes_operation_id or operation_id,
    )

    turn_number = draft.base_revision + 1
    chunks: list[str] = []
    invocation_records = list(prepared.llm_invocations)
    resume_audit = {
        **(
            {"resumes_operation_id": resumes_operation_id}
            if resumes_operation_id is not None else {}
        ),
        **(
            {"capsule_id": resume_capsule_id}
            if resume_capsule_id is not None else {}
        ),
    }

    async def audit_task_cancellation(partial_narrative: str) -> None:
        provenance_audit, usage_audit = build_invocation_audit(invocation_records)
        await _await_under_shield(
            store.record_failed_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                status="cancelled",
                user_input=user_input,
                partial_narrative="",
                error={
                    "category": "cancelled",
                    "code": "request_task_cancelled",
                    "safe_message": "Client request ended before canonical turn commit.",
                },
                provenance=provenance_audit,
                usage=usage_audit,
                metadata={
                    **resume_audit,
                    "draft_id": draft.draft_id,
                    "discarded_output_sha256": (
                        hashlib.sha256(partial_narrative.encode("utf-8")).hexdigest()
                        if partial_narrative
                        else None
                    ),
                    "discarded_output_chars": len(partial_narrative),
                },
                chronicle_name=chronicle_name,
            )
        )

    if preclaimed_attempt is not None:
        _validate_preclaimed_attempt(
            preclaimed_attempt,
            session_id=session_id,
            operation_id=operation_id,
            attempt_id=draft.attempt_id,
        )
        attempt_result = preclaimed_attempt
    else:
        start_task = asyncio.create_task(
            store.start_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                user_input=user_input,
                metadata={**resume_audit, "draft_id": draft.draft_id},
                chronicle_name=chronicle_name,
            )
        )
        try:
            attempt_result = await asyncio.shield(start_task)
        except asyncio.CancelledError as exc:
            cancellation.cancel("request task cancelled while starting attempt")
            try:
                await _await_under_shield(start_task)
                await audit_task_cancellation("")
            except Exception as audit_exc:
                exc.add_note(f"Cancellation audit failed: {type(audit_exc).__name__}")
            raise

    existing_result = await _result_for_existing_attempt(
        attempt_result,
        store=store,
        session_id=session_id,
        operation_id=operation_id,
        fallback_turn_id=draft.turn_id,
        fallback_turn_number=turn_number,
    )
    if existing_result is not None:
        return existing_result

    terminal = None
    stream_protocol_error: NormalizedError | None = None
    stream_protocol_violation = False
    stream_protocol_evidence: InvocationEvidence | None = None
    expected_sequence = 0
    callback_error: Exception | None = None
    try:
        # AnyIO uses level cancellation for disconnected requests.  Shield the
        # provider consumer long enough for the linked token to produce one
        # normalized terminal event and auditable invocation evidence.
        with CancelScope(shield=True):
            async for event in run_narrator_events(
                user_input,
                prepared.system_log,
                player_sheet=prepared.updated_context,
                gateway=gateway,
                target=target,
                cancellation=cancellation,
            ):
                if stream_protocol_violation:
                    # Invalid deltas have no evidence by contract.  Drain the
                    # adapter until its required terminal event so the failed
                    # invocation remains attributable, but never publish or
                    # persist content emitted after the first violation.
                    if event.is_terminal and terminal is None:
                        terminal = event
                        stream_protocol_evidence = event.evidence
                    continue
                if event.sequence != expected_sequence or terminal is not None:
                    stream_protocol_violation = True
                    stream_protocol_evidence = (
                        terminal.evidence if terminal is not None else event.evidence
                    )
                    if event.is_terminal and terminal is None:
                        terminal = event
                    continue
                expected_sequence += 1
                if event.kind is StreamEventKind.DELTA:
                    assert event.delta is not None
                    chunks.append(event.delta)
                    continue
                terminal = event
    except asyncio.CancelledError as exc:
        cancellation.cancel("request task cancelled during narrative stream")
        try:
            await audit_task_cancellation("".join(chunks))
        except Exception as audit_exc:
            exc.add_note(f"Cancellation audit failed: {type(audit_exc).__name__}")
        raise
    except Exception as exc:
        callback_error = callback_error or exc
        if terminal is not None and terminal.evidence is not None:
            stream_protocol_error = NormalizedError(
                category=ErrorCategory.MALFORMED_RESPONSE,
                code="stream_raised_after_terminal",
                phase=OperationPhase.STREAM,
                invocation_id=terminal.evidence.provenance.invocation_id,
                target=target,
                safe_message="LLM stream raised after emitting a terminal event.",
                evidence=terminal.evidence,
                partial_output=bool(chunks),
                retryable=False,
            )

    partial = "".join(chunks)
    if stream_protocol_violation and stream_protocol_error is None:
        evidence = stream_protocol_evidence or (
            terminal.evidence if terminal is not None else None
        )
        if evidence is not None:
            stream_protocol_error = NormalizedError(
                category=ErrorCategory.MALFORMED_RESPONSE,
                code="invalid_stream_event_sequence",
                phase=OperationPhase.STREAM,
                invocation_id=evidence.provenance.invocation_id,
                target=target,
                safe_message="LLM stream violated terminal or sequence invariants.",
                evidence=evidence,
                partial_output=bool(chunks),
                retryable=False,
            )
    if (
        stream_protocol_error is not None
        or terminal is None
        or terminal.kind is not StreamEventKind.COMPLETED
    ):
        if stream_protocol_error is not None:
            invocation_records.append(
                InvocationRecord.failed("H6.direct_scene", stream_protocol_error)
            )
            error = stream_protocol_error
            evidence = stream_protocol_error.evidence
            status = "failed"
        elif terminal is not None and terminal.error is not None:
            invocation_records.append(
                InvocationRecord.failed("H6.direct_scene", terminal.error)
            )
            error: NormalizedError | dict[str, Any] = terminal.error
            evidence = terminal.evidence
            status = {
                StreamEventKind.CANCELLED: "cancelled",
                StreamEventKind.TIMED_OUT: "timeout",
            }.get(terminal.kind, "failed")
        else:
            error = {
                "category": "application",
                "code": "narrative_stream_interrupted",
                "safe_message": "Narrative generation ended without a valid terminal event.",
            }
            evidence = None
            status = "cancelled" if cancellation.is_cancelled else "failed"

        provenance_audit, usage_audit = build_invocation_audit(invocation_records)

        await _await_under_shield(
            store.record_failed_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                status=status,
                user_input=user_input,
                partial_narrative="",
                error=_safe_diagnostic(error),
                provenance=provenance_audit,
                usage=usage_audit,
                metadata={
                    **resume_audit,
                    "draft_id": draft.draft_id,
                    "turn_id": draft.turn_id,
                    "transport_error": type(callback_error).__name__
                    if callback_error
                    else None,
                    "discarded_output_sha256": (
                        hashlib.sha256(partial.encode("utf-8")).hexdigest()
                        if partial
                        else None
                    ),
                    "discarded_output_chars": len(partial),
                },
                chronicle_name=chronicle_name,
            )
        )
        pause_projection = None
        eligibility = (
            classify_pause_eligibility(error)
            if isinstance(error, NormalizedError)
            else None
        )
        if isinstance(error, NormalizedError) and eligibility in {
            PauseEligibility.TRANSIENT,
            PauseEligibility.CONFIGURATION_BLOCKED,
        }:
            stored_attempt = await _await_under_shield(
                store.load_attempt_by_operation(session_id, operation_id)
            )
            timing = normalize_gate_timing(error, server_now=utc_now())
            failure_gate = gate_from_error(error, server_now=timing.server_now)
            if failure_gate is None:
                raise RuntimeError("pause-eligible failure did not produce a gate")
            await _await_under_shield(store.upsert_narrator_availability_gate(
                session_id=session_id,
                gate=failure_gate,
            ))
            capsule_id = resume_capsule_id or f"capsule-{uuid5(NAMESPACE_URL, f'storyteller:resume:{session_id}:{operation_id}')}"
            if resume_capsule_id is not None:
                await _await_under_shield(store.transition_narration_resume(
                    session_id=session_id, capsule_id=resume_capsule_id,
                    from_state="direct_resume_trial", to_state="paused",
                    resume_operation_id=operation_id,
                ))
            else:
                capsule = NarrationResumeCapsule(
                    capsule_id=capsule_id,
                    session_id=session_id,
                    source_operation_id=operation_id,
                    source_attempt_id=draft.attempt_id,
                    turn_id=draft.turn_id,
                    requested_turn=turn_number,
                    state_revision=draft.base_state_revision,
                    request_hash=str((stored_attempt or {}).get("request_hash") or hashlib.sha256(
                        f"{session_id}:{operation_id}:{user_input}".encode("utf-8")
                    ).hexdigest()),
                    action=user_input,
                    draft=draft,
                    resolution=build_resolution_receipt(
                        draft.facts, turn_id=draft.turn_id, narrative_mode="pending_narration",
                    ),
                    frozen_context={
                        "system_log": prepared.system_log,
                        "updated_context": prepared.updated_context,
                        "relationships_state": _safe_diagnostic(prepared.relationships_state),
                        "relationships_for_frontend": prepared.relationships_for_frontend,
                        "context_packet": (
                            prepared.context_packet.model_dump(mode="json")
                            if prepared.context_packet is not None else None
                        ),
                    },
                    requested_target=target.model_dump(mode="json"),
                    normalized_reason={
                        **_safe_diagnostic(error),
                        "retry_not_before": (
                            timing.retry_not_before.isoformat()
                            if timing.retry_not_before is not None else None
                        ),
                        "server_now": timing.server_now.isoformat(),
                        "gate_scope": failure_gate.scope.value,
                        "evidence_scope": failure_gate.evidence_scope,
                    },
                )
                await _await_under_shield(store.create_narration_resume_capsule(capsule))
            resolution = build_resolution_receipt(
                draft.facts, turn_id=draft.turn_id, narrative_mode="pending_narration",
            )
            pause_projection = NarrationPauseProjection(
                capsule_id=capsule_id,
                source_operation_id=resumes_operation_id or operation_id,
                expected_state_revision=draft.base_state_revision,
                action_summary=user_input,
                resolution_summary=(
                    resolution.get("display") if isinstance(resolution, dict) else None
                ),
                category=error.category.value,
                safe_message=error.safe_message,
                retryable=bool(error.retryable),
                retry_not_before=timing.retry_not_before,
                server_now=timing.server_now,
                rate_limit_origin=(
                    error.rate_limit.origin.value if error.rate_limit is not None else
                    "unknown" if error.category is ErrorCategory.RATE_LIMITED else None
                ),
                gate_scope=failure_gate.scope.value,
                evidence_scope=failure_gate.evidence_scope,
                allowed_actions=("resume", "abandon"),
            )
        return TurnExecutionResult(
            status=status,
            operation_id=operation_id,
            turn_id=draft.turn_id,
            turn_number=turn_number,
            partial_narrative="",
            evidence=evidence,
            error=error,
            invocations=tuple(invocation_records),
            narration_pause=pause_projection,
        )

    assert terminal is not None and terminal.evidence is not None
    evidence = terminal.evidence
    raw_partial = partial
    admitted_scene_event: CanonicalEvent | None = None
    proposal: SceneContinuationProposal | None = None
    validation_diagnostic: NormalizedError | None = None
    scene_validation_diagnostic: dict[str, Any] | None = None
    invocation_records.append(
        InvocationRecord.completed("H6.direct_scene", evidence)
    )
    narrative_mode = "llm"
    provenance_audit, usage_audit = build_invocation_audit(invocation_records)
    try:
        if cancellation.is_cancelled:
            raise ClientTurnCancelledError(
                "client disconnected after the stream and before canonical commit"
            )
        try:
            proposal = SceneContinuationProposal.model_validate_json(raw_partial)
            protected_secrets = _protected_storyteller_context(
                prepared.context_packet
            )
            validate_scene_continuation(
                proposal,
                facts=draft.facts,
                current_scene=scene_from_context(prepared.updated_context),
                player_input=draft.player_input,
                protected_secrets=protected_secrets,
                player_aliases=_scene_player_aliases(prepared.updated_context),
                npc_aliases=_scene_npc_aliases(
                    prepared.updated_context,
                    proposal,
                ),
                scene_beat=scene_beat,
            )
            partial = validate_narrative_contract(
                proposal.player_text,
                facts=draft.facts,
                scene_proposal=proposal,
                player_input=draft.player_input,
                current_scene=scene_from_context(prepared.updated_context),
            )
            draft, admitted_scene_event, _ = _admit_scene_continuation(
                draft,
                proposal,
                operation_id=operation_id,
                turn_number=turn_number,
                invocation_id=evidence.provenance.invocation_id,
                context=prepared.updated_context,
                protected_secrets=protected_secrets,
                scene_beat=scene_beat,
            )
        except (NarrativeContractError, SceneProposalError, ValueError) as exc:
            if isinstance(exc, SceneProposalError):
                scene_validation_diagnostic = _scene_validation_diagnostic(exc)
            contract_error = (
                exc
                if isinstance(exc, NarrativeContractError)
                else NarrativeContractError(
                    exc.code
                    if isinstance(exc, SceneProposalError)
                    else "scene_proposal_invalid"
                )
            )
            validation_diagnostic = _narrative_validation_error(
                contract_error,
                evidence=evidence,
                target=target,
                partial_output=bool(raw_partial),
            )
            prepared.llm_diagnostics.append(validation_diagnostic)
            raise contract_error from None
        try:
            await on_chunk(partial)
        except Exception as exc:
            callback_error = exc
            cancellation.cancel("client transport disconnected")
            raise ClientTurnCancelledError(
                "client disconnected before validated narrative delivery"
            ) from exc
        narratable_events = tuple(
            event
            for event in draft.events
            if event.visibility.value in {"public", "player"}
        )
        if not narratable_events:
            raise ValueError("A completed player narrative requires a visible source event")
        narrative = NarrativeRecord(
            narrative_id=f"narrative-{operation_id}",
            session_id=session_id,
            turn_id=draft.turn_id,
            text=partial,
            source_event_ids=tuple(event.event_id for event in narratable_events),
            invocation_id=(
                evidence.provenance.invocation_id
                if narrative_mode == "llm"
                else None
            ),
        )
        memory_event = admitted_scene_event or narratable_events[0]
        candidate = derive_memory_candidate(
            memory_event,
            narrative,
            candidate_id=f"memory-candidate-{operation_id}",
            summary=(proposal.scene_summary if proposal is not None else None),
            proposed_by=(
                CandidateProposer.LLM
                if proposal is not None
                else CandidateProposer.DETERMINISTIC
            ),
        )
        candidate = validate_memory_candidate(
            candidate,
            events=draft.events,
            narratives=(narrative,),
            facts=draft.facts,
            semantic_grounding_confirmed=proposal is not None,
        )
        memory = promote_memory_candidate(
            candidate,
            memory_id=f"episodic-memory-{operation_id}",
        )

        state_event = sync_event_from_context(
            session_id,
            prepared.updated_context,
            status_override=_status_override(prepared.updated_context),
            turn_number=turn_number,
            state_revision=draft.base_state_revision,
        )
        state_event.relationships = prepared.relationships_for_frontend
        relationships = (
            prepared.relationships_state.model_dump(mode="json")
            if prepared.relationships_state is not None
            else {}
        )
        context_payload = {
            "packet": (
                prepared.context_packet.model_dump(mode="json")
                if prepared.context_packet is not None
                else {}
            ),
            "llm_diagnostics": [
                _safe_diagnostic(item) for item in prepared.llm_diagnostics
            ],
            "narrative_validation": {
                "mode": narrative_mode,
                "rejected_code": (
                    validation_diagnostic.code
                    if validation_diagnostic is not None
                    else None
                ),
                "rejected_output_sha256": (
                    hashlib.sha256(raw_partial.encode("utf-8")).hexdigest()
                    if validation_diagnostic is not None
                    else None
                ),
                "rejected_output_chars": (
                    len(raw_partial) if validation_diagnostic is not None else 0
                ),
            },
        }
        if proposal is not None:
            context_payload["scene_direction"] = {
                "outcome": proposal.outcome,
                "location": proposal.location,
                "open_threads": list(proposal.open_threads),
                "resolved_threads": list(proposal.resolved_threads),
                "player_prompt": proposal.player_prompt,
                "admitted_fact_count": len(proposal.new_facts),
                "policy": "scene_director_admission.v1",
            }
        resolution_receipt = build_resolution_receipt(
            draft.facts,
            turn_id=draft.turn_id,
            narrative_mode=narrative_mode,
        )
        if resolution_receipt is not None:
            context_payload["resolution_receipt"] = resolution_receipt
        if scene_beat is not None:
            context_payload["scene_resolution"] = scene_beat.model_dump(mode="json")
        if cancellation.is_cancelled:
            raise ClientTurnCancelledError(
                "client disconnected before canonical turn commit"
            )
        await store.commit_turn(
            session_id=session_id,
            operation_id=operation_id,
            turn_id=draft.turn_id,
            attempt_id=draft.attempt_id,
            turn_number=turn_number,
            base_revision=draft.base_revision,
            base_state_revision=draft.base_state_revision,
            state=state_event.model_dump(mode="json"),
            narrative=narrative,
            facts=draft.facts,
            events=draft.events,
            memory_candidates=(candidate,),
            episodic_memories=(memory,),
            relationships=relationships,
            context=context_payload,
            provenance=provenance_audit,
            usage=usage_audit,
            user_input=user_input,
            chronicle_name=chronicle_name,
        )
        state_event.state_revision = draft.base_state_revision + 1
        if resume_capsule_id is not None:
            await store.transition_narration_resume(
                session_id=session_id, capsule_id=resume_capsule_id,
                from_state="direct_resume_trial", to_state="completed",
                resume_operation_id=operation_id,
            )
        target_payload = target.model_dump(mode="json")
        target_scope_key = hashlib.sha256(
            repr(sorted(target_payload.items())).encode("utf-8")
        ).hexdigest()
        await store.upsert_narrator_availability_gate(
            session_id=session_id,
            gate=NarratorAvailabilityGate(
                gate_id=f"gate-{target_scope_key[:24]}",
                state=NarratorGateState.AVAILABLE,
                scope=NarratorGateScope.EXACT_TARGET,
                scope_key=target_scope_key,
                target=target_payload,
                observed_at=utc_now(),
                evidence_scope="exact_target",
                timing_source="completed_call",
                timing_confidence="observed",
            ),
        )
    except asyncio.CancelledError as exc:
        cancellation.cancel("request task cancelled before canonical commit")
        try:
            await audit_task_cancellation(partial)
        except Exception as audit_exc:
            exc.add_note(f"Cancellation audit failed: {type(audit_exc).__name__}")
        raise
    except Exception as exc:
        cancelled = isinstance(exc, ClientTurnCancelledError)
        invalid_narrative = isinstance(exc, NarrativeContractError)
        error = (
            {
                "category": "cancelled",
                "code": "client_turn_cancelled",
                "safe_message": "Client disconnected before canonical turn commit.",
            }
            if cancelled
            else _narrative_validation_error(
                exc,
                evidence=evidence,
                target=target,
                partial_output=bool(raw_partial),
            )
            if invalid_narrative
            else {
                "category": "validation_or_persistence",
                "code": type(exc).__name__,
                "safe_message": "Turn validation or transactional commit failed.",
            }
        )
        status = "cancelled" if cancelled else "failed"
        await _await_under_shield(
            store.record_failed_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                status=status,
                user_input=user_input,
                partial_narrative="",
                error=_safe_diagnostic(error),
                provenance=provenance_audit,
                usage=usage_audit,
                metadata={
                    **resume_audit,
                    "draft_id": draft.draft_id,
                    "turn_id": draft.turn_id,
                    "rejected_output_sha256": (
                        hashlib.sha256(raw_partial.encode("utf-8")).hexdigest()
                        if invalid_narrative
                        else None
                    ),
                    **(
                        {"validation_diagnostic": scene_validation_diagnostic}
                        if scene_validation_diagnostic is not None else {}
                    ),
                },
                chronicle_name=chronicle_name,
            )
        )
        return TurnExecutionResult(
            status=status,
            operation_id=operation_id,
            turn_id=draft.turn_id,
            turn_number=turn_number,
            # Rejected provider output is audit-only.  Returning it here would
            # let a transport layer accidentally expose the same text that was
            # intentionally excluded from canonical narrative and memory.
            partial_narrative="",
            evidence=evidence,
            error=error,
            invocations=tuple(invocation_records),
        )

    return TurnExecutionResult(
        status="completed",
        operation_id=operation_id,
        turn_id=draft.turn_id,
        turn_number=turn_number,
        state_event=state_event,
        narrative=narrative,
        evidence=evidence,
        invocations=tuple(invocation_records),
        resolution_receipt=resolution_receipt,
        scene_resolution_receipt=scene_beat,
        narrative_mode=narrative_mode,
    )


async def execute_prepared_lore_turn(
    prepared: TurnPipelineResult,
    *,
    session_id: str,
    operation_id: str,
    user_input: str,
    chronicle_name: str,
    store: SQLitePersistence,
    cancellation: CancellationToken | None = None,
    preclaimed_attempt: AttemptResult | None = None,
) -> TurnExecutionResult:
    """Commit a prebuilt lore or deterministic response as derived narrative."""

    draft = prepared.draft
    if prepared.kind not in {"lore", "direct"} or draft is None or len(draft.events) != 1:
        raise ValueError(
            "execute_prepared_lore_turn requires one lore or direct response event"
        )
    response_kind = prepared.kind
    turn_number = draft.base_revision + 1
    invocation_records = list(prepared.llm_invocations)
    cancellation = cancellation or CancellationToken()
    provenance_audit, usage_audit = build_invocation_audit(invocation_records)

    async def audit_task_cancellation() -> None:
        await _await_under_shield(
            store.record_failed_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                status="cancelled",
                user_input=user_input,
                error={
                    "category": "cancelled",
                    "code": "request_task_cancelled",
                    "safe_message": "Client request ended before response commit.",
                },
                provenance=provenance_audit,
                usage=usage_audit,
                metadata={
                    "draft_id": draft.draft_id,
                    "turn_id": draft.turn_id,
                    "kind": response_kind,
                },
                chronicle_name=chronicle_name,
            )
        )

    if preclaimed_attempt is not None:
        _validate_preclaimed_attempt(
            preclaimed_attempt,
            session_id=session_id,
            operation_id=operation_id,
            attempt_id=draft.attempt_id,
        )
        attempt_result = preclaimed_attempt
    else:
        start_task = asyncio.create_task(
            store.start_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                user_input=user_input,
                metadata={
                    "draft_id": draft.draft_id,
                    "turn_id": draft.turn_id,
                    "kind": response_kind,
                },
                chronicle_name=chronicle_name,
            )
        )
        try:
            attempt_result = await asyncio.shield(start_task)
        except asyncio.CancelledError as exc:
            cancellation.cancel("request task cancelled while starting response attempt")
            try:
                await _await_under_shield(start_task)
                await audit_task_cancellation()
            except Exception as audit_exc:
                exc.add_note(f"Cancellation audit failed: {type(audit_exc).__name__}")
            raise

    existing_result = await _result_for_existing_attempt(
        attempt_result,
        store=store,
        session_id=session_id,
        operation_id=operation_id,
        fallback_turn_id=draft.turn_id,
        fallback_turn_number=turn_number,
    )
    if existing_result is not None:
        return existing_result

    response_prefix = (
        "[DIRECT_RESPONSE] " if response_kind == "direct" else "[LORE_RESPONSE] "
    )
    text = prepared.system_log.removeprefix(response_prefix).strip()
    narrative_invocation_id = next(
        (
            record.evidence.provenance.invocation_id
            for record in reversed(invocation_records)
            if record.operation == "h4.answer_lore_query" and record.error is None
        ),
        None,
    )
    try:
        if cancellation.is_cancelled:
            raise ClientTurnCancelledError("client disconnected before response commit")
        narrative = NarrativeRecord(
            narrative_id=f"narrative-{operation_id}",
            session_id=session_id,
            turn_id=draft.turn_id,
            text=text,
            source_event_ids=(draft.events[0].event_id,),
            invocation_id=narrative_invocation_id,
        )
        candidate = derive_memory_candidate(
            draft.events[0],
            narrative,
            candidate_id=f"memory-candidate-{operation_id}",
            summary=(text if response_kind == "direct" else None),
        )
        candidate = validate_memory_candidate(
            candidate,
            events=draft.events,
            narratives=(narrative,),
            facts=draft.facts,
        )
        memory = promote_memory_candidate(
            candidate,
            memory_id=f"episodic-memory-{operation_id}",
        )
        state_event = sync_event_from_context(
            session_id,
            prepared.updated_context,
            status_override=_status_override(prepared.updated_context),
            turn_number=turn_number,
            state_revision=draft.base_state_revision,
        )
        state_event.relationships = prepared.relationships_for_frontend
        relationships = (
            prepared.relationships_state.model_dump(mode="json")
            if prepared.relationships_state is not None
            else {}
        )
        if cancellation.is_cancelled:
            raise ClientTurnCancelledError("client disconnected before response commit")
        await store.commit_turn(
            session_id=session_id,
            operation_id=operation_id,
            turn_id=draft.turn_id,
            attempt_id=draft.attempt_id,
            turn_number=turn_number,
            base_revision=draft.base_revision,
            base_state_revision=draft.base_state_revision,
            state=state_event.model_dump(mode="json"),
            narrative=narrative,
            facts=draft.facts,
            events=draft.events,
            memory_candidates=(candidate,),
            episodic_memories=(memory,),
            relationships=relationships,
            context={
                "packet": (
                    prepared.context_packet.model_dump(mode="json")
                    if prepared.context_packet is not None
                    else {}
                ),
                "llm_diagnostics": [
                    _safe_diagnostic(item) for item in prepared.llm_diagnostics
                ],
            },
            provenance=provenance_audit,
            usage=usage_audit,
            user_input=user_input,
            chronicle_name=chronicle_name,
        )
        state_event.state_revision = draft.base_state_revision + 1
    except asyncio.CancelledError as exc:
        cancellation.cancel("request task cancelled before response commit")
        try:
            await audit_task_cancellation()
        except Exception as audit_exc:
            exc.add_note(f"Cancellation audit failed: {type(audit_exc).__name__}")
        raise
    except Exception as exc:
        cancelled = isinstance(exc, ClientTurnCancelledError)
        error = {
            "category": "cancelled" if cancelled else "validation_or_persistence",
            "code": type(exc).__name__,
            "safe_message": (
                "Response was cancelled before commit."
                if cancelled
                else "Response validation or commit failed."
            ),
        }
        await _await_under_shield(
            store.record_failed_attempt(
                session_id=session_id,
                operation_id=operation_id,
                attempt_id=draft.attempt_id,
                requested_turn=turn_number,
                status="cancelled" if cancelled else "failed",
                user_input=user_input,
                error=error,
                provenance=provenance_audit,
                usage=usage_audit,
                metadata={"draft_id": draft.draft_id, "kind": response_kind},
                chronicle_name=chronicle_name,
            )
        )
        return TurnExecutionResult(
            status="cancelled" if cancelled else "failed",
            operation_id=operation_id,
            turn_id=draft.turn_id,
            turn_number=turn_number,
            error=error,
            invocations=tuple(invocation_records),
        )

    return TurnExecutionResult(
        status="completed",
        operation_id=operation_id,
        turn_id=draft.turn_id,
        turn_number=turn_number,
        state_event=state_event,
        narrative=narrative,
        invocations=tuple(invocation_records),
    )
