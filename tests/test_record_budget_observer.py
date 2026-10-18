"""Offline transport controls for the single fixed budget diagnostic."""
import asyncio
from datetime import timedelta
from functools import lru_cache
import hashlib
import json

import httpx
import pytest
from pydantic import SecretStr

from scripts import narrator_record_budget_observer as observer
from scripts import narrator_record_derivation as derivation
from scripts import narrator_record_evidence as contract
from api.llm.adapters.groq import GROQ_GPT_OSS_MODEL_ID, GROQ_OFFICIAL_BASE_URL
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION, CapabilityDescriptor, CapabilitySet,
    CapabilitySupport, CancellationToken, ErrorCategory, GenerationParameters,
    LLMInvocationError, LLMMessage, LLMTarget, MessageRole,
    StructuredGenerationRequest, utc_now,
)

_SECRET = "synthetic-budget-key-never-persist"
_PRIVATE = "PRIVATE_RESPONSE_OR_REASONING_NEVER_PERSIST"
_REQUEST_ID = "req_01m1xtmhhdeyjbew0n7ffxv9tg"


@lru_cache(maxsize=1)
def _fixed_messages():
    _, system = contract.load_evidence_prompt()
    user, _ = contract.build_evidence_packet(derivation.load_fixed_cases()[0])
    return (LLMMessage(role=MessageRole.SYSTEM, content=system),
            LLMMessage(role=MessageRole.USER, content=user))


def _request(**overrides):
    values = dict(
        operation="record-evidence-budget-probe",
        target=LLMTarget(profile="record-evidence-budget-1536-v1", provider="Groq",
                         model=GROQ_GPT_OSS_MODEL_ID),
        messages=_fixed_messages(), response_model=contract.RecordEvidenceProposal,
        parameters=GenerationParameters(temperature=0.65, max_output_tokens=1536),
        deadline=utc_now() + timedelta(seconds=5),
    )
    values.update(overrides)
    return StructuredGenerationRequest(**values)


def _adapter(handler):
    return observer.BudgetObservationAdapter(
        base_url=GROQ_OFFICIAL_BASE_URL,
        capability_set=CapabilitySet(target=_request().target, descriptors=(
            CapabilityDescriptor(name=CAPABILITY_TEXT_GENERATION, support=CapabilitySupport.NATIVE),
            CapabilityDescriptor(name=CAPABILITY_STRUCTURED_GENERATION,
                                 support=CapabilitySupport.NATIVE),)),
        api_key=SecretStr(_SECRET), reasoning_effort="low",
        transport=httpx.MockTransport(handler),
    )


def _body(**overrides):
    error = {"code": "json_validate_failed", "message": _PRIVATE,
             "failed_generation": '{"private":"' + _PRIVATE + '"'}
    error.update(overrides)
    return json.dumps({"error": error}).encode()


def _valid_content():
    return json.dumps({"records": {"o": "unresolved", "l": "Corredor",
        "s": "O corredor tem pedra fria.", "p": [], "f": [], "t": [],
        "r": [], "q": "O que você faz agora?"}, "supports": []})


def _success(**overrides):
    payload = {"model": GROQ_GPT_OSS_MODEL_ID, "choices": [{
        "message": {"content": _valid_content(), "reasoning": _PRIVATE},
        "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2320, "completion_tokens": 980,
                  "total_tokens": 3300, "completion_tokens_details": {
                      "reasoning_tokens": 700, "reasoning": _PRIVATE}}}
    payload.update(overrides)
    return payload


def _traceback_text(exception):
    rows = []
    traceback = exception.__traceback__
    while traceback is not None:
        module = traceback.tb_frame.f_globals.get("__name__", "")
        if module.startswith(("api.llm", "scripts.narrator_record_budget_observer")):
            rows.extend(f"{k}={v!r}" for k, v in traceback.tb_frame.f_locals.items())
        traceback = traceback.tb_next
    return "\n".join(rows)


def _assert_safe(adapter, exception=None):
    encoded = json.dumps(adapter.observation, ensure_ascii=False)
    if exception is not None:
        assert exception.__context__ is None
        assert exception.__cause__ is None
        encoded += exception.error.model_dump_json() + repr(exception) + _traceback_text(exception)
    assert _SECRET not in encoded
    assert _PRIVATE not in encoded
    assert _fixed_messages()[1].content not in encoded
    assert "failed_generation\": \"" not in encoded


def _invoke_error(body, *, status=400, headers=None):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, content=body, headers=headers, request=request)
    adapter = _adapter(handler)
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert len(calls) == 1
    _assert_safe(adapter, caught.value)
    return adapter.observation, caught.value.error


