"""Pure aggregate consistency: these fixtures prove no database provenance."""
import ast
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.narrative_source_input import SourceInputClaim, create_source_input_request
from api.narrative_source_observation import (
    SourceConfirmedObservation, SourceObservationError, SourcePlayerObservation,
    SourceRequestedObservation, validate_source_player_observation,
)
from api.narrative_source_setup import create_source_setup_manifest
from api.narrative_source_status import SourceOperationSnapshot
from api.narrative_source_transport import project_source_briefing, project_source_operation, project_source_preparation
from test_narrative_source_input import request, config, complete, failed
from test_narrative_source_preparation import snapshot
from test_narrative_source_turn import fixture

SESSION, OP = "session-1", "operation-1"


def sample(p_status="completed", h_status="completed"):
    base = request()
    original = create_source_input_request(SESSION,
        {"operation_id": OP, "player_input": base.player_input}, created_at=base.created_at,
        snapshot=snapshot(SESSION), state=base.state, relationships=base.relationships,
        producer_config=config(system_prompt="PRIVATE_SYSTEM_SENTINEL"))
    completion = complete(original) if p_status == "completed" else (
        failed(original) if p_status == "failed" else None)
    claim = SourceInputClaim(request=original, status=p_status, newly_claimed=False, completion=completion)
    narrative, envelope, latest = None, None, None
    if p_status == "completed":
        narrative = SourceOperationSnapshot(session_id=SESSION, operation_id=OP,
            capsule_sha256=completion.capsule_sha256, base_turn=0, base_state_revision=7,
            current_turn=1 if h_status == "completed" else 0,
            current_state_revision=8 if h_status == "completed" else 7,
            status=h_status, committed_turn_id="turn-1" if h_status == "completed" else None)
        if h_status == "completed":
            envelope, _ = fixture()
            latest = SourceConfirmedObservation(operation=narrative, envelope=envelope)
    return SourcePlayerObservation(session_id=SESSION,
        manifest=create_source_setup_manifest({"location": "Oficina", "npcs_present": [],
            "declared_objective": "Conhecer o lugar."}, session_id=SESSION),
        latest_completed=latest, requested=SourceRequestedObservation(operation_id=OP,
            preparation=claim, narrative=narrative, confirmed=envelope))


def check(value, **updates):
    args = dict(session_id=SESSION, operation_id=OP)
    args.update(updates)
    return validate_source_player_observation(value, **args)


def rejected(value, **updates):
    with pytest.raises(SourceObservationError) as error:
        check(value, **updates)
    assert str(error.value) == "source_observation_invalid"
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("p,h", [
    ("pending", None), ("failed", None), ("completed", "retained_unstarted"),
    ("completed", "pending"), ("completed", "failed"), ("completed", "timeout"),
    ("completed", "cancelled"), ("completed", "completed"),
])
def test_existing_public_projections_consume_only_explicit_aggregate_members(p, h):
    value = check(sample(p, h))
    public = [project_source_briefing(value.manifest, session_id=SESSION),
              project_source_preparation(value.requested.preparation, session_id=SESSION, operation_id=OP)]
    if value.requested.narrative is not None:
        public.append(project_source_operation(value.requested.narrative, session_id=SESSION,
            operation_id=OP, confirmed_envelope=value.requested.confirmed))
    assert "PRIVATE" not in str([item.model_dump(mode="json") for item in public])
    assert value.model_dump(mode="json") == {"protocol": "source-player-observation-v1"}
    assert "PRIVATE" not in repr(value) and SESSION not in repr(value)


def test_missing_query_and_unknown_query_are_distinct_and_never_pending():
    value = sample().model_copy(update={"requested": None})
    assert check(value, operation_id=None).requested is None
    rejected(value)
    unknown = value.model_copy(update={"requested": SourceRequestedObservation(operation_id="unknown")})
    result = check(unknown, operation_id="unknown")
    assert result.requested.preparation is result.requested.narrative is result.requested.confirmed is None
    rejected(unknown, operation_id=None)


