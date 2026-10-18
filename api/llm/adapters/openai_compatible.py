"""Provider-neutral adapter for an explicitly configured OpenAI-compatible API.

The adapter is bound to one target and one endpoint by its composition root. It
never selects a provider, model, route, retry, repair, or fallback.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, AsyncIterator
from contextlib import suppress
from datetime import datetime
from typing import Any, NoReturn, TypeVar

import httpx
from pydantic import SecretStr, ValidationError

from ..contract import (
    AdapterIdentity,
    CapabilitySet,
    CapabilitySupport,
    ConnectionTestRequest,
    ConnectionTestResult,
    CostMeasurement,
    ErrorCategory,
    GenerationParameters,
    GenerationRequest,
    InvocationEvidence,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceValue,
    RateLimitEvidence,
    RateLimitOrigin,
    StreamEvent,
    StreamEventBuilder,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    StructuredGenerationResult,
    StructureValidationEvidence,
    SYNTHETIC_PROBE_EXPECTED,
    SYNTHETIC_PROBE_MAX_OUTPUT_TOKENS,
    SYNTHETIC_PROBE_PROMPT,
    SYNTHETIC_PROBE_VERSION,
    TextGenerationResult,
    TokenUsage,
    seconds_until,
    utc_now,
)
from ..structure_diagnostics import build_structure_validation_evidence


_T = TypeVar("_T")

_FULL_JSON_FENCE = re.compile(
    r"\A```(?:json)?\s*(?P<body>.*?)\s*```\Z",
    flags=re.IGNORECASE | re.DOTALL,
)
_MAX_ERROR_RESPONSE_BYTES = 64 * 1024


def _load_structured_json(content: str) -> Any:
    """Parse plain JSON or one JSON document occupying a complete code fence."""

    stripped = content.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = _FULL_JSON_FENCE.fullmatch(stripped)
        if match is None:
            raise
        return json.loads(match.group("body"))


class _Cancelled(Exception):
    pass


class _DeadlineExceeded(Exception):
    pass


class _CallerCancelledOutcome:
    pass


_CALLER_CANCELLED = _CallerCancelledOutcome()


class _AdapterProblem(Exception):
    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        phase: OperationPhase,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
        rate_limit_origin: RateLimitOrigin | None = None,
        provider_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.phase = phase
        self.status_code = status_code
        self.retryable = retryable
        self.rate_limit_origin = rate_limit_origin
        self.provider_code = provider_code


def _raise_public_error(error: NormalizedError) -> NoReturn:
    """Raise only the product-owned error from a frame with safe locals."""

    raise LLMInvocationError(error)


def _raise_caller_cancelled() -> NoReturn:
    """Recreate cancellation without retaining transport or request frames."""

    raise asyncio.CancelledError


class OpenAICompatibleAdapter:
    """HTTP adapter for one caller-supplied endpoint and immutable target."""

    def __init__(
        self,
        *,
        base_url: str,
        capability_set: CapabilitySet,
        api_key: SecretStr | None = None,
        reasoning_effort: str | None = None,
        adapter_name: str = "openai-compatible-http",
        adapter_version: str = "1.0",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if not cleaned_url:
            raise ValueError("base_url must not be blank")
        self._endpoint = f"{cleaned_url}/chat/completions"
        self._capability_set = capability_set
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._transport = transport
        self._identity = AdapterIdentity(
            name=adapter_name, version=adapter_version
        )

    def capabilities(self, target: LLMTarget) -> CapabilitySet:
        if target == self._capability_set.target:
            return self._capability_set
        return CapabilitySet(target=target, descriptors=())

    async def generate_text(self, request: GenerationRequest) -> TextGenerationResult:
        outcome = await self._post_chat(request, response_format=None)
        if outcome is _CALLER_CANCELLED:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            outcome = None
            _raise_caller_cancelled()
        if isinstance(outcome, NormalizedError):
            # Public traceback frames must not retain the bound adapter (and its
            # credential) or the request (and its prompt).
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            _raise_public_error(outcome)
        content, evidence = outcome
        return TextGenerationResult(content=content, evidence=evidence)

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        support = self._capability_set.support_for("structured_generation")
        response_format: dict[str, Any] | None = None
        if support is CapabilitySupport.NATIVE:
            response_format = self._native_response_format(request)
        elif support is CapabilitySupport.EMULATED:
            response_format = self._emulated_response_format(request)

        outcome = await self._post_chat(
            request, response_format=response_format
        )
        if outcome is _CALLER_CANCELLED:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            response_format = None
            outcome = None
            _raise_caller_cancelled()
        if isinstance(outcome, NormalizedError):
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            response_format = None
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
        # Raise outside the handler so the raw parser/validation exception is not
        # retained in either __cause__ or __context__ across the product boundary.
        if validation_error is not None:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            response_format = None
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
            response_format = None
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
        effective_provider: str | None = None
        effective_model: str | None = None
        usage = TokenUsage.unavailable()
        cost = CostMeasurement.unavailable()
        error_response_body: bytes | None = None
        emitted_content = False
        saw_stop = False
        caller_cancelled = False

        try:
            self._validate_request(request, started_at)
            payload = self._payload(request, stream=True, response_format=None)
            client = self._new_client()
            outbound = client.build_request("POST", self._endpoint, json=payload)
            phase = OperationPhase.CONNECT
            response = await self._controlled(
                client.send(outbound, stream=True), request
            )
            if response.status_code == 429:
                # ``send(..., stream=True)`` leaves error bodies unread. Capture
                # only a bounded envelope, under the same cancellation/deadline
                # controls, so provider-specific diagnostics cannot replace the
                # original HTTP status or allocate an unbounded response body.
                error_response_body = await self._read_bounded_error_body(
                    response, request
                )
            response.raise_for_status()
            phase = OperationPhase.STREAM
            line_iterator = response.aiter_lines().__aiter__()

            while True:
                try:
                    line = await self._controlled(line_iterator.__anext__(), request)
                except StopAsyncIteration as exc:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "stream_ended_without_terminal",
                        "LLM stream ended without its terminal marker.",
                        OperationPhase.STREAM,
                    ) from exc

                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "invalid_stream_frame",
                        "LLM stream returned an invalid event frame.",
                        OperationPhase.STREAM,
                    )

                data_text = line[5:].strip()
                if data_text == "[DONE]":
                    if not saw_stop:
                        raise _AdapterProblem(
                            ErrorCategory.MALFORMED_RESPONSE,
                            "stream_missing_stop_reason",
                            "LLM stream ended without a successful finish reason.",
                            OperationPhase.STREAM,
                        )
                    evidence = self._evidence(
                        request=request,
                        started_at=started_at,
                        effective_provider=effective_provider,
                        effective_model=effective_model,
                        usage=usage,
                        cost=cost,
                    )
                    self._validate_final_evidence(request, evidence)
                    self._raise_if_target_mismatch(request, evidence)
                    await self._close_stream(response, client)
                    response = None
                    client = None
                    yield builder.complete(evidence)
                    return

                try:
                    payload_part = json.loads(data_text)
                except json.JSONDecodeError as exc:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "invalid_stream_json",
                        "LLM stream returned malformed JSON.",
                        OperationPhase.STREAM,
                    ) from exc

                if not isinstance(payload_part, dict):
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "invalid_stream_payload",
                        "LLM stream returned an invalid payload.",
                        OperationPhase.STREAM,
                    )
                reported_model = self._effective_model(payload_part)
                if reported_model:
                    effective_model = reported_model
                reported_provider = self._effective_provider(payload_part)
                if reported_provider:
                    effective_provider = reported_provider
                self._validate_response_payload(request, payload_part)
                parsed_usage = self._parse_usage(payload_part)
                if parsed_usage.status is not MeasurementStatus.UNAVAILABLE:
                    usage = parsed_usage
                parsed_cost = self._parse_cost(payload_part)
                if parsed_cost.status is not MeasurementStatus.UNAVAILABLE:
                    cost = parsed_cost

                choices = payload_part.get("choices")
                if self._is_stream_bookkeeping_payload(
                    payload_part,
                    after_stop=saw_stop,
                ):
                    continue
                if saw_stop:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "stream_data_after_stop",
                        "LLM stream returned data after its successful finish reason.",
                        OperationPhase.STREAM,
                    )
                try:
                    choice = choices[0]
                    delta = choice["delta"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "missing_stream_delta",
                        "LLM stream response did not contain a valid delta.",
                        OperationPhase.STREAM,
                    ) from exc

                finish_reason = choice.get("finish_reason")
                if finish_reason is not None:
                    self._require_successful_finish_reason(
                        finish_reason,
                        phase=OperationPhase.STREAM,
                    )
                    saw_stop = True

                content = delta.get("content")
                if content is None:
                    continue
                if not isinstance(content, str):
                    raise _AdapterProblem(
                        ErrorCategory.MALFORMED_RESPONSE,
                        "invalid_stream_delta",
                        "LLM stream returned a non-text delta.",
                        OperationPhase.STREAM,
                    )
                if content:
                    emitted_content = True
                    yield builder.delta(content)

        except asyncio.CancelledError:
            caller_cancelled = True
        except Exception as exc:
            error = self._normalize_exception(
                request=request,
                started_at=started_at,
                phase=phase,
                exc=exc,
                response=response,
                response_body=error_response_body,
                effective_provider=effective_provider,
                effective_model=effective_model,
                usage=usage,
                cost=cost,
                partial_output=emitted_content,
            )
            error_response_body = None
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
            # Discard every local that can retain the outbound prompt, headers,
            # response body, or the adapter credential before recreating the
            # control-flow exception from a safe frame.
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            response = None
            client = None
            error_response_body = None
            payload = None
            outbound = None
            line_iterator = None
            line = None
            data_text = None
            payload_part = None
            choices = None
            choice = None
            delta = None
            content = None
            _raise_caller_cancelled()

    async def test_connection(
        self, request: ConnectionTestRequest
    ) -> ConnectionTestResult:
        generation_request = GenerationRequest(
            invocation_id=request.invocation_id,
            operation=SYNTHETIC_PROBE_VERSION,
            target=request.target,
            messages=(
                LLMMessage(role=MessageRole.USER, content=SYNTHETIC_PROBE_PROMPT),
            ),
            parameters=GenerationParameters(
                max_output_tokens=SYNTHETIC_PROBE_MAX_OUTPUT_TOKENS,
            ),
            deadline=request.deadline,
            cancellation=request.cancellation,
        )
        caller_cancelled = False
        try:
            result = await self.generate_text(generation_request)
            self._raise_if_inactive(
                generation_request,
                result.evidence,
                phase=OperationPhase.RESPONSE,
            )
            if result.content.strip() != SYNTHETIC_PROBE_EXPECTED:
                error = self._make_error(
                    request=generation_request,
                    evidence=result.evidence,
                    category=ErrorCategory.MALFORMED_RESPONSE,
                    code="synthetic_probe_unexpected_response",
                    phase=OperationPhase.RESPONSE,
                    safe_message="LLM target returned an unexpected synthetic probe response.",
                )
                return ConnectionTestResult(
                    probe_version=SYNTHETIC_PROBE_VERSION,
                    success=False,
                    target=request.target,
                    evidence=result.evidence,
                    error=error,
                )
            return ConnectionTestResult(
                probe_version=SYNTHETIC_PROBE_VERSION,
                success=True,
                target=request.target,
                evidence=result.evidence,
            )
        except asyncio.CancelledError:
            caller_cancelled = True
        except LLMInvocationError as exc:
            return ConnectionTestResult(
                probe_version=SYNTHETIC_PROBE_VERSION,
                success=False,
                target=request.target,
                evidence=exc.error.evidence,
                error=exc.error,
            )
        if caller_cancelled:
            self = None  # type: ignore[assignment]
            request = None  # type: ignore[assignment]
            generation_request = None
            _raise_caller_cancelled()
        raise RuntimeError("LLM connection test reached an invalid terminal state")

    async def _post_chat(
        self,
        request: GenerationRequest,
        *,
        response_format: dict[str, Any] | None,
    ) -> tuple[str, InvocationEvidence] | NormalizedError | _CallerCancelledOutcome:
        started_at = utc_now()
        response: httpx.Response | None = None
        phase = OperationPhase.VALIDATION
        normalized_error: NormalizedError | None = None
        effective_provider: str | None = None
        effective_model: str | None = None
        try:
            self._validate_request(request, started_at)
            payload = self._payload(
                request, stream=False, response_format=response_format
            )
            phase = OperationPhase.CONNECT
            async with self._new_client() as client:
                response = await self._controlled(
                    client.post(self._endpoint, json=payload), request
                )
            response.raise_for_status()
            phase = OperationPhase.RESPONSE
            try:
                response_payload = response.json()
                if not isinstance(response_payload, dict):
                    raise TypeError("completion response must be an object")
                effective_provider = self._effective_provider(response_payload)
                effective_model = self._effective_model(response_payload)
                self._validate_response_payload(request, response_payload)
                choice = response_payload["choices"][0]
                self._require_successful_finish_reason(
                    choice.get("finish_reason"),
                    phase=OperationPhase.RESPONSE,
                )
                content = choice["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise _AdapterProblem(
                    ErrorCategory.MALFORMED_RESPONSE,
                    "missing_message_content",
                    "LLM response did not contain message content.",
                    OperationPhase.RESPONSE,
                ) from exc
            if not isinstance(content, str) or not content.strip():
                raise _AdapterProblem(
                    ErrorCategory.MALFORMED_RESPONSE,
                    "invalid_message_content",
                    "LLM response did not contain non-empty text.",
                    OperationPhase.RESPONSE,
                )
            evidence = self._evidence(
                request=request,
                started_at=started_at,
                effective_provider=effective_provider,
                effective_model=effective_model,
                usage=self._parse_usage(response_payload),
                cost=self._parse_cost(response_payload),
            )
            self._raise_if_inactive(
                request,
                evidence,
                phase=OperationPhase.RESPONSE,
            )
            self._validate_final_evidence(request, evidence)
            self._raise_if_target_mismatch(request, evidence)
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
                effective_provider=effective_provider,
                effective_model=effective_model,
            )
        # Return a safe value instead of raising here: a traceback originating in
        # this frame would retain request/response/payload and adapter credentials.
        if normalized_error is not None:
            return normalized_error
        raise RuntimeError("LLM adapter reached an invalid terminal state")

    @staticmethod
    def _require_successful_finish_reason(
        finish_reason: Any,
        *,
        phase: OperationPhase,
    ) -> None:
        if finish_reason == "stop":
            return
        if finish_reason == "content_filter":
            raise _AdapterProblem(
                ErrorCategory.CONTENT_REJECTED,
                "generation_content_filtered",
                "LLM generation was rejected by the target's content policy.",
                phase,
            )
        if finish_reason == "length":
            raise _AdapterProblem(
                ErrorCategory.MALFORMED_RESPONSE,
                "generation_truncated",
                "LLM generation stopped before producing a complete response.",
                phase,
            )
        if finish_reason in {"tool_calls", "function_call"}:
            raise _AdapterProblem(
                ErrorCategory.UNSUPPORTED_CAPABILITY,
                "unexpected_tool_call",
                "LLM target requested an unsupported tool call.",
                phase,
            )
        if finish_reason is None:
            code = "missing_finish_reason"
        else:
            code = "unknown_finish_reason"
        raise _AdapterProblem(
            ErrorCategory.MALFORMED_RESPONSE,
            code,
            "LLM target did not report a successful completion reason.",
            phase,
        )

    def _validate_request(
        self, request: GenerationRequest, started_at: datetime
    ) -> None:
        if request.target != self._capability_set.target:
            evidence = self._evidence(request=request, started_at=started_at)
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.CONFIGURATION_INVALID,
                    code="adapter_target_not_bound",
                    phase=OperationPhase.VALIDATION,
                    safe_message="The adapter is not bound to the requested LLM target.",
                )
            )
        if request.cancellation.is_cancelled:
            raise _Cancelled()
        if seconds_until(request.deadline) <= 0:
            raise _DeadlineExceeded()
        unmet = self._capability_set.unmet(request.required_capabilities)
        if unmet:
            name, support = unmet[0]
            evidence = self._evidence(request=request, started_at=started_at)
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.UNSUPPORTED_CAPABILITY,
                    code=f"capability_{name}_{support.value}",
                    phase=OperationPhase.VALIDATION,
                    safe_message=f"Required LLM capability '{name}' is not available.",
                )
            )

    def _payload(
        self,
        request: GenerationRequest,
        *,
        stream: bool,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.target.model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "stream": stream,
        }
        if request.parameters.temperature is not None:
            payload["temperature"] = request.parameters.temperature
        if request.parameters.max_output_tokens is not None:
            payload["max_tokens"] = request.parameters.max_output_tokens
        if request.parameters.seed is not None:
            payload["seed"] = request.parameters.seed
        if self._reasoning_effort is not None:
            payload["reasoning_effort"] = self._reasoning_effort
        if response_format is not None:
            payload["response_format"] = response_format
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _emulated_response_format(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any] | None:
        """Allow a concrete adapter to request JSON mode for local validation."""

        return None

    def _native_response_format(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any]:
        """Build the default OpenAI-compatible strict JSON Schema envelope.

        Concrete providers may normalize the schema at this boundary when their
        documented strict subset differs. Product-side Pydantic validation
        remains authoritative after every response.
        """

        return {
            "type": "json_schema",
            "json_schema": {
                "name": request.response_model.__name__,
                "strict": True,
                "schema": request.response_model.model_json_schema(),
            },
        }

    def _validate_response_payload(
        self, request: GenerationRequest, payload: dict[str, Any]
    ) -> None:
        """Validate provider-specific routing evidence when an adapter has it."""

    def _effective_provider(self, payload: dict[str, Any]) -> str | None:
        """Return provider-reported route identity when the protocol exposes it."""

        return None

    def _effective_model(self, payload: dict[str, Any]) -> str | None:
        """Return the model identity reported by the protocol response."""

        value = payload.get("model")
        return value if isinstance(value, str) and value.strip() else None

    def _validate_final_evidence(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        """Allow concrete protocols to require final routing provenance."""

    def _is_stream_bookkeeping_payload(
        self,
        payload: dict[str, Any],
        *,
        after_stop: bool,
    ) -> bool:
        """Recognize non-generative stream accounting frames.

        The generic OpenAI-compatible shape uses an empty choices list for its
        final usage frame. Concrete protocols may extend this narrowly when
        they document a different administrative trailer shape.
        """

        del after_stop
        return payload.get("choices") == [] and "usage" in payload

    def _parse_cost(self, payload: dict[str, Any]) -> CostMeasurement:
        """Keep unknown cost unknown unless a concrete protocol reports it."""

        return CostMeasurement.unavailable()

    def _new_client(self) -> httpx.AsyncClient:
        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            secret = self._api_key.get_secret_value().strip()
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        return httpx.AsyncClient(
            headers=headers,
            timeout=None,
            transport=self._transport,
        )

    async def _read_bounded_error_body(
        self,
        response: httpx.Response,
        request: GenerationRequest,
    ) -> bytes | None:
        """Best-effort buffering for a small error envelope from a streamed call."""

        declared_length = response.headers.get("content-length")
        if declared_length is not None:
            try:
                parsed_length = int(declared_length)
            except ValueError:
                return None
            if parsed_length < 0 or parsed_length > _MAX_ERROR_RESPONSE_BYTES:
                return None

        chunks: list[bytes] = []
        total = 0
        iterator = response.aiter_bytes(chunk_size=8192).__aiter__()
        try:
            while True:
                try:
                    chunk = await self._controlled(iterator.__anext__(), request)
                except StopAsyncIteration:
                    break
                total += len(chunk)
                if total > _MAX_ERROR_RESPONSE_BYTES:
                    return None
                chunks.append(chunk)
        except (httpx.HTTPError, OSError, RuntimeError, ValueError):
            # The HTTP status and allowlisted headers remain authoritative even
            # when the optional provider error envelope cannot be consumed.
            return None
        return b"".join(chunks)

    async def _controlled(
        self,
        awaitable: Awaitable[_T],
        request: GenerationRequest,
    ) -> _T:
        if request.cancellation.is_cancelled:
            if hasattr(awaitable, "close"):
                awaitable.close()  # type: ignore[attr-defined]
            raise _Cancelled()
        remaining = seconds_until(request.deadline)
        if remaining <= 0:
            if hasattr(awaitable, "close"):
                awaitable.close()  # type: ignore[attr-defined]
            raise _DeadlineExceeded()

        operation_task = asyncio.ensure_future(awaitable)
        cancellation_task = asyncio.create_task(request.cancellation.wait())
        try:
            done, _ = await asyncio.wait(
                {operation_task, cancellation_task},
                timeout=remaining,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_task in done:
                operation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await operation_task
                raise _Cancelled()
            if operation_task not in done:
                operation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await operation_task
                raise _DeadlineExceeded()
            return await operation_task
        finally:
            # Cancellation of the coroutine that owns this adapter call must
            # also stop the in-flight transport.  Token/deadline paths already
            # do this explicitly; this branch covers task-level cancellation
            # such as a disconnected request handler.
            if not operation_task.done():
                operation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await operation_task
            cancellation_task.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation_task

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
                effective_provider=(
                    ProvenanceValue.reported(effective_provider)
                    if effective_provider
                    else ProvenanceValue.unknown()
                ),
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

    def _parse_usage(self, payload: dict[str, Any]) -> TokenUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return TokenUsage.unavailable()

        def count(name: str) -> int | None:
            value = usage.get(name)
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

        input_tokens = count("prompt_tokens")
        output_tokens = count("completion_tokens")
        total_tokens = count("total_tokens")
        if input_tokens is None and output_tokens is None and total_tokens is None:
            return TokenUsage.unavailable()
        return TokenUsage(
            status=MeasurementStatus.REPORTED,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            source="openai-compatible response.usage",
        )

    def _raise_if_target_mismatch(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        effective_model = evidence.provenance.effective_model
        if effective_model.value and not self._reported_model_matches_request(
            request, effective_model.value
        ):
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="reported_model_mismatch",
                    phase=OperationPhase.RESPONSE,
                    safe_message="LLM target reported a different model than requested.",
                )
            )

    def _reported_model_matches_request(
        self, request: GenerationRequest, reported_model: str
    ) -> bool:
        """Keep generic OpenAI-compatible targets exact unless overridden."""

        return reported_model == request.target.model

    def _raise_if_inactive(
        self,
        request: GenerationRequest,
        evidence: InvocationEvidence,
        *,
        phase: OperationPhase,
    ) -> None:
        if request.cancellation.is_cancelled:
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.CANCELLED,
                    code="operation_cancelled",
                    phase=OperationPhase.CANCELLATION,
                    safe_message="LLM operation was cancelled.",
                )
            )
        if seconds_until(request.deadline) <= 0:
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TIMEOUT,
                    code="operation_deadline_exceeded",
                    phase=phase,
                    safe_message="LLM operation exceeded its deadline.",
                )
            )

    def _make_error(
        self,
        *,
        request: GenerationRequest,
        evidence: InvocationEvidence,
        category: ErrorCategory,
        code: str,
        phase: OperationPhase,
        safe_message: str,
        partial_output: bool = False,
        external_id: str | None = None,
        status_code: int | None = None,
        retryable: bool | None = None,
        retry_after_seconds: float | None = None,
        rate_limit: RateLimitEvidence | None = None,
        structure_validation: StructureValidationEvidence | None = None,
    ) -> NormalizedError:
        return NormalizedError(
            category=category,
            code=code,
            phase=phase,
            invocation_id=request.invocation_id,
            target=request.target,
            safe_message=safe_message,
            evidence=evidence,
            partial_output=partial_output,
            external_id=external_id,
            status_code=status_code,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
            rate_limit=rate_limit,
            structure_validation=structure_validation,
        )

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
        if isinstance(exc, LLMInvocationError):
            error = exc.error
            if partial_output and not error.partial_output:
                return error.model_copy(update={"partial_output": True})
            return error

        category = ErrorCategory.ADAPTER_FAILURE
        code = "adapter_failure"
        safe_message = "LLM adapter failed to complete the operation."
        error_phase = phase
        problem_status_code: int | None = None
        problem_retryable: bool | None = None
        problem_rate_limit_origin: RateLimitOrigin | None = None
        problem_provider_code: str | None = None

        if isinstance(exc, _Cancelled):
            category = ErrorCategory.CANCELLED
            code = "operation_cancelled"
            safe_message = "LLM operation was cancelled."
            error_phase = OperationPhase.CANCELLATION
        elif isinstance(exc, (_DeadlineExceeded, httpx.TimeoutException)):
            category = ErrorCategory.TIMEOUT
            code = "operation_deadline_exceeded"
            safe_message = "LLM operation exceeded its deadline."
        elif isinstance(exc, _AdapterProblem):
            category = exc.category
            code = exc.code
            safe_message = exc.message
            error_phase = exc.phase
            problem_status_code = exc.status_code
            problem_retryable = exc.retryable
            problem_rate_limit_origin = exc.rate_limit_origin
            problem_provider_code = exc.provider_code
        elif isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
            status = response.status_code
            category = self._http_category(status)
            code = f"http_{status}"
            safe_message = self._http_safe_message(category)
        elif isinstance(exc, httpx.RequestError):
            category = ErrorCategory.TRANSPORT_FAILURE
            code = "transport_failure"
            safe_message = "LLM transport failed before a valid response was received."

        evidence = self._evidence(
            request=request,
            started_at=started_at,
            effective_provider=effective_provider,
            effective_model=effective_model,
            usage=usage,
            cost=cost,
        )
        if problem_status_code is not None:
            status_code = problem_status_code
        elif response is not None:
            status_code = response.status_code
        else:
            status_code = None
        retryable = (
            problem_retryable
            if problem_retryable is not None
            else self._retryable(category, status_code)
        )
        return self._make_error(
            request=request,
            evidence=evidence,
            category=category,
            code=code,
            phase=error_phase,
            safe_message=safe_message,
            partial_output=partial_output,
            external_id=self._external_id(response),
            status_code=status_code,
            retryable=retryable,
            retry_after_seconds=self._retry_after(response),
            rate_limit=self._rate_limit_evidence(
                category=category,
                response=response,
                response_body=response_body,
                origin=problem_rate_limit_origin,
                provider_code=problem_provider_code,
            ),
        )

    def _rate_limit_evidence(
        self,
        *,
        category: ErrorCategory,
        response: httpx.Response | None,
        response_body: bytes | None = None,
        origin: RateLimitOrigin | None = None,
        provider_code: str | None = None,
    ) -> RateLimitEvidence | None:
        if category is not ErrorCategory.RATE_LIMITED:
            return None
        return RateLimitEvidence(
            origin=origin or RateLimitOrigin.UNKNOWN,
            limit=(
                response.headers.get("x-ratelimit-limit")
                if response is not None
                else None
            ),
            remaining=(
                response.headers.get("x-ratelimit-remaining")
                if response is not None
                else None
            ),
            reset=(
                response.headers.get("x-ratelimit-reset")
                if response is not None
                else None
            ),
            provider_code=provider_code,
        )

    @staticmethod
    def _retryable(
        category: ErrorCategory, status_code: int | None
    ) -> bool | None:
        if status_code is not None:
            if status_code in {408, 429} or status_code >= 500:
                return True
            if 400 <= status_code < 500:
                return False
        if category in {
            ErrorCategory.TRANSPORT_FAILURE,
            ErrorCategory.PROVIDER_UNAVAILABLE,
        }:
            return True
        return None

    @staticmethod
    def _http_category(status: int) -> ErrorCategory:
        if status in {400, 422}:
            return ErrorCategory.INVALID_REQUEST
        if status == 401:
            return ErrorCategory.AUTHENTICATION_FAILED
        if status == 403:
            return ErrorCategory.PERMISSION_DENIED
        if status == 402:
            return ErrorCategory.PAYMENT_REQUIRED
        if status == 404:
            return ErrorCategory.MODEL_UNAVAILABLE
        if status == 408:
            return ErrorCategory.TIMEOUT
        if status == 429:
            return ErrorCategory.RATE_LIMITED
        if status >= 500:
            return ErrorCategory.PROVIDER_UNAVAILABLE
        return ErrorCategory.UNKNOWN

    @staticmethod
    def _http_safe_message(category: ErrorCategory) -> str:
        messages = {
            ErrorCategory.INVALID_REQUEST: "LLM target rejected the request.",
            ErrorCategory.AUTHENTICATION_FAILED: "LLM target rejected authentication.",
            ErrorCategory.PERMISSION_DENIED: "LLM target denied this operation.",
            ErrorCategory.PAYMENT_REQUIRED: (
                "LLM target requires available credit for this operation."
            ),
            ErrorCategory.MODEL_UNAVAILABLE: "Requested LLM model is unavailable.",
            ErrorCategory.TIMEOUT: "LLM target timed out.",
            ErrorCategory.RATE_LIMITED: "LLM target rate-limited the operation.",
            ErrorCategory.PROVIDER_UNAVAILABLE: "LLM target is currently unavailable.",
        }
        return messages.get(category, "LLM target returned an unclassified error.")

    @staticmethod
    def _external_id(response: httpx.Response | None) -> str | None:
        if response is None:
            return None
        return (
            response.headers.get("x-generation-id")
            or response.headers.get("x-request-id")
            or response.headers.get("request-id")
        )

    @staticmethod
    def _retry_after(response: httpx.Response | None) -> float | None:
        if response is None:
            return None
        value = response.headers.get("retry-after")
        if value is None:
            return None
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    async def _close_stream(
        response: httpx.Response | None, client: httpx.AsyncClient | None
    ) -> None:
        if response is not None:
            with suppress(Exception):
                await response.aclose()
        if client is not None:
            with suppress(Exception):
                await client.aclose()
