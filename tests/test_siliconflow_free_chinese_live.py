from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_siliconflow_free_chinese_live.py"
LAUNCHER = ROOT / "scripts/run_siliconflow_free_chinese_live.ps1"
KEY_ENV = "STORYTELLER_SILICONFLOW_FREE_KEY"


def _keyless() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(KEY_ENV, None)
    return environment


def test_preflight_freezes_three_exact_free_targets() -> None:
    result = subprocess.run([str(PYTHON), str(RUNNER), "--preflight"], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["hypothesis_id"] == "HYP-005-SILICONFLOW-FREE-CHINESE-L1"
    assert preflight["max_calls"] == 24
    assert preflight["paid_spend_authorized"] is False
    assert preflight["provider_calls"] == 0
    assert preflight["credential_inspected"] is False
    assert preflight["automatic_retries"] == 0
    assert preflight["repair"] is False
    assert preflight["fallback"] is False
    assert [x["model"] for x in preflight["selected_candidates"]] == [
        "XingChenAGI/Xing4.0-29B", "Qwen/Qwen3.5-4B", "THUDM/GLM-4-9B-0414"
    ]
    assert len(preflight["schedule"]) == 24


def test_missing_key_stops_before_run_creation(tmp_path: Path) -> None:
    preflight_result = subprocess.run([str(PYTHON), str(RUNNER), "--preflight"], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(preflight_result.stdout, encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected = ROOT / f"eval-results/siliconflow-free-chinese-{batch_id}"
    result = subprocess.run([
        str(PYTHON), str(RUNNER), "--live", "--allow-synthetic-only", "--batch-id", batch_id,
        "--expected-preflight", str(preflight), "--expected-preflight-sha256", digest,
    ], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    assert result.returncode == 3
    assert "credential_missing" in result.stderr
    assert not expected.exists()


def test_launcher_uses_masked_input_and_clears_credential() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert source.count("-AsSecureString") == 2
    assert ".env" not in source
    assert "SiliconFlow API key" in source
    assert "Digite FREE" in source
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1

