import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping
from uuid import NAMESPACE_URL, uuid4, uuid5

from .rules_service import (
    DeterministicTurnInputs,
    PlayerSheetModel,
    ResolutionResult,
    V5ActionPayload,
    V5ActionTarget,
    V5Attribute,
    V5Skill,
    V5WeaponCategory,
    calculate_resolution,
)
from .economy_service import rouse_check, feed
from .combat_service import calculate_damage
from .discipline_service import (
    apply_power_modifiers,
    get_power_action_roll_policy,
    get_power_cost,
)
from .metagame_service import apply_willpower_reroll
from .physiology_service import get_blood_surge_bonus, get_healing_amount
from .parser_service import extract_intent
from .scene_service import (
    SceneState,
    ensure_scene_context,
    scene_fact_text,
)
from .context_service import (
    ContextItem,
    ContextLayer,
    ContextQuery,
    LayeredContext,
    assemble_context,
)
from .core.config import settings
from .llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CancellationToken,
    CapabilityRequirement,
    ErrorCategory,
    GenerationParameters,
    InvocationRecord,
    LLMGateway,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    StreamEvent,
    StreamEventBuilder,
    StreamEventKind,
    StructuredGenerationRequest,
    StructuredGenerationResult,
    utc_now,
)
from .scene_director_service import SceneContinuationProposal
from .llm.runtime import get_llm_runtime
from .turn_models import (
    CanonicalEvent,
    CanonicalFact,
    Consolidation,
    ConsolidationScope,
    EntityReference,
    EpisodicMemory,
    RecordReference,
    StateChange,
    TurnDraft,
    Visibility,
)
from .prompt_service import load_versioned_prompt

STORYTELLER_SYSTEM_PROMPT = load_versioned_prompt(
    "H6_vtm_narrator",
    fallback="Narre somente a partir dos fatos fornecidos e preserve a agência do jogador.",
)

class SystemLogBuilder:
    def __init__(self):
        self.action = ""
        self.result = ""
        self.combat_log = ""
        self.hunger = 0
        self.power_log = ""
        self.economy_log = ""
        self.willpower_reroll = "Não"
        self.lore_context = ""
        self.memory_context = ""
        self.relationship_context = ""
        self.scene_fact = ""
        self.response_instruction = ""
        self.narrative_options: tuple[str, ...] = ()
        
    def build(self, *, expected_outcome: str) -> str:
        expected_outcome = expected_outcome.strip().casefold()
        if expected_outcome not in {"success", "failure", "unresolved"}:
            raise ValueError("expected_outcome must be success, failure or unresolved")

        facts = [
            value.strip()
            for value in (
                self.scene_fact,
                self.result,
                self.combat_log,
                self.power_log,
                self.economy_log,
            )
            if value.strip()
        ]
        if self.hunger >= 5:
            facts.append("A fome está crítica.")
        elif self.hunger >= 3:
            facts.append("A fome está alta.")
        if self.willpower_reroll == "Sim":
            facts.append("A rerrolagem de Força de Vontade foi aplicada.")

        packet: dict[str, Any] = {
            "schema": "storyteller.turn.v2",
            "player_action": {
                "source": "player",
                "trusted": False,
                "text": self.action.strip(),
            },
            "expected_outcome": {
                "source": "deterministic_engine",
                "trusted": True,
                "value": expected_outcome,
                "output_field": "o",
                "instruction": (
                    "Copie value exatamente para o campo o; não reinterprete."
                ),
            },
            "canonical_facts": {
                "source": "deterministic_engine",
                "trusted": True,
                "items": facts,
            },
        }
        if self.response_instruction:
            packet["objective"] = {
                "source": "application",
                "trusted": True,
                "text": self.response_instruction.strip(),
            }
        if self.narrative_options:
            packet["authorized_narrative"] = {
                "source": "application",
                "trusted": True,
                "instruction": "Reproduza exatamente uma opção, sem alteração.",
                "options": list(self.narrative_options),
            }
        context: dict[str, Any] = {}
        if self.lore_context:
            context["lore"] = {
                "source": "versioned_catalog",
                "trusted": True,
                "text": self.lore_context.strip(),
            }
        if self.memory_context:
            context["memory"] = {
                "source": "local_retrieval",
                "trusted": False,
                "text": self.memory_context.strip(),
            }
        if self.relationship_context:
            context["relationships"] = {
                "source": "deterministic_state",
                "trusted": True,
                "text": self.relationship_context.strip(),
            }
        if context:
            packet["context"] = context
        return "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n" + json.dumps(
            packet,
            ensure_ascii=False,
            separators=(",", ":"),
        )


@dataclass(slots=True)
class TurnPipelineResult:
    """Side-effect-free deterministic result awaiting narrative and commit."""

    kind: str
    system_log: str
    updated_context: dict
    code: str | None = None
    message: str | None = None
    relationships_state: Any | None = None
    relationships_for_frontend: list[dict] | None = None
    draft: TurnDraft | None = None
    context_packet: LayeredContext | None = None
    llm_diagnostics: list[Any] = field(default_factory=list)
    llm_invocations: list[InvocationRecord] = field(default_factory=list)

    @property
    def is_error(self) -> bool:
        return self.kind == "error"

    @property
    def is_clarification(self) -> bool:
        return self.kind == "clarification"

    @property
    def is_lore_query(self) -> bool:
        return self.kind == "lore"

    @property
    def is_direct_response(self) -> bool:
        return self.kind == "direct"


def _stable_id(operation_id: str, record_type: str, index: int = 0) -> str:
    return str(uuid5(NAMESPACE_URL, f"storyteller:{operation_id}:{record_type}:{index}"))


def _resolve_llm(
    gateway: LLMGateway | None, target: LLMTarget | None
) -> tuple[LLMGateway, LLMTarget]:
    if gateway is not None and target is not None:
        return gateway, target
    if gateway is not None or target is not None:
        raise ValueError("gateway and target must be supplied together")
    runtime = get_llm_runtime()
    return runtime.gateway, runtime.target


def _context_prompt(packet: LayeredContext) -> str:
    if not packet.selected:
        return ""
    known: list[str] = []
    confidential: list[str] = []
    seen: set[str] = set()
    for entry in packet.selected:
        item = entry.item
        # Only content explicitly tagged as already projected may be omitted.
        # Other canonical facts (notably state.character) remain available to
        # H6 under the normal visibility and token-budget rules.
        if "system_log_projection" in item.tags:
            continue
        content = item.content.strip()
        if not content or content in seen:
            continue
        seen.add(content)
        target = (
            confidential
            if item.visibility in {Visibility.STORYTELLER, Visibility.SYSTEM}
            else known
        )
        target.append(content)

    parts: list[str] = []
    if known:
        parts.append("CONHECIDO\n" + "\n".join(f"- {value}" for value in known))
    if confidential:
        parts.append(
            "CONFIDENCIAL\n"
            + "\n".join(f"- {value}" for value in confidential)
        )
    return "\n\n".join(parts)


def _scene_npc_ids(scene: SceneState | None) -> tuple[str, ...]:
    if scene is None or not scene.npcs_present:
        return ()
    from .npc_service import find_npc_ids

    return find_npc_ids(" ".join(scene.npcs_present))


def _scene_query_catalog_candidates(
    scene: SceneState | None,
    player_sheet: PlayerSheetModel | None,
) -> tuple[Any, ...]:
    """Produce independent catalog candidates for a scene query before selection."""

    from .catalog_models import (
        CatalogContextCandidate,
        CatalogDomain,
        CatalogRelevanceSignals,
    )

    candidates: list[CatalogContextCandidate] = []
    if player_sheet is not None:
        from .clan_service import get_clan_narrative

        clan_data = get_clan_narrative(player_sheet.clan)
        if clan_data is not None:
            entry_id = player_sheet.clan
            candidates.append(
                CatalogContextCandidate(
                    domain=CatalogDomain.CLAN,
                    entry_id=entry_id,
                    minimal_text=(
                        f"Clã ({entry_id}): {clan_data.lore_summary} "
                        f"Perdição: {clan_data.bane_description} "
                        f"Compulsão: {clan_data.compulsion_description} "
                        f"{clan_data.narrator_enforcement}"
                    ),
                    visibility=Visibility.PLAYER,
                    signals=CatalogRelevanceSignals(text_relevant=True),
                    importance=0.6,
                    source_refs=(
                        RecordReference(
                            record_id=f"catalog:clan/{entry_id}",
                            record_type="catalog_entry",
                            relation="derived_from",
                        ),
                    ),
                )
            )

    if scene is not None:
        from .npc_service import get_all_npcs

        npcs = get_all_npcs()
        for npc_id in _scene_npc_ids(scene):
            npc = npcs.get(npc_id)
            if npc is None:
                continue
            candidates.append(
                CatalogContextCandidate(
                    domain=CatalogDomain.NPC_ARCHETYPE,
                    entry_id=npc_id,
                    minimal_text=(
                        f"NPC ({npc_id}): {npc.narrative_data.social_standing} "
                        f"Tática: {npc.narrative_data.combat_tactics}"
                    ),
                    visibility=Visibility.PLAYER,
                    signals=CatalogRelevanceSignals(active_in_scene=True),
                    importance=npc.engine_data.threat_level / 5,
                    source_refs=(
                        RecordReference(
                            record_id=f"catalog:npc_archetype/{npc_id}",
                            record_type="catalog_entry",
                            relation="derived_from",
                        ),
                    ),
                )
            )

    return tuple(candidates)


def _narrative_resolution_summary(resolution: ResolutionResult) -> str:
    parts = [
        "A ação teve sucesso." if resolution.is_success else "A ação falhou."
    ]
    if resolution.messy_critical:
        parts.append("O resultado foi um Messy Critical.")
    if resolution.bestial_failure:
        parts.append("O resultado foi uma Bestial Failure.")
    return " ".join(parts)


def _safe_scene_label(scene: Any | None) -> str | None:
    """Return a short canonical place label that cannot alter the H6 contract."""

    raw_location = getattr(scene, "location", None)
    if not isinstance(raw_location, str):
        return None
    location = " ".join(raw_location.split())
    if len(location) > 48 or not re.fullmatch(
        r"[^\W_]+(?:[ \-’'][^\W_]+){0,3}", location, flags=re.UNICODE
    ):
        return None
    return location


