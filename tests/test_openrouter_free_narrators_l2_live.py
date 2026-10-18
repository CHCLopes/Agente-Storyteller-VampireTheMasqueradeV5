from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from scripts import evaluate_openrouter_free_narrators_l2_live as runner


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_openrouter_free_narrators_l2_live.py"
L1_RUNNER = ROOT / "scripts/evaluate_openrouter_free_narrators_live.py"
LAUNCHER = ROOT / "scripts/run_openrouter_free_narrators_l2_live.ps1"
KEY_ENV = "STORYTELLER_OPENROUTER_FREE_KEY"


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


def test_l2_changes_only_the_approved_generation_budget() -> None:
    l1 = _preflight(L1_RUNNER)
    l2 = _preflight(RUNNER)

    assert l2["hypothesis_id"] == "HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET"
    assert l2["single_changed_variable"] == {
        "name": "max_output_tokens",
        "from": 768,
        "to": 2048,
    }
    assert l2["generation_parameters"] == {
        **l1["generation_parameters"],
        "max_output_tokens": 2048,
        "max_total_output_tokens": 49152,
    }
    for field in (
        "synthetic_only",
        "campaign_data_eligible",
        "max_calls",
        "automatic_retries",
        "repair",
        "model_fallback",
        "provider_fallback",
        "paid_spend_authorized",
        "zero_cost_must_be_reported_per_response",
        "human_review_required",
        "runtime_default_eligible",
        "routing_policy",
        "selected_candidates",
        "schedule",
        "admission",
    ):
        assert l2[field] == l1[field]
    assert l2["provider_calls"] == 0
    assert l2["credential_inspected"] is False


def test_l2_dispatch_request_and_payload_use_2048_without_reasoning_change(
    monkeypatch,
) -> None:
    prepared = runner.prepare_live()
    monkeypatch.setattr(runner.base, "VERSION", runner.VERSION)
    monkeypatch.setattr(runner.base, "MAX_OUTPUT_TOKENS", 2048)
    monkeypatch.setattr(runner.base, "DEADLINE_SECONDS", 90)
    request = runner.base._request(
        prepared,
        str(uuid4()),
        runner.NEMOTRON,
        "hold-silent-bell",
        {},
    )
    assert request.parameters.max_output_tokens == 2048
    assert request.parameters.temperature == 0.65

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
    assert payload["max_tokens"] == 2048
    assert payload["temperature"] == 0.65
    assert "reasoning" not in payload
    assert "reasoning_effort" not in payload
    assert payload["provider"] == {
        "only": ["nvidia"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
    }


def test_l2_missing_key_stops_before_run_creation(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(PYTHON), str(RUNNER), "--preflight"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    preflight = tmp_path / "preflight.json"
    preflight.write_text(result.stdout, encoding="utf-8")
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected = ROOT / f"eval-results/openrouter-free-narrators-l2-{batch_id}"

    blocked = subprocess.run(
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
    assert blocked.returncode == 3
    assert "credential_missing" in blocked.stderr
    assert not expected.exists()


def test_l2_launcher_freezes_budget_masks_and_clears_credential() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert source.count("-AsSecureString") == 2
    assert ".env" not in source
    assert "OpenRouter API key" in source
    assert "Digite FREE" in source
    assert "from -ne 768" in source
    assert "to -ne 2048" in source
    assert "max_output_tokens -ne 2048" in source
    assert "max_total_output_tokens -ne 49152" in source
    assert source.count("--preflight") == 1
    assert source.count("--live") == 1
    assert source.count("--verify-artifacts") == 1
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1
