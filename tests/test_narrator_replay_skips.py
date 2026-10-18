"""Offline admission replay preserves explicit, unavailable continuation turns."""

from copy import deepcopy

import pytest

from scripts import evaluate_narrator_models as module


def _fixture(repetitions=1):
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    records = []
    for repetition in range(1, repetitions + 1):
        for episode in corpus["episodes"]:
            for turn_index, turn in enumerate(episode["turns"]):
                record = {
                    "episode_id": episode["episode_id"],
                    "turn_id": turn["turn_id"], "repetition": repetition,
                }
                if episode["episode_id"] == "warehouse-continuity" and turn_index:
                    record.update({
                        "kind": "narrative_skip", "call_made": False,
                        "skipped_reason": "previous_episode_turn_not_admitted",
                        "blocked_by_turn_id": "investigate-success",
                    })
                else:
                    scene = episode.get("initial_scene")
                    record.update({
                        "kind": "narrative_turn", "call_made": True,
                        "player_input": turn["player_input"], "outcome": turn["outcome"],
                        "schema_valid": True,
                        "admitted": episode["episode_id"] != "warehouse-continuity",
                        "proposal": {
                            "n": (
                                "A porta metálica vibra e a luz oscila sobre o concreto. "
                                "O rádio chia sobre uma bancada coberta de poeira antiga."
                            ),
                            "o": turn["outcome"],
                            "l": scene["location"] if scene else "Beco urbano",
                            "s": "A porta metálica vibra sob uma luz oscilante.",
                            "p": [], "f": [], "t": ["Investigar o rádio"], "r": [],
                            "q": "O que você faz agora?",
                        },
                    })
                records.append(record)
    return corpus, records


@pytest.mark.parametrize("repetitions", [1, 3])
def test_original_skips_remain_unavailable_even_if_blocker_is_now_admitted(
    monkeypatch, repetitions,
):
    corpus, records = _fixture(repetitions)
    original = deepcopy(records)
    validated = []

    def accepting_policy(proposal, **kwargs):
        validated.append(kwargs["player_input"])
        return proposal

    monkeypatch.setattr(module, "validate_scene_continuation", accepting_policy)
    replayed, actual_repetitions = module.replay_admission(records, corpus)

    assert records == original
    assert actual_repetitions == repetitions
    assert len(validated) == 5 * repetitions
    skips = [row for row in replayed if row["kind"] == "narrative_skip"]
    assert len(skips) == 2 * repetitions
    for skip in skips:
        assert skip["call_made"] is False
        assert skip["offline_replay"] is True
        assert skip["replay_status"] == "not_attempted_original_run"
        assert "proposal" not in skip
        assert skip.get("admitted") is not True
    parents = [row for row in replayed if row["turn_id"] == "investigate-success"]
    assert all(row["admitted"] is True for row in parents)
    assert all(row["original_admission"]["admitted"] is False for row in parents)
    manifest = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
    candidate = module.load_candidates(manifest)["qwen-3.8-27b-groq-free-synthetic-nonthink"]
    summary = module.summarize(candidate, replayed, repetitions)
    assert summary["narrative_calls"] == 5 * repetitions
    assert summary["narrative_turns_skipped"] == 2 * repetitions
    assert summary["hard_gates"]["all_expected_turns_attempted"] is False
    assert summary["automated_gates_passed"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("call_made", True),
    ("skipped_reason", "provider_unavailable"),
    ("blocked_by_turn_id", "establish-scene"),
    ("blocked_by_turn_id", "follow-discovered-detail"),
    ("proposal", {"n": "Fabricated continuation"}),
    ("evidence", {}),
    ("llm_error", {"category": "timeout"}),
    ("admitted", True),
    ("schema_valid", True),
    ("player_input", "Different input"),
    ("outcome", "success"),
])
def test_skip_cannot_claim_unmade_response_or_invalid_predecessor(field, value):
    corpus, records = _fixture()
    skip = next(row for row in records if row["kind"] == "narrative_skip")
    skip[field] = value
    with pytest.raises(ValueError, match="invalid narrative skip"):
        module.replay_admission(records, corpus)


def test_skip_cannot_follow_originally_admitted_predecessor():
    corpus, records = _fixture()
    next(row for row in records if row["turn_id"] == "investigate-success")["admitted"] = True
    with pytest.raises(ValueError, match="invalid narrative skip"):
        module.replay_admission(records, corpus)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "reordered"])
def test_replay_still_requires_exact_unique_ordered_corpus(mutation):
    corpus, records = _fixture()
    if mutation == "missing":
        records.pop(3)
    elif mutation == "duplicate":
        records.append(deepcopy(records[2]))
    elif mutation == "unknown":
        records[2]["turn_id"] = "unknown-turn"
    else:
        records[2], records[3] = records[3], records[2]
    with pytest.raises(ValueError, match="exact evaluation corpus|out of corpus order"):
        module.replay_admission(records, corpus)


def test_a_single_opening_cannot_be_promoted_to_corpus_replay():
    corpus, records = _fixture()
    with pytest.raises(ValueError, match="exact evaluation corpus"):
        module.replay_admission(records[:1], corpus)


def test_skip_cannot_start_an_episode_without_attempted_predecessor():
    corpus, records = _fixture()
    records[0] = {
        **records[2], "episode_id": "opening", "turn_id": "establish-scene",
    }
    with pytest.raises(ValueError, match="invalid narrative skip"):
        module.replay_admission(records, corpus)


def test_replay_cannot_resume_after_an_original_skip():
    corpus, records = _fixture()
    turn = corpus["episodes"][1]["turns"][2]
    records[3] = {
        **records[1], "turn_id": turn["turn_id"],
        "player_input": turn["player_input"], "outcome": turn["outcome"],
    }
    with pytest.raises(ValueError, match="resumes an originally skipped episode"):
        module.replay_admission(records, corpus)


def test_cli_replay_validation_failure_is_safe_and_has_no_raw_traceback(monkeypatch):
    def invalid_replay(args):
        raise ValueError("untrusted-record-content")

    monkeypatch.setattr(module, "_run_offline_replay", invalid_replay)
    with pytest.raises(SystemExit, match="Offline replay rejected") as caught:
        module.main(["--replay", "recorded.jsonl", "--candidate", "synthetic-test"])
    assert "untrusted-record-content" not in str(caught.value)
