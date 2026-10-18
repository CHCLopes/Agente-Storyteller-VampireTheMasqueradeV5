"""Focused offline checks of the isolated Qwen summary-only executor and measurement contract."""
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
from pydantic import SecretStr, ValidationError
from api.llm.contract import LLMInvocationError
from scripts import evaluate_narrator_summary_only as m
from scripts.evaluate_narrator_summary_only import SummaryOnlyObservationAdapter

KEY = "SYNTHETIC_SUMMARY_ONLY_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_SUMMARY_REASONING_NEVER_PERSIST"


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real = m.shared._CallPacer
    elapsed = [0.0]
    async def sleep(seconds):
        elapsed[0] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer",
        lambda interval: real(interval, _clock=lambda: elapsed[0], _sleeper=sleep))
    return elapsed


def structure():
    return {"summary": "  Uma lanterna vermelha ilumina pastas; uma vibração sugere um motor.  "}


def completion(*, value=None, model="qwen/qwen3.8-27b", finish="stop"):
    return {"model": model, "id": "synthetic-inline", "choices": [{"finish_reason": finish,
        "message": {"content": json.dumps(structure() if value is None else value), "reasoning": LEAK}}],
        "usage": {"prompt_tokens": 2100, "completion_tokens": 900, "total_tokens": 3000,
                  "completion_tokens_details": {"reasoning_tokens": 0}}}


def install(monkeypatch, pacing, handler=None, *, transform=None):
    state = {"calls": [], "requests": [], "instances": []}
    class Gateway(SummaryOnlyObservationAdapter):
        def __init__(self, **kwargs):
            async def dispatch(request):
                state["calls"].append({"request": request, "started": pacing[0]})
                return handler(request) if handler else httpx.Response(200, json=completion())
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
            state["instances"].append(self)
        async def generate_structured(self, request):
            state["requests"].append(request)
            result = await super().generate_structured(request)
            return transform(result) if transform else result
        async def generate_text(self, request):
            pytest.fail("No text diagnostic or fallback")
    monkeypatch.setattr(m, "SummaryOnlyObservationAdapter", Gateway)
    return state


def run():
    return asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(KEY)))


def test_preflight_reconstructs_frozen_body_same_full_user_and_new_summary_contract(monkeypatch):
    monkeypatch.setattr(m, "SummaryOnlyObservationAdapter", lambda **kwargs: pytest.fail("preflight client"))
    prepared = m.prepare_experiment()
    dossier = json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    body = m._fixed_payload(m._make_request(prepared))
    baseline_path = m.PROJECT_ROOT / "evals/narrator/reports/record-inline-evidence-qwen-dossier-6876955e-2026-09-07.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["request"]["body"]
    assert body == dossier["request"]["body"]
    assert {key for key in body if body[key] != baseline[key]} == {"messages", "response_format"}
    assert body["messages"][1] == baseline["messages"][1]
    assert body["messages"][0]["role"] == baseline["messages"][0]["role"]
    restored = copy.deepcopy(body)
    restored["messages"][0]["content"] = baseline["messages"][0]["content"]
    restored["response_format"]["json_schema"]["name"] = baseline["response_format"]["json_schema"]["name"]
    restored["response_format"]["json_schema"]["schema"] = baseline["response_format"]["json_schema"]["schema"]
    assert restored == baseline
    assert body["response_format"]["json_schema"]["name"] == "SummaryOnlyProposal"
    assert set(body["response_format"]["json_schema"]["schema"]["properties"]) == {"summary"}
    assert m._canonical_sha(body) == m.PROPOSED_BODY_SHA256
    assert body["model"] == m.GROQ_QWEN_MODEL_ID and body["reasoning_effort"] == "none"
    assert "include_reasoning" not in body
    assert body["max_completion_tokens"] == 3072 and body["temperature"] == 0.65
    assert prepared.target.profile == m.TARGET_PROFILE
    assert hashlib.sha256(prepared.packet.encode()).hexdigest() == m.USER_PACKET_SHA256
    assert "".join(u["text"] for u in prepared.case["source_units"]) == prepared.case["narrative"]
    metadata = prepared.metadata; inputs = metadata["inputs"]
    assert metadata["selected_candidate_id"] == "qwen-3.8-27b-groq-free-synthetic-nonthink"
    assert metadata["protocol"] == "record-summary-only-v1"
    assert inputs["cases"][0]["generation_context"]["version"] == "record-inline-evidence-v1"
    assert inputs["cases"][0]["generation_context"]["budget"]["estimated_tokens"] == 168
    assert inputs["cases"][0]["source"]["origin"] == "agent_authored_synthetic_case"
    assert not {"candidate_id", "model", "batch_id"}.intersection(inputs["cases"][0]["source"])
    assert inputs["measurement_policy"] == dossier["measurement_policy"]
    assert inputs["provider_schema_sha256"] == m.RESPONSE_SCHEMA_SHA256
    assert "projection_policy" not in inputs and "inline_generation_parameters" not in metadata
    assert inputs["implementation"][0]["file"] == "scripts/narrator_summary_only.py"
    assert metadata["summary_generation_parameters"] == m._parameters()


