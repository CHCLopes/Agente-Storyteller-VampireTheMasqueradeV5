"""Two synthetic retained B turns; never a product runtime or a retry runner.

The preparation template is not a live body. Each actual body is reconstructed
from its retained capsule before HTTP. SQLite checks establish local consistency,
not provider authentication, semantic truth or crash-safe exactly-once delivery.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import NAMESPACE_URL, UUID, uuid5

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

import httpx
from pydantic import SecretStr
from api.llm.adapters.groq import GroqAdapter, GROQ_OFFICIAL_BASE_URL, GROQ_QWEN_MODEL_ID, _normalize_groq_strict_schema
from api.llm.contract import InvocationEvidence, NormalizedError, CancellationToken, GenerationParameters, LLMInvocationError, LLMMessage, LLMTarget, MessageRole, StructuredGenerationRequest, utc_now
from api.narrative_source_capsule import create_source_turn_capsule, validate_source_turn_capsule
from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_coordinator import prepare_retained_source_turn, execute_retained_source_turn
from api.narrative_source_preparation import DeclaredActionPreparation
from api import narrative_source_profile as profile
from api.narrative_source_turn import PROTOCOL as TURN_PROTOCOL, INVOCATION_OPERATION
from api.persistence import SQLitePersistence
from api.scene_service import SceneState
from api.turn_models import Visibility
from scripts import evaluate_narrator_models as shared
from scripts.evaluate_narrator_source import _route_status, _validate_observation_snapshot
from scripts.narrator_record_budget_observer import BudgetObservationAdapter, _unavailable_observation

PROBE_KIND = "retained_source_probe"
EXPERIMENT_VERSION = "retained-source-observation-v1"
PROTOCOL = "narrative-source-application-v1"
CANDIDATE_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"
TARGET_PROFILE = "retained-source-" + CANDIDATE_ID
CASE_ID = "gallery-retained-observe-wait"
TURN_KEYS = ("observe", "wait")
PLAYER_INPUTS = ("Observo a galeria sem tocar em nada.", "Aguardo no mesmo lugar sem tocar em nada.")
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
MANIFEST_PATH = PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
MANIFEST_SHA256 = "de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6"
PROMPT_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-v1.md"
PROMPT_FILE_SHA256 = "8859291d17c6036166878802839204d8b770f17c442dcd178c24cc357929477d"
PROMPT_SHA256 = "147588db153513bb5da8a0aff3f0ef67773481b8feabc40093de4f8bd259084c"
KEY_ENV = "STORYTELLER_RETAINED_GROQ_KEY"
MAX_CALLS = 2
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_DB_BYTES = 16 * 1024 * 1024
PARAMETERS = {"temperature": 0.65, "max_output_tokens": 768, "reasoning_effort": "none", "max_total_output_tokens": 1536,
              "initial_quiet_seconds": 60, "minimum_inter_call_delay_seconds": 60, "deadline_seconds": 60}
IMPLEMENTATION_FILES = (
    "scripts/evaluate_retained_source.py", "scripts/evaluate_narrator_source.py", "scripts/evaluate_narrator_models.py",
    "scripts/narrator_record_budget_observer.py", "api/narrative_source_coordinator.py", "api/narrative_source_capsule.py",
    "api/narrative_source_preparation.py", "api/narrative_source_execution_service.py", "api/narrative_source_context.py",
    "api/narrative_source_profile.py", "api/narrative_source_turn.py", "api/narrative_grounding.py", "api/persistence.py",
    "api/scene_service.py", "api/scene_director_service.py", "api/turn_models.py", "api/llm/contract.py",
    "api/llm/adapters/groq.py", "api/llm/adapters/openai_compatible.py",
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _same(left: Any, right: Any) -> bool:
    return _json(left) == _json(right)


def _require(condition: bool, code: str = "retained_probe_artifact_invalid") -> None:
    if not condition:
        raise ValueError(code)


def _batch(value: str) -> str:
    _require(type(value) is str and str(UUID(value)) == value, "retained_probe_batch_invalid")
    return value


def run_path(batch_id: str) -> Path:
    return OUTPUT_ROOT / ("retained-source-" + _batch(batch_id))


def _operation(batch: str, index: int) -> str:
    return str(uuid5(UUID(batch), "retained-source." + TURN_KEYS[index]))


def _scope() -> dict:
    return dict(purpose=PROBE_KIND, probe_kind=PROBE_KIND, experiment_version=EXPERIMENT_VERSION,
        protocol=PROTOCOL, selected_candidate_id=CANDIDATE_ID, synthetic_only=True, campaign_data_eligible=False,
        cap_001_approved=False, runtime_default_eligible=False, semantic_not_evaluated=True, max_calls=2)


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    prompt: str
    metadata: dict


def _request(capsule, deadline=None, cancellation=None) -> StructuredGenerationRequest:
    context = profile.build_source_context(session_id=capsule.session_id, current_scene=capsule.canonical_scene,
        attributed_sources=tuple(item.projection for item in capsule.snapshot.sources))
    user = _json({"context": context, "player_input": capsule.player_input, "turn": capsule.draft.turn_id,
        "server_facts": [item.model_dump(mode="json") for item in capsule.draft.facts
                         if item.visibility in (Visibility.PUBLIC, Visibility.PLAYER)]})
    _require(len(user) <= profile.MAX_CONTEXT_CHARACTERS, "retained_probe_user_budget_exceeded")
    invocation = str(uuid5(NAMESPACE_URL, _json([TURN_PROTOCOL, capsule.session_id, capsule.operation_id])))
    return StructuredGenerationRequest(operation=INVOCATION_OPERATION, invocation_id=invocation, target=capsule.target,
        messages=(LLMMessage(role=MessageRole.SYSTEM, content=capsule.system_prompt), LLMMessage(role=MessageRole.USER, content=user)),
        deadline=deadline or utc_now()+timedelta(seconds=60), cancellation=cancellation or CancellationToken(),
        parameters=capsule.parameters, response_model=profile.NarrativeSourceProposal)


def _body(request) -> dict:
    builder = object.__new__(GroqAdapter)
    builder._reasoning_effort = "none"
    return GroqAdapter._payload(builder, request, stream=False, response_format=builder._native_response_format(request))


def _request_record(request) -> dict:
    body = _body(request)
    return dict(operation=request.operation, invocation_id=request.invocation_id, body_sha256=_sha(body),
                user_packet=request.messages[1].content, request=body)


def prepare_experiment() -> PreparedExperiment:
    for path, digest in ((MANIFEST_PATH, MANIFEST_SHA256), (PROMPT_PATH, PROMPT_FILE_SHA256)):
        _require(shared._sha256(path) == digest, "retained_probe_input_changed")
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    _require(candidate.adapter_kind == "groq" and candidate.model == GROQ_QWEN_MODEL_ID
        and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
        and candidate.reasoning_effort == "none" and candidate.structured_mode == "native"
        and candidate.campaign_data_eligible is False, "retained_probe_target_invalid")
    document = PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    _require(front is not None, "retained_probe_prompt_invalid")
    prompt = document[front.end():].strip()
    _require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA256 and profile.VERSION == PROTOCOL,
             "retained_probe_prompt_invalid")
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=GROQ_QWEN_MODEL_ID)
    scene = SceneState(location="Galeria")
    case = dict(case_id=CASE_ID, origin="agent_authored_synthetic_case", synthetic_only=True,
                scene=scene.model_dump(mode="json"), turns=[dict(turn_key=k, player_input=p) for k,p in zip(TURN_KEYS,PLAYER_INPUTS)])
    batch = "00000000-0000-0000-0000-000000000000"
    snapshot = SourceContextSnapshot(origin=create_source_context_origin(batch, scene), current_turn=0,
        state_revision=0, sources=(), selected_turn_ids=(), omitted_turn_ids=())
    capsule = create_source_turn_capsule(snapshot, operation_id=_operation(batch,0),
        created_at=datetime(2026,9,10,tzinfo=timezone.utc), player_input=PLAYER_INPUTS[0], preparation=DeclaredActionPreparation(),
        state={}, relationships={}, target=target, system_prompt=prompt, parameters=GenerationParameters(temperature=.65,max_output_tokens=768))
    template = _body(_request(capsule))
    schema = profile.NarrativeSourceProposal.model_json_schema()
    metadata = {**_scope(), "generation_parameters": copy.deepcopy(PARAMETERS), "evaluator": {**shared._evaluator_provenance(),"file":"scripts/evaluate_retained_source.py","sha256":shared._sha256(Path(__file__)),"version":EXPERIMENT_VERSION},
        "inputs": {"manifest": {"file": MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256": MANIFEST_SHA256},
            "prompt": {"file": PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(), "file_sha256": PROMPT_FILE_SHA256, "sha256": PROMPT_SHA256},
            "case": {"case_id":CASE_ID,"sha256":_sha(case),"data":case},
            "response_schema_sha256":_sha(schema), "provider_schema_sha256":_sha(_normalize_groq_strict_schema(schema)),
            "implementation":[{"file":f,"sha256":shared._sha256(PROJECT_ROOT/f)} for f in IMPLEMENTATION_FILES]},
        "source_policy":{"source_field":"n","question_is_source":False,"canonical_truth_confirmed":False,
            "normalization":profile.TEXT_NORMALIZATION,"user_character_limit":profile.MAX_CONTEXT_CHARACTERS,
            "replay":"fresh_store_no_gateway","second_user":"previous_committed_complete_source"},
        "first_request_template":{"is_live_request":False,"body_sha256":_sha(template),"request":template}}
    return PreparedExperiment(candidate,target,prompt,metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment, "retained_probe_prepared_invalid")
    current = prepare_experiment()
    _require(current.target == prepared.target and current.prompt == prepared.prompt
        and _same(asdict(current.candidate),asdict(prepared.candidate)) and _same(current.metadata,prepared.metadata),
        "retained_probe_prepared_drift")


class DispatchBudget:
    """Counter shared by the two one-use adapters, incremented by HTTPX's hook."""
    def __init__(self):
        self.calls = 0
        self.pacer = shared._CallPacer(60)
        self.pacer._last_call_started_at = self.pacer._clock()

    async def wait(self):
        await self.pacer.before_call(PROBE_KIND)

    def consume(self):
        _require(self.calls < MAX_CALLS, "retained_probe_http_limit")
        self.calls += 1
        self.pacer._last_call_started_at = self.pacer._clock()


