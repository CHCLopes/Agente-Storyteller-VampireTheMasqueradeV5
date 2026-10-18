"""Offline execution of two independent cases with frozen low-effort requests."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from datetime import timedelta
import json
import re
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from api.llm.contract import LLMInvocationError
from scripts import evaluate_narrator_record_independent_cases as m
from scripts.evaluate_narrator_record_independent_cases import IndependentCaseObservationAdapter

KEY = "SYNTHETIC_INDEPENDENT_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_PROVIDER_REASONING_NEVER_PERSIST"


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real = m.shared._CallPacer
    elapsed = [0.0]
    async def sleep(seconds): elapsed[0] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer", lambda interval: real(
        interval, _clock=lambda: elapsed[0], _sleeper=sleep))
    return elapsed


def envelope(case_id, *, outcome="unresolved"):
    first = case_id == m.CASE_IDS[0]
    summary = ("A luz de uma luminária acesa ilumina o interior da biblioteca, que está vazia naquele momento." if first
               else "Sobre a bancada da oficina, uma lâmpada de cor azul pisca de maneira intermitente.")
    return {"records": {"o": outcome, "l": "Biblioteca" if first else "Oficina",
        "s": summary, "p": [], "f": [{"k": "observation", "s": summary,
        "v": "public", "i": 0.5, "p": True, "a": []}],
        "t": [], "r": [], "q": "O que você deseja fazer agora?"},
        "supports": [{"p": "/s", "c": summary, "s": ["n0" if first else "n1"], "m": "established"}]}


def completion(case_id, *, value=None, finish="stop", model="openai/gpt-oss-120b", usage=True):
    payload = {"id": "synthetic-independent", "model": model,
        "choices": [{"finish_reason": finish, "message": {
            "content": json.dumps(envelope(case_id) if value is None else value), "reasoning": LEAK}}]}
    if usage:
        payload["usage"] = {"prompt_tokens": 2300, "completion_tokens": 900,
            "total_tokens": 3200, "completion_tokens_details": {"reasoning_tokens": 150}}
    return payload


def install(monkeypatch, handler, elapsed):
    state = {"calls": [], "instances": [], "requests": []}
    class Gateway(IndependentCaseObservationAdapter):
        def __init__(self, **kwargs):
            case_id = kwargs["case_id"]
            async def dispatch(request):
                state["calls"].append({"case_id": case_id, "request": request, "started": elapsed[0]})
                return handler(case_id, request)
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
            state["instances"].append(self)
        async def generate_structured(self, request):
            state["requests"].append(request)
            return await super().generate_structured(request)
        async def generate_text(self, request):
            pytest.fail("independent experiment cannot generate text diagnostics")
    monkeypatch.setattr(m, "IndependentCaseObservationAdapter", Gateway)
    return state


def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))


def test_preflight_builds_only_two_frozen_new_user_packets_without_historical_source(monkeypatch):
    monkeypatch.setattr(m.record_contract, "load_fixed_cases", lambda: pytest.fail("historical source read"))
    monkeypatch.setattr(m, "IndependentCaseObservationAdapter", lambda **kwargs: pytest.fail("client in preflight"))
    prepared = m.prepare_experiment()
    baseline = json.loads(m.BASELINE_DOSSIER_PATH.read_text(encoding="utf-8"))["request"]["body"]
    dossier = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    assert tuple(c.case_id for c in prepared.cases) == m.CASE_IDS
    for index, case in enumerate(prepared.cases):
        assert len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", case.narrative, flags=re.UNICODE)) >= 30
        body = m._fixed_payload(m._make_request(prepared, index))
        assert body == dossier["requests"][index]["request"]["body"]
        assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256_BY_CASE[case.case_id]
        assert set(body) == set(baseline)
        assert {k for k in body if body[k] != baseline[k]} == {"messages"}
        restored = copy.deepcopy(body)
        restored["messages"][1] = baseline["messages"][1]
        assert restored == baseline
        assert body["reasoning_effort"] == "low" and body["max_completion_tokens"] == 3072
        assert case.source["case_binding"] == "record-independent-cases-v1"
        assert case.source["origin"] == "agent_authored_synthetic_cases"
        assert not {"candidate_id", "model", "batch_id"}.intersection(case.source)
        assert prepared.metadata["inputs"]["cases"][index]["source"] == case.source
    metadata = prepared.metadata
    assert prepared.target.profile == m.TARGET_PROFILE
    assert metadata["inputs"]["corpus"] == {"file": "record_independent_cases_v1.json", "sha256": m.CORPUS_SHA256}
    assert metadata["inputs"]["dossier"]["changed_payload_fields"] == ["messages[1].content"]
    assert metadata["inputs"]["prompt"]["variant"] == "record-evidence-claim-check-v1"
    assert metadata["inputs"]["support_resolution_policy"]["quote_protocol"] == "record-evidence-target-quotes-v1"
    assert metadata["evidence_generation_parameters"]["max_total_output_tokens"] == 6144
    assert metadata["inputs"]["response_schema_sha256"] == "225adcde7c70dbd5be868b06a8731fc59f00bf11de80cc9639a88d7573db15d8"
    assert metadata["inputs"]["provider_schema_sha256"] == "fe5e9738d12ca0b094643c04e45cdbf87aee17588b0889f75927ec8df663cff2"


def test_two_real_mock_calls_order_pacing_fresh_observations_and_no_semantic_promotion(monkeypatch, pacing):
    def handler(case_id, request):
        first = case_id == m.CASE_IDS[0]
        return httpx.Response(200, json=completion(case_id, usage=first),
            headers={"x-request-id": "req_" + "a" * 26} if first else {})
    state = install(monkeypatch, handler, pacing)
    rows = run()
    assert tuple(r["case_id"] for r in rows) == m.CASE_IDS
    assert [c["started"] for c in state["calls"]] == [60.0, 120.0]
    assert len(state["instances"]) == len(state["calls"]) == 2
    assert state["instances"][0] is not state["instances"][1]
    for index, row in enumerate(rows):
        assert row["admitted"] is row["envelope_valid"] is row["final_schema_valid"] is True
        assert row["composed_proposal"]["narrative"] == row["fixed_narrative"]
        body = json.loads(state["calls"][index]["request"].content)
        assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256_BY_CASE[row["case_id"]]
        assert row["evidence"]["adapter"]["name"] == "groq-chat-completions"
        assert row["evidence"]["requested_target"]["profile"] == m.TARGET_PROFILE
    assert rows[0]["provider_observation"]["request_id"] == "req_" + "a" * 26
    assert rows[1]["provider_observation"]["request_id"] is None
    assert rows[1]["provider_observation"]["usage"]["reasoning_tokens"] is None
    summary = m.summarize(rows)
    assert summary["calls_made"] == summary["admitted"] == 2 and summary["cases_skipped"] == 0
    assert summary["process_exit_code"] == 0
    assert summary["provider_observation"] is None
    assert [v["case_id"] for v in summary["provider_observations"]] == list(m.CASE_IDS)
    assert summary["route_verification"]["verified_calls"] == 2
    assert summary["usage_aggregate"]["status"] == "partial"
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["support_coverage_review"] == {"status": "not_performed", "approval": None}
    assert summary["runtime_promoted"] is summary["automated_gates_passed"] is False
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_deadline_after_each_wait_and_next_start_spacing_not_previous_finish(monkeypatch, pacing):
    start = m.utc_now()
    monkeypatch.setattr(m, "utc_now", lambda: start + timedelta(seconds=pacing[0]))
    def handler(case_id, request):
        pacing[0] += 2.0
        return httpx.Response(200, json=completion(case_id))
    state = install(monkeypatch, handler, pacing)
    rows = run()
    assert [c["started"] for c in state["calls"]] == [60.0, 120.0]
    assert [r.deadline for r in state["requests"]] == [start + timedelta(seconds=120), start + timedelta(seconds=180)]
    assert len(rows) == 2 and pacing[0] == 122.0


@pytest.mark.parametrize("failure", ["http400", "http429", "http503", "length", "schema", "envelope", "route", "admission", "final_schema"])
def test_first_failure_stops_and_emits_second_case_skip(monkeypatch, pacing, failure):
    if failure == "final_schema":
        def invalid_composition(*args):
            return m.FocusedSceneContinuationProposal.model_validate({})
        monkeypatch.setattr(m.record_contract, "compose_derivation", invalid_composition)
    def handler(case_id, request):
        assert case_id == m.CASE_IDS[0]
        if failure.startswith("http"):
            return httpx.Response(int(failure[4:]), json={"error": {
                "message": LEAK, "code": "json_validate_failed", "failed_generation": LEAK}})
        value = envelope(case_id, outcome="success" if failure == "admission" else "unresolved")
        if failure == "schema": value = {"records": value["records"]}
        if failure == "envelope": value["supports"][0]["c"] = "missing quote"
        return httpx.Response(200, json=completion(case_id, value=value,
            finish="length" if failure == "length" else "stop",
            model="other-model" if failure == "route" else "openai/gpt-oss-120b"))
    state = install(monkeypatch, handler, pacing)
    rows = run()
    assert len(state["calls"]) == len(state["instances"]) == 1
    assert rows[0]["call_made"] is True and rows[0]["admitted"] is False
    assert rows[1] == {"kind": "record_evidence_independent_cases_skip", "case_id": m.CASE_IDS[1],
        "episode_id": "independent-sensory", "turn_id": "derive-sensory", "call_made": False,
        "skipped_reason": "previous_operational_failure"}
    summary = m.summarize(rows)
    assert summary["calls_made"] == summary["cases_skipped"] == 1
    assert summary["process_exit_code"] == (2 if failure in {"http429", "http503"} else 1)
    assert summary["operational_probe_passed"] is False
    assert summary["provider_observation"] == rows[0]["provider_observation"]
    assert len(summary["provider_observations"]) == 1
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_second_failure_preserves_first_admission_without_partial_approval(monkeypatch, pacing):
    def handler(case_id, request):
        if case_id == m.CASE_IDS[1]:
            return httpx.Response(400, json={"error": {"code": "json_validate_failed", "message": LEAK}})
        return httpx.Response(200, json=completion(case_id))
    state = install(monkeypatch, handler, pacing)
    rows = run(); summary = m.summarize(rows)
    assert len(state["calls"]) == 2 and summary["cases_skipped"] == 0
    assert rows[0]["admitted"] is True and rows[1]["admitted"] is False
    assert summary["admitted"] == 1 and summary["process_exit_code"] == 1
    assert summary["operational_probe_passed"] is False


@pytest.mark.parametrize("mutation", ["order", "extra", "source", "candidate", "target", "packet", "metadata"])
def test_mutated_preparation_cannot_construct_a_gateway(monkeypatch, mutation):
    prepared = m.prepare_experiment()
    if mutation == "order": prepared = replace(prepared, cases=prepared.cases[::-1])
    elif mutation == "extra": prepared = replace(prepared, cases=prepared.cases + (prepared.cases[0],))
    elif mutation == "source":
        changed = replace(prepared.cases[0], source={**prepared.cases[0].source, "model": "fabricated"})
        prepared = replace(prepared, cases=(changed, prepared.cases[1]))
    elif mutation == "candidate": prepared = replace(prepared, candidate=replace(prepared.candidate, reasoning_effort="medium"))
    elif mutation == "target": prepared = replace(prepared, target=prepared.target.model_copy(update={"profile": "old"}))
    elif mutation == "packet": prepared = replace(prepared, packets=(prepared.packets[0] + " drift", prepared.packets[1]))
    else: prepared.metadata["max_calls"] = 3
    monkeypatch.setattr(m, "IndependentCaseObservationAdapter", lambda **kwargs: pytest.fail("gateway before integrity"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("which", ["prompt", "corpus"])
def test_drift_during_first_quiet_wait_never_constructs_gateway(monkeypatch, which):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, interval): self._clock = lambda: 0.0
        async def before_call(self, label):
            monkeypatch.setattr(m, "PROMPT_SHA256" if which == "prompt" else "CORPUS_SHA256", "0" * 64)
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "IndependentCaseObservationAdapter", lambda **kwargs: pytest.fail("gateway after drift"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("which", ["prompt", "corpus", "dossier"])
def test_preflight_drift_precedes_credential_access(monkeypatch, capsys, which):
    class Environment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("credential inspected after drift")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", Environment())
    monkeypatch.setattr(m, {"prompt": "PROMPT_SHA256", "corpus": "CORPUS_SHA256", "dossier": "DOSSIER_SHA256"}[which], "0" * 64)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
    assert "preflight failed" in capsys.readouterr().err


def test_preflight_main_emits_only_json_and_never_reads_credential_or_creates_artifact(monkeypatch, capsys):
    class Environment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("credential inspected during preflight")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", Environment())
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("preflight artifact"))
    assert m.main(["--preflight"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["max_calls"] == 2 and output.err == ""


def test_missing_credential_has_no_artifacts(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("artifact without key"))
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3


@pytest.mark.parametrize("cancel_at", [1, 2])
def test_main_quiet_cancellation_preserves_ordered_call_skip_inventory(monkeypatch, tmp_path, pacing, cancel_at):
    real = m.shared._CallPacer
    count = [0]
    class Pacer:
        def __init__(self, interval):
            self.wrapped = real(interval)
            self._clock = self.wrapped._clock
        async def before_call(self, label):
            count[0] += 1
            if count[0] == cancel_at: raise asyncio.CancelledError()
            self.wrapped._last_call_started_at = self._last_call_started_at
            await self.wrapped.before_call(label)
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    state = install(monkeypatch, lambda case_id, req: httpx.Response(200, json=completion(case_id)), pacing)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 130
    rows = [json.loads(line) for line in (tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["summary"]
    assert len(state["calls"]) == cancel_at - 1
    assert tuple(r["case_id"] for r in rows) == m.CASE_IDS
    assert summary["calls_made"] + summary["cases_skipped"] == 2
    assert summary["cases_skipped"] == 3 - cancel_at and summary["process_exit_code"] == 130
    assert len(summary["provider_observations"]) == cancel_at - 1
    assert summary["operational_probe_passed"] is False
    assert KEY not in json.dumps(rows) + json.dumps(summary)


def test_main_persists_safe_error_and_skip_as_two_rows(monkeypatch, tmp_path, pacing, capsys):
    state = install(monkeypatch, lambda case_id, req: httpx.Response(400, json={"error": {
        "message": LEAK, "code": "json_validate_failed", "failed_generation": LEAK}}), pacing)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 1
    text = (tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8")
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert len(text.splitlines()) == 2 and len(state["calls"]) == 1
    assert summary["summary"]["cases_skipped"] == 1
    assert summary["inputs"]["corpus"]["sha256"] == m.CORPUS_SHA256
    assert KEY not in text + json.dumps(summary) + capsys.readouterr().out
    assert LEAK not in text + json.dumps(summary)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "order", "wrong_kind", "false_type"])
def test_summary_rejects_incomplete_or_ambiguous_case_inventory(mutation):
    prepared = m.prepare_experiment(); rows = []
    m._skip_remaining(prepared, rows, "cancelled")
    if mutation == "missing": rows.pop()
    elif mutation == "duplicate": rows[1] = copy.deepcopy(rows[0])
    elif mutation == "order": rows.reverse()
    elif mutation == "wrong_kind": rows[0]["kind"] = "narrative_turn"
    else: rows[0]["call_made"] = 0
    with pytest.raises(ValueError, match="ordered call or skip"):
        m.summarize(rows)


def test_case_bound_observer_refuses_other_case_and_second_dispatch():
    prepared = m.prepare_experiment(); calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion(m.CASE_IDS[0]))
    gateway = IndependentCaseObservationAdapter(case_id=m.CASE_IDS[0], base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(prepared.candidate, prepared.target),
        api_key=SecretStr(KEY), reasoning_effort="low", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(m._make_request(prepared, 1)))
    assert calls == []
    asyncio.run(gateway.generate_structured(m._make_request(prepared, 0)))
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(m._make_request(prepared, 0)))
    assert len(calls) == 1


@pytest.mark.parametrize("argv", [
    ["--preflight", "--live"], ["--live"], ["--preflight", "--case", "opening"],
    ["--preflight", "--max-output-tokens", "6144"], ["--preflight", "--reasoning-effort", "medium"],
    ["--preflight", "--api-key-env", "OTHER_KEY"],
])
def test_cli_refuses_new_scope_before_preflight(monkeypatch, argv):
    monkeypatch.setattr(m, "prepare_experiment", lambda: pytest.fail("preflight after invalid CLI"))
    with pytest.raises(SystemExit): m.main(argv)
