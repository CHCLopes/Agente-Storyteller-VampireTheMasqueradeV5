from datetime import datetime, timedelta
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

from .core.config import settings
from .llm import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement,
    CancellationToken,
    ErrorCategory,
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
class H1IntentPayload(BaseModel):
    """Semantic action classification; no canonical mechanics or outcomes."""

    # Obsolete provider fields are ignored defensively. They cannot cross into
    # the engine because this contract has no difficulty, threat, status or
    # result fields and the orchestrator builds the mechanical payload itself.
    model_config = ConfigDict(extra="ignore")

    intent: str


LLMServiceDiagnostic: TypeAlias = NormalizedError | dict[str, str]

H1_PROMPT = load_versioned_prompt(
    "H1_vtm_rules_parser",
    fallback="Extraia apenas a intenção sem decidir mecânica ou resultado.",
)

async def extract_intent(
    user_input: str,
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline_seconds: float | None = None,
    diagnostics: list[LLMServiceDiagnostic] | None = None,
    invocations: list[InvocationRecord] | None = None,
) -> H1IntentPayload:
    if not settings.llm_h1_enabled:
        return _create_fallback_payload(user_input)

    try:
        messages = (
            LLMMessage(role=MessageRole.SYSTEM, content=H1_PROMPT),
            LLMMessage(role=MessageRole.USER, content=user_input),
        )
        resolved_gateway, resolved_target = _resolve_llm(gateway, target)
        shared_cancellation = cancellation or CancellationToken()
        effective_deadline_seconds = min(
            deadline_seconds
            if deadline_seconds is not None
            else settings.llm_h1_timeout_seconds,
            float(settings.llm_timeout_seconds),
        )
        deadline = utc_now() + timedelta(seconds=effective_deadline_seconds)
        return await _call_h1(
            messages,
            gateway=resolved_gateway,
            target=resolved_target,
            cancellation=shared_cancellation,
            deadline=deadline,
            operation="h1.extract_intent.attempt_1",
            invocations=invocations,
        )
    except LLMInvocationError as exc:
        if diagnostics is not None:
            diagnostics.append(exc.error)
        if exc.error.category is not ErrorCategory.INVALID_STRUCTURED_OUTPUT:
            return _create_fallback_payload(user_input)

        repair_messages = (
            *messages,
            LLMMessage(
                role=MessageRole.ASSISTANT,
                content="A resposta anterior não correspondeu ao schema solicitado.",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="Tente novamente e retorne somente um objeto válido para o schema.",
            ),
        )
        try:
            return await _call_h1(
                repair_messages,
                gateway=resolved_gateway,
                target=resolved_target,
                cancellation=shared_cancellation,
                deadline=deadline,
                operation="h1.extract_intent.attempt_2",
                invocations=invocations,
            )
        except LLMInvocationError as retry_exc:
            if diagnostics is not None:
                diagnostics.append(retry_exc.error)
            return _create_fallback_payload(user_input)
        except Exception:
            _append_safe_diagnostic(
                diagnostics,
                category="adapter_failure",
                code="h1_retry_runtime_failure",
                message="H1 retry could not complete through the configured LLM runtime.",
            )
            return _create_fallback_payload(user_input)
    except Exception:
        _append_safe_diagnostic(
            diagnostics,
            category="adapter_failure",
            code="h1_runtime_failure",
            message="H1 could not access the configured LLM runtime.",
        )
        return _create_fallback_payload(user_input)


async def _call_h1(
    messages: list[dict[str, str]] | tuple[LLMMessage, ...],
    *,
    gateway: LLMGateway | None = None,
    target: LLMTarget | None = None,
    cancellation: CancellationToken | None = None,
    deadline: datetime | None = None,
    deadline_seconds: float = 30.0,
    operation: str = "h1.extract_intent",
    invocations: list[InvocationRecord] | None = None,
) -> H1IntentPayload:
    resolved_gateway, resolved_target = _resolve_llm(gateway, target)
    request = StructuredGenerationRequest(
        operation=operation,
        target=resolved_target,
        messages=_coerce_messages(messages),
        deadline=deadline or (utc_now() + timedelta(seconds=deadline_seconds)),
        cancellation=cancellation or CancellationToken(),
        parameters=GenerationParameters(temperature=0.1),
        response_model=H1IntentPayload,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )
    try:
        result = await resolved_gateway.generate_structured(request)
    except LLMInvocationError as exc:
        if invocations is not None:
            invocations.append(InvocationRecord.failed(request.operation, exc.error))
        raise
    if invocations is not None:
        invocations.append(InvocationRecord.completed(request.operation, result.evidence))
    if not isinstance(result.value, H1IntentPayload):
        raise TypeError("H1 returned an unexpected product result type")
    return result.value


def _coerce_messages(
    messages: list[dict[str, str]] | tuple[LLMMessage, ...],
) -> tuple[LLMMessage, ...]:
    converted: list[LLMMessage] = []
    for message in messages:
        if isinstance(message, LLMMessage):
            converted.append(message)
        else:
            converted.append(
                LLMMessage(
                    role=MessageRole(message["role"]),
                    content=message["content"],
                )
            )
    return tuple(converted)


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

def _create_fallback_payload(user_input: str) -> H1IntentPayload:
    """Preserve the player's declaration when semantic enrichment is unavailable."""

    return H1IntentPayload(intent=user_input)
