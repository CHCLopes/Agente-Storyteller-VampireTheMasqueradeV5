"""Native-shell boundaries for a retained, synthetic source observation."""

from datetime import datetime, timedelta
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
RUNNER = ROOT / 'scripts/run_groq_source_context_probe.ps1'
EVALUATOR = 'scripts/evaluate_source_context.py'
PRIVATE_KEY = 'STORYTELLER_CONTEXT_GROQ_KEY'
SENTINELS = ('synthetic-new-key', 'synthetic-private-old-key',
             'synthetic-unrelated-key', 'synthetic-provider-error')
SHELLS = [path for name in ('pwsh', 'powershell') if (path := shutil.which(name))]


def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def _run(shell, command, cwd, temp):
    names = ('SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC',
             'USERPROFILE', 'LOCALAPPDATA', 'APPDATA')
    env = {name: os.environ[name] for name in names if name in os.environ}
    env.update(TEMP=str(temp), TMP=str(temp), STORYTELLER_DISABLE_DOTENV='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    return subprocess.run([shell, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', command],
                          cwd=cwd, env=env, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=30)


@pytest.fixture
def shell(tmp_path):
    selected = shutil.which('pwsh')
    if selected is None:
        pytest.skip('PowerShell 7 unavailable')
    policy = _run(selected, 'Get-ExecutionPolicy', ROOT, tmp_path)
    if policy.returncode or policy.stdout.strip() in {'Restricted', 'AllSigned'}:
        pytest.skip('Host policy prevents execution; no policy bypass')
    return selected


NATIVE = r'''
import hashlib,json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
mode=config['mode'];code=config['code'];args=sys.argv[1:]
def arg(name):return args[args.index(name)+1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
ledger=root/'calls.json'
calls=json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({'args':args,'private_present':'STORYTELLER_CONTEXT_GROQ_KEY' in os.environ,
              'private_correct':os.environ.get('STORYTELLER_CONTEXT_GROQ_KEY')=='synthetic-new-key',
              'unrelated_absent':'GROQ_API_KEY' not in os.environ and 'OTHER_PROVIDER_KEY' not in os.environ,
              'dotenv_off':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1',
              'bytecode_off':os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'})
ledger.write_text(json.dumps(calls),encoding='utf-8')
assert calls[-1]['unrelated_absent'] and calls[-1]['dotenv_off'] and calls[-1]['bytecode_off']
def noise():
 print('synthetic-provider-error');print('synthetic-provider-error',file=sys.stderr)
def metadata():
 return {'purpose':'source_context_probe','probe_kind':'source_context_probe',
  'experiment_version':'source-context-observation-v1','protocol':'narrative-source-application-v1',
  'selected_candidate_id':'qwen-3.8-27b-groq-free-synthetic-nonthink','max_calls':2,
  'synthetic_only':True,'campaign_data_eligible':False,'cap_001_approved':False,'runtime_default_eligible':False,
  'generation_parameters':{'temperature':.65,'max_output_tokens':768,'reasoning_effort':'none',
   'max_total_output_tokens':1536,'initial_quiet_seconds':60,'minimum_inter_call_delay_seconds':60,'deadline_seconds':60},
  'inputs':{'case':{'case_id':'synthetic-case','data':{'location':'Galeria iluminada à noite'}},
   'implementation':[{'file':'scripts/evaluate_source_context.py','sha256':sha(Path(__file__))}]}}
if args==['--preflight']:
 assert not calls[-1]['private_present']
 if mode in ('preflight_failure','preflight_malformed'):
  noise();sys.exit(3 if mode=='preflight_failure' else 0)
 doc=metadata()
 if config['change']:
  path,value=config['change'];node=doc
  for key in path.split('.')[:-1]:node=node[key]
  node[path.split('.')[-1]]=value
 if mode=='preflight_self_drift':
  with Path(__file__).open('a') as f:f.write('\n# changed\n')
 print(json.dumps(doc,ensure_ascii=False));sys.exit(0)
expected_path=Path(arg('--expected-preflight'))
assert sha(expected_path)==arg('--expected-preflight-sha256')
assert json.loads(expected_path.read_text(encoding='utf-8'))==metadata()
batch=arg('--batch-id')
binding=json.loads(expected_path.with_name('binding.json').read_text())
assert binding['batch_id']==batch and binding['preflight_sha256']==sha(expected_path)
lifecycle=json.loads(expected_path.with_name('lifecycle.json').read_text())
assert lifecycle['batch_id']==batch and lifecycle['exit_code'] is None
run=root/'eval-results'/('source-context-'+batch)
summary=run/'summary.json'
if args[0]=='--live':
 assert '--allow-synthetic-only' in args and arg('--api-key-env')=='STORYTELLER_CONTEXT_GROQ_KEY'
 assert calls[-1]['private_correct'] and lifecycle['status']=='running'
 if mode=='wait_for_interrupt':
  (root/'waiting-child.json').write_text(json.dumps({'pid':os.getpid()}))
  time.sleep(120)
 run.mkdir()
 (run/'records.jsonl').write_text('{}\n');(run/'retained-source.sqlite3').write_bytes(b'synthetic database stand-in')
 doc={'batch_id':batch,'process_exit_code':code}
 if mode=='summary_wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
 if mode=='summary_boolean_exit':doc['process_exit_code']=False
 if mode!='summary_absent':summary.write_text(json.dumps(doc))
 noise();sys.exit(code)
assert args[0]=='--verify-artifacts' and Path(arg('--verify-artifacts'))==summary
assert not calls[-1]['private_present'] and lifecycle['status']=='verifying_artifacts'
if mode in ('verifier_failure','verifier_noisy'):
 noise();sys.exit(3 if mode=='verifier_failure' else 0)
doc={'verified':True,'summary_path':str(summary),'process_exit_code':code,'batch_id':batch}
if mode=='verifier_false':doc['verified']=False
if mode=='verifier_wrong_batch':doc['batch_id']='00000000-0000-0000-0000-000000000000'
if mode=='verifier_wrong_exit':doc['process_exit_code']=2 if code==0 else 0
if mode=='verifier_boolean_exit':doc['process_exit_code']=False
if mode=='verifier_wrong_path':doc['summary_path']=str(root/'eval-results/old/summary.json')
if mode=='verifier_mutates_summary':summary.write_text(summary.read_text()+' ')
print(json.dumps(doc))
'''


