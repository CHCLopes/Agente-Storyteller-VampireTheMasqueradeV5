import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from api.memory_service import build_grounded_consolidation_summary
from api.persistence import (
    ConsolidationVersionError,
    IdempotencyConflictError,
    LegacyCorruptionError,
    PersistenceError,
    SchemaVersionError,
    SQLitePersistence,
    StateRevisionError,
    TurnSequenceError,
)
from api.turn_models import (
    CandidateValidationStatus,
    CanonicalEvent,
    CanonicalFact,
    Consolidation,
    ConsolidationScope,
    EpisodicMemory,
    MemoryCandidate,
    NarrativeRecord,
    NarrationResumeCapsule,
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
    TurnDraft,
    Visibility,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_payload(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _turn_records(session_id: str, turn_id: str, suffix: str):
    fact = CanonicalFact(
        fact_id=f"fact-{suffix}",
        fact_type="mechanical_result",
        predicate="hunger_changed",
        value={"from": 1, "to": 2},
        occurred_at=_now(),
        importance=0.8,
    )
    event = CanonicalEvent(
        event_id=f"event-{suffix}",
        session_id=session_id,
        turn_id=turn_id,
        sequence=0,
        event_type="action_resolved",
        occurred_at=_now(),
        summary="A fome aumentou.",
        fact_ids=(fact.fact_id,),
        importance=0.8,
    )
    narrative = NarrativeRecord(
        narrative_id=f"narrative-{suffix}",
        session_id=session_id,
        turn_id=turn_id,
        text="A Besta desperta sob a pele.",
        source_event_ids=(event.event_id,),
    )
    candidate = MemoryCandidate(
        candidate_id=f"candidate-{suffix}",
        session_id=session_id,
        turn_id=turn_id,
        summary="A fome aumentou durante a ação.",
        source_event_ids=(event.event_id,),
        tags=("fome",),
        importance=0.8,
        validation_status=CandidateValidationStatus.ACCEPTED,
    )
    memory = EpisodicMemory(
        memory_id=f"memory-{suffix}",
        session_id=session_id,
        created_at=candidate.created_at,
        summary=candidate.summary,
        source_event_ids=(event.event_id,),
        tags=candidate.tags,
        actors=candidate.actors,
        place=candidate.place,
        occurred_at=candidate.occurred_at,
        importance=candidate.importance,
        visibility=candidate.visibility,
        pending=candidate.pending,
    )
    return fact, event, narrative, candidate, memory


def test_schema_wal_foreign_keys_and_version(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        await store.initialize()
        info = await store.database_info()
        assert info == {
            "schema_version": 4,
            "journal_mode": "wal",
            "foreign_keys": True,
        }

        with sqlite3.connect(store.db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert {
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
        } <= tables
        with sqlite3.connect(store.db_path) as connection:
            attempt_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(attempts)")
            }
            campaign_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(campaigns)")
            }
        assert {"request_hash", "result_hash"} <= attempt_columns
        assert "state_revision" in campaign_columns

        unversioned_path = tmp_path / "unversioned.sqlite3"
        with sqlite3.connect(unversioned_path) as connection:
            connection.execute("CREATE TABLE campaigns(id TEXT)")
        with pytest.raises(SchemaVersionError):
            await SQLitePersistence(unversioned_path).initialize()
        with sqlite3.connect(unversioned_path) as connection:
            assert {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            } == {"campaigns"}

    asyncio.run(scenario())


def test_resume_capsule_is_immutable_single_flight_and_survives_reopen(tmp_path):
    async def scenario():
        path = tmp_path / "resume.sqlite3"
        store = SQLitePersistence(path)
        await store.start_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta",
        )
        await store.record_failed_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta", status="timeout",
            error={"category": "timeout", "retryable": True},
        )
        draft = TurnDraft(
            draft_id="draft-1", session_id="session-1", turn_id="turn-1",
            attempt_id="source-attempt", player_input="Observar a porta",
            base_revision=0, base_state_revision=0,
        )
        capsule = NarrationResumeCapsule(
            capsule_id="capsule-1", session_id="session-1",
            source_operation_id="source-op", source_attempt_id="source-attempt",
            turn_id="turn-1", requested_turn=1, state_revision=0,
            request_hash="a" * 64, action="Observar a porta", draft=draft,
            frozen_context={}, requested_target={"provider": "groq", "model": "fixed"},
            normalized_reason={"category": "timeout", "retryable": True},
        )
        assert await store.create_narration_resume_capsule(capsule) == capsule
        reopened = SQLitePersistence(path)
        active = await reopened.load_active_narration_resume_capsule("session-1")
        assert active is not None and active["payload"]["capsule_id"] == "capsule-1"
        claimed = await reopened.claim_narration_resume(
            session_id="session-1", capsule_id="capsule-1",
            resume_operation_id="resume-op", expected_state_revision=0,
        )
        assert claimed["state"] == "direct_resume_trial"
        with pytest.raises(StateRevisionError):
            await reopened.claim_narration_resume(
                session_id="session-1", capsule_id="capsule-1",
                resume_operation_id="resume-op-2", expected_state_revision=0,
            )
        assert await reopened.transition_narration_resume(
            session_id="session-1", capsule_id="capsule-1",
            from_state="direct_resume_trial", to_state="paused",
            resume_operation_id="resume-op",
        )

        gate = NarratorAvailabilityGate(
            gate_id="gate-1", state=NarratorGateState.COOLDOWN,
            scope=NarratorGateScope.EXACT_TARGET, scope_key="opaque",
            target={"provider": "groq", "model": "fixed"}, observed_at=_now(),
        )
        await reopened.upsert_narrator_availability_gate(session_id="session-1", gate=gate)
        gates = await SQLitePersistence(path).load_narrator_availability_gates("session-1")
        assert gates[0]["payload"]["state"] == "cooldown"

    asyncio.run(scenario())


def test_resume_capsule_claim_is_single_flight_across_concurrent_connections(tmp_path):
    async def scenario():
        path = tmp_path / "resume-concurrent.sqlite3"
        store = SQLitePersistence(path)
        await store.start_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta",
        )
        await store.record_failed_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta", status="timeout",
            error={"category": "timeout", "retryable": True},
        )
        draft = TurnDraft(
            draft_id="draft-1", session_id="session-1", turn_id="turn-1",
            attempt_id="source-attempt", player_input="Observar a porta",
            base_revision=0, base_state_revision=0,
        )
        await store.create_narration_resume_capsule(NarrationResumeCapsule(
            capsule_id="capsule-1", session_id="session-1",
            source_operation_id="source-op", source_attempt_id="source-attempt",
            turn_id="turn-1", requested_turn=1, state_revision=0,
            request_hash="a" * 64, action="Observar a porta", draft=draft,
            frozen_context={}, requested_target={"provider": "groq", "model": "fixed"},
            normalized_reason={"category": "timeout", "retryable": True},
        ))

        async def claim(index: int):
            contender = SQLitePersistence(path)
            return await contender.claim_narration_resume(
                session_id="session-1", capsule_id="capsule-1",
                resume_operation_id=f"resume-op-{index}", expected_state_revision=0,
            )

        results = await asyncio.gather(
            *(claim(index) for index in range(10)), return_exceptions=True,
        )
        winners = [result for result in results if isinstance(result, dict)]
        losers = [result for result in results if isinstance(result, StateRevisionError)]
        assert len(winners) == 1
        assert len(losers) == 9
        assert winners[0]["state"] == "direct_resume_trial"
        active = await SQLitePersistence(path).load_active_narration_resume_capsule("session-1")
        assert active is not None
        assert active["resume_operation_id"] == winners[0]["resume_operation_id"]

    asyncio.run(scenario())


