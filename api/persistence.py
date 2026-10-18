"""Transactional local persistence for campaigns, turns, and derived memory.

The module deliberately uses only the Python standard-library SQLite driver.
All public operations open their own connection and blocking work is moved to a
worker thread.  Per-session asyncio locks make read/modify/write operations
deterministic in the application's single-process deployment; SQLite's
``BEGIN IMMEDIATE`` remains the cross-connection serialization boundary.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import math
import os
import re
import sqlite3
import threading
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable


if TYPE_CHECKING:
    from .turn_models import NarrationResumeCapsule, NarratorAvailabilityGate
    from .narrative_source_turn import NarrativeSourceTurnEnvelope
    from .narrative_source_context import SourceContextSnapshot
    from .narrative_source_capsule import SourceTurnCapsule
    from .narrative_source_status import SourceOperationSnapshot
    from .narrative_source_observation import SourcePlayerObservation
    from .narrative_source_entry import SourcePlayerActionRequest
    from .narrative_source_input import (
        SourceProducerConfig, SourceInputRequest, SourceInputCompletion, SourceInputClaim,
    )
    from .narrative_source_setup import SourceSetupManifest
    from .scene_service import SceneState


SCHEMA_VERSION = 4
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "saves" / "storyteller.sqlite3"
_SAFE_LEGACY_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_TERMINAL_FAILURE_STATUSES = frozenset({"failed", "cancelled", "timeout"})
_FINAL_CANDIDATE_STATUSES = frozenset({"accepted", "rejected"})
_VISIBILITY_RESTRICTION = {
    "public": 0,
    "player": 1,
    "storyteller": 2,
    "system": 3,
}

_SCHEMA_COLUMNS_V3: dict[str, frozenset[str]] = {
    "schema_meta": frozenset({"key", "value"}),
    "campaigns": frozenset(
        {
            "session_id",
            "chronicle_name",
            "schema_version",
            "current_turn",
            "state_revision",
            "state_json",
            "relationships_json",
            "metadata_json",
            "created_at",
            "updated_at",
        }
    ),
    "attempts": frozenset(
        {
            "id",
            "attempt_id",
            "session_id",
            "operation_id",
            "requested_turn",
            "status",
            "user_input",
            "partial_narrative",
            "error_json",
            "provenance_json",
            "usage_json",
            "metadata_json",
            "payload_hash",
            "request_hash",
            "result_hash",
            "committed_turn_id",
            "started_at",
            "completed_at",
        }
    ),
    "turns": frozenset(
        {
            "id",
            "turn_id",
            "session_id",
            "operation_id",
            "attempt_id",
            "turn_number",
            "user_input",
            "narrative_text",
            "narrative_complete",
            "narrative_json",
            "facts_json",
            "context_json",
            "state_json",
            "relationships_json",
            "provenance_json",
            "usage_json",
            "payload_hash",
            "committed_at",
        }
    ),
    "events": frozenset(
        {
            "id",
            "event_id",
            "session_id",
            "turn_id",
            "turn_number",
            "sequence",
            "event_type",
            "summary",
            "fact_ids_json",
            "tags_json",
            "actors_json",
            "place_json",
            "importance",
            "visibility",
            "references_json",
            "pending",
            "occurred_at",
            "payload_json",
            "schema_version",
        }
    ),
    "memory_candidates": frozenset(
        {
            "id",
            "candidate_id",
            "session_id",
            "turn_id",
            "turn_number",
            "summary",
            "source_event_ids_json",
            "tags_json",
            "actors_json",
            "place_json",
            "occurred_at",
            "importance",
            "visibility",
            "pending",
            "proposed_by",
            "validation_status",
            "validation_notes_json",
            "payload_json",
            "schema_version",
            "created_at",
        }
    ),
    "episodic_memories": frozenset(
        {
            "id",
            "memory_id",
            "session_id",
            "turn_id",
            "turn_number",
            "summary",
            "source_event_ids_json",
            "tags_json",
            "actors_json",
            "place_json",
            "occurred_at",
            "importance",
            "visibility",
            "pending",
            "version",
            "payload_json",
            "schema_version",
            "created_at",
        }
    ),
    "consolidations": frozenset(
        {
            "id",
            "consolidation_id",
            "session_id",
            "scope",
            "version",
            "summary",
            "source_memory_ids_json",
            "source_event_ids_json",
            "tags_json",
            "visibility",
            "supersedes_consolidation_id",
            "payload_json",
            "schema_version",
            "created_at",
        }
    ),
    "legacy_imports": frozenset(
        {
            "id",
            "session_id",
            "source_kind",
            "source_path",
            "content_fingerprint",
            "content_sha256",
            "raw_bytes",
            "parse_status",
            "parse_error",
            "parsed_json",
            "audited_at",
            "applied_at",
        }
    ),
    "narration_resume_capsules": frozenset(
        {
            "capsule_id", "session_id", "source_operation_id", "source_attempt_id",
            "resume_operation_id", "state", "state_revision", "payload_json",
            "payload_hash", "created_at", "updated_at", "completed_at",
        }
    ),
    "narrator_availability_gates": frozenset(
        {
            "gate_id", "session_id", "scope", "scope_key", "target_json", "state",
            "payload_json", "observed_at", "retry_not_before", "lease_operation_id",
            "updated_at",
        }
    ),
}

# These uniqueness guarantees are part of the repository contract.  Merely
# finding the expected column names is not enough: an old partial table could
# otherwise survive CREATE TABLE IF NOT EXISTS and be marked current.
_SCHEMA_UNIQUES: dict[str, frozenset[frozenset[str]]] = {
    "schema_meta": frozenset({frozenset({"key"})}),
    "campaigns": frozenset({frozenset({"session_id"})}),
    "attempts": frozenset(
        {
            frozenset({"attempt_id"}),
            frozenset({"session_id", "operation_id"}),
        }
    ),
    "turns": frozenset(
        {
            frozenset({"turn_id"}),
            frozenset({"session_id", "operation_id"}),
            frozenset({"session_id", "turn_number"}),
        }
    ),
    "events": frozenset(
        {
            frozenset({"event_id"}),
            frozenset({"turn_id", "sequence"}),
        }
    ),
    "memory_candidates": frozenset({frozenset({"candidate_id"})}),
    "episodic_memories": frozenset({frozenset({"memory_id"})}),
    "consolidations": frozenset(
        {
            frozenset({"consolidation_id"}),
            frozenset({"session_id", "scope", "version"}),
        }
    ),
    "legacy_imports": frozenset(
        {frozenset({"session_id", "source_kind", "content_fingerprint"})}
    ),
    "narration_resume_capsules": frozenset(
        {frozenset({"capsule_id"}), frozenset({"session_id", "source_operation_id"}),
         frozenset({"session_id", "resume_operation_id"})}
    ),
    "narrator_availability_gates": frozenset(
        {frozenset({"gate_id"}), frozenset({"session_id", "scope", "scope_key"})}
    ),
}

_SCHEMA_FOREIGN_KEYS: dict[str, frozenset[tuple[str, str, str, str]]] = {
    "attempts": frozenset(
        {("session_id", "campaigns", "session_id", "CASCADE")}
    ),
    "turns": frozenset(
        {
            ("session_id", "campaigns", "session_id", "CASCADE"),
            ("attempt_id", "attempts", "attempt_id", "NO ACTION"),
        }
    ),
    "events": frozenset(
        {
            ("session_id", "campaigns", "session_id", "CASCADE"),
            ("turn_id", "turns", "turn_id", "CASCADE"),
        }
    ),
    "memory_candidates": frozenset(
        {
            ("session_id", "campaigns", "session_id", "CASCADE"),
            ("turn_id", "turns", "turn_id", "CASCADE"),
        }
    ),
    "episodic_memories": frozenset(
        {
            ("session_id", "campaigns", "session_id", "CASCADE"),
            ("turn_id", "turns", "turn_id", "SET NULL"),
        }
    ),
    "consolidations": frozenset(
        {
            ("session_id", "campaigns", "session_id", "CASCADE"),
            (
                "supersedes_consolidation_id",
                "consolidations",
                "consolidation_id",
                "NO ACTION",
            ),
        }
    ),
    "narration_resume_capsules": frozenset(
        {("session_id", "campaigns", "session_id", "CASCADE"),
         ("source_attempt_id", "attempts", "attempt_id", "NO ACTION")}
    ),
    "narrator_availability_gates": frozenset(
        {("session_id", "campaigns", "session_id", "CASCADE")}
    ),
}

_SCHEMA_CHECKS_V3: dict[str, frozenset[str]] = {
    "campaigns": frozenset(
        {"check(current_turn>=0)", "check(state_revision>=0)"}
    ),
    "attempts": frozenset(
        {
            "check(statusin('pending','completed','failed','cancelled','timeout'))"
        }
    ),
    "turns": frozenset(
        {"check(turn_number>0)", "check(narrative_completein(0,1))"}
    ),
    "events": frozenset(
        {"check(sequence>=0)", "check(pendingin(0,1))"}
    ),
    "memory_candidates": frozenset({"check(pendingin(0,1))"}),
    "episodic_memories": frozenset(
        {"check(pendingin(0,1))", "check(version>0)"}
    ),
    "consolidations": frozenset({"check(version>0)"}),
    "legacy_imports": frozenset(
        {"check(parse_statusin('missing','valid','corrupt'))"}
    ),
    "narration_resume_capsules": frozenset(
        {"check(statein('paused','direct_resume_trial','completed','abandoned'))",
         "check(state_revision>=0)"}
    ),
}


class PersistenceError(RuntimeError):
    """Base class for persistence failures exposed to application code."""


class SchemaVersionError(PersistenceError):
    """The database schema is newer than this application understands."""


class IdempotencyConflictError(PersistenceError):
    """An operation id was reused for a different payload or terminal state."""


class TurnSequenceError(PersistenceError):
    """A requested turn is not the next monotonic turn for the campaign."""


class StateRevisionError(PersistenceError):
    """A control snapshot was based on a stale campaign state revision."""


class ConsolidationVersionError(PersistenceError):
    """A consolidation version is not the next version for its scope."""


class LegacyMigrationError(PersistenceError):
    """Base class for non-destructive legacy import failures."""


class LegacyCorruptionError(LegacyMigrationError):
    def __init__(self, session_id: str, sources: Sequence[str]):
        self.session_id = session_id
        self.sources = tuple(sources)
        super().__init__(
            f"Legacy session {session_id!r} contains corrupt JSON: {', '.join(self.sources)}"
        )


class LegacySourceChangedError(LegacyMigrationError):
    def __init__(self, session_id: str, source_kind: str):
        self.session_id = session_id
        self.source_kind = source_kind
        super().__init__(
            f"Legacy source {source_kind!r} for {session_id!r} changed after it was audited"
        )


class LegacyStateRequiredError(LegacyMigrationError):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Legacy session {session_id!r} has memory or relationships but no state snapshot"
        )


@dataclasses.dataclass(frozen=True)
class CommitResult:
    session_id: str
    operation_id: str
    turn_id: str
    turn_number: int
    idempotent: bool = False


@dataclasses.dataclass(frozen=True)
class AttemptResult:
    session_id: str
    operation_id: str
    attempt_id: str
    status: str
    idempotent: bool = False
    state_revision: int | None = None


@dataclasses.dataclass(frozen=True)
class ConsolidationResult:
    session_id: str
    consolidation_id: str
    scope: str
    version: int
    idempotent: bool = False


@dataclasses.dataclass(frozen=True)
class LegacyMigrationResult:
    session_id: str
    status: str
    imported: bool
    idempotent: bool
    current_turn: int
    imported_memories: int = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plain(value: Any) -> Any:
    """Convert Pydantic/dataclass/domain objects into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _plain(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        try:
            return _plain(value.model_dump(mode="json"))
        except TypeError:
            return _plain(value.model_dump())
    if dataclasses.is_dataclass(value):
        return _plain(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    raise TypeError(f"Unsupported persistence value: {type(value).__name__}")


def _json_dump(value: Any) -> str:
    return json.dumps(_plain(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_load(value: str | None, default: Any) -> Any:
    return default if value is None else json.loads(value)


def _payload_hash(value: Any) -> str:
    return hashlib.sha256(_json_dump(value).encode("utf-8")).hexdigest()


def _attempt_request_payload(
    requested_turn: int | None,
    user_input: str,
    metadata: Any = None,
) -> dict[str, Any]:
    """Canonical data that identifies one immutable attempt request."""

    return {
        "requested_turn": requested_turn,
        "user_input": user_input,
        "metadata": metadata or {},
    }


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _required_text(value: Any, name: str) -> str:
    result = _field(value, name)
    if result is None or not str(result).strip():
        raise ValueError(f"{name} is required")
    return str(result)


def _id_sequence(value: Any, name: str, *, required: bool) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence of ids")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{name} must contain non-empty normalized string ids")
        result.append(item)
    if required and not result:
        raise ValueError(f"{name} must contain at least one id")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicate ids")
    return tuple(result)


def _visibility(value: Any, field_name: str) -> str:
    normalized = _normalize_visibility(value)
    if normalized not in _VISIBILITY_RESTRICTION:
        raise ValueError(f"{field_name} has unsupported visibility {normalized!r}")
    return normalized


def _derived_memory_key(record: Mapping[str, Any]) -> str:
    """Fields copied verbatim by promote_memory_candidate."""
    return _json_dump(
        {
            "created_at": record.get("created_at"),
            "summary": record.get("summary"),
            "source_event_ids": record.get("source_event_ids", []),
            "tags": record.get("tags", []),
            "actors": record.get("actors", []),
            "place": record.get("place"),
            "occurred_at": record.get("occurred_at"),
            "importance": record.get("importance", 0),
            "visibility": record.get("visibility"),
            "pending": bool(record.get("pending", False)),
        }
    )


def _mapping_payloads(values: Sequence[Any], label: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for value in values:
        payload = _plain(value)
        if not isinstance(payload, Mapping):
            raise ValueError(f"Each {label} must be an object")
        result.append(dict(payload))
    return result


def _normalize_visibility(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if value is None:
        return "player"
    return str(value)


def _decode_row(row: sqlite3.Row, json_columns: Sequence[str]) -> dict[str, Any]:
    result = dict(row)
    for column in json_columns:
        if column in result:
            result[column.removesuffix("_json")] = _json_load(result.pop(column), None)
    for column in ("pending", "narrative_complete"):
        if column in result and result[column] is not None:
            result[column] = bool(result[column])
    return result


def _validate_narrative_source_obligation(
    *, narrative_contract: str | None, attempt: Mapping[str, Any] | None,
    context: Any, narrative: Any, session_id: str, operation_id: str,
    turn_id: str, attempt_id: str, requested_turn: int | None, user_input: str,
    facts: Sequence[Any], events: Sequence[Any], memory_candidates: Sequence[Any],
    episodic_memories: Sequence[Any], provenance: Any,
) -> Any:
    """Keep the server's reserved source obligation independent of context."""
    metadata = _json_load(attempt["metadata_json"], {}) if attempt is not None else {}
    has_marker = isinstance(metadata, Mapping) and "narrative_contract" in metadata
    has_envelope = isinstance(context, Mapping) and "narrative_source" in context
    from .campaign_source_turn import PROTOCOL as CAMPAIGN_SOURCE_PROTOCOL
    if (narrative_contract == CAMPAIGN_SOURCE_PROTOCOL
            or isinstance(metadata, Mapping) and metadata.get("narrative_contract") == CAMPAIGN_SOURCE_PROTOCOL
            or isinstance(context, Mapping) and "campaign_source" in context):
        # The complete v2 obligation is checked inside BEGIN IMMEDIATE where
        # P/K/H, the campaign base and the resulting state share one snapshot.
        return None
    if narrative_contract is None and not has_marker and not has_envelope:
        return None

    from .narrative_source_turn import (
        INVOCATION_OPERATION, PROTOCOL, SourceTurnContractError,
        validate_source_turn_commit,
    )

    if (
        type(narrative_contract) is not str or narrative_contract != PROTOCOL
        or not has_marker or metadata["narrative_contract"] != PROTOCOL
        or not has_envelope
    ):
        raise SourceTurnContractError("source_turn_contract_required")
    if (
        attempt is None or attempt["status"] not in {"pending", "completed"}
        or attempt["session_id"] != session_id or attempt["operation_id"] != operation_id
        or attempt["attempt_id"] != attempt_id or attempt["user_input"] != user_input
        or type(requested_turn) is not int or requested_turn < 1
        or attempt["requested_turn"] != requested_turn
        or type(metadata.get("expected_invocation_id")) is not str
        or not metadata["expected_invocation_id"].strip()
        or metadata.get("expected_invocation_operation") != INVOCATION_OPERATION
        or attempt["request_hash"] != _payload_hash(_attempt_request_payload(
            attempt["requested_turn"], attempt["user_input"], metadata,
        ))
    ):
        raise SourceTurnContractError("source_turn_attempt_mismatch")
    return validate_source_turn_commit(
        context["narrative_source"], narrative=narrative, session_id=session_id,
        turn_id=turn_id, operation_id=operation_id, attempt_id=attempt_id,
        expected_invocation_id=metadata["expected_invocation_id"],
        expected_invocation_operation=metadata["expected_invocation_operation"],
        facts=facts, events=events, memory_candidates=memory_candidates,
        episodic_memories=episodic_memories, provenance=provenance,
    )


class SourceInputPersistenceError(ValueError):
    """Closed refusal of the producer DB boundary; not a persisted P failure."""

    def __init__(self, code: str = "source_input_stored_pair_invalid"):
        self.code = code if type(code) is str and code in {
            "source_input_database_unavailable", "source_input_schema_incompatible",
            "source_input_history_invalid", "source_input_stored_pair_invalid",
            "source_input_operation_conflict", "source_input_session_busy",
            "source_input_claim_missing", "source_input_query_invalid",
        } else "source_input_stored_pair_invalid"
        super().__init__(self.code)


class SourceSetupPersistenceError(ValueError):
    """Closed setup storage diagnostic, never a campaign payload or raw error."""

    def __init__(self, code: str = "source_setup_manifest_invalid"):
        self.code = code if type(code) is str and code in {
            "source_setup_query_invalid", "source_setup_database_unavailable",
            "source_setup_schema_incompatible", "source_setup_campaign_exists",
            "source_setup_campaign_missing", "source_setup_manifest_missing",
            "source_setup_manifest_invalid", "source_setup_history_invalid",
            "source_setup_arguments_invalid",
        } else "source_setup_manifest_invalid"
        super().__init__(self.code)


class SQLitePersistence:
    """SQLite repository with explicit transaction and idempotency semantics."""

    def __init__(self, db_path: str | os.PathLike[str] = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._session_locks_guard = asyncio.Lock()
        self._initialize_lock = asyncio.Lock()
        self._initialized = False

    async def _session_lock(self, session_id: str) -> asyncio.Lock:
        if not session_id:
            raise ValueError("session_id is required")
        async with self._session_locks_guard:
            return self._session_locks.setdefault(session_id, asyncio.Lock())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    async def initialize(self) -> None:
        if self._initialized:
            return
        async with self._initialize_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    @staticmethod
    def _require_columns(
        connection: sqlite3.Connection,
        table: str,
        required: set[str],
        *,
        schema_version: int,
    ) -> set[str]:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = sorted(required - columns)
        if missing:
            raise SchemaVersionError(
                f"Schema v{schema_version} table {table!r} is missing columns: "
                + ", ".join(missing)
            )
        return columns

    @staticmethod
    def _unique_column_sets(
        connection: sqlite3.Connection, table: str
    ) -> set[frozenset[str]]:
        """Return global UNIQUE/PRIMARY KEY column sets for one table."""

        result: set[frozenset[str]] = set()
        for index in connection.execute(f"PRAGMA index_list({table})").fetchall():
            if not bool(index["unique"]) or bool(index["partial"]):
                continue
            index_name = str(index["name"]).replace('"', '""')
            columns = frozenset(
                str(row["name"])
                for row in connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                ).fetchall()
                if row["name"] is not None
            )
            if columns:
                result.add(columns)
        return result

    @staticmethod
    def _foreign_key_signatures(
        connection: sqlite3.Connection, table: str
    ) -> set[tuple[str, str, str, str]]:
        return {
            (
                str(row["from"]),
                str(row["table"]),
                str(row["to"]),
                str(row["on_delete"]).upper(),
            )
            for row in connection.execute(
                f"PRAGMA foreign_key_list({table})"
            ).fetchall()
        }

    @staticmethod
    def _normalized_table_sql(
        connection: sqlite3.Connection, table: str
    ) -> str:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        sql = str(row["sql"] or "") if row is not None else ""
        return re.sub(r"[\s\"`\[\]]+", "", sql.lower())

    def _validate_schema_shape(
        self,
        connection: sqlite3.Connection,
        *,
        schema_version: int,
        existing_only: bool,
    ) -> None:
        """Validate existing tables before writes and the complete post-schema.

        Versions 1 and 2 differ from v3 only in the two attempt hashes and the
        campaign state revision.  Tables absent from an older schema may be
        introduced by the transactional DDL, but a table that already exists
        must never be silently accepted with a partial shape.
        """

        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table, v3_columns in _SCHEMA_COLUMNS_V3.items():
            if table not in existing_tables:
                if existing_only:
                    continue
                raise SchemaVersionError(
                    f"Schema v{schema_version} is missing table {table!r}"
                )
            required = set(v3_columns)
            if table == "campaigns" and schema_version < 3:
                required.remove("state_revision")
            if table == "attempts" and schema_version < 2:
                required.difference_update({"request_hash", "result_hash"})
            self._require_columns(
                connection,
                table,
                required,
                schema_version=schema_version,
            )

            available_unique_sets = self._unique_column_sets(connection, table)
            missing_unique_sets = _SCHEMA_UNIQUES.get(table, frozenset()) - available_unique_sets
            if missing_unique_sets:
                labels = sorted(
                    "+".join(sorted(columns)) for columns in missing_unique_sets
                )
                raise SchemaVersionError(
                    f"Schema v{schema_version} table {table!r} is missing UNIQUE "
                    f"invariants: {', '.join(labels)}"
                )

            required_foreign_keys = _SCHEMA_FOREIGN_KEYS.get(
                table, frozenset()
            )
            missing_foreign_keys = required_foreign_keys - self._foreign_key_signatures(
                connection, table
            )
            if missing_foreign_keys:
                labels = sorted(
                    f"{source}->{target}.{column} ON DELETE {on_delete}"
                    for source, target, column, on_delete in missing_foreign_keys
                )
                raise SchemaVersionError(
                    f"Schema v{schema_version} table {table!r} is missing FOREIGN KEY "
                    f"invariants: {', '.join(labels)}"
                )

            required_checks = set(_SCHEMA_CHECKS_V3.get(table, frozenset()))
            if table == "campaigns" and schema_version < 3:
                required_checks.discard("check(state_revision>=0)")
            table_sql = self._normalized_table_sql(connection, table)
            missing_checks = sorted(
                fragment for fragment in required_checks if fragment not in table_sql
            )
            if missing_checks:
                raise SchemaVersionError(
                    f"Schema v{schema_version} table {table!r} is missing CHECK "
                    f"invariants: {', '.join(missing_checks)}"
                )

        if schema_version == 1 and "attempts" in existing_tables:
            # Parse every value before WAL/schema mutations. The migration does
            # this again while building hashes so the write transaction remains
            # self-contained even if invoked directly in a focused test.
            rows = connection.execute(
                "SELECT id, metadata_json FROM attempts"
            ).fetchall()
            for row in rows:
                try:
                    _json_load(row["metadata_json"], {})
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise SchemaVersionError(
                        f"Attempt row {row['id']} has invalid metadata_json"
                    ) from exc

    def _migrate_schema_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        """Separate request identity from results inside the caller transaction."""

        self._require_columns(
            connection,
            "campaigns",
            {
                "session_id",
                "chronicle_name",
                "schema_version",
                "current_turn",
                "state_json",
                "relationships_json",
                "metadata_json",
                "created_at",
                "updated_at",
            },
            schema_version=1,
        )
        columns = self._require_columns(
            connection,
            "attempts",
            {
                "id",
                "attempt_id",
                "session_id",
                "operation_id",
                "requested_turn",
                "status",
                "user_input",
                "partial_narrative",
                "error_json",
                "provenance_json",
                "usage_json",
                "metadata_json",
                "payload_hash",
                "committed_turn_id",
                "started_at",
                "completed_at",
            },
            schema_version=1,
        )
        rows = connection.execute(
            """SELECT id, requested_turn, user_input, metadata_json,
                      payload_hash, status
               FROM attempts"""
        ).fetchall()
        migrated_hashes: list[tuple[str, str | None, int]] = []
        for row in rows:
            try:
                metadata = _json_load(row["metadata_json"], {})
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise SchemaVersionError(
                    f"Attempt row {row['id']} has invalid metadata_json"
                ) from exc
            request_hash = _payload_hash(
                _attempt_request_payload(
                    row["requested_turn"], row["user_input"], metadata
                )
            )
            result_hash = None if row["status"] == "pending" else row["payload_hash"]
            migrated_hashes.append((request_hash, result_hash, int(row["id"])))

        if "request_hash" not in columns:
            connection.execute(
                "ALTER TABLE attempts ADD COLUMN request_hash TEXT NOT NULL DEFAULT ''"
            )
        if "result_hash" not in columns:
            connection.execute("ALTER TABLE attempts ADD COLUMN result_hash TEXT")
        connection.executemany(
            "UPDATE attempts SET request_hash=?, result_hash=? WHERE id=?",
            migrated_hashes,
        )

    def _migrate_schema_v2_to_v3(self, connection: sqlite3.Connection) -> None:
        """Add a monotonic control-state revision inside the caller transaction."""

        columns = self._require_columns(
            connection,
            "campaigns",
            {
                "session_id",
                "chronicle_name",
                "schema_version",
                "current_turn",
                "state_json",
                "relationships_json",
                "metadata_json",
                "created_at",
                "updated_at",
            },
            schema_version=2,
        )
        self._require_columns(
            connection,
            "attempts",
            {
                "id",
                "attempt_id",
                "session_id",
                "operation_id",
                "requested_turn",
                "status",
                "user_input",
                "partial_narrative",
                "error_json",
                "provenance_json",
                "usage_json",
                "metadata_json",
                "payload_hash",
                "request_hash",
                "result_hash",
                "committed_turn_id",
                "started_at",
                "completed_at",
            },
            schema_version=2,
        )
        if "state_revision" not in columns:
            connection.execute(
                "ALTER TABLE campaigns ADD COLUMN state_revision "
                "INTEGER NOT NULL DEFAULT 0 CHECK (state_revision >= 0)"
            )

    def _initialize_sync(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            existing_tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            domain_tables = {
                "campaigns",
                "attempts",
                "turns",
                "events",
                "memory_candidates",
                "episodic_memories",
                "consolidations",
                "legacy_imports",
                "narration_resume_capsules",
                "narrator_availability_gates",
            }
            has_schema_meta = "schema_meta" in existing_tables
            if not has_schema_meta and existing_tables & domain_tables:
                raise SchemaVersionError(
                    "An unversioned persistence schema already exists and requires "
                    "an explicit migration"
                )

            version_number = 0
            if has_schema_meta:
                self._require_columns(
                    connection,
                    "schema_meta",
                    {"key", "value"},
                    schema_version=0,
                )
                existing_version = connection.execute(
                    "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                ).fetchone()
                if existing_version is None:
                    raise SchemaVersionError(
                        "Database schema is missing its schema_version marker"
                    )
                try:
                    version_number = int(existing_version["value"])
                except (TypeError, ValueError) as exc:
                    raise SchemaVersionError("Database schema version is invalid") from exc
                if version_number not in {1, 2, 3, SCHEMA_VERSION}:
                    raise SchemaVersionError(
                        "Database schema "
                        f"{existing_version['value']} requires an explicit migration; "
                        f"this build supports schema {SCHEMA_VERSION}"
                    )

                # Validate every table that already exists before any pragma,
                # DDL, or version marker can mutate the database.
                self._validate_schema_shape(
                    connection,
                    schema_version=version_number,
                    existing_only=True,
                )

            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE")
            try:
                if version_number == 1:
                    self._migrate_schema_v1_to_v2(connection)
                    version_number = 2
                if version_number == 2:
                    self._migrate_schema_v2_to_v3(connection)
                    version_number = 3
                if version_number == 3:
                    version_number = SCHEMA_VERSION

                schema_sql = (
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_revision INTEGER NOT NULL DEFAULT 0 CHECK (state_revision >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    operation_id TEXT NOT NULL,
                    requested_turn INTEGER,
                    status TEXT NOT NULL CHECK (status IN ('pending','completed','failed','cancelled','timeout')),
                    user_input TEXT NOT NULL DEFAULT '',
                    partial_narrative TEXT NOT NULL DEFAULT '',
                    error_json TEXT,
                    provenance_json TEXT,
                    usage_json TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    payload_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    result_hash TEXT,
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );

                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    turn_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    operation_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
                    turn_number INTEGER NOT NULL CHECK (turn_number > 0),
                    user_input TEXT NOT NULL DEFAULT '',
                    narrative_text TEXT NOT NULL,
                    narrative_complete INTEGER NOT NULL DEFAULT 1 CHECK (narrative_complete IN (0,1)),
                    narrative_json TEXT NOT NULL,
                    facts_json TEXT NOT NULL DEFAULT '[]',
                    context_json TEXT NOT NULL DEFAULT '{}',
                    state_json TEXT NOT NULL,
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    provenance_json TEXT,
                    usage_json TEXT,
                    payload_hash TEXT NOT NULL,
                    committed_at TEXT NOT NULL,
                    UNIQUE(session_id, operation_id),
                    UNIQUE(session_id, turn_number)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    turn_id TEXT NOT NULL REFERENCES turns(turn_id) ON DELETE CASCADE,
                    turn_number INTEGER NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence >= 0),
                    event_type TEXT NOT NULL,
                    summary TEXT,
                    fact_ids_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    actors_json TEXT NOT NULL DEFAULT '[]',
                    place_json TEXT,
                    importance REAL NOT NULL DEFAULT 0,
                    visibility TEXT NOT NULL,
                    references_json TEXT NOT NULL DEFAULT '[]',
                    pending INTEGER NOT NULL DEFAULT 0 CHECK (pending IN (0,1)),
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    UNIQUE(turn_id, sequence)
                );

                CREATE TABLE IF NOT EXISTS memory_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    turn_id TEXT NOT NULL REFERENCES turns(turn_id) ON DELETE CASCADE,
                    turn_number INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    actors_json TEXT NOT NULL DEFAULT '[]',
                    place_json TEXT,
                    occurred_at TEXT,
                    importance REAL NOT NULL DEFAULT 0,
                    visibility TEXT NOT NULL,
                    pending INTEGER NOT NULL DEFAULT 0 CHECK (pending IN (0,1)),
                    proposed_by TEXT NOT NULL DEFAULT '',
                    validation_status TEXT NOT NULL,
                    validation_notes_json TEXT NOT NULL DEFAULT '[]',
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS episodic_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    turn_id TEXT REFERENCES turns(turn_id) ON DELETE SET NULL,
                    turn_number INTEGER,
                    summary TEXT NOT NULL,
                    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    actors_json TEXT NOT NULL DEFAULT '[]',
                    place_json TEXT,
                    occurred_at TEXT,
                    importance REAL NOT NULL DEFAULT 0,
                    visibility TEXT NOT NULL,
                    pending INTEGER NOT NULL DEFAULT 0 CHECK (pending IN (0,1)),
                    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS consolidations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consolidation_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK (version > 0),
                    summary TEXT NOT NULL,
                    source_memory_ids_json TEXT NOT NULL DEFAULT '[]',
                    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    visibility TEXT NOT NULL,
                    supersedes_consolidation_id TEXT REFERENCES consolidations(consolidation_id),
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(session_id, scope, version)
                );

                CREATE TABLE IF NOT EXISTS legacy_imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    content_fingerprint TEXT NOT NULL,
                    content_sha256 TEXT,
                    raw_bytes BLOB,
                    parse_status TEXT NOT NULL CHECK (parse_status IN ('missing','valid','corrupt')),
                    parse_error TEXT,
                    parsed_json TEXT,
                    audited_at TEXT NOT NULL,
                    applied_at TEXT,
                    UNIQUE(session_id, source_kind, content_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS narration_resume_capsules (
                    capsule_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    source_operation_id TEXT NOT NULL,
                    source_attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
                    resume_operation_id TEXT,
                    state TEXT NOT NULL CHECK (state IN ('paused','direct_resume_trial','completed','abandoned')),
                    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, source_operation_id),
                    UNIQUE(session_id, resume_operation_id)
                );

                CREATE TABLE IF NOT EXISTS narrator_availability_gates (
                    gate_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE,
                    scope TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    retry_not_before TEXT,
                    lease_operation_id TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(session_id, scope, scope_key)
                );

                CREATE INDEX IF NOT EXISTS idx_turns_session_number
                    ON turns(session_id, turn_number);
                CREATE INDEX IF NOT EXISTS idx_attempts_session_started
                    ON attempts(session_id, started_at);
                CREATE INDEX IF NOT EXISTS idx_events_session_turn
                    ON events(session_id, turn_number, sequence);
                CREATE INDEX IF NOT EXISTS idx_events_visibility_pending
                    ON events(session_id, visibility, pending);
                CREATE INDEX IF NOT EXISTS idx_memories_session_turn
                    ON episodic_memories(session_id, turn_number);
                CREATE INDEX IF NOT EXISTS idx_memories_visibility_pending
                    ON episodic_memories(session_id, visibility, pending);
                CREATE INDEX IF NOT EXISTS idx_consolidations_session_scope
                    ON consolidations(session_id, scope, version);
                """
                )
                for statement in schema_sql.split(";"):
                    if statement.strip():
                        connection.execute(statement)

                self._validate_schema_shape(
                    connection,
                    schema_version=SCHEMA_VERSION,
                    existing_only=False,
                )
                connection.execute(
                    """INSERT INTO schema_meta(key, value)
                       VALUES('schema_version', ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                    (str(SCHEMA_VERSION),),
                )
                connection.execute(
                    "UPDATE campaigns SET schema_version=?", (SCHEMA_VERSION,)
                )
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    async def database_info(self) -> dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(self._database_info_sync)

    def _database_info_sync(self) -> dict[str, Any]:
        with self._connect() as connection:
            version = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            return {
                "schema_version": int(version["value"]),
                "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
                "foreign_keys": bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
            }

    async def create_source_setup_campaign(
        self, session_id: str, *, manifest: SourceSetupManifest,
        initial_state: Any, relationships: Any = None, chronicle_name: str = "",
    ) -> SourceSetupManifest:
        """Create origin and public setup together in an existing current database.

        Database bootstrap is an explicit, separate operation. This boundary
        never creates a database file, migrates schema, adopts an old campaign,
        interprets an action or manufactures an attributed narrative source.
        """
        from .narrative_source_setup import SourceSetupManifest, validate_source_setup_manifest
        from .narrative_source_context import validate_source_state_context
        try:
            if type(manifest) is not SourceSetupManifest or type(chronicle_name) is not str:
                raise ValueError
            checked = validate_source_setup_manifest(manifest, session_id=session_id)
            state = _plain(initial_state)
            relations = _plain({} if relationships is None else relationships)
            if type(state) is not dict or type(relations) is not dict:
                raise ValueError
            validate_source_state_context(state, checked.origin)
            # Capture all JSON-owned values before the first await.
            state = json.loads(json.dumps(state, ensure_ascii=False, allow_nan=False))
            relations = json.loads(json.dumps(relations, ensure_ascii=False, allow_nan=False))
            _json_dump(state).encode("utf-8")
            _json_dump(relations).encode("utf-8")
            chronicle_name.encode("utf-8")
        except (ValueError, TypeError, AttributeError, KeyError, RecursionError, OverflowError):
            raise SourceSetupPersistenceError("source_setup_arguments_invalid") from None
        return await asyncio.to_thread(
            self._create_source_setup_campaign_sync, session_id, checked, state,
            relations, chronicle_name,
        )

    async def read_source_setup_manifest(self, session_id: str) -> SourceSetupManifest:
        """Read a validated public briefing without initializing or writing."""
        try:
            if (type(session_id) is not str or not 1 <= len(session_id) <= 240
                    or session_id != session_id.strip()):
                raise ValueError
            session_id.encode("utf-8")
        except (ValueError, TypeError, AttributeError):
            raise SourceSetupPersistenceError("source_setup_query_invalid") from None
        return await asyncio.to_thread(
            self._source_setup_transaction,
            lambda connection: self._source_setup_manifest_in_connection(connection, session_id),
            write=False,
        )

    def _source_setup_transaction(self, work: Callable, *, write: bool) -> Any:
        """Use one current-schema transaction and always close its connection."""
        try:
            connection = sqlite3.connect(
                self.db_path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"),
                uri=True, timeout=30.0, isolation_level=None,
            )
        except (sqlite3.Error, OSError, ValueError):
            raise SourceSetupPersistenceError("source_setup_database_unavailable") from None
        try:
            connection.row_factory = sqlite3.Row
            if write:
                connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                marker = connection.execute(
                    "SELECT value FROM schema_meta WHERE key='schema_version'",
                ).fetchone()
                if marker is None or marker["value"] != str(SCHEMA_VERSION):
                    raise SchemaVersionError("Current schema required")
                self._validate_schema_shape(connection, schema_version=SCHEMA_VERSION, existing_only=False)
            except (SchemaVersionError, sqlite3.Error):
                raise SourceSetupPersistenceError("source_setup_schema_incompatible") from None
            result = work(connection)
            if write:
                connection.commit()
            return result
        except SourceSetupPersistenceError:
            connection.rollback()
            raise
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, sqlite3.Error):
            connection.rollback()
            raise SourceSetupPersistenceError("source_setup_manifest_invalid") from None
        finally:
            connection.close()

    def _source_setup_manifest_in_connection(
        self, connection: sqlite3.Connection, session_id: str,
    ) -> SourceSetupManifest:
        from .narrative_source_context import ORIGIN_KEY
        from .narrative_source_setup import MANIFEST_KEY, validate_source_setup_manifest
        row = connection.execute(
            "SELECT * FROM campaigns WHERE session_id=?", (session_id,),
        ).fetchone()
        if row is None:
            raise SourceSetupPersistenceError("source_setup_campaign_missing")
        metadata = _json_load(row["metadata_json"], None)
        if type(metadata) is not dict:
            raise SourceSetupPersistenceError("source_setup_manifest_invalid")
        if MANIFEST_KEY not in metadata:
            raise SourceSetupPersistenceError("source_setup_manifest_missing")
        try:
            manifest = validate_source_setup_manifest(metadata[MANIFEST_KEY], session_id=session_id)
            if (_json_dump(metadata[MANIFEST_KEY]) != _json_dump(manifest.model_dump(mode="json"))
                    or _json_dump(metadata.get(ORIGIN_KEY)) != _json_dump(manifest.origin.model_dump(mode="json"))):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
            raise SourceSetupPersistenceError("source_setup_manifest_invalid") from None
        try:
            if type(row["schema_version"]) is not int or row["schema_version"] != SCHEMA_VERSION:
                raise ValueError
            current = self._source_context_snapshot_in_connection(connection, session_id)
            if current.origin.model_dump(mode="json") != manifest.origin.model_dump(mode="json"):
                raise ValueError
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
            raise SourceSetupPersistenceError("source_setup_history_invalid") from None
        # This validates the setup's retained origin, not a zero-turn readiness
        # claim. Legitimate later turns and controls do not change the briefing.
        return manifest

    def _create_source_setup_campaign_sync(
        self, session_id: str, manifest: SourceSetupManifest, state: dict[str, Any],
        relationships: dict[str, Any], chronicle_name: str,
    ) -> SourceSetupManifest:
        from .narrative_source_context import ORIGIN_KEY
        from .narrative_source_setup import MANIFEST_KEY
        metadata = {ORIGIN_KEY: manifest.origin.model_dump(mode="json"),
                    MANIFEST_KEY: manifest.model_dump(mode="json")}

        def create(connection):
            if connection.execute(
                "SELECT 1 FROM campaigns WHERE session_id=?", (session_id,),
            ).fetchone() is not None:
                raise SourceSetupPersistenceError("source_setup_campaign_exists")
            # A new campaign cannot adopt orphaned actions or narrative history.
            for table in ("attempts", "turns", "events", "memory_candidates",
                          "episodic_memories", "consolidations", "legacy_imports"):
                if connection.execute(
                    f"SELECT 1 FROM {table} WHERE session_id=? LIMIT 1", (session_id,),
                ).fetchone() is not None:
                    raise SourceSetupPersistenceError("source_setup_history_invalid")
            self._insert_campaign_if_missing(
                connection, session_id, chronicle_name, state, relationships, metadata,
            )
            stored = self._source_setup_manifest_in_connection(connection, session_id)
            row = connection.execute(
                "SELECT current_turn, state_revision FROM campaigns WHERE session_id=?", (session_id,),
            ).fetchone()
            if row["current_turn"] != 0 or row["state_revision"] != 0:
                raise SourceSetupPersistenceError("source_setup_history_invalid")
            return stored

        return self._source_setup_transaction(create, write=True)

    async def create_narrative_source_campaign(
        self, session_id: str, *, initial_scene: SceneState,
        initial_state: Any = None, relationships: Any = None,
        chronicle_name: str = "",
    ) -> dict[str, Any]:
        """Create a new internal B origin; never register an existing campaign."""
        from .narrative_source_context import (
            ORIGIN_KEY, create_source_context_origin, validate_source_state_context,
        )
        origin = create_source_context_origin(session_id, initial_scene)
        state = _plain({} if initial_state is None else initial_state)
        relation_state = _plain({} if relationships is None else relationships)
        validate_source_state_context(state, origin)
        metadata = {ORIGIN_KEY: origin.model_dump(mode="json")}
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._create_narrative_source_campaign_sync, session_id,
                chronicle_name, state, relation_state, metadata,
            )

    def _create_narrative_source_campaign_sync(
        self, session_id: str, chronicle_name: str, state: Any,
        relationships: Any, metadata: dict[str, Any],
    ) -> dict[str, Any]:
        from .narrative_source_context import SourceContextError
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if connection.execute(
                    "SELECT 1 FROM campaigns WHERE session_id=?", (session_id,),
                ).fetchone() is not None:
                    raise SourceContextError("source_context_campaign_exists")
                self._insert_campaign_if_missing(
                    connection, session_id, chronicle_name, state, relationships, metadata,
                )
                row = connection.execute(
                    "SELECT * FROM campaigns WHERE session_id=?", (session_id,),
                ).fetchone()
                result = _decode_row(row, ("state_json", "relationships_json", "metadata_json"))
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise

    async def read_source_context_snapshot(
        self, session_id: str, *, expected_turn: int | None = None,
        expected_revision: int | None = None,
        allowed_visibilities: Sequence[str] = ("public", "player"),
    ) -> SourceContextSnapshot:
        """Read eligible origin, state and complete source history atomically."""
        from .narrative_source_context import SourceContextError
        if (
            type(session_id) is not str or not session_id.strip()
            or session_id != session_id.strip()
            or any(value is not None and (type(value) is not int or value < 0)
                   for value in (expected_turn, expected_revision))
            or not isinstance(allowed_visibilities, (tuple, list))
            or not allowed_visibilities
            or any(type(value) is not str or value not in {"public", "player"}
                   for value in allowed_visibilities)
        ):
            raise SourceContextError("source_context_query_invalid")
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._read_source_context_snapshot_sync, session_id,
                expected_turn, expected_revision, tuple(allowed_visibilities),
            )

    def _read_source_context_snapshot_sync(
        self, session_id: str, expected_turn: int | None,
        expected_revision: int | None, allowed_visibilities: tuple[str, ...],
    ) -> SourceContextSnapshot:
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._source_context_snapshot_in_connection(
                connection, session_id, expected_turn=expected_turn,
                expected_revision=expected_revision, allowed_visibilities=allowed_visibilities,
            )

    def _source_context_snapshot_in_connection(
        self, connection: sqlite3.Connection, session_id: str, *,
        expected_turn: int | None = None, expected_revision: int | None = None,
        allowed_visibilities: tuple[str, ...] = ("public", "player"),
    ) -> SourceContextSnapshot:
        from .narrative_source_context import (
            ORIGIN_KEY, ORIGIN_PROTOCOL, SELECTION_KEY, SourceContextError, SourceContextSnapshot,
            validate_source_context_origin, validate_source_selection,
            validate_source_state_context,
        )
        from .narrative_source_turn import SourceTurnContractError
        campaign = connection.execute(
            "SELECT * FROM campaigns WHERE session_id=?", (session_id,),
        ).fetchone()
        if campaign is None:
            raise SourceContextError("source_context_campaign_missing")
        metadata = _json_load(campaign["metadata_json"], {})
        origin = validate_source_context_origin(
            metadata.get(ORIGIN_KEY) if isinstance(metadata, Mapping) else None,
            session_id=session_id,
        )
        current_turn, revision = campaign["current_turn"], campaign["state_revision"]
        if (type(current_turn) is not int or current_turn < 0
                or type(revision) is not int or revision < current_turn
                or expected_turn is not None and current_turn != expected_turn
                or expected_revision is not None and revision != expected_revision):
            raise SourceContextError("source_context_revision_mismatch")
        validate_source_state_context(_json_load(campaign["state_json"], {}), origin)
        for table in ("memory_candidates", "episodic_memories", "consolidations", "legacy_imports"):
            if connection.execute(
                f"SELECT 1 FROM {table} WHERE session_id=? LIMIT 1", (session_id,),
            ).fetchone() is not None:
                raise SourceContextError("source_context_dependencies_forbidden")
        rows = connection.execute(
            "SELECT * FROM turns WHERE session_id=? ORDER BY turn_number", (session_id,),
        ).fetchall()
        if len(rows) != current_turn or any(
            type(row["turn_number"]) is not int or row["turn_number"] != index
            for index, row in enumerate(rows, 1)
        ):
            raise SourceContextError("source_context_history_incompatible")
        restored, history_ids = [], []
        previous_base_revision = -1
        for row in rows:
            try:
                context = _json_load(row["context_json"], {})
                if not isinstance(context, Mapping) or set(context) != {"narrative_source", SELECTION_KEY}:
                    raise SourceContextError("source_context_history_incompatible")
                envelope = self._restore_narrative_source_row(
                    connection, row, session_id, ("public", "player"),
                )
                validate_source_state_context(_json_load(row["state_json"], {}), origin)
                attempt = connection.execute(
                    "SELECT metadata_json FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, row["operation_id"]),
                ).fetchone()
                attempt_metadata = _json_load(attempt["metadata_json"], {})
                base_revision = attempt_metadata.get("source_context_base_state_revision")
                if (attempt_metadata.get("source_context_protocol") != ORIGIN_PROTOCOL
                        or type(base_revision) is not int or base_revision < row["turn_number"] - 1
                        or base_revision <= previous_base_revision or base_revision >= revision):
                    raise SourceContextError("source_context_stored_pair_mismatch")
                validate_source_selection(
                    context[SELECTION_KEY], origin=origin, current_turn=row["turn_number"] - 1,
                    state_revision=base_revision, history_turn_ids=tuple(history_ids),
                )
                previous_base_revision = base_revision
            except SourceContextError:
                raise
            except (SourceTurnContractError, ValueError, TypeError, KeyError, AttributeError):
                raise SourceContextError("source_context_stored_pair_mismatch") from None
            restored.append(envelope)
            history_ids.append(row["turn_id"])
        for envelope in restored:
            if envelope.projection.source.visibility.value not in allowed_visibilities:
                raise SourceContextError("source_context_dependencies_forbidden")
        return SourceContextSnapshot(
            origin=origin, current_turn=current_turn, state_revision=revision,
            sources=tuple(restored[-2:]), selected_turn_ids=tuple(history_ids[-2:]),
            omitted_turn_ids=tuple(history_ids[:-2]),
        )

    def _validate_source_campaign_commit(
        self, connection: sqlite3.Connection, *, session_id: str,
        narrative_contract: str | None, context: Any, state: Any,
        requested_turn: int | None, base_state_revision: int | None,
        operation_id: str,
    ) -> None:
        from .narrative_source_context import (
            ORIGIN_KEY, ORIGIN_PROTOCOL, SELECTION_KEY, SourceContextError,
            validate_source_state_context, validate_source_selection,
        )
        from .narrative_source_turn import PROTOCOL
        row = connection.execute(
            "SELECT metadata_json FROM campaigns WHERE session_id=?", (session_id,),
        ).fetchone()
        metadata = _json_load(row["metadata_json"], {}) if row is not None else {}
        attempt = connection.execute(
            "SELECT metadata_json FROM attempts WHERE session_id=? AND operation_id=?",
            (session_id, operation_id),
        ).fetchone()
        reserved = _json_load(attempt["metadata_json"], {}) if attempt is not None else {}
        if not (
            isinstance(metadata, Mapping) and ORIGIN_KEY in metadata
            or isinstance(reserved, Mapping) and "source_context_protocol" in reserved
            or isinstance(context, Mapping) and SELECTION_KEY in context
        ):
            return
        if (narrative_contract != PROTOCOL or not isinstance(context, Mapping)
                or set(context) != {"narrative_source", SELECTION_KEY}):
            raise SourceContextError("source_context_commit_contract_required")
        snapshot = self._source_context_snapshot_in_connection(connection, session_id)
        validate_source_state_context(_plain(state), snapshot.origin)
        if (reserved.get("source_context_protocol") != ORIGIN_PROTOCOL
                or type(requested_turn) is not int or requested_turn < 1
                or type(base_state_revision) is not int or base_state_revision < requested_turn - 1
                or reserved.get("source_context_base_state_revision") != base_state_revision
                or type(reserved.get("source_context_base_state_revision")) is not int):
            raise SourceContextError("source_context_stored_pair_mismatch")
        prior_ids = tuple(row["turn_id"] for row in connection.execute(
            "SELECT turn_id FROM turns WHERE session_id=? AND turn_number<? ORDER BY turn_number",
            (session_id, requested_turn),
        ))
        validate_source_selection(
            context[SELECTION_KEY], origin=snapshot.origin,
            current_turn=requested_turn - 1, state_revision=base_state_revision,
            history_turn_ids=prior_ids,
        )

    @staticmethod
    def _source_preparation_payloads(capsule: SourceTurnCapsule) -> tuple[dict, str, str]:
        from .narrative_source_capsule import CAPSULE_KEY
        metadata = {CAPSULE_KEY: capsule.model_dump(mode="json")}
        requested_turn = capsule.snapshot.current_turn + 1
        request_hash = _payload_hash(_attempt_request_payload(
            requested_turn, capsule.player_input, metadata,
        ))
        result_hash = _payload_hash({
            "status": "completed", "requested_turn": requested_turn,
            "user_input": capsule.player_input, "metadata": metadata,
            "provenance": None, "usage": None, "snapshot": None,
        })
        return metadata, request_hash, result_hash

    def _validate_source_preparation_base(
        self, connection: sqlite3.Connection, capsule: SourceTurnCapsule,
        current: SourceContextSnapshot,
    ) -> None:
        """Match the retained prefix without pretending its revision is still current."""
        from .narrative_source_capsule import SourceCapsuleError
        base = capsule.snapshot
        count = base.current_turn
        history = current.omitted_turn_ids + current.selected_turn_ids
        if (base.origin != current.origin or count > current.current_turn
                or base.state_revision > current.state_revision):
            raise SourceCapsuleError("source_capsule_base_mismatch")
        prefix = history[:count]
        if (base.selected_turn_ids != prefix[-2:]
                or base.omitted_turn_ids != prefix[:-2]):
            raise SourceCapsuleError("source_capsule_history_mismatch")
        restored = []
        for turn_id in prefix[-2:]:
            row = connection.execute(
                "SELECT * FROM turns WHERE session_id=? AND turn_id=?",
                (capsule.snapshot.origin.session_id, turn_id),
            ).fetchone()
            restored.append(self._restore_narrative_source_row(
                connection, row, capsule.snapshot.origin.session_id, ("public", "player"),
            ))
        if _json_dump(tuple(restored)) != _json_dump(base.sources):
            raise SourceCapsuleError("source_capsule_history_mismatch")
        # A control may advance revision without adding a turn. The retained
        # revision must fall between the adjacent committed turns, not equal
        # the current revision or the following turn's base.
        for number, lower_bound in ((count, True), (count + 1, False)):
            if not 1 <= number <= current.current_turn:
                continue
            row = connection.execute(
                """SELECT a.metadata_json FROM attempts a JOIN turns t
                   ON a.session_id=t.session_id AND a.operation_id=t.operation_id
                   WHERE t.session_id=? AND t.turn_number=?""",
                (capsule.snapshot.origin.session_id, number),
            ).fetchone()
            revision = _json_load(row["metadata_json"], {})["source_context_base_state_revision"]
            if (lower_bound and base.state_revision <= revision
                    or not lower_bound and base.state_revision > revision):
                raise SourceCapsuleError("source_capsule_base_mismatch")

    def _restore_source_preparation_row(
        self, connection: sqlite3.Connection, row: sqlite3.Row,
        session_id: str, operation_id: str, current: SourceContextSnapshot,
    ) -> SourceTurnCapsule:
        from .narrative_source_capsule import (
            CAPSULE_KEY, SourceCapsuleError, source_preparation_operation_id,
            source_preparation_attempt_id, validate_source_turn_capsule,
        )
        try:
            metadata = _json_load(row["metadata_json"], {})
            if not isinstance(metadata, Mapping) or set(metadata) != {CAPSULE_KEY}:
                raise ValueError
            capsule = validate_source_turn_capsule(
                metadata[CAPSULE_KEY], session_id=session_id, operation_id=operation_id,
            )
            expected_metadata, request_hash, result_hash = self._source_preparation_payloads(capsule)
            if (
                row["session_id"] != session_id
                or row["operation_id"] != source_preparation_operation_id(session_id, operation_id)
                or row["attempt_id"] != source_preparation_attempt_id(session_id, operation_id)
                or row["status"] != "completed" or row["committed_turn_id"] is not None
                or type(row["requested_turn"]) is not int
                or row["requested_turn"] != capsule.snapshot.current_turn + 1
                or row["user_input"] != capsule.player_input or row["partial_narrative"] != ""
                or row["error_json"] is not None or row["provenance_json"] is not None
                or row["usage_json"] is not None
                or row["payload_hash"] != request_hash or row["request_hash"] != request_hash
                or row["result_hash"] != result_hash
                or _json_dump(metadata) != _json_dump(expected_metadata)
                or type(row["started_at"]) is not str
                or row["started_at"] != row["completed_at"]
                or datetime.fromisoformat(row["started_at"]).utcoffset() is None
            ):
                raise ValueError
            self._validate_source_preparation_base(connection, capsule, current)
            return capsule
        except SourceCapsuleError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError):
            raise SourceCapsuleError("source_capsule_stored_pair_invalid") from None

    async def save_source_preparation(self, capsule: SourceTurnCapsule) -> AttemptResult:
        """Retain an immutable B preparation, never a narrative or campaign update."""
        from .narrative_source_capsule import (
            SourceTurnCapsule, SourceCapsuleError, validate_source_turn_capsule,
        )
        try:
            if type(capsule) is not SourceTurnCapsule:
                raise ValueError
            checked = validate_source_turn_capsule(
                capsule, session_id=capsule.snapshot.origin.session_id, operation_id=capsule.operation_id,
            )
            # Detach every nested caller-owned value before the first await.
            checked = validate_source_turn_capsule(
                checked.model_dump(mode="json"), session_id=checked.snapshot.origin.session_id,
                operation_id=checked.operation_id,
            )
        except SourceCapsuleError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError):
            raise SourceCapsuleError("source_capsule_invalid") from None
        await self.initialize()
        lock = await self._session_lock(checked.snapshot.origin.session_id)
        async with lock:
            return await asyncio.to_thread(self._save_source_preparation_sync, checked)

    def _save_source_preparation_sync(self, capsule: SourceTurnCapsule) -> AttemptResult:
        from .narrative_source_capsule import (
            SourceCapsuleError, source_preparation_operation_id, source_preparation_attempt_id,
        )
        session_id, operation_id = capsule.snapshot.origin.session_id, capsule.operation_id
        control_id = source_preparation_operation_id(session_id, operation_id)
        attempt_id = source_preparation_attempt_id(session_id, operation_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current = self._source_context_snapshot_in_connection(connection, session_id)
                existing = connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, control_id),
                ).fetchone()
                if existing is not None:
                    stored = self._restore_source_preparation_row(
                        connection, existing, session_id, operation_id, current,
                    )
                    if _json_dump(stored) != _json_dump(capsule):
                        raise IdempotencyConflictError("Source preparation already has different data")
                    connection.commit()
                    return AttemptResult(session_id, control_id, attempt_id, "completed", True,
                                         current.state_revision)
                if connection.execute(
                    "SELECT 1 FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone() is not None:
                    raise SourceCapsuleError("source_capsule_operation_already_started")
                if _json_dump(capsule.snapshot) != _json_dump(current):
                    raise SourceCapsuleError("source_capsule_base_mismatch")
                metadata, request_hash, result_hash = self._source_preparation_payloads(capsule)
                now = _utc_now()
                connection.execute(
                    """INSERT INTO attempts(
                        attempt_id,session_id,operation_id,requested_turn,status,user_input,
                        partial_narrative,error_json,provenance_json,usage_json,metadata_json,
                        payload_hash,request_hash,result_hash,committed_turn_id,started_at,completed_at
                    ) VALUES (?,?,?,?,'completed',?,'',NULL,NULL,NULL,?,?,?,?,NULL,?,?)""",
                    (attempt_id, session_id, control_id, capsule.snapshot.current_turn + 1,
                     capsule.player_input, _json_dump(metadata), request_hash, request_hash,
                     result_hash, now, now),
                )
                connection.commit()
                return AttemptResult(session_id, control_id, attempt_id, "completed", False,
                                     current.state_revision)
            except Exception:
                connection.rollback()
                raise

    async def load_source_preparation(
        self, session_id: str, operation_id: str,
    ) -> SourceTurnCapsule | None:
        from .narrative_source_capsule import source_preparation_operation_id
        control_id = source_preparation_operation_id(session_id, operation_id)
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._load_source_preparation_sync, session_id, operation_id, control_id,
            )

    def _load_source_preparation_sync(
        self, session_id: str, operation_id: str, control_id: str,
    ) -> SourceTurnCapsule | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            current = self._source_context_snapshot_in_connection(connection, session_id)
            row = connection.execute(
                "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                (session_id, control_id),
            ).fetchone()
            if row is None:
                return None
            return self._restore_source_preparation_row(
                connection, row, session_id, operation_id, current,
            )

    async def read_source_player_observation(
        self, session_id: str, *, operation_id: str | None = None,
    ) -> SourcePlayerObservation:
        """Observe one producer-backed P/K/H chain and latest text in one snapshot.

        This new reader requires P for any returned K/H/turn. Earlier retained
        readers keep their existing policy. No initialize, recovery, write,
        producer, execution handle or newly-claimed authority is involved.
        """
        from .narrative_source_observation import SourceObservationError
        from .narrative_source_input import source_input_operation_id
        try:
            # The shared identity helper validates both strings without I/O.
            source_input_operation_id(session_id, operation_id if operation_id is not None else session_id)
        except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
            raise SourceObservationError("source_observation_query_invalid") from None
        return await asyncio.to_thread(
            self._read_source_player_observation_sync, session_id, operation_id,
        )

    def _read_source_player_observation_sync(
        self, session_id: str, operation_id: str | None,
    ) -> SourcePlayerObservation:
        from .narrative_source_observation import (
            SourceConfirmedObservation, SourceObservationError, SourcePlayerObservation,
            validate_source_player_observation,
        )
        def work(connection: sqlite3.Connection) -> SourcePlayerObservation:
            manifest = self._source_setup_manifest_in_connection(connection, session_id)
            current = self._source_context_snapshot_in_connection(connection, session_id)
            latest = None
            latest_requested = None
            if current.sources:
                envelope = current.sources[-1]
                latest_requested = self._source_requested_observation_in_connection(
                    connection, session_id, envelope.operation_id, current,
                )
                if (latest_requested.confirmed != envelope
                        or latest_requested.narrative is None):
                    raise SourceObservationError("source_observation_stored_pair_invalid")
                latest = SourceConfirmedObservation(
                    operation=latest_requested.narrative, envelope=latest_requested.confirmed,
                )
            requested = None
            if operation_id is not None:
                requested = (latest_requested if latest_requested is not None
                    and latest_requested.operation_id == operation_id else
                    self._source_requested_observation_in_connection(
                        connection, session_id, operation_id, current,
                    ))
            return validate_source_player_observation(SourcePlayerObservation(
                session_id=session_id, manifest=manifest, latest_completed=latest,
                requested=requested,
            ), session_id=session_id, operation_id=operation_id)
        try:
            return self._source_setup_transaction(work, write=False)
        except SourceSetupPersistenceError as exc:
            code = ("source_observation_database_unavailable"
                    if str(exc) == "source_setup_database_unavailable"
                    else "source_observation_stored_pair_invalid")
            raise SourceObservationError(code) from None
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError,
                OverflowError, OSError, sqlite3.Error):
            raise SourceObservationError("source_observation_stored_pair_invalid") from None

    def _source_requested_observation_in_connection(
        self, connection: sqlite3.Connection, session_id: str, operation_id: str,
        current: SourceContextSnapshot,
    ):
        from .narrative_source_capsule import (
            source_preparation_operation_id, source_preparation_attempt_id,
        )
        from .narrative_source_input import SourceInputClaim
        from .narrative_source_preparation import _stable_id
        from .narrative_source_observation import SourceObservationError, SourceRequestedObservation
        from .narrative_source_status import create_source_operation_snapshot

        rows = self._source_input_control_rows(connection, session_id, operation_id)
        if len(rows) > 1:
            raise SourceObservationError("source_observation_stored_pair_invalid")
        if not rows:
            # An earlier internal K/H is incompatible here, never a missing P
            # silently eligible for adoption by this producer-backed reader.
            orphan = connection.execute(
                """SELECT 1 FROM attempts WHERE (session_id=? AND operation_id IN (?,?))
                   OR attempt_id IN (?,?) LIMIT 1""",
                (session_id, operation_id, source_preparation_operation_id(session_id, operation_id),
                 source_preparation_attempt_id(session_id, operation_id), _stable_id(session_id, operation_id, "attempt")),
            ).fetchone()
            turn = connection.execute(
                """SELECT 1 FROM turns WHERE (session_id=? AND operation_id=?)
                   OR attempt_id=? OR turn_id=? LIMIT 1""",
                (session_id, operation_id, _stable_id(session_id, operation_id, "attempt"),
                 _stable_id(session_id, operation_id, "turn")),
            ).fetchone()
            if orphan is not None or turn is not None:
                raise SourceObservationError("source_observation_stored_pair_invalid")
            return SourceRequestedObservation(operation_id=operation_id)
        request, completion, capsule, attempt = self._restore_source_input_row(connection, rows[0], current)
        claim = SourceInputClaim(request=request, status=rows[0]["status"],
                                 newly_claimed=False, completion=completion)
        snapshot, envelope = None, None
        if capsule is None:
            # P pending/terminal cannot hide an H/turn under a displaced public
            # operation ID. The earlier restorer's policy remains unchanged.
            orphan = connection.execute(
                "SELECT 1 FROM attempts WHERE attempt_id=? LIMIT 1",
                (_stable_id(session_id, operation_id, "attempt"),),
            ).fetchone()
            turn = connection.execute(
                "SELECT 1 FROM turns WHERE attempt_id=? OR turn_id=? LIMIT 1",
                (_stable_id(session_id, operation_id, "attempt"),
                 _stable_id(session_id, operation_id, "turn")),
            ).fetchone()
            if orphan is not None or turn is not None:
                raise SourceObservationError("source_observation_stored_pair_invalid")
        if capsule is not None:
            error = None
            if attempt is not None:
                # Existing restoration already checked the pair/hash. Restore
                # the exact confirmed row, including historical operations.
                turn = connection.execute(
                    "SELECT * FROM turns WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                error = self._validate_source_status_pair(connection, capsule, attempt, turn)
                if attempt["status"] == "completed":
                    envelope = self._restore_narrative_source_row(
                        connection, turn, session_id, ("public", "player"),
                    )
            snapshot = create_source_operation_snapshot(
                capsule, current_turn=current.current_turn,
                current_state_revision=current.state_revision,
                status="retained_unstarted" if attempt is None else attempt["status"],
                committed_turn_id=None if attempt is None else attempt["committed_turn_id"],
                error=error,
            )
        return SourceRequestedObservation(operation_id=operation_id, preparation=claim,
                                          narrative=snapshot, confirmed=envelope)

    async def read_source_operation_status(
        self, session_id: str, operation_id: str,
    ) -> SourceOperationSnapshot | None:
        """Observe retained B state, without initialization, execution or takeover."""
        from .narrative_source_capsule import source_preparation_operation_id
        from .narrative_source_status import SourceOperationStatusError
        try:
            control_id = source_preparation_operation_id(session_id, operation_id)
        except (ValueError, TypeError, UnicodeError):
            raise SourceOperationStatusError("source_operation_status_query_invalid") from None
        return await asyncio.to_thread(
            self._read_source_operation_status_sync, session_id, operation_id, control_id,
        )

    def _read_source_operation_status_sync(
        self, session_id: str, operation_id: str, control_id: str,
    ) -> SourceOperationSnapshot | None:
        from .narrative_source_capsule import (
            SourceCapsuleError, source_preparation_attempt_id,
        )
        from .narrative_source_context import SourceContextError
        from .narrative_source_status import (
            SourceOperationStatusError, create_source_operation_snapshot,
        )
        from .narrative_source_turn import SourceTurnContractError

        # A URI with mode=ro cannot create a missing file or migrate an old one.
        try:
            connection = sqlite3.connect(
                self.db_path.resolve().as_uri() + "?mode=ro", uri=True,
                timeout=30.0, isolation_level=None,
            )
        except (sqlite3.Error, OSError, ValueError):
            raise SourceOperationStatusError("source_operation_status_database_unavailable") from None
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            try:
                marker = connection.execute(
                    "SELECT value FROM schema_meta WHERE key='schema_version'",
                ).fetchone()
                if marker is None or marker["value"] != str(SCHEMA_VERSION):
                    raise SchemaVersionError("Current schema required")
                self._validate_schema_shape(
                    connection, schema_version=SCHEMA_VERSION, existing_only=False,
                )
            except (sqlite3.Error, SchemaVersionError):
                raise SourceOperationStatusError("source_operation_status_schema_incompatible") from None
            current = self._source_context_snapshot_in_connection(connection, session_id)
            controls = connection.execute(
                """SELECT * FROM attempts WHERE (session_id=? AND operation_id=?)
                   OR attempt_id=?""",
                (session_id, control_id, source_preparation_attempt_id(session_id, operation_id)),
            ).fetchall()
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                (session_id, operation_id),
            ).fetchone()
            turn = connection.execute(
                "SELECT * FROM turns WHERE session_id=? AND operation_id=?",
                (session_id, operation_id),
            ).fetchone()
            if not controls:
                if attempt is not None or turn is not None:
                    raise SourceOperationStatusError("source_operation_status_stored_pair_invalid")
                return None
            if len(controls) != 1:
                raise SourceOperationStatusError("source_operation_status_stored_pair_invalid")
            capsule = self._restore_source_preparation_row(
                connection, controls[0], session_id, operation_id, current,
            )
            # Also catch displaced rows instead of reporting an orphan as unstarted.
            attempts = connection.execute(
                """SELECT * FROM attempts WHERE (session_id=? AND operation_id=?)
                   OR attempt_id=?""", (session_id, operation_id, capsule.draft.attempt_id),
            ).fetchall()
            turns = connection.execute(
                """SELECT * FROM turns WHERE (session_id=? AND operation_id=?)
                   OR attempt_id=? OR turn_id=?""",
                (session_id, operation_id, capsule.draft.attempt_id, capsule.draft.turn_id),
            ).fetchall()
            if len(attempts) > 1 or len(turns) > 1 or not attempts and turns:
                raise SourceOperationStatusError("source_operation_status_stored_pair_invalid")
            if not attempts:
                return create_source_operation_snapshot(
                    capsule, current_turn=current.current_turn,
                    current_state_revision=current.state_revision, status="retained_unstarted",
                )
            attempt, turn = attempts[0], turns[0] if turns else None
            error = self._validate_source_status_pair(connection, capsule, attempt, turn)
            return create_source_operation_snapshot(
                capsule, current_turn=current.current_turn,
                current_state_revision=current.state_revision, status=attempt["status"],
                committed_turn_id=attempt["committed_turn_id"], error=error,
            )
        except SourceOperationStatusError:
            raise
        except SourceCapsuleError:
            raise SourceOperationStatusError("source_operation_status_capsule_invalid") from None
        except (SourceContextError, SourceTurnContractError):
            raise SourceOperationStatusError("source_operation_status_history_invalid") from None
        except (sqlite3.Error, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
            raise SourceOperationStatusError("source_operation_status_stored_pair_invalid") from None
        finally:
            connection.close()

    def _validate_source_status_pair(
        self, connection: sqlite3.Connection, capsule: SourceTurnCapsule,
        attempt: sqlite3.Row, turn: sqlite3.Row | None,
    ) -> Any:
        """Validate both immutable request and terminal result before projection."""
        from .narrative_source_status import expected_source_attempt_metadata
        draft = capsule.draft
        metadata = expected_source_attempt_metadata(capsule)
        request_hash = _payload_hash(_attempt_request_payload(
            draft.base_revision + 1, draft.player_input, metadata,
        ))
        status = attempt["status"]
        if (
            attempt["session_id"] != draft.session_id
            or attempt["operation_id"] != capsule.operation_id
            or attempt["attempt_id"] != draft.attempt_id
            or type(attempt["requested_turn"]) is not int
            or attempt["requested_turn"] != draft.base_revision + 1
            or attempt["user_input"] != draft.player_input
            or _json_dump(_json_load(attempt["metadata_json"], None)) != _json_dump(metadata)
            or attempt["request_hash"] != request_hash or attempt["payload_hash"] != request_hash
            or attempt["partial_narrative"] != ""
            or status not in {"pending", "completed", "failed", "timeout", "cancelled"}
        ):
            raise ValueError
        started = datetime.fromisoformat(attempt["started_at"])
        if started.utcoffset() is None:
            raise ValueError
        if status == "pending":
            if turn is not None or any(attempt[name] is not None for name in (
                "result_hash", "committed_turn_id", "completed_at", "error_json",
                "provenance_json", "usage_json",
            )):
                raise ValueError
            return None
        completed = datetime.fromisoformat(attempt["completed_at"])
        if completed.utcoffset() is None or completed < started:
            raise ValueError
        error = _json_load(attempt["error_json"], None)
        provenance = _json_load(attempt["provenance_json"], None)
        usage = _json_load(attempt["usage_json"], None)
        if status != "completed":
            if turn is not None or attempt["committed_turn_id"] is not None:
                raise ValueError
            if attempt["result_hash"] != _payload_hash({
                "status": status, "requested_turn": draft.base_revision + 1,
                "user_input": draft.player_input, "partial_narrative": "",
                "error": error, "provenance": provenance, "usage": usage, "metadata": metadata,
            }):
                raise ValueError
            return error
        if (
            turn is None or attempt["error_json"] is not None
            or attempt["committed_turn_id"] != draft.turn_id
            or turn["session_id"] != draft.session_id or turn["operation_id"] != capsule.operation_id
            or turn["attempt_id"] != draft.attempt_id or turn["turn_id"] != draft.turn_id
            or type(turn["turn_number"]) is not int or turn["turn_number"] != draft.base_revision + 1
            or turn["user_input"] != draft.player_input
            or turn["provenance_json"] != attempt["provenance_json"]
            or turn["usage_json"] != attempt["usage_json"]
            or turn["committed_at"] != attempt["completed_at"]
        ):
            raise ValueError
        self._restore_narrative_source_row(connection, turn, draft.session_id, ("public", "player"))
        events = [_json_load(row["payload_json"], None) for row in connection.execute(
            "SELECT payload_json FROM events WHERE session_id=? AND turn_id=? ORDER BY sequence",
            (draft.session_id, draft.turn_id),
        ).fetchall()]
        for stored, expected in (
            (_json_load(turn["state_json"], None), capsule.state),
            (_json_load(turn["relationships_json"], None), capsule.relationships),
            (_json_load(turn["facts_json"], None), draft.facts), (events, draft.events),
        ):
            if _json_dump(stored) != _json_dump(expected):
                raise ValueError
        digest = _payload_hash({
            "turn_id": draft.turn_id, "state": capsule.state,
            "narrative": _json_load(turn["narrative_json"], None), "facts": draft.facts,
            "events": draft.events, "memory_candidates": [], "episodic_memories": [],
            "relationships": capsule.relationships, "context": _json_load(turn["context_json"], None),
            "provenance": provenance, "usage": usage, "user_input": draft.player_input,
            "requested_turn": draft.base_revision + 1, "base_revision": draft.base_revision,
            "base_state_revision": draft.base_state_revision,
        })
        if turn["payload_hash"] != digest or attempt["result_hash"] != digest:
            raise ValueError
        return None

    async def claim_source_input(
        self, session_id: str, request: SourcePlayerActionRequest, *,
        producer_config: SourceProducerConfig,
    ) -> SourceInputClaim:
        """Reserve one server producer before classification/RNG, never an H6."""
        from .narrative_source_entry import validate_source_player_action_request
        from .narrative_source_input import SourceProducerConfig, source_input_operation_id
        try:
            checked = validate_source_player_action_request(request)
            source_input_operation_id(session_id, checked.operation_id)
            if type(producer_config) is not SourceProducerConfig:
                raise ValueError
            config = SourceProducerConfig.model_validate(producer_config)
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise SourceInputPersistenceError("source_input_query_invalid") from None
        return await asyncio.to_thread(self._claim_source_input_sync, session_id, checked, config)

    async def finalize_source_input(
        self, session_id: str, operation_id: str, *, request_sha256: str,
        completion: SourceInputCompletion, capsule: SourceTurnCapsule | None = None,
    ) -> SourceInputClaim:
        """Commit K and P together, or only a closed terminal producer failure."""
        from .narrative_source_capsule import SourceTurnCapsule, validate_source_turn_capsule
        from .narrative_source_input import SourceInputCompletion, source_input_operation_id
        try:
            source_input_operation_id(session_id, operation_id)
            if type(request_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", request_sha256) is None:
                raise ValueError
            if type(completion) is not SourceInputCompletion:
                raise ValueError
            checked = SourceInputCompletion.model_validate(completion)
            if checked.request_sha256 != request_sha256:
                raise ValueError
            retained = None
            if capsule is not None:
                if type(capsule) is not SourceTurnCapsule:
                    raise ValueError
                retained = validate_source_turn_capsule(
                    capsule, session_id=session_id, operation_id=operation_id,
                )
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            raise SourceInputPersistenceError("source_input_query_invalid") from None
        return await asyncio.to_thread(
            self._finalize_source_input_sync, session_id, operation_id, request_sha256, checked, retained,
        )

    def _source_input_transaction(self, work: Callable[[sqlite3.Connection], Any]) -> Any:
        """Existing current-schema DB only; no nested connection or migration."""
        try:
            connection = sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=rw", uri=True,
                                         timeout=30.0, isolation_level=None)
        except (sqlite3.Error, OSError, ValueError):
            raise SourceInputPersistenceError("source_input_database_unavailable") from None
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("BEGIN IMMEDIATE")
            try:
                marker = connection.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                if marker is None or marker["value"] != str(SCHEMA_VERSION):
                    raise SchemaVersionError("Current schema required")
                self._validate_schema_shape(connection, schema_version=SCHEMA_VERSION, existing_only=False)
            except (SchemaVersionError, sqlite3.Error):
                raise SourceInputPersistenceError("source_input_schema_incompatible") from None
            result = work(connection)
            connection.commit()
            return result
        except SourceInputPersistenceError:
            connection.rollback()
            raise
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, sqlite3.Error):
            connection.rollback()
            raise SourceInputPersistenceError("source_input_stored_pair_invalid") from None
        finally:
            connection.close()

    @staticmethod
    def _source_input_control_rows(
        connection: sqlite3.Connection, session_id: str, operation_id: str,
    ) -> list[sqlite3.Row]:
        from .narrative_source_input import source_input_operation_id, source_input_attempt_id
        return connection.execute(
            "SELECT * FROM attempts WHERE (session_id=? AND operation_id=?) OR attempt_id=?",
            (session_id, source_input_operation_id(session_id, operation_id),
             source_input_attempt_id(session_id, operation_id)),
        ).fetchall()

    def _source_input_current(self, connection: sqlite3.Connection, session_id: str) -> SourceContextSnapshot:
        try:
            return self._source_context_snapshot_in_connection(connection, session_id)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            raise SourceInputPersistenceError("source_input_history_invalid") from None

    def _validate_source_input_prefix(
        self, connection: sqlite3.Connection, request: SourceInputRequest, current: SourceContextSnapshot,
    ) -> None:
        """Validate a retained request without manufacturing a receipt/capsule."""
        base = request.snapshot
        count = base.current_turn
        history = current.omitted_turn_ids + current.selected_turn_ids
        if (base.origin != current.origin or count > current.current_turn
                or base.state_revision > current.state_revision
                or base.selected_turn_ids != history[:count][-2:]
                or base.omitted_turn_ids != history[:count][:-2]):
            raise SourceInputPersistenceError("source_input_history_invalid")
        restored = []
        for turn_id in base.selected_turn_ids:
            row = connection.execute("SELECT * FROM turns WHERE session_id=? AND turn_id=?",
                                     (request.session_id, turn_id)).fetchone()
            if row is None:
                raise SourceInputPersistenceError("source_input_history_invalid")
            restored.append(self._restore_narrative_source_row(
                connection, row, request.session_id, ("public", "player"),
            ))
        if _json_dump(restored) != _json_dump(base.sources):
            raise SourceInputPersistenceError("source_input_history_invalid")
        for number, lower in ((count, True), (count + 1, False)):
            if not 1 <= number <= current.current_turn:
                continue
            row = connection.execute(
                """SELECT a.metadata_json FROM attempts a JOIN turns t
                   ON a.session_id=t.session_id AND a.operation_id=t.operation_id
                   WHERE t.session_id=? AND t.turn_number=?""", (request.session_id, number),
            ).fetchone()
            revision = _json_load(row["metadata_json"], {})["source_context_base_state_revision"]
            if lower and base.state_revision <= revision or not lower and base.state_revision > revision:
                raise SourceInputPersistenceError("source_input_history_invalid")
        if (base.current_turn, base.state_revision) == (current.current_turn, current.state_revision):
            row = connection.execute("SELECT state_json,relationships_json FROM campaigns WHERE session_id=?",
                                     (request.session_id,)).fetchone()
            if (_json_dump(request.state) != _json_dump(_json_load(row["state_json"], {}))
                    or _json_dump(request.relationships) != _json_dump(_json_load(row["relationships_json"], {}))):
                raise SourceInputPersistenceError("source_input_stored_pair_invalid")

    def _restore_source_input_row(
        self, connection: sqlite3.Connection, row: sqlite3.Row, current: SourceContextSnapshot,
    ) -> tuple[SourceInputRequest, SourceInputCompletion | None, SourceTurnCapsule | None, sqlite3.Row | None]:
        from .narrative_source_capsule import source_preparation_operation_id, source_preparation_attempt_id
        from .narrative_source_input import (
            REQUEST_KEY, COMPLETION_KEY, SourceInputRequest, SourceInputCompletion, SourceInputFailure,
            source_input_operation_id, source_input_attempt_id, source_input_request_metadata,
            source_input_request_hash, source_input_completion_metadata, source_input_result_hash,
            create_source_input_completion,
        )
        metadata = _json_load(row["metadata_json"], None)
        if not isinstance(metadata, dict) or REQUEST_KEY not in metadata:
            raise ValueError
        request = SourceInputRequest.model_validate(metadata[REQUEST_KEY])
        initial = source_input_request_metadata(request)
        request_hash = source_input_request_hash(request)
        status = row["status"]
        if (request.session_id != current.origin.session_id or row["session_id"] != request.session_id
                or row["operation_id"] != source_input_operation_id(request.session_id, request.operation_id)
                or row["attempt_id"] != source_input_attempt_id(request.session_id, request.operation_id)
                or type(row["requested_turn"]) is not int
                or row["requested_turn"] != request.snapshot.current_turn + 1
                or row["user_input"] != request.player_input or row["partial_narrative"] != ""
                or row["request_hash"] != request_hash or row["payload_hash"] != request_hash
                or row["committed_turn_id"] is not None
                or row["provenance_json"] is not None or row["usage_json"] is not None
                or status not in {"pending", "completed", "failed", "timeout", "cancelled"}):
            raise ValueError
        started = datetime.fromisoformat(row["started_at"])
        if started.utcoffset() is None or started != request.created_at:
            raise ValueError
        self._validate_source_input_prefix(connection, request, current)
        completion = None
        if status == "pending":
            if (row["result_hash"] is not None or row["completed_at"] is not None
                    or row["error_json"] is not None or _json_dump(metadata) != _json_dump(initial)):
                raise ValueError
        else:
            finished = datetime.fromisoformat(row["completed_at"])
            if finished.utcoffset() is None or finished < started:
                raise ValueError
            if set(metadata) == {REQUEST_KEY} and status == "cancelled":
                # Existing explicit startup recovery predates P completion metadata.
                error = {"category": "cancelled", "code": "process_interrupted",
                         "safe_message": "The previous process ended before this operation completed."}
                expected_hash = _payload_hash({
                    "status": "cancelled", "requested_turn": request.snapshot.current_turn + 1,
                    "user_input": request.player_input, "partial_narrative": "", "error": error,
                    "provenance": None, "usage": None, "metadata": initial,
                })
                if (_json_dump(metadata) != _json_dump(initial)
                        or _json_dump(_json_load(row["error_json"], None)) != _json_dump(error)
                        or row["result_hash"] != expected_hash):
                    raise ValueError
                completion = create_source_input_completion(request, status="cancelled",
                    failure=SourceInputFailure(code="process_interrupted"))
            else:
                if set(metadata) != {REQUEST_KEY, COMPLETION_KEY}:
                    raise ValueError
                completion = SourceInputCompletion.model_validate(metadata[COMPLETION_KEY])
                expected_error = None if completion.failure is None else completion.failure.model_dump(mode="json")
                if (completion.status != status
                        or _json_dump(metadata) != _json_dump(source_input_completion_metadata(request, completion))
                        or row["result_hash"] != source_input_result_hash(request, completion)
                        or _json_dump(_json_load(row["error_json"], None)) != _json_dump(expected_error)):
                    raise ValueError
        controls = connection.execute(
            "SELECT * FROM attempts WHERE (session_id=? AND operation_id=?) OR attempt_id=?",
            (request.session_id, source_preparation_operation_id(request.session_id, request.operation_id),
             source_preparation_attempt_id(request.session_id, request.operation_id)),
        ).fetchall()
        attempts = connection.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                                      (request.session_id, request.operation_id)).fetchall()
        turns = connection.execute("SELECT * FROM turns WHERE session_id=? AND operation_id=?",
                                   (request.session_id, request.operation_id)).fetchall()
        if status != "completed":
            if controls or attempts or turns:
                raise ValueError
            return request, completion, None, None
        if len(controls) != 1:
            raise ValueError
        capsule = self._restore_source_preparation_row(
            connection, controls[0], request.session_id, request.operation_id, current,
        )
        expected = create_source_input_completion(request, status="completed", capsule=capsule)
        if _json_dump(completion) != _json_dump(expected):
            raise ValueError
        attempts = connection.execute(
            "SELECT * FROM attempts WHERE (session_id=? AND operation_id=?) OR attempt_id=?",
            (request.session_id, request.operation_id, capsule.draft.attempt_id),
        ).fetchall()
        turns = connection.execute(
            "SELECT * FROM turns WHERE (session_id=? AND operation_id=?) OR attempt_id=? OR turn_id=?",
            (request.session_id, request.operation_id, capsule.draft.attempt_id, capsule.draft.turn_id),
        ).fetchall()
        if len(attempts) > 1 or len(turns) > 1 or turns and not attempts:
            raise ValueError
        h6 = attempts[0] if attempts else None
        if h6 is not None:
            self._validate_source_status_pair(connection, capsule, h6, turns[0] if turns else None)
        return request, completion, capsule, h6

    def _guard_source_input_session(self, connection: sqlite3.Connection, session_id: str,
                                    current: SourceContextSnapshot) -> None:
        from .narrative_source_input import REQUEST_KEY
        occupied = False
        for row in connection.execute("SELECT * FROM attempts WHERE session_id=? ORDER BY id", (session_id,)).fetchall():
            tagged = row["operation_id"].startswith("source-input-operation-") or row["attempt_id"].startswith("source-input-attempt-")
            try:
                metadata = _json_load(row["metadata_json"], None)
            except (ValueError, TypeError, RecursionError):
                if tagged:
                    raise SourceInputPersistenceError("source_input_stored_pair_invalid") from None
                continue
            if not tagged and not (isinstance(metadata, dict) and REQUEST_KEY in metadata):
                continue
            _, _, _, h6 = self._restore_source_input_row(connection, row, current)
            if row["status"] == "pending" or row["status"] == "completed" and (h6 is None or h6["status"] == "pending"):
                occupied = True
        if occupied:
            raise SourceInputPersistenceError("source_input_session_busy")

    def _claim_source_input_sync(self, session_id: str, public: SourcePlayerActionRequest,
                                 config: SourceProducerConfig) -> SourceInputClaim:
        from .narrative_source_capsule import source_preparation_operation_id, source_preparation_attempt_id
        from .narrative_source_input import (
            SourceInputClaim, create_source_input_request, source_input_operation_id, source_input_attempt_id,
            source_input_request_hash, source_input_request_metadata,
        )
        def work(connection: sqlite3.Connection) -> SourceInputClaim:
            rows = self._source_input_control_rows(connection, session_id, public.operation_id)
            if len(rows) > 1:
                raise SourceInputPersistenceError("source_input_stored_pair_invalid")
            current = self._source_input_current(connection, session_id)
            if rows:
                original, completion, _, _ = self._restore_source_input_row(connection, rows[0], current)
                if (original.player_input != public.player_input
                        or _json_dump(original.config) != _json_dump(config)):
                    raise SourceInputPersistenceError("source_input_operation_conflict")
                return SourceInputClaim(request=original, status=rows[0]["status"],
                                        newly_claimed=False, completion=completion)
            # An old internal K/H is not adopted as a producer-backed action.
            for table, sql, args in (
                ("attempts", "(session_id=? AND operation_id IN (?,?)) OR attempt_id=?",
                 (session_id, public.operation_id, source_preparation_operation_id(session_id, public.operation_id),
                  source_preparation_attempt_id(session_id, public.operation_id))),
                ("turns", "session_id=? AND operation_id=?", (session_id, public.operation_id)),
            ):
                if connection.execute(f"SELECT 1 FROM {table} WHERE {sql} LIMIT 1", args).fetchone() is not None:
                    raise SourceInputPersistenceError("source_input_stored_pair_invalid")
            self._guard_source_input_session(connection, session_id, current)
            row = connection.execute("SELECT state_json,relationships_json FROM campaigns WHERE session_id=?",
                                     (session_id,)).fetchone()
            now = _utc_now()
            request = create_source_input_request(session_id, public, created_at=datetime.fromisoformat(now),
                snapshot=current, state=_json_load(row["state_json"], {}),
                relationships=_json_load(row["relationships_json"], {}), producer_config=config)
            digest = source_input_request_hash(request)
            connection.execute(
                """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,user_input,
                       metadata_json,payload_hash,request_hash,result_hash,started_at)
                   VALUES (?,?,?,?,'pending',?,?,?,?,NULL,?)""",
                (source_input_attempt_id(session_id, public.operation_id), session_id,
                 source_input_operation_id(session_id, public.operation_id), current.current_turn + 1,
                 public.player_input, _json_dump(source_input_request_metadata(request)), digest, digest, now),
            )
            return SourceInputClaim(request=request, status="pending", newly_claimed=True)
        return self._source_input_transaction(work)

    def _finalize_source_input_sync(self, session_id: str, operation_id: str, request_hash: str,
                                    completion: SourceInputCompletion, capsule: SourceTurnCapsule | None) -> SourceInputClaim:
        from .narrative_source_capsule import source_preparation_operation_id, source_preparation_attempt_id
        from .narrative_source_input import (
            SourceInputClaim, SourceInputFailure, create_source_input_completion, source_input_request_hash,
            source_input_completion_metadata, source_input_result_hash,
        )
        def work(connection: sqlite3.Connection) -> SourceInputClaim:
            rows = self._source_input_control_rows(connection, session_id, operation_id)
            if not rows:
                raise SourceInputPersistenceError("source_input_claim_missing")
            if len(rows) != 1:
                raise SourceInputPersistenceError("source_input_stored_pair_invalid")
            current = self._source_input_current(connection, session_id)
            request, stored_completion, _, _ = self._restore_source_input_row(connection, rows[0], current)
            if source_input_request_hash(request) != request_hash:
                raise SourceInputPersistenceError("source_input_operation_conflict")
            expected = create_source_input_completion(request, status=completion.status,
                                                     capsule=capsule, failure=completion.failure)
            if _json_dump(expected) != _json_dump(completion):
                raise SourceInputPersistenceError("source_input_operation_conflict")
            if rows[0]["status"] != "pending":
                if _json_dump(stored_completion) != _json_dump(completion):
                    raise SourceInputPersistenceError("source_input_operation_conflict")
                return SourceInputClaim(request=request, status=stored_completion.status,
                                        newly_claimed=False, completion=stored_completion)
            outcome = expected
            if outcome.status == "completed" and (
                request.snapshot.current_turn != current.current_turn
                or request.snapshot.state_revision != current.state_revision
            ):
                outcome = create_source_input_completion(request, status="failed",
                    failure=SourceInputFailure(code="source_input_base_mismatch", stage="finalization"))
            now = _utc_now()
            if outcome.status == "completed":
                metadata, k_request_hash, k_result_hash = self._source_preparation_payloads(capsule)
                connection.execute(
                    """INSERT INTO attempts(attempt_id,session_id,operation_id,requested_turn,status,user_input,
                       partial_narrative,error_json,provenance_json,usage_json,metadata_json,payload_hash,
                       request_hash,result_hash,committed_turn_id,started_at,completed_at)
                       VALUES (?,?,?,?,'completed',?,'',NULL,NULL,NULL,?,?,?,?,NULL,?,?)""",
                    (source_preparation_attempt_id(session_id, operation_id), session_id,
                     source_preparation_operation_id(session_id, operation_id), request.snapshot.current_turn + 1,
                     request.player_input, _json_dump(metadata), k_request_hash, k_request_hash, k_result_hash, now, now),
                )
            error = None if outcome.failure is None else _json_dump(outcome.failure)
            cursor = connection.execute(
                """UPDATE attempts SET status=?,error_json=?,metadata_json=?,result_hash=?,completed_at=?
                   WHERE id=? AND status='pending' AND request_hash=?""",
                (outcome.status, error, _json_dump(source_input_completion_metadata(request, outcome)),
                 source_input_result_hash(request, outcome), now, rows[0]["id"], request_hash),
            )
            if cursor.rowcount != 1:
                raise SourceInputPersistenceError("source_input_operation_conflict")
            return SourceInputClaim(request=request, status=outcome.status, newly_claimed=False, completion=outcome)
        return self._source_input_transaction(work)

    async def ensure_campaign(
        self,
        session_id: str,
        *,
        chronicle_name: str = "",
        initial_state: Any = None,
        relationships: Any = None,
        metadata: Any = None,
    ) -> dict[str, Any]:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            await asyncio.to_thread(
                self._ensure_campaign_sync,
                session_id,
                chronicle_name,
                initial_state,
                relationships,
                metadata,
            )
            campaign = await asyncio.to_thread(self._load_campaign_sync, session_id)
            assert campaign is not None
            return campaign

    def _insert_campaign_if_missing(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        chronicle_name: str,
        initial_state: Any,
        relationships: Any,
        metadata: Any,
    ) -> None:
        now = _utc_now()
        connection.execute(
            """
            INSERT OR IGNORE INTO campaigns(
                session_id, chronicle_name, schema_version, current_turn,
                state_json, relationships_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                chronicle_name,
                SCHEMA_VERSION,
                _json_dump(initial_state or {}),
                _json_dump(relationships or {}),
                _json_dump(metadata or {}),
                now,
                now,
            ),
        )

    def _ensure_campaign_sync(
        self,
        session_id: str,
        chronicle_name: str,
        initial_state: Any,
        relationships: Any,
        metadata: Any,
    ) -> None:
        from .narrative_source_context import ORIGIN_KEY, SourceContextError
        if isinstance(metadata, Mapping) and ORIGIN_KEY in metadata:
            raise SourceContextError("source_context_origin_mutation_forbidden")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._insert_campaign_if_missing(
                    connection,
                    session_id,
                    chronicle_name,
                    initial_state,
                    relationships,
                    metadata,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    async def load_campaign(self, session_id: str) -> dict[str, Any] | None:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(self._load_campaign_sync, session_id)

    async def load_or_migrate_campaign(
        self,
        session_id: str,
        legacy_dir: str | os.PathLike[str],
        *,
        chronicle_name: str = "",
    ) -> dict[str, Any] | None:
        """Load a campaign, importing legacy JSON only when no campaign exists."""
        campaign = await self.load_campaign(session_id)
        if campaign is not None:
            return campaign
        result = await self.migrate_legacy_session(
            session_id, legacy_dir, chronicle_name=chronicle_name
        )
        if result.status == "not_found":
            return None
        return await self.load_campaign(session_id)

    def _load_campaign_sync(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM campaigns WHERE session_id=?", (session_id,)
            ).fetchone()
            if row is None:
                return None
            return _decode_row(row, ("state_json", "relationships_json", "metadata_json"))

    async def update_campaign_snapshot(
        self,
        session_id: str,
        *,
        state: Any,
        relationships: Any | None = None,
        chronicle_name: str | None = None,
        metadata: Any | None = None,
        expected_turn: int | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        """Persist a non-turn snapshot without advancing the canonical turn.

        This is reserved for campaign initialization and deterministic control
        operations such as XP or frenzy resolution. Narrated actions must use
        :meth:`commit_turn` so state, events, narrative and memory stay atomic.
        """

        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            await asyncio.to_thread(
                self._update_campaign_snapshot_sync,
                session_id,
                state,
                relationships,
                chronicle_name,
                metadata,
                expected_turn,
                expected_revision,
            )
            campaign = await asyncio.to_thread(self._load_campaign_sync, session_id)
            assert campaign is not None
            return campaign

    def _update_campaign_snapshot_sync(
        self,
        session_id: str,
        state: Any,
        relationships: Any | None,
        chronicle_name: str | None,
        metadata: Any | None,
        expected_turn: int | None,
        expected_revision: int | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    """SELECT current_turn, state_revision, metadata_json FROM campaigns
                       WHERE session_id=?""",
                    (session_id,),
                ).fetchone()
                from .narrative_source_context import (
                    ORIGIN_KEY, SourceContextError, validate_source_context_origin,
                    validate_source_state_context,
                )
                stored_metadata = _json_load(row["metadata_json"], {}) if row is not None else {}
                from .campaign_source_context import ORIGIN_KEY as CAMPAIGN_SOURCE_ORIGIN_KEY
                from .campaign_source_storage import CampaignSourceStorageError
                if (isinstance(stored_metadata, Mapping)
                        and CAMPAIGN_SOURCE_ORIGIN_KEY in stored_metadata
                        or isinstance(metadata, Mapping)
                        and CAMPAIGN_SOURCE_ORIGIN_KEY in metadata):
                    raise CampaignSourceStorageError("campaign_source_snapshot_mutation_forbidden")
                old_origin = stored_metadata.get(ORIGIN_KEY) if isinstance(stored_metadata, Mapping) else None
                has_origin = isinstance(stored_metadata, Mapping) and ORIGIN_KEY in stored_metadata
                if has_origin:
                    origin = validate_source_context_origin(old_origin, session_id=session_id)
                    if metadata is not None and (
                        not isinstance(metadata, Mapping) or ORIGIN_KEY not in metadata
                        or _json_dump(metadata[ORIGIN_KEY]) != _json_dump(old_origin)
                    ):
                        raise SourceContextError("source_context_origin_mutation_forbidden")
                    validate_source_state_context(_plain(state), origin)
                elif isinstance(metadata, Mapping) and ORIGIN_KEY in metadata:
                    raise SourceContextError("source_context_origin_mutation_forbidden")
                if row is None:
                    if expected_revision not in (None, 0):
                        raise StateRevisionError(
                            f"Expected state revision {expected_revision} for a new campaign"
                        )
                    self._insert_campaign_if_missing(
                        connection,
                        session_id,
                        chronicle_name or "",
                        state,
                        relationships or {},
                        metadata or {},
                    )
                    connection.commit()
                    return

                if expected_revision is None:
                    raise StateRevisionError(
                        "expected_revision is required for an existing campaign snapshot"
                    )
                current_revision = int(row["state_revision"])
                if current_revision != expected_revision:
                    raise StateRevisionError(
                        f"Expected state revision {expected_revision} does not match "
                        f"current revision {current_revision}"
                    )
                if expected_turn is not None and int(row["current_turn"]) != expected_turn:
                    raise TurnSequenceError(
                        f"Expected turn {expected_turn} does not match current turn "
                        f"{row['current_turn']}"
                    )

                assignments = [
                    "state_json=?",
                    "updated_at=?",
                    "state_revision=state_revision+1",
                ]
                values: list[Any] = [_json_dump(state), _utc_now()]
                if relationships is not None:
                    assignments.append("relationships_json=?")
                    values.append(_json_dump(relationships))
                if chronicle_name is not None:
                    assignments.append("chronicle_name=?")
                    values.append(chronicle_name)
                if metadata is not None:
                    assignments.append("metadata_json=?")
                    values.append(_json_dump(metadata))
                values.extend((session_id, expected_revision))
                cursor = connection.execute(
                    f"""UPDATE campaigns SET {', '.join(assignments)}
                        WHERE session_id=? AND state_revision=?""",
                    tuple(values),
                )
                if cursor.rowcount != 1:
                    raise StateRevisionError(
                        "Campaign state revision changed during snapshot update"
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    async def start_attempt(
        self,
        *,
        session_id: str,
        operation_id: str,
        attempt_id: str | None = None,
        requested_turn: int | None = None,
        user_input: str = "",
        metadata: Any = None,
        chronicle_name: str = "",
    ) -> AttemptResult:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._start_attempt_sync,
                session_id,
                operation_id,
                attempt_id or f"attempt-{operation_id}",
                requested_turn,
                user_input,
                metadata,
                chronicle_name,
            )

    def _start_attempt_sync(
        self,
        session_id: str,
        operation_id: str,
        attempt_id: str,
        requested_turn: int | None,
        user_input: str,
        metadata: Any,
        chronicle_name: str,
    ) -> AttemptResult:
        request_digest = _payload_hash(
            _attempt_request_payload(requested_turn, user_input, metadata)
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._insert_campaign_if_missing(
                    connection, session_id, chronicle_name, {}, {}, {}
                )
                existing = connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["request_hash"] != request_digest
                        or existing["attempt_id"] != attempt_id
                    ):
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} was already started with different data"
                        )
                    connection.commit()
                    return AttemptResult(
                        session_id, operation_id, attempt_id, existing["status"], True
                    )
                connection.execute(
                    """
                    INSERT INTO attempts(
                        attempt_id, session_id, operation_id, requested_turn, status,
                        user_input, metadata_json, payload_hash, request_hash,
                        result_hash, started_at
                    ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        attempt_id,
                        session_id,
                        operation_id,
                        requested_turn,
                        user_input,
                        _json_dump(metadata or {}),
                        request_digest,
                        request_digest,
                        _utc_now(),
                    ),
                )
                connection.commit()
                return AttemptResult(session_id, operation_id, attempt_id, "pending")
            except Exception:
                connection.rollback()
                raise

    async def record_failed_attempt(
        self,
        *,
        session_id: str,
        operation_id: str,
        status: str = "failed",
        attempt_id: str | None = None,
        requested_turn: int | None = None,
        user_input: str = "",
        partial_narrative: str = "",
        error: Any = None,
        provenance: Any = None,
        usage: Any = None,
        metadata: Any = None,
        chronicle_name: str = "",
    ) -> AttemptResult:
        if status not in _TERMINAL_FAILURE_STATUSES:
            raise ValueError(f"Failure status must be one of {sorted(_TERMINAL_FAILURE_STATUSES)}")
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._record_failed_attempt_sync,
                session_id,
                operation_id,
                status,
                attempt_id or f"attempt-{operation_id}",
                requested_turn,
                user_input,
                partial_narrative,
                error,
                provenance,
                usage,
                metadata,
                chronicle_name,
            )

    def _record_failed_attempt_sync(
        self,
        session_id: str,
        operation_id: str,
        status: str,
        attempt_id: str,
        requested_turn: int | None,
        user_input: str,
        partial_narrative: str,
        error: Any,
        provenance: Any,
        usage: Any,
        metadata: Any,
        chronicle_name: str,
    ) -> AttemptResult:
        terminal_payload = {
            "status": status,
            "requested_turn": requested_turn,
            "user_input": user_input,
            "partial_narrative": partial_narrative,
            "error": error,
            "provenance": provenance,
            "usage": usage,
            "metadata": metadata or {},
        }
        result_digest = _payload_hash(terminal_payload)
        direct_request_digest = _payload_hash(
            _attempt_request_payload(requested_turn, user_input)
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._insert_campaign_if_missing(
                    connection, session_id, chronicle_name, {}, {}, {}
                )
                existing = connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                if existing is not None:
                    if existing["status"] == "completed":
                        raise IdempotencyConflictError(
                            f"Completed operation {operation_id!r} cannot become {status}"
                        )
                    if existing["status"] in _TERMINAL_FAILURE_STATUSES:
                        if (
                            existing["result_hash"] != result_digest
                            or existing["status"] != status
                            or existing["attempt_id"] != attempt_id
                        ):
                            raise IdempotencyConflictError(
                                f"Operation {operation_id!r} already has a different terminal failure"
                            )
                        connection.commit()
                        return AttemptResult(
                            session_id, operation_id, existing["attempt_id"], status, True
                        )
                    if existing["attempt_id"] != attempt_id:
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} uses a different attempt id"
                        )
                    if (
                        existing["requested_turn"] != requested_turn
                        or existing["user_input"] != user_input
                    ):
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} failure does not match its request"
                        )
                    connection.execute(
                        """
                        UPDATE attempts SET status=?, partial_narrative=?, error_json=?,
                            provenance_json=?, usage_json=?,
                            metadata_json=?, result_hash=?, completed_at=?
                        WHERE id=?
                        """,
                        (
                            status,
                            partial_narrative,
                            _json_dump(error) if error is not None else None,
                            _json_dump(provenance) if provenance is not None else None,
                            _json_dump(usage) if usage is not None else None,
                            _json_dump(metadata or {}),
                            result_digest,
                            _utc_now(),
                            existing["id"],
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO attempts(
                            attempt_id, session_id, operation_id, requested_turn, status,
                            user_input, partial_narrative, error_json, provenance_json,
                            usage_json, metadata_json, payload_hash, request_hash,
                            result_hash, started_at, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            attempt_id,
                            session_id,
                            operation_id,
                            requested_turn,
                            status,
                            user_input,
                            partial_narrative,
                            _json_dump(error) if error is not None else None,
                            _json_dump(provenance) if provenance is not None else None,
                            _json_dump(usage) if usage is not None else None,
                            _json_dump(metadata or {}),
                            direct_request_digest,
                            direct_request_digest,
                            result_digest,
                            _utc_now(),
                            _utc_now(),
                        ),
                    )
                connection.commit()
                return AttemptResult(session_id, operation_id, attempt_id, status)
            except Exception:
                connection.rollback()
                raise

    async def recover_pending_attempts(self, *, started_before: datetime) -> int:
        """Cancel attempts inherited from a previous single-worker process.

        This operation is intentionally explicit instead of part of
        :meth:`initialize`: a second repository object in the same live
        process must never mistake active work for a crashed process. The app
        startup lifecycle calls it with the process start time before accepting
        requests, so attempts created by this process are never reclaimed.
        """

        if started_before.tzinfo is None or started_before.utcoffset() is None:
            raise ValueError("started_before must be timezone-aware")
        cutoff = started_before.astimezone(timezone.utc).isoformat()
        await self.initialize()
        return await asyncio.to_thread(self._recover_pending_attempts_sync, cutoff)

    def _recover_pending_attempts_sync(self, cutoff: str) -> int:
        error = {
            "category": "cancelled",
            "code": "process_interrupted",
            "safe_message": (
                "The previous process ended before this operation completed."
            ),
        }
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """SELECT * FROM attempts
                       WHERE status='pending' AND started_at < ? ORDER BY id""",
                    (cutoff,),
                ).fetchall()
                now = _utc_now()
                for row in rows:
                    metadata = _json_load(row["metadata_json"], {})
                    provenance = _json_load(row["provenance_json"], None)
                    usage = _json_load(row["usage_json"], None)
                    result_digest = _payload_hash(
                        {
                            "status": "cancelled",
                            "requested_turn": row["requested_turn"],
                            "user_input": row["user_input"],
                            "partial_narrative": row["partial_narrative"],
                            "error": error,
                            "provenance": provenance,
                            "usage": usage,
                            "metadata": metadata,
                        }
                    )
                    connection.execute(
                        """UPDATE attempts SET status='cancelled', error_json=?,
                                  result_hash=?, completed_at=?
                           WHERE id=? AND status='pending'""",
                        (_json_dump(error), result_digest, now, row["id"]),
                    )
                connection.commit()
                return len(rows)
            except Exception:
                connection.rollback()
                raise

    async def complete_control_attempt(
        self,
        *,
        session_id: str,
        operation_id: str,
        attempt_id: str | None = None,
        requested_turn: int | None = None,
        user_input: str = "",
        state: Any | None = None,
        expected_turn: int | None = None,
        expected_state_revision: int | None = None,
        metadata: Any = None,
        provenance: Any = None,
        usage: Any = None,
        chronicle_name: str = "",
    ) -> AttemptResult:
        """Complete a non-turn interceptor attempt without inventing a turn id."""

        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._complete_control_attempt_sync,
                session_id,
                operation_id,
                attempt_id or f"attempt-{operation_id}",
                requested_turn,
                user_input,
                state,
                expected_turn,
                expected_state_revision,
                metadata,
                provenance,
                usage,
                chronicle_name,
            )

    def _complete_control_attempt_sync(
        self,
        session_id: str,
        operation_id: str,
        attempt_id: str,
        requested_turn: int | None,
        user_input: str,
        state: Any | None,
        expected_turn: int | None,
        expected_state_revision: int | None,
        metadata: Any,
        provenance: Any,
        usage: Any,
        chronicle_name: str,
    ) -> AttemptResult:
        terminal_payload = {
            "status": "completed",
            "requested_turn": requested_turn,
            "user_input": user_input,
            "metadata": metadata or {},
            "provenance": provenance,
            "usage": usage,
            "snapshot": (
                {
                    "state": state,
                    "expected_turn": expected_turn,
                    "expected_state_revision": expected_state_revision,
                }
                if state is not None
                else None
            ),
        }
        result_digest = _payload_hash(terminal_payload)
        request_digest = _payload_hash(
            _attempt_request_payload(requested_turn, user_input)
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._insert_campaign_if_missing(
                    connection, session_id, chronicle_name, {}, {}, {}
                )
                existing = connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                campaign = connection.execute(
                    """SELECT current_turn, state_revision, metadata_json FROM campaigns
                       WHERE session_id=?""",
                    (session_id,),
                ).fetchone()
                assert campaign is not None
                from .narrative_source_context import (
                    ORIGIN_KEY, validate_source_context_origin, validate_source_state_context,
                )
                campaign_metadata = _json_load(campaign["metadata_json"], {})
                if isinstance(campaign_metadata, Mapping) and ORIGIN_KEY in campaign_metadata:
                    origin = validate_source_context_origin(
                        campaign_metadata[ORIGIN_KEY], session_id=session_id,
                    )
                    if state is not None:
                        validate_source_state_context(_plain(state), origin)
                if existing is not None:
                    if existing["status"] == "completed":
                        if (
                            existing["committed_turn_id"] is not None
                            or existing["result_hash"] != result_digest
                            or existing["attempt_id"] != attempt_id
                            or existing["requested_turn"] != requested_turn
                            or existing["user_input"] != user_input
                        ):
                            raise IdempotencyConflictError(
                                f"Operation {operation_id!r} has a different completed result"
                            )
                        connection.commit()
                        return AttemptResult(
                            session_id,
                            operation_id,
                            existing["attempt_id"],
                            "completed",
                            True,
                            int(campaign["state_revision"]),
                        )
                    if existing["status"] in _TERMINAL_FAILURE_STATUSES:
                        raise IdempotencyConflictError(
                            f"Failed operation {operation_id!r} cannot become completed"
                        )
                    if (
                        existing["attempt_id"] != attempt_id
                        or existing["requested_turn"] != requested_turn
                        or existing["user_input"] != user_input
                    ):
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} completion does not match its request"
                        )

                next_state_revision = int(campaign["state_revision"])
                if (
                    state is not None
                    or expected_turn is not None
                    or expected_state_revision is not None
                ):
                    if expected_turn is None or expected_state_revision is None:
                        raise StateRevisionError(
                            "Control completion CAS requires expected_turn and "
                            "expected_state_revision together"
                        )
                    if int(campaign["current_turn"]) != expected_turn:
                        raise TurnSequenceError(
                            f"Expected turn {expected_turn} does not match current turn "
                            f"{campaign['current_turn']}"
                        )
                    if int(campaign["state_revision"]) != expected_state_revision:
                        raise StateRevisionError(
                            f"Expected state revision {expected_state_revision} does not "
                            f"match current revision {campaign['state_revision']}"
                        )
                if state is not None:
                    cursor = connection.execute(
                        """UPDATE campaigns SET state_json=?,
                                  state_revision=state_revision+1, updated_at=?
                           WHERE session_id=? AND current_turn=? AND state_revision=?""",
                        (
                            _json_dump(state),
                            _utc_now(),
                            session_id,
                            expected_turn,
                            expected_state_revision,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise StateRevisionError(
                            "Campaign changed during atomic control completion"
                        )
                    next_state_revision += 1

                if existing is not None:
                    connection.execute(
                        """UPDATE attempts SET status='completed', partial_narrative='',
                                  error_json=NULL, provenance_json=?, usage_json=?,
                                  metadata_json=?, result_hash=?, committed_turn_id=NULL,
                                  completed_at=?
                           WHERE id=?""",
                        (
                            _json_dump(provenance) if provenance is not None else None,
                            _json_dump(usage) if usage is not None else None,
                            _json_dump(metadata or {}),
                            result_digest,
                            _utc_now(),
                            existing["id"],
                        ),
                    )
                else:
                    now = _utc_now()
                    connection.execute(
                        """INSERT INTO attempts(
                               attempt_id, session_id, operation_id, requested_turn,
                               status, user_input, partial_narrative, error_json,
                               provenance_json, usage_json, metadata_json, payload_hash,
                               request_hash, result_hash, committed_turn_id,
                               started_at, completed_at
                           ) VALUES (?, ?, ?, ?, 'completed', ?, '', NULL, ?, ?, ?,
                                     ?, ?, ?, NULL, ?, ?)""",
                        (
                            attempt_id,
                            session_id,
                            operation_id,
                            requested_turn,
                            user_input,
                            _json_dump(provenance) if provenance is not None else None,
                            _json_dump(usage) if usage is not None else None,
                            _json_dump(metadata or {}),
                            request_digest,
                            request_digest,
                            result_digest,
                            now,
                            now,
                        ),
                    )
                connection.commit()
                return AttemptResult(
                    session_id,
                    operation_id,
                    attempt_id,
                    "completed",
                    False,
                    next_state_revision,
                )
            except Exception:
                connection.rollback()
                raise

    async def commit_turn(
        self,
        *,
        session_id: str,
        operation_id: str,
        turn_id: str,
        state: Any,
        narrative: Any,
        facts: Sequence[Any] = (),
        events: Sequence[Any] = (),
        memory_candidates: Sequence[Any] = (),
        episodic_memories: Sequence[Any] = (),
        relationships: Any = None,
        context: Any = None,
        provenance: Any = None,
        usage: Any = None,
        user_input: str = "",
        attempt_id: str | None = None,
        turn_number: int | None = None,
        base_revision: int | None = None,
        base_state_revision: int | None = None,
        chronicle_name: str = "",
        narrative_contract: str | None = None,
    ) -> CommitResult:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._commit_turn_sync,
                session_id,
                operation_id,
                turn_id,
                state,
                narrative,
                facts,
                events,
                memory_candidates,
                episodic_memories,
                relationships,
                context,
                provenance,
                usage,
                user_input,
                attempt_id or f"attempt-{operation_id}",
                turn_number,
                base_revision,
                base_state_revision,
                chronicle_name,
                narrative_contract,
            )

    def _commit_turn_sync(
        self,
        session_id: str,
        operation_id: str,
        turn_id: str,
        state: Any,
        narrative: Any,
        facts: Sequence[Any],
        events: Sequence[Any],
        memory_candidates: Sequence[Any],
        episodic_memories: Sequence[Any],
        relationships: Any,
        context: Any,
        provenance: Any,
        usage: Any,
        user_input: str,
        attempt_id: str,
        requested_turn: int | None,
        base_revision: int | None,
        base_state_revision: int | None,
        chronicle_name: str,
        narrative_contract: str | None,
    ) -> CommitResult:
        if narrative_contract is not None or (
            isinstance(context, Mapping) and "narrative_source" in context
        ):
            # Snapshot the new envelope and its audit before validation/digest.
            context = _plain(context)
            provenance = _plain(provenance)
        narrative_payload = _plain(narrative)
        if not isinstance(narrative_payload, Mapping):
            raise ValueError("Narrative must be a structured object")
        narrative_payload = dict(narrative_payload)
        narrative_text = narrative_payload.get("text")
        if not isinstance(narrative_text, str) or not narrative_text.strip():
            raise ValueError("A canonical turn requires a non-empty narrative")
        if narrative_payload.get("complete") is not True:
            raise ValueError("Only a complete narrative can promote a canonical turn")
        if _required_text(narrative_payload, "session_id") != session_id:
            raise ValueError("Narrative session_id does not match commit session_id")
        if _required_text(narrative_payload, "turn_id") != turn_id:
            raise ValueError("Narrative turn_id does not match commit turn_id")

        narrative_source_ids = _id_sequence(
            narrative_payload.get("source_event_ids", []),
            "narrative.source_event_ids",
            required=True,
        )
        narrative_payload["source_event_ids"] = sorted(narrative_source_ids)
        narrative_visibility = _visibility(
            narrative_payload.get("visibility", "player"), "narrative"
        )
        narrative_payload["visibility"] = narrative_visibility

        fact_payloads = _mapping_payloads(facts, "canonical fact")
        event_payloads = _mapping_payloads(events, "canonical event")
        candidate_payloads = _mapping_payloads(memory_candidates, "memory candidate")
        memory_payloads = _mapping_payloads(episodic_memories, "episodic memory")

        fact_payloads.sort(key=lambda fact: _required_text(fact, "fact_id"))
        event_payloads.sort(
            key=lambda event: (
                int(event.get("sequence", 0)),
                _required_text(event, "event_id"),
            )
        )
        candidate_payloads.sort(
            key=lambda candidate: _required_text(candidate, "candidate_id")
        )
        memory_payloads.sort(key=lambda memory: _required_text(memory, "memory_id"))

        for event in event_payloads:
            if _required_text(event, "session_id") != session_id:
                raise ValueError("Event session_id does not match commit session_id")
            if _required_text(event, "turn_id") != turn_id:
                raise ValueError("Event turn_id does not match commit turn_id")
        fact_by_id = {
            _required_text(fact, "fact_id"): fact for fact in fact_payloads
        }
        if len(fact_by_id) != len(fact_payloads):
            raise ValueError("Canonical fact ids must be unique within a turn")
        for fact in fact_payloads:
            fact["visibility"] = _visibility(
                fact.get("visibility", "player"), "canonical fact"
            )
        event_by_id = {
            _required_text(event, "event_id"): event for event in event_payloads
        }
        if len(event_by_id) != len(event_payloads):
            raise ValueError("Canonical event ids must be unique within a turn")
        event_sequences = [int(event.get("sequence", 0)) for event in event_payloads]
        if len(event_sequences) != len(set(event_sequences)):
            raise ValueError("Canonical event sequences must be unique within a turn")

        for event in event_payloads:
            event_fact_ids = _id_sequence(
                event.get("fact_ids", []), "event.fact_ids", required=False
            )
            event["fact_ids"] = sorted(event_fact_ids)
            unknown = set(event_fact_ids) - set(fact_by_id)
            if unknown:
                raise ValueError(
                    f"Event {event['event_id']!r} references unknown facts: {sorted(unknown)}"
                )
            source_visibilities = [
                _visibility(event.get("visibility", "player"), "event")
            ]
            source_visibilities.extend(
                _visibility(fact_by_id[fact_id].get("visibility", "player"), "fact")
                for fact_id in event_fact_ids
            )
            event_visibility = source_visibilities[0]
            event["visibility"] = event_visibility
            if _VISIBILITY_RESTRICTION[event_visibility] < max(
                _VISIBILITY_RESTRICTION[value] for value in source_visibilities
            ):
                raise ValueError("Canonical event cannot broaden fact visibility")

        event_ids = set(event_by_id)
        unknown_narrative_sources = set(narrative_source_ids) - event_ids
        if unknown_narrative_sources:
            raise ValueError(
                "Narrative references unknown events: "
                f"{sorted(unknown_narrative_sources)}"
            )

        narrative_source_visibilities: list[str] = []
        for event_id in narrative_source_ids:
            event = event_by_id[event_id]
            narrative_source_visibilities.append(event["visibility"])
            narrative_source_visibilities.extend(
                _visibility(fact_by_id[fact_id].get("visibility", "player"), "fact")
                for fact_id in event["fact_ids"]
            )
        if _VISIBILITY_RESTRICTION[narrative_visibility] < max(
            _VISIBILITY_RESTRICTION[value] for value in narrative_source_visibilities
        ):
            raise ValueError("Narrative cannot broaden source visibility")

        candidate_ids = [
            _required_text(candidate, "candidate_id") for candidate in candidate_payloads
        ]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Memory candidate ids must be unique within a turn")
        memory_ids = [_required_text(memory, "memory_id") for memory in memory_payloads]
        if len(memory_ids) != len(set(memory_ids)):
            raise ValueError("Episodic memory ids must be unique within a turn")

        accepted_candidates_by_key: dict[str, list[str]] = {}
        for candidate in candidate_payloads:
            source_ids = _id_sequence(
                candidate.get("source_event_ids", []),
                "candidate.source_event_ids",
                required=True,
            )
            candidate["source_event_ids"] = sorted(source_ids)
            unknown = set(source_ids) - event_ids
            if unknown:
                raise ValueError(
                    f"Memory candidate {candidate.get('candidate_id')!r} references "
                    f"unknown events: {sorted(unknown)}"
                )
            if not set(source_ids) <= set(narrative_source_ids):
                raise ValueError("Memory candidate sources must be covered by the narrative")
            status = str(candidate.get("validation_status", ""))
            if status not in _FINAL_CANDIDATE_STATUSES:
                raise ValueError("Memory candidates must have a final validation status")
            candidate_visibility = _visibility(
                candidate.get("visibility", "player"), "memory candidate"
            )
            candidate["visibility"] = candidate_visibility
            source_visibilities = [narrative_visibility]
            for event_id in source_ids:
                event = event_by_id[event_id]
                source_visibilities.append(event["visibility"])
                source_visibilities.extend(
                    _visibility(fact_by_id[fact_id].get("visibility", "player"), "fact")
                    for fact_id in event["fact_ids"]
                )
            if _VISIBILITY_RESTRICTION[candidate_visibility] < max(
                _VISIBILITY_RESTRICTION[value] for value in source_visibilities
            ):
                raise ValueError("Memory candidate cannot broaden source visibility")
            if status == "accepted":
                accepted_candidates_by_key.setdefault(
                    _derived_memory_key(candidate), []
                ).append(candidate["candidate_id"])

        for memory in memory_payloads:
            source_ids = _id_sequence(
                memory.get("source_event_ids", []),
                "memory.source_event_ids",
                required=True,
            )
            memory["source_event_ids"] = sorted(source_ids)
            unknown = set(source_ids) - event_ids
            if unknown:
                raise ValueError(
                    f"Episodic memory {memory.get('memory_id')!r} references "
                    f"unknown events in its committed turn: {sorted(unknown)}"
                )
            memory["visibility"] = _visibility(
                memory.get("visibility", "player"), "episodic memory"
            )
            derivation_key = _derived_memory_key(memory)
            matching_candidates = accepted_candidates_by_key.get(derivation_key, [])
            if not matching_candidates:
                raise ValueError(
                    "Each episodic memory must be derived from one accepted memory candidate"
                )
            matching_candidates.pop(0)

        unpromoted_candidate_ids = sorted(
            candidate_id
            for candidate_ids_for_key in accepted_candidates_by_key.values()
            for candidate_id in candidate_ids_for_key
        )
        if unpromoted_candidate_ids:
            raise ValueError(
                "Accepted memory candidates must be promoted exactly once: "
                f"{unpromoted_candidate_ids}"
            )

        for item in (*candidate_payloads, *memory_payloads):
            if _required_text(item, "session_id") != session_id:
                raise ValueError("Memory session_id does not match commit session_id")
        for candidate in candidate_payloads:
            if _required_text(candidate, "turn_id") != turn_id:
                raise ValueError("Memory turn_id does not match commit turn_id")

        payload = {
            "turn_id": turn_id,
            "state": state,
            "narrative": narrative_payload,
            "facts": fact_payloads,
            "events": event_payloads,
            "memory_candidates": candidate_payloads,
            "episodic_memories": memory_payloads,
            "relationships": relationships,
            "context": context or {},
            "provenance": provenance,
            "usage": usage,
            "user_input": user_input,
            "requested_turn": requested_turn,
            "base_revision": base_revision,
            "base_state_revision": base_state_revision,
        }
        result_digest = _payload_hash(payload)

        def validate_source_obligation(connection: sqlite3.Connection) -> None:
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                (session_id, operation_id),
            ).fetchone()
            _validate_narrative_source_obligation(
                narrative_contract=narrative_contract, attempt=attempt,
                context=context, narrative=narrative_payload, session_id=session_id,
                operation_id=operation_id, turn_id=turn_id, attempt_id=attempt_id,
                requested_turn=requested_turn, user_input=user_input,
                facts=fact_payloads, events=event_payloads,
                memory_candidates=candidate_payloads, episodic_memories=memory_payloads,
                provenance=provenance,
            )

        with self._connect() as connection:
            validate_source_obligation(connection)
            connection.execute("BEGIN IMMEDIATE")
            try:
                # Recheck the reserved obligation under the transaction, including
                # before an idempotent return. Removing both arguments is no bypass.
                validate_source_obligation(connection)
                from .campaign_source_storage import validate_campaign_commit_in_connection
                validate_campaign_commit_in_connection(
                    connection, session_id=session_id, operation_id=operation_id,
                    attempt_id=attempt_id, turn_id=turn_id,
                    narrative_contract=narrative_contract, requested_turn=requested_turn,
                    base_revision=base_revision, base_state_revision=base_state_revision,
                    user_input=user_input, state=state, relationships=relationships,
                    context=context, narrative=narrative_payload, facts=fact_payloads,
                    events=event_payloads, memory_candidates=candidate_payloads,
                    episodic_memories=memory_payloads, provenance=provenance,
                )
                self._validate_source_campaign_commit(
                    connection, session_id=session_id, narrative_contract=narrative_contract,
                    context=context, state=state, requested_turn=requested_turn,
                    base_state_revision=base_state_revision, operation_id=operation_id,
                )
                existing_turn = connection.execute(
                    "SELECT * FROM turns WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                if existing_turn is not None:
                    if (
                        existing_turn["payload_hash"] != result_digest
                        or existing_turn["turn_id"] != turn_id
                    ):
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} was committed with different data"
                        )
                    if narrative_contract is not None:
                        # A B replay also requires the stored terminal pair;
                        # matching the caller's digest alone is insufficient.
                        replay_attempt = connection.execute(
                            "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                            (session_id, operation_id),
                        ).fetchone()
                        if (
                            replay_attempt is None
                            or replay_attempt["status"] != "completed"
                            or replay_attempt["committed_turn_id"] != existing_turn["turn_id"]
                            or replay_attempt["attempt_id"] != existing_turn["attempt_id"]
                            or replay_attempt["result_hash"] != existing_turn["payload_hash"]
                            or replay_attempt["provenance_json"] != existing_turn["provenance_json"]
                        ):
                            from .narrative_source_turn import SourceTurnContractError
                            raise SourceTurnContractError("source_turn_stored_pair_mismatch")
                    connection.commit()
                    return CommitResult(
                        session_id,
                        operation_id,
                        existing_turn["turn_id"],
                        existing_turn["turn_number"],
                        True,
                    )

                self._insert_campaign_if_missing(
                    connection, session_id, chronicle_name, {}, {}, {}
                )
                campaign = connection.execute(
                    "SELECT * FROM campaigns WHERE session_id=?", (session_id,)
                ).fetchone()
                assert campaign is not None
                current_turn = int(campaign["current_turn"])
                current_state_revision = int(campaign["state_revision"])
                effective_relationships = (
                    _json_load(campaign["relationships_json"], {})
                    if relationships is None
                    else relationships
                )
                if base_revision is not None and base_revision != current_turn:
                    raise TurnSequenceError(
                        f"Base revision {base_revision} does not match current turn {current_turn}"
                    )
                expected_state_revision = (
                    current_state_revision
                    if base_state_revision is None
                    else base_state_revision
                )
                if expected_state_revision != current_state_revision:
                    raise StateRevisionError(
                        f"Base state revision {expected_state_revision} does not match "
                        f"current revision {current_state_revision}"
                    )
                next_turn = current_turn + 1
                if requested_turn is not None and requested_turn != next_turn:
                    raise TurnSequenceError(
                        f"Requested turn {requested_turn} is not next turn {next_turn}"
                    )

                existing_attempt = connection.execute(
                    "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                    (session_id, operation_id),
                ).fetchone()
                if existing_attempt is not None:
                    if existing_attempt["status"] in _TERMINAL_FAILURE_STATUSES:
                        raise IdempotencyConflictError(
                            f"Failed operation {operation_id!r} must be retried with a new operation id"
                        )
                    if existing_attempt["attempt_id"] != attempt_id:
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} uses a different attempt id"
                        )
                    if existing_attempt["status"] == "completed":
                        raise IdempotencyConflictError(
                            f"Completed operation {operation_id!r} has no matching turn"
                        )
                    if (
                        existing_attempt["requested_turn"] not in (None, next_turn)
                        or existing_attempt["user_input"] != user_input
                    ):
                        raise IdempotencyConflictError(
                            f"Operation {operation_id!r} commit does not match its request"
                        )
                else:
                    request_digest = _payload_hash(
                        _attempt_request_payload(next_turn, user_input)
                    )
                    connection.execute(
                        """
                        INSERT INTO attempts(
                            attempt_id, session_id, operation_id, requested_turn, status,
                            user_input, metadata_json, payload_hash, request_hash,
                            result_hash, started_at
                        ) VALUES (?, ?, ?, ?, 'pending', ?, '{}', ?, ?, NULL, ?)
                        """,
                        (
                            attempt_id,
                            session_id,
                            operation_id,
                            next_turn,
                            user_input,
                            request_digest,
                            request_digest,
                            _utc_now(),
                        ),
                    )

                now = _utc_now()
                connection.execute(
                    """
                    INSERT INTO turns(
                        turn_id, session_id, operation_id, attempt_id, turn_number,
                        user_input, narrative_text, narrative_complete, narrative_json,
                        facts_json, context_json, state_json, relationships_json, provenance_json,
                        usage_json, payload_hash, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        turn_id,
                        session_id,
                        operation_id,
                        attempt_id,
                        next_turn,
                        user_input,
                        narrative_text,
                        _json_dump(narrative_payload),
                        _json_dump(fact_payloads),
                        _json_dump(context or {}),
                        _json_dump(state),
                        _json_dump(effective_relationships),
                        _json_dump(provenance) if provenance is not None else None,
                        _json_dump(usage) if usage is not None else None,
                        result_digest,
                        now,
                    ),
                )

                for index, event in enumerate(event_payloads):
                    self._insert_event(connection, session_id, turn_id, next_turn, index, event)
                for candidate in candidate_payloads:
                    self._insert_memory_candidate(
                        connection, session_id, turn_id, next_turn, candidate
                    )
                for memory in memory_payloads:
                    self._insert_episodic_memory(
                        connection, session_id, turn_id, next_turn, memory
                    )

                cursor = connection.execute(
                    """
                    UPDATE campaigns SET current_turn=?, state_json=?, relationships_json=?,
                        state_revision=state_revision+1,
                        chronicle_name=CASE WHEN ? <> '' THEN ? ELSE chronicle_name END,
                        updated_at=?
                    WHERE session_id=? AND current_turn=? AND state_revision=?
                    """,
                    (
                        next_turn,
                        _json_dump(state),
                        _json_dump(effective_relationships),
                        chronicle_name,
                        chronicle_name,
                        now,
                        session_id,
                        current_turn,
                        expected_state_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise StateRevisionError(
                        "Campaign changed during canonical turn commit"
                    )
                connection.execute(
                    """
                    UPDATE attempts SET status='completed', partial_narrative='',
                        error_json=NULL, provenance_json=?, usage_json=?,
                        result_hash=?, committed_turn_id=?, completed_at=?
                    WHERE session_id=? AND operation_id=?
                    """,
                    (
                        _json_dump(provenance) if provenance is not None else None,
                        _json_dump(usage) if usage is not None else None,
                        result_digest,
                        turn_id,
                        now,
                        session_id,
                        operation_id,
                    ),
                )
                connection.commit()
                return CommitResult(session_id, operation_id, turn_id, next_turn)
            except Exception:
                connection.rollback()
                raise

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        turn_id: str,
        turn_number: int,
        fallback_sequence: int,
        event: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO events(
                event_id, session_id, turn_id, turn_number, sequence, event_type,
                summary, fact_ids_json, tags_json, actors_json, place_json, importance,
                visibility, references_json, pending, occurred_at, payload_json,
                schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _required_text(event, "event_id"),
                session_id,
                turn_id,
                turn_number,
                int(event.get("sequence", fallback_sequence)),
                _required_text(event, "event_type"),
                event.get("summary"),
                _json_dump(event.get("fact_ids", [])),
                _json_dump(event.get("tags", [])),
                _json_dump(event.get("actors", [])),
                _json_dump(event.get("place")) if event.get("place") is not None else None,
                float(event.get("importance", 0)),
                _normalize_visibility(event.get("visibility")),
                _json_dump(event.get("references", [])),
                int(bool(event.get("pending", False))),
                str(event.get("occurred_at") or _utc_now()),
                _json_dump(event),
                str(event.get("schema_version", "1.0")),
            ),
        )

    def _insert_memory_candidate(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        turn_id: str,
        turn_number: int,
        candidate: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO memory_candidates(
                candidate_id, session_id, turn_id, turn_number, summary,
                source_event_ids_json, tags_json, actors_json, place_json,
                occurred_at, importance, visibility, pending, proposed_by,
                validation_status, validation_notes_json, payload_json,
                schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _required_text(candidate, "candidate_id"),
                session_id,
                turn_id,
                turn_number,
                _required_text(candidate, "summary"),
                _json_dump(candidate.get("source_event_ids", [])),
                _json_dump(candidate.get("tags", [])),
                _json_dump(candidate.get("actors", [])),
                _json_dump(candidate.get("place")) if candidate.get("place") is not None else None,
                candidate.get("occurred_at"),
                float(candidate.get("importance", 0)),
                _normalize_visibility(candidate.get("visibility")),
                int(bool(candidate.get("pending", False))),
                str(candidate.get("proposed_by", "")),
                str(candidate.get("validation_status", "pending")),
                _json_dump(candidate.get("validation_notes", [])),
                _json_dump(candidate),
                str(candidate.get("schema_version", "1.0")),
                str(candidate.get("created_at") or _utc_now()),
            ),
        )

    def _insert_episodic_memory(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        turn_id: str | None,
        turn_number: int | None,
        memory: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO episodic_memories(
                memory_id, session_id, turn_id, turn_number, summary,
                source_event_ids_json, tags_json, actors_json, place_json,
                occurred_at, importance, visibility, pending, version,
                payload_json, schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _required_text(memory, "memory_id"),
                session_id,
                turn_id,
                turn_number,
                _required_text(memory, "summary"),
                _json_dump(memory.get("source_event_ids", [])),
                _json_dump(memory.get("tags", [])),
                _json_dump(memory.get("actors", [])),
                _json_dump(memory.get("place")) if memory.get("place") is not None else None,
                memory.get("occurred_at"),
                float(memory.get("importance", 0)),
                _normalize_visibility(memory.get("visibility")),
                int(bool(memory.get("pending", False))),
                int(memory.get("version", 1)),
                _json_dump(memory),
                str(memory.get("schema_version", "1.0")),
                str(memory.get("created_at") or _utc_now()),
            ),
        )

    async def list_attempts(self, session_id: str) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            "SELECT * FROM attempts WHERE session_id=? ORDER BY id",
            (session_id,),
            ("error_json", "provenance_json", "usage_json", "metadata_json"),
        )

    async def create_narration_resume_capsule(
        self, capsule: NarrationResumeCapsule,
    ) -> NarrationResumeCapsule:
        """Persist one immutable capsule for a terminal source operation."""
        from .turn_models import NarrationResumeCapsule

        await self.initialize()
        payload = capsule.model_dump(mode="json")
        digest = _payload_hash(payload)
        lock = await self._session_lock(capsule.session_id)
        async with lock:
            def write() -> NarrationResumeCapsule:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    source = connection.execute(
                        "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
                        (capsule.session_id, capsule.source_operation_id),
                    ).fetchone()
                    if (
                        source is None or source["attempt_id"] != capsule.source_attempt_id
                        or source["status"] not in _TERMINAL_FAILURE_STATUSES
                    ):
                        raise IdempotencyConflictError("resume capsule requires its terminal source attempt")
                    existing = connection.execute(
                        "SELECT * FROM narration_resume_capsules WHERE session_id=? AND source_operation_id=?",
                        (capsule.session_id, capsule.source_operation_id),
                    ).fetchone()
                    if existing is not None:
                        if existing["payload_hash"] != digest:
                            raise IdempotencyConflictError("source operation already has a different capsule")
                        connection.commit()
                        return NarrationResumeCapsule.model_validate(_json_load(existing["payload_json"], {}))
                    now = _utc_now()
                    connection.execute(
                        """INSERT INTO narration_resume_capsules(
                               capsule_id,session_id,source_operation_id,source_attempt_id,
                               state,state_revision,payload_json,payload_hash,created_at,updated_at
                           ) VALUES (?,?,?,?, 'paused', ?,?,?,?,?)""",
                        (capsule.capsule_id, capsule.session_id, capsule.source_operation_id,
                         capsule.source_attempt_id, capsule.state_revision, _json_dump(payload),
                         digest, capsule.created_at.isoformat(), now),
                    )
                    connection.commit()
                    return capsule
            return await asyncio.to_thread(write)

    async def load_active_narration_resume_capsule(
        self, session_id: str,
    ) -> dict[str, Any] | None:
        await self.initialize()
        rows = await self._list_rows(
            session_id,
            """SELECT * FROM narration_resume_capsules
               WHERE session_id=? AND state IN ('paused','direct_resume_trial')
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,), ("payload_json",),
        )
        if not rows:
            return None
        row = rows[0]
        if _payload_hash(row.get("payload") or {}) != row.get("payload_hash"):
            raise PersistenceError("resume capsule payload hash mismatch")
        return row

    async def recover_narration_resume_trials(
        self, *, started_before: datetime,
    ) -> tuple[int, int]:
        """Release only leases owned by a process that predates this startup."""

        if started_before.tzinfo is None or started_before.utcoffset() is None:
            raise ValueError("started_before must be timezone-aware")
        await self.initialize()
        cutoff = started_before.astimezone(timezone.utc).isoformat()

        def write() -> tuple[int, int]:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                capsules = connection.execute(
                    """UPDATE narration_resume_capsules
                       SET state='paused',resume_operation_id=NULL,updated_at=?
                       WHERE state='direct_resume_trial' AND updated_at<?""",
                    (_utc_now(), cutoff),
                ).rowcount
                gate_rows = connection.execute(
                    """SELECT gate_id,payload_json FROM narrator_availability_gates
                       WHERE state='direct_resume_trial' AND updated_at<?""",
                    (cutoff,),
                ).fetchall()
                for row in gate_rows:
                    payload = _json_load(row["payload_json"], {})
                    payload["state"] = "unavailable"
                    payload["lease_operation_id"] = None
                    connection.execute(
                        """UPDATE narrator_availability_gates
                           SET state='unavailable',lease_operation_id=NULL,
                               payload_json=?,updated_at=? WHERE gate_id=?""",
                        (_json_dump(payload), _utc_now(), row["gate_id"]),
                    )
                connection.commit()
                return capsules, len(gate_rows)

        return await asyncio.to_thread(write)

    async def claim_narration_resume(
        self, *, session_id: str, capsule_id: str, resume_operation_id: str,
        expected_state_revision: int,
    ) -> dict[str, Any]:
        """CAS paused -> direct trial; duplicate clicks cannot acquire a second lease."""
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            def write() -> dict[str, Any]:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    row = connection.execute(
                        "SELECT * FROM narration_resume_capsules WHERE session_id=? AND capsule_id=?",
                        (session_id, capsule_id),
                    ).fetchone()
                    if row is None:
                        raise PersistenceError("resume capsule was not found")
                    if row["state"] != "paused" or row["state_revision"] != expected_state_revision:
                        raise StateRevisionError("resume capsule is not claimable")
                    changed = connection.execute(
                        """UPDATE narration_resume_capsules
                           SET state='direct_resume_trial',resume_operation_id=?,updated_at=?
                           WHERE capsule_id=? AND state='paused' AND state_revision=?""",
                        (resume_operation_id, _utc_now(), capsule_id, expected_state_revision),
                    ).rowcount
                    if changed != 1:
                        raise StateRevisionError("resume capsule lease was already claimed")
                    connection.commit()
                    result = dict(row)
                    result.update(state="direct_resume_trial", resume_operation_id=resume_operation_id)
                    result["payload_json"] = _json_load(result["payload_json"], {})
                    return result
            return await asyncio.to_thread(write)

    async def transition_narration_resume(
        self, *, session_id: str, capsule_id: str, from_state: str, to_state: str,
        resume_operation_id: str | None = None,
    ) -> bool:
        allowed = {
            ("paused", "abandoned"), ("direct_resume_trial", "paused"),
            ("direct_resume_trial", "completed"),
        }
        if (from_state, to_state) not in allowed:
            raise ValueError("invalid narration resume transition")
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            def write() -> bool:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    params: list[Any] = [to_state, _utc_now()]
                    terminal = ",completed_at=?" if to_state in {"completed", "abandoned"} else ""
                    if terminal:
                        params.append(_utc_now())
                    sql = f"UPDATE narration_resume_capsules SET state=?,updated_at=?{terminal} WHERE session_id=? AND capsule_id=? AND state=?"
                    params.extend([session_id, capsule_id, from_state])
                    if resume_operation_id is not None:
                        sql += " AND resume_operation_id=?"
                        params.append(resume_operation_id)
                    changed = connection.execute(sql, tuple(params)).rowcount
                    connection.commit()
                    return changed == 1
            return await asyncio.to_thread(write)

    async def upsert_narrator_availability_gate(
        self, *, session_id: str, gate: NarratorAvailabilityGate,
    ) -> None:
        await self.initialize()
        payload = gate.model_dump(mode="json")
        lock = await self._session_lock(session_id)
        async with lock:
            def write() -> None:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    self._insert_campaign_if_missing(connection, session_id, "", {}, {}, {})
                    connection.execute(
                        """INSERT INTO narrator_availability_gates(
                               gate_id,session_id,scope,scope_key,target_json,state,payload_json,
                               observed_at,retry_not_before,lease_operation_id,updated_at
                           ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(session_id,scope,scope_key) DO UPDATE SET
                               gate_id=excluded.gate_id,target_json=excluded.target_json,
                               state=excluded.state,payload_json=excluded.payload_json,
                               observed_at=excluded.observed_at,retry_not_before=excluded.retry_not_before,
                               lease_operation_id=excluded.lease_operation_id,updated_at=excluded.updated_at""",
                        (gate.gate_id, session_id, gate.scope.value, gate.scope_key,
                         _json_dump(gate.target), gate.state.value, _json_dump(payload),
                         gate.observed_at.isoformat(),
                         gate.retry_not_before.isoformat() if gate.retry_not_before else None,
                         gate.lease_operation_id, _utc_now()),
                    )
                    connection.commit()
            await asyncio.to_thread(write)

    async def load_narrator_availability_gates(self, session_id: str) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            "SELECT * FROM narrator_availability_gates WHERE session_id=? ORDER BY updated_at DESC",
            (session_id,), ("target_json", "payload_json"),
        )

    async def load_attempt_by_operation(
        self, session_id: str, operation_id: str
    ) -> dict[str, Any] | None:
        rows = await self._list_rows(
            session_id,
            "SELECT * FROM attempts WHERE session_id=? AND operation_id=? LIMIT 1",
            (session_id, operation_id),
            ("error_json", "provenance_json", "usage_json", "metadata_json"),
        )
        return rows[0] if rows else None

    async def list_turns(
        self, session_id: str, *, after_turn: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            """SELECT * FROM turns WHERE session_id=? AND turn_number>?
               ORDER BY turn_number LIMIT ?""",
            (session_id, after_turn, max(1, limit)),
            (
                "narrative_json",
                "facts_json",
                "context_json",
                "state_json",
                "relationships_json",
                "provenance_json",
                "usage_json",
            ),
        )

    async def load_turn_by_operation(
        self, session_id: str, operation_id: str
    ) -> dict[str, Any] | None:
        rows = await self._list_rows(
            session_id,
            "SELECT * FROM turns WHERE session_id=? AND operation_id=? LIMIT 1",
            (session_id, operation_id),
            (
                "narrative_json",
                "facts_json",
                "context_json",
                "state_json",
                "relationships_json",
                "provenance_json",
                "usage_json",
            ),
        )
        return rows[0] if rows else None

    async def get_recent_narrative_source_turns(
        self, session_id: str, *, limit: int = 2,
        allowed_visibilities: Sequence[str] = ("public", "player"),
    ) -> tuple[NarrativeSourceTurnEnvelope, ...]:
        """Restore the required recent sources, never hide incompatible turns.

        Stored turn/attempt hashes are paired; this does not reconstruct the
        entire historical digest or authenticate a provider independently.
        """
        from .narrative_source_turn import SourceTurnContractError

        if (
            type(session_id) is not str or not session_id.strip()
            or session_id != session_id.strip()
            or type(limit) is not int or not 1 <= limit <= 2
            or not isinstance(allowed_visibilities, (tuple, list))
            or not allowed_visibilities
            or any(type(v) is not str or v not in {"public", "player"}
                   for v in allowed_visibilities)
        ):
            raise SourceTurnContractError("source_turn_query_invalid")
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._get_recent_narrative_source_turns_sync, session_id,
                limit, tuple(allowed_visibilities),
            )

    def _get_recent_narrative_source_turns_sync(
        self, session_id: str, limit: int, allowed_visibilities: tuple[str, ...],
    ) -> tuple[NarrativeSourceTurnEnvelope, ...]:
        from .narrative_source_turn import PROTOCOL, SourceTurnContractError

        restored = []
        with self._connect() as connection:
            # One read snapshot keeps turn, attempt and antecedents paired.
            connection.execute("BEGIN")
            rows = connection.execute(
                """SELECT * FROM (
                       SELECT * FROM turns WHERE session_id=?
                       ORDER BY turn_number DESC LIMIT ?
                   ) ORDER BY turn_number""", (session_id, limit),
            ).fetchall()
            for row in rows:
                restored.append(self._restore_narrative_source_row(
                    connection, row, session_id, allowed_visibilities,
                ))
        return tuple(restored)

    def _restore_narrative_source_row(
        self, connection: sqlite3.Connection, row: sqlite3.Row,
        session_id: str, allowed_visibilities: tuple[str, ...],
    ) -> NarrativeSourceTurnEnvelope:
        from .narrative_source_turn import PROTOCOL, SourceTurnContractError

        attempt = connection.execute(
            "SELECT * FROM attempts WHERE session_id=? AND operation_id=?",
            (session_id, row["operation_id"]),
        ).fetchone()
        if (
            attempt is None or attempt["status"] != "completed"
            or attempt["committed_turn_id"] != row["turn_id"]
            or attempt["attempt_id"] != row["attempt_id"]
            or attempt["result_hash"] != row["payload_hash"]
            or not re.fullmatch(r"[0-9a-f]{64}", row["payload_hash"] or "")
            or attempt["provenance_json"] != row["provenance_json"]
        ):
            raise SourceTurnContractError("source_turn_stored_pair_mismatch")
        try:
            context = _json_load(row["context_json"], {})
            if not isinstance(context, Mapping) or "narrative_source" not in context:
                raise SourceTurnContractError("source_turn_history_incompatible")
            narrative = _json_load(row["narrative_json"], {})
            if row["narrative_complete"] != 1 or narrative.get("text") != row["narrative_text"]:
                raise SourceTurnContractError("source_turn_stored_pair_mismatch")
            collections = {}
            for name, table in (
                ("events", "events"), ("memory_candidates", "memory_candidates"),
                ("episodic_memories", "episodic_memories"),
            ):
                collections[name] = [
                    _json_load(item["payload_json"], {})
                    for item in connection.execute(
                        f"SELECT payload_json FROM {table} WHERE session_id=? AND turn_id=?",
                        (session_id, row["turn_id"]),
                    ).fetchall()
                ]
            envelope = _validate_narrative_source_obligation(
                narrative_contract=PROTOCOL, attempt=attempt,
                context=context, narrative=narrative, session_id=session_id,
                operation_id=row["operation_id"], turn_id=row["turn_id"],
                attempt_id=row["attempt_id"], requested_turn=row["turn_number"],
                user_input=row["user_input"], facts=_json_load(row["facts_json"], []),
                provenance=_json_load(row["provenance_json"], None), **collections,
            )
            if envelope.projection.source.visibility.value not in allowed_visibilities:
                raise SourceTurnContractError("source_turn_visibility_forbidden")
        except SourceTurnContractError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError):
            raise SourceTurnContractError("source_turn_stored_pair_mismatch") from None
        return envelope

    async def list_latest_turns(
        self, session_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return the newest bounded window in chronological order."""

        return await self._list_rows(
            session_id,
            """SELECT * FROM (
                   SELECT * FROM turns WHERE session_id=?
                   ORDER BY turn_number DESC LIMIT ?
               ) ORDER BY turn_number""",
            (session_id, max(1, limit)),
            (
                "narrative_json",
                "facts_json",
                "context_json",
                "state_json",
                "relationships_json",
                "provenance_json",
                "usage_json",
            ),
        )

    async def list_events(
        self, session_id: str, *, after_turn: int = 0, limit: int = 500
    ) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            """SELECT * FROM events WHERE session_id=? AND turn_number>?
               ORDER BY turn_number, sequence LIMIT ?""",
            (session_id, after_turn, max(1, limit)),
            (
                "fact_ids_json",
                "tags_json",
                "actors_json",
                "place_json",
                "references_json",
                "payload_json",
            ),
        )

    async def list_memory_candidates(self, session_id: str) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            "SELECT * FROM memory_candidates WHERE session_id=? ORDER BY turn_number, id",
            (session_id,),
            (
                "source_event_ids_json",
                "tags_json",
                "actors_json",
                "place_json",
                "validation_notes_json",
                "payload_json",
            ),
        )

    async def list_episodic_memories(self, session_id: str) -> list[dict[str, Any]]:
        return await self._list_rows(
            session_id,
            "SELECT * FROM episodic_memories WHERE session_id=? ORDER BY id",
            (session_id,),
            (
                "source_event_ids_json",
                "tags_json",
                "actors_json",
                "place_json",
                "payload_json",
            ),
        )

    async def _list_rows(
        self,
        session_id: str,
        statement: str,
        parameters: tuple[Any, ...],
        json_columns: Sequence[str],
    ) -> list[dict[str, Any]]:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._list_rows_sync, statement, parameters, json_columns
            )

    def _list_rows_sync(
        self,
        statement: str,
        parameters: tuple[Any, ...],
        json_columns: Sequence[str],
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [
                _decode_row(row, json_columns)
                for row in connection.execute(statement, parameters).fetchall()
            ]

    async def retrieve_memories(
        self,
        session_id: str,
        *,
        query: str = "",
        allowed_visibilities: Sequence[str] | None = None,
        limit: int = 20,
        token_budget: int | None = None,
        token_estimator: Callable[[str], int] | None = None,
        relevance_weight: float = 0.45,
        recency_weight: float = 0.20,
        importance_weight: float = 0.20,
        pending_weight: float = 0.15,
    ) -> list[dict[str, Any]]:
        memories = await self.list_episodic_memories(session_id)
        allowed = (
            {_normalize_visibility(item) for item in allowed_visibilities}
            if allowed_visibilities is not None
            else None
        )
        if allowed is not None:
            memories = [item for item in memories if item["visibility"] in allowed]
        query_terms = _terms(query)
        newest_turn = max((item.get("turn_number") or 0 for item in memories), default=0)
        for item in memories:
            searchable = " ".join(
                [
                    item.get("summary", ""),
                    *[str(tag) for tag in item.get("tags", [])],
                    *[_entity_text(actor) for actor in item.get("actors", [])],
                ]
            )
            terms = _terms(searchable)
            relevance = len(query_terms & terms) / max(1, len(query_terms)) if query_terms else 0.0
            turn_number = item.get("turn_number") or 0
            recency = 1.0 / (1.0 + max(0, newest_turn - turn_number)) if newest_turn else 0.0
            importance = float(item.get("importance", 0))
            if importance > 1:
                importance = min(1.0, importance / 5.0)
            item["score"] = (
                relevance * relevance_weight
                + recency * recency_weight
                + max(0.0, importance) * importance_weight
                + float(bool(item.get("pending"))) * pending_weight
            )
        memories.sort(
            key=lambda item: (
                -item["score"],
                -(item.get("turn_number") or 0),
                item["memory_id"],
            )
        )
        estimator = token_estimator or (lambda text: max(1, math.ceil(len(text) / 4)))
        selected: list[dict[str, Any]] = []
        consumed = 0
        for item in memories:
            if len(selected) >= max(1, limit):
                break
            estimated = max(1, int(estimator(item["summary"])))
            if token_budget is not None and consumed + estimated > token_budget:
                continue
            item["estimated_tokens"] = estimated
            selected.append(item)
            consumed += estimated
        return selected

    async def save_consolidation(self, consolidation: Any) -> ConsolidationResult:
        await self.initialize()
        payload = _plain(consolidation)
        if not isinstance(payload, Mapping):
            raise ValueError("consolidation must be an object")
        payload = dict(payload)
        session_id = _required_text(payload, "session_id")
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(self._save_consolidation_sync, payload)

    def _save_consolidation_sync(
        self, consolidation: Mapping[str, Any]
    ) -> ConsolidationResult:
        normalized = dict(consolidation)
        session_id = _id_sequence(
            (normalized.get("session_id"),), "session_id", required=True
        )[0]
        consolidation_id = _id_sequence(
            (normalized.get("consolidation_id"),),
            "consolidation_id",
            required=True,
        )[0]
        source_memory_ids = tuple(
            sorted(
                _id_sequence(
                    normalized.get("source_memory_ids", ()),
                    "source_memory_ids",
                    required=True,
                )
            )
        )
        source_event_ids = tuple(
            sorted(
                _id_sequence(
                    normalized.get("source_event_ids", ()),
                    "source_event_ids",
                    required=True,
                )
            )
        )
        visibility = _visibility(normalized.get("visibility"), "consolidation")
        supersedes = normalized.get("supersedes_consolidation_id")
        if supersedes is not None:
            supersedes = _id_sequence(
                (supersedes,), "supersedes_consolidation_id", required=True
            )[0]
        normalized.update(
            {
                "session_id": session_id,
                "consolidation_id": consolidation_id,
                "source_memory_ids": list(source_memory_ids),
                "source_event_ids": list(source_event_ids),
                "visibility": visibility,
                "supersedes_consolidation_id": supersedes,
            }
        )
        scope = _required_text(normalized, "scope")
        version = int(normalized.get("version", 1))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                placeholders = ",".join("?" for _ in source_memory_ids)
                memory_rows = connection.execute(
                    f"""SELECT memory_id, session_id, summary,
                               source_event_ids_json, visibility
                        FROM episodic_memories
                        WHERE memory_id IN ({placeholders})""",
                    source_memory_ids,
                ).fetchall()
                memories_by_id = {row["memory_id"]: row for row in memory_rows}
                missing_memory_ids = sorted(set(source_memory_ids) - memories_by_id.keys())
                if missing_memory_ids:
                    raise ValueError(
                        "source_memory_ids contain unknown memories: "
                        + ", ".join(missing_memory_ids)
                    )
                wrong_session_memory_ids = sorted(
                    memory_id
                    for memory_id, row in memories_by_id.items()
                    if row["session_id"] != session_id
                )
                if wrong_session_memory_ids:
                    raise ValueError(
                        "source_memory_ids must belong to the consolidation session: "
                        + ", ".join(wrong_session_memory_ids)
                    )

                from .memory_service import build_grounded_consolidation_summary

                grounded_summary = build_grounded_consolidation_summary(
                    (memory_id, str(memories_by_id[memory_id]["summary"]))
                    for memory_id in source_memory_ids
                )
                if _required_text(normalized, "summary") != grounded_summary:
                    raise ValueError(
                        "consolidation summary must be derived exactly from its "
                        "episodic memory sources"
                    )
                normalized["summary"] = grounded_summary

                canonical_event_ids: set[str] = set()
                source_visibilities: list[str] = []
                for memory_id in source_memory_ids:
                    row = memories_by_id[memory_id]
                    canonical_event_ids.update(
                        _id_sequence(
                            _json_load(row["source_event_ids_json"], []),
                            f"episodic memory {memory_id!r} source_event_ids",
                            required=True,
                        )
                    )
                    source_visibilities.append(
                        _visibility(row["visibility"], f"episodic memory {memory_id!r}")
                    )
                expected_event_ids = tuple(sorted(canonical_event_ids))
                if source_event_ids != expected_event_ids:
                    raise ValueError(
                        "source_event_ids must exactly match the union of the source "
                        "memories' canonical events"
                    )

                event_placeholders = ",".join("?" for _ in expected_event_ids)
                event_rows = connection.execute(
                    f"""SELECT event_id, session_id, visibility
                        FROM events WHERE event_id IN ({event_placeholders})""",
                    expected_event_ids,
                ).fetchall()
                events_by_id = {row["event_id"]: row for row in event_rows}
                missing_event_ids = sorted(canonical_event_ids - events_by_id.keys())
                if missing_event_ids:
                    raise ValueError(
                        "source_event_ids contain unknown canonical events: "
                        + ", ".join(missing_event_ids)
                    )
                wrong_session_event_ids = sorted(
                    event_id
                    for event_id, row in events_by_id.items()
                    if row["session_id"] != session_id
                )
                if wrong_session_event_ids:
                    raise ValueError(
                        "source_event_ids must belong to the consolidation session: "
                        + ", ".join(wrong_session_event_ids)
                    )
                source_visibilities.extend(
                    _visibility(row["visibility"], f"canonical event {event_id!r}")
                    for event_id, row in events_by_id.items()
                )
                if _VISIBILITY_RESTRICTION[visibility] < max(
                    _VISIBILITY_RESTRICTION[value] for value in source_visibilities
                ):
                    raise ValueError(
                        "consolidation visibility cannot broaden source visibility"
                    )

                existing = connection.execute(
                    "SELECT * FROM consolidations WHERE consolidation_id=?",
                    (consolidation_id,),
                ).fetchone()
                if existing is not None:
                    if existing["payload_json"] != _json_dump(normalized):
                        raise IdempotencyConflictError(
                            f"Consolidation {consolidation_id!r} has different data"
                        )
                    connection.commit()
                    return ConsolidationResult(
                        session_id, consolidation_id, scope, version, True
                    )
                last = connection.execute(
                    """SELECT consolidation_id, version FROM consolidations
                       WHERE session_id=? AND scope=?
                       ORDER BY version DESC LIMIT 1""",
                    (session_id, scope),
                ).fetchone()
                expected = 1 if last is None else int(last["version"]) + 1
                if version != expected:
                    raise ConsolidationVersionError(
                        f"Consolidation {scope!r} version {version} is not next version {expected}"
                    )
                expected_supersedes = (
                    None if last is None else str(last["consolidation_id"])
                )
                if supersedes != expected_supersedes:
                    if expected_supersedes is None:
                        message = "A version 1 consolidation cannot supersede another record"
                    else:
                        message = (
                            "supersedes_consolidation_id must reference the immediately "
                            f"previous consolidation {expected_supersedes!r}"
                        )
                    raise ConsolidationVersionError(message)
                connection.execute(
                    """
                    INSERT INTO consolidations(
                        consolidation_id, session_id, scope, version, summary,
                        source_memory_ids_json, source_event_ids_json, tags_json,
                        visibility, supersedes_consolidation_id, payload_json,
                        schema_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        consolidation_id,
                        session_id,
                        scope,
                        version,
                        _required_text(normalized, "summary"),
                        _json_dump(source_memory_ids),
                        _json_dump(source_event_ids),
                        _json_dump(normalized.get("tags", [])),
                        visibility,
                        supersedes,
                        _json_dump(normalized),
                        str(normalized.get("schema_version", "1.0")),
                        str(normalized.get("created_at") or _utc_now()),
                    ),
                )
                connection.commit()
                return ConsolidationResult(session_id, consolidation_id, scope, version)
            except Exception:
                connection.rollback()
                raise

    async def list_consolidations(
        self, session_id: str, *, scope: str | None = None
    ) -> list[dict[str, Any]]:
        if scope is None:
            statement = (
                "SELECT * FROM consolidations WHERE session_id=? ORDER BY scope, version"
            )
            parameters: tuple[Any, ...] = (session_id,)
        else:
            statement = (
                "SELECT * FROM consolidations WHERE session_id=? AND scope=? ORDER BY version"
            )
            parameters = (session_id, scope)
        rows = await self._list_rows(
            session_id,
            statement,
            parameters,
            (
                "source_memory_ids_json",
                "source_event_ids_json",
                "tags_json",
                "payload_json",
            ),
        )
        memories = {
            row["memory_id"]: row
            for row in await self.list_episodic_memories(session_id)
        }
        events = {
            row["event_id"]: row for row in await self.list_events(session_id)
        }
        from .memory_service import build_grounded_consolidation_summary

        grounded_rows: list[dict[str, Any]] = []
        for row in rows:
            source_ids = tuple(row.get("source_memory_ids") or ())
            if not source_ids or any(memory_id not in memories for memory_id in source_ids):
                # A source-less or orphaned legacy row cannot safely enter context.
                continue
            grounded_summary = build_grounded_consolidation_summary(
                (memory_id, str(memories[memory_id]["summary"]))
                for memory_id in source_ids
            )
            expected_event_ids = tuple(
                sorted(
                    {
                        event_id
                        for memory_id in source_ids
                        for event_id in memories[memory_id].get(
                            "source_event_ids", ()
                        )
                    }
                )
            )
            if not expected_event_ids or any(
                event_id not in events for event_id in expected_event_ids
            ):
                continue
            source_visibilities = [
                _visibility(
                    memories[memory_id]["visibility"],
                    f"episodic memory {memory_id!r}",
                )
                for memory_id in source_ids
            ]
            source_visibilities.extend(
                _visibility(events[event_id]["visibility"], f"event {event_id!r}")
                for event_id in expected_event_ids
            )
            stored_visibility = _visibility(
                row.get("visibility"), "consolidation"
            )
            effective_visibility = max(
                (*source_visibilities, stored_visibility),
                key=lambda value: _VISIBILITY_RESTRICTION[value],
            )
            normalized_row = dict(row)
            normalized_row["summary"] = grounded_summary
            normalized_row["source_memory_ids"] = list(sorted(source_ids))
            normalized_row["source_event_ids"] = list(expected_event_ids)
            normalized_row["visibility"] = effective_visibility
            payload = dict(normalized_row.get("payload") or {})
            payload["summary"] = grounded_summary
            payload["source_memory_ids"] = list(sorted(source_ids))
            payload["source_event_ids"] = list(expected_event_ids)
            payload["visibility"] = effective_visibility
            normalized_row["payload"] = payload
            grounded_rows.append(normalized_row)
        return grounded_rows

    async def migrate_legacy_session(
        self,
        session_id: str,
        legacy_dir: str | os.PathLike[str],
        *,
        chronicle_name: str = "",
    ) -> LegacyMigrationResult:
        if _SAFE_LEGACY_SESSION_ID.fullmatch(session_id) is None:
            raise ValueError("Legacy session_id may contain only letters, digits, '_' and '-'")
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(
                self._migrate_legacy_session_sync,
                session_id,
                Path(legacy_dir),
                chronicle_name,
            )

    def _migrate_legacy_session_sync(
        self, session_id: str, legacy_dir: Path, chronicle_name: str
    ) -> LegacyMigrationResult:
        source_paths = {
            "state": legacy_dir / f"{session_id}.json",
            "memory": legacy_dir / f"{session_id}_memory.json",
            "relationships": legacy_dir / f"{session_id}_relationships.json",
        }
        audited: dict[str, dict[str, Any]] = {}
        for kind, path in source_paths.items():
            if not path.exists():
                audited[kind] = {
                    "path": str(path),
                    "raw": None,
                    "sha256": None,
                    "fingerprint": "<missing>",
                    "status": "missing",
                    "error": None,
                    "parsed": None,
                }
                continue
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            try:
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise ValueError("root value must be a JSON object")
                status = "valid"
                error = None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                parsed = None
                status = "corrupt"
                error = f"{type(exc).__name__}: {exc}"
            audited[kind] = {
                "path": str(path),
                "raw": raw,
                "sha256": digest,
                "fingerprint": digest,
                "status": status,
                "error": error,
                "parsed": parsed,
            }

        self._validate_legacy_payloads(session_id, audited)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for kind, source in audited.items():
                    existing = connection.execute(
                        """SELECT * FROM legacy_imports
                           WHERE session_id=? AND source_kind=? AND content_fingerprint=?""",
                        (session_id, kind, source["fingerprint"]),
                    ).fetchone()
                    if existing is None:
                        cursor = connection.execute(
                            """
                            INSERT INTO legacy_imports(
                                session_id, source_kind, source_path, content_fingerprint,
                                content_sha256, raw_bytes, parse_status, parse_error,
                                parsed_json, audited_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                session_id,
                                kind,
                                source["path"],
                                source["fingerprint"],
                                source["sha256"],
                                source["raw"],
                                source["status"],
                                source["error"],
                                _json_dump(source["parsed"])
                                if source["parsed"] is not None
                                else None,
                                _utc_now(),
                            ),
                        )
                        source["import_id"] = cursor.lastrowid
                    else:
                        source["import_id"] = existing["id"]
                corrupt = [
                    kind for kind, source in audited.items() if source["status"] == "corrupt"
                ]
                if corrupt:
                    connection.commit()
                    raise LegacyCorruptionError(session_id, corrupt)

                present = [
                    kind for kind, source in audited.items() if source["status"] == "valid"
                ]
                existing_campaign = connection.execute(
                    "SELECT * FROM campaigns WHERE session_id=?", (session_id,)
                ).fetchone()
                applied = connection.execute(
                    """SELECT COUNT(*) AS count FROM legacy_imports
                       WHERE session_id=? AND applied_at IS NOT NULL""",
                    (session_id,),
                ).fetchone()["count"]
                if existing_campaign is not None:
                    changed_after_import = [
                        kind
                        for kind, source in audited.items()
                        if connection.execute(
                            "SELECT applied_at FROM legacy_imports WHERE id=?",
                            (source["import_id"],),
                        ).fetchone()["applied_at"]
                        is None
                    ]
                    connection.commit()
                    if applied and changed_after_import:
                        raise LegacySourceChangedError(
                            session_id, changed_after_import[0]
                        )
                    return LegacyMigrationResult(
                        session_id,
                        "already_migrated" if applied else "campaign_exists",
                        False,
                        bool(applied),
                        int(existing_campaign["current_turn"]),
                        0,
                    )

                if not present:
                    connection.commit()
                    return LegacyMigrationResult(
                        session_id, "not_found", False, False, 0, 0
                    )
                if audited["state"]["status"] == "missing":
                    connection.commit()
                    raise LegacyStateRequiredError(session_id)

                state = audited["state"]["parsed"] or {}
                memory = audited["memory"]["parsed"] or {}
                relationships = audited["relationships"]["parsed"] or {}
                current_turn = _legacy_turn(state, memory)
                imported_name = chronicle_name or str(
                    state.get("chronicle_name") or "Legacy Chronicle"
                )
                now = _utc_now()
                connection.execute(
                    """
                    INSERT INTO campaigns(
                        session_id, chronicle_name, schema_version, current_turn,
                        state_json, relationships_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        imported_name,
                        SCHEMA_VERSION,
                        current_turn,
                        _json_dump(state),
                        _json_dump(relationships),
                        _json_dump({"legacy_imported": True}),
                        now,
                        now,
                    ),
                )
                imported_memories = self._import_legacy_memories(
                    connection, session_id, memory, current_turn
                )
                import_ids = [source["import_id"] for source in audited.values()]
                placeholders = ",".join("?" for _ in import_ids)
                connection.execute(
                    f"UPDATE legacy_imports SET applied_at=? WHERE id IN ({placeholders})",
                    (now, *import_ids),
                )
                connection.commit()
                return LegacyMigrationResult(
                    session_id,
                    "migrated",
                    True,
                    False,
                    current_turn,
                    imported_memories,
                )
            except LegacyMigrationError:
                raise
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _validate_legacy_payloads(
        session_id: str,
        audited: dict[str, dict[str, Any]],
    ) -> None:
        """Validate syntax-valid legacy JSON before any source is marked applied.

        Imports are local to avoid coupling the persistence schema to provider or
        transport code.  Validation failures retain the exact source bytes in the
        audit table, but no incompatible projection can become campaign state.
        """

        from .memory_service import SessionMemory
        from .relationship_service import RelationshipState
        from .state_service import StateUpdateEvent

        validators = {
            "state": StateUpdateEvent,
            "memory": SessionMemory,
            "relationships": RelationshipState,
        }
        for kind, model in validators.items():
            source = audited[kind]
            if source["status"] != "valid":
                continue
            try:
                raw_payload = source["parsed"]
                validated = model.model_validate(raw_payload)
                if validated.session_id != session_id:
                    raise ValueError("session_id does not match the legacy filename")
                normalized = validated.model_dump(mode="json")
                if kind == "state" and isinstance(raw_payload, Mapping):
                    for metadata_key in ("chronicle_name", "turn"):
                        if metadata_key in raw_payload:
                            normalized[metadata_key] = _plain(raw_payload[metadata_key])
                source["parsed"] = normalized
            except Exception as exc:
                source["status"] = "corrupt"
                source["error"] = (
                    f"{kind} schema validation failed ({type(exc).__name__})"
                )
                source["parsed"] = None

    def _import_legacy_memories(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        memory: Mapping[str, Any],
        current_turn: int,
    ) -> int:
        scene = memory.get("scene", {}) if isinstance(memory, Mapping) else {}
        campaign = memory.get("campaign", {}) if isinstance(memory, Mapping) else {}
        entries: list[tuple[str, bool, list[str]]] = []
        for text in scene.get("recent_events", []) if isinstance(scene, Mapping) else []:
            if isinstance(text, str) and text.strip():
                entries.append((text.strip(), False, ["legacy", "scene_event"]))
        for decision in campaign.get("key_decisions", []) if isinstance(campaign, Mapping) else []:
            if isinstance(decision, Mapping):
                text = str(decision.get("summary", "")).strip()
            else:
                text = str(decision).strip()
            if text:
                entries.append((text, True, ["legacy", "key_decision"]))
        for arc in campaign.get("chronicle_arcs", []) if isinstance(campaign, Mapping) else []:
            text = str(arc).strip()
            if text:
                entries.append((text, True, ["legacy", "chronicle_arc"]))

        for index, (summary, pending, tags) in enumerate(entries):
            digest = hashlib.sha256(
                f"{session_id}\0{index}\0{summary}".encode("utf-8")
            ).hexdigest()[:24]
            memory_id = f"legacy-memory-{digest}"
            turn_match = re.match(r"^T(\d+):", summary)
            turn_number = int(turn_match.group(1)) if turn_match else current_turn or None
            payload = {
                "schema_version": "1.0",
                "memory_id": memory_id,
                "session_id": session_id,
                "created_at": _utc_now(),
                "summary": summary,
                "source_event_ids": [],
                "tags": tags,
                "actors": [],
                "importance": 0.5,
                "visibility": "player",
                "pending": pending,
                "version": 1,
                "legacy_unreferenced": True,
            }
            self._insert_episodic_memory(
                connection, session_id, None, turn_number, payload
            )
        return len(entries)

    async def list_legacy_imports(self, session_id: str) -> list[dict[str, Any]]:
        await self.initialize()
        lock = await self._session_lock(session_id)
        async with lock:
            return await asyncio.to_thread(self._list_legacy_imports_sync, session_id)

    def _list_legacy_imports_sync(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM legacy_imports WHERE session_id=? ORDER BY source_kind, id",
                (session_id,),
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["parsed"] = _json_load(item.pop("parsed_json"), None)
                result.append(item)
            return result


def _legacy_turn(state: Mapping[str, Any], memory: Mapping[str, Any]) -> int:
    candidates: list[Any] = [state.get("turn", 0), state.get("turn_number", 0)]
    scene = memory.get("scene", {}) if isinstance(memory, Mapping) else {}
    campaign = memory.get("campaign", {}) if isinstance(memory, Mapping) else {}
    if isinstance(scene, Mapping):
        candidates.append(scene.get("last_updated_turn", 0))
    if isinstance(campaign, Mapping):
        candidates.append(campaign.get("last_updated_turn", 0))
    valid = []
    for candidate in candidates:
        try:
            number = int(candidate)
        except (TypeError, ValueError):
            continue
        if number >= 0:
            valid.append(number)
    return max(valid, default=0)


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"\w+", text.casefold(), flags=re.UNICODE) if term}


def _entity_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(
            str(value.get(key, "")) for key in ("entity_id", "entity_type", "label")
        )
    return str(value)


_default_store: SQLitePersistence | None = None
_default_store_guard = threading.Lock()


def get_default_persistence() -> SQLitePersistence:
    """Return the process-wide repository without opening a database eagerly."""
    global _default_store
    if _default_store is None:
        with _default_store_guard:
            if _default_store is None:
                _default_store = SQLitePersistence()
    return _default_store
