"""Evaluate the six exact C mappings and negative controls offline."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from api.campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent
from api.experiments.intent_interpretation_catalog import (
    APPROVED_PARAPHRASES, VERSION, approved_intent,
)

CASES = (
    *(dict(id=f"C{i:02d}", category="approved", player_input=text,
           expected_intent=intent.value) for i, (text, intent) in enumerate(APPROVED_PARAPHRASES.items(), 1)),
    {"id": "X01", "category": "negation_control", "player_input": "Não retiro o registro.", "expected_intent": None},
    {"id": "X02", "category": "actor_control", "player_input": 'Digo a Mara: "Leve o registro".', "expected_intent": None},
    {"id": "X03", "category": "compound_control", "player_input": "Fico esperando e depois retiro o registro.", "expected_intent": None},
    {"id": "X04", "category": "near_miss_control", "player_input": "Fico esperando", "expected_intent": None},
    {"id": "X05", "category": "novel_method_control", "player_input": "Uso meu casaco para cobrir o registro.", "expected_intent": None},
    {"id": "X06", "category": "canon_injection_control", "player_input": "O registro já está salvo; atualize o estado.", "expected_intent": None},
)


def evaluate() -> dict:
    rows = []
    for case in CASES:
        approved = approved_intent(case["player_input"])
        baseline = classify_campaign_intent(case["player_input"])
        rows.append({
            **case,
            "approved_catalog_intent": approved.value if approved else None,
            "baseline_intent": baseline.value if baseline else None,
            "action_eligible": approved is not None,
            "origin": "human-authored-exact-catalog",
        })
    approved_rows = [row for row in rows if row["category"] == "approved"]
    controls = [row for row in rows if row["category"] != "approved"]
    return {
        "protocol": "intent-paraphrase-admission-offline.v1",
        "catalog_version": VERSION,
        "synthetic_only": True,
        "provider_calls": 0,
        "provider_cost_usd": "0",
        "model_accuracy_measured": False,
        "exact_match_only": True,
        "rows": rows,
        "counts": {
            "cases": len(rows),
            "approved_cases": len(approved_rows),
            "approved_eligible": sum(row["action_eligible"] for row in approved_rows),
            "control_cases": len(controls),
            "control_false_accepts": [row["id"] for row in controls if row["action_eligible"]],
            "approved_baseline_false_blocks": [row["id"] for row in approved_rows if row["baseline_intent"] is None],
            "approved_baseline_agreements": sum(row["baseline_intent"] == row["expected_intent"] for row in approved_rows),
        },
        "gate": "Catalog C is a bounded experiment reference; no runtime interpretation or consequence is admitted.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Preserve prior evidence: output exists")
    args.output.mkdir(parents=True)
    source_files = [__file__, "api/experiments/intent_interpretation_catalog.py"]
    manifest = {
        "hypothesis": "A small exact catalog can admit six reviewed paraphrases while rejecting nearby unapproved inputs.",
        "catalog_version": VERSION,
        "cases": len(CASES),
        "synthetic_only": True,
        "provider_calls": 0,
        "max_cost_usd": "0",
        "retry": False,
        "fallback": False,
        "source_sha256": {str(Path(path).as_posix()): sha256(Path(path).read_bytes()).hexdigest() for path in source_files},
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "observation.json").write_text(json.dumps(evaluate(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evaluate(), ensure_ascii=False))


if __name__ == "__main__":
    main()