def test_single_native_mock_call_keeps_literal_text_and_separates_measurement_from_approval(monkeypatch, pacing):
    start = m.utc_now()
    monkeypatch.setattr(m, "utc_now", lambda: start + timedelta(seconds=pacing[0]))
    state = install(monkeypatch, pacing)
    rows = run(); row = rows[0]; summary = m.summarize(rows)
    assert len(state["calls"]) == len(state["instances"]) == len(rows) == 1
    assert state["calls"][0]["started"] == 60.0
    assert state["requests"][0].deadline == start + timedelta(seconds=120)
    assert state["requests"][0].operation == "summary-only.archive-vibration"
    assert m._canonical_sha(json.loads(state["calls"][0]["request"].content)) == m.PROPOSED_BODY_SHA256
    assert row["response_structure"] == structure()
    assert row["summary_text"] == structure()["summary"]
    assert row["summary_text"].startswith("  ") and row["summary_text"].endswith("  ")
    assert row["instruction_measurements"] == m.contract.measure_summary_words(structure()["summary"])
    assert summary["instruction_measurements"] == row["instruction_measurements"]
    assert row["schema_valid"] is True and row["route_status"] == "verified"
    assert summary["process_exit_code"] == 0 and summary["operational_probe_passed"] is True
    assert summary["provider_observation"] == row["provider_observation"]
    assert summary["usage_aggregate"]["status"] == "reported"
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["automated_gates_passed"] is summary["runtime_promoted"] is False
    assert summary["actor_admission"] == "not_applied"
    removed = {"projection", "projection_valid", "projection_audit", "admitted", "final_schema_valid",
               "composed_proposal", "derived_records", "support_coverage_review", "open_questions"}
    assert not removed.intersection(row) and not removed.intersection(summary)
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("failure", ["http400", "http429", "http503", "length", "extra_field", "short", "boolean", "route"])
def test_one_failure_has_no_retry_or_fallback_and_never_retains_invalid_text(monkeypatch, pacing, failure):
    def handler(request):
        if failure.startswith("http"):
            return httpx.Response(int(failure[4:]), json={"error": {
                "message": LEAK, "code": "json_validate_failed", "failed_generation": LEAK}})
        value = structure()
        if failure == "extra_field": value["open_questions"] = [LEAK]
        if failure == "short": value["summary"] = "tiny"
        if failure == "boolean": value["summary"] = True
        return httpx.Response(200, json=completion(value=value,
            finish="length" if failure == "length" else "stop",
            model="unapproved-model" if failure == "route" else m.GROQ_QWEN_MODEL_ID))
    state = install(monkeypatch, pacing, handler)
    rows = run(); row = rows[0]; summary = m.summarize(rows)
    assert len(state["calls"]) == 1 and row["schema_valid"] is False
    assert not {"response_structure", "summary_text", "instruction_measurements"}.intersection(row)
    assert summary["instruction_measurements"] is None
    assert summary["process_exit_code"] == (2 if failure in {"http429", "http503"} else 1)
    assert summary["operational_probe_passed"] is False
    assert summary["calls_made"] == 1 and summary["cases_skipped"] == 0
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("value", [True, "tiny", "x" * 601])
def test_forged_pydantic_instance_is_revalidated_without_warning_or_retention(monkeypatch, pacing, value, capsys):
    bad = m.contract.SummaryOnlyProposal.model_construct(summary=value)
    state = install(monkeypatch, pacing, transform=lambda result: result.model_copy(update={"value": bad}))
    rows = run()
    assert len(state["calls"]) == 1 and rows[0]["schema_valid"] is False
    assert rows[0]["schema_error"] == {"code": "summary_only_schema_invalid"}
    assert "response_structure" not in rows[0] and "summary_text" not in rows[0]
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("mutation", ["case", "case_scalar_type", "metadata", "metadata_scalar_type", "packet", "prompt", "candidate", "target"])
def test_modified_preparation_cannot_construct_gateway(monkeypatch, mutation):
    prepared = m.prepare_experiment()
    if mutation == "case": prepared.case["source_units"][0]["text"] += " drift"
    elif mutation == "case_scalar_type": prepared.case["synthetic_only"] = 1
    elif mutation == "metadata": prepared.metadata["inputs"]["case"]["sha256"] = "0" * 64
    elif mutation == "metadata_scalar_type": prepared.metadata["runtime_promoted"] = 0
    elif mutation == "packet": prepared = replace(prepared, packet=prepared.packet + " drift")
    elif mutation == "prompt": prepared = replace(prepared, prompt=prepared.prompt + " drift")
    elif mutation == "candidate": prepared = replace(prepared, candidate=replace(prepared.candidate, reasoning_effort="medium"))
    else: prepared = replace(prepared, target=prepared.target.model_copy(update={"profile": "other"}))
    monkeypatch.setattr(m, "SummaryOnlyObservationAdapter", lambda **kwargs: pytest.fail("gateway after mutation"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("which", ["CASE_SHA256", "PROMPT_FILE_SHA256", "CONTRACT_SHA256", "DOSSIER_SHA256"])
def test_drift_during_initial_wait_blocks_dispatch(monkeypatch, which):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, interval): self._clock = lambda: 0.0
        async def before_call(self, label): monkeypatch.setattr(m, which, "0" * 64)
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "SummaryOnlyObservationAdapter", lambda **kwargs: pytest.fail("gateway after wait drift"))
    with pytest.raises(ValueError):
        asyncio.run(m.evaluate_probe(prepared, api_key=SecretStr(KEY)))


