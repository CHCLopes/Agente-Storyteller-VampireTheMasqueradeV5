"""Pure source-turn pair and aggregate boundaries; no semantic truth oracle."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

import pytest
from pydantic import ValidationError

from api.llm.contract import AdapterIdentity, LLMTarget, Provenance
from api.narrative_grounding import (
    DerivationDecision, DerivationDestination, SemanticStatus,
    bind_narrative_derivation, create_narrative_source, materialize_source_projection,
)
from api.narrative_source_profile import VERSION
from api.narrative_source_turn import (
    INVOCATION_OPERATION, PROTOCOL, NarrativeSourceTurnEnvelope,
    SourceTurnCode, SourceTurnContractError,
    create_source_turn_envelope, validate_source_turn_commit,
)
from api.turn_models import CanonicalEvent, CanonicalFact, NarrativeRecord, RecordReference

NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)
TEXT = (
    "O pátio permanece silencioso entre as paredes altas. Perto do banco vazio, "
    "a luz da janela ilumina o chão de pedra. Uma brisa leve passa pelas folhas "
    "da trepadeira, que ainda cobre parte do muro."
)
QUESTION = "O que você faz agora?"


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_projection(text=TEXT, visibility="player", policy=VERSION):
    # Models here represent an already-admitted caller-owned source. The pure
    # commit boundary does not pretend to repeat scene-policy/semantic checks.
    source = create_narrative_source(
        source_id="source-1", session_id="session-1", turn_id="turn-1",
        invocation_id="invocation-1", text=text, source_policy=policy,
        visibility=visibility,
    )
    binding = bind_narrative_derivation(source, text,
        destination=DerivationDestination.NARRATIVE_SOURCE_VIEW)
    return materialize_source_projection(source, binding, text)


def fixture(*, text=TEXT, visibility="player"):
    projection = make_projection(text, visibility)
    fact = CanonicalFact(
        fact_id="fact-1", fact_type="action.declaration", predicate="declared_player_action",
        value={"player_input": "Espero sem tocar em nada.", "requires_roll": False,
               "summary": "Espera declarada pelo jogador."}, occurred_at=NOW,
        visibility=visibility,
        source_refs=(RecordReference(record_id="orchestrator.local_action_classification",
                                     record_type="deterministic_module", relation="produced_by"),),
    )
    event = CanonicalEvent(event_id="event-1", session_id="session-1", turn_id="turn-1",
                           sequence=0, event_type="player_action_declared", occurred_at=NOW,
                           summary="Espero sem tocar em nada.", fact_ids=(fact.fact_id,),
                           visibility=visibility)
    narrative = NarrativeRecord(
        narrative_id="narrative-1", session_id="session-1", turn_id="turn-1",
        created_at=NOW, text=text + "\n\n" + QUESTION,
        source_event_ids=(event.event_id,), invocation_id="invocation-1", visibility=visibility,
    )
    provenance = {"invocations": [{
        "invocation_id": "invocation-1", "operation": INVOCATION_OPERATION,
        "status": "completed", "error": None,
        "provenance": Provenance(
            invocation_id="invocation-1",
            requested_target=LLMTarget(profile="local-proof", provider="fake", model="authored"),
            adapter=AdapterIdentity(name="fixture", version="1"), started_at=NOW, finished_at=NOW,
        ).model_dump(mode="json"),
    }]}
    envelope = create_source_turn_envelope(
        projection=projection, narrative=narrative, question=QUESTION,
        operation_id="operation-1", attempt_id="attempt-1", provenance=provenance,
    )
    arguments = dict(narrative=narrative, session_id="session-1", turn_id="turn-1",
                     operation_id="operation-1", attempt_id="attempt-1",
                     expected_invocation_id="invocation-1",
                     expected_invocation_operation=INVOCATION_OPERATION,
                     facts=(fact,), events=(event,), memory_candidates=(), episodic_memories=(),
                     provenance=provenance)
    return envelope, arguments


def reject(envelope, arguments, code=None):
    with pytest.raises(SourceTurnContractError) as error:
        validate_source_turn_commit(envelope, **arguments)
    assert error.value.code in {item.value for item in SourceTurnCode}
    assert str(error.value) == error.value.code
    assert TEXT not in str(error.value)
    if code is not None:
        assert error.value.code == code


def test_literal_large_unicode_source_and_question_are_bound_without_memory_or_truth():
    text = " ".join([TEXT, "O catálogo de cafe\u0301 permanece ali. 🙂", TEXT, TEXT, TEXT])
    envelope, arguments = fixture(text=text)
    before = deepcopy(arguments)
    result = validate_source_turn_commit(envelope, **arguments)
    assert 600 < len(result.projection.text) <= 1600
    assert result.projection.text == text
    assert result.question == QUESTION
    assert QUESTION not in result.projection.source.text
    assert result.presentation_sha256 == sha(text + "\n\n" + QUESTION)
    assert result.projection.assessment.decision is DerivationDecision.SOURCE_ONLY
    assert result.projection.assessment.semantic_status is SemanticStatus.NOT_ASSESSED
    assert result.protocol == PROTOCOL
    assert arguments == before
    assert arguments["memory_candidates"] == arguments["episodic_memories"] == ()
    assert arguments["provenance"]["invocations"][0]["provenance"]["effective_model"] == {
        "value": None, "source": "unknown"}


def test_mapping_roundtrip_and_validated_result_do_not_alias_input():
    envelope, arguments = fixture()
    wire = json.loads(envelope.model_dump_json())
    for name in ("narrative",):
        arguments[name] = arguments[name].model_dump(mode="json")
    for name in ("facts", "events"):
        arguments[name] = [item.model_dump(mode="json") for item in arguments[name]]
    result = validate_source_turn_commit(wire, **arguments)
    wire["question"] = "ALTERADO"
    arguments["provenance"]["invocations"][0]["status"] = "failed"
    assert result.question == QUESTION
    assert result.provenance_sha256 == envelope.provenance_sha256


@pytest.mark.parametrize("field", ["session_id", "turn_id", "operation_id", "attempt_id",
                                   "expected_invocation_id", "expected_invocation_operation"])
def test_server_identity_is_independent_of_envelope(field):
    envelope, arguments = fixture()
    arguments[field] = "another-identity"
    reject(envelope, arguments, "source_turn_identity_mismatch")


@pytest.mark.parametrize("field,value", [
    ("question", "O que você observa?"), ("question", " " + QUESTION),
    ("question", True), ("question", "x" * 201),
    ("presentation_sha256", "0" * 64), ("protocol", "1.0"),
    ("invocation_operation", "H6.scene"), ("narrative_id", "other"),
    ("source_event_ids", ["event-1", "event-1"]),
    ("source_event_ids", {"event-1"}), ("source_event_ids", ["missing"]),
])
def test_forged_envelope_is_revalidated(field, value):
    envelope, arguments = fixture()
    reject(envelope.model_copy(update={field: value}), arguments)


def test_forged_extra_fields_are_not_erased_by_dump():
    envelope, arguments = fixture()
    reject(envelope.model_copy(update={"semantic_approval": True}), arguments)
    data = dict(envelope.__dict__)
    data["question"] = False
    reject(NarrativeSourceTurnEnvelope.model_construct(**data), arguments)
    arguments["facts"] = (arguments["facts"][0].model_copy(update={"unchecked": "extra"}),)
    reject(envelope, arguments)


@pytest.mark.parametrize("field,value", [("text", "wrong presentation"),
    ("complete", 1), ("complete", False), ("invocation_id", None),
    ("session_id", "other"), ("turn_id", "other"),
    ("visibility", "public"), ("source_event_ids", ("missing",))])
def test_legacy_narrative_forgery_is_revalidated(field, value):
    envelope, arguments = fixture()
    arguments["narrative"] = arguments["narrative"].model_copy(update={field: value})
    reject(envelope, arguments)


def test_presentation_whitespace_is_not_repaired_by_legacy_normalizer():
    envelope, arguments = fixture()
    arguments["narrative"] = arguments["narrative"].model_dump(mode="json")
    arguments["narrative"]["text"] = " " + arguments["narrative"]["text"]
    reject(envelope, arguments, "source_turn_narrative_invalid")


@pytest.mark.parametrize("text,policy,visibility", [
    (TEXT, "narrative-source-profile-v1", "player"),
    (TEXT, VERSION, "storyteller"), (TEXT, VERSION, "system"),
    ("too short", VERSION, "player"), ("a" * 1601, VERSION, "player"),
    (TEXT + "  more", VERSION, "player"),
])
def test_valid_core_projection_does_not_bypass_application_scope(text, policy, visibility):
    envelope, arguments = fixture()
    alternate = make_projection(text, visibility, policy)
    reject(envelope.model_copy(update={"projection": alternate}), arguments)


def test_nested_projection_or_assessment_forgery_is_recomputed():
    envelope, arguments = fixture()
    projection = envelope.projection.model_copy(update={"text": TEXT + " inventado"})
    reject(envelope.model_copy(update={"projection": projection}), arguments)
    assessment = envelope.projection.assessment.model_copy(update={"semantic_status": "confirmed"})
    projection = envelope.projection.model_copy(update={"assessment": assessment})
    reject(envelope.model_copy(update={"projection": projection}), arguments)


@pytest.mark.parametrize("name", ["memory_candidates", "episodic_memories"])
@pytest.mark.parametrize("value", [[{"summary": "not allowed"}], None, "", set(), iter(())])
def test_memory_collections_are_explicit_empty_ordered_inputs(name, value):
    envelope, arguments = fixture()
    arguments[name] = value
    reject(envelope, arguments, "source_turn_memories_forbidden")


@pytest.mark.parametrize("fact_type", ["world.scene", "world.scene.detail", "memory.semantic"])
def test_narrative_fact_types_cannot_be_injected(fact_type):
    envelope, arguments = fixture()
    arguments["facts"] = (arguments["facts"][0].model_copy(update={"fact_type": fact_type}),)
    reject(envelope, arguments, "source_turn_antecedents_invalid")


@pytest.mark.parametrize("event_type", ["scene_advanced", "player_scene_query", "unknown"])
def test_scene_derivation_and_query_events_are_outside_initial_bridge(event_type):
    envelope, arguments = fixture()
    arguments["events"] = (arguments["events"][0].model_copy(update={"event_type": event_type}),)
    reject(envelope, arguments, "source_turn_antecedents_invalid")


@pytest.mark.parametrize("field,value", [("fact_ids", ("missing",)), ("fact_ids", ()),
    ("fact_ids", ("fact-1", "fact-1")), ("session_id", "other"),
    ("turn_id", "other"), ("pending", True)])
def test_event_references_and_ownership_are_required(field, value):
    envelope, arguments = fixture()
    arguments["events"] = (arguments["events"][0].model_copy(update={field: value}),)
    reject(envelope, arguments)


@pytest.mark.parametrize("name", ["facts", "events"])
def test_duplicate_ids_or_unordered_collection_are_rejected(name):
    envelope, arguments = fixture()
    arguments[name] = arguments[name] * 2
    reject(envelope, arguments, "source_turn_antecedents_invalid")
    arguments[name] = iter(arguments[name])
    reject(envelope, arguments, "source_turn_antecedents_invalid")


def test_unique_event_ids_still_require_unique_sequence():
    envelope, arguments = fixture()
    event = arguments["events"][0].model_copy(update={"event_id": "event-2"})
    arguments["events"] += (event,)
    reject(envelope, arguments, "source_turn_antecedents_invalid")


@pytest.mark.parametrize("name", ["facts", "events"])
def test_restricted_antecedent_cannot_be_published_to_player(name):
    envelope, arguments = fixture()
    arguments[name] = (arguments[name][0].model_copy(update={"visibility": "storyteller"}),)
    reject(envelope, arguments, "source_turn_visibility_forbidden")


def test_unreferenced_relationship_antecedent_remains_server_state_not_narrative_source():
    envelope, arguments = fixture(visibility="public")
    fact = arguments["facts"][0].model_copy(update={"fact_id": "relationship-1",
            "fact_type": "world.relationships", "visibility": "storyteller"})
    event = arguments["events"][0].model_copy(update={"event_id": "relationship-event",
            "sequence": 1, "event_type": "relationship_state_updated",
            "fact_ids": (fact.fact_id,), "visibility": "storyteller"})
    arguments["facts"] += (fact,)
    arguments["events"] += (event,)
    result = validate_source_turn_commit(envelope, **arguments)
    assert result.source_event_ids == ("event-1",)


def test_factory_sorts_reference_ids_but_preserves_text_exactly():
    envelope, arguments = fixture()
    other = arguments["events"][0].model_copy(update={"event_id": "event-0", "sequence": 1})
    arguments["events"] += (other,)
    arguments["narrative"] = arguments["narrative"].model_copy(update={
        "source_event_ids": ("event-1", "event-0")})
    result = create_source_turn_envelope(projection=envelope.projection,
        narrative=arguments["narrative"], question=QUESTION, operation_id="operation-1",
        attempt_id="attempt-1", provenance=arguments["provenance"])
    assert result.source_event_ids == ("event-0", "event-1")
    assert validate_source_turn_commit(result, **arguments).projection.text == TEXT


@pytest.mark.parametrize("field,value", [("status", "failed"), ("status", True),
    ("operation", "H6.scene"), ("invocation_id", "other"),
    ("error", {"message": "private synthetic text"})])
def test_matching_invocation_must_be_completed_and_exact(field, value):
    envelope, arguments = fixture()
    arguments["provenance"]["invocations"][0][field] = value
    reject(envelope, arguments, "source_turn_provenance_invalid")


@pytest.mark.parametrize("shape", ["empty", "duplicate", "extra_h6", "nested_id", "extra", "surrogate"])
def test_audit_shape_ids_and_safe_serialization(shape):
    envelope, arguments = fixture()
    audit = arguments["provenance"]
    if shape == "empty":
        audit["invocations"] = []
    elif shape in ("duplicate", "extra_h6"):
        row = deepcopy(audit["invocations"][0])
        if shape == "extra_h6":
            row["invocation_id"] = "another"
        audit["invocations"].append(row)
    elif shape == "nested_id":
        audit["invocations"][0]["provenance"]["invocation_id"] = "another"
    elif shape == "extra":
        audit["invocations"][0]["body"] = "private synthetic text"
    else:
        audit["invocations"][0]["provenance"]["adapter"]["name"] = "\ud800"
    reject(envelope, arguments, "source_turn_provenance_invalid")


def test_other_invocations_are_bound_without_inventing_provider_or_usage():
    envelope, arguments = fixture()
    row = deepcopy(arguments["provenance"]["invocations"][0])
    row.update(invocation_id="prior-1", operation="H1.action")
    row["provenance"]["invocation_id"] = "prior-1"
    arguments["provenance"]["invocations"].insert(0, row)
    bound = create_source_turn_envelope(projection=envelope.projection,
        narrative=arguments["narrative"], question=QUESTION, operation_id="operation-1",
        attempt_id="attempt-1", provenance=arguments["provenance"])
    assert validate_source_turn_commit(bound, **arguments) == bound
    arguments["provenance"]["invocations"][0]["provenance"]["adapter"]["version"] = "2"
    reject(bound, arguments, "source_turn_provenance_mismatch")


def test_public_fact_contents_remain_trusted_server_input_not_semantic_approval():
    envelope, arguments = fixture()
    arguments["facts"] = (arguments["facts"][0].model_copy(update={
        "value": {"summary": "Texto servidor diferente, não inferido a partir de n."}}),)
    result = validate_source_turn_commit(envelope, **arguments)
    assert result.projection.assessment.semantic_status is SemanticStatus.NOT_ASSESSED


def test_factory_does_not_hide_duplicate_references_or_invalid_pair():
    envelope, arguments = fixture()
    narrative = arguments["narrative"].model_copy(update={"source_event_ids": ("event-1", "event-1")})
    with pytest.raises(SourceTurnContractError):
        create_source_turn_envelope(projection=envelope.projection, narrative=narrative,
            question=QUESTION, operation_id="operation-1", attempt_id="attempt-1",
            provenance=arguments["provenance"])


def test_envelope_is_frozen_and_diagnostics_have_closed_domain():
    envelope, _ = fixture()
    with pytest.raises(ValidationError):
        envelope.question = "Mutação"
    for code in SourceTurnCode:
        assert SourceTurnContractError(code.value).code == code.value
    assert str(SourceTurnContractError("private synthetic text")) == "source_turn_invalid"


@pytest.mark.parametrize("field,value", [
    ("session_id", " session-1 "), ("turn_id", " turn-1 "),
    ("narrative_id", " narrative-1 "), ("invocation_id", " invocation-1 "),
    ("source_event_ids", (" event-1 ",)),
])
def test_narrative_identifiers_cannot_be_silently_normalized(field, value):
    envelope, arguments = fixture()
    arguments["narrative"] = arguments["narrative"].model_copy(update={field: value})
    reject(envelope, arguments, "source_turn_narrative_invalid")