def test_resume_capsule_integrity_and_abandoned_trial_recover_after_restart(tmp_path):
    async def scenario():
        path = tmp_path / "resume-recovery.sqlite3"
        store = SQLitePersistence(path)
        await store.start_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta",
        )
        await store.record_failed_attempt(
            session_id="session-1", operation_id="source-op", attempt_id="source-attempt",
            requested_turn=1, user_input="Observar a porta", status="timeout",
            error={"category": "timeout", "retryable": True},
        )
        draft = TurnDraft(
            draft_id="draft-1", session_id="session-1", turn_id="turn-1",
            attempt_id="source-attempt", player_input="Observar a porta",
            base_revision=0, base_state_revision=0,
        )
        capsule = NarrationResumeCapsule(
            capsule_id="capsule-1", session_id="session-1",
            source_operation_id="source-op", source_attempt_id="source-attempt",
            turn_id="turn-1", requested_turn=1, state_revision=0,
            request_hash="a" * 64, action="Observar a porta", draft=draft,
            frozen_context={}, requested_target={"provider": "groq", "model": "fixed"},
            normalized_reason={"category": "timeout", "retryable": True},
        )
        await store.create_narration_resume_capsule(capsule)
        await store.claim_narration_resume(
            session_id="session-1", capsule_id="capsule-1",
            resume_operation_id="resume-op", expected_state_revision=0,
        )
        gate = NarratorAvailabilityGate(
            gate_id="gate-1", state=NarratorGateState.DIRECT_RESUME_TRIAL,
            scope=NarratorGateScope.EXACT_TARGET, scope_key="opaque",
            target={"provider": "groq", "model": "fixed"}, observed_at=_now(),
            lease_operation_id="resume-op",
        )
        await store.upsert_narrator_availability_gate(session_id="session-1", gate=gate)

        recovered = SQLitePersistence(path)
        assert await recovered.recover_narration_resume_trials(
            started_before=_now() + timedelta(seconds=1),
        ) == (1, 1)
        active = await recovered.load_active_narration_resume_capsule("session-1")
        assert active is not None
        assert active["state"] == "paused"
        assert active["resume_operation_id"] is None
        gates = await recovered.load_narrator_availability_gates("session-1")
        assert gates[0]["state"] == "unavailable"
        assert gates[0]["payload"]["lease_operation_id"] is None

        with sqlite3.connect(path) as connection:
            payload = json.loads(connection.execute(
                "SELECT payload_json FROM narration_resume_capsules WHERE capsule_id=?",
                ("capsule-1",),
            ).fetchone()[0])
            payload["action"] = "ação adulterada"
            connection.execute(
                "UPDATE narration_resume_capsules SET payload_json=? WHERE capsule_id=?",
                (json.dumps(payload), "capsule-1"),
            )
        with pytest.raises(PersistenceError, match="hash mismatch"):
            await recovered.load_active_narration_resume_capsule("session-1")

    asyncio.run(scenario())


def test_schema_v1_attempt_hashes_migrate_transactionally(tmp_path):
    async def scenario():
        database_path = tmp_path / "schema-v1.sqlite3"
        request_metadata = {"draft_id": "draft-old"}
        terminal_digest = _hash_payload({"legacy": "terminal-result"})
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
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
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                """
            )
            connection.execute(
                """INSERT INTO campaigns(
                       session_id, chronicle_name, schema_version, current_turn,
                       state_json, relationships_json, metadata_json, created_at, updated_at
                   ) VALUES (?, '', 1, 1, '{}', '{}', '{}', ?, ?)""",
                ("session-old", _now().isoformat(), _now().isoformat()),
            )
            connection.execute(
                """INSERT INTO attempts(
                       attempt_id, session_id, operation_id, requested_turn, status,
                       user_input, metadata_json, payload_hash, committed_turn_id,
                       started_at, completed_at
                   ) VALUES (?, ?, ?, 1, 'completed', ?, ?, ?, ?, ?, ?)""",
                (
                    "attempt-old",
                    "session-old",
                    "operation-old",
                    "Eu observo.",
                    json.dumps(request_metadata, separators=(",", ":"), sort_keys=True),
                    terminal_digest,
                    "turn-old",
                    _now().isoformat(),
                    _now().isoformat(),
                ),
            )

        store = SQLitePersistence(database_path)
        await store.initialize()
        attempt = (await store.list_attempts("session-old"))[0]
        expected_request_hash = _hash_payload(
            {
                "requested_turn": 1,
                "user_input": "Eu observo.",
                "metadata": request_metadata,
            }
        )

        assert (await store.database_info())["schema_version"] == 4
        assert attempt["payload_hash"] == terminal_digest
        assert attempt["request_hash"] == expected_request_hash
        assert attempt["result_hash"] == terminal_digest
        with sqlite3.connect(database_path) as connection:
            campaign_version = connection.execute(
                "SELECT schema_version FROM campaigns WHERE session_id='session-old'"
            ).fetchone()[0]
        assert campaign_version == 4

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("case", "session_column", "status_column", "error_match"),
    (
        (
            "missing-foreign-key",
            "session_id TEXT NOT NULL",
            "status TEXT NOT NULL CHECK (status IN ('pending','completed','failed','cancelled','timeout'))",
            "FOREIGN KEY",
        ),
        (
            "missing-check",
            "session_id TEXT NOT NULL REFERENCES campaigns(session_id) ON DELETE CASCADE",
            "status TEXT NOT NULL",
            "CHECK",
        ),
    ),
)
def test_schema_v1_rejects_missing_integrity_constraints_without_mutation(
    tmp_path,
    case,
    session_column,
    status_column,
    error_match,
):
    async def scenario():
        database_path = tmp_path / f"schema-v1-{case}.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                f"""
                PRAGMA user_version = 1;
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{{}}',
                    relationships_json TEXT NOT NULL DEFAULT '{{}}',
                    metadata_json TEXT NOT NULL DEFAULT '{{}}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL UNIQUE,
                    {session_column},
                    operation_id TEXT NOT NULL,
                    requested_turn INTEGER,
                    {status_column},
                    user_input TEXT NOT NULL DEFAULT '',
                    partial_narrative TEXT NOT NULL DEFAULT '',
                    error_json TEXT,
                    provenance_json TEXT,
                    usage_json TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{{}}',
                    payload_hash TEXT NOT NULL,
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                """
            )
            before = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()

        with pytest.raises(SchemaVersionError, match=error_match):
            await SQLitePersistence(database_path).initialize()

        with sqlite3.connect(database_path) as connection:
            after = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()
            assert after == before
            assert connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0] == "1"
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1

    asyncio.run(scenario())


def test_schema_v1_migration_rolls_back_all_changes_on_corrupt_metadata(tmp_path):
    async def scenario():
        database_path = tmp_path / "schema-v1-corrupt.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                PRAGMA user_version = 1;
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
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
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                """
            )
            now = _now().isoformat()
            connection.execute(
                """INSERT INTO campaigns(
                       session_id, schema_version, created_at, updated_at
                   ) VALUES ('session-corrupt', 1, ?, ?)""",
                (now, now),
            )
            connection.execute(
                """INSERT INTO attempts(
                       attempt_id, session_id, operation_id, requested_turn, status,
                       user_input, metadata_json, payload_hash, started_at
                   ) VALUES (
                       'attempt-corrupt', 'session-corrupt', 'operation-corrupt',
                       1, 'pending', 'Eu observo.', '{', 'legacy-digest', ?
                   )""",
                (now,),
            )

        with pytest.raises(SchemaVersionError, match="invalid metadata_json"):
            await SQLitePersistence(database_path).initialize()

        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(attempts)")
            }
            metadata_version = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0]
            campaign_version = connection.execute(
                "SELECT schema_version FROM campaigns WHERE session_id='session-corrupt'"
            ).fetchone()[0]
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]

        assert "request_hash" not in columns
        assert "result_hash" not in columns
        assert metadata_version == "1"
        assert campaign_version == 1
        assert user_version == 1

    asyncio.run(scenario())