class RetainedObservationAdapter(BudgetObservationAdapter):
    """Known-key filtering precedes metadata parsing and structured return."""
    def __init__(self, *, prepared, request, api_key, budget, transport=None):
        super().__init__(base_url=GROQ_OFFICIAL_BASE_URL, capability_set=shared._capabilities(prepared.candidate,prepared.target),
            api_key=api_key, reasoning_effort="none", transport=transport)
        self.approved = _request_record(request)
        self.budget = budget
        self.http_sent = False
        self.credential_echo_blocked = False
        self.capture = {}

    def _contains_key(self,value):
        secret = self._api_key.get_secret_value().strip()
        if isinstance(value,str):
            return bool(secret and secret in value)
        if isinstance(value,dict):
            return any(self._contains_key(k) or self._contains_key(v) for k,v in value.items())
        if isinstance(value,(list,tuple)):
            return any(self._contains_key(v) for v in value)
        return False

    def _reject_echo(self,value):
        if self._contains_key(value):
            self.credential_echo_blocked = True
            self._observation = _unavailable_observation()
            self.capture.clear()
            raise ValueError("retained_probe_credential_echo_blocked")

    def _external_id(self,response):
        value = BudgetObservationAdapter._external_id(response)
        return None if self._contains_key(value) else value

    def _effective_model(self,payload):
        return GROQ_QWEN_MODEL_ID if payload.get("model") == GROQ_QWEN_MODEL_ID else None

    def _observe_metadata(self,payload):
        self._reject_echo(payload)
        return super()._observe_metadata(payload)

    def _observe_error_body(self,body):
        self._reject_echo(body.decode("utf-8", errors="replace"))
        return super()._observe_error_body(body)

    async def _observe_response(self,response):
        self._reject_echo(dict(response.headers))
        await super()._observe_response(response)

    def _payload(self,request,*,stream,response_format):
        payload = GroqAdapter._payload(self,request,stream=stream,response_format=response_format)
        _require(not stream and not self._dispatch_started and _same(_request_record(request),self.approved)
                 and _sha(payload)==self.approved["body_sha256"], "retained_probe_request_changed")
        self._dispatch_started = True
        return payload

    async def _dispatch(self,request):
        _require(not self.http_sent and request.method == "POST"
            and str(request.url) == GROQ_OFFICIAL_BASE_URL+"/chat/completions"
            and _sha(json.loads(request.content)) == self.approved["body_sha256"], "retained_probe_http_request_invalid")
        self.budget.consume()
        self.http_sent = True
        self.capture["http_started_at"] = utc_now().isoformat()

    def _new_client(self):
        client = super()._new_client()
        client.event_hooks["request"].append(self._dispatch)
        return client

    async def generate_structured(self,request):
        try:
            result = await super().generate_structured(request)
        except LLMInvocationError as exc:
            # The upstream normalizer is already bounded. Refuse any known-key
            # echo again before its evidence can enter the application audit.
            _require(not self.credential_echo_blocked,"retained_probe_credential_echo_blocked")
            self._reject_echo(exc.error.model_dump(mode="json"))
            self.capture["llm_error"] = shared._normalized_error_payload(exc.error)
            self.capture["evidence"] = shared._evidence_payload(exc.error.evidence)
            raise
        self._reject_echo(result.model_dump(mode="json"))
        evidence = shared._evidence_payload(result.evidence)
        _require(_route_status(evidence,request.target,request.invocation_id)=="verified", "retained_probe_route_invalid")
        value = profile.NarrativeSourceProposal.model_validate(result.value.model_dump(mode="json"))
        self.capture.update(evidence=evidence,response_structure=value.model_dump(mode="json",by_alias=True))
        return result


