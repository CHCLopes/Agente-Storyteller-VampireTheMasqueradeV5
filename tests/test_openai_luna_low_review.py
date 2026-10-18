from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts import build_openai_luna_low_review as review


def test_builds_frozen_complete_luna_review(tmp_path: Path) -> None:
    output = review.build(tmp_path / "review.json")
    document = json.loads(output.read_text(encoding="utf-8"))

    assert document["source"] == {
        "summary_sha256": review.EXPECTED_SUMMARY_SHA256,
        "records_sha256": review.EXPECTED_RECORDS_SHA256,
    }
    assert document["scope"] == {
        "records_total": 8,
        "records_completed": 8,
        "records_semantically_reviewed": 8,
        "records_failed_operationally": 0,
        "records_skipped_causally": 0,
        "candidate_qualification_permitted": True,
    }
    assert len(document["reviews"]) == 8
    assert all(item["fatal_semantic_gate_passed"] for item in document["reviews"])
    assert document["classification"]["qualified_candidates"] == [
        "gpt-5.6-luna-openai-low-synthetic"
    ]
    assert document["classification"]["narrator_admitted"] is False


def test_refuses_tampered_luna_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(review, "EXPECTED_RECORDS_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="records_not_frozen"):
        review.build(tmp_path / "review.json")


def test_luna_observation_links_all_frozen_artifacts() -> None:
    report = json.loads(
        (
            review.ROOT
            / "evals/narrator/reports/openai-luna-low-observation-c875289b-2026-09-28.json"
        ).read_text(encoding="utf-8")
    )
    semantic = (
        review.ROOT
        / "evals/narrator/reviews/openai-luna-low-c875289b-codex.json"
    )

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert report["source_hashes"] == {
        "preflight_sha256": "47138cae7ac41f7bf474651348905bba1d4cd61303fce1de1bc768de2ce15b0e",
        "summary_sha256": sha(review.SUMMARY),
        "records_sha256": sha(review.RECORDS),
        "semantic_review_sha256": sha(semantic),
    }
    assert report["execution"]["artifact_verification_passed"] is True
    assert report["execution"]["paid_live_gate_reclosed"] is True
    assert report["classification"]["narrator_admitted"] is False
