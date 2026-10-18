"""Offline tests of one-source/two-SYSTEM identity, sequencing and retained evidence."""
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
from scripts import evaluate_narrator_summary_relational as m
from scripts.evaluate_narrator_summary_relational import SummaryRelationalObservationAdapter

KEY = "SYNTHETIC_RELATIONAL_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_RELATIONAL_REASONING_NEVER_PERSIST"
TEXT = "  O espelho reflete a tapeçaria diante da janela fechada.  "


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real = m.shared._CallPacer
    elapsed = [0.0]
    async def sleep(seconds):
        elapsed[0] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer", lambda interval: real(
        interval, _clock=lambda: elapsed[0], _sleeper=sleep))
    return elapsed


def completion(*, text=TEXT, model=m.GROQ_QWEN_MODEL_ID, value=None):
    return {"model": model, "id": "synthetic-relational", "choices": [{"finish_reason": "stop",
        "message": {"content": json.dumps({"summary": text} if value is None else value), "reasoning": LEAK}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19}}


def install(monkeypatch, pacing, handler=None):
    state = {"calls": [], "requests": [], "instances": []}
    class Gateway(SummaryRelationalObservationAdapter):
        def __init__(self, **kwargs):
            arm_id = kwargs["arm_id"]
            async def dispatch(request):
                state["calls"].append({"arm_id": arm_id, "request": request, "started": pacing[0]})
                return handler(arm_id, request) if handler else httpx.Response(200, json=completion())
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
            state["instances"].append(self)
        async def generate_structured(self, request):
            state["requests"].append(request)
            return await super().generate_structured(request)
        async def generate_text(self, request):
            pytest.fail("No diagnostic or fallback")
    monkeypatch.setattr(m, "SummaryRelationalObservationAdapter", Gateway)
    return state


def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))


def main_at(monkeypatch, path):
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: path)
    return m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())])


