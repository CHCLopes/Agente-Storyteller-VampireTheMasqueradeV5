from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from api.narrative_grounding import (
    DerivationDestination, NarrativeVisibility, bind_narrative_derivation,
    create_narrative_source, materialize_source_projection,
)
from api.narrative_source_context import (
    ORIGIN_PROTOCOL, SELECTION_PROTOCOL, SourceContextCode, SourceContextError,
    SourceContextOrigin, SourceContextSnapshot, create_source_context_origin,
    validate_source_context_origin, validate_source_scene,
    validate_source_selection, validate_source_state_context,
)
from api.narrative_source_profile import VERSION
from api.narrative_source_turn import NarrativeSourceTurnEnvelope
from api.scene_service import SceneState


SCENE = SceneState(location="Galeria", npcs_present=("Mara", "Ivo"))


def _origin():
    return create_source_context_origin("synthetic-session", SCENE)


def _envelope(index: int, session: str = "synthetic-session"):
    text = "A luz permanece acesa junto à janela da galeria silenciosa."
    question = "O que você faz?"
    source = create_narrative_source(
        source_id=f"source-{index}", session_id=session, turn_id=f"turn-{index}",
        invocation_id=f"invocation-{index}", text=text, source_policy=VERSION,
        visibility=NarrativeVisibility.PLAYER,
    )
    binding = bind_narrative_derivation(
        source, text, destination=DerivationDestination.NARRATIVE_SOURCE_VIEW,
    )
    projection = materialize_source_projection(source, binding, text)
    return NarrativeSourceTurnEnvelope(
        operation_id=f"operation-{index}", attempt_id=f"attempt-{index}",
        narrative_id=f"narrative-{index}", question=question, projection=projection,
        source_event_ids=(f"event-{index}",),
        presentation_sha256=hashlib.sha256((text + "\n\n" + question).encode()).hexdigest(),
        # Pure envelope consistency does not authenticate a provider audit.
        provenance_sha256="0" * 64,
    )


def _snapshot():
    return SourceContextSnapshot(
        origin=_origin(), current_turn=3, state_revision=7,
        sources=(_envelope(2), _envelope(3)),
        selected_turn_ids=("turn-2", "turn-3"), omitted_turn_ids=("turn-1",),
    )


def test_origin_binds_exact_normalized_scene_and_session_deterministically():
    origin = _origin()
    payload = {
        "protocol": ORIGIN_PROTOCOL, "creator": "explicit_server_seed",
        "session_id": "synthetic-session", "seed_scene": SCENE.model_dump(mode="json"),
    }
    expected = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    assert origin.fingerprint_sha256 == expected
    assert _origin() == origin
    assert validate_source_context_origin(
        origin.model_dump(mode="json"), session_id="synthetic-session",
    ) == origin
    assert validate_source_scene(SCENE, origin) == origin.seed_scene


def test_origin_and_nested_scene_are_immutable_and_detached():
    raw = SCENE.model_dump(mode="json")
    origin = create_source_context_origin("synthetic-session", raw)
    raw["npcs_present"].append("Outro")
    assert origin.seed_scene.npcs_present == ("Mara", "Ivo")
    with pytest.raises(ValidationError):
        origin.session_id = "other"
    with pytest.raises(ValidationError):
        origin.seed_scene.location = "Other"


@pytest.mark.parametrize("session", ["", " ", " padded", "padded ", "line\n", True, 3, None, "\ud800"])
def test_nonliteral_or_invalid_session_ids_are_rejected(session):
    with pytest.raises(SourceContextError):
        create_source_context_origin(session, SCENE)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("summary", "Texto legado."), ("summary", " "),
        ("details", ["Detalhe legado"]), ("details", [""]),
        ("open_threads", ["Pergunta antiga"]), ("last_turn", 1),
        ("last_turn", True), ("last_turn", "0"),
        ("location", " Galeria"), ("npcs_present", [" Mara", "Ivo"]),
        ("npcs_present", ["Mara", "mara"]), ("npcs_present", {"Mara", "Ivo"}),
        ("l", "Galeria"), ("private_extra", "DO_NOT_ECHO"),
    ],
)
def test_seed_scene_refuses_rich_alias_normalized_or_forged_data(field, value):
    raw = SCENE.model_dump(mode="json")
    raw[field] = value
    with pytest.raises(SourceContextError) as caught:
        create_source_context_origin("synthetic-session", raw)
    assert "DO_NOT_ECHO" not in str(caught.value)