class _ClosingConnection:
    def __init__(self,connection):
        self.connection=connection
    def __enter__(self):
        return self.connection.__enter__()
    def __exit__(self,*args):
        try:
            return self.connection.__exit__(*args)
        finally:
            self.connection.close()


class ProbePersistence(SQLitePersistence):
    """Close each inherited context's handle so sealed copies are removable on Windows."""
    def _connect(self):
        return _ClosingConnection(super()._connect())


class NoCallGateway:
    async def generate_structured(self,request):
        raise AssertionError("retained_probe_replay_dispatched")


async def _no_chunk(_text):
    # Streamed text is provisional; only the completed envelope is an artifact.
    return None


def _result_record(result):
    return {"status":result.status,"operation_id":result.operation_id,"turn_id":result.turn_id,"turn_number":result.turn_number,
        "error":copy.deepcopy(result.error),"narrative":result.narrative.model_dump(mode="json") if result.narrative else None,
        "envelope":result.envelope.model_dump(mode="json") if result.envelope else None}


async def _forbid_replay_chunk(_text):
    raise AssertionError("retained_probe_replay_chunk")

async def _replay(store,batch,operation):
    return await execute_retained_source_turn(session_id=batch,operation_id=operation,store=store,gateway=NoCallGateway(),
        deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=_forbid_replay_chunk)


