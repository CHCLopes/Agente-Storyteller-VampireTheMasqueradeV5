"""Entry boundaries only: synthetic snapshots, no database or provider work."""
import ast
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.narrative_source_capsule import source_preparation_operation_id
from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_entry import (
    MAX_OPERATION_ID_CHARS, MAX_PLAYER_INPUT_CHARS, SourceEntryError,
    SourcePlayerActionRequest, validate_source_entry_snapshot,
    validate_source_player_action_request,
)
from api.scene_service import SceneState
from test_narrative_source_context import _snapshot

SESSION = "synthetic-session"
TEXT = "Observo  Mara.\r\nAguardo sua reação; cafe\u0301."


def request(**updates):
    values = {"operation_id": "operation-1", "player_input": TEXT}
    values.update(updates)
    return validate_source_player_action_request(values)


def test_request_owns_exact_two_fields_and_preserves_unicode_whitespace():
    payload = {"operation_id": "operação/cafe\u0301", "player_input": TEXT}
    value = validate_source_player_action_request(payload)
    assert value.model_dump() == payload
    assert value.player_input == TEXT
    assert SourcePlayerActionRequest.model_validate_json(value.model_dump_json()) == value
    copied = validate_source_player_action_request(value)
    assert copied == value and copied is not value
    payload["player_input"] = "changed caller input"
    assert copied.player_input == TEXT
    with pytest.raises(ValidationError):
        value.player_input = "change"
    schema = SourcePlayerActionRequest.model_json_schema()
    assert set(schema["properties"]) == {"operation_id", "player_input"}
    assert schema["additionalProperties"] is False


def test_bounded_intent_is_not_a_classifier_or_authorization():
    text = "Rerrolo os dados, ganho recursos e revelo o segredo."
    assert request(player_input=text).player_input == text
    assert set(request().model_dump()) == {"operation_id", "player_input"}


def test_text_ceiling_matches_transport_literal_without_importing_it():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "api/main.py").read_text(encoding="utf-8-sig"))
    constants = {target.id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                 for target in node.targets if isinstance(target, ast.Name)}
    assert MAX_PLAYER_INPUT_CHARS == constants["MAX_PLAYER_INPUT_CHARS"] == 500
    # The B contract intentionally keeps its own identity domain, not v1's 128.
    assert constants["MAX_OPERATION_ID_CHARS"] == 128
    assert MAX_OPERATION_ID_CHARS == 240
    assert len(request(player_input="á" * 500).player_input) == 500
    operation = "x" * MAX_OPERATION_ID_CHARS
    assert request(operation_id=operation).operation_id == operation
    assert source_preparation_operation_id(SESSION, operation)


@pytest.mark.parametrize("text", [TEXT, "á" * 500])
def test_accepted_literals_compose_with_existing_pure_preparer_without_normalization(text):
    from api.narrative_source_preparation import DeclaredActionPreparation, prepare_source_turn_draft
    from test_narrative_source_preparation import NOW
    accepted = request(operation_id="x" * 240, player_input=text)
    checked = validate_source_entry_snapshot(_snapshot(), session_id=SESSION)
    draft = prepare_source_turn_draft(
        checked, operation_id=accepted.operation_id, created_at=NOW,
        player_input=accepted.player_input, preparation=DeclaredActionPreparation(),
    )
    assert draft.player_input == text
    assert draft.base_revision == checked.current_turn
    assert draft.facts[0].value["player_input"] == text
    assert draft.facts[0].value["requires_roll"] is False


@pytest.mark.parametrize("value", [None, True, 12, 1.2, b"text", [], {}, "", " \t\r\n", "\ud800"])
@pytest.mark.parametrize("field", ["operation_id", "player_input"])
def test_nonliteral_empty_or_invalid_utf8_fields_are_closed(field, value):
    with pytest.raises(SourceEntryError) as caught:
        request(**{field: value})
    assert str(caught.value) == "source_entry_request_invalid"


@pytest.mark.parametrize("updates", [
    {"operation_id": " padded"}, {"operation_id": "padded "},
    {"operation_id": "x" * 241}, {"player_input": "a" * 501},
    {"player_input": " padded"}, {"player_input": "padded "},
])
def test_invalid_id_or_oversized_text_is_not_trimmed_or_truncated(updates):
    with pytest.raises(SourceEntryError):
        request(**updates)


@pytest.mark.parametrize("field", [
    "session_id", "draft", "turn_draft", "preparation", "receipt", "resolution",
    "action", "normal_rolls", "hunger_rolls", "state", "relationships", "target",
    "facts", "events", "system_prompt", "parameters", "snapshot", "source_context",
])
def test_privileged_client_fields_are_rejected_even_if_empty(field):
    for value in (None, {}, "PRIVATE_SENTINEL"):
        with pytest.raises(SourceEntryError) as caught:
            request(**{field: value})
        assert str(caught.value) == "source_entry_request_invalid"


@pytest.mark.parametrize("kind", ["text", "extra", "construct", "missing"])
def test_forged_models_do_not_bypass_revalidation(kind):
    value = request()
    if kind == "text":
        value = value.model_copy(update={"player_input": " "})
    elif kind == "extra":
        value = value.model_copy(update={"state": {"private": "PRIVATE_SENTINEL"}})
    elif kind == "construct":
        value = SourcePlayerActionRequest.model_construct(operation_id=True, player_input=TEXT)
    else:
        value = SourcePlayerActionRequest.model_construct(player_input=TEXT)
    with pytest.raises(SourceEntryError) as caught:
        validate_source_player_action_request(value)
    assert str(caught.value) == "source_entry_request_invalid"