@pytest.mark.parametrize(
    "scene",
    [
        SceneState(location="Outra galeria", npcs_present=("Mara", "Ivo")),
        SceneState(location="Galeria", npcs_present=("Ivo", "Mara")),
        SceneState(location="Galeria", npcs_present=("mara", "Ivo")),
    ],
)
def test_seed_identity_has_exact_labels_and_order(scene):
    with pytest.raises(SourceContextError, match="source_context_scene_mismatch"):
        validate_source_scene(scene, _origin())


@pytest.mark.parametrize("field", ["session_id", "creator", "protocol", "fingerprint_sha256"])
def test_origin_copy_does_not_bypass_revalidation(field):
    origin = _origin()
    changed = origin.model_copy(update={field: "FORGED_PRIVATE"})
    with pytest.raises(SourceContextError) as caught:
        validate_source_context_origin(changed, session_id="synthetic-session")
    assert "FORGED_PRIVATE" not in str(caught.value)


def test_forged_nested_scene_extra_and_hash_are_not_normalized_away():
    origin = _origin()
    altered = SCENE.model_copy(update={"private_extra": "DO_NOT_ECHO"})
    forged = origin.model_copy(update={"seed_scene": altered})
    with pytest.raises(SourceContextError):
        validate_source_context_origin(forged, session_id="synthetic-session")
    raw = origin.model_dump(mode="json")
    raw["seed_scene"]["location"] = "Outro"
    with pytest.raises(SourceContextError):
        validate_source_context_origin(raw, session_id="synthetic-session")
    forged = SourceContextOrigin.model_construct(**raw)
    with pytest.raises(SourceContextError):
        validate_source_context_origin(forged, session_id="synthetic-session")


def test_missing_origin_and_cross_session_do_not_grant_eligibility():
    with pytest.raises(SourceContextError, match="source_context_origin_missing"):
        validate_source_context_origin(None, session_id="synthetic-session")
    with pytest.raises(SourceContextError, match="source_context_identity_mismatch"):
        validate_source_context_origin(_origin(), session_id="other-session")


def test_empty_snapshot_and_three_turn_selection_receipt_are_text_free():
    empty = SourceContextSnapshot(
        origin=_origin(), current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )
    assert empty.audit_payload()["selected_turn_ids"] == []
    snapshot = _snapshot()
    receipt = snapshot.audit_payload()
    assert receipt == {
        "protocol": SELECTION_PROTOCOL, "session_id": "synthetic-session",
        "current_turn": 3, "state_revision": 7,
        "origin_sha256": _origin().fingerprint_sha256,
        "selected_turn_ids": ["turn-2", "turn-3"],
        "omitted_turn_ids": ["turn-1"],
        "selection_policy": "required_recent_two",
    }
    assert snapshot.canonical_scene == SCENE
    serialized = json.dumps(receipt, ensure_ascii=False)
    for text in ("Galeria", "Mara", snapshot.sources[0].question, snapshot.sources[0].projection.text):
        assert text not in serialized
    assert validate_source_selection(
        receipt, origin=_origin(), current_turn=3, state_revision=7,
        history_turn_ids=("turn-1", "turn-2", "turn-3"),
    ) == receipt
    receipt["selected_turn_ids"].clear()
    assert snapshot.selected_turn_ids == ("turn-2", "turn-3")
    with pytest.raises(ValidationError):
        snapshot.current_turn = 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_turn", True), ("state_revision", "7"),
        ("current_turn", -1), ("state_revision", -1),
        ("sources", []), ("selected_turn_ids", {"turn-2", "turn-3"}),
        ("omitted_turn_ids", ("turn-2",)),
        ("selected_turn_ids", ("turn-3", "turn-2")),
        ("selected_turn_ids", (" turn-2", "turn-3")),
        ("private_extra", "DO_NOT_ECHO"),
    ],
)
def test_snapshot_requires_complete_typed_ordered_bound_sources(field, value):
    raw = _snapshot().model_dump(mode="json")
    raw[field] = value
    with pytest.raises((ValidationError, SourceContextError)):
        SourceContextSnapshot.model_validate(raw)


