"""Execute the real PowerShell prompt runner with isolated evaluators.

Alias tests simulate exceptional invocations. Native-process regressions run the
verified Python executable against a stdlib-only synthetic evaluator in a temp
tree. Neither the production evaluator nor a provider is called. Credential
fixtures are synthetic sentinels, never the user's environment or dotenv files.
"""

from __future__ import annotations

import json
from functools import lru_cache
from itertools import combinations
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_prompt_experiment.ps1"
SHELLS = [executable for name in ("pwsh", "powershell")
          if (executable := shutil.which(name))]
QWEN = "qwen-3.8-27b-groq-free-synthetic-nonthink"
GPT = "gpt-oss-120b-groq-free-synthetic-low"
CONTROL = "h6-control-v1"
VARIANT = "scene-beat-v1"
FOCUS = "scene-focus-v1"
GROUNDED = "scene-grounded-v1"
ATTRIBUTED = "scene-attributed-v1"
FAITHFUL = "scene-faithful-v1"


@pytest.fixture(params=[
    pytest.param(("attributed_only", ATTRIBUTED, GROUNDED, "AttributedOnly"), id="attributed"),
    pytest.param(("faithful_only", FAITHFUL, ATTRIBUTED, "FaithfulOnly"), id="faithful"),
])
def system_observation(request):
    return request.param


def _ps_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


@pytest.fixture(params=SHELLS or [None], ids=lambda value: Path(value).stem if value else "no-powershell")
def available_shell(request):
    if request.param is None:
        pytest.skip("PowerShell is unavailable; runner execution is unverified")
    return request.param


@lru_cache(maxsize=None)
def _execution_policy(shell):
    result = _run(shell, "Get-ExecutionPolicy", cwd=ROOT)
    if result.returncode != 0:
        return "Unavailable"
    return result.stdout.strip()


@pytest.fixture
def shell(available_shell):
    policy = _execution_policy(available_shell)
    if policy == "Unavailable":
        pytest.skip("Host cannot load its execution-policy module; script execution is unverified")
    if policy in {"Restricted", "AllSigned"}:
        pytest.skip("Host execution policy blocks unsigned scripts; policy is not bypassed")
    return available_shell


def _run(shell: str, command: str, *, cwd: Path) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    # Let each PowerShell version resolve its own standard modules instead of
    # inheriting PowerShell 7 module paths inside Windows PowerShell 5.
    environment.pop("PSModulePath", None)
    environment["STORYTELLER_DISABLE_DOTENV"] = "1"
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=25, check=False,
    )


