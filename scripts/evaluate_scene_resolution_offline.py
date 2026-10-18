"""Evaluate authored beat/proposal/state cases without provider or persistence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    project_scene,
    validate_scene_continuation,
)
from api.scene_resolution_service import SceneBeatResolution
from api.scene_service import SceneState

CORPUS = ROOT / "evals/narrator/scene_resolution_offline_v1.json"
PROTOCOL = ROOT / "evals/narrator/scene_resolution_offline_protocol_v1.md"
GATES = ("causality", "agency", "attribution", "progression", "non_contradiction")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evaluate_case(raw: dict) -> dict:
    beat = SceneBeatResolution.model_validate(raw["beat"])
    proposal = SceneContinuationProposal.model_validate(raw["proposal"])
    previous = SceneState.model_validate(raw["previous_scene"])
    try:
        admitted = validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=previous,
            player_input=raw["player_input"],
            protected_secrets=tuple(raw["protected_secrets"]),
            npc_aliases=tuple(raw["npc_aliases"]),
            scene_beat=beat,
        )
        projected = project_scene(
            admitted, previous=previous, turn_number=beat.base_revision + 1
        )
        progression = bool(
            beat.observable_change
            or beat.npc_move
            or beat.open_threads
            or beat.resolve_threads
            or beat.transition_to
        )
        state_matches = (
            projected.last_turn == beat.base_revision + 1
            and set(beat.open_threads).issubset(projected.open_threads)
            and not set(beat.resolve_threads).intersection(projected.open_threads)
            and (
                beat.transition_to is None
                or projected.location.casefold() == beat.transition_to.casefold()
            )
            and (
                beat.observable_change is None
                or beat.observable_change.casefold()
                in {value.casefold() for value in projected.details}
            )
        )
        actual, code = "admitted", None
        gates = {name: True for name in GATES}
        gates["progression"] = progression and state_matches
    except SceneProposalError as exc:
        actual, code, projected = "rejected", exc.code, None
        gates = {name: raw["expected"] == "rejected" for name in GATES}

    passed = (
        actual == raw["expected"]
        and code == raw.get("expected_code")
        and all(gates.values())
    )
    return {
        "case_id": raw["case_id"],
        "expected": raw["expected"],
        "actual": actual,
        "code": code,
        "gates": gates,
        "passed": passed,
        "projected_state": (
            projected.model_dump(mode="json") if projected is not None else None
        ),
    }


def evaluate() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    if corpus.get("version") != "scene-resolution-offline-v1":
        raise ValueError("scene_resolution_offline_version_invalid")
    if tuple(corpus.get("gates", ())) != GATES:
        raise ValueError("scene_resolution_offline_gates_invalid")
    results = [_evaluate_case(case) for case in corpus["cases"]]
    return {
        "protocol": "scene-resolution-offline-v1",
        "synthetic_only": True,
        "provider_calls": 0,
        "inputs": {"corpus_sha256": _sha(CORPUS), "protocol_sha256": _sha(PROTOCOL)},
        "case_count": len(results),
        "passed_count": sum(item["passed"] for item in results),
        "failed_count": sum(not item["passed"] for item in results),
        "all_gates_passed": all(item["passed"] for item in results),
        "model_selected": False,
        "runtime_default_eligible": False,
        "cap_001_approved": False,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
