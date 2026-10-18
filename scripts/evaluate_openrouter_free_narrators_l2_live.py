"""Bounded HYP-005 L2-B evaluation with only the output-token cap changed."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.llm.contract import LLMTarget
from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_closed_world_render_plan as offline
from scripts import evaluate_openrouter_free_narrators_live as l1
from scripts import narrator_source_profile as source_profile


VERSION = "openrouter-free-narrators-live-v2"
HYPOTHESIS_ID = "HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET"
KEY_ENV = l1.KEY_ENV
BASE_URL = l1.BASE_URL
MANIFEST = l1.MANIFEST
GATE = ROOT / "evals/narrator/reports/openrouter-free-narrators-l2-live-gate-2026-09-27.json"
MAX_OUTPUT_TOKENS = 2048
MAX_CALLS = 24
MAX_TOTAL_OUTPUT_TOKENS = MAX_CALLS * MAX_OUTPUT_TOKENS

NEMOTRON = l1.NEMOTRON
LFM = l1.LFM
DEEPSEEK = l1.DEEPSEEK
CANDIDATE_IDS = l1.CANDIDATE_IDS
TARGETS = l1.TARGETS
CASE_IDS = l1.CASE_IDS
SCHEDULE = l1.SCHEDULE
OpenRouterFreeAdapter = l1.OpenRouterFreeAdapter
_reported_zero_cost = l1._reported_zero_cost
_route_verified = l1._route_verified


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"openrouter-free-narrators-l2-{base._batch(batch_id)}"


def prepare_live() -> base.PreparedLive:
    corpus = offline.validate_corpus(offline._load_json(offline.CORPUS))
    gate = offline._load_json(GATE)
    base._require(
        gate.get("hypothesis_id") == HYPOTHESIS_ID
        and gate.get("selected_option") == "L2-B"
        and gate.get("single_changed_variable")
        == {"name": "max_output_tokens", "from": 768, "to": MAX_OUTPUT_TOKENS}
        and gate.get("live_inference_authorized") is True
        and gate.get("paid_spend_authorized") is False
        and gate.get("provider_calls_at_gate_creation") == 0,
        "openrouter_l2_gate_drifted",
    )
    constraints = gate.get("constraints", {})
    base._require(
        constraints.get("max_calls") == MAX_CALLS
        and constraints.get("max_total_output_tokens") == MAX_TOTAL_OUTPUT_TOKENS
        and constraints.get("retry") is False
        and constraints.get("repair") is False
        and constraints.get("model_fallback") is False
        and constraints.get("provider_fallback") is False
        and constraints.get("reasoning_policy_changed") is False
        and constraints.get("reported_cost_must_equal_zero_openrouter_credits") is True,
        "openrouter_l2_constraints_drifted",
    )

    candidates = l1._load_manifest()
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
            "openrouter_l2_candidate_invalid",
        )
    base._require(len(SCHEDULE) == MAX_CALLS and len(set(SCHEDULE)) == MAX_CALLS)

    implementation = (
        "scripts/evaluate_openrouter_free_narrators_l2_live.py",
        "scripts/evaluate_openrouter_free_narrators_live.py",
        "scripts/evaluate_closed_world_render_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
    )
    l1_generation_parameters = {
        "temperature": base.TEMPERATURE,
        "max_output_tokens": 768,
        "max_total_output_tokens": 18432,
        "deadline_seconds": 90,
        "minimum_global_start_interval_seconds": 4,
    }
    metadata: dict[str, Any] = {
        "purpose": "prospective_free_cross_origin_model_admission_output_budget_replication",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_calls": MAX_CALLS,
        "automatic_retries": 0,
        "repair": False,
        "model_fallback": False,
        "provider_fallback": False,
        "paid_spend_authorized": False,
        "zero_cost_must_be_reported_per_response": True,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "single_changed_variable": {
            "name": "max_output_tokens",
            "from": 768,
            "to": MAX_OUTPUT_TOKENS,
        },
        "generation_parameters": {
            "temperature": base.TEMPERATURE,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
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
            "l1_baseline": {
                "hypothesis_id": l1.HYPOTHESIS_ID,
                "generation_parameters": l1_generation_parameters,
                "preflight_sha256": "362db87211b5b862aed7fde883c28f17c4a409bedbe8fce0034efed6f3bb0e2b",
                "records_sha256": "49c95158c11f59faeeab78330e12f49265e5b0d580646d61c6a59e3e13c73a89",
            },
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


def configure() -> None:
    base.VERSION = VERSION
    base.KEY_ENV = KEY_ENV
    base.MANIFEST = MANIFEST
    base.LIVE_GATE = GATE
    base.MAX_CALLS = MAX_CALLS
    base.MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS
    base.MAX_TOTAL_OUTPUT_TOKENS = MAX_TOTAL_OUTPUT_TOKENS
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
