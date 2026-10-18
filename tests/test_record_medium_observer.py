"""Offline boundaries for the explicit medium-effort observation policy."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from api.llm.adapters.groq import GroqAdapter, GROQ_GPT_OSS_MODEL_ID, GROQ_OFFICIAL_BASE_URL
from api.llm.adapters.openai_compatible import OpenAICompatibleAdapter
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION, CapabilityDescriptor,
    CapabilitySet, CapabilitySupport, CancellationToken, ErrorCategory,
    GenerationParameters, LLMInvocationError, LLMMessage, LLMTarget,
    StructuredGenerationRequest, utc_now,
)
from scripts import narrator_record_medium_observer as m
from scripts import narrator_record_quote_evidence as contract

ROOT = Path(__file__).resolve().parent.parent
_SECRET = "SYNTHETIC_MEDIUM_CREDENTIAL_NEVER_PERSIST"
_PRIVATE = "PRIVATE_MODEL_ERROR_REASONING_NEVER_PERSIST"
_REQUEST_ID = "req_01m1y7g4zrec5r9hhcs391ra1w"


@lru_cache(maxsize=1)
def _baseline_body():
    return json.loads((ROOT / "evals/narrator/reports/record-evidence-claim-check-dossier-fda8af66-2026-09-07.json").read_text(encoding="utf-8"))["request"]["body"]


def _target(**changes):
    return LLMTarget(**{"profile": m.MEDIUM_PROFILE, "provider": "Groq",
                       "model": GROQ_GPT_OSS_MODEL_ID, **changes})


def _request(**changes):
    return StructuredGenerationRequest(**{
        "operation": "record-reasoning-medium.opening", "target": _target(),
        "messages": tuple(LLMMessage(**item) for item in _baseline_body()["messages"]),
        "response_model": contract.RecordQuoteEvidenceProposal,
        "parameters": GenerationParameters(temperature=0.65, max_output_tokens=3072),
        "deadline": utc_now() + timedelta(seconds=5), **changes,
    })


def _capabilities(target=None):
    return CapabilitySet(target=target or _target(), descriptors=(
        CapabilityDescriptor(name=CAPABILITY_TEXT_GENERATION, support=CapabilitySupport.NATIVE),
        CapabilityDescriptor(name=CAPABILITY_STRUCTURED_GENERATION, support=CapabilitySupport.NATIVE),
    ))


def _adapter(handler=None, **changes):
    values = {"base_url": GROQ_OFFICIAL_BASE_URL, "capability_set": _capabilities(),
              "api_key": SecretStr(_SECRET), "reasoning_effort": "medium",
              "transport": httpx.MockTransport(handler) if handler else None}
    values.update(changes)
    return m.MediumObservationAdapter(**values)


def _completion(finish="stop"):
    content = {"records": {"o": "unresolved", "l": "Corredor",
        "s": "Um sussurro distante ecoa.", "p": [], "f": [], "t": [], "r": [],
        "q": "O que você faz agora?"}, "supports": []}
    return {"model": GROQ_GPT_OSS_MODEL_ID, "choices": [{"finish_reason": finish,
        "message": {"content": json.dumps(content), "reasoning": _PRIVATE}}],
        "usage": {"prompt_tokens": 2888, "completion_tokens": 900, "total_tokens": 3788,
                  "completion_tokens_details": {"reasoning_tokens": 450}}}


def _error_body():
    return json.dumps({"error": {"code": "json_validate_failed", "message": _PRIVATE,
                                  "failed_generation": '{"private":"' + _PRIVATE + '"'}}).encode()


def _assert_safe(adapter, exception=None):
    text = json.dumps(adapter.observation)
    if exception is not None:
        assert exception.__context__ is exception.__cause__ is None
        text += exception.error.model_dump_json() + repr(exception)
        trace = exception.__traceback__
        while trace is not None:
            module = trace.tb_frame.f_globals.get("__name__", "")
            if module.startswith(("api.llm", "scripts.narrator_record_")):
                text += repr(trace.tb_frame.f_locals)
            trace = trace.tb_next
    assert _SECRET not in text and _PRIVATE not in text
    assert _baseline_body()["messages"][1]["content"] not in text


def test_medium_wire_identity_and_one_dispatch_without_historical_constructor(monkeypatch):
    monkeypatch.setattr(GroqAdapter, "__init__", lambda *args, **kwargs: pytest.fail("historical low constructor called"))
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=_completion(), headers={"x-request-id": _REQUEST_ID})
    adapter = _adapter(handler)
    assert adapter._reasoning_effort == "medium"
    assert adapter.observation["http_status"] is None
    result = asyncio.run(adapter.generate_structured(_request()))
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert str(calls[0].url) == GROQ_OFFICIAL_BASE_URL + "/chat/completions"
    assert calls[0].headers["authorization"] == "Bearer " + _SECRET
    assert {key for key in body if body[key] != _baseline_body()[key]} == {"reasoning_effort"}
    assert body == {**_baseline_body(), "reasoning_effort": "medium"}
    assert m._canonical_sha(body) == m.APPROVED_PAYLOAD_SHA256
    assert body["max_completion_tokens"] == 3072 and body["include_reasoning"] is False
    assert result.evidence.provenance.adapter.name == m.ADAPTER_NAME
    assert result.evidence.provenance.requested_target.profile == m.MEDIUM_PROFILE
    assert result.evidence.provenance.effective_provider.value == "Groq"
    assert result.evidence.provenance.effective_model.value == GROQ_GPT_OSS_MODEL_ID
    assert result.value.supports == ()
    assert adapter.observation["usage"]["reasoning_tokens"] == 450
    assert adapter.observation["request_id"] == _REQUEST_ID
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert len(calls) == 1
    _assert_safe(adapter, caught.value)


def test_preflight_builder_has_no_constructor_client_or_credential(monkeypatch):
    monkeypatch.setattr(OpenAICompatibleAdapter, "__init__", lambda *args, **kwargs: pytest.fail("transport constructed at preflight"))
    monkeypatch.setattr(GroqAdapter, "__init__", lambda *args, **kwargs: pytest.fail("Groq constructed at preflight"))
    monkeypatch.setattr(OpenAICompatibleAdapter, "_new_client", lambda *args: pytest.fail("HTTP client created at preflight"))
    class ForbiddenEnvironment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("credential inspected at preflight")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", ForbiddenEnvironment())
    body = m.build_medium_payload(_request())
    assert body == {**_baseline_body(), "reasoning_effort": "medium"}
    assert m._canonical_sha(body) == m.APPROVED_PAYLOAD_SHA256


@pytest.mark.parametrize("changes", [
    {"reasoning_effort": "low"}, {"reasoning_effort": "high"}, {"reasoning_effort": None},
    {"base_url": "https://api.groq.com/openai/v1/"},
    {"base_url": " https://api.groq.com/openai/v1"},
    {"base_url": "https://api.groq.com.evil.test/openai/v1"},
    {"base_url": "http://api.groq.com/openai/v1"},
    {"capability_set": _capabilities(_target(provider="groq"))},
    {"capability_set": _capabilities(_target(provider="OpenRouter"))},
    {"capability_set": _capabilities(_target(model="openai/gpt-oss-20b"))},
    {"capability_set": _capabilities(_target(profile="record-claim-check-gpt-oss-120b-groq-free-synthetic-low"))},
    {"api_key": None}, {"api_key": SecretStr("")}, {"api_key": SecretStr("  ")},
    {"api_key": _SECRET},
])
def test_constructor_rejects_any_unbound_medium_profile_before_transport(monkeypatch, changes):
    monkeypatch.setattr(OpenAICompatibleAdapter, "__init__", lambda *args, **kwargs: pytest.fail("invalid policy reached transport constructor"))
    with pytest.raises(ValueError) as caught:
        _adapter(**changes)
    assert _SECRET not in str(caught.value)


def test_historical_groq_still_rejects_medium():
    with pytest.raises(ValueError, match="requires reasoning_effort='low'"):
        GroqAdapter(base_url=GROQ_OFFICIAL_BASE_URL, capability_set=_capabilities(),
                    api_key=SecretStr(_SECRET), reasoning_effort="medium")


@pytest.mark.parametrize("change", ["budget", "temperature", "system", "user", "schema", "profile"])
def test_changed_request_cannot_reach_transport(change):
    calls = []
    adapter = _adapter(lambda request: calls.append(request))
    request = _request()
    if change in {"budget", "temperature"}:
        values = request.parameters.model_dump()
        values.update({"max_output_tokens": 1536} if change == "budget" else {"temperature": 0.5})
        request = request.model_copy(update={"parameters": GenerationParameters(**values)})
    elif change == "profile":
        request = request.model_copy(update={"target": _target(profile="another-experiment")})
    elif change == "schema":
        request = request.model_copy(update={"response_model": contract.RecordQuoteSupport})
    else:
        messages = list(request.messages)
        index = 0 if change == "system" else 1
        messages[index] = messages[index].model_copy(update={"content": _PRIVATE})
        request = request.model_copy(update={"messages": tuple(messages)})
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))
    assert calls == []
    _assert_safe(adapter, caught.value)


def test_streaming_payload_is_rejected_and_does_not_consume_single_use():
    adapter = _adapter()
    request = _request()
    with pytest.raises(ValueError):
        adapter._payload(request, stream=True, response_format=adapter._native_response_format(request))
    assert adapter._dispatch_started is False


@pytest.mark.parametrize("malformed", [False, True])
def test_inherited_http400_hook_and_normalization_remain_sanitized(malformed):
    body = b"{incomplete " + _PRIVATE.encode() if malformed else _error_body()
    adapter = _adapter(lambda request: httpx.Response(400, content=body))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert caught.value.error.code == ("http_400" if malformed else "groq_json_validate_failed")
    assert adapter.observation["error_body"]["complete"] is True
    assert adapter.observation["error_body"]["json_valid"] is (not malformed)
    assert adapter.observation["failed_generation"]["present"] is (None if malformed else True)
    _assert_safe(adapter, caught.value)


def test_length_observation_cannot_override_inherited_completion_gate():
    adapter = _adapter(lambda request: httpx.Response(200, json=_completion("length")))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert caught.value.error.code == "generation_truncated"
    assert adapter.observation["finish_reason"] == "length"
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("extra", [0, 1])
def test_inherited_64_kib_limit_is_inclusive_without_partial_parse(extra):
    body = _error_body()
    body += b" " * (65536 - len(body) + extra)
    adapter = _adapter(lambda request: httpx.Response(400, content=body))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert adapter.observation["error_body"]["complete"] is (extra == 0)
    assert adapter.observation["provider_code"] == ("json_validate_failed" if extra == 0 else None)
    _assert_safe(adapter, caught.value)


class _ErrorStream(httpx.AsyncByteStream):
    def __init__(self, *, overflow=False):
        self.overflow = overflow
        self.entered = asyncio.Event()
        self.closed = False
        self.count = 0
    async def __aiter__(self):
        self.count += 1
        yield _error_body()
        if self.overflow:
            self.count += 1
            yield b" " * 65536
            self.count += 1
            yield b"must not be read"
        self.entered.set()
        await asyncio.Event().wait()
    async def aclose(self): self.closed = True


def test_underreported_error_stream_cannot_bypass_inherited_bound():
    stream = _ErrorStream(overflow=True)
    adapter = _adapter(lambda request: httpx.Response(400, stream=stream, headers={"content-length": "1"}))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert stream.closed and stream.count == 2
    assert adapter.observation["error_body"]["status"] == "limit_exceeded"
    assert adapter.observation["provider_code"] is None
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("mode", ["deadline", "token", "task"])
def test_inherited_error_hook_obeys_original_cancellation_and_deadline(mode):
    async def run():
        stream = _ErrorStream()
        adapter = _adapter(lambda request: httpx.Response(400, stream=stream))
        token = CancellationToken()
        request = _request(cancellation=token, deadline=utc_now() + timedelta(seconds=0.05 if mode == "deadline" else 5))
        task = asyncio.create_task(adapter.generate_structured(request))
        await stream.entered.wait()
        if mode == "token": token.cancel()
        elif mode == "task": task.cancel()
        with pytest.raises(asyncio.CancelledError if mode == "task" else LLMInvocationError) as caught:
            await asyncio.wait_for(task, timeout=1)
        assert stream.closed
        assert adapter.observation["error_body"]["complete"] is False
        if mode != "task":
            assert caught.value.error.category is (ErrorCategory.TIMEOUT if mode == "deadline" else ErrorCategory.CANCELLED)
            _assert_safe(adapter, caught.value)
        _assert_safe(adapter)
    asyncio.run(run())


def test_historical_files_are_unchanged():
    frozen = {
        "api/llm/adapters/groq.py": "dbcde3da86ad591d2ccc2891d0425e30b3d9a5eb7ea09af5132e7417e1e94328",
        "scripts/narrator_record_budget_observer.py": "36a119fb82702580aeaf9ed6608679ec7fecb85faab57334d8eb5ea0f6f06060",
        "evals/narrator/groq_candidates_2026-09-05.json": "de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6",
    }
    for name, sha in frozen.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
