"""Native PowerShell launcher contracts with synthetic credentials/children only.

Temporary project sources are synthetic. No real provider, key, or network.
The launcher selects the installed test Python interpreter; one fault case
injects a host interruption immediately after its owned child starts.
"""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_retained_source_probe_wrapper import _ps, _run, shell

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_source_dialogue_response.ps1"
KEY = "STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY"
SENTINELS = ("synthetic-new-key", "synthetic-private-old-key", "synthetic-unrelated-key", "synthetic-provider-error")
INPUT_FILES = ("evals/narrator/source_dialogue_response_v1.json", "evals/narrator/source_dialogue_response_protocol_v1.md")
EXTRA_FILES = ("evals/narrator/fake_manifest.json", "evals/narrator/prompts/narrative-source-dialogue-v1.md")

EVALUATOR = r"""

import hashlib,json,os,sys,time
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
    'private_present':'STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY' in os.environ,
    'private_correct':os.environ.get('STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY')=='synthetic-new-key',
    'parent_keys_absent':'GROQ_API_KEY' not in os.environ and 'OTHER_PROVIDER_KEY' not in os.environ,
    'dotenv_off':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1',
    'bytecode_off':os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'})
calls_path.write_text(json.dumps(calls))
assert calls[-1]['parent_keys_absent'] and calls[-1]['dotenv_off'] and calls[-1]['bytecode_off']
def metadata():
 candidate='qwen-3.8-27b-groq-free-synthetic-nonthink'
 system='Synthetic SYSTEM only.'
 slots=[{'slot_id':'slot-'+str(i+1),'case_id':case} for i,case in enumerate(['direct-question','after-silence','wait-control'])]
 frozen=[]
 for slot in slots:
  user=json.dumps({'case_id':slot['case_id'],'player_input':'Aguardo.'},sort_keys=True,separators=(',',':'))
  body={'model':'qwen/qwen3.8-27b','reasoning_effort':'none','max_completion_tokens':768,'temperature':.65,'stream':False,
   'response_format':{'type':'json_schema','json_schema':{'name':'synthetic','strict':True,'schema':{}}},
   'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
  frozen.append({**slot,'npc_aliases':['Mara'],'request':body,
   'body_sha256':hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
   'user_packet':user,'user_packet_sha256':hashlib.sha256(user.encode()).hexdigest(),
   'authored_source':{'origin':'authored_synthetic_fixture','provider_evidence':None,'application_commit':False,'projection':None}})
 return {'purpose':'source_dialogue_response_probe','probe_kind':'source_dialogue_response_probe',
    'experiment_version':'source-dialogue-response-v1','protocol':'narrative-source-application-v1',
    'selected_candidate_id':candidate,'max_calls':3,
    'target':{'profile':'source-dialogue-response-'+candidate,'provider':'Groq','model':'qwen/qwen3.8-27b'},
    'slots':slots,'frozen_requests':frozen,
    'synthetic_only':True,'campaign_data_eligible':False,'cap_001_approved':False,'runtime_default_eligible':False,
    'generation_parameters':{'temperature':.65,'max_output_tokens':768,'reasoning_effort':'none','max_calls':3,
        'max_total_output_tokens':2304,'initial_quiet_seconds':60,'minimum_inter_call_delay_seconds':60,'deadline_seconds':60},
    'inputs':{'corpus':entry('evals/narrator/source_dialogue_response_v1.json'),
        'protocol':entry('evals/narrator/source_dialogue_response_protocol_v1.md'),
        'manifest':entry('evals/narrator/fake_manifest.json'),
        'prompt':{'file':'evals/narrator/prompts/narrative-source-dialogue-v1.md',
         'file_sha256':sha(root/'evals/narrator/prompts/narrative-source-dialogue-v1.md'),
         'sha256':hashlib.sha256(system.encode()).hexdigest(),'version':'narrative-source-dialogue-v1'},
        'response_schema_sha256':'0'*64,'provider_schema_sha256':'0'*64,
        'implementation':[entry('scripts/evaluate_source_dialogue_response.py'),entry('api/synthetic_contract.py')]}}
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
  with (root/'scripts/run_groq_source_dialogue_response.ps1').open('a') as file:file.write('\n# changed\n')
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
assert binding['launcher_sha256']==sha(root/'scripts/run_groq_source_dialogue_response.ps1')
lifecycle=json.loads(expected.with_name('lifecycle.json').read_text())
assert lifecycle['batch_id']==batch and lifecycle['exit_code'] is None
run=root/'eval-results'/('source-dialogue-response-'+batch)
summary=run/'summary.json'
if args[0]=='--live':
 assert '--allow-synthetic-only' in args and arg('--api-key-env')=='STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY'
 assert calls[-1]['private_correct'] and lifecycle['status']=='running'
 if mode=='host_interruption':
  (root/'waiting-child.json').write_text(json.dumps({'pid':os.getpid()}))
  time.sleep(30)
 run.mkdir(parents=True)
 doc={'batch_id':batch,'process_exit_code':code}
 if mode=='summary_incomplete':del doc['process_exit_code']
 if mode=='summary_wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
 if mode!='summary_absent':summary.write_text(json.dumps(doc))
 if mode=='live_implementation_drift':
  with (root/'api/synthetic_contract.py').open('a') as file:file.write('\n# changed\n')
 if mode=='live_launcher_drift':
  with (root/'scripts/run_groq_source_dialogue_response.ps1').open('a') as file:file.write('\n# changed\n')
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


def launch(shell, tmp_path, *, provided=True, credential="present", preflight=False,
           mode="normal", change=None, prompt_drift=None, code=0):
    # Keep child artifact paths below Windows native path limits even with a long basetemp.
    project = tmp_path / "project"
    runner = project / RUNNER.relative_to(ROOT)
    runner.parent.mkdir(parents=True)
    original = RUNNER.read_text(encoding="utf-8-sig")
    anchor = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert original.count(anchor) == 1
    original = original.replace(anchor, "$python = " + _ps(sys.executable))
    if mode == "host_interruption":
        fault_anchor = "        $stdout = $process.StandardOutput.ReadToEndAsync()"
        assert original.count(fault_anchor) == 1
        original = original.replace(fault_anchor, """        if ($null -ne $ChildCredential) {
            $ready = Join-Path $projectRoot 'waiting-child.json'
            $until = [DateTime]::UtcNow.AddSeconds(8)
            while (-not (Test-Path -LiteralPath $ready) -and [DateTime]::UtcNow -lt $until) { Start-Sleep -Milliseconds 25 }
            [System.IO.File]::WriteAllText((Join-Path $projectRoot 'started-child.json'), (@{pid=$process.Id} | ConvertTo-Json))
            throw 'synthetic-provider-error'
        }
