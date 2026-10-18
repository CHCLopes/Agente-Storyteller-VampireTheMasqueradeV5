"""Prepared, paid-gated closed-world evaluation for GPT-5.6 Luna low."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from pydantic import SecretStr, ValidationError

from api.llm.contract import (
    AdapterIdentity, CostMeasurement, ErrorCategory, InvocationEvidence,
    LLMInvocationError, LLMTarget, MeasurementStatus, NormalizedError,
    OperationPhase, Provenance, ProvenanceValue, StructuredGenerationResult,
    TokenUsage, utc_now,
)
from api.llm.structure_diagnostics import build_structure_validation_evidence
from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_closed_world_render_plan as offline
from scripts import narrator_source_profile as source_profile


VERSION = "openai-luna-low-live-v1"
HYPOTHESIS_ID = "HYP-006-OPENAI-LUNA-LOW-L1"
KEY_ENV = "STORYTELLER_OPENAI_LUNA_KEY"
BASE_URL = "https://api.openai.com/v1"
MANIFEST = ROOT / "evals/narrator/openai_luna_low_candidate_2026-09-26.json"
GATE = ROOT / "evals/narrator/reports/openai-luna-low-live-gate-2026-09-26.json"
CANDIDATE_ID = "gpt-5.6-luna-openai-low-synthetic"
TARGETS = {CANDIDATE_ID: {"profile": "closed-world-gpt-5.6-luna-low", "model": "gpt-5.6-luna", "reasoning": "low"}}
CASE_IDS = (
    "hold-silent-bell", "authorized-single-bell", "known-sealed-tube",
    "unknown-glass-disc", "favorable-shutter-result", "unfavorable-slab-result",
    "npc-protected-code", "ambiguous-sealed-boxes",
)
SCHEDULE = tuple((CANDIDATE_ID, case) for case in CASE_IDS)


class OpenAIResponsesAdapter:
    """Minimal Responses API adapter used only by the bounded Luna evaluation."""

    def __init__(
        self, *, base_url: str, capability_set, api_key: SecretStr,
        reasoning_effort: str | None, transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/responses"
        self._capability_set = capability_set
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._transport = transport
        self._identity = AdapterIdentity(name="openai-responses-eval", version="1.0")

    def _native_response_format(self, request) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": request.response_model.__name__,
            "strict": True,
            "schema": request.response_model.model_json_schema(),
        }

    def _payload(self, request, *, stream: bool, response_format: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.target.model,
            "input": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "stream": stream,
            "store": False,
            "max_output_tokens": request.parameters.max_output_tokens,
            "reasoning": {"effort": self._reasoning_effort},
            "text": {"format": response_format or self._native_response_format(request)},
        }
        return payload

    def _evidence(
        self, *, request, started_at, effective_model=None,
        usage: TokenUsage | None = None,
    ) -> InvocationEvidence:
        return InvocationEvidence(
            provenance=Provenance(
                invocation_id=request.invocation_id,
                requested_target=request.target,
                adapter=self._identity,
                effective_provider=ProvenanceValue.observed("OpenAI"),
                effective_model=(ProvenanceValue.reported(effective_model) if effective_model else ProvenanceValue.unknown()),
                started_at=started_at,
                finished_at=utc_now(),
            ),
            usage=usage or TokenUsage.unavailable(),
            cost=CostMeasurement.unavailable(),
        )

    @staticmethod
    def _output_text(payload: dict[str, Any]) -> str:
        parts: list[str] = []
        for item in payload.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    parts.append(content["text"])
        return "".join(parts)

    @staticmethod
    def _usage(payload: dict[str, Any]) -> TokenUsage:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return TokenUsage.unavailable()
        return TokenUsage(
            status=MeasurementStatus.REPORTED,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            total_tokens=usage.get("total_tokens"),
            source="OpenAI Responses API usage",
        )

    def _error(self, request, started_at, *, category, code, phase, message, status_code=None) -> LLMInvocationError:
        evidence = self._evidence(request=request, started_at=started_at)
        return LLMInvocationError(NormalizedError(
            category=category, code=code, phase=phase,
            invocation_id=request.invocation_id, target=request.target,
            safe_message=message, evidence=evidence,
            status_code=status_code,
        ))

    async def generate_structured(self, request) -> StructuredGenerationResult:
        started_at = utc_now()
        secret = self._api_key.get_secret_value().strip()
        if not secret:
            raise self._error(
                request, started_at, category=ErrorCategory.AUTHENTICATION_FAILED,
                code="credential_missing", phase=OperationPhase.AUTHENTICATION,
                message="OpenAI authentication is unavailable.",
            )
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=60.0) as client:
                response = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                    json=self._payload(
                        request, stream=False,
                        response_format=self._native_response_format(request),
                    ),
                )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            category = {
                401: ErrorCategory.AUTHENTICATION_FAILED,
                403: ErrorCategory.PERMISSION_DENIED,
                429: ErrorCategory.RATE_LIMITED,
            }.get(status, ErrorCategory.PROVIDER_UNAVAILABLE if status >= 500 else ErrorCategory.INVALID_REQUEST)
            raise self._error(
                request, started_at, category=category, code=f"http_{status}",
                phase=OperationPhase.RESPONSE, message="OpenAI rejected the evaluation request.",
                status_code=status,
            ) from None
        except (httpx.HTTPError, ValueError):
            raise self._error(
                request, started_at, category=ErrorCategory.PROVIDER_UNAVAILABLE,
                code="transport_or_response_invalid", phase=OperationPhase.RESPONSE,
                message="OpenAI evaluation transport did not return a usable response.",
            ) from None
        model = payload.get("model") if isinstance(payload.get("model"), str) else None
        evidence = self._evidence(
            request=request, started_at=started_at, effective_model=model,
            usage=self._usage(payload),
        )
        text = self._output_text(payload)
        try:
            raw = json.loads(text)
            value = request.response_model.model_validate(raw)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            stage = "json_parse" if isinstance(exc, json.JSONDecodeError) else "schema_validation"
            raise LLMInvocationError(NormalizedError(
                category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
                code="structured_output_schema_mismatch",
                phase=OperationPhase.STRUCTURE_VALIDATION,
                invocation_id=request.invocation_id,
                target=request.target,
                safe_message="OpenAI output did not match the evaluation schema.",
                evidence=evidence,
                structure_validation=build_structure_validation_evidence(exc, request.response_model, stage),
            )) from None
        return StructuredGenerationResult(value=value, evidence=evidence)


class OpenAIObservedAdapter(OpenAIResponsesAdapter):
    """Compatibility alias used by the frozen live runner composition."""

    pass


def _candidate() -> Any:
    row = json.loads(MANIFEST.read_text(encoding="utf-8"))["candidate"]
    return SimpleNamespace(
        **row, adapter_kind="groq", effective_provider="OpenAI",
        upstream_provider=None, require_zdr=False, allow_data_collection=True,
        expiration_date=None,
    )


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"openai-luna-low-{base._batch(batch_id)}"


def prepare_live() -> base.PreparedLive:
    corpus = offline.validate_corpus(offline._load_json(offline.CORPUS))
    gate = offline._load_json(GATE)
    base._require(
        gate.get("hypothesis_id") == HYPOTHESIS_ID
        and gate.get("offline_preparation_authorized") is True
        and gate.get("provider_calls_at_gate_creation") == 0,
        "luna_gate_drifted",
    )
    candidate = _candidate()
    target = LLMTarget(profile=TARGETS[CANDIDATE_ID]["profile"], provider="OpenAI", model="gpt-5.6-luna")
    implementation = (
        "scripts/evaluate_openai_luna_low_live.py",
        "scripts/evaluate_closed_world_render_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "api/llm/contract.py",
    )
    metadata = {
        "purpose": "prospective_luna_low_admission",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_calls": 8,
        "automatic_retries": 0,
        "repair": False,
        "fallback": False,
        "paid_spend_authorized": gate.get("paid_spend_authorized") is True,
        "live_inference_authorized": gate.get("live_inference_authorized") is True,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "generation_parameters": {
            "temperature": base.TEMPERATURE, "reasoning_effort": "low",
            "max_output_tokens": base.MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": 8 * base.MAX_OUTPUT_TOKENS,
            "deadline_seconds": base.DEADLINE_SECONDS,
            "minimum_global_start_interval_seconds": base.MINIMUM_INTERVAL_SECONDS,
        },
        "pricing_observed": {"input_usd_per_million_tokens": 0.20, "output_usd_per_million_tokens": 1.20},
        "transport": {"protocol": "OpenAI Responses API", "endpoint": "/v1/responses", "store": False},
        "selected_candidates": [base._candidate_metadata(candidate, target)],
        "schedule": [
            {"slot": i, "candidate_id": CANDIDATE_ID, "case_id": case,
             "prior_case_id": next(x["prior_case_id"] for x in corpus["cases"] if x["case_id"] == case)}
            for i, case in enumerate(CASE_IDS)
        ],
        "inputs": {
            "offline_preflight": offline.prepare_protocol(),
            "candidate_manifest": {"file": MANIFEST.relative_to(ROOT).as_posix(), "sha256": base._sha_file(MANIFEST)},
            "live_gate": {"file": GATE.relative_to(ROOT).as_posix(), "sha256": base._sha_file(GATE)},
            "response_schema_sha256": base._sha_value(source_profile.NarrativeSourceProposal.model_json_schema()),
            "implementation": [{"file": name, "sha256": base._sha_file(ROOT / name)} for name in implementation],
        },
        "provider_calls": 0,
        "credential_inspected": False,
        "live_execution_requires_cli_opt_in": True,
        "admission": {"threshold": "8/8", "aggregate_prior_runs": False, "best_of_selection": False},
    }
    return base.PreparedLive({CANDIDATE_ID: candidate}, {CANDIDATE_ID: target}, corpus, offline.render_system_prompt(), metadata)


def _route_verified(evidence: dict[str, Any], target: LLMTarget) -> bool:
    provenance = evidence.get("provenance") if isinstance(evidence, dict) else None
    return bool(
        isinstance(provenance, dict)
        and provenance.get("requested_target") == target.model_dump(mode="json")
        and provenance.get("effective_provider", {}).get("value") == "OpenAI"
        and provenance.get("effective_provider", {}).get("source") == "observed"
        and provenance.get("effective_model", {}).get("value") == target.model
        and provenance.get("effective_model", {}).get("source") == "reported"
    )


def configure() -> None:
    base.VERSION = VERSION
    base.KEY_ENV = KEY_ENV
    base.MANIFEST = MANIFEST
    base.LIVE_GATE = GATE
    base.MAX_CALLS = 8
    base.MAX_TOTAL_OUTPUT_TOKENS = 8 * base.MAX_OUTPUT_TOKENS
    base.CANDIDATE_IDS = (CANDIDATE_ID,)
    base.TARGETS = TARGETS
    base.SCHEDULE = SCHEDULE
    base.GROQ_OFFICIAL_BASE_URL = BASE_URL
    base.GroqAdapter = OpenAIObservedAdapter
    base.run_path = run_path
    base.prepare_live = prepare_live
    base._route_verified = _route_verified


def main(argv: list[str] | None = None) -> int:
    configure()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--live" in arguments:
        gate = offline._load_json(GATE)
        if gate.get("live_inference_authorized") is not True or gate.get("paid_spend_authorized") is not True:
            print("openai_luna_paid_authorization_missing", file=sys.stderr)
            return 3
    return base.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
