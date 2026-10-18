from __future__ import annotations

import copy

from functools import lru_cache

import hashlib

import json

import os

from pathlib import Path

import shutil

import subprocess

import sys

from uuid import UUID

import pytest

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from scripts import evaluate_narrator_summary_budget as executor

from scripts.narrator_summary_only import measure_summary_words

ROOT = Path(__file__).resolve().parents[1]

RUNNER = ROOT / "scripts/run_groq_summary_budget_probe.ps1"

EVALUATOR = "scripts/evaluate_narrator_summary_budget.py"

SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]

def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def _shell_run(shell, command, cwd):
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment.pop("PSModulePath", None)
    environment["STORYTELLER_DISABLE_DOTENV"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=25,
    )


@lru_cache(maxsize=None)
def _policy(shell):
    result = _shell_run(shell, "Get-ExecutionPolicy", ROOT)
    return result.stdout.strip() if result.returncode == 0 else "Unavailable"


@pytest.fixture
def shell():
    selected = shutil.which("pwsh")
    if selected is None:
        pytest.skip("PowerShell 7 unavailable")
    if _policy(selected) in {"Unavailable", "Restricted", "AllSigned"}:
        pytest.skip("Host policy/module prevents execution; policy is not bypassed")
    return selected


@pytest.fixture(scope="module")
def metadata():
    # The real pure preflight is the fixture source: no hand-maintained replica
    # of its shape, hashes, source units, or experimental scope.
    return executor.prepare_experiment().metadata


def _real_summary(code, mode="normal"):
    if mode in {"local_error_after_schema", "cancelled_after_schema"}:
        row = {"kind": "summary_budget_call", "case_id": executor.CASE_ID,
               "call_made": True, "schema_valid": True, "route_status": "verified",
               "provider_observation": {"response_status": 200},
               "summary_text": "Resumo sintético válido.",
               "instruction_measurements": measure_summary_words("Resumo sintético válido.")}
        status = "local_error" if mode == "local_error_after_schema" else "cancelled"
        result = executor.summarize([row], status=status)
        assert result["process_exit_code"] == code
        assert result["transport_and_schema_passed"] is False
        return result
    if code in {3, 130}:
        row = {"kind": "summary_budget_skip", "case_id": executor.CASE_ID,
               "call_made": False, "skipped_reason": "cancelled" if code == 130 else "local_error"}
        return executor.summarize([row], status="cancelled" if code == 130 else "local_error")
    row = {"kind": "summary_budget_call", "case_id": executor.CASE_ID,
           "call_made": True, "schema_valid": code == 0,
           "route_status": "verified" if code != 2 else "unavailable",
           "provider_observation": {"response_status": 200 if code != 2 else None}}
    if code == 0:
        summary_text = "Resumo sintético válido."
        if mode == "long_summary":
            summary_text = " ".join(["palavra"] * 26)
        elif mode == "spaces_summary":
            summary_text = " " * 8
        row["summary_text"] = summary_text
        row["instruction_measurements"] = measure_summary_words(summary_text)
    if code == 2:
        row["llm_error"] = {"category": sorted(executor.AVAILABILITY_CATEGORIES)[0]}
    result = executor.summarize([row])
    assert result["process_exit_code"] == code
    return result


