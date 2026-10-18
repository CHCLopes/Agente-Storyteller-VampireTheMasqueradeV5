from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_closed_world_render_replication_live.py"
LAUNCHER = ROOT / "scripts/run_closed_world_render_replication_live.ps1"
KEY_ENV = "STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY"


def _environment_without_key() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(KEY_ENV, None)
    return environment


def test_replication_preflight_is_distinct_but_keeps_the_frozen_comparison() -> None:
    result = subprocess.run(
        [str(PYTHON), str(RUNNER), "--preflight"],
        cwd=ROOT,
        env=_environment_without_key(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["version"] == "closed-world-render-replication-live-v1"
    assert preflight["hypothesis_id"] == "HYP-004-QWEN-GPT-OSS-REPLICATION-L1"
    assert preflight["option"] == "HYP-004-REPLICATION-L1"
    assert preflight["max_calls"] == 16
    assert preflight["automatic_retries"] == 0
    assert preflight["repair"] is False
    assert preflight["fallback"] is False
    assert preflight["paid_spend_authorized"] is False
    assert preflight["provider_calls"] == 0
    assert preflight["credential_inspected"] is False
    assert preflight["replication"] == {
        "source_hypothesis": "HYP-002-L2",
        "same_cases": True,
        "same_targets": True,
        "same_parameters": True,
        "aggregate_for_admission": False,
        "best_of_selection": False,
        "comparison_requires_independent_human_review": True,
    }
    assert [item["model"] for item in preflight["selected_candidates"]] == [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
    ]
    assert len(preflight["schedule"]) == 16
    assert any(
        item["file"] == "scripts/evaluate_closed_world_render_replication_live.py"
        for item in preflight["inputs"]["implementation"]
    )


def test_replication_live_without_key_stops_before_creating_a_run(tmp_path: Path) -> None:
    preflight_result = subprocess.run(
        [str(PYTHON), str(RUNNER), "--preflight"],
        cwd=ROOT,
        env=_environment_without_key(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert preflight_result.returncode == 0
    preflight = tmp_path / "preflight.json"
    preflight.write_text(preflight_result.stdout, encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected_run = ROOT / f"eval-results/closed-world-render-replication-{batch_id}"
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
        env=_environment_without_key(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert "credential_missing" in result.stderr
    assert not expected_run.exists()


def test_replication_launcher_uses_masked_temporary_input_and_clears_it() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert source.count("-AsSecureString") == 2
    assert "Groq API key" in source
    assert "Digite FREE" in source
    assert ".env" not in source
    assert "--api-key-env" not in source
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1
    assert "HYP-004" in source
    assert "LIVE_EXIT=" in source
    assert "VERIFY_EXIT=" in source
