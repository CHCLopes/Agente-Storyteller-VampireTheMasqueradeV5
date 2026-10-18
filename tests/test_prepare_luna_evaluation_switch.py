from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts import prepare_luna_evaluation_switch as switch


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
SCRIPT = ROOT / "scripts/prepare_luna_evaluation_switch.py"
LUNA_KEY = "STORYTELLER_OPENAI_LUNA_KEY"


def _keyless() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(LUNA_KEY, None)
    return environment


def test_switch_preflight_is_offline_closed_and_does_not_change_default() -> None:
    packet = switch.prepare_switch()

    assert packet["status"] == "prepared_not_activated"
    assert packet["scope"] == "evaluation_lane_only"
    assert packet["target_lane"] == {
        "hypothesis_id": "HYP-006-OPENAI-LUNA-LOW-L1",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "status": "prepared_paid_live_closed",
    }
    assert packet["activation"]["allowed_now"] is False
    assert packet["paid_provider_policy"]["status"] == "temporarily_allowed_for_testing"
    assert packet["paid_provider_policy"]["does_not_authorize_unbounded_spend"] is True
    assert packet["limits"]["free_tier_supported"] is False
    assert packet["limits"]["max_calls"] == 8
    assert packet["provider_calls"] == 0
    assert packet["credential_inspected"] is False
    assert packet["runtime_default_changed"] is False
    assert packet["narrator_admitted"] is False


def test_switch_cli_has_only_preflight_and_never_accepts_live() -> None:
    prepared = subprocess.run(
        [str(PYTHON), str(SCRIPT), "--preflight"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert prepared.returncode == 0, prepared.stderr
    packet = json.loads(prepared.stdout)
    assert packet["provider_calls"] == 0
    assert packet["credential_inspected"] is False

    live = subprocess.run(
        [str(PYTHON), str(SCRIPT), "--live"],
        cwd=ROOT,
        env=_keyless(),
        capture_output=True,
        text=True,
    )
    assert live.returncode != 0
    assert "required: --preflight" in live.stderr


def test_switch_rejects_any_attempt_to_open_paid_gate(monkeypatch) -> None:
    original = switch._load

    def opened(path: Path):
        value = original(path)
        if Path(path) == switch.GATE:
            value["paid_spend_authorized"] = True
        return value

    monkeypatch.setattr(switch, "_load", opened)
    with pytest.raises(ValueError, match="luna_switch_gate_invalid"):
        switch.prepare_switch()


def test_switch_rejects_luna_runner_gate_drift(monkeypatch) -> None:
    original = switch._load

    def opened(path: Path):
        value = original(path)
        if Path(path) == switch.luna.GATE:
            value["live_inference_authorized"] = True
        return value

    monkeypatch.setattr(switch, "_load", opened)
    with pytest.raises(ValueError, match="luna_switch_target_lane_not_closed"):
        switch.prepare_switch()
