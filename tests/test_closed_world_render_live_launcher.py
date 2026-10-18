from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "scripts/run_closed_world_render_live.ps1"


def test_live_launcher_uses_only_the_existing_process_credential() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert "STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY" in source
    assert "GetEnvironmentVariable($credentialName, 'Process')" in source
    assert "Read-Host" not in source
    assert ".env" not in source
    assert "-ApiKey" not in source
    assert "--api-key-env" not in source
    assert "-ErrorAction Continue\n    exit 3" in source


def test_live_launcher_freezes_runs_verifies_and_clears_once() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert source.count("--preflight") == 1
    assert source.count("'--live'") == 1
    assert source.count("'--allow-synthetic-only'") == 1
    assert source.count("'--verify-artifacts'") == 1
    assert source.count("'--expected-preflight-sha256'") == 2
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1
    assert "LIVE_EXIT=" in source
    assert "VERIFY_EXIT=" in source