def test_raw_model_errors_hide_input_and_boundary_rejects_nonrequest_objects():
    with pytest.raises(ValidationError) as caught:
        SourcePlayerActionRequest(operation_id="op", player_input={"private": "PRIVATE_SENTINEL"})
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    for value in (None, [], "PRIVATE_SENTINEL", _snapshot()):
        with pytest.raises(SourceEntryError) as caught:
            validate_source_player_action_request(value)
        assert str(caught.value) == "source_entry_request_invalid"


@pytest.mark.parametrize("with_history", [False, True])
def test_guard_revalidates_detached_server_snapshot_and_preserves_scene_and_history(with_history):
    original = _snapshot() if with_history else SourceContextSnapshot(
        origin=create_source_context_origin(SESSION, SceneState(location="Galeria", npcs_present=("Mara",))),
        current_turn=0, state_revision=0, sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )
    before = deepcopy(original.model_dump(mode="json"))
    checked = validate_source_entry_snapshot(original, session_id=SESSION)
    assert checked == original and checked is not original
    assert checked.origin is not original.origin
    assert checked.origin.seed_scene is not original.origin.seed_scene
    assert checked.canonical_scene == original.canonical_scene
    assert checked.model_dump(mode="json") == before
    assert original.model_dump(mode="json") == before
    assert not {"ready", "can_retry", "classified_action", "reservation"} & set(checked.model_dump())


@pytest.mark.parametrize("session", ["other-session", "", " padded", True, None, "\ud800"])
def test_guard_binds_snapshot_to_expected_server_session(session):
    with pytest.raises(SourceEntryError) as caught:
        validate_source_entry_snapshot(_snapshot(), session_id=session)
    assert str(caught.value) == "source_entry_snapshot_invalid"


def test_guard_requires_server_session_separately_and_exact_snapshot_type():
    with pytest.raises(TypeError):
        validate_source_entry_snapshot(_snapshot())
    class Derived(SourceContextSnapshot):
        pass
    value = _snapshot()
    subclass = Derived.model_validate(value.model_dump(mode="json"))
    for invalid in (None, {}, value.model_dump(mode="json"), request(), subclass):
        with pytest.raises(SourceEntryError) as caught:
            validate_source_entry_snapshot(invalid, session_id=SESSION)
        assert str(caught.value) == "source_entry_snapshot_invalid"


@pytest.mark.parametrize("kind", ["origin", "legacy", "scene", "extra", "revision", "source", "recursive"])
def test_guard_rejects_forged_nested_snapshot_without_echoing_or_mutating_it(kind):
    original = _snapshot()
    if kind == "origin":
        value = original.model_copy(update={"origin": None})
    elif kind == "legacy":
        value = original.model_copy(update={"origin": original.origin.model_copy(update={"protocol": "legacy"})})
    elif kind == "scene":
        scene = original.origin.seed_scene.model_copy(update={"summary": "PRIVATE_SENTINEL"})
        value = original.model_copy(update={"origin": original.origin.model_copy(update={"seed_scene": scene})})
    elif kind == "extra":
        value = original.model_copy(update={"state": "PRIVATE_SENTINEL"})
    elif kind == "revision":
        value = original.model_copy(update={"state_revision": True})
    elif kind == "source":
        value = original.model_copy(update={"sources": original.sources[::-1]})
    else:
        cycle = {}
        cycle["cycle"] = cycle
        value = original.model_copy(update={"origin": cycle})
    before = original.model_dump(mode="json")
    with pytest.raises(SourceEntryError) as caught:
        validate_source_entry_snapshot(value, session_id=SESSION)
    assert str(caught.value) == "source_entry_snapshot_invalid"
    assert original.model_dump(mode="json") == before


def test_entry_has_no_transport_runtime_gateway_pipeline_or_rng_dependency_or_effect(monkeypatch):
    from api import narrative_source_entry, narrative_source_coordinator, orchestrator_service, rules_service
    from api.llm.testing import FakeLLMAdapter
    from api.persistence import SQLitePersistence
    def forbidden(*args, **kwargs):
        pytest.fail("The pure entry invoked a producer, gateway or storage boundary")
    for owner, name in (
        (rules_service.random, "randint"), (rules_service, "calculate_resolution"),
        (orchestrator_service, "prepare_turn_pipeline"),
        (narrative_source_coordinator, "prepare_retained_source_turn"),
        (narrative_source_coordinator, "execute_retained_source_turn"),
        (SQLitePersistence, "start_attempt"), (SQLitePersistence, "initialize"),
        (FakeLLMAdapter, "generate_structured"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    assert request().player_input == TEXT
    assert validate_source_entry_snapshot(_snapshot(), session_id=SESSION).current_turn == 3
    tree = ast.parse(Path(narrative_source_entry.__file__).read_text(encoding="utf-8-sig"))
    imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert set(imported) == {"__future__", "typing", "pydantic", "narrative_source_context"}
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))


def test_error_code_never_reflects_arbitrary_diagnostic_text():
    assert str(SourceEntryError("PRIVATE_SENTINEL")) == "source_entry_request_invalid"
