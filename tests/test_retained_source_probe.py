"""Bounded retained-source harness tests. Only HTTPX MockTransport is used."""
from __future__ import annotations
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
import httpx
from pydantic import SecretStr
import pytest
from scripts import evaluate_retained_source as probe
from tests.test_narrative_source_bridge import FIRST, SECOND, QUESTION

KEY = "synthetic-runtime-credential-never-retain"

def response(n=FIRST,q=QUESTION,*,model=probe.GROQ_QWEN_MODEL_ID,finish="stop",extra=None):
    body = {"model":model,"choices":[{"finish_reason":finish,"message":{"role":"assistant","content":json.dumps({"n":n,"q":q},ensure_ascii=False)}}],
        "usage":{"prompt_tokens":100,"completion_tokens":80,"total_tokens":180}}
    body.update(extra or {})
    return httpx.Response(200,json=body)

@pytest.fixture
def harness(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,"OUTPUT_ROOT",tmp_path/"results")
    async def no_wait(self): pass
    monkeypatch.setattr(probe.DispatchBudget,"wait",no_wait)
    seen=[]
    replies=[response(),response(SECOND)]
    def handler(request):
        seen.append(json.loads(request.content))
        return replies.pop(0)
    original=probe.RetainedObservationAdapter.__init__
    def init(self,**kwargs):
        return original(self,transport=httpx.MockTransport(handler),**kwargs)
    monkeypatch.setattr(probe.RetainedObservationAdapter,"__init__",init)
    return seen,replies

async def run(harness):
    prepared=probe.prepare_experiment()
    batch=str(uuid4())
    path=probe.run_path(batch)
    rows=await probe.evaluate_probe(prepared,api_key=SecretStr(KEY),batch_id=batch,run_directory=path)
    return prepared,batch,path,rows

@pytest.mark.asyncio
async def test_two_retained_turns_replay_and_source_chain(harness):
    prepared,batch,path,rows=await run(harness)
    document=json.loads((path/"summary.json").read_text())
    assert document["process_exit_code"]==0, rows
    assert document["summary"]["calls_made"]==2
    assert document["summary"]["turns_committed"]==2
    assert document["summary"]["replays_verified"]==2
    assert len(harness[0])==2
    second=json.loads(harness[0][1]["messages"][1]["content"])
    assert FIRST in probe._json(second)
    assert QUESTION not in probe._json(second)
    assert all(row["request"]["body_sha256"]==probe._sha(body) for row,body in zip(rows,harness[0]))
    assert rows[0]["request"]["body_sha256"]!=prepared.metadata["first_request_template"]["body_sha256"]

def expected_file(prepared,path):
    target=path.parent/(path.name+"-preflight.json")
    target.write_text(probe._json(prepared.metadata),encoding="utf-8")
    return target,probe.shared._sha256(target)

async def verify(prepared,batch,path):
    target,digest=expected_file(prepared,path)
    return await asyncio.to_thread(probe.verify_artifacts,path/"summary.json",target,batch,expected_preflight_sha256=digest)

