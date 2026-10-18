"""Offline boundaries for the approved single-opening budget diagnostic."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from api.llm.contract import (AdapterIdentity, ErrorCategory, InvocationEvidence, LLMInvocationError,
    NormalizedError, OperationPhase, Provenance, utc_now)
from scripts import evaluate_narrator_record_budget as m
from scripts.narrator_record_budget_observer import BudgetObservationAdapter

KEY = "SYNTHETIC_BUDGET_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_ERROR_REASONING_NEVER_PERSIST"


@pytest.fixture(autouse=True)
def deterministic_pacing(monkeypatch):
    real = m.shared._CallPacer
    elapsed = [0.0]
    async def sleep(seconds): elapsed[0] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer", lambda interval: real(
        interval, _clock=lambda:elapsed[0], _sleeper=sleep))
    return elapsed


def envelope(outcome="unresolved", supports=None):
    return {"records": {"o": outcome, "l": "Corredor de pedra",
        "s": "Um sussurro distante ecoa no corredor.", "p": [],
        "f": [{"k":"observation","s":"Um sussurro distante ecoa no corredor.",
               "v":"public","i":0.5,"p":True,"a":[]}],
        "t": [], "r": [], "q": "O que você faz agora?"},
        "supports": [] if supports is None else supports}


def completion(value=None, finish="stop", model="openai/gpt-oss-120b"):
    return {"id": "chatcmpl-budget-synthetic", "model": model,
            "choices": [{"finish_reason": finish,
                         "message": {"content": json.dumps(value or envelope()), "reasoning": LEAK}}],
            "usage": {"prompt_tokens": 2320, "completion_tokens": 950,
                      "total_tokens": 3270, "completion_tokens_details": {"reasoning_tokens": 150}}}


def install(monkeypatch, handler):
    calls = []
    async def dispatch(request):
        calls.append(request)
        return handler(request)
    class Gateway(BudgetObservationAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
    monkeypatch.setattr(m, "BudgetObservationAdapter", Gateway)
    return calls


def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))


def test_preflight_preserves_payload_except_ceiling_and_never_reads_key(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Credential or client access during preflight")
    monkeypatch.setattr(m.os, "environ", {})
    monkeypatch.setattr(m, "BudgetObservationAdapter", forbidden)
    prepared = m.prepare_experiment()
    body = m._fixed_payload(m._make_request(prepared))
    original = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))["request"]["body"]
    assert set(body) == set(original)
    assert [k for k in original if original[k] != body[k]] == ["max_completion_tokens"]
    assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256
    assert len(prepared.cases) == len(prepared.packets) == 1
    assert prepared.cases[0].case_id == "opening"
    assert prepared.metadata["max_calls"] == 1
    assert prepared.metadata["inputs"]["prompt"]["variant"] == "record-evidence-v1"
    assert prepared.metadata["experiment_version"] == "record-evidence-budget-1536-v1"


def test_actual_mock_transport_sends_one_exact_body_and_applies_admission(monkeypatch, deterministic_pacing):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion()))
    rows = run()
    assert len(calls) == len(rows) == 1
    assert deterministic_pacing[0] == 60.0
    body = json.loads(calls[0].content)
    assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256
    assert str(calls[0].url) == "https://api.groq.com/openai/v1/chat/completions"
    assert rows[0]["kind"] == "record_evidence_budget_call"
    assert "composed_proposal" in rows[0], rows[0]
    assert rows[0]["fixed_narrative"] == rows[0]["composed_proposal"]["narrative"]
    assert rows[0]["schema_valid"] is rows[0]["envelope_valid"] is rows[0]["admitted"] is True
    assert rows[0]["provider_observation"]["finish_reason"] == "stop"
    summary = m.summarize(rows)
    assert summary["process_exit_code"] == 0
    assert summary["max_calls"] == summary["calls_made"] == 1
    assert summary["cases_skipped"] == 0
    assert summary["runtime_promoted"] is summary["automated_gates_passed"] is False
    assert summary["cap_001_status"] == "not_evaluated"
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("payload,expected_schema,expected_envelope", [
    (envelope(outcome="success"), True, True),
    (envelope(supports=[{"p":"/s","b":0,"e":5,"s":["nonexistent"],"m":"established"}]), True, False),
    ({"records":{"o":"unresolved"},"supports":[]}, False, False),
    ({**envelope(),"records":{**envelope()["records"],"f":[]}}, True, True),
])
def test_structure_does_not_bypass_supports_or_admission(monkeypatch, payload, expected_schema, expected_envelope):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(payload)))
    rows = run()
    assert len(calls) == len(rows) == 1
    assert rows[0]["schema_valid"] is expected_schema
    assert rows[0]["envelope_valid"] is expected_envelope
    assert rows[0]["admitted"] is False
    assert m.summarize(rows)["process_exit_code"] == 1


@pytest.mark.parametrize("status", [400,401,403,404,408,413,422,429,500,502,503])
def test_every_http_failure_ends_one_call_without_mara(monkeypatch, status):
    calls = install(monkeypatch, lambda req: httpx.Response(status, json={
        "error":{"message":LEAK,"code":"json_validate_failed","failed_generation":LEAK}}))
    rows = run()
    assert len(calls) == len(rows) == 1
    assert rows[0]["llm_error"]["status_code"] == status
    assert rows[0]["admitted"] is False
    assert m.summarize(rows)["cases_skipped"] == 0
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("finish", ["length","content_filter","tool_calls","function_call",None,LEAK])
def test_termination_observation_cannot_override_incomplete_result(monkeypatch, finish):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(finish=finish)))
    rows = run()
    assert len(calls) == 1
    assert rows[0]["admitted"] is False
    assert rows[0]["provider_observation"]["finish_reason"] == ("unknown" if finish==LEAK else finish)
    assert LEAK not in json.dumps(rows)


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_non_http_provider_categories_never_retry(monkeypatch, category):
    calls=[]
    class Gateway:
        observation={}
        def __init__(self, **kwargs): pass
        async def generate_structured(self, request):
            calls.append(request)
            raise LLMInvocationError(NormalizedError(
                category=category,code="synthetic_error",safe_message="Safe synthetic error.",
                phase=OperationPhase.RESPONSE,invocation_id=request.invocation_id,target=request.target,retryable=True,
                evidence=InvocationEvidence(provenance=Provenance(
                    invocation_id=request.invocation_id,requested_target=request.target,
                    adapter=AdapterIdentity(name="groq-chat-completions",version="1.0"),
                    started_at=utc_now(),finished_at=utc_now()))))
    monkeypatch.setattr(m,"BudgetObservationAdapter",Gateway)
    rows=run()
    assert len(calls)==len(rows)==1
    assert m.summarize(rows)["automatic_retries"]==0


@pytest.mark.parametrize("mutation", ["prompt","packet","case","metadata"])
def test_mutated_preparation_cannot_dispatch(monkeypatch, mutation):
    prepared=m.prepare_experiment()
    if mutation=="prompt": prepared=replace(prepared,prompt=prepared.prompt+" changed")
    elif mutation=="packet": prepared=replace(prepared,packets=(prepared.packets[0]+" changed",))
    elif mutation=="case": prepared=replace(prepared,cases=tuple(m.record_contract.load_fixed_cases()))
    else:
        prepared.metadata["max_calls"]=2
    def forbidden(**kwargs): raise AssertionError("Gateway must not be constructed")
    monkeypatch.setattr(m,"BudgetObservationAdapter",forbidden)
    with pytest.raises(ValueError,match="changed before dispatch"):
        asyncio.run(m.evaluate_probe(prepared,api_key=SecretStr(KEY)))


def test_deadline_is_created_after_pacing(monkeypatch):
    from datetime import timedelta
    start=m.utc_now(); clock=[start];requests=[]
    monkeypatch.setattr(m,"utc_now",lambda:clock[0])
    class Pacer:
        def __init__(self, seconds): self._clock=lambda:1000.0
        async def before_call(self,label): clock[0]+=timedelta(seconds=60)
    class Gateway:
        observation={}
        def __init__(self,**kwargs): pass
        async def generate_structured(self,request):
            requests.append(request)
            raise asyncio.CancelledError()
    monkeypatch.setattr(m.shared,"_CallPacer",Pacer)
    monkeypatch.setattr(m,"BudgetObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY),records=rows))
    assert requests[0].deadline==start+timedelta(seconds=120)
    assert len(rows)==1 and rows[0]["cancelled"] is True
    assert m.summarize(rows,status="cancelled")["process_exit_code"]==130


@pytest.mark.parametrize("argv", [["--preflight","--batch-id",str(uuid4())],["--live"],
    ["--live","--allow-synthetic-only"],["--preflight","--candidate","other"],
    ["--preflight","--max-output-tokens","768"],["--preflight","--case","mara"]])
def test_cli_rejects_unapproved_modes(argv):
    with pytest.raises(SystemExit): m.main(argv)


def test_main_persists_one_safe_observation(monkeypatch,tmp_path,capsys):
    monkeypatch.setenv("GROQ_API_KEY",KEY)
    monkeypatch.setattr(m,"_new_run_directory",lambda *args:tmp_path)
    calls=install(monkeypatch,lambda req:httpx.Response(400,json={"error":{
        "code":"json_validate_failed","message":LEAK,"failed_generation":"{bad-json"}},
        headers={"x-request-id":"req_synthetic_budget"}))
    code=m.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4())])
    summary=json.loads((tmp_path/"summary.json").read_text(encoding="utf-8"))
    raw=(tmp_path/(m.CANDIDATE_ID+".jsonl")).read_text(encoding="utf-8")
    assert len(calls)==len(raw.splitlines())==1
    assert code==summary["process_exit_code"]==1
    assert summary["summary"]["calls_made"]==1
    assert summary["experiment_version"]==m.EXPERIMENT_VERSION
    output=raw+json.dumps(summary)+capsys.readouterr().out
    assert KEY not in output and LEAK not in output and "{bad-json" not in output


def test_missing_credential_cannot_create_artifact(monkeypatch,capsys):
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    monkeypatch.setattr(m,"_new_run_directory",lambda *a:pytest.fail("artifact created without credential"))
    assert m.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4())])==3
    assert "missing" in capsys.readouterr().err


def test_cancellation_during_quiet_period_never_dispatches(monkeypatch):
    class Pacer:
        def __init__(self, seconds): self._clock=lambda:0.0
        async def before_call(self,label): raise asyncio.CancelledError()
    class Gateway:
        observation={}
        def __init__(self,**kwargs): pass
        async def generate_structured(self,request): pytest.fail("dispatch after cancellation")
    monkeypatch.setattr(m.shared,"_CallPacer",Pacer)
    monkeypatch.setattr(m,"BudgetObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY),records=rows))
    assert rows==[]


def test_source_drift_during_quiet_period_never_dispatches(monkeypatch):
    prepared=m.prepare_experiment()
    class Pacer:
        def __init__(self,seconds): self._clock=lambda:0.0
        async def before_call(self,label):
            monkeypatch.setattr(m.contract,"load_evidence_prompt",lambda:(
                m.PROJECT_ROOT/"evals/narrator/prompts/record-evidence-v1.md",prepared.prompt+" drift"))
    class Gateway:
        observation={}
        def __init__(self,**kwargs): pass
        async def generate_structured(self,request): pytest.fail("dispatch after source drift")
    monkeypatch.setattr(m.shared,"_CallPacer",Pacer)
    monkeypatch.setattr(m,"BudgetObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared,api_key=SecretStr(KEY),records=rows))
    assert rows==[]
