from __future__ import annotations

import json

import pytest

from api import scene_director_service as scene
from api import turn_execution_service as execution
from api.llm.contract import CancellationToken
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.state_service import sync_event_from_context
from test_turn_execution_service import (
    VALID_PROPOSAL, _context_packet_with_secret, _prepared, _target_and_capabilities,
)


@pytest.mark.anyio
async def test_secret_rejection_retains_only_structural_diagnostic(tmp_path):
    operation = "diagnostic-secret"
    secret = "A encomenda violeta permanece trancada no armário."
    prepared = _prepared(operation)
    prepared.context_packet = _context_packet_with_secret(secret)
    payload = VALID_PROPOSAL.model_dump(mode="json")
    payload["narrative"] += " " + secret
    store = SQLitePersistence(tmp_path / "diagnostic.sqlite3")
    await store.ensure_campaign(
        "session",
        initial_state=sync_event_from_context(
            "session", prepared.updated_context
        ).model_dump(mode="json"),
    )
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(capability_set=capabilities, structured_payload=payload)
    chunks = []

    async def collect(chunk):
        chunks.append(chunk)

    result = await execution.execute_prepared_turn(
        prepared, session_id="session", operation_id=operation,
        user_input="Eu avanço.", chronicle_name="Synthetic",
        store=store, gateway=gateway, target=target,
        cancellation=CancellationToken(), on_chunk=collect,
    )
    attempts = await store.list_attempts("session")
    assert result.status == "failed"
    assert result.error.code == "scene_secret_disclosed"
    assert result.error.retryable is False
    assert result.partial_narrative == ""
    assert chunks == []
    assert gateway.external_call_count == 1
    assert await store.list_turns("session") == []
    assert await store.list_memory_candidates("session") == []
    assert await store.list_episodic_memories("session") == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert attempts[0]["partial_narrative"] == ""
    diagnostic = attempts[0]["metadata"]["validation_diagnostic"]
    assert diagnostic["protocol"] == "scene-validation-diagnostic-v1"
    assert diagnostic["code"] == "scene_secret_disclosed"
    assert diagnostic["evidence"]["source"] == "protected_context"
    assert diagnostic["evidence"]["field"] == "narrative"
    assert diagnostic["evidence"]["field_index"] == 0
    assert diagnostic["evidence"]["comparison"] == "normalized_substring"
    safe = json.dumps(attempts, ensure_ascii=False)
    assert secret not in safe
    assert payload["narrative"] not in safe
    assert "violeta" not in safe
    assert "validation_diagnostic" not in result.error.model_dump_json()


def _roster_evidence():
    return {
        "previous_count": 1, "proposed_count": 2,
        "added_count": 1, "removed_count": 0,
        "fact_kind_counts": {
            "observation": 1, "clue": 0, "npc_action": 0,
            "complication": 0, "transition": 0, "hook": 0,
        },
        "has_change_fact": False,
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("previous_count", True), ("proposed_count", "2"),
        ("added_count", -1), ("removed_count", 9),
        ("has_change_fact", 0), ("private_text", "PRIVATE_SENTINEL"),
        ("fact_kind_counts", {"observation": 1}),
        ("fact_kind_counts", {
            "observation": 5, "clue": 0, "npc_action": 0,
            "complication": 0, "transition": 0, "hook": 0,
        }),
        ("fact_kind_counts", {
            "observation": 4, "clue": 1, "npc_action": 0,
            "complication": 0, "transition": 0, "hook": 0,
        }),
    ],
)
def test_roster_diagnostic_rejects_poison_and_invalid_types(key, value):
    evidence = _roster_evidence()
    evidence[key] = value
    error = scene.SceneProposalError(
        "scene_npc_roster_changed_without_event", evidence=evidence,
    )
    assert execution._scene_validation_diagnostic(error) is None


def test_roster_diagnostic_copies_nested_counts():
    error = scene.SceneProposalError(
        "scene_npc_roster_changed_without_event", evidence=_roster_evidence(),
    )
    diagnostic = execution._scene_validation_diagnostic(error)
    assert diagnostic["evidence"] == error.evidence
    error.evidence["fact_kind_counts"]["observation"] = 4
    assert diagnostic["evidence"]["fact_kind_counts"]["observation"] == 1
    error.code = "unlisted"
    assert execution._scene_validation_diagnostic(error) is None


