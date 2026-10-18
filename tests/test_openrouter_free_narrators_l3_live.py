from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest
from pydantic import SecretStr

from api.llm.contract import (
    AdapterIdentity,
    CostMeasurement,
    ErrorCategory,
    InvocationEvidence,
    LLMInvocationError,
    MeasurementStatus,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceValue,
    StructuredGenerationResult,
)
from scripts import evaluate_openrouter_free_narrators_l2_live as l2
from scripts import evaluate_openrouter_free_narrators_l3_live as runner
from scripts import narrator_source_profile as source_profile


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_openrouter_free_narrators_l3_live.py"
LAUNCHER = ROOT / "scripts/run_openrouter_free_narrators_l3_live.ps1"
KEY_ENV = "STORYTELLER_OPENROUTER_FREE_KEY"


class NoWaitPacer:
    async def before_call(self, label: str) -> None:
        return None


class CancellingPacer:
    async def before_call(self, label: str) -> None:
        raise __import__("asyncio").CancelledError


def _keyless() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(KEY_ENV, None)
    return environment


def _preflight(path: Path) -> dict:
    result = subprocess.run(
        [str(PYTHON), str(path), "--preflight"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _configure(monkeypatch, output_root: Path) -> None:
    values = {
        "VERSION": runner.VERSION,
        "KEY_ENV": runner.KEY_ENV,
        "MANIFEST": runner.MANIFEST,
        "LIVE_GATE": runner.GATE,
        "MAX_CALLS": runner.MAX_CALLS,
        "MAX_OUTPUT_TOKENS": runner.MAX_OUTPUT_TOKENS,
        "MAX_TOTAL_OUTPUT_TOKENS": runner.MAX_TOTAL_OUTPUT_TOKENS,
        "DEADLINE_SECONDS": 90,
        "MINIMUM_INTERVAL_SECONDS": 4,
        "CANDIDATE_IDS": runner.CANDIDATE_IDS,
        "TARGETS": runner.TARGETS,
        "SCHEDULE": runner.SCHEDULE,
        "GROQ_OFFICIAL_BASE_URL": runner.BASE_URL,
        "GroqAdapter": runner.OpenRouterFreeAdapter,
        "run_path": runner.run_path,
        "prepare_live": runner.prepare_live,
        "summarize": runner.summarize,
        "verify_artifacts": runner.verify_artifacts,
        "_route_verified": runner._route_verified,
        "OUTPUT_ROOT": output_root,
    }
    for name, value in values.items():
        monkeypatch.setattr(runner.base, name, value)


def _evidence(request) -> InvocationEvidence:
    now = datetime.now(timezone.utc)
    upstream = runner.OpenRouterFreeAdapter._UPSTREAM_BY_MODEL[request.target.model]
    return InvocationEvidence(
        provenance=Provenance(
            invocation_id=request.invocation_id,
            requested_target=request.target,
            adapter=AdapterIdentity(name="openrouter", version="test"),
            effective_provider=ProvenanceValue.reported(upstream),
            effective_model=ProvenanceValue.reported(request.target.model),
            started_at=now,
            finished_at=now,
        ),
        cost=CostMeasurement(
            status=MeasurementStatus.REPORTED,
            amount=Decimal("0"),
            currency="OPENROUTER_CREDITS",
            source="synthetic-test",
        ),
    )


def _proposal(case_id: str) -> source_profile.NarrativeSourceProposal:
    return source_profile.NarrativeSourceProposal(
        n=f"Registro sintético preservado para {case_id}, sem alterar o estado canônico.",
        q="Qual é sua próxima ação?",
    )


def _error(request, *, category=ErrorCategory.PROVIDER_UNAVAILABLE, code=runner.RETRY_CODE, retryable=True):
    return LLMInvocationError(
        NormalizedError(
            category=category,
            code=code,
            phase=OperationPhase.CONNECT,
            invocation_id=request.invocation_id,
            target=request.target,
            safe_message="Synthetic provider failure.",
            evidence=_evidence(request),
            retryable=retryable,
        )
    )


def _preflight_file(tmp_path: Path, prepared) -> tuple[Path, str]:
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(prepared.metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_l3_changes_only_the_approved_retry_policy() -> None:
    baseline = _preflight(ROOT / "scripts/evaluate_openrouter_free_narrators_l2_live.py")
    current = _preflight(RUNNER)

    assert current["hypothesis_id"] == runner.HYPOTHESIS_ID
    assert current["execution_window"] == "new_free_daily_window_only"
    assert current["single_changed_variable"]["name"] == "overload_retry_policy"
    assert current["max_calls"] == 48
    assert current["automatic_retries"] == 1
    assert current["retry_policy"] == {
        "max_attempts_per_slot": 2,
        "category": "provider_unavailable",
        "code": "openrouter_provider_overloaded",
        "retryable_must_be_true": True,
        "same_request_body": True,
        "same_target": True,
        "reported_retry_after_honored_up_to_seconds": 60.0,
        "default_delay_seconds": 15.0,
        "all_other_errors_retried": False,
    }
    assert current["generation_parameters"] == {
        **baseline["generation_parameters"],
        "max_total_output_tokens": 98304,
    }
    for field in (
        "synthetic_only", "campaign_data_eligible", "repair", "model_fallback",
        "provider_fallback", "paid_spend_authorized",
        "zero_cost_must_be_reported_per_response", "routing_policy",
        "selected_candidates", "schedule", "admission",
    ):
        assert current[field] == baseline[field]
    assert current["provider_calls"] == 0
    assert current["credential_inspected"] is False


@pytest.mark.parametrize(
    "error, expected",
    [
        ({"category": runner.RETRY_CATEGORY, "code": runner.RETRY_CODE, "retryable": True}, 15.0),
        ({"category": runner.RETRY_CATEGORY, "code": runner.RETRY_CODE, "retryable": True, "retry_after_seconds": 0}, 0.0),
        ({"category": runner.RETRY_CATEGORY, "code": runner.RETRY_CODE, "retryable": True, "retry_after_seconds": 60}, 60.0),
        ({"category": runner.RETRY_CATEGORY, "code": runner.RETRY_CODE, "retryable": True, "retry_after_seconds": 61}, None),
        ({"category": runner.RETRY_CATEGORY, "code": "other", "retryable": True}, None),
        ({"category": "transport", "code": runner.RETRY_CODE, "retryable": True}, None),
        ({"category": runner.RETRY_CATEGORY, "code": runner.RETRY_CODE, "retryable": False}, None),
    ],
)
def test_retry_delay_is_exact_and_bounded(error, expected) -> None:
    assert runner._retry_delay(error) == expected


@pytest.mark.asyncio
async def test_exact_overload_retries_same_request_once_and_verifies(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    calls = []

    async def no_sleep(delay):
        return None

    async def generate(self, request):
        calls.append(request)
        if len(calls) == 1:
            raise _error(request)
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(value=_proposal(case_id), evidence=_evidence(request))

    monkeypatch.setattr(runner.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(runner.OpenRouterFreeAdapter, "generate_structured", generate)
    prepared = runner.prepare_live()
    batch = str(uuid4())
    document = await runner.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=runner.run_path(batch),
        pacer=NoWaitPacer(),
    )
    rows = [json.loads(line)["record"] for line in (runner.run_path(batch) / "records.jsonl").read_text(encoding="utf-8").splitlines()]

    assert document["summary"]["calls_made"] == 25
    assert document["summary"]["retry_attempts"] == 1
    assert document["summary"]["completed"] == 24
    assert rows[0]["attempt_count"] == 2
    assert rows[0]["attempts"][0]["retry_scheduled"] is True
    assert rows[0]["attempts"][0]["retry_delay_seconds"] == 15.0
    assert rows[0]["attempts"][0]["request"] == rows[0]["attempts"][1]["request"]
    preflight, digest = _preflight_file(tmp_path, prepared)
    assert runner.verify_artifacts(
        runner.run_path(batch) / "summary.json", preflight, batch,
        expected_preflight_sha256=digest,
    )["verified"] is True

    records_path = runner.run_path(batch) / "records.jsonl"
    envelopes = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    envelopes[0]["record"]["attempts"][0]["request"]["body_sha256"] = "0" * 64
    records_path.write_text(
        "".join(runner.base._canonical(envelope) + "\n" for envelope in envelopes),
        encoding="utf-8",
    )
    summary_path = runner.run_path(batch) / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"]["records"]["sha256"] = hashlib.sha256(records_path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="live_attempt_identity_invalid"):
        runner.verify_artifacts(
            summary_path, preflight, batch, expected_preflight_sha256=digest,
        )


@pytest.mark.asyncio
async def test_other_error_is_not_retried_and_stops_globally(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    calls = 0

    async def generate(self, request):
        nonlocal calls
        calls += 1
        raise _error(request, code="other_provider_failure", retryable=True)

    monkeypatch.setattr(runner.OpenRouterFreeAdapter, "generate_structured", generate)
    prepared = runner.prepare_live()
    batch = str(uuid4())
    document = await runner.run_live(
        prepared, api_key=SecretStr("synthetic-live-test-key"), batch_id=batch,
        run_directory=runner.run_path(batch), pacer=NoWaitPacer(),
    )
    assert calls == document["summary"]["calls_made"] == 1
    assert document["summary"]["retry_attempts"] == 0
    assert document["summary"]["skipped"] == 23


@pytest.mark.asyncio
async def test_exact_overload_is_attempted_at_most_twice(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    calls = 0

    async def no_sleep(delay):
        return None

    async def generate(self, request):
        nonlocal calls
        calls += 1
        raise _error(request)

    monkeypatch.setattr(runner.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(runner.OpenRouterFreeAdapter, "generate_structured", generate)
    prepared = runner.prepare_live()
    batch = str(uuid4())
    document = await runner.run_live(
        prepared, api_key=SecretStr("synthetic-live-test-key"), batch_id=batch,
        run_directory=runner.run_path(batch), pacer=NoWaitPacer(),
    )
    rows = [json.loads(line)["record"] for line in (runner.run_path(batch) / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    assert calls == document["summary"]["calls_made"] == 2
    assert document["summary"]["retry_attempts"] == 1
    assert document["summary"]["skipped"] == 23
    assert rows[0]["attempt_count"] == 2
    assert rows[0]["attempts"][1]["retry_scheduled"] is False


@pytest.mark.asyncio
async def test_cancellation_before_dispatch_is_persisted_without_counting_a_call(tmp_path, monkeypatch) -> None:
    _configure(monkeypatch, tmp_path)
    prepared = runner.prepare_live()
    batch = str(uuid4())
    document = await runner.run_live(
        prepared, api_key=SecretStr("synthetic-live-test-key"), batch_id=batch,
        run_directory=runner.run_path(batch), pacer=CancellingPacer(),
    )
    assert document["summary"]["calls_made"] == 0
    assert document["summary"]["process_exit_code"] == 130
    preflight, digest = _preflight_file(tmp_path, prepared)
    assert runner.verify_artifacts(
        runner.run_path(batch) / "summary.json", preflight, batch,
        expected_preflight_sha256=digest,
    )["verified"] is True


def test_l3_missing_key_stops_before_run_creation(tmp_path: Path) -> None:
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps(_preflight(RUNNER), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected = ROOT / f"eval-results/openrouter-free-narrators-l3-{batch_id}"
    blocked = subprocess.run(
        [str(PYTHON), str(RUNNER), "--live", "--allow-synthetic-only", "--batch-id", batch_id,
         "--expected-preflight", str(preflight), "--expected-preflight-sha256", digest],
        cwd=ROOT, env=_keyless(), capture_output=True, text=True,
    )
    assert blocked.returncode == 3
    assert "credential_missing" in blocked.stderr
    assert not expected.exists()


def test_l3_launcher_freezes_retry_window_masks_and_clears_credential() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert source.count("-AsSecureString") == 2
    assert ".env" not in source
    assert "new_free_daily_window_only" in source
    assert "max_calls -ne 48" in source
    assert "max_attempts_per_slot -ne 2" in source
    assert "openrouter_provider_overloaded" in source
    assert "max_total_output_tokens -ne 98304" in source
    assert source.count("--preflight") == 1
    assert source.count("--live") == 1
    assert source.count("--verify-artifacts") == 1
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1
