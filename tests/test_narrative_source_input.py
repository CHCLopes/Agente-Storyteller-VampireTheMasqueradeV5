"""Pure producer data boundaries; fingerprints never authenticate a claim."""
import ast
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.narrative_source_capsule import create_source_turn_capsule, source_preparation_operation_id
from api.narrative_source_input import (
    PROTOCOL, REQUEST_KEY, COMPLETION_KEY, SourceInputClaim, SourceInputCompletion, SourceInputError,
    SourceInputFailure, SourceInputRequest, SourceProducerConfig,
    create_source_input_completion, create_source_input_request, create_source_producer_config,
    source_input_attempt_id, source_input_completion_metadata, source_input_operation_id,
    source_input_request_hash, source_input_request_metadata, source_input_result_hash,
)
from test_narrative_source_capsule import arguments
from test_narrative_source_preparation import resolved


def config(**updates):
    source = arguments()
    values = {key: source[key] for key in ("target", "system_prompt", "parameters", "player_aliases", "npc_aliases", "chronicle_name")}
    values.update(updates)
    return create_source_producer_config(**values)


def request(**updates):
    source = arguments()
    values = dict(created_at=source["created_at"], snapshot=source["snapshot"], state=source["state"],
                  relationships=source["relationships"], producer_config=config())
    values.update(updates)
    public = values.pop("public", {"operation_id": source["operation_id"], "player_input": source["player_input"]})
    return create_source_input_request(source["snapshot"].origin.session_id, public, **values)


def capsule_for(value, **updates):
    values = dict(snapshot=value.snapshot, operation_id=value.operation_id, created_at=value.created_at,
                  player_input=value.player_input, preparation=resolved(), state=value.state, relationships=value.relationships,
                  target=value.config.target, system_prompt=value.config.system_prompt, parameters=value.config.parameters,
                  player_aliases=value.config.player_aliases, npc_aliases=value.config.npc_aliases, chronicle_name=value.config.chronicle_name)
    values.update(updates)
    return create_source_turn_capsule(**values)


def complete(value=None):
    value = value or request()
    return create_source_input_completion(value, status="completed", capsule=capsule_for(value))


def failed(value=None, code="source_input_out_of_scope", status="failed"):
    return create_source_input_completion(value or request(), status=status, failure=SourceInputFailure(code=code))


def test_original_request_roundtrip_copies_all_server_data_and_protects_fingerprint():
    source = arguments()
    value = request(state=source["state"], relationships=source["relationships"])
    before = value.model_dump(mode="json")
    source["state"]["player_sheet"]["inventory"].append("caller mutation")
    source["relationships"]["links"].append("caller mutation")
    assert value.model_dump(mode="json") == before
    restored = SourceInputRequest.model_validate_json(value.model_dump_json())
    assert restored == value and restored is not value
    restored.state["player_sheet"]["inventory"].append("nested mutation")
    assert value.model_dump(mode="json") == before
    with pytest.raises(SourceInputError, match="source_input_request_invalid"):
        source_input_request_metadata(restored)
    assert set(before) == {"protocol", "session_id", "operation_id", "player_input", "created_at", "snapshot", "state", "relationships", "config", "fingerprint_sha256"}
    with pytest.raises(ValidationError):
        value.operation_id = "other"


