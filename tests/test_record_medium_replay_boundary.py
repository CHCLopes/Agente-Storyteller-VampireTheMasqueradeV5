"""Medium reasoning probes remain outside CAP replay even after partial relabeling."""

from copy import deepcopy

import pytest

from scripts import evaluate_narrator_models as module


MANIFEST = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"
MEDIUM_MARKERS = [
    ("purpose", "record_evidence_reasoning_medium_probe"),
    ("probe_kind", "record_evidence_reasoning_medium_probe"),
    ("experiment_version", "record-evidence-reasoning-medium-v1"),
    ("kind", "record_evidence_reasoning_medium_call"),
    ("kind", "record_evidence_reasoning_medium_skip"),
]


def _legacy_records():
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    records = [
        {
            "kind": "narrative_turn", "episode_id": episode["episode_id"],
            "turn_id": turn["turn_id"], "repetition": 1,
            "player_input": turn["player_input"], "outcome": turn["outcome"],
            "schema_valid": False, "admitted": False,
        }
        for episode in corpus["episodes"] for turn in episode["turns"]
    ]
    return corpus, records


def _mark_record(records, marker, value, placement):
    if placement == "existing":
        target = records[0]
    else:
        target = {"kind": "text_probe"}
        records.append(target)
    target.update({marker: value, "full_evaluation": True})


@pytest.mark.parametrize("marker,value", MEDIUM_MARKERS)
@pytest.mark.parametrize("placement", ["existing", "extra"])
def test_direct_replay_rejects_each_reasoning_medium_identity_without_mutation(marker, value, placement):
    corpus, records = _legacy_records()
    _mark_record(records, marker, value, placement)
    original = deepcopy(records)
    with pytest.raises(ValueError, match="record evidence reasoning medium.*CAP-001"):
        module.replay_admission(records, corpus)
    assert records == original


@pytest.mark.parametrize("marker,value", MEDIUM_MARKERS)
@pytest.mark.parametrize("placement", ["existing", "extra"])
def test_cli_rejects_reasoning_medium_before_context_replay_or_output(
    marker, value, placement, monkeypatch, tmp_path,
):
    _, records = _legacy_records()
    _mark_record(records, marker, value, placement)
    original = deepcopy(records)
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "reasoning_medium.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path / "output")
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: records)
    monkeypatch.setattr(module, "_require_record_context", lambda *args: pytest.fail("context replay reached"))
    monkeypatch.setattr(module, "replay_admission", lambda *args: pytest.fail("CAP replay reached"))
    args = module._parser().parse_args([
        "--replay", "reasoning_medium.jsonl", "--manifest", str(MANIFEST), "--candidate", CANDIDATE,
    ])
    with pytest.raises(SystemExit, match="record evidence reasoning medium.*CAP-001"):
        module._run_offline_replay(args)
    assert not (tmp_path / "output").exists()
    assert records == original


def test_unmarked_legacy_replay_keeps_its_original_behavior():
    corpus, records = _legacy_records()
    original = deepcopy(records)
    replayed, repetitions = module.replay_admission(records, corpus)
    assert repetitions == 1
    assert len(replayed) == 7
    assert all(row["replay_status"] == "no_recorded_proposal" for row in replayed)
    assert records == original
