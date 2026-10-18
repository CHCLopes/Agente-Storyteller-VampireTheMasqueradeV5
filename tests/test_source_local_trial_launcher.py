"""Native launcher checks with synthetic Python/Vite children and no sockets.

The sole launcher substitution selects the test Python interpreter. A synthetic
Vite module exercises the real fixed Node control program without opening ports.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from test_retained_source_probe_wrapper import _ps, _run, shell

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'scripts/run_groq_source_local_trial.ps1'
PRIVATE = 'STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY'
SENTINELS = ('synthetic-new-key', 'synthetic-parent-key', 'synthetic-provider-error')

BACKEND = r'''
import hashlib,json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
config=json.loads((root/'config.json').read_text())
mode=config['mode']
def arg(name):return args[args.index(name)+1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
run_id=arg('--run-id');session='source-groq-trial.'+run_id
run=root/'eval-results'/('source-local-groq-trial-'+run_id)
status_dir=Path(os.environ['TEMP'])/('storyteller-source-local-groq-trial-'+run_id)
paths={'run_directory':str(run),'database':str(run/'storyteller.sqlite3'),
    'status_directory':str(status_dir),'status_file':str(status_dir/'status.json'),
    'frontend_url':'http://127.0.0.1:5178/source-player-trial.html?backendPort=8018&session='+session,
    'websocket_url':'ws://127.0.0.1:8018/ws/source-local/'+session}
ledger=root/'calls.json'
calls=json.loads(ledger.read_text()) if ledger.exists() else []
private='STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY'
calls.append({'args':args,'private_present':private in os.environ,
    'private_correct':os.environ.get(private)=='synthetic-new-key',
    'parent_absent':'GROQ_API_KEY' not in os.environ and 'OTHER_PROVIDER_KEY' not in os.environ,
    'dotenv_off':os.environ.get('STORYTELLER_DISABLE_DOTENV')=='1',
    'bytecode_off':os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'})
ledger.write_text(json.dumps(calls))
assert calls[-1]['parent_absent'] and calls[-1]['dotenv_off'] and calls[-1]['bytecode_off']
def metadata():
 files=['scripts/run_source_local_groq_trial.py','api/synthetic_contract.py',
     'client/vite.source-player-trial.config.ts','client/source-player-trial.html','client/src/index.css']
 prompt='evals/narrator/prompts/narrative-source-progress-v1.md'
 return {'status':'preflight_passed','purpose':'source_local_groq_trial','protocol':'source-local-groq-trial-v1',
    'profile':'narrative-source-application-v1','run_id':run_id,'session_id':session,
    'synthetic_only':True,'cap_001_approved':False,'runtime_default_eligible':False,
    'target':{'profile':'source-local-groq-trial-qwen-3.8-27b-groq-free-synthetic-nonthink','provider':'Groq','model':'qwen/qwen3.8-27b'},
    'backend_port':8018,'origin_port':5178,'expected_origin':'http://127.0.0.1:5178','expected_host':'127.0.0.1:8018',
    'generation_parameters':{'max_output_tokens':768,'temperature':.65,'reasoning_effort':'none'},
    'budget':{'max_calls':4,'max_total_output_tokens':3072,'initial_quiet_seconds':60,'minimum_inter_call_delay_seconds':60,'deadline_seconds':60},
    'paths':paths,'prompt':{'file':prompt,'file_sha256':sha(root/prompt),'sha256':'0'*64,'version':'narrative-source-progress-v1'},
    'inputs':[{'file':f,'sha256':sha(root/f)} for f in files]}
if '--preflight-only' in args:
 assert not calls[-1]['private_present']
 doc=metadata()
 if config['change']:
  path,value=config['change'];node=doc
  for part in path.split('.')[:-1]:node=node[int(part)] if isinstance(node,list) else node[part]
  part=path.split('.')[-1]
  if isinstance(node,list):node[int(part)]=value
  else:node[part]=value
 if mode=='preflight_drift':
  with (root/'api/synthetic_contract.py').open('a') as output:output.write('#changed')
 if mode=='preflight_bad_json':print('not json');sys.exit(0)
 if mode=='preflight_noisy':print('synthetic-provider-error',file=sys.stderr)
 print(json.dumps(doc));sys.exit(0)
assert '--live' in args and '--allow-synthetic-only' in args and '--managed-stdin-stop' in args
assert arg('--api-key-env')==private and calls[-1]['private_correct']
expected=Path(arg('--expected-preflight'))
assert sha(expected)==arg('--expected-preflight-sha256') and json.loads(expected.read_text())==metadata()
binding=json.loads(expected.with_name('binding.json').read_text())
assert binding['run_id']==run_id and binding['session_id']==session and binding['preflight_sha256']==sha(expected)
assert json.loads(expected.with_name('lifecycle.json').read_text())['status']=='starting'
run.mkdir(parents=True);status_dir.mkdir()
(run/'storyteller.sqlite3').write_bytes(b'synthetic stand-in, not SQLite')
def state(status):
 doc={'protocol':'source-local-groq-trial-v1','purpose':'source_local_groq_trial','run_id':run_id,
    'session_id':session,'status':status,'pid':os.getpid(),'paths':paths}
 if mode=='status_wrong_identity':doc['session_id']='other'
 if mode=='status_wrong_path':doc['paths']={**paths,'database':str(root/'other.sqlite3')}
 (status_dir/'status.json').write_text(json.dumps(doc))
state('running')
(root/'backend-ready.json').write_text(json.dumps({'pid':os.getpid(),'parent_pid':os.getppid()}))
print('synthetic-new-key synthetic-provider-error',flush=True)
print('synthetic-new-key synthetic-provider-error',file=sys.stderr,flush=True)
if mode=='backend_ignore_stop':time.sleep(120)
elif mode in ('frontend_exit','status_wrong_identity','status_wrong_path','backend_fail','live_drift'):
 line=sys.stdin.readline()
 (root/'backend-stop.json').write_text(json.dumps({'stop_received':line=='stop\n','eof':line==''}))
else:time.sleep(1.8)
if mode=='live_drift':
 with (root/'api/synthetic_contract.py').open('a') as output:output.write('#changed')
state('failed' if mode=='backend_fail' else 'stopped')
sys.exit(3 if mode=='backend_fail' else 0)
'''

VITE = r'''
import fs from 'node:fs';
import path from 'node:path';
const root=path.dirname(process.cwd());
const config=JSON.parse(fs.readFileSync(path.join(root,'config.json'),'utf8'));
const ready=path.join(root,'frontend-ready.json');
const env={private_absent:!('STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY' in process.env),
  parent_absent:!('GROQ_API_KEY' in process.env)&&!('OTHER_PROVIDER_KEY' in process.env),
  dotenv_off:process.env.STORYTELLER_DISABLE_DOTENV==='1'};
fs.writeFileSync(path.join(root,'frontend-env.json'),JSON.stringify(env));
if(!Object.values(env).every(Boolean))throw Error('isolated env');
let ticker;
export async function createServer(options){
 if(options.server.host!=='127.0.0.1'||options.server.port!==5178||!options.server.strictPort)throw Error('server options');
 return {
  async listen(){
   ticker=setInterval(()=>{},1000);
   fs.writeFileSync(ready,JSON.stringify({pid:process.pid}));
   if(['frontend_exit','backend_ignore_stop','backend_fail','live_drift'].includes(config.mode))setTimeout(()=>process.exit(7),650);
   process.stdout.write('synthetic-provider-error\n');
   process.stderr.write('synthetic-provider-error\n');
  },
  async close(){
   clearInterval(ticker);
   fs.writeFileSync(path.join(root,'frontend-close.json'),JSON.stringify({closed:true}));
  }
 };
}
'''

def fixture_project(tmp_path, mode='normal', change=None):
    project=tmp_path/'p'
    runner=project/'scripts/run_groq_source_local_trial.ps1'
    runner.parent.mkdir(parents=True)
    source=LAUNCHER.read_text(encoding='utf-8-sig')
    anchor='$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(anchor)==1
    runner.write_text(source.replace(anchor,'$python = '+_ps(sys.executable)),encoding='utf-8')
    (runner.parent/'run_source_local_groq_trial.py').write_text(BACKEND,encoding='utf-8')
    for file in ('api/synthetic_contract.py','client/vite.source-player-trial.config.ts',
                 'client/source-player-trial.html','client/src/index.css','evals/narrator/prompts/narrative-source-progress-v1.md',
                 'client/node_modules/vite/bin/vite.js'):
        item=project/file
        item.parent.mkdir(parents=True,exist_ok=True)
        item.write_text('# synthetic frozen source\n',encoding='utf-8')
    module=project/'client/node_modules/vite'
    (module/'dist/node').mkdir(parents=True)
    (module/'dist/node/index.js').write_text(VITE,encoding='utf-8')
    (module/'package.json').write_text(json.dumps({'type':'module','exports':'./dist/node/index.js'}),encoding='utf-8')
    (project/'config.json').write_text(json.dumps({'mode':mode,'change':change}),encoding='utf-8')
    private=tmp_path/'t'
    private.mkdir()
    return project,runner,private

def launch(shell,tmp_path,*,mode='normal',change=None,preflight=False,provided=True,credential='present',prompt_drift=None):
    project,runner,private=fixture_project(tmp_path,mode,change)
    report=project/'report.json'
    secret=' ' if credential=='blank' else 'synthetic-new-key'
    if credential=='null':
        key_command='$StorytellerGroqKey=$null'
        source_unchanged='($null -eq $StorytellerGroqKey)'
    else:
        key_command='$StorytellerGroqKey=ConvertTo-SecureString '+_ps(secret)+' -AsPlainText -Force'
        source_unchanged='([Net.NetworkCredential]::new("",$StorytellerGroqKey).Password -ceq '+_ps(secret)+')'
        if credential=='disposed':
            key_command+='\n$StorytellerGroqKey.Dispose()'
            source_unchanged='$true'
    switches=(' -PreflightOnly' if preflight else '')+(' -Credential $StorytellerGroqKey' if provided else '')
    drift=''
    if prompt_drift:
        drift_path="(Join-Path $life[0].DirectoryName 'preflight.json')" if prompt_drift=='preflight' else _ps(project/prompt_drift)
        drift='[IO.File]::AppendAllText('+drift_path+",' ' )"
    command=f'''
$ErrorActionPreference='Stop'
{key_command}
$env:GROQ_API_KEY='synthetic-parent-key'
$env:OTHER_PROVIDER_KEY='synthetic-parent-key'
$env:STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY='synthetic-parent-key'
$global:trialPromptCount=0
$global:trialPortQueries=0
$global:protectedPrompt=$false
function Read-Host {{
 param([string]$Prompt,[switch]$AsSecureString)
 $global:trialPromptCount+=1
 $global:protectedPrompt=[bool]$AsSecureString
 if (-not $AsSecureString -or {'$true' if provided or preflight else '$false'}) {{ throw 'Unexpected prompt' }}
 $life=@(Get-ChildItem -LiteralPath {_ps(private)} -Recurse -Filter lifecycle.json)
 if ($life.Count -ne 1) {{ throw 'Missing preflight' }}
 if ((Get-Content -LiteralPath $life[0].FullName -Raw | ConvertFrom-Json).status -cne 'awaiting_secure_credential') {{ throw 'Prompt before preflight' }}
 {drift}
 return (ConvertTo-SecureString 'synthetic-new-key' -AsPlainText -Force)
}}
function Get-NetTCPConnection {{
 param($LocalPort,$State,$ErrorAction)
 $global:trialPortQueries+=1
 if ({'$true' if mode=='port_occupied' else '$false'}) {{ return [pscustomobject]@{{LocalAddress='127.0.0.1';OwningProcess=1}} }}
 $file=if($LocalPort -eq 8018){{{_ps(project/'backend-ready.json')}}}else{{{_ps(project/'frontend-ready.json')}}}
 if (Test-Path -LiteralPath $file) {{
  $pidData=Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
  return [pscustomobject]@{{LocalAddress='127.0.0.1';OwningProcess=$pidData.pid}}
 }}
}}
function Get-CimInstance {{
 param($ClassName,$Filter,$Property,$ErrorAction)
 $known=Get-Content -LiteralPath {_ps(project/'backend-ready.json')} -Raw | ConvertFrom-Json
 if($Filter -ceq ('ProcessId = '+$known.pid+' AND ParentProcessId = '+$known.parent_pid)) {{
  return [pscustomobject]@{{Name='python.exe';ProcessId=$known.pid;ParentProcessId=$known.parent_pid}}
 }}
 return $null
}}
& {_ps(runner)}{switches}
$taskSuccess=$?
$taskExit=$LASTEXITCODE
$record=@{{exit_code=$taskExit;command_success=$taskSuccess;source_unchanged={source_unchanged};
  parent_unchanged=($env:GROQ_API_KEY -ceq 'synthetic-parent-key');
  private_unchanged=($env:STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY -ceq 'synthetic-parent-key');
  other_unchanged=($env:OTHER_PROVIDER_KEY -ceq 'synthetic-parent-key');
  prompted=$global:trialPromptCount;protected_prompt=$global:protectedPrompt;port_queries=$global:trialPortQueries}}
[IO.File]::WriteAllText({_ps(report)},($record|ConvertTo-Json))
exit 0
'''
    completed=_run(shell,command,project,private)
    assert completed.returncode==0 and not completed.stderr,completed.stdout+completed.stderr
    result=json.loads(report.read_text(encoding='utf-8-sig'))
    assert all(result[k] for k in ('source_unchanged','parent_unchanged','private_unchanged','other_unchanged'))
    assert not any(x in completed.stdout for x in SENTINELS)
    calls=json.loads((project/'calls.json').read_text())
    assert '--preflight-only' in calls[0]['args'] and not calls[0]['private_present']
    assert all(c['parent_absent'] and c['dotenv_off'] and c['bytecode_off'] for c in calls)
    lifecycle=list(private.glob('storyteller-source-local-trial-window-*/lifecycle.json'))
    if lifecycle:
        assert len(lifecycle)==1
        life=json.loads(lifecycle[0].read_text(encoding='utf-8-sig'))
        assert life['exit_code']==result['exit_code']
        assert life['status']==('preflight_only_completed' if preflight and result['exit_code']==0 else 'stopped' if result['exit_code']==0 else 'failed')
        result['lifecycle']=life
    for ready in (project/'backend-ready.json',project/'frontend-ready.json'):
        if ready.exists():
            pid=json.loads(ready.read_text())['pid']
            probe=_run(shell,f'if(Get-Process -Id {pid} -ErrorAction SilentlyContinue){{exit 1}}else{{exit 0}}',project,private)
            assert probe.returncode==0,'Owned child survived launcher'
    for artifact in private.rglob('*.json'):
        assert not any(x in artifact.read_text(encoding='utf-8-sig') for x in SENTINELS)
    if (project/'frontend-env.json').exists():
        assert all(json.loads((project/'frontend-env.json').read_text()).values())
    return result,calls,project,private

@pytest.mark.parametrize('provided',[True,False])
def test_preflight_is_offline_and_ignores_key(shell,tmp_path,provided):
    result,calls,project,_=launch(shell,tmp_path,preflight=True,provided=provided,credential='disposed')
    assert result['exit_code']==0 and result['prompted']==0 and result['port_queries']==0
    assert len(calls)==1 and not (project/'eval-results').exists() and not (project/'frontend-env.json').exists()

@pytest.mark.parametrize('provided',[True,False])
def test_live_only_backend_gets_key_copy(shell,tmp_path,provided):
    result,calls,project,_=launch(shell,tmp_path,provided=provided)
    assert result['exit_code']==0 and len(calls)==2 and calls[1]['private_correct']
    assert result['prompted']==(0 if provided else 1)
    assert provided or result['protected_prompt']
    assert json.loads((project/'frontend-close.json').read_text())['closed']

@pytest.mark.parametrize('credential',['null','blank','disposed'])
def test_invalid_supplied_key_stops_safely(shell,tmp_path,credential):
    result,calls,_,_=launch(shell,tmp_path,credential=credential)
    assert result['exit_code']==3 and result['prompted']==0 and len(calls)==1

@pytest.mark.parametrize('change',[
    ('purpose','other'),('run_id','other'),('session_id','other'),('synthetic_only','true'),
    ('cap_001_approved',True),('runtime_default_eligible',True),('target.model','other'),
    ('target.provider','OpenRouter'),('backend_port',True),('origin_port',5179),
    ('expected_origin','http://0.0.0.0:5178'),('budget.max_calls',5),('budget.max_calls',True),
    ('budget.max_total_output_tokens',3073),('budget.initial_quiet_seconds',0),
    ('budget.minimum_inter_call_delay_seconds',0),('budget.deadline_seconds',61),
    ('generation_parameters.max_output_tokens',769),('generation_parameters.reasoning_effort','low'),
    ('paths.database','C:/outside.sqlite3'),('paths.frontend_url','http://other/'),
    ('inputs.1.file','../outside.py'),('inputs.1.file','api/.env'),('inputs.1.sha256','0'*64),
    ('prompt.file','evals/narrator/prompts/narrative-source-word-budget-v1.md'),
])
def test_invalid_freeze_stops_before_key(shell,tmp_path,change):
    result,calls,_,_=launch(shell,tmp_path,provided=False,change=change)
    assert result['exit_code']==3 and result['prompted']==0 and len(calls)==1

@pytest.mark.parametrize('mode',['preflight_drift','preflight_bad_json','preflight_noisy'])
def test_preflight_error_output_is_not_echoed(shell,tmp_path,mode):
    result,calls,_,_=launch(shell,tmp_path,mode=mode,provided=False)
    assert result['exit_code']==3 and result['prompted']==0 and len(calls)==1

@pytest.mark.parametrize('path',['preflight','scripts/run_groq_source_local_trial.ps1',
    'scripts/run_source_local_groq_trial.py','api/synthetic_contract.py','client/vite.source-player-trial.config.ts',
    'client/source-player-trial.html','client/src/index.css','client/node_modules/vite/dist/node/index.js',
    'evals/narrator/prompts/narrative-source-progress-v1.md'])
def test_prompt_drift_prevents_live(shell,tmp_path,path):
    result,calls,_,_=launch(shell,tmp_path,provided=False,prompt_drift=path)
    assert result['exit_code']==3 and result['prompted']==1 and len(calls)==1

def test_busy_port_does_not_touch_other_process(shell,tmp_path):
    result,calls,project,_=launch(shell,tmp_path,mode='port_occupied',provided=False)
    assert result['exit_code']==3 and result['prompted']==0 and len(calls)==1
    assert not (project/'backend-ready.json').exists()

@pytest.mark.parametrize('mode',['frontend_exit','status_wrong_identity','status_wrong_path','backend_fail','live_drift'])
def test_child_failure_stops_owned_children(shell,tmp_path,mode):
    result,calls,project,_=launch(shell,tmp_path,mode=mode)
    assert result['exit_code']==3 and len(calls)==2
    assert json.loads((project/'backend-stop.json').read_text())['stop_received']

def test_shutdown_fallback_owns_only_created_child(shell,tmp_path):
    helper=tmp_path/'sleep.py'
    helper.write_text('import time\ntime.sleep(120)\n',encoding='utf-8')
    command=f'''
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile({_ps(LAUNCHER)},[ref]$tokens,[ref]$errors)
$function=$ast.Find({{param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Stop-OwnedChild'}},$true)
Invoke-Expression $function.Extent.Text
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName={_ps(sys.executable)}
$info.UseShellExecute=$false
$info.CreateNoWindow=$true
$info.RedirectStandardInput=$true
$info.ArgumentList.Add('-B')
$info.ArgumentList.Add({_ps(helper)})
$info.Environment.Clear()
foreach($name in @('SYSTEMROOT','WINDIR','TEMP','TMP','PATH')){{
 $value=[Environment]::GetEnvironmentVariable($name,'Process')
 if($null -ne $value){{$info.Environment[$name]=$value}}
}}
$process=[Diagnostics.Process]::Start($info)
$owned=@{{process=$process;forced=$false}}
try{{
 Stop-OwnedChild $owned 'stop' 100
 if(-not $owned.forced -or -not $process.HasExited){{exit 1}}
}}finally{{if(-not $process.HasExited){{$process.Kill($true)}};$process.Dispose()}}
exit 0
'''
    result=_run(shell,command,ROOT,tmp_path)
    assert result.returncode==0 and not result.stderr

@pytest.mark.parametrize('stdin,code', [('stop\n',0),('',0),('malformed\n',3)])
def test_vite_control_channel_without_listener(shell,tmp_path,stdin,code):
    project,_,_=fixture_project(tmp_path)
    source=LAUNCHER.read_text(encoding='utf-8-sig')
    program=re.search(r"\$frontendProgram = @'\n(.*?)\n'@",source,re.S).group(1)
    node=shutil.which('node')
    assert node
    import os
    names=('SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','USERPROFILE','LOCALAPPDATA','APPDATA','TEMP','TMP')
    env={k:os.environ[k] for k in names if k in os.environ}
    env['STORYTELLER_DISABLE_DOTENV']='1'
    result=subprocess.run([node,'--input-type=module','--eval',program,'--',str(project/'client/vite.source-player-trial.config.ts')],
        cwd=project/'client',env=env,input=stdin,text=True,capture_output=True,timeout=10)
    assert result.returncode==code
    assert json.loads((project/'frontend-close.json').read_text())['closed']

def test_parser_and_safe_ownership_contract(shell,tmp_path):
    command=f'''
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile({_ps(LAUNCHER)},[ref]$tokens,[ref]$errors)
if(@($errors).Count){{exit 1}}
$key=$ast.ParamBlock.Parameters|Where-Object {{$_.Name.VariablePath.UserPath -eq 'Credential'}}
if($key.StaticType -ne [Security.SecureString]){{exit 2}}
exit 0
'''
    result=_run(shell,command,ROOT,tmp_path)
    assert result.returncode==0 and not result.stderr
    source=LAUNCHER.read_text(encoding='utf-8-sig')
    assert '$Credential.Copy()' in source and '$Credential.Dispose()' not in source
    assert '$env:'+PRIVATE not in source and 'Stop-Process' not in source and 'taskkill' not in source
    assert 'ReadToEndAsync()' in source and 'CopyToAsync([IO.Stream]::Null)' in source