def _seal_database(source,destination):
    _require(not destination.exists(), "retained_probe_database_exists")
    connection = sqlite3.connect(source.resolve().as_uri()+"?mode=ro",uri=True)
    target = sqlite3.connect(destination)
    try:
        connection.backup(target)
        target.execute("PRAGMA journal_mode=DELETE")
    finally:
        target.close()
        connection.close()


async def evaluate_probe(prepared, *, api_key, batch_id, run_directory, records=None, on_record=None):
    _batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip()),"retained_probe_credential_invalid")
    directory = Path(run_directory)
    _require(directory.resolve()==run_path(batch_id).resolve(),"retained_probe_output_invalid")
    directory.mkdir(parents=True,exist_ok=False)
    rows = records if records is not None else []
    _require(type(rows) is list and not rows,"retained_probe_records_invalid")
    store = ProbePersistence(directory/"working.sqlite3")
    budget = DispatchBudget()
    status = "completed"
    started = utc_now().isoformat()
    await store.create_narrative_source_campaign(batch_id,initial_scene=SceneState(location="Galeria"),initial_state={},relationships={})
    try:
        for index,key in enumerate(TURN_KEYS):
            row = {"kind":"retained_source_turn","turn_key":key,"operation_id":_operation(batch_id,index),
                   "capsule":None,"request":None,"call_made":False,"schema_valid":False,"route_status":"unavailable",
                   "provider_observation":_unavailable_observation(),"response_structure":None,"evidence":None,"llm_error":None,
                   "credential_echo_blocked":False,"http_started_at":None,"result":None,"replay_verified":False,"local_error":None}
            adapter = None
            try:
                _check_prepared(prepared)
                capsule = await prepare_retained_source_turn(session_id=batch_id,operation_id=row["operation_id"],created_at=utc_now(),
                    player_input=PLAYER_INPUTS[index],preparation=DeclaredActionPreparation(),state={},relationships={},store=store,
                    target=prepared.target,system_prompt=prepared.prompt,parameters=GenerationParameters(temperature=.65,max_output_tokens=768))
                row["capsule"] = capsule.model_dump(mode="json")
                await budget.wait()
                _check_prepared(prepared)
                deadline = utc_now()+timedelta(seconds=60)
                request = _request(capsule,deadline)
                row["request"] = _request_record(request)
                adapter = RetainedObservationAdapter(prepared=prepared,request=request,api_key=api_key,budget=budget)
                result = await execute_retained_source_turn(session_id=batch_id,operation_id=row["operation_id"],store=store,
                    gateway=adapter,deadline=deadline,cancellation=CancellationToken(),on_chunk=_no_chunk)
                row["result"] = _result_record(result)
                if result.status == "completed":
                    replay = await _replay(ProbePersistence(store.db_path),batch_id,row["operation_id"])
                    _require(_same(_result_record(replay),row["result"]),"retained_probe_replay_invalid")
                    row["replay_verified"] = True
            except asyncio.CancelledError:
                status = "cancelled"
                row["local_error"] = "retained_probe_cancelled"
                # SQLite may have won the commit before cancellation surfaced.
                # Recover that terminal result without another H6 or delivery;
                # cancellation remains the run outcome and the next turn skips.
                committed = await store.load_turn_by_operation(batch_id,row["operation_id"])
                if committed is not None:
                    replay = await _replay(ProbePersistence(store.db_path),batch_id,row["operation_id"])
                    _require(replay.status == "completed","retained_probe_cancelled_commit_invalid")
                    row["result"] = _result_record(replay)
                    row["replay_verified"] = True
            except Exception:
                status = "local_error"
                row["local_error"] = "retained_probe_local_error"
            finally:
                if adapter is not None:
                    row.update({k:copy.deepcopy(adapter.capture.get(k)) for k in ("response_structure","evidence","llm_error","http_started_at")})
                    row["provider_observation"] = adapter.observation
                    row["call_made"] = adapter.http_sent
                    row["credential_echo_blocked"] = adapter.credential_echo_blocked
                    row["schema_valid"] = row["response_structure"] is not None
                    if row["evidence"] is not None:
                        row["route_status"] = _route_status(row["evidence"],prepared.target,row["request"]["invocation_id"])
                    adapter._reject_echo(row)
            rows.append(row)
            if on_record is not None:
                try:
                    on_record(copy.deepcopy(row))
                except Exception:
                    status = "local_error"
                    row["local_error"] = "retained_probe_local_error"
            if status != "completed" or row["result"] is None or row["result"]["status"] != "completed":
                break
    finally:
        for index in range(len(rows),2):
            rows.append({"kind":"retained_source_skip","turn_key":TURN_KEYS[index],"operation_id":_operation(batch_id,index),
                         "reason":status if status != "completed" else "previous_operational_failure"})
        _seal_database(store.db_path,directory/"retained-source.sqlite3")
        document = {"metadata":copy.deepcopy(prepared.metadata),"batch_id":batch_id,"started_at":started,"finished_at":utc_now().isoformat(),
                    "evaluation_status":status,"summary":summarize(rows,status),"artifacts":{
                        "database":{"file":"retained-source.sqlite3","sha256":shared._sha256(directory/"retained-source.sqlite3")},
                        "records":{"file":CANDIDATE_ID+".jsonl","sha256":None}}}
        raw = "".join(_json({"metadata":prepared.metadata,"batch_id":batch_id,"record":row})+"\n" for row in rows)
        (directory/(CANDIDATE_ID+".jsonl")).write_text(raw,encoding="utf-8")
        document["artifacts"]["records"]["sha256"] = shared._sha256(directory/(CANDIDATE_ID+".jsonl"))
        document["process_exit_code"] = document["summary"]["process_exit_code"]
        (directory/"summary.json").write_text(_json(document)+"\n",encoding="utf-8")
    return rows