@pytest.mark.parametrize("which", ["CASE_SHA256", "PROMPT_SHA256", "CONTRACT_SHA256", "DOSSIER_SHA256"])
def test_preflight_fingerprint_failure_precedes_key_access(monkeypatch, which, capsys):
    class Environment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("credential inspected after failed preflight")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", Environment())
    monkeypatch.setattr(m, which, "0" * 64)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
    assert "preflight failed" in capsys.readouterr().err


def test_preflight_stdout_is_one_json_without_credential_or_artifact(monkeypatch, capsys):
    class Environment(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("preflight credential")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", Environment())
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("preflight artifact"))
    assert m.main(["--preflight"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["protocol"] == "record-summary-only-v1"
    assert output.err == "" and len(output.out.splitlines()) == 1


def test_missing_credential_creates_no_artifact(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("artifact without key"))
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3


@pytest.mark.parametrize("when", ["initial_wait", "inflight"])
def test_main_cancellation_preserves_exact_call_or_skip_and_exit130(monkeypatch, tmp_path, pacing, when):
    if when == "initial_wait":
        class Pacer:
            def __init__(self, interval): self._clock = lambda: 0.0
            async def before_call(self, label): raise asyncio.CancelledError()
        monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    def handler(request): raise asyncio.CancelledError()
    state = install(monkeypatch, pacing, handler)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 130
    rows = [json.loads(x) for x in (tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["summary"]
    calls = 1 if when == "inflight" else 0
    assert len(state["calls"]) == calls and len(rows) == 1
    assert summary["calls_made"] == calls and summary["cases_skipped"] == 1 - calls
    assert summary["process_exit_code"] == 130 and summary["operational_probe_passed"] is False
    assert KEY not in json.dumps(rows) + json.dumps(summary)


def test_main_success_artifact_roundtrip_reconstructs_summary_and_measurement(monkeypatch, tmp_path, pacing):
    state = install(monkeypatch, pacing)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    batch = str(uuid4())
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", batch]) == 0
    doc = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    assert doc["summary"] == m.summarize(rows)
    assert rows[0]["summary_text"] == structure()["summary"]
    assert rows[0]["response_structure"] == structure()
    assert rows[0]["instruction_measurements"] == m.contract.measure_summary_words(rows[0]["summary_text"])
    assert doc["batch_id"] == rows[0]["batch_id"] == batch and len(state["calls"]) == 1
    assert doc["summary_generation_parameters"] == m._parameters()
    assert KEY not in json.dumps(doc) + json.dumps(rows) and LEAK not in json.dumps(rows)


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "case", "kind", "call_type", "outcome_type", "measurement_type"])
def test_summary_refuses_ambiguous_inventory_and_untyped_results(mutation):
    rows = [{"kind": "summary_only_call", "case_id": m.CASE_ID, "call_made": True,
             "schema_valid": True, "route_status": "verified", "summary_text": structure()["summary"],
             "instruction_measurements": m.contract.measure_summary_words(structure()["summary"])}]
    if mutation == "empty": rows.clear()
    elif mutation == "duplicate": rows += copy.deepcopy(rows)
    elif mutation == "case": rows[0]["case_id"] = "opening"
    elif mutation == "kind": rows[0]["kind"] = "narrative_turn"
    elif mutation == "call_type": rows[0]["call_made"] = 1
    elif mutation == "outcome_type": rows[0]["schema_valid"] = 1
    else: rows[0]["instruction_measurements"]["within_word_limit"] = 1
    with pytest.raises(ValueError): m.summarize(rows)


def test_observer_rejects_changed_request_and_second_dispatch():
    prepared = m.prepare_experiment(); calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    gateway = SummaryOnlyObservationAdapter(base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(prepared.candidate, prepared.target),
        api_key=SecretStr(KEY), reasoning_effort="none", transport=httpx.MockTransport(handler))
    request = m._make_request(prepared)
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(request.model_copy(update={"operation": "other"})))
    assert calls == []
    asyncio.run(gateway.generate_structured(request))
    with pytest.raises(LLMInvocationError):
        asyncio.run(gateway.generate_structured(m._make_request(prepared)))
    assert len(calls) == 1


@pytest.mark.parametrize("argv", [
    ["--preflight", "--live"], ["--live"], ["--preflight", "--case", "opening"],
    ["--preflight", "--max-output-tokens", "6144"], ["--preflight", "--reasoning-effort", "medium"],
    ["--preflight", "--api-key-env", "OTHER_KEY"],
])
def test_cli_scope_rejection_precedes_preflight(monkeypatch, argv):
    monkeypatch.setattr(m, "prepare_experiment", lambda: pytest.fail("preflight after invalid CLI"))
    with pytest.raises(SystemExit): m.main(argv)


@pytest.mark.parametrize("reported_model", ["openai/gpt-oss-120b", None, "qwen-3.8-27b", "qwen/qwen3.8-27b "])
def test_only_exact_qwen_reported_model_can_reach_summary_validation(monkeypatch, pacing, reported_model):
    state = install(monkeypatch, pacing, lambda request: httpx.Response(200, json=completion(model=reported_model)))
    rows = run(); row = rows[0]; summary = m.summarize(rows)
    assert len(state["calls"]) == 1 and row["schema_valid"] is False
    assert row["llm_error"]["code"] == "groq_unverified_target_provenance"
    assert row["llm_error"]["category"] == "target_mismatch"
    assert row["provider_observation"]["model"] is None
    assert row["route_status"] == "unavailable"
    assert "response_structure" not in row and "summary_text" not in row
    assert summary["instruction_measurements"] is None
    assert summary["process_exit_code"] == 1 and summary["operational_probe_passed"] is False


@pytest.mark.parametrize("field,value", [
    ("profile", "inline-evidence-gpt-oss-120b-groq-free-synthetic-low"),
    ("provider", "OpenRouter"), ("model", "openai/gpt-oss-120b"), ("reasoning_effort", "low"),
])
def test_qwen_observer_constructor_refuses_cross_profile_target(field, value):
    prepared = m.prepare_experiment()
    target = prepared.target if field == "reasoning_effort" else prepared.target.model_copy(update={field:value})
    effort = value if field == "reasoning_effort" else "none"
    with pytest.raises(ValueError, match="exact model, profile and none effort"):
        SummaryOnlyObservationAdapter(base_url=m.GROQ_OFFICIAL_BASE_URL,
            capability_set=m.shared._capabilities(prepared.candidate, target),
            api_key=SecretStr(KEY), reasoning_effort=effort)


def test_nonthinking_request_does_not_infer_unreported_reasoning_count(monkeypatch, pacing):
    value = completion(); value["usage"].pop("completion_tokens_details")
    state = install(monkeypatch, pacing, lambda request: httpx.Response(200, json=value))
    rows = run(); row = rows[0]
    assert len(state["calls"]) == 1 and row["schema_valid"] is True
    assert row["provider_observation"]["usage"]["reasoning_tokens"] is None
    assert row["provider_observation"]["model"] == m.GROQ_QWEN_MODEL_ID
    assert LEAK not in json.dumps(rows)


@pytest.mark.parametrize("value", [None, True, 123, 1.5, b"eightchars", ["eightchars"], {}, "short", "x" * 601])
def test_summary_model_requires_strict_string_and_character_bounds(value):
    with pytest.raises(ValidationError):
        m.contract.SummaryOnlyProposal.model_validate({"summary": value})


def test_summary_model_forbids_extra_fields_is_frozen_and_preserves_unicode_spacing():
    for field in ("open_questions", "sources", "modality"):
        with pytest.raises(ValidationError):
            m.contract.SummaryOnlyProposal.model_validate({"summary": "eightchars", field: []})
    for text in ("ação ação", " " * 8, "á" * 600):
        result = m.contract.SummaryOnlyProposal(summary=text)
        assert result.summary == text
        with pytest.raises(ValidationError):
            result.summary = "changed text"


@pytest.mark.parametrize("text,expected", [
    ("pé-de-meia d'água d’água ação 42", 5), ("porta—mesa … luz", 3),
    ("  pastas.\nLanterna vermelha  ", 3), ("um_dois", 2), ("...", 0), ("", 0),
])
def test_unicode_word_measurement_is_explicit_and_does_not_rewrite_text(text, expected):
    measured = m.contract.measure_summary_words(text)
    assert measured == {"method": "unicode_words_with_internal_hyphen_or_apostrophe",
        "pattern": m.contract.WORD_PATTERN, "word_count": expected, "max_words": 25,
        "within_word_limit": expected <= 25, "semantic_fidelity_evaluated": False}


@pytest.mark.parametrize("value", [True, 123, None, b"words here"])
def test_measurement_does_not_coerce_non_strings(value):
    with pytest.raises(TypeError): m.contract.measure_summary_words(value)


@pytest.mark.parametrize("count", [25, 26, 32])
def test_word_limit_compliance_is_measured_but_does_not_change_operational_exit(monkeypatch, pacing, count):
    text = " ".join(["palavra"] * count)
    state = install(monkeypatch, pacing, lambda request: httpx.Response(200, json=completion(value={"summary": text})))
    rows = run(); summary = m.summarize(rows)
    assert len(state["calls"]) == 1 and rows[0]["summary_text"] == text
    assert summary["instruction_measurements"]["word_count"] == count
    assert summary["instruction_measurements"]["within_word_limit"] is (count <= 25)
    assert summary["process_exit_code"] == 0 and summary["operational_probe_passed"] is True
    assert summary["automated_gates_passed"] is summary["runtime_promoted"] is False


def test_route_mismatch_precedes_even_forged_response_validation(monkeypatch, pacing):
    def transform(result):
        provenance = result.evidence.provenance.model_copy(update={"invocation_id": str(uuid4())})
        evidence = result.evidence.model_copy(update={"provenance": provenance})
        return result.model_copy(update={"evidence": evidence, "value": object()})
    state = install(monkeypatch, pacing, transform=transform)
    row = run()[0]
    assert len(state["calls"]) == 1 and row["route_status"] == "mismatch"
    assert row["schema_valid"] is False and row["route_error"] == "effective_route_not_verified"
    assert "schema_error" not in row and "summary_text" not in row


def test_local_measurement_error_retains_valid_text_but_records_exit3(monkeypatch, tmp_path, pacing):
    state = install(monkeypatch, pacing)
    def fail(text): raise RuntimeError(LEAK)
    monkeypatch.setattr(m.contract, "measure_summary_words", fail)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: tmp_path)
    assert m.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
    row = json.loads((tmp_path / (m.CANDIDATE_ID + ".jsonl")).read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["summary"]
    assert len(state["calls"]) == 1 and row["schema_valid"] is True
    assert row["response_structure"] == structure() and row["summary_text"] == structure()["summary"]
    assert row["local_error"] == {"code": "local_summary_only_failure"}
    assert summary["instruction_measurements"] is None
    assert summary["operational_probe_passed"] is summary["transport_and_schema_passed"] is False
    assert LEAK not in json.dumps(row) and KEY not in json.dumps(row)