def test_fixed_request_only_one_dispatch_and_no_secret_in_observation():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=_success(), headers={"x-request-id": _REQUEST_ID})
    adapter = _adapter(handler)
    result = asyncio.run(adapter.generate_structured(_request()))
    assert result.value.supports == ()
    assert hashlib.sha256(json.dumps(calls[0], ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest() == observer.APPROVED_PAYLOAD_SHA256
    assert calls[0]["max_completion_tokens"] == 1536
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(_request()))
    assert len(calls) == 1
    observed = adapter.observation
    assert observed["request_id"] == _REQUEST_ID
    assert observed["model"] == GROQ_GPT_OSS_MODEL_ID
    assert observed["usage"] == {"input_tokens": 2320, "output_tokens": 980,
                                  "total_tokens": 3300, "reasoning_tokens": 700}
    assert observed["finish_reason"] == "stop"
    observed["usage"]["input_tokens"] = _PRIVATE
    assert adapter.observation["usage"]["input_tokens"] == 2320
    _assert_safe(adapter)


@pytest.mark.parametrize("change", ["budget", "temperature", "user", "system", "seed"])
def test_different_request_is_rejected_before_transport(change):
    calls = []
    adapter = _adapter(lambda request: calls.append(request))
    request = _request()
    if change in {"budget", "temperature", "seed"}:
        data = request.parameters.model_dump()
        data.update({"budget": {"max_output_tokens": 768},
                     "temperature": {"temperature": 0.64}, "seed": {"seed": 9}}[change])
        request = request.model_copy(update={"parameters": GenerationParameters(**data)})
    else:
        messages = list(request.messages)
        index = 1 if change == "user" else 0
        messages[index] = messages[index].model_copy(update={"content": _PRIVATE})
        request = request.model_copy(update={"messages": tuple(messages)})
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(request))
    assert calls == []
    assert adapter.observation["http_status"] is None
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("value,valid,position", [
    ('{"x":1}', True, None), ('  {"x":1}\n', True, None),
    ('{"x":1} trailing', False, 8), ('```json\n{"x":1}\n```', False, 0),
    ('{"x":', False, 5), ('', False, 0),
])
def test_failed_generation_is_parsed_integrally_without_repair(value, valid, position):
    observed, error = _invoke_error(_body(failed_generation=value))
    assert error.category is ErrorCategory.INVALID_REQUEST
    assert error.code == "groq_json_validate_failed"
    assert observed["provider_code"] == "json_validate_failed"
    assert observed["failed_generation"] == {"status": "observed", "present": True,
        "characters": len(value), "json_valid": valid, "error_position": position}
    assert observed["finish_reason"] is None
    assert all(v is None for v in observed["usage"].values())


@pytest.mark.parametrize("value", [None, 0, True, {}, [], [_PRIVATE]])
def test_nonstring_failed_generation_is_present_but_not_parsed(value):
    observed, _ = _invoke_error(_body(failed_generation=value))
    assert observed["failed_generation"] == {"status": "non_string", "present": True,
        "characters": None, "json_valid": None, "error_position": None}


def test_absence_is_not_false_json_or_zero_tokens():
    observed, _ = _invoke_error(b'{"error":{"code":"json_validate_failed"}}')
    assert observed["failed_generation"]["status"] == "absent"
    assert observed["failed_generation"]["present"] is None
    assert observed["failed_generation"]["json_valid"] is None
    assert observed["failed_generation"]["characters"] is None
    assert all(value is None for value in observed["usage"].values())


@pytest.mark.parametrize("body", [b"", b"{partial", b"\xff", b"[]", b"null"])
def test_unusable_complete_error_body_does_not_invent_generation_metadata(body):
    observed, _ = _invoke_error(body)
    assert observed["error_body"]["complete"] is True
    assert observed["failed_generation"]["present"] is None
    assert observed["provider_code"] is None


@pytest.mark.parametrize("extra", [0, 1])
def test_64_kib_bound_inclusive_and_no_prefix_parse(extra):
    body = _body(failed_generation='{"x":1}')
    body += b" " * (65536 - len(body) + extra)
    observed, _ = _invoke_error(body)
    assert observed["error_body"]["complete"] is (extra == 0)
    assert observed["failed_generation"]["json_valid"] is (True if extra == 0 else None)
    assert observed["provider_code"] == ("json_validate_failed" if extra == 0 else None)


class _Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks, *, wait_after=False, fail=False):
        self.chunks = chunks
        self.wait_after = wait_after
        self.fail = fail
        self.entered = asyncio.Event()
        self.closed = False
        self.count = 0
    async def __aiter__(self):
        for chunk in self.chunks:
            self.count += 1
            yield chunk
        self.entered.set()
        if self.wait_after:
            await asyncio.Event().wait()
        if self.fail:
            raise httpx.ReadError(_PRIVATE)
    async def aclose(self):
        self.closed = True


def _stream_adapter(stream, headers=None):
    return _adapter(lambda request: httpx.Response(400, stream=stream, headers=headers,
                                                  request=request))


