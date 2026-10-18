"""Independent offline boundaries for the evidence-bearing derivation executor."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from scripts import evaluate_narrator_record_evidence as module
from api.llm.contract import (
    AdapterIdentity, InvocationEvidence, Provenance, ProvenanceValue,
    StructuredGenerationResult, utc_now,
)


def _records(case_id):
    opening = case_id == "opening"
    summary = "Um sussurro distante ecoa no corredor." if opening else "Mara desliza um papel amassado sobre o balcão."
    return {
        "o": "unresolved", "l": "Corredor de pedra" if opening else "Bar fechado",
        "s": summary, "p": [] if opening else ["Mara"],
        "f": [{"k": "observation", "s": summary, "v": "public", "i": 0.5, "p": True,
               "a": [] if opening else [{"n": "Mara", "p": "present"}]}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }


def _envelope(case, records=None):
    records = records if records is not None else _records(case.case_id)
    _, audit = module.contract.build_evidence_packet(case)
    source_ids = [unit["id"] for unit in audit["source_units"] if unit["origin"] == "narrative"]
    return {
        "records": records,
        "supports": [{"p": "/s", "b": 0, "e": len(records["s"]), "s": source_ids, "m": "established"}],
    }


def _result(request, payload):
    return StructuredGenerationResult(
        value=module.contract.RecordEvidenceProposal.model_validate(payload),
        evidence=InvocationEvidence(provenance=Provenance(
            invocation_id=request.invocation_id, requested_target=request.target,
            adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
            effective_model=ProvenanceValue.reported(request.target.model),
            effective_provider=ProvenanceValue.observed(request.target.provider),
            started_at=utc_now(), finished_at=utc_now(),
        )),
    )


class _Clock:
    def __init__(self):
        self.now = 0.0

    def read(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


def _install_pacer(monkeypatch, clock):
    real = module.shared._CallPacer
    monkeypatch.setattr(module.shared, "_CallPacer", lambda interval: real(
        interval, _clock=clock.read, _sleeper=clock.sleep,
    ))


def _gateway(monkeypatch, prepared, mutate=None, starts=None, clock=None):
    requests = []
    cases = {case.case_id: case for case in prepared.cases}

    class Gateway:
        async def generate_structured(self, request):
            requests.append(request)
            if starts is not None:
                starts.append(clock.now)
            case = cases[request.operation.rsplit(".", 1)[-1]]
            payload = _envelope(case)
            if mutate is not None:
                mutate(payload, len(requests), case)
            return _result(request, payload)

    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: Gateway())
    return requests


def test_pacing_anchors_after_slow_integrity_check_at_actual_dispatch(monkeypatch):
    prepared = module.prepare_experiment()
    clock = _Clock()
    _install_pacer(monkeypatch, clock)
    actual_check = module._check_prepared
    checks = 0

    def expensive_check(value):
        nonlocal checks
        actual_check(value)
        checks += 1
        if checks == 3:
            clock.now += 20.0

    monkeypatch.setattr(module, "_check_prepared", expensive_check)
    starts = []
    _gateway(monkeypatch, prepared, starts=starts, clock=clock)
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(starts) == 2 and starts[1] - starts[0] >= 60.0
    assert all(row["admitted"] for row in rows)


@pytest.mark.parametrize("invalid", ["source", "path", "range"])
def test_structural_envelope_failure_aborts_second_independent_input(invalid, monkeypatch):
    prepared = module.prepare_experiment()
    _install_pacer(monkeypatch, _Clock())

    def mutate(payload, count, case):
        assert count == 1
        support = payload["supports"][0]
        if invalid == "source":
            support["s"] = ["nonexistent-source"]
        elif invalid == "path":
            support["p"] = "/f/3/s"
        else:
            support["e"] = len(payload["records"]["s"]) + 1

    requests = _gateway(monkeypatch, prepared, mutate=mutate)
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(requests) == 1
    assert rows[0]["schema_valid"] is True
    assert rows[0]["envelope_valid"] is False and rows[0]["admitted"] is False
    assert rows[0]["envelope_error"]["code"]
    assert "local_error" not in rows[0] and "composed_proposal" not in rows[0]
    assert rows[1]["call_made"] is False
    assert rows[1]["skipped_reason"] == "previous_operational_failure"
    assert module.summarize(rows)["process_exit_code"] != 0


def test_valid_envelope_with_final_schema_rejection_keeps_second_input_independent(monkeypatch):
    prepared = module.prepare_experiment()
    _install_pacer(monkeypatch, _Clock())

    def mutate(payload, count, case):
        if count == 1:
            payload["records"].update(f=[], t=[], r=[])

    requests = _gateway(monkeypatch, prepared, mutate=mutate)
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(requests) == 2
    assert rows[0]["schema_valid"] is True and rows[0]["envelope_valid"] is True
    assert rows[0]["final_schema_valid"] is False and rows[0]["final_schema_errors"]
    assert "local_error" not in rows[0]
    assert rows[1]["admitted"] is True
    assert module.summarize(rows)["operational_probe_passed"] is False


def test_structurally_supported_but_unfaithful_relation_never_promotes_semantics(monkeypatch):
    prepared = module.prepare_experiment()
    _install_pacer(monkeypatch, _Clock())

    def mutate(payload, count, case):
        if case.case_id == "mara":
            invented = "Mara desliza sobre o balcão um papel que contém o endereço."
            payload["records"]["f"][0]["s"] = invented
            payload["supports"][0].update(p="/f/0/s", b=0, e=len(invented), m="established")

    _gateway(monkeypatch, prepared, mutate=mutate)
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert all(row["envelope_valid"] and row["admitted"] for row in rows)
    assert "supports" not in rows[1]["composed_proposal"]
    summary = module.summarize(rows)
    assert summary["operational_probe_passed"] is True
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["support_coverage_review"] == {"status": "not_performed", "approval": None}
    assert summary["support_validation_scope"] == "structural_only"
    assert summary["automated_gates_passed"] is False and summary["full_evaluation"] is False
    assert summary["cap_001_status"] == "not_evaluated" and summary["runtime_promoted"] is False


def _run_main_to_tmp(monkeypatch, tmp_path):
    run_dir = tmp_path / "evidence-artifacts"
    run_dir.mkdir()
    monkeypatch.setattr(module, "_new_run_directory", lambda *args: run_dir)
    monkeypatch.setattr(module, "os", SimpleNamespace(environ={"GROQ_API_KEY": "synthetic-key"}))
    exit_code = module.main([
        "--live", "--allow-synthetic-only", "--batch-id", "11111111-1111-4111-8111-111111111111",
    ])
    raw = (run_dir / f"{module.CANDIDATE_ID}.jsonl").read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw.splitlines()]
    document = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert "synthetic-key" not in raw
    assert all(row["purpose"] == "record_evidence_probe" and row["full_evaluation"] is False for row in rows)
    return exit_code, rows, document


def test_source_drift_during_second_wait_persists_first_call_and_refuses_dispatch(monkeypatch, tmp_path):
    prepared = module.prepare_experiment()
    drifted = False
    clock = _Clock()
    original_sleep = clock.sleep

    async def drift_after_wait(seconds):
        nonlocal drifted
        await original_sleep(seconds)
        drifted = True

    clock.sleep = drift_after_wait
    _install_pacer(monkeypatch, clock)
    actual_read = module.record_contract._read_frozen

    def changed_source(path, expected):
        if drifted and path == module.record_contract.SOURCE_JSONL_PATH:
            raise module.record_contract.DerivationContractError("record_derivation_source_hash_mismatch")
        return actual_read(path, expected)

    monkeypatch.setattr(module.record_contract, "_read_frozen", changed_source)
    requests = _gateway(monkeypatch, prepared)
    exit_code, rows, document = _run_main_to_tmp(monkeypatch, tmp_path)
    assert exit_code == 3 and len(requests) == 1
    assert rows[0]["admitted"] is True
    assert rows[1]["call_made"] is False and rows[1]["skipped_reason"] == "local_error"
    assert document["evaluation_status"] == "local_error"
    assert document["summary"]["calls_made"] == 1


@pytest.mark.parametrize("stage", ["second_wait", "second_dispatch"])
def test_partial_cancellation_preserves_attempted_versus_uncalled_cases(stage, monkeypatch, tmp_path):
    prepared = module.prepare_experiment()
    clock = _Clock()
    if stage == "second_wait":
        async def cancel_wait(seconds):
            raise asyncio.CancelledError()
        clock.sleep = cancel_wait
    _install_pacer(monkeypatch, clock)

    def cancel_dispatch(payload, count, case):
        if count == 2:
            raise asyncio.CancelledError()

    requests = _gateway(monkeypatch, prepared, mutate=cancel_dispatch)
    exit_code, rows, document = _run_main_to_tmp(monkeypatch, tmp_path)
    expected_calls = 1 if stage == "second_wait" else 2
    assert exit_code == 130 and len(requests) == expected_calls
    assert rows[0]["admitted"] is True
    assert document["evaluation_status"] == "cancelled"
    assert document["summary"]["calls_made"] == expected_calls
    assert document["summary"]["cases_skipped"] == 2 - expected_calls
    if stage == "second_wait":
        assert rows[1]["call_made"] is False and rows[1]["skipped_reason"] == "cancelled"
    else:
        assert rows[1]["call_made"] is True and rows[1]["cancelled"] is True


def test_real_groq_adapter_wire_keeps_fixed_route_budget_and_nested_envelope(monkeypatch):
    prepared = module.prepare_experiment()
    _install_pacer(monkeypatch, _Clock())
    transmitted = []

    def respond(request):
        body = json.loads(request.content)
        transmitted.append(body)
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        case = prepared.cases[len(transmitted) - 1]
        return httpx.Response(200, json={
            "id": "synthetic-response", "model": prepared.target.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(_envelope(case), ensure_ascii=False)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        })

    real_adapter = module.GroqAdapter
    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: real_adapter(
        **kwargs, transport=httpx.MockTransport(respond),
    ))
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(transmitted) == 2 and all(row["admitted"] for row in rows)
    for index, body in enumerate(transmitted):
        assert body["model"] == "openai/gpt-oss-120b"
        assert body["temperature"] == 0.65 and body["max_completion_tokens"] == 768
        assert body["reasoning_effort"] == "low"
        assert body["messages"] == [
            {"role": "system", "content": prepared.prompt},
            {"role": "user", "content": prepared.packets[index]},
        ]
        response_format = body["response_format"]["json_schema"]
        assert response_format["strict"] is True
        schema = response_format["schema"]
        assert set(schema["properties"]) == {"records", "supports"}
        assert set(schema["required"]) == {"records", "supports"}
        records_schema = schema["properties"]["records"]
        if "$ref" in records_schema:
            records_schema = schema["$defs"][records_schema["$ref"].rsplit("/", 1)[-1]]
        assert set(records_schema["properties"]) == set("olspft rq".replace(" ", ""))
        assert "n" not in records_schema["properties"]
    assert module.summarize(rows)["usage_aggregate"]["totals"]["total_tokens"] == 40