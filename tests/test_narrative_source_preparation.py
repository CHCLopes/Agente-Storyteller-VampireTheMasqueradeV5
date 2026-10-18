"""Focused pure boundaries for server-owned preparation; no provider or RNG."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_preparation import (
    PRODUCER, DeclaredActionPreparation, ResolvedActionPreparation,
    SourcePreparationCode, SourcePreparationError, prepare_source_turn_draft,
)
from api.rules_service import ResolutionResult, V5ActionPayload, V5Attribute, V5Skill
from api.scene_service import SceneState

NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)
INPUT = "Investigo a bancada sem tocar nos objetos."


def snapshot(session="synthetic-session"):
    return SourceContextSnapshot(
        origin=create_source_context_origin(session, SceneState(location="Oficina")),
        current_turn=0, state_revision=7, sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )


def action():
    return V5ActionPayload(
        intent=INPUT, attribute=V5Attribute.Intelligence, skill=V5Skill.INVESTIGATION,
        requires_roll=True, is_aggressive=False, inferred_difficulty=2,
    )


def receipt():
    return ResolutionResult(
        successes=2, is_success=True, bestial_failure=False, messy_critical=False,
        summary="  Recibo literal: cafe\u0301.\n", normal_rolls=[6, 2], hunger_rolls=[8], margin=0,
    )


def resolved():
    return ResolvedActionPreparation(action=action(), resolution=receipt())


def draft(preparation=None, **updates):
    values = dict(snapshot=snapshot(), operation_id="operation-1", created_at=NOW,
                  player_input=INPUT, preparation=preparation or DeclaredActionPreparation())
    values.update(updates)
    return prepare_source_turn_draft(**values)


def rejected(preparation=None, **updates):
    with pytest.raises(SourcePreparationError) as caught:
        draft(preparation, **updates)
    assert caught.value.code in {code.value for code in SourcePreparationCode}
    assert str(caught.value) == caught.value.code
    assert INPUT not in str(caught.value)
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    return caught.value.code


def test_declaration_preserves_input_without_interpreting_it_or_claiming_classifier_execution():
    # Deliberately not a no-roll text classifier: classification is an explicit
    # server premise, even when the literal input mentions mechanics.
    text = "Solicito um teste:  cafe\u0301."
    result = draft(player_input=text)
    assert result.player_input == text
    assert result.base_revision == 0 and result.base_state_revision == 7
    assert result.created_at == NOW
    assert len(result.facts) == len(result.events) == 1
    fact, event = result.facts[0], result.events[0]
    assert fact.fact_type == "action.declaration"
    assert fact.value["player_input"] == text and fact.value["requires_roll"] is False
    assert event.event_type == "player_action_declared"
    assert event.fact_ids == (fact.fact_id,)
    assert event.turn_id == result.turn_id and event.session_id == result.session_id
    assert fact.source_refs[0].record_id == PRODUCER
    assert "orchestrator.local_action_classification" not in result.model_dump_json()
    assert not result.state_changes and not result.context_references
    assert event.pending is False and event.visibility.value == "player"


def test_resolved_receipt_is_literal_and_detached_without_recalculation(monkeypatch):
    import api.rules_service as rules
    def prohibited(*_args, **_kwargs):
        raise AssertionError("The pure preparer must not run the rules engine or RNG")
    monkeypatch.setattr(rules, "calculate_resolution", prohibited)
    monkeypatch.setattr(rules.random, "randint", prohibited)
    original = receipt()
    prepared = ResolvedActionPreparation(action=action(), resolution=original)
    result = draft(prepared)
    value = result.facts[0].value
    assert {key: value[key] for key in ResolutionResult.model_fields} == original.model_dump(mode="json")
    assert value["attribute"] == "Intelligence" and value["skill"] == "Investigation"
    assert (value["dice_pool"], value["hunger_dice"], value["difficulty"]) == (3, 1, 2)
    assert value["outcome"] == "success"
    assert result.events[0].event_type == "player_action_resolved"
    original.normal_rolls.append(10)
    prepared.resolution.normal_rolls.append(9)
    assert value["normal_rolls"] == [6, 2]
    assert prepared.resolution.normal_rolls == [6, 2, 9]
    assert result.facts[0].source_refs[0].record_id == PRODUCER


def test_ordinary_failure_and_clean_critical_are_preserved_without_effects():
    for update in (
        dict(successes=1, is_success=False, normal_rolls=[2], hunger_rolls=[8], margin=-1),
        dict(successes=4, is_success=True, normal_rolls=[10, 10], hunger_rolls=[], margin=2),
    ):
        received = receipt().model_copy(update=update)
        result = draft(ResolvedActionPreparation(action=action(), resolution=received))
        assert all(result.facts[0].value[key] == value
                   for key, value in received.model_dump(mode="json").items())
        assert not result.state_changes


def test_ids_are_stable_role_separated_and_unambiguous_across_sessions_and_operations():
    first = draft()
    assert first == draft()
    assert len({first.draft_id, first.attempt_id, first.turn_id,
                first.facts[0].fact_id, first.events[0].event_id}) == 5
    left = draft(snapshot=snapshot("a/b"), operation_id="c")
    right = draft(snapshot=snapshot("a"), operation_id="b/c")
    assert left.turn_id != right.turn_id
    assert draft(operation_id="operation-2").turn_id != first.turn_id
    assert draft(snapshot=snapshot("other")).attempt_id != first.attempt_id


def test_frozen_preparations_and_json_roundtrip():
    original = resolved()
    with pytest.raises(ValidationError):
        original.kind = "declared_action"
    restored = ResolvedActionPreparation.model_validate_json(original.model_dump_json())
    assert draft(restored) == draft(original)
    assert DeclaredActionPreparation.model_validate_json('{"kind":"declared_action"}') == DeclaredActionPreparation()


@pytest.mark.parametrize("field,value", [
    ("requires_roll", False), ("action_target", "OPPOSED"),
    ("weapon_category", "light_melee"), ("power_used", "potence"),
    ("is_aggressive", True), ("is_feeding", True), ("is_healing", True),
    ("target_killed", True), ("is_bane_damage", True), ("is_blood_surge", True),
    ("is_willpower_reroll", True), ("is_compulsion_active", True), ("is_true_faith_active", True),
])
def test_effectful_or_nonordinary_actions_are_not_downgraded(field, value):
    forged = ResolvedActionPreparation.model_construct(
        action=action().model_copy(update={field: value}), resolution=receipt(),
    )
    rejected(forged)


@pytest.mark.parametrize("field", ["messy_critical", "bestial_failure"])
def test_special_results_are_outside_first_scope(field):
    rejected(ResolvedActionPreparation.model_construct(
        action=action(), resolution=receipt().model_copy(update={field: True}),
    ))


@pytest.mark.parametrize("update", [
    {"normal_rolls": [True]}, {"normal_rolls": [11]}, {"normal_rolls": [] , "hunger_rolls": []},
    {"successes": "2"}, {"is_success": 1}, {"summary": "\ud800"},
])
def test_malformed_receipts_cannot_be_laundered_by_model_construct(update):
    rejected(ResolvedActionPreparation.model_construct(
        action=action(), resolution=receipt().model_copy(update=update),
    ))


def test_missing_extra_and_wrong_branch_inputs_fail_closed_without_private_text():
    for value in (
        ResolvedActionPreparation.model_construct(action=action()),
        DeclaredActionPreparation.model_construct(kind="ordinary_resolution"),
        DeclaredActionPreparation().model_copy(update={"n": "PRIVATE_SENTINEL"}),
        ResolvedActionPreparation.model_construct(
            action=action().model_copy(update={"secret": "PRIVATE_SENTINEL"}), resolution=receipt()),
        ResolvedActionPreparation.model_construct(
            action=action(), resolution=receipt().model_copy(update={"n": "PRIVATE_SENTINEL"})),
        {"kind": "declared_action", "facts": ["PRIVATE_SENTINEL"]},
    ):
        rejected(value)


def test_mutating_nested_preparation_after_construction_is_revalidated():
    prepared = resolved()
    prepared.action.requires_roll = "false"
    rejected(prepared)
    prepared = resolved()
    prepared.resolution.normal_rolls.append(0)
    rejected(prepared)


def test_literal_action_input_mismatch_is_not_repaired():
    assert rejected(resolved(), player_input=INPUT.replace("bancada", "janela")) == "source_preparation_input_mismatch"


@pytest.mark.parametrize("operation", [" padded", "", True, "\ud800"])
def test_operation_identity_is_literal(operation):
    assert rejected(operation_id=operation) == "source_preparation_identity_invalid"


@pytest.mark.parametrize("updates", [
    {"player_input": " padded"}, {"player_input": True},
    {"created_at": NOW.replace(tzinfo=None)}, {"created_at": NOW.isoformat()},
])
def test_input_and_timestamp_are_not_silently_normalized(updates):
    rejected(**updates)


def test_forged_snapshots_and_origins_are_revalidated():
    valid = snapshot()
    before = deepcopy(valid.model_dump(mode="json"))
    cases = [valid.model_copy(update={"current_turn": 1}),
             valid.model_copy(update={"state_revision": True}),
             valid.model_copy(update={"extra": "PRIVATE_SENTINEL"}),
             valid.model_copy(update={"origin": valid.origin.model_copy(update={"session_id": "other"})}),
             SourceContextSnapshot.model_construct(), valid.model_dump(mode="json")]
    for value in cases:
        assert rejected(snapshot=value) == "source_preparation_snapshot_invalid"
    draft(snapshot=valid)
    assert valid.model_dump(mode="json") == before


def test_error_domain_does_not_echo_unknown_codes():
    for value in ("PRIVATE_SENTINEL", {"n": "PRIVATE_SENTINEL"}, None):
        assert str(SourcePreparationError(value)) == "source_preparation_invalid"


def test_structurally_valid_snapshot_with_revision_below_turn_is_rejected():
    # Reuse the existing pure source fixture, not a forged snapshot that would
    # fail a different gate before reaching this new consistency check.
    from test_narrative_source_context import _snapshot
    value = _snapshot().model_copy(update={"state_revision": 2})
    SourceContextSnapshot.model_validate(value)
    assert value.current_turn == 3
    assert rejected(snapshot=value) == "source_preparation_snapshot_invalid"
    valid = _snapshot()
    result = draft(snapshot=valid)
    assert (result.base_revision, result.base_state_revision) == (3, 7)
