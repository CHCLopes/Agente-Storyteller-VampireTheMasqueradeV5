"""Groq HTTP 400 codes are diagnostic observations, never local schema verdicts."""

import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel

from api.llm.adapters.groq import GROQ_GPT_OSS_MODEL_ID, GROQ_QWEN_MODEL_ID
from api.llm.contract import (
    ErrorCategory, LLMInvocationError, MeasurementStatus, OperationPhase,
    ProvenanceSource, StreamingGenerationRequest, StructuredGenerationRequest,
    StreamEventKind, utc_now, validate_stream_events,
)
from scripts import evaluate_narrator_models as evaluator

from .test_groq_adapter import _SECRET, _adapter, _request, _success_payload, _target
from .test_openai_compatible_adapter import _traceback_locals


_PRIVATE = "syntheticPrivateCampaignDetailNeverPersist"
_PROVIDER_CODE = "json_validate_failed"
_LOCAL_CODE = "groq_json_validate_failed"


class _Answer(BaseModel):
    answer: str


def _encoded(error):
    return json.dumps({"error": error}).encode()


def _invoke(mode, body, *, status=400, model=GROQ_GPT_OSS_MODEL_ID):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, content=body, request=request)

    adapter = _adapter(handler, target=_target(model=model))
    request = _request(model=model)
    with pytest.raises(LLMInvocationError) as caught:
        if mode == "structured":
            values = request.model_dump(exclude={"required_capabilities"})
            asyncio.run(adapter.generate_structured(
                StructuredGenerationRequest(**values, response_model=_Answer)
            ))
        else:
            asyncio.run(adapter.generate_text(request))
    exception = caught.value
    assert len(calls) == 1
    assert exception.__cause__ is None
    assert exception.__context__ is None
    for serialized in (
        exception.error.model_dump_json(), repr(exception), _traceback_locals(exception),
        json.dumps(evaluator._normalized_error_payload(exception.error)),
    ):
        assert _SECRET not in serialized
        assert _PRIVATE not in serialized
        assert "entrada sintética" not in serialized
    return exception.error


def _assert_http_400(error, expected_code="http_400"):
    assert error.category is ErrorCategory.INVALID_REQUEST
    assert error.code == expected_code
    assert error.status_code == 400
    assert error.phase is OperationPhase.CONNECT
    assert error.retryable is False
    assert error.retry_after_seconds is None
    assert error.safe_message == "LLM target rejected the request."
    assert error.partial_output is False
    assert error.structure_validation is None
    assert error.rate_limit is None
    assert error.evidence.provenance.effective_provider.value == "Groq"
    assert error.evidence.provenance.effective_model.source is ProvenanceSource.UNKNOWN
    assert error.evidence.usage.status is MeasurementStatus.UNAVAILABLE
    assert error.evidence.cost.status is MeasurementStatus.UNAVAILABLE


@pytest.mark.parametrize("mode", ["text", "structured"])
@pytest.mark.parametrize("model", [GROQ_GPT_OSS_MODEL_ID, GROQ_QWEN_MODEL_ID])
def test_http_400_retains_only_exact_provider_code_without_reclassifying_or_retry(mode, model):
    error = _invoke(mode, _encoded({
        "code": _PROVIDER_CODE,
        "message": f"{_SECRET} {_PRIVATE} entrada sintética",
        "failed_generation": {"answer": _PRIVATE},
        "metadata": {"api_key": _SECRET},
    }), model=model)

    _assert_http_400(error, _LOCAL_CODE)
    saved = evaluator._normalized_error_payload(error)
    assert saved["code"] == _LOCAL_CODE
    assert saved["category"] == "invalid_request"
    assert saved["status_code"] == 400
    assert "structure_validation" not in saved


@pytest.mark.parametrize("mode", ["text", "structured"])
@pytest.mark.parametrize("code", [
    None, "", "tool_use_failed", "JSON_VALIDATE_FAILED", " json_validate_failed",
    "json_validate_failed ", "prefix_json_validate_failed", "json_validate_failed_suffix",
    _PRIVATE, _SECRET, 400, True, [], {"code": _PROVIDER_CODE},
])
def test_unknown_nonexact_or_nonstring_codes_remain_generic(mode, code):
    _assert_http_400(_invoke(mode, _encoded({
        "code": code, "message": _PRIVATE, "failed_generation": _SECRET,
    })))


@pytest.mark.parametrize("mode", ["text", "structured"])
@pytest.mark.parametrize("body", [
    b"", b"{invalid", b"null", b"[]", b'{"error":null}', b'{"error":[]}',
    b'{"error":"json_validate_failed"}', b"\xff",
    b"[" * 1200 + b"]" * 1200,
    json.dumps({"code": _PROVIDER_CODE}).encode(),
    _encoded({"message": _PROVIDER_CODE, "failed_generation": _PROVIDER_CODE}),
    _encoded({"metadata": {"code": _PROVIDER_CODE}}),
])
def test_invalid_or_misplaced_envelopes_do_not_infer_a_code(mode, body):
    _assert_http_400(_invoke(mode, body))


@pytest.mark.parametrize("mode", ["text", "structured"])
@pytest.mark.parametrize("extra,expected", [(0, _LOCAL_CODE), (1, "http_400")])
def test_32_kib_envelope_limit_is_inclusive_and_never_accepts_a_larger_body(mode, extra, expected):
    body = _encoded({"code": _PROVIDER_CODE, "message": _PRIVATE})
    body += b" " * (32 * 1024 - len(body) + extra)
    _assert_http_400(_invoke(mode, body), expected)


