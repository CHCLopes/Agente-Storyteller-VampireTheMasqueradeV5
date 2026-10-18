from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts import build_openrouter_free_narrator_review as review


BATCH_ID = "cbdad0ac-216c-4b40-baef-3b73c9ae1621"


def test_builds_byte_linked_partial_review(tmp_path: Path) -> None:
    output = review.build(BATCH_ID, tmp_path / "review.json")
    document = json.loads(output.read_text(encoding="utf-8"))

    assert document["source"]["records_sha256"] == review.EXPECTED_RECORDS_SHA256
    assert document["scope"] == {
        "records_total": 24,
        "records_completed": 1,
        "records_semantically_reviewed": 1,
        "incomplete_records_not_scored": 23,
        "candidate_qualification_permitted": False,
    }
    assert document["review"]["fatal_semantic_gate_passed"] is False
    assert document["review"]["criteria"]["unlisted_render_claim"] is True
    assert document["classification"]["qualified_candidates"] == []
    assert document["classification"]["narrator_admitted"] is False


def test_refuses_unfrozen_records_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review, "EXPECTED_RECORDS_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="records_not_frozen"):
        review.build(BATCH_ID, tmp_path / "review.json")


def test_observation_report_is_linked_to_frozen_artifacts() -> None:
    report = json.loads(
        (
            review.ROOT
            / "evals/narrator/reports/openrouter-free-narrators-observation-cbdad0ac-2026-09-27.json"
        ).read_text(encoding="utf-8")
    )
    run = review.ROOT / "eval-results" / f"{review.RUN_PREFIX}{BATCH_ID}"
    partial = (
        review.ROOT
        / "evals/narrator/reviews/openrouter-free-narrators-cbdad0ac-partial-codex.json"
    )

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert report["source_hashes"] == {
        "preflight_sha256": "362db87211b5b862aed7fde883c28f17c4a409bedbe8fce0034efed6f3bb0e2b",
        "records_sha256": sha(run / "records.jsonl"),
        "summary_sha256": sha(run / "summary.json"),
        "partial_review_sha256": sha(partial),
    }
    assert report["execution"]["calls_made"] == 15
    assert report["qualified_candidates"] == []
    assert report["narrator_admitted"] is False
