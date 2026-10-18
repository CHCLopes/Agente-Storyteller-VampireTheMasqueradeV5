"""Focused offline checks for one frozen 768-token summary-budget request."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from datetime import timedelta
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from api.llm.contract import LLMInvocationError
from scripts import evaluate_narrator_summary_budget as m
from scripts.evaluate_narrator_summary_budget import SummaryBudgetObservationAdapter

KEY="SYNTHETIC_SUMMARY_BUDGET_KEY_NEVER_PERSIST"
LEAK="UNTRUSTED_BUDGET_REASONING_NEVER_PERSIST"
TEXT="  O relógio parado marca seis horas na estação vazia.  "


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real=m.shared._CallPacer; elapsed=[0.0]
    async def sleep(seconds): elapsed[0]+=seconds
    monkeypatch.setattr(m.shared,"_CallPacer",lambda interval:real(interval,_clock=lambda:elapsed[0],_sleeper=sleep))
    return elapsed


def completion(*,finish="stop",model=m.GROQ_QWEN_MODEL_ID,value=None):
    return {"model":model,"id":"synthetic-budget","choices":[{"finish_reason":finish,
        "message":{"content":json.dumps({"summary":TEXT} if value is None else value),"reasoning":LEAK}}]}


def install(monkeypatch,pacing,handler=None,transform=None):
    state={"calls":[],"requests":[]}
    class Gateway(SummaryBudgetObservationAdapter):
        def __init__(self,**kwargs):
            async def dispatch(request):
                state["calls"].append({"request":request,"started":pacing[0]})
                return handler(request) if handler else httpx.Response(200,json=completion())
            super().__init__(**kwargs,transport=httpx.MockTransport(dispatch))
        async def generate_structured(self,request):
            state["requests"].append(request)
            result=await super().generate_structured(request)
            return transform(result) if transform else result
        async def generate_text(self,request): pytest.fail("No narrative, diagnostic or fallback")
    monkeypatch.setattr(m,"SummaryBudgetObservationAdapter",Gateway)
    return state


def run(): return asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY)))


def main_at(monkeypatch,path):
    monkeypatch.setenv("GROQ_API_KEY",KEY)
    monkeypatch.setattr(m,"_new_run_directory",lambda *args:path)
    return m.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4())])


def artifacts(path):
    row=json.loads((path/(m.CANDIDATE_ID+".jsonl")).read_text(encoding="utf-8"))
    doc=json.loads((path/"summary.json").read_text(encoding="utf-8"))
    return row,doc


def test_keyless_preflight_exact_new_case_prompt_and_768_body_with_unchanged_schema(monkeypatch,capsys):
    class Environment(dict):
        def get(self,key,*args):
            if key=="GROQ_API_KEY": pytest.fail("preflight credential access")
            return super().get(key,*args)
    monkeypatch.setattr(m.os,"environ",Environment())
    monkeypatch.setattr(m,"SummaryBudgetObservationAdapter",lambda **kwargs:pytest.fail("preflight client"))
    monkeypatch.setattr(m,"_new_run_directory",lambda *args:pytest.fail("preflight artifact"))
    p=m.prepare_experiment(); dossier=json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    body=m._fixed_payload(m._make_request(p))
    assert body==dossier["request"]["body"] and m._canonical_sha(body)==m.PROPOSED_BODY_SHA256
    assert body["max_completion_tokens"]==768 and body["temperature"]==0.65 and body["reasoning_effort"]=="none"
    assert "include_reasoning" not in body and len(body["messages"])==2
    assert p.case["case_id"]=="station-clock" and p.case["origin"]=="agent_authored_synthetic_case"
    assert json.loads(p.packet.split("\n",1)[1])==p.case
    assert "".join(s["text"] for s in p.case["source_units"])==p.case["narrative"]
    assert m.PROTOCOL=="record-summary-only-v1" and m.PROMPT_VARIANT=="record-summary-budget-v1"
    assert p.metadata["inputs"]["prompt"]["variant"]==m.PROMPT_VARIANT
    assert p.metadata["inputs"]["response_schema_sha256"]=="56665f9935721c6e5909de1d3f8b7fb869de6cda7cecd4af0b3591d977a15616"
    assert p.metadata["summary_generation_parameters"]["max_total_output_tokens"]==768
    assert p.metadata["max_calls"]==1 and p.metadata["automatic_retries"]==0
    assert not {"candidate_id","model","batch_id"}.intersection(p.metadata["inputs"]["cases"][0]["source"])
    assert m.main(["--preflight"])==0
    output=capsys.readouterr(); assert json.loads(output.out)==p.metadata and output.err==""


def test_native_one_shot_keeps_literal_text_null_usage_and_no_semantic_approval(monkeypatch,pacing):
    state=install(monkeypatch,pacing); rows=run(); row=rows[0]; summary=m.summarize(rows)
    assert len(state["calls"])==len(rows)==1
    assert m._canonical_sha(json.loads(state["calls"][0]["request"].content))==m.PROPOSED_BODY_SHA256
    assert row["response_structure"]=={"summary":TEXT} and row["summary_text"]==TEXT
    assert row["instruction_measurements"]==m.contract.measure_summary_words(TEXT)
    assert summary["instruction_measurements"]==row["instruction_measurements"]
    assert row["schema_valid"] is True and row["route_status"]=="verified"
    assert summary["process_exit_code"]==0 and summary["calls_made"]==1 and summary["cases_skipped"]==0
    assert all(value is None for value in row["provider_observation"]["usage"].values())
    assert summary["usage_aggregate"]["status"]==summary["cost_aggregate"]["status"]=="unavailable"
    assert summary["semantic_fidelity_review"]=={"status":"not_performed","approval":None}
    assert summary["automated_gates_passed"] is summary["runtime_promoted"] is False
    assert not {"projection","admitted","open_questions","final_schema_valid"}.intersection(row)
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_deadline_is_created_after_initial_wait_and_fresh_integrity_check(monkeypatch,pacing):
    start=m.utc_now(); monkeypatch.setattr(m,"utc_now",lambda:start+timedelta(seconds=pacing[0]))
    real=m._check_prepared; checks=[0]
    def check(p):
        real(p); checks[0]+=1
        if checks[0]==2: pacing[0]+=2.0
    monkeypatch.setattr(m,"_check_prepared",check)
    state=install(monkeypatch,pacing); run()
    assert state["calls"][0]["started"]==62.0
    assert state["requests"][0].deadline==start+timedelta(seconds=122)
    assert state["requests"][0].operation=="summary-budget.station-clock"


@pytest.mark.parametrize("failure",["429","length","schema","route"])
def test_failed_attempt_never_retries_or_retains_unvalidated_summary(monkeypatch,pacing,failure):
    def handler(request):
        if failure=="429": return httpx.Response(429,json={"error":{"code":"rate_limit_exceeded","message":LEAK}})
        return httpx.Response(200,json=completion(finish="length" if failure=="length" else "stop",
            model="other" if failure=="route" else m.GROQ_QWEN_MODEL_ID,value={"summary":True} if failure=="schema" else None))
    state=install(monkeypatch,pacing,handler); rows=run(); summary=m.summarize(rows)
    assert len(state["calls"])==1 and len(rows)==1 and rows[0]["schema_valid"] is False
    assert not {"summary_text","response_structure","instruction_measurements"}.intersection(rows[0])
    assert summary["instruction_measurements"] is None and summary["process_exit_code"]==(2 if failure=="429" else 1)
    assert summary["operational_probe_passed"] is False
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("when",["wait","inflight"])
def test_cancel_persists_one_call_or_skip_and_no_second_attempt(monkeypatch,tmp_path,pacing,when):
    if when=="wait":
        class Pacer:
            def __init__(self,interval): self._clock=lambda:0.0
            async def before_call(self,label): raise asyncio.CancelledError()
        monkeypatch.setattr(m.shared,"_CallPacer",Pacer)
    def handler(request): raise asyncio.CancelledError()
    state=install(monkeypatch,pacing,handler)
    assert main_at(monkeypatch,tmp_path)==130
    row,doc=artifacts(tmp_path)
    assert len(state["calls"])==(1 if when=="inflight" else 0)
    assert row["kind"]==("summary_budget_call" if when=="inflight" else "summary_budget_skip")
    assert row["case_id"]==m.CASE_ID and doc["summary"]==m.summarize([row],status="cancelled")
    assert KEY not in json.dumps(row)+json.dumps(doc)


def test_forged_model_is_revalidated_before_retention(monkeypatch,pacing):
    bad=m.contract.SummaryOnlyProposal.model_construct(summary=True)
    state=install(monkeypatch,pacing,transform=lambda r:r.model_copy(update={"value":bad}))
    rows=run(); assert len(state["calls"])==1
    assert rows[0]["schema_error"]=={"code":"summary_budget_schema_invalid"}
    assert rows[0]["schema_valid"] is False and "summary_text" not in rows[0]


@pytest.mark.parametrize("which",["CASE_SHA256","PROMPT_SHA256","DOSSIER_SHA256"])
def test_changed_frozen_input_during_wait_prevents_dispatch(monkeypatch,which):
    p=m.prepare_experiment()
    class Pacer:
        def __init__(self,interval): self._clock=lambda:0.0
        async def before_call(self,label): monkeypatch.setattr(m,which,"0"*64)
    monkeypatch.setattr(m.shared,"_CallPacer",Pacer)
    monkeypatch.setattr(m,"SummaryBudgetObservationAdapter",lambda **kwargs:pytest.fail("gateway after drift"))
    with pytest.raises(ValueError): asyncio.run(m.evaluate_probe(p,api_key=SecretStr(KEY)))


@pytest.mark.parametrize("mutation",["metadata_type","old_source"])
def test_modified_preparation_is_refused_without_a_gateway(monkeypatch,mutation):
    p=m.prepare_experiment()
    if mutation=="metadata_type": p.metadata["runtime_promoted"]=0
    else: p=replace(p,case=json.loads((m.PROJECT_ROOT/'evals/narrator/record_inline_case_v1.json').read_text(encoding='utf-8')))
    monkeypatch.setattr(m,"SummaryBudgetObservationAdapter",lambda **kwargs:pytest.fail("gateway after changed preparation"))
    with pytest.raises(ValueError): asyncio.run(m.evaluate_probe(p,api_key=SecretStr(KEY)))


@pytest.mark.parametrize("mutation",["3072","old_source"])
def test_observer_refuses_old_budget_or_source_and_permits_only_one_exact_request(mutation):
    p=m.prepare_experiment(); calls=[]
    def handler(request): calls.append(request); return httpx.Response(200,json=completion())
    adapter=SummaryBudgetObservationAdapter(base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(p.candidate,p.target),api_key=SecretStr(KEY),reasoning_effort="none",transport=httpx.MockTransport(handler))
    exact=m._make_request(p)
    if mutation=="3072": changed=exact.model_copy(update={"parameters":exact.parameters.model_copy(update={"max_output_tokens":3072})})
    else:
        old=json.loads((m.PROJECT_ROOT/'evals/narrator/reports/record-summary-only-dossier-94a95216-2026-09-07.json').read_text(encoding='utf-8'))['request']['body']['messages'][1]['content']
        changed=exact.model_copy(update={"messages":(exact.messages[0],exact.messages[1].model_copy(update={"content":old}))})
    with pytest.raises(LLMInvocationError): asyncio.run(adapter.generate_structured(changed))
    assert calls==[]
    asyncio.run(adapter.generate_structured(exact))
    with pytest.raises(LLMInvocationError): asyncio.run(adapter.generate_structured(m._make_request(p)))
    assert len(calls)==1


def test_local_measurement_error_retains_valid_literal_response_with_exit3(monkeypatch,tmp_path,pacing):
    state=install(monkeypatch,pacing)
    def fail(text): raise RuntimeError(LEAK)
    monkeypatch.setattr(m.contract,"measure_summary_words",fail)
    assert main_at(monkeypatch,tmp_path)==3
    row,doc=artifacts(tmp_path)
    assert len(state["calls"])==1 and row["response_structure"]=={"summary":TEXT}
    assert row["schema_valid"] is True and row["local_error"]=={"code":"local_summary_budget_failure"}
    assert doc["summary"]["instruction_measurements"] is None and doc["summary"]["operational_probe_passed"] is False
    assert LEAK not in json.dumps(row)


def test_success_artifact_roundtrip_preserves_budget_scope_and_measurement(monkeypatch,tmp_path,pacing):
    state=install(monkeypatch,pacing)
    assert main_at(monkeypatch,tmp_path)==0
    row,doc=artifacts(tmp_path)
    assert len(state["calls"])==1 and doc["summary"]==m.summarize([row])
    assert doc["inputs"]==m.prepare_experiment().metadata["inputs"]
    assert doc["purpose"]==row["purpose"]=="summary_budget_qwen_probe"
    assert doc["experiment_version"]=="record-summary-budget-qwen-observation-v1"
    assert row["summary_text"]==TEXT and doc["summary_generation_parameters"]["max_total_output_tokens"]==768
    assert KEY not in json.dumps(doc)+json.dumps(row) and LEAK not in json.dumps(row)


@pytest.mark.parametrize("argv",[["--preflight","--max-output-tokens","3072"],["--preflight","--case","archive-vibration"],["--preflight","--reasoning-effort","low"],["--live"]])
def test_mutable_scope_cli_rejected_before_preflight(monkeypatch,argv):
    monkeypatch.setattr(m,"prepare_experiment",lambda:pytest.fail("preflight after invalid CLI"))
    with pytest.raises(SystemExit): m.main(argv)