def test_snapshot_rejects_foreign_and_duplicated_sources():
    raw = _snapshot().model_dump(mode="json")
    raw["sources"][0] = _envelope(2, "foreign-session").model_dump(mode="json")
    with pytest.raises((ValidationError, SourceContextError)):
        SourceContextSnapshot.model_validate(raw)
    raw["sources"] = [_envelope(2), _envelope(2)]
    with pytest.raises((ValidationError, SourceContextError)):
        SourceContextSnapshot.model_validate(raw)


def test_snapshot_forgery_is_revalidated_when_audit_is_used():
    original = _snapshot()
    forged = original.model_copy(update={"state_revision": True})
    with pytest.raises((ValidationError, SourceContextError)):
        forged.audit_payload()
    forged = original.model_copy(update={"origin": _origin().model_copy(
        update={"fingerprint_sha256": "0" * 64},
    )})
    with pytest.raises((ValidationError, SourceContextError)):
        forged.audit_payload()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_turn", True), ("state_revision", 8),
        ("session_id", "foreign-session"), ("origin_sha256", "0" * 64),
        ("selected_turn_ids", ("turn-2", "turn-3")),
        ("selected_turn_ids", ["turn-3", "turn-2"]),
        ("omitted_turn_ids", []), ("private_extra", "DO_NOT_ECHO"),
        ("selection_policy", "pick_any"), ("protocol", "legacy"),
    ],
)
def test_selection_is_compared_to_trusted_history_and_revision(field, value):
    raw = _snapshot().audit_payload()
    raw[field] = value
    with pytest.raises(SourceContextError, match="source_context_selection_invalid"):
        validate_source_selection(
            raw, origin=_origin(), current_turn=3, state_revision=7,
            history_turn_ids=("turn-1", "turn-2", "turn-3"),
        )


@pytest.mark.parametrize("path", [(), ("context",), ("player_sheet",)])
@pytest.mark.parametrize("key", ["scene", "location", "npcs_present", "narrative_history", "packet", "facts", "consolidations", "narrative_source"])
def test_known_state_contexts_do_not_hide_legacy_dependencies(path, key):
    value = {"scene": SceneState(location="Wrong").model_dump(mode="json"),
             "location": "Wrong", "npcs_present": ["Other"]}.get(key, ["Legacy text"])
    state = {key: value}
    for parent in reversed(path):
        state = {parent: state}
    with pytest.raises(SourceContextError):
        validate_source_state_context(state, _origin())


def test_only_known_paths_are_checked_and_opaque_state_is_not_exported():
    opaque = {"attributes": {"summary": "Opaque mechanical extension"}}
    state = {
        "context": {"scene": SCENE.model_dump(mode="json"), "pending_roll": None},
        "player_sheet": {"location": "Galeria", "npcs_present": ["Mara", "Ivo"],
                         "player_sheet": opaque},
        "narrative_history": [], "counter": 9,
    }
    before = json.dumps(state, ensure_ascii=False, sort_keys=True)
    assert validate_source_state_context(state, _origin()) is None
    assert json.dumps(state, ensure_ascii=False, sort_keys=True) == before
    assert "Opaque" not in json.dumps(_snapshot().audit_payload())


@pytest.mark.parametrize("state", [None, [], {"context": None}, {"player_sheet": []}, {"narrative_history": False}])
def test_state_shape_is_not_coerced(state):
    with pytest.raises(SourceContextError):
        validate_source_state_context(state, _origin())


def test_error_domain_is_closed_without_echoing_values():
    assert str(SourceContextError("DO_NOT_ECHO")) == "source_context_invalid"
    assert str(SourceContextError({"secret": "DO_NOT_ECHO"})) == "source_context_invalid"
    for code in SourceContextCode:
        assert SourceContextError(code).code == code.value


def test_incomplete_constructed_origin_raises_closed_error():
    forged = SourceContextOrigin.model_construct()
    with pytest.raises(SourceContextError, match="source_context_origin_invalid"):
        validate_source_scene(SCENE, forged)
