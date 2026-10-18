"""Prepare an offline evaluation-lane switch to Luna without activating it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_openai_luna_low_live as luna


SWITCH_ID = "NARRATOR-EVAL-SWITCH-OPENROUTER-L3-TO-LUNA-LOW-V1"
GATE = ROOT / "evals/narrator/reports/narrator-evaluation-switch-to-luna-gate-2026-09-27.json"
OPENROUTER_L3_GATE = ROOT / "evals/narrator/reports/openrouter-free-narrators-l3-live-gate-2026-09-27.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("luna_switch_document_invalid")
    return value


def prepare_switch() -> dict[str, Any]:
    gate = _load(GATE)
    openrouter_gate = _load(OPENROUTER_L3_GATE)
    luna_gate = _load(luna.GATE)
    luna_preflight = luna.prepare_live().metadata
    constraints = gate.get("constraints", {})

    base._require(
        gate.get("switch_id") == SWITCH_ID
        and gate.get("scope") == "evaluation_lane_only"
        and gate.get("provider_calls_at_gate_creation") == 0
        and gate.get("credential_status") == "not_requested"
        and gate.get("live_inference_authorized") is False
        and gate.get("paid_spend_authorized") is False
        and gate.get("paid_provider_policy")
        == {
            "status": "temporarily_allowed_for_testing",
            "human_decision": (
                "Revogue temporariamente a decisão provedores pagos fora de "
                "questão para podermos realizar os testes. eu a trarei de "
                "volta quando necessário"
            ),
            "does_not_authorize_unbounded_spend": True,
        }
        and gate.get("runtime_default_change_authorized") is False
        and gate.get("narrator_admission_authorized") is False,
        "luna_switch_gate_invalid",
    )
    base._require(
        openrouter_gate.get("hypothesis_id")
        == "HYP-005-OPENROUTER-FREE-L3-STRICT-OVERLOAD-RETRY"
        and openrouter_gate.get("execution_window") == "new_free_daily_window_only"
        and openrouter_gate.get("paid_spend_authorized") is False,
        "luna_switch_source_lane_invalid",
    )
    base._require(
        luna_gate.get("hypothesis_id") == luna.HYPOTHESIS_ID
        and luna_gate.get("live_inference_authorized") is False
        and luna_gate.get("paid_spend_authorized") is False
        and luna_preflight.get("hypothesis_id") == luna.HYPOTHESIS_ID
        and luna_preflight.get("live_inference_authorized") is False
        and luna_preflight.get("paid_spend_authorized") is False,
        "luna_switch_target_lane_not_closed",
    )
    base._require(
        constraints.get("synthetic_only") is True
        and constraints.get("max_calls") == 8
        and constraints.get("max_output_tokens_per_call") == 768
        and constraints.get("max_output_tokens_total") == 6144
        and constraints.get("automatic_retries") == 0
        and constraints.get("repair") is False
        and constraints.get("fallback") is False
        and constraints.get("target_switch_inside_batch") is False
        and constraints.get("aggregate_with_openrouter") is False
        and constraints.get("best_of_selection") is False
        and constraints.get("free_tier_supported") is False
        and constraints.get("account_spend_limit_required_usd") == 0.05,
        "luna_switch_constraints_invalid",
    )
    base._require(
        luna_preflight.get("max_calls") == constraints["max_calls"]
        and luna_preflight.get("automatic_retries") == 0
        and luna_preflight.get("repair") is False
        and luna_preflight.get("fallback") is False
        and luna_preflight.get("generation_parameters", {}).get("reasoning_effort")
        == "low"
        and luna_preflight.get("generation_parameters", {}).get("max_output_tokens")
        == constraints["max_output_tokens_per_call"]
        and luna_preflight.get("generation_parameters", {}).get("max_total_output_tokens")
        == constraints["max_output_tokens_total"]
        and luna_preflight.get("provider_calls") == 0
        and luna_preflight.get("credential_inspected") is False,
        "luna_switch_preflight_drifted",
    )

    files = (
        GATE,
        OPENROUTER_L3_GATE,
        luna.GATE,
        ROOT / "scripts/evaluate_openai_luna_low_live.py",
        ROOT / "scripts/run_openai_luna_low_live.ps1",
        ROOT / "evals/narrator/openai_luna_low_candidate_2026-09-26.json",
    )
    return {
        "switch_id": SWITCH_ID,
        "status": "prepared_not_activated",
        "scope": "evaluation_lane_only",
        "source_lane": gate["from"],
        "target_lane": gate["to"],
        "activation": {
            "allowed_now": False,
            "requirements": gate["activation_requires"],
        },
        "paid_provider_policy": gate["paid_provider_policy"],
        "limits": constraints,
        "official_sources_checked_2026_09_27": gate[
            "official_sources_checked_2026_09_27"
        ],
        "inputs": [
            {
                "file": path.relative_to(ROOT).as_posix(),
                "sha256": base._sha_file(path),
            }
            for path in files
        ],
        "provider_calls": 0,
        "credential_inspected": False,
        "runtime_default_changed": False,
        "narrator_admitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true", required=True)
    arguments = parser.parse_args(argv)
    if not arguments.preflight:
        return 3
    print(json.dumps(prepare_switch(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
