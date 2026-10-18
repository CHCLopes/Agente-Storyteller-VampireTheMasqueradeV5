"""Groq quota diagnostics must preserve dimensions without exposing raw errors."""

import asyncio
import json
from typing import Any

import httpx
import pytest

from api.llm.contract import (
    ErrorCategory,
    LLMInvocationError,
    RateLimitOrigin,
    StreamEventKind,
    StreamingGenerationRequest,
    validate_stream_events,
)

from .test_groq_adapter import _SECRET, _adapter, _request


_PRIVATE = "syntheticcampaignsecretDoNotPersist123"
_HEADERS = {
    "x-ratelimit-limit-requests": "1000",
    "x-ratelimit-remaining-requests": "994",
    "x-ratelimit-reset-requests": "2m59.56s",
    "x-ratelimit-limit-tokens": "8000",
    "x-ratelimit-remaining-tokens": "0",
    "x-ratelimit-reset-tokens": "7.66s",
}


class _UnreadBody(httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.closed = False

    async def __aiter__(self):
        for offset in range(0, len(self.content), 4096):
            yield self.content[offset : offset + 4096]

    async def aclose(self) -> None:
        self.closed = True


def _encoded_body(error: dict[str, Any]) -> bytes:
    return json.dumps({"error": error}).encode()


def _invoke_error(
    mode: str,
    *,
    body: bytes = b"{}",
    headers: dict[str, str] | None = None,
    status: int = 429,
):
    unread_body = _UnreadBody(body)

    def handler(request: httpx.Request) -> httpx.Response:
        raw_headers = [
            (name.encode("ascii"), value.encode("utf-8"))
            for name, value in (headers or {}).items()
        ]
        if mode == "stream":
            return httpx.Response(
                status, headers=raw_headers, stream=unread_body, request=request
            )
        return httpx.Response(
            status, headers=raw_headers, content=body, request=request
        )

    if mode == "text":
        with pytest.raises(LLMInvocationError) as caught:
            asyncio.run(_adapter(handler).generate_text(_request()))
        error = caught.value.error
    else:
        async def collect():
            values = _request().model_dump()
            values.pop("required_capabilities")
            request = StreamingGenerationRequest(**values)
            return [event async for event in _adapter(handler).stream_text(request)]

        events = asyncio.run(collect())
        validate_stream_events(events)
        assert [event.kind for event in events] == [StreamEventKind.FAILED]
        assert unread_body.closed is True
        error = events[0].error
        assert error is not None

    assert error.status_code == status
    assert error.partial_output is False
    serialized = error.model_dump_json()
    assert _SECRET not in serialized
    assert _PRIVATE not in serialized
    assert "entrada sintética" not in serialized
    return error


def _quotas(error) -> dict[str, dict[str, Any]]:
    evidence = error.rate_limit
    assert evidence is not None
    assert evidence.origin is RateLimitOrigin.UNKNOWN
    assert evidence.limit is None
    assert evidence.remaining is None
    assert evidence.reset is None
    return {
        quota.resource: quota.model_dump(mode="json")
        for quota in evidence.quotas
    }


@pytest.mark.parametrize("mode", ["text", "stream"])
@pytest.mark.parametrize("resource", ["requests", "tokens"])
def test_429_retains_separate_quota_windows_and_allowlisted_error_type(
    mode: str, resource: str
) -> None:
    error = _invoke_error(
        mode,
        headers={**_HEADERS, "retry-after": "4"},
        body=_encoded_body(
            {
                "code": "rate_limit_exceeded",
                "type": resource,
                "message": f"{_SECRET} {_PRIVATE} entrada sintética",
                "organization": _PRIVATE,
                "metadata": {"api_key": _SECRET},
            }
        ),
    )

    assert error.category is ErrorCategory.RATE_LIMITED
    assert error.code == "http_429"
    assert error.retryable is True
    assert error.retry_after_seconds == 4
    quotas = _quotas(error)
    assert quotas == {
        "requests": {
            "resource": "requests",
            "window_seconds": 86400,
            "limit": 1000,
            "remaining": 994,
            "reset_after_seconds": pytest.approx(179.56),
        },
        "tokens": {
            "resource": "tokens",
            "window_seconds": 60,
            "limit": 8000,
            "remaining": 0,
            "reset_after_seconds": pytest.approx(7.66),
        },
    }
    assert error.rate_limit.provider_code == "rate_limit_exceeded"
    assert error.rate_limit.resource == resource


@pytest.mark.parametrize("mode", ["text", "stream"])
def test_quota_snapshot_does_not_infer_limiting_resource_or_retry_after(
    mode: str,
) -> None:
    error = _invoke_error(mode, headers=_HEADERS)

    assert len(_quotas(error)) == 2
    assert error.rate_limit.resource is None
    assert error.rate_limit.provider_code is None
    assert error.retry_after_seconds is None


@pytest.mark.parametrize("mode", ["text", "stream"])
def test_429_without_metadata_remains_unknown_and_keeps_no_quota(mode: str) -> None:
    error = _invoke_error(mode)

    assert _quotas(error) == {}
    assert error.rate_limit.resource is None
    assert error.rate_limit.provider_code is None
    assert error.retry_after_seconds is None


@pytest.mark.parametrize("mode", ["text", "stream"])
@pytest.mark.parametrize(
    "invalid_value",
    ["-1", "1.5", "1e3", "8000 tokens", "٨٠٠٠", "9" * 200, _PRIVATE],
)
def test_invalid_or_secret_shaped_quota_headers_do_not_cross_boundary(
    mode: str, invalid_value: str
) -> None:
    error = _invoke_error(
        mode,
        headers={name: invalid_value for name in _HEADERS},
        body=_encoded_body(
            {"code": _PRIVATE, "type": _PRIVATE, "message": _PRIVATE}
        ),
    )

    assert _quotas(error) == {}
    assert error.rate_limit.provider_code is None
    assert error.rate_limit.resource is None


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        ("0s", 0.0),
        ("2m59.56s", 179.56),
        ("7.66s", 7.66),
        ("250ms", 0.25),
        ("1h2m3s4ms", 3723.004),
    ],
)
def test_duration_headers_support_documented_units(
    duration: str, expected: float
) -> None:
    error = _invoke_error(
        "text", headers={"x-ratelimit-reset-tokens": duration}
    )

    quota = _quotas(error)["tokens"]
    assert quota["limit"] is None
    assert quota["remaining"] is None
    assert quota["reset_after_seconds"] == pytest.approx(expected)


