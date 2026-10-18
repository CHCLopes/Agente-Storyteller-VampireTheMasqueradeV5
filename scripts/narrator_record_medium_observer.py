"""Explicit medium-effort policy for one frozen synthetic observation only.

Historical Groq profiles remain unchanged. The experimental constructor binds
its own exact target before initializing the shared transport directly at medium.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr

from api.llm.adapters.groq import GroqAdapter, GROQ_GPT_OSS_MODEL_ID, GROQ_OFFICIAL_BASE_URL
from api.llm.adapters.openai_compatible import OpenAICompatibleAdapter
from api.llm.contract import CapabilitySet, GenerationRequest, LLMTarget, StructuredGenerationRequest
from scripts.narrator_record_budget_observer import BudgetObservationAdapter, _unavailable_observation

APPROVED_PAYLOAD_SHA256 = "5037c4c4e040c6ce800d848217951374ef19489c18bd4857aaf5ca652e13cdaf"
MEDIUM_PROFILE = "record-reasoning-medium-gpt-oss-120b-groq-free-synthetic-medium"
ADAPTER_NAME = "groq-chat-completions-record-medium-probe"


def _require_medium_target(target: LLMTarget) -> None:
    if (target.provider != "Groq" or target.model != GROQ_GPT_OSS_MODEL_ID
            or target.profile != MEDIUM_PROFILE):
        raise ValueError("Medium observer requires its exact synthetic Groq target.")


def _canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def build_medium_payload(request: StructuredGenerationRequest) -> dict[str, Any]:
    """Build the native body without constructing a client or reading a credential."""
    _require_medium_target(request.target)
    builder = object.__new__(GroqAdapter)
    builder._reasoning_effort = "medium"
    return GroqAdapter._payload(builder, request, stream=False,
                               response_format=builder._native_response_format(request))


class MediumObservationAdapter(BudgetObservationAdapter):
    """Inherit bounded observation and public errors under an isolated policy."""

    def __init__(self, *, base_url: str, capability_set: CapabilitySet,
                 api_key: SecretStr | None, reasoning_effort: str | None,
                 adapter_version: str = "1.0", transport: Any = None) -> None:
        if base_url != GROQ_OFFICIAL_BASE_URL:
            raise ValueError("Medium observer requires the exact official Groq base URL.")
        _require_medium_target(capability_set.target)
        if reasoning_effort != "medium":
            raise ValueError("Medium observer requires reasoning_effort='medium'.")
        if not isinstance(api_key, SecretStr) or not api_key.get_secret_value().strip():
            raise ValueError("Medium observer requires an explicit non-empty SecretStr credential.")
        # Deliberately initialize the transport under this new policy, never
        # construct the historical low profile or change its effort afterward.
        OpenAICompatibleAdapter.__init__(
            self, base_url=base_url, capability_set=capability_set, api_key=api_key,
            reasoning_effort="medium", adapter_name=ADAPTER_NAME,
            adapter_version=adapter_version, transport=transport,
        )
        self._observation = _unavailable_observation()
        self._dispatch_started = False

    def _payload(self, request: GenerationRequest, *, stream: bool,
                 response_format: dict[str, Any] | None) -> dict[str, Any]:
        payload = GroqAdapter._payload(self, request, stream=stream,
                                       response_format=response_format)
        if stream or _canonical_sha(payload) != APPROVED_PAYLOAD_SHA256 or self._dispatch_started:
            raise ValueError("Medium observer requires its single approved fixed request.")
        self._dispatch_started = True
        return payload
