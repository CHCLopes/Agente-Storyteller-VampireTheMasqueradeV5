"""Bounded synthetic player dialogue/wait through authored setup, P/K and H6.

Only the existing player-action service produces receipts, after acquiring P.
Preflight records static provider inputs, never a fabricated receipt/live body.
The retained probe's bounded observer, HTTP hook, key-echo filter and audit helpers
are reused directly; none of that module's globals or old experiments is changed.
Artifact checks establish local consistency, not provider authenticity or quality.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
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

shared = retained.shared
profile = retained.profile
_json, _sha, _same = retained._json, retained._sha, retained._same
_request, _request_record = retained._request, retained._request_record
_read_json, _loads = retained._read_json, retained._loads
_result_record = retained._result_record
ProbePersistence, NoCallGateway = retained.ProbePersistence, retained.NoCallGateway
ObservationAdapter = retained.RetainedObservationAdapter
GROQ_QWEN_MODEL_ID = retained.GROQ_QWEN_MODEL_ID
PROBE_KIND = "source_player_probe"
EXPERIMENT_VERSION = "source-player-observation-v1"
PROTOCOL = profile.VERSION
CANDIDATE_ID = retained.CANDIDATE_ID
KEY_ENV = "STORYTELLER_SOURCE_PLAYER_GROQ_KEY"
TARGET_PROFILE = "source-player-" + CANDIDATE_ID
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
DATABASE_NAME = "source-player.sqlite3"
MANIFEST_PATH, MANIFEST_SHA256 = retained.MANIFEST_PATH, retained.MANIFEST_SHA256
PROMPT_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-progress-v1.md"
PROMPT_FILE_SHA256 = "87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e"
PROMPT_SHA256 = "17b64cf63d7f851b4190a24dd39f65215393251ada18487873710c92e99d2a6d"
MAX_CALLS = 2
PARAMETERS = copy.deepcopy(retained.PARAMETERS)
CASE_ID = "gallery-player-dialogue-wait"
TURN_KEYS = ("dialogue", "wait")
PLAYER_INPUTS = (
    'Pergunto a Mara: "Quero conhecer melhor este lugar por meio da conversa. O que você pode me contar?"',
    "Espero a reação de Mara.",
)
SETUP = {"protocol": "narrative-source-setup-request-v1", "location": "Galeria", "npcs_present": ["Mara"],
         "declared_objective": "Conhecer melhor este lugar por meio da conversa."}
IMPLEMENTATION_FILES = retained.IMPLEMENTATION_FILES + (
    "scripts/evaluate_source_player.py", "api/narrative_source_setup.py", "api/narrative_source_setup_service.py",
    "api/narrative_source_entry.py", "api/narrative_source_input.py", "api/narrative_source_input_service.py",
    "api/narrative_source_action_producer.py", "api/narrative_source_status.py", "api/rules_service.py",
)


def _require(condition, code="source_player_probe_artifact_invalid"):
    if not condition:
        raise ValueError(code)


def run_path(batch_id):
    return OUTPUT_ROOT / ("source-player-" + retained._batch(batch_id))


def _operation(batch, index):
    return str(uuid5(UUID(batch), "source-player." + TURN_KEYS[index]))


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
    metadata: dict


def prepare_experiment():
    for path, digest in ((MANIFEST_PATH, MANIFEST_SHA256), (PROMPT_PATH, PROMPT_FILE_SHA256)):
        _require(shared._sha256(path) == digest, "source_player_probe_input_changed")
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    _require(candidate.adapter_kind == "groq" and candidate.model == GROQ_QWEN_MODEL_ID
        and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
        and candidate.reasoning_effort == "none" and candidate.structured_mode == "native"
        and candidate.campaign_data_eligible is False)
    document = PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    _require(front is not None)
    prompt = document[front.end():].strip()
    _require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA256)
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=GROQ_QWEN_MODEL_ID)
    setup = create_source_setup_manifest(SETUP, session_id="00000000-0000-0000-0000-000000000000")
    case = {"case_id": CASE_ID, "origin": "agent_authored_synthetic_player_fixture", "synthetic_only": True,
        "setup": setup.request.model_dump(mode="json"), "initial_state": _state(), "relationships": {},
        "producer_context": {"npc_aliases": ["Mara"], "player_aliases": [], "chronicle_name": ""},
        "turns": [{"turn_key": k, "player_input": p} for k, p in zip(TURN_KEYS, PLAYER_INPUTS)]}
    for index, text in enumerate(PLAYER_INPUTS):
        SourcePlayerActionRequest(operation_id=str(index), player_input=text)
    schema = profile.NarrativeSourceProposal.model_json_schema()
    static = {"model": target.model, "system_prompt": prompt,
              "generation_parameters": copy.deepcopy(PARAMETERS),
              "response_schema": retained._normalize_groq_strict_schema(schema)}
    metadata = {**_scope(), "generation_parameters": copy.deepcopy(PARAMETERS),
        "evaluator": {**shared._evaluator_provenance(), "file": "scripts/evaluate_source_player.py",
            "sha256": shared._sha256(Path(__file__)), "version": EXPERIMENT_VERSION},
        "inputs": {"manifest": {"file": MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256": MANIFEST_SHA256},
            "prompt": {"file": PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(), "file_sha256": PROMPT_FILE_SHA256, "sha256": PROMPT_SHA256},
            "case": {"case_id": CASE_ID, "sha256": _sha(case), "data": case},
            "response_schema_sha256": _sha(schema), "provider_schema_sha256": _sha(static["response_schema"]),
            "implementation": [{"file": f, "sha256": shared._sha256(PROJECT_ROOT/f)} for f in IMPLEMENTATION_FILES]},
        "source_policy": {"source_field": "n", "briefing_is_source": False, "question_is_source": False,
            "canonical_truth_confirmed": False, "normalization": profile.TEXT_NORMALIZATION,
            "user_character_limit": profile.MAX_CONTEXT_CHARACTERS, "producer": "source-local-ordinary-v1",
            "replay": "fresh_store_no_production_or_gateway", "second_user": "previous_committed_complete_source"},
        "first_request_template": {"is_live_request": False, "requires_retained_capsule": True,
            "body_sha256": None, "setup": copy.deepcopy(SETUP), "player_input": PLAYER_INPUTS[0],
            "provider_static": static}}
    return PreparedExperiment(candidate, target, prompt, metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment)
    current = prepare_experiment()
    _require(current.target == prepared.target and current.prompt == prepared.prompt
        and _same(asdict(current.candidate), asdict(prepared.candidate)) and _same(current.metadata, prepared.metadata),
        "source_player_probe_prepared_drift")


def _config(prepared):
    return create_source_producer_config(target=prepared.target, system_prompt=prepared.prompt,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Mara",))


class DispatchBudget(retained.DispatchBudget):
    async def wait(self):
        await self.pacer.before_call(PROBE_KIND)


async def _prepare(store, prepared, batch, index, *, replay=False):
    return await prepare_source_player_action(session_id=batch,
        request=SourcePlayerActionRequest(operation_id=_operation(batch, index), player_input=PLAYER_INPUTS[index]),
        store=store, producer_config=_config(prepared), cancellation=CancellationToken(),
        deadline=utc_now()+timedelta(seconds=-1 if replay else 60))


async def _replay(store, batch, operation):
    return await execute_retained_source_turn(session_id=batch, operation_id=operation, store=store,
        gateway=NoCallGateway(), deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(),
        on_chunk=retained._forbid_replay_chunk)


async def _replay_input(store, prepared, batch, index, row):
    # Existing P is checked first: replay must not accidentally create a new P.
    attempt = await store.load_attempt_by_operation(batch, source_input_operation_id(batch, row["operation_id"]))
    _require(attempt is not None)
    claim = await _prepare(ProbePersistence(store.db_path), prepared, batch, index, replay=True)
    _require(not claim.newly_claimed)
    if row["input_claim"] is not None:
        _require(_same(row["input_claim"], claim.model_dump(mode="json")))
    row["input_claim"] = claim.model_dump(mode="json")
    row["input_replay_verified"] = True


def _turn_row(batch, index):
    return {"kind": "source_player_turn", "turn_key": TURN_KEYS[index], "operation_id": _operation(batch, index),
        "input_claim": None, "input_replay_verified": False, "capsule": None, "request": None,
        "call_made": False, "schema_valid": False, "route_status": "unavailable",
        "provider_observation": retained._unavailable_observation(), "response_structure": None,
        "evidence": None, "llm_error": None, "credential_echo_blocked": False, "http_started_at": None,
        "result": None, "replay_verified": False, "local_error": None}


async def evaluate_probe(prepared, *, api_key, batch_id, run_directory):
    retained._batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip()), "source_player_probe_credential_invalid")
    _require(api_key.get_secret_value().strip() not in _json(prepared.metadata), "source_player_probe_credential_conflict")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve())
    directory.mkdir(parents=True, exist_ok=False)
    store = ProbePersistence(directory/"working.sqlite3")
    await store.initialize()
    setup = await create_source_trial_setup(session_id=batch_id, request=SETUP, store=store,
        initial_state=_state(), relationships={})
    _require(await ProbePersistence(store.db_path).read_source_setup_manifest(batch_id) == setup)
    budget, rows, status = DispatchBudget(), [], "completed"
    started = utc_now().isoformat()
    try:
        for index in range(MAX_CALLS):
            row, adapter = _turn_row(batch_id, index), None
            try:
                _check_prepared(prepared)
                claim = await _prepare(store, prepared, batch_id, index)
                row["input_claim"] = claim.model_dump(mode="json")
                await _replay_input(store, prepared, batch_id, index, row)
                if claim.status == "completed":
                    capsule = await store.load_source_preparation(batch_id, row["operation_id"])
                    _require(capsule is not None)
                    row["capsule"] = capsule.model_dump(mode="json")
                    await budget.wait()
                    _check_prepared(prepared)
                    deadline = utc_now()+timedelta(seconds=60)
                    request = _request(capsule, deadline)
                    row["request"] = _request_record(request)
                    adapter = ObservationAdapter(prepared=prepared, request=request, api_key=api_key, budget=budget)
                    result = await execute_retained_source_turn(session_id=batch_id, operation_id=row["operation_id"],
                        store=store, gateway=adapter, deadline=deadline, cancellation=CancellationToken(),
                        on_chunk=retained._no_chunk)
                    row["result"] = _result_record(result)
                    if result.status == "completed":
                        replay = await _replay(ProbePersistence(store.db_path), batch_id, row["operation_id"])
                        _require(_same(_result_record(replay), row["result"]))
                        await _replay_input(store, prepared, batch_id, index, row)
                        row["replay_verified"] = True
            except asyncio.CancelledError:
                status, row["local_error"] = "cancelled", "source_player_probe_cancelled"
                # The service settles its worker before propagating cancellation:
                # P (and possibly K) may exist even if the call never returned.
                # Observe that existing P only; never manufacture a replacement.
                producer = await store.load_attempt_by_operation(batch_id,
                    source_input_operation_id(batch_id, row["operation_id"]))
                if producer is not None:
                    await _replay_input(store, prepared, batch_id, index, row)
                    capsule = await store.load_source_preparation(batch_id, row["operation_id"])
                    row["capsule"] = capsule.model_dump(mode="json") if capsule is not None else None
                committed = await store.load_turn_by_operation(batch_id, row["operation_id"])
                if committed is not None:
                    replay = await _replay(ProbePersistence(store.db_path), batch_id, row["operation_id"])
                    row["result"], row["replay_verified"] = _result_record(replay), True
            except Exception:
                status, row["local_error"] = "local_error", "source_player_probe_local_error"
            finally:
                if adapter is not None:
                    row.update({k: copy.deepcopy(adapter.capture.get(k))
                        for k in ("response_structure", "evidence", "llm_error", "http_started_at")})
                    row.update(provider_observation=adapter.observation, call_made=adapter.http_sent,
                        credential_echo_blocked=adapter.credential_echo_blocked,
                        schema_valid=adapter.capture.get("response_structure") is not None)
                    if row["evidence"] is not None:
                        row["route_status"] = retained._route_status(row["evidence"], prepared.target, row["request"]["invocation_id"])
                    adapter._reject_echo(row)
            rows.append(row)
            if status != "completed" or row["result"] is None or row["result"]["status"] != "completed":
                break
    finally:
        for index in range(len(rows), MAX_CALLS):
            rows.append({"kind": "source_player_skip", "turn_key": TURN_KEYS[index], "operation_id": _operation(batch_id, index),
                "reason": status if status != "completed" else "previous_operational_failure"})
        retained._seal_database(store.db_path, directory/DATABASE_NAME)
        raw = "".join(_json({"metadata": prepared.metadata, "batch_id": batch_id, "record": row})+"\n" for row in rows)
        (directory/(CANDIDATE_ID+".jsonl")).write_text(raw, encoding="utf-8")
        document = {"metadata": prepared.metadata, "batch_id": batch_id, "started_at": started, "finished_at": utc_now().isoformat(),
            "setup_manifest": setup.model_dump(mode="json"), "evaluation_status": status, "summary": summarize(rows, status),
            "artifacts": {"database": {"file": DATABASE_NAME, "sha256": shared._sha256(directory/DATABASE_NAME)},
                "records": {"file": CANDIDATE_ID+".jsonl", "sha256": shared._sha256(directory/(CANDIDATE_ID+".jsonl"))}}}
        document["process_exit_code"] = document["summary"]["process_exit_code"]
        (directory/"summary.json").write_text(_json(document)+"\n", encoding="utf-8")
    return rows


def summarize(rows, status="completed"):
    _require(type(rows) is list and len(rows) == MAX_CALLS and status in ("completed", "local_error", "cancelled"))
    turns = []
    for index, row in enumerate(rows):
        _require(row["turn_key"] == TURN_KEYS[index])
        if row["kind"] == "source_player_skip":
            _require(index == 1 and row["reason"] == (status if status != "completed" else "previous_operational_failure"))
            continue
        _require(row["kind"] == "source_player_turn")
        if index:
            _require(rows[0]["result"] is not None and rows[0]["result"]["status"] == "completed"
                and rows[0]["replay_verified"] and rows[0]["input_replay_verified"])
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
        _require(turns[-1]["local_error"] == "source_player_probe_" + ("cancelled" if status == "cancelled" else "local_error"))
    success = committed == 2 and all(r["replay_verified"] and r["input_replay_verified"] and r["call_made"]
        and r["schema_valid"] and r["route_status"] == "verified" for r in turns)
    availability = any(r["llm_error"] and r["llm_error"].get("category") in
        {"timeout", "rate_limited", "quota_exceeded", "provider_unavailable"} for r in turns)
    code = 130 if status == "cancelled" else 3 if status == "local_error" else 0 if success else 2 if availability else 1
    return {**_scope(), "turns_processed": len(turns), "turns_skipped": 2-len(turns), "turns_committed": committed,
        "calls_made": sum(r["call_made"] for r in turns), "capsules_retained": sum(r["capsule"] is not None for r in turns),
        "producer_completions": sum(r["input_claim"] is not None and r["input_claim"]["status"] == "completed" for r in turns),
        "input_replays_verified": sum(r["input_replay_verified"] for r in turns), "replays_verified": sum(r["replay_verified"] for r in turns),
        "schema_valid": sum(r["schema_valid"] for r in turns), "route_verified": sum(r["route_status"] == "verified" for r in turns),
        "operational_probe_passed": success and status == "completed", "process_exit_code": code,
        "semantic_fidelity_review": {"status": "not_performed", "approval": None}}


def _expected(path, digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and shared._sha256(Path(path)) == digest, "source_player_probe_preflight_hash_invalid")
    prepared = prepare_experiment()
    _require(_same(_read_json(path), prepared.metadata), "source_player_probe_preflight_changed")
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
        if row["kind"] == "source_player_skip":
            _require(set(row) == {"kind", "turn_key", "operation_id", "reason"})
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
        request = _request(capsule)
        _require(row["request"] is None or _same(row["request"], _request_record(request)))
        _require(not row["call_made"] or row["request"] is not None)
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
            retained._verify_audit(row, attempt, request)
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
            committed.append(result["envelope"])
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
                    "source_turn_commit_failed", "source_turn_delivery_failed"))
    attempts = await store.list_attempts(batch)
    _require({a["operation_id"] for a in attempts} == expected_ops and all(a["status"] != "pending" for a in attempts))


def verify_artifacts(summary_path, expected_preflight, batch_id, *, expected_preflight_sha256):
    prepared = _expected(expected_preflight, expected_preflight_sha256)
    path = Path(summary_path)
    _require(path.resolve() == (run_path(batch_id)/"summary.json").resolve() and not path.is_symlink())
    doc = _read_json(path)
    _require(set(doc) == {"metadata", "batch_id", "started_at", "finished_at", "setup_manifest", "evaluation_status", "summary", "artifacts", "process_exit_code"})
    _require(_same(doc["metadata"], prepared.metadata) and doc["batch_id"] == batch_id)
    start, end = (datetime.fromisoformat(doc[k]) for k in ("started_at", "finished_at"))
    _require(start.tzinfo is not None and end.tzinfo is not None and end >= start)
    _require(set(doc["artifacts"]) == {"database", "records"})
    artifacts = {}
    for kind, name, limit in (("database", DATABASE_NAME, retained.MAX_DB_BYTES), ("records", CANDIDATE_ID+".jsonl", retained.MAX_JSON_BYTES)):
        entry, artifact = doc["artifacts"][kind], path.parent/name
        _require(type(entry) is dict and set(entry) == {"file", "sha256"} and entry["file"] == name
            and not artifact.is_symlink() and artifact.resolve().parent == path.parent.resolve() and artifact.stat().st_size <= limit
            and shared._sha256(artifact) == entry["sha256"])
        artifacts[kind] = artifact
    lines = artifacts["records"].read_text(encoding="utf-8").splitlines()
    _require(len(lines) == 2)
    rows = []
    for line in lines:
        item = _loads(line.encode("utf-8"))
        _require(set(item) == {"metadata", "batch_id", "record"} and _same(item["metadata"], prepared.metadata) and item["batch_id"] == batch_id)
        rows.append(item["record"])
    recomputed = summarize(rows, doc["evaluation_status"])
    _require(_same(recomputed, doc["summary"]) and type(doc["process_exit_code"]) is int and doc["process_exit_code"] == recomputed["process_exit_code"])
    originals = {p: shared._sha256(p) for p in (path, *artifacts.values())}
    with tempfile.TemporaryDirectory(prefix="storyteller-source-player-verify-") as temporary:
        database = Path(temporary)/"copy.sqlite3"
        database.write_bytes(artifacts["database"].read_bytes())
        with retained._ClosingConnection(sqlite3.connect(database.resolve().as_uri()+"?mode=ro", uri=True)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _require(conn.execute("PRAGMA integrity_check").fetchone() == ("ok",) and conn.execute("PRAGMA foreign_key_check").fetchall() == [])
            _require(conn.execute("SELECT session_id FROM campaigns").fetchall() == [(batch_id,)])
            for table in ("attempts", "turns", "events"):
                _require(conn.execute("SELECT count(*) FROM "+table+" WHERE session_id!=?", (batch_id,)).fetchone() == (0,))
            for table in ("memory_candidates", "episodic_memories", "consolidations", "legacy_imports"):
                _require(conn.execute("SELECT count(*) FROM "+table).fetchone() == (0,))
        asyncio.run(_verify_database(database, prepared, batch_id, rows, recomputed, doc["setup_manifest"]))
    _require(all(shared._sha256(p) == digest for p, digest in originals.items()))
    return {"verified": True, "batch_id": batch_id, "process_exit_code": recomputed["process_exit_code"], "summary_path": str(path.resolve())}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Two synthetic chosen player actions; no imported campaign or retry.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--verify-artifacts", type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env", choices=(KEY_ENV,), default=KEY_ENV)
    parser.add_argument("--allow-synthetic-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            _require(args.batch_id is None and args.expected_preflight is None and args.expected_preflight_sha256 is None and not args.allow_synthetic_only)
            print(_json(prepare_experiment().metadata))
            return 0
        retained._batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts is not None:
            _require(not args.allow_synthetic_only)
            print(_json(verify_artifacts(args.verify_artifacts, args.expected_preflight, args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256)))
            return 0
        _require(args.allow_synthetic_only)
        prepared = _expected(args.expected_preflight, args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists())
    except Exception:
        print("source_player_probe_preflight_or_verification_failed", file=sys.stderr)
        return 3
    key = SecretStr(os.environ.get(KEY_ENV, "").strip())
    if not key.get_secret_value():
        print("source_player_probe_credential_missing", file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_probe(prepared, api_key=key, batch_id=args.batch_id, run_directory=run_path(args.batch_id)))
        code = _read_json(run_path(args.batch_id)/"summary.json")["process_exit_code"]
        print(_json({"summary_path": str((run_path(args.batch_id)/"summary.json").resolve()), "process_exit_code": code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("source_player_probe_local_failure", file=sys.stderr)
        return 3
    finally:
        key = None


if __name__ == "__main__":
    raise SystemExit(main())
