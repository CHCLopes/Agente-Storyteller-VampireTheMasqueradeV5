"""Do not attribute policy-skipped continuity turns to provider availability."""

from copy import deepcopy

import pytest

from scripts import evaluate_narrator_models as module


def _candidate():
    manifest = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
    return module.load_candidates(manifest)["qwen-3.8-27b-groq-free-synthetic-nonthink"]


def _records():
    candidate = _candidate()
    evidence = {
        "requested_target": {
            "model": candidate.model, "provider": candidate.provider_label,
        },
        "adapter": {"name": "groq-chat-completions"},
        "effective_model": {"value": candidate.model, "source": "reported"},
        "effective_provider": {"value": "Groq", "source": "observed"},
    }
    records = [
        {
            "kind": kind, "call_made": True, "passed": True,
            "evidence": deepcopy(evidence),
        }
        for kind in sorted(module._REQUIRED_PROBE_KINDS)
    ]
    for episode_id, turns in module._EXPECTED_CORPUS_CONTRACT:
        for turn_id, _ in turns:
            records.append({
                "kind": "narrative_turn", "call_made": True,
                "episode_id": episode_id, "turn_id": turn_id, "repetition": 1,
                "schema_valid": True, "admitted": True,
                "adversarial_case": (episode_id, turn_id) in module._ADVERSARIAL_CASES,
                "evidence": deepcopy(evidence),
            })
    return records


def test_policy_skips_do_not_masquerade_as_provider_failure():
    records = _records()
    for row in records:
        if row.get("episode_id") != "warehouse-continuity":
            continue
        if row["turn_id"] == "investigate-success":
            row["admitted"] = False
            row["admission_error"] = "scene_player_agency_violation"
        else:
            row["kind"] = "narrative_skip"
            row["call_made"] = False
            row["skipped_reason"] = "prior_turn_not_admitted"

    summary = module.summarize(_candidate(), records, repetitions=1)

    assert summary["narrative_calls"] == 5
    assert summary["narrative_turns_skipped"] == 2
    assert summary["hard_gates"]["no_timeout_or_rate_limit"] is True
    assert summary["hard_gates"]["all_expected_turns_attempted"] is False
    assert summary["hard_gates"]["all_screening_turns_admitted"] is False
    assert summary["automated_gates_passed"] is False
    assert summary["aborted_during_narratives"] is False
    assert summary["reliability_measurement"] == {
        "scope": "diagnostics_and_attempted_narrative_turns",
        "status": "no_timeout_or_rate_limit_observed",
        "error_counts": {"timeout": 0, "rate_limited": 0, "quota_exceeded": 0},
        "calls_made": 7, "expected_calls": 9,
        "all_expected_turns_attempted": False,
    }


@pytest.mark.parametrize("category", ["timeout", "rate_limited", "quota_exceeded"])
@pytest.mark.parametrize("kind", ["text_probe", "stream_probe", "narrative_turn"])
def test_actual_reliability_errors_fail_even_when_all_turns_exist(category, kind):
    records = _records()
    row = next(row for row in records if row["kind"] == kind)
    row["llm_error" if kind == "narrative_turn" else "error"] = {
        "category": category,
    }

    summary = module.summarize(_candidate(), records, repetitions=1)

    assert summary["hard_gates"]["all_expected_turns_attempted"] is True
    assert summary["hard_gates"]["no_timeout_or_rate_limit"] is False
    assert summary["automated_gates_passed"] is False
    measurement = summary["reliability_measurement"]
    assert measurement["status"] == "failure_observed"
    assert measurement["error_counts"][category] == 1
    assert sum(measurement["error_counts"].values()) == 1


def test_no_calls_is_unavailable_not_a_successful_reliability_sample():
    summary = module.summarize(_candidate(), [], repetitions=1)

    assert summary["hard_gates"]["no_timeout_or_rate_limit"] is False
    assert summary["automated_gates_passed"] is False
    assert summary["reliability_measurement"]["status"] == "unavailable"
    assert summary["reliability_measurement"]["calls_made"] == 0


def test_complete_clean_sample_keeps_all_automated_gates_passing():
    summary = module.summarize(_candidate(), _records(), repetitions=1)

    assert summary["hard_gates"]["no_timeout_or_rate_limit"] is True
    assert summary["automated_gates_passed"] is True
    measurement = summary["reliability_measurement"]
    assert measurement["calls_made"] == measurement["expected_calls"] == 9
    assert measurement["all_expected_turns_attempted"] is True