def _wrapper(shell, tmp_path, *, mode='normal', code=0, change=None, preflight_only=False):
    project = tmp_path / 'isolated project'
    runner = project / RUNNER.relative_to(ROOT)
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding='utf-8-sig')
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source=source.replace(assignment, '$python = ' + _ps(sys.executable))
    if mode=='lifecycle_final_failure':
        anchor="    if ($null -eq $lifecyclePath) { return }"
        assert source.count(anchor)==1
        source=source.replace(anchor,anchor+"\n    if ($Status -ceq 'finished') { throw 'synthetic-provider-error' }")
    if mode=='wait_for_interrupt':
        anchor='        $stdout = $process.StandardOutput.ReadToEndAsync()'
        assert source.count(anchor)==1
        # Inject a host failure only after this owned child has actually started.
        source=source.replace(anchor, '''        if ($WithCredential) {
            $ready=Join-Path $projectRoot 'waiting-child.json'
            $until=[DateTime]::UtcNow.AddSeconds(8)
            while (-not (Test-Path -LiteralPath $ready) -and [DateTime]::UtcNow -lt $until) { Start-Sleep -Milliseconds 25 }
            throw 'synthetic-provider-error'
        }
''' + anchor)
    runner.write_text(source, encoding='utf-8')
    (project / EVALUATOR).write_text(NATIVE, encoding='utf-8')
    (project / 'config.json').write_text(json.dumps({'mode':mode,'code':code,'change':change}),encoding='utf-8')
    old = project / 'eval-results/old/summary.json'
    old.parent.mkdir(parents=True)
    old.write_text('unrelated historical evidence')
    result_path = project / 'harness.json'
    prompt_path = project / 'prompt.json'
    temp = tmp_path / 'private temp'
    temp.mkdir()
    options = ' -PreflightOnly' if preflight_only else ''
    command = f'''
$ErrorActionPreference='Stop'
$env:GROQ_API_KEY='synthetic-unrelated-key'
$env:OTHER_PROVIDER_KEY='synthetic-unrelated-key'
$env:STORYTELLER_CONTEXT_GROQ_KEY='synthetic-private-old-key'
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 if (-not $AsSecureString) {{ throw 'Unprotected prompt' }}
 $paths=@(Get-ChildItem -LiteralPath {_ps(temp)} -Recurse -Filter lifecycle.json)
 if ($paths.Count -ne 1) {{ throw 'Missing preflight lifecycle' }}
 $state=Get-Content -Raw -LiteralPath $paths[0].FullName | ConvertFrom-Json
 if ($state.status -cne 'awaiting_secure_credential') {{ throw 'Prompt before verified preflight' }}
 [System.IO.File]::WriteAllText({_ps(prompt_path)},'{{"protected":true}}')
 if ({_ps(mode)} -eq 'prompt_preflight_drift') {{
  [System.IO.File]::AppendAllText((Join-Path $paths[0].DirectoryName 'preflight.json'),' ')
 }}
 if ({_ps(mode)} -eq 'prompt_evaluator_drift') {{
  [System.IO.File]::AppendAllText({_ps(project / EVALUATOR)},"`n# changed at prompt`n")
 }}
 if ({_ps(mode)} -eq 'run_collision') {{
  [System.IO.Directory]::CreateDirectory((Join-Path {_ps(project / 'eval-results')} ('source-context-'+$state.batch_id))) | Out-Null
 }}
 if ({_ps(mode)} -eq 'blank_key') {{ return [System.Security.SecureString]::new() }}
 return (ConvertTo-SecureString 'synthetic-new-key' -AsPlainText -Force)
}}
& {_ps(runner)}{options}
$result=@{{exit_code=$LASTEXITCODE; private_absent=(-not (Test-Path Env:STORYTELLER_CONTEXT_GROQ_KEY)); unrelated_unchanged=($env:GROQ_API_KEY -eq 'synthetic-unrelated-key' -and $env:OTHER_PROVIDER_KEY -eq 'synthetic-unrelated-key')}}
[System.IO.File]::WriteAllText({_ps(result_path)},($result | ConvertTo-Json))
exit 0
'''
    completed = _run(shell, command, project, temp)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == ''
    assert not any(value in completed.stdout for value in SENTINELS)
    result = json.loads(result_path.read_text(encoding='utf-8-sig'))
    assert result['private_absent'] is result['unrelated_unchanged'] is True
    batch = next(line.split(': ',1)[1] for line in completed.stdout.splitlines()
                 if line.startswith('Source context probe batch: '))
    assert str(UUID(batch)) == batch
    evidence = temp / ('storyteller-source-context-window-' + batch)
    if evidence.exists():
        lifecycle = json.loads((evidence/'lifecycle.json').read_text(encoding='utf-8-sig'))
        assert set(lifecycle)=={'batch_id','status','updated_at','exit_code'}
        assert lifecycle['batch_id']==batch
        if mode=='lifecycle_final_failure':
            # The last valid record remains; host output still fails closed.
            assert lifecycle['status']=='verifying_artifacts' and lifecycle['exit_code'] is None
        else:
            assert type(lifecycle['exit_code']) is int and lifecycle['exit_code']==result['exit_code']
            assert lifecycle['status']==('preflight_only_completed' if preflight_only and result['exit_code']==0 else 'finished')
        assert datetime.fromisoformat(lifecycle['updated_at'].replace('Z','+00:00')).utcoffset()==timedelta(0)
        binding=json.loads((evidence/'binding.json').read_text(encoding='utf-8-sig'))
        assert binding['batch_id']==batch
        for path in evidence.iterdir():
            assert not any(value in path.read_text(encoding='utf-8-sig') for value in SENTINELS)
    assert old.read_text()=='unrelated historical evidence'
    calls=json.loads((project/'calls.json').read_text())
    assert calls[0]['args']==['--preflight'] and calls[0]['private_present'] is False
    assert all(c['unrelated_absent'] and c['dotenv_off'] and c['bytecode_off'] for c in calls)
    return result,calls,prompt_path.exists(),completed.stdout,evidence


