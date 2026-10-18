from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts import build_openrouter_free_narrator_l2_review as review


def test_builds_frozen_partial_l2_review(tmp_path: Path) -> None:
    output = review.build(tmp_path / "review.json")
    document = json.loads(output.read_text(encoding="utf-8"))

    assert document["source"]["summary_sha256"] == review.EXPECTED_SUMMARY_SHA256
    assert document["source"]["records_sha256"] == review.EXPECTED_RECORDS_SHA256
    assert document["scope"] == {
        "records_total": 24,
        "records_completed": 1,
        "records_semantically_reviewed": 1,
        "records_failed_operationally": 1,
        "records_skipped_causally": 22,
        "candidate_qualification_permitted": False,
    }
    assert document["review"]["criteria"]["unlisted_render_claim"] is True
    assert document["review"]["fatal_semantic_gate_passed"] is False
    assert document["classification"]["qualified_candidates"] == []
    assert document["classification"]["narrator_admitted"] is False


def test_refuses_tampered_l2_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(review, "EXPECTED_RECORDS_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="records_not_frozen"):
        review.build(tmp_path / "review.json")


def test_l2_observation_links_all_frozen_artifacts() -> None:
    report = json.loads(
        (
            review.ROOT
            / "evals/narrator/reports/openrouter-free-narrators-l2-observation-47f0c07f-2026-09-27.json"
        ).read_text(encoding="utf-8")
    )
    partial = (
        review.ROOT
        / "evals/narrator/reviews/openrouter-free-narrators-l2-47f0c07f-partial-codex.json"
    )

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert report["source_hashes"] == {
        "preflight_sha256": "bdb6969a598932d1f4bf9c4acbb744a97130b5bc3d0c03e4de4437c07c5f35fc",
        "summary_sha256": sha(review.SUMMARY),
        "records_sha256": sha(review.RECORDS),
        "partial_review_sha256": sha(partial),
    }
    assert report["execution"]["artifact_verification_passed"] is True
    assert report["classification"]["qualified_candidates"] == []
    assert report["classification"]["narrator_admitted"] is False