def test_revalidation_detaches_nested_claims_and_envelopes_and_rejects_newness():
    source = sample()
    copied = check(source)
    assert copied == source and copied is not source
    assert copied.requested.preparation is not source.requested.preparation
    assert copied.latest_completed.envelope is not source.latest_completed.envelope
    pending = sample("pending", None)
    pending.requested.preparation.__dict__["newly_claimed"] = True
    rejected(pending)
    with pytest.raises(ValidationError):
        copied.session_id = "other"


@pytest.mark.parametrize("kind", [
    "outer_extra", "outer_pydantic_extra", "manifest_extra", "origin_extra",
    "requested_extra", "claim_extra", "config_extra", "target_extra", "parameters_extra",
    "snapshot_extra", "latest_extra", "envelope_extra", "projection_extra", "source_extra",
])
def test_forged_nested_extras_cannot_disappear_in_model_dump(kind):
    value = deepcopy(sample())
    members = {
        "outer_extra": value, "outer_pydantic_extra": value, "manifest_extra": value.manifest,
        "origin_extra": value.manifest.origin, "requested_extra": value.requested,
        "claim_extra": value.requested.preparation, "config_extra": value.requested.preparation.request.config,
        "target_extra": value.requested.preparation.request.config.target,
        "parameters_extra": value.requested.preparation.request.config.parameters,
        "snapshot_extra": value.requested.narrative, "latest_extra": value.latest_completed,
        "envelope_extra": value.requested.confirmed, "projection_extra": value.requested.confirmed.projection,
        "source_extra": value.requested.confirmed.projection.source,
    }
    if kind == "outer_pydantic_extra":
        object.__setattr__(members[kind], "__pydantic_extra__", {"PRIVATE": True})
    else:
        members[kind].__dict__["PRIVATE"] = True
    rejected(value)


@pytest.mark.parametrize("kind", [
    "session", "requested_id", "claim_missing", "claim_pending_with_h", "h_missing",
    "capsule_hash", "base", "envelope_missing", "envelope_uncommitted", "foreign_envelope",
    "latest_not_last", "latest_missing", "latest_pair_differs", "manifest_origin",
])
def test_inconsistent_detached_pairs_are_closed(kind):
    value = sample()
    if kind == "session": value = value.model_copy(update={"session_id": "other"})
    elif kind == "requested_id": value.requested.__dict__["operation_id"] = "other"
    elif kind == "claim_missing": value.requested.__dict__["preparation"] = None
    elif kind == "claim_pending_with_h": value.requested.__dict__["preparation"] = sample("pending", None).requested.preparation
    elif kind == "h_missing": value.requested.__dict__["narrative"] = None
    elif kind == "capsule_hash": value.requested.narrative.__dict__["capsule_sha256"] = "f"*64
    elif kind == "base": value.requested.narrative.__dict__["base_state_revision"] = 6
    elif kind == "envelope_missing": value.requested.__dict__["confirmed"] = None
    elif kind == "envelope_uncommitted": value.requested.__dict__["narrative"] = sample("completed", "pending").requested.narrative
    elif kind == "foreign_envelope": value.requested.confirmed.__dict__["operation_id"] = "other"
    elif kind == "latest_not_last": value.latest_completed.operation.__dict__["current_turn"] = 2
    elif kind == "latest_missing": value.__dict__["latest_completed"] = None
    elif kind == "latest_pair_differs": value.latest_completed.operation.__dict__["capsule_sha256"] = "f"*64
    else:
        value.__dict__["manifest"] = create_source_setup_manifest({"location": "Outra",
            "npcs_present": [], "declared_objective": "Conhecer."}, session_id=SESSION)
    rejected(value)


@pytest.mark.parametrize("identity", ["", " padded ", 1, True, "x"*241, "\ud800"])
def test_query_identity_rejects_nonliteral_values(identity):
    rejected(sample(), operation_id=identity)
    rejected(sample(), session_id=identity)


def test_module_has_no_storage_or_execution_dependency():
    tree = ast.parse(Path("api/narrative_source_observation.py").read_text(encoding="utf-8"))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(item in imports for item in (
        "persistence", "main", "state_service", "narrative_source_input_service",
        "narrative_source_coordinator", "narrative_source_execution_service"))
    for unsafe in ("PRIVATE_ERROR", None, {}, 42):
        assert str(SourceObservationError(unsafe)) == "source_observation_invalid"
