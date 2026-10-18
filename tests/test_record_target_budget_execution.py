"""Offline boundaries for the single-opening target-spans observation at 3072."""


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


from scripts import evaluate_narrator_record_target_budget as m


from scripts.evaluate_narrator_record_target_budget import TargetBudgetObservationAdapter


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
    class Gateway(TargetBudgetObservationAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
    monkeypatch.setattr(m, "TargetBudgetObservationAdapter", Gateway)
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
    assert rows[0]["kind"] == "record_evidence_target_budget_call"
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
    monkeypatch.setattr(m,"TargetBudgetObservationAdapter",forbidden)
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
    monkeypatch.setattr(m,"TargetBudgetObservationAdapter",Gateway)
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
    monkeypatch.setattr(m,"TargetBudgetObservationAdapter",Gateway)
    rows=[]
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY),records=rows))
    assert rows==[]


@pytest.mark.parametrize("span", [(3, 25), (0, 197)])
def test_invalid_target_spans_are_preserved_and_rejected_without_repair(monkeypatch, span):
    value = envelope(supports=[{"p": "/l", "b": span[0], "e": span[1],
        "s": ["n0"], "m": "established"}])
    before = copy.deepcopy(value)
    calls = install(monkeypatch, lambda req: httpx.Response(200, json=completion(value)))
    row = run()[0]
    assert len(calls) == 1
    assert row["schema_valid"] is True
    assert row["envelope_valid"] is row["final_schema_valid"] is row["admitted"] is False
    assert row["envelope_error"] == {"code": "record_evidence_span_invalid"}
    assert row["response_envelope"] == before
    assert row["derived_records"] == before["records"]
    assert "composed_proposal" not in row
    assert m.summarize([row])["process_exit_code"] == 1


def test_valid_target_spans_and_question_text_remain_exact_without_semantic_self_approval(monkeypatch):
    value = envelope()
    value["records"]["t"] = ["Quem ou o que está observando?"]
    value["supports"] = [
        {"p": "/l", "b": 0, "e": len(value["records"]["l"]), "s": ["n0"], "m": "established"},
        {"p": "/t/0", "b": 0, "e": len(value["records"]["t"][0]), "s": ["n0"], "m": "suggested"},
    ]
    before = copy.deepcopy(value)
    install(monkeypatch, lambda req: httpx.Response(200, json=completion(value)))
    row = run()[0]
    assert row["envelope_valid"] is True
    assert row["response_envelope"] == before
    assert row["derived_records"] == before["records"]
    summary = m.summarize([row])
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["support_coverage_review"] == {"status": "not_performed", "approval": None}
    assert summary["automated_gates_passed"] is False


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
    assert document["experiment_version"] == "record-evidence-target-spans-3072-v1"
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
        monkeypatch.setattr(m, "PROMPT_SHA256", "0" * 64)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
    captured = capsys.readouterr()
    assert "preflight failed" in captured.err
    assert captured.out == ""


