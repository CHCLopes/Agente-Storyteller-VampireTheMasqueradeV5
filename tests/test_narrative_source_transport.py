"""Public projection boundaries only; no route activation or live provider calls."""
import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.narrative_source_input import SourceInputClaim, SourceInputFailure
from api.narrative_source_setup import SourceSetupRequest, create_source_setup_manifest
from api.narrative_source_status import SourceOperationFailure, SourceOperationSnapshot, safe_source_failure
from api.narrative_source_transport import (
    PROTOCOL, SourceBriefingEvent, SourcePreparationEvent, SourcePreparationRejectedEvent,
    SourceNarrativePendingEvent, SourceNarrativeCompleteEvent, SourceNarrativeRejectedEvent,
    SourceUnavailableEvent, SourceTransportError, project_source_briefing,
    project_source_preparation, project_source_operation, project_source_unavailable,
    validate_source_public_event,
)
from test_narrative_source_input import config, request, complete, failed
from test_narrative_source_turn import fixture, TEXT, QUESTION


def setup():
    return create_source_setup_manifest(SourceSetupRequest(location="Galeria",
        npcs_present=("Mara",), declared_objective="Conhecer melhor este lugar."), session_id="session-1")


def claim(status="pending", *, code="source_input_out_of_scope", stage=None, newly=False):
    private = request(producer_config=config(system_prompt="PRIVATE_SYSTEM_SENTINEL",
        chronicle_name="PRIVATE_CHRONICLE_SENTINEL"),
        state={"inventory": ["PRIVATE_STATE_SENTINEL"]},
        relationships={"private": "PRIVATE_RELATION_SENTINEL"})
    completion = None
    if status == "completed":
        completion = complete(private)
    elif status != "pending":
        completion = failed(private, code=code, status=status)
        completion = completion.model_copy(update={"failure": SourceInputFailure(code=code, stage=stage)})
    return SourceInputClaim(request=private, status=status, newly_claimed=newly, completion=completion)


def observe(status="pending", *, failure=None, **updates):
    values = dict(session_id="session-1", operation_id="operation-1", capsule_sha256="a" * 64,
        base_turn=0, base_state_revision=7, current_turn=3, current_state_revision=11,
        status=status, committed_turn_id="turn-1" if status == "completed" else None, failure=failure)
    values.update(updates)
    return SourceOperationSnapshot(**values)


def project_claim(value):
    return project_source_preparation(value, session_id="synthetic-session", operation_id="operation-1")


def project_status(value, envelope=None):
    return project_source_operation(value, session_id="session-1", operation_id="operation-1",
                                    confirmed_envelope=envelope)


def closed(function, *args, **kwargs):
    with pytest.raises(SourceTransportError) as caught:
        function(*args, **kwargs)
    assert str(caught.value) == "source_transport_projection_invalid"
    assert "PRIVATE" not in str(caught.value)


def samples():
    envelope, _ = fixture()
    return (
        project_source_briefing(setup(), session_id="session-1"),
        project_claim(claim()), project_claim(claim("completed")), project_claim(claim("failed")),
        project_status(observe("retained_unstarted")), project_status(observe()),
        project_status(observe("completed"), envelope),
        project_status(observe("failed", failure=SourceOperationFailure(code="scene_player_agency_violation", stage="policy"))),
        project_source_unavailable(operation_id="operation-1", phase="preparation"),
        project_status(observe("failed")),
    )


def test_briefing_preserves_authored_literal_text_without_turn_source_or_request():
    manifest = setup()
    before = manifest.model_dump(mode="json")
    result = project_source_briefing(manifest, session_id="session-1")
    assert result.model_dump(mode="json") == {
        "protocol": PROTOCOL, "event": "briefing", "origin": "authored_trial_setup", "text": manifest.briefing,
    }
    assert manifest.model_dump(mode="json") == before
    assert "Objetivo declarado pelo jogador (intenção, não fato estabelecido):" in result.text


@pytest.mark.parametrize("newly", [False, True])
def test_pending_preparation_never_exposes_new_claim_authority_or_private_payload(newly):
    value = claim(newly=newly)
    before = value.model_dump(mode="json")
    result = project_claim(value)
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "preparation",
        "operation_id": value.request.operation_id, "status": "pending"}
    assert value.model_dump(mode="json") == before
    assert "PRIVATE" not in result.model_dump_json()