""" + fault_anchor)
    runner.write_text(original, encoding="utf-8")
    (runner.parent / "evaluate_source_dialogue_response.py").write_text(EVALUATOR, encoding="utf-8")
    (project / "api").mkdir()
    (project / "api/synthetic_contract.py").write_text("# synthetic input\n", encoding="utf-8")
    for file in INPUT_FILES:
        copy = project / file
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text("synthetic authored input\n", encoding="utf-8")
    for file in EXTRA_FILES:
        (project / file).parent.mkdir(parents=True, exist_ok=True)
        (project / file).write_text("synthetic frozen input\n", encoding="utf-8")
    (project / "config.json").write_text(json.dumps({"mode": mode, "change": change, "code": code}), encoding="utf-8")
    temp = tmp_path / "private temp"
    temp.mkdir()
    report = project / "report.json"
    synthetic = " " if credential == "blank" else "synthetic-new-key"
    if credential == "null":
        credential_command = "$StorytellerGroqKey=$null"
    else:
        credential_command = "$StorytellerGroqKey=ConvertTo-SecureString " + _ps(synthetic) + " -AsPlainText -Force"
        if credential == "disposed":
            credential_command += "\n$StorytellerGroqKey.Dispose()"
    switches = (" -Credential $StorytellerGroqKey" if provided else "") + (" -PreflightOnly" if preflight else "")
    if credential == "null":
        expected_source = "($null -eq $StorytellerGroqKey)"
    elif credential == "disposed":
        expected_source = "$true"
    else:
        expected_source = "([System.Net.NetworkCredential]::new('', $StorytellerGroqKey).Password -ceq " + _ps(synthetic) + ")"
    drift_command = ""
    if prompt_drift:
        drift_path = "$paths[0].DirectoryName + '\\preflight.json'" if prompt_drift == "preflight" else _ps(project / prompt_drift)
        drift_command = "[System.IO.File]::AppendAllText((" + drift_path + "),' ' )"
    command = f"""