def test_preflight_changes_only_budget_and_keeps_prompt_and_user_identity(monkeypatch):
    from scripts import evaluate_narrator_record_target_spans as baseline
    monkeypatch.setattr(m.os, "environ", {})
    monkeypatch.setattr(m, "TargetBudgetObservationAdapter", lambda **kwargs: pytest.fail("client during preflight"))
    prepared = m.prepare_experiment()
    body = m._fixed_payload(m._make_request(prepared))
    frozen = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))["request"]["body"]
    assert body == frozen
    previous = baseline._fixed_payload(baseline._make_request(baseline.prepare_experiment()))
    assert set(body) == set(previous)
    assert [key for key in body if body[key] != previous[key]] == ["max_completion_tokens"]
    assert previous["max_completion_tokens"] == 1536
    assert body["max_completion_tokens"] == 3072
    assert m._canonical_sha(previous) == "8138c098ec49cdc768e7c5d9fe19cc952001939f1c54af11bdb1241762526a09"
    assert m._canonical_sha(body) == "5e376cb4cdee903b0f1a5bbcd3a14fa181d966656102f4c4985d87b4eb9ea186"
    assert len(prepared.cases) == len(prepared.packets) == 1
    assert prepared.cases[0].case_id == "opening"
    assert prepared.metadata["purpose"] == prepared.metadata["probe_kind"] == "record_evidence_target_budget_probe"
    assert prepared.metadata["experiment_version"] == "record-evidence-target-spans-3072-v1"
    inputs = prepared.metadata["inputs"]
    assert inputs["prompt"]["variant"] == m.PROMPT_VARIANT == "record-evidence-target-spans-v1"
    assert inputs["prompt"]["sha256"] == "fdba32bb00dd20144ec5553d72635c3a2388fee9c4621486f3bddd6f3b1721cb"
    assert inputs["dossier"]["changed_payload_fields"] == ["max_completion_tokens"]
    assert inputs["dossier"]["sha256"] == "ae30f021f344c49e97a901685a591602755e836885b890d7e469dad8670f88d0"
    assert inputs["cases"][0]["generation_context"]["version"] == "record-evidence-v1"
    assert inputs["cases"][0]["generation_context"]["user_packet_sha256"] == "42eb962a2042c00b2030d5cb63b1f7e1f17894158e5df61cdcad0d317c32a480"
    params = prepared.metadata["evidence_generation_parameters"]
    assert params["requested"]["max_output_tokens"] == params["transmitted"]["max_output_tokens"] == params["max_total_output_tokens"] == 3072
    assert params["deadline_seconds"] == params["minimum_inter_call_delay_seconds"] == 60


def test_source_drift_during_quiet_period_cannot_dispatch(monkeypatch):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, seconds): self._clock = lambda: 0.0
        async def before_call(self, label):
            monkeypatch.setattr(m, "load_target_spans_prompt", lambda: (
                m.PROMPT_PATH, prepared.prompt + " drift"))
    class Gateway:
        observation = {}
        def __init__(self, **kwargs): pass
        async def generate_structured(self, request): pytest.fail("dispatch after prompt drift")
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "TargetBudgetObservationAdapter", Gateway)
    rows = []
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY), records=rows))
    assert rows == []


@pytest.mark.parametrize("budget", [1536, 3073])
def test_observer_rejects_other_budgets_and_second_valid_request_without_global_patch(budget):
    from scripts.narrator_record_budget_observer import APPROVED_PAYLOAD_SHA256
    from api.llm.contract import GenerationParameters
    prepared = m.prepare_experiment()
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    gateway = m.TargetBudgetObservationAdapter(base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(prepared.candidate, prepared.target),
        api_key=SecretStr(KEY), reasoning_effort="low", transport=httpx.MockTransport(handler))
    request = m._make_request(prepared)
    wrong = request.model_copy(update={"parameters": GenerationParameters(temperature=0.65, max_output_tokens=budget)})
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(wrong))
    assert calls == []
    asyncio.run(gateway.generate_structured(request))
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(m._make_request(prepared)))
    assert len(calls) == 1
    assert APPROVED_PAYLOAD_SHA256 == "90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f"


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
        "scripts/evaluate_narrator_record_target_spans.py": "c5c75819e781477c4786b7ed6da2ab8a6cb1402ebf98fda0702e0db0ab726dc1",
        "scripts/narrator_record_budget_observer.py": "36a119fb82702580aeaf9ed6608679ec7fecb85faab57334d8eb5ea0f6f06060",
        "evals/narrator/prompts/record-evidence-target-spans-v1.md": "aed7e269b11b88379d09221a071f598dfe1fb845be2a65ecb3bbe479d76e91a4",
    }
    for name, sha in frozen.items():
        assert hashlib.sha256((m.PROJECT_ROOT / name).read_bytes()).hexdigest() == sha
    assert {"file": "scripts/narrator_record_budget_observer.py", "sha256": frozen["scripts/narrator_record_budget_observer.py"]} in m.prepare_experiment().metadata["inputs"]["implementation"]