@pytest.mark.parametrize("mode", ["text", "structured"])
@pytest.mark.parametrize("status,category", [
    (401, ErrorCategory.AUTHENTICATION_FAILED),
    (422, ErrorCategory.INVALID_REQUEST),
    (429, ErrorCategory.RATE_LIMITED),
    (500, ErrorCategory.PROVIDER_UNAVAILABLE),
    (503, ErrorCategory.PROVIDER_UNAVAILABLE),
])
def test_other_http_statuses_keep_their_existing_classification(mode, status, category):
    error = _invoke(mode, _encoded({"code": _PROVIDER_CODE}), status=status)
    assert error.category is category
    assert error.code == f"http_{status}"
    assert error.status_code == status
    assert error.structure_validation is None


@pytest.mark.parametrize("mode", ["text", "structured"])
def test_successful_response_does_not_interpret_an_error_shaped_extra_field(mode):
    calls = []

    def handler(request):
        calls.append(request)
        payload = _success_payload(json.dumps({"answer": "valid"}))
        payload["error"] = {"code": _PROVIDER_CODE, "failed_generation": _PRIVATE}
        return httpx.Response(200, json=payload, request=request)

    adapter = _adapter(handler)
    request = _request()
    if mode == "structured":
        values = request.model_dump(exclude={"required_capabilities"})
        result = asyncio.run(adapter.generate_structured(
            StructuredGenerationRequest(**values, response_model=_Answer)
        ))
        assert result.value.answer == "valid"
    else:
        result = asyncio.run(adapter.generate_text(request))
        assert json.loads(result.content) == {"answer": "valid"}
    assert len(calls) == 1


@pytest.mark.parametrize("content", ["not valid json", "{}"])
def test_http_200_local_structure_failure_is_not_recast_as_provider_http_400(content):
    payload = _success_payload(content, model=GROQ_GPT_OSS_MODEL_ID)
    payload["error"] = {"code": _PROVIDER_CODE, "failed_generation": _PRIVATE}
    error = _invoke("structured", json.dumps(payload).encode(), status=200)
    assert error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    assert error.code == "structured_output_schema_mismatch"
    assert error.phase is OperationPhase.STRUCTURE_VALIDATION
    assert error.structure_validation is not None


def test_unconsumed_stream_http_400_is_closed_without_reading_its_body():
    class UnreadBody(httpx.AsyncByteStream):
        reads = 0
        closed = False

        async def __aiter__(self):
            self.reads += 1
            yield _encoded({"code": _PROVIDER_CODE, "failed_generation": _PRIVATE})

        async def aclose(self):
            self.closed = True

    body = UnreadBody()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, stream=body, request=request)

    async def collect():
        request = StreamingGenerationRequest(**_request().model_dump(
            exclude={"required_capabilities"}
        ))
        return [event async for event in _adapter(handler).stream_text(request)]

    events = asyncio.run(collect())
    validate_stream_events(events)
    assert [event.kind for event in events] == [StreamEventKind.FAILED]
    _assert_http_400(events[0].error)
    assert len(calls) == 1
    assert body.reads == 0
    assert body.closed is True


def test_provider_code_enrichment_changes_no_other_normalized_error_field(monkeypatch):
    from api.llm.adapters.openai_compatible import OpenAICompatibleAdapter

    adapter = _adapter(lambda _: pytest.fail("unexpected dispatch"))
    request = _request()
    started_at = utc_now()
    evidence = adapter._evidence(request=request, started_at=started_at)
    monkeypatch.setattr(adapter, "_evidence", lambda **_: evidence)
    response = httpx.Response(
        400, content=_encoded({"code": _PROVIDER_CODE}),
        headers={"retry-after": "4", "x-request-id": "synthetic-request-id"},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    exception = httpx.HTTPStatusError(_PRIVATE, request=response.request, response=response)
    arguments = dict(
        request=request, started_at=started_at, phase=OperationPhase.CONNECT,
        exc=exception, response=response, partial_output=True,
    )
    baseline = OpenAICompatibleAdapter._normalize_exception(adapter, **arguments)
    enriched = adapter._normalize_exception(**arguments)
    assert enriched.code == _LOCAL_CODE
    assert baseline.code == "http_400"
    assert enriched.model_dump(exclude={"code"}) == baseline.model_dump(exclude={"code"})


@pytest.mark.parametrize("exception_type", [ValueError, httpx.ReadTimeout, httpx.ConnectError])
def test_attached_http_400_does_not_override_a_non_http_exception(exception_type):
    adapter = _adapter(lambda _: pytest.fail("unexpected dispatch"))
    request = _request()
    response = httpx.Response(
        400, content=_encoded({"code": _PROVIDER_CODE}),
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    error = adapter._normalize_exception(
        request=request, started_at=utc_now(), phase=OperationPhase.CONNECT,
        exc=exception_type(_PRIVATE), response=response,
    )
    assert error.code not in {_LOCAL_CODE, "http_400"}


def test_already_normalized_http_400_is_not_reinterpreted_from_an_attached_body():
    original = _invoke("text", b"{}")
    adapter = _adapter(lambda _: pytest.fail("unexpected dispatch"))
    response = httpx.Response(
        400, content=_encoded({"code": _PROVIDER_CODE}),
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    request = _request()
    error = adapter._normalize_exception(
        request=request, started_at=utc_now(), phase=OperationPhase.CONNECT,
        exc=LLMInvocationError(original), response=response,
    )
    assert error is original
    assert error.code == "http_400"