def summarize(rows,status="completed"):
    _require(type(rows) is list and len(rows)==2 and status in ("completed","local_error","cancelled"))
    calls = []
    for index,row in enumerate(rows):
        _require(row["turn_key"]==TURN_KEYS[index])
        if row["kind"]=="retained_source_skip":
            _require(index==1 and row["reason"]==(status if status!="completed" else "previous_operational_failure"))
        else:
            _require(row["kind"]=="retained_source_turn" and not (index and rows[0]["kind"]=="retained_source_skip"))
            if index:
                _require(rows[0]["result"] is not None and rows[0]["result"]["status"]=="completed" and rows[0]["replay_verified"] is True)
            for field in ("call_made","schema_valid","replay_verified","credential_echo_blocked"):
                _require(type(row[field]) is bool)
            _require(row["schema_valid"] == (row["response_structure"] is not None))
            _require(not row["schema_valid"] or row["call_made"] and row["route_status"]=="verified")
            _require(not row["credential_echo_blocked"] or row["response_structure"] is row["evidence"] is None)
            calls.append(row)
    completed = sum(r["result"] is not None and r["result"]["status"]=="completed" for r in calls)
    if status=="completed":
        _require(all(r["local_error"] is None for r in calls))
        _require(len(calls)==2 or calls[-1]["result"] is not None and calls[-1]["result"]["status"]!="completed")
    else:
        _require(calls[-1]["local_error"] == ("retained_probe_cancelled" if status=="cancelled" else "retained_probe_local_error"))
    available_failure = any(r["llm_error"] is not None and r["llm_error"].get("category") in
        {"timeout","rate_limited","quota_exceeded","provider_unavailable"} for r in calls)
    success = completed==2 and all(r["replay_verified"] and r["call_made"] and r["schema_valid"] and r["route_status"]=="verified" for r in calls)
    exit_code = 130 if status=="cancelled" else 3 if status=="local_error" else 0 if success else 2 if available_failure else 1
    return {**_scope(),"turns_processed":len(calls),"turns_skipped":2-len(calls),"calls_made":sum(r["call_made"] for r in calls),
        "capsules_retained":sum(r["capsule"] is not None for r in calls),"schema_valid":sum(r["schema_valid"] for r in calls),
        "route_verified":sum(r["route_status"]=="verified" for r in calls),"turns_committed":completed,
        "replays_verified":sum(r["replay_verified"] for r in calls),"operational_probe_passed":success and status=="completed",
        "semantic_fidelity_review":{"status":"not_performed","approval":None},"process_exit_code":exit_code}


