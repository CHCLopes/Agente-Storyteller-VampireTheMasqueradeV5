"""
api/h0_controller_service.py
H0 — Controller LLM. Pré-processador de triagem e enriquecimento de contexto.
Decide se o input é ação de jogo (roteada para H1) ou consulta de lore (roteada para H4).
Operação graceful: se a chamada LLM falhar, assume ação de jogo (fallback seguro).
"""
import re
from datetime import timedelta
from typing import Iterable, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from .core.config import settings
from .llm import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement,
    CancellationToken,
    GenerationParameters,
    InvocationRecord,
    LLMGateway,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    NormalizedError,
    StructuredGenerationRequest,
    get_llm_runtime,
)
from .llm.contract import utc_now
from .prompt_service import load_versioned_prompt


LLMServiceDiagnostic: TypeAlias = NormalizedError | dict[str, str]

_H0_SYSTEM_PROMPT = load_versioned_prompt(
    "H0_vtm_orchestrator",
    section="triage",
    fallback="Classifique a entrada como action ou lore_query e responda no schema solicitado.",
)


class H0TriageResult:
    """Resultado da triagem do H0."""
    def __init__(self, route: str = "action", scene_notes: str = "", lore_keywords: list[str] | None = None):
        self.route = route
        self.scene_notes = scene_notes
        self.lore_keywords = lore_keywords or []

    @property
    def is_lore_query(self) -> bool:
        return self.route == "lore_query"


class H0StructuredResult(BaseModel):
    """Product-owned schema accepted from the H0 model."""

    model_config = ConfigDict(extra="forbid")

    route: Literal["action", "lore_query"] = "action"
    scene_notes: str = ""
    lore_keywords: list[str] = Field(default_factory=list)


async def triage_input(
    user_input: str,
    *,
    npc_aliases: Iterable[str] = (),
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
    diagnostics: list[LLMServiceDiagnostic] | None = None,
    invocations: list[InvocationRecord] | None = None,
) -> H0TriageResult:
    """
    Chama o LLM para classificar e enriquecer o input do jogador.
    Retorna H0TriageResult com rota, notas de cena e keywords de lore.
    Em caso de falha, retorna fallback seguro (route=action).
    """
    if _addresses_present_npc(user_input, npc_aliases):
        return H0TriageResult(route="action")
    if not settings.llm_h0_enabled:
        return _deterministic_triage(user_input)

    try:
        resolved_gateway, resolved_target = _resolve_llm(gateway, target)
        effective_deadline_seconds = min(
            deadline_seconds
            if deadline_seconds is not None
            else settings.llm_h0_timeout_seconds,
            float(settings.llm_timeout_seconds),
        )
        request = StructuredGenerationRequest(
            operation="h0.triage",
            target=resolved_target,
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=_H0_SYSTEM_PROMPT),
                LLMMessage(role=MessageRole.USER, content=user_input),
            ),
            deadline=utc_now() + timedelta(seconds=effective_deadline_seconds),
            cancellation=cancellation or CancellationToken(),
            parameters=GenerationParameters(temperature=0.1),
            response_model=H0StructuredResult,
            required_capabilities=(
                CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
                CapabilityRequirement(
                    name=CAPABILITY_STRUCTURED_GENERATION,
                    allow_emulated=True,
                ),
            ),
        )
        result = await resolved_gateway.generate_structured(request)
        if invocations is not None:
            invocations.append(InvocationRecord.completed(request.operation, result.evidence))
        if not isinstance(result.value, H0StructuredResult):
            _append_safe_diagnostic(
                diagnostics,
                category="malformed_response",
                code="h0_unexpected_result_type",
                message="H0 returned an unexpected product result type.",
            )
            return _deterministic_triage(user_input)
        return H0TriageResult(
            route=result.value.route,
            scene_notes=result.value.scene_notes,
            lore_keywords=result.value.lore_keywords,
        )
    except LLMInvocationError as exc:
        if invocations is not None:
            invocations.append(InvocationRecord.failed(request.operation, exc.error))
        if diagnostics is not None:
            diagnostics.append(exc.error)
    except Exception:
        _append_safe_diagnostic(
            diagnostics,
            category="adapter_failure",
            code="h0_runtime_failure",
            message="H0 could not access the configured LLM runtime.",
        )

    # Fallback determinístico
    return _deterministic_triage(user_input)


def _resolve_llm(
    gateway: LLMGateway | None,
    target: LLMTarget | None,
) -> tuple[LLMGateway, LLMTarget]:
    if gateway is not None and target is not None:
        return gateway, target
    if gateway is not None or target is not None:
        raise ValueError("gateway and target must be supplied together")
    runtime = get_llm_runtime()
    return runtime.gateway, runtime.target


def _append_safe_diagnostic(
    diagnostics: list[LLMServiceDiagnostic] | None,
    *,
    category: str,
    code: str,
    message: str,
) -> None:
    if diagnostics is not None:
        diagnostics.append(
            {"category": category, "code": code, "safe_message": message}
        )


def _deterministic_triage(user_input: str) -> H0TriageResult:
    """Triagem determinística como fallback se o LLM falhar."""
    addressed_npc_patterns = (
        r"^\s*[\wÀ-ÿ][\wÀ-ÿ '-]{0,79},\s*(?:me\s+)?(?:fale|conte|explique|diga)\b",
        r"\b(?:digo|pergunto|falo)\s+(?:a|ao|com)\s+[\wÀ-ÿ][\wÀ-ÿ '-]{0,79}\b",
    )
    if any(
        re.search(pattern, user_input, flags=re.IGNORECASE)
        for pattern in addressed_npc_patterns
    ):
        return H0TriageResult(route="action")
    lore_patterns = [
        r'\bo que [ée]\b', r'\bquem [ée]\b', r'\bcomo funciona\b',
        r'\bexplique\b', r'\bqual\b.*\bsignificado\b', r'\bhistória d[aeo]\b',
        r'\bconte.me sobre\b', r'\bme fale sobre\b', r'\bdefina\b'
    ]
    normalized = user_input.lower()
    for pattern in lore_patterns:
        if re.search(pattern, normalized):
            # Extrai keywords simples
            stop_words = {"o", "a", "os", "as", "de", "da", "do", "em", "que", "é", "um", "uma", "me", "sobre"}
            words = [w for w in re.findall(r'\w+', normalized) if w not in stop_words and len(w) > 2]
            return H0TriageResult(route="lore_query", lore_keywords=words[:3])

    return H0TriageResult(route="action")


def _addresses_present_npc(user_input: str, npc_aliases: Iterable[str]) -> bool:
    """Keep direct speech to a present NPC inside the scene pipeline."""

    for raw_alias in npc_aliases:
        if not isinstance(raw_alias, str):
            continue
        alias = " ".join(raw_alias.split())
        if not alias or len(alias) > 80:
            continue
        escaped = re.escape(alias)
        if re.search(rf"^\s*{escaped}\s*,\s*\S", user_input, flags=re.IGNORECASE):
            return True
        if re.search(
            rf"\b(?:digo|pergunto|falo)\s+(?:a|ao|com)\s+{escaped}\b",
            user_input,
            flags=re.IGNORECASE,
        ):
            return True
    return False