@pytest.mark.parametrize('available_shell',SHELLS or [None],ids=lambda p:Path(p).stem if p else 'unavailable')
def test_source_context_wrapper_parses_without_policy_bypass(available_shell,tmp_path):
    if available_shell is None:pytest.skip('PowerShell unavailable')
    command='$tokens=$null; $errors=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('+_ps(RUNNER)+',[ref]$tokens,[ref]$errors); if ($errors.Count) { exit 1 }'
    result=_run(available_shell,command,tmp_path,tmp_path)
    assert result.returncode==0,result.stdout+result.stderr


def test_preflight_only_never_prompts_or_starts_live(shell,tmp_path):
    result,calls,prompted,output,evidence=_wrapper(shell,tmp_path,preflight_only=True)
    assert result['exit_code']==0 and len(calls)==1 and not prompted,output
    binding=json.loads((evidence/'binding.json').read_text())
    assert binding['preflight_sha256']==hashlib.sha256((evidence/'preflight.json').read_bytes()).hexdigest()
    assert 'remain unapproved' in output
    assert 'Two independent synthetic conditions' in output
    assert 'Content rejection may continue; technical failure stops' in output
    assert 'No campaign, SQLite or application commit is created' in output


@pytest.mark.parametrize('mode',['preflight_failure','preflight_malformed','preflight_self_drift'])
def test_preflight_failure_or_drift_prevents_key_entry(shell,tmp_path,mode):
    result,calls,prompted,output,evidence=_wrapper(shell,tmp_path,mode=mode)
    assert result['exit_code']==3 and len(calls)==1 and not prompted,output
    assert not evidence.exists()