def _loads(data: bytes):
    _require(len(data)<=MAX_JSON_BYTES)
    def pairs(items):
        result={}
        for key,value in items:
            _require(key not in result)
            result[key]=value
        return result
    def invalid(_value):
        raise ValueError("retained_probe_json_invalid")
    return json.loads(data.decode("utf-8-sig"),object_pairs_hook=pairs,parse_constant=invalid)


def _read_json(path: Path):
    return _loads(Path(path).read_bytes())

def _expected(path,digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}",digest) is not None
        and shared._sha256(Path(path))==digest,"retained_probe_preflight_hash_invalid")
    expected=_read_json(Path(path))
    prepared=prepare_experiment()
    _require(_same(expected,prepared.metadata),"retained_probe_preflight_changed")
    return prepared


def _verify_audit(row,attempt,request):
    provenance=attempt["provenance"]
    usage=attempt["usage"]
    if row["evidence"] is None:
        _require(provenance is usage is None and row["llm_error"] is None)
        return
    _require(type(provenance) is dict and set(provenance)=={"invocations"}
        and type(usage) is dict and set(usage)=={"invocations"}
        and len(provenance["invocations"])==len(usage["invocations"])==1)
    identity=provenance["invocations"][0]
    measurement=usage["invocations"][0]
    evidence=InvocationEvidence.model_validate({"provenance":identity["provenance"],"usage":measurement["tokens"],"cost":measurement["cost"]})
    _require(_same(shared._evidence_payload(evidence),row["evidence"]))
    _require(evidence.provenance.invocation_id==request.invocation_id and evidence.provenance.requested_target==request.target)
    _require(set(identity)=={"invocation_id","operation","status","provenance","error"}
        and set(measurement)=={"invocation_id","operation","status","tokens","cost"})
    for key,value in (("invocation_id",request.invocation_id),("operation",INVOCATION_OPERATION)):
        _require(identity[key]==measurement[key]==value)
    if row["llm_error"] is None:
        _require(identity["status"]==measurement["status"]=="completed" and identity["error"] is None)
    else:
        error=NormalizedError.model_validate({**row["llm_error"],"invocation_id":request.invocation_id,"target":request.target,
            "evidence":evidence})
        _require(_same(shared._normalized_error_payload(error),row["llm_error"]))
        _require(identity["status"]==measurement["status"]=="failed"
            and identity["error"]=={"category":error.category.value,"code":"source_turn_provider_failure"})
    # The product audit intentionally omits external IDs/HTTP/error prose.
    # Those fields are only checked against the bounded observer when present.
    for key in ("input_tokens","output_tokens","total_tokens"):
        observed=row["provider_observation"]["usage"][key]
        value=getattr(evidence.usage,key)
        _require(observed is None or value is None or observed==value)


