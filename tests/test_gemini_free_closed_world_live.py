from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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
from scripts import evaluate_gemini_free_closed_world_live as live
from scripts import narrator_source_profile as source_profile


class NoWaitPacer:
    def __init__(self) -> None:
        self.labels: list[str] = []

    async def before_call(self, label: str) -> None:
        self.labels.append(label)


class NoWaitRetryWaiter:
    def __init__(self) -> None:
        self.waits: list[tuple[int, str]] = []

    async def wait(self, delay_seconds: int, label: str) -> None:
        self.waits.append((delay_seconds, label))


def _evidence(request, *, model: str = "gemini-3.8-flash-001") -> InvocationEvidence:
    now = datetime.now(timezone.utc)
    return InvocationEvidence(
        provenance=Provenance(
            invocation_id=request.invocation_id,
            requested_target=request.target,
            adapter=AdapterIdentity(name="gemini-generate-content-http", version="1.0"),
            effective_provider=ProvenanceValue.observed("Google Gemini"),
            effective_model=ProvenanceValue.reported(model),
            started_at=now,
            finished_at=now,
        )
    )


def _proposal(case_id: str, suffix: str = "") -> source_profile.NarrativeSourceProposal:
    return source_profile.NarrativeSourceProposal(
        n=(
            "O ambiente conserva cada fato delimitado no plano e mantém os objetos "
            "em seus estados descritos, sem escolher pelo personagem ou preencher "
            f"informação desconhecida. Este registro sintético representa {case_id}. {suffix}"
        ),
        q="Como você deseja prosseguir?",
    )


def _preflight_file(tmp_path: Path, prepared: live.PreparedLive) -> tuple[Path, str]:
    path = tmp_path / "preflight.json"
    path.write_text(
        json.dumps(prepared.metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_preflight_is_keyless_free_tier_synthetic_and_bounded(monkeypatch):
    original = live.os.environ.get

    def guarded(name, *args):
        assert name != live.KEY_ENV
        return original(name, *args)

    monkeypatch.setattr(live.os.environ, "get", guarded)
    prepared = live.prepare_live()

    assert prepared.metadata["hypothesis_id"] == "HYP-003-GEMINI-FREE-L4"
    assert (
        prepared.metadata["option"]
        == "GEMINI-FREE-L4-INTEGRAL-TRANSPORT-RETRY"
    )
    assert prepared.metadata["max_cases"] == 8
    assert prepared.metadata["max_provider_attempts"] == 16
    assert prepared.metadata["automatic_retries"] == 2
    assert prepared.metadata["narrative_retries"] == 0
    assert prepared.metadata["transport_retry_policy"] == {
        "only_without_response": True,
        "eligible_http_statuses": [408, 429, "5xx"],
        "eligible_phases": ["connect"],
        "max_retries_per_case": 2,
        "global_attempt_cap": 16,
        "backoff_base_seconds": [60, 180],
        "deterministic_jitter_max_seconds": 15,
        "all_attempts_persisted": True,
    }
    assert prepared.metadata["provider_calls"] == 0
    assert prepared.metadata["credential_inspected"] is False
    assert prepared.metadata["paid_spend_authorized"] is False
    assert prepared.metadata["synthetic_only"] is True
    assert prepared.metadata["free_tier_content_may_improve_google_products"] is True
    assert prepared.metadata["selected_candidate"]["model"] == "gemini-3.8-flash"
    assert len(prepared.metadata["schedule"]) == 8


def test_launcher_masks_tier_confirmation_and_api_key():
    launcher = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_gemini_free_closed_world_live.ps1"
    ).read_text(encoding="utf-8")

    assert "secureTierConfirmation = Read-Host" in launcher
    assert "'Digite FREE para confirmar o projeto sem billing habilitado' `\n        -AsSecureString" in launcher
    assert "secureKey = Read-Host 'Gemini API key' -AsSecureString" in launcher


def test_request_uses_native_schema_low_thinking_and_no_sampling_knobs():
    prepared = live.prepare_live()
    request = live._request(prepared, str(uuid4()), "map-cylinder-hold", {})
    body = live._request_body(request)
    generation = body["generationConfig"]

    assert generation["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert generation["maxOutputTokens"] == 768
    assert generation["responseFormat"]["text"]["mimeType"] == "APPLICATION_JSON"
    assert "schema" in generation["responseFormat"]["text"]
    assert "temperature" not in generation
    assert "topP" not in generation
    assert "topK" not in generation
    assert body["store"] is False


@pytest.mark.asyncio
async def test_full_fake_run_makes_eight_calls_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    requests = []

    async def generate(self, request):
        requests.append(request)
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    pacer = NoWaitPacer()
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=pacer,
    )

    assert document["process_exit_code"] == 0
    assert document["summary"]["calls_made"] == 8
    assert document["summary"]["transport_retries_made"] == 0
    assert document["summary"]["completed"] == 8
    assert len(requests) == len(pacer.labels) == 8
    second = json.loads(requests[1].messages[1].content)
    assert second["attributed_source"]["case_id"] == "map-cylinder-hold"

    preflight, digest = _preflight_file(tmp_path, prepared)
    result = live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )
    assert result["verified"] is True
    for path in live.run_path(batch).iterdir():
        if path.is_file():
            assert b"synthetic-gemini-test-key" not in path.read_bytes()


