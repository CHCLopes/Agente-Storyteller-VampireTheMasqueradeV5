"""Focused native-shell barriers for the bounded narrative source wrapper."""

from datetime import datetime, timedelta
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


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_narrative_source_probe.ps1"
EVALUATOR = "scripts/evaluate_narrator_source.py"
SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]
SENTINELS = ("synthetic-supplied-sentinel", "synthetic-previous-sentinel",
             "synthetic-sensitive-error-payload")


def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def _shell_run(shell, command, cwd):
    names = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "PATHEXT", "COMSPEC",
             "USERPROFILE", "LOCALAPPDATA", "APPDATA")
    env = {name: os.environ[name] for name in names if name in os.environ}
    env.update(STORYTELLER_DISABLE_DOTENV="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=cwd, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
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
        pytest.skip("Host policy prevents script execution; no policy bypass")
    return selected


NATIVE_EVALUATOR = r"""
import hashlib,json,os,sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
args=sys.argv[1:]
mode=config['mode']
code=config['code']
ledger=root/'calls.json'
calls=json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({
 'arguments':args,
 'key_present':'GROQ_API_KEY' in os.environ,
 'key_supplied':os.environ.get('GROQ_API_KEY')=='synthetic-supplied-sentinel',
 'dotenv_disabled':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1',
 'bytecode_disabled':os.environ.get('PYTHONDONTWRITEBYTECODE')=='1',
})
ledger.write_text(json.dumps(calls),encoding='utf-8')
def noise():
 print('synthetic-sensitive-error-payload')
 print('synthetic-sensitive-error-payload',file=sys.stderr)
def metadata():
 return {
  'purpose':'narrative_source_probe','probe_kind':'narrative_source_probe',
  'experiment_version':'narrative-source-observation-v1',
  'protocol':'narrative-source-profile-v1','max_calls':2,'automatic_retries':0,
  'synthetic_only':True,'runtime_promoted':False,'cap_001_status':'not_evaluated',
  'selected_candidate_id':'qwen-3.8-27b-groq-free-synthetic-nonthink',
  'inputs':{'case':{'case_id':argument('--case-id')}},
  'evaluator':{'file':'scripts/evaluate_narrator_source.py',
               'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
 }
def argument(name):
 return args[args.index(name)+1]
if args[0]=='--preflight':
 if mode in ('failed_preflight','malformed_preflight'):
  noise();sys.exit(3 if mode=='failed_preflight' else 0)
 doc=metadata()
 change=config.get('preflight_change')
 if change:
  name,value=change
  if name=='evaluator.sha256':doc['evaluator']['sha256']=value
  elif name=='inputs.case.case_id':doc['inputs']['case']['case_id']=value
  else:doc[name]=value
 if mode=='preflight_file_drift':
  with Path(__file__).open('a') as stream:stream.write('\n# synthetic drift\n')
 print(json.dumps(doc));sys.exit(0)
if '--verify-artifacts' in args:
 expected=json.loads(Path(argument('--expected-preflight')).read_text(encoding='utf-8'))
 assert expected==metadata()
 lifecycle=json.loads(Path(argument('--expected-preflight')).with_name('lifecycle.json').read_text(encoding='utf-8'))
 assert lifecycle['status']=='verifying_artifacts' and lifecycle['exit_code'] is None
 assert lifecycle['batch_id']==argument('--batch-id')
 assert 'GROQ_API_KEY' not in os.environ
 assert Path(argument('--verify-artifacts')).is_file()
 noise()
 sys.exit(3 if mode=='verifier_failure' else 0)
assert args[0]=='--live' and '--allow-synthetic-only' in args
assert argument('--api-key-env')=='GROQ_API_KEY'
expected=json.loads(Path(argument('--expected-preflight')).read_text(encoding='utf-8'))
assert expected==metadata()
lifecycle=json.loads(Path(argument('--expected-preflight')).with_name('lifecycle.json').read_text(encoding='utf-8'))
assert lifecycle['status']=='running' and lifecycle['exit_code'] is None
batch=argument('--batch-id')
assert lifecycle['batch_id']==batch
doc={'batch_id':batch,'process_exit_code':code}
if mode=='wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
if mode=='wrong_exit':doc['process_exit_code']=2 if code==0 else 0
if mode=='boolean_exit':doc['process_exit_code']=False
folder=root/'eval-results/synthetic-run'
folder.mkdir(parents=True)
(folder/'records.jsonl').write_text(json.dumps({'batch_id':batch})+'\n',encoding='utf-8')
if mode!='missing_summary':
 (folder/'summary.json').write_text(
  'malformed' if mode=='malformed_summary' else json.dumps(doc),encoding='utf-8')
if mode=='duplicate_summary':
 other=root/'eval-results/other';other.mkdir()
 (other/'summary.json').write_text(json.dumps(doc),encoding='utf-8')
if mode=='live_file_drift':
 with Path(__file__).open('a') as stream:stream.write('\n# synthetic drift\n')
noise()
sys.exit(code)
"""


def _wrapper(shell, tmp_path, *, mode="normal", code=0, preexisting=True,
             preflight_change=None, blank=False, optional=False, case_id="courtyard-observe-wait"):
    project = tmp_path / "isolated project"
    runner = project / RUNNER.relative_to(ROOT)
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    runner.write_text(
        source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve())),
        encoding="utf-8",
    )
    (project / EVALUATOR).write_text(NATIVE_EVALUATOR, encoding="utf-8")
    (project / "config.json").write_text(json.dumps({
        "mode": mode, "code": code, "preflight_change": preflight_change,
    }), encoding="utf-8")
    # Existing unrelated evidence must neither satisfy the new run nor be rewritten.
    old = project / "eval-results/old/summary.json"
    old.parent.mkdir(parents=True)
    old.write_text("old evidence, deliberately not parsed", encoding="utf-8")
    result_path = project / "harness-result.json"
    prompt_path = project / "prompt-called.txt"
    set_key = ("$env:GROQ_API_KEY='synthetic-previous-sentinel'" if preexisting
               else "Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue")
    key = ("[System.Security.SecureString]::new()" if blank else
           "ConvertTo-SecureString 'synthetic-supplied-sentinel' -AsPlainText -Force")
    invoke = f"& {_ps(runner)} -CaseId {_ps(case_id)}" + ("" if optional else " -ApiKey $key")
    command = f"""
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
{set_key}
$env:STORYTELLER_DISABLE_DOTENV='synthetic-prior-dotenv'
$env:PYTHONDONTWRITEBYTECODE='synthetic-prior-bytecode'
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 if (-not $AsSecureString) {{ throw 'Unprotected prompt' }}
 [System.IO.File]::WriteAllText({_ps(prompt_path)},'protected')
 return (ConvertTo-SecureString 'synthetic-supplied-sentinel' -AsPlainText -Force)
}}
$key={key}
$global:LASTEXITCODE=0
{invoke}
$result=@{{exit_code=$LASTEXITCODE;present=(Test-Path Env:GROQ_API_KEY);
restored=($env:GROQ_API_KEY -eq 'synthetic-previous-sentinel');
dotenv=$env:STORYTELLER_DISABLE_DOTENV;bytecode=$env:PYTHONDONTWRITEBYTECODE;
preference=$PSNativeCommandUseErrorActionPreference;temp_root=[System.IO.Path]::GetTempPath()}}
$result | ConvertTo-Json | Set-Content -LiteralPath {_ps(result_path)}
exit 0
"""
    completed = _shell_run(shell, command, project)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for sentinel in SENTINELS:
        assert sentinel not in completed.stdout + completed.stderr
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    assert result["present"] is result["restored"] is preexisting
    assert result["dotenv"] == "synthetic-prior-dotenv"
    assert result["bytecode"] == "synthetic-prior-bytecode"
    assert result["preference"] is True
    batch = next(line.split(": ", 1)[1] for line in completed.stdout.splitlines()
                 if line.startswith("Narrative source probe batch: "))
    assert str(UUID(batch)) == batch
    lifecycle_path = Path(result["temp_root"]) / ("storyteller-narrative-source-window-" + batch) / "lifecycle.json"
    if "stopped during offline preflight" in completed.stdout:
        assert not lifecycle_path.exists()
    else:
        lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        assert set(lifecycle) == {"batch_id", "status", "updated_at", "exit_code"}
        assert lifecycle["batch_id"] == batch and lifecycle["status"] == "finished"
        assert type(lifecycle["exit_code"]) is int
        assert lifecycle["exit_code"] == result["exit_code"]
        assert datetime.fromisoformat(lifecycle["updated_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)
        assert not any(value in lifecycle_path.read_text(encoding="utf-8") for value in SENTINELS)
    assert old.read_text(encoding="utf-8") == "old evidence, deliberately not parsed"
    calls = json.loads((project / "calls.json").read_text(encoding="utf-8"))
    assert calls[0]["arguments"] == ["--preflight", "--case-id", case_id]
    assert calls[0]["key_present"] is False
    assert all(call["dotenv_disabled"] and call["bytecode_disabled"] for call in calls)
    return result, calls, completed.stdout, prompt_path.exists(), project


@pytest.mark.parametrize("available_shell", SHELLS or [None],
                         ids=lambda p: Path(p).stem if p else "unavailable")
def test_source_wrapper_parses_without_policy_bypass(available_shell, tmp_path):
    if available_shell is None:
        pytest.skip("PowerShell unavailable")
    command = (
        "$tokens=$null; $errors=$null; "
        "$null=[System.Management.Automation.Language.Parser]::ParseFile("
        + _ps(RUNNER) + ",[ref]$tokens,[ref]$errors); if ($errors.Count) { exit 1 }"
    )
    result = _shell_run(available_shell, command, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("code", "preexisting"), [(0, True), (1, False), (2, True),
                                                  (3, False), (130, True)])
def test_verified_child_exits_preserve_scope_secret_lifecycle_and_artifacts(
    shell, tmp_path, code, preexisting
):
    result, calls, output, prompted, project = _wrapper(
        shell, tmp_path, code=code, preexisting=preexisting
    )
    assert result["exit_code"] == code, output
    assert len(calls) == 3 and not prompted
    assert calls[1]["key_supplied"] is True
    assert calls[2]["key_present"] is False
    live = calls[1]["arguments"]
    batch = live[live.index("--batch-id") + 1]
    expected = live[live.index("--expected-preflight") + 1]
    assert str(UUID(batch)) == batch
    assert live == ["--live", "--case-id", "courtyard-observe-wait", "--allow-synthetic-only", "--batch-id", batch,
                    "--expected-preflight", expected, "--api-key-env", "GROQ_API_KEY"]
    assert calls[2]["arguments"] == [
        "--verify-artifacts", str(project / "eval-results/synthetic-run/summary.json"),
        "--case-id", "courtyard-observe-wait", "--expected-preflight", expected, "--batch-id", batch,
    ]
    assert Path(expected).is_file()
    assert "remain unapproved" in output


@pytest.mark.parametrize("mode", ["failed_preflight", "malformed_preflight", "preflight_file_drift"])
def test_failed_or_changed_preflight_never_reaches_protected_prompt(shell, tmp_path, mode):
    result, calls, output, prompted, _ = _wrapper(shell, tmp_path, mode=mode, optional=True)
    assert result["exit_code"] == 3 and len(calls) == 1 and not prompted
    assert "stopped during offline preflight" in output


@pytest.mark.parametrize("change", [
    ("purpose", "other_probe"),
    ("experiment_version", "other-observation-v1"),
    ("max_calls", "2"),
    ("automatic_retries", False),
    ("evaluator.sha256", "0" * 64),
], ids=lambda value: value[0])
def test_scope_types_and_executable_identity_precede_credential_entry(shell, tmp_path, change):
    result, calls, output, prompted, _ = _wrapper(
        shell, tmp_path, preflight_change=change, optional=True
    )
    assert result["exit_code"] == 3 and len(calls) == 1 and not prompted
    assert "stopped during offline preflight" in output


def test_optional_key_uses_protected_prompt_after_preflight_only(shell, tmp_path):
    result, calls, _, prompted, _ = _wrapper(shell, tmp_path, optional=True, preexisting=False)
    assert result["exit_code"] == 0 and prompted and len(calls) == 3
    assert calls[0]["key_present"] is False and calls[1]["key_supplied"] is True
    assert calls[2]["key_present"] is False


def test_blank_secure_string_stops_before_any_live_invocation(shell, tmp_path):
    result, calls, output, prompted, _ = _wrapper(
        shell, tmp_path, blank=True, preexisting=False
    )
    assert result["exit_code"] == 3 and len(calls) == 1 and not prompted
    assert "stopped during protected credential entry" in output


def test_failed_offline_verifier_overrides_successful_child_and_discards_its_output(shell, tmp_path):
    result, calls, output, _, _ = _wrapper(shell, tmp_path, mode="verifier_failure")
    assert result["exit_code"] == 3 and len(calls) == 3
    assert calls[-1]["key_present"] is False
    assert "stopped during offline evidence verification" in output


@pytest.mark.parametrize("mode", ["wrong_batch", "wrong_exit", "boolean_exit", "malformed_summary"])
def test_verifier_success_cannot_override_local_summary_identity_checks(shell, tmp_path, mode):
    result, calls, output, _, _ = _wrapper(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3 and len(calls) == 3
    assert "stopped during offline evidence verification" in output


@pytest.mark.parametrize("mode", ["missing_summary", "duplicate_summary"])
def test_missing_or_ambiguous_new_evidence_is_preserved_without_retry(shell, tmp_path, mode):
    result, calls, output, _, project = _wrapper(shell, tmp_path, mode=mode, code=130)
    assert result["exit_code"] == 3 and len(calls) == 2
    assert (project / "eval-results/synthetic-run/records.jsonl").is_file()
    assert "stopped during offline evidence verification" in output


def test_evaluator_drift_during_child_blocks_verifier_and_preserves_cleanup(shell, tmp_path):
    result, calls, output, _, _ = _wrapper(shell, tmp_path, mode="live_file_drift")
    assert result["exit_code"] == 3 and len(calls) == 2
    assert "stopped during offline evidence verification" in output


def test_unknown_native_child_exit_cannot_be_promoted_to_a_known_result(shell, tmp_path):
    result, calls, output, _, _ = _wrapper(shell, tmp_path, code=17)
    assert result["exit_code"] == 3 and len(calls) == 2
    assert "stopped during bounded live invocation" in output


def test_real_preflight_reaches_blank_credential_without_call_or_result_artifact(shell, tmp_path):
    case_id = "courtyard-observe-wait"
    output_root = ROOT / "eval-results"
    def inventory():
        return {str(path.relative_to(output_root)): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in output_root.rglob("*") if path.is_file()}
    before = inventory()
    command = f"""
$ErrorActionPreference='Stop'
Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
$key=[System.Security.SecureString]::new()
& {_ps(RUNNER)} -CaseId {_ps(case_id)} -ApiKey $key
$code=$LASTEXITCODE
if (Test-Path Env:GROQ_API_KEY) {{ exit 91 }}
exit $code
"""
    result = _shell_run(shell, command, ROOT)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "stopped during protected credential entry" in result.stdout
    assert "Protected credential accepted" not in result.stdout
    assert result.stderr == ""
    assert inventory() == before


def test_courtyard_choice_reaches_all_three_stages_with_no_secret_in_verifier(shell, tmp_path):
    result, calls, output, prompted, _ = _wrapper(shell, tmp_path, case_id="courtyard-observe-wait")
    assert result["exit_code"] == 0, output
    assert len(calls) == 3 and not prompted
    for call in calls:
        arguments = call["arguments"]
        assert arguments[arguments.index("--case-id") + 1] == "courtyard-observe-wait"
    assert calls[1]["key_supplied"] and not calls[2]["key_present"]


def test_wrong_preflight_case_never_reaches_key_prompt(shell, tmp_path):
    result, calls, output, prompted, _ = _wrapper(
        shell, tmp_path, case_id="courtyard-observe-wait", optional=True,
        preflight_change=("inputs.case.case_id", "greenhouse-observe-wait"))
    assert result["exit_code"] == 3 and len(calls) == 1 and not prompted
    assert "stopped during offline preflight" in output


def test_operational_wrapper_rejects_closed_case_before_preflight(shell, tmp_path):
    result = _shell_run(shell, f"& {_ps(RUNNER)} -CaseId 'greenhouse-observe-wait'", ROOT)
    assert result.returncode != 0
    assert "Narrative source probe batch:" not in result.stdout
    assert "Protected credential accepted" not in result.stdout