@pytest.mark.asyncio
async def test_verifier_reconstructs_sealed_copy_without_mutating_originals(harness):
    prepared,batch,path,rows=await run(harness)
    before={p.name:probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    result=await verify(prepared,batch,path)
    assert result["verified"] is True and result["process_exit_code"]==0
    assert before=={p.name:probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}

@pytest.mark.parametrize("failure",["policy","429","schema","length","route"])
@pytest.mark.asyncio
async def test_failures_stop_dependence_preserve_status_and_verify(harness,failure):
    replies=harness[1]
    if failure=="policy": replies[0]=response(q="Quem está aqui?")
    elif failure=="429": replies[0]=httpx.Response(429,json={"error":{"code":"rate_limit_exceeded","message":"synthetic quota"}})
    elif failure=="schema": replies[0]=response(n="curta")
    elif failure=="length": replies[0]=response(finish="length")
    else: replies[0]=response(model="wrong-model")
    prepared,batch,path,rows=await run(harness)
    document=json.loads((path/"summary.json").read_text())
    assert document["evaluation_status"]=="completed",rows
    assert document["process_exit_code"]==(2 if failure=="429" else 1),rows
    assert len(harness[0])==1 and rows[1]["kind"]=="retained_source_skip"
    assert rows[0]["replay_verified"] is False
    assert rows[0]["schema_valid"]==(failure=="policy")
    assert (await verify(prepared,batch,path))["verified"] is True

@pytest.mark.parametrize("location",["n","q","metadata","header","error"])
@pytest.mark.asyncio
async def test_runtime_credential_echo_never_reaches_sqlite_artifacts_or_logs(harness,location,capsys):
    if location=="n": reply=response(n=FIRST+" "+KEY)
    elif location=="q": reply=response(q="O que você faz com "+KEY+"?")
    elif location=="metadata": reply=response(extra={"request_id":KEY})
    elif location=="header":
        reply=response()
        reply.headers["x-request-id"]=KEY
    else: reply=httpx.Response(429,json={"error":{"code":"rate_limit_exceeded","message":KEY}})
    harness[1][0]=reply
    prepared,batch,path,rows=await run(harness)
    assert rows[0]["credential_echo_blocked"] is True
    assert rows[0]["response_structure"] is None
    assert rows[0]["result"]["status"]!="completed"
    assert len(harness[0])==1
    for file in path.iterdir():
        if file.is_file(): assert KEY.encode() not in file.read_bytes()
    captured=capsys.readouterr()
    assert KEY not in captured.out+captured.err
    assert (await verify(prepared,batch,path))["verified"] is True

@pytest.mark.asyncio
async def test_blank_credential_and_reused_directory_fail_before_dispatch(harness):
    prepared=probe.prepare_experiment();batch=str(uuid4());path=probe.run_path(batch)
    with pytest.raises(ValueError):
        await probe.evaluate_probe(prepared,api_key=SecretStr(" "),batch_id=batch,run_directory=path)
    assert not path.exists() and not harness[0]
    path.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        await probe.evaluate_probe(prepared,api_key=SecretStr(KEY),batch_id=batch,run_directory=path)
    assert not harness[0]

@pytest.mark.asyncio
async def test_prepared_drift_after_wait_is_closed_without_http(harness,monkeypatch):
    original=probe.DispatchBudget.wait
    async def drift(self):
        await original(self)
        monkeypatch.setattr(probe,"PLAYER_INPUTS",("changed",probe.PLAYER_INPUTS[1]))
    monkeypatch.setattr(probe.DispatchBudget,"wait",drift)
    prepared,batch,path,rows=await run(harness)
    assert not harness[0]
    assert rows[0]["capsule"] is not None and rows[0]["local_error"]=="retained_probe_local_error"
    assert json.loads((path/"summary.json").read_text())["process_exit_code"]==3

@pytest.mark.asyncio
async def test_global_http_budget_and_one_use_guard(harness):
    prepared,batch,path,rows=await run(harness)
    capsule=probe.validate_source_turn_capsule(rows[0]["capsule"],session_id=batch,operation_id=rows[0]["operation_id"])
    request=probe._request(capsule)
    budget=probe.DispatchBudget()
    budget.calls=2
    adapter=probe.RetainedObservationAdapter(prepared=prepared,request=request,api_key=SecretStr(KEY),budget=budget)
    with pytest.raises(Exception): await adapter.generate_structured(request)
    assert budget.calls==2 and not adapter.http_sent and len(harness[0])==2
    with pytest.raises(Exception): await adapter.generate_structured(request)
    assert len(harness[0])==2

@pytest.mark.asyncio
async def test_completed_replay_forbids_duplicate_chunk(harness,monkeypatch):
    real=probe.execute_retained_source_turn
    async def changed(**kwargs):
        if isinstance(kwargs["gateway"],probe.NoCallGateway):
            await kwargs["on_chunk"]("must not be delivered")
        return await real(**kwargs)
    monkeypatch.setattr(probe,"execute_retained_source_turn",changed)
    prepared,batch,path,rows=await run(harness)
    assert rows[0]["local_error"]=="retained_probe_local_error"
    assert len(harness[0])==1 and not rows[0]["replay_verified"]

@pytest.mark.asyncio
async def test_cancel_before_http_has_zero_calls_and_retained_capsule(harness,monkeypatch):
    async def cancel(self): raise asyncio.CancelledError()
    monkeypatch.setattr(probe.DispatchBudget,"wait",cancel)
    prepared,batch,path,rows=await run(harness)
    assert len(harness[0])==0 and rows[0]["capsule"] is not None
    assert json.loads((path/"summary.json").read_text())["process_exit_code"]==130
    assert (await verify(prepared,batch,path))["verified"] is True


def rewrite(path,rows):
    doc=json.loads((path/"summary.json").read_text())
    raw="".join(probe._json({"metadata":doc["metadata"],"batch_id":doc["batch_id"],"record":r})+"\n" for r in rows)
    output=path/(probe.CANDIDATE_ID+".jsonl")
    output.write_text(raw,encoding="utf-8")
    doc["artifacts"]["records"]["sha256"]=probe.shared._sha256(output)
    doc["summary"]=probe.summarize(rows,doc["evaluation_status"])
    doc["process_exit_code"]=doc["summary"]["process_exit_code"]
    (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")

@pytest.mark.parametrize("field",["body","capsule","response","snapshot","database"])
@pytest.mark.asyncio
async def test_coherent_artifact_rehash_cannot_hide_tampering(harness,field):
    prepared,batch,path,rows=await run(harness)
    if field=="body": rows[0]["request"]["request"]["max_completion_tokens"]=767
    elif field=="capsule": rows[0]["capsule"]["player_input"]="forged"
    elif field=="response": rows[0]["response_structure"]["n"]=SECOND
    elif field=="snapshot": rows[0]["provider_observation"]["private_text"]="forged"
    else:
        connection=sqlite3.connect(path/"retained-source.sqlite3")
        connection.execute("UPDATE attempts SET status='pending' WHERE operation_id=?",(rows[0]["operation_id"],))
        connection.commit();connection.close()
    rewrite(path,rows)
    if field=="database":
        doc=json.loads((path/"summary.json").read_text())
        doc["artifacts"]["database"]["sha256"]=probe.shared._sha256(path/"retained-source.sqlite3")
        (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")
    with pytest.raises(Exception): await verify(prepared,batch,path)


def test_preflight_is_keyless_and_names_current_executor(monkeypatch,capsys):
    original=probe.os.environ.get
    def guarded(key,*args):
        assert "KEY" not in key and "TOKEN" not in key
        return original(key,*args)
    monkeypatch.setattr(probe.os.environ,"get",guarded)
    assert probe.main(["--preflight"])==0
    data=json.loads(capsys.readouterr().out)
    assert data["first_request_template"]["is_live_request"] is False
    assert data["evaluator"]["file"]=="scripts/evaluate_retained_source.py"
    assert data["generation_parameters"]==probe.PARAMETERS


def test_expected_preflight_hash_checked_before_credential(tmp_path,monkeypatch):
    prepared=probe.prepare_experiment()
    pre=tmp_path/"preflight.json";pre.write_text(probe._json(prepared.metadata))
    original=probe.os.environ.get
    def guarded(key,*args):
        assert key!=probe.KEY_ENV
        return original(key,*args)
    monkeypatch.setattr(probe.os.environ,"get",guarded)
    assert probe.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4()),"--expected-preflight",str(pre),
                      "--expected-preflight-sha256","0"*64])==3

