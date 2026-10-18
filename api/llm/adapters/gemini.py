"""Direct Gemini Generate Content adapter behind the product-owned LLM contract.

The adapter is bound to one stable model on Google's official endpoint.  It
does not use the Google SDK, remote conversation state, tools, retries,
fallbacks, or mutable model aliases.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx
from pydantic import SecretStr, ValidationError

from ..contract import (
    AdapterIdentity,
    CapabilitySet,
    CapabilitySupport,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    InvocationEvidence,
    LLMInvocationError,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceSource,
    ProvenanceValue,
    StreamEvent,
    StreamEventBuilder,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    StructuredGenerationResult,
    TokenUsage,
    utc_now,
)
from ..structure_diagnostics import build_structure_validation_evidence
from .openai_compatible import (
    OpenAICompatibleAdapter,
    _AdapterProblem,
    _CALLER_CANCELLED,
    _load_structured_json,
    _raise_caller_cancelled,
    _raise_public_error,
)


GEMINI_OFFICIAL_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_PROVIDER_LABEL = "Google Gemini"
_STABLE_MODEL = re.compile(r"\Agemini-\d+(?:\.\d+)+-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_MUTABLE_OR_PRERELEASE_MARKERS = ("latest", "preview", "experimental", "-exp")

_THINKING_LEVELS = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
}

_SAFETY_SETTINGS = (
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)

_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {"default", "minLength", "maxLength"}
)


def _normalize_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Reduce Pydantic JSON Schema to Gemini's documented REST subset.

    The official Google SDK performs an equivalent provider-boundary
    transformation.  Product validation remains the authority for every
    constraint removed here.
    """

    definitions = schema.get("$defs", {})
    if not isinstance(definitions, dict):
        raise _AdapterProblem(
            ErrorCategory.INVALID_REQUEST,
            "gemini_invalid_schema_definitions",
            "Gemini structured schema contains invalid definitions.",
            OperationPhase.VALIDATION,
        )

    def merge(
        base: dict[str, Any], siblings: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(base)
        for key, value in siblings.items():
            if key in merged and merged[key] != value:
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_conflicting_schema_composition",
                    "Gemini structured schema contains an unsupported composition.",
                    OperationPhase.VALIDATION,
                )
            merged[key] = value
        return merged

    def visit(value: Any, stack: tuple[str, ...] = ()) -> Any:
        if isinstance(value, list):
            return [visit(item, stack) for item in value]
        if not isinstance(value, dict):
            return value

        reference = value.get("$ref")
        if reference is not None:
            prefix = "#/$defs/"
            if not isinstance(reference, str) or not reference.startswith(prefix):
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_unsupported_schema_reference",
                    "Gemini structured schema contains an unsupported reference.",
                    OperationPhase.VALIDATION,
                )
            name = reference.removeprefix(prefix)
            target = definitions.get(name)
            if not name or "/" in name or not isinstance(target, dict):
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_unknown_schema_reference",
                    "Gemini structured schema contains an unresolved reference.",
                    OperationPhase.VALIDATION,
                )
            if name in stack:
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_recursive_schema_reference",
                    "Gemini structured schema contains a recursive reference.",
                    OperationPhase.VALIDATION,
                )
            resolved = visit(target, stack + (name,))
            assert isinstance(resolved, dict)
            siblings = visit(
                {key: item for key, item in value.items() if key != "$ref"},
                stack,
            )
            assert isinstance(siblings, dict)
            return merge(resolved, siblings)

        all_of = value.get("allOf")
        if all_of is not None:
            if not isinstance(all_of, list) or len(all_of) != 1:
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_unsupported_schema_composition",
                    "Gemini structured schema contains an unsupported composition.",
                    OperationPhase.VALIDATION,
                )
            base = visit(all_of[0], stack)
            if not isinstance(base, dict):
                raise _AdapterProblem(
                    ErrorCategory.INVALID_REQUEST,
                    "gemini_invalid_schema_composition",
                    "Gemini structured schema contains an invalid composition.",
                    OperationPhase.VALIDATION,
                )
            siblings = visit(
                {
                    key: item
                    for key, item in value.items()
                    if key != "allOf" and key not in _UNSUPPORTED_SCHEMA_KEYS
                },
                stack,
            )
            assert isinstance(siblings, dict)
            return merge(base, siblings)

        return {
            key: visit(item, stack)
            for key, item in value.items()
            if key != "$defs" and key not in _UNSUPPORTED_SCHEMA_KEYS
        }

    normalized = visit(schema)
    assert isinstance(normalized, dict)
    return normalized