@pytest.mark.parametrize("duration", ["-1s", "NaNs", "infs", "1d", "7.5", "1sJUNK"])
def test_invalid_duration_does_not_discard_valid_limit(duration: str) -> None:
    error = _invoke_error(
        "text",
        headers={
            "x-ratelimit-limit-tokens": "8000",
            "x-ratelimit-reset-tokens": duration,
        },
    )

    assert _quotas(error)["tokens"] == {
        "resource": "tokens",
        "window_seconds": 60,
        "limit": 8000,
        "remaining": None,
        "reset_after_seconds": None,
    }


@pytest.mark.parametrize("mode", ["text", "stream"])
@pytest.mark.parametrize(
    "body",
    [
        b"{invalid-json",
        b"null",
        b'{"error":[]}',
        _encoded_body(
            {
                "code": "rate_limit_exceeded",
                "type": "tokens",
                "message": _PRIVATE + "x" * (64 * 1024),
            }
        ),
    ],
    ids=["invalid-json", "null-body", "invalid-error-shape", "oversized-body"],
)
def test_invalid_or_oversized_body_preserves_valid_headers_only(
    mode: str, body: bytes
) -> None:
    error = _invoke_error(mode, body=body, headers=_HEADERS)

    assert error.category is ErrorCategory.RATE_LIMITED
    assert len(_quotas(error)) == 2
    assert error.rate_limit.provider_code is None
    assert error.rate_limit.resource is None


@pytest.mark.parametrize("mode", ["text", "stream"])
def test_groq_does_not_mix_generic_headers_into_dimensional_quotas(mode: str) -> None:
    error = _invoke_error(
        mode,
        headers={
            **_HEADERS,
            "x-ratelimit-limit": "20",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1788561200",
            "x-private-diagnostic": _PRIVATE,
        },
    )

    assert len(_quotas(error)) == 2


@pytest.mark.parametrize("mode", ["text", "stream"])
def test_non_429_errors_do_not_claim_rate_limit_evidence(mode: str) -> None:
    error = _invoke_error(
        mode,
        status=503,
        headers=_HEADERS,
        body=_encoded_body(
            {"code": "rate_limit_exceeded", "type": "tokens", "message": _PRIVATE}
        ),
    )

    assert error.category is ErrorCategory.PROVIDER_UNAVAILABLE
    assert error.code == "http_503"
    assert error.rate_limit is None
