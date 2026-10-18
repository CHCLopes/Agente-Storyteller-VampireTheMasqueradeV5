"""Direct Groq policy behind the provider-neutral LLM boundary.

The adapter is deliberately limited to the exact targets admitted to the
synthetic narrator comparison. It reuses Groq's OpenAI-compatible transport,
but never routes through an intermediary or substitutes another model.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import SecretStr

from ..contract import (
    CapabilitySet,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    InvocationEvidence,
    LLMInvocationError,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceSource,
    ProvenanceValue,
    RateLimitEvidence,
    RateLimitOrigin,
    RateLimitQuota,
    StructuredGenerationRequest,
    TokenUsage,
    utc_now,
)
from .openai_compatible import OpenAICompatibleAdapter, _MAX_ERROR_RESPONSE_BYTES


GROQ_OFFICIAL_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_PROVIDER_LABEL = "Groq"
GROQ_QWEN_MODEL_ID = "qwen/qwen3.8-27b"
GROQ_GPT_OSS_MODEL_ID = "openai/gpt-oss-120b"
GROQ_EVALUATED_MODEL_IDS = frozenset(
    {GROQ_QWEN_MODEL_ID, GROQ_GPT_OSS_MODEL_ID}
)

_FIXED_REASONING_EFFORT = {
    GROQ_QWEN_MODEL_ID: "none",
    GROQ_GPT_OSS_MODEL_ID: "low",
}

_QUOTA_COUNT = re.compile(r"[0-9]{1,15}\Z")
_QUOTA_DURATION = re.compile(
    r"(?:(?P<hours>[0-9]{1,6})h)?"
    r"(?:(?P<minutes>[0-9]{1,8})m)?"
    r"(?:(?P<seconds>[0-9]{1,8}(?:\.[0-9]{1,6})?)s)?"
    r"(?:(?P<milliseconds>[0-9]{1,8}(?:\.[0-9]{1,6})?)ms)?\Z"
)


def _quota_count(value: str | None) -> int | None:
    if value is None or _QUOTA_COUNT.fullmatch(value.strip()) is None:
        return None
    return int(value.strip())


def _quota_reset_seconds(value: str | None) -> float | None:
    if value is None or len(value) > 64:
        return None
    matched = _QUOTA_DURATION.fullmatch(value.strip())
    if matched is None or not any(matched.groupdict().values()):
        return None
    factors = {"hours": 3600, "minutes": 60, "seconds": 1, "milliseconds": 0.001}
    seconds = sum(
        float(amount) * factors[unit]
        for unit, amount in matched.groupdict().items() if amount is not None
    )
    return seconds if seconds <= 31_536_000 else None


def _rate_limit_body_fields(
    response: Any, response_body: bytes | None
) -> tuple[str | None, str | None]:
    """Read bounded machine fields only; never retain a raw provider message."""

    if response is None or response.status_code != 429:
        return None, None
    if response_body is None:
        if not response.is_stream_consumed:
            return None, None
        try:
            response_body = response.content
        except RuntimeError:
            return None, None
    if len(response_body) > _MAX_ERROR_RESPONSE_BYTES:
        return None, None
    try:
        payload = json.loads(response_body)
    except (ValueError, TypeError, RecursionError):
        return None, None
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return None, None
    # A character regex is not sufficient: an echoed credential can also look
    # like a machine code. Only these exact non-sensitive values may escape.
    code = "rate_limit_exceeded" if error.get("code") == "rate_limit_exceeded" else None
    resource = error.get("type")
    if not isinstance(resource, str) or resource not in {"requests", "tokens"}:
        resource = None
    return code, resource


_MAX_BAD_REQUEST_BODY_BYTES = 32 * 1024


def _bad_request_code(
    response: httpx.Response, response_body: bytes | None
) -> str | None:
    """Retain one provider-reported code, never its message or failed output."""

    if response.status_code != 400:
        return None
    if response_body is None:
        if not response.is_stream_consumed:
            return None
        try:
            response_body = response.content
        except RuntimeError:
            return None
    if len(response_body) > _MAX_BAD_REQUEST_BODY_BYTES:
        return None
    try:
        payload = json.loads(response_body)
    except (ValueError, TypeError, RecursionError):
        return None
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("code") == "json_validate_failed":
        # This is a provider report, not proof of a local JSON/schema failure.
        # Exact matching prevents arbitrary error strings from crossing the boundary.
        return "groq_json_validate_failed"
    return None


def _normalize_groq_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adapt Pydantic JSON Schema to Groq's documented strict-mode rules.

    Groq strict mode requires every object property to be listed in
    ``required`` and every object to reject additional properties. Pydantic
    defaults remain product behavior, but strict constrained decoding cannot
    omit those fields, so provider-bound defaults are removed and the model
    must emit their explicit values. The input schema is never mutated.
    """

    def visit(value: Any) -> Any:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value

        all_of = value.get("allOf")
        if all_of is not None:
            siblings = {
                key: item
                for key, item in value.items()
                if key not in {"allOf", "default"}
            }
            if (
                not isinstance(all_of, list)
                or len(all_of) != 1
                or not isinstance(all_of[0], dict)
                or siblings
            ):
                raise ValueError(
                    "Groq strict schema contains an unsupported allOf composition."
                )
            # Pydantic wraps enum references that carry a default in a unitary
            # allOf. Groq's strict subset does not document allOf, so preserve
            # the equivalent reference after the default is removed.
            return visit(all_of[0])

        normalized = {
            key: visit(item)
            for key, item in value.items()
            if key != "default"
        }
        properties = normalized.get("properties")
        if isinstance(properties, dict):
            normalized["required"] = list(properties)
            normalized["additionalProperties"] = False
        return normalized

    normalized = visit(schema)
    assert isinstance(normalized, dict)
    return normalized