def test_completed_preparation_ready_is_only_observation_without_capsule_permission():
    value = claim("completed")
    result = project_claim(value)
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "preparation",
        "operation_id": "operation-1", "status": "ready"}
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.parametrize("internal,status,public", [
    ("source_input_out_of_scope", "failed", "out_of_scope"),
    ("source_input_clarification_required", "failed", "clarification_required"),
    ("source_input_base_mismatch", "failed", "preparation_failed"),
    ("source_input_production_failed", "failed", "preparation_failed"),
    ("source_input_cancelled", "cancelled", "cancelled"),
    ("process_interrupted", "cancelled", "cancelled"),
    ("source_input_deadline_exceeded", "timeout", "timeout"),
])
@pytest.mark.parametrize("stage", [None, "preflight", "classification", "resolution", "production", "finalization"])
def test_preparation_terminals_have_only_closed_public_category_and_stage(internal, status, public, stage):
    value = claim(status, code=internal, stage=stage)
    before = value.model_dump(mode="json")
    result = project_claim(value)
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "preparation_rejected",
        "operation_id": "operation-1", "status": status, "code": public, "stage": stage}
    assert "PRIVATE" not in result.model_dump_json()
    assert value.model_dump(mode="json") == before


@pytest.mark.parametrize("status", ["retained_unstarted", "pending"])
def test_retained_unstarted_is_distinct_even_when_base_is_old(status):
    result = project_status(observe(status))
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "narrative_pending",
        "operation_id": "operation-1", "status": status}


def test_completed_preserves_n_q_separately_and_never_relabels_historical_turn():
    envelope, _ = fixture(text=TEXT + " O catálogo de cafe\u0301 permanece ali. 🙂")
    status = observe("completed", current_turn=80, current_state_revision=105)
    before = deepcopy((status.model_dump(mode="json"), envelope.model_dump(mode="json")))
    result = project_status(status, envelope)
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "narrative_complete",
        "operation_id": "operation-1", "n": envelope.projection.text, "q": QUESTION}
    assert "\n\n" not in result.n and result.q not in result.n
    assert before == (status.model_dump(mode="json"), envelope.model_dump(mode="json"))
    assert "turn" not in result.model_dump()


@pytest.mark.parametrize("internal,status,public", [
    ("source_turn_cancelled", "cancelled", "cancelled"),
    ("process_interrupted", "cancelled", "cancelled"),
    ("source_turn_deadline_exceeded", "timeout", "timeout"),
    ("source_turn_provider_failure", "failed", "narrative_failed"),
    ("source_turn_commit_failed", "failed", "narrative_failed"),
    ("source_turn_policy_failed", "failed", "narrative_rejected"),
    ("scene_secret_disclosed", "failed", "narrative_rejected"),
    ("scene_player_agency_violation", "failed", "narrative_rejected"),
])
@pytest.mark.parametrize("stage", [None, "preflight", "generation", "policy", "admission", "delivery", "commit"])
def test_known_narrative_terminals_map_without_provider_or_policy_prose(internal, status, public, stage):
    result = project_status(observe(status, failure=SourceOperationFailure(code=internal, stage=stage)))
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "narrative_rejected",
        "operation_id": "operation-1", "status": status, "code": public, "stage": stage}


@pytest.mark.parametrize("status", ["failed", "timeout", "cancelled"])
@pytest.mark.parametrize("raw_error", [None, "PRIVATE_SENTINEL", {"code": "PRIVATE_SENTINEL"},
    {"code": "source_turn_cancelled", "stage": "PRIVATE_SENTINEL", "evidence": "PRIVATE_SENTINEL"}])
def test_unknown_error_stays_unavailable_without_echo_or_invented_reason(status, raw_error):
    before = deepcopy(raw_error)
    result = project_status(observe(status, failure=safe_source_failure(raw_error)))
    assert result.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "unavailable",
        "operation_id": "operation-1", "phase": "narrative", "code": "unavailable"}
    assert raw_error == before


def test_unmapped_but_valid_internal_code_does_not_expand_public_contract():
    result = project_status(observe("failed", failure=SourceOperationFailure(code="source_context_scene_invalid")))
    assert type(result) is SourceUnavailableEvent


def test_raw_diagnostic_extras_are_discarded_before_projection_while_known_code_survives():
    raw = {"code": "scene_player_agency_violation", "stage": "policy",
           "error_json": "PRIVATE_ERROR_SENTINEL", "evidence": {"raw": "PRIVATE_EVIDENCE_SENTINEL"}}
    result = project_status(observe("failed", failure=safe_source_failure(raw)))
    assert result.code == "narrative_rejected" and result.stage == "policy"
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.parametrize("field", ["session_id", "operation_id"])
@pytest.mark.parametrize("wrong", ["different", " padded", "", "x" * 241, True, None, "\ud800"])
def test_factories_bind_expected_server_identities(field, wrong):
    kwargs = dict(session_id="synthetic-session", operation_id="operation-1")
    kwargs[field] = wrong
    closed(project_source_preparation, claim(), **kwargs)
    kwargs["session_id"] = "session-1" if field == "operation_id" else wrong
    closed(project_source_operation, observe(), **kwargs)