@pytest.mark.parametrize(
    ("secret", "visible", "comparison"),
    [
        ("âmbar violeta", "O armário guarda âmbar violeta.", "normalized_substring"),
        ("âmbar violeta cobre bronze", "bronze cobre violeta âmbar", "shared_tokens"),
        ("âmbar violeta cobre bronze", "violeta âmbar prata chumbo", "shared_token_ratio"),
        ("Autoridade prepara cilada.", "Xerife organiza armadilha.", "shared_concepts"),
        ("âmbar violeta cobre bronze", "âmbar prata chumbo estanho", None),
        ("", "âmbar", None),
    ],
)
def test_overlap_decisions_keep_original_branches(secret, visible, comparison):
    detail = scene._secret_overlap_evidence(secret, visible)
    assert scene._secret_overlaps_visible(secret, visible) is (comparison is not None)
    if comparison is None:
        assert detail is None
    else:
        assert detail["comparison"] == comparison
        assert all(value is None or type(value) in {str, int} for value in detail.values())
        assert secret not in json.dumps(detail, ensure_ascii=False)


@pytest.mark.parametrize("source", ["in_proposal", "protected_context"])
@pytest.mark.parametrize(
    "field", ["narrative", "location", "scene_summary", "npcs_present",
              "open_threads", "resolved_threads", "player_prompt", "new_facts"],
)
def test_secret_diagnostic_tracks_only_structural_field_and_origin(source, field):
    secret = "Encomenda violeta lacrada no armário."
    payload = VALID_PROPOSAL.model_dump(mode="json")
    if field in {"npcs_present", "open_threads", "resolved_threads"}:
        payload[field] = [secret]
    elif field == "new_facts":
        payload[field][0]["summary"] = secret
    elif field == "narrative":
        payload[field] += " " + secret
    else:
        payload[field] = secret
    protected = (secret,)
    if source == "in_proposal":
        payload["new_facts"].append({
            "kind": "hook", "summary": secret, "visibility": "storyteller",
        })
        # Duplicate protected text must preserve the original proposal-first order.
    proposal = scene.SceneContinuationProposal.model_validate(payload)
    with pytest.raises(scene.SceneProposalError) as caught:
        scene._validate_secret_separation(
            proposal, scene._player_visible_scene_fields(proposal),
            protected_secrets=protected,
        )
    diagnostic = execution._scene_validation_diagnostic(caught.value)
    assert diagnostic["evidence"]["source"] == source
    assert diagnostic["evidence"]["field"] == field
    assert secret not in str(caught.value)
    assert secret not in json.dumps(diagnostic, ensure_ascii=False)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("field", "PRIVATE_SENTINEL"), ("field_index", True),
        ("field_index", 24), ("source", "PRIVATE_SENTINEL"),
        ("comparison", ["normalized_substring"]), ("shared_token_count", -1),
        ("token_denominator", 1601), ("shared_concept_count", 8),
        ("secret", "PRIVATE_SENTINEL"),
    ],
)
def test_secret_diagnostic_discards_untrusted_evidence(key, value):
    evidence = {
        "field": "narrative", "field_index": 0, "source": "protected_context",
        "comparison": "normalized_substring", "shared_token_count": None,
        "token_denominator": None, "shared_concept_count": None,
    }
    evidence[key] = value
    assert execution._scene_validation_diagnostic(
        scene.SceneProposalError("scene_secret_disclosed", evidence=evidence),
    ) is None


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            {"field": "narrative", "rule": "assigned_internal_state"},
            {"field": "narrative", "rule": "assigned_internal_state"},
        ),
        (
            {
                "field": "scene_summary", "rule": "unestablished_opening_history",
                "history_concepts": ["wake", "memory_loss"],
            },
            {
                "field": "scene_summary", "rule": "unestablished_opening_history",
                "history_concepts": ["wake", "memory_loss"],
            },
        ),
        (
            {
                "field": "narrative", "rule": "undeclared_player_action",
                "subject": "Nome privado do personagem", "clause_index": 2,
                "unauthorized_concepts": ["move", "social"],
            },
            {
                "field": "narrative", "rule": "undeclared_player_action",
                "subject_class": "explicit_player_reference", "clause_index": 2,
                "unauthorized_concepts": ["move", "social"],
            },
        ),
    ],
)
def test_agency_diagnostic_retains_only_closed_structural_evidence(evidence, expected):
    diagnostic = execution._scene_validation_diagnostic(
        scene.SceneProposalError("scene_player_agency_violation", evidence=evidence),
    )
    assert diagnostic == {
        "protocol": "scene-validation-diagnostic-v1",
        "code": "scene_player_agency_violation",
        "evidence": expected,
    }
    assert "Nome privado" not in json.dumps(diagnostic, ensure_ascii=False)


