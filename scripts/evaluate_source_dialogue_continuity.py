"""Two fixed dialogues through real P/K/H; the second source is the first commit.

New synthetic consumer, not an invocation or mutation of historical evaluators.
The preflight freezes construction inputs, not a future generated HTTP body.
Only complete committed n becomes a source; q and authored briefing do not.
Local artifact consistency and replay do not approve narrative quality.
"""


from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from uuid import UUID, uuid5

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr
from api.llm.contract import CancellationToken, GenerationParameters, LLMTarget, utc_now
from api.narrative_source_capsule import source_preparation_operation_id, validate_source_turn_capsule
from api.narrative_source_coordinator import execute_retained_source_turn
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_input import (
    SourceInputClaim, create_source_input_completion, create_source_producer_config,
    source_input_operation_id, source_input_request_hash, source_input_result_hash,
)
from api.narrative_source_input_service import prepare_source_player_action
from api.narrative_source_preparation import DeclaredActionPreparation
from api.narrative_source_status import safe_source_failure
from api.narrative_source_setup import create_source_setup_manifest, validate_source_setup_manifest
from api.narrative_source_setup_service import create_source_trial_setup
from api.rules_service import PlayerSheetModel, StatusModel, TrackerModel
from scripts import evaluate_retained_source as retained
from scripts.evaluate_source_context import _verify_evidence

shared = retained.shared
profile = retained.profile
_json, _sha, _same = retained._json, retained._sha, retained._same
_request, _batch = retained._request, retained._batch
_read_json, _loads = retained._read_json, retained._loads
_result_record = retained._result_record
ProbePersistence, NoCallGateway = retained.ProbePersistence, retained.NoCallGateway
GROQ_QWEN_MODEL_ID = retained.GROQ_QWEN_MODEL_ID
PROBE_KIND = "source_dialogue_continuity_probe"
EXPERIMENT_VERSION = "source-dialogue-continuity-v1"
PROTOCOL = profile.VERSION
CANDIDATE_ID = retained.CANDIDATE_ID
KEY_ENV = "STORYTELLER_SOURCE_DIALOGUE_CONTINUITY_GROQ_KEY"
TARGET_PROFILE = "source-dialogue-continuity-" + CANDIDATE_ID
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
DATABASE_NAME = "source-dialogue-continuity.sqlite3"
MANIFEST_PATH, MANIFEST_SHA256 = retained.MANIFEST_PATH, retained.MANIFEST_SHA256
PROMPT_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-dialogue-v1.md"
PROMPT_FILE_SHA256 = "473208c260c2284fdc2c65cfdcb767c8a701c64d652a9c691712be99878a779d"
CORPUS_PATH = PROJECT_ROOT / "evals/narrator/source_dialogue_continuity_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "evals/narrator/source_dialogue_continuity_protocol_v1.md"
INPUT_HASHES = {
    CORPUS_PATH: "851a9e60262bc2d5b29fd13f40eb2a76ba4a7b39436df427ff8a773f6b61b2df",
    PROTOCOL_PATH: "705dc27554ed07bfee20ed9effc0311589936b2db0578d4660c21d47ac1ba4ba",
    PROMPT_PATH: PROMPT_FILE_SHA256,
    MANIFEST_PATH: MANIFEST_SHA256,
}
MAX_CALLS = 2
PARAMETERS = {"temperature": .65, "max_output_tokens": 768, "reasoning_effort": "none",
    "max_calls": 2, "max_total_output_tokens": 1536, "initial_quiet_seconds": 60,
    "minimum_inter_call_delay_seconds": 60, "shared_turn_deadline_seconds": 60}
TURN_KEYS = ("turn-1", "turn-2")
PLAYER_INPUTS = ('Digo a Mara: "Mara, o que é este lugar?"', 'Digo a Mara: "Mara, explique melhor sua resposta."')
SETUP = {"protocol": "narrative-source-setup-request-v1", "location": "Galeria", "npcs_present": ["Mara"],
    "declared_objective": "Conhecer melhor este lugar por meio da conversa."}


IMPLEMENTATION_FILES = retained.IMPLEMENTATION_FILES + (
    "scripts/evaluate_source_dialogue_continuity.py", "api/narrative_source_setup.py", "api/narrative_source_setup_service.py",
    "api/narrative_source_entry.py", "api/narrative_source_input.py", "api/narrative_source_input_service.py",
    "api/narrative_source_action_producer.py", "api/narrative_source_status.py", "api/rules_service.py",
    "scripts/evaluate_source_context.py",
)


def _require(condition, code="source_dialogue_continuity_probe_artifact_invalid"):
    if not condition:
        raise ValueError(code)


def run_path(batch_id):
    return OUTPUT_ROOT / ("source-dialogue-continuity-" + retained._batch(batch_id))


def _operation(batch, index):
    return str(uuid5(UUID(batch), "source-dialogue-continuity." + TURN_KEYS[index]))


def _state():
    sheet = PlayerSheetModel(attributes={"Wits": 3}, skills={"Investigation": 2}, disciplines={},
        status=StatusModel(blood_potency=1, current_hunger=0, humanity=7,
            health_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0)))
    return {"player_sheet": sheet.model_dump(mode="json")}