def test_p_ids_are_literal_domain_separated_and_independent_of_time_base_or_content():
    value = request()
    operation = source_input_operation_id(value.session_id, value.operation_id)
    attempt = source_input_attempt_id(value.session_id, value.operation_id)
    assert operation == "source-input-operation-" + hashlib.sha256(json.dumps(
        [PROTOCOL, value.session_id, value.operation_id, "operation"], ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert len({operation, attempt, value.operation_id, source_preparation_operation_id(value.session_id, value.operation_id)}) == 4
    later = request(created_at=value.created_at + timedelta(seconds=1))
    changed = request(public={"operation_id": value.operation_id, "player_input": "Aguardo a reação."})
    newer = request(snapshot=value.snapshot.model_copy(update={"state_revision": 8}))
    reconfigured = request(producer_config=config(system_prompt="Another explicit SYSTEM."))
    changed_state = request(state={"counter": 1})
    changed_relationships = request(relationships={"links": ["new"]})
    for other in (later, changed, newer, reconfigured, changed_state, changed_relationships):
        assert source_input_operation_id(other.session_id, other.operation_id) == operation
        assert other.fingerprint_sha256 != value.fingerprint_sha256
        assert source_input_request_hash(other) != source_input_request_hash(value)
    assert source_input_operation_id("a/b", "c") != source_input_operation_id("a", "b/c")


@pytest.mark.parametrize("identity", ["", " padded", "x" * 241, True, None, "\ud800"])
def test_identity_helpers_are_strict_and_closed(identity):
    for helper in (source_input_attempt_id, source_input_operation_id):
        with pytest.raises(SourceInputError):
            helper("session", identity)


@pytest.mark.parametrize("updates", [
    {"profile": "remote"}, {"protected_secrets": ("PRIVATE_SENTINEL",)},
    {"protected_secrets": None}, {"player_aliases": {"Player"}},
    {"npc_aliases": (" padded",)}, {"system_prompt": " "}, {"system_prompt": "\ud800"},
    {"chronicle_name": True},
])
def test_config_refuses_hidden_dependencies_and_invalid_values(updates):
    with pytest.raises(SourceInputError) as caught:
        config(**updates)
    assert "PRIVATE_SENTINEL" not in str(caught.value)


@pytest.mark.parametrize("kind", ["target", "parameters", "extra"])
def test_config_does_not_coerce_or_drop_forged_model_fields(kind):
    value = config()
    if kind == "target":
        forged = value.target.model_copy(update={"model": " padded"})
        kwargs = {"target": forged}
    elif kind == "parameters":
        kwargs = {"parameters": value.parameters.model_copy(update={"max_output_tokens": True})}
    else:
        kwargs = {"target": value.target.model_copy(update={"api_key": "PRIVATE_SENTINEL"})}
    with pytest.raises(SourceInputError):
        config(**kwargs)
    for field in ("protected_secrets", "gateway", "deadline", "cancellation", "connection"):
        with pytest.raises(ValidationError):
            SourceProducerConfig.model_validate(value.model_copy(update={field: "PRIVATE_SENTINEL"}))


@pytest.mark.parametrize("updates", [
    {"created_at": 1}, {"created_at": arguments()["created_at"].replace(tzinfo=None)},
    {"state": []}, {"state": {"scene_summary": "legacy"}}, {"state": {"value": float("nan")}},
    {"relationships": {1: "not a string key"}}, {"relationships": {"object": object()}},
    {"relationships": {"value": (1, 2)}}, {"producer_config": {}},
    {"public": {"operation_id": "op", "player_input": "x" * 501}},
])
def test_request_rejects_nonliteral_base_configuration_and_client_fields(updates):
    with pytest.raises(SourceInputError) as caught:
        request(**updates)
    assert str(caught.value) == "source_input_request_invalid"


@pytest.mark.parametrize("kind", ["extra", "snapshot", "config", "fingerprint", "recursive", "unicode"])
def test_forged_requests_fail_before_metadata_or_hash_output(kind):
    value = request()
    if kind == "extra":
        value = value.model_copy(update={"gateway": "PRIVATE_SENTINEL"})
    elif kind == "snapshot":
        value = value.model_copy(update={"snapshot": value.snapshot.model_copy(update={"state_revision": True})})
    elif kind == "config":
        value = value.model_copy(update={"config": value.config.model_copy(update={"api_key": "PRIVATE_SENTINEL"})})
    elif kind == "fingerprint":
        value = value.model_copy(update={"fingerprint_sha256": "0" * 64})
    elif kind == "unicode":
        value.state["bad"] = "\ud800"
    else:
        value.state["cycle"] = value.state
    for helper in (source_input_request_metadata, source_input_request_hash):
        with pytest.raises(SourceInputError) as caught:
            helper(value)
        assert str(caught.value) == "source_input_request_invalid"


def test_completed_binds_full_capsule_and_keeps_only_k_identity():
    value = request()
    retained = capsule_for(value)
    completion = create_source_input_completion(value, status="completed", capsule=retained)
    assert completion.capsule_operation_id == source_preparation_operation_id(value.session_id, value.operation_id)
    assert completion.capsule_sha256 == retained.fingerprint_sha256
    assert completion.request_sha256 == source_input_request_hash(value)
    assert completion.request_sha256 != value.fingerprint_sha256
    assert completion.failure is None
    assert SourceInputCompletion.model_validate_json(completion.model_dump_json()) == completion
    assert "preparation" not in completion.model_dump()


@pytest.mark.parametrize("kind", ["time", "state", "relationships", "prompt", "operation", "fingerprint"])
def test_completed_refuses_rebound_capsule_and_unapproved_state_effects(kind):
    value = request()
    updates = {"time": {"created_at": value.created_at + timedelta(seconds=1)}, "state": {"state": {"effect": 1}},
               "relationships": {"relationships": {"effect": 1}}, "prompt": {"system_prompt": "Changed SYSTEM."},
               "operation": {"operation_id": "different"}}
    retained = capsule_for(value, **updates.get(kind, {}))
    if kind == "fingerprint":
        retained = retained.model_copy(update={"fingerprint_sha256": "0" * 64})
    with pytest.raises(SourceInputError, match="source_input_completion_invalid"):
        create_source_input_completion(value, status="completed", capsule=retained)


@pytest.mark.parametrize(("code", "status"), [
    ("source_input_out_of_scope", "failed"), ("source_input_clarification_required", "failed"),
    ("source_input_base_mismatch", "failed"), ("source_input_production_failed", "failed"),
    ("source_input_cancelled", "cancelled"), ("process_interrupted", "cancelled"),
    ("source_input_deadline_exceeded", "timeout"),
])
def test_terminal_failures_have_safe_codes_and_never_a_capsule(code, status):
    result = failed(code=code, status=status)
    assert result.status == status and result.failure.code == code
    assert result.capsule_operation_id is None and result.capsule_sha256 is None


def test_terminal_combinations_and_failure_fields_cannot_be_forged():
    value = request()
    for kwargs in ({"status": "completed"}, {"status": "failed"},
            {"status": "timeout", "failure": SourceInputFailure(code="source_input_out_of_scope")},
            {"status": "failed", "capsule": capsule_for(value)},
            {"status": "completed", "capsule": capsule_for(value), "failure": SourceInputFailure(code="source_input_cancelled")}):
        with pytest.raises(SourceInputError):
            create_source_input_completion(value, **kwargs)
    for kwargs in ({"code": "PRIVATE_SENTINEL"}, {"code": "source_input_out_of_scope", "stage": "PRIVATE_SENTINEL"},
            {"code": "source_input_out_of_scope", "safe_message": "PRIVATE_SENTINEL"}):
        with pytest.raises(ValidationError):
            SourceInputFailure(**kwargs)


def test_claim_is_copied_observation_and_does_not_authenticate_newness():
    value = request()
    claim = SourceInputClaim(request=value, status="pending", newly_claimed=True)
    assert claim.request == value and claim.request is not value
    # In-memory reconstruction is possible: service must never accept this as authority.
    assert SourceInputClaim.model_validate_json(claim.model_dump_json()) == claim
    replay = SourceInputClaim(request=value, status="pending", newly_claimed=False)
    assert not replay.newly_claimed and replay.completion is None
    done = SourceInputClaim(request=value, status="completed", newly_claimed=False, completion=complete(value))
    assert done.completion.status == "completed"
    for kwargs in ({"status": "pending", "newly_claimed": 1},
            {"status": "completed", "newly_claimed": True, "completion": complete(value)},
            {"status": "completed", "newly_claimed": False},
            {"status": "pending", "newly_claimed": False, "completion": failed(value)},
            {"status": "failed", "newly_claimed": False, "completion": failed(request(created_at=value.created_at + timedelta(seconds=1)))}):
        with pytest.raises(ValidationError):
            SourceInputClaim(request=value, **kwargs)


@pytest.mark.anyio
@pytest.mark.parametrize(("status", "code"), [
    ("completed", None), ("failed", "source_input_out_of_scope"),
    ("cancelled", "source_input_cancelled"), ("timeout", "source_input_deadline_exceeded"),
])
async def test_hashes_match_existing_sqlite_controls_with_no_new_producer(status, code, tmp_path):
    from api.persistence import SQLitePersistence
    store = SQLitePersistence(tmp_path / "hash-format.sqlite3")
    source = arguments()
    await store.initialize()
    await store.create_narrative_source_campaign(source["snapshot"].origin.session_id,
        initial_scene=source["snapshot"].canonical_scene, initial_state=source["state"], relationships=source["relationships"])
    value = request(snapshot=await store.read_source_context_snapshot(source["snapshot"].origin.session_id))
    result = complete(value) if status == "completed" else failed(value, code=code, status=status)
    initial = source_input_request_metadata(value)
    terminal = source_input_completion_metadata(value, result)
    assert terminal[REQUEST_KEY] == initial[REQUEST_KEY] and COMPLETION_KEY not in initial
    ids = dict(session_id=value.session_id, operation_id=source_input_operation_id(value.session_id, value.operation_id),
               attempt_id=source_input_attempt_id(value.session_id, value.operation_id),
               requested_turn=value.snapshot.current_turn + 1, user_input=value.player_input)
    await store.start_attempt(**ids, metadata=initial)
    pending = await store.load_attempt_by_operation(ids["session_id"], ids["operation_id"])
    assert pending["request_hash"] == source_input_request_hash(value)
    assert pending["payload_hash"] == pending["request_hash"]
    assert pending["result_hash"] is None
    if status == "completed":
        await store.complete_control_attempt(**ids, metadata=terminal)
    else:
        await store.record_failed_attempt(**ids, status=status, error=result.failure.model_dump(mode="json"), metadata=terminal)
    observed = await store.load_attempt_by_operation(ids["session_id"], ids["operation_id"])
    assert observed["request_hash"] == pending["request_hash"]
    assert observed["metadata"] == terminal
    assert observed["result_hash"] == source_input_result_hash(value, result)
    assert observed["result_hash"] != observed["request_hash"]
    # These existing controls test payload compatibility, not atomic P/K finalization.
    assert await store.load_source_preparation(value.session_id, value.operation_id) is None

def test_metadata_outputs_are_detached_and_revalidate_result_binding():
    value = request()
    result = complete(value)
    metadata = source_input_completion_metadata(value, result)
    metadata[REQUEST_KEY]["state"]["changed"] = True
    assert "changed" not in value.state
    forged = result.model_copy(update={"capsule_operation_id": "other"})
    with pytest.raises(SourceInputError):
        source_input_result_hash(value, forged)
    forged = result.model_copy(update={"request_sha256": "0" * 64})
    with pytest.raises(SourceInputError):
        source_input_completion_metadata(value, forged)


def test_pure_contracts_never_import_persistence_pipeline_or_execute_rules(monkeypatch):
    from api import narrative_source_input, rules_service
    from api.persistence import SQLitePersistence
    def forbidden(*args, **kwargs):
        pytest.fail("Pure contract executed storage or rules")
    monkeypatch.setattr(rules_service, "calculate_resolution", forbidden)
    monkeypatch.setattr(rules_service.random, "randint", forbidden)
    monkeypatch.setattr(SQLitePersistence, "start_attempt", forbidden)
    monkeypatch.setattr(SQLitePersistence, "initialize", forbidden)
    value = request()
    assert complete(value).status == "completed"
    assert SourceInputClaim(request=value, status="pending", newly_claimed=True).newly_claimed
    tree = ast.parse(Path(narrative_source_input.__file__).read_text(encoding="utf-8-sig"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name and any(part in name for part in ("persistence", "orchestrator", "config", "main", "service", "gateway")) for name in imports)
    assert str(SourceInputError("PRIVATE_SENTINEL")) == "source_input_invalid"