$ErrorActionPreference='Stop'
{credential_command}
$env:GROQ_API_KEY='synthetic-private-old-key'
$env:OTHER_PROVIDER_KEY='synthetic-unrelated-key'
$env:STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY='synthetic-private-old-key'
$global:sourceDialogueResponseTestPromptCount=0
$global:sourceDialogueResponseTestProtectedPrompt=$false
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 $global:sourceDialogueResponseTestPromptCount+=1
 $global:sourceDialogueResponseTestProtectedPrompt=[bool]$AsSecureString
 if ({'$true' if provided or preflight else '$false'}) {{ throw 'Unexpected prompt.' }}
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
 private_unchanged=($env:STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY -ceq 'synthetic-private-old-key');
 parent_unchanged=($env:GROQ_API_KEY -ceq 'synthetic-private-old-key');
 source_unchanged={expected_source};
 unrelated_unchanged=($env:OTHER_PROVIDER_KEY -ceq 'synthetic-unrelated-key');
 prompted=$global:sourceDialogueResponseTestPromptCount; protected_prompt=$global:sourceDialogueResponseTestProtectedPrompt}}
[System.IO.File]::WriteAllText({_ps(report)},($result | ConvertTo-Json))
exit 0
"""
    completed = _run(shell, command, project, temp)
    assert completed.returncode == 0 and completed.stderr == "", completed.stdout + completed.stderr
    result = json.loads(report.read_text(encoding="utf-8-sig"))
    assert result["private_unchanged"] and result["source_unchanged"] and result["parent_unchanged"] and result["unrelated_unchanged"]
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


def test_supplied_secure_string_is_preserved_and_only_live_child_receives_a_copy(shell, tmp_path):
    result, calls = launch(shell, tmp_path)
    assert result["exit_code"] == 0 and result["prompted"] == 0
    assert [call["args"][0] for call in calls] == ["--preflight", "--live", "--verify-artifacts"]
    assert [call["private_present"] for call in calls] == [False, True, False]
    assert calls[1]["private_correct"]


@pytest.mark.parametrize("credential", ["blank", "null", "disposed"])
def test_invalid_supplied_credential_stops_without_prompt_or_live(shell, tmp_path, credential):
    result, calls = launch(shell, tmp_path, credential=credential)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("provided", [False, True])
def test_preflight_never_requests_or_copies_a_key(shell, tmp_path, provided):
    result, calls = launch(shell, tmp_path, provided=provided, credential="disposed", preflight=True)
    assert result["exit_code"] == 0 and result["prompted"] == 0 and len(calls) == 1


def test_default_secure_prompt_follows_verified_preflight(shell, tmp_path):
    result, calls = launch(shell, tmp_path, provided=False)
    assert result["exit_code"] == 0 and result["prompted"] == 1 and result["protected_prompt"]
    assert calls[1]["private_correct"] and not calls[-1]["private_present"]


@pytest.mark.parametrize("change", [
    ("purpose", "old"), ("max_calls", 4), ("max_calls", True), ("synthetic_only", "true"),
    ("campaign_data_eligible", True), ("target.model", "other"), ("target.provider", "OpenRouter"),
    ("generation_parameters.reasoning_effort", "low"), ("generation_parameters.max_total_output_tokens", 2305),
    ("generation_parameters.max_output_tokens", 769), ("generation_parameters.temperature", 1),
    ("generation_parameters.initial_quiet_seconds", 0), ("generation_parameters.minimum_inter_call_delay_seconds", 0),
    ("generation_parameters.deadline_seconds", 61), ("slots.2.case_id", "direct-question"),
    ("inputs.corpus.sha256", "0" * 64), ("inputs.protocol.sha256", "0" * 64),
    ("inputs.manifest.sha256", "0" * 64), ("inputs.prompt.file_sha256", "0" * 64),
    ("inputs.implementation.1.sha256", "0" * 64), ("inputs.implementation.1.file", "../outside.py"),
    ("generation_parameters.max_calls", 4), ("slots.1.slot_id", "slot-1"),
    ("frozen_requests.1.case_id", "direct-question"), ("frozen_requests.0.npc_aliases", []),
    ("frozen_requests.0.user_packet_sha256", "0" * 64),
    ("frozen_requests.0.request.messages.1.content", "different user"),
    ("frozen_requests.0.request.messages.0.content", "different system"),
    ("frozen_requests.0.request.max_completion_tokens", 769),
    ("frozen_requests.0.request.response_format.json_schema.strict", False),
    ("frozen_requests.0.authored_source.application_commit", True),
    ("frozen_requests.0.authored_source.provider_evidence", {"synthetic": True}),
    ("inputs.prompt.version", "old"), ("inputs.response_schema_sha256", "invalid"),

])
def test_changed_contract_rejected_before_prompt(shell, tmp_path, change):
    result, calls = launch(shell, tmp_path, provided=False, change=change)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("mode", ["preflight_self_drift", "preflight_launcher_drift", "preflight_malformed", "preflight_noisy"])
def test_preflight_drift_and_invalid_output_fail_before_key(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, provided=False, mode=mode)
    assert result["exit_code"] == 3 and result["prompted"] == 0 and len(calls) == 1


@pytest.mark.parametrize("prompt_drift", ["scripts/evaluate_source_dialogue_response.py", "scripts/run_groq_source_dialogue_response.ps1",
    "api/synthetic_contract.py", *INPUT_FILES, *EXTRA_FILES, "preflight"])
def test_frozen_files_changed_during_prompt_cannot_start_live(shell, tmp_path, prompt_drift):
    result, calls = launch(shell, tmp_path, provided=False, prompt_drift=prompt_drift)
    assert result["exit_code"] == 3 and result["prompted"] == 1 and len(calls) == 1


@pytest.mark.parametrize("mode", ["summary_absent", "live_implementation_drift", "live_launcher_drift"])
def test_live_artifact_absence_or_code_drift_prevents_verifier(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3
    assert [call["args"][0] for call in calls] == ["--preflight", "--live"]


@pytest.mark.parametrize("mode", ["summary_incomplete", "summary_wrong_batch", "verifier_incomplete", "verifier_false",
    "verifier_boolean_exit", "verifier_wrong_batch", "verifier_wrong_path", "verifier_mutates_summary", "verifier_noisy", "verifier_failure"])
def test_false_incomplete_or_changed_verification_fails_closed(shell, tmp_path, mode):
    result, calls = launch(shell, tmp_path, mode=mode)
    assert result["exit_code"] == 3 and len(calls) == 3 and not calls[-1]["private_present"]


@pytest.mark.parametrize("code", [1, 2, 3, 130])
def test_valid_nonzero_observation_is_audited_without_destroying_supplied_key(shell, tmp_path, code):
    result, calls = launch(shell, tmp_path, code=code)
    assert result["exit_code"] == code and len(calls) == 3
    assert [call["private_present"] for call in calls] == [False, True, False]


def test_unknown_exit_code_cannot_be_certified(shell, tmp_path):
    result, calls = launch(shell, tmp_path, code=17)
    assert result["exit_code"] == 3 and len(calls) == 2


def test_launcher_parses_and_has_typed_secure_object_copy_without_parent_environment_mutation(shell, tmp_path):
    command = f"""