async def _verify_database(database,prepared,batch,rows,summary):
    store=ProbePersistence(database)
    snapshot=await store.read_source_context_snapshot(batch)
    _require(snapshot.current_turn==summary["turns_committed"] and snapshot.state_revision==snapshot.current_turn)
    _require(_same(snapshot.canonical_scene.model_dump(mode="json"),SceneState(location="Galeria").model_dump(mode="json")))
    all_attempts=await store.list_attempts(batch)
    expected_operations=set()
    committed=[]
    for index,row in enumerate(rows):
        _require(row["operation_id"]==_operation(batch,index))
        if row["kind"]=="retained_source_skip":
            _require(set(row)=={"kind","turn_key","operation_id","reason"})
            continue
        _require(set(row)=={"kind","turn_key","operation_id","capsule","request","call_made","schema_valid","route_status",
            "provider_observation","response_structure","evidence","llm_error","credential_echo_blocked","http_started_at",
            "result","replay_verified","local_error"})
        _validate_observation_snapshot(row)
        capsule=await store.load_source_preparation(batch,row["operation_id"])
        if row["capsule"] is None:
            _require(capsule is None and row["request"] is None and not row["call_made"] and row["result"] is None)
            continue
        from api.narrative_source_capsule import source_preparation_operation_id
        expected_operations.add(source_preparation_operation_id(batch,row["operation_id"]))
        _require(capsule is not None and _same(capsule.model_dump(mode="json"),row["capsule"]))
        capsule=validate_source_turn_capsule(row["capsule"],session_id=batch,operation_id=row["operation_id"])
        _require(capsule.player_input==PLAYER_INPUTS[index] and type(capsule.preparation) is DeclaredActionPreparation
            and capsule.target==prepared.target and capsule.system_prompt==prepared.prompt
            and capsule.parameters==GenerationParameters(temperature=.65,max_output_tokens=768)
            and capsule.state==capsule.relationships=={} and capsule.player_aliases==capsule.npc_aliases==()
            and capsule.chronicle_name=="")
        _require(capsule.snapshot.current_turn==index and capsule.snapshot.state_revision==index)
        _require(_same([v.model_dump(mode="json") for v in capsule.snapshot.sources],committed))
        request=_request(capsule)
        if row["request"] is not None:
            _require(_same(row["request"],_request_record(request)))
        else:
            _require(not row["call_made"] and row["result"] is None and row["local_error"] is not None)
        if row["evidence"] is not None:
            _require(row["route_status"]==_route_status(row["evidence"],prepared.target,request.invocation_id))
        else:
            _require(row["route_status"]=="unavailable")
        _require(not row["call_made"] or row["request"] is not None)
        if row["call_made"] and not row["credential_echo_blocked"]:
            _require(type(row["http_started_at"]) is str and datetime.fromisoformat(row["http_started_at"]).tzinfo is not None)
        proposal=None
        policy_error=None
        projection=None
        if row["response_structure"] is not None:
            proposal=profile.NarrativeSourceProposal.model_validate(row["response_structure"])
            _require(_same(proposal.model_dump(mode="json",by_alias=True),row["response_structure"]))
            try:
                projection=profile.create_source_projection(proposal,source_id="source-"+request.invocation_id,
                    session_id=batch,turn_id=capsule.draft.turn_id,invocation_id=request.invocation_id,
                    current_scene=capsule.canonical_scene,facts=capsule.draft.facts,player_input=capsule.player_input)
            except (ValueError,TypeError) as exc:
                policy_error=getattr(exc,"code",None)
                _require(type(policy_error) is str)
        attempt=await store.load_attempt_by_operation(batch,row["operation_id"])
        if attempt is not None:
            expected_operations.add(row["operation_id"])
            _require(attempt["attempt_id"]==capsule.draft.attempt_id and attempt["partial_narrative"]=="")
            _verify_audit(row,attempt,request)
        else:
            _require(row["evidence"] is None and row["llm_error"] is None)
        result=row["result"]
        if result is None:
            _require(row["local_error"] is not None)
            _require(attempt is None or attempt["status"] in ("failed","cancelled","timeout"))
            continue
        _require(attempt is not None and result["status"]==attempt["status"]
            and result["operation_id"]==capsule.operation_id and result["turn_id"]==capsule.draft.turn_id
            and result["turn_number"]==index+1)
        if result["status"]=="completed":
            _require(projection is not None and row["schema_valid"] and row["route_status"]=="verified")
            _require(_same(result["envelope"]["projection"],projection.model_dump(mode="json")))
            replay=await _replay(ProbePersistence(database),batch,capsule.operation_id)
            _require(row["replay_verified"] and _same(_result_record(replay),result))
            committed.append(result["envelope"])
        else:
            _require(result["narrative"] is result["envelope"] is None and not row["replay_verified"])
            _require(_same(result["error"],attempt["error"]))
            _require(set(result["error"])=={"code","stage"} and result["error"]["stage"] in ("preflight","generation","policy","admission","delivery","commit"))
            if policy_error is not None:
                _require(result["error"]["code"]==policy_error)
            elif proposal is not None:
                _require(result["error"]["code"] in ("source_turn_policy_failed","source_turn_admission_failed","source_turn_commit_failed","source_turn_delivery_failed"))
    _require({a["operation_id"] for a in all_attempts}==expected_operations)
    _require(all(a["status"]!="pending" for a in all_attempts))


