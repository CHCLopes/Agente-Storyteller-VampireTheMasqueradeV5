"""Capsule boundaries only; preparation/rules integration has its own suite."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json

import pytest
from pydantic import ValidationError

from api.llm.contract import GenerationParameters, LLMTarget
from api.narrative_source_capsule import (
    CAPSULE_KEY, PROTOCOL, SourceCapsuleCode, SourceCapsuleError, SourceTurnCapsule,
    create_source_turn_capsule, source_preparation_attempt_id,
    source_preparation_operation_id, validate_source_turn_capsule,
)
from api.narrative_source_preparation import DeclaredActionPreparation
from test_narrative_source_preparation import INPUT, NOW, resolved, snapshot


def arguments():
    return dict(
        snapshot=snapshot(), operation_id="operation-1", created_at=NOW,
        player_input=INPUT, preparation=resolved(),
        state={"player_sheet": {"attributes": {"Wits": 3}, "inventory": ["cafe\u0301"]}},
        relationships={"links": [], "revision": 0},
        target=LLMTarget(profile="synthetic-local", provider="fake", model="authored"),
        system_prompt="  SYSTEM literal.\n", parameters=GenerationParameters(
            temperature=0.65, max_output_tokens=768, seed=None),
        player_aliases=("Você",), npc_aliases=(), chronicle_name="Crônica sintética",
    )


def capsule(**updates):
    values = arguments()
    values.update(updates)
    return create_source_turn_capsule(**values)


def validate(value, **updates):
    kwargs = dict(session_id="synthetic-session", operation_id="operation-1")
    kwargs.update(updates)
    return validate_source_turn_capsule(value, **kwargs)


def fingerprint(payload):
    return hashlib.sha256(json.dumps(
        {key: value for key, value in payload.items() if key != "fingerprint_sha256"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def rejected(value, **updates):
    with pytest.raises(SourceCapsuleError) as caught:
        validate(value, **updates)
    assert caught.value.code in {code.value for code in SourceCapsuleCode}
    assert str(caught.value) == caught.value.code
    assert "PRIVATE_SENTINEL" not in str(caught.value)
    return caught.value.code


def test_resolved_capsule_json_roundtrip_preserves_whole_receipt_and_configuration():
    value = capsule()
    payload = value.model_dump(mode="json")
    assert validate(json.loads(value.model_dump_json())) == value
    assert value.session_id == "synthetic-session"
    assert value.canonical_scene == value.snapshot.canonical_scene
    assert value.fingerprint_sha256 == fingerprint(payload)
    assert value.system_prompt == "  SYSTEM literal.\n"
    assert value.draft.base_state_revision == 7
    assert value.preparation.resolution.model_dump(mode="json") == arguments()["preparation"].resolution.model_dump(mode="json")
    assert all(value.draft.facts[0].value[key] == item
               for key, item in value.preparation.resolution.model_dump(mode="json").items())
    assert CAPSULE_KEY == "narrative_source_capsule"
    assert payload["protocol"] == PROTOCOL
    assert set(payload) == {
        "protocol", "snapshot", "operation_id", "created_at", "player_input",
        "preparation", "draft", "state", "relationships", "target", "system_prompt",
        "parameters", "player_aliases", "npc_aliases", "chronicle_name", "fingerprint_sha256",
    }


def test_declared_capsule_reconstitutes_without_calling_engine_or_rng(monkeypatch):
    import api.rules_service as rules
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No RNG or rules execution belongs to capsule construction")
    monkeypatch.setattr(rules, "calculate_resolution", forbidden)
    monkeypatch.setattr(rules.random, "randint", forbidden)
    value = capsule(preparation=DeclaredActionPreparation())
    assert value.draft.facts[0].fact_type == "action.declaration"
    assert validate(value.model_dump(mode="json")) == value


def test_capsule_owns_copies_and_nested_mutation_is_rejected_at_boundary():
    inputs = arguments()
    value = create_source_turn_capsule(**inputs)
    before = deepcopy(value.model_dump(mode="json"))
    inputs["state"]["player_sheet"]["inventory"].append("new")
    inputs["relationships"]["links"].append("new")
    inputs["preparation"].resolution.normal_rolls.append(8)
    assert value.model_dump(mode="json") == before
    with pytest.raises(ValidationError):
        value.operation_id = "other"
    restored = validate(value)
    restored.state["player_sheet"]["inventory"].append("changed")
    assert value.model_dump(mode="json") == before
    rejected(restored)
    value.preparation.resolution.normal_rolls.append(7)
    rejected(value)


def test_ids_are_domain_separated_session_bound_literal_and_deterministic():
    value = capsule()
    op = source_preparation_operation_id(value.session_id, value.operation_id)
    attempt = source_preparation_attempt_id(value.session_id, value.operation_id)
    assert op == source_preparation_operation_id(value.session_id, value.operation_id)
    assert len({op, attempt, value.operation_id, value.draft.attempt_id, value.draft.turn_id}) == 5
    assert source_preparation_operation_id("a/b", "c") != source_preparation_operation_id("a", "b/c")
    assert source_preparation_attempt_id("other", value.operation_id) != attempt
    assert source_preparation_operation_id(value.session_id, "other") != op


@pytest.mark.parametrize("identity", [True, " padded", "", "\ud800"])
def test_control_ids_do_not_coerce_or_normalize_identity(identity):
    for helper in (source_preparation_attempt_id, source_preparation_operation_id):
        with pytest.raises(SourceCapsuleError):
            helper("synthetic-session", identity)


@pytest.mark.parametrize("secret", [("PRIVATE_SENTINEL",), ["PRIVATE_SENTINEL"], "", None, False, set()])
def test_protected_secret_argument_is_explicitly_rejected(secret):
    with pytest.raises(SourceCapsuleError) as caught:
        capsule(protected_secrets=secret)
    assert str(caught.value) == "source_capsule_secrets_forbidden"
    assert "protected_secrets" not in capsule().model_dump(mode="json")


@pytest.mark.parametrize("field", ["gateway", "api_key", "deadline", "cancellation", "on_chunk", "protected_secrets", "context"])
def test_runtime_secret_and_passthrough_fields_cannot_be_persisted(field):
    raw = capsule().model_dump(mode="json")
    raw[field] = "PRIVATE_SENTINEL"
    raw["fingerprint_sha256"] = fingerprint(raw)
    rejected(raw)


@pytest.mark.parametrize("bad", [
    {1: "coerced-key"}, {"handle": object()}, {"nested": (1, 2)},
    {"not_finite": float("nan")}, {"not_finite": float("inf")},
    {"nested": DeclaredActionPreparation()},
])
def test_state_json_does_not_coerce_non_json_values_or_models(bad):
    with pytest.raises(SourceCapsuleError):
        capsule(state=bad)


def test_known_legacy_state_context_and_non_mapping_relationships_are_rejected():
    with pytest.raises(SourceCapsuleError):
        capsule(state={"scene_summary": "PRIVATE_SENTINEL"})
    with pytest.raises(SourceCapsuleError):
        capsule(relationships=[])


@pytest.mark.parametrize("field,bad", [
    ("max_output_tokens", True), ("seed", "2"), ("temperature", "0.65"),
])
def test_forged_generation_parameter_coercions_are_rejected(field, bad):
    invalid = arguments()["parameters"].model_copy(update={field: bad})
    with pytest.raises(SourceCapsuleError):
        capsule(parameters=invalid)


def test_target_normalization_and_nested_extra_are_rejected():
    for update in ({"model": " padded"}, {"secret": "PRIVATE_SENTINEL"}):
        invalid = arguments()["target"].model_copy(update=update)
        with pytest.raises(SourceCapsuleError):
            capsule(target=invalid)


def test_recomputed_fingerprint_cannot_authorize_a_different_draft():
    raw = capsule().model_dump(mode="json")
    raw["draft"]["facts"][0]["value"]["is_success"] = False
    raw["fingerprint_sha256"] = fingerprint(raw)
    rejected(raw)
    raw = capsule().model_dump(mode="json")
    raw["draft"]["base_revision"] = False  # Python equality would confuse False and 0.
    raw["fingerprint_sha256"] = fingerprint(raw)
    rejected(raw)


def test_plain_and_forged_extra_fields_are_never_laundered():
    value = capsule()
    rejected(value.model_copy(update={"arbitrary": "PRIVATE_SENTINEL"}))
    raw = value.model_dump(mode="json")
    raw["draft"]["events"][0]["summary"] = "PRIVATE_SENTINEL"
    raw["fingerprint_sha256"] = fingerprint(raw)
    rejected(raw)
    rejected(SourceTurnCapsule.model_construct())


def test_fingerprint_covers_both_static_configuration_and_retained_state():
    for field, replacement in (
        ("system_prompt", "Changed"), ("state", {}), ("relationships", {}),
        ("chronicle_name", "Other"), ("player_aliases", []),
    ):
        raw = capsule().model_dump(mode="json")
        raw[field] = replacement
        rejected(raw)
    raw = capsule().model_dump(mode="json")
    raw["fingerprint_sha256"] = "0" * 64
    rejected(raw)


def test_expected_identity_is_checked_without_rebinding_or_authentication_claim():
    value = capsule()
    assert rejected(value, session_id="other") == "source_capsule_identity_invalid"
    assert rejected(value, operation_id="other") == "source_capsule_identity_invalid"
    # An explicit new preparation may legitimately have a different prompt.
    # A matching hash is identity, not a claim about who supplied that prompt.
    changed = capsule(system_prompt="Different explicitly supplied SYSTEM")
    assert changed.fingerprint_sha256 != value.fingerprint_sha256
    assert validate(changed) == changed


def test_timestamp_and_alias_inputs_do_not_use_epoch_or_unordered_coercion():
    for update in ({"created_at": NOW.isoformat()}, {"created_at": 0},
                   {"player_aliases": {"Você"}}, {"npc_aliases": [True]}):
        with pytest.raises(SourceCapsuleError):
            capsule(**update)
    raw = capsule().model_dump(mode="json")
    raw["created_at"] = 0
    rejected(raw)


def test_errors_have_closed_codes_and_do_not_echo_values():
    for code in ("PRIVATE_SENTINEL", {"secret": "PRIVATE_SENTINEL"}, None):
        assert str(SourceCapsuleError(code)) == "source_capsule_invalid"
    for code in ("source_capsule_stored_pair_invalid", "source_capsule_history_mismatch",
                 "source_capsule_base_mismatch", "source_capsule_operation_already_started"):
        assert SourceCapsuleError(code).code == code
