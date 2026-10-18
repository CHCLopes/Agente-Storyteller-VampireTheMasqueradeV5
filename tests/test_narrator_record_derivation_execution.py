"""Offline dispatch and persistence tests for the bounded derivation probe."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from api.llm.contract import (
    AdapterIdentity, ErrorCategory, InvocationEvidence, LLMInvocationError,
    NormalizedError, OperationPhase, Provenance, ProvenanceValue, StructuredGenerationResult,
)
from scripts import evaluate_narrator_record_derivation as module
from scripts import narrator_record_derivation as contract


@pytest.fixture
def prepared():
    return module.prepare_experiment()


def records_for(case):
    summary = ("Um sussurro distante ecoa no corredor." if case.case_id == "opening"
               else "Mara desliza um papel amassado sobre o balcão.")
    return {"o": case.outcome, "l": "Corredor de pedra" if case.scene is None else case.scene.location,
            "s": summary, "p": [] if case.scene is None else ["Mara"],
            "f": [{"k": "observation", "s": summary, "v": "public", "i": 0.5, "p": True,
                   "a": [] if case.scene is None else [{"n": "Mara", "p": "present"}]}],
            "t": [], "r": [], "q": "O que você faz agora?"}


def fake_gateway(monkeypatch, prepared, effects=None):
    requests, waits = [], []
    effects = effects or {}
    class Pacer:
        def __init__(self, interval):
            assert interval == 60
            self._clock = lambda: 1000 + len(requests) * 60
        async def before_call(self, label):
            waits.append(label)
    monkeypatch.setattr(module.shared, "_CallPacer", Pacer)
    class Gateway:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == module.GROQ_OFFICIAL_BASE_URL
            assert kwargs["reasoning_effort"] == "low"
        async def test_connection(self, _):
            pytest.fail("diagnostic forbidden")
        def stream_text(self, _):
            pytest.fail("streaming forbidden")
        async def generate_structured(self, request):
            index = len(requests)
            requests.append(request)
            now = datetime.now(timezone.utc)
            evidence = InvocationEvidence(provenance=Provenance(
                invocation_id=request.invocation_id, requested_target=request.target,
                adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
                effective_provider=ProvenanceValue.observed("Groq"),
                effective_model=ProvenanceValue.reported(request.target.model),
                started_at=now, finished_at=now,
            ))
            effect = effects.get(index)
            if isinstance(effect, ErrorCategory):
                raise LLMInvocationError(NormalizedError(
                    category=effect, code="synthetic_failure", phase=OperationPhase.RESPONSE,
                    invocation_id=request.invocation_id, target=request.target,
                    safe_message="Safe synthetic failure.", evidence=evidence, retryable=True,
                ))
            if isinstance(effect, BaseException):
                raise effect
            raw = records_for(prepared.cases[index])
            if callable(effect):
                raw = effect(raw)
            try:
                value = contract.RecordDerivationProposal.model_validate(raw)
            except ValueError:
                # Simulate a gateway violating its own output contract.
                return StructuredGenerationResult.model_construct(value=raw, evidence=evidence)
            return StructuredGenerationResult(value=value, evidence=evidence)
    monkeypatch.setattr(module, "GroqAdapter", Gateway)
    return requests, waits


def run(prepared, **kwargs):
    return asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-only"), **kwargs))


def test_two_fixed_independent_native_calls_preserve_literal_narratives(monkeypatch, prepared):
    requests, waits = fake_gateway(monkeypatch, prepared)
    observed = run(prepared)
    assert len(requests) == len(waits) == len(observed) == 2
    for index, request in enumerate(requests):
        assert request.operation == "record-derivation." + prepared.cases[index].case_id
        assert request.target == prepared.target
        assert request.messages[0].content == prepared.prompt
        assert request.messages[1].content == prepared.packets[index]
        assert request.response_model is contract.RecordDerivationProposal
        assert "n" not in request.response_model.model_json_schema(by_alias=True)["properties"]
        assert request.parameters.temperature == .65
        assert request.parameters.max_output_tokens == 768
        remaining = (request.deadline - datetime.now(timezone.utc)).total_seconds()
        assert 40 < remaining <= 60
        assert observed[index]["fixed_narrative"] == prepared.cases[index].narrative
        assert observed[index]["composed_proposal"]["narrative"] == prepared.cases[index].narrative
        assert observed[index]["admitted"] is True
        assert observed[index]["route_status"] == "verified"
        assert observed[index]["kind"] == "record_derivation_call"
        assert "proposal" not in observed[index]
    summary = module.summarize(observed)
    assert summary["process_exit_code"] == 0
    assert summary["operational_probe_passed"] is True
    assert summary["automated_gates_passed"] is summary["runtime_promoted"] is False
    assert summary["full_evaluation"] is False
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}


def test_semantic_rejection_does_not_skip_independent_second_case(monkeypatch, prepared):
    requests, _ = fake_gateway(monkeypatch, prepared, {0: lambda raw: {**raw, "o": "success"}})
    observed = run(prepared)
    assert len(requests) == 2
    assert observed[0]["schema_valid"] is True
    assert observed[0]["admitted"] is False
    assert observed[1]["admitted"] is True
    summary = module.summarize(observed)
    assert summary["process_exit_code"] == 1
    assert summary["calls_made"] == 2
    assert summary["cases_skipped"] == 0


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_all_provider_error_categories_abort_without_retry(monkeypatch, prepared, category):
    requests, _ = fake_gateway(monkeypatch, prepared, {0: category})
    observed = run(prepared)
    assert len(requests) == 1
    assert len(observed) == 2
    assert observed[0]["llm_error"]["category"] == category.value
    assert observed[1]["kind"] == "record_derivation_skip"
    assert observed[1]["call_made"] is False
    assert observed[1]["skipped_reason"] == "previous_operational_failure"
    summary = module.summarize(observed)
    assert summary["calls_made"] == summary["cases_skipped"] == 1
    assert summary["automatic_retries"] == 0
    assert summary["process_exit_code"] == (2 if category.value in module.AVAILABILITY_CATEGORIES else 1)


@pytest.mark.parametrize("mutation", [
    lambda raw: {**raw, "n": "Replacement narrative forbidden"},
    lambda raw: {k: v for k, v in raw.items() if k != "q"},
    lambda raw: {**raw, "f": [{"k": "observation", "s": "Missing actor field"}]},
])
def test_invalid_record_schema_is_observed_and_aborts(monkeypatch, prepared, mutation):
    requests, _ = fake_gateway(monkeypatch, prepared, {0: mutation})
    observed = run(prepared)
    assert len(requests) == 1
    assert observed[0]["schema_valid"] is False
    assert observed[0]["schema_errors"]
    assert observed[1]["call_made"] is False


def test_preflight_never_reads_credential_or_constructs_gateway(monkeypatch, capsys):
    old_get = module.os.environ.get
    def guarded(name, *args):
        if name.endswith("API_KEY"):
            pytest.fail("preflight inspected credential")
        return old_get(name, *args)
    monkeypatch.setattr(module.os.environ, "get", guarded)
    monkeypatch.setattr(module, "GroqAdapter", lambda **_: pytest.fail("preflight constructed gateway"))
    assert module.main(["--preflight"]) == 0
    meta = json.loads(capsys.readouterr().out)
    assert meta["max_calls"] == 2
    assert meta["narrative_generation_calls"] == 0
    assert meta["inputs"]["final_schema_sha256"] == module.FINAL_SCHEMA_SHA256


@pytest.mark.parametrize("args", [
    ["--live"], ["--live", "--allow-synthetic-only"], ["--preflight", "--allow-synthetic-only"],
    ["--live", "--allow-synthetic-only", "--batch-id", "not-uuid"],
    ["--live", "--allow-synthetic-only", "--batch-id", str(uuid4()), "--max-output-tokens", "900"],
])
def test_cli_scope_rejected_before_preflight_or_key(monkeypatch, args):
    monkeypatch.setattr(module, "prepare_experiment", lambda: pytest.fail("invalid CLI reached preflight"))
    with pytest.raises(SystemExit):
        module.main(args)


@pytest.mark.parametrize("effect,expected,calls", [
    (None, 0, 2), (ErrorCategory.RATE_LIMITED, 2, 1),
    (RuntimeError("SENSITIVE_SYNTHETIC_EXCEPTION"), 3, 1), (asyncio.CancelledError(), 130, 1),
])
def test_main_persists_progress_and_safe_summary(monkeypatch, prepared, tmp_path, capsys, effect, expected, calls):
    requests, _ = fake_gateway(monkeypatch, prepared, {} if effect is None else {0: effect})
    secret = "SYNTHETIC_CREDENTIAL_NEVER_PERSIST"
    monkeypatch.setenv("GROQ_API_KEY", secret)
    def new_run(*_):
        folder = tmp_path / "run"
        folder.mkdir()
        return folder
    monkeypatch.setattr(module, "_new_run_directory", new_run)
    batch = str(uuid4())
    result = module.main(["--live", "--allow-synthetic-only", "--batch-id", batch])
    assert result == expected
    assert len(requests) == calls
    doc = json.loads((tmp_path / "run/summary.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (tmp_path / "run" / f"{module.CANDIDATE_ID}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert doc["batch_id"] == batch
    assert doc["process_exit_code"] == doc["summary"]["process_exit_code"] == expected
    assert doc["summary"]["calls_made"] == calls
    assert all(row["purpose"] == "record_derivation_probe" for row in rows)
    assert all(row["full_evaluation"] is False for row in rows)
    text = json.dumps([doc, rows]) + capsys.readouterr().out
    assert secret not in text
    assert "SENSITIVE_SYNTHETIC_EXCEPTION" not in text
    assert doc["evaluator"]["file"] == "scripts/evaluate_narrator_record_derivation.py"
    assert doc["evaluator"]["sha256"] == module.shared._sha256(module.PROJECT_ROOT / doc["evaluator"]["file"])


def test_record_is_flushed_to_sink_before_next_case(monkeypatch, prepared):
    requests, _ = fake_gateway(monkeypatch, prepared)
    saved = []
    def sink(row):
        saved.append((len(requests), row["case_id"]))
    run(prepared, on_record=sink)
    assert saved == [(1, "opening"), (2, "mara")]


def test_missing_credential_stops_before_output_directory(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(module, "_new_run_directory", lambda *_: pytest.fail("artifact created without key"))
    assert module.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())]) == 3
