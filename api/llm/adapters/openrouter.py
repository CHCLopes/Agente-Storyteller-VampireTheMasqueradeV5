"""OpenRouter transport policy behind the provider-neutral LLM boundary."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, NoReturn

from pydantic import SecretStr

from ..contract import (
    CapabilitySet,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    InvocationEvidence,
    MeasurementStatus,
    OperationPhase,
    RateLimitEvidence,
    RateLimitOrigin,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
)
from .openai_compatible import OpenAICompatibleAdapter, _AdapterProblem


_OFFICIAL_BASE_URLS = frozenset(
    {
        "https://openrouter.ai/api/v1",
        "https://eu.openrouter.ai/api/v1",
    }
)
_PROVIDER_SLUG = re.compile(r"\A[a-z0-9][a-z0-9._-]*\Z")
_PROVIDER_ERROR_CODE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:\-]*\Z")
_OPENROUTER_ERROR_CATEGORIES = {
    "authentication": ErrorCategory.AUTHENTICATION_FAILED,
    "permission_denied": ErrorCategory.PERMISSION_DENIED,
    "payment_required": ErrorCategory.PAYMENT_REQUIRED,
    "rate_limit_exceeded": ErrorCategory.RATE_LIMITED,
    "provider_overloaded": ErrorCategory.PROVIDER_UNAVAILABLE,
    "provider_unavailable": ErrorCategory.PROVIDER_UNAVAILABLE,
    "timeout": ErrorCategory.TIMEOUT,
    "content_policy_violation": ErrorCategory.CONTENT_REJECTED,
    "refusal": ErrorCategory.CONTENT_REJECTED,
    "context_length_exceeded": ErrorCategory.CONTEXT_LIMIT_EXCEEDED,
    "max_tokens_exceeded": ErrorCategory.MALFORMED_RESPONSE,
    "token_limit_exceeded": ErrorCategory.QUOTA_EXCEEDED,
    "string_too_long": ErrorCategory.INVALID_REQUEST,
    "invalid_request": ErrorCategory.INVALID_REQUEST,
    "invalid_prompt": ErrorCategory.INVALID_REQUEST,
    "precondition_failed": ErrorCategory.INVALID_REQUEST,
    "payload_too_large": ErrorCategory.INVALID_REQUEST,
    "unprocessable": ErrorCategory.INVALID_REQUEST,
    "not_found": ErrorCategory.MODEL_UNAVAILABLE,
    "server": ErrorCategory.PROVIDER_UNAVAILABLE,
    "unmapped": ErrorCategory.UNKNOWN,
}
_OPENROUTER_ERROR_MESSAGES = {
    ErrorCategory.INVALID_REQUEST: "OpenRouter rejected the generation request.",
    ErrorCategory.AUTHENTICATION_FAILED: "OpenRouter rejected authentication.",
    ErrorCategory.PERMISSION_DENIED: "OpenRouter denied this operation.",
    ErrorCategory.PAYMENT_REQUIRED: "OpenRouter requires available credit for this operation.",
    ErrorCategory.MODEL_UNAVAILABLE: "The requested OpenRouter model is unavailable.",
    ErrorCategory.RATE_LIMITED: "OpenRouter rate-limited the operation.",
    ErrorCategory.CONTENT_REJECTED: "OpenRouter rejected the generated content.",
    ErrorCategory.CONTEXT_LIMIT_EXCEEDED: (
        "The OpenRouter request exceeded a token or context limit."
    ),
    ErrorCategory.QUOTA_EXCEEDED: "The OpenRouter request exceeded an account or token quota.",
    ErrorCategory.TIMEOUT: "The OpenRouter generation timed out.",
    ErrorCategory.PROVIDER_UNAVAILABLE: (
        "The OpenRouter provider became unavailable during generation."
    ),
    ErrorCategory.MALFORMED_RESPONSE: "OpenRouter stopped before producing a complete response.",
    ErrorCategory.UNKNOWN: "OpenRouter returned an unclassified generation error.",
}


class OpenRouterAdapter(OpenAICompatibleAdapter):
    """Bind one exact model to one exact OpenRouter upstream provider.

    The adapter deliberately opts out of provider fallback and requires the
    selected endpoint to support every requested parameter. Product runtime
    composition additionally enforces no data collection and ZDR.
    """

    def __init__(
        self,
        *,
        base_url: str,
        capability_set: CapabilitySet,
        upstream_provider: str,
        api_key: SecretStr | None,
        reasoning_effort: str | None = None,
        require_zdr: bool = True,
        allow_data_collection: bool = False,
        adapter_version: str = "1.0",
        transport: Any = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url not in _OFFICIAL_BASE_URLS:
            raise ValueError("OpenRouter adapter requires an official API base URL")

        provider = upstream_provider.strip().casefold()
        if not _PROVIDER_SLUG.fullmatch(provider):
            raise ValueError("OpenRouter upstream provider must be one exact slug")

        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError("OpenRouter adapter requires a non-blank API key")

        self._validate_fixed_model(capability_set.target.model)
        self._upstream_provider = provider
        self._require_zdr = require_zdr
        self._allow_data_collection = allow_data_collection
        super().__init__(
            base_url=cleaned_url,
            capability_set=capability_set,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            adapter_name="openrouter-chat-completions",
            adapter_version=adapter_version,
            transport=transport,
        )

    @staticmethod
    def _validate_fixed_model(model: str) -> None:
        normalized = model.strip().casefold()
        if (
            normalized.startswith("openrouter/")
            or normalized.startswith("~")
            or (":" in normalized and not normalized.endswith(":free"))
        ):
            raise ValueError(
                "OpenRouter model must be a fixed slug, not a router or dynamic variant"
            )

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
        # OpenRouter now reports usage on every response; this legacy option is
        # deprecated there and must not influence provider compatibility.
        payload.pop("stream_options", None)
        provider_policy: dict[str, Any] = {
            "only": [self._upstream_provider],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": (
                "allow" if self._allow_data_collection else "deny"
            ),
        }
        if self._require_zdr:
            provider_policy["zdr"] = True
        payload["provider"] = provider_policy
        payload["plugins"] = [
            {"id": "web", "enabled": False},
            {"id": "response-healing", "enabled": False},
            {"id": "context-compression", "enabled": False},
        ]
        return payload

    def _new_client(self):
        client = super()._new_client()
        client.headers["X-OpenRouter-Metadata"] = "enabled"
        client.headers["X-OpenRouter-Cache"] = "false"
        return client

    def _emulated_response_format(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any]:
        return {"type": "json_object"}

    def _validate_response_payload(
        self, request: GenerationRequest, payload: dict[str, Any]
    ) -> None:
        self._raise_if_in_band_error(request, payload)
        metadata = payload.get("openrouter_metadata")
        # Partial stream chunks can omit metadata. Final evidence performs the
        # fail-closed check after the terminal chunk has been consumed.
        if metadata is None:
            return
        if not isinstance(metadata, dict):
            self._routing_problem("openrouter_invalid_metadata")

        requested = metadata.get("requested")
        if requested != request.target.model:
            self._routing_problem("openrouter_requested_model_mismatch")
        if metadata.get("strategy") != "direct":
            self._routing_problem("openrouter_dynamic_routing_detected")
        attempt_number = metadata.get("attempt")
        if (
            not isinstance(attempt_number, int)
            or isinstance(attempt_number, bool)
            or attempt_number != 1
        ):
            self._routing_problem("openrouter_fallback_attempt_detected")
        pipeline = metadata.get("pipeline")
        if pipeline is not None and pipeline != [] and pipeline != ():
            self._routing_problem("openrouter_pipeline_transformation_detected")

        selected_endpoints = self._selected_endpoints(metadata)
        if len(selected_endpoints) != 1:
            self._routing_problem("openrouter_selected_endpoint_count_invalid")
        selected = selected_endpoints[0]
        selected_provider = self._required_route_value(
            selected,
            "provider",
            missing_code="openrouter_selected_provider_missing",
        )
        selected_model = self._required_route_value(
            selected,
            "model",
            missing_code="openrouter_selected_model_missing",
        )
        if self._provider_key(selected_provider) != self._provider_key(
            self._upstream_provider
        ):
            self._routing_problem("openrouter_selected_provider_mismatch")
        if selected_model != selected_model.strip():
            self._routing_problem("openrouter_selected_model_mismatch")

        # OpenRouter documents `attempts` as optional. `attempt == 1`, the
        # selected endpoint, and the successful HTTP response still prove a
        # first-attempt direct route when detailed attempt records are absent.
        # If the optional detail is present, keep validating it fail-closed.
        if "attempts" in metadata:
            attempts = metadata["attempts"]
            if not isinstance(attempts, list):
                self._routing_problem("openrouter_successful_attempt_count_invalid")
            successful_attempts = [
                attempt
                for attempt in attempts
                if isinstance(attempt, dict)
                and isinstance(attempt.get("status"), int)
                and not isinstance(attempt.get("status"), bool)
                and attempt.get("status") == 200
            ]
            if len(successful_attempts) != 1:
                self._routing_problem("openrouter_successful_attempt_count_invalid")
            if len(attempts) != attempt_number:
                self._routing_problem("openrouter_attempt_count_inconsistent")
            successful = successful_attempts[0]
            successful_provider = self._required_route_value(
                successful,
                "provider",
                missing_code="openrouter_successful_attempt_provider_missing",
            )
            successful_model = self._required_route_value(
                successful,
                "model",
                missing_code="openrouter_successful_attempt_model_missing",
            )
            if self._provider_key(successful_provider) != self._provider_key(
                self._upstream_provider
            ):
                self._routing_problem(
                    "openrouter_successful_attempt_provider_mismatch"
                )
            if (
                successful_model != successful_model.strip()
                or successful_model != selected_model
            ):
                self._routing_problem(
                    "openrouter_successful_attempt_model_mismatch"
                )

        response_model = payload.get("model")
        if not isinstance(response_model, str) or not response_model.strip():
            self._routing_problem("openrouter_effective_model_missing")
        if (
            response_model != response_model.strip()
            or response_model not in {request.target.model, selected_model}
        ):
            self._routing_problem("openrouter_effective_model_mismatch")

    def _raise_if_in_band_error(
        self,
        request: GenerationRequest,
        payload: dict[str, Any],
    ) -> None:
        phase = (
            OperationPhase.STREAM
            if isinstance(request, StreamingGenerationRequest)
            else OperationPhase.RESPONSE
        )
        choices = payload.get("choices")
        reports_error_finish = isinstance(choices, list) and any(
            isinstance(choice, dict) and choice.get("finish_reason") == "error"
            for choice in choices
        )
        if "error" not in payload and not reports_error_finish:
            return
        if "error" not in payload:
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "openrouter_missing_error_envelope",
                "OpenRouter ended the stream with an incomplete error envelope.",
                phase,
            )
        error = payload.get("error")
        if not isinstance(error, dict):
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "openrouter_invalid_error_envelope",
                "OpenRouter returned a malformed generation error.",
                phase,
            )

        metadata = error.get("metadata")
        raw_error_type = (
            metadata.get("error_type") if isinstance(metadata, dict) else None
        )
        error_type = (
            raw_error_type.strip().casefold()
            if isinstance(raw_error_type, str) and raw_error_type.strip()
            else None
        )
        raw_status = error.get("code")
        status_code = (
            raw_status
            if isinstance(raw_status, int)
            and not isinstance(raw_status, bool)
            and 400 <= raw_status <= 599
            else None
        )
        provider_code = self._safe_provider_code(
            metadata.get("provider_code") if isinstance(metadata, dict) else None
        )

        category = _OPENROUTER_ERROR_CATEGORIES.get(error_type or "")
        if category is not None:
            code = f"openrouter_{error_type}"
        elif status_code is not None:
            category = self._http_category(status_code)
            code = f"openrouter_http_{status_code}"
        else:
            category = ErrorCategory.UNKNOWN
            code = "openrouter_in_band_error"

        raise _AdapterProblem(
            category,
            code,
            _OPENROUTER_ERROR_MESSAGES.get(
                category,
                "OpenRouter returned an unclassified generation error.",
            ),
            phase,
            status_code=status_code,
            retryable=self._retryable(category, status_code),
            rate_limit_origin=(
                RateLimitOrigin.UPSTREAM
                if category is ErrorCategory.RATE_LIMITED
                and provider_code is not None
                else None
            ),
            provider_code=(
                provider_code if category is ErrorCategory.RATE_LIMITED else None
            ),
        )

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

        safe_provider_code = provider_code or self._response_provider_code(
            response, response_body
        )
        if safe_provider_code is not None:
            resolved_origin = RateLimitOrigin.UPSTREAM
        elif response is not None and any(
            response.headers.get(name) is not None
            for name in (
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-reset",
            )
        ):
            resolved_origin = RateLimitOrigin.GATEWAY
        else:
            resolved_origin = origin or RateLimitOrigin.UNKNOWN

        return super()._rate_limit_evidence(
            category=category,
            response=response,
            response_body=response_body,
            origin=resolved_origin,
            provider_code=safe_provider_code,
        )

    @classmethod
    def _response_provider_code(
        cls, response: Any, response_body: bytes | None = None
    ) -> str | None:
        if response is None or response.status_code != 429:
            return None
        try:
            if response_body is not None:
                payload = json.loads(response_body)
            elif getattr(response, "is_stream_consumed", True) is False:
                return None
            else:
                payload = response.json()
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if not isinstance(error, dict):
            return None
        metadata = error.get("metadata")
        if not isinstance(metadata, dict):
            return None
        return cls._safe_provider_code(metadata.get("provider_code"))

    @staticmethod
    def _safe_provider_code(value: Any) -> str | None:
        if isinstance(value, int) and not isinstance(value, bool):
            value = str(value)
        if not isinstance(value, str):
            return None
        cleaned = value.strip()[:64]
        if not cleaned or _PROVIDER_ERROR_CODE.fullmatch(cleaned) is None:
            return None
        return cleaned

    def _effective_provider(self, payload: dict[str, Any]) -> str | None:
        if isinstance(payload.get("error"), dict):
            provider = payload.get("provider")
            if isinstance(provider, str) and provider.strip():
                return provider.strip()
        metadata = payload.get("openrouter_metadata")
        if not isinstance(metadata, dict):
            return None
        return self._selected_provider(metadata)

    def _effective_model(self, payload: dict[str, Any]) -> str | None:
        metadata = payload.get("openrouter_metadata")
        if isinstance(metadata, dict):
            selected = self._selected_endpoints(metadata)
            if len(selected) == 1:
                model = selected[0].get("model")
                if isinstance(model, str) and model.strip():
                    return model
        return super()._effective_model(payload)

    def _is_stream_bookkeeping_payload(
        self,
        payload: dict[str, Any],
        *,
        after_stop: bool,
    ) -> bool:
        if super()._is_stream_bookkeeping_payload(
            payload,
            after_stop=after_stop,
        ):
            return True
        if not after_stop:
            return False

        # With router metadata enabled, OpenRouter delivers routing metadata
        # and usage in the final SSE chunk before [DONE]. Its documented shape
        # keeps one choice whose delta content is empty. Accept only that
        # administrative trailer; any late content, tool/reasoning field, or
        # second finish reason remains a malformed stream.
        if not isinstance(payload.get("openrouter_metadata"), dict):
            return False
        if not isinstance(payload.get("usage"), dict):
            return False
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            return False
        choice = choices[0]
        if not isinstance(choice, dict):
            return False
        if choice.get("finish_reason") not in (None, "stop"):
            return False
        if choice.get("native_finish_reason") not in (None, "stop"):
            return False
        if choice.get("message") is not None or choice.get("text") is not None:
            return False
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            return False
        if not set(delta).issubset({"content", "role"}):
            return False
        if delta.get("content") not in (None, ""):
            return False
        return delta.get("role") in (None, "assistant")

    def _validate_final_evidence(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        provenance = evidence.provenance
        effective_provider = provenance.effective_provider.value
        if effective_provider is None:
            self._routing_problem("openrouter_route_metadata_missing")
        if self._provider_key(effective_provider) != self._provider_key(
            self._upstream_provider
        ):
            self._routing_problem("openrouter_effective_provider_mismatch")
        effective_model = provenance.effective_model.value
        if effective_model is None:
            self._routing_problem("openrouter_effective_model_missing")

    def _reported_model_matches_request(
        self, request: GenerationRequest, reported_model: str
    ) -> bool:
        # The response validator already proved the exact logical request,
        # direct pinned provider, single successful attempt, and coherence
        # between the selected endpoint and the reported physical model.
        return bool(reported_model.strip())

    def _parse_cost(self, payload: dict[str, Any]) -> CostMeasurement:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return CostMeasurement.unavailable()
        raw_cost = usage.get("cost")
        if isinstance(raw_cost, bool) or raw_cost is None:
            return CostMeasurement.unavailable()
        try:
            amount = Decimal(str(raw_cost))
        except (InvalidOperation, ValueError):
            return CostMeasurement.unavailable()
        if not amount.is_finite() or amount < 0:
            return CostMeasurement.unavailable()
        return CostMeasurement(
            status=MeasurementStatus.REPORTED,
            amount=amount,
            currency="OPENROUTER_CREDITS",
            source="openrouter response.usage.cost",
        )

    @staticmethod
    def _selected_endpoints(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        endpoints = metadata.get("endpoints")
        available = (
            endpoints.get("available") if isinstance(endpoints, dict) else None
        )
        if not isinstance(available, list):
            return []
        return [
            endpoint
            for endpoint in available
            if isinstance(endpoint, dict) and endpoint.get("selected") is True
        ]

    @classmethod
    def _selected_provider(cls, metadata: dict[str, Any]) -> str | None:
        selected = cls._selected_endpoints(metadata)
        if len(selected) != 1:
            return None
        provider = selected[0].get("provider")
        return (
            provider.strip()
            if isinstance(provider, str) and provider.strip()
            else None
        )

    @classmethod
    def _required_route_value(
        cls,
        record: dict[str, Any],
        field: str,
        *,
        missing_code: str,
    ) -> str:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            cls._routing_problem(missing_code)
        return value

    @staticmethod
    def _provider_key(value: str) -> str:
        return "-".join(re.findall(r"[a-z0-9]+", value.casefold()))

    @staticmethod
    def _routing_problem(code: str) -> NoReturn:
        raise _AdapterProblem(
            ErrorCategory.TARGET_MISMATCH,
            code,
            "OpenRouter reported a route different from the configured target.",
            OperationPhase.RESPONSE,
        )