class GroqAdapter(OpenAICompatibleAdapter):
    """Bind one fixed Groq-hosted evaluation target to the LLM contract."""

    def __init__(
        self,
        *,
        base_url: str,
        capability_set: CapabilitySet,
        api_key: SecretStr | None,
        reasoning_effort: str | None,
        adapter_version: str = "1.0",
        transport: Any = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url != GROQ_OFFICIAL_BASE_URL:
            raise ValueError(
                "Groq adapter requires the exact official OpenAI-compatible base URL."
            )
        if (
            capability_set.target.provider.strip().casefold()
            != GROQ_PROVIDER_LABEL.casefold()
        ):
            raise ValueError(
                f"Groq adapter target provider must be {GROQ_PROVIDER_LABEL}."
            )
        model = capability_set.target.model.strip()
        if model not in GROQ_EVALUATED_MODEL_IDS:
            raise ValueError(
                "Groq adapter requires one of the fixed narrator evaluation model ids."
            )
        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError(
                "Groq adapter requires an explicit non-empty GROQ_API_KEY."
            )
        expected_reasoning = _FIXED_REASONING_EFFORT[model]
        if reasoning_effort != expected_reasoning:
            raise ValueError(
                f"Groq narrator profile {model} requires reasoning_effort="
                f"{expected_reasoning!r}."
            )

        super().__init__(
            base_url=cleaned_url,
            capability_set=capability_set,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            adapter_name="groq-chat-completions",
            adapter_version=adapter_version,
            transport=transport,
        )

    def _native_response_format(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": request.response_model.__name__,
                "strict": True,
                "schema": _normalize_groq_strict_schema(
                    request.response_model.model_json_schema()
                ),
            },
        }

    def _payload(
        self,
        request: GenerationRequest,
        *,
        stream: bool,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = super()._payload(
            request,
            stream=stream,
            response_format=response_format,
        )
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
        # The generic adapter requests a final usage-only SSE frame. The Groq
        # comparison does not rely on that optional extension, so omit it and
        # keep absent streaming measurements explicitly unavailable.
        payload.pop("stream_options", None)
        if request.target.model == GROQ_GPT_OSS_MODEL_ID:
            # GPT-OSS does not support ``reasoning_format`` on Groq. Exclude
            # its separate reasoning field with the documented control so the
            # evaluation persists only the answer the product can validate.
            payload["include_reasoning"] = False
        return payload

    def _evidence(
        self,
        *,
        request: GenerationRequest,
        started_at: datetime,
        effective_provider: str | None = None,
        effective_model: str | None = None,
        usage: TokenUsage | None = None,
        cost: CostMeasurement | None = None,
    ) -> InvocationEvidence:
        return InvocationEvidence(
            provenance=Provenance(
                invocation_id=request.invocation_id,
                requested_target=request.target,
                adapter=self._identity,
                effective_provider=ProvenanceValue.observed(GROQ_PROVIDER_LABEL),
                effective_model=(
                    ProvenanceValue.reported(effective_model)
                    if effective_model
                    else ProvenanceValue.unknown()
                ),
                started_at=started_at,
                finished_at=utc_now(),
            ),
            usage=usage or TokenUsage.unavailable(),
            cost=cost or CostMeasurement.unavailable(),
        )

    def _validate_final_evidence(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        provenance = evidence.provenance
        if (
            provenance.effective_provider.source is not ProvenanceSource.OBSERVED
            or provenance.effective_provider.value != GROQ_PROVIDER_LABEL
            or provenance.effective_model.source is not ProvenanceSource.REPORTED
            or provenance.effective_model.value is None
        ):
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="groq_unverified_target_provenance",
                    phase=OperationPhase.RESPONSE,
                    safe_message="Groq target provenance could not be verified.",
                )
            )

    def _parse_cost(self, payload: dict[str, Any]) -> CostMeasurement:
        # Groq's chat response does not document a per-call monetary charge.
        return CostMeasurement.unavailable()

    def _normalize_exception(
        self,
        *,
        request: GenerationRequest,
        started_at: datetime,
        phase: OperationPhase,
        exc: Exception,
        response: httpx.Response | None = None,
        response_body: bytes | None = None,
        effective_provider: str | None = None,
        effective_model: str | None = None,
        usage: TokenUsage | None = None,
        cost: CostMeasurement | None = None,
        partial_output: bool = False,
    ) -> NormalizedError:
        error = super()._normalize_exception(
            request=request,
            started_at=started_at,
            phase=phase,
            exc=exc,
            response=response,
            response_body=response_body,
            effective_provider=effective_provider,
            effective_model=effective_model,
            usage=usage,
            cost=cost,
            partial_output=partial_output,
        )
        if (
            isinstance(exc, httpx.HTTPStatusError)
            and exc.response.status_code == 400
            and error.category is ErrorCategory.INVALID_REQUEST
            and error.code == "http_400"
        ):
            code = _bad_request_code(exc.response, response_body)
            if code is not None:
                return error.model_copy(update={"code": code})
        return error

    def _rate_limit_evidence(
        self,
        *,
        category: ErrorCategory,
        response: Any,
        response_body: bytes | None = None,
        origin: RateLimitOrigin | None = None,
        provider_code: str | None = None,
    ) -> RateLimitEvidence | None:
        if category is not ErrorCategory.RATE_LIMITED:
            return None
        code, resource = _rate_limit_body_fields(response, response_body)
        quotas = []
        # Groq documents request headers as RPD and token headers as TPM.
        # These are separate observations, not a computed retry-after value.
        for unit, window in (("requests", 86400), ("tokens", 60)):
            headers = response.headers if response is not None else {}
            limit = _quota_count(headers.get(f"x-ratelimit-limit-{unit}"))
            remaining = _quota_count(headers.get(f"x-ratelimit-remaining-{unit}"))
            reset = _quota_reset_seconds(headers.get(f"x-ratelimit-reset-{unit}"))
            if any(value is not None for value in (limit, remaining, reset)):
                quotas.append(RateLimitQuota(
                    resource=unit,
                    window_seconds=window,
                    limit=limit,
                    remaining=remaining,
                    reset_after_seconds=reset,
                ))
        return RateLimitEvidence(
            provider_code=code,
            resource=resource,
            quotas=tuple(quotas),
        )
