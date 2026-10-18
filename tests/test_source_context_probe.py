"""Independent-source diagnostic boundaries; HTTPX MockTransport only."""
import asyncio
import copy
from datetime import timedelta
import json
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from scripts import evaluate_source_context as probe
from api.persistence import SQLitePersistence
from tests.test_narrative_source_progression_admission import AUTHORED_CONTINUATION, AUTHORED_QUESTION

KEY="synthetic-source-context-key-never-retain"


def response(n=AUTHORED_CONTINUATION,q=AUTHORED_QUESTION,*,model=probe.GROQ_QWEN_MODEL_ID,finish="stop",extra=None):
    body={"model":model,"choices":[{"finish_reason":finish,"message":{"role":"assistant",
        "content":json.dumps({"n":n,"q":q},ensure_ascii=False)}}],
        "usage":{"prompt_tokens":100,"completion_tokens":80,"total_tokens":180}}
    body.update(extra or {})
    return httpx.Response(200,json=body)


@pytest.fixture
def harness(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,"OUTPUT_ROOT",tmp_path/"results")
    from api.llm import contract
    from api.llm.adapters import groq, openai_compatible
    real_now=probe.utc_now
    clock=[0.0]
    def simulated_now(): return real_now()+timedelta(seconds=clock[0])
    for module in (probe,probe.observer,contract,groq,openai_compatible):
        monkeypatch.setattr(module,"utc_now",simulated_now)
    original_pacer=probe.shared._CallPacer
    async def sleep(seconds): clock[0]+=seconds
    def pacer(seconds): return original_pacer(seconds,_clock=lambda:clock[0],_sleeper=sleep)
    monkeypatch.setattr(probe.shared,"_CallPacer",pacer)
    async def no_database(*args,**kwargs): pytest.fail("Pure diagnostic entered SQLite")
    monkeypatch.setattr(SQLitePersistence,"initialize",no_database)
    seen=[]
    replies=[response(),response()]
    def handler(request):
        seen.append(json.loads(request.content))
        return replies.pop(0)
    original=probe.RetainedObservationAdapter.__init__
    def init(self,**kwargs):
        return original(self,transport=httpx.MockTransport(handler),**kwargs)
    monkeypatch.setattr(probe.RetainedObservationAdapter,"__init__",init)
    return seen,replies


async def run(harness,**kwargs):
    prepared=probe.prepare_experiment()
    batch=str(uuid4())
    path=probe.run_path(batch)
    rows=await probe.evaluate_probe(prepared,api_key=SecretStr(KEY),batch_id=batch,run_directory=path,**kwargs)
    return prepared,batch,path,rows


def expected_file(prepared,path):
    target=path.parent/(path.name+"-preflight.json")
    target.write_text(probe._json(prepared.metadata),encoding="utf-8")
    return target,probe.shared._sha256(target)


def verify(prepared,batch,path):
    target,digest=expected_file(prepared,path)
    return probe.verify_artifacts(path/"summary.json",target,batch,expected_preflight_sha256=digest)


