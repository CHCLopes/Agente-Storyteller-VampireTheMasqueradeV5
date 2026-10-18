"""Offline differences for the two frozen summary-attachment cases."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from api.llm.contract import LLMInvocationError
from scripts import evaluate_narrator_summary_attachment as m
from scripts.evaluate_narrator_summary_attachment import SummaryAttachmentObservationAdapter

KEY = "SYNTHETIC_ATTACHMENT_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_ATTACHMENT_REASONING_NEVER_PERSIST"


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real = m.shared._CallPacer
    elapsed = [0.0]
    async def sleep(seconds): elapsed[0] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer", lambda interval: real(
        interval, _clock=lambda: elapsed[0], _sleeper=sleep))
    return elapsed


def structure(case_id):
    return {"summary": "  Uma luminária de carcaça verde ilumina o painel.  " if case_id == m.CASE_IDS[0]
            else "  Uma luminária emite luz verde sobre o painel.  "}


def completion(case_id, *, value=None, model=m.GROQ_QWEN_MODEL_ID, finish="stop", usage=True):
    result = {"model": model, "id": "synthetic-attachment", "choices": [{"finish_reason": finish,
        "message": {"content": json.dumps(structure(case_id) if value is None else value), "reasoning": LEAK}}]}
    if usage: result["usage"] = {"prompt_tokens": 400, "completion_tokens": 60, "total_tokens": 460}
    return result


def install(monkeypatch, pacing, handler=None, *, transform=None):
    state = {"calls": [], "requests": [], "instances": []}
    class Gateway(SummaryAttachmentObservationAdapter):
        def __init__(self, **kwargs):
            case_id = kwargs["case_id"]
            async def dispatch(request):
                state["calls"].append({"case_id": case_id, "request": request, "started": pacing[0]})
                return handler(case_id, request) if handler else httpx.Response(200, json=completion(case_id))
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
            state["instances"].append(self)
        async def generate_structured(self, request):
            state["requests"].append(request)
            result = await super().generate_structured(request)
            return transform(self._case_id, result) if transform else result
        async def generate_text(self, request): pytest.fail("No diagnostic or fallback")
    monkeypatch.setattr(m, "SummaryAttachmentObservationAdapter", Gateway)
    return state


def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))


def read_artifacts(path):
    rows = [json.loads(line) for line in (path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    doc = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    return rows, doc


def main_at(monkeypatch, path):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: path)
    return m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())])


def valid_rows():
    return [{"kind": "summary_attachment_call", "case_id": case_id, "call_made": True,
             "schema_valid": True, "route_status": "verified", "summary_text": structure(case_id)["summary"],
             "instruction_measurements": m.contract.measure_summary_words(structure(case_id)["summary"])}
            for case_id in m.CASE_IDS]


def test_preflight_exact_two_new_user_bodies_and_unchanged_summary_system_schema(monkeypatch):
    monkeypatch.setattr(m, "SummaryAttachmentObservationAdapter", lambda **kwargs: pytest.fail("preflight client"))
    p = m.prepare_experiment()
    dossier = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    old = json.loads((m.PROJECT_ROOT / "evals/narrator/reports/record-summary-only-dossier-94a95216-2026-09-07.json").read_text(encoding="utf-8"))["request"]["body"]
    assert tuple(c["case_id"] for c in p.cases) == m.CASE_IDS
    for index, case in enumerate(p.cases):
        body = m._fixed_payload(m._make_request(p, index))
        assert body == dossier["requests"][index]["body"]
        assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256_BY_CASE[case["case_id"]]
        restored = copy.deepcopy(body); restored["messages"][1] = old["messages"][1]
        assert restored == old and body["messages"][1] != old["messages"][1]
        assert body["reasoning_effort"] == "none" and "include_reasoning" not in body
        assert hashlib.sha256(p.packets[index].encode()).hexdigest() == m.USER_PACKET_SHA256_BY_CASE[case["case_id"]]
        packet = json.loads(p.packets[index].split("\n", 1)[1])
        assert packet == case and set(packet) == {"schema", "case_id", "synthetic_only", "origin", "narrative", "source_units"}
        assert "".join(u["text"] for u in packet["source_units"]) == packet["narrative"]
        assert m.contract.measure_summary_words(case["narrative"])["word_count"] == 32
        source = p.metadata["inputs"]["cases"][index]["source"]
        assert source["origin"] == "agent_authored_synthetic_case" and source["case_index"] == index
        assert not {"candidate_id", "model", "batch_id"}.intersection(source)
    assert p.metadata["inputs"]["stopping_policy"] == dossier["stopping_policy"]
    assert p.metadata["max_calls"] == 2 and p.metadata["summary_generation_parameters"]["max_total_output_tokens"] == 6144
    assert p.metadata["inputs"]["provider_schema_sha256"] == m.RESPONSE_SCHEMA_SHA256
    assert p.metadata["inputs"]["prompt"]["variant"] == "record-summary-only-v1"
    assert [c["generation_context"]["budget"]["estimated_tokens"] for c in p.metadata["inputs"]["cases"]] == [170,168]


def test_native_pair_has_ordered_independent_observations_and_literal_measurements(monkeypatch, pacing):
    def handler(case_id, request):
        first = case_id == m.CASE_IDS[0]
        return httpx.Response(200, json=completion(case_id, usage=first),
            headers={"x-request-id": "req_" + "a" * 26} if first else {})
    state = install(monkeypatch, pacing, handler)
    rows = run(); summary = m.summarize(rows)
    assert [c["case_id"] for c in state["calls"]] == list(m.CASE_IDS)
    assert len(state["instances"]) == 2 and state["instances"][0] is not state["instances"][1]
    assert rows[0]["provider_observation"]["request_id"] == "req_" + "a" * 26
    assert rows[1]["provider_observation"]["request_id"] is None
    assert rows[1]["provider_observation"]["usage"]["reasoning_tokens"] is None
    for index, row in enumerate(rows):
        assert row["response_structure"] == structure(m.CASE_IDS[index])
        assert row["summary_text"] == structure(m.CASE_IDS[index])["summary"]
        assert row["instruction_measurements"] == m.contract.measure_summary_words(row["summary_text"])
        assert summary["case_measurements"][index] == {"case_id": row["case_id"], "instruction_measurements": row["instruction_measurements"]}
        assert m._canonical_sha(json.loads(state["calls"][index]["request"].content)) == m.PROPOSED_BODY_SHA256_BY_CASE[row["case_id"]]
    assert summary["provider_observation"] is None and len(summary["provider_observations"]) == 2
    assert summary["usage_aggregate"]["status"] == "partial"
    assert summary["process_exit_code"] == 0 and summary["calls_made"] == summary["schema_valid"] == 2
    assert summary["cases_skipped"] == 0 and summary["route_verification"]["verified_calls"] == 2
    assert summary["semantic_fidelity_review"] == {"status":"not_performed", "approval":None}
    assert summary["automated_gates_passed"] is summary["runtime_promoted"] is False
    removed = {"projection", "projection_valid", "admitted", "final_schema_valid", "open_questions", "support_coverage_review"}
    assert not removed.intersection(summary) and all(not removed.intersection(r) for r in rows)
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_initial_and_between_start_waits_include_post_wait_checks_before_deadline(monkeypatch, pacing):
    start = m.utc_now()
    monkeypatch.setattr(m, "utc_now", lambda: start + timedelta(seconds=pacing[0]))
    check = m._check_prepared; count = [0]
    def delayed_check(p):
        check(p); count[0] += 1
        if count[0] in {3,5}: pacing[0] += 3.0
    monkeypatch.setattr(m, "_check_prepared", delayed_check)
    def handler(case_id, request):
        pacing[0] += 2.0
        return httpx.Response(200, json=completion(case_id))
    state = install(monkeypatch, pacing, handler)
    run()
    assert [c["started"] for c in state["calls"]] == [63.0,126.0]
    assert [r.deadline for r in state["requests"]] == [start + timedelta(seconds=123), start + timedelta(seconds=186)]
    assert pacing[0] == 128.0


@pytest.mark.parametrize("failure", ["http400", "http429", "http503", "length", "schema", "route"])
def test_first_operational_failure_stops_second_and_preserves_partial_measurement(monkeypatch, pacing, failure):
    def handler(case_id, request):
        assert case_id == m.CASE_IDS[0]
        if failure.startswith("http"):
            return httpx.Response(int(failure[4:]), json={"error":{"message":LEAK,"code":"json_validate_failed","failed_generation":LEAK}})
        return httpx.Response(200, json=completion(case_id,
            value={"summary":True} if failure == "schema" else None,
            model="unapproved" if failure == "route" else m.GROQ_QWEN_MODEL_ID,
            finish="length" if failure == "length" else "stop"))
    state = install(monkeypatch, pacing, handler)
    rows = run(); summary = m.summarize(rows)
    assert len(state["calls"]) == len(state["instances"]) == 1
    assert rows[1] == {"kind":"summary_attachment_skip","case_id":m.CASE_IDS[1],"call_made":False,"skipped_reason":"previous_operational_failure"}
    assert rows[0]["schema_valid"] is False and "summary_text" not in rows[0]
    assert summary["case_measurements"] == [{"case_id":i,"instruction_measurements":None} for i in m.CASE_IDS]
    assert summary["calls_made"] == summary["cases_skipped"] == 1
    assert summary["provider_observation"] == summary["provider_observations"][0]["observation"]
    assert summary["process_exit_code"] == (2 if failure in {"http429","http503"} else 1)
    assert LEAK not in json.dumps(rows) and KEY not in json.dumps(rows)


@pytest.mark.parametrize("failure", ["http429", "schema", "route"])
def test_second_failure_keeps_first_success_and_makes_no_third_call(monkeypatch, pacing, failure):
    def handler(case_id, request):
        if case_id == m.CASE_IDS[0]: return httpx.Response(200,json=completion(case_id))
        if failure == "http429": return httpx.Response(429,json={"error":{"message":LEAK}})
        return httpx.Response(200,json=completion(case_id,value={"summary":"short"} if failure == "schema" else None,
            model=None if failure == "route" else m.GROQ_QWEN_MODEL_ID))
    state = install(monkeypatch,pacing,handler); rows=run(); summary=m.summarize(rows)
    assert len(state["calls"]) == 2 and summary["cases_skipped"] == 0
    assert rows[0]["schema_valid"] is True and rows[1]["schema_valid"] is False
    assert summary["case_measurements"][0]["instruction_measurements"] is not None
    assert summary["case_measurements"][1]["instruction_measurements"] is None
    assert summary["process_exit_code"] == (2 if failure == "http429" else 1)
    assert summary["provider_observation"] is None


@pytest.mark.parametrize("first_text", [" ".join(["palavra"]*32), "A luminária emite luz verde sobre o painel."])
def test_word_limit_and_semantic_counterexample_do_not_block_second_case(monkeypatch,pacing,first_text):
    state=install(monkeypatch,pacing,lambda case_id,request:httpx.Response(200,json=completion(case_id,
        value={"summary":first_text} if case_id==m.CASE_IDS[0] else None)))
    rows=run(); summary=m.summarize(rows)
    assert len(state["calls"]) == 2 and summary["process_exit_code"] == 0
    assert rows[0]["summary_text"] == first_text
    assert summary["case_measurements"][0]["instruction_measurements"] == m.contract.measure_summary_words(first_text)
    assert summary["semantic_fidelity_review"]["approval"] is None


@pytest.mark.parametrize("value", [True,"short","x"*601])
def test_forged_model_stops_pair_without_retaining_invalid_value(monkeypatch,pacing,value):
    bad=m.contract.SummaryOnlyProposal.model_construct(summary=value)
    state=install(monkeypatch,pacing,transform=lambda case_id,result:result.model_copy(update={"value":bad}))
    rows=run()
    assert len(state["calls"]) == 1 and rows[0]["schema_valid"] is False
    assert rows[0]["schema_error"] == {"code":"summary_attachment_schema_invalid"}
    assert "response_structure" not in rows[0] and rows[1]["call_made"] is False


def test_route_evidence_mismatch_precedes_even_forged_schema(monkeypatch,pacing):
    def transform(case_id,result):
        provenance=result.evidence.provenance.model_copy(update={"invocation_id":str(uuid4())})
        return result.model_copy(update={"evidence":result.evidence.model_copy(update={"provenance":provenance}),"value":object()})
    state=install(monkeypatch,pacing,transform=transform); rows=run()
    assert len(state["calls"]) == 1 and rows[0]["route_status"] == "mismatch"
    assert rows[0]["schema_valid"] is False and "schema_error" not in rows[0]
    assert "summary_text" not in rows[0]


@pytest.mark.parametrize("when", ["initial_wait","second_wait","second_inflight"])
def test_main_cancel_preserves_ordered_calls_and_skips(monkeypatch,tmp_path,pacing,when):
    if when != "second_inflight":
        real=m.shared._CallPacer
        def pacer(interval):
            value=real(interval); original=value.before_call; seen=[0]
            async def before(label):
                seen[0]+=1
                if seen[0]==(1 if when=="initial_wait" else 2): raise asyncio.CancelledError()
                await original(label)
            value.before_call=before
            return value
        monkeypatch.setattr(m.shared,"_CallPacer",pacer)
    def handler(case_id,request):
        if when=="second_inflight" and case_id==m.CASE_IDS[1]: raise asyncio.CancelledError()
        return httpx.Response(200,json=completion(case_id))
    state=install(monkeypatch,pacing,handler)
    assert main_at(monkeypatch,tmp_path)==130
    rows,doc=read_artifacts(tmp_path)
    expected={"initial_wait":0,"second_wait":1,"second_inflight":2}[when]
    assert len(state["calls"])==expected and len(rows)==2
    assert doc["summary"]["calls_made"]==expected and doc["summary"]["cases_skipped"]==2-expected
    assert tuple(r["case_id"] for r in rows)==m.CASE_IDS
    assert doc["summary"]==m.summarize(rows,status="cancelled")
    if expected: assert rows[0]["summary_text"]==structure(m.CASE_IDS[0])["summary"]
    assert KEY not in json.dumps(doc)+json.dumps(rows)


@pytest.mark.parametrize("failed_case", [0,1])
def test_local_measurement_error_retains_schema_text_and_stops_remaining(monkeypatch,tmp_path,pacing,failed_case):
    state=install(monkeypatch,pacing); real=m.contract.measure_summary_words
    def measure(text):
        if text==structure(m.CASE_IDS[failed_case])["summary"]: raise RuntimeError(LEAK)
        return real(text)
    monkeypatch.setattr(m.contract,"measure_summary_words",measure)
    assert main_at(monkeypatch,tmp_path)==3
    rows,doc=read_artifacts(tmp_path); row=rows[failed_case]
    assert len(state["calls"])==failed_case+1 and row["schema_valid"] is True
    assert row["response_structure"]==structure(m.CASE_IDS[failed_case])
    assert row["summary_text"]==structure(m.CASE_IDS[failed_case])["summary"]
    assert row["local_error"]=={"code":"local_summary_attachment_failure"}
    assert doc["summary"]["case_measurements"][failed_case]["instruction_measurements"] is None
    assert doc["summary"]["operational_probe_passed"] is False
    assert LEAK not in json.dumps(rows)+json.dumps(doc)


def test_main_success_roundtrip_exact_summary_metadata_and_two_literal_responses(monkeypatch,tmp_path,pacing):
    state=install(monkeypatch,pacing)
    assert main_at(monkeypatch,tmp_path)==0
    rows,doc=read_artifacts(tmp_path)
    assert len(state["calls"])==len(rows)==2 and doc["summary"]==m.summarize(rows)
    assert doc["inputs"]==m.prepare_experiment().metadata["inputs"]
    assert all(row["batch_id"]==doc["batch_id"] for row in rows)
    assert all(row["response_structure"]==structure(row["case_id"]) for row in rows)
    assert doc["summary"]["usage_aggregate"]["status"]=="reported"
    assert doc["summary"]["cost_aggregate"]["status"]=="unavailable"
    assert doc["summary"]["cost_aggregate"]["total_amount"] is None
    assert doc["summary"]["cost_aggregate"]["reported_amount_subtotal"] is None
    assert KEY not in json.dumps(doc)+json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("mutation", ["order","source_type","packet","metadata_type","candidate","target"])
def test_prepared_drift_refuses_gateway_before_key_or_dispatch(monkeypatch,mutation):
    p=m.prepare_experiment()
    if mutation=="order": p=replace(p,cases=tuple(reversed(p.cases)))
    elif mutation=="source_type": p.cases[1]["synthetic_only"]=1
    elif mutation=="packet": p=replace(p,packets=(p.packets[0],p.packets[1]+" drift"))
    elif mutation=="metadata_type": p.metadata["runtime_promoted"]=0
    elif mutation=="candidate": p=replace(p,candidate=replace(p.candidate,reasoning_effort="low"))
    else: p=replace(p,target=p.target.model_copy(update={"profile":"other"}))
    monkeypatch.setattr(m,"SummaryAttachmentObservationAdapter",lambda **kwargs:pytest.fail("gateway after drift"))
    with pytest.raises(ValueError): asyncio.run(m.evaluate_probe(p,api_key=SecretStr(KEY)))


@pytest.mark.parametrize("which", ["CORPUS_SHA256","DOSSIER_SHA256"])
def test_drift_during_second_wait_keeps_first_result_and_skips_second(monkeypatch,tmp_path,pacing,which):
    real=m.shared._CallPacer
    def pacer(interval):
        value=real(interval); before=value.before_call; seen=[0]
        async def wait(label):
            seen[0]+=1; await before(label)
            if seen[0]==2: monkeypatch.setattr(m,which,"0"*64)
        value.before_call=wait
        return value
    monkeypatch.setattr(m.shared,"_CallPacer",pacer)
    state=install(monkeypatch,pacing)
    assert main_at(monkeypatch,tmp_path)==3
    rows,doc=read_artifacts(tmp_path)
    assert len(state["calls"])==1 and rows[0]["schema_valid"] is True
    assert rows[1]["call_made"] is False and doc["summary"]["case_measurements"][1]["instruction_measurements"] is None


@pytest.mark.parametrize("which", ["CORPUS_SHA256","DOSSIER_SHA256","PROMPT_SHA256"])
def test_preflight_fingerprint_failure_precedes_credential_access(monkeypatch,capsys,which):
    class Environment(dict):
        def get(self,key,*args):
            if key=="GROQ_API_KEY": pytest.fail("credential read")
            return super().get(key,*args)
    monkeypatch.setattr(m.os,"environ",Environment())
    monkeypatch.setattr(m,which,"0"*64)
    assert m.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4())])==3
    assert "preflight failed" in capsys.readouterr().err


def test_preflight_stdout_is_one_json_without_key_or_artifacts(monkeypatch,capsys):
    class Environment(dict):
        def get(self,key,*args):
            if key=="GROQ_API_KEY": pytest.fail("preflight credential")
            return super().get(key,*args)
    monkeypatch.setattr(m.os,"environ",Environment())
    monkeypatch.setattr(m,"_new_run_directory",lambda *args:pytest.fail("preflight artifacts"))
    assert m.main(["--preflight"])==0
    output=capsys.readouterr(); value=json.loads(output.out)
    assert value["max_calls"]==2 and output.err=="" and len(output.out.splitlines())==1


@pytest.mark.parametrize("mutation", ["reverse","duplicate","call_type","schema_type","skip_before_call","first_failed","first_missing_measurement","measurement_bool","wrong_kind"])
def test_summary_rejects_incoherent_order_stop_rule_and_typed_outcomes(mutation):
    rows=valid_rows()
    if mutation=="reverse": rows.reverse()
    elif mutation=="duplicate": rows[1]=copy.deepcopy(rows[0])
    elif mutation=="call_type": rows[0]["call_made"]=1
    elif mutation=="schema_type": rows[1]["schema_valid"]=1
    elif mutation=="skip_before_call": rows[0].update(kind="summary_attachment_skip",call_made=False)
    elif mutation=="first_failed": rows[0]["schema_valid"]=False
    elif mutation=="first_missing_measurement": rows[0].pop("instruction_measurements")
    elif mutation=="measurement_bool": rows[1]["instruction_measurements"]["within_word_limit"]=1
    else: rows[1]["kind"]="summary_only_call"
    with pytest.raises(ValueError): m.summarize(rows)


@pytest.mark.parametrize("status", [None,True,0,"unexpected"])
def test_summary_status_is_a_closed_typed_domain(status):
    with pytest.raises(ValueError): m.summarize(valid_rows(),status=status)


@pytest.mark.parametrize("wrong", ["case","operation","body"])
def test_case_bound_observer_refuses_cross_case_then_allows_only_one_exact_dispatch(wrong):
    p=m.prepare_experiment(); calls=[]
    def handler(request):
        calls.append(request); return httpx.Response(200,json=completion(m.CASE_IDS[0]))
    gateway=SummaryAttachmentObservationAdapter(case_id=m.CASE_IDS[0],base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(p.candidate,p.target),api_key=SecretStr(KEY),reasoning_effort="none",
        transport=httpx.MockTransport(handler))
    exact=m._make_request(p,0)
    altered=m._make_request(p,1)
    if wrong=="operation": altered=exact.model_copy(update={"operation":"summary-only.archive-vibration"})
    elif wrong=="body": altered=exact.model_copy(update={"messages":(exact.messages[0],altered.messages[1])})
    with pytest.raises(LLMInvocationError): asyncio.run(gateway.generate_structured(altered))
    assert calls==[]
    asyncio.run(gateway.generate_structured(exact))
    with pytest.raises(LLMInvocationError): asyncio.run(gateway.generate_structured(m._make_request(p,0)))
    assert len(calls)==1


@pytest.mark.parametrize("argv", [
    ["--preflight","--case","observatory-b"], ["--preflight","--max-output-tokens","6144"],
    ["--preflight","--repetitions","2"], ["--preflight","--reasoning-effort","low"],
    ["--live"], ["--preflight","--api-key-env","OTHER_KEY"],
])
def test_mutable_cli_scope_rejected_before_preflight(monkeypatch,argv):
    monkeypatch.setattr(m,"prepare_experiment",lambda:pytest.fail("preflight after invalid CLI"))
    with pytest.raises(SystemExit): m.main(argv)