def _authorized_narrative_candidates(
    *,
    operation_id: str,
    resolution: ResolutionResult | None,
    skill: str | None,
    scene: Any | None,
) -> tuple[str, ...]:
    """Build closed, player-safe prose choices from deterministic turn facts.

    H6 may select wording, but it never receives authority to add a claim.  The
    stable rotation prevents one template from dominating repeated turns while
    keeping replay and idempotency deterministic.
    """

    location = _safe_scene_label(scene)
    scene_lead = f"Em {location}, a" if location else "A"
    if resolution is None:
        candidates = (
            (
                "A ação foi registrada, mas nenhum resultado, efeito adicional, "
                "detalhe observável, entidade ou mudança no mundo foi estabelecido "
                "canonicamente para esta campanha durante o turno presente."
            ),
            (
                f"{scene_lead} intenção do personagem foi registrada sem teste "
                "mecânico; nenhum novo detalhe, efeito, encontro ou mudança de estado "
                "foi estabelecido canonicamente ao fim deste turno."
            ),
            (
                "O turno registra somente a ação declarada pelo jogador; os fatos "
                "disponíveis não autorizam consequência, descoberta, entidade nova "
                "ou alteração adicional no estado canônico da campanha."
            ),
        )
    elif skill == "Investigation" and resolution.is_success:
        candidates = (
            (
                "A investigação é bem-sucedida, mas nenhum achado específico foi "
                "estabelecido pelos fatos disponíveis; a cena permanece sem novos "
                "detalhes canônicos confirmados ao fim deste turno."
            ),
            (
                f"{scene_lead} busca alcança sucesso sem estabelecer um achado "
                "específico; nenhum novo detalhe da cena é confirmado, e o estado "
                "canônico permanece inalterado ao término deste turno."
            ),
            (
                "A análise é concluída com sucesso, embora os fatos disponíveis não "
                "autorizem uma descoberta específica; a cena conserva somente os "
                "detalhes canônicos já confirmados anteriormente."
            ),
        )
    elif skill == "Investigation":
        candidates = (
            (
                "A investigação termina sem revelar nada conclusivo; nenhum novo "
                "detalhe do alvo é confirmado, e o estado canônico da cena permanece "
                "inalterado ao fim deste turno."
            ),
            (
                f"{scene_lead} busca termina sem revelar nada conclusivo; nenhum "
                "indício novo é confirmado, nenhuma entidade adicional é estabelecida, "
                "e o estado canônico da cena permanece inalterado."
            ),
            (
                "Apesar do exame realizado, nada conclusivo foi estabelecido; os "
                "fatos disponíveis não confirmam novos detalhes, consequências ou "
                "mudanças, e a cena conserva seu estado canônico."
            ),
        )
    elif resolution.is_success:
        candidates = (
            (
                "A tentativa foi bem-sucedida, mas nenhum efeito adicional, detalhe "
                "observável, entidade ou mudança no mundo foi estabelecido canonicamente "
                "para a campanha presente até este momento."
            ),
            (
                f"{scene_lead} ação alcança sucesso sem produzir consequência "
                "adicional registrada; nenhum novo detalhe, encontro ou estado do "
                "mundo é confirmado canonicamente na campanha ao fim deste turno."
            ),
            (
                "O resultado confirma o sucesso da tentativa, enquanto os fatos "
                "disponíveis preservam a cena sem novas entidades, descobertas, "
                "consequências ou mudanças canônicas adicionais relevantes ao turno."
            ),
        )
    else:
        candidates = (
            (
                "A tentativa falhou e nada conclusivo foi revelado; nenhum efeito adicional, "
                "detalhe observável, entidade ou mudança no mundo foi estabelecido "
                "canonicamente para a campanha até este momento."
            ),
            (
                f"{scene_lead} tentativa falha sem revelar nada conclusivo; nenhum "
                "novo detalhe, encontro, efeito ou estado do mundo é confirmado "
                "canonicamente na campanha presente ao fim deste turno."
            ),
            (
                "O resultado confirma a falha e nada conclusivo é estabelecido; "
                "a cena permanece sem novas entidades, descobertas, consequências ou "
                "mudanças canônicas confirmadas durante este turno."
            ),
        )

    offset = int(uuid5(NAMESPACE_URL, f"storyteller:{operation_id}:narrative").hex, 16)
    offset %= len(candidates)
    return (*candidates[offset:], *candidates[:offset])


def _narrator_fact_content(
    fact: CanonicalFact,
    *,
    active_relationship: str = "",
) -> str:
    value = fact.value if isinstance(fact.value, Mapping) else {}
    if fact.fact_type == "mechanics.resolution":
        try:
            return _narrative_resolution_summary(
                ResolutionResult.model_validate(value)
            )
        except Exception:
            return "O resultado mecânico canônico está disponível."
    if fact.fact_type == "action.declaration":
        return "A ação foi declarada sem teste mecânico."
    if fact.fact_type == "state.character":
        health = value.get("health_tracker") or {}
        willpower = value.get("willpower_tracker") or {}
        return (
            f"Estado após a ação: fome {value.get('current_hunger', 0)}; "
            f"humanidade {value.get('humanity', 7)}; "
            "saúde "
            f"{health.get('superficial', 0)} superficial/"
            f"{health.get('aggravated', 0)} agravada; vontade "
            f"{willpower.get('superficial', 0)} superficial/"
            f"{willpower.get('aggravated', 0)} agravada."
        )
    if fact.fact_type == "world.relationships":
        return active_relationship or "O estado relacional permaneceu sem foco narrativo."
    return fact.predicate.replace("_", " ")


def _active_relationship_context(state: Any, active_npc_id: str | None) -> str:
    if not active_npc_id:
        return ""
    relationship_id = {
        "sheriff": "xerife",
        "prince": "principe",
    }.get(active_npc_id, active_npc_id)
    relationship = getattr(state, "relationships", {}).get(relationship_id)
    if relationship is None:
        return ""
    disposition = {
        "hostile": "hostil",
        "unfavorable": "desfavorável",
        "neutral": "neutra",
        "favorable": "favorável",
        "allied": "aliada",
    }.get(relationship.disposition, relationship.disposition)
    latest = relationship.history[-1] if relationship.history else "sem histórico"
    label = relationship_id.replace("_", " ").title()
    return f"{label}: relação {disposition}; {latest}."


def _normalized_intent_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char))
        .replace("_", " ")
        .split()
    )


_ATTRIBUTE_ALIASES = {
    "forca": V5Attribute.Strength,
    "strength": V5Attribute.Strength,
    "destreza": V5Attribute.Dexterity,
    "dexterity": V5Attribute.Dexterity,
    "vigor": V5Attribute.Stamina,
    "stamina": V5Attribute.Stamina,
    "carisma": V5Attribute.Charisma,
    "charisma": V5Attribute.Charisma,
    "manipulacao": V5Attribute.Manipulation,
    "manipulation": V5Attribute.Manipulation,
    "autocontrole": V5Attribute.Composure,
    "composure": V5Attribute.Composure,
    "inteligencia": V5Attribute.Intelligence,
    "intelligence": V5Attribute.Intelligence,
    "raciocinio": V5Attribute.Wits,
    "wits": V5Attribute.Wits,
    "determinacao": V5Attribute.Resolve,
    "resolve": V5Attribute.Resolve,
}

_SKILL_ALIASES = {
    "atletismo": V5Skill.ATHLETICS,
    "athletics": V5Skill.ATHLETICS,
    "briga": V5Skill.BRAWL,
    "brawl": V5Skill.BRAWL,
    "oficio": V5Skill.CRAFT,
    "craft": V5Skill.CRAFT,
    "conducao": V5Skill.DRIVE,
    "drive": V5Skill.DRIVE,
    "armas de fogo": V5Skill.FIREARMS,
    "firearms": V5Skill.FIREARMS,
    "ladrao": V5Skill.LARCENY,
    "larceny": V5Skill.LARCENY,
    "armas brancas": V5Skill.MELEE,
    "melee": V5Skill.MELEE,
    "furtividade": V5Skill.STEALTH,
    "stealth": V5Skill.STEALTH,
    "sobrevivencia": V5Skill.SURVIVAL,
    "survival": V5Skill.SURVIVAL,
    "trato com animais": V5Skill.ANIMAL_KEN,
    "animal ken": V5Skill.ANIMAL_KEN,
    "etiqueta": V5Skill.ETIQUETTE,
    "etiquette": V5Skill.ETIQUETTE,
    "intuicao": V5Skill.INSIGHT,
    "insight": V5Skill.INSIGHT,
    "intimidacao": V5Skill.INTIMIDATION,
    "intimidation": V5Skill.INTIMIDATION,
    "lideranca": V5Skill.LEADERSHIP,
    "leadership": V5Skill.LEADERSHIP,
    "performance": V5Skill.PERFORMANCE,
    "persuasao": V5Skill.PERSUASION,
    "persuasion": V5Skill.PERSUASION,
    "manha": V5Skill.STREETWISE,
    "streetwise": V5Skill.STREETWISE,
    "subterfugio": V5Skill.SUBTERFUGE,
    "subterfuge": V5Skill.SUBTERFUGE,
    "academicos": V5Skill.ACADEMICS,
    "academics": V5Skill.ACADEMICS,
    "percepcao": V5Skill.AWARENESS,
    "awareness": V5Skill.AWARENESS,
    "financas": V5Skill.FINANCE,
    "finance": V5Skill.FINANCE,
    "investigacao": V5Skill.INVESTIGATION,
    "investigation": V5Skill.INVESTIGATION,
    "medicina": V5Skill.MEDICINE,
    "medicine": V5Skill.MEDICINE,
    "ocultismo": V5Skill.OCCULT,
    "occult": V5Skill.OCCULT,
    "politica": V5Skill.POLITICS,
    "politics": V5Skill.POLITICS,
    "ciencia": V5Skill.SCIENCE,
    "science": V5Skill.SCIENCE,
    "tecnologia": V5Skill.TECHNOLOGY,
    "technology": V5Skill.TECHNOLOGY,
}

