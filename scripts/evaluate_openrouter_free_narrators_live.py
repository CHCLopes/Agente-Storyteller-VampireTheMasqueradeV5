"""Bounded HYP-005 evaluation of explicit free OpenRouter narrator targets."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.llm.adapters.openrouter import OpenRouterAdapter
from api.llm.contract import (
    ErrorCategory,
    InvocationEvidence,
    LLMInvocationError,
    LLMTarget,
    MeasurementStatus,
    OperationPhase,
)
from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_closed_world_render_plan as offline
from scripts import narrator_source_profile as source_profile


VERSION = "openrouter-free-narrators-live-v1"
HYPOTHESIS_ID = "HYP-005-OPENROUTER-FREE-L1"
KEY_ENV = "STORYTELLER_OPENROUTER_FREE_KEY"
BASE_URL = "https://openrouter.ai/api/v1"
MANIFEST = ROOT / "evals/narrator/openrouter_free_narrator_candidates_2026-09-26.json"
GATE = ROOT / "evals/narrator/reports/openrouter-free-narrators-live-gate-2026-09-26.json"

NEMOTRON = "nemotron-3-super-openrouter-free-synthetic"
LFM = "lfm-2.5-2.6b-openrouter-free-synthetic"
DEEPSEEK = "deepseek-v4-flash-0731-openrouter-free-synthetic"
CANDIDATE_IDS = (NEMOTRON, LFM, DEEPSEEK)
TARGETS = {
    NEMOTRON: {
        "profile": "closed-world-nemotron-3-super-free",
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "reasoning": None,
    },
    LFM: {
        "profile": "closed-world-lfm-2.5-2.6b-free",
        "model": "liquid/lfm-2.5-2.6b:free",
        "reasoning": None,
    },
    DEEPSEEK: {
        "profile": "closed-world-deepseek-v4-flash-0731-free",
        "model": "deepseek/deepseek-v4-flash-0731:free",
        "reasoning": None,
    },
}
CASE_IDS = (
    "hold-silent-bell",
    "authorized-single-bell",
    "known-sealed-tube",
    "unknown-glass-disc",
    "favorable-shutter-result",
    "unfavorable-slab-result",
    "npc-protected-code",
    "ambiguous-sealed-boxes",
)
SCHEDULE = tuple(
    (candidate_id, case_id)
    for candidate_id in CANDIDATE_IDS
    for case_id in CASE_IDS
)


class OpenRouterFreeAdapter(OpenRouterAdapter):
    """Use the hardened exact-route adapter and additionally require zero cost."""

    _UPSTREAM_BY_MODEL = {
        TARGETS[NEMOTRON]["model"]: "nvidia",
        TARGETS[LFM]["model"]: "liquid",
        TARGETS[DEEPSEEK]["model"]: "deepseek",
    }

    def __init__(
        self,
        *,
        base_url,
        capability_set,
        api_key=None,
        reasoning_effort=None,
        transport=None,
    ) -> None:
        model = capability_set.target.model
        if model not in self._UPSTREAM_BY_MODEL:
            raise ValueError("OpenRouter free target is not frozen in HYP-005")
        super().__init__(
            base_url=base_url,
            capability_set=capability_set,
            upstream_provider=self._UPSTREAM_BY_MODEL[model],
            api_key=api_key,
            reasoning_effort=reasoning_effort,
            require_zdr=False,
            allow_data_collection=True,
            adapter_version="hyp-005-free-v1",
            transport=transport,
        )

    def _payload(self, request, *, stream: bool, response_format):
        # The shared evaluator builds a credential-free request capsule through
        # ``object.__new__`` before dispatch. Reconstruct only the public routing
        # policy for that offline path; live adapters still use ``__init__``.
        if not hasattr(self, "_upstream_provider"):
            model = request.target.model
            if model not in self._UPSTREAM_BY_MODEL:
                raise ValueError("OpenRouter free target is not frozen in HYP-005")
            self._upstream_provider = self._UPSTREAM_BY_MODEL[model]
            self._require_zdr = False
            self._allow_data_collection = True
        return super()._payload(
            request,
            stream=stream,
            response_format=response_format,
        )

    def _validate_final_evidence(
        self, request, evidence: InvocationEvidence
    ) -> None:
        super()._validate_final_evidence(request, evidence)
        cost = evidence.cost
        if cost.status is MeasurementStatus.REPORTED and cost.amount == Decimal("0"):
            return
        raise LLMInvocationError(
            self._make_error(
                request=request,
                evidence=evidence,
                category=ErrorCategory.PAYMENT_REQUIRED,
                code="openrouter_zero_cost_not_proven",
                phase=OperationPhase.RESPONSE,
                safe_message=(
                    "OpenRouter did not report an exact zero-dollar cost for the free target."
                ),
            )
        )

    def _new_client(self):
        client = super()._new_client()
        client.headers["X-OpenRouter-Metadata"] = "enabled"
        return client


def _load_manifest() -> dict[str, Any]:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        row["candidate_id"]: SimpleNamespace(
            **row,
            adapter_kind="openai-compatible",
            effective_provider="OpenRouter",
            require_zdr=False,
            allow_data_collection=True,
            expiration_date=None,
        )
        for row in document["candidates"]
    }


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"openrouter-free-narrators-{base._batch(batch_id)}"


def prepare_live() -> base.PreparedLive:
    corpus = offline.validate_corpus(offline._load_json(offline.CORPUS))
    gate = offline._load_json(GATE)
    base._require(
        gate.get("hypothesis_id") == HYPOTHESIS_ID
        and gate.get("live_inference_authorized") is True
        and gate.get("paid_spend_authorized") is False
        and gate.get("provider_calls_at_gate_creation") == 0,
        "openrouter_gate_drifted",
    )
    candidates = _load_manifest()
    targets = {
        candidate_id: LLMTarget(
            profile=TARGETS[candidate_id]["profile"],
            provider="OpenRouter",
            model=TARGETS[candidate_id]["model"],
        )
        for candidate_id in CANDIDATE_IDS
    }
    for candidate_id in CANDIDATE_IDS:
        candidate = candidates[candidate_id]
        expected = TARGETS[candidate_id]
        base._require(
            candidate.provider_label == "OpenRouter"
            and candidate.model == expected["model"]
            and candidate.upstream_provider
            == OpenRouterFreeAdapter._UPSTREAM_BY_MODEL[expected["model"]]
            and candidate.structured_mode == "native"
            and candidate.schema_enforcement == "json_schema_strict"
            and candidate.price_observed_usd_per_million_input == 0
            and candidate.price_observed_usd_per_million_output == 0
            and candidate.campaign_data_eligible is False,
            "openrouter_candidate_invalid",
        )
    base._require(len(SCHEDULE) == 24 and len(set(SCHEDULE)) == 24)
    implementation = (
        "scripts/evaluate_openrouter_free_narrators_live.py",
        "scripts/evaluate_closed_world_render_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
    )
    metadata = {
        "purpose": "prospective_free_cross_origin_model_admission",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_calls": 24,
        "automatic_retries": 0,
        "repair": False,
        "model_fallback": False,
        "provider_fallback": False,
        "paid_spend_authorized": False,
        "zero_cost_must_be_reported_per_response": True,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "generation_parameters": {
            "temperature": base.TEMPERATURE,
            "max_output_tokens": base.MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": 24 * base.MAX_OUTPUT_TOKENS,
            "deadline_seconds": 90,
            "minimum_global_start_interval_seconds": 4,
        },
        "routing_policy": {
            "explicit_model_slug": True,
            "allow_fallbacks": False,
            "require_parameters": True,
            "reported_usage_and_cost_required": True,
            "dynamic_router": False,
        },
        "selected_candidates": [
            base._candidate_metadata(candidates[candidate_id], targets[candidate_id])
            for candidate_id in CANDIDATE_IDS
        ],
        "schedule": [
            {
                "slot": slot,
                "candidate_id": candidate_id,
                "case_id": case_id,
                "prior_case_id": next(
                    case["prior_case_id"]
                    for case in corpus["cases"]
                    if case["case_id"] == case_id
                ),
            }
            for slot, (candidate_id, case_id) in enumerate(SCHEDULE)
        ],
        "inputs": {
            "offline_preflight": offline.prepare_protocol(),
            "candidate_manifest": {
                "file": MANIFEST.relative_to(ROOT).as_posix(),
                "sha256": base._sha_file(MANIFEST),
            },
            "live_gate": {
                "file": GATE.relative_to(ROOT).as_posix(),
                "sha256": base._sha_file(GATE),
            },
            "response_schema_sha256": base._sha_value(
                source_profile.NarrativeSourceProposal.model_json_schema()
            ),
            "implementation": [
                {"file": name, "sha256": base._sha_file(ROOT / name)}
                for name in implementation
            ],
        },
        "provider_calls": 0,
        "credential_inspected": False,
        "live_execution_requires_cli_opt_in": True,
        "admission": {
            "threshold": "8/8 per candidate",
            "aggregate_prior_runs": False,
            "best_of_selection": False,
        },
    }
    return base.PreparedLive(
        candidates,
        targets,
        corpus,
        offline.render_system_prompt(),
        metadata,
    )


def _reported_zero_cost(cost: object) -> bool:
    if not isinstance(cost, dict):
        return False
    try:
        amount = Decimal(str(cost.get("amount")))
    except (InvalidOperation, ValueError):
        return False
    return (
        cost.get("status") == "reported"
        and amount == Decimal("0")
        and cost.get("currency") == "OPENROUTER_CREDITS"
    )


def _route_verified(evidence: dict[str, Any], target: LLMTarget) -> bool:
    provenance = evidence.get("provenance") if isinstance(evidence, dict) else None
    provider = provenance.get("effective_provider") if isinstance(provenance, dict) else None
    model = provenance.get("effective_model") if isinstance(provenance, dict) else None
    cost = evidence.get("cost") if isinstance(evidence, dict) else None
    return bool(
        isinstance(provenance, dict)
        and provenance.get("requested_target") == target.model_dump(mode="json")
        and isinstance(provider, dict)
        and isinstance(provider.get("value"), str)
        and provider["value"].strip().casefold()
        == OpenRouterFreeAdapter._UPSTREAM_BY_MODEL[target.model]
        and provider.get("source") == "reported"
        and isinstance(model, dict)
        and isinstance(model.get("value"), str)
        and bool(model["value"].strip())
        and model.get("source") == "reported"
        and _reported_zero_cost(cost)
    )


def configure() -> None:
    base.VERSION = VERSION
    base.KEY_ENV = KEY_ENV
    base.MANIFEST = MANIFEST
    base.LIVE_GATE = GATE
    base.MAX_CALLS = 24
    base.MAX_TOTAL_OUTPUT_TOKENS = 24 * base.MAX_OUTPUT_TOKENS
    base.DEADLINE_SECONDS = 90
    base.MINIMUM_INTERVAL_SECONDS = 4
    base.CANDIDATE_IDS = CANDIDATE_IDS
    base.TARGETS = TARGETS
    base.SCHEDULE = SCHEDULE
    base.GROQ_OFFICIAL_BASE_URL = BASE_URL
    base.GroqAdapter = OpenRouterFreeAdapter
    base.run_path = run_path
    base.prepare_live = prepare_live
    base._route_verified = _route_verified


def main(argv: list[str] | None = None) -> int:
    configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