def _wrapper(shell, tmp_path, metadata, *, code=0, preexisting=True, blank=False,
             preflight_change=None, live_change=None, mode="normal", disk_drift=None):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_summary_budget_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    inputs = metadata["inputs"]
    files = {inputs[name]["file"] for name in ("dossier", "case", "prompt")}
    files.add("evals/narrator/" + inputs["manifest"]["file"])
    files.update(item["file"] for item in inputs["implementation"])
    for relative in files:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    if disk_drift:
        with (project / disk_drift).open("ab") as stream:
            stream.write(b"\nsynthetic drift")
    meta = copy.deepcopy(metadata)
    fake = project / EVALUATOR
    fake.write_text(NATIVE_EVALUATOR, encoding="utf-8")
    meta["evaluator"]["sha256"] = hashlib.sha256(fake.read_bytes()).hexdigest()
    config = {"code": code, "mode": mode, "metadata": meta, "summary": _real_summary(code, mode),
              "preflight_change": preflight_change, "live_change": live_change}
    (project / "config.json").write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    if mode == "preexisting_artifact":
        old = project / "eval-results/old"
        old.mkdir(parents=True)
        (old / "summary.json").write_text("old malformed artifact", encoding="utf-8")
    result_path = project / "harness-result.json"
    command = f"""
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
{'$env:GROQ_API_KEY='+_ps('synthetic-previous-sentinel') if preexisting else 'Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue'}
$key=ConvertTo-SecureString {_ps(' ' if blank else 'synthetic-supplied-sentinel')} -AsPlainText -Force
$global:LASTEXITCODE=0
& {_ps(runner)} -ApiKey $key
$result=@{{exit_code=$LASTEXITCODE; present=(Test-Path Env:GROQ_API_KEY); restored=($env:GROQ_API_KEY -eq 'synthetic-previous-sentinel'); preference=$PSNativeCommandUseErrorActionPreference}}
$result | ConvertTo-Json | Set-Content -LiteralPath {_ps(result_path)}
exit 0
"""
    completed = _shell_run(shell, command, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for sentinel in ("synthetic-supplied-sentinel", "synthetic-previous-sentinel", "synthetic-sensitive-error-payload"):
        assert sentinel not in completed.stdout + completed.stderr
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    assert result["present"] is result["restored"] is preexisting
    assert result["preference"] is True
    ledger = project / "calls.json"
    calls = json.loads(ledger.read_text()) if ledger.exists() else []
    return result, calls, completed.stdout


NATIVE_EVALUATOR = r"""
import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
args=sys.argv[1:]
ledger=root/'calls.json'
calls=json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({'arguments':args,'key_present':'GROQ_API_KEY' in os.environ,'key_supplied':os.environ.get('GROQ_API_KEY')=='synthetic-supplied-sentinel'})
ledger.write_text(json.dumps(calls))
def change(doc,spec):
 if spec is None:return
 path,value=spec;names=path.split('.');item=doc
 for name in names[:-1]:item=item[int(name)] if isinstance(item,list) else item[name]
 name=names[-1]
 if isinstance(item,list):item[int(name)]=value
 else:item[name]=value
doc=config['metadata'];mode=config['mode'];code=config['code']
if args==['--preflight']:
 if mode in {'failed_preflight','invalid_preflight_json'}:
  print('synthetic-sensitive-error-payload');sys.exit(3 if mode=='failed_preflight' else 0)
 change(doc,config['preflight_change'])
 print(json.dumps(doc));sys.exit(0)
doc.update(batch_id=args[args.index('--batch-id')+1],evaluation_status='local_error' if code==3 else 'cancelled' if code==130 else 'completed',process_exit_code=code,summary=config['summary'])
if mode=='missing_evaluation_status':doc.pop('evaluation_status')
change(doc,config['live_change'])
if mode=='partial_jsonl':
 folder=root/'eval-results/partial';folder.mkdir(parents=True)
 (folder/'records.jsonl').write_text('partial synthetic evidence')
if mode not in {'missing_summary','partial_jsonl'}:
 folder=root/'eval-results/synthetic-run';folder.mkdir(parents=True)
 (folder/'summary.json').write_text('malformed' if mode=='malformed_summary' else json.dumps(doc))
 if mode=='duplicate_summary':
  other=root/'eval-results/other';other.mkdir()
  (other/'summary.json').write_text(json.dumps(doc))
print('synthetic-sensitive-error-payload')
print('synthetic-sensitive-error-payload',file=sys.stderr)
sys.exit(code)
"""

REPLACEMENTS = {'evaluate_narrator_summary_only.py': 'evaluate_narrator_summary_budget.py', 'summary_only_qwen_probe': 'summary_budget_qwen_probe', 'record-summary-only-qwen-observation-v1': 'record-summary-budget-qwen-observation-v1', 'evals/narrator/record_inline_case_v1.json': 'evals/narrator/record_summary_budget_case_v1.json', '5b812d5f4f20ef592e20268a08c2e7fd837cb5d1e6d0d96a175a4033b0383cd7': '98cf0817f45f18cf39e6ead2d0825a18134d71e5e38213e789a0a0fce2e0415a', 'archive-vibration': 'station-clock', '$inputs.prompt.variant -cne "record-summary-only-v1"': '$inputs.prompt.variant -cne "record-summary-budget-v1"', 'evals/narrator/prompts/record-summary-only-v1.md': 'evals/narrator/prompts/record-summary-budget-v1.md', '94c47c36b620628bb07b74f308adb6d556db7050f31d2aa2c262daa693c0a5d7': '1eca37a720951743b0f989b3ed31b1fd726663345bad71016179966d5548d5ce', '71df999d6f1ff6f77ec2bd9f2744878e11ee31a43e4f3abd4302499e81c91146': '6a59513d8b99659f00548ed3d5300f3137e402f40a2e3f7fc26d674dbc9964f4', '70adab37989c455858052582a4dba8e2edfa3fbce0d1d2ca8257a18aa37e8685': '2191a03f86fa363ab4cdfdf83dd360124454a18992c1eab88e49443f1fbc8b2b', 'b7706e060b634d25235955eb43dd3720051916947b7ef508afb02fa75badc7bc': 'e82e044261995d7cf942da383756a1e15d3c94efae7f52143f32327b6c896758', 'b327fdb6be496eb5028dd640fd7ee9fa5e97e2d98e2288b612948146f9a4ec2b': 'df7fdae143699d07a94032a1d97eaf962a958fc1d299d2598ccbe845930d7d44', '"estimated_tokens":168': '"estimated_tokens":147', 'evals/narrator/reports/record-summary-only-dossier-94a95216-2026-09-07.json': 'evals/narrator/reports/record-summary-budget-dossier-1edf4d3e-2026-09-07.json', '4e7486ae1498e799b0b59997e2de73ff94fd3cabc7a9762416609923585079ea': '8df1c12ea57076dd44a5aca2173b06b693f1904fada52bfd8b041bcebc557cac', 'b95c1cb7e0bcf93f02a09d2f2a1a4df3b874d505a9c4748aad0722b630dc895f': 'd494be582e549a917419c06229fed3acb60f092f7f7bcbc982ebe8caea804eac', '3072': '768', 'Summary-only Qwen probe': 'Summary-budget Qwen probe'}

def test_wrapper_is_exact_declared_derivation_of_frozen_single_call_flow():
    old = (ROOT / "scripts/run_groq_summary_only_probe.ps1").read_bytes()
    assert hashlib.sha256(old).hexdigest() == "6bc2628f98899d57f812f9fa1104d5908d475e84e2ba8fb793a0138907548e65"
    for before, after in REPLACEMENTS.items():
        assert before.encode() in old
        old = old.replace(before.encode(), after.encode())
    assert RUNNER.read_bytes() == old


@pytest.mark.parametrize("available_shell", SHELLS or [None], ids=lambda p: Path(p).stem if p else "unavailable")
def test_new_wrapper_syntax(available_shell, tmp_path):
    if available_shell is None:
        pytest.skip("PowerShell unavailable")
    command = "$tokens=$null; $errors=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile(" + _ps(RUNNER) + ",[ref]$tokens,[ref]$errors); if ($errors.Count) { exit 1 }"
    result = _shell_run(available_shell, command, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_budget_real_summary_exit_key_order_and_environment_restoration(shell, tmp_path, metadata, code):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=code, preexisting=code % 2 == 0)
    assert result["exit_code"] == code, output
    assert len(calls) == 2
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False
    assert calls[1]["key_supplied"] is True
    args = calls[1]["arguments"]
    batch = args[args.index("--batch-id") + 1]
    assert str(UUID(batch)) == batch
    assert args == ["--live", "--allow-synthetic-only", "--batch-id", batch, "--api-key-env", "GROQ_API_KEY"]
    assert "768 output tokens" in output


def test_budget_blank_secure_key_stops_after_pure_preflight(shell, tmp_path, metadata):
    result, calls, output = _wrapper(shell, tmp_path, metadata, blank=True)
    assert result["exit_code"] == 3
    assert len(calls) == 1 and calls[0]["key_present"] is False
    assert "(credential validation)" in output


@pytest.mark.parametrize("change", [
    ("purpose", "summary_only_qwen_probe"),
    ("experiment_version", "record-summary-only-qwen-observation-v1"),
    ("protocol", "record-summary-budget-v1"),
    ("summary_generation_parameters.requested.max_output_tokens", 3072),
    ("summary_generation_parameters.transmitted.max_output_tokens", 3072),
    ("summary_generation_parameters.max_total_output_tokens", 3072),
    ("summary_generation_parameters.transmitted.reasoning_effort", "low"),
    ("inputs.case.case_id", "observatory-b"),
    ("inputs.case.file", "evals/narrator/record_inline_case_v1.json"),
    ("inputs.prompt.variant", "record-summary-only-v1"),
    ("inputs.prompt.sha256", "94c47c36b620628bb07b74f308adb6d556db7050f31d2aa2c262daa693c0a5d7"),
    ("inputs.cases.0.generation_context.user_packet_sha256", "b7706e060b634d25235955eb43dd3720051916947b7ef508afb02fa75badc7bc"),
    ("inputs.dossier.body_sha256", "b95c1cb7e0bcf93f02a09d2f2a1a4df3b874d505a9c4748aad0722b630dc895f"),
], ids=lambda c: c[0])
def test_new_identity_source_prompt_and_budget_mismatch_precedes_key(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, preflight_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 1 and calls[0]["key_present"] is False
    assert "(offline preflight)" in output


@pytest.mark.parametrize("change", [
    ("evaluation_status", "local_error"),
    ("summary.calls_made", 2),
    ("summary.route_verification.identity_consistent", False),
    ("summary.semantic_fidelity_review.approval", True),
    ("inputs.prompt.variant", "record-summary-only-v1"),
])
def test_live_budget_provenance_counts_route_and_semantics_fail_closed(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, live_change=change)
    assert result["exit_code"] == 3 and len(calls) == 2
    assert "(summary verification)" in output


@pytest.mark.parametrize("mode", ["missing_summary", "duplicate_summary", "preexisting_artifact"])
def test_new_summary_path_is_unique_and_never_reuses_old_evidence(shell, tmp_path, metadata, mode):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode=mode)
    assert result["exit_code"] == (0 if mode == "preexisting_artifact" else 3)
    assert len(calls) == 2
    if mode == "preexisting_artifact":
        assert (tmp_path / "isolated project/eval-results/old/summary.json").read_text() == "old malformed artifact"


def test_word_limit_does_not_promote_or_reject_operational_observation(shell, tmp_path, metadata):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode="long_summary")
    assert result["exit_code"] == 0 and len(calls) == 2
    doc = json.loads((tmp_path / "isolated project/eval-results/synthetic-run/summary.json").read_text())
    assert doc["summary"]["instruction_measurements"]["within_word_limit"] is False
    assert doc["summary"]["semantic_fidelity_review"] == {"status":"not_performed", "approval":None}