@pytest.mark.asyncio
async def test_transport_failure_without_http_status_stops_without_retry(
    tmp_path, monkeypatch
):
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

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
    )

    assert calls == 1
    assert document["summary"]["calls_made"] == 1
    assert document["summary"]["skipped"] == 7
    assert document["process_exit_code"] == 2


@pytest.mark.asyncio
async def test_503_retries_twice_then_completes_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls_by_case: dict[str, int] = {}

    async def generate(self, request):
        case_id = request.operation.rsplit(".", 1)[-1]
        calls_by_case[case_id] = calls_by_case.get(case_id, 0) + 1
        if case_id == "map-cylinder-hold" and calls_by_case[case_id] <= 2:
            raise LLMInvocationError(
                NormalizedError(
                    category=ErrorCategory.PROVIDER_UNAVAILABLE,
                    code="synthetic_503",
                    phase=OperationPhase.CONNECT,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic 503.",
                    status_code=503,
                    retryable=True,
                    evidence=_evidence(request),
                )
            )
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    waiter = NoWaitRetryWaiter()
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
        retry_waiter=waiter,
    )

    assert document["process_exit_code"] == 0
    assert document["summary"]["calls_made"] == 10
    assert document["summary"]["transport_retries_made"] == 2
    assert document["summary"]["completed"] == 8
    assert [delay for delay, _ in waiter.waits] == [
        live._transport_retry_delay(batch, 0, 1),
        live._transport_retry_delay(batch, 0, 2),
    ]

    preflight, digest = _preflight_file(tmp_path, prepared)
    verified = live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )
    assert verified["verified"] is True


@pytest.mark.asyncio
async def test_verifier_rejects_tampered_retry_delay_even_with_updated_file_hash(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    first_call = True

    async def generate(self, request):
        nonlocal first_call
        if first_call:
            first_call = False
            raise LLMInvocationError(
                NormalizedError(
                    category=ErrorCategory.PROVIDER_UNAVAILABLE,
                    code="synthetic_503",
                    phase=OperationPhase.CONNECT,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic 503.",
                    status_code=503,
                    retryable=True,
                    evidence=_evidence(request),
                )
            )
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
        retry_waiter=NoWaitRetryWaiter(),
    )
    run_directory = live.run_path(batch)
    records_path = run_directory / "records.jsonl"
    envelopes = [json.loads(line) for line in records_path.read_text().splitlines()]
    envelopes[0]["record"]["attempts"][0]["retry_delay_seconds"] += 1
    records_path.write_text(
        "".join(live._canonical(value) + "\n" for value in envelopes),
        encoding="utf-8",
    )
    summary_path = run_directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"]["records"]["sha256"] = hashlib.sha256(
        records_path.read_bytes()
    ).hexdigest()
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    preflight, digest = _preflight_file(tmp_path, prepared)

    with pytest.raises(ValueError, match="gemini_free_transport_retry_invalid"):
        live.verify_artifacts(
            summary_path,
            preflight,
            batch,
            expected_preflight_sha256=digest,
        )


@pytest.mark.asyncio
async def test_503_exhausts_two_retries_then_stops_globally(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls = 0

    async def generate(self, request):
        nonlocal calls
        calls += 1
        raise LLMInvocationError(
            NormalizedError(
                category=ErrorCategory.PROVIDER_UNAVAILABLE,
                code="synthetic_503",
                phase=OperationPhase.CONNECT,
                invocation_id=request.invocation_id,
                target=request.target,
                safe_message="Synthetic 503.",
                status_code=503,
                retryable=True,
                evidence=_evidence(request),
            )
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    waiter = NoWaitRetryWaiter()
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
        retry_waiter=waiter,
    )

    assert calls == 3
    assert len(waiter.waits) == 2
    assert document["summary"]["calls_made"] == 3
    assert document["summary"]["transport_retries_made"] == 2
    assert document["summary"]["failed"] == 1
    assert document["summary"]["skipped"] == 7
    assert document["process_exit_code"] == 2


@pytest.mark.asyncio
async def test_global_attempt_cap_stops_at_sixteen_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls_by_case: dict[str, int] = {}

    async def generate(self, request):
        case_id = request.operation.rsplit(".", 1)[-1]
        calls_by_case[case_id] = calls_by_case.get(case_id, 0) + 1
        should_fail = calls_by_case[case_id] == 1 or (
            case_id == "ambiguous-disc-and-linen"
            and calls_by_case[case_id] == 2
        )
        if should_fail:
            raise LLMInvocationError(
                NormalizedError(
                    category=ErrorCategory.PROVIDER_UNAVAILABLE,
                    code="synthetic_503",
                    phase=OperationPhase.CONNECT,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic 503.",
                    status_code=503,
                    retryable=True,
                    evidence=_evidence(request),
                )
            )
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
        retry_waiter=NoWaitRetryWaiter(),
    )

    assert document["summary"]["calls_made"] == 16
    assert document["summary"]["transport_retries_made"] == 8
    assert document["summary"]["completed"] == 7
    assert document["summary"]["failed"] == 1
    assert document["process_exit_code"] == 2

    preflight, digest = _preflight_file(tmp_path, prepared)
    verified = live.verify_artifacts(
        live.run_path(batch) / "summary.json",
        preflight,
        batch,
        expected_preflight_sha256=digest,
    )
    assert verified["verified"] is True