_DEFAULT_ATTRIBUTE_BY_SKILL = {
    V5Skill.ATHLETICS: V5Attribute.Dexterity,
    V5Skill.BRAWL: V5Attribute.Strength,
    V5Skill.CRAFT: V5Attribute.Dexterity,
    V5Skill.DRIVE: V5Attribute.Dexterity,
    V5Skill.FIREARMS: V5Attribute.Dexterity,
    V5Skill.LARCENY: V5Attribute.Dexterity,
    V5Skill.MELEE: V5Attribute.Strength,
    V5Skill.STEALTH: V5Attribute.Dexterity,
    V5Skill.SURVIVAL: V5Attribute.Wits,
    V5Skill.ANIMAL_KEN: V5Attribute.Charisma,
    V5Skill.ETIQUETTE: V5Attribute.Charisma,
    V5Skill.INSIGHT: V5Attribute.Wits,
    V5Skill.INTIMIDATION: V5Attribute.Charisma,
    V5Skill.LEADERSHIP: V5Attribute.Charisma,
    V5Skill.PERFORMANCE: V5Attribute.Charisma,
    V5Skill.AWARENESS: V5Attribute.Wits,
    V5Skill.INVESTIGATION: V5Attribute.Wits,
    V5Skill.PERSUASION: V5Attribute.Charisma,
    V5Skill.STREETWISE: V5Attribute.Wits,
    V5Skill.SUBTERFUGE: V5Attribute.Manipulation,
    V5Skill.ACADEMICS: V5Attribute.Intelligence,
    V5Skill.FINANCE: V5Attribute.Intelligence,
    V5Skill.MEDICINE: V5Attribute.Intelligence,
    V5Skill.OCCULT: V5Attribute.Intelligence,
    V5Skill.POLITICS: V5Attribute.Intelligence,
    V5Skill.SCIENCE: V5Attribute.Intelligence,
    V5Skill.TECHNOLOGY: V5Attribute.Intelligence,
}

def _power_aliases() -> dict[str, tuple[str, ...]]:
    from .catalog_models import CatalogDomain
    from .catalog_service import get_catalog_registry

    return {
        record.identity.entry_id: tuple(
            alias.replace("_", " ")
            for alias in (record.identity.entry_id, *record.identity.aliases)
        )
        for record in get_catalog_registry().entries(CatalogDomain.DISCIPLINE_POWER)
    }


def _explicit_power_from_intent(
    user_input: str, *, is_aggressive: bool
) -> str | None:
    """Resolve an explicit power command before checking player authority.

    Bare power names are narrative mentions. Activation verbs (or ``com`` in an
    explicit attack) turn a known name into a mechanical request. Commands that
    explicitly say ``poder``/``disciplina`` must name exactly one catalogued
    power; this prevents an unknown name from falling through to narration.
    """

    text = _normalized_intent_text(user_input)
    command_prefix = (
        r"(?:^|[.!?;]\s*|\b(?:e|ou|entao|depois)\s+)"
        r"(?:eu\s+)?(?:(?:vou|quero|pretendo)\s+)?"
        r"(?:uso|usar|ativo|ativar)"
    )
    known_mentions: set[str] = set()
    explicit_matches: set[str] = set()

    aliases_by_power = _power_aliases()
    for power_id, aliases in aliases_by_power.items():
        for alias in aliases:
            alias_pattern = re.escape(alias)
            if re.search(rf"\b{alias_pattern}\b", text):
                known_mentions.add(power_id)
            if re.search(
                rf"{command_prefix}(?:\s+(?:o|a))?"
                rf"(?:\s+(?:poder|disciplina))?"
                rf"\s+{alias_pattern}\b",
                text,
            ):
                explicit_matches.add(power_id)
            if is_aggressive and re.search(
                rf"\bcom(?:\s+(?:o|a))?(?:\s+(?:poder|disciplina))?"
                rf"\s+{alias_pattern}\b",
                text,
            ):
                explicit_matches.add(power_id)

    marked_commands = tuple(
        re.finditer(
            command_prefix
            + r"(?:\s+(?:o|a))?\s+(?:poder|disciplina)\b",
            text,
        )
    )
    for command in marked_commands:
        remainder = text[command.end() :].lstrip()
        resolved = {
            power_id
            for power_id, aliases in aliases_by_power.items()
            if any(
                re.match(rf"{re.escape(alias)}\b", remainder)
                for alias in aliases
            )
        }
        if not resolved:
            raise ValueError("explicit power command names an unknown power")
        explicit_matches.update(resolved)

    if len(explicit_matches) > 1 or (
        explicit_matches and len(known_mentions) > 1
    ):
        raise ValueError("explicit power command is ambiguous")
    if explicit_matches:
        return next(iter(explicit_matches))
    return None


def _authorize_power_use(
    requested_power: str,
    deterministic: DeterministicTurnInputs,
    player_sheet: PlayerSheetModel,
) -> str:
    from .catalog_models import CatalogDomain, DisciplinePowerMetadata
    from .catalog_service import get_catalog_registry, normalize_catalog_id

    registry = get_catalog_registry()
    record = registry.require(CatalogDomain.DISCIPLINE_POWER, requested_power)
    power_id = record.identity.entry_id
    metadata = DisciplinePowerMetadata.model_validate(
        record.payload["catalog_metadata"]
    )

    allowed_ids = {
        candidate.identity.entry_id
        for supplied in deterministic.allowed_power_ids
        if (candidate := registry.get(CatalogDomain.DISCIPLINE_POWER, supplied))
        is not None
    }
    owned_power_ids = {
        candidate.identity.entry_id
        for supplied in player_sheet.disciplines
        if (candidate := registry.get(CatalogDomain.DISCIPLINE_POWER, supplied))
        is not None
    }
    family_levels = {
        normalize_catalog_id(supplied): level
        for supplied, level in player_sheet.disciplines.items()
        if registry.get(CatalogDomain.DISCIPLINE_POWER, supplied) is None
    }

    owns_power = power_id in owned_power_ids
    selected_from_family = (
        power_id in allowed_ids
        and metadata.discipline_family_id in family_levels
    )
    if not owns_power and not selected_from_family:
        raise ValueError(
            "explicit power command is not possessed by the player character"
        )
    if metadata.level is not None and not owns_power:
        if family_levels[metadata.discipline_family_id] < metadata.level:
            raise ValueError("explicit power command exceeds the owned discipline level")
    if any(
        family_levels.get(requirement.discipline_family_id, 0) < requirement.level
        for requirement in metadata.amalgam_requirements
    ):
        raise ValueError("explicit power command does not meet amalgam requirements")
    if any(prerequisite not in owned_power_ids for prerequisite in metadata.prerequisite_power_ids):
        raise ValueError("explicit power command does not meet power prerequisites")
    return power_id


def _explicit_test_pool(user_input: str) -> tuple[V5Attribute, V5Skill] | None:
    """Parse only the UI's unambiguous ``teste de X + Y`` command form."""

    text = _normalized_intent_text(user_input)
    for attribute_name, attribute in _ATTRIBUTE_ALIASES.items():
        for skill_name, skill in _SKILL_ALIASES.items():
            if f"teste de {attribute_name} + {skill_name}" in text:
                return attribute, skill
    for skill_name, skill in _SKILL_ALIASES.items():
        if text == f"fazer teste de {skill_name}" or text == f"teste de {skill_name}":
            return _DEFAULT_ATTRIBUTE_BY_SKILL[skill], skill
    return None


def _explicit_test_difficulty(user_input: str) -> int | None:
    """Read difficulty only from the UI's explicit, locally parsed test form."""

    if _explicit_test_pool(user_input) is None:
        return None
    match = re.search(
        r"\bcom dificuldade ([1-7])\b",
        _normalized_intent_text(user_input),
    )
    return int(match.group(1)) if match else None


_WEAPON_ALIASES: dict[V5WeaponCategory, tuple[str, ...]] = {
    V5WeaponCategory.LIGHT_FIREARM: ("pistola", "revolver"),
    V5WeaponCategory.HEAVY_FIREARM: ("rifle", "fuzil", "escopeta"),
    V5WeaponCategory.LIGHT_MELEE: ("faca", "adaga", "canivete", "cassetete"),
    V5WeaponCategory.HEAVY_MELEE: ("espada", "machado", "marreta"),
    V5WeaponCategory.INCENDIARY: ("coquetel molotov", "lanca chamas"),
    V5WeaponCategory.ELECTRICAL: ("arma de choque", "taser"),
    V5WeaponCategory.CHEMICAL: ("arma quimica",),
    V5WeaponCategory.HEAVY_MACHINERY: ("maquina pesada",),
    V5WeaponCategory.HOLY_ARTIFACT: ("artefato sagrado",),
}


def _mentioned_weapon_category(user_input: str) -> V5WeaponCategory | None:
    """Resolve explicit weapon words without guessing inventory or category."""

    text = _normalized_intent_text(user_input)
    matches = {
        category
        for category, aliases in _WEAPON_ALIASES.items()
        if any(
            re.search(
                r"\b(?:com|usando|empunhando|empunho|minha|meu|disparo)\s+"
                r"(?:uma?|o|a)?\s*"
                + re.escape(alias)
                + r"\b",
                text,
            )
            for alias in aliases
        )
    }
    if len(matches) > 1:
        raise ValueError("multiple weapon categories were mentioned")
    if matches:
        return next(iter(matches))
    if re.search(
        r"\b(?:com|usando|empunhando|empunho|minha|meu)\s+"
        r"(?:uma?|o|a)?\s*(?:arma|arma de fogo|arma branca)\b",
        text,
    ):
        raise ValueError("weapon mention is ambiguous; select an authorized category")
    return None


