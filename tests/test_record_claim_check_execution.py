"""Offline boundaries for the single-opening claim-check SYSTEM experiment at 3072."""

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

from scripts import evaluate_narrator_record_claim_check as m

from scripts.evaluate_narrator_record_claim_check import ClaimCheckObservationAdapter

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
    class Gateway(ClaimCheckObservationAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
    monkeypatch.setattr(m, "ClaimCheckObservationAdapter", Gateway)
    return calls

def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))

def test_actual_mock_transport_sends_one_exact_body_and_applies_admission(monkeypatch, deterministic_pacing):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion()))
    rows = run()
    assert len(calls) == len(rows) == 1
    assert deterministic_pacing[0] == 60.0
    body = json.loads(calls[0].content)
    assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256
    assert str(calls[0].url) == "https://api.groq.com/openai/v1/chat/completions"
    assert rows[0]["kind"] == "record_evidence_claim_check_call"
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

@pytest.mark.parametrize("status", [400,429,503])
def test_every_http_failure_ends_one_call_without_mara(monkeypatch, status):
    calls = install(monkeypatch, lambda req: httpx.Response(status, json={
        "error":{"message":LEAK,"code":"json_validate_failed","failed_generation":LEAK}}))
    rows = run()
    assert len(calls) == len(rows) == 1
    assert rows[0]["llm_error"]["status_code"] == status
    assert rows[0]["admitted"] is False
    assert m.summarize(rows)["cases_skipped"] == 0
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)

@pytest.mark.parametrize("finish", ["length",None,LEAK])
def test_termination_observation_cannot_override_incomplete_result(monkeypatch, finish):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(finish=finish)))
    rows = run()
    assert len(calls) == 1
    assert rows[0]["admitted"] is False
    assert rows[0]["provider_observation"]["finish_reason"] == ("unknown" if finish==LEAK else finish)
    assert LEAK not in json.dumps(rows)

@pytest.mark.parametrize("mutation", ["prompt","packet","case","metadata"])
def test_mutated_preparation_cannot_dispatch(monkeypatch, mutation):
    prepared=m.prepare_experiment()
    if mutation=="prompt": prepared=replace(prepared,prompt=prepared.prompt+" changed")
    elif mutation=="packet": prepared=replace(prepared,packets=(prepared.packets[0]+" changed",))
    elif mutation=="case": prepared=replace(prepared,cases=tuple(m.record_contract.load_fixed_cases()))
    else:
        prepared.metadata["max_calls"]=2
    def forbidden(**kwargs): raise AssertionError("Gateway must not be constructed")
    monkeypatch.setattr(m,"ClaimCheckObservationAdapter",forbidden)
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
    monkeypatch.setattr(m,"ClaimCheckObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY),records=rows))
    assert requests[0].deadline==start+timedelta(seconds=120)
    assert len(rows)==1 and rows[0]["cancelled"] is True
    assert m.summarize(rows,status="cancelled")["process_exit_code"]==130

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
    monkeypatch.setattr(m,"ClaimCheckObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY),records=rows))
    assert rows==[]

def test_preflight_main_returns_one_json_document_without_credential_or_output(monkeypatch, capsys):
    class ForbiddenEnvironment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY":
                pytest.fail("credential inspected during preflight")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", ForbiddenEnvironment())
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("artifact created during preflight"))
    assert m.main(["--preflight"]) == 0
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document["experiment_version"] == "record-evidence-claim-check-v1"
    assert captured.err == ""

@pytest.mark.parametrize("which", ["dossier", "prompt"])
def test_preflight_drift_precedes_credential_access(monkeypatch, capsys, which):
    class ForbiddenEnvironment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY":
                pytest.fail("credential inspected after preflight drift")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", ForbiddenEnvironment())
    if which == "dossier":
        monkeypatch.setattr(m, "DOSSIER_SHA256", "0" * 64)
    else:
        monkeypatch.setattr(m, "load_claim_check_prompt", lambda: (_ for _ in ()).throw(ValueError("prompt drift")))
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
    captured = capsys.readouterr()
    assert "preflight failed" in captured.err
    assert captured.out == ""

def test_source_drift_during_quiet_period_cannot_dispatch(monkeypatch):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, seconds): self._clock = lambda: 0.0
        async def before_call(self, label):
            monkeypatch.setattr(m, "load_claim_check_prompt", lambda: (
                m.PROJECT_ROOT / "evals/narrator/prompts/record-evidence-claim-check-v1.md", prepared.prompt + " drift"))
    class Gateway:
        observation = {}
        def __init__(self, **kwargs): pass
        async def generate_structured(self, request): pytest.fail("dispatch after prompt drift")
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "ClaimCheckObservationAdapter", Gateway)
    rows = []
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY), records=rows))
    assert rows == []

