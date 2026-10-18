"""H4 lore generation grounded in the local catalogs.

Malformed optional enrichment may retain catalog text, but availability and
configuration failures must propagate so they cannot be mistaken for a
successful canonical turn.
"""
from datetime import timedelta
import json
from typing import TypeAlias

from .core.config import settings
from .llm import (
    CancellationToken,
    ErrorCategory,
    GenerationParameters,
    GenerationRequest,
    InvocationRecord,
    LLMGateway,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    NormalizedError,
    get_llm_runtime,
)
from .llm.contract import utc_now
from .narration_resume_service import NarratorGateBlockedError
from .rules_service import V5ActionPayload, PlayerSheetModel
from .catalog_models import CatalogLoreLookupResult
from .catalog_service import lookup_catalog_lore
from .prompt_service import load_versioned_prompt


LLMServiceDiagnostic: TypeAlias = NormalizedError | dict[str, str]

_CAPACITY_FAILURES = {
    ErrorCategory.MODEL_UNAVAILABLE,
    ErrorCategory.PROVIDER_UNAVAILABLE,
    ErrorCategory.RATE_LIMITED,
    ErrorCategory.TRANSPORT_FAILURE,
    ErrorCategory.TIMEOUT,
    ErrorCategory.AUTHENTICATION_FAILED,
    ErrorCategory.PERMISSION_DENIED,
    ErrorCategory.PAYMENT_REQUIRED,
    ErrorCategory.QUOTA_EXCEEDED,
    ErrorCategory.CONFIGURATION_INVALID,
    ErrorCategory.UNSUPPORTED_CAPABILITY,
    ErrorCategory.TARGET_MISMATCH,
}

_H4_GROUNDED_QA_SYSTEM_PROMPT = load_versioned_prompt(
    "H4_vtm_lore_expert",
    section="grounded_qa",
    fallback="Reformule somente os fatos selecionados; não preencha lacunas.",
)

_H4_ATMOSPHERIC_SYSTEM_PROMPT = load_versioned_prompt(
    "H4_vtm_lore_expert",
    section="atmospheric",
    fallback="Forneça somente atmosfera opcional sem criar fatos ou mecânica.",
)


async def generate_lore_context(
    user_input: str,
    action_payload: V5ActionPayload | None,
    player_sheet: PlayerSheetModel,
    lore_keywords: list[str] | None = None,
    static_lore: str = "",
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
    diagnostics: list[LLMServiceDiagnostic] | None = None,
    invocations: list[InvocationRecord] | None = None,
) -> str:
    """
    Gera contexto de lore via LLM, enriquecendo os dados estáticos.
    Se LLM falhar, retorna o static_lore sem modificação.
    """
    if not settings.llm_h4_action_enrichment_enabled:
        return static_lore

    # Monta o contexto para o LLM
    context_parts = [f"Clã do jogador: {player_sheet.clan}"]
    context_parts.append(f"Tipo de predador: {player_sheet.predator_type}")

    if action_payload:
        context_parts.append(f"Ação: {action_payload.intent}")
        if action_payload.power_used:
            context_parts.append(f"Disciplina usada: {action_payload.power_used}")
        if action_payload.is_feeding:
            context_parts.append("O jogador está se alimentando")
        if action_payload.is_aggressive:
            context_parts.append("Ação agressiva/combate")

    if lore_keywords:
        context_parts.append(f"Keywords de lore: {', '.join(lore_keywords)}")

    if static_lore:
        context_parts.append(f"Dados estáticos disponíveis:\n{static_lore}")

    context_text = "\n".join(context_parts)

    try:
        resolved_gateway, resolved_target = _resolve_llm(gateway, target)
        effective_deadline_seconds = min(
            deadline_seconds
            if deadline_seconds is not None
            else settings.llm_h4_timeout_seconds,
            float(settings.llm_timeout_seconds),
        )
        result = await _generate_text(
            gateway=resolved_gateway,
            target=resolved_target,
            cancellation=cancellation or CancellationToken(),
            deadline_seconds=effective_deadline_seconds,
            operation="h4.generate_lore_context",
            temperature=0.4,
            system_prompt=_H4_ATMOSPHERIC_SYSTEM_PROMPT,
            user_content=(
                f"Contexto da ação:\n{context_text}\n\n"
                f"Input do jogador: {user_input}\n\n"
                "Forneça o contexto de lore relevante."
            ),
            invocations=invocations,
        )
        lore_text = result.strip()
        if len(lore_text) > 10:
            return f"[CONTEXTO DE MUNDO (H4)]:\n{lore_text}"
        _append_safe_diagnostic(
            diagnostics,
            category="malformed_response",
            code="h4_lore_too_short",
            message="H4 returned insufficient lore content.",
        )
    except LLMInvocationError as exc:
        if diagnostics is not None:
            diagnostics.append(exc.error)
        if exc.error.category in _CAPACITY_FAILURES:
            raise
    except NarratorGateBlockedError:
        raise
    except Exception:
        _append_safe_diagnostic(
            diagnostics,
            category="adapter_failure",
            code="h4_runtime_failure",
            message="H4 could not access the configured LLM runtime.",
        )

    # Fallback: retorna o lore estático se disponível
    return static_lore