@pytest.mark.parametrize('change',[
    ('purpose','old_probe'),('protocol','narrative-source-profile-v1'),
    ('max_calls',True),('cap_001_approved',0),
    ('generation_parameters.max_output_tokens',3072),
    ('generation_parameters.temperature','0.65'),
    ('generation_parameters.reasoning_effort','low'),
],ids=lambda value:value[0])
def test_preflight_identity_types_and_limits_fail_before_key(shell,tmp_path,change):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,change=change)
    assert result['exit_code']==3 and len(calls)==1 and not prompted,output


@pytest.mark.parametrize('mode',['blank_key','prompt_preflight_drift','prompt_evaluator_drift','run_collision'])
def test_protected_prompt_cannot_bypass_blank_key_integrity_or_exclusivity(shell,tmp_path,mode):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,mode=mode)
    assert result['exit_code']==3 and len(calls)==1 and prompted,output


@pytest.mark.parametrize('code',[0,1,2,3,130])
def test_single_child_and_keyless_verifier_preserve_operational_exit(shell,tmp_path,code):
    result,calls,prompted,output,evidence=_wrapper(shell,tmp_path,code=code)
    assert result['exit_code']==code and len(calls)==3 and prompted,output
    assert calls[1]['private_correct'] is True and calls[2]['private_present'] is False
    binding=json.loads((evidence/'binding.json').read_text())
    for call in calls[1:]:
        args=call['args']
        assert args[args.index('--batch-id')+1]==binding['batch_id']
        assert args[args.index('--expected-preflight-sha256')+1]==binding['preflight_sha256']
        assert args[args.index('--expected-preflight')+1]==str(evidence/'preflight.json')
    assert calls[1]['args'][0]=='--live' and calls[2]['args'][0]=='--verify-artifacts'


@pytest.mark.parametrize('mode',[
    'summary_absent','summary_wrong_batch','summary_boolean_exit','verifier_failure',
    'verifier_noisy','verifier_false','verifier_wrong_batch','verifier_wrong_exit',
    'verifier_boolean_exit','verifier_wrong_path','verifier_mutates_summary',
])
def test_child_success_does_not_override_missing_or_inconsistent_verification(shell,tmp_path,mode):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,mode=mode)
    assert result['exit_code']==3 and prompted,output
    assert len(calls)==(2 if mode=='summary_absent' else 3)


def test_unrecognized_child_exit_fails_closed_without_verification(shell,tmp_path):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,code=7)
    assert result['exit_code']==3 and len(calls)==2 and prompted,output


def test_host_failure_after_start_terminates_only_owned_child(shell,tmp_path):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,mode='wait_for_interrupt')
    assert result['exit_code']==3 and len(calls)==2 and prompted,output
    child=json.loads((tmp_path/'isolated project/waiting-child.json').read_text())
    check=_run(shell, 'if (Get-Process -Id '+str(child['pid'])+' -ErrorAction SilentlyContinue) { exit 1 }', ROOT, tmp_path)
    assert check.returncode==0,check.stdout+check.stderr


def test_lifecycle_write_failure_exposes_only_fixed_message(shell,tmp_path):
    result,calls,prompted,output,_=_wrapper(shell,tmp_path,mode='lifecycle_final_failure')
    assert result['exit_code']==3 and len(calls)==3 and prompted,output
    assert 'stopped during lifecycle finalization' in output


WRAPPER_TRANSFORM = [('evaluate_progressing_source.py', 'evaluate_source_context.py'), ('progressing_source_probe', 'source_context_probe'), ('progressing-source-observation-v1', 'source-context-observation-v1'), ('progressing-source-', 'source-context-'), ('STORYTELLER_PROGRESSING_GROQ_KEY', 'STORYTELLER_CONTEXT_GROQ_KEY'), ('Progressing source probe', 'Source context probe'), ('Two dependent synthetic turns;', 'Two independent synthetic conditions;'), ('First failure stops the chain; no retry, repair, diagnostics or fallback.', 'Content rejection may continue; technical failure stops the remaining condition. No retry, repair or fallback.'), ('try {\n    Remove-Item Env:STORYTELLER_CONTEXT_GROQ_KEY', "Write-Host 'No campaign, SQLite or application commit is created. Authored synthetic sources have no provider provenance.'\ntry {\n    Remove-Item Env:STORYTELLER_CONTEXT_GROQ_KEY")]

def test_context_wrapper_has_only_closed_identity_and_scope_message_changes():
    baseline=(ROOT/'scripts/run_groq_progressing_source_probe.ps1').read_bytes()
    assert hashlib.sha256(baseline).hexdigest()=='37ad487e156ea96d5815f15302e6184beff3190611f3c9d559ae26c223b0a267'
    expected=baseline.decode('utf-8')
    for old,new in WRAPPER_TRANSFORM:
        assert old in expected
        expected=expected.replace(old,new)
    assert RUNNER.read_bytes()==expected.encode('utf-8')