def rewrite(path,rows,status=None):
    doc=probe._read_json(path/"summary.json")
    if status: doc["evaluation_status"]=status
    raw="".join(probe._json({"metadata":doc["metadata"],"batch_id":doc["batch_id"],"record":row})+"\n" for row in rows)
    target=path/(probe.CANDIDATE_ID+".jsonl")
    target.write_text(raw,encoding="utf-8")
    doc["artifacts"]["records"]["sha256"]=probe.shared._sha256(target)
    # Recompute when the forged state is superficially allowed by summarize;
    # otherwise leave summary so the verifier still must refuse the artifact.
    try: doc["summary"]=probe.summarize(rows,doc["evaluation_status"])
    except ValueError: pass
    doc["process_exit_code"]=doc["summary"]["process_exit_code"]
    (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")


def test_preflight_binds_authored_sources_without_fake_provider_evidence_or_clock():
    a=probe.prepare_experiment(); b=probe.prepare_experiment()
    assert a.metadata==b.metadata
    assert a.metadata["source_policy"]["application_commit"] is False
    assert a.metadata["source_policy"]["replay"]=="not_applied"
    assert a.metadata["evaluator"]["file"]=="scripts/evaluate_source_context.py"
    packets=[]
    for index,frozen in enumerate(a.metadata["frozen_requests"]):
        assert frozen["authored_source"]["origin"]=="authored_synthetic_fixture"
        assert frozen["authored_source"]["provider_evidence"] is None
        source=frozen["authored_source"]["projection"]["source"]
        assert source["invocation_id"].startswith("authoring-") and source["source_id"].startswith("fixture-")
        packet=json.loads(frozen["user_packet"])
        assert packet["server_facts"]==[] and packet["player_input"]==a.corpus["player_input"]
        assert packet["context"]["attributed_sources"][0]["text"]==a.corpus["conditions"][index]["source_text"]
        assert a.corpus["source_question"] not in frozen["user_packet"]
        assert not any(label in frozen["user_packet"] for label in probe.CONDITIONS)
        assert frozen["request"]["messages"][0]["content"]==a.prompt
        assert frozen["body_sha256"]==probe._sha(frozen["request"])
        packets.append(packet)
    left,right=copy.deepcopy(packets)
    left["context"]["attributed_sources"]=right["context"]["attributed_sources"]
    assert left==right
    assert a.metadata["generation_parameters"]==probe.observer.PARAMETERS


@pytest.mark.asyncio
async def test_two_independent_calls_use_frozen_bodies_and_never_sqlite(harness):
    prepared,batch,path,rows=await run(harness)
    assert len(harness[0])==2
    assert all(row["outcome"]=="accepted" for row in rows)
    for index,row in enumerate(rows):
        assert row["request"]["request"]==harness[0][index]==prepared.metadata["frozen_requests"][index]["request"]
        assert row["response_structure"]=={"n":AUTHORED_CONTINUATION,"q":AUTHORED_QUESTION}
        assert row["output_projection"]["text"]==AUTHORED_CONTINUATION
        assert row["output_projection"]["assessment"]["decision"]=="source_only"
        assert row["output_projection"]["source"]["invocation_id"]==row["request"]["invocation_id"]
    assert AUTHORED_CONTINUATION not in rows[1]["request"]["user_packet"]
    assert set(p.name for p in path.iterdir())=={"summary.json",probe.CANDIDATE_ID+".jsonl"}
    before={p.name:probe.shared._sha256(p) for p in path.iterdir()}
    checked=verify(prepared,batch,path)
    assert checked["verified"] is True and checked["process_exit_code"]==0
    assert before=={p.name:probe.shared._sha256(p) for p in path.iterdir()}
    assert probe._read_json(path/"summary.json")["summary"]["semantic_fidelity_review"]=={"status":"not_performed","approval":None}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure",["policy","schema","length","429","401","route"])
async def test_content_may_continue_but_operational_failure_stops(harness,failure):
    if failure=="policy": harness[1][0]=response(q="Quem está aqui?")
    elif failure=="schema": harness[1][0]=response(n="curta")
    elif failure=="length": harness[1][0]=response(finish="length")
    elif failure in ("429","401"): harness[1][0]=httpx.Response(int(failure),json={"error":{"code":"rate_limit_exceeded","message":"synthetic"}})
    else: harness[1][0]=response(model="unrequested-model")
    prepared,batch,path,rows=await run(harness)
    continuing=failure in ("policy","schema")
    assert len(harness[0])==(2 if continuing else 1), rows
    assert (rows[1]["kind"]=="source_context_call")==continuing
    assert rows[0]["schema_valid"]==(failure=="policy")
    assert verify(prepared,batch,path)["process_exit_code"]==(2 if failure=="429" else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("location",["n","q","metadata","header","error"])
async def test_known_credential_echo_is_discarded_before_any_artifact(harness,location,capsys):
    if location=="n": reply=response(n=AUTHORED_CONTINUATION+" "+KEY)
    elif location=="q": reply=response(q="O que você faz com "+KEY+"?")
    elif location=="metadata": reply=response(extra={"request_id":KEY})
    elif location=="header":
        reply=response(); reply.headers["x-request-id"]=KEY
    else: reply=httpx.Response(429,json={"error":{"code":"rate_limit_exceeded","message":KEY}})
    harness[1][0]=reply
    prepared,batch,path,rows=await run(harness)
    assert rows[0]["credential_echo_blocked"] is True and len(harness[0])==1
    assert rows[0]["response_structure"] is rows[0]["evidence"] is rows[0]["output_projection"] is None
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir())
    output=capsys.readouterr()
    assert KEY not in output.out+output.err
    assert verify(prepared,batch,path)["process_exit_code"]==3


@pytest.mark.asyncio
@pytest.mark.parametrize("stage",["wait","projection","record"])
async def test_local_partial_or_cancellation_never_becomes_retroactive_admission(harness,monkeypatch,stage):
    original_project=probe._project
    if stage=="wait":
        async def cancel(self): raise asyncio.CancelledError()
        monkeypatch.setattr(probe.DispatchBudget,"wait",cancel)
    elif stage=="projection":
        def fail(*args,**kwargs): raise RuntimeError("synthetic local failure")
        monkeypatch.setattr(probe,"_project",fail)
    def on_record(row):
        if stage=="record": raise RuntimeError("synthetic callback failure")
    prepared,batch,path,rows=await run(harness,on_record=on_record)
    assert len(harness[0])==(0 if stage=="wait" else 1)
    assert rows[1]["kind"]=="source_context_skip"
    if stage=="projection":
        monkeypatch.setattr(probe,"_project",original_project)
        assert rows[0]["policy_valid"] is True and rows[0]["projection_valid"] is False
    assert verify(prepared,batch,path)["process_exit_code"]==(130 if stage=="wait" else 3)


@pytest.mark.asyncio
async def test_blank_credential_existing_path_and_drift_are_pre_dispatch_barriers(harness):
    prepared=probe.prepare_experiment(); batch=str(uuid4()); path=probe.run_path(batch)
    with pytest.raises(ValueError): await probe.evaluate_probe(prepared,api_key=SecretStr(" "),batch_id=batch,run_directory=path)
    assert not path.exists()
    prepared.metadata["conditions"].reverse()
    with pytest.raises(ValueError): await probe.evaluate_probe(prepared,api_key=SecretStr(KEY),batch_id=batch,run_directory=path)
    assert not path.exists()
    prepared=probe.prepare_experiment(); path.mkdir(parents=True)
    with pytest.raises(FileExistsError): await probe.evaluate_probe(prepared,api_key=SecretStr(KEY),batch_id=batch,run_directory=path)
    assert not harness[0]


@pytest.mark.asyncio
async def test_one_use_and_actual_http_counter_bound_survive_new_adapter(harness):
    prepared,batch,path,rows=await run(harness)
    request=probe.make_request(prepared,0,batch,deadline=probe.utc_now()+timedelta(seconds=60))
    budget=probe.DispatchBudget(); budget.calls=2
    adapter=probe.RetainedObservationAdapter(prepared=prepared,request=request,api_key=SecretStr(KEY),budget=budget)
    for _ in range(2):
        with pytest.raises((ValueError,probe.LLMInvocationError)): await adapter.generate_structured(request)
    assert budget.calls==2 and adapter.http_sent is False and len(harness[0])==2


@pytest.mark.asyncio
async def test_deadline_is_created_after_wait_and_second_prepared_check(harness,monkeypatch):
    waits=[]
    original_wait=probe.DispatchBudget.wait
    async def waited(self):
        await original_wait(self)
        waits.append(probe.utc_now())
    monkeypatch.setattr(probe.DispatchBudget,"wait",waited)
    prepared,batch,path,rows=await run(harness)
    assert len(waits)==2
    for waited_at,row in zip(waits,rows):
        assert probe._aware(row["deadline_at"])>=waited_at+timedelta(seconds=60)
    assert verify(prepared,batch,path)["verified"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("change",["source","request","projection","extra","usage","status","skip","echo","deadline","batch","preflight-post","preflight-evidence","run-time","initial-wait","start-gap"])
async def test_verifier_rejects_consistently_rehashed_artifact_tampering(harness,change):
    prepared,batch,path,rows=await run(harness)
    if change=="source": rows[0]["authored_source"]["provider_evidence"]={"provider":"Groq"}
    elif change=="request": rows[1]["request"]["user_packet"]=rows[0]["request"]["user_packet"]
    elif change=="projection": rows[0]["output_projection"]["text"]="changed"
    elif change=="extra": rows[0]["provider_observation"]["free_text"]="untrusted"
    elif change=="usage": rows[0]["evidence"]["usage"]["input_tokens"]=999
    elif change=="status": rows[0]["outcome"]="local_error"; rows[0]["local_error"]={"code":"source_context_local_error","stage":None}
    elif change=="skip": rows[1]={"kind":"source_context_skip","condition_id":probe.CONDITIONS[1],"reason":"previous_operational_failure"}
    elif change=="echo": rows[0]["credential_echo_blocked"]=True
    elif change=="deadline": rows[0]["deadline_at"]=rows[0]["http_started_at"]
    elif change=="batch": rows[0]["request"]["invocation_id"]=str(uuid4())
    elif change in ("preflight-post","preflight-evidence"):
        rows[0].update(outcome="local_error",local_error={"code":"source_context_local_error","stage":"preflight"},
            response_structure=None,output_projection=None,schema_valid=False,policy_valid=False,projection_valid=False)
        if change=="preflight-evidence": rows[0].update(call_made=False,http_started_at=None)
        rows[1]={"kind":"source_context_skip","condition_id":probe.CONDITIONS[1],"reason":"local_error"}
    elif change=="run-time":
        rows[0]["evidence"]["started_at"]="1999-01-01T00:00:00+00:00"
    elif change=="initial-wait":
        rows[0]["deadline_at"]=(probe._aware(rows[0]["deadline_at"])-timedelta(seconds=40)).isoformat()
    elif change=="start-gap":
        rows[1]["deadline_at"]=(probe._aware(rows[1]["deadline_at"])-timedelta(seconds=40)).isoformat()
    rewrite(path,rows,"local_error" if change in ("preflight-post","preflight-evidence") else None)
    with pytest.raises((ValueError,TypeError)): verify(prepared,batch,path)


@pytest.mark.asyncio
@pytest.mark.parametrize("attack",["duplicate","nan"])
async def test_jsonl_strict_parser_refuses_duplicate_keys_and_nonfinite_values(harness,attack):
    prepared,batch,path,rows=await run(harness)
    raw=path/(probe.CANDIDATE_ID+".jsonl")
    data=raw.read_text(encoding="utf-8")
    if attack=="duplicate": data=data.replace('"call_made":true','"call_made":false,"call_made":true',1)
    else: data=data.replace('"http_started_at":"','"untrusted":NaN,"http_started_at":"',1)
    raw.write_text(data,encoding="utf-8")
    doc=probe._read_json(path/"summary.json"); doc["artifacts"]["records"]["sha256"]=probe.shared._sha256(raw)
    (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")
    with pytest.raises(ValueError): verify(prepared,batch,path)


def test_cli_preflight_and_verifier_never_read_private_credential(harness,monkeypatch,capsys,tmp_path):
    original=probe.os.environ.get
    def guarded(name,*args):
        if name in (probe.KEY_ENV,"GROQ_API_KEY"): pytest.fail("Read credential before live boundary")
        return original(name,*args)
    monkeypatch.setattr(probe.os.environ,"get",guarded)
    assert probe.main(["--preflight"])==0
    prepared=probe.prepare_experiment(); expected,digest=expected_file(prepared,tmp_path/"unused")
    assert probe.main(["--verify-artifacts",str(tmp_path/"missing.json"),"--batch-id",str(uuid4()),
        "--expected-preflight",str(expected),"--expected-preflight-sha256",digest])==3
    assert not harness[0]

