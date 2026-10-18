"""Evidence observations cannot be relabeled into a full CAP-001 replay."""

from copy import deepcopy

import pytest

from scripts import evaluate_narrator_models as module


MANIFEST = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"


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


@pytest.mark.parametrize("marker", ["purpose", "probe_kind"])
@pytest.mark.parametrize("kind", ["narrative_turn", "record_evidence_case", "text_probe"])
def test_direct_replay_rejects_evidence_markers_even_after_kind_changes(marker, kind):
    corpus, records = _legacy_records()
    if kind == "narrative_turn":
        records[0].update({marker: "record_evidence_probe", "full_evaluation": True})
    else:
        records.append({"kind": kind, marker: "record_evidence_probe", "full_evaluation": True})
    original = deepcopy(records)
    with pytest.raises(ValueError, match="record evidence.*CAP-001"):
        module.replay_admission(records, corpus)
    assert records == original


def test_unmarked_legacy_replay_keeps_its_original_behavior():
    corpus, records = _legacy_records()
    original = deepcopy(records)
    replayed, repetitions = module.replay_admission(records, corpus)
    assert repetitions == 1
    assert len(replayed) == 7
    assert all(row["replay_status"] == "no_recorded_proposal" for row in replayed)
    assert records == original


@pytest.mark.parametrize("marker", ["purpose", "probe_kind"])
def test_cli_boundary_refuses_evidence_before_context_replay_or_output(marker, monkeypatch, tmp_path):
    _, records = _legacy_records()
    records[-1].update({marker: "record_evidence_probe", "full_evaluation": True})
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "evidence.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path / "output")
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: records)
    monkeypatch.setattr(module, "_require_record_context", lambda *args: pytest.fail("context replay reached"))
    monkeypatch.setattr(module, "replay_admission", lambda *args: pytest.fail("CAP replay reached"))
    args = module._parser().parse_args([
        "--replay", "evidence.jsonl", "--manifest", str(MANIFEST), "--candidate", CANDIDATE,
    ])
    with pytest.raises(SystemExit, match="record evidence.*CAP-001"):
        module._run_offline_replay(args)
    assert not (tmp_path / "output").exists()