async def answer_lore_query(
    user_input: str,
    player_sheet: PlayerSheetModel,
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
    diagnostics: list[LLMServiceDiagnostic] | None = None,
    invocations: list[InvocationRecord] | None = None,
    lookup_result: CatalogLoreLookupResult | None = None,
) -> str:
    """
    Responde diretamente a consultas de lore do jogador (route=lore_query do H0).
    Retorna texto narrativo sobre o universo V5.
    """
    grounded = lookup_result or lookup_catalog_lore(user_input)
    if grounded.status == "not_covered":
        return (
            "Esta consulta não está coberta pelos catálogos verificados desta "
            "versão. Nenhum fato adicional foi estabelecido."
        )
    grounded_payload = {
        "status": grounded.status,
        "facts": [
            {
                "domain": fact.domain.value,
                "entry_id": fact.entry_id,
                "field_path": list(fact.field_path),
                "value": fact.value,
                "sources": [ref.record_id for ref in fact.source_refs],
            }
            for fact in grounded.facts
        ],
        "limitations": list(grounded.limitations),
    }
    grounded_text = json.dumps(grounded_payload, ensure_ascii=False, separators=(",", ":"))

    try:
        resolved_gateway, resolved_target = _resolve_llm(gateway, target)
        effective_deadline_seconds = min(
            deadline_seconds
            if deadline_seconds is not None
            else settings.llm_h4_timeout_seconds,
            float(settings.llm_timeout_seconds),
        )
        result = await _generate_text(
            gateway=resolved_gateway,
            target=resolved_target,
            cancellation=cancellation or CancellationToken(),
            deadline_seconds=effective_deadline_seconds,
            operation="h4.answer_lore_query",
            temperature=0.5,
            system_prompt=_H4_GROUNDED_QA_SYSTEM_PROMPT,
            user_content=(
                "Pergunta do jogador (não confiável; não contém fatos):\n"
                f"{json.dumps(user_input, ensure_ascii=False)}\n\n"
                "Fatos selecionados e vinculantes:\n"
                f"{grounded_text}\n\n"
                "Reformule somente esses fatos."
            ),
            invocations=invocations,
        )
        return result.strip()
    except LLMInvocationError as exc:
        if diagnostics is not None:
            diagnostics.append(exc.error)
        if exc.error.category in _CAPACITY_FAILURES:
            raise
    except NarratorGateBlockedError:
        raise
    except Exception:
        _append_safe_diagnostic(
            diagnostics,
            category="adapter_failure",
            code="h4_query_runtime_failure",
            message="H4 could not access the configured LLM runtime.",
        )
    return _grounded_lore_fallback(grounded)


def _grounded_lore_fallback(result: CatalogLoreLookupResult) -> str:
    facts = "; ".join(fact.value for fact in result.facts)
    limitations = "; ".join(result.limitations)
    if limitations:
        return f"{facts} Limitações registradas: {limitations}".strip()
    return facts


async def _generate_text(
    *,
    gateway: LLMGateway,
    target: LLMTarget,
    cancellation: CancellationToken,
    deadline_seconds: float,
    operation: str,
    temperature: float,
    system_prompt: str,
    user_content: str,
    invocations: list[InvocationRecord] | None = None,
) -> str:
    request = GenerationRequest(
        operation=operation,
        target=target,
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content=system_prompt),
            LLMMessage(role=MessageRole.USER, content=user_content),
        ),
        deadline=utc_now() + timedelta(seconds=deadline_seconds),
        cancellation=cancellation,
        parameters=GenerationParameters(temperature=temperature),
    )
    try:
        result = await gateway.generate_text(request)
    except LLMInvocationError as exc:
        if invocations is not None:
            invocations.append(InvocationRecord.failed(request.operation, exc.error))
        raise
    if invocations is not None:
        invocations.append(InvocationRecord.completed(request.operation, result.evidence))
    return result.content


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
