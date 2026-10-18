from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import SecretStr

from api.llm.contract import (
    AdapterIdentity,
    ErrorCategory,
    InvocationEvidence,
    LLMInvocationError,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceValue,
    StructuredGenerationResult,
)
from scripts import evaluate_grounded_progression_live as live
from scripts import narrator_source_profile as source_profile


class NoWaitPacer:
    def __init__(self) -> None:
        self.labels: list[str] = []

    async def before_call(self, label: str) -> None:
        self.labels.append(label)


class CancellingPacer:
    async def before_call(self, label: str) -> None:
        raise asyncio.CancelledError


def _evidence(request, *, model: str | None = None) -> InvocationEvidence:
    now = datetime.now(timezone.utc)
    return InvocationEvidence(
        provenance=Provenance(
            invocation_id=request.invocation_id,
            requested_target=request.target,
            adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
            effective_provider=ProvenanceValue.observed("Groq"),
            effective_model=ProvenanceValue.reported(model or request.target.model),
            started_at=now,
            finished_at=now,
        )
    )


def _proposal(case_id: str, *, suffix: str = "") -> source_profile.NarrativeSourceProposal:
    narrative = (
        "O ambiente conserva os fatos apresentados e oferece um detalhe concreto, "
        "sem decidir a reação do personagem nem completar qualquer estado ainda desconhecido. "
        f"O foco deste registro sintético permanece no caso {case_id}. {suffix}"
    )
    return source_profile.NarrativeSourceProposal(
        n=narrative,
        q="Qual é sua próxima ação?",
    )


def _preflight_file(tmp_path: Path, prepared: live.PreparedLive) -> tuple[Path, str]:
    path = tmp_path / "preflight.json"
    path.write_text(
        json.dumps(prepared.metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_preflight_freezes_l1_without_credentials_or_calls(monkeypatch):
    original = live.os.environ.get

    def guarded(name, *args):
        assert name != live.KEY_ENV
        return original(name, *args)

    monkeypatch.setattr(live.os.environ, "get", guarded)
    prepared = live.prepare_live()

    assert prepared.metadata["option"] == "L1"
    assert prepared.metadata["max_calls"] == 16
    assert prepared.metadata["provider_calls"] == 0
    assert prepared.metadata["credential_inspected"] is False
    assert prepared.metadata["automatic_retries"] == 0
    assert prepared.metadata["repair"] is False
    assert prepared.metadata["fallback"] is False
    assert prepared.metadata["paid_spend_authorized"] is False
    assert [item["model"] for item in prepared.metadata["selected_candidates"]] == [
        "qwen/qwen3.8-27b", "openai/gpt-oss-120b"
    ]
    assert len(prepared.metadata["schedule"]) == 16


def test_preflight_accepts_only_the_recorded_protected_credential_transition(monkeypatch):
    original = live.offline._load_json

    def available_gate(path):
        value = original(path)
        if Path(path) == live.LIVE_GATE:
            value = json.loads(json.dumps(value))
            value["credential_status"] = "available_protected"
        return value

    monkeypatch.setattr(live.offline, "_load_json", available_gate)
    prepared = live.prepare_live()

    assert prepared.metadata["provider_calls"] == 0
    assert prepared.metadata["credential_inspected"] is False


def test_schedule_keeps_each_dependency_inside_candidate_chain():
    prepared = live.prepare_live()
    schedule = prepared.metadata["schedule"]

    for candidate_id in live.CANDIDATE_IDS:
        first = next(
            item for item in schedule
            if item["candidate_id"] == candidate_id
            and item["case_id"] == "wait-without-authorized-progression"
        )
        second = next(
            item for item in schedule
            if item["candidate_id"] == candidate_id
            and item["case_id"] == "wait-with-authorized-event"
        )
        assert second["slot"] == first["slot"] + 1
        assert second["prior_case_id"] == first["case_id"]


@pytest.mark.asyncio
async def test_full_fake_run_makes_sixteen_calls_and_verifies_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    requests = []

    async def generate(self, request):
        requests.append(request)
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    pacer = NoWaitPacer()
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=pacer,
    )

    assert document["process_exit_code"] == 0
    assert document["summary"]["calls_made"] == 16
    assert document["summary"]["completed"] == 16
    assert len(requests) == len(pacer.labels) == 16
    qwen_second = json.loads(requests[1].messages[1].content)
    gpt_second = json.loads(requests[3].messages[1].content)
    assert "wait-without-authorized-progression" in qwen_second["attributed_source"]["case_id"]
    assert qwen_second["attributed_source"]["content"] != gpt_second["attributed_source"]["content"] or requests[1].target != requests[3].target

    preflight, digest = _preflight_file(tmp_path, prepared)
    result = live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )
    assert result["verified"] is True
    assert result["process_exit_code"] == 0
    for path in live.run_path(batch).iterdir():
        if path.is_file():
            assert b"synthetic-live-test-key" not in path.read_bytes()