def test_runner_parses_with_real_powershell(available_shell, tmp_path):
    result = _run(available_shell, f"""
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    {_ps_literal(RUNNER)}, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) {{ $parseErrors | Out-String | Write-Output; exit 1 }}
exit 0
""", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def _experiment(shell, tmp_path, *, codes=(0, 0), order="ControlFirst", candidate=GPT,
                mode="normal", preexisting_key=True, blank_key=False,
                variant_only=False, focus_only=False, grounded_only=False, attributed_only=False, faithful_only=False,
                delay_seconds=60,
                native=False, stale_global=97, legacy_shadow=False):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_prompt_experiment.ps1"
    runner.parent.mkdir(parents=True)
    shutil.copyfile(RUNNER, runner)
    python = project / ".venv/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"inert: intercepted by a PowerShell alias")
    evaluator = runner.parent / "evaluate_narrator_models.py"
    evaluator.write_text("# never executed\n")
    if native:
        real_python = Path(sys.executable).resolve(strict=True)
        assert real_python.is_file()
        source = runner.read_text(encoding="utf-8")
        assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
        assert source.count(assignment) == 1
        source = source.replace(assignment, "$python = " + _ps_literal(real_python))
        if legacy_shadow:
            # Negative control: reproduce the original local/global shadowing
            # bug only in the disposable copy, never in the production runner.
            for fixed, broken in (
                ("$global:LASTEXITCODE = $null", "$LASTEXITCODE = $null"),
                ("$exitCode = $global:LASTEXITCODE", "$exitCode = $LASTEXITCODE"),
            ):
                assert source.count(fixed) == 1
                source = source.replace(fixed, broken)
        runner.write_text(source, encoding="utf-8")
        (project / "synthetic-config.json").write_text(json.dumps({"codes": codes, "mode": mode}))
        evaluator.write_text('''"""Offline child process: never imports production code or contacts a provider."""
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "synthetic-config.json").read_text())
arguments = sys.argv[1:]
def option(name):
    return arguments[arguments.index(name) + 1]
candidate, variant, batch = option("--candidate"), option("--prompt-variant"), option("--batch-id")
ledger = root / "native-calls.json"
calls = json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({
    "arguments": arguments, "candidate": candidate, "variant": variant, "batch": batch,
    "pid": os.getpid(),
    "supplied_key": os.environ.get("GROQ_API_KEY") == "synthetic-evaluation-sentinel",
})
ledger.write_text(json.dumps(calls))
exit_code = config["codes"][len(calls) - 1]
mode = config["mode"]
if mode not in {"missing_summary", "cancel_no_summary"}:
    document = {
        "batch_id": batch, "selected_candidate_id": candidate, "process_exit_code": exit_code,
        "inputs": {"prompt": {
            "variant": variant, "file": f"evals/narrator/prompts/{variant}.md", "sha256": "a" * 64,
        }},
    }
    if mode == "wrong_batch": document["batch_id"] = "00000000-0000-0000-0000-000000000000"
    if mode == "wrong_candidate": document["selected_candidate_id"] = "different-candidate"
    if mode == "wrong_variant": document["inputs"]["prompt"]["variant"] = "runtime"
    if mode == "old_variant": document["inputs"]["prompt"]["variant"] = "scene-beat-v1"
    if variant in {"scene-attributed-v1", "scene-faithful-v1"}:
        experiment = {
            "version": variant,
            "baseline_prompt_variant": "scene-attributed-v1" if variant == "scene-faithful-v1" else "scene-grounded-v1",
            "context_contract_version": "scene-focus-v1", "interventions": ["system_prompt"],
            "causal_comparison": False, "complete_ab_experiment": False,
            "runtime_promoted": False, "human_review_required": True,
        }
        changes = {
            "wrong_version": ("version", "scene-grounded-v1"),
            "wrong_baseline": ("baseline_prompt_variant", "scene-focus-v1"),
            "wrong_context": ("context_contract_version", "scene-attributed-v1"),
            "previous_version": ("version", "scene-attributed-v1"),
            "previous_baseline": ("baseline_prompt_variant", "scene-grounded-v1"),
            "wrong_interventions": ("interventions", ["system_prompt", "actor_contract"]),
            "empty_interventions": ("interventions", []),
            "wrong_causal": ("causal_comparison", True),
            "wrong_complete_ab": ("complete_ab_experiment", True),
            "wrong_runtime": ("runtime_promoted", True),
            "wrong_review": ("human_review_required", False),
            "string_false": ("runtime_promoted", "False"),
        }
        if mode in changes:
            field, value = changes[mode]
            experiment[field] = value
        if mode != "missing_experiment":
            document["inputs"]["scene_focus_experiment"] = experiment
    if mode == "focus_variant": document["inputs"]["prompt"]["variant"] = "scene-focus-v1"
    if mode == "grounded_variant": document["inputs"]["prompt"]["variant"] = "scene-grounded-v1"
    if mode == "attributed_variant": document["inputs"]["prompt"]["variant"] = "scene-attributed-v1"
    if mode == "wrong_file": document["inputs"]["prompt"]["file"] = "skills/H6_vtm_narrator.md"
    if mode == "wrong_hash": document["inputs"]["prompt"]["sha256"] = "not-a-hash"
    if mode == "wrong_exit": document["process_exit_code"] = 2
    output = root / "eval-results" / variant
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(document))
    if mode == "duplicate_summary":
        duplicate = root / "eval-results" / f"duplicate-{variant}"
        duplicate.mkdir()
        (duplicate / "summary.json").write_text(json.dumps(document))
print(f"Offline synthetic child completed with exit code {exit_code}.")
sys.exit(exit_code)
''', encoding="utf-8")
    manifest = project / "evals/narrator/groq_candidates_2026-09-05.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    prompt_dir = manifest.parent / "prompts"
    prompt_dir.mkdir()
    for variant in (CONTROL, VARIANT, FOCUS, GROUNDED, ATTRIBUTED, FAITHFUL):
        if mode != f"missing_{variant}":
            (prompt_dir / f"{variant}.md").write_text("Synthetic prompt fixture.")
    harness = project / "harness.ps1"
    harness.write_text("""
$ErrorActionPreference = 'Stop'
$global:ExperimentCalls = @()
$global:ExperimentSleeps = @()
$global:ExperimentCodes = @(__CODES__)
$global:ExperimentMode = __MODE__
$global:ExperimentRoot = __ROOT__
$PSNativeCommandUseErrorActionPreference = $true
__EXISTING_KEY__

function Start-Sleep {
    param([int] $Seconds)
    $global:ExperimentSleeps += $Seconds
}

function Invoke-FakeEvaluator {
    $arguments = @($args)
    $candidate = $arguments[$arguments.IndexOf('--candidate') + 1]
    $variant = $arguments[$arguments.IndexOf('--prompt-variant') + 1]
    $batch = $arguments[$arguments.IndexOf('--batch-id') + 1]
    $call = @{
        arguments = $arguments
        candidate = $candidate
        variant = $variant
        batch = $batch
        supplied_key = ($env:GROQ_API_KEY -eq 'synthetic-evaluation-sentinel')
    }
    $global:ExperimentCalls += $call
    if ($global:ExperimentMode -eq 'throw') { throw 'synthetic evaluator failure' }
    if ($global:ExperimentMode -eq 'secret_throw') { throw 'synthetic-evaluation-sentinel synthetic-previous-sentinel' }
    $exitCode = $global:ExperimentCodes[$global:ExperimentCalls.Count - 1]
    if ($global:ExperimentMode -ne 'no_status') {
        Set-Variable -Name LASTEXITCODE -Scope Global -Value $exitCode
    }
    if ($global:ExperimentMode -in @('missing_summary', 'cancel_no_summary')) { return }
    $document = @{
        batch_id = $batch
        selected_candidate_id = $candidate
        process_exit_code = $exitCode
        inputs = @{ prompt = @{
            variant = $variant
            file = "evals/narrator/prompts/$variant.md"
            sha256 = ('a' * 64)
        } }
    }
    if ($variant -in @('scene-attributed-v1', 'scene-faithful-v1')) {
        $document.inputs.scene_focus_experiment = @{
            version = $variant
            baseline_prompt_variant = $(if ($variant -eq 'scene-faithful-v1') { 'scene-attributed-v1' } else { 'scene-grounded-v1' })
            context_contract_version = 'scene-focus-v1'
            interventions = @('system_prompt')
            causal_comparison = $false
            complete_ab_experiment = $false
            runtime_promoted = $false
            human_review_required = $true
        }
    }
    switch ($global:ExperimentMode) {
        'wrong_batch' { $document.batch_id = [guid]::NewGuid().ToString('D') }
        'wrong_candidate' { $document.selected_candidate_id = 'different-candidate' }
        'wrong_variant' { $document.inputs.prompt.variant = 'runtime' }
        'old_variant' { $document.inputs.prompt.variant = 'scene-beat-v1' }
        'focus_variant' { $document.inputs.prompt.variant = 'scene-focus-v1' }
        'grounded_variant' { $document.inputs.prompt.variant = 'scene-grounded-v1' }
        'wrong_file' { $document.inputs.prompt.file = 'skills/H6_vtm_narrator.md' }
        'wrong_hash' { $document.inputs.prompt.sha256 = 'not-a-hash' }
        'wrong_exit' { $document.process_exit_code = 2 }
    }
    $output = Join-Path $global:ExperimentRoot "eval-results/$variant"
    $null = New-Item -Path $output -ItemType Directory -Force
    $document | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'summary.json')
    if ($global:ExperimentMode -eq 'duplicate_summary') {
        $duplicate = Join-Path $global:ExperimentRoot "eval-results/duplicate-$variant"
        $null = New-Item -Path $duplicate -ItemType Directory -Force
        $document | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $duplicate 'summary.json')
    }
    if ($global:ExperimentMode -eq 'decoy_summary') {
        $decoy = Join-Path $global:ExperimentRoot "eval-results/decoy-$variant"
        $null = New-Item -Path $decoy -ItemType Directory -Force
        $document.inputs.prompt.variant = 'runtime'
        $document | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $decoy 'summary.json')
    }
}

__EVALUATOR_ALIAS__
$secureKey = ConvertTo-SecureString __SUPPLIED_KEY__ -AsPlainText -Force
$global:LASTEXITCODE = __STALE_GLOBAL__
& __RUNNER__ -ApiKey $secureKey -Order __ORDER__ -Candidate __CANDIDATE__ __VARIANT_ONLY__ __FOCUS_ONLY__ __GROUNDED_ONLY__ __ATTRIBUTED_ONLY__ __FAITHFUL_ONLY__ -InterCallDelaySeconds __DELAY__
$runnerExit = $LASTEXITCODE
__NATIVE_CALLS__
$result = @{
    exit_code = $runnerExit
    calls = @($global:ExperimentCalls)
    sleeps = @($global:ExperimentSleeps)
    key_present = (Test-Path Env:GROQ_API_KEY)
    key_restored = ($env:GROQ_API_KEY -eq 'synthetic-previous-sentinel')
    native_preference_restored = $PSNativeCommandUseErrorActionPreference
}
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath __RESULT__
exit 0
""".replace("__CODES__", ",".join(map(str, codes)))
        .replace("__MODE__", _ps_literal(mode))
        .replace("__ROOT__", _ps_literal(project))
        .replace("__EXISTING_KEY__", "$env:GROQ_API_KEY = 'synthetic-previous-sentinel'"
                 if preexisting_key else "Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue")
        .replace("__EVALUATOR_ALIAS__", "" if native else
                 f"Set-Alias -Name {_ps_literal(python)} -Value Invoke-FakeEvaluator")
        .replace("__STALE_GLOBAL__", str(stale_global))
        .replace("__VARIANT_ONLY__", "-VariantOnly" if variant_only else "")
        .replace("__FOCUS_ONLY__", "-FocusOnly" if focus_only else "")
        .replace("__GROUNDED_ONLY__", "-GroundedOnly" if grounded_only else "")
        .replace("__ATTRIBUTED_ONLY__", "-AttributedOnly" if attributed_only else "")
        .replace("__FAITHFUL_ONLY__", "-FaithfulOnly" if faithful_only else "")
        .replace("__DELAY__", str(delay_seconds))
        .replace("__NATIVE_CALLS__", "" if not native else f"""
$ledger = {_ps_literal(project / 'native-calls.json')}
if (Test-Path -LiteralPath $ledger) {{
    $global:ExperimentCalls = @(Get-Content -Raw -LiteralPath $ledger | ConvertFrom-Json)
}}
""")
        .replace("__SUPPLIED_KEY__", _ps_literal(" " if blank_key else "synthetic-evaluation-sentinel"))
        .replace("__RUNNER__", _ps_literal(runner))
        .replace("__ORDER__", _ps_literal(order))
        .replace("__CANDIDATE__", _ps_literal(candidate))
        .replace("__RESULT__", _ps_literal(project / "result.json")), encoding="utf-8")
    result = _run(shell, f"& {_ps_literal(harness)}", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "synthetic-evaluation-sentinel" not in result.stdout + result.stderr
    assert "synthetic-previous-sentinel" not in result.stdout + result.stderr
    document = json.loads((project / "result.json").read_text(encoding="utf-8-sig"))
    assert document["native_preference_restored"] is True
    assert document["key_present"] is preexisting_key
    assert document["key_restored"] is preexisting_key
    return document, result.stdout


def _assert_fixed_parameters(call, *, delay_seconds=60):
    assert call["supplied_key"] is True
    arguments = call["arguments"]
    for option, value in (
        ("--max-output-tokens", "768"), ("--temperature", "0.65"),
        ("--inter-call-delay-seconds", str(delay_seconds)), ("--repetitions", "1"),
        ("--diagnostic-rate-limit-retry-delay-seconds", "15"),
        ("--diagnostic-rate-limit-retry-cap-seconds", "30"),
        ("--deadline-seconds", "60"), ("--api-key-env", "GROQ_API_KEY"),
    ):
        actual = arguments[arguments.index(option) + 1]
        if option == "--api-key-env":
            assert actual == value
        else:
            assert float(actual) == pytest.approx(float(value))
    assert "--allow-synthetic-only" in arguments
    assert "--live" in arguments


@pytest.mark.parametrize("candidate", [GPT, QWEN])
@pytest.mark.parametrize("order, variants", [
    ("ControlFirst", [CONTROL, VARIANT]),
    ("VariantFirst", [VARIANT, CONTROL]),
])
def test_experiment_changes_only_prompt_and_preserves_order(shell, tmp_path, candidate, order, variants):
    result, stdout = _experiment(shell, tmp_path, candidate=candidate, order=order)
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == variants
    assert {call["candidate"] for call in result["calls"]} == {candidate}
    assert len({call["batch"] for call in result["calls"]}) == 1
    assert result["sleeps"] == [60]
    left, right = [call["arguments"] for call in result["calls"]]
    index = left.index("--prompt-variant") + 1
    assert left[:index] + left[index + 1:] == right[:index] + right[index + 1:]
    for call in result["calls"]:
        _assert_fixed_parameters(call)
    assert "18 normal calls plus 4 bounded diagnostic retries" in stdout
    assert "does not approve CAP-001" in stdout
    assert "diagnostics: 128 tokens" in stdout


@pytest.mark.parametrize("codes, expected_count, expected_exit", [
    ((1, 0), 2, 1), ((0, 1), 2, 1), ((1, 1), 2, 1),
    ((2, 0), 1, 2), ((3, 0), 1, 3), ((130, 0), 1, 130),
    ((0, 2), 2, 2), ((0, 3), 2, 3), ((0, 130), 2, 130),
    ((9, 0), 1, 3),
])
def test_exit_codes_control_progress_without_retry(shell, tmp_path, codes, expected_count, expected_exit):
    result, _ = _experiment(shell, tmp_path, codes=codes)
    assert result["exit_code"] == expected_exit
    assert len(result["calls"]) == expected_count
    assert result["sleeps"] == ([60] if expected_count == 2 else [])


@pytest.mark.parametrize("mode", [
    "missing_summary", "wrong_batch", "wrong_candidate", "wrong_variant",
    "wrong_file", "wrong_hash", "wrong_exit", "duplicate_summary", "throw", "no_status",
])
def test_missing_or_unverifiable_evidence_aborts_and_restores_key(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


def test_wrong_variant_decoy_is_not_used_as_this_arms_summary(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, mode="decoy_summary")
    assert result["exit_code"] == 0
    assert len(result["calls"]) == 2


def test_cancellation_without_completed_summary_is_not_a_quality_failure(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, mode="cancel_no_summary", codes=(130, 0))
    assert result["exit_code"] == 130
    assert len(result["calls"]) == 1


@pytest.mark.parametrize("preexisting_key", [False, True])
def test_blank_key_never_calls_evaluator_or_overwrites_prior_environment(shell, tmp_path, preexisting_key):
    result, _ = _experiment(shell, tmp_path, blank_key=True, preexisting_key=preexisting_key)
    assert result["exit_code"] == 3
    assert result["calls"] == []


def test_new_key_is_removed_after_success(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, preexisting_key=False)
    assert result["exit_code"] == 0


@pytest.mark.parametrize("variant", [CONTROL, VARIANT])
def test_both_prompt_files_are_required_before_any_call(shell, tmp_path, variant):
    result, _ = _experiment(shell, tmp_path, mode=f"missing_{variant}")
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []


@pytest.mark.parametrize("arguments", [
    "-InterCallDelaySeconds 0", "-InterCallDelaySeconds 301",
    "-Candidate unapproved-model", "-Order Random",
])
def test_disallowed_parameters_cannot_bypass_the_experiment_scope(shell, tmp_path, arguments):
    result = _run(shell, f"""
$key = ConvertTo-SecureString 'synthetic' -AsPlainText -Force
try {{ & {_ps_literal(RUNNER)} -ApiKey $key {arguments}; exit 1 }}
catch {{ exit 0 }}
""", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_variant_only_has_one_arm_and_never_claims_complete_ab(shell, tmp_path, code):
    result, stdout = _experiment(shell, tmp_path, variant_only=True, codes=(code, 0))
    assert result["exit_code"] == code
    assert len(result["calls"]) == 1
    call = result["calls"][0]
    assert call["variant"] == VARIANT
    assert call["candidate"] == GPT
    _assert_fixed_parameters(call)
    assert result["sleeps"] == []
    assert "9 normal calls plus 2 bounded diagnostic retries" in stdout
    assert "Both prompt arms" not in stdout
    assert "Starting prompt arm: h6-control-v1" not in stdout
    assert "does not approve CAP-001" in stdout


def test_variant_only_is_not_changed_by_order_and_removes_new_key(shell, tmp_path):
    result, _ = _experiment(
        shell, tmp_path, variant_only=True, order="VariantFirst", candidate=QWEN,
        preexisting_key=False,
    )
    assert [call["variant"] for call in result["calls"]] == [VARIANT]
    assert result["calls"][0]["candidate"] == QWEN
    assert result["exit_code"] == 0


def test_variant_only_uses_a_fresh_batch_instead_of_resuming_old_evidence(shell, tmp_path):
    first, _ = _experiment(shell, tmp_path / "first", variant_only=True)
    second, _ = _experiment(shell, tmp_path / "second", variant_only=True)
    assert first["calls"][0]["batch"] != second["calls"][0]["batch"]


def test_absent_exit_status_cannot_inherit_stale_global_success(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, mode="no_status", stale_global=0)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1


@pytest.mark.parametrize("codes, expected_count, expected_exit", [
    ((0, 0), 2, 0), ((1, 0), 2, 1), ((0, 1), 2, 1),
    ((2, 0), 1, 2), ((3, 0), 1, 3), ((130, 0), 1, 130),
])
def test_real_native_exit_status_drives_the_next_arm(shell, tmp_path, codes, expected_count, expected_exit):
    result, stdout = _experiment(shell, tmp_path, codes=codes, native=True, stale_global=97)
    assert result["exit_code"] == expected_exit
    assert len(result["calls"]) == expected_count
    assert len({call["pid"] for call in result["calls"]}) == expected_count
    assert os.getpid() not in {call["pid"] for call in result["calls"]}
    assert "Offline synthetic child completed" in stdout
    for call in result["calls"]:
        _assert_fixed_parameters(call)


@pytest.mark.parametrize("mode", [
    "wrong_batch", "wrong_variant", "wrong_exit", "wrong_hash", "missing_summary", "duplicate_summary",
])
def test_real_native_success_does_not_override_bad_artifacts(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, native=True, mode=mode, stale_global=0)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_variant_only_preserves_real_native_exit_codes(shell, tmp_path, code):
    result, stdout = _experiment(shell, tmp_path, native=True, variant_only=True, codes=(code,))
    assert result["exit_code"] == code
    assert [call["variant"] for call in result["calls"]] == [VARIANT]
    assert "Both prompt arms" not in stdout
    assert "9 normal calls plus 2 bounded diagnostic retries" in stdout


def test_native_regression_detects_the_previous_local_shadowing_bug(shell, tmp_path):
    broken, _ = _experiment(shell, tmp_path / "old", native=True, legacy_shadow=True, codes=(1, 0))
    assert broken["exit_code"] == 3
    assert [call["variant"] for call in broken["calls"]] == [CONTROL]
    fixed, _ = _experiment(shell, tmp_path / "fixed", native=True, codes=(1, 0))
    assert fixed["exit_code"] == 1
    assert [call["variant"] for call in fixed["calls"]] == [CONTROL, VARIANT]


@pytest.mark.parametrize("native", [False, True], ids=["alias", "native"])
@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_focus_only_has_one_joint_observation_with_unchanged_exit_codes(shell, tmp_path, native, code):
    result, stdout = _experiment(shell, tmp_path, native=native, focus_only=True, codes=(code,))
    assert result["exit_code"] == code
    assert [call["variant"] for call in result["calls"]] == [FOCUS]
    assert result["calls"][0]["candidate"] == GPT
    _assert_fixed_parameters(result["calls"][0])
    assert result["sleeps"] == []
    assert "Joint context+actor-contract observation: scene-focus-v1" in stdout
    assert "their effects are not isolated" in stdout
    assert "9 normal calls plus 2 bounded diagnostic retries" in stdout
    assert "This is not a complete A/B experiment" in stdout
    assert "does not approve CAP-001" in stdout
    assert "Both prompt arms" not in stdout
    assert "Starting prompt arm: h6-control-v1" not in stdout
    assert "Starting prompt arm: scene-beat-v1" not in stdout


@pytest.mark.parametrize("missing", [CONTROL, VARIANT])
def test_focus_only_requires_only_its_selected_prompt(shell, tmp_path, missing):
    result, _ = _experiment(shell, tmp_path, focus_only=True, mode=f"missing_{missing}")
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [FOCUS]


def test_missing_focus_prompt_aborts_before_any_call(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, focus_only=True, mode=f"missing_{FOCUS}")
    assert result["exit_code"] == 3
    assert result["calls"] == []


@pytest.mark.parametrize("variant_only", [False, True])
def test_old_modes_do_not_require_or_select_focus_prompt(shell, tmp_path, variant_only):
    result, _ = _experiment(shell, tmp_path, variant_only=variant_only, mode=f"missing_{FOCUS}")
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == ([VARIANT] if variant_only else [CONTROL, VARIANT])


@pytest.mark.parametrize("preexisting_key", [False, True])
def test_focus_only_and_variant_only_are_mutually_exclusive_before_credentials(shell, tmp_path, preexisting_key):
    result, stdout = _experiment(
        shell, tmp_path, focus_only=True, variant_only=True, preexisting_key=preexisting_key,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert "mutually exclusive" in stdout


def test_focus_only_preserves_candidate_and_ignores_arm_order_without_retaining_key(shell, tmp_path):
    result, _ = _experiment(
        shell, tmp_path, focus_only=True, candidate=QWEN, order="VariantFirst", preexisting_key=False,
    )
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [FOCUS]
    assert result["calls"][0]["candidate"] == QWEN
    _assert_fixed_parameters(result["calls"][0])


@pytest.mark.parametrize("mode", ["old_variant", "wrong_variant", "wrong_file", "wrong_hash", "wrong_exit"])
def test_focus_only_refuses_other_prompt_or_incoherent_native_evidence(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, focus_only=True, native=True, mode=mode)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


def test_focus_only_is_a_new_batch_not_an_imported_previous_observation(shell, tmp_path):
    first, _ = _experiment(shell, tmp_path / "first", focus_only=True)
    second, _ = _experiment(shell, tmp_path / "second", focus_only=True)
    assert first["calls"][0]["batch"] != second["calls"][0]["batch"]


@pytest.mark.parametrize("native", [False, True], ids=["alias", "native"])
@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_grounded_only_is_one_system_observation_with_fixed_candidate_and_limits(shell, tmp_path, native, code):
    result, stdout = _experiment(shell, tmp_path, native=native, grounded_only=True, codes=(code,))
    assert result["exit_code"] == code
    assert [call["variant"] for call in result["calls"]] == [GROUNDED]
    assert result["calls"][0]["candidate"] == GPT
    _assert_fixed_parameters(result["calls"][0])
    assert result["sleeps"] == []
    assert "SYSTEM-only observation: scene-grounded-v1 relative to scene-focus-v1" in stdout
    assert "Same scene-focus-v1 context organization and actor contract/schema" in stdout
    assert "only the SYSTEM prompt changes" in stdout
    assert "9 normal calls plus 2 bounded diagnostic retries" in stdout
    assert "diagnostics: 128 tokens" in stdout
    assert "no control is run or imported" in stdout
    assert "not a complete A/B experiment or a causal A/B conclusion" in stdout
    assert "No narrative retries or fallback" in stdout
    assert "does not approve CAP-001" in stdout
    assert "Both prompt arms" not in stdout
    assert "Starting prompt arm: h6-control-v1" not in stdout
    assert "Starting prompt arm: scene-beat-v1" not in stdout
    assert "Starting prompt arm: scene-focus-v1" not in stdout
    if code == 0:
        assert "not a causal A/B conclusion, narrative-quality approval" in stdout


@pytest.mark.parametrize("preexisting_key", [False, True])
@pytest.mark.parametrize("other_modes", [
    {"focus_only": True}, {"variant_only": True},
    {"focus_only": True, "variant_only": True},
])
def test_grounded_only_conflicts_are_rejected_before_credentials(shell, tmp_path, preexisting_key, other_modes):
    result, stdout = _experiment(
        shell, tmp_path, grounded_only=True, preexisting_key=preexisting_key, **other_modes,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert "mutually exclusive" in stdout


@pytest.mark.parametrize("preexisting_key", [False, True])
def test_grounded_only_rejects_qwen_before_credentials_or_dispatch(shell, tmp_path, preexisting_key):
    result, stdout = _experiment(
        shell, tmp_path, grounded_only=True, candidate=QWEN, preexisting_key=preexisting_key,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert f"GroundedOnly requires {GPT}" in stdout


@pytest.mark.parametrize("missing", [CONTROL, VARIANT, FOCUS])
def test_grounded_only_requires_only_its_selected_prompt(shell, tmp_path, missing):
    result, _ = _experiment(shell, tmp_path, grounded_only=True, mode=f"missing_{missing}")
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [GROUNDED]


def test_missing_grounded_prompt_aborts_before_credentials_or_dispatch(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, grounded_only=True, mode=f"missing_{GROUNDED}")
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []


@pytest.mark.parametrize("other_modes,variants", [
    ({}, [CONTROL, VARIANT]), ({"variant_only": True}, [VARIANT]), ({"focus_only": True}, [FOCUS]),
])
def test_prior_modes_do_not_require_or_select_grounded_prompt(shell, tmp_path, other_modes, variants):
    result, _ = _experiment(shell, tmp_path, mode=f"missing_{GROUNDED}", candidate=QWEN, **other_modes)
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == variants
    assert {call["candidate"] for call in result["calls"]} == {QWEN}


@pytest.mark.parametrize("mode", [
    "focus_variant", "old_variant", "wrong_variant", "wrong_batch", "wrong_candidate",
    "wrong_file", "wrong_hash", "wrong_exit", "missing_summary", "duplicate_summary",
])
def test_grounded_only_rejects_incoherent_native_evidence_and_restores_key(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, grounded_only=True, native=True, mode=mode)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("mode", ["throw", "no_status"])
def test_grounded_only_failed_invocation_restores_key_without_retry(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, grounded_only=True, mode=mode, stale_global=0)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("native", [False, True], ids=["alias", "native"])
def test_grounded_only_cancel_without_summary_preserves_native_status(shell, tmp_path, native):
    result, _ = _experiment(
        shell, tmp_path, grounded_only=True, native=native, mode="cancel_no_summary", codes=(130,),
    )
    assert result["exit_code"] == 130
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


def test_grounded_only_ignores_arm_order_and_removes_temporary_key(shell, tmp_path):
    result, _ = _experiment(
        shell, tmp_path, grounded_only=True, order="VariantFirst", preexisting_key=False, native=True,
    )
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [GROUNDED]
    assert result["sleeps"] == []


def test_grounded_only_is_a_new_batch_without_importing_previous_focus_evidence(shell, tmp_path):
    first, _ = _experiment(shell, tmp_path / "first", focus_only=True)
    second, _ = _experiment(shell, tmp_path / "second", grounded_only=True)
    assert first["calls"][0]["batch"] != second["calls"][0]["batch"]


@pytest.mark.parametrize("native", [False, True], ids=["alias", "native"])
@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_system_only_is_one_system_observation_with_fixed_candidate_and_limits(shell, tmp_path, native, code, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, stdout = _experiment(shell, tmp_path, native=native, **{mode_flag: True}, codes=(code,))
    assert result["exit_code"] == code
    assert [call["variant"] for call in result["calls"]] == [variant]
    call = result["calls"][0]
    assert call["candidate"] == GPT
    _assert_fixed_parameters(call)
    assert result["sleeps"] == []
    assert f"SYSTEM-only observation: {variant} relative to {baseline}" in stdout
    assert "Same scene-focus-v1 USER packet and actor contract/schema, validators, corpus and parameters" in stdout
    assert "only the SYSTEM prompt changes" in stdout
    assert "9 normal calls plus 2 bounded diagnostic retries" in stdout
    assert "diagnostics: 128 tokens" in stdout
    assert "no baseline or other arm is run or imported" in stdout
    assert "not a complete A/B experiment or a causal A/B conclusion" in stdout
    assert "No narrative retries or fallback" in stdout
    assert "does not approve CAP-001" in stdout
    assert "Both prompt arms" not in stdout
    for old_variant in (CONTROL, VARIANT, FOCUS, GROUNDED, ATTRIBUTED, FAITHFUL):
        if old_variant == variant:
            continue
        assert f"Starting prompt arm: {old_variant}" not in stdout
    if code == 0:
        assert "not a causal A/B conclusion, narrative-quality approval" in stdout
    if code == 1:
        assert "Baseline was not run; human review remains required" in stdout


@pytest.mark.parametrize("preexisting_key", [False, True])
@pytest.mark.parametrize("other_modes", [
    {"grounded_only": True}, {"focus_only": True}, {"variant_only": True},
    {"grounded_only": True, "focus_only": True},
    {"grounded_only": True, "variant_only": True},
    {"focus_only": True, "variant_only": True},
    {"grounded_only": True, "focus_only": True, "variant_only": True},
])
def test_attributed_only_conflicts_are_rejected_before_credentials(shell, tmp_path, preexisting_key, other_modes):
    result, stdout = _experiment(
        shell, tmp_path, attributed_only=True, preexisting_key=preexisting_key, **other_modes,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert "AttributedOnly, GroundedOnly, FocusOnly and VariantOnly are mutually exclusive" in stdout


@pytest.mark.parametrize("preexisting_key", [False, True])
def test_system_only_rejects_qwen_before_credentials_or_dispatch(shell, tmp_path, preexisting_key, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, stdout = _experiment(
        shell, tmp_path, **{mode_flag: True}, candidate=QWEN, preexisting_key=preexisting_key,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert f"{switch} requires {GPT}" in stdout


@pytest.mark.parametrize("missing", [CONTROL, VARIANT, FOCUS, GROUNDED])
def test_system_only_requires_only_its_selected_prompt(shell, tmp_path, missing, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(shell, tmp_path, **{mode_flag: True}, mode=f"missing_{missing}")
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [variant]


def test_missing_system_observation_prompt_aborts_before_credentials_or_dispatch(shell, tmp_path, system_observation):
    mode_flag, variant, _, _ = system_observation
    result, _ = _experiment(shell, tmp_path, **{mode_flag: True}, mode=f"missing_{variant}")
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []


@pytest.mark.parametrize("other_modes,variants,candidate", [
    ({}, [CONTROL, VARIANT], QWEN),
    ({"variant_only": True}, [VARIANT], QWEN),
    ({"focus_only": True}, [FOCUS], QWEN),
    ({"grounded_only": True}, [GROUNDED], GPT),
])
def test_prior_modes_do_not_require_or_select_attributed_prompt(shell, tmp_path, other_modes, variants, candidate):
    result, stdout = _experiment(
        shell, tmp_path, mode=f"missing_{ATTRIBUTED}", candidate=candidate, **other_modes,
    )
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == variants
    assert {call["candidate"] for call in result["calls"]} == {candidate}
    assert "Attributed-only" not in stdout


@pytest.mark.parametrize("mode", [
    "grounded_variant", "focus_variant", "old_variant", "wrong_variant", "wrong_batch", "wrong_candidate",
    "wrong_file", "wrong_hash", "wrong_exit", "missing_summary", "duplicate_summary",
    "wrong_version", "wrong_baseline", "wrong_context", "wrong_interventions", "empty_interventions",
    "wrong_causal", "wrong_complete_ab", "wrong_runtime", "wrong_review", "string_false", "missing_experiment",
])
def test_system_only_rejects_incoherent_native_evidence_and_restores_key(shell, tmp_path, mode, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(shell, tmp_path, **{mode_flag: True}, native=True, mode=mode)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("preexisting_key", [False, True])
@pytest.mark.parametrize("mode", ["throw", "secret_throw", "no_status"])
def test_system_only_failed_invocation_restores_key_without_echo_or_retry(shell, tmp_path, mode, preexisting_key, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(
        shell, tmp_path, **{mode_flag: True}, mode=mode, stale_global=0, preexisting_key=preexisting_key,
    )
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("preexisting_key", [False, True])
def test_system_only_blank_key_never_dispatches_or_overwrites_environment(shell, tmp_path, preexisting_key, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(
        shell, tmp_path, **{mode_flag: True}, blank_key=True, preexisting_key=preexisting_key,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []


@pytest.mark.parametrize("native", [False, True], ids=["alias", "native"])
def test_system_only_cancel_without_summary_preserves_native_status(shell, tmp_path, native, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(
        shell, tmp_path, **{mode_flag: True}, native=native, mode="cancel_no_summary", codes=(130,),
    )
    assert result["exit_code"] == 130
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []


@pytest.mark.parametrize("delay_seconds", [60, 300])
def test_system_only_keeps_pacing_bounds_ignores_order_and_removes_key(shell, tmp_path, delay_seconds, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result, _ = _experiment(
        shell, tmp_path, **{mode_flag: True}, order="VariantFirst", preexisting_key=False,
        native=True, delay_seconds=delay_seconds,
    )
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [variant]
    _assert_fixed_parameters(result["calls"][0], delay_seconds=delay_seconds)
    assert result["sleeps"] == []


@pytest.mark.parametrize("arguments", [
    "-InterCallDelaySeconds 59", "-InterCallDelaySeconds 301",
    "-Candidate unapproved-model", "-Order Random",
])
def test_system_only_disallowed_parameters_fail_before_dispatch(shell, tmp_path, arguments, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    result = _run(shell, f"""
$key = ConvertTo-SecureString 'synthetic-evaluation-sentinel' -AsPlainText -Force
try {{ & {_ps_literal(RUNNER)} -ApiKey $key -{switch} {arguments}; exit 1 }}
catch {{ exit 0 }}
""", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "synthetic-evaluation-sentinel" not in result.stdout + result.stderr
    assert "Starting prompt arm" not in result.stdout + result.stderr


def test_system_only_is_a_new_batch_without_importing_previous_baseline_evidence(shell, tmp_path, system_observation):
    mode_flag, variant, baseline, switch = system_observation
    first, _ = _experiment(shell, tmp_path / "first", **{"grounded_only" if baseline == GROUNDED else "attributed_only": True})
    second, _ = _experiment(shell, tmp_path / "second", **{mode_flag: True})
    assert first["calls"][0]["batch"] != second["calls"][0]["batch"]


@pytest.mark.parametrize("preexisting_key", [False, True])
@pytest.mark.parametrize("other_modes", [
    dict.fromkeys(selected, True)
    for count in range(1, 5)
    for selected in combinations(("attributed_only", "grounded_only", "focus_only", "variant_only"), count)
])
def test_faithful_only_conflicts_are_rejected_before_credentials(shell, tmp_path, preexisting_key, other_modes):
    result, stdout = _experiment(
        shell, tmp_path, faithful_only=True, preexisting_key=preexisting_key, **other_modes,
    )
    assert result["exit_code"] == 3
    assert result["calls"] == []
    assert result["sleeps"] == []
    assert "FaithfulOnly, AttributedOnly, GroundedOnly, FocusOnly and VariantOnly are mutually exclusive" in stdout


def test_faithful_only_does_not_require_its_baseline_prompt(shell, tmp_path):
    result, _ = _experiment(shell, tmp_path, faithful_only=True, mode=f"missing_{ATTRIBUTED}")
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == [FAITHFUL]


@pytest.mark.parametrize("other_modes,variants,candidate", [
    ({}, [CONTROL, VARIANT], QWEN),
    ({"variant_only": True}, [VARIANT], QWEN),
    ({"focus_only": True}, [FOCUS], QWEN),
    ({"grounded_only": True}, [GROUNDED], GPT),
    ({"attributed_only": True}, [ATTRIBUTED], GPT),
])
def test_prior_modes_do_not_require_or_select_faithful_prompt(shell, tmp_path, other_modes, variants, candidate):
    result, stdout = _experiment(
        shell, tmp_path, mode=f"missing_{FAITHFUL}", candidate=candidate, **other_modes,
    )
    assert result["exit_code"] == 0
    assert [call["variant"] for call in result["calls"]] == variants
    assert {call["candidate"] for call in result["calls"]} == {candidate}
    assert "Faithful-only" not in stdout


@pytest.mark.parametrize("mode", ["attributed_variant", "previous_version", "previous_baseline"])
def test_faithful_only_rejects_predecessor_provenance_without_retry(shell, tmp_path, mode):
    result, _ = _experiment(shell, tmp_path, faithful_only=True, native=True, mode=mode)
    assert result["exit_code"] == 3
    assert len(result["calls"]) == 1
    assert result["sleeps"] == []