@pytest.mark.asyncio
async def test_invalid_structured_output_is_never_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    calls = 0

    async def generate(self, request):
        nonlocal calls
        calls += 1
        if request.operation.endswith("map-cylinder-hold"):
            raise LLMInvocationError(
                NormalizedError(
                    category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
                    code="synthetic_invalid_structure",
                    phase=OperationPhase.STRUCTURE_VALIDATION,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic invalid structure.",
                    retryable=False,
                    evidence=_evidence(request),
                )
            )
        case_id = request.operation.rsplit(".", 1)[-1]
        return StructuredGenerationResult(
            value=_proposal(case_id), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    waiter = NoWaitRetryWaiter()
    document = await live.run_live(
        prepared,
        api_key=SecretStr("synthetic-gemini-test-key"),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
        retry_waiter=waiter,
    )

    assert calls == 7
    assert waiter.waits == []
    assert document["summary"]["transport_retries_made"] == 0
    assert document["summary"]["failed"] == 1
    assert document["summary"]["skipped"] == 1
    assert document["process_exit_code"] == 1


@pytest.mark.parametrize(
    ("status", "category", "eligible"),
    [
        (408, "timeout", True),
        (429, "rate_limited", True),
        (503, "provider_unavailable", True),
        (400, "invalid_request", False),
        (None, "transport_failure", False),
    ],
)
def test_strict_transport_retry_predicate(status, category, eligible):
    error = {
        "status_code": status,
        "category": category,
        "retryable": True,
        "partial_output": False,
        "phase": "connect",
    }
    assert live._is_strict_transport_retry(error) is eligible
    error["partial_output"] = True
    assert live._is_strict_transport_retry(error) is False


@pytest.mark.asyncio
async def test_free_tier_confirmation_is_required_before_directory_or_call(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)

    async def generate(self, request):
        pytest.fail("provider call must not happen")

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    with pytest.raises(ValueError, match="gemini_free_tier_not_confirmed"):
        await live.run_live(
            prepared,
            api_key=SecretStr("synthetic-gemini-test-key"),
            batch_id=batch,
            run_directory=live.run_path(batch),
            free_tier_project_confirmed=False,
            pacer=NoWaitPacer(),
        )
    assert not live.run_path(batch).exists()


def test_cli_without_dedicated_credential_stops_before_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path / "results")
    monkeypatch.delenv(live.KEY_ENV, raising=False)
    prepared = live.prepare_live()
    preflight, digest = _preflight_file(tmp_path, prepared)
    batch = str(uuid4())

    code = live.main(
        [
            "--live",
            "--allow-synthetic-only",
            "--confirm-free-tier-project",
            "--batch-id",
            batch,
            "--expected-preflight",
            str(preflight),
            "--expected-preflight-sha256",
            digest,
        ]
    )

    assert code == 3
    assert "gemini_free_credential_missing" in capsys.readouterr().err
    assert not live.run_path(batch).exists()


@pytest.mark.asyncio
async def test_credential_echo_is_blocked_and_never_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "OUTPUT_ROOT", tmp_path)
    secret = "synthetic-secret-never-persist"

    async def generate(self, request):
        return StructuredGenerationResult(
            value=_proposal("echo", secret), evidence=_evidence(request)
        )

    monkeypatch.setattr(live.GeminiAdapter, "generate_structured", generate)
    prepared = live.prepare_live()
    batch = str(uuid4())
    document = await live.run_live(
        prepared,
        api_key=SecretStr(secret),
        batch_id=batch,
        run_directory=live.run_path(batch),
        free_tier_project_confirmed=True,
        pacer=NoWaitPacer(),
    )

    assert document["process_exit_code"] == 3
    assert document["summary"]["calls_made"] == 1
    for path in live.run_path(batch).iterdir():
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
