"""Native launcher contract with an isolated synthetic child, never live Groq.

The launcher runs unchanged except for the interpreter path in a temporary
project. Real authored corpus/protocol bytes are copied; all credentials and
provider output below are deliberately synthetic sentinels.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_retained_source_probe_wrapper import _ps, _run, shell

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_source_comparison.ps1"
KEY = "STORYTELLER_SOURCE_COMPARISON_GROQ_KEY"
SENTINELS = ("synthetic-new-key", "synthetic-private-old-key", "synthetic-unrelated-key",
             "synthetic-provider-error")
INPUT_FILES = ("evals/narrator/source_comparison_v1.json",
               "evals/narrator/source_comparison_protocol_v1.md")
EXTRA_FILES = ("evals/narrator/fake_manifest.json", "evals/narrator/fake_prompt.md")

EVALUATOR = r"""
import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
config=json.loads((root/'config.json').read_text())
mode=config['mode'];code=config['code']
def arg(name): return args[args.index(name)+1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def entry(file): return {'file':file,'sha256':sha(root/file)}
calls_path=root/'calls.json'
calls=json.loads(calls_path.read_text()) if calls_path.exists() else []
calls.append({'args':args,
    'private_present':'STORYTELLER_SOURCE_COMPARISON_GROQ_KEY' in os.environ,
    'private_correct':os.environ.get('STORYTELLER_SOURCE_COMPARISON_GROQ_KEY')=='synthetic-new-key',
    'parent_keys_absent':'GROQ_API_KEY' not in os.environ and 'OTHER_PROVIDER_KEY' not in os.environ,
    'dotenv_off':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1',
    'bytecode_off':os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'})
calls_path.write_text(json.dumps(calls))
assert calls[-1]['parent_keys_absent'] and calls[-1]['dotenv_off'] and calls[-1]['bytecode_off']
def metadata():
 ids=['qwen-3.8-27b-groq-free-synthetic-nonthink','gpt-oss-120b-groq-free-synthetic-low']
 return {'purpose':'source_model_comparison','probe_kind':'source_model_comparison',
    'experiment_version':'source-comparison-v1','protocol':'narrative-source-application-v1',
    'selected_candidate_ids':ids,'max_calls':12,
    'synthetic_only':True,'campaign_data_eligible':False,'cap_001_approved':False,'runtime_default_eligible':False,
    'generation_parameters':{'temperature':.65,'max_output_tokens':768,
        'max_total_output_tokens':9216,'initial_quiet_seconds':60,'minimum_inter_call_delay_seconds':60,'deadline_seconds':60},
    'inputs':{'candidates':[{'candidate_id':ids[0],'model':'qwen/qwen3.8-27b','reasoning_effort':'none','provider':'Groq'},
                            {'candidate_id':ids[1],'model':'openai/gpt-oss-120b','reasoning_effort':'low','provider':'Groq'}],
        'corpus':entry('evals/narrator/source_comparison_v1.json'),
        'protocol':entry('evals/narrator/source_comparison_protocol_v1.md'),
        'manifest':entry('evals/narrator/fake_manifest.json'),
        'prompt':{'file':'evals/narrator/fake_prompt.md','file_sha256':sha(root/'evals/narrator/fake_prompt.md'),'sha256':'0'*64},
        'implementation':[entry('scripts/evaluate_source_comparison.py'),entry('api/synthetic_contract.py')]}}
if args==['--preflight']:
 assert not calls[-1]['private_present']
 doc=metadata()
 if config['change']:
  path,value=config['change'];node=doc
  for key in path.split('.')[:-1]:node=node[int(key)] if isinstance(node,list) else node[key]
  key=path.split('.')[-1]
  node[int(key) if isinstance(node,list) else key]=value
 if mode=='preflight_self_drift':
  with Path(__file__).open('a') as file:file.write('\n# changed\n')
 if mode=='preflight_launcher_drift':
  with (root/'scripts/run_groq_source_comparison.ps1').open('a') as file:file.write('\n# changed\n')
 if mode=='preflight_noisy':print('synthetic-provider-error',file=sys.stderr)
 if mode=='preflight_malformed':print('synthetic-provider-error')
 else: print(json.dumps(doc))
 sys.exit(0)
expected=Path(arg('--expected-preflight'))
assert sha(expected)==arg('--expected-preflight-sha256')
assert json.loads(expected.read_text())==metadata()
batch=arg('--batch-id')
binding=json.loads(expected.with_name('binding.json').read_text())
assert binding['batch_id']==batch and binding['preflight_sha256']==sha(expected)
assert binding['launcher_sha256']==sha(root/'scripts/run_groq_source_comparison.ps1')
lifecycle=json.loads(expected.with_name('lifecycle.json').read_text())
assert lifecycle['batch_id']==batch and lifecycle['exit_code'] is None
run=root/'eval-results'/('source-comparison-'+batch)
summary=run/'summary.json'
if args[0]=='--live':
 assert '--allow-synthetic-only' in args and arg('--api-key-env')=='STORYTELLER_SOURCE_COMPARISON_GROQ_KEY'
 assert calls[-1]['private_correct'] and lifecycle['status']=='running'
 run.mkdir(parents=True)
 doc={'batch_id':batch,'process_exit_code':code}
 if mode=='summary_incomplete':del doc['process_exit_code']
 if mode=='summary_wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
 if mode!='summary_absent':summary.write_text(json.dumps(doc))
 if mode=='live_implementation_drift':
  with (root/'api/synthetic_contract.py').open('a') as file:file.write('\n# changed\n')
 if mode=='live_launcher_drift':
  with (root/'scripts/run_groq_source_comparison.ps1').open('a') as file:file.write('\n# changed\n')
 # Deliberately noisy child output must never reach the parent console.
 print('synthetic-new-key synthetic-provider-error')
 print('synthetic-new-key synthetic-provider-error',file=sys.stderr)
 sys.exit(code)
assert args[0]=='--verify-artifacts' and Path(arg('--verify-artifacts'))==summary
assert not calls[-1]['private_present'] and lifecycle['status']=='verifying_artifacts'
doc={'verified':True,'summary_path':str(summary),'process_exit_code':code,'batch_id':batch}
if mode=='verifier_incomplete':del doc['process_exit_code']
if mode=='verifier_false':doc['verified']=False
if mode=='verifier_boolean_exit':doc['process_exit_code']=False
if mode=='verifier_wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
if mode=='verifier_wrong_path':doc['summary_path']=str(root/'eval-results/old/summary.json')
if mode=='verifier_mutates_summary':summary.write_text(summary.read_text()+' ')
if mode=='verifier_noisy':print('synthetic-provider-error',file=sys.stderr)
print(json.dumps(doc))
sys.exit(3 if mode=='verifier_failure' else 0)
"""


def launch(shell, tmp_path, *, process=True, credential="present", preflight=False,
           mode="normal", change=None, prompt_drift=None, code=0):
    # Keep child artifact paths below Windows native path limits even with a long basetemp.
    project = tmp_path / "project"
    runner = project / RUNNER.relative_to(ROOT)
    runner.parent.mkdir(parents=True)
    original = RUNNER.read_text(encoding="utf-8-sig")
    anchor = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert original.count(anchor) == 1
    runner.write_text(original.replace(anchor, "$python = " + _ps(sys.executable)), encoding="utf-8")
    (runner.parent / "evaluate_source_comparison.py").write_text(EVALUATOR, encoding="utf-8")
    (project / "api").mkdir()
    (project / "api/synthetic_contract.py").write_text("# synthetic input\n", encoding="utf-8")
    for file in INPUT_FILES:
        copy = project / file
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes((ROOT / file).read_bytes())
    for file in EXTRA_FILES:
        (project / file).write_text("synthetic frozen input\n", encoding="utf-8")
    (project / "config.json").write_text(json.dumps({"mode": mode, "change": change, "code": code}), encoding="utf-8")
    temp = tmp_path / "private temp"
    temp.mkdir()
    report = project / "report.json"
    if credential == "missing":
        credential_command = "Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue"
        expected_parent = "(-not (Test-Path Env:GROQ_API_KEY))"
    else:
        synthetic = " " if credential == "blank" else "synthetic-new-key"
        credential_command = "$env:GROQ_API_KEY=" + _ps(synthetic)
        expected_parent = "($env:GROQ_API_KEY -ceq " + _ps(synthetic) + ")"
    switches = (" -UseProcessCredential" if process else "") + (" -PreflightOnly" if preflight else "")
    drift_command = ""
    if prompt_drift:
        drift_path = "$paths[0].DirectoryName + '\\preflight.json'" if prompt_drift == "preflight" else _ps(project / prompt_drift)
        drift_command = "[System.IO.File]::AppendAllText((" + drift_path + "),' ' )"
    command = f"""
$ErrorActionPreference='Stop'
{credential_command}
$env:OTHER_PROVIDER_KEY='synthetic-unrelated-key'
$env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY='synthetic-private-old-key'
$global:sourceComparisonTestPromptCount=0
$global:sourceComparisonTestProtectedPrompt=$false
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 $global:sourceComparisonTestPromptCount+=1
 $global:sourceComparisonTestProtectedPrompt=[bool]$AsSecureString
 if ({'$true' if process or preflight else '$false'}) {{ throw 'Unexpected prompt.' }}
 if (-not $AsSecureString) {{ throw 'Unprotected prompt.' }}
 $paths=@(Get-ChildItem -LiteralPath {_ps(temp)} -Recurse -Filter lifecycle.json)
 if ($paths.Count -ne 1) {{ throw 'Missing verified preflight.' }}
 $life=Get-Content -Raw -LiteralPath $paths[0].FullName | ConvertFrom-Json
 if ($life.status -cne 'awaiting_secure_credential') {{ throw 'Prompt preceded preflight.' }}
 {drift_command}
 return (ConvertTo-SecureString 'synthetic-new-key' -AsPlainText -Force)
}}
& {_ps(runner)}{switches}
$taskSucceeded=$?
$taskExit=$LASTEXITCODE
$result=@{{exit_code=$taskExit; command_success=$taskSucceeded;
 private_absent=(-not (Test-Path Env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY));
 parent_unchanged={expected_parent};
 unrelated_unchanged=($env:OTHER_PROVIDER_KEY -ceq 'synthetic-unrelated-key');
 prompted=$global:sourceComparisonTestPromptCount; protected_prompt=$global:sourceComparisonTestProtectedPrompt}}
[System.IO.File]::WriteAllText({_ps(report)},($result | ConvertTo-Json))
exit 0
"""
    completed = _run(shell, command, project, temp)
    assert completed.returncode == 0 and completed.stderr == "", completed.stdout + completed.stderr
    result = json.loads(report.read_text(encoding="utf-8-sig"))
    assert result["private_absent"] and result["parent_unchanged"] and result["unrelated_unchanged"]
    assert not any(sentinel in completed.stdout for sentinel in SENTINELS)
    calls = json.loads((project / "calls.json").read_text())
    assert calls[0]["args"] == ["--preflight"] and not calls[0]["private_present"]
    assert all(call["parent_keys_absent"] and call["dotenv_off"] and call["bytecode_off"] for call in calls)
    lifecycle_paths = list(temp.rglob("lifecycle.json"))
    assert len(lifecycle_paths) <= 1
    if lifecycle_paths:
        lifecycle = json.loads(lifecycle_paths[0].read_text(encoding="utf-8-sig"))
        assert lifecycle["exit_code"] == result["exit_code"]
        assert lifecycle["status"] == ("preflight_only_completed" if preflight and not result["exit_code"] else "finished")
        binding = json.loads(lifecycle_paths[0].with_name("binding.json").read_text(encoding="utf-8-sig"))
        assert binding["batch_id"] == lifecycle["batch_id"] and len(binding["launcher_sha256"]) == 64
        if prompt_drift != "preflight":
            assert binding["preflight_sha256"] == hashlib.sha256(lifecycle_paths[0].with_name("preflight.json").read_bytes()).hexdigest()
    for path in temp.rglob("*.json"):
        assert not any(sentinel in path.read_text(encoding="utf-8-sig") for sentinel in SENTINELS)
    return result, calls


def test_process_credential_only_live_child_and_safe_output(shell, tmp_path):
    result, calls = launch(shell, tmp_path)
    assert result["exit_code"] == 0 and result["prompted"] == 0
    assert [call["args"][0] for call in calls] == ["--preflight", "--live", "--verify-artifacts"]
    assert [call["private_present"] for call in calls] == [False, True, False]
    assert calls[1]["private_correct"]


@pytest.mark.parametrize("credential", ["missing", "blank"])
def test_missing_process_credential_stops_without_prompt_or_live(shell, tmp_path, credential):
    result, calls = launch(shell, tmp_path, credential=credential)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("process", [False, True])
def test_preflight_never_requests_key(shell, tmp_path, process):
    result, calls = launch(shell, tmp_path, process=process, credential="missing", preflight=True)
    assert result["exit_code"] == 0 and result["prompted"] == 0 and len(calls) == 1


def test_default_secure_prompt_follows_verified_preflight(shell, tmp_path):
    result, calls = launch(shell, tmp_path, process=False)
    assert result["exit_code"] == 0 and result["prompted"] == 1 and result["protected_prompt"]
    assert calls[1]["private_correct"] and not calls[-1]["private_present"]


@pytest.mark.parametrize("change", [
    ("purpose", "source_player_probe"), ("experiment_version", "old"), ("max_calls", 13),
    ("max_calls", True), ("synthetic_only", "true"), ("campaign_data_eligible", True),
    ("selected_candidate_ids.0", "gpt-oss-120b-groq-free-synthetic-low"),
    ("inputs.candidates.1.model", "openai/gpt-oss-20b"),
    ("inputs.candidates.0.reasoning_effort", "low"), ("inputs.candidates.1.provider", "OpenRouter"),
    ("generation_parameters.max_total_output_tokens", 10000),
    ("generation_parameters.max_output_tokens", 769), ("generation_parameters.temperature", 1),
    ("generation_parameters.initial_quiet_seconds", 0),
    ("generation_parameters.minimum_inter_call_delay_seconds", 0),
    ("generation_parameters.deadline_seconds", 61),
    ("inputs.corpus.sha256", "0" * 64), ("inputs.protocol.sha256", "0" * 64),
    ("inputs.manifest.sha256", "0" * 64), ("inputs.prompt.file_sha256", "0" * 64),
    ("inputs.implementation.1.sha256", "0" * 64),
    ("inputs.implementation.1.file", "../outside.py"),
])
def test_changed_contract_rejected_before_prompt(shell, tmp_path, change):
    result, calls = launch(shell, tmp_path, process=False, change=change)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("mode", ["preflight_self_drift", "preflight_launcher_drift", "preflight_malformed", "preflight_noisy"])
def test_preflight_drift_and_invalid_output_fail_before_key(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, process=False, mode=mode)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("prompt_drift", ["scripts/evaluate_source_comparison.py", "scripts/run_groq_source_comparison.ps1",
                                         "api/synthetic_contract.py", *INPUT_FILES, *EXTRA_FILES, "preflight"])
def test_frozen_files_changed_during_prompt_cannot_start_live(shell, tmp_path, prompt_drift):
    result, calls = launch(shell, tmp_path, process=False, prompt_drift=prompt_drift)
    assert result["exit_code"] == 3 and result["prompted"] == 1 and len(calls) == 1


@pytest.mark.parametrize("mode", ["summary_absent", "live_implementation_drift", "live_launcher_drift"])
def test_live_artifact_absence_or_code_drift_prevents_verifier(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3
    assert [call["args"][0] for call in calls] == ["--preflight", "--live"]


@pytest.mark.parametrize("mode", ["summary_incomplete", "summary_wrong_batch", "verifier_incomplete", "verifier_false",
                                 "verifier_boolean_exit", "verifier_wrong_batch", "verifier_wrong_path",
                                 "verifier_mutates_summary", "verifier_noisy", "verifier_failure"])
def test_false_incomplete_or_changed_verification_fails_closed(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3 and len(calls) == 3
    assert not calls[-1]["private_present"]


@pytest.mark.parametrize("code", [1, 2, 3, 130])
def test_valid_nonzero_observation_is_still_audited_without_credential(shell, tmp_path, code):
    result, calls = launch(shell, tmp_path, code=code)
    assert result["exit_code"] == code and len(calls) == 3
    assert [call["private_present"] for call in calls] == [False, True, False]


def test_unknown_exit_code_cannot_be_certified(shell, tmp_path):
    result, calls = launch(shell, tmp_path, code=17)
    assert result["exit_code"] == 3 and len(calls) == 2