def test_schema_v1_prevalidation_rejects_missing_columns_without_mutation(tmp_path):
    async def scenario():
        database_path = tmp_path / "schema-v1-incomplete.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                PRAGMA user_version = 1;
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
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
                    committed_turn_id TEXT,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                """
            )
            before_schema = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()

        with pytest.raises(SchemaVersionError, match="started_at"):
            await SQLitePersistence(database_path).initialize()

        with sqlite3.connect(database_path) as connection:
            after_schema = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()
            metadata_version = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0]
            campaign_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(campaigns)")
            }
            attempt_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(attempts)")
            }
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]

        assert after_schema == before_schema
        assert metadata_version == "1"
        assert user_version == 1
        assert "state_revision" not in campaign_columns
        assert "request_hash" not in attempt_columns
        assert "result_hash" not in attempt_columns

    asyncio.run(scenario())


def test_schema_v1_partial_turns_table_is_rejected_without_mutation(tmp_path):
    async def scenario():
        database_path = tmp_path / "schema-v1-partial-turns.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                PRAGMA user_version = 1;
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
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
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                CREATE TABLE turns (session_id TEXT, turn_number INTEGER);
                """
            )
            before_schema = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()
            before_journal = connection.execute("PRAGMA journal_mode").fetchone()[0]

        with pytest.raises(SchemaVersionError, match="table 'turns'.*missing columns"):
            await SQLitePersistence(database_path).initialize()

        with sqlite3.connect(database_path) as connection:
            after_schema = connection.execute(
                """SELECT type, name, sql FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
            ).fetchall()
            assert after_schema == before_schema
            assert connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0] == "1"
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == before_journal
            assert {
                row[1] for row in connection.execute("PRAGMA table_info(attempts)")
            }.isdisjoint({"request_hash", "result_hash"})
            assert "state_revision" not in {
                row[1] for row in connection.execute("PRAGMA table_info(campaigns)")
            }

    asyncio.run(scenario())


def test_schema_v1_late_failure_rolls_back_ddl_and_version_markers(tmp_path):
    async def scenario():
        database_path = tmp_path / "schema-v1-late-failure.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                PRAGMA user_version = 1;
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta(key, value) VALUES('schema_version', '1');
                CREATE TABLE campaigns (
                    session_id TEXT PRIMARY KEY,
                    chronicle_name TEXT NOT NULL DEFAULT '',
                    schema_version INTEGER NOT NULL,
                    current_turn INTEGER NOT NULL DEFAULT 0 CHECK (current_turn >= 0),
                    state_json TEXT NOT NULL DEFAULT '{}',
                    relationships_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE attempts (
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
                    committed_turn_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(session_id, operation_id)
                );
                INSERT INTO campaigns(
                    session_id, schema_version, created_at, updated_at
                ) VALUES('late-session', 1, 'now', 'now');
                CREATE TRIGGER reject_schema_upgrade
                BEFORE UPDATE OF schema_version ON campaigns
                WHEN NEW.schema_version = 4
                BEGIN
                    SELECT RAISE(ABORT, 'late migration failure');
                END;
                """
            )

        with pytest.raises(sqlite3.IntegrityError, match="late migration failure"):
            await SQLitePersistence(database_path).initialize()

        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "turns" not in tables
            assert "events" not in tables
            assert "state_revision" not in {
                row[1] for row in connection.execute("PRAGMA table_info(campaigns)")
            }
            assert {
                row[1] for row in connection.execute("PRAGMA table_info(attempts)")
            }.isdisjoint({"request_hash", "result_hash"})
            assert connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0] == "1"
            assert connection.execute(
                "SELECT schema_version FROM campaigns WHERE session_id='late-session'"
            ).fetchone()[0] == 1
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1

    asyncio.run(scenario())


