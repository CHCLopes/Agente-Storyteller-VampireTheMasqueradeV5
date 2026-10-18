"""Build the byte-linked partial semantic review for HYP-005 L2-B."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BATCH_ID = "47f0c07f-ed8a-49b1-a9a6-4b760e7c4ffd"
RUN = ROOT / "eval-results" / f"openrouter-free-narrators-l2-{BATCH_ID}"
SUMMARY = RUN / "summary.json"
RECORDS = RUN / "records.jsonl"
REVIEWS = ROOT / "evals/narrator/reviews"
EXPECTED_HYPOTHESIS = "HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET"
EXPECTED_SUMMARY_SHA256 = "5e21e0eea47073273e7741127215bfbcc18c938444d2f0fa4b31091235f4b0fa"
EXPECTED_RECORDS_SHA256 = "61ca88fa5046b0e875e631ba30fff4d159ccb0e65c9ee163ed5e8336190cf111"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)["record"]
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def build(output: Path | None = None) -> Path:
    summary = _load_json(SUMMARY)
    if _sha(SUMMARY) != EXPECTED_SUMMARY_SHA256:
        raise ValueError("summary_not_frozen")
    if _sha(RECORDS) != EXPECTED_RECORDS_SHA256:
        raise ValueError("records_not_frozen")
    if (
        summary.get("batch_id") != BATCH_ID
        or summary.get("metadata", {}).get("hypothesis_id") != EXPECTED_HYPOTHESIS
        or summary.get("process_exit_code") != 2
        or summary.get("artifacts", {}).get("records", {}).get("sha256")
        != EXPECTED_RECORDS_SHA256
    ):
        raise ValueError("summary_contract_invalid")

    rows = _records(RECORDS)
    completed = [row for row in rows if row.get("status") == "completed"]
    failed = [row for row in rows if row.get("status") == "failed"]
    skipped = [row for row in rows if row.get("status") == "skipped"]
    if not (
        len(rows) == 24
        and len(completed) == 1
        and len(failed) == 1
        and len(skipped) == 22
    ):
        raise ValueError("record_shape_invalid")
    row = completed[0]
    if (
        row.get("slot"),
        row.get("candidate_id"),
        row.get("case_id"),
    ) != (
        0,
        "nemotron-3-super-openrouter-free-synthetic",
        "hold-silent-bell",
    ):
        raise ValueError("completed_record_invalid")
    failure = failed[0]
    if (
        failure.get("slot") != 1
        or failure.get("error", {}).get("category") != "provider_unavailable"
        or failure.get("error", {}).get("code") != "openrouter_provider_overloaded"
    ):
        raise ValueError("global_stop_invalid")
    response = row.get("response")
    if not isinstance(response, dict):
        raise ValueError("response_invalid")

    document = {
        "version": "openrouter-free-narrators-l2-partial-review-v1",
        "hypothesis_id": EXPECTED_HYPOTHESIS,
        "batch_id": BATCH_ID,
        "reviewer": "codex-independent-semantic-review",
        "review_date": "2026-09-27",
        "source": {
            "summary_sha256": EXPECTED_SUMMARY_SHA256,
            "records_sha256": EXPECTED_RECORDS_SHA256,
            "completed_response_sha256": _sha_bytes(
                json.dumps(
                    response,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ),
        },
        "scope": {
            "records_total": 24,
            "records_completed": 1,
            "records_semantically_reviewed": 1,
            "records_failed_operationally": 1,
            "records_skipped_causally": 22,
            "candidate_qualification_permitted": False,
        },
        "review": {
            "candidate_id": row["candidate_id"],
            "case_id": row["case_id"],
            "slot": row["slot"],
            "narrative": response["n"],
            "question": response["q"],
            "rendered_unit_ids": [
                "bell-still",
                "cord-out-of-reach",
                "arch-visible",
                "cool-air",
                "stone-echo",
            ],
            "transition_id": None,
            "asserted_unknown_ids": [],
            "criteria": {
                "unlisted_render_claim": True,
                "player_agency_attribution": False,
                "unauthorized_secret_disclosure": False,
                "mechanical_result_expansion": False,
                "continuity_material_repetition": False,
                "progression_observed": False,
                "coherent_hold_observed": True,
                "next_choice_preserved": True,
            },
            "unlisted_claims": [
                "silencio envolve o sino e a pedra",
            ],
            "fatal_semantic_gate_passed": False,
            "rationale": (
                "Sino, corda, arco, ar frio, eco e a acao declarada de permanecer "
                "parado foram preservados; a pergunta devolve a proxima escolha. "
                "A afirmacao ambiental de que o silencio envolve o sino e a pedra "
                "nao pertence ao plano fechado e falha o gate fatal de alegacao "
                "nao listada."
            ),
        },
        "classification": {
            "nemotron": (
                "ineligible_batch_incomplete_and_only_completed_case_failed_"
                "fatal_semantic_gate"
            ),
            "liquid": "inconclusive_not_dispatched_after_global_provider_unavailable",
            "deepseek": "inconclusive_not_dispatched_after_global_provider_unavailable",
            "qualified_candidates": [],
            "narrator_admitted": False,
            "human_acceptance_required": True,
        },
    }
    target = output or REVIEWS / (
        f"openrouter-free-narrators-l2-{BATCH_ID[:8]}-partial-codex.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    built = build(args.output)
    try:
        display = built.relative_to(ROOT).as_posix()
    except ValueError:
        display = str(built)
    print(display)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