@pytest.mark.parametrize("wrong", ["other", " padded", "", "x" * 241, True, None, "\ud800"])
def test_briefing_binds_server_session(wrong):
    closed(project_source_briefing, setup(), session_id=wrong)


@pytest.mark.parametrize("status", ["retained_unstarted", "pending", "failed", "timeout", "cancelled"])
def test_uncommitted_narrative_text_is_never_accepted_even_when_envelope_is_valid(status):
    envelope, _ = fixture()
    closed(project_status, observe(status), envelope)


def test_completed_requires_envelope_and_exact_committed_pair():
    envelope, _ = fixture()
    closed(project_status, observe("completed"))
    closed(project_status, observe("completed", committed_turn_id="another-turn"), envelope)
    closed(project_status, observe("completed"), envelope.model_copy(update={"operation_id": "other"}))
    closed(project_status, observe("completed", session_id="other"), envelope)


@pytest.mark.parametrize("changes", [
    {"status": "pending", "committed_turn_id": "turn-1"}, {"current_turn": True},
    {"current_state_revision": 2}, {"base_turn": 4}, {"protocol": "legacy"},
    {"can_retry": True}, {"error_json": "PRIVATE_SENTINEL"},
    {"failure": {"code": "PRIVATE_SENTINEL"}},
])
def test_forged_status_fails_closed_instead_of_becoming_unavailable(changes):
    closed(project_status, observe().model_copy(update=changes))


@pytest.mark.parametrize("status,code", [("failed", "source_turn_cancelled"),
    ("cancelled", "source_turn_deadline_exceeded"), ("timeout", "source_turn_commit_failed")])
def test_contradictory_known_narrative_terminal_and_code_fail_closed(status, code):
    closed(project_status, observe(status, failure=SourceOperationFailure(code=code)))


@pytest.mark.parametrize("where", ["manifest", "request", "origin"])
def test_briefing_rejects_forged_nested_model_extras_and_hash_changes(where):
    value = setup()
    if where == "manifest":
        value = value.model_copy(update={"briefing": "PRIVATE_SENTINEL"})
    else:
        nested = getattr(value, where).model_copy(update={"forged": "PRIVATE_SENTINEL"})
        value = value.model_copy(update={where: nested})
    closed(project_source_briefing, value, session_id="session-1")


@pytest.mark.parametrize("kind", ["extra", "request", "config", "completion", "missing", "cycle", "failure_extra", "failure_unknown"])
def test_forged_claims_and_nested_data_fail_without_leakage(kind):
    value = claim("failed")
    if kind == "extra":
        value = value.model_copy(update={"can_retry": True})
    elif kind == "request":
        value = value.model_copy(update={"request": value.request.model_copy(update={"operation_id": "other"})})
    elif kind == "config":
        value = value.model_copy(update={"request": value.request.model_copy(update={"config": value.request.config.model_copy(update={"key": "PRIVATE_SENTINEL"})})})
    elif kind == "completion":
        value = value.model_copy(update={"completion": value.completion.model_copy(update={"request_sha256": "0" * 64})})
    elif kind == "missing":
        value = SourceInputClaim.model_construct(status="pending", newly_claimed=True)
    elif kind == "cycle":
        value.request.state["cycle"] = value.request.state
    else:
        updates = {"evidence": "PRIVATE_SENTINEL"} if kind == "failure_extra" else {"code": "PRIVATE_SENTINEL"}
        value = value.model_copy(update={"completion": value.completion.model_copy(update={"failure": value.completion.failure.model_copy(update=updates)})})
    closed(project_claim, value)


@pytest.mark.parametrize("kind", ["envelope_extra", "source_extra", "source_pydantic_extra", "binding_extra",
    "assessment_extra", "projection_text", "question", "source_hash", "source_session", "construct", "source_type"])
