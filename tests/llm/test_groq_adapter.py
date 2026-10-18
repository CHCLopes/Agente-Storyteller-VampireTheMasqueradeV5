import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from api.llm.adapters import GroqAdapter
from api.llm.adapters.groq import (
    GROQ_GPT_OSS_MODEL_ID,
    GROQ_OFFICIAL_BASE_URL,
    GROQ_PROVIDER_LABEL,
    GROQ_QWEN_MODEL_ID,
    _normalize_groq_strict_schema,
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
    validate_stream_events,
)
from api.scene_director_service import SceneContinuationProposal


_SECRET = "synthetic-groq-secret-never-log"


class _Detail(BaseModel):
    note: str
    visible: bool = True


class _Route(BaseModel):
    route: str
    detail: _Detail
    tags: tuple[str, ...] = ()


class _SSEStream(httpx.AsyncByteStream):
    def __init__(self, rows: list[str]) -> None:
        self._content = "".join(f"data: {row}\n\n" for row in rows).encode()

    async def __aiter__(self):
        yield self._content

    async def aclose(self) -> None:
        return None


def _target(
    *,
    provider: str = GROQ_PROVIDER_LABEL,
    model: str = GROQ_QWEN_MODEL_ID,
) -> LLMTarget:
    return LLMTarget(profile="groq-free-synthetic", provider=provider, model=model)


def _capabilities(target: LLMTarget | None = None) -> CapabilitySet:
    return CapabilitySet(
        target=target or _target(),
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )


def _reasoning(model: str) -> str:
    return "none" if model == GROQ_QWEN_MODEL_ID else "low"


def _adapter(
    handler,
    *,
    target: LLMTarget | None = None,
) -> GroqAdapter:
    selected = target or _target()
    return GroqAdapter(
        base_url=GROQ_OFFICIAL_BASE_URL,
        capability_set=_capabilities(selected),
        api_key=SecretStr(_SECRET),
        reasoning_effort=_reasoning(selected.model),
        transport=httpx.MockTransport(handler),
    )


def _deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=5)


def _request(*, model: str = GROQ_QWEN_MODEL_ID, **overrides) -> GenerationRequest:
    values = {
        "operation": "groq-text",
        "target": _target(model=model),
        "messages": (LLMMessage(role=MessageRole.USER, content="entrada sintética"),),
        "deadline": _deadline(),
    }
    values.update(overrides)
    return GenerationRequest(**values)


def _success_payload(
    text: str = "resultado",
    *,
    model: str = GROQ_QWEN_MODEL_ID,
    include_model: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "synthetic-groq-response",
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
    }
    if include_model:
        payload["model"] = model
    return payload


@pytest.mark.parametrize(
    ("base_url", "provider", "model", "secret", "reasoning"),
    [
        ("http://api.groq.com/openai/v1", GROQ_PROVIDER_LABEL, GROQ_QWEN_MODEL_ID, _SECRET, "none"),
        ("https://api.groq.com.evil.test/openai/v1", GROQ_PROVIDER_LABEL, GROQ_QWEN_MODEL_ID, _SECRET, "none"),
        (GROQ_OFFICIAL_BASE_URL, "misleading-provider", GROQ_QWEN_MODEL_ID, _SECRET, "none"),
        (GROQ_OFFICIAL_BASE_URL, GROQ_PROVIDER_LABEL, "qwen/qwen-latest", _SECRET, "none"),
        (GROQ_OFFICIAL_BASE_URL, GROQ_PROVIDER_LABEL, GROQ_QWEN_MODEL_ID, " ", "none"),
        (GROQ_OFFICIAL_BASE_URL, GROQ_PROVIDER_LABEL, GROQ_QWEN_MODEL_ID, _SECRET, "low"),
        (GROQ_OFFICIAL_BASE_URL, GROQ_PROVIDER_LABEL, GROQ_GPT_OSS_MODEL_ID, _SECRET, "none"),
    ],
)
def test_constructor_rejects_unbound_or_unapproved_profile(
    base_url: str,
    provider: str,
    model: str,
    secret: str,
    reasoning: str,
) -> None:
    target = _target(provider=provider, model=model)
    with pytest.raises(ValueError):
        GroqAdapter(
            base_url=base_url,
            capability_set=_capabilities(target),
            api_key=SecretStr(secret),
            reasoning_effort=reasoning,
        )


