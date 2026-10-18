from __future__ import annotations

import json
from pathlib import Path

from scripts import build_closed_world_replication_review as review_builder
from scripts.evaluate_closed_world_render_plan import verify_responses


BATCH_ID = "dfd7febc-9e64-4ff6-b81c-c6c40cfd2aa0"


def test_review_builder_preserves_live_bytes_and_frozen_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(review_builder, "REVIEWS", tmp_path)

    outputs = review_builder.build(BATCH_ID)

    assert len(outputs) == 2
    results = {}
    for output in outputs:
        document = json.loads(output.read_text(encoding="utf-8"))
        target_id = document["target"]["requested"]["target_id"]
        results[target_id] = verify_responses(document)
        assert document["review_metadata"]["batch_id"] == BATCH_ID
        assert document["invocation"] == {"retry_count": 0, "fallback_used": False}
        assert len(document["responses"]) == 8

    assert results[review_builder.QWEN]["passed_count"] == 2
    assert results[review_builder.QWEN]["qualified_in_protocol"] is False
    assert results[review_builder.GPT]["passed_count"] == 0
    assert results[review_builder.GPT]["qualified_in_protocol"] is False

