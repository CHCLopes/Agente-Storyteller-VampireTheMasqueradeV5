"""Operational relational observations cannot enter CAP replay by partial relabeling."""
from copy import deepcopy
import pytest
from scripts import evaluate_narrator_models as module

MARKERS = [
    ("purpose", "summary_relational_qwen_probe"),
    ("probe_kind", "summary_relational_qwen_probe"),
    ("experiment_version", "record-summary-relational-qwen-observation-v1"),
    ("kind", "summary_relational_call"),
    ("kind", "summary_relational_skip"),
]

def legacy_records():
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    records = [{"kind": "narrative_turn", "episode_id": episode["episode_id"],
                "turn_id": turn["turn_id"], "repetition": 1,
                "player_input": turn["player_input"], "outcome": turn["outcome"],
                "schema_valid": False, "admitted": False}
               for episode in corpus["episodes"] for turn in episode["turns"]]
    return corpus, records

@pytest.mark.parametrize("marker,value", MARKERS)
def test_relational_marker_blocks_direct_replay_before_mutation(marker, value):
    corpus, records = legacy_records()
    records[0].update({marker: value, "full_evaluation": True})
    original = deepcopy(records)
    with pytest.raises(ValueError, match="summary-relational.*CAP-001"):
        module.replay_admission(records, corpus)
    assert records == original

@pytest.mark.parametrize("marker,value", MARKERS)
def test_relational_marker_blocks_cli_even_in_extra_row(marker, value, monkeypatch, tmp_path):
    _, records = legacy_records()
    records.append({"kind": "text_probe", marker: value, "full_evaluation": True})
    original = deepcopy(records)
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "relational.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path / "output")
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: records)
    monkeypatch.setattr(module, "_require_record_context", lambda *a: pytest.fail("context reached"))
    monkeypatch.setattr(module, "replay_admission", lambda *a: pytest.fail("CAP replay reached"))
    args = module._parser().parse_args([
        "--replay", "relational.jsonl", "--manifest",
        str(module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"),
        "--candidate", "qwen-3.8-27b-groq-free-synthetic-nonthink",
    ])
    with pytest.raises(SystemExit, match="summary-relational.*CAP-001"):
        module._run_offline_replay(args)
    assert records == original
    assert not (tmp_path / "output").exists()

def test_unmarked_legacy_records_keep_their_existing_behavior():
    corpus, records = legacy_records()
    original = deepcopy(records)
    replayed, repetitions = module.replay_admission(records, corpus)
    assert repetitions == 1 and len(replayed) == 7
    assert all(row["replay_status"] == "no_recorded_proposal" for row in replayed)
    assert records == original
