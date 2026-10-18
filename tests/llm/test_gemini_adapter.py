import asyncio
import json
from datetime import datetime, timedelta, timezone
from enum import Enum

import httpx
import pytest
from pydantic import BaseModel, Field, SecretStr

from api.llm.adapters import GeminiAdapter
from api.llm.adapters.gemini import (
    GEMINI_OFFICIAL_BASE_URL,
    GEMINI_PROVIDER_LABEL,
)
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    GenerationParameters,
    GenerationRequest,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MeasurementStatus,
    MessageRole,
    ProvenanceSource,
    StreamEventKind,
    StreamingGenerationRequest,
    StructuredGenerationRequest,
    TokenUsage,
    validate_stream_events,
)


_SECRET = "synthetic-gemini-secret-never-log"


class _Route(BaseModel):
    route: str


class _Visibility(str, Enum):
    PUBLIC = "public"
    PLAYER = "player"


class _BoundedFact(BaseModel):
    summary: str = Field(min_length=3, max_length=40)
    visibility: _Visibility = _Visibility.PLAYER


class _NestedEnvelope(BaseModel):
    facts: tuple[_BoundedFact, ...] = Field(default=(), max_length=4)


class _UnreadJSONStream(httpx.AsyncByteStream):
    def __init__(self, payload: dict) -> None:
        self._content = json.dumps(payload).encode("utf-8")

    async def __aiter__(self):
        yield self._content

    async def aclose(self) -> None:
        return None


def _target(model: str = "gemini-3.7-flash") -> LLMTarget:
    return LLMTarget(
        profile="gemini-synthetic-only",
        provider=GEMINI_PROVIDER_LABEL,
        model=model,
    )


def _capabilities(
    target: LLMTarget | None = None,
    *,
    structured: CapabilitySupport = CapabilitySupport.NATIVE,
) -> CapabilitySet:
    return CapabilitySet(
        target=target or _target(),
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=structured,
                source=(
                    "local Pydantic validation over JSON text"
                    if structured is CapabilitySupport.EMULATED
                    else None
                ),
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )


def _deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=5)


def _adapter(
    handler,
    *,
    target: LLMTarget | None = None,
    structured: CapabilitySupport = CapabilitySupport.NATIVE,
    reasoning_effort: str | None = None,
) -> GeminiAdapter:
    selected = target or _target()
    return GeminiAdapter(
        base_url=GEMINI_OFFICIAL_BASE_URL,
        capability_set=_capabilities(selected, structured=structured),
        api_key=SecretStr(_SECRET),
        reasoning_effort=reasoning_effort,
        transport=httpx.MockTransport(handler),
    )


def _request(**overrides) -> GenerationRequest:
    values = {
        "operation": "gemini-text",
        "target": _target(),
        "messages": (LLMMessage(role=MessageRole.USER, content="entrada sintética"),),
        "deadline": _deadline(),
    }
    values.update(overrides)
    return GenerationRequest(**values)


def _success_payload(
    text: str = "resultado",
    *,
    model: str = "gemini-3.7-flash",
    finish_reason: str = "STOP",
) -> dict:
    return {
        "modelVersion": model,
        "responseId": "synthetic-response-id",
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": finish_reason,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 9,
            "candidatesTokenCount": 4,
            "thoughtsTokenCount": 2,
            "totalTokenCount": 15,
        },
    }


def _traceback_locals(exc: BaseException) -> str:
    rows: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        module_name = traceback.tb_frame.f_globals.get("__name__", "")
        if module_name.startswith("api.llm"):
            rows.extend(
                f"{name}={value!r}"
                for name, value in traceback.tb_frame.f_locals.items()
            )
        traceback = traceback.tb_next
    return "\n".join(rows)