def artifacts(path):
    rows = [json.loads(s) for s in (path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    return rows, json.loads((path / "summary.json").read_text(encoding="utf-8"))


def valid_rows():
    return [{"kind": "summary_relational_call", "arm_id": arm, "case_id": m.CASE_ID,
             "call_made": True, "schema_valid": True, "route_status": "verified", "summary_text": TEXT,
             "instruction_measurements": m.contract.measure_summary_words(TEXT)} for arm in m.ARM_IDS]


def test_keyless_preflight_two_systems_exactly_one_source_and_only_system_body_delta(monkeypatch, capsys):
    class Environment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY":
                pytest.fail("preflight credential read")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", Environment())
    monkeypatch.setattr(m, "SummaryRelationalObservationAdapter", lambda **kwargs: pytest.fail("preflight client"))
    prepared = m.prepare_experiment()
    dossier = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    bodies = [m._fixed_payload(m._make_request(prepared, index)) for index in range(2)]
    assert bodies == [r["body"] for r in dossier["requests"]]
    assert bodies[0]["messages"][1] == bodies[1]["messages"][1]
    assert bodies[0]["messages"][0] != bodies[1]["messages"][0]
    adjusted = copy.deepcopy(bodies[1])
    adjusted["messages"][0] = bodies[0]["messages"][0]
    assert adjusted == bodies[0]
    assert json.loads(prepared.packet.split("\n", 1)[1]) == prepared.case
    assert set(prepared.case) == {"schema", "case_id", "synthetic_only", "origin", "narrative", "source_units"}
    assert "".join(unit["text"] for unit in prepared.case["source_units"]) == prepared.case["narrative"]
    assert prepared.case["case_id"] == "gallery-reflection"
    assert bodies[0]["max_completion_tokens"] == bodies[1]["max_completion_tokens"] == 768
    assert bodies[0]["reasoning_effort"] == "none" and "include_reasoning" not in bodies[0]
    inputs = prepared.metadata["inputs"]
    assert "cases" not in inputs and "prompt" not in inputs and "corpus" not in inputs
    assert inputs["case"]["source"]["origin"] == "agent_authored_synthetic_case"
    assert [a["arm_id"] for a in inputs["arms"]] == ["control", "relational"]
    assert [a["prompt"]["variant"] for a in inputs["arms"]] == ["record-summary-budget-v1", "record-summary-relational-v1"]
    assert all(a["case_id"] == m.CASE_ID for a in inputs["arms"])
    assert prepared.metadata["protocol"] == "record-summary-only-v1"
    assert prepared.metadata["summary_generation_parameters"]["max_total_output_tokens"] == 1536
    assert m.main(["--preflight"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == prepared.metadata and output.err == ""


def test_native_pair_retains_literal_and_arm_provenance_without_word_limit_block(monkeypatch, tmp_path, pacing):
    long_text = " ".join(["palavra"] * 32)
    state = install(monkeypatch, pacing, lambda arm, request: httpx.Response(
        200, json=completion(text=long_text if arm == "control" else TEXT)))
    assert main_at(monkeypatch, tmp_path) == 0
    rows, doc = artifacts(tmp_path)
    summary = doc["summary"]
    assert [call["arm_id"] for call in state["calls"]] == list(m.ARM_IDS)
    assert len(state["instances"]) == 2 and state["instances"][0] is not state["instances"][1]
    assert all(row["case_id"] == m.CASE_ID for row in rows)
    assert rows[0]["source"] == rows[1]["source"] == doc["inputs"]["case"]["source"]
    assert rows[0]["generation_context"] == rows[1]["generation_context"]
    assert [row["generation_prompt"] for row in rows] == [a["prompt"] for a in doc["inputs"]["arms"]]
    assert rows[0]["summary_text"] == long_text and rows[1]["summary_text"] == TEXT
    assert rows[0]["instruction_measurements"]["within_word_limit"] is False
    assert rows[1]["response_structure"] == {"summary": TEXT}
    for call, row in zip(state["calls"], rows):
        assert m._canonical_sha(json.loads(call["request"].content)) == m.PROPOSED_BODY_SHA256_BY_ARM[row["arm_id"]]
    assert summary == m.summarize(rows) and doc["inputs"] == m.prepare_experiment().metadata["inputs"]
    assert summary["calls_made"] == summary["schema_valid"] == 2 and summary["arms_skipped"] == 0
    assert [(v["arm_id"], v["case_id"]) for v in summary["arm_measurements"]] == [(a, m.CASE_ID) for a in m.ARM_IDS]
    assert [(v["arm_id"], v["case_id"]) for v in summary["provider_observations"]] == [(a, m.CASE_ID) for a in m.ARM_IDS]
    assert summary["provider_observation"] is None
    assert all(row["provider_observation"]["usage"]["reasoning_tokens"] is None for row in rows)
    assert summary["cost_aggregate"]["status"] == "unavailable"
    assert summary["usage_aggregate"]["reported_subtotals"]["total_tokens"] == 38
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["runtime_promoted"] is summary["automated_gates_passed"] is summary["causal_comparison"] is False
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_arm_pacing_rechecks_before_deadlines_and_anchors_dispatch(monkeypatch, pacing):
    start = m.utc_now()
    monkeypatch.setattr(m, "utc_now", lambda: start + timedelta(seconds=pacing[0]))
    original = m._check_prepared
    checked = []
    def check(prepared):
        original(prepared)
        checked.append(pacing[0])
        if len(checked) in {3, 5}:
            pacing[0] += 2
    monkeypatch.setattr(m, "_check_prepared", check)
    def handler(arm, request):
        pacing[0] += 1
        return httpx.Response(200, json=completion())
    state = install(monkeypatch, pacing, handler)
    run()
    assert len(checked) == 5
    assert [call["started"] for call in state["calls"]] == [62, 124]
    assert [request.deadline for request in state["requests"]] == [start + timedelta(seconds=122), start + timedelta(seconds=184)]


@pytest.mark.parametrize("mutation", ["other_system", "other_operation", "arm_in_user", "3072"])
def test_adapter_binds_arm_operation_system_and_unchanged_source_before_one_use(mutation):
    prepared = m.prepare_experiment()
    calls = []
    def dispatch(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    adapter = SummaryRelationalObservationAdapter(arm_id="control", base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(prepared.candidate, prepared.target), api_key=SecretStr(KEY),
        reasoning_effort="none", transport=httpx.MockTransport(dispatch))
    exact = m._make_request(prepared, 0)
    if mutation == "other_system":
        changed = exact.model_copy(update={"messages": (m._make_request(prepared, 1).messages[0], exact.messages[1])})
    elif mutation == "other_operation":
        changed = exact.model_copy(update={"operation": "summary-relational.relational"})
    elif mutation == "arm_in_user":
        changed = exact.model_copy(update={"messages": (exact.messages[0], exact.messages[1].model_copy(
            update={"content": exact.messages[1].content + '\n{"arm_id":"control"}'}))})
    else:
        changed = exact.model_copy(update={"parameters": exact.parameters.model_copy(update={"max_output_tokens": 3072})})
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(changed))
    assert calls == []
    asyncio.run(adapter.generate_structured(exact))
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(m._make_request(prepared, 0)))
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["prompts_reversed", "case_substitution", "arm_source_mapping", "bool_as_zero"])
def test_prepared_arm_source_forgery_aborts_before_gateway(monkeypatch, mutation):
    prepared = m.prepare_experiment()
    if mutation == "prompts_reversed":
        prepared = replace(prepared, prompts=tuple(reversed(prepared.prompts)))
    elif mutation == "case_substitution":
        prepared.case["case_id"] = "reading-room-a"
    elif mutation == "arm_source_mapping":
        prepared.metadata["inputs"]["arms"][1]["case_id"] = "reading-room-b"
    else:
        prepared.metadata["inputs"]["arms"][0]["arm_index"] = False
    monkeypatch.setattr(m, "SummaryRelationalObservationAdapter", lambda **kwargs: pytest.fail("forged prepared gateway"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("drift", ["dossier", "case", "relational_prompt"])
def test_source_or_arm_asset_drift_during_wait_aborts_before_dispatch(monkeypatch, drift):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, interval):
            self._clock = lambda: 0.0
        async def before_call(self, label):
            if drift == "dossier":
                monkeypatch.setattr(m, "DOSSIER_SHA256", "0" * 64)
            elif drift == "case":
                monkeypatch.setattr(m, "CASE_PATH", m.PROJECT_ROOT / "evals/narrator/record_summary_budget_case_v1.json")
            else:
                monkeypatch.setitem(m.PROMPT_PATH_BY_ARM, "relational", m.PROMPT_PATH_BY_ARM["control"])
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "SummaryRelationalObservationAdapter", lambda **kwargs: pytest.fail("gateway after drift"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("failure", ["429", "schema", "route"])
def test_control_operational_failure_records_relational_skip_without_response_retention(monkeypatch, pacing, failure):
    def handler(arm, request):
        assert arm == "control"
        if failure == "429":
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": LEAK}})
        return httpx.Response(200, json=completion(value={"summary": True} if failure == "schema" else None,
            model="other" if failure == "route" else m.GROQ_QWEN_MODEL_ID))
    state = install(monkeypatch, pacing, handler)
    rows = run()
    summary = m.summarize(rows)
    assert len(state["calls"]) == 1 and rows[0]["schema_valid"] is False
    assert rows[1] == {"kind": "summary_relational_skip", "arm_id": "relational", "case_id": m.CASE_ID,
                       "call_made": False, "skipped_reason": "previous_operational_failure"}
    assert not {"response_structure", "summary_text", "instruction_measurements"}.intersection(rows[0])
    assert summary["process_exit_code"] == (2 if failure == "429" else 1)
    assert summary["arms_skipped"] == 1 and summary["provider_observation"] == summary["provider_observations"][0]["observation"]
    assert all(v["instruction_measurements"] is None for v in summary["arm_measurements"])
    assert LEAK not in json.dumps(rows)


def test_relational_failure_preserves_control_and_never_retries(monkeypatch, pacing):
    state = install(monkeypatch, pacing, lambda arm, request: httpx.Response(200, json=completion())
        if arm == "control" else httpx.Response(429, json={"error": {"message": LEAK}}))
    rows = run()
    summary = m.summarize(rows)
    assert len(state["calls"]) == 2 and summary["arms_skipped"] == 0 and summary["process_exit_code"] == 2
    assert rows[0]["summary_text"] == TEXT and rows[1]["schema_valid"] is False
    assert summary["arm_measurements"][0]["instruction_measurements"] is not None
    assert summary["arm_measurements"][1]["instruction_measurements"] is None


@pytest.mark.parametrize("when", ["wait", "inflight"])
def test_cancel_second_arm_preserves_control_and_exact_arm_inventory(monkeypatch, tmp_path, pacing, when):
    if when == "wait":
        real = m.shared._CallPacer
        def factory(interval):
            pacer = real(interval)
            before = pacer.before_call
            async def wait(label):
                if label.endswith("relational"):
                    raise asyncio.CancelledError()
                await before(label)
            pacer.before_call = wait
            return pacer
        monkeypatch.setattr(m.shared, "_CallPacer", factory)
    def handler(arm, request):
        if arm == "relational":
            raise asyncio.CancelledError()
        return httpx.Response(200, json=completion())
    state = install(monkeypatch, pacing, handler)
    assert main_at(monkeypatch, tmp_path) == 130
    rows, doc = artifacts(tmp_path)
    assert len(state["calls"]) == (1 if when == "wait" else 2)
    assert tuple(row["arm_id"] for row in rows) == m.ARM_IDS
    assert rows[0]["summary_text"] == TEXT and rows[1]["case_id"] == m.CASE_ID
    assert doc["summary"] == m.summarize(rows, status="cancelled")
    assert doc["summary"]["arms_skipped"] == (1 if when == "wait" else 0)


def test_local_measurement_failure_keeps_valid_control_text_and_skips_relational(monkeypatch, tmp_path, pacing):
    state = install(monkeypatch, pacing)
    def fail(text):
        raise RuntimeError(LEAK)
    monkeypatch.setattr(m.contract, "measure_summary_words", fail)
    assert main_at(monkeypatch, tmp_path) == 3
    rows, doc = artifacts(tmp_path)
    assert len(state["calls"]) == 1 and rows[0]["schema_valid"] is True
    assert rows[0]["summary_text"] == TEXT and rows[1]["call_made"] is False
    assert rows[0]["local_error"] == {"code": "local_summary_relational_failure"}
    assert doc["summary"]["arm_measurements"][0]["instruction_measurements"] is None
    assert LEAK not in json.dumps(rows)


@pytest.mark.parametrize("mutation", ["reverse", "duplicate_arm", "case_is_arm", "failed_then_call", "skip_then_call"])
def test_summary_rejects_conflated_arm_source_or_impossible_sequence(mutation):
    rows = valid_rows()
    if mutation == "reverse":
        rows.reverse()
    elif mutation == "duplicate_arm":
        rows[1]["arm_id"] = "control"
    elif mutation == "case_is_arm":
        rows[1]["case_id"] = "relational"
    elif mutation == "failed_then_call":
        rows[0]["schema_valid"] = False
    else:
        rows[0].update(kind="summary_relational_skip", call_made=False)
    with pytest.raises(ValueError):
        m.summarize(rows)
