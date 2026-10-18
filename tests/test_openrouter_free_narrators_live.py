from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from scripts import evaluate_openrouter_free_narrators_live as runner


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_openrouter_free_narrators_live.py"
LAUNCHER = ROOT / "scripts/run_openrouter_free_narrators_live.ps1"
KEY_ENV = "STORYTELLER_OPENROUTER_FREE_KEY"


def _keyless() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(KEY_ENV, None)
    return environment


def test_preflight_freezes_cross_origin_exact_free_targets() -> None:
    result = subprocess.run(
        [str(PYTHON), str(RUNNER), "--preflight"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["hypothesis_id"] == "HYP-005-OPENROUTER-FREE-L1"
    assert preflight["max_calls"] == 24
    assert preflight["paid_spend_authorized"] is False
    assert preflight["provider_calls"] == 0
    assert preflight["credential_inspected"] is False
    assert preflight["automatic_retries"] == 0
    assert preflight["repair"] is False
    assert preflight["model_fallback"] is False
    assert preflight["provider_fallback"] is False
    assert preflight["zero_cost_must_be_reported_per_response"] is True
    assert [x["model"] for x in preflight["selected_candidates"]] == [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "liquid/lfm-2.5-2.6b:free",
        "deepseek/deepseek-v4-flash-0731:free",
    ]
    assert len(preflight["schedule"]) == 24


def test_openrouter_payload_disables_fallback_and_requires_parameters() -> None:
    prepared = runner.prepare_live()
    target = prepared.targets[runner.NEMOTRON]
    request = runner.base.StructuredGenerationRequest(
        invocation_id=str(uuid4()),
        operation="openrouter-payload-contract-test",
        target=target,
        messages=(
            runner.base.LLMMessage(
                role=runner.base.MessageRole.SYSTEM,
                content=prepared.system_prompt,
            ),
            runner.base.LLMMessage(
                role=runner.base.MessageRole.USER,
                content="{}",
            ),
        ),
        deadline=runner.base.utc_now() + timedelta(seconds=90),
        cancellation=runner.base.CancellationToken(),
        parameters=runner.base.GenerationParameters(
            temperature=runner.base.TEMPERATURE,
            max_output_tokens=runner.base.MAX_OUTPUT_TOKENS,
        ),
        response_model=runner.source_profile.NarrativeSourceProposal,
        required_capabilities=(
            runner.base.CapabilityRequirement(
                name=runner.base.CAPABILITY_TEXT_GENERATION
            ),
            runner.base.CapabilityRequirement(
                name=runner.base.CAPABILITY_STRUCTURED_GENERATION,
                allow_emulated=False,
            ),
        ),
    )
    adapter = runner.OpenRouterFreeAdapter(
        base_url=runner.BASE_URL,
        capability_set=runner.base.shared._capabilities(
            prepared.candidates[runner.NEMOTRON], request.target
        ),
        api_key=runner.base.SecretStr("synthetic-test-key"),
    )
    payload = adapter._payload(
        request,
        stream=False,
        response_format=adapter._native_response_format(request),
    )
    assert payload["model"] == request.target.model
    assert "models" not in payload
    assert payload["provider"] == {
        "only": ["nvidia"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
    }
    assert payload["plugins"] == [
        {"id": "web", "enabled": False},
        {"id": "response-healing", "enabled": False},
        {"id": "context-compression", "enabled": False},
    ]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True


def test_openrouter_cost_parser_distinguishes_zero_from_unknown() -> None:
    prepared = runner.prepare_live()
    target = prepared.targets[runner.NEMOTRON]
    adapter = runner.OpenRouterFreeAdapter(
        base_url=runner.BASE_URL,
        capability_set=runner.base.shared._capabilities(
            prepared.candidates[runner.NEMOTRON], target
        ),
        api_key=runner.base.SecretStr("synthetic-test-key"),
    )
    zero = adapter._parse_cost({"usage": {"cost": 0}})
    assert zero.status.value == "reported"
    assert zero.amount == Decimal("0")
    assert zero.currency == "OPENROUTER_CREDITS"
    assert adapter._parse_cost({"usage": {}}).status.value == "unavailable"
    assert adapter._parse_cost({"usage": {"cost": "invalid"}}).status.value == "unavailable"
    assert runner._reported_zero_cost(zero.model_dump(mode="json")) is True
    assert runner._reported_zero_cost({"status": "reported", "amount": "0.01", "currency": "OPENROUTER_CREDITS"}) is False
    assert runner._reported_zero_cost({"status": "unavailable", "amount": None, "currency": None}) is False


def test_missing_key_stops_before_run_creation(tmp_path: Path) -> None:
    preflight_result = subprocess.run(
        [str(PYTHON), str(RUNNER), "--preflight"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert preflight_result.returncode == 0, preflight_result.stderr
    preflight = tmp_path / "preflight.json"
    preflight.write_text(preflight_result.stdout, encoding="utf-8")
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected = ROOT / f"eval-results/openrouter-free-narrators-{batch_id}"
    result = subprocess.run(
        [
            str(PYTHON),
            str(RUNNER),
            "--live",
            "--allow-synthetic-only",
            "--batch-id",
            batch_id,
            "--expected-preflight",
            str(preflight),
            "--expected-preflight-sha256",
            digest,
        ],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3
    assert "credential_missing" in result.stderr
    assert not expected.exists()


def test_launcher_uses_masked_input_and_clears_credential() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert source.count("-AsSecureString") == 2
    assert ".env" not in source
    assert "OpenRouter API key" in source
    assert "Digite FREE" in source
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1
