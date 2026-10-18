"""Build the byte-linked semantic review for HYP-006 Luna low."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BATCH_ID = "c875289b-e3f0-4907-8301-2408781a96ce"
RUN = ROOT / "eval-results" / f"openai-luna-low-{BATCH_ID}"
SUMMARY = RUN / "summary.json"
RECORDS = RUN / "records.jsonl"
REVIEWS = ROOT / "evals/narrator/reviews"
EXPECTED_HYPOTHESIS = "HYP-006-OPENAI-LUNA-LOW-L1"
EXPECTED_SUMMARY_SHA256 = "a593d4eecdd50c567a4bff7e383b43e6dd39a0dda4e0ed84a95c43caedfd21dc"
EXPECTED_RECORDS_SHA256 = "f84679cd4696206c75fd1f7e5991df629f0e8cc3ac8fbf9e8cfa351a9ba5f01b"


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


REVIEW_FACTS = {
    "hold-silent-bell": {
        "rendered_unit_ids": ["bell-still", "cord-out-of-reach", "cool-air", "stone-echo"],
        "transition_id": None,
        "asserted_unknown_ids": [],
        "progression_observed": False,
        "coherent_hold_observed": True,
        "rationale": "Preserva sino, corda, ar frio e eco; nenhuma transicao ocorre e a proxima escolha retorna ao jogador.",
    },
    "authorized-single-bell": {
        "rendered_unit_ids": ["bell-one-note", "cord-remains-still", "brief-metal-note", "echo-fades"],
        "transition_id": "bell-rings-once",
        "asserted_unknown_ids": ["bell-cause"],
        "progression_observed": True,
        "coherent_hold_observed": False,
        "rationale": "Executa uma unica nota, conserva a corda imovel, nao explica a causa e preserva interpretar ou investigar.",
    },
    "known-sealed-tube": {
        "rendered_unit_ids": ["tube-on-shelf", "wax-seal-intact", "seal-mark", "brass-dull", "shelf-dry"],
        "transition_id": None,
        "asserted_unknown_ids": ["tube-content"],
        "progression_observed": False,
        "coherent_hold_observed": True,
        "rationale": "Mantem tubo e lacre intactos, descreve apenas atributos listados e conserva o conteudo desconhecido.",
    },
    "unknown-glass-disc": {
        "rendered_unit_ids": ["disc-visible", "surface-dark", "wall-pale"],
        "transition_id": None,
        "asserted_unknown_ids": ["disc-purpose", "disc-active"],
        "progression_observed": False,
        "coherent_hold_observed": True,
        "rationale": "Limita-se ao disco fixado, superficie e parede; funcao e estado continuam desconhecidos.",
    },
    "favorable-shutter-result": {
        "rendered_unit_ids": ["test-succeeded", "shutter-hand-width", "shutter-stops", "wood-scrapes", "thin-air-current"],
        "transition_id": "shutter-opens-hand-width",
        "asserted_unknown_ids": ["space-beyond-shutter"],
        "progression_observed": True,
        "coherent_hold_observed": False,
        "rationale": "Preserva o sucesso e a abertura exata, sem ampliar nem descrever o espaco alem da fresta.",
    },
    "unfavorable-slab-result": {
        "rendered_unit_ids": ["test-failed", "slab-remains", "chalk-flakes", "stone-rough", "chalk-pale"],
        "transition_id": "chalk-mark-flakes",
        "asserted_unknown_ids": ["slab-mechanism"],
        "progression_observed": True,
        "coherent_hold_observed": False,
        "rationale": "Mantem o fracasso, a laje imovel e apenas a perda de giz autorizada, sem inventar mecanismo.",
    },
    "npc-protected-code": {
        "rendered_unit_ids": ["iara-withholds-code", "iara-offers-route-card", "card-on-palm", "card-cream", "ink-blue"],
        "transition_id": "iara-offers-route-card",
        "asserted_unknown_ids": [],
        "progression_observed": True,
        "coherent_hold_observed": False,
        "rationale": "Protege o codigo, oferece somente a pista autorizada e nao atribui aceite do cartao ao jogador.",
    },
    "ambiguous-sealed-boxes": {
        "rendered_unit_ids": ["four-boxes", "no-box-chosen", "different-sizes", "support-stone", "room-light-even"],
        "transition_id": None,
        "asserted_unknown_ids": ["box-contents"],
        "progression_observed": False,
        "coherent_hold_observed": True,
        "rationale": "Preserva quatro caixas seladas sem material ou conteudo inventado e devolve a escolha ao jogador.",
    },
}


def build(output: Path | None = None) -> Path:
    summary = _load_json(SUMMARY)
    if _sha(SUMMARY) != EXPECTED_SUMMARY_SHA256:
        raise ValueError("summary_not_frozen")
    if _sha(RECORDS) != EXPECTED_RECORDS_SHA256:
        raise ValueError("records_not_frozen")
    if (
        summary.get("batch_id") != BATCH_ID
        or summary.get("metadata", {}).get("hypothesis_id") != EXPECTED_HYPOTHESIS
        or summary.get("process_exit_code") != 0
        or summary.get("artifacts", {}).get("records", {}).get("sha256")
        != EXPECTED_RECORDS_SHA256
    ):
        raise ValueError("summary_contract_invalid")

    rows = _records(RECORDS)
    if not (
        len(rows) == 8
        and all(row.get("status") == "completed" for row in rows)
        and [row.get("case_id") for row in rows] == list(REVIEW_FACTS)
        and all(row.get("route_verified") is True for row in rows)
    ):
        raise ValueError("record_shape_invalid")

    reviews = []
    for row in rows:
        response = row.get("response")
        if not isinstance(response, dict):
            raise ValueError("response_invalid")
        facts = REVIEW_FACTS[row["case_id"]]
        reviews.append({
            "slot": row["slot"],
            "case_id": row["case_id"],
            "narrative": response["n"],
            "question": response["q"],
            "response_sha256": _sha_bytes(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
            "rendered_unit_ids": facts["rendered_unit_ids"],
            "transition_id": facts["transition_id"],
            "asserted_unknown_ids": facts["asserted_unknown_ids"],
            "criteria": {
                "unlisted_render_claim": False,
                "player_agency_attribution": False,
                "unauthorized_secret_disclosure": False,
                "mechanical_result_expansion": False,
                "continuity_material_repetition": False,
                "progression_observed": facts["progression_observed"],
                "coherent_hold_observed": facts["coherent_hold_observed"],
                "next_choice_preserved": True,
            },
            "unlisted_claims": [],
            "fatal_semantic_gate_passed": True,
            "rationale": facts["rationale"],
        })

    document = {
        "version": "openai-luna-low-semantic-review-v1",
        "hypothesis_id": EXPECTED_HYPOTHESIS,
        "batch_id": BATCH_ID,
        "reviewer": "codex-independent-semantic-review",
        "review_date": "2026-09-28",
        "source": {
            "summary_sha256": EXPECTED_SUMMARY_SHA256,
            "records_sha256": EXPECTED_RECORDS_SHA256,
        },
        "scope": {
            "records_total": 8,
            "records_completed": 8,
            "records_semantically_reviewed": 8,
            "records_failed_operationally": 0,
            "records_skipped_causally": 0,
            "candidate_qualification_permitted": True,
        },
        "reviews": reviews,
        "classification": {
            "candidate_id": "gpt-5.6-luna-openai-low-synthetic",
            "technical_semantic_result": "eligible_for_final_human_narrative_acceptance",
            "fatal_semantic_cases_failed": 0,
            "qualified_candidates": ["gpt-5.6-luna-openai-low-synthetic"],
            "narrator_admitted": False,
            "runtime_default_changed": False,
            "human_acceptance_required": True,
        },
    }
    target = output or REVIEWS / f"openai-luna-low-{BATCH_ID[:8]}-codex.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
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