@pytest.mark.asyncio
async def test_chain_local_failure_skips_only_its_dependent_case(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls = 0

    async def generate(self, request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LLMInvocationError(
                NormalizedError(
                    category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
                    code="synthetic_invalid",
                    phase=OperationPhase.STRUCTURE_VALIDATION,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic invalid output.",
                    evidence=_evidence(request),
                    retryable=False,
                )
            )
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(value=_proposal(case_id), evidence=_evidence(request))

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=NoWaitPacer(),
    )
    records = [
        json.loads(line)["record"]
        for line in (live.run_path(batch) / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert calls == 15
    assert document["process_exit_code"] == 1
    assert records[0]["status"] == "failed"
    assert records[1] == {
        "slot": 1,
        "candidate_id": live.QWEN_ID,
        "case_id": "wait-with-authorized-event",
        "prior_case_id": "wait-without-authorized-progression",
        "status": "skipped",
        "reason": "prior_case_failed",
    }
    assert records[2]["status"] == "completed"

    preflight, digest = _preflight_file(tmp_path, prepared)
    result = live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )
    assert result["verified"] is True
    assert result["process_exit_code"] == 1


@pytest.mark.asyncio
async def test_transport_failure_stops_globally_without_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls = 0

    async def generate(self, request):
        nonlocal calls
        calls += 1
        raise LLMInvocationError(
            NormalizedError(
                category=ErrorCategory.TRANSPORT_FAILURE,
                code="synthetic_transport_failure",
                phase=OperationPhase.CONNECT,
                invocation_id=request.invocation_id,
                target=request.target,
                safe_message="Synthetic transport failure.",
                evidence=_evidence(request),
                retryable=True,
            )
        )

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=NoWaitPacer(),
    )

    assert calls == 1
    assert document["summary"]["calls_made"] == 1
    assert document["summary"]["skipped"] == 15
    assert document["process_exit_code"] == 2

    preflight, digest = _preflight_file(tmp_path, prepared)
    assert live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )["verified"] is True


@pytest.mark.asyncio
async def test_cancellation_during_pacing_records_zero_calls_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)

    async def generate(self, request):
        pytest.fail("provider dispatch must not happen after pacing cancellation")

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=CancellingPacer(),
    )

    assert document["summary"]["calls_made"] == 0
    assert document["summary"]["failed"] == 1
    assert document["summary"]["skipped"] == 15
    assert document["process_exit_code"] == 130

    preflight, digest = _preflight_file(tmp_path, prepared)
    assert live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )["verified"] is True


@pytest.mark.asyncio
async def test_deadline_is_rebased_after_each_pacing_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    clock = [datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)]
    observed_deadlines = []

    class AdvancingPacer:
        async def before_call(self, label: str) -> None:
            clock[0] += timedelta(seconds=45)

    async def generate(self, request):
        observed_deadlines.append(request.deadline)
        assert request.deadline == clock[0] + timedelta(seconds=live.DEADLINE_SECONDS)
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live, "utc_now", lambda: clock[0])
    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=AdvancingPacer(),
    )

    assert len(observed_deadlines) == live.MAX_CALLS
    assert document["summary"]["completed"] == live.MAX_CALLS


@pytest.mark.asyncio
async def test_target_mismatch_stops_globally_after_one_call(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)

    async def generate(self, request):
        return StructuredGenerationResult(
            value=_proposal("mismatch"),
            evidence=_evidence(request, model="unexpected/model"),
        )

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=NoWaitPacer(),
    )

    assert document["summary"]["calls_made"] == 1
    assert document["summary"]["skipped"] == 15
    assert document["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_credential_echo_is_blocked_and_never_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    secret = "synthetic-secret-never-persist"

    async def generate(self, request):
        return StructuredGenerationResult(
            value=_proposal("echo", suffix=secret), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr(secret),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=NoWaitPacer(),
    )

    assert document["process_exit_code"] == 3
    assert document["summary"]["calls_made"] == 1
    for path in live.run_path(batch).iterdir():
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


def test_cli_live_without_dedicated_credential_stops_before_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path / "results")
    monkeypatch.delenv(live.KEY_ENV, raising=False)
    prepared = live.prepare_live()
    preflight, digest = _preflight_file(tmp_path, prepared)
    batch = str(uuid4())

    code = live.main(
        [
            "--live", "--allow-synthetic-only", "--batch-id", batch,
            "--expected-preflight", str(preflight),
            "--expected-preflight-sha256", digest,
        ]
    )

    assert code == 3
    assert "credential_missing" in capsys.readouterr().err
    assert not live.run_path(batch).exists()


@pytest.mark.asyncio
async def test_rehashed_record_tampering_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)

    async def generate(self, request):
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(value=_proposal(case_id), evidence=_evidence(request))

    monkeypatch.setattr(live.GroqAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-live-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        pacer=NoWaitPacer(),
    )
    preflight, digest = _preflight_file(tmp_path, prepared)
    records_path = live.run_path(batch) / "records.jsonl"
    rows = records_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["record"]["capsule"]["case_id"] = "forged"
    rows[0] = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
    records_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    summary_path = live.run_path(batch) / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"]["records"]["sha256"] = hashlib.sha256(records_path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        live.verify_artifacts(
            summary_path, preflight, batch,
            expected_preflight_sha256=digest,
        )
