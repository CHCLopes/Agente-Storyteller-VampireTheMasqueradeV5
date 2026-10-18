"""Prospective closed-world evaluation of exact free Chinese SiliconFlow targets."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import SecretStr

from api.llm.adapters.openai_compatible import OpenAICompatibleAdapter
from api.llm.contract import (
    CostMeasurement,
    InvocationEvidence,
    LLMTarget,
    Provenance,
    ProvenanceValue,
    TokenUsage,
    utc_now,
)
from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_closed_world_render_plan as offline
from scripts import evaluate_narrator_models as shared
from scripts import narrator_source_profile as source_profile


VERSION = "siliconflow-free-chinese-live-v1"
HYPOTHESIS_ID = "HYP-005-SILICONFLOW-FREE-CHINESE-L1"
KEY_ENV = "STORYTELLER_SILICONFLOW_FREE_KEY"
BASE_URL = "https://api.siliconflow.cn/v1"
MANIFEST = ROOT / "evals/narrator/siliconflow_free_chinese_candidates_2026-09-26.json"
GATE = ROOT / "evals/narrator/reports/siliconflow-free-chinese-live-gate-2026-09-26.json"

XING = "xing4-29b-siliconflow-free-synthetic"
QWEN = "qwen3.5-4b-siliconflow-free-synthetic"
GLM = "glm4-9b-siliconflow-free-synthetic"
CANDIDATE_IDS = (XING, QWEN, GLM)
TARGETS = {
    XING: {"profile": "closed-world-xing4-29b", "model": "XingChenAGI/Xing4.0-29B", "reasoning": None},
    QWEN: {"profile": "closed-world-qwen3.5-4b", "model": "Qwen/Qwen3.5-4B", "reasoning": None},
    GLM: {"profile": "closed-world-glm4-9b", "model": "THUDM/GLM-4-9B-0414", "reasoning": None},
}
CASE_IDS = (
    "hold-silent-bell", "authorized-single-bell", "known-sealed-tube",
    "unknown-glass-disc", "favorable-shutter-result", "unfavorable-slab-result",
    "npc-protected-code", "ambiguous-sealed-boxes",
)
SCHEDULE = tuple((candidate, case) for case in CASE_IDS for candidate in CANDIDATE_IDS)


class SiliconFlowAdapter(OpenAICompatibleAdapter):
    """Bind the generic protocol to the exact SiliconFlow endpoint and identity."""

    def _evidence(
        self, *, request, started_at, effective_provider=None, effective_model=None,
        usage: TokenUsage | None = None, cost: CostMeasurement | None = None,
    ) -> InvocationEvidence:
        return InvocationEvidence(
            provenance=Provenance(
                invocation_id=request.invocation_id,
                requested_target=request.target,
                adapter=self._identity,
                effective_provider=ProvenanceValue.observed("SiliconFlow"),
                effective_model=(ProvenanceValue.reported(effective_model) if effective_model else ProvenanceValue.unknown()),
                started_at=started_at,
                finished_at=utc_now(),
            ),
            usage=usage or TokenUsage.unavailable(),
            cost=cost or CostMeasurement.unavailable(),
        )


def _load_manifest() -> dict[str, Any]:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {row["candidate_id"]: SimpleNamespace(
        **row, adapter_kind="groq", effective_provider="SiliconFlow",
        upstream_provider=None, require_zdr=False, allow_data_collection=True,
        expiration_date=None,
    ) for row in document["candidates"]}


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"siliconflow-free-chinese-{base._batch(batch_id)}"


def prepare_live() -> base.PreparedLive:
    corpus = offline.validate_corpus(offline._load_json(offline.CORPUS))
    gate = offline._load_json(GATE)
    base._require(
        gate.get("hypothesis_id") == HYPOTHESIS_ID
        and gate.get("live_inference_authorized") is True
        and gate.get("paid_spend_authorized") is False
        and gate.get("provider_calls_at_gate_creation") == 0,
        "siliconflow_gate_drifted",
    )
    candidates = _load_manifest()
    targets = {
        candidate_id: LLMTarget(
            profile=TARGETS[candidate_id]["profile"], provider="SiliconFlow",
            model=TARGETS[candidate_id]["model"],
        ) for candidate_id in CANDIDATE_IDS
    }
    implementation = (
        "scripts/evaluate_siliconflow_free_chinese_live.py",
        "scripts/evaluate_closed_world_render_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
    )
    metadata = {
        "purpose": "prospective_free_chinese_model_admission",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_calls": 24,
        "automatic_retries": 0,
        "repair": False,
        "fallback": False,
        "paid_spend_authorized": False,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "generation_parameters": {
            "temperature": base.TEMPERATURE,
            "max_output_tokens": base.MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": 24 * base.MAX_OUTPUT_TOKENS,
            "deadline_seconds": base.DEADLINE_SECONDS,
            "minimum_global_start_interval_seconds": base.MINIMUM_INTERVAL_SECONDS,
        },
        "selected_candidates": [base._candidate_metadata(candidates[c], targets[c]) for c in CANDIDATE_IDS],
        "schedule": [
            {"slot": i, "candidate_id": c, "case_id": k,
             "prior_case_id": next(x["prior_case_id"] for x in corpus["cases"] if x["case_id"] == k)}
            for i, (c, k) in enumerate(SCHEDULE)
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
        "admission": {"threshold": "8/8 per candidate", "aggregate_prior_runs": False, "best_of_selection": False},
    }
    return base.PreparedLive(candidates, targets, corpus, offline.render_system_prompt(), metadata)


def _route_verified(evidence: dict[str, Any], target: LLMTarget) -> bool:
    provenance = evidence.get("provenance") if isinstance(evidence, dict) else None
    return bool(
        isinstance(provenance, dict)
        and provenance.get("requested_target") == target.model_dump(mode="json")
        and provenance.get("effective_provider", {}).get("value") == "SiliconFlow"
        and provenance.get("effective_provider", {}).get("source") == "observed"
        and provenance.get("effective_model", {}).get("value") == target.model
        and provenance.get("effective_model", {}).get("source") == "reported"
    )


def configure() -> None:
    base.VERSION = VERSION
    base.KEY_ENV = KEY_ENV
    base.MANIFEST = MANIFEST
    base.LIVE_GATE = GATE
    base.MAX_CALLS = 24
    base.MAX_TOTAL_OUTPUT_TOKENS = 24 * base.MAX_OUTPUT_TOKENS
    base.CANDIDATE_IDS = CANDIDATE_IDS
    base.TARGETS = TARGETS
    base.SCHEDULE = SCHEDULE
    base.GROQ_OFFICIAL_BASE_URL = BASE_URL
    base.GroqAdapter = SiliconFlowAdapter
    base.run_path = run_path
    base.prepare_live = prepare_live
    base._route_verified = _route_verified


def main(argv: list[str] | None = None) -> int:
    configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
