"""One frozen synthetic Qwen/GPT-OSS comparison through setup -> P/K -> H6.

Four independent three-turn blocks share one HTTP budget and pacing clock.
No old experiment is modified, imported as an arm, or monkeypatched. Auditing
reconstructs local consistency, not provider authenticity or narrative quality.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import hashlib
import json
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
from api.llm.adapters.groq import GroqAdapter, GROQ_OFFICIAL_BASE_URL
from api.llm.contract import CancellationToken, GenerationParameters, InvocationEvidence, LLMTarget, NormalizedError, utc_now
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
from scripts import evaluate_source_player as player
from scripts import evaluate_retained_source as retained
from scripts.narrator_record_budget_observer import BudgetObservationAdapter

shared, profile = retained.shared, retained.profile
_json, _sha, _same = retained._json, retained._sha, retained._same
_read_json, _loads, _request = retained._read_json, retained._loads, retained._request
_result_record = retained._result_record
ProbePersistence = retained.ProbePersistence
PROBE_KIND = "source_model_comparison"
EXPERIMENT_VERSION = "source-comparison-v1"
PROTOCOL = "narrative-source-application-v1"
KEY_ENV = "STORYTELLER_SOURCE_COMPARISON_GROQ_KEY"
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
QWEN_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"
GPT_OSS_ID = "gpt-oss-120b-groq-free-synthetic-low"
CANDIDATE_IDS = (QWEN_ID, GPT_OSS_ID)
MODELS = {QWEN_ID: ("qwen/qwen3.8-27b", "none"), GPT_OSS_ID: ("openai/gpt-oss-120b", "low")}
MAX_CALLS, TURNS_PER_BLOCK = 12, 3
PARAMETERS = {"temperature": .65, "max_output_tokens": 768, "max_total_output_tokens": 9216,
    "initial_quiet_seconds": 60, "minimum_inter_call_delay_seconds": 60, "deadline_seconds": 60}
MANIFEST_PATH, MANIFEST_SHA256 = player.MANIFEST_PATH, player.MANIFEST_SHA256
PROMPT_PATH, PROMPT_FILE_SHA256, PROMPT_SHA256 = player.PROMPT_PATH, player.PROMPT_FILE_SHA256, player.PROMPT_SHA256
CORPUS_PATH = PROJECT_ROOT / "evals/narrator/source_comparison_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "evals/narrator/source_comparison_protocol_v1.md"
CORPUS_SHA256 = "b755b921be4a77b2c1af030a0eed65fc4e9d9e81d5c4393eaf99507fc6e7d9e5"
PROTOCOL_SHA256 = "ea2257537c8d913872dd65dadf0f3ff42a01162f9584c970c5665bc777be741d"
IMPLEMENTATION_FILES = tuple(dict.fromkeys(player.IMPLEMENTATION_FILES + ("scripts/evaluate_source_comparison.py",)))
CHAIN_ERRORS = frozenset({"invalid_structured_output", "malformed_response", "content_rejected"})


def _require(condition, code="source_comparison_artifact_invalid"):
    if not condition:
        raise ValueError(code)


def run_path(batch_id):
    return OUTPUT_ROOT / ("source-comparison-" + retained._batch(batch_id))


def _session(batch, block):
    return str(uuid5(UUID(batch), "source-comparison." + block.block_id))


def _operation(session, index):
    return str(uuid5(UUID(session), "source-comparison.turn." + str(index + 1)))


def _scope():
    return {"purpose": PROBE_KIND, "probe_kind": PROBE_KIND, "experiment_version": EXPERIMENT_VERSION,
        "protocol": PROTOCOL, "selected_candidate_ids": list(CANDIDATE_IDS), "synthetic_only": True,
        "campaign_data_eligible": False, "cap_001_approved": False, "runtime_default_eligible": False,
        "semantic_not_evaluated": True, "max_calls": MAX_CALLS}


@dataclass(frozen=True)
class PreparedBlock:
    block_id: str
    candidate: shared.Candidate
    target: LLMTarget
    case: dict
    prompt: str


@dataclass(frozen=True)
class PreparedExperiment:
    blocks: tuple[PreparedBlock, ...]
    metadata: dict


def prepare_experiment():
    for path, digest in ((MANIFEST_PATH, MANIFEST_SHA256), (PROMPT_PATH, PROMPT_FILE_SHA256),
                         (CORPUS_PATH, CORPUS_SHA256), (PROTOCOL_PATH, PROTOCOL_SHA256)):
        _require(shared._sha256(path) == digest, "source_comparison_input_changed")
    corpus = _read_json(CORPUS_PATH)
    _require(corpus["version"] == EXPERIMENT_VERSION and corpus["synthetic_only"] is True
        and corpus["selected_candidate_ids"] == list(CANDIDATE_IDS) and corpus["generation_parameters"] == PARAMETERS
        and corpus["max_calls"] == 12 and corpus["max_calls_per_block"] == 3
        and corpus["reasoning_effort"] == {cid: MODELS[cid][1] for cid in CANDIDATE_IDS})
    cases = corpus["cases"]
    _require(len(cases) == 2 and [case["case_id"] for case in cases] ==
        ["workshop-dialogue-continuity", "archive-dialogue-continuity"])
    candidates = shared.load_candidates(MANIFEST_PATH)
    text = PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", text, re.DOTALL)
    _require(front is not None)
    prompt = text[front.end():].strip()
    _require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA256 and profile.VERSION == PROTOCOL)
    for case in cases:
        setup = create_source_setup_manifest(case["setup"], session_id="00000000-0000-0000-0000-000000000000")
        _require(len(case["turns"]) == 3 and len(setup.request.npcs_present) == 1)
        for index, turn in enumerate(case["turns"]):
            SourcePlayerActionRequest(operation_id=str(index), player_input=turn["player_input"])
    blocks = []
    schedule = (("block-1", QWEN_ID, 0), ("block-2", GPT_OSS_ID, 0), ("block-3", GPT_OSS_ID, 1), ("block-4", QWEN_ID, 1))
    _require(corpus["blocks"] == [{"block_id": name, "candidate_id": cid, "case_id": cases[index]["case_id"]}
        for name, cid, index in schedule])
    for block_id, candidate_id, case_index in schedule:
        candidate = candidates[candidate_id]
        model, reasoning = MODELS[candidate_id]
        _require(candidate.adapter_kind == "groq" and candidate.model == model
            and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
            and candidate.reasoning_effort == reasoning and candidate.structured_mode == "native"
            and candidate.campaign_data_eligible is False)
        target = LLMTarget(profile="source-comparison-" + candidate_id, provider="Groq", model=model)
        blocks.append(PreparedBlock(block_id, candidate, target, copy.deepcopy(cases[case_index]), prompt))
    schema = profile.NarrativeSourceProposal.model_json_schema()
    metadata = {**_scope(), "generation_parameters": copy.deepcopy(PARAMETERS),
        "evaluator": {**shared._evaluator_provenance(), "file": "scripts/evaluate_source_comparison.py",
            "sha256": shared._sha256(Path(__file__)), "version": EXPERIMENT_VERSION},
        "inputs": {
            "manifest": {"file": MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256": MANIFEST_SHA256},
            "corpus": {"file": CORPUS_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256": CORPUS_SHA256, "data": corpus},
            "protocol": {"file": PROTOCOL_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256": PROTOCOL_SHA256},
            "prompt": {"file": PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(), "file_sha256": PROMPT_FILE_SHA256, "sha256": PROMPT_SHA256},
            "candidates": [{"candidate_id": cid, "model": MODELS[cid][0], "reasoning_effort": MODELS[cid][1], "provider": "Groq"} for cid in CANDIDATE_IDS],
            "initial_state": player._state(), "relationships": {},
            "response_schema_sha256": _sha(schema), "provider_schema_sha256": _sha(retained._normalize_groq_strict_schema(schema)),
            "implementation": [{"file": f, "sha256": shared._sha256(PROJECT_ROOT/f)} for f in IMPLEMENTATION_FILES]},
        "schedule": [{"block_id": b.block_id, "case_id": b.case["case_id"], "candidate_id": b.candidate.candidate_id,
            "turn_keys": [t["turn_key"] for t in b.case["turns"]]} for b in blocks],
        "source_policy": {"source_field": "n", "briefing_is_source": False, "question_is_source": False,
            "canonical_truth_confirmed": False, "producer": "source-local-ordinary-v1",
            "replay": "fresh_store_no_production_or_gateway", "history": "own_previous_committed_complete_sources_max_two"},
        "first_request_templates": [{"block_id": b.block_id, "is_live_request": False, "requires_retained_capsule": True,
            "body_sha256": None, "setup": b.case["setup"], "player_input": b.case["turns"][0]["player_input"],
            "provider_static": {"model": b.target.model, "reasoning_effort": b.candidate.reasoning_effort,
                "system_prompt": prompt, "response_schema": retained._normalize_groq_strict_schema(schema)}} for b in blocks]}
    return PreparedExperiment(tuple(blocks), metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment)
    current = prepare_experiment()
    _require(current.blocks == prepared.blocks and _same(current.metadata, prepared.metadata), "source_comparison_prepared_drift")


def _config(block):
    return create_source_producer_config(target=block.target, system_prompt=block.prompt,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        npc_aliases=tuple(block.case["setup"]["npcs_present"]))


def _body(request, reasoning_effort):
    builder = object.__new__(GroqAdapter)
    builder._reasoning_effort = reasoning_effort
    return GroqAdapter._payload(builder, request, stream=False, response_format=builder._native_response_format(request))


def _request_record(request, block):
    body = _body(request, block.candidate.reasoning_effort)
    return {"operation": request.operation, "invocation_id": request.invocation_id, "deadline": request.deadline.isoformat(),
        "body_sha256": _sha(body), "user_packet": request.messages[1].content, "request": body}


class DispatchBudget:
    """One global pacer; actual HTTP admission enforces both time and call caps."""
    def __init__(self):
        self.calls = 0
        self.block_calls = {}
        self.pacer = shared._CallPacer(60)
        self.last_dispatch = self.pacer._clock()
        self.pacer._last_call_started_at = self.last_dispatch

    async def wait(self, block_id):
        await self.pacer.before_call("source comparison " + block_id)

    def consume(self, block_id):
        now = self.pacer._clock()
        _require(self.calls < MAX_CALLS and self.block_calls.get(block_id, 0) < 3, "source_comparison_http_limit")
        _require(now - self.last_dispatch >= 60, "source_comparison_http_spacing")
        self.calls += 1
        self.block_calls[block_id] = self.block_calls.get(block_id, 0) + 1
        self.last_dispatch = self.pacer._last_call_started_at = now


class ObservationAdapter(retained.RetainedObservationAdapter):
    """Reuse bounded capture/key filtering, with an explicitly bound candidate."""
    def __init__(self, *, block, request, api_key, budget, transport=None):
        BudgetObservationAdapter.__init__(self, base_url=GROQ_OFFICIAL_BASE_URL,
            capability_set=shared._capabilities(block.candidate, block.target), api_key=api_key,
            reasoning_effort=block.candidate.reasoning_effort, transport=transport)
        self.block, self.approved = block, _request_record(request, block)
        self.budget, self.http_sent, self.credential_echo_blocked, self.capture = budget, False, False, {}
        self.http_started_at = None

    def _effective_model(self, payload):
        return self.block.target.model if payload.get("model") == self.block.target.model else None

    def _payload(self, request, *, stream, response_format):
        payload = GroqAdapter._payload(self, request, stream=stream, response_format=response_format)
        _require(not stream and not self._dispatch_started and _same(_request_record(request, self.block), self.approved)
            and _sha(payload) == self.approved["body_sha256"], "source_comparison_request_changed")
        self._dispatch_started = True
        return payload

    async def _dispatch(self, request):
        _require(not self.http_sent and request.method == "POST"
            and str(request.url) == GROQ_OFFICIAL_BASE_URL + "/chat/completions"
            and _sha(_loads(request.content)) == self.approved["body_sha256"], "source_comparison_http_request_invalid")
        now = utc_now()
        _require(now <= datetime.fromisoformat(self.approved["deadline"]), "source_comparison_expired_dispatch")
        self.budget.consume(self.block.block_id)
        self.http_sent = True
        self.http_started_at = now.isoformat()


async def _prepare(store, block, session, index, *, replay=False):
    return await prepare_source_player_action(session_id=session,
        request=SourcePlayerActionRequest(operation_id=_operation(session, index), player_input=block.case["turns"][index]["player_input"]),
        store=store, producer_config=_config(block), cancellation=CancellationToken(),
        deadline=utc_now()+timedelta(seconds=-1 if replay else 60))


async def _replay(store, session, operation):
    return await execute_retained_source_turn(session_id=session, operation_id=operation, store=store,
        gateway=retained.NoCallGateway(), deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(),
        on_chunk=retained._forbid_replay_chunk)


async def _replay_input(store, block, session, index, row):
    attempt = await store.load_attempt_by_operation(session, source_input_operation_id(session, row["operation_id"]))
    _require(attempt is not None)
    claim = await _prepare(ProbePersistence(store.db_path), block, session, index, replay=True)
    _require(not claim.newly_claimed)
    if row["input_claim"] is not None:
        _require(_same(row["input_claim"], claim.model_dump(mode="json")))
    row["input_claim"], row["input_replay_verified"] = claim.model_dump(mode="json"), True


def _identity(block, session, index):
    return {"block_id": block.block_id, "case_id": block.case["case_id"], "candidate_id": block.candidate.candidate_id,
        "session_id": session, "turn_key": block.case["turns"][index]["turn_key"], "operation_id": _operation(session, index)}


def _turn_row(block, session, index):
    return {**_identity(block, session, index), "kind": "source_comparison_turn", "input_claim": None,
        "input_replay_verified": False, "capsule": None, "request": None, "deadline_created_at": None,
        "call_made": False, "schema_valid": False, "route_status": "unavailable",
        "provider_observation": retained._unavailable_observation(), "response_structure": None,
        "evidence": None, "llm_error": None, "credential_echo_blocked": False, "http_started_at": None,
        "result": None, "replay_verified": False, "local_error": None}


def _global_stop(row):
    if row["local_error"] is not None:
        return row["local_error"]
    if row["credential_echo_blocked"]:
        return "credential_echo_blocked"
    reported = row["provider_observation"]["usage"]["output_tokens"]
    if type(reported) is int and reported > PARAMETERS["max_output_tokens"]:
        return "reported_budget_exceeded"
    if row["result"] is not None and row["result"]["status"] in ("timeout", "cancelled"):
        return row["result"]["status"]
    if row["llm_error"] is not None and row["llm_error"]["category"] not in CHAIN_ERRORS:
        return row["llm_error"]["category"]
    if row["input_claim"] is not None and row["input_claim"]["status"] != "completed":
        return "producer_failure"
    if row["result"] is not None and row["result"]["status"] != "completed" and row["llm_error"] is None and row["response_structure"] is None:
        return "unclassified_provider_failure" if row["call_made"] else "local_error"
    return None


async def _execute_turn(store, experiment, block, session, index, budget, api_key):
    row, adapter = _turn_row(block, session, index), None
    try:
        _check_prepared(experiment)
        claim = await _prepare(store, block, session, index)
        row["input_claim"] = claim.model_dump(mode="json")
        await _replay_input(store, block, session, index, row)
        if claim.status == "completed":
            capsule = await store.load_source_preparation(session, row["operation_id"])
            _require(capsule is not None and type(capsule.preparation) is DeclaredActionPreparation)
            row["capsule"] = capsule.model_dump(mode="json")
            await budget.wait(block.block_id)
            _check_prepared(experiment)
            created = utc_now()
            deadline = created + timedelta(seconds=60)
            request = _request(capsule, deadline)
            row["deadline_created_at"], row["request"] = created.isoformat(), _request_record(request, block)
            adapter = ObservationAdapter(block=block, request=request, api_key=api_key, budget=budget)
            result = await execute_retained_source_turn(session_id=session, operation_id=row["operation_id"], store=store,
                gateway=adapter, deadline=deadline, cancellation=CancellationToken(), on_chunk=retained._no_chunk)
            row["result"] = _result_record(result)
            if result.status == "completed":
                replay = await _replay(ProbePersistence(store.db_path), session, row["operation_id"])
                _require(_same(_result_record(replay), row["result"]))
                await _replay_input(store, block, session, index, row)
                row["replay_verified"] = True
    except asyncio.CancelledError:
        row["local_error"] = "cancelled"
        producer = await store.load_attempt_by_operation(session, source_input_operation_id(session, row["operation_id"]))
        if producer is not None:
            await _replay_input(store, block, session, index, row)
            capsule = await store.load_source_preparation(session, row["operation_id"])
            row["capsule"] = capsule.model_dump(mode="json") if capsule else None
        if await store.load_turn_by_operation(session, row["operation_id"]) is not None:
            replay = await _replay(ProbePersistence(store.db_path), session, row["operation_id"])
            row["result"], row["replay_verified"] = _result_record(replay), True
    except Exception:
        row["local_error"] = "local_error"
    finally:
        if adapter is not None:
            row.update({key: copy.deepcopy(adapter.capture.get(key))
                for key in ("response_structure", "evidence", "llm_error")})
            row["http_started_at"] = adapter.http_started_at
            row.update(provider_observation=adapter.observation, call_made=adapter.http_sent,
                credential_echo_blocked=adapter.credential_echo_blocked, schema_valid=adapter.capture.get("response_structure") is not None)
            if row["evidence"] is not None:
                row["route_status"] = retained._route_status(row["evidence"], block.target, row["request"]["invocation_id"])
            adapter._reject_echo(row)
    return row


async def evaluate_comparison(prepared, *, api_key, batch_id, run_directory):
    retained._batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip()), "source_comparison_credential_invalid")
    _require(api_key.get_secret_value().strip() not in _json(prepared.metadata), "source_comparison_credential_conflict")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve())
    directory.mkdir(parents=True, exist_ok=False)
    started = utc_now().isoformat()
    budget, rows, artifacts, manifests, stop = DispatchBudget(), [], {}, {}, None
    try:
        for block in prepared.blocks:
            session, store, chain_failed = _session(batch_id, block), None, False
            if stop is None:
                store = ProbePersistence(directory/(block.block_id+".working.sqlite3"))
                await store.initialize()
                setup = await create_source_trial_setup(session_id=session, request=block.case["setup"], store=store,
                    initial_state=player._state(), relationships={})
                _require(await ProbePersistence(store.db_path).read_source_setup_manifest(session) == setup)
                manifests[block.block_id] = setup.model_dump(mode="json")
            for index in range(TURNS_PER_BLOCK):
                if stop is not None or chain_failed:
                    rows.append({**_identity(block, session, index), "kind": "source_comparison_skip",
                        "reason": "global_"+stop if stop is not None else "previous_chain_failure"})
                    continue
                row = await _execute_turn(store, prepared, block, session, index, budget, api_key)
                rows.append(row)
                stop = _global_stop(row)
                chain_failed = row["result"] is None or row["result"]["status"] != "completed"
            if store is not None:
                destination = directory/(block.block_id+".sqlite3")
                retained._seal_database(store.db_path, destination)
                artifacts[block.block_id] = {"file": destination.name, "sha256": shared._sha256(destination)}
    finally:
        # Unexpected filesystem/setup failures preserve existing evidence but cannot
        # be certified as a complete matrix. They surface as a local CLI failure.
        raw = "".join(_json({"metadata": prepared.metadata, "batch_id": batch_id, "record": row})+"\n" for row in rows)
        records = directory/"records.jsonl"
        records.write_text(raw, encoding="utf-8")
        if len(rows) == MAX_CALLS:
            summary = summarize(rows, prepared, batch_id)
            document = {"metadata": prepared.metadata, "batch_id": batch_id, "started_at": started,
                "finished_at": utc_now().isoformat(), "setup_manifests": manifests, "summary": summary,
                "artifacts": {"databases": artifacts, "records": {"file": records.name, "sha256": shared._sha256(records)}},
                "process_exit_code": summary["process_exit_code"]}
            (directory/"summary.json").write_text(_json(document)+"\n", encoding="utf-8")
    return rows


def summarize(rows, prepared, batch):
    _require(type(rows) is list and len(rows) == MAX_CALLS)
    processed, stop = [], None
    for block_index, block in enumerate(prepared.blocks):
        failed = False
        for index, row in enumerate(rows[block_index*3:block_index*3+3]):
            session = _session(batch, block)
            _require(all(row.get(k) == v for k, v in _identity(block, session, index).items()))
            if stop is not None or failed:
                _require(set(row) == set(_identity(block, session, index)) | {"kind", "reason"}
                    and row["kind"] == "source_comparison_skip"
                    and row["reason"] == ("global_"+stop if stop is not None else "previous_chain_failure"))
                continue
            _require(set(row) == set(_turn_row(block, session, index)) and row["kind"] == "source_comparison_turn")
            for key in ("call_made", "schema_valid", "replay_verified", "input_replay_verified", "credential_echo_blocked"):
                _require(type(row[key]) is bool)
            _require(row["schema_valid"] == (row["response_structure"] is not None)
                and (not row["schema_valid"] or row["call_made"] and row["route_status"] == "verified"))
            _require(row["local_error"] in (None, "local_error", "cancelled"))
            _require(not row["credential_echo_blocked"] or row["response_structure"] is row["evidence"] is None)
            failed = row["result"] is None or row["result"]["status"] != "completed"
            if not failed:
                _require(row["replay_verified"] and row["input_replay_verified"] and row["schema_valid"] and row["call_made"])
            stop = _global_stop(row)
            processed.append(row)
    def metrics(items):
        calls = [r for r in items if r["call_made"]]
        usage = {key: sum(r["provider_observation"]["usage"][key] for r in calls)
            if calls and all(r["provider_observation"]["usage"][key] is not None for r in calls) else None
            for key in ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens")}
        return {"usage_reported": usage, "requested_output_token_ceiling": len(calls)*PARAMETERS["max_output_tokens"],
            "turns_processed": len(items), "turns_committed": sum(r["result"] is not None and r["result"]["status"] == "completed" for r in items),
            "calls_made": sum(r["call_made"] for r in items), "schema_valid": sum(r["schema_valid"] for r in items),
            "route_verified": sum(r["route_status"] == "verified" for r in items), "capsules_retained": sum(r["capsule"] is not None for r in items),
            "input_replays_verified": sum(r["input_replay_verified"] for r in items), "replays_verified": sum(r["replay_verified"] for r in items)}
    overall = metrics(processed)
    success = overall["turns_committed"] == MAX_CALLS and stop is None
    code = 130 if stop == "cancelled" else 3 if stop in ("local_error", "credential_echo_blocked", "producer_failure") else 2 if stop else 0 if success else 1
    return {**_scope(), **overall, "turns_skipped": MAX_CALLS-len(processed), "global_stop_reason": stop,
        "operational_comparison_passed": success, "process_exit_code": code,
        "by_candidate": {cid: metrics([r for r in processed if r["candidate_id"] == cid]) for cid in CANDIDATE_IDS},
        "by_block": {b.block_id: metrics([r for r in processed if r["block_id"] == b.block_id]) for b in prepared.blocks},
        "semantic_fidelity_review": {"status": "not_performed", "approval": None}}


def _expected(path, digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and shared._sha256(Path(path)) == digest, "source_comparison_preflight_hash_invalid")
    prepared = prepare_experiment()
    _require(_same(_read_json(path), prepared.metadata), "source_comparison_preflight_changed")
    return prepared


def _observation(row, expected_model):
    """Closed observer shape, parameterized by the actual block target."""
    observation = row["provider_observation"]
    if not row["call_made"]:
        _require(_same(observation, retained._unavailable_observation()), "source_comparison_observation_without_http")
    shapes = {"usage": {"input_tokens", "output_tokens", "total_tokens", "reasoning_tokens"},
        "error_body": {"status", "complete", "bytes", "json_valid"},
        "failed_generation": {"status", "present", "characters", "json_valid", "error_position"}}
    _require(type(observation) is dict and set(observation) == {"schema", "http_status", "request_id", "provider_code", "model", "finish_reason", *shapes}
        and observation["schema"] == "storyteller.eval.record-budget-observation.v1"
        and all(type(observation[k]) is dict and set(observation[k]) == fields for k, fields in shapes.items()))
    _require(observation["model"] in (None, expected_model) and observation["provider_code"] in (None, "json_validate_failed", "rate_limit_exceeded")
        and observation["finish_reason"] in (None, "stop", "length", "content_filter", "tool_calls", "function_call", "unknown"))
    _require(observation["request_id"] is None or type(observation["request_id"]) is str
        and re.fullmatch(r"req_[a-z0-9]{26}", observation["request_id"]) is not None)
    body, failed = observation["error_body"], observation["failed_generation"]
    _require(body["status"] in ("unavailable", "reading", "complete", "parser_limit", "limit_exceeded", "invalid_content_length", "read_error", "interrupted")
        and failed["status"] in ("unavailable", "absent", "non_string", "observed", "parser_limit")
        and all(value is None or type(value) is bool for value in (body["complete"], body["json_valid"], failed["present"], failed["json_valid"])))
    _require(all(value is None or type(value) is int and value >= 0 for value in
        (*observation["usage"].values(), body["bytes"], failed["characters"], failed["error_position"]))
        and (body["bytes"] is None or body["bytes"] <= 65536)
        and (observation["http_status"] is None or type(observation["http_status"]) is int and 100 <= observation["http_status"] <= 599))
    evidence, error = row["evidence"] or {}, row["llm_error"] or {}
    for left, right in ((observation["model"], evidence.get("effective_model", {}).get("value")),
                       (observation["http_status"], error.get("status_code")), (observation["request_id"], error.get("external_id"))):
        _require(left is None or right is None or left == right)


def _verify_audit(row, attempt, request):
    """Reconstruct the product audit, including its timeout/cancel statuses."""
    provenance, usage = attempt["provenance"], attempt["usage"]
    if row["evidence"] is None:
        _require(provenance is usage is None and row["llm_error"] is None)
        return
    _require(type(provenance) is dict and set(provenance) == {"invocations"}
        and type(usage) is dict and set(usage) == {"invocations"}
        and len(provenance["invocations"]) == len(usage["invocations"]) == 1)
    identity, measurement = provenance["invocations"][0], usage["invocations"][0]
    evidence = InvocationEvidence.model_validate({"provenance": identity["provenance"], "usage": measurement["tokens"], "cost": measurement["cost"]})
    _require(_same(shared._evidence_payload(evidence), row["evidence"])
        and evidence.provenance.invocation_id == request.invocation_id and evidence.provenance.requested_target == request.target)
    _require(set(identity) == {"invocation_id", "operation", "status", "provenance", "error"}
        and set(measurement) == {"invocation_id", "operation", "status", "tokens", "cost"})
    for key, value in (("invocation_id", request.invocation_id), ("operation", retained.INVOCATION_OPERATION)):
        _require(identity[key] == measurement[key] == value)
    if row["llm_error"] is None:
        _require(identity["status"] == measurement["status"] == "completed" and identity["error"] is None)
    else:
        error = NormalizedError.model_validate({**row["llm_error"], "invocation_id": request.invocation_id,
            "target": request.target, "evidence": evidence})
        _require(_same(shared._normalized_error_payload(error), row["llm_error"]))
        status = {"timeout": "timed_out", "cancelled": "cancelled"}.get(error.category.value, "failed")
        _require(identity["status"] == measurement["status"] == status
            and identity["error"] == {"category": error.category.value, "code": "source_turn_provider_failure"})
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        observed, reported = row["provider_observation"]["usage"][key], getattr(evidence.usage, key)
        _require(observed is None or reported is None or observed == reported)


async def _verify_database(database, block, session, rows, manifest):
    store = ProbePersistence(database)
    actual = await store.read_source_setup_manifest(session)
    _require(actual == validate_source_setup_manifest(manifest, session_id=session)
        == create_source_setup_manifest(block.case["setup"], session_id=session))
    snapshot = await store.read_source_context_snapshot(session)
    completed = sum(r.get("result") is not None and r["result"]["status"] == "completed" for r in rows)
    _require(snapshot.current_turn == snapshot.state_revision == completed and snapshot.canonical_scene == actual.origin.seed_scene)
    campaign = await store.load_campaign(session)
    _require(_same(campaign["state"], player._state()) and campaign["relationships"] == {})
    expected_ops, committed = set(), []
    for index, row in enumerate(rows):
        if row["kind"] == "source_comparison_skip":
            continue
        _observation(row, block.target.model)
        p_id = source_input_operation_id(session, row["operation_id"])
        producer = await store.load_attempt_by_operation(session, p_id)
        capsule = await store.load_source_preparation(session, row["operation_id"])
        if row["input_claim"] is None:
            _require(producer is capsule is row["capsule"] is row["request"] is row["result"] is None
                and not row["call_made"] and not row["input_replay_verified"] and row["local_error"] is not None)
            continue
        expected_ops.add(p_id)
        claim = SourceInputClaim.model_validate(row["input_claim"])
        _require(producer is not None and not claim.newly_claimed and claim.request.operation_id == row["operation_id"])
        _require(claim.request.player_input == block.case["turns"][index]["player_input"] and claim.request.session_id == session
            and claim.request.state == player._state() and claim.request.relationships == {} and claim.request.config == _config(block))
        _require(claim.request.snapshot.current_turn == claim.request.snapshot.state_revision == index)
        _require(_same([s.model_dump(mode="json") for s in claim.request.snapshot.sources], committed[-2:]))
        _require(producer["request_hash"] == source_input_request_hash(claim.request)
            and producer["result_hash"] == source_input_result_hash(claim.request, claim.completion))
        _require(await _prepare(store, block, session, index, replay=True) == claim and row["input_replay_verified"])
        if claim.status != "completed":
            _require(capsule is row["capsule"] is row["request"] is row["result"] is None and not row["call_made"])
            continue
        expected_ops.add(source_preparation_operation_id(session, row["operation_id"]))
        _require(capsule is not None and _same(capsule.model_dump(mode="json"), row["capsule"]))
        capsule = validate_source_turn_capsule(capsule, session_id=session, operation_id=row["operation_id"])
        _require(type(capsule.preparation) is DeclaredActionPreparation)
        _require(claim.completion == create_source_input_completion(claim.request, status="completed", capsule=capsule))
        deadline = datetime.fromisoformat(row["request"]["deadline"]) if row["request"] is not None else None
        request = _request(capsule, deadline)
        _require(row["request"] is None or _same(row["request"], _request_record(request, block)))
        _require(not row["call_made"] or row["request"] is not None)
        _require(row["route_status"] == retained._route_status(row["evidence"], block.target, request.invocation_id))
        if row["request"] is not None:
            created = datetime.fromisoformat(row["deadline_created_at"])
            _require(created.tzinfo is not None and deadline.tzinfo is not None and deadline-created == timedelta(seconds=60))
        else:
            _require(row["deadline_created_at"] is None)
        attempt = await store.load_attempt_by_operation(session, row["operation_id"])
        if attempt is not None:
            expected_ops.add(row["operation_id"])
            _require(attempt["attempt_id"] == capsule.draft.attempt_id and attempt["partial_narrative"] == "")
            _verify_audit(row, attempt, request)
        else:
            _require(row["evidence"] is row["llm_error"] is None)
        await store.read_source_operation_status(session, row["operation_id"])
        result = row["result"]
        if result is None:
            _require(row["local_error"] is not None and (attempt is None or attempt["status"] in ("failed", "cancelled", "timeout")))
            continue
        _require(set(result) == {"status", "operation_id", "turn_id", "turn_number", "error", "narrative", "envelope"})
        _require(attempt is not None and result["status"] == attempt["status"] and result["operation_id"] == capsule.operation_id
            and result["turn_id"] == capsule.draft.turn_id and result["turn_number"] == index+1)
        projection, policy_error = None, None
        if row["response_structure"] is not None:
            proposal = profile.NarrativeSourceProposal.model_validate(row["response_structure"])
            _require(_same(proposal.model_dump(mode="json", by_alias=True), row["response_structure"]))
            try:
                projection = profile.create_source_projection(proposal, source_id="source-"+request.invocation_id,
                    session_id=session, turn_id=capsule.draft.turn_id, invocation_id=request.invocation_id,
                    current_scene=capsule.canonical_scene, facts=capsule.draft.facts, player_input=capsule.player_input,
                    player_aliases=capsule.player_aliases, npc_aliases=capsule.npc_aliases)
            except (ValueError, TypeError) as exc:
                policy_error = getattr(exc, "code", None)
                _require(type(policy_error) is str)
        if result["status"] == "completed":
            _require(projection is not None and row["schema_valid"] and row["route_status"] == "verified" and row["replay_verified"])
            _require(_same(result["envelope"]["projection"], projection.model_dump(mode="json")))
            replay = await _replay(store, session, row["operation_id"])
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
    attempts = await store.list_attempts(session)
    _require({a["operation_id"] for a in attempts} == expected_ops and all(a["status"] != "pending" for a in attempts))


def _artifact(entry, path, expected_name, limit):
    file = path.parent/expected_name
    _require(type(entry) is dict and set(entry) == {"file", "sha256"} and entry["file"] == expected_name
        and not file.is_symlink() and file.resolve().parent == path.parent.resolve() and file.stat().st_size <= limit
        and shared._sha256(file) == entry["sha256"])
    return file


def verify_artifacts(summary_path, expected_preflight, batch_id, *, expected_preflight_sha256):
    prepared = _expected(expected_preflight, expected_preflight_sha256)
    path = Path(summary_path)
    _require(path.resolve() == (run_path(batch_id)/"summary.json").resolve() and not path.is_symlink())
    doc = _read_json(path)
    _require(set(doc) == {"metadata", "batch_id", "started_at", "finished_at", "setup_manifests", "summary", "artifacts", "process_exit_code"}
        and _same(doc["metadata"], prepared.metadata) and doc["batch_id"] == batch_id)
    start, end = (datetime.fromisoformat(doc[k]) for k in ("started_at", "finished_at"))
    _require(start.tzinfo is not None and end.tzinfo is not None and end >= start)
    _require(set(doc["artifacts"]) == {"databases", "records"})
    records = _artifact(doc["artifacts"]["records"], path, "records.jsonl", 8*retained.MAX_JSON_BYTES)
    lines = records.read_text(encoding="utf-8").splitlines()
    _require(len(lines) == MAX_CALLS)
    rows = []
    for line in lines:
        item = _loads(line.encode("utf-8"))
        _require(set(item) == {"metadata", "batch_id", "record"} and _same(item["metadata"], prepared.metadata) and item["batch_id"] == batch_id)
        rows.append(item["record"])
    summary = summarize(rows, prepared, batch_id)
    _require(_same(summary, doc["summary"]) and type(doc["process_exit_code"]) is int and doc["process_exit_code"] == summary["process_exit_code"])
    present = {b.block_id for i, b in enumerate(prepared.blocks) if rows[i*3]["kind"] == "source_comparison_turn"}
    _require(set(doc["artifacts"]["databases"]) == set(doc["setup_manifests"]) == present)
    databases = {name: _artifact(entry, path, name+".sqlite3", retained.MAX_DB_BYTES)
        for name, entry in doc["artifacts"]["databases"].items()}
    originals = {p: shared._sha256(p) for p in (path, records, *databases.values())}
    previous = start
    for row in rows:
        if row.get("call_made"):
            # Known-key rejection clears observer metadata; timestamps remain a
            # separate safe dispatch fact, never recovered from provider text.
            now = datetime.fromisoformat(row["http_started_at"])
            created, deadline = (datetime.fromisoformat(row[k]) if k == "deadline_created_at"
                else datetime.fromisoformat(row["request"]["deadline"]) for k in ("deadline_created_at", "deadline"))
            _require(now.tzinfo is not None and created.tzinfo is not None and deadline.tzinfo is not None
                and now-previous >= timedelta(seconds=60) and start <= created <= now <= deadline and now <= end)
            previous = now
        elif row["kind"] == "source_comparison_turn":
            _require(row["http_started_at"] is None)
        if row.get("evidence") is not None:
            created = datetime.fromisoformat(row["deadline_created_at"])
            deadline = datetime.fromisoformat(row["request"]["deadline"])
            evidence_start, evidence_end = (datetime.fromisoformat(row["evidence"][k]) for k in ("started_at", "finished_at"))
            _require(evidence_start.tzinfo is not None and evidence_end.tzinfo is not None
                and start <= created <= evidence_start <= evidence_end <= end, "source_comparison_evidence_chronology")
            if row["call_made"]:
                _require(evidence_start <= datetime.fromisoformat(row["http_started_at"]) <= evidence_end,
                    "source_comparison_evidence_chronology")
            if row["llm_error"] is None and row["response_structure"] is not None:
                _require(evidence_end <= deadline, "source_comparison_evidence_deadline")
    with tempfile.TemporaryDirectory(prefix="storyteller-source-comparison-verify-") as temporary:
        for i, block in enumerate(prepared.blocks):
            if block.block_id not in present:
                continue
            session = _session(batch_id, block)
            database = Path(temporary)/(block.block_id+".sqlite3")
            database.write_bytes(databases[block.block_id].read_bytes())
            with retained._ClosingConnection(sqlite3.connect(database.resolve().as_uri()+"?mode=ro", uri=True)) as conn:
                conn.execute("PRAGMA query_only=ON")
                _require(conn.execute("PRAGMA integrity_check").fetchone() == ("ok",) and conn.execute("PRAGMA foreign_key_check").fetchall() == [])
                _require(conn.execute("SELECT session_id FROM campaigns").fetchall() == [(session,)])
                for table in ("attempts", "turns", "events"):
                    _require(conn.execute("SELECT count(*) FROM "+table+" WHERE session_id!=?", (session,)).fetchone() == (0,))
                for table in ("memory_candidates", "episodic_memories", "consolidations", "legacy_imports"):
                    _require(conn.execute("SELECT count(*) FROM "+table).fetchone() == (0,))
            asyncio.run(_verify_database(database, block, session, rows[i*3:i*3+3], doc["setup_manifests"][block.block_id]))
    _require(all(shared._sha256(p) == digest for p, digest in originals.items()))
    return {"verified": True, "batch_id": batch_id, "process_exit_code": summary["process_exit_code"], "summary_path": str(path.resolve())}


def main(argv=None):
    parser = argparse.ArgumentParser(description="One frozen twelve-call synthetic comparison; no replayed live calls.")
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
        print("source_comparison_preflight_or_verification_failed", file=sys.stderr)
        return 3
    key = SecretStr(os.environ.get(KEY_ENV, "").strip())
    if not key.get_secret_value():
        print("source_comparison_credential_missing", file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_comparison(prepared, api_key=key, batch_id=args.batch_id, run_directory=run_path(args.batch_id)))
        code = _read_json(run_path(args.batch_id)/"summary.json")["process_exit_code"]
        print(_json({"summary_path": str((run_path(args.batch_id)/"summary.json").resolve()), "process_exit_code": code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("source_comparison_local_failure", file=sys.stderr)
        return 3
    finally:
        key = None


if __name__ == "__main__":
    raise SystemExit(main())