@pytest.mark.parametrize("declared", [None, "1", "65536"])
def test_unknown_or_underreported_stream_length_still_cannot_bypass_bound(declared):
    stream = _Chunks([_body(failed_generation='{"x":1}'), b" " * 65536, b"not read"])
    adapter = _stream_adapter(stream, {} if declared is None else {"content-length": declared})
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert adapter.observation["error_body"]["status"] == "limit_exceeded"
    assert adapter.observation["provider_code"] is None
    assert adapter.observation["failed_generation"]["present"] is None
    assert stream.closed
    assert stream.count == 2
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("declared", ["65537", "-1", "invalid"])
def test_rejected_declared_length_never_reads_the_error_stream(declared):
    stream = _Chunks([_body()])
    adapter = _stream_adapter(stream, {"content-length": declared})
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(_request()))
    assert stream.count == 0
    assert stream.closed
    assert adapter.observation["error_body"]["complete"] is False
    assert adapter.observation["failed_generation"]["present"] is None


def test_partial_stream_io_failure_is_not_parsed_as_a_complete_error():
    stream = _Chunks([_body()], fail=True)
    adapter = _stream_adapter(stream)
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert caught.value.error.status_code == 400
    assert adapter.observation["error_body"]["status"] == "read_error"
    assert adapter.observation["failed_generation"]["present"] is None
    assert stream.closed
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("mode", ["deadline", "token", "task"])
def test_error_inspection_obeys_original_deadline_and_cancellation(mode):
    async def run():
        stream = _Chunks([_body()], wait_after=True)
        adapter = _stream_adapter(stream)
        token = CancellationToken()
        request = _request(cancellation=token, deadline=utc_now() + timedelta(
            seconds=0.05 if mode == "deadline" else 5))
        task = asyncio.create_task(adapter.generate_structured(request))
        await stream.entered.wait()
        if mode == "token":
            token.cancel()
        elif mode == "task":
            task.cancel()
        with pytest.raises(asyncio.CancelledError if mode == "task" else LLMInvocationError) as caught:
            await asyncio.wait_for(task, timeout=1)
        if mode != "task":
            expected = ErrorCategory.TIMEOUT if mode == "deadline" else ErrorCategory.CANCELLED
            assert caught.value.error.category is expected
            _assert_safe(adapter, caught.value)
        assert stream.closed
        assert adapter.observation["error_body"]["complete"] is False
        assert adapter.observation["failed_generation"]["json_valid"] is None
        _assert_safe(adapter)
    asyncio.run(run())


@pytest.mark.parametrize("reason,expected", [("length", "length"), ("content_filter", "content_filter"),
    ("tool_calls", "tool_calls"), ("function_call", "function_call"), (_PRIVATE, "unknown"),
    (None, None)])
def test_finish_observed_before_inherited_failure_without_inference(reason, expected):
    payload = _success()
    payload["choices"][0]["finish_reason"] = reason
    adapter = _adapter(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert adapter.observation["finish_reason"] == expected
    assert adapter.observation["usage"]["reasoning_tokens"] == 700
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("model", [_PRIVATE, _SECRET, "another-model", "", None, True, {}])
def test_unrecognized_reported_model_never_escapes_and_route_fails_closed(model):
    adapter = _adapter(lambda request: httpx.Response(200, json=_success(model=model)))
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(adapter.generate_structured(_request()))
    assert caught.value.error.category is ErrorCategory.TARGET_MISMATCH
    assert caught.value.error.evidence.provenance.effective_model.value is None
    assert adapter.observation["model"] is None
    _assert_safe(adapter, caught.value)


@pytest.mark.parametrize("value", [_PRIVATE, _SECRET, "req_" + _PRIVATE, "req_a/b", "", "x" * 300])
def test_untrusted_ids_are_absent_from_observation_and_public_error(value):
    observed, error = _invoke_error(_body(), headers={"x-request-id": value,
        "request-id": value, "x-generation-id": value})
    assert observed["request_id"] is None
    assert error.external_id is None


@pytest.mark.parametrize("value", [True, -1, "768", 1.5, {}, [_PRIVATE], None])
def test_numeric_usage_does_not_coerce_other_types(value):
    payload = _success(usage={"prompt_tokens": value, "completion_tokens": value,
        "total_tokens": value, "completion_tokens_details": {"reasoning_tokens": value}})
    adapter = _adapter(lambda request: httpx.Response(200, json=payload))
    asyncio.run(adapter.generate_structured(_request()))
    assert all(v is None for v in adapter.observation["usage"].values())
    _assert_safe(adapter)


def test_explicit_error_metadata_and_zero_are_preserved_without_free_text():
    payload = {"request_id": _REQUEST_ID, "model": GROQ_GPT_OSS_MODEL_ID,
        "usage": {"prompt_tokens": 2320, "completion_tokens": 0, "total_tokens": 2320,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
        "finish_reason": "length", "reasoning": _PRIVATE,
        "error": {"code": "json_validate_failed", "failed_generation": "{}", "message": _PRIVATE}}
    observed, _ = _invoke_error(json.dumps(payload).encode())
    assert observed["request_id"] == _REQUEST_ID
    assert observed["model"] == GROQ_GPT_OSS_MODEL_ID
    assert observed["finish_reason"] == "length"
    assert observed["usage"]["reasoning_tokens"] == 0
    assert observed["usage"]["output_tokens"] == 0