"""Pure generation diagnostic from two independent authored textual sources.

No campaign, SQLite, commit or replay is performed. Authorship IDs are fixture
identities, not provider invocations. Verification establishes local consistency
of frozen requests, typed observations and gates, never external authentication.
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
import sys
from uuid import NAMESPACE_URL, UUID, uuid5

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr
from api import narrative_source_profile as profile
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from api.llm.contract import (
    InvocationEvidence, NormalizedError, LLMInvocationError, CancellationToken,
    GenerationParameters, LLMMessage, StructuredGenerationRequest, MessageRole, LLMTarget, utc_now,
)
from scripts import evaluate_progressing_source as observer
from scripts.evaluate_progressing_source import RetainedObservationAdapter
from scripts.evaluate_narrator_source import _route_status, _validate_observation_snapshot
from scripts.narrator_record_budget_observer import _unavailable_observation

shared = observer.shared
_json, _sha, _same, _loads, _read_json = observer._json, observer._sha, observer._same, observer._loads, observer._read_json
_body, _request_record = observer._body, observer._request_record
PROBE_KIND = "source_context_probe"
EXPERIMENT_VERSION = "source-context-observation-v1"
PROTOCOL = profile.VERSION
CANDIDATE_ID = observer.CANDIDATE_ID
GROQ_QWEN_MODEL_ID = observer.GROQ_QWEN_MODEL_ID
TARGET_PROFILE = observer.TARGET_PROFILE
KEY_ENV = "STORYTELLER_CONTEXT_GROQ_KEY"
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
CORPUS_PATH = PROJECT_ROOT / "evals/narrator/source_context_cases_v1.json"
CORPUS_SHA256 = "372cac22b21ae1df8bd5572c0d498c72bcc51fa65f5c2091d852e263c78a5524"
OBSERVER_SHA256 = "8adc2bde0e7bc86063e2c516356279f7bec98fdc1c0bd9fc3be4ae3d4ca19f57"
CONDITIONS = ("steady", "event_started")
PARAMETERS = copy.deepcopy(observer.PARAMETERS)
MAX_CALLS = 2
MAX_JSON_BYTES = observer.MAX_JSON_BYTES
SESSION_ID = "fixture-session-" + str(uuid5(NAMESPACE_URL, "source-context-authored-gallery-v1"))
SOURCE_ID = "fixture-source-" + str(uuid5(NAMESPACE_URL, "source-context-authored-source-v1"))
SOURCE_TURN = "fixture-turn-" + str(uuid5(NAMESPACE_URL, "source-context-authored-turn-v1"))
AUTHORING_ID = "authoring-" + str(uuid5(NAMESPACE_URL, "source-context-authored-v1"))
OUTPUT_TURN = str(uuid5(NAMESPACE_URL, "source-context-continuation-v1"))
OPERATION = "evaluation.source_context"
IMPLEMENTATION_FILES = (
    "scripts/evaluate_source_context.py", "scripts/evaluate_progressing_source.py",
    "scripts/evaluate_narrator_source.py", "scripts/evaluate_narrator_models.py",
    "scripts/narrator_record_budget_observer.py", "api/narrative_source_profile.py",
    "api/narrative_grounding.py", "api/scene_service.py", "api/scene_director_service.py",
    "api/turn_models.py", "api/llm/contract.py", "api/llm/adapters/groq.py",
    "api/llm/adapters/openai_compatible.py",
)
CONTENT_ERRORS = frozenset({"invalid_structured_output", "content_rejected"})
UTC_TOLERANCE_SECONDS = .01


class DispatchBudget(observer.DispatchBudget):
    async def wait(self):
        await self.pacer.before_call(PROBE_KIND)


STAGES = frozenset({"preflight", "transport", "policy", "projection", "record"})


def _require(ok, code="source_context_artifact_invalid"):
    if not ok:
        raise ValueError(code)


def _batch(value):
    _require(type(value) is str and str(UUID(value)) == value, "source_context_batch_invalid")
    return value


def run_path(batch_id):
    return OUTPUT_ROOT / ("source-context-" + _batch(batch_id))


def _scope():
    return dict(purpose=PROBE_KIND, probe_kind=PROBE_KIND, experiment_version=EXPERIMENT_VERSION,
        protocol=PROTOCOL, selected_candidate_id=CANDIDATE_ID, synthetic_only=True, campaign_data_eligible=False,
        cap_001_approved=False, runtime_default_eligible=False, semantic_not_evaluated=True, max_calls=2)


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    prompt: str
    corpus: dict
    metadata: dict


def authored_projection(corpus, index):
    # Shared fixture IDs intentionally avoid encoding the condition in USER.
    return profile.create_source_projection(
        {"n": corpus["conditions"][index]["source_text"], "q": corpus["source_question"]},
        source_id=SOURCE_ID, session_id=SESSION_ID, turn_id=SOURCE_TURN, invocation_id=AUTHORING_ID,
        current_scene=SceneState.model_validate(corpus["scene"]), facts=(), player_input=corpus["player_input"],
    )


def build_user_packet(prepared, index):
    _require(type(index) is int and index in (0, 1), "source_context_condition_invalid")
    packet = _json({"context": profile.build_source_context(session_id=SESSION_ID,
        current_scene=SceneState.model_validate(prepared.corpus["scene"]),
        attributed_sources=(authored_projection(prepared.corpus, index),)),
        "player_input": prepared.corpus["player_input"], "turn": OUTPUT_TURN, "server_facts": []})
    _require((len(packet)+3)//4 <= 2000, "source_context_user_budget_exceeded")
    return packet


def make_request(prepared, index, batch_id, *, deadline=None, cancellation=None):
    _batch(batch_id)
    return StructuredGenerationRequest(operation=OPERATION,
        invocation_id=str(uuid5(UUID(batch_id), f"source-context.{index}")), target=prepared.target,
        messages=(LLMMessage(role=MessageRole.SYSTEM, content=prepared.prompt),
                  LLMMessage(role=MessageRole.USER, content=build_user_packet(prepared, index))),
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        response_model=profile.NarrativeSourceProposal,
        deadline=deadline or datetime(2000, 1, 1, tzinfo=timezone.utc),
        cancellation=cancellation or CancellationToken())


def prepare_experiment():
    _require(shared._sha256(CORPUS_PATH) == CORPUS_SHA256
        and shared._sha256(Path(observer.__file__)) == OBSERVER_SHA256, "source_context_input_changed")
    for path, digest in ((observer.MANIFEST_PATH, observer.MANIFEST_SHA256),
                         (observer.PROMPT_PATH, observer.PROMPT_FILE_SHA256)):
        _require(shared._sha256(path) == digest, "source_context_input_changed")
    corpus = _read_json(CORPUS_PATH)
    _require(corpus["order"] == list(CONDITIONS)
        and [c["condition_id"] for c in corpus["conditions"]] == list(CONDITIONS)
        and corpus["source_origin"] == "authored_synthetic_fixture" and corpus["conditions_independent"] is True)
    candidate = shared.load_candidates(observer.MANIFEST_PATH)[CANDIDATE_ID]
    _require(candidate.adapter_kind == "groq" and candidate.model == GROQ_QWEN_MODEL_ID
        and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
        and candidate.reasoning_effort == "none" and candidate.structured_mode == "native"
        and candidate.campaign_data_eligible is False, "source_context_target_invalid")
    document = observer.PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    _require(front is not None)
    prompt = document[front.end():].strip()
    _require(hashlib.sha256(prompt.encode()).hexdigest() == observer.PROMPT_SHA256)
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=GROQ_QWEN_MODEL_ID)
    provisional = PreparedExperiment(candidate, target, prompt, corpus, {})
    frozen = []
    for index, condition in enumerate(CONDITIONS):
        request = make_request(provisional, index, "00000000-0000-0000-0000-000000000000")
        body = _body(request)
        frozen.append({"condition_id":condition, "request":body, "body_sha256":_sha(body),
            "user_packet":request.messages[1].content,
            "authored_source":{"origin":"authored_synthetic_fixture", "provider_evidence":None,
                "projection":authored_projection(corpus,index).model_dump(mode="json")}})
    schema = profile.NarrativeSourceProposal.model_json_schema()
    metadata = {**_scope(), "generation_parameters":copy.deepcopy(PARAMETERS), "conditions":list(CONDITIONS),
        "evaluator":{**shared._evaluator_provenance(), "file":"scripts/evaluate_source_context.py",
                     "sha256":shared._sha256(Path(__file__)), "version":EXPERIMENT_VERSION},
        "inputs":{"corpus":{"file":CORPUS_PATH.relative_to(PROJECT_ROOT).as_posix(), "sha256":CORPUS_SHA256},
            "manifest":{"file":observer.MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(),"sha256":observer.MANIFEST_SHA256},
            "prompt":{"file":observer.PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(),
                      "file_sha256":observer.PROMPT_FILE_SHA256,"sha256":observer.PROMPT_SHA256},
            "response_schema_sha256":_sha(schema),
            "provider_schema_sha256":_sha(observer._normalize_groq_strict_schema(schema)),
            "implementation":[{"file":f,"sha256":shared._sha256(PROJECT_ROOT/f)} for f in IMPLEMENTATION_FILES]},
        "source_policy":{"origin":"authored_synthetic_fixture","source_field":"n","question_is_source":False,
            "canonical_truth_confirmed":False,"application_commit":False,"replay":"not_applied",
            "normalization":profile.TEXT_NORMALIZATION,"conditions_independent":True,"user_estimated_token_limit":2000},
        "timing_policy":{"clock":"local_utc","tolerance_seconds":UTC_TOLERANCE_SECONDS,
            "monotonic_capture_available":False,"remote_arrival_measured":False},
        "frozen_requests":frozen}
    return PreparedExperiment(candidate,target,prompt,corpus,metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment, "source_context_prepared_invalid")
    current=prepare_experiment()
    _require(current.target==prepared.target and current.prompt==prepared.prompt
        and _same(asdict(current.candidate),asdict(prepared.candidate)) and _same(current.corpus,prepared.corpus)
        and _same(current.metadata,prepared.metadata), "source_context_prepared_drift")


def _expected(path,digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}",digest) is not None
        and shared._sha256(Path(path))==digest,"source_context_preflight_hash_invalid")
    prepared=prepare_experiment()
    _require(_same(_read_json(Path(path)),prepared.metadata),"source_context_preflight_changed")
    return prepared


def _project(prepared,index,batch,proposal):
    request=make_request(prepared,index,batch)
    return profile.create_source_projection(proposal, source_id="generated-"+request.invocation_id,
        session_id=SESSION_ID, turn_id=OUTPUT_TURN, invocation_id=request.invocation_id,
        current_scene=SceneState.model_validate(prepared.corpus["scene"]), facts=(),
        player_input=prepared.corpus["player_input"])


def _continue(row):
    return row["route_status"]=="verified" and row["outcome"] in ("accepted","schema_rejected","policy_rejected")


def _new_row(prepared,index,batch):
    return {"kind":"source_context_call","condition_id":CONDITIONS[index],
        "request":_request_record(make_request(prepared,index,batch)), "deadline_at":None,
        "authored_source":copy.deepcopy(prepared.metadata["frozen_requests"][index]["authored_source"]),
        "call_made":False,"schema_valid":False,"policy_valid":False,"projection_valid":False,
        "route_status":"unavailable","provider_observation":_unavailable_observation(),
        "response_structure":None,"output_projection":None,"evidence":None,"llm_error":None,
        "credential_echo_blocked":False,"http_started_at":None,"outcome":"local_error",
        "policy_error":None,"local_error":None}


async def evaluate_probe(prepared,*,api_key,batch_id,run_directory,records=None,on_record=None):
    _batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip()),"source_context_credential_invalid")
    _require(api_key.get_secret_value().strip() not in _json(prepared.metadata),"source_context_credential_invalid")
    directory=Path(run_directory)
    _require(directory.resolve()==run_path(batch_id).resolve(),"source_context_output_invalid")
    rows=records if records is not None else []
    _require(type(rows) is list and not rows,"source_context_records_invalid")
    directory.mkdir(parents=True,exist_ok=False)
    started=utc_now().isoformat()
    budget=DispatchBudget()
    status="completed"
    for index in range(MAX_CALLS):
        row=_new_row(prepared,index,batch_id)
        adapter=None
        stage="preflight"
        try:
            _check_prepared(prepared)
            await budget.wait()
            _check_prepared(prepared)
            deadline=utc_now()+timedelta(seconds=60)
            row["deadline_at"]=deadline.isoformat()
            request=make_request(prepared,index,batch_id,deadline=deadline)
            _require(_same(_request_record(request),row["request"]))
            stage="transport"
            adapter=RetainedObservationAdapter(prepared=prepared,request=request,api_key=api_key,budget=budget)
            result=await adapter.generate_structured(request)
            stage="policy"
            proposal=profile.validate_source_proposal(result.value,current_scene=SceneState.model_validate(prepared.corpus["scene"]),
                facts=(),player_input=prepared.corpus["player_input"])
            row["policy_valid"]=True
            stage="projection"
            row["output_projection"]=_project(prepared,index,batch_id,proposal).model_dump(mode="json")
            row["projection_valid"]=True
            row["outcome"]="accepted"
        except SceneProposalError as exc:
            row["policy_error"]=exc.code
            row["outcome"]="policy_rejected"
        except LLMInvocationError as exc:
            row["outcome"]="schema_rejected" if exc.error.category.value in CONTENT_ERRORS else "provider_failed"
        except asyncio.CancelledError:
            status="cancelled"
            row["outcome"]="cancelled"
            row["local_error"]={"code":"source_context_cancelled","stage":stage}
        except Exception:
            status="local_error"
            row["outcome"]="local_error"
            row["local_error"]={"code":"source_context_local_error","stage":stage}
        finally:
            if adapter is not None:
                row.update({key:copy.deepcopy(adapter.capture.get(key)) for key in
                            ("response_structure","evidence","llm_error","http_started_at")})
                row["provider_observation"]=adapter.observation
                row["call_made"]=adapter.http_sent
                row["credential_echo_blocked"]=adapter.credential_echo_blocked
                row["schema_valid"]=row["response_structure"] is not None
                row["route_status"]=_route_status(row["evidence"],prepared.target,row["request"]["invocation_id"])
        rows.append(row)
        if on_record is not None:
            try:
                on_record(copy.deepcopy(row))
            except Exception:
                status="local_error"
                row["outcome"]="local_error"
                row["local_error"]={"code":"source_context_local_error","stage":"record"}
        if status!="completed" or not _continue(row):
            break
    for index in range(len(rows),MAX_CALLS):
        rows.append({"kind":"source_context_skip","condition_id":CONDITIONS[index],
                     "reason":status if status!="completed" else "previous_operational_failure"})
    _require(budget.calls==sum(row.get("call_made",False) for row in rows))
    summary=summarize(rows,status)
    raw="".join(_json({"metadata":prepared.metadata,"batch_id":batch_id,"record":row})+"\n" for row in rows)
    raw_path=directory/(CANDIDATE_ID+".jsonl")
    raw_path.write_text(raw,encoding="utf-8")
    document={"metadata":copy.deepcopy(prepared.metadata),"batch_id":batch_id,"started_at":started,
        "finished_at":utc_now().isoformat(),"evaluation_status":status,"summary":summary,
        "artifacts":{"records":{"file":raw_path.name,"sha256":shared._sha256(raw_path)}},
        "process_exit_code":summary["process_exit_code"]}
    (directory/"summary.json").write_text(_json(document)+"\n",encoding="utf-8")
    return rows


def summarize(rows,status="completed"):
    _require(type(rows) is list and len(rows)==2 and status in ("completed","local_error","cancelled"))
    calls=[]
    for index,row in enumerate(rows):
        _require(row["condition_id"]==CONDITIONS[index])
        if row["kind"]=="source_context_skip":
            _require(index==1 and not _continue(rows[0]) and row["reason"]==
                (status if status!="completed" else "previous_operational_failure"))
        else:
            _require(row["kind"]=="source_context_call" and (not index or _continue(rows[0])))
            for field in ("call_made","schema_valid","policy_valid","projection_valid","credential_echo_blocked"):
                _require(type(row[field]) is bool)
            calls.append(row)
    _require(bool(calls))
    if status=="completed":
        _require(all(r["local_error"] is None for r in calls))
        _require(len(calls)==2 or not _continue(calls[-1]))
    else:
        _require(calls[-1]["outcome"]==status and calls[-1]["local_error"] is not None)
    success=len(calls)==2 and all(r["outcome"]=="accepted" and r["route_status"]=="verified" for r in calls)
    availability=any((r["llm_error"] or {}).get("category") in
        {"rate_limited","quota_exceeded","timeout","provider_unavailable","transport_failure"} for r in calls)
    code=130 if status=="cancelled" else 3 if status=="local_error" else 0 if success else 2 if availability else 1
    return {**_scope(),"conditions_processed":len(calls),"conditions_skipped":2-len(calls),
        "calls_made":sum(r["call_made"] for r in calls),"schema_valid":sum(r["schema_valid"] for r in calls),
        "policy_valid":sum(r["policy_valid"] for r in calls),"projection_valid":sum(r["projection_valid"] for r in calls),
        "route_verified":sum(r["route_status"]=="verified" for r in calls),
        "operational_probe_passed":success and status=="completed",
        "semantic_fidelity_review":{"status":"not_performed","approval":None},
        "process_exit_code":code}


def _aware(value):
    _require(type(value) is str)
    parsed=datetime.fromisoformat(value)
    _require(parsed.tzinfo is not None)
    return parsed


def _verify_evidence(row,request):
    _validate_observation_snapshot(row)
    raw=row["evidence"]
    if raw is None:
        _require(row["llm_error"] is None and row["route_status"]=="unavailable")
        return
    provenance={key:raw[key] for key in ("invocation_id","requested_target","adapter","effective_model",
                                       "effective_provider","started_at","finished_at")}
    evidence=InvocationEvidence.model_validate({"provenance":provenance,"usage":raw["usage"],"cost":raw["cost"]})
    _require(_same(shared._evidence_payload(evidence),raw))
    _require(evidence.provenance.invocation_id==request.invocation_id and evidence.provenance.requested_target==request.target)
    _require(row["route_status"]==_route_status(raw,request.target,request.invocation_id))
    if row["llm_error"] is not None:
        error=NormalizedError.model_validate({**row["llm_error"],"invocation_id":request.invocation_id,
            "target":request.target,"evidence":evidence})
        _require(_same(shared._normalized_error_payload(error),row["llm_error"]))
    for key in ("input_tokens","output_tokens","total_tokens"):
        observed=row["provider_observation"]["usage"][key]
        measured=getattr(evidence.usage,key)
        _require(observed is None or measured is None or observed==measured)


def _verify_row(prepared,index,batch,row):
    if row["kind"]=="source_context_skip":
        _require(set(row)=={"kind","condition_id","reason"})
        return
    expected=_new_row(prepared,index,batch)
    _require(set(row)==set(expected) and row["kind"]==expected["kind"])
    _require(_same(row["request"],expected["request"]) and _same(row["authored_source"],expected["authored_source"]))
    request=make_request(prepared,index,batch)
    _verify_evidence(row,request)
    _require(row["schema_valid"]==(row["response_structure"] is not None))
    _require(row["projection_valid"]==(row["output_projection"] is not None))
    local=row["local_error"]
    stage=None
    if local is not None:
        _require(type(local) is dict and set(local)=={"code","stage"} and local["stage"] in STAGES)
        _require(local["code"]==("source_context_cancelled" if row["outcome"]=="cancelled" else "source_context_local_error"))
        _require(row["outcome"] in ("local_error","cancelled"))
        stage=local["stage"]
    if stage=="preflight":
        _require(not row["call_made"] and not row["credential_echo_blocked"]
            and row["response_structure"] is row["evidence"] is row["llm_error"] is row["http_started_at"] is None
            and row["output_projection"] is None and row["policy_error"] is None
            and not row["policy_valid"] and not row["projection_valid"]
            and _same(row["provider_observation"],_unavailable_observation()))
    if row["deadline_at"] is None:
        _require(not row["call_made"] and local is not None and stage=="preflight")
    else:
        deadline=_aware(row["deadline_at"])
        if row["http_started_at"] is not None:
            _require(deadline-timedelta(seconds=60)<=_aware(row["http_started_at"])<=deadline)
    if not row["call_made"]:
        _require(row["http_started_at"] is None and not row["schema_valid"] and row["output_projection"] is None)
    elif not row["credential_echo_blocked"]:
        _require(row["http_started_at"] is not None)
    if row["credential_echo_blocked"]:
        _require(local is not None and stage=="transport" and row["outcome"]=="local_error")
        _require(row["response_structure"] is row["evidence"] is row["llm_error"] is row["output_projection"] is row["http_started_at"] is None)
        _require(not row["policy_valid"] and not row["projection_valid"]
                 and _same(row["provider_observation"],_unavailable_observation()))
    proposal=None
    policy_error=None
    if row["schema_valid"]:
        _require(row["call_made"] and row["route_status"]=="verified" and row["llm_error"] is None)
        proposal=profile.NarrativeSourceProposal.model_validate(row["response_structure"])
        _require(_same(proposal.model_dump(mode="json",by_alias=True),row["response_structure"]))
        try:
            profile.validate_source_proposal(proposal,current_scene=SceneState.model_validate(prepared.corpus["scene"]),
                facts=(),player_input=prepared.corpus["player_input"])
        except SceneProposalError as exc:
            policy_error=exc.code
    _require(row["policy_error"]==policy_error)
    if row["policy_valid"]:
        _require(proposal is not None and policy_error is None)
    if row["projection_valid"]:
        _require(row["policy_valid"] and _same(row["output_projection"],_project(prepared,index,batch,proposal).model_dump(mode="json")))
    if local is not None:
        if stage in ("preflight","transport"):
            _require(not row["policy_valid"] and not row["projection_valid"])
        elif stage=="policy":
            _require(proposal is not None and not row["policy_valid"] and not row["projection_valid"])
        elif stage=="projection":
            _require(row["policy_valid"] and not row["projection_valid"])
        return
    if row["outcome"]=="accepted":
        _require(row["call_made"] and row["schema_valid"] and row["policy_valid"] and row["projection_valid"])
    elif row["outcome"]=="policy_rejected":
        _require(proposal is not None and policy_error is not None and not row["policy_valid"] and not row["projection_valid"])
    else:
        _require(row["outcome"] in ("schema_rejected","provider_failed") and proposal is None
            and not row["policy_valid"] and not row["projection_valid"] and row["llm_error"] is not None)
        content=row["llm_error"]["category"] in CONTENT_ERRORS
        _require((row["outcome"]=="schema_rejected")==content)


def _verify_times(document,rows):
    # UTC is a local consistency check, not a persisted monotonic clock or wire capture.
    start,end=(_aware(document[k]) for k in ("started_at","finished_at"))
    tolerance=timedelta(seconds=UTC_TOLERANCE_SECONDS)
    last_http=None
    for row in rows:
        if row["kind"]=="source_context_skip":
            continue
        if row["deadline_at"] is not None:
            created=_aware(row["deadline_at"])-timedelta(seconds=60)
            _require(start<=created<=end)
            _require(created+tolerance>=start+timedelta(seconds=60))
            if last_http is not None:
                _require(created+tolerance>=last_http+timedelta(seconds=60))
        if row["evidence"] is not None:
            began,finished=(_aware(row["evidence"][k]) for k in ("started_at","finished_at"))
            _require(start<=began<=finished<=end and row["deadline_at"] is not None)
            _require(created<=began<=_aware(row["deadline_at"]))
        if row["http_started_at"] is not None:
            http=_aware(row["http_started_at"])
            _require(start<=http<=end and created<=http)
            if row["evidence"] is not None:
                _require(began<=http<=finished)
            last_http=http


def verify_artifacts(summary_path,expected_preflight,batch_id,*,expected_preflight_sha256):
    prepared=_expected(expected_preflight,expected_preflight_sha256)
    path=Path(summary_path)
    _require(path.resolve()==(run_path(batch_id)/"summary.json").resolve() and not path.is_symlink())
    before=shared._sha256(path)
    document=_read_json(path)
    _require(set(document)=={"metadata","batch_id","started_at","finished_at","evaluation_status","summary","artifacts","process_exit_code"})
    _require(_same(document["metadata"],prepared.metadata) and document["batch_id"]==batch_id)
    _require(_aware(document["finished_at"])>=_aware(document["started_at"]))
    _require(type(document["artifacts"]) is dict and set(document["artifacts"])=={"records"})
    entry=document["artifacts"]["records"]
    raw=path.parent/(CANDIDATE_ID+".jsonl")
    _require(type(entry) is dict and set(entry)=={"file","sha256"} and entry["file"]==raw.name
        and not raw.is_symlink() and raw.resolve().parent==path.parent.resolve() and raw.stat().st_size<=MAX_JSON_BYTES)
    _require(shared._sha256(raw)==entry["sha256"])
    lines=raw.read_text(encoding="utf-8").splitlines()
    _require(len(lines)==2)
    rows=[]
    for index,line in enumerate(lines):
        item=_loads(line.encode("utf-8"))
        _require(set(item)=={"metadata","batch_id","record"} and _same(item["metadata"],prepared.metadata) and item["batch_id"]==batch_id)
        _verify_row(prepared,index,batch_id,item["record"])
        rows.append(item["record"])
    _verify_times(document,rows)
    recomputed=summarize(rows,document["evaluation_status"])
    _require(_same(recomputed,document["summary"]) and type(document["process_exit_code"]) is int
        and document["process_exit_code"]==recomputed["process_exit_code"])
    _require(shared._sha256(path)==before and shared._sha256(raw)==entry["sha256"])
    return {"verified":True,"batch_id":batch_id,"summary_path":str(path.resolve()),
            "process_exit_code":recomputed["process_exit_code"]}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Independent authored-source conditions; no campaign or retry.")
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight",action="store_true")
    modes.add_argument("--live",action="store_true")
    modes.add_argument("--verify-artifacts",type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight",type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env",choices=(KEY_ENV,),default=KEY_ENV)
    parser.add_argument("--allow-synthetic-only",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.preflight:
            _require(args.batch_id is None and args.expected_preflight is None and args.expected_preflight_sha256 is None and not args.allow_synthetic_only)
            print(_json(prepare_experiment().metadata))
            return 0
        _batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts:
            _require(not args.allow_synthetic_only)
            print(_json(verify_artifacts(args.verify_artifacts,args.expected_preflight,args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256)))
            return 0
        _require(args.allow_synthetic_only)
        prepared=_expected(args.expected_preflight,args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists(),"source_context_run_exists")
    except Exception:
        print("source_context_preflight_or_verification_failed",file=sys.stderr)
        return 3
    key=SecretStr(os.environ.get(KEY_ENV,"").strip())
    if not key.get_secret_value():
        print("source_context_credential_missing",file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_probe(prepared,api_key=key,batch_id=args.batch_id,run_directory=run_path(args.batch_id)))
        code=_read_json(run_path(args.batch_id)/"summary.json")["process_exit_code"]
        print(_json({"summary_path":str((run_path(args.batch_id)/"summary.json").resolve()),"process_exit_code":code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("source_context_local_failure",file=sys.stderr)
        return 3
    finally:
        key=None


if __name__=="__main__":
    raise SystemExit(main())