@pytest.mark.parametrize(
    ("base_url", "provider", "model", "secret"),
    [
        ("http://generativelanguage.googleapis.com/v1beta", GEMINI_PROVIDER_LABEL, "gemini-3.7-flash", _SECRET),
        ("https://generativelanguage.googleapis.com.evil.test/v1beta", GEMINI_PROVIDER_LABEL, "gemini-3.7-flash", _SECRET),
        (GEMINI_OFFICIAL_BASE_URL, "misleading-provider", "gemini-3.7-flash", _SECRET),
        (GEMINI_OFFICIAL_BASE_URL, GEMINI_PROVIDER_LABEL, "gemini-flash-latest", _SECRET),
        (GEMINI_OFFICIAL_BASE_URL, GEMINI_PROVIDER_LABEL, "gemini-3.7-flash-preview", _SECRET),
        (GEMINI_OFFICIAL_BASE_URL, GEMINI_PROVIDER_LABEL, "gemini-3.7-flash", " "),
    ],
)
def test_constructor_rejects_unsafe_or_incomplete_targets(
    base_url: str, provider: str, model: str, secret: str
) -> None:
    target = LLMTarget(profile="invalid", provider=provider, model=model)
    with pytest.raises(ValueError):
        GeminiAdapter(
            base_url=base_url,
            capability_set=_capabilities(target),
            api_key=SecretStr(secret),
        )


def test_constructor_rejects_unsupported_none_reasoning_effort() -> None:
    with pytest.raises(ValueError, match="reasoning effort"):
        _adapter(lambda request: httpx.Response(500, request=request), reasoning_effort="none")


def test_text_request_uses_only_official_header_and_maps_protocol() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_success_payload(), request=request)

    adapter = _adapter(handler, reasoning_effort="low")
    request = _request(
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content="instrução fixa"),
            LLMMessage(role=MessageRole.USER, content="ação do jogador"),
            LLMMessage(role=MessageRole.ASSISTANT, content="continuidade anterior"),
            LLMMessage(role=MessageRole.USER, content="nova ação"),
        ),
        parameters=GenerationParameters(
            temperature=0.65,
            max_output_tokens=128,
            seed=7,
        ),
    )

    result = asyncio.run(adapter.generate_text(request))

    assert captured["url"] == (
        f"{GEMINI_OFFICIAL_BASE_URL}/models/gemini-3.7-flash:generateContent"
    )
    assert "key=" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == _SECRET
    assert "authorization" not in captured["headers"]
    payload = captured["payload"]
    assert payload["systemInstruction"] == {"parts": [{"text": "instrução fixa"}]}
    assert [item["role"] for item in payload["contents"]] == ["user", "model", "user"]
    assert payload["store"] is False
    assert len(payload["safetySettings"]) == 4
    assert all(
        row["threshold"] == "BLOCK_ONLY_HIGH" for row in payload["safetySettings"]
    )
    generation = payload["generationConfig"]
    assert generation["maxOutputTokens"] == 128
    assert generation["seed"] == 7
    assert generation["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert "temperature" not in generation
    assert result.content == "resultado"
    assert result.evidence.provenance.effective_provider.value == GEMINI_PROVIDER_LABEL
    assert (
        result.evidence.provenance.effective_provider.source
        is ProvenanceSource.OBSERVED
    )
    assert result.evidence.provenance.effective_model.value == "gemini-3.7-flash"
    assert (
        result.evidence.provenance.effective_model.source
        is ProvenanceSource.REPORTED
    )
    assert result.evidence.usage == TokenUsage(
        status=MeasurementStatus.REPORTED,
        input_tokens=9,
        output_tokens=4,
        total_tokens=15,
        source="Gemini GenerateContentResponse.usageMetadata",
    )
    assert result.evidence.cost.status is MeasurementStatus.UNAVAILABLE


def test_structured_request_uses_current_native_schema_and_validates_locally() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_success_payload('{"route":"galpão"}'),
            request=request,
        )

    adapter = _adapter(handler)
    request = StructuredGenerationRequest(
        operation="gemini-structured",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="continue a cena"),),
        deadline=_deadline(),
        response_model=_Route,
    )

    result = asyncio.run(adapter.generate_structured(request))

    text_format = captured["generationConfig"]["responseFormat"]["text"]
    assert text_format["mimeType"] == "APPLICATION_JSON"
    assert text_format["schema"] == _Route.model_json_schema()
    assert result.value == _Route(route="galpão")


