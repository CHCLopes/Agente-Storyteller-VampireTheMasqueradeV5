"""Exercise the real wrapper and native Python without production API calls.

Only a disposable wrapper's Python assignment changes. Its child is a stdlib
fake in a temporary project, and all credential values are synthetic sentinels.
PowerShell execution policies are inspected and respected, never bypassed.
"""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_continuity_probe.ps1"
SHELLS = [found for name in ("pwsh", "powershell") if (found := shutil.which(name))]
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"


def _literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def _run(shell, command, cwd):
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment.pop("PSModulePath", None)
    environment["STORYTELLER_DISABLE_DOTENV"] = "1"
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=25, check=False,
    )


@lru_cache(maxsize=None)
def _policy_allows_scripts(shell):
    result = _run(shell, "Get-ExecutionPolicy", ROOT)
    return result.returncode == 0 and result.stdout.strip() not in {"Restricted", "AllSigned"}


@pytest.fixture(scope="module")
def operational_shell():
    for executable in SHELLS:
        if _policy_allows_scripts(executable):
            return executable
    pytest.skip("No host permits unsigned scripts; execution policy is not bypassed")


@pytest.mark.parametrize("shell", SHELLS or [None], ids=lambda p: Path(p).stem if p else "unavailable")
def test_continuity_runner_parses_each_available_powershell(shell, tmp_path):
    if shell is None:
        pytest.skip("PowerShell unavailable")
    result = _run(shell, f"""
$tokens = $null
$errors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    {_literal(RUNNER)}, [ref]$tokens, [ref]$errors)
if ($errors.Count) {{ $errors | Out-String | Write-Output; exit 1 }}
exit 0
""", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def _probe(shell, tmp_path, *, code=0, mutations=None, absent_key=False, mode="normal"):
    project = tmp_path / "isolated project"
    script_dir = project / "scripts"
    script_dir.mkdir(parents=True)
    runner = script_dir / RUNNER.name
    real_python = Path(sys.executable).resolve(strict=True)
    assert real_python.is_file()
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    source = RUNNER.read_text(encoding="utf-8")
    assert source.count(assignment) == 1
    runner.write_text(source.replace(assignment, "$python = " + _literal(real_python)), encoding="utf-8")
    fixture = project / "evals/narrator/experiments/continuity-probe-v1.json"
    fixture.parent.mkdir(parents=True)
    if mode != "missing_fixture":
        fixture.write_text("{}", encoding="utf-8")
    (fixture.parents[1] / "groq_candidates_2026-09-05.json").write_text("{}", encoding="utf-8")
    prompt = fixture.parents[1] / "prompts/scene-focus-v1.md"
    prompt.parent.mkdir()
    prompt.write_text("Synthetic fixture.", encoding="utf-8")
    (project / "synthetic-config.json").write_text(json.dumps({
        "code": code, "mutations": mutations or {}, "mode": mode,
    }), encoding="utf-8")
    evaluator = script_dir / "evaluate_narrator_continuity.py"
    evaluator.write_text('''"""Offline stdlib-only child; no production imports or provider access."""
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "synthetic-config.json").read_text())
arguments = sys.argv[1:]
run_id = arguments[arguments.index("--run-id") + 1]
ledger = root / "native-calls.json"
calls = json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({"arguments": arguments, "run_id": run_id, "pid": os.getpid(),
              "supplied_key": os.environ.get("GROQ_API_KEY") == "synthetic-probe-sentinel"})
ledger.write_text(json.dumps(calls))
if config["mode"] != "missing_summary":
    document = {
        "run_id": run_id, "purpose": "continuity_probe",
        "selected_candidate_id": "gpt-oss-120b-groq-free-synthetic-low",
        "prompt_variant": "scene-focus-v1", "full_evaluation": False,
        "cap_001_status": "not_evaluated", "process_exit_code": config["code"],
        "mode": "live", "status": "observed", "calls_started": 1,
        "maximum_provider_calls": 1, "automatic_retries": 0,
        "diagnostics_executed": False, "fallback": False, "runtime_promoted": False,
        "continuation_automated_passed": config["code"] == 0,
    }
    document.update(config["mutations"])
    output = root / "eval-results/continuity-probe" / run_id
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(document))
print("Offline synthetic child completed.")
sys.exit(config["code"])
''', encoding="utf-8")
    harness = project / "harness.ps1"
    key_setup = (
        "Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue"
        if absent_key else "$env:GROQ_API_KEY = 'synthetic-previous-sentinel'"
    )
    supplied = "   " if mode == "blank_key" else "synthetic-probe-sentinel"
    harness.write_text(f"""
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
{key_setup}
$secure = ConvertTo-SecureString {_literal(supplied)} -AsPlainText -Force
$global:LASTEXITCODE = 97
& {_literal(runner)} -ApiKey $secure
$runnerExit = $LASTEXITCODE
$result = @{{
    exit_code = $runnerExit
    key_present = (Test-Path Env:GROQ_API_KEY)
    key_restored = ($env:GROQ_API_KEY -eq 'synthetic-previous-sentinel')
    native_preference_restored = $PSNativeCommandUseErrorActionPreference
}}
$result | ConvertTo-Json | Set-Content -LiteralPath {_literal(project / 'harness-result.json')} -Encoding UTF8
exit 0
""", encoding="utf-8")
    process = _run(shell, "& " + _literal(harness), project)
    output = process.stdout + process.stderr
    assert process.returncode == 0, output
    assert "synthetic-probe-sentinel" not in output
    assert "synthetic-previous-sentinel" not in output
    result = json.loads((project / "harness-result.json").read_text(encoding="utf-8-sig"))
    assert result["native_preference_restored"] is True
    assert result["key_present"] is not absent_key
    assert result["key_restored"] is not absent_key
    ledger = project / "native-calls.json"
    calls = json.loads(ledger.read_text()) if ledger.exists() else []
    if calls:
        assert len(calls) == 1, "A one-call probe must never retry or start diagnostics"
        call = calls[0]
        assert call["pid"] != os.getpid()  # Actual native child, not a PowerShell alias.
        assert str(uuid.UUID(call["run_id"])) == call["run_id"]
        assert call["arguments"] == ["--live", "--run-id", call["run_id"]]
        assert call["supplied_key"] is True
    return result, calls, output


@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_native_child_exit_is_preserved_without_stale_global_or_retry(operational_shell, tmp_path, code):
    result, calls, output = _probe(operational_shell, tmp_path, code=code, absent_key=code == 0)
    assert result["exit_code"] == code
    assert len(calls) == 1
    assert "Verified continuity probe summary:" in output
    assert CANDIDATE in output
    assert "at most one provider call" in output
    assert "CAP-001 status: not_evaluated" in output
    if code == 0:
        assert "Human narrative review and full evaluation remain required" in output


@pytest.mark.parametrize("mutation", [
    {"run_id": "00000000-0000-0000-0000-000000000000"},
    {"purpose": "full_evaluation"},
    {"selected_candidate_id": "another-model"},
    {"prompt_variant": "runtime"},
    {"full_evaluation": "false"},
    {"cap_001_status": "approved"},
    {"process_exit_code": 1},
    {"mode": "offline_preparation", "status": "prepared", "calls_started": 0},
    {"calls_started": 2},
    {"calls_started": 0},
    {"calls_started": True},
    {"status": "prepared"},
    {"maximum_provider_calls": 2},
    {"automatic_retries": 1},
    {"diagnostics_executed": "false"},
    {"fallback": "false"},
    {"runtime_promoted": "false"},
    {"continuation_automated_passed": "true"},
])
def test_summary_scope_or_exit_mismatch_fails_closed(operational_shell, tmp_path, mutation):
    result, calls, output = _probe(operational_shell, tmp_path, mutations=mutation)
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert "Verified continuity probe summary:" not in output
    assert "summary verification" in output


@pytest.mark.parametrize("mode", ["missing_fixture", "blank_key"])
def test_preflight_or_blank_key_never_invokes_child(operational_shell, tmp_path, mode):
    result, calls, _ = _probe(operational_shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3
    assert calls == []


@pytest.mark.parametrize("code, expected", [(0, 3), (130, 130), (9, 3)])
def test_missing_report_or_unknown_exit_is_not_approved(operational_shell, tmp_path, code, expected):
    result, calls, output = _probe(operational_shell, tmp_path, code=code, mode="missing_summary")
    assert result["exit_code"] == expected
    assert len(calls) == 1
    assert "Verified continuity probe summary:" not in output
    if code == 130:
        assert "no completed summary was produced" in output
