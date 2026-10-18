"""Strict read-model boundaries; fixtures synthetic and no provider invocation."""
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from api.narrative_source_capsule import SourceTurnCapsule
from api.narrative_source_status import (
    PROTOCOL, SourceOperationFailure, SourceOperationSnapshot, SourceOperationStatusError,
    create_source_operation_snapshot, expected_source_attempt_metadata, safe_source_failure,
)
from test_narrative_source_capsule import capsule


def observe(value=None, **updates):
    args = dict(current_turn=0, current_state_revision=7, status="retained_unstarted")
    args.update(updates)
    return create_source_operation_snapshot(value or capsule(), **args)


def test_snapshot_has_only_observation_and_remains_readiness_neutral_when_stale():
    retained = capsule()
    value = observe(retained, current_turn=2, current_state_revision=10)
    payload = value.model_dump(mode="json")
    assert payload == {
        "protocol": PROTOCOL, "session_id": retained.session_id,
        "operation_id": retained.operation_id, "capsule_sha256": retained.fingerprint_sha256,
        "base_turn": 0, "base_state_revision": 7, "current_turn": 2,
        "current_state_revision": 10, "status": "retained_unstarted",
        "committed_turn_id": None, "failure": None,
    }
    assert SourceOperationSnapshot.model_validate_json(value.model_dump_json()) == value
    with pytest.raises(ValidationError):
        value.status = "pending"
    for forbidden in ("player_input", "system_prompt", "state", "relationships", "ready", "can_retry", "can_execute"):
        assert forbidden not in payload


@pytest.mark.parametrize("status", ["pending", "failed", "timeout", "cancelled"])
def test_non_completed_statuses_need_no_commit_or_available_diagnostic(status):
    assert observe(status=status).status == status


def test_completed_factory_binds_exact_draft_and_later_observed_revision():
    retained = capsule()
    value = observe(retained, status="completed", committed_turn_id=retained.draft.turn_id,
                    current_turn=3, current_state_revision=11)
    assert value.committed_turn_id == retained.draft.turn_id
    assert value.failure is None
    with pytest.raises(SourceOperationStatusError):
        observe(retained, status="completed", committed_turn_id="other", current_turn=1, current_state_revision=8)


@pytest.mark.parametrize("updates", [
    {"current_turn": True}, {"current_turn": 1.0}, {"current_state_revision": "7"},
    {"current_turn": -1}, {"current_state_revision": 6},
    {"current_turn": 9, "current_state_revision": 8}, {"status": "ready"},
    {"status": []}, {"status": "completed"}, {"committed_turn_id": "other"},
    {"status": "pending", "error": {"code": "source_turn_cancelled"}},
])
def test_factory_rejects_invalid_combinations_with_closed_error(updates):
    with pytest.raises(SourceOperationStatusError) as caught:
        observe(**updates)
    assert str(caught.value) == "source_operation_status_invalid"


@pytest.mark.parametrize("updates", [
    {"protocol": "legacy"}, {"session_id": True}, {"session_id": " padded"},
    {"session_id": ""}, {"operation_id": "x" * 241}, {"session_id": "\ud800"},
    {"capsule_sha256": "A" * 64}, {"capsule_sha256": "a" * 63},
    {"base_turn": True}, {"base_turn": 3, "base_state_revision": 2},
    {"base_turn": 1}, {"ready": True},
    {"status": "completed", "committed_turn_id": "turn", "current_turn": 0},
    {"status": "completed", "committed_turn_id": "turn", "current_turn": 1},
    {"failure": {"code": "source_turn_cancelled"}},
])
def test_model_rejects_forged_instances_types_and_relationships(updates):
    forged = observe().model_copy(update=updates)
    with pytest.raises(ValidationError) as caught:
        SourceOperationSnapshot.model_validate(forged)
    assert "input_value" not in str(caught.value)


@pytest.mark.parametrize("stage", [None, "preflight", "generation", "policy", "admission", "delivery", "commit"])
def test_literal_safe_code_and_stage_survive_while_free_evidence_does_not(stage):
    error = {"code": "scene_player_agency_violation", "stage": stage,
             "safe_message": "PRIVATE_SENTINEL", "evidence": {"text": "PRIVATE_SENTINEL"}}
    before = deepcopy(error)
    result = safe_source_failure(error)
    assert result.model_dump(mode="json") == {"code": error["code"], "stage": stage}
    assert error == before
    assert "PRIVATE_SENTINEL" not in result.model_dump_json()
    value = observe(status="failed", error=error)
    assert value.failure == result