def test_native_schema_inlines_pydantic_refs_and_removes_unsupported_keywords() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_success_payload(
                '{"facts":[{"summary":"pista sintética","visibility":"public"}]}'
            ),
            request=request,
        )

    request = StructuredGenerationRequest(
        operation="gemini-normalized-schema",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="continue a cena"),),
        deadline=_deadline(),
        response_model=_NestedEnvelope,
    )

    result = asyncio.run(_adapter(handler).generate_structured(request))

    schema = captured["generationConfig"]["responseFormat"]["text"]["schema"]
    serialized = json.dumps(schema)
    for unsupported in (
        '"$defs"',
        '"$ref"',
        '"allOf"',
        '"default"',
        '"minLength"',
        '"maxLength"',
    ):
        assert unsupported not in serialized
    fact_schema = schema["properties"]["facts"]["items"]
    assert fact_schema["properties"]["visibility"]["enum"] == ["public", "player"]
    assert schema["properties"]["facts"]["maxItems"] == 4
    assert result.value.facts[0].summary == "pista sintética"


def test_emulated_structured_mode_requests_json_without_schema() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_success_payload('{"route":"rua"}'),
            request=request,
        )

    adapter = _adapter(handler, structured=CapabilitySupport.EMULATED)
    request = StructuredGenerationRequest(
        operation="gemini-emulated-structured",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="continue a cena"),),
        deadline=_deadline(),
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=True,
            ),
        ),
    )

    result = asyncio.run(adapter.generate_structured(request))

    text_format = captured["generationConfig"]["responseFormat"]["text"]
    assert text_format == {"mimeType": "APPLICATION_JSON"}
    assert result.value.route == "rua"


def test_invalid_structured_output_fails_without_repair_or_second_call() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_success_payload("not-json"), request=request)

    adapter = _adapter(handler)
    request = StructuredGenerationRequest(
        operation="gemini-invalid-structured",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="continue a cena"),),
        deadline=_deadline(),
        response_model=_Route,
    )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))

    assert calls == 1
    assert caught.value.error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT


@pytest.mark.parametrize(
    ("payload", "category"),
    [
        ({"promptFeedback": {"blockReason": "SAFETY"}}, ErrorCategory.CONTENT_REJECTED),
        (_success_payload(finish_reason="MAX_TOKENS"), ErrorCategory.MALFORMED_RESPONSE),
        (_success_payload(finish_reason="SAFETY"), ErrorCategory.CONTENT_REJECTED),
        (_success_payload(finish_reason="RECITATION"), ErrorCategory.CONTENT_REJECTED),
        (_success_payload(finish_reason="OTHER"), ErrorCategory.MALFORMED_RESPONSE),
    ],
)
def test_blocked_or_incomplete_responses_fail_closed(
    payload: dict, category: ErrorCategory
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_request()))

    assert caught.value.error.category is category


@pytest.mark.parametrize(
    ("model", "accepted"),
    [
        ("gemini-3.7-flash", True),
        ("gemini-3.7-flash-001", True),
        ("models/gemini-3.7-flash-001", True),
        ("gemini-3.7-pro", False),
        ("gemini-3.7-flash-preview-001", False),
    ],
)
def test_reported_model_version_is_required_and_cannot_silently_change(
    model: str, accepted: bool
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_success_payload(model=model), request=request)

    if accepted:
        result = asyncio.run(_adapter(handler).generate_text(_request()))
        assert result.evidence.provenance.effective_model.value == model.removeprefix(
            "models/"
        )
    else:
        with pytest.raises(LLMInvocationError) as caught:
            asyncio.run(_adapter(handler).generate_text(_request()))
        assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH


def test_current_gemini_38_stable_target_and_reported_version_are_accepted() -> None:
    target = _target("gemini-3.8-flash")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_success_payload(model="gemini-3.8-flash-001"),
            request=request,
        )

    result = asyncio.run(
        _adapter(handler, target=target, reasoning_effort="low").generate_text(
            _request(target=target)
        )
    )

    assert result.evidence.provenance.requested_target == target
    assert result.evidence.provenance.effective_model.value == "gemini-3.8-flash-001"