def verify_artifacts(summary_path,expected_preflight,batch_id,*,expected_preflight_sha256):
    """Validate a disposable copy; no SQLite connection or migration on originals."""
    _batch(batch_id)
    prepared=_expected(expected_preflight,expected_preflight_sha256)
    path=Path(summary_path)
    _require(path.resolve()==(run_path(batch_id)/"summary.json").resolve() and not path.is_symlink())
    directory=path.parent
    document=_read_json(path)
    _require(set(document)=={"metadata","batch_id","started_at","finished_at","evaluation_status","summary","artifacts","process_exit_code"})
    _require(_same(document["metadata"],prepared.metadata) and document["batch_id"]==batch_id)
    start,end=(datetime.fromisoformat(document[k]) for k in ("started_at","finished_at"))
    _require(start.tzinfo is not None and end.tzinfo is not None and end>=start)
    _require(set(document["artifacts"])=={"database","records"})
    artifacts={}
    for kind,name,limit in (("database","retained-source.sqlite3",MAX_DB_BYTES),("records",CANDIDATE_ID+".jsonl",MAX_JSON_BYTES)):
        entry=document["artifacts"][kind]
        artifact=directory/name
        _require(type(entry) is dict and set(entry)=={"file","sha256"} and entry["file"]==name and not artifact.is_symlink()
                 and artifact.resolve().parent==directory.resolve() and artifact.stat().st_size<=limit)
        _require(shared._sha256(artifact)==entry["sha256"])
        artifacts[kind]=artifact
    lines=artifacts["records"].read_text(encoding="utf-8").splitlines()
    _require(len(lines)==2)
    rows=[]
    for line in lines:
        item=_loads(line.encode("utf-8"))
        _require(set(item)=={"metadata","batch_id","record"} and _same(item["metadata"],prepared.metadata) and item["batch_id"]==batch_id)
        rows.append(item["record"])
    recomputed=summarize(rows,document["evaluation_status"])
    _require(_same(recomputed,document["summary"]) and type(document["process_exit_code"]) is int
             and document["process_exit_code"]==recomputed["process_exit_code"])
    originals={p:shared._sha256(p) for p in (path,*artifacts.values())}
    with tempfile.TemporaryDirectory(prefix="storyteller-retained-verify-") as temporary:
        copy_path=Path(temporary)/"copy.sqlite3"
        copy_path.write_bytes(artifacts["database"].read_bytes())
        connection=sqlite3.connect(copy_path.resolve().as_uri()+"?mode=ro",uri=True)
        try:
            connection.execute("PRAGMA query_only=ON")
            _require(connection.execute("PRAGMA integrity_check").fetchone()==("ok",))
            _require(connection.execute("PRAGMA foreign_key_check").fetchall()==[])
            _require(connection.execute("SELECT session_id FROM campaigns").fetchall()==[(batch_id,)])
            for table in ("memory_candidates","episodic_memories","consolidations","legacy_imports"):
                _require(connection.execute("SELECT count(*) FROM "+table).fetchone()==(0,))
        finally:
            connection.close()
        asyncio.run(_verify_database(copy_path,prepared,batch_id,rows,recomputed))
    _require(all(shared._sha256(p)==digest for p,digest in originals.items()))
    return {"verified":True,"summary_path":str(path.resolve()),"process_exit_code":recomputed["process_exit_code"],"batch_id":batch_id}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Two new synthetic retained-source turns; no retry or imported campaign.")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight",action="store_true")
    mode.add_argument("--live",action="store_true")
    mode.add_argument("--verify-artifacts",type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight",type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env",choices=(KEY_ENV,),default=KEY_ENV)
    parser.add_argument("--allow-synthetic-only",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.preflight:
            _require(args.batch_id is None and args.expected_preflight is None and args.expected_preflight_sha256 is None
                     and not args.allow_synthetic_only)
            print(_json(prepare_experiment().metadata))
            return 0
        _batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts is not None:
            _require(not args.allow_synthetic_only)
            print(_json(verify_artifacts(args.verify_artifacts,args.expected_preflight,args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256)))
            return 0
        _require(args.allow_synthetic_only)
        prepared=_expected(args.expected_preflight,args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists(),"retained_probe_run_exists")
    except Exception:
        print("retained_probe_preflight_or_verification_failed",file=sys.stderr)
        return 3
    key=SecretStr(os.environ.get(KEY_ENV,"").strip())
    if not key.get_secret_value():
        print("retained_probe_credential_missing",file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_probe(prepared,api_key=key,batch_id=args.batch_id,run_directory=run_path(args.batch_id)))
        document=_read_json(run_path(args.batch_id)/"summary.json")
        code=document["process_exit_code"]
        print(_json({"summary_path":str((run_path(args.batch_id)/"summary.json").resolve()),"process_exit_code":code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("retained_probe_local_failure",file=sys.stderr)
        return 3
    finally:
        key=None


if __name__ == "__main__":
    raise SystemExit(main())