def _local_mechanical_pool(
    user_input: str,
    *,
    flags: Mapping[str, bool],
    weapon: V5WeaponCategory,
    power_used: str | None,
) -> tuple[V5Attribute, V5Skill] | None:
    """Resolve supported action patterns without delegating mechanics to H1."""

    explicit = _explicit_test_pool(user_input)
    if explicit is not None:
        return explicit
    if get_power_action_roll_policy(power_used) == "no_roll":
        return None
    text = _normalized_intent_text(user_input)

    if flags["is_willpower_reroll"]:
        return V5Attribute.Resolve, V5Skill.AWARENESS
    if power_used in {"feral_weapons", "scorpion_touch"}:
        return V5Attribute.Strength, V5Skill.BRAWL
    if flags["is_aggressive"]:
        if weapon in {
            V5WeaponCategory.LIGHT_FIREARM,
            V5WeaponCategory.HEAVY_FIREARM,
        }:
            return V5Attribute.Dexterity, V5Skill.FIREARMS
        if weapon in {V5WeaponCategory.LIGHT_MELEE, V5WeaponCategory.HEAVY_MELEE}:
            return V5Attribute.Strength, V5Skill.MELEE
        return V5Attribute.Strength, V5Skill.BRAWL
    if flags["is_healing"]:
        return V5Attribute.Stamina, V5Skill.MEDICINE
    if flags["is_feeding"] or flags["is_blood_surge"]:
        return V5Attribute.Strength, V5Skill.BRAWL

    patterns = (
        (
            r"\b(investigo|investigar|examino|examinar|vasculho|vasculhar|analiso|analisar|procuro pistas?)\b",
            V5Attribute.Wits,
            V5Skill.INVESTIGATION,
        ),
        (
            r"\b(convenco|persuado|negocio|argumento|seduzo|suborno|subornar)\b",
            V5Attribute.Charisma,
            V5Skill.PERSUASION,
        ),
        (
            r"\b(esgueiro|me escondo|escondo|infiltr\w*|passo despercebido)\b",
            V5Attribute.Dexterity,
            V5Skill.STEALTH,
        ),
        (
            r"\b(observo|vigio|escuto|percebo)\b",
            V5Attribute.Wits,
            V5Skill.AWARENESS,
        ),
        (
            r"\b(forco|arrombo|derrubo|escalo|corro|salto)\b",
            V5Attribute.Strength,
            V5Skill.ATHLETICS,
        ),
    )
    for pattern, attribute, skill in patterns:
        if re.search(pattern, text):
            return attribute, skill
    return None


def _requests_unspecified_roll(user_input: str) -> bool:
    """Recognize a roll request that supplies no action or mechanical pool."""

    text = re.sub(r"[^a-z0-9\s]", "", _normalized_intent_text(user_input))
    attribute_only = re.fullmatch(r"(?:fazer\s+)?teste\s+de\s+(.+)", text)
    if attribute_only and attribute_only.group(1) in _ATTRIBUTE_ALIASES:
        return True
    return bool(
        re.fullmatch(
            r"(?:eu\s+)?(?:quero\s+)?(?:fazer\s+)?(?:uma\s+)?"
            r"(?:rolagem|rolar(?:\s+os)?\s+dados?)",
            text,
        )
        or re.fullmatch(r"(?:por favor\s+)?role(?:\s+os)?\s+dados?", text)
    )


ROLL_POOL_REQUIRED_CODE = "roll_pool_required"
ROLL_POOL_REQUIRED_MESSAGE = (
    "Descreva o que o personagem tenta fazer ou informe atributo e perícia "
    "para a rolagem."
)


def _is_standalone_scene_query(user_input: str) -> bool:
    """Keep deterministic scene lookup narrow so compound actions still run."""

    text = re.sub(r"[^a-z0-9\s]", "", _normalized_intent_text(user_input))
    patterns = (
        r"(?:por favor\s+)?onde (?:eu )?estou",
        r"(?:por favor\s+)?me mostre (?:o )?(?:lugar|local|ambiente|arredores)",
        r"(?:por favor\s+)?(?:descreva|mostre) (?:o )?(?:lugar|local|ambiente|arredores)",
        r"(?:por favor\s+)?o que (?:ha|tem) (?:aqui|ao redor)",
        r"(?:por favor\s+)?olh(?:o|ar) ao redor",
    )
    return any(re.fullmatch(pattern, text) for pattern in patterns)


def _context_supplies_explicit_roll_pool(
    context: Mapping[str, Any] | None,
) -> bool:
    if not context:
        return False
    try:
        deterministic = DeterministicTurnInputs.model_validate(
            context.get("deterministic_mechanics") or {}
        )
    except Exception:
        return False
    return {"attribute", "skill"}.issubset(deterministic.model_fields_set)


def turn_requires_llm_runtime(
    user_input: str,
    context: Mapping[str, Any] | None = None,
) -> bool:
    """Tell the transport whether this input can terminate locally.

    A bare roll request without a trusted pool is a local clarification. Every
    fictional input, including a scene query, retains scene direction so the
    world can answer and continue rather than behave like a static database.
    """

    return not (
        _requests_unspecified_roll(user_input)
        and not _context_supplies_explicit_roll_pool(context)
    )


def _authorized_intent_flags(user_input: str) -> dict[str, bool]:
    """Authorize only explicit first-person/imperative mechanical commands."""

    text = _normalized_intent_text(user_input)

    def begins(*phrases: str) -> bool:
        return any(text == phrase or text.startswith(f"{phrase} ") for phrase in phrases)

    aggressive = begins(
        "ataco",
        "eu ataco",
        "atacar",
        "agrido",
        "eu agrido",
        "golpeio",
        "eu golpeio",
        "disparo",
        "eu disparo",
        "esfaqueio",
        "eu esfaqueio",
        "soco",
        "eu soco",
        "chuto",
        "eu chuto",
        "fazer teste de forca + briga",
    )

    flags = {
        "is_aggressive": aggressive,
        "is_feeding": begins(
            "eu me alimento",
            "me alimento",
            "vou me alimentar",
            "alimentar se",
            "bebo sangue",
            "eu bebo sangue",
            "dreno o sangue",
            "eu dreno o sangue",
            "caco para beber sangue",
        ),
        "is_healing": begins(
            "eu curo",
            "curo meu",
            "curo minha",
            "curar meu",
            "curar minha",
            "curar ferimento",
            "uso mending",
            "ativo mending",
        ),
        "is_blood_surge": begins(
            "surto de sangue",
            "uso surto de sangue",
            "ativo surto de sangue",
            "blood surge",
        )
        or (aggressive and " com surto de sangue" in text),
        "is_willpower_reroll": begins(
            "rerrolar",
            "rerrolo",
            "eu rerrolo",
            "rolar novamente",
            "eu uso forca de vontade para rerrolar",
        ),
    }
    exclusive_modes = sum(
        int(flags[name])
        for name in ("is_feeding", "is_healing", "is_willpower_reroll")
    )
    if exclusive_modes > 1:
        raise ValueError("feeding, healing and willpower reroll are mutually exclusive")
    return flags


def _mechanical_action_from_intent(
    semantic_action: Any,
    deterministic: DeterministicTurnInputs,
    player_sheet: PlayerSheetModel,
    user_input: str,
    diagnostics: list[Any],
) -> V5ActionPayload:
    """Cross the semantic/mechanical boundary without trusting H1 state."""

    flags = _authorized_intent_flags(user_input)
    power_used = _explicit_power_from_intent(
        user_input, is_aggressive=flags["is_aggressive"]
    )
    if power_used is not None:
        power_used = _authorize_power_use(
            power_used, deterministic, player_sheet
        )

    mentioned_weapon = _mentioned_weapon_category(user_input)
    selected_weapon = deterministic.weapon_category
    if mentioned_weapon is not None:
        if mentioned_weapon not in deterministic.allowed_weapon_categories:
            raise ValueError(
                "mentioned weapon is not authorized by deterministic inventory/state"
            )
        if (
            "weapon_category" in deterministic.model_fields_set
            and deterministic.weapon_category is not mentioned_weapon
        ):
            raise ValueError(
                "mentioned weapon conflicts with deterministic weapon selection"
            )
        selected_weapon = mentioned_weapon

    attribute = deterministic.attribute
    skill = deterministic.skill
    local_pool = _local_mechanical_pool(
        user_input,
        flags=flags,
        weapon=selected_weapon,
        power_used=power_used,
    )
    if flags["is_feeding"] and _explicit_test_pool(user_input) is None:
        from .physiology_service import get_supported_predator_hunt_profile

        hunt_profile = get_supported_predator_hunt_profile(player_sheet.predator_type)
        local_pool = (hunt_profile.attribute, hunt_profile.skill)
    if local_pool is not None:
        local_attribute, local_skill = local_pool
        if "attribute" not in deterministic.model_fields_set:
            attribute = local_attribute
        if "skill" not in deterministic.model_fields_set:
            skill = local_skill
    power_roll_policy = get_power_action_roll_policy(power_used)
    if (
        power_used is not None
        and local_pool is None
        and power_roll_policy == "standard_action"
        and "attribute" not in deterministic.model_fields_set
        and "skill" not in deterministic.model_fields_set
    ):
        raise ValueError(
            "selected power has no deterministic mechanical pool implementation"
        )
    requires_roll = bool(
        local_pool is not None
        or "attribute" in deterministic.model_fields_set
        or "skill" in deterministic.model_fields_set
        or (power_used is not None and power_roll_policy == "standard_action")
        or any(flags.values())
    )
    explicit_difficulty = _explicit_test_difficulty(user_input)
    difficulty = deterministic.unopposed_difficulty
    if (
        explicit_difficulty is not None
        and "unopposed_difficulty" not in deterministic.model_fields_set
    ):
        difficulty = explicit_difficulty

    return V5ActionPayload(
        intent=user_input,
        attribute=attribute,
        skill=skill,
        requires_roll=requires_roll,
        power_used=power_used,
        weapon_category=selected_weapon,
        is_aggressive=flags["is_aggressive"],
        is_feeding=flags["is_feeding"],
        is_healing=flags["is_healing"],
        target_killed=deterministic.target_killed,
        is_bane_damage=deterministic.is_bane_damage,
        is_blood_surge=flags["is_blood_surge"],
        is_willpower_reroll=flags["is_willpower_reroll"],
        is_compulsion_active=deterministic.is_compulsion_active,
        is_true_faith_active=deterministic.is_true_faith_active,
        action_target=deterministic.action_target or V5ActionTarget.UNOPPOSED,
        inferred_difficulty=difficulty,
        npc_threat_level=deterministic.opposed_difficulty,
    )


def _find_active_npc(
    user_input: str,
    *,
    cached_npc_id: str | None = None,
) -> tuple[Any | None, str | None]:
    from .npc_service import find_npc_ids, get_supported_npc_model

    mentioned_ids = find_npc_ids(user_input)
    if mentioned_ids:
        npc_key = mentioned_ids[0]
        try:
            return get_supported_npc_model(npc_key), npc_key
        except ValueError:
            return None, None
    if cached_npc_id:
        try:
            return get_supported_npc_model(cached_npc_id), cached_npc_id
        except ValueError:
            return None, None
    return None, None