def test_nested_envelope_forgery_is_recursively_revalidated(kind):
    value, _ = fixture()
    if kind == "envelope_extra":
        value = value.model_copy(update={"can_retry": True})
    elif kind == "question":
        value = value.model_copy(update={"question": "Outra pergunta?"})
    elif kind == "construct":
        value = type(value).model_construct(**{**value.__dict__, "question": False})
    elif kind == "projection_text":
        value = value.model_copy(update={"projection": value.projection.model_copy(update={"text": "PRIVATE_SENTINEL"})})
    elif kind in ("source_extra", "source_pydantic_extra", "source_hash", "source_session", "source_type"):
        source = value.projection.source.model_copy()
        if kind == "source_pydantic_extra":
            object.__setattr__(source, "__pydantic_extra__", {"secret": "PRIVATE_SENTINEL"})
        else:
            updates = {"source_extra": {"secret": "PRIVATE_SENTINEL"}, "source_hash": {"sha256": "0" * 64},
                       "source_session": {"session_id": "other"}, "source_type": {"source_id": True}}
            source = source.model_copy(update=updates[kind])
        value = value.model_copy(update={"projection": value.projection.model_copy(update={"source": source})})
    else:
        name = "binding" if kind == "binding_extra" else "assessment"
        child = getattr(value.projection, name).model_copy(update={"private": "PRIVATE_SENTINEL"})
        value = value.model_copy(update={"projection": value.projection.model_copy(update={name: child})})
    closed(project_status, observe("completed"), value)


def test_factories_only_accept_typed_server_results_not_client_lookalike_mappings():
    closed(project_claim, claim().model_dump(mode="json"))
    closed(project_status, observe().model_dump(mode="json"))
    closed(project_source_briefing, setup().model_dump(mode="json"), session_id="session-1")
    envelope, _ = fixture()
    closed(project_status, observe("completed"), envelope.model_dump(mode="json"))


def test_public_models_are_strict_frozen_versioned_and_exact_in_json_roundtrip():
    for value in samples():
        op = None if type(value) is SourceBriefingEvent else "operation-1"
        payload = json.loads(value.model_dump_json())
        result = validate_source_public_event(payload, operation_id=op)
        assert type(result) is type(value) and result == value and result is not value
        assert validate_source_public_event(value, operation_id=op) == value
        with pytest.raises(ValidationError):
            value.protocol = "other"
        for update in ({"protocol": "legacy"}, {"can_retry": True}, {"state": "PRIVATE_SENTINEL"}):
            forged = value.model_copy(update=update)
            closed(validate_source_public_event, forged, operation_id=op)
            with pytest.raises(ValidationError):
                type(value).model_validate(forged)


@pytest.mark.parametrize("updates", [{"operation_id": True}, {"operation_id": " other"}, {"n": True},
    {"n": "short"}, {"q": "x" * 201}, {"q": " padded"}, {"n": "x" * 1601},
    {"q": "\ud800"}, {"state": "PRIVATE_SENTINEL"}, {"event": "unknown"}])
def test_public_complete_rejects_forged_wire_types_and_content(updates):
    value = SourceNarrativeCompleteEvent(operation_id="operation-1", n=TEXT, q=QUESTION)
    closed(validate_source_public_event, value.model_copy(update=updates), operation_id="operation-1")


@pytest.mark.parametrize("model,kwargs", [
    (SourcePreparationEvent, {"status": "completed"}),
    (SourceNarrativePendingEvent, {"status": "ready"}),
    (SourcePreparationRejectedEvent, {"status": "failed", "code": "PRIVATE_SENTINEL"}),
    (SourcePreparationRejectedEvent, {"status": "failed", "code": "timeout"}),
    (SourcePreparationRejectedEvent, {"status": "failed", "code": "preparation_failed", "stage": "commit"}),
    (SourceNarrativeRejectedEvent, {"status": "failed", "code": "narrative_failed", "stage": "PRIVATE_SENTINEL"}),
    (SourceUnavailableEvent, {"phase": "PRIVATE_SENTINEL"}),
])
def test_public_state_models_refuse_unknown_status_code_stage_and_combination(model, kwargs):
    with pytest.raises(ValidationError):
        model(operation_id="operation-1", **kwargs)


def test_public_validation_rechecks_identity_and_has_no_provenance_authority():
    for value in samples():
        closed(validate_source_public_event, value, operation_id="wrong")
    # A standalone public payload is syntactically valid, never evidence of a
    # confirmed database turn. The factory separately requires the server pair.
    standalone = SourceNarrativeCompleteEvent(operation_id="operation-1", n=TEXT, q=QUESTION)
    assert validate_source_public_event(standalone, operation_id="operation-1") == standalone


