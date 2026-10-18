"""Exercise the scene visibility contract through both native HTTP adapters."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import SecretStr

from api.llm.adapters import GeminiAdapter, GroqAdapter
from api.llm.adapters.gemini import GEMINI_OFFICIAL_BASE_URL, GEMINI_PROVIDER_LABEL
from api.llm.adapters.groq import (
    GROQ_OFFICIAL_BASE_URL,
    GROQ_PROVIDER_LABEL,
    GROQ_QWEN_MODEL_ID,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    StructuredGenerationRequest,
)
from api.scene_director_service import SceneContinuationProposal
from api.turn_models import Visibility


_KEY = "synthetic-visibility-test-key"
_FACT = "Uma câmera oculta acompanha a entrada do galpão."


def _scene_payload(visibility):
    return {
        "n": (
            "O galpão abandonado ocupa o fim da rua, sob um letreiro enferrujado. "
            "A chuva bate nas janelas enquanto passos ecoam atrás da porta lateral."
        ),
        "o": "unresolved",
        "l": "Galpão abandonado",
        "s": "A entrada do galpão está silenciosa sob a chuva.",
        "p": [],
        "f": [{
            "k": "observation", "s": _FACT, "v": visibility,
            "i": 0.5, "p": False,
        }],
        "t": ["Identificar a origem dos passos"],
        "r": [],
        "q": "O que você faz diante da entrada?",
    }


def _http_adapter(adapter_kind, visibility, calls):
    is_groq = adapter_kind == "groq"
    model = GROQ_QWEN_MODEL_ID if is_groq else "gemini-3.8-flash"
    target = LLMTarget(
        profile="scene-visibility-synthetic",
        provider=GROQ_PROVIDER_LABEL if is_groq else GEMINI_PROVIDER_LABEL,
        model=model,
    )
    capabilities = CapabilitySet(
        target=target,
        descriptors=tuple(
            CapabilityDescriptor(name=name, support=CapabilitySupport.NATIVE)
            for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)
        ),
    )

    def handler(request):
        calls.append(json.loads(request.content))
        text = json.dumps(_scene_payload(visibility), ensure_ascii=False)
        if is_groq:
            assert str(request.url) == f"{GROQ_OFFICIAL_BASE_URL}/chat/completions"
            payload = {
                "model": model,
                "choices": [{
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }],
            }
        else:
            assert str(request.url) == f"{GEMINI_OFFICIAL_BASE_URL}/models/{model}:generateContent"
            payload = {
                "modelVersion": model,
                "candidates": [{
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": "STOP",
                }],
            }
        return httpx.Response(200, json=payload, request=request)

    adapter_class = GroqAdapter if is_groq else GeminiAdapter
    adapter = adapter_class(
        base_url=GROQ_OFFICIAL_BASE_URL if is_groq else GEMINI_OFFICIAL_BASE_URL,
        capability_set=capabilities,
        api_key=SecretStr(_KEY),
        reasoning_effort="none" if is_groq else "low",
        transport=httpx.MockTransport(handler),
    )
    request = StructuredGenerationRequest(
        operation="scene-visibility-synthetic",
        target=target,
        messages=(LLMMessage(role=MessageRole.USER, content="Onde estou?"),),
        deadline=datetime.now(timezone.utc) + timedelta(seconds=5),
        response_model=SceneContinuationProposal,
    )
    return adapter, request


def _sent_visibility_schema(adapter_kind, payload):
    if adapter_kind == "groq":
        schema = payload["response_format"]["json_schema"]["schema"]
    else:
        schema = payload["generationConfig"]["responseFormat"]["text"]["schema"]

    def resolve(node):
        while "$ref" in node:
            reference = node["$ref"]
            assert reference.startswith("#/")
            node = schema
            for part in reference[2:].split("/"):
                node = node[part]
        return node

    facts = resolve(schema["properties"]["f"])
    fact = resolve(facts["items"])
    return resolve(fact["properties"]["v"])


@pytest.mark.parametrize("adapter_kind", ["groq", "gemini"])
@pytest.mark.parametrize("visibility", ["public", "player", "storyteller"])
def test_native_http_schema_excludes_system_and_preserves_allowed_visibility(
    adapter_kind, visibility,
):
    calls = []
    adapter, request = _http_adapter(adapter_kind, visibility, calls)

    result = asyncio.run(adapter.generate_structured(request))

    assert len(calls) == 1
    enum = _sent_visibility_schema(adapter_kind, calls[0])["enum"]
    assert set(enum) == {"public", "player", "storyteller"}
    assert len(enum) == 3
    assert "system" not in enum
    assert isinstance(result.value, SceneContinuationProposal)
    fact = result.value.new_facts[0]
    assert fact.visibility is Visibility(visibility)
    assert fact.summary == _FACT
    assert result.value.model_dump(mode="json", by_alias=True)["f"][0]["v"] == visibility


@pytest.mark.parametrize("adapter_kind", ["groq", "gemini"])
def test_malicious_system_visibility_is_rejected_without_repair_or_retry(adapter_kind):
    calls = []
    adapter, request = _http_adapter(adapter_kind, "system", calls)

    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))

    assert len(calls) == 1
    error = caught.value.error
    assert error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    evidence = error.structure_validation
    assert evidence is not None
    assert evidence.stage == "schema_validation"
    assert any(issue.path == ("f", 0, "v") and issue.code == "literal_error"
               for issue in evidence.issues)
    serialized = error.model_dump_json()
    assert _KEY not in serialized
    assert _FACT not in serialized