def _scope():
    return dict(purpose=PROBE_KIND, probe_kind=PROBE_KIND, experiment_version=EXPERIMENT_VERSION,
        protocol=PROTOCOL, selected_candidate_id=CANDIDATE_ID, synthetic_only=True, campaign_data_eligible=False,
        cap_001_approved=False, runtime_default_eligible=False, semantic_not_evaluated=True, max_calls=MAX_CALLS)


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    prompt: str
    corpus: dict
    metadata: dict


def prepare_experiment():
    for path, digest in INPUT_HASHES.items():
        _require(shared._sha256(path) == digest, "source_dialogue_continuity_input_changed")
    corpus = _read_json(CORPUS_PATH)
    _require(corpus["version"] == EXPERIMENT_VERSION and corpus["candidate_id"] == CANDIDATE_ID
        and corpus["source_origin"] == "runtime_committed_generated_narrative" and corpus["contexts_independent"] is False
        and corpus["npc_aliases"] == ["Mara"] and corpus["parameters"] == PARAMETERS
        and corpus["scene"] == {"location": "Galeria", "npcs_present": ["Mara"]}
        and [(r["turn_slot"], r["player_input"]) for r in corpus["turns"]] == list(zip(TURN_KEYS, PLAYER_INPUTS)))
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    _require(candidate.adapter_kind == "groq" and candidate.model == GROQ_QWEN_MODEL_ID
        and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
        and candidate.reasoning_effort == "none" and candidate.structured_mode == "native" and candidate.campaign_data_eligible is False)
    document = PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    _require(front is not None)
    prompt = document[front.end():].strip()
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=GROQ_QWEN_MODEL_ID)
    schema = profile.NarrativeSourceProposal.model_json_schema()
    inputs = {name: {"file": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": shared._sha256(path)}
        for name, path in (("corpus", CORPUS_PATH), ("protocol", PROTOCOL_PATH), ("manifest", MANIFEST_PATH))}
    inputs.update(prompt={"file": PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(), "file_sha256": PROMPT_FILE_SHA256,
        "sha256": hashlib.sha256(prompt.encode()).hexdigest(), "version": "narrative-source-dialogue-v1"},
        response_schema_sha256=_sha(schema), provider_schema_sha256=_sha(retained._normalize_groq_strict_schema(schema)),
        implementation=[{"file": f, "sha256": shared._sha256(PROJECT_ROOT / f)} for f in dict.fromkeys(IMPLEMENTATION_FILES)])
    metadata = {**_scope(), "target": target.model_dump(mode="json"), "generation_parameters": copy.deepcopy(PARAMETERS),
        "turns": copy.deepcopy(corpus["turns"]), "inputs": inputs,
        "evaluator": {**shared._evaluator_provenance(), "file": "scripts/evaluate_source_dialogue_continuity.py",
            "sha256": shared._sha256(Path(__file__)), "version": EXPERIMENT_VERSION},
        "initial_state": _state(), "relationships": {},
        "source_policy": {"source_field": "n", "source_origin": corpus["source_origin"], "contexts_independent": False,
            "briefing_is_source": False, "question_is_source": False, "canonical_truth_confirmed": False,
            "npc_aliases": ["Mara"], "normalization": profile.TEXT_NORMALIZATION,
            "user_character_limit": profile.MAX_CONTEXT_CHARACTERS, "producer": "source-local-ordinary-v1",
            "replay": "fresh_store_no_production_or_gateway", "second_user": "previous_committed_complete_source"},
        "first_request_template": {"is_live_request": False, "requires_retained_capsule": True, "body_sha256": None,
            "setup": copy.deepcopy(SETUP), "player_input": PLAYER_INPUTS[0],
            "provider_static": {"model": target.model, "system_prompt": prompt, "generation_parameters": copy.deepcopy(PARAMETERS),
                "response_schema": retained._normalize_groq_strict_schema(schema)}},
        "semantic_review": {"status": "not_performed", "approval": None},
        "timing_policy": {"clock": "local_utc", "tolerance_seconds": .01, "remote_arrival_measured": False}}
    return PreparedExperiment(candidate, target, prompt, corpus, metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment)
    current = prepare_experiment()
    _require(current.target == prepared.target and current.prompt == prepared.prompt
        and _same(asdict(current.candidate), asdict(prepared.candidate)) and _same(current.metadata, prepared.metadata)
        and _same(current.corpus, prepared.corpus),
        "source_dialogue_continuity_probe_prepared_drift")


def _config(prepared):
    return create_source_producer_config(target=prepared.target, system_prompt=prepared.prompt,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Mara",))


class DispatchBudget:
    def __init__(self, *, _clock=None, _sleeper=None):
        options = {}
        if _clock is not None: options["_clock"] = _clock
        if _sleeper is not None: options["_sleeper"] = _sleeper
        self.pacer = shared._CallPacer(60, **options)
        self.calls, self.operations = 0, set()
        self.last_dispatch = self.pacer._last_call_started_at = self.pacer._clock()

    async def wait(self):
        await self.pacer.before_call(PROBE_KIND)

    def consume(self, operation):
        now = self.pacer._clock()
        _require(self.calls < MAX_CALLS and operation not in self.operations, "source_dialogue_continuity_http_limit")
        _require(now - self.last_dispatch >= 60, "source_dialogue_continuity_http_spacing")
        self.calls += 1
        self.operations.add(operation)
        self.last_dispatch = self.pacer._last_call_started_at = now


def _request_record(request):
    return {**retained._request_record(request), "deadline": request.deadline.isoformat()}


class ObservationAdapter(retained.RetainedObservationAdapter):
    def __init__(self, *, prepared, request, operation, **kwargs):
        super().__init__(prepared=prepared, request=request, **kwargs)
        self.prepared, self.deadline, self.operation = prepared, request.deadline, operation
        self.operational_error = None
        self.http_started_at = None

    async def _dispatch(self, request):
        _check_prepared(self.prepared)
        _require(not self.http_sent and request.method == "POST"
            and str(request.url) == retained.GROQ_OFFICIAL_BASE_URL + "/chat/completions"
            and _sha(_loads(request.content)) == self.approved["body_sha256"], "source_dialogue_continuity_http_invalid")
        _require(utc_now() < self.deadline, "source_dialogue_continuity_expired_dispatch")
        self.budget.consume(self.operation)
        self.http_sent = True
        self.http_started_at = utc_now().isoformat()

    async def generate_structured(self, request):
        _require(request.deadline == self.deadline, "source_dialogue_continuity_deadline_changed")
        result = await super().generate_structured(request)
        self.operational_error = _operational_error(self.observation, self.capture.get("evidence"), self.deadline,
            proposal=self.capture.get("response_structure"), error=self.capture.get("llm_error"))
        _require(self.operational_error is None, "source_dialogue_continuity_response_outside_limits")
        return result


def _operational_error(observation, evidence, deadline, *, proposal=None, error=None):
    codes = []
    if proposal is not None:
        status = observation["http_status"]
        empty = retained._unavailable_observation()
        if (status is None or not 200 <= status < 300 or observation["finish_reason"] != "stop"
                or observation["model"] != GROQ_QWEN_MODEL_ID or observation["provider_code"] is not None
                or error is not None or not _same(observation["error_body"], empty["error_body"])
                or not _same(observation["failed_generation"], empty["failed_generation"])):
            codes.append("observer_outcome_mismatch")
    if evidence is None:
        return {"codes": codes} if codes else None
    if proposal is not None and any(evidence["usage"][name] != observation["usage"][name]
            for name in ("input_tokens", "output_tokens", "total_tokens")):
        codes.append("usage_mismatch")
    values = [value for value in (evidence["usage"]["output_tokens"], observation["usage"]["output_tokens"]) if value is not None]
    if values and max(values) > 768: codes.append("output_limit_exceeded")
    if datetime.fromisoformat(evidence["finished_at"]) > deadline: codes.append("deadline_exceeded")
    return {"codes": codes} if codes else None


async def _prepare(store, prepared, batch, index, *, deadline=None, cancellation=None, replay=False):
    if replay:
        deadline = utc_now() - timedelta(seconds=1)
    _require(isinstance(deadline, datetime) and deadline.utcoffset() is not None)
    return await prepare_source_player_action(session_id=batch,
        request=SourcePlayerActionRequest(operation_id=_operation(batch, index), player_input=PLAYER_INPUTS[index]),
        store=store, producer_config=_config(prepared), cancellation=cancellation or CancellationToken(), deadline=deadline)


async def _replay(store, batch, operation):
    before = _database_snapshot(store.db_path)
    result = await execute_retained_source_turn(session_id=batch, operation_id=operation, store=store,
        gateway=NoCallGateway(), deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(),
        on_chunk=retained._forbid_replay_chunk)
    _require(_database_snapshot(store.db_path) == before, "source_dialogue_continuity_replay_mutation")
    return result


async def _replay_input(store, prepared, batch, index, row):
    # Existing P is checked first: replay must not accidentally create a new P.
    before = _database_snapshot(store.db_path)
    attempt = await store.load_attempt_by_operation(batch, source_input_operation_id(batch, row["operation_id"]))
    _require(attempt is not None)
    claim = await _prepare(ProbePersistence(store.db_path), prepared, batch, index, replay=True)
    _require(not claim.newly_claimed)
    if row["input_claim"] is not None:
        prior = copy.deepcopy(row["input_claim"])
        prior["newly_claimed"] = False
        _require(_same(prior, claim.model_dump(mode="json")))
    _require(_database_snapshot(store.db_path) == before, "source_dialogue_continuity_replay_mutation")
    row["input_claim"] = claim.model_dump(mode="json")
    row["input_replay_verified"] = True


def _turn_row(batch, index):
    return {"kind": "source_dialogue_continuity_turn", "turn_slot": TURN_KEYS[index], "operation_id": _operation(batch, index),
        "input_claim": None, "input_replay_verified": False, "capsule": None, "request": None,
        "call_made": False, "schema_valid": False, "route_status": "unavailable",
        "provider_observation": retained._unavailable_observation(), "response_structure": None,
        "evidence": None, "llm_error": None, "credential_echo_blocked": False, "http_started_at": None,
        "result": None, "replay_verified": False, "local_error": None,
        "operation_started_at": None, "deadline": None, "operational_error": None}


def _database_files(path):
    return [p for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")) if p.exists()]


def _database_snapshot(path):
    with retained._ClosingConnection(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        data = {}
        for table in tables:
            _require(re.fullmatch(r"[a-z_]+", table) is not None)
            data[table] = sorted([list(row) for row in connection.execute('SELECT * FROM "' + table + '"')], key=_json)
        return {"counts": {name: len(data[name]) for name in ("attempts", "turns", "events")}, "logical_sha256": _sha(data)}


async def evaluate_probe(prepared, *, api_key, batch_id, run_directory, transport=None, budget=None):
    retained._batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip())
        and api_key.get_secret_value().strip() not in _json(prepared.metadata), "source_dialogue_continuity_credential_invalid")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve())
    directory.mkdir(parents=True, exist_ok=False)
    store = ProbePersistence(directory / DATABASE_NAME)
    await store.initialize()
    setup = await create_source_trial_setup(session_id=batch_id, request=SETUP, store=store, initial_state=_state(), relationships={})
    _require(await ProbePersistence(store.db_path).read_source_setup_manifest(batch_id) == setup)
    budget = budget if budget is not None else DispatchBudget()
    _require(type(budget) is DispatchBudget and budget.calls == 0 and not budget.operations)
    rows, status, committed = [], "completed", []
    started = utc_now().isoformat()
    try:
        for index in range(MAX_CALLS):
            row, adapter = _turn_row(batch_id, index), None
            try:
                _check_prepared(prepared)
                await budget.wait()
                _check_prepared(prepared)
                beginning = utc_now()
                deadline, cancellation = beginning + timedelta(seconds=60), CancellationToken()
                row.update(operation_started_at=beginning.isoformat(), deadline=deadline.isoformat())
                claim = await _prepare(store, prepared, batch_id, index, deadline=deadline, cancellation=cancellation)
                row["input_claim"] = claim.model_dump(mode="json")
                if claim.status == "completed":
                    capsule = await ProbePersistence(store.db_path).load_source_preparation(batch_id, row["operation_id"])
                    _require(capsule is not None)
                    row["capsule"] = capsule.model_dump(mode="json")
                    _require(_same([source.model_dump(mode="json") for source in capsule.snapshot.sources], committed),
                        "source_dialogue_continuity_prior_commit_mismatch")
                    request = _request(capsule, deadline, cancellation)
                    row["request"] = _request_record(request)
                    adapter = ObservationAdapter(prepared=prepared, request=request, api_key=api_key,
                        budget=budget, operation=row["operation_id"], transport=transport)
                    result = await execute_retained_source_turn(session_id=batch_id, operation_id=row["operation_id"],
                        store=store, gateway=adapter, deadline=deadline, cancellation=cancellation, on_chunk=retained._no_chunk)
                    row["result"] = _result_record(result)
                    if result.status == "completed":
                        replay = await _replay(ProbePersistence(store.db_path), batch_id, row["operation_id"])
                        _require(_same(_result_record(replay), row["result"]))
                        row["replay_verified"] = True
                        committed.append(row["result"]["envelope"])
                await _replay_input(ProbePersistence(store.db_path), prepared, batch_id, index, row)
            except asyncio.CancelledError:
                status, row["local_error"] = "cancelled", "source_dialogue_continuity_probe_cancelled"
                producer = await store.load_attempt_by_operation(batch_id, source_input_operation_id(batch_id, row["operation_id"]))
                if producer is not None:
                    await _replay_input(ProbePersistence(store.db_path), prepared, batch_id, index, row)
                    capsule = await store.load_source_preparation(batch_id, row["operation_id"])
                    row["capsule"] = capsule.model_dump(mode="json") if capsule is not None else None
                if await store.load_turn_by_operation(batch_id, row["operation_id"]) is not None:
                    replay = await _replay(ProbePersistence(store.db_path), batch_id, row["operation_id"])
                    row["result"], row["replay_verified"] = _result_record(replay), True
            except Exception:
                status, row["local_error"] = "local_error", "source_dialogue_continuity_probe_local_error"
            finally:
                if adapter is not None:
                    row.update({k: copy.deepcopy(adapter.capture.get(k)) for k in ("response_structure", "evidence", "llm_error", "http_started_at")})
                    row.update(provider_observation=adapter.observation, call_made=adapter.http_sent,
                        credential_echo_blocked=adapter.credential_echo_blocked, schema_valid=adapter.capture.get("response_structure") is not None,
                        http_started_at=adapter.http_started_at)
                    row["operational_error"] = _operational_error(row["provider_observation"], row["evidence"], adapter.deadline,
                        proposal=row["response_structure"], error=row["llm_error"])
                    if row["evidence"] is not None:
                        row["route_status"] = retained._route_status(row["evidence"], prepared.target, row["request"]["invocation_id"])
                    adapter._reject_echo(row)
            rows.append(row)
            if status != "completed" or row["result"] is None or row["result"]["status"] != "completed" or row["operational_error"] is not None:
                break
    finally:
        for index in range(len(rows), MAX_CALLS):
            rows.append({"kind": "source_dialogue_continuity_skip", "turn_slot": TURN_KEYS[index], "operation_id": _operation(batch_id, index),
                "reason": status if status != "completed" else "previous_operational_failure"})
        _require(budget.calls == sum(row.get("call_made", False) for row in rows))
        snapshot = _database_snapshot(store.db_path)
        raw_path = directory / "records.jsonl"
        raw_path.write_text("".join(_json({"metadata": prepared.metadata, "batch_id": batch_id, "record": row}) + "\n" for row in rows), encoding="utf-8")
        database_files = _database_files(store.db_path)
        document = {"metadata": prepared.metadata, "batch_id": batch_id, "started_at": started, "finished_at": utc_now().isoformat(),
            "setup_manifest": setup.model_dump(mode="json"), "evaluation_status": status, "summary": summarize(rows, status),
            "database_snapshot": snapshot,
            "artifacts": {"database": {"file": DATABASE_NAME, "sha256": shared._sha256(store.db_path),
                "sidecars": [{"file": p.name, "sha256": shared._sha256(p)} for p in database_files if p != store.db_path]},
                "records": {"file": "records.jsonl", "sha256": shared._sha256(raw_path)}}}
        document["process_exit_code"] = document["summary"]["process_exit_code"]
        (directory / "summary.json").write_text(_json(document) + "\n", encoding="utf-8")
    return rows


def summarize(rows, status="completed"):
    _require(type(rows) is list and len(rows) == MAX_CALLS and status in ("completed", "local_error", "cancelled"))
    turns = []
    for index, row in enumerate(rows):
        _require(row["turn_slot"] == TURN_KEYS[index])
        if row["kind"] == "source_dialogue_continuity_skip":
            _require(index == 1 and row["reason"] == (status if status != "completed" else "previous_operational_failure"))
            continue
        _require(row["kind"] == "source_dialogue_continuity_turn")
        if index:
            _require(rows[0]["result"] is not None and rows[0]["result"]["status"] == "completed"
                and rows[0]["replay_verified"] and rows[0]["input_replay_verified"] and rows[0]["operational_error"] is None)
        for key in ("call_made", "schema_valid", "replay_verified", "input_replay_verified", "credential_echo_blocked"):
            _require(type(row[key]) is bool)
        _require(row["schema_valid"] == (row["response_structure"] is not None))
        _require(not row["schema_valid"] or row["call_made"] and row["route_status"] == "verified")
        _require(not row["credential_echo_blocked"] or row["response_structure"] is row["evidence"] is None)
        turns.append(row)
    committed = sum(r["result"] is not None and r["result"]["status"] == "completed" for r in turns)
    if status == "completed":
        _require(all(r["local_error"] is None for r in turns))
        if len(turns) < MAX_CALLS:
            last = turns[-1]
            _require(last["result"] is not None and last["result"]["status"] != "completed" or
                last["result"] is None and last["input_claim"] is not None and last["input_claim"]["status"] != "completed")
    else:
        _require(turns[-1]["local_error"] == "source_dialogue_continuity_probe_" + ("cancelled" if status == "cancelled" else "local_error"))
    success = committed == 2 and all(r["replay_verified"] and r["input_replay_verified"] and r["call_made"]
        and r["schema_valid"] and r["route_status"] == "verified" and r["operational_error"] is None for r in turns)
    availability = any(r["llm_error"] and r["llm_error"].get("category") in
        {"timeout", "rate_limited", "quota_exceeded", "provider_unavailable"} for r in turns)
    code = 130 if status == "cancelled" else 3 if status == "local_error" or any(r["operational_error"] for r in turns) else 0 if success else 2 if availability else 1
    return {**_scope(), "turns_processed": len(turns), "turns_skipped": 2-len(turns), "turns_committed": committed,
        "calls_made": sum(r["call_made"] for r in turns), "capsules_retained": sum(r["capsule"] is not None for r in turns),
        "producer_completions": sum(r["input_claim"] is not None and r["input_claim"]["status"] == "completed" for r in turns),
        "input_replays_verified": sum(r["input_replay_verified"] for r in turns), "replays_verified": sum(r["replay_verified"] for r in turns),
        "schema_valid": sum(r["schema_valid"] for r in turns), "route_verified": sum(r["route_status"] == "verified" for r in turns),
        "operational_probe_passed": success and status == "completed", "process_exit_code": code,
        "semantic_fidelity_review": {"status": "not_performed", "approval": None}}


def _expected(path, digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and shared._sha256(Path(path)) == digest, "source_dialogue_continuity_probe_preflight_hash_invalid")
    prepared = prepare_experiment()
    _require(_same(_read_json(path), prepared.metadata), "source_dialogue_continuity_probe_preflight_changed")
    return prepared


async def _verify_database(database, prepared, batch, rows, summary, manifest):
    store = ProbePersistence(database)
    actual_manifest = await store.read_source_setup_manifest(batch)
    _require(actual_manifest == validate_source_setup_manifest(manifest, session_id=batch)
        == create_source_setup_manifest(SETUP, session_id=batch))
    snapshot = await store.read_source_context_snapshot(batch)
    _require(snapshot.current_turn == summary["turns_committed"] and snapshot.state_revision == snapshot.current_turn)
    _require(snapshot.canonical_scene == actual_manifest.origin.seed_scene)
    campaign = await store.load_campaign(batch)
    _require(_same(campaign["state"], _state()) and campaign["relationships"] == {})
    expected_ops, committed = set(), []
    for index, row in enumerate(rows):
        _require(row["operation_id"] == _operation(batch, index))
        if row["kind"] == "source_dialogue_continuity_skip":
            _require(set(row) == {"kind", "turn_slot", "operation_id", "reason"})
            continue
        _require(set(row) == set(_turn_row(batch, index)))
        retained._validate_observation_snapshot(row)
        p_id = source_input_operation_id(batch, row["operation_id"])
        producer = await store.load_attempt_by_operation(batch, p_id)
        capsule = await store.load_source_preparation(batch, row["operation_id"])
        if row["input_claim"] is None:
            _require(producer is capsule is row["capsule"] is row["request"] is row["result"] is None
                and not row["call_made"] and not row["input_replay_verified"] and row["local_error"] is not None)
            continue
        expected_ops.add(p_id)
        claim = SourceInputClaim.model_validate(row["input_claim"])
        _require(producer is not None and not claim.newly_claimed and claim.request.operation_id == row["operation_id"])
        _require(claim.request.player_input == PLAYER_INPUTS[index] and claim.request.session_id == batch
            and claim.request.state == _state() and claim.request.relationships == {} and claim.request.config == _config(prepared))
        _require(claim.request.snapshot.current_turn == claim.request.snapshot.state_revision == index)
        _require(_same([s.model_dump(mode="json") for s in claim.request.snapshot.sources], committed))
        _require(producer["request_hash"] == source_input_request_hash(claim.request)
            and producer["result_hash"] == source_input_result_hash(claim.request, claim.completion))
        checked = await _prepare(store, prepared, batch, index, replay=True)
        _require(checked == claim and row["input_replay_verified"])
        if claim.status != "completed":
            _require(capsule is row["capsule"] is row["request"] is row["result"] is None and not row["call_made"])
            continue
        expected_ops.add(source_preparation_operation_id(batch, row["operation_id"]))
        _require(capsule is not None and _same(capsule.model_dump(mode="json"), row["capsule"]))
        capsule = validate_source_turn_capsule(capsule, session_id=batch, operation_id=row["operation_id"])
        # Both authored player fixtures are declarations. Do not certify an
        # internally consistent but unrelated rolled receipt, or rerun the RNG.
        _require(type(capsule.preparation) is DeclaredActionPreparation)
        _require(claim.completion == create_source_input_completion(claim.request, status="completed", capsule=capsule))
        request = _request(capsule, datetime.fromisoformat(row["deadline"]))
        _require(row["request"] is None or _same(row["request"], _request_record(request)))
        _require(not row["call_made"] or row["request"] is not None)
        _verify_evidence(row, request)
        _require(_same(row["operational_error"], _operational_error(row["provider_observation"], row["evidence"], request.deadline,
            proposal=row["response_structure"], error=row["llm_error"])))
        if row["evidence"] is not None:
            _require(row["route_status"] == retained._route_status(row["evidence"], prepared.target, request.invocation_id))
        else:
            _require(row["route_status"] == "unavailable")
        if row["call_made"] and not row["credential_echo_blocked"]:
            _require(type(row["http_started_at"]) is str and datetime.fromisoformat(row["http_started_at"]).tzinfo is not None)
        attempt = await store.load_attempt_by_operation(batch, row["operation_id"])
        if attempt is not None:
            expected_ops.add(row["operation_id"])
            _require(attempt["attempt_id"] == capsule.draft.attempt_id and attempt["partial_narrative"] == "")
            if row["operational_error"] is not None and row["llm_error"] is None:
                _require(attempt["provenance"] is attempt["usage"] is None and result_or_failed(attempt))
            else:
                _verify_application_audit(row, attempt, request)
        else:
            _require(row["evidence"] is row["llm_error"] is None)
        await store.read_source_operation_status(batch, row["operation_id"])
        result = row["result"]
        if result is None:
            _require(row["local_error"] is not None and (attempt is None or attempt["status"] in ("failed", "cancelled", "timeout")))
            continue
        _require(set(result) == {"status", "operation_id", "turn_id", "turn_number", "error", "narrative", "envelope"})
        _require(attempt is not None and result["status"] == attempt["status"]
            and result["operation_id"] == capsule.operation_id and result["turn_id"] == capsule.draft.turn_id
            and result["turn_number"] == index+1)
        projection, policy_error = None, None
        if row["response_structure"] is not None:
            proposal = profile.NarrativeSourceProposal.model_validate(row["response_structure"])
            _require(_same(proposal.model_dump(mode="json", by_alias=True), row["response_structure"]))
            try:
                projection = profile.create_source_projection(proposal, source_id="source-"+request.invocation_id,
                    session_id=batch, turn_id=capsule.draft.turn_id, invocation_id=request.invocation_id,
                    current_scene=capsule.canonical_scene, facts=capsule.draft.facts, player_input=capsule.player_input,
                    player_aliases=capsule.player_aliases, npc_aliases=capsule.npc_aliases)
            except (ValueError, TypeError) as exc:
                policy_error = getattr(exc, "code", None)
                _require(type(policy_error) is str)
        if result["status"] == "completed":
            _require(projection is not None and row["schema_valid"] and row["route_status"] == "verified" and row["replay_verified"])
            _require(_same(result["envelope"]["projection"], projection.model_dump(mode="json")))
            replay = await _replay(store, batch, row["operation_id"])
            _require(_same(_result_record(replay), result))
            stored = await store.load_turn_by_operation(batch, row["operation_id"])
            _require(stored is not None)
            envelope = stored["context"]["narrative_source"]
            _require(_same(envelope, result["envelope"]))
            committed.append(envelope)
        else:
            _require(result["narrative"] is result["envelope"] is None and not row["replay_verified"]
                and _same(result["error"], attempt["error"]))
            _require(set(result["error"]) == {"code", "stage"}
                and result["error"]["stage"] in ("preflight", "generation", "policy", "admission", "delivery", "commit")
                and safe_source_failure(result["error"]) is not None)
            if policy_error is not None:
                _require(result["error"]["code"] == policy_error)
            elif projection is not None:
                _require(result["error"]["code"] in ("source_turn_policy_failed", "source_turn_admission_failed",
                    "source_turn_commit_failed", "source_turn_delivery_failed", "source_turn_generation_failed"))
    attempts = await store.list_attempts(batch)
    _require({a["operation_id"] for a in attempts} == expected_ops and all(a["status"] != "pending" for a in attempts))


def _verify_application_audit(row, attempt, request):
    """Check actual audit statuses, including timed_out, without editing captures."""
    if row["evidence"] is None:
        _require(attempt["provenance"] is attempt["usage"] is None and row["llm_error"] is None)
        return
    raw = row["evidence"]
    provenance = {name: raw[name] for name in ("invocation_id", "requested_target", "adapter",
        "effective_model", "effective_provider", "started_at", "finished_at")}
    evidence = retained.InvocationEvidence.model_validate({"provenance": provenance, "usage": raw["usage"], "cost": raw["cost"]})
    _require(_same(shared._evidence_payload(evidence), raw))
    category = (row["llm_error"] or {}).get("category")
    status = "completed" if category is None else {"timeout": "timed_out", "cancelled": "cancelled"}.get(category, "failed")
    identity = {"invocation_id": request.invocation_id, "operation": request.operation, "status": status}
    expected_provenance = {"invocations": [{**identity, "provenance": evidence.provenance.model_dump(mode="json"),
        "error": None if category is None else {"category": category, "code": "source_turn_provider_failure"}}]}
    expected_usage = {"invocations": [{**identity, "tokens": evidence.usage.model_dump(mode="json"), "cost": evidence.cost.model_dump(mode="json")}]}
    _require(_same(attempt["provenance"], expected_provenance) and _same(attempt["usage"], expected_usage))


def result_or_failed(attempt):
    return attempt["status"] in ("failed", "timeout", "cancelled")


def _verify_times(doc, rows):
    start, end = (datetime.fromisoformat(doc[name]) for name in ("started_at", "finished_at"))
    _require(start.utcoffset() is not None and end.utcoffset() is not None and start <= end)
    last_http, last_finished, tolerance = None, None, timedelta(seconds=.01)
    for row in rows:
        if row["kind"] == "source_dialogue_continuity_skip": continue
        if row["operation_started_at"] is None:
            _require(row["deadline"] is row["input_claim"] is row["request"] is None and row["local_error"] is not None)
            continue
        beginning, deadline = (datetime.fromisoformat(row[name]) for name in ("operation_started_at", "deadline"))
        _require(beginning.utcoffset() is not None and deadline == beginning + timedelta(seconds=60)
            and start <= beginning <= end and beginning + tolerance >= start + timedelta(seconds=60))
        if last_http is not None: _require(beginning + tolerance >= last_http + timedelta(seconds=60))
        if last_finished is not None: _require(beginning >= last_finished)
        if row["request"] is not None: _require(row["request"]["deadline"] == row["deadline"])
        _require(row["call_made"] == (row["http_started_at"] is not None))
        if row["http_started_at"] is not None:
            http = datetime.fromisoformat(row["http_started_at"])
            _require(beginning <= http <= deadline and http <= end)
            last_http = http
        if row["evidence"] is not None:
            began, finished = (datetime.fromisoformat(row["evidence"][name]) for name in ("started_at", "finished_at"))
            _require(beginning <= began <= finished <= end)
            if row["http_started_at"] is not None: _require(began <= http <= finished)
            _require(finished <= deadline or "deadline_exceeded" in (row["operational_error"] or {}).get("codes", []))
            last_finished = finished


def verify_artifacts(summary_path, expected_preflight, batch_id, *, expected_preflight_sha256):
    prepared = _expected(expected_preflight, expected_preflight_sha256)
    path = Path(summary_path)
    _require(path.resolve() == (run_path(batch_id) / "summary.json").resolve() and not path.is_symlink())
    doc = _read_json(path)
    _require(set(doc) == {"metadata", "batch_id", "started_at", "finished_at", "setup_manifest", "evaluation_status", "summary", "artifacts", "process_exit_code", "database_snapshot"})
    _require(_same(doc["metadata"], prepared.metadata) and doc["batch_id"] == batch_id and set(doc["artifacts"]) == {"database", "records"})
    database = path.parent / DATABASE_NAME
    entry = doc["artifacts"]["database"]
    _require(set(entry) == {"file", "sha256", "sidecars"} and entry["file"] == DATABASE_NAME and type(entry["sidecars"]) is list)
    entries = [{"file": entry["file"], "sha256": entry["sha256"]}, *entry["sidecars"], doc["artifacts"]["records"]]
    names = [item["file"] for item in entries]
    _require(names[-1] == "records.jsonl" and len(names) == len(set(names))
        and all(name in {DATABASE_NAME, DATABASE_NAME + "-wal", DATABASE_NAME + "-shm", "records.jsonl"} for name in names)
        and [p.name for p in _database_files(database)] == names[:-1])
    for item in entries:
        p = path.parent / item["file"]
        _require(set(item) == {"file", "sha256"} and not p.is_symlink() and p.resolve().parent == path.parent.resolve()
            and p.stat().st_size <= (retained.MAX_JSON_BYTES if p.name == "records.jsonl" else retained.MAX_DB_BYTES)
            and shared._sha256(p) == item["sha256"])
    originals = {p: shared._sha256(p) for p in [path, *(path.parent / name for name in names)]}
    lines = (path.parent / "records.jsonl").read_text(encoding="utf-8").splitlines()
    _require(len(lines) == MAX_CALLS)
    rows = []
    for line in lines:
        item = _loads(line.encode("utf-8"))
        _require(set(item) == {"metadata", "batch_id", "record"} and _same(item["metadata"], prepared.metadata) and item["batch_id"] == batch_id)
        rows.append(item["record"])
    recomputed = summarize(rows, doc["evaluation_status"])
    _require(_same(recomputed, doc["summary"]) and type(doc["process_exit_code"]) is int and doc["process_exit_code"] == recomputed["process_exit_code"])
    _verify_times(doc, rows)
    with tempfile.TemporaryDirectory(prefix="storyteller-dialogue-continuity-verify-") as temporary:
        copy_db = Path(temporary) / DATABASE_NAME
        for name in names[:-1]: (Path(temporary) / name).write_bytes((path.parent / name).read_bytes())
        with retained._ClosingConnection(sqlite3.connect(copy_db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _require(conn.execute("PRAGMA integrity_check").fetchone() == ("ok",) and conn.execute("PRAGMA foreign_key_check").fetchall() == [])
            _require(conn.execute("SELECT session_id FROM campaigns").fetchall() == [(batch_id,)])
            for table in ("attempts", "turns", "events"):
                _require(conn.execute("SELECT count(*) FROM " + table + " WHERE session_id!=?", (batch_id,)).fetchone() == (0,))
            for table in ("memory_candidates", "episodic_memories", "consolidations", "legacy_imports"):
                _require(conn.execute("SELECT count(*) FROM " + table).fetchone() == (0,))
        _require(_same(_database_snapshot(copy_db), doc["database_snapshot"]))
        asyncio.run(_verify_database(copy_db, prepared, batch_id, rows, recomputed, doc["setup_manifest"]))
        _require(_same(_database_snapshot(copy_db), doc["database_snapshot"]))
    _require(all(shared._sha256(p) == digest for p, digest in originals.items())
        and [p.name for p in _database_files(database)] == names[:-1])
    return {"verified": True, "batch_id": batch_id, "process_exit_code": recomputed["process_exit_code"], "summary_path": str(path.resolve())}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("source_dialogue_continuity_arguments_invalid")


def main(argv=None):
    parser = _Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--verify-artifacts", type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env", choices=(KEY_ENV,))
    parser.add_argument("--allow-synthetic-only", action="store_true")
    key = None
    try:
        args = parser.parse_args(argv)
        if args.preflight:
            _require(args.batch_id is None and args.expected_preflight is None
                and args.expected_preflight_sha256 is None and args.api_key_env is None and not args.allow_synthetic_only)
            print(_json(prepare_experiment().metadata))
            return 0
        _batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts:
            _require(args.api_key_env is None and not args.allow_synthetic_only)
            print(_json(verify_artifacts(args.verify_artifacts, args.expected_preflight, args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256)))
            return 0
        _require(args.allow_synthetic_only and args.api_key_env == KEY_ENV)
        # Provenance launches Git children; remove their access before it runs.
        key = SecretStr(os.environ.pop(KEY_ENV, "").strip())
        if not key.get_secret_value():
            print("source_dialogue_continuity_credential_missing", file=sys.stderr)
            key = None
            return 3
        prepared = _expected(args.expected_preflight, args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists(), "source_dialogue_continuity_run_exists")
    except Exception:
        key = None
        print("source_dialogue_continuity_preflight_or_verification_failed", file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_probe(prepared, api_key=key, batch_id=args.batch_id, run_directory=run_path(args.batch_id)))
        code = _read_json(run_path(args.batch_id) / "summary.json")["process_exit_code"]
        print(_json({"summary_path": str((run_path(args.batch_id) / "summary.json").resolve()), "process_exit_code": code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("source_dialogue_continuity_local_failure", file=sys.stderr)
        return 3
    finally:
        key = None


if __name__ == "__main__":
    raise SystemExit(main())
