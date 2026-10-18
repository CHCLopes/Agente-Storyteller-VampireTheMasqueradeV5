"""Pure setup boundaries: synthetic literals, no campaign or narrative production."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_entry import MAX_PLAYER_INPUT_CHARS, validate_source_entry_snapshot
from api.narrative_source_setup import (
    MANIFEST_KEY, MANIFEST_PROTOCOL, MAX_LOCATION_CHARS, MAX_NPC_NAME_CHARS,
    MAX_NPCS, MAX_OBJECTIVE_CHARS, REQUEST_PROTOCOL, SourceSetupError,
    SourceSetupManifest, SourceSetupRequest, create_source_setup_manifest,
    validate_source_setup_manifest, validate_source_setup_request,
)
from api.scene_service import SceneState

SESSION = "setup-synthetic-session"
OBJECTIVE = "Conhecer  a galeria.\r\nConversar sobre o cafe\u0301."


def request(**updates):
    payload = {"location": "Galeria", "npcs_present": ["Mara", "Ivo"],
               "declared_objective": OBJECTIVE}
    payload.update(updates)
    return validate_source_setup_request(payload)


def manifest(**updates):
    return create_source_setup_manifest(request(**updates), session_id=SESSION)


def _rehash(payload):
    raw = deepcopy(payload)
    raw.pop("fingerprint_sha256", None)
    return hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def test_public_shape_is_versioned_strict_frozen_and_literal():
    raw = {"location": "Galeria  do cafe\u0301", "npcs_present": ["Érica", "Ivo"],
           "declared_objective": OBJECTIVE}
    value = validate_source_setup_request(raw)
    assert value.model_dump(mode="json") == {"protocol": REQUEST_PROTOCOL, **raw}
    assert SourceSetupRequest.model_validate_json(value.model_dump_json()) == value
    copied = validate_source_setup_request(value)
    assert copied == value and copied is not value
    raw["npcs_present"].append("Outro")
    assert copied.npcs_present == ("Érica", "Ivo")
    with pytest.raises(ValidationError):
        value.declared_objective = "changed"
    schema = SourceSetupRequest.model_json_schema()
    assert set(schema["properties"]) == {"protocol", "location", "npcs_present", "declared_objective"}
    assert schema["additionalProperties"] is False


def test_boundaries_match_seed_and_entry_without_truncation():
    assert MAX_LOCATION_CHARS == 160 and MAX_NPC_NAME_CHARS == 80 and MAX_NPCS == 8
    assert MAX_OBJECTIVE_CHARS == MAX_PLAYER_INPUT_CHARS == 500
    value = request(location="á" * 160, npcs_present=[str(i) + "á" * 79 for i in range(8)],
                    declared_objective="á" * 500)
    result = create_source_setup_manifest(value, session_id="s" * 240)
    assert result.request == value
    assert result.origin.seed_scene.location == value.location
    assert result.origin.seed_scene.npcs_present == value.npcs_present


@pytest.mark.parametrize("field,value", [
    ("location", "a" * 161), ("npcs_present", ["n" * 81]),
    ("npcs_present", [str(i) for i in range(9)]), ("declared_objective", "a" * 501),
    ("location", " Galeria"), ("location", "Galeria "),
    ("npcs_present", [" Mara"]), ("npcs_present", ["Mara "]),
    ("npcs_present", ["Ana  Maria"]), ("npcs_present", ["Ana\nMaria"]),
    ("npcs_present", ["Mara", "mara"]), ("npcs_present", ["Mara", "Mara"]),
    ("declared_objective", " padded"), ("declared_objective", "padded "),
    ("protocol", "legacy-v1"), ("protocol", True),
])
def test_incompatible_literals_are_refused_not_normalized(field, value):
    with pytest.raises(SourceSetupError, match="^source_setup_request_invalid$"):
        request(**{field: value})


@pytest.mark.parametrize("value", [None, True, 1, 1.2, b"text", [], {}, "", " \t\n", "\ud800"])
@pytest.mark.parametrize("field", ["location", "declared_objective"])
def test_text_types_and_utf8_are_strict(field, value):
    with pytest.raises(SourceSetupError, match="^source_setup_request_invalid$"):
        request(**{field: value})


@pytest.mark.parametrize("value", [None, True, "Mara", {"Mara"}, {"name": "Mara"},
                                  [True], [None], [1], [""], ["\ud800"]])
def test_cast_requires_ordered_literal_names(value):
    with pytest.raises(SourceSetupError, match="^source_setup_request_invalid$"):
        request(npcs_present=value)


@pytest.mark.parametrize("field", [
    "session_id", "origin", "scene", "summary", "details", "open_threads", "last_turn",
    "state", "player_sheet", "relationships", "config", "target", "system_prompt",
    "provider", "parameters", "effects", "source", "projection", "invocation_id",
    "receipt", "normal_rolls", "hunger_rolls", "resolution", "operation_id", "player_input",
])
def test_privileged_or_historical_public_fields_are_rejected_even_empty(field):
    for extra in ({}, None, "PRIVATE_SENTINEL"):
        with pytest.raises(SourceSetupError) as caught:
            request(**{field: extra})
        assert str(caught.value) == "source_setup_request_invalid"


def test_manifest_binds_complete_request_origin_and_authored_presentation():
    value = manifest()
    assert value.protocol == MANIFEST_PROTOCOL
    assert value.kind == "authored_trial_setup"
    assert MANIFEST_KEY == "narrative_source_setup_manifest"
    assert value.origin.creator == "explicit_server_seed"
    assert value.origin.session_id == SESSION
    assert value.origin.seed_scene.model_dump(mode="json") == {
        "location": "Galeria", "npcs_present": ["Mara", "Ivo"],
        "summary": "", "details": [], "open_threads": [], "last_turn": 0,
    }
    assert value.fingerprint_sha256 == _rehash(value.model_dump(mode="json"))
    assert value.briefing.startswith("Preparação autorada deste ensaio.\nLocal: Galeria\n")
    assert "Elenco presente: Mara; Ivo\n" in value.briefing
    assert "Objetivo declarado pelo jogador (intenção, não fato estabelecido):\n" + OBJECTIVE in value.briefing
    assert value == manifest()
    assert SourceSetupManifest.model_validate_json(value.model_dump_json()) == value
    assert set(value.model_dump()) == {"protocol", "kind", "request", "origin", "briefing", "fingerprint_sha256"}


def test_empty_cast_does_not_create_a_character():
    value = manifest(npcs_present=[])
    assert value.origin.seed_scene.npcs_present == ()
    assert "Elenco presente: nenhum NPC indicado\n" in value.briefing


def test_objective_remains_intention_not_canonical_fact_source_or_chosen_action():
    objective = "Já achei a chave, venci o guarda e descobri todo o segredo."
    value = manifest(declared_objective=objective)
    assert value.request.declared_objective == objective
    assert objective in value.briefing
    assert objective not in value.origin.model_dump_json()
    snapshot = SourceContextSnapshot(origin=value.origin, current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=())
    checked = validate_source_entry_snapshot(snapshot, session_id=SESSION)
    assert checked.sources == () and checked.current_turn == checked.state_revision == 0
    assert checked.canonical_scene.summary == ""
    assert not {"player_input", "operation_id", "turn_id", "source_id", "invocation_id", "state", "config"} & set(value.model_dump())


def test_manifest_roundtrip_and_revalidation_detach_all_nested_models():
    original = manifest()
    raw = original.model_dump(mode="json")
    checked = validate_source_setup_manifest(original, session_id=SESSION)
    assert checked == original and checked is not original
    assert checked.request is not original.request
    assert checked.origin is not original.origin
    assert checked.origin.seed_scene is not original.origin.seed_scene
    from_raw = validate_source_setup_manifest(raw, session_id=SESSION)
    raw["request"]["npcs_present"].append("Other")
    raw["origin"]["seed_scene"]["location"] = "Other"
    assert from_raw == original
    with pytest.raises(ValidationError):
        checked.briefing = "changed"


@pytest.mark.parametrize("field,value", [
    ("protocol", "legacy"), ("kind", "model_output"),
    ("briefing", "PRIVATE_SENTINEL"), ("briefing", "\ud800"),
    ("briefing", True), ("fingerprint_sha256", "0" * 64),
    ("source", {}), ("turn_id", "turn-1"), ("state", {}), ("config", {}),
])
def test_manifest_tampering_or_privileged_extras_are_closed(field, value):
    raw = manifest().model_dump(mode="json")
    raw[field] = value
    with pytest.raises(SourceSetupError) as caught:
        validate_source_setup_manifest(raw, session_id=SESSION)
    assert str(caught.value) == "source_setup_manifest_invalid"


@pytest.mark.parametrize("field,value", [
    ("summary", "old story"), ("details", ["invented clue"]),
    ("open_threads", ["old objective"]), ("last_turn", 1), ("last_turn", True),
    ("location", "Other"), ("npcs_present", ["Ivo", "Mara"]), ("hidden", "PRIVATE_SENTINEL"),
])
def test_false_enriched_or_legacy_origin_is_rejected(field, value):
    raw = manifest().model_dump(mode="json")
    raw["origin"]["seed_scene"][field] = value
    raw["fingerprint_sha256"] = _rehash(raw)
    with pytest.raises(SourceSetupError, match="^source_setup_manifest_invalid$"):
        validate_source_setup_manifest(raw, session_id=SESSION)


def test_recomputed_hash_does_not_erase_request_scene_or_briefing_binding():
    raw = manifest().model_dump(mode="json")
    raw["origin"] = create_source_context_origin(SESSION, SceneState(location="Elsewhere")).model_dump(mode="json")
    raw["fingerprint_sha256"] = _rehash(raw)
    with pytest.raises(SourceSetupError):
        validate_source_setup_manifest(raw, session_id=SESSION)
    raw = manifest().model_dump(mode="json")
    raw["request"]["declared_objective"] = "changed objective"
    raw["fingerprint_sha256"] = _rehash(raw)
    with pytest.raises(SourceSetupError):
        validate_source_setup_manifest(raw, session_id=SESSION)


@pytest.mark.parametrize("session", ["other-session", None, True, "", " padded", "x" * 241, "\ud800"])
def test_manifest_checks_expected_server_session_separately(session):
    with pytest.raises(SourceSetupError, match="^source_setup_manifest_invalid$"):
        validate_source_setup_manifest(manifest(), session_id=session)


@pytest.mark.parametrize("session", [None, True, "", " padded", "x" * 241, "\ud800"])
def test_factory_rejects_invalid_server_identity_safely(session):
    with pytest.raises(SourceSetupError, match="^source_setup_manifest_invalid$"):
        create_source_setup_manifest(request(), session_id=session)


def test_server_session_is_required_and_hashes_are_not_authentication():
    with pytest.raises(TypeError):
        create_source_setup_manifest(request())
    with pytest.raises(TypeError):
        validate_source_setup_manifest(manifest())
    other = create_source_setup_manifest(request(), session_id="other-session")
    assert other.fingerprint_sha256 != manifest().fingerprint_sha256
    assert validate_source_setup_manifest(other, session_id="other-session") == other
    # A self-consistent object cannot prove server/DB authorship in a pure model.


@pytest.mark.parametrize("kind", ["request-extra", "nested-extra", "origin-extra", "origin-missing",
                                   "request-missing", "outer-extra", "construct", "wrong-text"])
def test_forged_models_are_revalidated_instead_of_trusted(kind):
    value = manifest()
    if kind == "request-extra":
        value = request().model_copy(update={"state": {"private": "PRIVATE_SENTINEL"}})
        validator = validate_source_setup_request
    else:
        validator = lambda value: validate_source_setup_manifest(value, session_id=SESSION)
        if kind == "nested-extra":
            value = value.model_copy(update={"request": value.request.model_copy(update={"state": {}})})
        elif kind == "origin-extra":
            value = value.model_copy(update={"origin": value.origin.model_copy(update={"source": {}})})
        elif kind == "origin-missing":
            value = value.model_copy(update={"origin": {"session_id": SESSION}})
        elif kind == "request-missing":
            value = value.model_copy(update={"request": SourceSetupRequest.model_construct(location="Galeria")})
        elif kind == "outer-extra":
            value = value.model_copy(update={"state": {}})
        elif kind == "construct":
            value = SourceSetupManifest.model_construct(protocol=MANIFEST_PROTOCOL)
        else:
            value = value.model_copy(update={"request": value.request.model_copy(update={"declared_objective": True})})
    with pytest.raises(SourceSetupError) as caught:
        validator(value)
    assert "PRIVATE_SENTINEL" not in str(caught.value)


def test_closed_helpers_handle_wrong_objects_subclasses_and_cycles():
    class SubRequest(SourceSetupRequest):
        pass
    class SubManifest(SourceSetupManifest):
        pass
    for value in (None, [], "PRIVATE_SENTINEL", SceneState(location="Galeria"),
                  SubRequest.model_validate(request().model_dump())):
        with pytest.raises(SourceSetupError):
            validate_source_setup_request(value)
    for value in (None, [], "PRIVATE_SENTINEL", request(),
                  SubManifest.model_validate(manifest().model_dump())):
        with pytest.raises(SourceSetupError):
            validate_source_setup_manifest(value, session_id=SESSION)
    cycle = {}
    cycle["cycle"] = cycle
    with pytest.raises(SourceSetupError):
        validate_source_setup_request(cycle)
    with pytest.raises(SourceSetupError):
        validate_source_setup_manifest(cycle, session_id=SESSION)


def test_raw_errors_and_error_class_never_echo_private_input():
    with pytest.raises(ValidationError) as caught:
        SourceSetupRequest(location="Galeria", npcs_present=[], declared_objective={"PRIVATE_SENTINEL": True})
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert str(SourceSetupError("PRIVATE_SENTINEL")) == "source_setup_request_invalid"
    assert str(SourceSetupError({})) == "source_setup_request_invalid"


def test_pure_factories_do_not_open_read_write_roll_or_create_narrative(monkeypatch):
    import builtins
    import random
    import sqlite3
    import api.narrative_grounding as grounding
    import api.rules_service as rules
    import api.scene_service as scene

    def forbidden(*args, **kwargs):
        raise AssertionError("setup must remain pure")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(random, "randint", forbidden)
    monkeypatch.setattr(rules, "calculate_resolution", forbidden)
    monkeypatch.setattr(grounding, "create_narrative_source", forbidden)
    monkeypatch.setattr(scene, "load_scene_seed", forbidden)
    value = manifest()
    assert validate_source_setup_manifest(value, session_id=SESSION) == value
