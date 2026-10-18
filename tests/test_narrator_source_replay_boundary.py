"""A source view probe must not be reclassified as a CAP evaluation."""

from copy import deepcopy

import pytest

from scripts import evaluate_narrator_models as module


MARKERS = [
    ("purpose", "narrative_source_probe"),
    ("probe_kind", "narrative_source_probe"),
    ("experiment_version", "narrative-source-observation-v1"),
    ("protocol", "narrative-source-profile-v1"),
    ("kind", "narrative_source_call"),
    ("kind", "narrative_source_skip"),
]


def legacy_records():
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    records = [
        {"kind": "narrative_turn", "episode_id": episode["episode_id"],
         "turn_id": turn["turn_id"], "repetition": 1,
         "player_input": turn["player_input"], "outcome": turn["outcome"],
         "schema_valid": False, "admitted": False}
        for episode in corpus["episodes"] for turn in episode["turns"]
    ]
    return corpus, records


@pytest.mark.parametrize(("marker", "value"), MARKERS)
def test_source_marker_blocks_direct_replay_before_mutation(marker, value):
    corpus, records = legacy_records()
    records[0].update({marker: value, "full_evaluation": True})
    original = deepcopy(records)
    with pytest.raises(ValueError, match="narrative-source.*CAP-001"):
        module.replay_admission(records, corpus)
    assert records == original


@pytest.mark.parametrize(("marker", "value"), MARKERS)
def test_source_marker_blocks_cli_in_extra_rows_before_context_or_output(
    marker, value, monkeypatch, tmp_path
):
    _, records = legacy_records()
    records.append({"kind": "text_probe", marker: value, "full_evaluation": True})
    original = deepcopy(records)
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "source.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path / "output")
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: records)
    monkeypatch.setattr(module, "_require_record_context",
                        lambda *a: pytest.fail("context reached"))
    monkeypatch.setattr(module, "replay_admission",
                        lambda *a: pytest.fail("CAP replay reached"))
    args = module._parser().parse_args([
        "--replay", "source.jsonl", "--manifest",
        str(module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"),
        "--candidate", "qwen-3.8-27b-groq-free-synthetic-nonthink",
    ])
    with pytest.raises(SystemExit, match="narrative-source.*CAP-001"):
        module._run_offline_replay(args)
    assert records == original
    assert not (tmp_path / "output").exists()


def test_unmarked_legacy_evidence_keeps_its_existing_replay_result():
    corpus, records = legacy_records()
    original = deepcopy(records)
    replayed, repetitions = module.replay_admission(records, corpus)
    assert repetitions == 1 and len(replayed) == 7
    assert all(row["replay_status"] == "no_recorded_proposal" for row in replayed)
    assert records == original