@pytest.mark.parametrize(
    "evidence",
    [
        {"field": "PRIVATE_SENTINEL", "rule": "assigned_internal_state"},
        {"field": "narrative", "rule": "PRIVATE_SENTINEL"},
        {"field": "narrative", "rule": "assigned_internal_state", "text": "PRIVATE_SENTINEL"},
        {"field": "narrative", "rule": "undeclared_player_action",
         "unauthorized_concepts": ["PRIVATE_SENTINEL"]},
        {"field": "narrative", "rule": "undeclared_player_action",
         "subject": "player_alias", "unauthorized_concepts": ["move"]},
        {"field": "scene_summary", "rule": "unestablished_opening_history",
         "history_concepts": ["PRIVATE_SENTINEL"]},
    ],
)
def test_agency_diagnostic_discards_untrusted_evidence(evidence):
    assert execution._scene_validation_diagnostic(
        scene.SceneProposalError("scene_player_agency_violation", evidence=evidence),
    ) is None


@pytest.mark.anyio
async def test_agency_rejection_persists_safe_diagnostic_without_narrative(
    tmp_path, monkeypatch,
):
    private = "PRIVATE_SENTINEL conteúdo narrativo rejeitado."
    payload = VALID_PROPOSAL.model_dump(mode="json")
    payload["narrative"] = private

    def reject(*args, **kwargs):
        raise scene.SceneProposalError(
            "scene_player_agency_violation",
            evidence={
                "field": "narrative", "rule": "undeclared_player_action",
                "subject": "Nome privado do personagem", "clause_index": 0,
                "unauthorized_concepts": ["move"],
            },
        )

    monkeypatch.setattr(execution, "validate_scene_continuation", reject)
    prepared = _prepared("agency-diagnostic")
    store = SQLitePersistence(tmp_path / "agency.sqlite3")
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(capability_set=capabilities, structured_payload=payload)

    async def collect(chunk):
        raise AssertionError("rejected narrative must not stream")

    result = await execution.execute_prepared_turn(
        prepared, session_id="session", operation_id="agency-diagnostic",
        user_input="Eu pergunto.", chronicle_name="Synthetic",
        store=store, gateway=gateway, target=target,
        cancellation=CancellationToken(), on_chunk=collect,
    )
    attempts = await store.list_attempts("session")
    diagnostic = attempts[0]["metadata"]["validation_diagnostic"]
    serialized = json.dumps(attempts, ensure_ascii=False)

    assert result.status == "failed"
    assert result.error.code == "scene_player_agency_violation"
    assert diagnostic["evidence"] == {
        "field": "narrative", "rule": "undeclared_player_action",
        "subject_class": "explicit_player_reference", "clause_index": 0,
        "unauthorized_concepts": ["move"],
    }
    assert private not in serialized
    assert "Nome privado" not in serialized
    assert await store.list_turns("session") == []


@pytest.mark.anyio
async def test_poisoned_evidence_never_reaches_attempt_or_error(tmp_path, monkeypatch):
    private = "PRIVATE_SENTINEL segredo e narrativa não devem ser auditados."
    poisoned = {**_roster_evidence(), "narrative": private, "secret": private}

    def reject(*args, **kwargs):
        raise scene.SceneProposalError(
            "scene_npc_roster_changed_without_event", evidence=poisoned,
        )

    monkeypatch.setattr(execution, "validate_scene_continuation", reject)
    prepared = _prepared("poisoned-diagnostic")
    store = SQLitePersistence(tmp_path / "poisoned.sqlite3")
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )
    chunks = []

    async def collect(chunk):
        chunks.append(chunk)

    result = await execution.execute_prepared_turn(
        prepared, session_id="session", operation_id="poisoned-diagnostic",
        user_input="Eu avanço.", chronicle_name="Synthetic",
        store=store, gateway=gateway, target=target,
        cancellation=CancellationToken(), on_chunk=collect,
    )
    attempts = await store.list_attempts("session")
    assert result.status == "failed"
    assert result.partial_narrative == ""
    assert chunks == []
    assert gateway.external_call_count == 1
    assert await store.list_turns("session") == []
    assert "validation_diagnostic" not in attempts[0]["metadata"]
    assert "PRIVATE_SENTINEL" not in json.dumps(attempts, ensure_ascii=False)
    assert "PRIVATE_SENTINEL" not in result.error.model_dump_json()