def test_every_public_payload_omits_private_objects_hashes_execution_and_retry_flags():
    forbidden = {"request", "claim", "capsule", "config", "target", "system_prompt", "state", "relationships",
        "error_json", "evidence", "can_retry", "can_execute", "newly_claimed", "snapshot", "provenance",
        "fingerprint_sha256", "capsule_sha256", "presentation_sha256", "player_input", "session_id", "turn_number"}
    for value in samples():
        payload = value.model_dump(mode="json")
        assert not forbidden.intersection(payload)
        assert all(type(item) in (str, type(None)) for item in payload.values())
        assert "PRIVATE" not in value.model_dump_json()


def test_projection_never_calls_rules_storage_production_or_narrative_executor(monkeypatch):
    import api.narrative_source_action_producer as producer
    import api.narrative_source_coordinator as coordinator
    import api.narrative_source_input_service as input_service
    import api.rules_service as rules
    from api.persistence import SQLitePersistence
    pending = claim(newly=True)
    complete_claim = claim("completed")
    envelope, _ = fixture()
    manifest = setup()
    def forbidden(*args, **kwargs):
        raise AssertionError("Projection must never execute external work")
    monkeypatch.setattr(producer, "produce_source_player_action", forbidden)
    monkeypatch.setattr(input_service, "prepare_source_player_action", forbidden)
    monkeypatch.setattr(coordinator, "execute_retained_source_turn", forbidden)
    monkeypatch.setattr(rules, "calculate_resolution", forbidden)
    monkeypatch.setattr(rules.random, "randint", forbidden)
    for name in ("claim_source_input", "finalize_source_input", "read_source_operation_status",
                 "create_source_setup_campaign", "read_source_setup_manifest"):
        monkeypatch.setattr(SQLitePersistence, name, forbidden)
    assert project_claim(pending).status == "pending"
    assert project_claim(complete_claim).status == "ready"
    assert project_source_briefing(manifest, session_id="session-1").text == manifest.briefing
    assert project_status(observe("completed"), envelope).n == TEXT
    assert project_status(observe("retained_unstarted")).status == "retained_unstarted"
    assert project_status(observe("cancelled")).code == "unavailable"


def test_module_has_no_router_executor_storage_clock_rng_or_network_dependency():
    import api.narrative_source_transport as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {"__future__", "typing", "pydantic", "narrative_source_input",
        "narrative_source_setup", "narrative_source_status", "narrative_source_turn"}
    assert not any(isinstance(node, (ast.Import, ast.AsyncFunctionDef)) for node in ast.walk(tree))


@pytest.mark.anyio
@pytest.mark.parametrize("kind,expected_status", [
    ("provider_timeout", "timeout"), ("provider_cancelled", "cancelled"), ("delivery", "cancelled"),
])
async def test_actual_executor_provider_and_delivery_terminals_project_after_restart(tmp_path, kind, expected_status):
    # These pairs are emitted by execute_source_turn's LLMInvocationError and
    # _Stopped paths, not fabricated from a desired public classification.
    from api.llm.contract import ErrorCategory
    from api.persistence import SQLitePersistence
    from test_narrative_source_bridge import _gateway
    from test_narrative_source_capsule_persistence import ledger
    from test_narrative_source_coordinator import SESSION, make_store, prepare, run
    store = await make_store(tmp_path)
    await prepare(store)
    overrides = {}
    if kind.startswith("provider_"):
        category = ErrorCategory.TIMEOUT if kind == "provider_timeout" else ErrorCategory.CANCELLED
        _, gateway = _gateway(failure_category=category)
        expected_internal, expected_stage = "source_turn_provider_failure", "generation"
    else:
        _, gateway = _gateway()
        async def reject_chunk(value):
            raise RuntimeError("PRIVATE_DELIVERY_SENTINEL")
        overrides["on_chunk"] = reject_chunk
        expected_internal, expected_stage = "source_turn_delivery_failed", "delivery"
    result, _, chunks = await run(store, gateway=gateway, **overrides)
    assert result.status == expected_status and result.envelope is None
    assert len(gateway.requests) == 1 and not chunks
    before = ledger(store)
    reader = SQLitePersistence(store.db_path)
    observed = await reader.read_source_operation_status(SESSION, "first")
    assert observed.status == expected_status
    assert observed.failure.code == expected_internal and observed.failure.stage == expected_stage
    public = project_source_operation(observed, session_id=SESSION, operation_id="first")
    assert public.model_dump(mode="json") == {"protocol": PROTOCOL, "event": "narrative_rejected",
        "operation_id": "first", "status": expected_status, "code": expected_status, "stage": expected_stage}
    assert project_source_operation(observed, session_id=SESSION, operation_id="first") == public
    assert "PRIVATE" not in public.model_dump_json()
    assert len(gateway.requests) == 1 and ledger(store) == before
