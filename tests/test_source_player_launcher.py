"""Small behavioral suite for explicit process credentials, using a fake child.

The real launcher is copied into a temporary project and runs unchanged except
for its Python executable path. The child is a standalone synthetic evaluator;
no application provider, environment file or real credential is available.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_retained_source_probe_wrapper import _ps, _run, shell

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_source_player_probe.ps1"
KEY = "STORYTELLER_SOURCE_PLAYER_GROQ_KEY"
SENTINELS = ("synthetic-new-key", "synthetic-private-old-key", "synthetic-unrelated-key",
             "synthetic-provider-error")

EVALUATOR = r"""
import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
config=json.loads((root/'config.json').read_text())
def arg(name): return args[args.index(name)+1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
calls_path=root/'calls.json'
calls=json.loads(calls_path.read_text()) if calls_path.exists() else []
calls.append({'args':args,
    'private_present':'STORYTELLER_SOURCE_PLAYER_GROQ_KEY' in os.environ,
    'private_correct':os.environ.get('STORYTELLER_SOURCE_PLAYER_GROQ_KEY')=='synthetic-new-key',
    'parent_keys_absent':'GROQ_API_KEY' not in os.environ and 'OTHER_PROVIDER_KEY' not in os.environ,
    'dotenv_off':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1'})
calls_path.write_text(json.dumps(calls))
assert calls[-1]['parent_keys_absent'] and calls[-1]['dotenv_off']
def metadata():
 return {'purpose':'source_player_probe','probe_kind':'source_player_probe',
    'experiment_version':'source-player-observation-v1','protocol':'narrative-source-application-v1',
    'selected_candidate_id':'qwen-3.8-27b-groq-free-synthetic-nonthink','max_calls':2,
    'synthetic_only':True,'campaign_data_eligible':False,'cap_001_approved':False,'runtime_default_eligible':False,
    'generation_parameters':{'temperature':.65,'max_output_tokens':768,'reasoning_effort':'none',
        'max_total_output_tokens':1536,'initial_quiet_seconds':60,'minimum_inter_call_delay_seconds':60,'deadline_seconds':60},
    'inputs':{'implementation':[{'file':'scripts/evaluate_source_player.py','sha256':sha(Path(__file__))}]}}
if args==['--preflight']:
 assert not calls[-1]['private_present']
 print(json.dumps(metadata()));sys.exit(0)
expected=Path(arg('--expected-preflight'))
assert sha(expected)==arg('--expected-preflight-sha256')
assert json.loads(expected.read_text())==metadata()
batch=arg('--batch-id')
binding=json.loads(expected.with_name('binding.json').read_text())
assert binding['batch_id']==batch and binding['preflight_sha256']==sha(expected)
lifecycle=json.loads(expected.with_name('lifecycle.json').read_text())
assert lifecycle['batch_id']==batch and lifecycle['exit_code'] is None
run=root/'eval-results'/('source-player-'+batch)
summary=run/'summary.json'
if args[0]=='--live':
 assert '--allow-synthetic-only' in args and arg('--api-key-env')=='STORYTELLER_SOURCE_PLAYER_GROQ_KEY'
 assert calls[-1]['private_correct'] and lifecycle['status']=='running'
 if not config['fail_live']:
  run.mkdir(parents=True)
  summary.write_text(json.dumps({'batch_id':batch,'process_exit_code':0}))
 # Deliberately noisy child output must never reach the parent console.
 print('synthetic-new-key synthetic-provider-error')
 print('synthetic-new-key synthetic-provider-error',file=sys.stderr)
 sys.exit(3 if config['fail_live'] else 0)
assert args[0]=='--verify-artifacts' and Path(arg('--verify-artifacts'))==summary
assert not calls[-1]['private_present'] and lifecycle['status']=='verifying_artifacts'
print(json.dumps({'verified':True,'summary_path':str(summary),'process_exit_code':0,'batch_id':batch}))
"""


def launch(shell, tmp_path, *, process=True, credential="present", preflight=False, fail_live=False):
    project = tmp_path / "isolated source player project"
    runner = project / "scripts/run_groq_source_player_probe.ps1"
    runner.parent.mkdir(parents=True)
    original = RUNNER.read_text(encoding="utf-8-sig")
    anchor = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert original.count(anchor) == 1
    runner.write_text(original.replace(anchor, "$python = " + _ps(sys.executable)), encoding="utf-8")
    (runner.parent/"evaluate_source_player.py").write_text(EVALUATOR, encoding="utf-8")
    (project/"config.json").write_text(json.dumps({"fail_live": fail_live}), encoding="utf-8")
    temp = tmp_path/"private temp"
    temp.mkdir()
    report = project/"report.json"
    if credential == "missing":
        credential_command = "Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue"
        expected_parent = "(-not (Test-Path Env:GROQ_API_KEY))"
    else:
        synthetic = " " if credential == "blank" else "synthetic-new-key"
        credential_command = "$env:GROQ_API_KEY=" + _ps(synthetic)
        expected_parent = "($env:GROQ_API_KEY -ceq " + _ps(synthetic) + ")"
    switches = (" -UseProcessCredential" if process else "") + (" -PreflightOnly" if preflight else "")
    command = f"""
$ErrorActionPreference='Stop'
{credential_command}
$env:OTHER_PROVIDER_KEY='synthetic-unrelated-key'
$env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY='synthetic-private-old-key'
$global:sourcePlayerTestPromptCount=0
$global:sourcePlayerTestProtectedPrompt=$false
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 $global:sourcePlayerTestPromptCount+=1
 $global:sourcePlayerTestProtectedPrompt=[bool]$AsSecureString
 if ({'$true' if process or preflight else '$false'}) {{ throw 'Unexpected prompt.' }}
 if (-not $AsSecureString) {{ throw 'Unprotected prompt.' }}
 $paths=@(Get-ChildItem -LiteralPath {_ps(temp)} -Recurse -Filter lifecycle.json)
 if ($paths.Count -ne 1) {{ throw 'Missing verified preflight.' }}
 $life=Get-Content -Raw -LiteralPath $paths[0].FullName | ConvertFrom-Json
 if ($life.status -cne 'awaiting_secure_credential') {{ throw 'Prompt preceded preflight.' }}
 return (ConvertTo-SecureString 'synthetic-new-key' -AsPlainText -Force)
}}
& {_ps(runner)}{switches}
$taskSucceeded=$?
$taskExit=$LASTEXITCODE
$result=@{{exit_code=$taskExit; command_success=$taskSucceeded;
 private_absent=(-not (Test-Path Env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY));
 parent_unchanged={expected_parent};
 unrelated_unchanged=($env:OTHER_PROVIDER_KEY -ceq 'synthetic-unrelated-key');
 prompted=$global:sourcePlayerTestPromptCount; protected_prompt=$global:sourcePlayerTestProtectedPrompt}}
[System.IO.File]::WriteAllText({_ps(report)},($result | ConvertTo-Json))
exit 0
"""
    completed = _run(shell, command, project, temp)
    assert completed.returncode == 0 and completed.stderr == "", completed.stdout + completed.stderr
    assert report.is_file()
    result = json.loads(report.read_text(encoding="utf-8-sig"))
    assert result["private_absent"] and result["parent_unchanged"] and result["unrelated_unchanged"]
    assert not any(sentinel in completed.stdout for sentinel in SENTINELS)
    calls = json.loads((project/"calls.json").read_text())
    assert calls[0]["args"] == ["--preflight"] and not calls[0]["private_present"]
    assert all(call["parent_keys_absent"] and call["dotenv_off"] for call in calls)
    lifecycle_paths = list(temp.rglob("lifecycle.json"))
    assert len(lifecycle_paths) == 1
    lifecycle = json.loads(lifecycle_paths[0].read_text(encoding="utf-8-sig"))
    assert lifecycle["exit_code"] == result["exit_code"]
    assert lifecycle["status"] == ("preflight_only_completed" if preflight else "finished")
    binding = json.loads(lifecycle_paths[0].with_name("binding.json").read_text(encoding="utf-8-sig"))
    assert binding["batch_id"] == lifecycle["batch_id"]
    assert binding["preflight_sha256"] == hashlib.sha256(lifecycle_paths[0].with_name("preflight.json").read_bytes()).hexdigest()
    for path in temp.rglob("*.json"):
        assert not any(sentinel in path.read_text(encoding="utf-8-sig") for sentinel in SENTINELS)
    return result, calls


def test_explicit_process_key_reaches_only_live_child_without_prompt(shell, tmp_path):
    result, calls = launch(shell, tmp_path)
    assert result["exit_code"] == 0 and result["prompted"] == 0
    assert [call["args"][0] for call in calls] == ["--preflight", "--live", "--verify-artifacts"]
    assert [call["private_present"] for call in calls] == [False, True, False]
    assert calls[1]["private_correct"]


@pytest.mark.parametrize("credential", ["missing", "blank"])
def test_missing_process_key_stops_before_live_without_prompt(shell, tmp_path, credential):
    result, calls = launch(shell, tmp_path, credential=credential)
    assert result["exit_code"] == 3 and result["prompted"] == 0
    assert len(calls) == 1


@pytest.mark.parametrize("process", [False, True])
def test_preflight_only_requires_no_key_or_prompt(shell, tmp_path, process):
    result, calls = launch(shell, tmp_path, process=process, credential="missing", preflight=True)
    assert result["exit_code"] == 0 and result["prompted"] == 0
    assert len(calls) == 1


def test_default_mode_still_uses_protected_prompt_after_preflight(shell, tmp_path):
    result, calls = launch(shell, tmp_path, process=False)
    assert result["exit_code"] == 0 and result["prompted"] == 1 and result["protected_prompt"]
    assert calls[1]["private_correct"] and not calls[-1]["private_present"]


def test_live_failure_cleans_private_key_and_preserves_parent_key(shell, tmp_path):
    result, calls = launch(shell, tmp_path, fail_live=True)
    assert result["exit_code"] == 3 and result["prompted"] == 0
    assert [call["args"][0] for call in calls] == ["--preflight", "--live"]
    assert calls[1]["private_correct"]