@pytest.mark.parametrize("argv", [
    ["--preflight", "--live"], ["--live"],
    ["--live", "--allow-synthetic-only", "--batch-id", "a0b0845d54a14d1da465c16d3763865b"],
    ["--preflight", "--max-output-tokens", "1536"], ["--preflight", "--case", "mara"],
])
def test_cli_refuses_scope_or_batch_changes_before_preflight(monkeypatch, argv):
    monkeypatch.setattr(m, "prepare_experiment", lambda: pytest.fail("preflight after disallowed CLI options"))
    with pytest.raises(SystemExit):
        m.main(argv)

def test_previous_executors_observer_and_prompt_remain_frozen():
    import hashlib
    frozen = {
        "scripts/evaluate_narrator_record_quotes.py": "f302b423adf931557877a98d262873c102f9843e45e0062b33bf02e0ebb40cdd",
        "scripts/narrator_record_quote_evidence.py": "15083d0bfa8fe9df88784efd5980f54cdaafc5133ce9125933b98ed234ff3f58",
        "evals/narrator/prompts/record-evidence-target-quotes-v1.md": "02ed8a68a84384bfaf33a82c844f56415f5c8c9a847c11c82e6d08a0a237ec4c",
        "scripts/evaluate_narrator_record_target_spans.py": "c5c75819e781477c4786b7ed6da2ab8a6cb1402ebf98fda0702e0db0ab726dc1",
        "scripts/narrator_record_budget_observer.py": "36a119fb82702580aeaf9ed6608679ec7fecb85faab57334d8eb5ea0f6f06060",
        "evals/narrator/prompts/record-evidence-target-spans-v1.md": "aed7e269b11b88379d09221a071f598dfe1fb845be2a65ecb3bbe479d76e91a4",
    }
    for name, sha in frozen.items():
        assert hashlib.sha256((m.PROJECT_ROOT / name).read_bytes()).hexdigest() == sha
    assert {"file": "scripts/narrator_record_budget_observer.py", "sha256": frozen["scripts/narrator_record_budget_observer.py"]} in m.prepare_experiment().metadata["inputs"]["implementation"]


def test_preflight_changes_only_system_and_preserves_schema_user_budget(monkeypatch):
    from scripts import evaluate_narrator_record_quotes as baseline
    monkeypatch.setattr(m.os, "environ", {})
    monkeypatch.setattr(m, "ClaimCheckObservationAdapter", lambda **kwargs: pytest.fail("client during preflight"))
    prepared = m.prepare_experiment()
    body = m._fixed_payload(m._make_request(prepared))
    previous = baseline._fixed_payload(baseline._make_request(baseline.prepare_experiment()))
    frozen = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))["request"]["body"]
    assert body == frozen
    assert set(body) == set(previous)
    assert {key for key in body if body[key] != previous[key]} == {"messages"}
    restored = copy.deepcopy(body)
    restored["messages"][0]["content"] = previous["messages"][0]["content"]
    assert restored == previous
    assert m._canonical_sha(previous) == "573bfe7589a2efefb75435c6f38a6127c87909170798523780e8a18da1969d89"
    assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256
    assert body["max_completion_tokens"] == 3072
    assert body["messages"][1] == previous["messages"][1]
    assert body["response_format"]["json_schema"]["name"] == "RecordQuoteEvidenceProposal"
    assert len(prepared.cases) == len(prepared.packets) == 1
    assert prepared.cases[0].case_id == "opening"
    assert prepared.metadata["purpose"] == prepared.metadata["probe_kind"] == "record_evidence_claim_check_probe"
    assert prepared.metadata["experiment_version"] == "record-evidence-claim-check-v1"
    inputs = prepared.metadata["inputs"]
    assert inputs["prompt"]["variant"] == "record-evidence-claim-check-v1"
    assert inputs["dossier"]["changed_payload_fields"] == ["messages[0].content"]
    assert inputs["cases"][0]["generation_context"]["version"] == "record-evidence-v1"
    assert inputs["cases"][0]["generation_context"]["user_packet_sha256"] == "42eb962a2042c00b2030d5cb63b1f7e1f17894158e5df61cdcad0d317c32a480"
    assert inputs["support_resolution_policy"]["method"] == "unique_exact_target_quote"
    assert inputs["support_resolution_policy"]["quote_protocol"] == "record-evidence-target-quotes-v1"
    assert inputs["response_schema_sha256"] == "225adcde7c70dbd5be868b06a8731fc59f00bf11de80cc9639a88d7573db15d8"
    assert inputs["provider_schema_sha256"] == "fe5e9738d12ca0b094643c04e45cdbf87aee17588b0889f75927ec8df663cff2"
    assert any(item["file"] == "scripts/narrator_record_quote_evidence.py" for item in inputs["implementation"])