def _stored_memory_context_item(memory: Mapping[str, Any]) -> ContextItem | None:
    """Restore every scoring field from the validated persisted memory payload."""

    try:
        restored = EpisodicMemory.model_validate(memory.get("payload") or memory)
    except Exception:
        return None
    if {"declared_action", "scene_query"} & set(restored.tags):
        return None
    return ContextItem(
        item_id=restored.memory_id,
        layer=(
            ContextLayer.OPEN_THREADS
            if restored.pending
            else ContextLayer.EPISODIC_MEMORY
        ),
        content=restored.summary,
        visibility=restored.visibility,
        occurred_at=restored.occurred_at,
        importance=restored.importance,
        pending=restored.pending,
        tags=restored.tags,
        actors=restored.actors,
        place=restored.place,
        source_refs=tuple(
            RecordReference(
                record_id=source_id,
                record_type="canonical_event",
                relation="derived_from",
            )
            for source_id in restored.source_event_ids
        ),
    )


def _stored_confidential_scene_fact_item(
    fact_payload: Mapping[str, Any],
) -> ContextItem | None:
    """Restore admitted storyteller-only scene facts without exposing them in state."""

    try:
        fact = CanonicalFact.model_validate(fact_payload)
    except Exception:
        return None
    if (
        fact.visibility is not Visibility.STORYTELLER
        or not fact.fact_type.startswith("world.scene.")
    ):
        return None
    value = fact.value if isinstance(fact.value, Mapping) else {}
    summary = value.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    pending = bool(value.get("pending"))
    return ContextItem(
        item_id=fact.fact_id,
        layer=ContextLayer.OPEN_THREADS if pending else ContextLayer.WORLD_STATE,
        content=" ".join(summary.split()),
        visibility=Visibility.STORYTELLER,
        occurred_at=fact.occurred_at,
        importance=fact.importance,
        pending=pending,
        tags=(*fact.tags, "confidential_scene_fact"),
        source_refs=(
            RecordReference(
                record_id=fact.fact_id,
                record_type="canonical_fact",
                relation="projected_from",
            ),
            *fact.source_refs,
        ),
    )


async def _restore_narrator_context_items(
    session_id: str,
    *,
    query_text: str,
    token_budget: int,
    current_turn: int,
) -> list[ContextItem]:
    """Restore persisted context shared by actions and direct scene queries."""

    from .state_service import get_persistence

    store = get_persistence()
    stored_memories = await store.retrieve_memories(
        session_id,
        query=query_text,
        allowed_visibilities=(
            Visibility.PUBLIC.value,
            Visibility.PLAYER.value,
            Visibility.STORYTELLER.value,
        ),
        limit=50,
        token_budget=token_budget,
    )
    historical_turns = await store.list_latest_turns(
        session_id,
        limit=max(8, current_turn),
    )
    consolidation_rows = await store.list_consolidations(session_id)

    restored_items: list[ContextItem] = []
    for memory in stored_memories:
        memory_item = _stored_memory_context_item(memory)
        if memory_item is not None:
            restored_items.append(memory_item)

    recent_start = max(0, len(historical_turns) - 8)
    confidential_by_id: dict[str, ContextItem] = {}
    for index, stored_turn in enumerate(historical_turns):
        is_recent = index >= recent_start
        for fact_payload in stored_turn.get("facts") or ():
            if not isinstance(fact_payload, Mapping):
                continue
            confidential_item = _stored_confidential_scene_fact_item(fact_payload)
            if confidential_item is None:
                continue
            if is_recent or confidential_item.pending:
                confidential_by_id[confidential_item.item_id] = confidential_item
    restored_items.extend(confidential_by_id.values())

    latest_consolidations: dict[ConsolidationScope, Consolidation] = {}
    for row in consolidation_rows:
        try:
            consolidation = Consolidation.model_validate(row.get("payload") or {})
        except Exception:
            continue
        if consolidation.visibility not in {
            Visibility.PUBLIC,
            Visibility.PLAYER,
            Visibility.STORYTELLER,
        }:
            continue
        previous = latest_consolidations.get(consolidation.scope)
        if previous is None or consolidation.version > previous.version:
            latest_consolidations[consolidation.scope] = consolidation

    for consolidation in latest_consolidations.values():
        restored_items.append(
            ContextItem(
                item_id=consolidation.consolidation_id,
                layer=(
                    ContextLayer.WORLD_STATE
                    if consolidation.scope is ConsolidationScope.SESSION
                    else ContextLayer.EPISODIC_MEMORY
                ),
                content=consolidation.summary,
                visibility=consolidation.visibility,
                occurred_at=consolidation.created_at,
                importance=(
                    0.9
                    if consolidation.scope is ConsolidationScope.SESSION
                    else 0.8
                ),
                tags=(
                    *consolidation.tags,
                    "consolidation",
                    consolidation.scope.value,
                ),
                source_refs=(
                    *(
                        RecordReference(
                            record_id=memory_id,
                            record_type="episodic_memory",
                            relation="consolidates",
                        )
                        for memory_id in consolidation.source_memory_ids
                    ),
                    *(
                        RecordReference(
                            record_id=event_id,
                            record_type="canonical_event",
                            relation="derived_from",
                        )
                        for event_id in consolidation.source_event_ids
                    ),
                ),
            )
        )
    return restored_items


NARRATOR_CONTEXT_BUDGET_CODE = "narrator_context_budget_exceeded"
NARRATOR_CONTEXT_BUDGET_MESSAGE = (
    "O contexto obrigatório da cena excede o orçamento configurado; "
    "o turno não foi executado."
)


class NarratorContextBudgetError(ValueError):
    """Report an intact required context that cannot fit, without its contents."""

    code = NARRATOR_CONTEXT_BUDGET_CODE

    def __init__(self) -> None:
        super().__init__(NARRATOR_CONTEXT_BUDGET_MESSAGE)


async def _assemble_narrator_context(
    *,
    session_id: str,
    operation_id: str,
    user_input: str,
    current_turn: int,
    occurred_at: datetime,
    base_items: list[ContextItem],
    catalog_candidates: tuple[Any, ...] = (),
    relationship_context: str = "",
    query_tags: tuple[str, ...] = (),
    actor_ids: tuple[str, ...] = (),
) -> LayeredContext:
    """Apply one visibility-safe budget policy to every H6 entry path."""

    narrator_context_budget = min(
        settings.context_token_budget,
        settings.narrator_context_token_budget,
    )
    context_items = list(base_items)
    if catalog_candidates:
        from .catalog_selection_service import rank_catalog_context_candidates

        ranked_catalog = rank_catalog_context_candidates(catalog_candidates)
        for selection_priority, candidate in enumerate(ranked_catalog, start=1):
            signal_tags = tuple(
                name
                for name, active in candidate.signals.model_dump().items()
                if active
            )
            context_items.append(
                ContextItem(
                    item_id=(
                        f"catalog:{candidate.domain.value}/{candidate.entry_id}"
                    ),
                    layer=ContextLayer.WORLD_STATE,
                    content=candidate.minimal_text,
                    visibility=candidate.visibility,
                    occurred_at=occurred_at,
                    importance=candidate.importance,
                    required=candidate.required,
                    selection_priority=selection_priority,
                    tags=("lore", "world", "catalog", candidate.domain.value, *signal_tags),
                    source_refs=candidate.source_refs,
                )
            )
    if relationship_context:
        context_items.append(
            ContextItem(
                item_id=_stable_id(operation_id, "context-relationships"),
                layer=ContextLayer.WORLD_STATE,
                content=relationship_context,
                visibility=Visibility.STORYTELLER,
                occurred_at=occurred_at,
                importance=0.7,
                tags=("relationships", "world"),
            )
        )
    context_items.extend(
        await _restore_narrator_context_items(
            session_id,
            query_text=user_input,
            token_budget=narrator_context_budget,
            current_turn=current_turn,
        )
    )
    try:
        return assemble_context(
            context_items,
            ContextQuery(
                query_text=user_input,
                tags=query_tags,
                actor_ids=actor_ids,
                allowed_visibilities=frozenset(
                    {Visibility.PUBLIC, Visibility.PLAYER, Visibility.STORYTELLER}
                ),
                now=occurred_at,
                token_budget=narrator_context_budget,
                chars_per_token=settings.context_chars_per_token,
            ),
        )
    except ValueError as exc:
        if str(exc) == "required canonical context exceeds the configured token budget":
            raise NarratorContextBudgetError() from None
        raise


def _resolve_target_successes(
    action: V5ActionPayload,
    deterministic: DeterministicTurnInputs,
    active_npc: Any | None,
) -> tuple[int, int]:
    """Resolve target from trusted state/catalog and apply deterministic rules."""

    if action.action_target is V5ActionTarget.OPPOSED:
        target = (
            active_npc.engine_data.threat_level
            if active_npc is not None
            else deterministic.opposed_difficulty
        )
    else:
        target = action.inferred_difficulty

    reduction = 0
    if active_npc is not None and action.skill.value in {
        "Persuasion",
        "Subterfuge",
        "Intimidation",
    }:
        reduction = max(0, active_npc.engine_data.corruption_index - 1)
        target = max(1, target - reduction)

    if action.action_target is V5ActionTarget.OPPOSED:
        action.npc_threat_level = target
    else:
        action.inferred_difficulty = target
    return target, reduction

async def run_narrator_events(
    user_input: str,
    system_log: str,
    player_sheet: dict | None = None,
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
) -> AsyncIterator[StreamEvent]:
    """Project a typed H6 result into the existing auditable event protocol."""

    builder = StreamEventBuilder()
    try:
        result = await run_scene_director(
            system_log,
            gateway=gateway,
            target=target,
            cancellation=cancellation,
            deadline_seconds=deadline_seconds,
        )
        assert isinstance(result.value, SceneContinuationProposal)
        # The domain keeps descriptive field names; the LLM wire format uses
        # short aliases so compact local models spend tokens on fiction, not keys.
        yield builder.delta(result.value.model_dump_json(by_alias=True))
        yield builder.complete(result.evidence)
    except LLMInvocationError as exc:
        kind = {
            ErrorCategory.CANCELLED: StreamEventKind.CANCELLED,
            ErrorCategory.TIMEOUT: StreamEventKind.TIMED_OUT,
        }.get(exc.error.category, StreamEventKind.FAILED)
        yield builder.fail(kind, exc.error, partial_output=False)