@pytest.mark.parametrize(
    ("model", "reasoning", "include_reasoning"),
    [
        (GROQ_QWEN_MODEL_ID, "none", None),
        (GROQ_GPT_OSS_MODEL_ID, "low", False),
    ],
)
def test_text_request_uses_fixed_route_and_explicit_reasoning(
    model: str, reasoning: str, include_reasoning: bool | None
) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json=_success_payload(model=model),
            request=request,
        )

    target = _target(model=model)
    result = asyncio.run(
        _adapter(handler, target=target).generate_text(
            _request(
                model=model,
                parameters=GenerationParameters(
                    temperature=0.65,
                    max_output_tokens=256,
                    seed=7,
                ),
            )
        )
    )

    assert captured["url"] == f"{GROQ_OFFICIAL_BASE_URL}/chat/completions"
    assert captured["headers"]["authorization"] == f"Bearer {_SECRET}"
    payload = captured["payload"]
    assert payload["model"] == model
    assert payload["reasoning_effort"] == reasoning
    assert payload.get("include_reasoning") == include_reasoning
    assert "reasoning_format" not in payload
    assert payload["max_completion_tokens"] == 256
    assert "max_tokens" not in payload
    assert result.content == "resultado"
    assert result.evidence.provenance.effective_provider.value == GROQ_PROVIDER_LABEL
    assert result.evidence.provenance.effective_provider.source is ProvenanceSource.OBSERVED
    assert result.evidence.provenance.effective_model.value == model
    assert result.evidence.provenance.effective_model.source is ProvenanceSource.REPORTED
    assert result.evidence.usage.status is MeasurementStatus.REPORTED
    assert result.evidence.cost.status is MeasurementStatus.UNAVAILABLE


def test_structured_request_normalizes_strict_schema_and_validates_locally() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        content = json.dumps(
            {
                "route": "galpão",
                "detail": {"note": "porta entreaberta", "visible": True},
                "tags": [],
            },
            ensure_ascii=False,
        )
        return httpx.Response(200, json=_success_payload(content), request=request)

    values = _request().model_dump()
    values.pop("required_capabilities")
    request = StructuredGenerationRequest(
        **values,
        response_model=_Route,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION),
        ),
    )
    result = asyncio.run(_adapter(handler).generate_structured(request))

    response_format = captured["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["required"] == ["route", "detail", "tags"]
    assert schema["additionalProperties"] is False
    detail_schema = schema["$defs"]["_Detail"]
    assert detail_schema["required"] == ["note", "visible"]
    assert detail_schema["additionalProperties"] is False

    def keys(value: Any):
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from keys(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from keys(nested)

    assert "default" not in set(keys(schema))
    assert result.value == _Route(
        route="galpão",
        detail=_Detail(note="porta entreaberta", visible=True),
        tags=(),
    )


def test_real_scene_proposal_schema_uses_only_groq_supported_composition() -> None:
    schema = _normalize_groq_strict_schema(
        SceneContinuationProposal.model_json_schema()
    )

    serialized = json.dumps(schema)
    assert '"allOf"' not in serialized
    visibility = schema["$defs"]["ProposedSceneFact"]["properties"]["v"]
    assert visibility["type"] == "string"
    assert set(visibility["enum"]) == {"public", "player", "storyteller"}
    assert "default" not in visibility


def test_unsupported_all_of_composition_fails_before_provider_call() -> None:
    with pytest.raises(ValueError, match="unsupported allOf composition"):
        _normalize_groq_strict_schema(
            {"allOf": [{"type": "string"}, {"maxLength": 10}]}
        )


@pytest.mark.parametrize(
    "reported_model",
    [None, GROQ_GPT_OSS_MODEL_ID],
)
def test_missing_or_mismatched_reported_model_fails_closed(
    reported_model: str | None,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_success_payload(
                model=reported_model or GROQ_QWEN_MODEL_ID,
                include_model=reported_model is not None,
            ),
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_request()))

    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert _SECRET not in str(caught.value)


def test_stream_is_separate_from_structured_output_and_has_verified_route() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        rows = [
            json.dumps(
                {
                    "model": GROQ_QWEN_MODEL_ID,
                    "choices": [
                        {"delta": {"content": "STORY"}, "finish_reason": None}
                    ],
                }
            ),
            json.dumps(
                {
                    "model": GROQ_QWEN_MODEL_ID,
                    "choices": [{"delta": {}, "finish_reason": "stop"}],
                }
            ),
            "[DONE]",
        ]
        return httpx.Response(
            200,
            stream=_SSEStream(rows),
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    async def collect():
        values = _request().model_dump()
        values.pop("required_capabilities")
        request = StreamingGenerationRequest(**values)
        return [event async for event in _adapter(handler).stream_text(request)]

    events = asyncio.run(collect())

    validate_stream_events(events)
    assert [event.kind for event in events] == [
        StreamEventKind.DELTA,
        StreamEventKind.COMPLETED,
    ]
    assert captured["stream"] is True
    assert "response_format" not in captured
    assert "stream_options" not in captured
    assert events[-1].evidence is not None
    assert (
        events[-1].evidence.provenance.effective_provider.source
        is ProvenanceSource.OBSERVED
    )


def test_rate_limit_is_normalized_without_secret_or_prompt_leakage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": f"blocked {_SECRET} entrada sintética"}},
            headers={"retry-after": "4"},
            request=request,
        )

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(_adapter(handler).generate_text(_request()))

    error = caught.value.error
    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.retry_after_seconds == 4
    assert _SECRET not in str(caught.value)
    assert "entrada sintética" not in str(caught.value)
