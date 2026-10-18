"""Build the byte-linked partial semantic review for HYP-005 L1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RUN_PREFIX = "openrouter-free-narrators-"
EXPECTED_HYPOTHESIS = "HYP-005-OPENROUTER-FREE-L1"
EXPECTED_RECORDS_SHA256 = "49c95158c11f59faeeab78330e12f49265e5b0d580646d61c6a59e3e13c73a89"
EXPECTED_COMPLETED = (
    "lfm-2.5-2.6b-openrouter-free-synthetic",
    "favorable-shutter-result",
    12,
)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]


def build(batch_id: str, output: Path | None = None) -> Path:
    run = ROOT / "eval-results" / f"{RUN_PREFIX}{batch_id}"
    summary_path = run / "summary.json"
    records_path = run / "records.jsonl"
    summary = _load_json(summary_path)
    records_sha256 = _sha(records_path)
    if summary.get("batch_id") != batch_id:
        raise ValueError("batch_id_mismatch")
    if summary.get("metadata", {}).get("hypothesis_id") != EXPECTED_HYPOTHESIS:
        raise ValueError("hypothesis_mismatch")
    if summary.get("process_exit_code") != 2:
        raise ValueError("unexpected_process_exit_code")
    if records_sha256 != EXPECTED_RECORDS_SHA256:
        raise ValueError("records_not_frozen")
    if summary.get("artifacts", {}).get("records", {}).get("sha256") != records_sha256:
        raise ValueError("records_hash_mismatch")

    rows = _records(records_path)
    completed = [row for row in rows if row.get("status") == "completed"]
    if len(rows) != 24 or len(completed) != 1:
        raise ValueError("unexpected_record_shape")
    row = completed[0]
    observed = (row.get("candidate_id"), row.get("case_id"), row.get("slot"))
    if observed != EXPECTED_COMPLETED:
        raise ValueError("unexpected_completed_record")
    narrative = row.get("response", {}).get("n")
    question = row.get("response", {}).get("q")
    if not isinstance(narrative, str) or not isinstance(question, str):
        raise ValueError("completed_response_invalid")

    document = {
        "version": "openrouter-free-narrators-partial-review-v1",
        "hypothesis_id": EXPECTED_HYPOTHESIS,
        "batch_id": batch_id,
        "reviewer": "codex-independent-semantic-review",
        "review_date": "2026-09-27",
        "source": {
            "summary_sha256": _sha(summary_path),
            "records_sha256": records_sha256,
            "completed_response_sha256": _sha_bytes(
                json.dumps(row["response"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ),
        },
        "scope": {
            "records_total": 24,
            "records_completed": 1,
            "records_semantically_reviewed": 1,
            "incomplete_records_not_scored": 23,
            "candidate_qualification_permitted": False,
        },
        "review": {
            "candidate_id": row["candidate_id"],
            "case_id": row["case_id"],
            "slot": row["slot"],
            "narrative": narrative,
            "question": question,
            "rendered_unit_ids": [
                "test-succeeded",
                "shutter-hand-width",
                "shutter-stops",
                "wood-scrapes",
                "thin-air-current",
            ],
            "transition_id": "shutter-opens-hand-width",
            "asserted_unknown_ids": [],
            "criteria": {
                "unlisted_render_claim": True,
                "player_agency_attribution": False,
                "unauthorized_secret_disclosure": False,
                "mechanical_result_expansion": False,
                "progression_observed": True,
                "next_choice_preserved": True,
            },
            "unlisted_claims": [
                "veneziana anteriormente completamente fechada",
                "som ecoa suavemente",
                "corrente de ar fria",
                "existencia de uma sala",
                "luz em fios pela fresta",
                "particulas de poeira no ar",
                "ambiente parece segurar a respiracao",
            ],
            "fatal_semantic_gate_passed": False,
            "rationale": (
                "A transicao mecanica, a largura da fresta, o atrito, a corrente de ar e a proxima escolha "
                "foram preservados. A narrativa, porem, acrescentou sete alegacoes que nao pertencem ao "
                "plano fechado; unlisted_render_claim e fatal neste protocolo."
            ),
        },
        "classification": {
            "nemotron": "inconclusive_operational_truncation_0_of_8_completed",
            "liquid": "ineligible_batch_incomplete_and_only_completed_case_failed_fatal_semantic_gate",
            "deepseek": "inconclusive_exact_free_route_unavailable_0_of_8_completed",
            "qualified_candidates": [],
            "narrator_admitted": False,
            "human_acceptance_required": True,
        },
    }
    target = output or ROOT / "evals" / "narrator" / "reviews" / f"openrouter-free-narrators-{batch_id[:8]}-partial-codex.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    built = build(args.batch_id, args.output)
    try:
        display = built.relative_to(ROOT).as_posix()
    except ValueError:
        display = str(built)
    print(display)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