def test_unique_quote_resolves_to_audit_offsets_without_rewriting_original_envelope(monkeypatch):
    value = envelope()
    value["records"]["t"] = ["Quem ou o que está observando?"]
    value["supports"] = [
        {"p": "/s", "c": "sussurro distante", "s": ["n0"], "m": "established"},
        {"p": "/t/0", "c": value["records"]["t"][0], "s": ["n0"], "m": "suggested"},
    ]
    before = copy.deepcopy(value)
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(value)))
    row = run()[0]
    assert len(calls) == 1
    assert row["schema_valid"] is row["envelope_valid"] is True
    assert row["response_envelope"] == before
    assert row["derived_records"] == before["records"]
    audit = row["support_validation"]
    assert audit["quote_protocol"] == "record-evidence-target-quotes-v1"
    assert audit["validated_supports"][0]["quote"] == "sussurro distante"
    assert "b" not in row["response_envelope"]["supports"][0]
    assert "e" not in row["response_envelope"]["supports"][0]
    summary = m.summarize([row])
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["support_coverage_review"] == {"status": "not_performed", "approval": None}
    assert summary["automated_gates_passed"] is False


@pytest.mark.parametrize("text,quote", [
    ("Um sussurro distante ecoa no corredor.", "Sussurro distante"),
    ("Um sussurro distante ecoa no corredor.", "sussurro  distante"),
    ("Um sussurro distante ecoa no corredor.", "ausente"),
    ("Eco distante, eco distante.", "distante"),
])
def test_missing_or_ambiguous_quote_is_rejected_without_repair(monkeypatch, text, quote):
    value = envelope()
    value["records"]["s"] = text
    value["supports"] = [{"p": "/s", "c": quote, "s": ["n0"], "m": "established"}]
    before = copy.deepcopy(value)
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(value)))
    row = run()[0]
    assert len(calls) == 1
    assert row["schema_valid"] is True
    assert row["envelope_valid"] is row["final_schema_valid"] is row["admitted"] is False
    assert "envelope_error" in row
    assert row["response_envelope"] == before
    assert row["derived_records"] == before["records"]
    assert "support_validation" not in row and "composed_proposal" not in row
    assert m.summarize([row])["process_exit_code"] == 1


@pytest.mark.parametrize("value,schema_valid,envelope_valid", [
    (envelope(outcome="success"), True, True),
    (envelope(supports=[{"p": "/s", "c": "sussurro", "s": ["missing"], "m": "established"}]), True, False),
    (envelope(supports=[{"p": "/s", "b": 0, "e": 197, "s": ["n0"], "m": "established"}]), False, False),
])
def test_quote_structure_cannot_bypass_origin_validation_or_admission(monkeypatch, value, schema_valid, envelope_valid):
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(value)))
    row = run()[0]
    assert len(calls) == 1
    assert row["schema_valid"] is schema_valid
    assert row["envelope_valid"] is envelope_valid
    assert row["admitted"] is False
    assert m.summarize([row])["process_exit_code"] == 1


def test_observer_rejects_previous_system_and_second_call_without_global_patch():
    from scripts import evaluate_narrator_record_quotes as baseline
    from scripts.narrator_record_budget_observer import APPROVED_PAYLOAD_SHA256
    prepared = m.prepare_experiment()
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    gateway = m.ClaimCheckObservationAdapter(base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(prepared.candidate, prepared.target),
        api_key=SecretStr(KEY), reasoning_effort="low", transport=httpx.MockTransport(handler))
    previous = baseline._make_request(baseline.prepare_experiment())
    wrong = previous.model_copy(update={"target": prepared.target})
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(wrong))
    assert calls == []
    asyncio.run(gateway.generate_structured(m._make_request(prepared)))
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(m._make_request(prepared)))
    assert len(calls) == 1
    assert APPROVED_PAYLOAD_SHA256 == "90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f"


@pytest.mark.parametrize("mutation", ["missing", "metadata", "body"])
def test_new_prompt_loader_requires_its_frozen_identity_and_text(monkeypatch, tmp_path, mutation):
    original = m.PROMPT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "claim-check.md"
    if mutation == "metadata":
        path.write_text(original.replace("name: record-evidence-claim-check-v1", "name: record-evidence-target-quotes-v1"), encoding="utf-8")
    elif mutation == "body":
        path.write_text(original + " altered", encoding="utf-8")
    monkeypatch.setattr(m, "PROMPT_PATH", path)
    with pytest.raises((ValueError, FileNotFoundError)):
        m.load_claim_check_prompt()


def test_main_quiet_period_cancellation_persists_only_claim_check_skip(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    class Pacer:
        def __init__(self, seconds): self._clock = lambda: 0.0
        async def before_call(self, label): raise asyncio.CancelledError()
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    calls = install(monkeypatch, lambda request: pytest.fail("dispatch after quiet-period cancellation"))
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 130
    rows = [json.loads(line) for line in (tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    assert calls == [] and len(rows) == 1
    assert rows[0]["kind"] == "record_evidence_claim_check_skip"
    assert rows[0]["call_made"] is False and rows[0]["skipped_reason"] == "cancelled"
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["summary"]
    assert summary["calls_made"] == 0 and summary["cases_skipped"] == 1
    assert summary["process_exit_code"] == 130
    assert summary["operational_probe_passed"] is False
    assert KEY not in json.dumps(rows) + json.dumps(summary)
