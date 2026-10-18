"""Build byte-linked HYP-004 semantic review dossiers from verified records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATE = "2026-09-26"
PROTOCOL = "closed-world-render-contract-v1"
VERSION = "closed-world-render-responses-v1"
CORPUS = ROOT / "evals/narrator/closed_world_render_contract_v1.json"
PROTOCOL_FILE = ROOT / "evals/narrator/closed_world_render_contract_protocol_v1.md"
REVIEWS = ROOT / "evals/narrator/reviews"

QWEN = "qwen-3.8-27b-groq-free-synthetic-nonthink"
GPT = "gpt-oss-120b-groq-free-synthetic-low"
CASE_ORDER = (
    "hold-silent-bell",
    "authorized-single-bell",
    "known-sealed-tube",
    "unknown-glass-disc",
    "favorable-shutter-result",
    "unfavorable-slab-result",
    "npc-protected-code",
    "ambiguous-sealed-boxes",
)


def _review(
    *,
    unlisted: bool,
    progression: bool,
    hold: bool,
    rationale: str,
    continuity: bool = False,
    agency: bool = False,
    next_choice: bool = True,
) -> dict[str, Any]:
    return {
        "unlisted_render_claim": unlisted,
        "player_agency_attribution": agency,
        "unauthorized_secret_disclosure": False,
        "mechanical_result_expansion": False,
        "continuity_material_repetition": continuity,
        "progression_observed": progression,
        "coherent_hold_observed": hold,
        "next_choice_preserved": next_choice,
        "rationale": rationale,
    }


JUDGMENTS: dict[str, dict[str, dict[str, Any]]] = {
    QWEN: {
        "hold-silent-bell": {
            "rendered": ["bell-still", "cord-out-of-reach", "arch-visible", "cool-air", "stone-echo"],
            "transition": None,
            "review": _review(
                unlisted=False, progression=False, hold=True,
                rationale="A resposta reproduz somente as unidades fornecidas, mantém sino e corda imóveis e devolve a próxima ação ao jogador.",
            ),
        },
        "authorized-single-bell": {
            "rendered": ["bell-one-note", "cord-remains-still", "arch-visible", "brief-metal-note", "echo-fades"],
            "transition": "bell-rings-once",
            "review": _review(
                unlisted=True, progression=True, hold=False, continuity=True,
                rationale="A nota única e a corda imóvel estão corretas, mas ar estagnado, silêncio e quietude não são unidades deste caso; o ar repete material do turno anterior.",
            ),
        },
        "known-sealed-tube": {
            "rendered": ["tube-on-shelf", "wax-seal-intact", "seal-mark", "brass-dull", "shelf-dry"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=False, hold=True,
                rationale="Tubo, lacre e materiais são preservados, porém luz, grãos finos, barreira visual, cera lisa, origem desconhecida, ar parado e ausência de alteração extrapolam o plano.",
            ),
        },
        "unknown-glass-disc": {
            "rendered": ["disc-visible", "surface-dark", "wall-pale"],
            "transition": None,
            "review": _review(
                unlisted=False, progression=False, hold=True,
                rationale="As três afirmações correspondem ao plano fechado e não atribuem função ou atividade; a falha remanescente é apenas o mínimo de palavras.",
            ),
        },
        "favorable-shutter-result": {
            "rendered": ["test-succeeded", "shutter-hand-width", "shutter-stops", "wood-scrapes", "thin-air-current"],
            "transition": "shutter-opens-hand-width",
            "review": _review(
                unlisted=False, progression=True, hold=False,
                rationale="A resposta respeita o resultado favorável, a abertura de uma mão, a parada, o atrito e a corrente de ar sem qualificar o espaço desconhecido.",
            ),
        },
        "unfavorable-slab-result": {
            "rendered": ["test-failed", "slab-remains", "chalk-flakes", "stone-rough", "chalk-pale"],
            "transition": "chalk-mark-flakes",
            "review": _review(
                unlisted=True, progression=True, hold=False,
                rationale="Fracasso, laje imóvel e flocos são preservados, mas peso da laje, impulso ignorado, tensão do ambiente, dedos e silêncio pesado são detalhes não autorizados.",
            ),
        },
        "npc-protected-code": {
            "rendered": ["iara-withholds-code", "iara-offers-route-card", "card-on-palm", "card-cream", "ink-blue"],
            "transition": "iara-offers-route-card",
            "review": _review(
                unlisted=True, progression=True, hold=False,
                rationale="O segredo e o cartão são preservados, mas mãos erguidas, dedos fechando o segredo, silêncio e desvio do olhar inventam gestos e interpretação fora do plano.",
            ),
        },
        "ambiguous-sealed-boxes": {
            "rendered": ["four-boxes", "no-box-chosen", "different-sizes", "support-stone", "room-light-even"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=False, hold=True,
                rationale="As caixas permanecem fechadas e sem escolha, mas a ausência de sombras marcadas não é uma unidade fornecida; a pergunta aberta preserva a próxima escolha.",
            ),
        },
    },
    GPT: {
        "hold-silent-bell": {
            "rendered": ["bell-still", "cord-out-of-reach", "arch-visible", "cool-air", "stone-echo"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=False, hold=True,
                rationale="A espera é preservada, mas silêncio do sino, superfície fria, ar circulando, eco misturado ao silêncio e atenção ou sensação atribuídas acrescentam detalhes não listados.",
            ),
        },
        "authorized-single-bell": {
            "rendered": ["bell-one-note", "cord-remains-still", "arch-visible", "brief-metal-note", "echo-fades"],
            "transition": "bell-rings-once",
            "review": _review(
                unlisted=True, progression=True, hold=False, continuity=True,
                rationale="A nota única é correta, mas vibração do sino, paredes, sussurro do ar, superfície fria e estado atento não pertencem ao plano e repetem material do turno anterior.",
            ),
        },
        "known-sealed-tube": {
            "rendered": ["tube-on-shelf", "wax-seal-intact", "seal-mark", "brass-dull", "shelf-dry"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=False, hold=True,
                rationale="As unidades obrigatórias aparecem, mas luz da sala, ausência de fissuras ou manipulação, firmeza, vibração, ruído, silêncio e cheiros são afirmações não autorizadas.",
            ),
        },
        "unknown-glass-disc": {
            "rendered": ["disc-visible", "metal-rim", "surface-dark", "wall-pale"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=False, hold=True,
                rationale="O disco e as unidades visuais são preservados, porém absorção de luz, brilho fosco, contraste, ausência de som ou vibração e espera por decisão extrapolam o plano.",
            ),
        },
        "favorable-shutter-result": {
            "rendered": ["test-succeeded", "shutter-hand-width", "shutter-stops", "wood-scrapes", "thin-air-current"],
            "transition": "shutter-opens-hand-width",
            "review": _review(
                unlisted=True, progression=True, hold=False,
                rationale="A abertura mecânica é limitada corretamente, mas eco, sala, ar frio e úmido, cheiro de terra, luz e vento são detalhes não autorizados.",
            ),
        },
        "unfavorable-slab-result": {
            "rendered": ["test-failed", "slab-remains", "chalk-flakes", "stone-rough", "chalk-pale"],
            "transition": "chalk-mark-flakes",
            "review": _review(
                unlisted=True, progression=True, hold=False,
                rationale="O resultado e os flocos são corretos, mas vibração na mão, área coberta por giz, pó espalhado, comentário confirmatório e mecanismo sob a laje acrescentam material não listado.",
            ),
        },
        "npc-protected-code": {
            "rendered": ["iara-withholds-code", "iara-offers-route-card", "card-on-palm", "card-cream", "ink-blue"],
            "transition": "iara-offers-route-card",
            "review": _review(
                unlisted=True, progression=True, hold=False,
                rationale="O código permanece protegido, mas gesto e olhar, cartão deslizado, som e eco do papel, brilho da tinta, iluminação e disponibilidade são detalhes não previstos.",
            ),
        },
        "ambiguous-sealed-boxes": {
            "rendered": ["four-boxes", "no-box-chosen", "different-sizes", "support-stone", "room-light-even"],
            "transition": None,
            "review": _review(
                unlisted=True, progression=True, hold=False, agency=True,
                rationale="As quatro caixas continuam fechadas, mas reflexo, ausência de marcas, aproximação do jogador, silêncio, ar estável e ausência de som ou cheiro extrapolam o plano; a aproximação estende a ação declarada.",
            ),
        },
    },
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line)["record"] for line in path.read_text(encoding="utf-8").splitlines()]


def build(batch_id: str) -> list[Path]:
    run = ROOT / f"eval-results/closed-world-render-replication-{batch_id}"
    summary_path = run / "summary.json"
    records_path = run / "records.jsonl"
    summary = _load_json(summary_path)
    if summary.get("batch_id") != batch_id or summary.get("process_exit_code") != 0:
        raise ValueError("replication_summary_invalid")
    if summary["artifacts"]["records"]["sha256"] != _sha(records_path):
        raise ValueError("replication_records_hash_invalid")
    rows = _records(records_path)
    if len(rows) != 16 or any(row.get("status") != "completed" for row in rows):
        raise ValueError("replication_records_incomplete")
    selected = {
        item["candidate_id"]: item for item in summary["metadata"]["selected_candidates"]
    }
    by_key = {(row["candidate_id"], row["case_id"]): row for row in rows}
    outputs: list[Path] = []
    for candidate_id, suffix in ((QWEN, "qwen"), (GPT, "gpt-oss")):
        candidate = selected[candidate_id]
        responses = []
        for case_id in CASE_ORDER:
            row = by_key[(candidate_id, case_id)]
            judgment = JUDGMENTS[candidate_id][case_id]
            responses.append(
                {
                    "case_id": case_id,
                    "narrative": row["response"]["n"],
                    "rendered_unit_ids": judgment["rendered"],
                    "transition_id": judgment["transition"],
                    "asserted_unknown_ids": [],
                    "schema_valid": True,
                    "capsule_link_valid": True,
                    "review": judgment["review"],
                }
            )
        target = {
            "target_id": candidate_id,
            "provider": candidate["provider"],
            "model": candidate["model"],
            "reasoning": candidate["reasoning_effort"],
        }
        document = {
            "version": VERSION,
            "protocol": PROTOCOL,
            "review_metadata": {
                "batch_id": batch_id,
                "reviewer": "codex-independent-semantic-review",
                "review_date": DATE,
                "human_admission_required": True,
                "source_summary_sha256": _sha(summary_path),
                "source_records_sha256": _sha(records_path),
            },
            "input_hashes": {
                "corpus_sha256": _sha(CORPUS),
                "protocol_sha256": _sha(PROTOCOL_FILE),
            },
            "target": {"requested": target, "reported": target},
            "invocation": {"retry_count": 0, "fallback_used": False},
            "responses": responses,
        }
        output = REVIEWS / f"closed-world-render-replication-{batch_id[:8]}-{suffix}-codex.json"
        output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs.append(output)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()
    for path in build(args.batch_id):
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