class GeminiAdapter(OpenAICompatibleAdapter):
    """HTTP adapter for one immutable Gemini Generate Content target."""

    def __init__(
        self,
        *,
        base_url: str,
        capability_set: CapabilitySet,
        api_key: SecretStr | None,
        reasoning_effort: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url != GEMINI_OFFICIAL_BASE_URL:
            raise ValueError(
                "Gemini adapter requires the exact official HTTPS v1beta base URL."
            )
        if capability_set.target.provider.casefold() != GEMINI_PROVIDER_LABEL.casefold():
            raise ValueError(
                f"Gemini adapter target provider must be {GEMINI_PROVIDER_LABEL}."
            )
        self._validate_stable_model(capability_set.target.model)
        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError("Gemini adapter requires an explicit non-empty LLM_API_KEY.")
        if reasoning_effort is not None and reasoning_effort not in _THINKING_LEVELS:
            raise ValueError("Gemini reasoning effort is not supported by this adapter.")

        super().__init__(
            base_url=cleaned_url,
            capability_set=capability_set,
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            adapter_name="gemini-generate-content-http",
            adapter_version="1.0",
            transport=transport,
        )
        model = capability_set.target.model
        self._generate_endpoint = f"{cleaned_url}/models/{model}:generateContent"
        self._stream_endpoint = (
            f"{cleaned_url}/models/{model}:streamGenerateContent?alt=sse"
        )
        self._reported_model_version: str | None = None

    @staticmethod
    def _validate_stable_model(model: str) -> None:
        cleaned = model.strip().casefold()
        if (
            not _STABLE_MODEL.fullmatch(cleaned)
            or any(marker in cleaned for marker in _MUTABLE_OR_PRERELEASE_MARKERS)
        ):
            raise ValueError(
                "Gemini adapter requires one concrete stable model id; mutable latest, "
                "preview, and experimental targets are rejected."
            )

    def _new_client(self) -> httpx.AsyncClient:
        assert self._api_key is not None
        return httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key.get_secret_value().strip(),
            },
            timeout=None,
            follow_redirects=False,
            transport=self._transport,
        )

    def _payload(
        self,
        request: GenerationRequest,
        *,
        response_schema: dict[str, Any] | None,
        json_mode: bool,
    ) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        conversation_started = False

        for message in request.messages:
            if message.role is MessageRole.SYSTEM:
                if conversation_started:
                    raise _AdapterProblem(
                        ErrorCategory.INVALID_REQUEST,
                        "gemini_system_message_after_conversation",
                        "Gemini system instructions must precede conversation messages.",
                        OperationPhase.VALIDATION,
                    )
                system_parts.append({"text": message.content})
                continue

            conversation_started = True
            role = "model" if message.role is MessageRole.ASSISTANT else "user"
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"].append({"text": message.content})
            else:
                contents.append({"role": role, "parts": [{"text": message.content}]})

        if not contents:
            raise _AdapterProblem(
                ErrorCategory.INVALID_REQUEST,
                "gemini_missing_conversation_content",
                "Gemini requests require at least one user or assistant message.",
                OperationPhase.VALIDATION,
            )

        payload: dict[str, Any] = {
            "contents": contents,
            "store": False,
            "safetySettings": [
                {"category": category, "threshold": "BLOCK_ONLY_HIGH"}
                for category in _SAFETY_SETTINGS
            ],
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        generation_config: dict[str, Any] = {}
        if request.parameters.max_output_tokens is not None:
            generation_config["maxOutputTokens"] = request.parameters.max_output_tokens
        if request.parameters.seed is not None:
            generation_config["seed"] = request.parameters.seed
        # Gemini 3.x deprecates sampling knobs such as temperature.  The product
        # parameter remains provider-neutral, but this adapter deliberately does
        # not transmit a setting the fixed target no longer supports.
        if self._reasoning_effort is not None:
            generation_config["thinkingConfig"] = {
                "thinkingLevel": _THINKING_LEVELS[self._reasoning_effort]
            }
        if json_mode:
            # responseFormat uses the TextResponseFormat enum, unlike the
            # deprecated responseMimeType field which accepted a MIME string.
            text_format: dict[str, Any] = {"mimeType": "APPLICATION_JSON"}
            if response_schema is not None:
                text_format["schema"] = _normalize_gemini_schema(response_schema)
            generation_config["responseFormat"] = {"text": text_format}
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload

    async def _post_chat(
        self,
        request: GenerationRequest,
        *,
        response_format: dict[str, Any] | None,
    ):
        if response_format is not None:
            raise RuntimeError("Gemini structured requests use the native schema path.")
        return await self._post_gemini(
            request,
            response_schema=None,
            json_mode=False,
        )

    async def _post_gemini(
        self,
        request: GenerationRequest,
        *,
        response_schema: dict[str, Any] | None,
        json_mode: bool,
    ):
        started_at = utc_now()
        response: httpx.Response | None = None
        phase = OperationPhase.VALIDATION
        effective_model: str | None = None
        usage = TokenUsage.unavailable()
        normalized_error: NormalizedError | None = None
        try:
            self._validate_request(request, started_at)
            payload = self._payload(
                request,
                response_schema=response_schema,
                json_mode=json_mode,
            )
            phase = OperationPhase.CONNECT
            async with self._new_client() as client:
                response = await self._controlled(
                    client.post(self._generate_endpoint, json=payload), request
                )
            self._raise_gemini_http_error(response)
            phase = OperationPhase.RESPONSE
            try:
                response_payload = response.json()
            except ValueError as exc:
                raise _AdapterProblem(
                    ErrorCategory.MALFORMED_RESPONSE,
                    "gemini_invalid_response_json",
                    "Gemini returned malformed response JSON.",
                    OperationPhase.RESPONSE,
                ) from exc
            if not isinstance(response_payload, dict):
                raise _AdapterProblem(
                    ErrorCategory.MALFORMED_RESPONSE,
                    "gemini_invalid_response_payload",
                    "Gemini returned an invalid response payload.",
                    OperationPhase.RESPONSE,
                )

            self._raise_prompt_block(
                response_payload, phase=OperationPhase.RESPONSE
            )
            effective_model = self._reported_model(response_payload)
            usage = self._parse_usage(response_payload)
            content = self._response_text(response_payload, streaming=False)
            evidence = self._evidence(
                request=request,
                started_at=started_at,
                effective_model=effective_model,
                usage=usage,
            )
            self._raise_if_inactive(request, evidence, phase=OperationPhase.RESPONSE)
            self._raise_if_target_mismatch(request, evidence)
            self._validate_final_evidence(request, evidence)
            return content, evidence
        except asyncio.CancelledError:
            return _CALLER_CANCELLED
        except LLMInvocationError as exc:
            normalized_error = exc.error
        except Exception as exc:
            normalized_error = self._normalize_exception(
                request=request,
                started_at=started_at,
                phase=phase,
                exc=exc,
                response=response,
                effective_model=effective_model,
                usage=usage,
            )
        if normalized_error is not None:
            return normalized_error
        raise RuntimeError("Gemini adapter reached an invalid terminal state")

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        support = self._capability_set.support_for("structured_generation")
        schema = (
            request.response_model.model_json_schema()
            if support is CapabilitySupport.NATIVE
            else None
        )
        outcome = await self._post_gemini(
            request,
            response_schema=schema,
            json_mode=support in {CapabilitySupport.NATIVE, CapabilitySupport.EMULATED},
        )
        if outcome is _CALLER_CANCELLED:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            schema = None
            outcome = None
            _raise_caller_cancelled()
        if isinstance(outcome, NormalizedError):
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            schema = None
            _raise_public_error(outcome)

        content, evidence = outcome
        validation_error: NormalizedError | None = None
        raw_value: Any = None
        validation_stage = "json_parse"
        try:
            raw_value = _load_structured_json(content)
            validation_stage = "schema_validation"
            value = request.response_model.model_validate(raw_value)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            validation_error = self._make_error(
                request=request,
                evidence=evidence,
                category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
                code="structured_output_schema_mismatch",
                phase=OperationPhase.STRUCTURE_VALIDATION,
                safe_message="LLM output did not match the requested product schema.",
                structure_validation=build_structure_validation_evidence(
                    exc, request.response_model, validation_stage
                ),
            )
        if validation_error is not None:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            schema = None
            content = ""
            raw_value = None
            outcome = None
            _raise_public_error(validation_error)

        evidence = evidence.model_copy(
            update={
                "provenance": evidence.provenance.model_copy(
                    update={"finished_at": utc_now()}
                )
            }
        )
        post_validation_error: NormalizedError | None = None
        try:
            self._raise_if_inactive(
                request,
                evidence,
                phase=OperationPhase.STRUCTURE_VALIDATION,
            )
        except LLMInvocationError as exc:
            post_validation_error = exc.error
        if post_validation_error is not None:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            schema = None
            content = ""
            raw_value = None
            value = None
            outcome = None
            _raise_public_error(post_validation_error)
        return StructuredGenerationResult(value=value, evidence=evidence)

    async def stream_text(
        self, request: StreamingGenerationRequest
    ) -> AsyncIterator[StreamEvent]:
        builder = StreamEventBuilder()
        started_at = utc_now()
        response: httpx.Response | None = None
        client: httpx.AsyncClient | None = None
        phase = OperationPhase.VALIDATION
        effective_model: str | None = None
        usage = TokenUsage.unavailable()
        emitted_content = False
        saw_stop = False
        caller_cancelled = False

        try:
            self._validate_request(request, started_at)
            payload = self._payload(request, response_schema=None, json_mode=False)
            client = self._new_client()
            outbound = client.build_request("POST", self._stream_endpoint, json=payload)
            phase = OperationPhase.CONNECT
            response = await self._controlled(client.send(outbound, stream=True), request)
            if not 200 <= response.status_code < 300:
                await self._controlled(response.aread(), request)
            self._raise_gemini_http_error(response)
            phase = OperationPhase.STREAM
            line_iterator = response.aiter_lines().__aiter__()

            while True:
                try:
                    line = await self._controlled(line_iterator.__anext__(), request)
                except StopAsyncIteration:
                    if not saw_stop:
                        raise _AdapterProblem(
                            ErrorCategory.MALFORMED_RESPONSE,
                            "gemini_stream_ended_without_stop",
                            "Gemini stream ended without a successful finish reason.",
                            OperationPhase.STREAM,
                        )
                    evidence = self._evidence(
                        request=request,
                        started_at=started_at,
                        effective_model=effective_model,
                        usage=usage,
                    )
                    self._raise_if_target_mismatch(request, evidence)
                    self._validate_final_evidence(request, evidence)
                    await self._close_stream(response, client)
                    response = None
                    client = None
                    yield builder.complete(evidence)
                    return

                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "gemini_invalid_stream_frame",
                        "Gemini stream returned an invalid event frame.",
                        OperationPhase.STREAM,
                    )
                if saw_stop:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "gemini_stream_data_after_stop",
                        "Gemini stream returned data after its successful finish reason.",
                        OperationPhase.STREAM,
                    )

                try:
                    payload_part = json.loads(line[5:].strip())
                except json.JSONDecodeError as exc:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "gemini_invalid_stream_json",
                        "Gemini stream returned malformed JSON.",
                        OperationPhase.STREAM,
                    ) from exc
                if not isinstance(payload_part, dict):
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "gemini_invalid_stream_payload",
                        "Gemini stream returned an invalid payload.",
                        OperationPhase.STREAM,
                    )

                self._raise_prompt_block(payload_part, phase=OperationPhase.STREAM)
                reported_model = self._reported_model(payload_part, required=False)
                if reported_model is not None:
                    if effective_model is not None and reported_model != effective_model:
                        raise _AdapterProblem(
                            ErrorCategory.TARGET_MISMATCH,
                            "gemini_stream_model_version_changed",
                            "Gemini changed model version during one stream.",
                            OperationPhase.STREAM,
                        )
                    effective_model = reported_model
                parsed_usage = self._parse_usage(payload_part)
                if parsed_usage.status is not MeasurementStatus.UNAVAILABLE:
                    usage = parsed_usage

                chunk_text, chunk_stopped = self._stream_chunk(payload_part)
                if chunk_text:
                    emitted_content = True
                    yield builder.delta(chunk_text)
                if chunk_stopped:
                    saw_stop = True

        except asyncio.CancelledError:
            caller_cancelled = True
        except Exception as exc:
            error = self._normalize_exception(
                request=request,
                started_at=started_at,
                phase=phase,
                exc=exc,
                response=response,
                effective_model=effective_model,
                usage=usage,
                partial_output=emitted_content,
            )
            if error.category is ErrorCategory.CANCELLED:
                kind = StreamEventKind.CANCELLED
            elif error.category is ErrorCategory.TIMEOUT:
                kind = StreamEventKind.TIMED_OUT
            else:
                kind = StreamEventKind.FAILED
            await self._close_stream(response, client)
            response = None
            client = None
            yield builder.fail(kind, error, partial_output=emitted_content)
        finally:
            await self._close_stream(response, client)
        if caller_cancelled:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            response = None
            client = None
            payload = None
            outbound = None
            line_iterator = None
            line = None
            payload_part = None
            _raise_caller_cancelled()

    def _response_text(self, payload: dict[str, Any], *, streaming: bool) -> str:
        self._raise_prompt_block(
            payload,
            phase=OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
        )
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1:
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_invalid_candidate_count",
                "Gemini did not return exactly one candidate.",
                OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
            )
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_invalid_candidate",
                "Gemini returned an invalid candidate.",
                OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
            )
        self._require_successful_finish_reason(
            candidate.get("finishReason"),
            phase=OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
        )
        return self._candidate_text(candidate, streaming=streaming)

    def _stream_chunk(self, payload: dict[str, Any]) -> tuple[str, bool]:
        self._raise_prompt_block(payload, phase=OperationPhase.STREAM)
        candidates = payload.get("candidates")
        if candidates is None or candidates == []:
            if "usageMetadata" in payload:
                return "", False
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_stream_missing_candidate",
                "Gemini stream did not contain a candidate.",
                OperationPhase.STREAM,
            )
        if not isinstance(candidates, list) or len(candidates) != 1:
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_invalid_candidate_count",
                "Gemini did not return exactly one candidate.",
                OperationPhase.STREAM,
            )
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_invalid_candidate",
                "Gemini returned an invalid candidate.",
                OperationPhase.STREAM,
            )
        finish_reason = candidate.get("finishReason")
        stopped = finish_reason == "STOP"
        if finish_reason not in {None, "", "FINISH_REASON_UNSPECIFIED", "STOP"}:
            self._require_successful_finish_reason(
                finish_reason, phase=OperationPhase.STREAM
            )
        text = self._candidate_text(candidate, streaming=True, allow_empty=True)
        return text, stopped

    @staticmethod
    def _candidate_text(
        candidate: dict[str, Any], *, streaming: bool, allow_empty: bool = False
    ) -> str:
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if parts is None and allow_empty:
            return ""
        if not isinstance(parts, list):
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_missing_content_parts",
                "Gemini response did not contain content parts.",
                OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
            )

        text_parts: list[str] = []
        for part in parts:
            if not isinstance(part, dict):
                raise _AdapterProblem(
                    ErrorCategory.MALFORMED_RESPONSE,
                    "gemini_invalid_content_part",
                    "Gemini returned an invalid content part.",
                    OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
                )
            if "functionCall" in part or "executableCode" in part:
                raise _AdapterProblem(
                    ErrorCategory.UNSUPPORTED_CAPABILITY,
                    "gemini_unexpected_tool_or_code",
                    "Gemini returned an unsupported tool or code request.",
                    OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
                )
            if part.get("thought") is True:
                continue
            text = part.get("text")
            if isinstance(text, str):
                text_parts.append(text)
                continue
            if part:
                raise _AdapterProblem(
                    ErrorCategory.UNSUPPORTED_CAPABILITY,
                    "gemini_non_text_response_part",
                    "Gemini returned a non-text response part.",
                    OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
                )
        combined = "".join(text_parts)
        if not combined.strip() and not allow_empty:
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_empty_text_response",
                "Gemini response did not contain non-empty text.",
                OperationPhase.STREAM if streaming else OperationPhase.RESPONSE,
            )
        return combined

    @staticmethod
    def _raise_prompt_block(
        payload: dict[str, Any], *, phase: OperationPhase
    ) -> None:
        feedback = payload.get("promptFeedback")
        if not isinstance(feedback, dict):
            return
        reason = feedback.get("blockReason")
        if reason in {None, "", "BLOCK_REASON_UNSPECIFIED"}:
            return
        raise _AdapterProblem(
            ErrorCategory.CONTENT_REJECTED,
            "gemini_prompt_blocked",
            "Gemini rejected the prompt under its content policy.",
            phase,
        )

    @staticmethod
    def _require_successful_finish_reason(
        finish_reason: Any,
        *,
        phase: OperationPhase,
    ) -> None:
        if finish_reason == "STOP":
            return
        if finish_reason == "MAX_TOKENS":
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "gemini_generation_truncated",
                "Gemini generation stopped before producing a complete response.",
                phase,
            )
        if finish_reason in {
            "SAFETY",
            "RECITATION",
            "LANGUAGE",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "SPII",
            "IMAGE_SAFETY",
        }:
            raise _AdapterProblem(
                ErrorCategory.CONTENT_REJECTED,
                f"gemini_generation_{str(finish_reason).casefold()}",
                "Gemini rejected the generated content under its content policy.",
                phase,
            )
        if finish_reason in {
            "MALFORMED_FUNCTION_CALL",
            "UNEXPECTED_TOOL_CALL",
            "TOO_MANY_TOOL_CALLS",
        }:
            raise _AdapterProblem(
                ErrorCategory.UNSUPPORTED_CAPABILITY,
                "gemini_unexpected_tool_call",
                "Gemini returned an unsupported tool call.",
                phase,
            )
        raise _AdapterProblem(
            ErrorCategory.MALFORMED_RESPONSE,
            "gemini_missing_or_unknown_finish_reason",
            "Gemini did not report a successful completion reason.",
            phase,
        )

    @staticmethod
    def _reported_model(
        payload: dict[str, Any], *, required: bool = True
    ) -> str | None:
        value = payload.get("modelVersion")
        if isinstance(value, str) and value.strip():
            return value.strip().removeprefix("models/")
        if required:
            raise _AdapterProblem(
                ErrorCategory.TARGET_MISMATCH,
                "gemini_missing_model_version",
                "Gemini did not report the effective model version.",
                OperationPhase.RESPONSE,
            )
        return None

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
                adapter=AdapterIdentity(
                    name="gemini-generate-content-http", version="1.0"
                ),
                effective_provider=ProvenanceValue.observed(GEMINI_PROVIDER_LABEL),
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
            or provenance.effective_provider.value != GEMINI_PROVIDER_LABEL
            or provenance.effective_model.source is not ProvenanceSource.REPORTED
            or provenance.effective_model.value is None
        ):
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="gemini_unverified_target_provenance",
                    phase=OperationPhase.RESPONSE,
                    safe_message="Gemini target provenance could not be verified.",
                )
            )
        reported_model = provenance.effective_model.value
        assert reported_model is not None
        if self._reported_model_version is None:
            self._reported_model_version = reported_model
        elif self._reported_model_version != reported_model:
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="gemini_model_version_changed_between_invocations",
                    phase=OperationPhase.RESPONSE,
                    safe_message="Gemini changed model version for the bound target.",
                )
            )

    def _raise_if_target_mismatch(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        reported = evidence.provenance.effective_model.value
        requested = request.target.model
        compatible = reported == requested or (
            reported is not None
            and re.fullmatch(rf"{re.escape(requested)}-\d{{3}}", reported) is not None
        )
        if not compatible:
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="gemini_reported_model_mismatch",
                    phase=OperationPhase.RESPONSE,
                    safe_message="Gemini reported a different model than requested.",
                )
            )

    def _parse_usage(self, payload: dict[str, Any]) -> TokenUsage:
        usage = payload.get("usageMetadata")
        if not isinstance(usage, dict):
            return TokenUsage.unavailable()

        def count(name: str) -> int | None:
            value = usage.get(name)
            return (
                value
                if isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
                else None
            )

        input_tokens = count("promptTokenCount")
        output_tokens = count("candidatesTokenCount")
        total_tokens = count("totalTokenCount")
        if input_tokens is None and output_tokens is None and total_tokens is None:
            return TokenUsage.unavailable()
        return TokenUsage(
            status=MeasurementStatus.REPORTED,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            source="Gemini GenerateContentResponse.usageMetadata",
        )

    @staticmethod
    def _raise_gemini_http_error(response: httpx.Response) -> None:
        if 200 <= response.status_code < 300:
            return
        provider_status: str | None = None
        reasons: set[str] = set()
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            error = payload["error"]
            if isinstance(error.get("status"), str):
                provider_status = error["status"]
            details = error.get("details")
            if isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict) and isinstance(detail.get("reason"), str):
                        reasons.add(detail["reason"])

        status = response.status_code
        if reasons & {"API_KEY_INVALID", "API_KEY_EXPIRED"}:
            category = ErrorCategory.AUTHENTICATION_FAILED
        elif provider_status == "UNAUTHENTICATED" or status == 401:
            category = ErrorCategory.AUTHENTICATION_FAILED
        elif provider_status == "PERMISSION_DENIED" or status == 403:
            category = ErrorCategory.PERMISSION_DENIED
        elif provider_status == "RESOURCE_EXHAUSTED" or status == 429:
            category = ErrorCategory.RATE_LIMITED
        elif provider_status == "DEADLINE_EXCEEDED" or status in {408, 504}:
            category = ErrorCategory.TIMEOUT
        elif provider_status == "NOT_FOUND" or status == 404:
            category = ErrorCategory.MODEL_UNAVAILABLE
        elif provider_status in {"UNAVAILABLE", "INTERNAL"} or status >= 500:
            category = ErrorCategory.PROVIDER_UNAVAILABLE
        else:
            category = ErrorCategory.INVALID_REQUEST

        messages = {
            ErrorCategory.AUTHENTICATION_FAILED: "Gemini rejected authentication.",
            ErrorCategory.PERMISSION_DENIED: "Gemini denied this operation.",
            ErrorCategory.RATE_LIMITED: "Gemini rate-limited the operation.",
            ErrorCategory.TIMEOUT: "Gemini operation exceeded its deadline.",
            ErrorCategory.MODEL_UNAVAILABLE: "Requested Gemini model is unavailable.",
            ErrorCategory.PROVIDER_UNAVAILABLE: "Gemini is currently unavailable.",
            ErrorCategory.INVALID_REQUEST: "Gemini rejected the request.",
        }
        code = (
            f"gemini_{provider_status.casefold()}"
            if provider_status
            else f"gemini_http_{status}"
        )
        raise _AdapterProblem(
            category,
            code,
            messages[category],
            OperationPhase.CONNECT,
        )

    @staticmethod
    def _http_category(status: int) -> ErrorCategory:
        if status == 504:
            return ErrorCategory.TIMEOUT
        return OpenAICompatibleAdapter._http_category(status)
