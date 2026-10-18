"""Sanitized observation of one frozen synthetic request, outside product runtime.

The response hook is awaited inside the inherited controlled POST, so inspecting
an error cannot obtain a new deadline or bypass cancellation. Only complete error
bodies of at most 64 KiB are parsed. No rejected output or free text is retained.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
from typing import Any

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

import httpx
from pydantic import SecretStr

from api.llm.adapters.groq import GroqAdapter, GROQ_GPT_OSS_MODEL_ID
from api.llm.contract import CapabilitySet, GenerationRequest

APPROVED_PAYLOAD_SHA256 = "90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f"
MAX_ERROR_BODY_BYTES = 64 * 1024
_REQUEST_ID = re.compile(r"req_[a-z0-9]{26}\Z")
_FINISH_REASONS = frozenset({"stop", "length", "content_filter", "tool_calls", "function_call"})
_PROVIDER_CODES = frozenset({"json_validate_failed", "rate_limit_exceeded"})


def _safe_request_id(value: Any) -> str | None:
    return value if isinstance(value, str) and _REQUEST_ID.fullmatch(value) else None


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _unavailable_observation() -> dict[str, Any]:
    return {
        "schema": "storyteller.eval.record-budget-observation.v1",
        "http_status": None, "request_id": None, "provider_code": None,
        "model": None, "finish_reason": None,
        "usage": {"input_tokens": None, "output_tokens": None,
                  "total_tokens": None, "reasoning_tokens": None},
        "error_body": {"status": "unavailable", "complete": None,
                       "bytes": None, "json_valid": None},
        "failed_generation": {"status": "unavailable", "present": None,
            "characters": None, "json_valid": None, "error_position": None},
    }


class BudgetObservationAdapter(GroqAdapter):
    """Same adapter constructor, with a one-use guard for the approved body.

    ``observation`` returns a detached JSON-safe snapshot. None means unavailable,
    not zero/false. Reported models outside the exact target become unavailable
    in both the snapshot and inherited evidence; existing route gates reject them.
    """

    def __init__(self, *, base_url: str, capability_set: CapabilitySet,
                 api_key: SecretStr | None, reasoning_effort: str | None,
                 adapter_version: str = "1.0", transport: Any = None) -> None:
        super().__init__(base_url=base_url, capability_set=capability_set,
                         api_key=api_key, reasoning_effort=reasoning_effort,
                         adapter_version=adapter_version, transport=transport)
        self._observation = _unavailable_observation()
        self._dispatch_started = False

    @property
    def observation(self) -> dict[str, Any]:
        return copy.deepcopy(self._observation)

    def _payload(self, request: GenerationRequest, *, stream: bool,
                 response_format: dict[str, Any] | None) -> dict[str, Any]:
        payload = super()._payload(request, stream=stream, response_format=response_format)
        fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if stream or fingerprint != APPROVED_PAYLOAD_SHA256 or self._dispatch_started:
            raise ValueError("Budget observer requires its single approved fixed request.")
        self._dispatch_started = True
        return payload

    def _new_client(self) -> httpx.AsyncClient:
        client = super()._new_client()
        # HTTPX otherwise buffers nonstream errors before our adapter can bound
        # them. This hook runs inside _controlled(client.post(...), request).
        client.event_hooks["response"].append(self._observe_response)
        return client

    @staticmethod
    def _external_id(response: httpx.Response | None) -> str | None:
        if response is None:
            return None
        for name in ("x-request-id", "request-id", "x-generation-id"):
            value = _safe_request_id(response.headers.get(name))
            if value is not None:
                return value
        return None

    def _effective_model(self, payload: dict[str, Any]) -> str | None:
        value = payload.get("model")
        return GROQ_GPT_OSS_MODEL_ID if value == GROQ_GPT_OSS_MODEL_ID else None

    def _validate_response_payload(self, request: GenerationRequest,
                                   payload: dict[str, Any]) -> None:
        # Called before the inherited finish gate, including length failures.
        self._observe_metadata(payload)
        super()._validate_response_payload(request, payload)

    def _observe_metadata(self, payload: dict[str, Any]) -> None:
        observed = self._observation
        if observed["request_id"] is None:
            observed["request_id"] = _safe_request_id(payload.get("request_id"))
            x_groq = payload.get("x_groq")
            if observed["request_id"] is None and isinstance(x_groq, dict):
                observed["request_id"] = _safe_request_id(x_groq.get("id"))
        observed["model"] = self._effective_model(payload)
        usage = payload.get("usage")
        if isinstance(usage, dict):
            for field, provider_field in (("input_tokens", "prompt_tokens"),
                    ("output_tokens", "completion_tokens"), ("total_tokens", "total_tokens")):
                observed["usage"][field] = _count(usage.get(provider_field))
            details = usage.get("completion_tokens_details")
            if isinstance(details, dict):
                observed["usage"]["reasoning_tokens"] = _count(details.get("reasoning_tokens"))
        # Only explicit fields, never inferred from an output count or parse error.
        choice = None
        choices = payload.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
        reason = choice.get("finish_reason") if choice is not None else payload.get("finish_reason")
        if reason is not None:
            observed["finish_reason"] = reason if isinstance(reason, str) and reason in _FINISH_REASONS else "unknown"

    def _observe_error_body(self, body: bytes) -> None:
        state = self._observation["error_body"]
        state.update(status="complete", complete=True, bytes=len(body))
        try:
            payload = json.loads(body)
        except (ValueError, TypeError):
            state["json_valid"] = False
            return
        except RecursionError:
            state["status"] = "parser_limit"
            return
        state["json_valid"] = True
        if not isinstance(payload, dict):
            return
        self._observe_metadata(payload)
        error = payload.get("error")
        if not isinstance(error, dict):
            return
        code = error.get("code")
        if isinstance(code, str) and code in _PROVIDER_CODES:
            self._observation["provider_code"] = code
        failed = self._observation["failed_generation"]
        if "failed_generation" not in error:
            failed.update(status="absent", present=None)
            return
        failed["present"] = True
        value = error["failed_generation"]
        if not isinstance(value, str):
            failed["status"] = "non_string"
            return
        failed.update(status="observed", characters=len(value))
        try:
            # Deliberately no strip/fences/repair or substring selection. This is
            # acceptance by Python json.loads, not schema or semantic validation.
            json.loads(value)
        except json.JSONDecodeError as exc:
            failed.update(json_valid=False, error_position=exc.pos)
        except (ValueError, RecursionError):
            failed["status"] = "parser_limit"
        else:
            failed["json_valid"] = True

    async def _observe_response(self, response: httpx.Response) -> None:
        self._observation["http_status"] = response.status_code
        self._observation["request_id"] = self._external_id(response)
        if response.status_code < 300:
            return
        state = self._observation["error_body"]
        state.update(status="reading", complete=False)
        body: bytes | None = None
        try:
            declared = response.headers.get("content-length")
            try:
                length = int(declared) if declared is not None else None
            except ValueError:
                length = -1
            if length is not None and (length < 0 or length > MAX_ERROR_BODY_BYTES):
                state["status"] = "limit_exceeded" if length > MAX_ERROR_BODY_BYTES else "invalid_content_length"
            else:
                chunks: list[bytes] = []
                total = 0
                try:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_ERROR_BODY_BYTES:
                            state["status"] = "limit_exceeded"
                            break
                        chunks.append(chunk)
                    else:
                        body = b"".join(chunks)
                except (httpx.HTTPError, OSError, RuntimeError, ValueError):
                    state["status"] = "read_error"
                if body is not None:
                    self._observe_error_body(body)
        except asyncio.CancelledError:
            state["status"] = "interrupted"
            raise
        finally:
            await response.aclose()
        # Stop HTTPX's subsequent implicit aread. A complete bounded body remains
        # available to the unchanged Groq normalizer (whose HTTP400 code parser
        # has its own stricter 32 KiB limit); an incomplete body is never supplied.
        response._content = body if body is not None else b""
        response.raise_for_status()