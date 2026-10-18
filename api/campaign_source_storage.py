"""SQLite boundaries for the opt-in campaign source profile (schema v4).

P and K are control rows, never canonical turns. This module does not choose a
provider or migrate an existing campaign. SQLite BEGIN IMMEDIATE serializes
claims, finalization and commits across connections and processes.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from .campaign_progression_service import CampaignProgressState, read_campaign_progress_state
from .campaign_source_capsule import (
    CAPSULE_KEY, CampaignSourceCapsule, CampaignSourceConfig,
)
from .campaign_source_context import (
    ORIGIN_KEY, CampaignSourceOrigin, CampaignSourceSnapshot,
    create_campaign_source_origin,
)
from .campaign_source_turn import CONTEXT_KEY, CampaignSourceTurnEnvelope, validate_campaign_source_turn_commit
from .narrative_source_context import create_source_context_origin, validate_source_state_context
from .persistence import (
    SCHEMA_VERSION, SQLitePersistence, _json_dump, _json_load, _payload_hash,
    _attempt_request_payload, _utc_now,
)
from .scene_service import SceneState

INPUT_KEY = "campaign_source_input"
INPUT_PROTOCOL = "campaign-source-input-v1"
PREPARATION_PROTOCOL = "campaign-source-preparation-control-v1"
_H_PROTOCOL = "campaign-source-turn-v1"


def campaign_attempt_metadata(capsule: CampaignSourceCapsule, *,
                              operation_id: str, invocation_id: str,
                              resumes_operation_id: str | None = None) -> dict[str, object]:
    from .narrative_source_turn import INVOCATION_OPERATION
    return {
        "narrative_contract": _H_PROTOCOL,
        "original_operation_id": capsule.operation_id,
        "campaign_capsule_sha256": capsule.fingerprint_sha256,
        "expected_invocation_id": invocation_id,
        "expected_invocation_operation": INVOCATION_OPERATION,
        "source_context_base_state_revision": capsule.snapshot.state_revision,
        "h_operation_id": operation_id,
        "resumes_operation_id": resumes_operation_id,
    }


class CampaignSourceStorageError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _control_id(domain: str, session_id: str, operation_id: str, role: str) -> str:
    if (type(session_id) is not str or not session_id.strip()
            or type(operation_id) is not str or not operation_id.strip()
            or len(session_id) > 240 or len(operation_id) > 240):
        raise CampaignSourceStorageError("campaign_source_identity_invalid")
    return domain + "-" + role + "-" + hashlib.sha256(_json_dump(
        [domain, session_id, operation_id, role]).encode("utf-8")).hexdigest()


def input_operation_id(session_id: str, operation_id: str) -> str:
    return _control_id(INPUT_PROTOCOL, session_id, operation_id, "operation")


def input_attempt_id(session_id: str, operation_id: str) -> str:
    return _control_id(INPUT_PROTOCOL, session_id, operation_id, "attempt")


def preparation_operation_id(session_id: str, operation_id: str) -> str:
    return _control_id(PREPARATION_PROTOCOL, session_id, operation_id, "operation")


def preparation_attempt_id(session_id: str, operation_id: str) -> str:
    return _control_id(PREPARATION_PROTOCOL, session_id, operation_id, "attempt")


class CampaignSourceInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    protocol: Literal["campaign-source-input-v1"] = INPUT_PROTOCOL
    session_id: StrictStr
    operation_id: StrictStr
    player_input: StrictStr
    created_at: datetime
    snapshot: CampaignSourceSnapshot
    state: dict[str, Any]
    relationships: dict[str, Any]
    config: CampaignSourceConfig
    fingerprint_sha256: StrictStr

    @model_validator(mode="after")
    def valid(self) -> "CampaignSourceInputRequest":
        payload = self.model_dump(mode="json", exclude={"fingerprint_sha256"})
        if (self.session_id != self.snapshot.origin.scene_origin.session_id
                or self.created_at.utcoffset() is None
                or not self.operation_id or self.operation_id != self.operation_id.strip()
                or not self.player_input or self.player_input != self.player_input.strip()
                or self.state.get("campaign_progression") != self.snapshot.progression.model_dump(mode="json")
                or self.fingerprint_sha256 != _payload_hash(payload)):
            raise ValueError("campaign source input request mismatch")
        return self


@dataclass(frozen=True)
class CampaignSourceClaim:
    status: str
    newly_claimed: bool
    request: CampaignSourceInputRequest
    capsule: CampaignSourceCapsule | None = None
    error_code: str | None = None


def _new_request(session_id: str, operation_id: str, player_input: str,
                 snapshot: CampaignSourceSnapshot, state: dict, relationships: dict,
                 config: CampaignSourceConfig) -> CampaignSourceInputRequest:
    payload = dict(protocol=INPUT_PROTOCOL, session_id=session_id, operation_id=operation_id,
                   player_input=player_input, created_at=datetime.fromisoformat(_utc_now()),
                   snapshot=snapshot, state=state,
                   relationships=relationships, config=config)
    # Normalize the time in the same representation Pydantic persists.
    candidate = CampaignSourceInputRequest.model_construct(**payload, fingerprint_sha256="")
    raw = candidate.model_dump(mode="json", exclude={"fingerprint_sha256"})
    return CampaignSourceInputRequest.model_validate({**raw, "fingerprint_sha256": _payload_hash(raw)})


def _origin(connection: sqlite3.Connection, session_id: str) -> tuple[sqlite3.Row, CampaignSourceOrigin]:
    row = connection.execute("SELECT * FROM campaigns WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        raise CampaignSourceStorageError("campaign_source_campaign_missing")
    metadata = _json_load(row["metadata_json"], {})
    if type(metadata) is not dict or set(metadata) != {ORIGIN_KEY}:
        raise CampaignSourceStorageError("campaign_source_origin_invalid")
    try:
        origin = CampaignSourceOrigin.model_validate(metadata[ORIGIN_KEY])
        if origin.scene_origin.session_id != session_id:
            raise ValueError
        return row, origin
    except (ValueError, TypeError, AttributeError):
        raise CampaignSourceStorageError("campaign_source_origin_invalid") from None


def _capsule_row(connection: sqlite3.Connection, session_id: str,
                 operation_id: str) -> CampaignSourceCapsule:
    row = connection.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                             (session_id, preparation_operation_id(session_id, operation_id))).fetchone()
    if row is None:
        raise CampaignSourceStorageError("campaign_source_capsule_missing")
    try:
        metadata = _json_load(row["metadata_json"], {})
        capsule = CampaignSourceCapsule.model_validate(metadata[CAPSULE_KEY])
        expected_request = _payload_hash({"status": "completed", "capsule": metadata[CAPSULE_KEY]})
        if (set(metadata) != {CAPSULE_KEY} or capsule.session_id != session_id
                or capsule.operation_id != operation_id
                or row["status"] != "completed" or row["committed_turn_id"] is not None
                or row["attempt_id"] != preparation_attempt_id(session_id, operation_id)
                or row["user_input"] != capsule.player_input
                or row["requested_turn"] != capsule.snapshot.current_turn + 1
                or row["request_hash"] != expected_request
                or row["payload_hash"] != expected_request
                or row["result_hash"] != expected_request):
            raise ValueError
        return capsule
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise CampaignSourceStorageError("campaign_source_capsule_invalid") from None


def _input_row(connection: sqlite3.Connection, session_id: str,
               operation_id: str) -> tuple[sqlite3.Row, CampaignSourceInputRequest]:
    row = connection.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                             (session_id, input_operation_id(session_id, operation_id))).fetchone()
    if row is None:
        raise CampaignSourceStorageError("campaign_source_claim_missing")
    try:
        metadata = _json_load(row["metadata_json"], {})
        request = CampaignSourceInputRequest.model_validate(metadata[INPUT_KEY])
        request_hash = _payload_hash(request.model_dump(mode="json"))
        if (set(metadata) not in ({INPUT_KEY}, {INPUT_KEY, "completion"})
                or request.session_id != session_id or request.operation_id != operation_id
                or row["attempt_id"] != input_attempt_id(session_id, operation_id)
                or row["user_input"] != request.player_input
                or row["requested_turn"] != request.snapshot.current_turn + 1
                or row["request_hash"] != request_hash or row["payload_hash"] != request_hash
                or row["status"] not in {"pending", "completed", "failed", "cancelled", "timeout"}
                or row["committed_turn_id"] is not None):
            raise ValueError
        if row["status"] == "pending":
            if set(metadata) != {INPUT_KEY} or row["result_hash"] is not None:
                raise ValueError
        elif set(metadata) == {INPUT_KEY} and row["status"] == "cancelled":
            recovery_error = {"category": "cancelled", "code": "process_interrupted",
                              "safe_message": "The previous process ended before this operation completed."}
            if (_json_load(row["error_json"], {}) != recovery_error
                    or row["result_hash"] != _payload_hash({
                        "status": "cancelled", "requested_turn": row["requested_turn"],
                        "user_input": row["user_input"], "partial_narrative": "",
                        "error": recovery_error, "provenance": None, "usage": None,
                        "metadata": metadata,
                    })):
                raise ValueError
        else:
            completion = metadata.get("completion")
            if (type(completion) is not dict
                    or set(completion) != {"status", "capsule_sha256", "failure_code"}
                    or completion["status"] != row["status"]
                    or row["result_hash"] != _payload_hash({"status": row["status"],
                                                             "metadata": metadata})
                    or (row["status"] == "completed") != (completion["capsule_sha256"] is not None)
                    or (row["status"] == "completed") == (completion["failure_code"] is not None)):
                raise ValueError
        return row, request
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise CampaignSourceStorageError("campaign_source_claim_invalid") from None


def _h_chain(connection: sqlite3.Connection, session_id: str,
             original_operation_id: str, capsule: CampaignSourceCapsule) -> tuple[sqlite3.Row, ...]:
    rows = []
    for row in connection.execute("SELECT * FROM attempts WHERE session_id=? ORDER BY id",
                                  (session_id,)).fetchall():
        metadata = _json_load(row["metadata_json"], {})
        if (type(metadata) is dict and metadata.get("narrative_contract") == _H_PROTOCOL
                and metadata.get("original_operation_id") == original_operation_id):
            rows.append(row)
    previous = None
    for row in rows:
        metadata = _json_load(row["metadata_json"], {})
        try:
            expected = campaign_attempt_metadata(
                capsule, operation_id=row["operation_id"],
                invocation_id=metadata["expected_invocation_id"],
                resumes_operation_id=previous,
            )
            if (metadata != expected or row["user_input"] != capsule.player_input
                    or row["requested_turn"] != capsule.snapshot.current_turn + 1
                    or row["request_hash"] != _payload_hash(_attempt_request_payload(
                        row["requested_turn"], row["user_input"], metadata))
                    or row["payload_hash"] != row["request_hash"]
                    or previous is None and row["operation_id"] != original_operation_id
                    or previous is not None and row["operation_id"] == original_operation_id):
                raise ValueError
            status = row["status"]
            if status == "pending":
                if row["result_hash"] is not None or row["completed_at"] is not None:
                    raise ValueError
            elif status in {"failed", "timeout", "cancelled"}:
                if (row["committed_turn_id"] is not None
                        or row["completed_at"] is None
                        or row["partial_narrative"] != ""
                        or row["result_hash"] != _payload_hash({
                            "status": status,
                            "requested_turn": row["requested_turn"],
                            "user_input": row["user_input"],
                            "partial_narrative": row["partial_narrative"],
                            "error": _json_load(row["error_json"], None),
                            "provenance": _json_load(row["provenance_json"], None),
                            "usage": _json_load(row["usage_json"], None),
                            "metadata": metadata,
                        })):
                    raise ValueError
            elif status != "completed":
                raise ValueError
            previous = row["operation_id"]
        except (ValueError, TypeError, KeyError, AttributeError):
            raise CampaignSourceStorageError("campaign_source_h_chain_invalid") from None
    if any(row["status"] not in {"failed", "timeout", "cancelled"} for row in rows[:-1]):
        raise CampaignSourceStorageError("campaign_source_h_chain_invalid")
    return tuple(rows)


def _snapshot(connection: sqlite3.Connection, session_id: str) -> CampaignSourceSnapshot:
    campaign, origin = _origin(connection, session_id)
    progression = read_campaign_progress_state(
        _json_load(campaign["state_json"], {}).get("campaign_progression"))
    rows = connection.execute("SELECT * FROM turns WHERE session_id=? ORDER BY turn_number",
                              (session_id,)).fetchall()
    if (campaign["current_turn"] != len(rows)
            or campaign["state_revision"] != len(rows)
            or progression.revision != len(rows)):
        raise CampaignSourceStorageError("campaign_source_history_invalid")
    history, projections = [], []
    prior = type(progression)(revision=0)
    for number, row in enumerate(rows, 1):
        try:
            if row["turn_number"] != number or row["narrative_complete"] != 1:
                raise ValueError
            h = connection.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                                   (session_id, row["operation_id"])).fetchone()
            if (h is None or h["status"] != "completed"
                    or h["attempt_id"] != row["attempt_id"]
                    or h["committed_turn_id"] != row["turn_id"]
                    or h["result_hash"] != row["payload_hash"]
                    or h["provenance_json"] != row["provenance_json"]):
                raise ValueError
            metadata = _json_load(h["metadata_json"], {})
            if metadata.get("narrative_contract") != _H_PROTOCOL:
                raise ValueError
            original = metadata["original_operation_id"]
            capsule = _capsule_row(connection, session_id, original)
            chain = _h_chain(connection, session_id, original, capsule)
            if not chain or chain[-1]["operation_id"] != row["operation_id"]:
                raise ValueError
            p, request = _input_row(connection, session_id, original)
            p_metadata = _json_load(p["metadata_json"], {})
            if (p["status"] != "completed" or request.snapshot.progression != prior
                    or p_metadata["completion"]["capsule_sha256"] != capsule.fingerprint_sha256
                    or metadata != campaign_attempt_metadata(
                        capsule, operation_id=row["operation_id"],
                        invocation_id=metadata["expected_invocation_id"],
                        resumes_operation_id=metadata["resumes_operation_id"])
                    or capsule.snapshot.progression != prior
                    or capsule.snapshot.current_turn != number - 1
                    or capsule.draft.turn_id != row["turn_id"]
                    or capsule.campaign_effect.after_state.revision != number
                    or request.player_input != capsule.player_input
                    or capsule.snapshot.selected_turn_ids != tuple(history[-2:])
                    or capsule.snapshot.omitted_turn_ids != tuple(history[:-2])
                    or capsule.snapshot.sources != tuple(projections[-2:])
                    or _json_dump(request.state) != _json_dump(capsule.state)
                    or _json_dump(request.relationships) != _json_dump(capsule.relationships)):
                raise ValueError
            context = _json_load(row["context_json"], {})
            if type(context) is not dict or set(context) != {CONTEXT_KEY, "campaign_source_context"}:
                raise ValueError
            expected_selection = capsule.snapshot.audit_payload()
            if context["campaign_source_context"] != expected_selection:
                raise ValueError
            narrative = _json_load(row["narrative_json"], {})
            events = [_json_load(item["payload_json"], {}) for item in connection.execute(
                "SELECT payload_json FROM events WHERE session_id=? AND turn_id=? ORDER BY sequence",
                (session_id, row["turn_id"])).fetchall()]
            envelope = validate_campaign_source_turn_commit(
                capsule=capsule, envelope=context[CONTEXT_KEY], narrative=narrative,
                operation_id=row["operation_id"], attempt_id=row["attempt_id"],
                expected_invocation_id=metadata["expected_invocation_id"],
                provenance=_json_load(row["provenance_json"], {}),
                facts=_json_load(row["facts_json"], []), events=events,
            )
            after_state = dict(capsule.state)
            after_state["campaign_progression"] = capsule.campaign_effect.after_state.model_dump(mode="json")
            persisted_state = _json_load(row["state_json"], {})
            persisted_facts = _json_load(row["facts_json"], [])
            persisted_relationships = _json_load(row["relationships_json"], {})
            persisted_provenance = _json_load(row["provenance_json"], None)
            persisted_usage = _json_load(row["usage_json"], None)
            digest = _payload_hash({
                "turn_id": row["turn_id"], "state": persisted_state,
                "narrative": narrative, "facts": persisted_facts, "events": events,
                "memory_candidates": [], "episodic_memories": [],
                "relationships": persisted_relationships, "context": context,
                "provenance": persisted_provenance, "usage": persisted_usage,
                "user_input": row["user_input"], "requested_turn": number,
                "base_revision": number - 1, "base_state_revision": number - 1,
            })
            if (_json_dump(_json_load(row["state_json"], {})) != _json_dump(after_state)
                    or row["narrative_text"] != narrative.get("text")
                    or row["payload_hash"] != digest):
                raise ValueError
            prior = capsule.campaign_effect.after_state
            history.append(row["turn_id"])
            projections.append(envelope.projection)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            raise CampaignSourceStorageError("campaign_source_history_invalid") from None
    if prior != progression:
        raise CampaignSourceStorageError("campaign_source_history_invalid")
    return CampaignSourceSnapshot(
        origin=origin, current_turn=len(rows), state_revision=campaign["state_revision"],
        progression=progression, sources=tuple(projections[-2:]),
        selected_turn_ids=tuple(history[-2:]), omitted_turn_ids=tuple(history[:-2]),
    )


async def create_campaign_source_session(store: SQLitePersistence, session_id: str, *,
                                         initial_state: dict[str, Any],
                                         relationships: dict[str, Any] | None = None,
                                         chronicle_name: str = "") -> CampaignSourceSnapshot:
    await store.initialize()
    origin = create_campaign_source_origin(create_source_context_origin(
        session_id, SceneState(location="Arquivo", npcs_present=("Mara",))))
    state = json.loads(_json_dump(initial_state))
    if "campaign_progression" in state:
        raise CampaignSourceStorageError("campaign_source_initial_state_invalid")
    validate_source_state_context(state, origin.scene_origin)
    state["campaign_progression"] = CampaignProgressState(revision=0).model_dump(mode="json")
    relations = json.loads(_json_dump(relationships or {}))
    def create():
        with store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM campaigns WHERE session_id=?", (session_id,)).fetchone():
                raise CampaignSourceStorageError("campaign_source_campaign_exists")
            for table in ("attempts", "turns", "events", "memory_candidates",
                          "episodic_memories", "consolidations", "legacy_imports"):
                if connection.execute(f"SELECT 1 FROM {table} WHERE session_id=? LIMIT 1",
                                      (session_id,)).fetchone():
                    raise CampaignSourceStorageError("campaign_source_history_invalid")
            store._insert_campaign_if_missing(connection, session_id, chronicle_name,
                                              state, relations, {ORIGIN_KEY: origin.model_dump(mode="json")})
            result = _snapshot(connection, session_id)
            connection.commit()
            return result
    return await asyncio.to_thread(create)


async def read_campaign_source_snapshot(store: SQLitePersistence,
                                        session_id: str) -> CampaignSourceSnapshot:
    await store.initialize()
    def read():
        with store._connect() as connection:
            connection.execute("BEGIN")
            return _snapshot(connection, session_id)
    return await asyncio.to_thread(read)


async def claim_campaign_source_input(
    store: SQLitePersistence, *, session_id: str, operation_id: str,
    player_input: str, config: CampaignSourceConfig,
) -> CampaignSourceClaim:
    """Only newly_claimed authorizes classification and at most one RNG call."""
    await store.initialize()
    input_operation_id(session_id, operation_id)
    if (type(player_input) is not str or not player_input.strip()
            or player_input != player_input.strip() or len(player_input) > 500):
        raise CampaignSourceStorageError("campaign_source_input_invalid")
    checked_config = CampaignSourceConfig.model_validate(config)

    def claim():
        with store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = _snapshot(connection, session_id)
            row = connection.execute("SELECT 1 FROM attempts WHERE session_id=? AND operation_id=?",
                                     (session_id, input_operation_id(session_id, operation_id))).fetchone()
            if row is not None:
                previous, request = _input_row(connection, session_id, operation_id)
                if (request.player_input != player_input or request.config != checked_config):
                    raise CampaignSourceStorageError("campaign_source_operation_conflict")
                capsule = (_capsule_row(connection, session_id, operation_id)
                           if previous["status"] == "completed" else None)
                return CampaignSourceClaim(previous["status"], False, request, capsule,
                                           _json_load(previous["error_json"], {}).get("code")
                                           if previous["error_json"] else None)
            if current.progression.outcome is not None:
                raise CampaignSourceStorageError("campaign_source_campaign_ended")
            if connection.execute("SELECT 1 FROM attempts WHERE session_id=? AND operation_id=?",
                                  (session_id, operation_id)).fetchone():
                raise CampaignSourceStorageError("campaign_source_operation_conflict")
            for candidate in connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id LIKE ?",
                    (session_id, INPUT_PROTOCOL + "-operation-%")).fetchall():
                metadata = _json_load(candidate["metadata_json"], {})
                if INPUT_KEY not in metadata:
                    raise CampaignSourceStorageError("campaign_source_claim_invalid")
                original = CampaignSourceInputRequest.model_validate(metadata[INPUT_KEY])
                _input_row(connection, session_id, original.operation_id)
                if candidate["status"] == "pending":
                    raise CampaignSourceStorageError("campaign_source_session_busy")
                if candidate["status"] == "completed":
                    stored = _capsule_row(connection, session_id, original.operation_id)
                    chain = _h_chain(connection, session_id, original.operation_id, stored)
                    if not chain or chain[-1]["status"] != "completed":
                        raise CampaignSourceStorageError("campaign_source_session_busy")
            campaign, _ = _origin(connection, session_id)
            request = _new_request(
                session_id, operation_id, player_input, current,
                _json_load(campaign["state_json"], {}),
                _json_load(campaign["relationships_json"], {}), checked_config,
            )
            digest = _payload_hash(request.model_dump(mode="json"))
            connection.execute(
                """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,
                    user_input,metadata_json,payload_hash,request_hash,result_hash,started_at)
                   VALUES(?,?,?,?,'pending',?,?,?,?,NULL,?)""",
                (input_attempt_id(session_id, operation_id), session_id,
                 input_operation_id(session_id, operation_id), current.current_turn + 1,
                 player_input, _json_dump({INPUT_KEY: request.model_dump(mode="json")}),
                 digest, digest, request.created_at.isoformat()),
            )
            connection.commit()
            return CampaignSourceClaim("pending", True, request)
    return await asyncio.to_thread(claim)


async def finalize_campaign_source_input(
    store: SQLitePersistence, *, session_id: str, operation_id: str,
    request_sha256: str, capsule: CampaignSourceCapsule | None = None,
    failure_code: str | None = None,
) -> CampaignSourceClaim:
    """Persist the original K with P in one transaction, or a closed P failure."""
    if (capsule is None) == (failure_code is None):
        raise CampaignSourceStorageError("campaign_source_completion_invalid")
    if failure_code is not None and failure_code not in {
        "campaign_source_out_of_scope", "campaign_source_clarification_required",
        "campaign_source_gate_blocked", "campaign_source_cancelled",
        "campaign_source_deadline_exceeded", "campaign_source_production_failed",
        "campaign_source_base_mismatch",
    }:
        raise CampaignSourceStorageError("campaign_source_completion_invalid")
    retained = CampaignSourceCapsule.model_validate(capsule) if capsule is not None else None
    def finalize():
        local_capsule = retained
        local_failure = failure_code
        with store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row, request = _input_row(connection, session_id, operation_id)
            if request.fingerprint_sha256 != request_sha256:
                raise CampaignSourceStorageError("campaign_source_operation_conflict")
            if row["status"] != "pending":
                stored = _capsule_row(connection, session_id, operation_id) if row["status"] == "completed" else None
                if (stored != local_capsule or (local_failure is None) != (row["status"] == "completed")):
                    raise CampaignSourceStorageError("campaign_source_operation_conflict")
                return CampaignSourceClaim(row["status"], False, request, stored,
                                           _json_load(row["error_json"], {}).get("code")
                                           if row["error_json"] else None)
            status = "completed" if local_capsule is not None else "failed"
            current = _snapshot(connection, session_id)
            if local_capsule is not None:
                if (local_capsule.snapshot != request.snapshot or local_capsule.operation_id != operation_id
                        or local_capsule.player_input != request.player_input
                        or local_capsule.created_at != request.created_at
                        or local_capsule.config != request.config
                        or _json_dump(local_capsule.state) != _json_dump(request.state)
                        or _json_dump(local_capsule.relationships) != _json_dump(request.relationships)):
                    raise CampaignSourceStorageError("campaign_source_capsule_invalid")
                if current != request.snapshot:
                    local_capsule = None
                    local_failure = "campaign_source_base_mismatch"
                    status = "failed"
            now = _utc_now()
            if local_capsule is not None:
                metadata = {CAPSULE_KEY: local_capsule.model_dump(mode="json")}
                digest = _payload_hash({"status": "completed", "capsule": metadata[CAPSULE_KEY]})
                connection.execute(
                    """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,
                        user_input,partial_narrative,metadata_json,payload_hash,request_hash,
                        result_hash,started_at,completed_at)
                       VALUES(?,?,?,?,'completed',?,'',?,?,?,?,?,?)""",
                    (preparation_attempt_id(session_id, operation_id), session_id,
                     preparation_operation_id(session_id, operation_id), current.current_turn + 1,
                     request.player_input, _json_dump(metadata), digest, digest, digest, now, now),
                )
            completion = {"status": status, "capsule_sha256": local_capsule.fingerprint_sha256
                          if local_capsule is not None else None, "failure_code": local_failure}
            metadata = {INPUT_KEY: request.model_dump(mode="json"), "completion": completion}
            result = _payload_hash({"status": status, "metadata": metadata})
            connection.execute(
                """UPDATE attempts SET status=?,metadata_json=?,error_json=?,result_hash=?,completed_at=?
                   WHERE id=? AND status='pending'""",
                (status, _json_dump(metadata), _json_dump({"code": local_failure}) if local_failure else None,
                 result, now, row["id"]),
            )
            connection.commit()
            return CampaignSourceClaim(status, False, request, local_capsule, local_failure)
    return await asyncio.to_thread(finalize)


@dataclass(frozen=True)
class CampaignNarrativeClaim:
    status: str
    newly_claimed: bool
    operation_id: str
    attempt_id: str
    invocation_id: str


@dataclass(frozen=True)
class CampaignSourceStatus:
    operation_id: str
    preparation_status: str
    narrative_status: str
    latest_narrative_operation_id: str | None
    resume_from_operation_id: str | None
    current_turn: int
    state_revision: int
    outcome: str | None
    error_code: str | None


async def read_campaign_source_status(
    store: SQLitePersistence, session_id: str, operation_id: str,
) -> CampaignSourceStatus | None:
    """Safe reconnect projection; no capsule, prompt, receipt or provider secrets."""
    await store.initialize()
    input_operation_id(session_id, operation_id)
    def read():
        with store._connect() as connection:
            connection.execute("BEGIN")
            current = _snapshot(connection, session_id)
            row = connection.execute(
                "SELECT 1 FROM attempts WHERE session_id=? AND operation_id=?",
                (session_id, input_operation_id(session_id, operation_id)),
            ).fetchone()
            if row is None:
                if connection.execute(
                    "SELECT 1 FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, preparation_operation_id(session_id, operation_id)),
                ).fetchone():
                    raise CampaignSourceStorageError("campaign_source_orphan_preparation")
                return None
            p, request = _input_row(connection, session_id, operation_id)
            capsule = _capsule_row(connection, session_id, operation_id) if p["status"] == "completed" else None
            chain = _h_chain(connection, session_id, operation_id, capsule) if capsule else ()
            if capsule and request.snapshot != capsule.snapshot:
                raise CampaignSourceStorageError("campaign_source_capsule_invalid")
            latest = chain[-1] if chain else None
            h_status = latest["status"] if latest else "retained_unstarted" if capsule else "not_started"
            error = _json_load(latest["error_json"], {}) if latest and latest["error_json"] else (
                _json_load(p["error_json"], {}) if p["error_json"] else {})
            if type(error) is not dict:
                raise CampaignSourceStorageError("campaign_source_status_invalid")
            return CampaignSourceStatus(
                operation_id=operation_id, preparation_status=p["status"],
                narrative_status=h_status,
                latest_narrative_operation_id=latest["operation_id"] if latest else None,
                resume_from_operation_id=(latest["operation_id"] if latest and
                                          latest["status"] in {"failed", "timeout", "cancelled"}
                                          else None),
                current_turn=current.current_turn, state_revision=current.state_revision,
                outcome=current.progression.outcome,
                error_code=error.get("code") if type(error.get("code")) is str else None,
            )
    return await asyncio.to_thread(read)


async def load_campaign_source_capsule(
    store: SQLitePersistence, session_id: str, operation_id: str,
) -> CampaignSourceCapsule:
    """Internal reconstruction after restart; never serialize this to a client."""
    await store.initialize()
    def read():
        with store._connect() as connection:
            connection.execute("BEGIN")
            current = _snapshot(connection, session_id)
            p, request = _input_row(connection, session_id, operation_id)
            if p["status"] != "completed":
                raise CampaignSourceStorageError("campaign_source_capsule_missing")
            capsule = _capsule_row(connection, session_id, operation_id)
            if (request.snapshot != capsule.snapshot
                    or current.current_turn == capsule.snapshot.current_turn
                    and current != capsule.snapshot):
                raise CampaignSourceStorageError("campaign_source_capsule_invalid")
            return capsule
    return await asyncio.to_thread(read)


async def claim_campaign_narrative(
    store: SQLitePersistence, *, capsule: CampaignSourceCapsule,
    operation_id: str, resumes_operation_id: str | None = None,
) -> CampaignNarrativeClaim:
    """Reserve one H, or one explicit new H linked to a terminal failed H."""
    retained = CampaignSourceCapsule.model_validate(capsule)
    input_operation_id(retained.session_id, operation_id)
    if resumes_operation_id is not None:
        input_operation_id(retained.session_id, resumes_operation_id)
    from uuid import NAMESPACE_URL, uuid5
    invocation_id = str(uuid5(NAMESPACE_URL, _json_dump(
        [_H_PROTOCOL, retained.session_id, operation_id])))
    attempt_id = (retained.draft.attempt_id if operation_id == retained.operation_id
                  else _control_id("campaign-narrative-resume-v1", retained.session_id,
                                   operation_id, "attempt"))
    metadata = campaign_attempt_metadata(
        retained, operation_id=operation_id, invocation_id=invocation_id,
        resumes_operation_id=resumes_operation_id,
    )
    def claim():
        with store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = _snapshot(connection, retained.session_id)
            stored = _capsule_row(connection, retained.session_id, retained.operation_id)
            p, request = _input_row(connection, retained.session_id, retained.operation_id)
            if (stored != retained or p["status"] != "completed"
                    or request.snapshot != retained.snapshot):
                raise CampaignSourceStorageError("campaign_source_capsule_invalid")
            existing = connection.execute(
                "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                (retained.session_id, operation_id),
            ).fetchone()
            digest = _payload_hash(_attempt_request_payload(
                retained.draft.base_revision + 1, retained.player_input, metadata))
            if existing is not None:
                if (existing["attempt_id"] != attempt_id or existing["request_hash"] != digest
                        or _json_load(existing["metadata_json"], {}) != metadata):
                    raise CampaignSourceStorageError("campaign_source_operation_conflict")
                return CampaignNarrativeClaim(existing["status"], False, operation_id,
                                              attempt_id, invocation_id)
            if current != retained.snapshot:
                raise CampaignSourceStorageError("campaign_source_base_mismatch")
            h_rows = _h_chain(connection, retained.session_id, retained.operation_id, retained)
            if not h_rows:
                if operation_id != retained.operation_id or resumes_operation_id is not None:
                    raise CampaignSourceStorageError("campaign_source_resume_link_invalid")
            else:
                if (h_rows[-1]["status"] not in {"failed", "timeout", "cancelled"}
                        or resumes_operation_id != h_rows[-1]["operation_id"]
                        or operation_id == retained.operation_id):
                    raise CampaignSourceStorageError("campaign_source_session_busy")
            connection.execute(
                """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,
                    user_input,metadata_json,payload_hash,request_hash,result_hash,started_at)
                   VALUES(?,?,?,?,'pending',?,?,?,?,NULL,?)""",
                (attempt_id, retained.session_id, operation_id,
                 retained.draft.base_revision + 1, retained.player_input,
                 _json_dump(metadata), digest, digest, _utc_now()),
            )
            connection.commit()
            return CampaignNarrativeClaim("pending", True, operation_id, attempt_id,
                                          invocation_id)
    return await asyncio.to_thread(claim)


def validate_campaign_commit_in_connection(
    connection: sqlite3.Connection, *, session_id: str, operation_id: str,
    attempt_id: str, turn_id: str, narrative_contract: str | None,
    requested_turn: int | None, base_revision: int | None,
    base_state_revision: int | None, user_input: str, state: object,
    relationships: object, context: object, narrative: object,
    facts: object, events: object, memory_candidates: object,
    episodic_memories: object, provenance: object,
) -> None:
    """Enforce P/K/H and exact campaign delta under the commit transaction."""
    campaign = connection.execute("SELECT * FROM campaigns WHERE session_id=?",
                                  (session_id,)).fetchone()
    metadata = _json_load(campaign["metadata_json"], {}) if campaign else {}
    h = connection.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                           (session_id, operation_id)).fetchone()
    h_metadata = _json_load(h["metadata_json"], {}) if h else {}
    present = (ORIGIN_KEY in metadata or narrative_contract == _H_PROTOCOL
               or h_metadata.get("narrative_contract") == _H_PROTOCOL
               or type(context) is dict and (CONTEXT_KEY in context or "campaign_source_context" in context))
    if not present:
        return
    if (narrative_contract != _H_PROTOCOL or ORIGIN_KEY not in metadata
            or type(context) is not dict
            or set(context) != {CONTEXT_KEY, "campaign_source_context"}
            or h is None or h["status"] not in {"pending", "completed"}):
        raise CampaignSourceStorageError("campaign_source_commit_contract_required")
    try:
        original = h_metadata["original_operation_id"]
        capsule = _capsule_row(connection, session_id, original)
        p, request = _input_row(connection, session_id, original)
        p_metadata = _json_load(p["metadata_json"], {})
        draft = capsule.draft
        expected_state = dict(capsule.state)
        expected_state["campaign_progression"] = capsule.campaign_effect.after_state.model_dump(mode="json")
        if (p["status"] != "completed"
                or p_metadata["completion"]["capsule_sha256"] != capsule.fingerprint_sha256
                or request.snapshot != capsule.snapshot
                or request.config != capsule.config
                or h_metadata != campaign_attempt_metadata(
                    capsule, operation_id=operation_id,
                    invocation_id=h_metadata["expected_invocation_id"],
                    resumes_operation_id=h_metadata["resumes_operation_id"])
                or h["attempt_id"] != attempt_id
                or h["user_input"] != user_input
                or h["requested_turn"] != requested_turn
                or user_input != capsule.player_input
                or turn_id != draft.turn_id
                or base_revision != draft.base_revision
                or base_state_revision != draft.base_state_revision
                or requested_turn != draft.base_revision + 1
                or context["campaign_source_context"] != capsule.snapshot.audit_payload()
                or _json_dump(state) != _json_dump(expected_state)
                or _json_dump(relationships) != _json_dump(capsule.relationships)):
            raise ValueError
        # A new H must still face the exact campaign base; replay validates the
        # stored terminal pair separately and never reapplies the delta.
        if h["status"] == "pending":
            current = _snapshot(connection, session_id)
            stored = _json_load(campaign["state_json"], {})
            if (current != capsule.snapshot or _json_dump(stored) != _json_dump(capsule.state)):
                raise ValueError
        validate_campaign_source_turn_commit(
            capsule=capsule, envelope=context[CONTEXT_KEY], narrative=narrative,
            provenance=provenance, operation_id=operation_id,
            attempt_id=attempt_id,
            expected_invocation_id=h_metadata["expected_invocation_id"],
            facts=facts, events=events, memory_candidates=memory_candidates,
            episodic_memories=episodic_memories,
        )
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        raise CampaignSourceStorageError("campaign_source_commit_mismatch") from None