@pytest.mark.parametrize("error", [
    None, "PRIVATE_SENTINEL", [], True, {}, {"code": None}, {"code": 3},
    {"code": "source_turn_PRIVATE_SENTINEL"}, {"code": "source_turn_cancelled "},
    {"code": "source_turn_cancelled", "stage": "PRIVATE_SENTINEL"},
    {"code": "source_turn_cancelled", "stage": False},
])
def test_unknown_or_nonliteral_failure_is_unavailable(error):
    assert safe_source_failure(error) is None
    assert observe(status="failed", error=error).failure is None


@pytest.mark.parametrize("code", ["source_turn_cancelled", "process_interrupted"])
def test_early_cancel_and_recovered_process_have_no_required_stage(code):
    error = {"category": "cancelled", "code": code, "safe_message": "PRIVATE_SENTINEL"}
    assert observe(status="cancelled", error=error).failure.model_dump(mode="json") == {"code": code, "stage": None}


def test_failure_model_rejects_extras_forgery_and_does_not_share_nested_instances():
    with pytest.raises(ValidationError):
        SourceOperationFailure(code="source_turn_cancelled", safe_message="PRIVATE_SENTINEL")
    failure = SourceOperationFailure(code="source_turn_cancelled")
    forged = failure.model_copy(update={"code": "PRIVATE_SENTINEL"})
    payload = observe(status="failed").model_dump(mode="json")
    with pytest.raises(ValidationError):
        SourceOperationSnapshot.model_validate({**payload, "failure": forged})
    value = SourceOperationSnapshot.model_validate({**payload, "failure": failure})
    assert value.failure is not failure
    with pytest.raises(ValidationError):
        value.failure.code = "source_turn_provider_failure"


@pytest.mark.parametrize("kind", ["mapping", "extra", "nested", "fingerprint"])
def test_both_helpers_revalidate_capsule_before_projecting_or_hashing(kind):
    value = capsule()
    if kind == "mapping":
        value = value.model_dump(mode="json")
    elif kind == "extra":
        value = value.model_copy(update={"PRIVATE_SENTINEL": "hidden"})
    elif kind == "nested":
        value.state["player_sheet"]["inventory"].append("PRIVATE_SENTINEL")
    else:
        value = value.model_copy(update={"fingerprint_sha256": "0" * 64})
    for helper in (lambda item: create_source_operation_snapshot(item, current_turn=0,
                   current_state_revision=7, status="pending"), expected_source_attempt_metadata):
        with pytest.raises(SourceOperationStatusError) as caught:
            helper(value)
        assert str(caught.value) == "source_operation_status_capsule_invalid"


def test_metadata_roundtrip_is_detached_and_static_changes_affect_only_expected_identity():
    value = capsule()
    before = value.model_dump(mode="json")
    result = expected_source_attempt_metadata(value)
    assert expected_source_attempt_metadata(SourceTurnCapsule.model_validate(before)) == result
    assert len(result) == 8
    assert len(result["source_turn_static_sha256"]) == 64
    assert result["source_context_base_state_revision"] == 7
    assert result["draft_id"] == value.draft.draft_id
    assert result["turn_id"] == value.draft.turn_id
    changed_prompt = expected_source_attempt_metadata(capsule(system_prompt="Different literal SYSTEM."))
    assert changed_prompt["source_turn_static_sha256"] != result["source_turn_static_sha256"]
    assert changed_prompt["expected_invocation_id"] == result["expected_invocation_id"]
    changed_operation = expected_source_attempt_metadata(capsule(operation_id="operation-2"))
    assert changed_operation["expected_invocation_id"] != result["expected_invocation_id"]
    assert changed_operation["source_turn_static_sha256"] != result["source_turn_static_sha256"]
    assert value.model_dump(mode="json") == before
    result["draft_id"] = "mutated result"
    assert expected_source_attempt_metadata(value)["draft_id"] == value.draft.draft_id
    assert value.system_prompt not in json.dumps(result)


def test_error_constructor_never_reflects_arbitrary_input():
    assert str(SourceOperationStatusError("PRIVATE_SENTINEL")) == "source_operation_status_invalid"
