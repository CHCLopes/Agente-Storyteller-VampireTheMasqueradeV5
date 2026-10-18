"""NVIDIA hosted NIM policy behind the provider-neutral LLM boundary.

The adapter is intentionally bound to the one hosted model selected for the
synthetic narrator evaluation.  It reuses the OpenAI-compatible transport, but
does not pretend that a provider field was reported when NVIDIA only makes the
route observable through its fixed official endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import SecretStr

from ..contract import (
    CapabilitySet,
    CostMeasurement,
    ErrorCategory,
    GenerationRequest,
    InvocationEvidence,
    LLMInvocationError,
    OperationPhase,
    Provenance,
    ProvenanceSource,
    ProvenanceValue,
    StructuredGenerationRequest,
    TokenUsage,
    utc_now,
)
from .openai_compatible import OpenAICompatibleAdapter


NVIDIA_NIM_OFFICIAL_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_PROVIDER_LABEL = "NVIDIA NIM"
NVIDIA_NIM_MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b"


class NvidiaNimAdapter(OpenAICompatibleAdapter):
    """Bind the NVIDIA hosted trial endpoint to one explicit logical model."""

    def __init__(
        self,
        *,
        base_url: str,
        capability_set: CapabilitySet,
        api_key: SecretStr | None,
        reasoning_effort: str | None = None,
        adapter_version: str = "1.0",
        transport: Any = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if cleaned_url != NVIDIA_NIM_OFFICIAL_BASE_URL:
            raise ValueError(
                "NVIDIA NIM adapter requires the exact official hosted API base URL."
            )
        if (
            capability_set.target.provider.strip().casefold()
            != NVIDIA_NIM_PROVIDER_LABEL.casefold()
        ):
            raise ValueError(
                f"NVIDIA NIM adapter target provider must be {NVIDIA_NIM_PROVIDER_LABEL}."
            )
        if capability_set.target.model.strip() != NVIDIA_NIM_MODEL_ID:
            raise ValueError(
                "NVIDIA NIM adapter requires the fixed evaluated model id "
                f"{NVIDIA_NIM_MODEL_ID}."
            )
        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError(
                "NVIDIA NIM adapter requires an explicit non-empty LLM_API_KEY."
            )
        if reasoning_effort not in {None, "none"}:
            raise ValueError(
                "NVIDIA NIM reasoning effort is not supported by this adapter; "
                "thinking is disabled for structured narrator output."
            )

        super().__init__(
            base_url=cleaned_url,
            capability_set=capability_set,
            api_key=api_key,
            reasoning_effort=None,
            adapter_name="nvidia-nim-chat-completions",
            adapter_version=adapter_version,
            transport=transport,
        )

    def _payload(
        self,
        request: GenerationRequest,
        *,
        stream: bool,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = super()._payload(
            request,
            stream=stream,
            response_format=response_format,
        )
        # The Ultra model can otherwise spend the complete output allowance on
        # reasoning.  NVIDIA recommends disabling thinking for concise and JSON
        # output so the product receives the visible response it can validate.
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        # The hosted reference documents SSE, but not include_usage.  Do not
        # send an unverified optional parameter; absent measurements stay
        # explicitly unavailable under LLM-001.
        payload.pop("stream_options", None)
        return payload

    def _emulated_response_format(
        self, request: StructuredGenerationRequest
    ) -> dict[str, Any]:
        # NVIDIA documents JSON mode for this NIM, not hosted JSON-Schema
        # enforcement.  Pydantic validation remains the product authority.
        return {"type": "json_object"}

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
                effective_provider=ProvenanceValue.observed(
                    NVIDIA_NIM_PROVIDER_LABEL
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

    def _validate_final_evidence(
        self, request: GenerationRequest, evidence: InvocationEvidence
    ) -> None:
        provenance = evidence.provenance
        if (
            provenance.effective_provider.source is not ProvenanceSource.OBSERVED
            or provenance.effective_provider.value != NVIDIA_NIM_PROVIDER_LABEL
            or provenance.effective_model.source is not ProvenanceSource.REPORTED
            or provenance.effective_model.value is None
        ):
            raise LLMInvocationError(
                self._make_error(
                    request=request,
                    evidence=evidence,
                    category=ErrorCategory.TARGET_MISMATCH,
                    code="nvidia_nim_unverified_target_provenance",
                    phase=OperationPhase.RESPONSE,
                    safe_message="NVIDIA NIM target provenance could not be verified.",
                )
            )

    def _parse_cost(self, payload: dict[str, Any]) -> CostMeasurement:
        # The hosted trial response does not document per-call monetary cost.
        return CostMeasurement.unavailable()