def test_missing_model_version_fails_target_provenance() -> None:
    payload = _success_payload()
    del payload["modelVersion"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_request()))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH


def test_bound_adapter_rejects_model_version_change_between_invocations() -> None:
    responses = iter(("gemini-3.7-flash-001", "gemini-3.7-flash-002"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_success_payload(model=next(responses)),
            request=request,
        )

    adapter = _adapter(handler)
    first = asyncio.run(adapter.generate_text(_request(operation="first")))
    assert first.evidence.provenance.effective_model.value.endswith("-001")

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_text(_request(operation="second")))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert (
        caught.value.error.code
        == "gemini_model_version_changed_between_invocations"
    )


def test_stream_uses_gemini_sse_and_completes_only_after_stop_and_eof() -> None:
    chunks = [
        {
            "modelVersion": "gemini-3.7-flash-001",
            "candidates": [{"content": {"parts": [{"text": "A porta "}]}}],
        },
        {
            "modelVersion": "gemini-3.7-flash-001",
            "candidates": [
                {
                    "content": {"parts": [{"text": "range."}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
                "totalTokenCount": 8,
            },
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith(
            "/models/gemini-3.7-flash:streamGenerateContent?alt=sse"
        )
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, text=body, request=request)

    adapter = _adapter(handler)
    request = StreamingGenerationRequest(
        operation="gemini-stream",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="abra a porta"),),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in adapter.stream_text(request)]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert [event.delta for event in events[:-1]] == ["A porta ", "range."]
    assert events[-1].kind is StreamEventKind.COMPLETED
    assert events[-1].evidence is not None
    assert events[-1].evidence.provenance.effective_model.value == (
        "gemini-3.7-flash-001"
    )


def test_stream_block_after_partial_text_is_terminal_failure() -> None:
    chunks = [
        {
            "modelVersion": "gemini-3.7-flash",
            "candidates": [{"content": {"parts": [{"text": "parcial"}]}}],
        },
        {
            "modelVersion": "gemini-3.7-flash",
            "candidates": [{"finishReason": "SAFETY"}],
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, text=body, request=request)

    adapter = _adapter(handler)
    request = StreamingGenerationRequest(
        operation="gemini-stream-block",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="entrada sintética"),),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in adapter.stream_text(request)]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert events[0].delta == "parcial"
    assert events[-1].kind is StreamEventKind.FAILED
    assert events[-1].partial_output is True
    assert events[-1].error is not None
    assert events[-1].error.category is ErrorCategory.CONTENT_REJECTED


def test_http_error_is_normalized_without_leaking_secret_or_prompt() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"status": "RESOURCE_EXHAUSTED", "message": _SECRET}},
            request=request,
        )

    prompt = "prompt-synthetic-never-retained"
    request = _request(
        messages=(LLMMessage(role=MessageRole.USER, content=prompt),)
    )
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(request))

    assert caught.value.error.category is ErrorCategory.RATE_LIMITED
    public = repr(caught.value.error) + str(caught.value) + _traceback_locals(caught.value)
    assert _SECRET not in public
    assert prompt not in public


def test_unread_stream_http_error_is_read_and_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"content-type": "application/json"},
            stream=_UnreadJSONStream(
                {
                    "error": {
                        "status": "RESOURCE_EXHAUSTED",
                        "message": _SECRET,
                    }
                }
            ),
            request=request,
        )

    request = StreamingGenerationRequest(
        operation="gemini-stream-http-error",
        target=_target(),
        messages=(LLMMessage(role=MessageRole.USER, content="entrada sintética"),),
        deadline=_deadline(),
    )

    async def collect():
        return [event async for event in _adapter(handler).stream_text(request)]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert len(events) == 1
    assert events[0].kind is StreamEventKind.FAILED
    assert events[0].error is not None
    assert events[0].error.category is ErrorCategory.RATE_LIMITED
    assert _SECRET not in repr(events[0].error)