$tokens=$null
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile({_ps(RUNNER)},[ref]$tokens,[ref]$errors)
if (@($errors).Count -ne 0) {{ exit 1 }}
$parameter=$ast.ParamBlock.Parameters | Where-Object {{ $_.Name.VariablePath.UserPath -eq 'Credential' }}
if ($parameter.StaticType -ne [System.Security.SecureString]) {{ exit 2 }}
exit 0
"""
    result = _run(shell, command, ROOT, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    source = RUNNER.read_text(encoding="utf-8")
    assert "$Credential.Copy()" in source and "$Credential.Dispose()" not in source
    assert "$secureCredentialCopy.Dispose()" in source
    assert "$env:STORYTELLER_SOURCE_DIALOGUE_RESPONSE_GROQ_KEY" not in source


def test_host_interruption_closes_only_the_owned_live_child_and_preserves_caller_credential(shell, tmp_path):
    result, calls = launch(shell, tmp_path, mode="host_interruption")
    assert result["exit_code"] == 3 and len(calls) == 2 and result["prompted"] == 0
    child = json.loads((tmp_path / "project/waiting-child.json").read_text())
    started = json.loads((tmp_path / "project/started-child.json").read_text(encoding="utf-8-sig"))
    # The actual venv stub and evaluator worker are the provider-capable path.
    # This does not promise termination of arbitrary worker trees or abrupt host death.
    assert started["pid"] != child["pid"], "The native venv stub/worker boundary was not exercised."
    owned_ids = str(started["pid"]) + "," + str(child["pid"])
    try:
        check = _run(shell, "$until=[DateTime]::UtcNow.AddSeconds(3); do { $remaining=@(Get-Process -Id " + owned_ids + " -ErrorAction SilentlyContinue); if (-not $remaining.Count) { exit 0 }; Start-Sleep -Milliseconds 25 } while ([DateTime]::UtcNow -lt $until); $remaining.Id | ConvertTo-Json; exit 1", ROOT, tmp_path)
        assert check.returncode == 0 and check.stderr == "", "Owned venv stub/evaluator survived host interruption: " + check.stdout
    finally:
        cleanup = _run(shell, "Get-Process -Id " + owned_ids + " -ErrorAction SilentlyContinue | Stop-Process -Force; exit 0", ROOT, tmp_path)
        assert cleanup.returncode == 0