@pytest.mark.asyncio
async def test_pacing_reanchors_at_real_dispatch_and_deadline_follows_wait(harness,monkeypatch):
    seen_deadlines=[]
    original=probe.RetainedObservationAdapter.generate_structured
    async def generate(self,request):
        seen_deadlines.append((request.deadline-probe.utc_now()).total_seconds())
        return await original(self,request)
    monkeypatch.setattr(probe.RetainedObservationAdapter,"generate_structured",generate)
    await run(harness)
    assert all(55<seconds<=60 for seconds in seen_deadlines)
    clock=[0.0];sleeps=[]
    async def sleeper(seconds): sleeps.append(seconds);clock[0]+=seconds
    pacer=probe.shared._CallPacer(60,_clock=lambda:clock[0],_sleeper=sleeper)
    pacer._last_call_started_at=0
    await pacer.before_call("fixture")
    clock[0]=62
    budget=probe.DispatchBudget();budget.pacer=pacer;budget.consume()
    clock[0]=80
    await pacer.before_call("fixture")
    assert sleeps==[60,42]

@pytest.mark.parametrize("syntax",["duplicate","nan"])
@pytest.mark.asyncio
async def test_jsonl_is_strict_even_after_manifest_rehash(harness,syntax):
    prepared,batch,path,rows=await run(harness)
    output=path/(probe.CANDIDATE_ID+".jsonl")
    raw=output.read_text(encoding="utf-8")
    if syntax=="duplicate":
        raw=raw.replace('{"batch_id":','{"batch_id":"'+batch+'","batch_id":',1)
    else:
        raw=raw.replace(probe._json(rows[0]["http_started_at"]),'NaN',1)
    output.write_text(raw,encoding="utf-8")
    doc=json.loads((path/"summary.json").read_text())
    doc["artifacts"]["records"]["sha256"]=probe.shared._sha256(output)
    (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")
    with pytest.raises(ValueError): await verify(prepared,batch,path)

@pytest.mark.parametrize("field",["usage","cost","adapter","started_at"])
@pytest.mark.asyncio
async def test_evidence_must_match_sqlite_audit(harness,field):
    prepared,batch,path,rows=await run(harness)
    evidence=rows[0]["evidence"]
    if field=="usage": evidence["usage"]["input_tokens"]+=1
    elif field=="cost": evidence["cost"]["source"]="forged"
    elif field=="adapter": evidence["adapter"]["version"]="forged"
    else: evidence["started_at"]="2026-01-01T00:00:00+00:00"
    rewrite(path,rows)
    with pytest.raises(ValueError): await verify(prepared,batch,path)

@pytest.mark.asyncio
async def test_orphan_attempt_in_rehashed_database_is_rejected(harness):
    prepared,batch,path,rows=await run(harness)
    db=path/"retained-source.sqlite3"
    connection=sqlite3.connect(db)
    connection.row_factory=sqlite3.Row
    row=dict(connection.execute("SELECT * FROM attempts LIMIT 1").fetchone())
    row.pop("id");row.update(session_id="orphan",operation_id="orphan-op",attempt_id="orphan-attempt")
    connection.execute("INSERT INTO attempts ("+",".join(row)+") VALUES ("+",".join("?" for _ in row)+")",tuple(row.values()))
    connection.commit();connection.close()
    doc=json.loads((path/"summary.json").read_text())
    doc["artifacts"]["database"]["sha256"]=probe.shared._sha256(db)
    (path/"summary.json").write_text(probe._json(doc),encoding="utf-8")
    with pytest.raises(ValueError): await verify(prepared,batch,path)

@pytest.mark.parametrize("cancel",[False,True])
@pytest.mark.asyncio
async def test_delivery_failure_or_cancellation_is_verifiable_without_promotion(harness,monkeypatch,cancel):
    async def fail(_text):
        if cancel: raise asyncio.CancelledError()
        raise RuntimeError("synthetic delivery failure")
    monkeypatch.setattr(probe,"_no_chunk",fail)
    prepared,batch,path,rows=await run(harness)
    assert rows[0]["schema_valid"] is True and len(harness[0])==1
    doc=json.loads((path/"summary.json").read_text())
    assert doc["summary"]["turns_committed"]==0
    assert doc["process_exit_code"]==(130 if cancel else 1)
    if not cancel: assert rows[0]["result"]["error"]["code"]=="source_turn_delivery_failed"
    assert (await verify(prepared,batch,path))["verified"] is True

@pytest.mark.asyncio
async def test_changed_request_rejected_before_http(harness):
    prepared,batch,path,rows=await run(harness)
    capsule=probe.validate_source_turn_capsule(rows[0]["capsule"],session_id=batch,operation_id=rows[0]["operation_id"])
    request=probe._request(capsule)
    budget=probe.DispatchBudget()
    adapter=probe.RetainedObservationAdapter(prepared=prepared,request=request,api_key=SecretStr(KEY),budget=budget)
    altered=request.model_copy(update={"parameters":probe.GenerationParameters(temperature=.65,max_output_tokens=767)})
    with pytest.raises(Exception): await adapter.generate_structured(altered)
    assert budget.calls==0 and not adapter.http_sent and len(harness[0])==2

@pytest.mark.asyncio
async def test_cancellation_after_commit_records_committed_turn_without_resend(harness,monkeypatch):
    real=probe.execute_retained_source_turn
    async def cancelled_after_commit(**kwargs):
        result=await real(**kwargs)
        if not isinstance(kwargs["gateway"],probe.NoCallGateway) and result.status=="completed":
            raise asyncio.CancelledError()
        return result
    monkeypatch.setattr(probe,"execute_retained_source_turn",cancelled_after_commit)
    prepared,batch,path,rows=await run(harness)
    document=json.loads((path/"summary.json").read_text())
    assert document["evaluation_status"]=="cancelled" and document["process_exit_code"]==130
    assert document["summary"]["turns_committed"]==1
    assert len(harness[0])==1 and rows[0]["replay_verified"] is True
    assert (await verify(prepared,batch,path))["verified"] is True
