"""Independent adversarial checks for the isolated derivation executor."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from scripts import evaluate_narrator_record_derivation as module
from api.llm.contract import (
    AdapterIdentity, InvocationEvidence, Provenance, ProvenanceValue,
    StructuredGenerationResult, utc_now,
)


def _payload(case_id):
    opening = case_id == "opening"
    summary = "Um sussurro distante ecoa no corredor." if opening else "Mara desliza um papel amassado sobre o balcão."
    return {"o": "unresolved", "l": "Corredor de pedra" if opening else "Bar fechado",
            "s": summary, "p": [] if opening else ["Mara"],
            "f": [{"k": "observation", "s": summary, "v": "public", "i": 0.5, "p": True,
                   "a": [] if opening else [{"n": "Mara", "p": "present"}]}],
            "t": [], "r": [], "q": "O que você faz agora?"}


def _result(request, payload):
    return StructuredGenerationResult(
        value=module.contract.RecordDerivationProposal.model_validate(payload),
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


def test_pacing_measures_actual_dispatch_after_slow_final_preflight(monkeypatch):
    prepared = module.prepare_experiment()
    clock = _Clock()
    _install_pacer(monkeypatch, clock)
    checks = 0
    actual_check = module._check_prepared
    def expensive_check(value):
        nonlocal checks
        actual_check(value)
        checks += 1
        if checks == 3:
            clock.now += 20.0
    monkeypatch.setattr(module, "_check_prepared", expensive_check)
    starts = []
    class Gateway:
        async def generate_structured(self, request):
            starts.append(clock.now)
            return _result(request, _payload(request.operation.rsplit(".", 1)[-1]))
    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: Gateway())
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(starts) == 2
    assert starts[1] - starts[0] >= 60.0
    assert all(row["admitted"] for row in rows)


def test_route_summary_does_not_claim_consistency_after_mixed_verified_and_mismatch():
    rows = [
        {"kind": "record_derivation_call", "call_made": True, "route_status": status,
         "schema_valid": True, "admitted": status == "verified"}
        for status in ("verified", "mismatch")
    ]
    summary = module.summarize(rows)
    assert summary["route_verification"]["status"] == "mismatch"
    assert summary["route_verification"]["identity_consistent"] is False
    assert summary["process_exit_code"] != 0


def test_final_proposal_content_rejection_is_recorded_and_second_case_stays_independent(monkeypatch):
    prepared = module.prepare_experiment()
    _install_pacer(monkeypatch, _Clock())
    requests = []
    class Gateway:
        async def generate_structured(self, request):
            requests.append(request)
            payload = _payload(request.operation.rsplit(".", 1)[-1])
            if len(requests) == 1:
                # Valid derivative schema, but no novelty for final admission.
                payload.update(f=[], t=[], r=[])
            return _result(request, payload)
    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: Gateway())
    rows = asyncio.run(module.evaluate_probe(prepared, api_key=SecretStr("synthetic-key")))
    assert len(requests) == 2
    assert rows[0]["schema_valid"] is True
    assert rows[0]["final_schema_valid"] is False
    assert rows[0]["admitted"] is False
    assert "local_error" not in rows[0]
    assert rows[1]["admitted"] is True


@pytest.mark.parametrize("field", ["packets", "prompt", "cases", "metadata"])
def test_modified_prepared_scope_is_refused_before_gateway_construction(field, monkeypatch):
    prepared = module.prepare_experiment()
    if field == "packets":
        changes = {field: prepared.packets[::-1]}
    elif field == "prompt":
        changes = {field: prepared.prompt + " altered"}
    elif field == "cases":
        changes = {field: prepared.cases[::-1]}
    else:
        metadata = deepcopy(prepared.metadata)
        metadata["max_calls"] = 3
        changes = {field: metadata}
    altered = replace(prepared, **changes)
    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: pytest.fail("gateway constructed"))
    with pytest.raises(ValueError, match="Prepared experiment changed"):
        asyncio.run(module.evaluate_probe(altered, api_key=SecretStr("synthetic-key")))


def test_preflight_never_reads_credential_or_constructs_gateway(monkeypatch, capsys):
    class NoCredentialRead(dict):
        def get(self, key, default=None):
            pytest.fail("credential inspected")
    monkeypatch.setattr(module, "os", SimpleNamespace(environ=NoCredentialRead()))
    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: pytest.fail("gateway constructed"))
    assert module.main(["--preflight"]) == 0
    assert '"purpose": "record_derivation_probe"' in capsys.readouterr().out


@pytest.mark.parametrize("cancel_stage", ["second_pacing", "second_dispatch"])
def test_second_case_cancellation_preserves_exact_calls_and_skip_boundary(cancel_stage, monkeypatch, tmp_path):
    import json

    clock = _Clock()
    if cancel_stage == "second_pacing":
        async def cancel_sleep(seconds):
            raise asyncio.CancelledError()
        clock.sleep = cancel_sleep
    _install_pacer(monkeypatch, clock)
    requests = []
    run_dir = tmp_path / "cancelled-derivation"
    run_dir.mkdir()

    class Gateway:
        async def generate_structured(self, request):
            requests.append(request)
            if len(requests) == 2:
                raise asyncio.CancelledError()
            return _result(request, _payload("opening"))

    monkeypatch.setattr(module, "GroqAdapter", lambda **kwargs: Gateway())
    monkeypatch.setattr(module, "_new_run_directory", lambda *args: run_dir)
    monkeypatch.setattr(module, "os", SimpleNamespace(environ={"GROQ_API_KEY": "synthetic-key"}))
    exit_code = module.main([
        "--live", "--allow-synthetic-only", "--batch-id", "11111111-1111-4111-8111-111111111111",
    ])
    rows = [json.loads(line) for line in (run_dir / f"{module.CANDIDATE_ID}.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert exit_code == 130
    assert len(rows) == 2
    assert rows[0]["case_id"] == "opening" and rows[0]["admitted"] is True
    assert rows[1]["case_id"] == "mara"
    assert all(row["purpose"] == "record_derivation_probe" and row["full_evaluation"] is False for row in rows)
    expected_calls = 1 if cancel_stage == "second_pacing" else 2
    assert len(requests) == expected_calls
    assert summary["evaluation_status"] == "cancelled"
    assert summary["summary"]["calls_made"] == expected_calls
    assert summary["summary"]["cases_skipped"] == 2 - expected_calls
    if cancel_stage == "second_pacing":
        assert rows[1]["call_made"] is False and rows[1]["skipped_reason"] == "cancelled"
    else:
        assert rows[1]["call_made"] is True and rows[1]["cancelled"] is True
    assert "synthetic-key" not in (run_dir / f"{module.CANDIDATE_ID}.jsonl").read_text(encoding="utf-8")