def test_commit_is_idempotent_monotonic_and_accepts_turn_models(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        await store.ensure_campaign(
            "session-a",
            chronicle_name="Noites",
            initial_state={"hunger": 1},
        )
        fact, event, narrative, candidate, memory = _turn_records(
            "session-a", "turn-a", "a"
        )
        kwargs = dict(
            session_id="session-a",
            operation_id="operation-a",
            turn_id="turn-a",
            turn_number=1,
            base_revision=0,
            state={"hunger": 2},
            relationships={"xerife": {"trust": 1}},
            narrative=narrative,
            facts=(fact,),
            events=(event,),
            memory_candidates=(candidate,),
            episodic_memories=(memory,),
            user_input="Eu uso o sangue.",
        )
        started = await store.start_attempt(
            session_id="session-a",
            operation_id="operation-a",
            requested_turn=1,
            user_input="Eu uso o sangue.",
            metadata={"draft_id": "draft-a"},
        )
        first = await store.commit_turn(**kwargs)
        second = await store.commit_turn(**kwargs)
        restarted = await store.start_attempt(
            session_id="session-a",
            operation_id="operation-a",
            requested_turn=1,
            user_input="Eu uso o sangue.",
            metadata={"draft_id": "draft-a"},
        )

        assert started.status == "pending"
        assert first.turn_number == 1
        assert first.idempotent is False
        assert second == type(second)("session-a", "operation-a", "turn-a", 1, True)
        assert restarted.status == "completed"
        assert restarted.idempotent is True

        attempt = (await store.list_attempts("session-a"))[0]
        assert attempt["payload_hash"] == attempt["request_hash"]
        assert attempt["request_hash"] != attempt["result_hash"]
        with pytest.raises(IdempotencyConflictError):
            await store.start_attempt(
                session_id="session-a",
                operation_id="operation-a",
                requested_turn=1,
                user_input="Eu uso o sangue.",
                metadata={"draft_id": "different-draft"},
            )

        campaign = await store.load_campaign("session-a")
        assert campaign["current_turn"] == 1
        assert campaign["state"] == {"hunger": 2}
        assert len(await store.list_turns("session-a")) == 1
        assert (await store.list_turns("session-a"))[0]["facts"][0]["fact_id"] == "fact-a"
        assert (await store.list_events("session-a"))[0]["fact_ids"] == ["fact-a"]
        assert len(await store.list_memory_candidates("session-a")) == 1
        stored_memories = await store.list_episodic_memories("session-a")
        assert len(stored_memories) == 1

        changed = dict(kwargs)
        changed["narrative"] = narrative.model_copy(
            update={"text": "Outra narrativa para a mesma operação."}
        )
        with pytest.raises(IdempotencyConflictError):
            await store.commit_turn(**changed)

        fact_b, event_b, narrative_b, _, _ = _turn_records(
            "session-a", "turn-b", "b"
        )
        with pytest.raises(TurnSequenceError):
            await store.commit_turn(
                session_id="session-a",
                operation_id="operation-b",
                turn_id="turn-b",
                turn_number=3,
                state={"hunger": 3},
                narrative=narrative_b,
                facts=(fact_b,),
                events=(event_b,),
            )
        assert (await store.load_campaign("session-a"))["current_turn"] == 1

        with pytest.raises(TurnSequenceError):
            await store.update_campaign_snapshot(
                "session-a",
                state={"hunger": 1, "available_xp": 10},
                expected_turn=0,
                expected_revision=1,
            )
        unchanged = await store.load_campaign("session-a")
        assert unchanged["state"] == {"hunger": 2}
        assert unchanged["current_turn"] == 1

        updated = await store.update_campaign_snapshot(
            "session-a",
            state={"hunger": 2, "available_xp": 10},
            expected_turn=1,
            expected_revision=1,
        )
        assert updated["state"] == {"hunger": 2, "available_xp": 10}
        assert updated["current_turn"] == 1
        assert updated["state_revision"] == 2

    asyncio.run(scenario())


def test_snapshot_cas_rejects_one_of_two_writers_with_same_revision(tmp_path):
    async def scenario():
        database_path = tmp_path / "snapshot-cas.sqlite3"
        first_store = SQLitePersistence(database_path)
        second_store = SQLitePersistence(database_path)
        await first_store.ensure_campaign(
            "session-cas",
            initial_state={"writer": "initial"},
        )
        first_view, second_view = await asyncio.gather(
            first_store.load_campaign("session-cas"),
            second_store.load_campaign("session-cas"),
        )
        assert first_view is not None and second_view is not None
        assert first_view["state_revision"] == second_view["state_revision"] == 0

        results = await asyncio.gather(
            first_store.update_campaign_snapshot(
                "session-cas",
                state={"writer": "first"},
                expected_turn=0,
                expected_revision=first_view["state_revision"],
            ),
            second_store.update_campaign_snapshot(
                "session-cas",
                state={"writer": "second"},
                expected_turn=0,
                expected_revision=second_view["state_revision"],
            ),
            return_exceptions=True,
        )

        successes = [item for item in results if isinstance(item, dict)]
        conflicts = [item for item in results if isinstance(item, StateRevisionError)]
        assert len(successes) == 1
        assert len(conflicts) == 1
        campaign = await first_store.load_campaign("session-cas")
        assert campaign is not None
        assert campaign["state_revision"] == 1
        assert campaign["state"] == successes[0]["state"]

    asyncio.run(scenario())


def test_turn_commit_rejects_state_changed_after_preparation(tmp_path):
    async def scenario():
        database_path = tmp_path / "turn-state-cas.sqlite3"
        turn_store = SQLitePersistence(database_path)
        control_store = SQLitePersistence(database_path)
        await turn_store.ensure_campaign(
            "session-turn-cas",
            initial_state={"phase": "prepared"},
        )
        prepared_campaign = await turn_store.load_campaign("session-turn-cas")
        assert prepared_campaign is not None

        await control_store.update_campaign_snapshot(
            "session-turn-cas",
            state={"phase": "control-updated"},
            expected_turn=0,
            expected_revision=prepared_campaign["state_revision"],
        )
        fact, event, narrative, _, _ = _turn_records(
            "session-turn-cas", "turn-stale", "stale"
        )
        with pytest.raises(StateRevisionError, match="Base state revision 0"):
            await turn_store.commit_turn(
                session_id="session-turn-cas",
                operation_id="operation-stale",
                turn_id="turn-stale",
                turn_number=1,
                base_revision=0,
                base_state_revision=prepared_campaign["state_revision"],
                state={"phase": "stale-turn"},
                narrative=narrative,
                facts=(fact,),
                events=(event,),
            )

        campaign = await turn_store.load_campaign("session-turn-cas")
        assert campaign is not None
        assert campaign["current_turn"] == 0
        assert campaign["state_revision"] == 1
        assert campaign["state"] == {"phase": "control-updated"}
        assert await turn_store.list_turns("session-turn-cas") == []
        assert await turn_store.list_attempts("session-turn-cas") == []

    asyncio.run(scenario())


def test_control_completion_is_atomic_idempotent_and_cas_guarded(tmp_path):
    async def scenario():
        database_path = tmp_path / "control-completion.sqlite3"
        first_store = SQLitePersistence(database_path)
        second_store = SQLitePersistence(database_path)
        await first_store.ensure_campaign(
            "session-control",
            initial_state={"frenzy": "pending"},
        )
        request_metadata = {"interceptor": "frenzy_check"}
        for store, operation_id in (
            (first_store, "operation-control-a"),
            (second_store, "operation-control-b"),
        ):
            await store.start_attempt(
                session_id="session-control",
                operation_id=operation_id,
                requested_turn=1,
                user_input="Resisto ao frenesi.",
                metadata=request_metadata,
            )

        completion = dict(
            session_id="session-control",
            operation_id="operation-control-a",
            requested_turn=1,
            user_input="Resisto ao frenesi.",
            state={"frenzy": "resolved"},
            expected_turn=0,
            expected_state_revision=0,
            metadata={"interceptor": "frenzy_check", "outcome": "resisted"},
        )
        completed = await first_store.complete_control_attempt(**completion)
        replayed = await first_store.complete_control_attempt(**completion)
        assert completed.status == "completed"
        assert completed.idempotent is False
        assert completed.state_revision == 1
        assert replayed.status == "completed"
        assert replayed.idempotent is True
        assert replayed.state_revision == 1

        with pytest.raises(StateRevisionError):
            await second_store.complete_control_attempt(
                session_id="session-control",
                operation_id="operation-control-b",
                requested_turn=1,
                user_input="Resisto ao frenesi.",
                state={"frenzy": "other-result"},
                expected_turn=0,
                expected_state_revision=0,
                metadata={"interceptor": "frenzy_check", "outcome": "failed"},
            )
        await second_store.start_attempt(
            session_id="session-control",
            operation_id="operation-control-stale-no-state",
            requested_turn=1,
            user_input="A Besta permanece.",
            metadata=request_metadata,
        )
        with pytest.raises(StateRevisionError):
            await second_store.complete_control_attempt(
                session_id="session-control",
                operation_id="operation-control-stale-no-state",
                requested_turn=1,
                user_input="A Besta permanece.",
                state=None,
                expected_turn=0,
                expected_state_revision=0,
                metadata={"interceptor": "frenzy_check", "outcome": "failed"},
            )
        attempts = {
            attempt["operation_id"]: attempt
            for attempt in await first_store.list_attempts("session-control")
        }
        assert attempts["operation-control-a"]["status"] == "completed"
        assert attempts["operation-control-a"]["committed_turn_id"] is None
        assert attempts["operation-control-b"]["status"] == "pending"
        assert attempts["operation-control-stale-no-state"]["status"] == "pending"
        campaign = await first_store.load_campaign("session-control")
        assert campaign is not None
        assert campaign["state"] == {"frenzy": "resolved"}
        assert campaign["state_revision"] == 1
        assert campaign["current_turn"] == 0

        await first_store.start_attempt(
            session_id="session-control",
            operation_id="operation-control-c",
            requested_turn=1,
            user_input="Resisto outra vez.",
            metadata=request_metadata,
        )
        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                CREATE TRIGGER reject_control_completion
                BEFORE UPDATE OF status ON attempts
                WHEN OLD.operation_id = 'operation-control-c'
                     AND NEW.status = 'completed'
                BEGIN
                    SELECT RAISE(ABORT, 'late control completion failure');
                END;
                """
            )
        with pytest.raises(sqlite3.IntegrityError, match="late control completion failure"):
            await first_store.complete_control_attempt(
                session_id="session-control",
                operation_id="operation-control-c",
                requested_turn=1,
                user_input="Resisto outra vez.",
                state={"frenzy": "must-roll-back"},
                expected_turn=0,
                expected_state_revision=1,
                metadata={"interceptor": "frenzy_check", "outcome": "resisted"},
            )
        rolled_back = await first_store.load_campaign("session-control")
        assert rolled_back is not None
        assert rolled_back["state"] == {"frenzy": "resolved"}
        assert rolled_back["state_revision"] == 1
        attempts = {
            attempt["operation_id"]: attempt
            for attempt in await first_store.list_attempts("session-control")
        }
        assert attempts["operation-control-c"]["status"] == "pending"

    asyncio.run(scenario())


def test_restart_recovery_cancels_pending_attempts_once_and_preserves_replay(tmp_path):
    async def scenario():
        database_path = tmp_path / "pending-recovery.sqlite3"
        original_process = SQLitePersistence(database_path)
        metadata = {
            "draft_id": "draft-interrupted",
            "websocket_terminal": {"action": "error", "terminal": True},
        }
        await original_process.start_attempt(
            session_id="session-recovery",
            operation_id="operation-recovery",
            requested_turn=1,
            user_input="Eu avanço.",
            metadata=metadata,
        )
        process_started_at = datetime.now(timezone.utc)
        await original_process.start_attempt(
            session_id="session-recovery",
            operation_id="operation-current-process",
            requested_turn=1,
            user_input="Eu aguardo.",
        )

        restarted_process = SQLitePersistence(database_path)
        assert await restarted_process.recover_pending_attempts(
            started_before=process_started_at
        ) == 1
        assert await restarted_process.recover_pending_attempts(
            started_before=process_started_at
        ) == 0
        attempts = await restarted_process.list_attempts("session-recovery")
        attempt = next(
            row for row in attempts if row["operation_id"] == "operation-recovery"
        )
        current_attempt = next(
            row
            for row in attempts
            if row["operation_id"] == "operation-current-process"
        )
        assert attempt["status"] == "cancelled"
        assert attempt["error"] == {
            "category": "cancelled",
            "code": "process_interrupted",
            "safe_message": (
                "The previous process ended before this operation completed."
            ),
        }
        assert attempt["metadata"] == metadata
        assert attempt["committed_turn_id"] is None
        assert current_attempt["status"] == "pending"
        assert await restarted_process.list_turns("session-recovery") == []

        replay = await restarted_process.start_attempt(
            session_id="session-recovery",
            operation_id="operation-recovery",
            requested_turn=1,
            user_input="Eu avanço.",
            metadata=metadata,
        )
        assert replay.status == "cancelled"
        assert replay.idempotent is True
        with pytest.raises(IdempotencyConflictError):
            await restarted_process.start_attempt(
                session_id="session-recovery",
                operation_id="operation-recovery",
                requested_turn=1,
                user_input="Eu recuo.",
                metadata=metadata,
            )

    asyncio.run(scenario())


def test_session_rehydration_keeps_the_latest_hundred_narratives(tmp_path):
    async def scenario():
        from api.state_service import (
            configure_persistence_for_tests,
            get_persistence,
            load_session_state,
            sync_event_from_context,
        )

        session_id = "session-history-window"
        store = SQLitePersistence(tmp_path / "history.sqlite3")
        previous = get_persistence()
        configure_persistence_for_tests(store)
        context = {
            "player_sheet": {
                "nome": "Karl",
                "clan": "brujah",
                "predator_type": "alleycat",
                "attributes": {"Strength": 3},
                "skills": {"Brawl": 2},
                "disciplines": {},
                "status": {
                    "blood_potency": 1,
                    "current_hunger": 1,
                    "humanity": 7,
                    "health_tracker": {
                        "size": 7,
                        "superficial": 0,
                        "aggravated": 0,
                    },
                    "willpower_tracker": {
                        "size": 5,
                        "superficial": 0,
                        "aggravated": 0,
                    },
                },
            },
            "last_action_cache": None,
            "pre_roll_snapshot": None,
        }
        initial = sync_event_from_context(session_id, context, turn_number=0)
        await store.ensure_campaign(
            session_id,
            initial_state=initial.model_dump(mode="json"),
        )
        try:
            for number in range(1, 103):
                turn_id = f"turn-{number}"
                fact, event, narrative, _, _ = _turn_records(
                    session_id, turn_id, str(number)
                )
                narrative = narrative.model_copy(
                    update={"text": f"Narrativa confirmada {number}."}
                )
                state = sync_event_from_context(
                    session_id,
                    context,
                    turn_number=number,
                )
                await store.commit_turn(
                    session_id=session_id,
                    operation_id=f"operation-{number}",
                    turn_id=turn_id,
                    turn_number=number,
                    base_revision=number - 1,
                    state=state.model_dump(mode="json"),
                    narrative=narrative,
                    facts=(fact,),
                    events=(event,),
                    user_input=f"Ação {number}",
                )

            restored = await load_session_state(session_id)
            assert restored is not None
            assert len(restored.narrative_history) == 100
            assert restored.narrative_history[0]["turn_number"] == 3
            assert restored.narrative_history[-1]["turn_number"] == 102
            assert restored.narrative_history[-1]["content"] == (
                "Narrativa confirmada 102."
            )
        finally:
            configure_persistence_for_tests(previous)

    asyncio.run(scenario())


def test_commit_rejects_incomplete_or_incoherent_records_before_transaction(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        await store.ensure_campaign("session-hard", initial_state={"revision": 0})
        fact, event, narrative, candidate, memory = _turn_records(
            "session-hard", "turn-hard", "hard"
        )

        async def rejects(operation_id: str, **overrides):
            values = {
                "session_id": "session-hard",
                "operation_id": operation_id,
                "turn_id": "turn-hard",
                "state": {"revision": 1},
                "narrative": narrative,
                "facts": (fact,),
                "events": (event,),
                "memory_candidates": (candidate,),
                "episodic_memories": (memory,),
            }
            values.update(overrides)
            with pytest.raises(ValueError):
                await store.commit_turn(**values)
            assert (await store.load_campaign("session-hard"))["current_turn"] == 0
            assert await store.list_turns("session-hard") == []
            assert await store.list_attempts("session-hard") == []

        await rejects("empty-text", narrative="   ")
        await rejects(
            "false-complete",
            narrative={
                "text": "Texto parcial",
                "complete": False,
                "source_event_ids": [event.event_id],
            },
        )
        await rejects(
            "string-complete",
            narrative={
                "text": "Texto parcial",
                "complete": "false",
                "source_event_ids": [event.event_id],
            },
        )
        await rejects(
            "missing-complete",
            narrative={"text": "Texto sem terminal", "source_event_ids": [event.event_id]},
        )

        candidate_without_sources = candidate.model_dump(mode="json")
        candidate_without_sources["source_event_ids"] = []
        candidate_without_sources["validation_status"] = "rejected"
        await rejects(
            "candidate-without-sources",
            memory_candidates=(candidate_without_sources,),
            episodic_memories=(),
        )

        candidate_unknown_source = candidate.model_dump(mode="json")
        candidate_unknown_source["source_event_ids"] = ["event-unknown"]
        await rejects(
            "candidate-unknown-source",
            memory_candidates=(candidate_unknown_source,),
            episodic_memories=(),
        )

        memory_unknown_source = memory.model_dump(mode="json")
        memory_unknown_source["source_event_ids"] = ["event-unknown"]
        await rejects(
            "memory-unknown-source",
            episodic_memories=(memory_unknown_source,),
        )

        await rejects(
            "accepted-not-promoted",
            memory_candidates=(candidate,),
            episodic_memories=(),
        )
        pending_candidate = candidate.model_copy(
            update={"validation_status": CandidateValidationStatus.PENDING}
        )
        await rejects(
            "pending-candidate",
            memory_candidates=(pending_candidate,),
            episodic_memories=(),
        )
        mismatched_memory = memory.model_copy(update={"summary": "Resumo divergente"})
        await rejects("mismatched-memory", episodic_memories=(mismatched_memory,))
        rejected_candidate = candidate.model_copy(
            update={"validation_status": CandidateValidationStatus.REJECTED}
        )
        await rejects(
            "rejected-promoted",
            memory_candidates=(rejected_candidate,),
            episodic_memories=(memory,),
        )

        secret_fact = fact.model_copy(update={"visibility": Visibility.SYSTEM})
        await rejects("event-broadens-fact", facts=(secret_fact,))
        secret_event = event.model_copy(update={"visibility": Visibility.STORYTELLER})
        secret_narrative = narrative.model_copy(
            update={"visibility": Visibility.PLAYER}
        )
        await rejects(
            "narrative-broadens-event",
            events=(secret_event,),
            narrative=secret_narrative,
            memory_candidates=(),
            episodic_memories=(),
        )

    asyncio.run(scenario())


def test_idempotency_canonicalizes_record_collection_order(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        fact_a, event_a, narrative_a, candidate_a, memory_a = _turn_records(
            "session-order", "turn-order", "order-a"
        )
        fact_b, event_b, _, candidate_b, memory_b = _turn_records(
            "session-order", "turn-order", "order-b"
        )
        event_b = event_b.model_copy(update={"sequence": 1})
        narrative = narrative_a.model_copy(
            update={"source_event_ids": (event_a.event_id, event_b.event_id)}
        )
        base = dict(
            session_id="session-order",
            operation_id="operation-order",
            turn_id="turn-order",
            state={"revision": 1},
            narrative=narrative,
            facts=(fact_a, fact_b),
            events=(event_a, event_b),
            memory_candidates=(candidate_a, candidate_b),
            episodic_memories=(memory_a, memory_b),
        )
        first = await store.commit_turn(**base)
        retry = dict(base)
        retry.update(
            narrative=narrative.model_copy(
                update={"source_event_ids": tuple(reversed(narrative.source_event_ids))}
            ),
            facts=tuple(reversed(base["facts"])),
            events=tuple(reversed(base["events"])),
            memory_candidates=tuple(reversed(base["memory_candidates"])),
            episodic_memories=tuple(reversed(base["episodic_memories"])),
        )
        second = await store.commit_turn(**retry)

        assert first.turn_number == 1
        assert second.idempotent is True
        assert len(await store.list_turns("session-order")) == 1
        assert len(await store.list_events("session-order")) == 2

    asyncio.run(scenario())


def test_failed_attempt_is_audited_without_promoting_state(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        await store.ensure_campaign("session-f", initial_state={"hunger": 1})
        await store.start_attempt(
            session_id="session-f",
            operation_id="operation-f",
            attempt_id="attempt-f",
            requested_turn=1,
            user_input="Eu observo o salão.",
        )
        first = await store.record_failed_attempt(
            session_id="session-f",
            operation_id="operation-f",
            attempt_id="attempt-f",
            requested_turn=1,
            user_input="Eu observo o salão.",
            status="timeout",
            partial_narrative="As luzes tremem",
            error={"code": "timeout"},
            provenance={"model": "unknown"},
            usage={"status": "unavailable"},
        )
        second = await store.record_failed_attempt(
            session_id="session-f",
            operation_id="operation-f",
            attempt_id="attempt-f",
            requested_turn=1,
            user_input="Eu observo o salão.",
            status="timeout",
            partial_narrative="As luzes tremem",
            error={"code": "timeout"},
            provenance={"model": "unknown"},
            usage={"status": "unavailable"},
        )
        assert first.status == "timeout"
        assert second.idempotent is True

        campaign = await store.load_campaign("session-f")
        assert campaign["current_turn"] == 0
        assert campaign["state"] == {"hunger": 1}
        attempts = await store.list_attempts("session-f")
        assert attempts[0]["status"] == "timeout"
        assert attempts[0]["partial_narrative"] == "As luzes tremem"
        assert attempts[0]["error"] == {"code": "timeout"}
        assert await store.list_turns("session-f") == []

        fact, event, narrative, _, _ = _turn_records("session-f", "turn-f", "f")
        with pytest.raises(IdempotencyConflictError):
            await store.commit_turn(
                session_id="session-f",
                operation_id="operation-f",
                attempt_id="attempt-f",
                turn_id="turn-f",
                state={"hunger": 2},
                narrative=narrative,
                facts=(fact,),
                events=(event,),
            )

    asyncio.run(scenario())


def test_concurrent_commits_are_serial_and_monotonic(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")

        async def commit(index: int):
            turn_id = f"turn-{index}"
            fact, event, narrative, _, _ = _turn_records(
                "session-c", turn_id, str(index)
            )
            return await store.commit_turn(
                session_id="session-c",
                operation_id=f"operation-{index}",
                turn_id=turn_id,
                state={"writer": index},
                narrative=narrative,
                facts=(fact,),
                events=(event,),
            )

        results = await asyncio.gather(*(commit(index) for index in range(8)))
        assert sorted(item.turn_number for item in results) == list(range(1, 9))
        assert (await store.load_campaign("session-c"))["current_turn"] == 8
        assert [item["turn_number"] for item in await store.list_turns("session-c")] == list(
            range(1, 9)
        )

    asyncio.run(scenario())


def test_constraint_failure_rolls_back_the_entire_turn(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        fact, event, narrative, _, _ = _turn_records("session-r", "turn-r1", "shared")
        await store.commit_turn(
            session_id="session-r",
            operation_id="operation-r1",
            turn_id="turn-r1",
            state={"revision": 1},
            narrative=narrative,
            facts=(fact,),
            events=(event,),
        )

        fact_2, event_2, narrative_2, _, _ = _turn_records(
            "session-r", "turn-r2", "second"
        )
        event_2 = event_2.model_copy(update={"event_id": event.event_id})
        narrative_2 = narrative_2.model_copy(
            update={"source_event_ids": (event.event_id,)}
        )
        with pytest.raises(sqlite3.IntegrityError):
            await store.commit_turn(
                session_id="session-r",
                operation_id="operation-r2",
                turn_id="turn-r2",
                state={"revision": 2},
                narrative=narrative_2,
                facts=(fact_2,),
                events=(event_2,),
            )

        campaign = await store.load_campaign("session-r")
        assert campaign["current_turn"] == 1
        assert campaign["state"] == {"revision": 1}
        assert len(await store.list_turns("session-r")) == 1
        assert len(await store.list_attempts("session-r")) == 1

    asyncio.run(scenario())


def test_retrieval_visibility_scoring_budget_and_consolidation_versions(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        fact, event, narrative, _, _ = _turn_records("session-m", "turn-m", "m")
        memories = (
            EpisodicMemory(
                memory_id="memory-xerife",
                session_id="session-m",
                summary="O Xerife prometeu cobrar a dívida.",
                source_event_ids=(event.event_id,),
                tags=("xerife", "dívida"),
                importance=0.9,
                pending=True,
            ),
            EpisodicMemory(
                memory_id="memory-praca",
                session_id="session-m",
                summary="A praça ficou vazia depois da chuva.",
                source_event_ids=(event.event_id,),
                importance=0.2,
            ),
            EpisodicMemory(
                memory_id="memory-secret",
                session_id="session-m",
                summary="O Príncipe ordenou uma emboscada secreta.",
                source_event_ids=(event.event_id,),
                visibility=Visibility.STORYTELLER,
                importance=1.0,
            ),
        )
        candidates = tuple(
            MemoryCandidate(
                candidate_id=f"candidate-{memory.memory_id}",
                session_id=memory.session_id,
                turn_id="turn-m",
                created_at=memory.created_at,
                summary=memory.summary,
                source_event_ids=memory.source_event_ids,
                tags=memory.tags,
                actors=memory.actors,
                place=memory.place,
                occurred_at=memory.occurred_at,
                importance=memory.importance,
                visibility=memory.visibility,
                pending=memory.pending,
                validation_status=CandidateValidationStatus.ACCEPTED,
            )
            for memory in memories
        )
        await store.commit_turn(
            session_id="session-m",
            operation_id="operation-m",
            turn_id="turn-m",
            state={"revision": 1},
            narrative=narrative,
            facts=(fact,),
            events=(event,),
            memory_candidates=candidates,
            episodic_memories=memories,
        )

        selected = await store.retrieve_memories(
            "session-m",
            query="xerife dívida",
            allowed_visibilities=("public", "player"),
            token_budget=2,
            token_estimator=lambda _text: 1,
        )
        assert [item["memory_id"] for item in selected] == [
            "memory-xerife",
            "memory-praca",
        ]
        assert all(item["visibility"] != "storyteller" for item in selected)

        first = Consolidation(
            consolidation_id="consolidation-1",
            session_id="session-m",
            scope=ConsolidationScope.SCENE,
            version=1,
            summary=build_grounded_consolidation_summary(
                (("memory-xerife", "O Xerife prometeu cobrar a dívida."),)
            ),
            source_memory_ids=("memory-xerife",),
            source_event_ids=(event.event_id,),
        )
        with pytest.raises(ConsolidationVersionError, match="version 1"):
            await store.save_consolidation(
                first.model_copy(
                    update={
                        "consolidation_id": "consolidation-1-invalid-link",
                        "supersedes_consolidation_id": "consolidation-does-not-exist",
                    }
                )
            )
        result = await store.save_consolidation(first)
        repeat = await store.save_consolidation(first)
        assert result.version == 1
        assert repeat.idempotent is True

        with pytest.raises(ConsolidationVersionError):
            await store.save_consolidation(
                first.model_copy(
                    update={"consolidation_id": "consolidation-3", "version": 3}
                )
            )
        with pytest.raises(ConsolidationVersionError, match="immediately previous"):
            await store.save_consolidation(
                first.model_copy(
                    update={
                        "consolidation_id": "consolidation-2-missing-link",
                        "version": 2,
                    }
                )
            )
        second = first.model_copy(
            update={
                "consolidation_id": "consolidation-2",
                "version": 2,
                "supersedes_consolidation_id": first.consolidation_id,
            }
        )
        await store.save_consolidation(second)
        with pytest.raises(ConsolidationVersionError, match="immediately previous"):
            await store.save_consolidation(
                first.model_copy(
                    update={
                        "consolidation_id": "consolidation-3-stale-link",
                        "version": 3,
                        "supersedes_consolidation_id": first.consolidation_id,
                    }
                )
            )
        third = second.model_copy(
            update={
                "consolidation_id": "consolidation-3",
                "version": 3,
                "supersedes_consolidation_id": second.consolidation_id,
            }
        )
        await store.save_consolidation(third)
        assert [item["version"] for item in await store.list_consolidations(
            "session-m", scope="scene"
        )] == [1, 2, 3]

    asyncio.run(scenario())


def test_consolidation_validates_sources_visibility_and_reordered_retry(tmp_path):
    async def scenario():
        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        fact_a, event_a, narrative_a, candidate_a, memory_a = _turn_records(
            "session-c", "turn-c", "consolidation-a"
        )
        fact_b, event_b, _, candidate_b, memory_b = _turn_records(
            "session-c", "turn-c", "consolidation-b"
        )
        event_b = event_b.model_copy(update={"sequence": 1})
        candidate_a = candidate_a.model_copy(
            update={"visibility": Visibility.STORYTELLER}
        )
        memory_a = memory_a.model_copy(update={"visibility": Visibility.STORYTELLER})
        candidate_b = candidate_b.model_copy(update={"visibility": Visibility.STORYTELLER})
        memory_b = memory_b.model_copy(update={"visibility": Visibility.STORYTELLER})
        narrative = narrative_a.model_copy(
            update={
                "source_event_ids": (event_a.event_id, event_b.event_id),
                "visibility": Visibility.STORYTELLER,
            }
        )
        await store.commit_turn(
            session_id="session-c",
            operation_id="operation-c",
            turn_id="turn-c",
            state={"revision": 1},
            narrative=narrative,
            facts=(fact_a, fact_b),
            events=(event_a, event_b),
            memory_candidates=(candidate_a, candidate_b),
            episodic_memories=(memory_a, memory_b),
        )

        consolidation = Consolidation(
            consolidation_id="consolidation-c",
            session_id="session-c",
            scope=ConsolidationScope.SCENE,
            summary=build_grounded_consolidation_summary(
                (
                    (memory_a.memory_id, memory_a.summary),
                    (memory_b.memory_id, memory_b.summary),
                )
            ),
            source_memory_ids=(memory_b.memory_id, memory_a.memory_id),
            source_event_ids=(event_b.event_id, event_a.event_id),
            visibility=Visibility.STORYTELLER,
        )
        with pytest.raises(ValueError, match="derived exactly"):
            await store.save_consolidation(
                consolidation.model_copy(
                    update={
                        "consolidation_id": "consolidation-ungrounded",
                        "summary": "O Príncipe morreu sem que as fontes registrem isso.",
                    }
                )
            )
        first = await store.save_consolidation(consolidation)
        retry = await store.save_consolidation(
            consolidation.model_copy(
                update={
                    "source_memory_ids": tuple(reversed(consolidation.source_memory_ids)),
                    "source_event_ids": tuple(reversed(consolidation.source_event_ids)),
                }
            )
        )
        assert first.idempotent is False
        assert retry.idempotent is True
        stored = await store.list_consolidations("session-c", scope="scene")
        assert len(stored) == 1
        assert stored[0]["source_memory_ids"] == sorted(consolidation.source_memory_ids)
        assert stored[0]["source_event_ids"] == sorted(consolidation.source_event_ids)

        # A legacy/tampered free summary is neutralized before any caller can
        # inject it into narrative context.
        with sqlite3.connect(store.db_path) as connection:
            payload = json.loads(
                connection.execute(
                    "SELECT payload_json FROM consolidations WHERE consolidation_id=?",
                    (consolidation.consolidation_id,),
                ).fetchone()[0]
            )
            payload["summary"] = "O Príncipe morreu sem fonte canônica."
            payload["source_event_ids"] = ["event-invented"]
            payload["visibility"] = Visibility.PLAYER.value
            connection.execute(
                """UPDATE consolidations
                   SET summary=?, source_event_ids_json=?, visibility=?, payload_json=?
                   WHERE consolidation_id=?""",
                (
                    payload["summary"],
                    json.dumps(["event-invented"]),
                    Visibility.PLAYER.value,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    consolidation.consolidation_id,
                ),
            )
        recovered = await store.list_consolidations("session-c", scope="scene")
        assert recovered[0]["summary"] == consolidation.summary
        assert recovered[0]["payload"]["summary"] == consolidation.summary
        assert "Príncipe morreu" not in recovered[0]["summary"]
        assert recovered[0]["source_event_ids"] == sorted(
            consolidation.source_event_ids
        )
        assert recovered[0]["payload"]["source_event_ids"] == sorted(
            consolidation.source_event_ids
        )
        assert recovered[0]["visibility"] == Visibility.STORYTELLER.value
        assert recovered[0]["payload"]["visibility"] == (
            Visibility.STORYTELLER.value
        )

        invalid_base = consolidation.model_copy(
            update={"consolidation_id": "invalid-c", "version": 2}
        )
        invalid_updates = (
            {"source_memory_ids": (memory_a.memory_id, "memory-missing")},
            {"source_event_ids": (event_a.event_id,)},
            {"source_event_ids": (event_a.event_id, event_b.event_id, "event-extra")},
            {"visibility": Visibility.PLAYER},
            {"source_memory_ids": (memory_a.memory_id, memory_a.memory_id)},
            {"source_event_ids": (event_a.event_id, f" {event_b.event_id}")},
        )
        for index, update in enumerate(invalid_updates):
            with pytest.raises(ValueError):
                await store.save_consolidation(
                    invalid_base.model_copy(
                        update={"consolidation_id": f"invalid-c-{index}", **update}
                    )
                )

        other_fact, other_event, other_narrative, other_candidate, other_memory = (
            _turn_records("session-other", "turn-other", "other")
        )
        await store.commit_turn(
            session_id="session-other",
            operation_id="operation-other",
            turn_id="turn-other",
            state={"revision": 1},
            narrative=other_narrative,
            facts=(other_fact,),
            events=(other_event,),
            memory_candidates=(other_candidate,),
            episodic_memories=(other_memory,),
        )
        with pytest.raises(ValueError, match="consolidation session"):
            await store.save_consolidation(
                invalid_base.model_copy(
                    update={
                        "consolidation_id": "invalid-other-session",
                        "source_memory_ids": (other_memory.memory_id,),
                        "source_event_ids": (other_event.event_id,),
                    }
                )
            )

        assert len(await store.list_consolidations("session-c", scope="scene")) == 1

    asyncio.run(scenario())


def test_legacy_migration_is_lazy_idempotent_and_preserves_exact_bytes(tmp_path):
    async def scenario():
        from api.memory_service import CampaignMemory, SceneMemory, SessionMemory
        from api.relationship_service import (
            NpcRelationship,
            RelationshipState,
            load_relationships,
        )
        import api.state_service as state_service_module
        from api.state_service import (
            configure_persistence_for_tests,
            get_persistence,
            load_session_state,
            sync_event_from_context,
        )

        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        session_id = "legacy_01"
        state_payload = sync_event_from_context(
            session_id,
            {
                "player_sheet": {
                    "nome": "Karl",
                    "attributes": {"Composure": 3, "Resolve": 3},
                    "status": {
                        "current_hunger": 2,
                        "humanity": 6,
                        "health_tracker": {
                            "size": 7,
                            "superficial": 1,
                            "aggravated": 0,
                        },
                        "willpower_tracker": {
                            "size": 5,
                            "superficial": 0,
                            "aggravated": 0,
                        },
                    },
                }
            },
            turn_number=3,
        ).model_dump(mode="json")
        state_payload.update({"chronicle_name": "Noites", "turn": 3})
        memory_payload = SessionMemory(
            session_id=session_id,
            scene=SceneMemory(
                recent_events=["T4: O jogador ouviu o Xerife"],
                last_updated_turn=4,
            ),
            campaign=CampaignMemory(
                key_decisions=[{"summary": "Aceitou a dívida"}],
                chronicle_arcs=["Cobrança pendente"],
                last_updated_turn=4,
            ),
        ).model_dump(mode="json")
        relationships_payload = RelationshipState(
            session_id=session_id,
            relationships={
                "xerife": NpcRelationship(npc_id="xerife", trust_level=2)
            },
        ).model_dump(mode="json")
        originals = {
            "state": (json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "memory": (json.dumps(memory_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "relationships": (
                json.dumps(relationships_payload, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8"),
        }
        paths = {
            "state": legacy_dir / f"{session_id}.json",
            "memory": legacy_dir / f"{session_id}_memory.json",
            "relationships": legacy_dir / f"{session_id}_relationships.json",
        }
        for kind, path in paths.items():
            path.write_bytes(originals[kind])

        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        result = await store.migrate_legacy_session(session_id, legacy_dir)
        repeat = await store.migrate_legacy_session(session_id, legacy_dir)
        assert result.status == "migrated"
        assert result.imported is True
        assert result.current_turn == 4
        assert result.imported_memories == 3
        assert repeat.status == "already_migrated"
        assert repeat.idempotent is True

        campaign = await store.load_campaign(session_id)
        assert campaign["current_turn"] == 4
        assert campaign["state"]["chronicle_name"] == "Noites"
        assert len(await store.list_episodic_memories(session_id)) == 3

        previous_store = get_persistence()
        previous_save_dir = state_service_module.SAVE_DIR
        configure_persistence_for_tests(store)
        state_service_module.SAVE_DIR = str(legacy_dir)
        try:
            restored_state = await load_session_state(session_id)
            restored_relationships = await load_relationships(session_id)
        finally:
            state_service_module.SAVE_DIR = previous_save_dir
            configure_persistence_for_tests(previous_store)
        assert restored_state is not None
        assert restored_state.turn_number == 4
        assert restored_state.character.fome == 2
        assert restored_relationships.relationships["xerife"].trust_level == 2

        imports = {item["source_kind"]: item for item in await store.list_legacy_imports(session_id)}
        assert set(imports) == set(originals)
        for kind, path in paths.items():
            assert path.read_bytes() == originals[kind]
            assert imports[kind]["raw_bytes"] == originals[kind]
            assert imports[kind]["parse_status"] == "valid"
            assert imports[kind]["applied_at"] is not None

    asyncio.run(scenario())


@pytest.mark.parametrize("invalid_kind", ["state", "relationships"])
def test_schema_invalid_legacy_source_is_audited_and_repairable(
    tmp_path,
    invalid_kind,
):
    async def scenario():
        from api.relationship_service import (
            NpcRelationship,
            RelationshipState,
            load_relationships,
        )
        import api.state_service as state_service_module
        from api.state_service import (
            configure_persistence_for_tests,
            get_persistence,
            load_session_state,
            sync_event_from_context,
        )

        session_id = f"legacy_schema_{invalid_kind}"
        legacy_dir = tmp_path / invalid_kind
        legacy_dir.mkdir()
        state_payload = sync_event_from_context(
            session_id,
            {"player_sheet": {"attributes": {}, "status": {}}},
            turn_number=2,
        ).model_dump(mode="json")
        relationship_payload = RelationshipState(
            session_id=session_id,
            relationships={
                "xerife": NpcRelationship(npc_id="xerife", trust_level=2)
            },
        ).model_dump(mode="json")
        valid_bytes = {
            "state": json.dumps(state_payload, ensure_ascii=False).encode("utf-8"),
            "relationships": json.dumps(
                relationship_payload, ensure_ascii=False
            ).encode("utf-8"),
        }
        invalid_bytes = (
            json.dumps({"session_id": session_id, "turn": 2}).encode("utf-8")
            if invalid_kind == "state"
            else json.dumps(
                {
                    "session_id": session_id,
                    "relationships": {"xerife": {"trust_level": 2}},
                }
            ).encode("utf-8")
        )
        paths = {
            "state": legacy_dir / f"{session_id}.json",
            "relationships": legacy_dir / f"{session_id}_relationships.json",
        }
        for kind, path in paths.items():
            path.write_bytes(invalid_bytes if kind == invalid_kind else valid_bytes[kind])

        store = SQLitePersistence(tmp_path / f"{invalid_kind}.sqlite3")
        with pytest.raises(LegacyCorruptionError) as exc_info:
            await store.migrate_legacy_session(session_id, legacy_dir)
        assert exc_info.value.sources == (invalid_kind,)
        assert await store.load_campaign(session_id) is None
        first_import = next(
            item
            for item in await store.list_legacy_imports(session_id)
            if item["source_kind"] == invalid_kind
        )
        assert first_import["raw_bytes"] == invalid_bytes
        assert first_import["parse_status"] == "corrupt"
        assert first_import["applied_at"] is None

        paths[invalid_kind].write_bytes(valid_bytes[invalid_kind])
        repaired = await store.migrate_legacy_session(session_id, legacy_dir)
        assert repaired.status == "migrated"
        assert repaired.current_turn == 2

        previous_store = get_persistence()
        previous_save_dir = state_service_module.SAVE_DIR
        configure_persistence_for_tests(store)
        state_service_module.SAVE_DIR = str(legacy_dir)
        try:
            restored_state = await load_session_state(session_id)
            restored_relationships = await load_relationships(session_id)
        finally:
            state_service_module.SAVE_DIR = previous_save_dir
            configure_persistence_for_tests(previous_store)
        assert restored_state is not None
        assert restored_state.turn_number == 2
        assert restored_relationships.relationships["xerife"].npc_id == "xerife"

        repaired_imports = [
            item
            for item in await store.list_legacy_imports(session_id)
            if item["source_kind"] == invalid_kind
        ]
        assert len(repaired_imports) == 2
        assert repaired_imports[0]["applied_at"] is None
        assert repaired_imports[1]["parse_status"] == "valid"
        assert repaired_imports[1]["applied_at"] is not None

    asyncio.run(scenario())


def test_corrupt_legacy_json_is_audited_but_never_promoted(tmp_path):
    async def scenario():
        from api.memory_service import SceneMemory, SessionMemory
        from api.state_service import sync_event_from_context

        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        session_id = "legacy_bad"
        state_payload = sync_event_from_context(
            session_id,
            {"player_sheet": {"attributes": {}, "status": {}}},
            turn_number=2,
        ).model_dump(mode="json")
        (legacy_dir / f"{session_id}.json").write_bytes(
            json.dumps(state_payload).encode("utf-8")
        )
        corrupt_bytes = b'{"scene": [}'
        (legacy_dir / f"{session_id}_memory.json").write_bytes(corrupt_bytes)

        store = SQLitePersistence(tmp_path / "campaign.sqlite3")
        with pytest.raises(LegacyCorruptionError) as exc_info:
            await store.migrate_legacy_session(session_id, legacy_dir)
        assert exc_info.value.sources == ("memory",)
        assert await store.load_campaign(session_id) is None

        imports = {item["source_kind"]: item for item in await store.list_legacy_imports(session_id)}
        assert imports["memory"]["parse_status"] == "corrupt"
        assert imports["memory"]["raw_bytes"] == corrupt_bytes
        assert imports["memory"]["applied_at"] is None

        repaired_bytes = json.dumps(
            SessionMemory(
                session_id=session_id,
                scene=SceneMemory(recent_events=["T2: Memoria reparada"]),
            ).model_dump(mode="json"),
            ensure_ascii=False,
        ).encode("utf-8")
        (legacy_dir / f"{session_id}_memory.json").write_bytes(repaired_bytes)
        repaired = await store.migrate_legacy_session(session_id, legacy_dir)
        assert repaired.status == "migrated"
        assert repaired.current_turn == 2

        memory_imports = [
            item
            for item in await store.list_legacy_imports(session_id)
            if item["source_kind"] == "memory"
        ]
        assert [item["parse_status"] for item in memory_imports] == ["corrupt", "valid"]
        assert memory_imports[0]["raw_bytes"] == corrupt_bytes
        assert memory_imports[0]["applied_at"] is None
        assert memory_imports[1]["raw_bytes"] == repaired_bytes
        assert memory_imports[1]["applied_at"] is not None

    asyncio.run(scenario())