async def run_scene_director(
    system_log: str,
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
) -> StructuredGenerationResult:
    """Ask H6 for one typed scene continuation through the LLM-001 boundary."""

    gateway, target = _resolve_llm(gateway, target)
    effective_deadline = min(
        float(deadline_seconds or settings.llm_timeout_seconds),
        float(settings.llm_timeout_seconds),
    )
    request = StructuredGenerationRequest(
        operation="H6.direct_scene",
        target=target,
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content=STORYTELLER_SYSTEM_PROMPT),
            LLMMessage(role=MessageRole.USER, content=system_log),
        ),
        deadline=utc_now() + timedelta(seconds=effective_deadline),
        cancellation=cancellation or CancellationToken(),
        parameters=GenerationParameters(
            temperature=settings.llm_scene_director_temperature,
            max_output_tokens=settings.llm_scene_director_max_output_tokens,
        ),
        response_model=SceneContinuationProposal,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )
    return await gateway.generate_structured(request)


async def run_narrator_stream(
    user_input: str,
    system_log: str,
    player_sheet: dict | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    """Compatibility projection that exposes only the validated player prose."""

    payload: list[str] = []
    async for event in run_narrator_events(
        user_input, system_log, player_sheet=player_sheet, **kwargs
    ):
        if event.kind is StreamEventKind.DELTA:
            assert event.delta is not None
            payload.append(event.delta)
        elif event.kind is not StreamEventKind.COMPLETED:
            assert event.error is not None
            raise LLMInvocationError(event.error)
    proposal = SceneContinuationProposal.model_validate_json("".join(payload))
    yield proposal.player_text


async def prepare_turn_pipeline(
    user_input: str,
    session_id: str,
    context: dict,
    turn: int,
    chronicle_name: str,
    *,
    operation_id: str,
    state_revision: int = 0,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    llm_invocations: list[InvocationRecord] | None = None,
    before_rng: Callable[[], Awaitable[None]] | None = None,
) -> TurnPipelineResult:
    diagnostics: list[Any] = []
    invocation_records = llm_invocations if llm_invocations is not None else []
    cancellation = cancellation or CancellationToken()

    if (
        _requests_unspecified_roll(user_input)
        and not _context_supplies_explicit_roll_pool(context)
    ):
        return TurnPipelineResult(
            kind="clarification",
            code=ROLL_POOL_REQUIRED_CODE,
            message=ROLL_POOL_REQUIRED_MESSAGE,
            system_log=f"[AÇÃO INCOMPLETA] {ROLL_POOL_REQUIRED_MESSAGE}",
            updated_context=context,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    scene = ensure_scene_context(context)

    if _is_standalone_scene_query(user_input):
        from .relationship_service import (
            get_relationships_for_frontend,
            load_relationships,
        )

        occurred_at = utc_now()
        turn_id = _stable_id(operation_id, "turn")
        scene_is_known = scene is not None
        scene_value = (
            {"status": "known", **scene.model_dump(mode="json")}
            if scene_is_known
            else {"status": "unknown", "location": None, "npcs_present": []}
        )
        scene_content = (
            scene_fact_text(scene)
            if scene_is_known
            else "Local atual: ainda não estabelecido."
        )
        scene_source = RecordReference(
            record_id="campaign.scene",
            record_type="campaign_state",
            relation="projected_from",
        )
        scene_fact = CanonicalFact(
            fact_id=_stable_id(operation_id, "fact-scene"),
            fact_type="world.scene",
            predicate="current_scene_status",
            value=scene_value,
            occurred_at=occurred_at,
            visibility=Visibility.PLAYER,
            importance=0.9,
            tags=(
                "world",
                "scene",
                "current_location",
                "known" if scene_is_known else "unknown",
            ),
            source_refs=(scene_source,),
        )
        scene_event = CanonicalEvent(
            event_id=_stable_id(operation_id, "event-scene-query"),
            session_id=session_id,
            turn_id=turn_id,
            sequence=0,
            event_type="player_scene_query",
            occurred_at=occurred_at,
            summary=(
                "O estado canônico conhecido da cena foi apresentado ao jogador."
                if scene_is_known
                else "A ausência de uma cena canônica foi apresentada ao jogador."
            ),
            fact_ids=(scene_fact.fact_id,),
            tags=("turn", "scene_query"),
            actors=(
                EntityReference(
                    entity_id=session_id,
                    entity_type="player_character",
                ),
            ),
            importance=0.5,
            visibility=Visibility.PLAYER,
            pending=False,
        )
        scene_item = ContextItem(
            item_id=scene_fact.fact_id,
            layer=ContextLayer.HOT_SCENE,
            content=scene_content,
            visibility=Visibility.PLAYER,
            occurred_at=occurred_at,
            importance=scene_fact.importance,
            required=True,
            tags=(*scene_fact.tags, "system_log_projection"),
            source_refs=scene_fact.source_refs,
        )
        rel_state = await load_relationships(session_id)
        context_items = [scene_item]
        try:
            player_sheet = PlayerSheetModel.model_validate(
                context.get("player_sheet") or {}
            )
        except Exception:
            player_sheet = None
        if player_sheet is not None:
            state_fact = CanonicalFact(
                fact_id=_stable_id(operation_id, "context-character-state"),
                fact_type="state.character",
                predicate="current_character_state",
                value=player_sheet.status.model_dump(mode="json"),
                occurred_at=occurred_at,
                visibility=Visibility.PLAYER,
                importance=0.7,
                tags=("character", "state"),
                source_refs=(
                    RecordReference(
                        record_id="campaign.player_sheet",
                        record_type="campaign_state",
                        relation="projected_from",
                    ),
                ),
            )
            context_items.append(
                ContextItem(
                    item_id=state_fact.fact_id,
                    layer=ContextLayer.CANONICAL_FACTS,
                    content=_narrator_fact_content(state_fact),
                    visibility=state_fact.visibility,
                    occurred_at=state_fact.occurred_at,
                    importance=state_fact.importance,
                    required=True,
                    tags=state_fact.tags,
                    source_refs=state_fact.source_refs,
                )
            )
        relationship_context = "\n".join(
            fragment
            for fragment in (
                _active_relationship_context(rel_state, npc_id)
                for npc_id in _scene_npc_ids(scene)
            )
            if fragment
        )
        context_packet = await _assemble_narrator_context(
            session_id=session_id,
            operation_id=operation_id,
            user_input=user_input,
            current_turn=turn,
            occurred_at=occurred_at,
            base_items=context_items,
            catalog_candidates=_scene_query_catalog_candidates(scene, player_sheet),
            relationship_context=relationship_context,
            actor_ids=(session_id, *_scene_npc_ids(scene)),
        )
        scene_log = SystemLogBuilder()
        scene_log.action = user_input
        scene_log.scene_fact = scene_fact_text(scene)
        scene_log.result = "A consulta da cena não exige teste mecânico."
        scene_log.response_instruction = (
            "Responda concretamente e faça a cena avançar. Se a cena ainda não "
            "existir, estabeleça um local coerente, tensão imediata e gancho; se "
            "existir, preserve sua continuidade e revele novo detalhe compatível."
        )
        scene_log.memory_context = _context_prompt(context_packet)
        return TurnPipelineResult(
            kind="action",
            system_log=scene_log.build(expected_outcome="unresolved"),
            updated_context=context,
            relationships_state=rel_state,
            relationships_for_frontend=get_relationships_for_frontend(rel_state),
            draft=TurnDraft(
                draft_id=_stable_id(operation_id, "draft"),
                session_id=session_id,
                turn_id=turn_id,
                attempt_id=f"attempt-{operation_id}",
                created_at=occurred_at,
                player_input=user_input,
                base_revision=max(0, turn - 1),
                base_state_revision=state_revision,
                facts=(scene_fact,),
                events=(scene_event,),
                context_references=tuple(
                    reference
                    for selected in context_packet.selected
                    for reference in selected.item.source_refs
                ),
            ),
            context_packet=context_packet,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    # --- H0 Controller: Triagem e enriquecimento (E-04) ---
    from .h0_controller_service import triage_input
    h0_result = await triage_input(
        user_input,
        npc_aliases=(scene.npcs_present if scene is not None else ()),
        gateway=gateway,
        target=target,
        cancellation=cancellation,
        diagnostics=diagnostics,
        invocations=invocation_records,
    )
    if cancellation.is_cancelled:
        return TurnPipelineResult(
            kind="error",
            system_log="[CANCELLED] O cliente encerrou a operação durante a triagem.",
            updated_context=context,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    # Se for consulta de lore, roteia para H4 sem pipeline mecânico
    if h0_result.is_lore_query:
        player_sheet_dict = context.get("player_sheet", {})
        try:
            from .rules_service import PlayerSheetModel as PSM
            ps = PSM(**player_sheet_dict)
        except Exception:
            ps = None

        from .h4_lore_expert_service import answer_lore_query
        if ps:
            lore_answer = await answer_lore_query(
                user_input,
                ps,
                gateway=gateway,
                target=target,
                cancellation=cancellation,
                diagnostics=diagnostics,
                invocations=invocation_records,
            )
        else:
            lore_answer = "Conhecimento indisponível no momento."
        if cancellation.is_cancelled:
            return TurnPipelineResult(
                kind="error",
                system_log="[CANCELLED] O cliente encerrou a consulta de lore.",
                updated_context=context,
                llm_diagnostics=diagnostics,
                llm_invocations=invocation_records,
            )

        # Carrega relationships para manter consistência no retorno
        from .relationship_service import load_relationships, get_relationships_for_frontend
        rel_state = await load_relationships(session_id)
        relationships_for_frontend = get_relationships_for_frontend(rel_state)
        occurred_at = utc_now()
        turn_id = _stable_id(operation_id, "turn")
        lore_event = CanonicalEvent(
            event_id=_stable_id(operation_id, "event-lore-query"),
            session_id=session_id,
            turn_id=turn_id,
            sequence=0,
            event_type="player_lore_query",
            occurred_at=occurred_at,
            summary=f"Consulta declarada pelo jogador: {user_input}",
            tags=("turn", "lore_query"),
            importance=0.4,
            visibility=Visibility.PLAYER,
            pending=False,
        )
        lore_draft = TurnDraft(
            draft_id=_stable_id(operation_id, "draft"),
            session_id=session_id,
            turn_id=turn_id,
            attempt_id=f"attempt-{operation_id}",
            created_at=occurred_at,
            player_input=user_input,
            base_revision=max(0, turn - 1),
            base_state_revision=state_revision,
            events=(lore_event,),
        )

        return TurnPipelineResult(
            kind="lore",
            system_log=f"[LORE_RESPONSE] {lore_answer}",
            updated_context=context,
            relationships_state=rel_state,
            relationships_for_frontend=relationships_for_frontend,
            draft=lore_draft,
            context_packet=LayeredContext(),
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    try:
        semantic_action = await extract_intent(
            user_input,
            gateway=gateway,
            target=target,
            cancellation=cancellation,
            diagnostics=diagnostics,
            invocations=invocation_records,
        )
        if cancellation.is_cancelled:
            return TurnPipelineResult(
                kind="error",
                system_log="[CANCELLED] O cliente encerrou a interpretação da ação.",
                updated_context=context,
                llm_diagnostics=diagnostics,
                llm_invocations=invocation_records,
            )
    except Exception as exc:
        diagnostics.append(
            {
                "category": "application",
                "code": type(exc).__name__,
                "safe_message": "H1 failed before producing a validated action.",
            }
        )
        return TurnPipelineResult(
            kind="error",
            system_log="[ERROR Parser H1] A intenção não pôde ser validada.",
            updated_context=context,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    player_sheet_dict = context.get("player_sheet", {})
    try:
        player_sheet = PlayerSheetModel(**player_sheet_dict)
    except Exception as exc:
        diagnostics.append(
            {
                "category": "application",
                "code": type(exc).__name__,
                "safe_message": "Player sheet validation failed.",
            }
        )
        return TurnPipelineResult(
            kind="error",
            system_log="[ERROR Player Sheet Validation] A ficha não pôde ser validada.",
            updated_context=context,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    try:
        deterministic_inputs = DeterministicTurnInputs.model_validate(
            context.get("deterministic_mechanics") or {}
        )
        action_payload = _mechanical_action_from_intent(
            semantic_action,
            deterministic_inputs,
            player_sheet,
            user_input,
            diagnostics,
        )
    except Exception as exc:
        diagnostics.append(
            {
                "category": "validation",
                "code": type(exc).__name__,
                "safe_message": "Deterministic turn inputs failed validation.",
            }
        )
        return TurnPipelineResult(
            kind="error",
            system_log="[ERROR Deterministic Inputs] A mecânica do turno não pôde ser validada.",
            updated_context=context,
            llm_diagnostics=diagnostics,
            llm_invocations=invocation_records,
        )

    status = player_sheet.status
    current_hunger = status.current_hunger
    health = status.health_tracker
    willpower = status.willpower_tracker
    
    log_builder = SystemLogBuilder()
    log_builder.scene_fact = scene_fact_text(scene)
    log_builder.response_instruction = (
        "Reaja à intenção, avance ou complique a situação e deixe uma pressão "
        "concreta para o próximo movimento, preservando a agência do jogador."
    )
    if user_input.rstrip().endswith("?"):
        log_builder.response_instruction += (
            " Responda à pergunta de modo concreto antes de continuar a cena."
        )
    occurred_at = utc_now()
    resolution_record: ResolutionResult | None = None
    resolution_action_payload: V5ActionPayload | None = None
    resolution_difficulty: int | None = None
    cache = context.get("last_action_cache")
    cached_npc_id = (
        str(cache.get("active_npc_id"))
        if isinstance(cache, Mapping) and cache.get("active_npc_id")
        else None
    )
    active_npc, active_npc_id = _find_active_npc(
        user_input,
        cached_npc_id=cached_npc_id if action_payload.is_willpower_reroll else None,
    )
    action_payload.action_target = deterministic_inputs.action_target or (
        V5ActionTarget.OPPOSED
        if active_npc is not None
        else V5ActionTarget.UNOPPOSED
    )
    
    if not action_payload.requires_roll:
        log_builder.action = user_input
        log_builder.result = (
            "A ação foi declarada sem teste mecânico."
        )
    elif action_payload.is_willpower_reroll:
        if not isinstance(cache, Mapping) or not cache:
            return TurnPipelineResult(
                kind="error",
                system_log="[ERROR_404]: Nenhum cache para rerrolar.",
                updated_context=context,
                llm_diagnostics=diagnostics,
                llm_invocations=invocation_records,
            )
        
        if before_rng is not None:
            await before_rng()
        last_res = ResolutionResult(**cache["resolution"])
        payload_cache = V5ActionPayload(**cache["payload"])
        resolution_action_payload = payload_cache
        
        cached_target = cache.get("target_successes")
        if (
            cache.get("mechanics_version") == 2
            and isinstance(cached_target, int)
            and 1 <= cached_target <= 7
        ):
            target_successes = cached_target
        else:
            target_successes, _ = _resolve_target_successes(
                payload_cache,
                deterministic_inputs,
                active_npc,
            )
        resolution_difficulty = target_successes
            
        new_res = apply_willpower_reroll(last_res, target_successes)
        resolution_record = new_res
        
        willpower.superficial += 1
        
        if payload_cache.is_aggressive:
            snapshot = context.get("pre_roll_snapshot")
            if snapshot and "health_tracker" in snapshot:
                health.size = snapshot["health_tracker"]["size"]
                health.superficial = snapshot["health_tracker"]["superficial"]
                health.aggravated = snapshot["health_tracker"]["aggravated"]

            margin = max(0, new_res.margin)
            reroll_modifiers = apply_power_modifiers(
                payload_cache.power_used,
                deterministic_inputs.is_bane_damage,
                player_sheet_dict,
                action_attribute=payload_cache.attribute.value,
            )
            damage_res = calculate_damage(
                margin=margin,
                weapon_category=payload_cache.weapon_category.value,
                is_bane=reroll_modifiers.is_bane,
                is_supernatural_target=(
                    active_npc.engine_data.is_supernatural
                    if active_npc is not None
                    else True
                ),
                weapon_damage_bonus=reroll_modifiers.weapon_damage_bonus,
                is_true_faith_active=deterministic_inputs.is_true_faith_active,
                unhalved_superficial_to_vampires=(
                    reroll_modifiers.unhalved_superficial_to_vampires
                ),
            )
            
            log_builder.combat_log = f"Novo Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({payload_cache.weapon_category.value}). "
            
        context["last_action_cache"]["resolution"] = new_res.model_dump()
        
        log_builder.action = "Rerrolar Força de Vontade"
        log_builder.result = _narrative_resolution_summary(new_res)
        log_builder.economy_log = "Dano de Vontade: 1 Superficial. "
        log_builder.willpower_reroll = "Sim"

    else:
        if before_rng is not None:
            await before_rng()
        context["pre_roll_snapshot"] = {
            "health_tracker": health.model_dump(),
            "willpower_tracker": willpower.model_dump()
        }
        
        attr_val = player_sheet.attributes.get(action_payload.attribute.value, 1)
        skill_val = player_sheet.skills.get(action_payload.skill.value, 0)
        base_pool = attr_val + skill_val
        
        power_weapon_bonus = 0
        unhalved_superficial_to_vampires = False
        current_is_bane = deterministic_inputs.is_bane_damage
        
        if action_payload.is_blood_surge:
            rouse_res = rouse_check(current_hunger, rouse_level=1)
            current_hunger = rouse_res.new_hunger
            surge_bonus = get_blood_surge_bonus(status.blood_potency)
            base_pool += surge_bonus
            log_builder.economy_log += f"(Surto: +{surge_bonus} dados. {rouse_res.summary}) "
            
        if action_payload.is_healing:
            heal_amount = get_healing_amount(status.blood_potency)
            rouse_res = rouse_check(current_hunger, rouse_level=1)
            current_hunger = rouse_res.new_hunger
            healed = min(heal_amount, health.superficial)
            health.superficial -= healed
            log_builder.economy_log += f"(Cura Mending: {healed} Superficial curado. {rouse_res.summary}) "
            
        if action_payload.power_used:
            cost = get_power_cost(action_payload.power_used)
            if cost > 0 and current_hunger >= 5:
                log_builder.power_log += f"(Poder falhou: {action_payload.power_used}. Fome muito alta para Rouse Check.) "
            else:
                if cost > 0:
                    rouse_res = rouse_check(current_hunger, rouse_level=cost)
                    current_hunger = rouse_res.new_hunger
                    log_builder.power_log += f"(Poder: {action_payload.power_used}. {rouse_res.summary}) "
                
                modifiers = apply_power_modifiers(
                    action_payload.power_used,
                    current_is_bane,
                    player_sheet_dict,
                    action_attribute=action_payload.attribute.value,
                )
                base_pool += modifiers.dice_bonus
                power_weapon_bonus = modifiers.weapon_damage_bonus
                current_is_bane = modifiers.is_bane
                unhalved_superficial_to_vampires = (
                    modifiers.unhalved_superficial_to_vampires
                )
            
        if action_payload.is_feeding:
            feed_res = feed(
                current_hunger,
                slake_amount=2,
                target_killed=deterministic_inputs.target_killed,
            )
            current_hunger = feed_res.new_hunger
            log_builder.economy_log += f"(Alimentação: {feed_res.summary}) "

        from .clan_service import get_clan_engine
        compulsion_penalty = 0
        if deterministic_inputs.is_compulsion_active:
            engine = get_clan_engine(player_sheet.clan)
            if engine:
                compulsion_penalty = engine.compulsion_dice_penalty
                base_pool -= compulsion_penalty
                base_pool = max(0, base_pool)
                log_builder.economy_log += f"(Compulsão Ativa: -{compulsion_penalty} dados) "

        target_successes, reduction = _resolve_target_successes(
            action_payload,
            deterministic_inputs,
            active_npc,
        )
        if reduction:
            log_builder.economy_log += f"(Corrupção do Alvo: Dificuldade reduzida em {reduction}) "

        resolution = calculate_resolution(action_payload, current_hunger, dice_pool=base_pool)
        resolution_record = resolution
        resolution_action_payload = action_payload
        resolution_difficulty = target_successes
        
        context["last_action_cache"] = {
            "resolution": resolution.model_dump(),
            "payload": action_payload.model_dump(),
            "is_bane": current_is_bane,
            "power_weapon_bonus": power_weapon_bonus,
            "is_supernatural_target": active_npc.engine_data.is_supernatural if active_npc else True,
            "active_npc_id": active_npc_id,
            "target_successes": target_successes,
            "mechanics_version": 2,
        }
        
        if action_payload.is_aggressive:
            margin = max(0, resolution.margin)
            damage_res = calculate_damage(
                margin=margin,
                weapon_category=action_payload.weapon_category.value,
                is_bane=current_is_bane,
                is_supernatural_target=context["last_action_cache"]["is_supernatural_target"],
                weapon_damage_bonus=power_weapon_bonus,
                is_true_faith_active=deterministic_inputs.is_true_faith_active,
                unhalved_superficial_to_vampires=unhalved_superficial_to_vampires,
            )
            weapon_desc = action_payload.power_used if action_payload.power_used else action_payload.weapon_category.value
            log_builder.combat_log = f"Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({weapon_desc}). "
            
        log_builder.action = action_payload.intent
        log_builder.result = _narrative_resolution_summary(resolution)

    status.current_hunger = current_hunger
    log_builder.hunger = current_hunger
    
    context["player_sheet"] = player_sheet.model_dump()
    
    # Catalog lore is deterministic input. Free-form H0/H4 output may guide
    # routing, but it is not eligible to become canonical action context.
    from .lore_service import get_contextual_lore_candidates
    catalog_candidates = get_contextual_lore_candidates(
        user_input, action_payload, player_sheet
    )

    # --- Motor relacional e fatos canônicos (sem persistência antecipada) ---
    from .relationship_service import (
        load_relationships,
        update_relationships_from_action,
        get_relationships_for_frontend
    )
    rel_state = await load_relationships(session_id)
    is_aggressive = action_payload.is_aggressive if action_payload else False
    rel_state = update_relationships_from_action(
        rel_state,
        user_input,
        is_aggressive,
        turn,
        resolution_success=(
            resolution_record.is_success if resolution_record is not None else None
        ),
        action_skill=(
            action_payload.skill.value if action_payload.requires_roll else None
        ),
        messy_critical=(
            resolution_record.messy_critical if resolution_record is not None else False
        ),
    )
    rel_fragment = _active_relationship_context(rel_state, active_npc_id)
    if rel_fragment:
        log_builder.relationship_context = rel_fragment
    relationships_for_frontend = get_relationships_for_frontend(rel_state)

    if resolution_record is not None:
        if resolution_action_payload is None or resolution_difficulty is None:
            raise RuntimeError("resolved action is missing its deterministic receipt")
        resolution_payload = {
            **resolution_record.model_dump(mode="json"),
            "attribute": resolution_action_payload.attribute.value,
            "skill": resolution_action_payload.skill.value,
            "dice_pool": (
                len(resolution_record.normal_rolls)
                + len(resolution_record.hunger_rolls)
            ),
            "hunger_dice": len(resolution_record.hunger_rolls),
            "difficulty": resolution_difficulty,
            "outcome": "success" if resolution_record.is_success else "failure",
            "messy": resolution_record.messy_critical,
            "bestial": resolution_record.bestial_failure,
        }
        resolution_fact_type = "mechanics.resolution"
        resolution_predicate = "resolved_player_action"
        resolution_tags = ("mechanics", "resolution")
        resolution_source = "rules_service.calculate_resolution"
        expected_outcome = resolution_payload["outcome"]
    else:
        resolution_payload = {
            "player_input": user_input,
            "requires_roll": False,
            "power_used": action_payload.power_used,
            "summary": log_builder.result,
        }
        resolution_fact_type = "action.declaration"
        resolution_predicate = "declared_player_action"
        resolution_tags = ("action", "declaration")
        resolution_source = "orchestrator.local_action_classification"
        expected_outcome = "unresolved"
    base_facts = (
        CanonicalFact(
            fact_id=_stable_id(operation_id, "fact-resolution"),
            fact_type=resolution_fact_type,
            predicate=resolution_predicate,
            value=resolution_payload,
            occurred_at=occurred_at,
            visibility=Visibility.PLAYER,
            importance=0.8,
            tags=resolution_tags,
            source_refs=(
                RecordReference(
                    record_id=resolution_source,
                    record_type="deterministic_module",
                    relation="produced_by",
                ),
            ),
        ),
        CanonicalFact(
            fact_id=_stable_id(operation_id, "fact-state"),
            fact_type="state.character",
            predicate="character_state_after_resolution",
            value=player_sheet.status.model_dump(mode="json"),
            occurred_at=occurred_at,
            visibility=Visibility.PLAYER,
            importance=0.7,
            tags=("character", "state"),
            source_refs=(
                RecordReference(
                    record_id="orchestrator.deterministic_transition",
                    record_type="deterministic_module",
                    relation="produced_by",
                ),
            ),
        ),
        CanonicalFact(
            fact_id=_stable_id(operation_id, "fact-relationships"),
            fact_type="world.relationships",
            predicate="relationships_after_action",
            value=rel_state.model_dump(mode="json"),
            occurred_at=occurred_at,
            visibility=Visibility.STORYTELLER,
            importance=0.5,
            tags=("world", "relationships"),
            source_refs=(
                RecordReference(
                    record_id="relationship_service.update_relationships_from_action",
                    record_type="deterministic_module",
                    relation="produced_by",
                ),
            ),
        ),
    )
    facts = base_facts

    actors = [
        EntityReference(
            entity_id=session_id,
            entity_type="player_character",
            label=player_sheet.nome,
        )
    ]
    if active_npc_id:
        actors.append(
            EntityReference(
                entity_id=active_npc_id,
                entity_type="npc",
                label=active_npc_id.replace("_", " ").title(),
            )
        )
    turn_id = _stable_id(operation_id, "turn")
    action_was_resolved = resolution_record is not None
    player_event = CanonicalEvent(
        event_id=_stable_id(operation_id, "event"),
        session_id=session_id,
        turn_id=turn_id,
        sequence=0,
        event_type=(
            "player_action_resolved" if action_was_resolved else "player_action_declared"
        ),
        occurred_at=occurred_at,
        summary=(
            f"Ação declarada: {user_input}. Resultado: {log_builder.result}"
            if action_was_resolved
            else f"Ação narrativa declarada pelo jogador: {user_input}"
        ),
        fact_ids=(facts[0].fact_id, facts[1].fact_id),
        tags=(
            ("turn", "resolved_action")
            if action_was_resolved
            else ("turn", "declared_action")
        ),
        actors=tuple(actors),
        importance=0.8,
        visibility=Visibility.PLAYER,
        pending=False,
    )
    relationship_event = CanonicalEvent(
        event_id=_stable_id(operation_id, "event-relationships"),
        session_id=session_id,
        turn_id=turn_id,
        sequence=1,
        event_type="relationship_state_updated",
        occurred_at=occurred_at,
        summary="O estado relacional foi avaliado após a ação do jogador.",
        fact_ids=(facts[2].fact_id,),
        tags=("turn", "relationships"),
        actors=tuple(actors),
        importance=0.5,
        visibility=Visibility.STORYTELLER,
        pending=False,
    )

    # --- Recuperação contextual em camadas e sob orçamento ---
    context_items: list[ContextItem] = [
        ContextItem(
            item_id=_stable_id(operation_id, "context-current-scene"),
            layer=ContextLayer.HOT_SCENE,
            content=scene_fact_text(scene),
            visibility=Visibility.PLAYER,
            occurred_at=occurred_at,
            importance=0.9,
            required=True,
            tags=("world", "scene", "current_location", "system_log_projection"),
            source_refs=(
                RecordReference(
                    record_id="campaign.scene",
                    record_type="campaign_state",
                    relation="projected_from",
                ),
            ),
        )
    ]
    for fact in facts:
        if fact.fact_type == "narrative.authorized_text":
            continue
        if fact.fact_type == "world.relationships" and not rel_fragment:
            continue
        context_items.append(
            ContextItem(
                item_id=fact.fact_id,
                layer=ContextLayer.CANONICAL_FACTS,
                content=_narrator_fact_content(
                    fact,
                    active_relationship=rel_fragment,
                ),
                visibility=fact.visibility,
                occurred_at=fact.occurred_at,
                importance=fact.importance,
                required=True,
                tags=(
                    (*fact.tags, "system_log_projection")
                    if fact.fact_type
                    in {"mechanics.resolution", "action.declaration"}
                    else fact.tags
                ),
                source_refs=fact.source_refs,
            )
        )
    context_packet = await _assemble_narrator_context(
        session_id=session_id,
        operation_id=operation_id,
        user_input=user_input,
        current_turn=turn,
        occurred_at=occurred_at,
        base_items=context_items,
        catalog_candidates=catalog_candidates,
        query_tags=tuple(str(tag) for tag in h0_result.lore_keywords),
        actor_ids=tuple(actor.entity_id for actor in actors),
    )
    log_builder.lore_context = ""
    log_builder.relationship_context = ""
    log_builder.memory_context = _context_prompt(context_packet)

    draft = TurnDraft(
        draft_id=_stable_id(operation_id, "draft"),
        session_id=session_id,
        turn_id=turn_id,
        attempt_id=f"attempt-{operation_id}",
        created_at=occurred_at,
        player_input=user_input,
        base_revision=max(0, turn - 1),
        base_state_revision=state_revision,
        facts=facts,
        events=(player_event, relationship_event),
        state_changes=(
            StateChange(
                path=("player_sheet",),
                value=context["player_sheet"],
            ),
            StateChange(
                path=("relationships",),
                value=rel_state.model_dump(mode="json"),
            ),
        ),
        context_references=tuple(
            reference
            for selected in context_packet.selected
            for reference in selected.item.source_refs
        ),
    )
    prepared_result = TurnPipelineResult(
        kind="action",
        system_log=log_builder.build(expected_outcome=expected_outcome),
        updated_context=context,
        relationships_state=rel_state,
        relationships_for_frontend=relationships_for_frontend,
        draft=draft,
        context_packet=context_packet,
        llm_diagnostics=diagnostics,
        llm_invocations=invocation_records,
    )
    from .scene_resolution_default import attach_catalog_scene_resolution

    return attach_catalog_scene_resolution(
        prepared_result,
        scene=scene,
        player_input=user_input,
        relationship=rel_state.relationships.get("mara"),
    )


async def process_turn_pipeline(
    user_input: str,
    session_id: str,
    context: dict,
    turn: int,
    chronicle_name: str,
    **kwargs: Any,
) -> tuple[str, dict, list[dict] | None]:
    """Legacy tuple projection; all new integration uses prepare_turn_pipeline."""

    result = await prepare_turn_pipeline(
        user_input,
        session_id,
        context,
        turn,
        chronicle_name,
        operation_id=kwargs.pop("operation_id", f"legacy-{uuid4()}"),
        **kwargs,
    )
    return (
        result.system_log,
        result.updated_context,
        result.relationships_for_frontend,
    )
