"""Keyless, network-free checks of explicitly authorized credential lifecycle."""
from datetime import datetime, timedelta, timezone
import json
import subprocess
from types import SimpleNamespace
import pytest
from scripts import luna_credential_supervisor as s


@pytest.fixture
def lease(tmp_path):
    gate = json.loads((s.ROOT / 'evals/narrator/reports/hybrid-campaign-luna-l25-live-gate-2026-10-18.json').read_text())
    gate['paid_ceiling_authorized'] = gate['live_inference_authorized'] = True
    frozen = {}
    for relative in gate['implementation_sha256']:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic fixture\n')
        frozen[relative] = s.sha(path)
    gate['implementation_sha256'] = frozen
    path = tmp_path / 'evals/narrator/reports/hybrid-campaign-luna-l25-live-gate-2026-10-18.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gate))
    request = {'lot': 25, 'manifest_sha256': s.sha(path)}
    return tmp_path, path, request, s.now() + timedelta(minutes=5), s.time.monotonic() + 300


def test_next_midnight_is_fortaleza_not_host_timezone():
    at = datetime(2026,10,19,10,35,tzinfo=timezone.utc)
    assert s.next_midnight(at) == datetime(2026,10,20,3,tzinfo=timezone.utc)


def test_valid_request_preserves_closed_real_gate(lease):
    root, _, request, expires, deadline = lease
    assert s.validate_request(request,root,expires,deadline)[0] == 25
    real = json.loads((s.ROOT / 'evals/narrator/reports/hybrid-campaign-luna-l25-live-gate-2026-10-18.json').read_text())
    assert real['live_inference_authorized'] is False


@pytest.mark.parametrize('field,value',[
    ('paid_ceiling_authorized',False),('live_inference_authorized',False),
    ('retry',True),('fallback',True),('admission_automatic',True),
    ('synthetic_only',False),('target_model','different-model'),
    ('max_estimated_usd','1.00'),('max_calls',18),('reasoning_effort','high'),
])
def test_gate_or_ceiling_cannot_be_bypassed(lease,field,value):
    root,path,request,expires,deadline=lease
    gate=json.loads(path.read_text());gate[field]=value;path.write_text(json.dumps(gate))
    request['manifest_sha256']=s.sha(path)
    with pytest.raises(ValueError,match='gate_invalid'):
        s.validate_request(request,root,expires,deadline)


@pytest.mark.parametrize('change',['digest','code','latch','extra','traversal','bool_lot'])
def test_request_drift_repeat_and_paths_are_rejected(lease,change):
    root,path,request,expires,deadline=lease
    if change=='digest':request['manifest_sha256']='0'*64
    elif change=='code':(root/'scripts/evaluate_hybrid_campaign_luna_l25_live.py').write_text('changed')
    elif change=='latch':(root/'eval-results/hybrid-campaign-luna-l25-once').mkdir(parents=True)
    elif change=='extra':request['command']='not allowed'
    elif change=='bool_lot':request['lot']=True
    else:
        gate=json.loads(path.read_text());key=next(iter(gate['implementation_sha256']))
        gate['implementation_sha256']['../outside']=gate['implementation_sha256'].pop(key)
        path.write_text(json.dumps(gate));request['manifest_sha256']=s.sha(path)
    with pytest.raises(ValueError):s.validate_request(request,root,expires,deadline)


@pytest.mark.parametrize('expired',['utc','monotonic'])
def test_expiry_denies_before_process_or_credential_use(lease,monkeypatch,expired):
    root,_,request,expires,deadline=lease
    if expired=='utc':expires=s.now()-timedelta(seconds=1)
    else:deadline=s.time.monotonic()-1
    monkeypatch.setattr(s.subprocess,'Popen',lambda *_a,**_kw:pytest.fail('must not launch'))
    with pytest.raises(ValueError,match='lease_expired'):
        s.dispatch(request,'synthetic-test-key',expires,deadline,root=root)


def test_dispatch_secret_only_in_live_child_not_args_or_parent(lease,monkeypatch):
    root,_,request,expires,deadline=lease
    calls=[]
    def launch(command,**kwargs):
        calls.append((list(command),dict(kwargs['env'])))
        return SimpleNamespace(wait=lambda timeout:0,poll=lambda:0)
    monkeypatch.setattr(s.subprocess,'Popen',launch)
    assert s.dispatch(request,'synthetic-test-key',expires,deadline,root=root)==0
    assert len(calls)==2 and '--preflight' in calls[0][0] and '--live' in calls[1][0]
    assert all('synthetic-test-key' not in str(args) for args,_ in calls)
    assert 'STORYTELLER_OPENAI_HYP007_L25_KEY' not in calls[0][1]
    assert calls[1][1]['STORYTELLER_OPENAI_HYP007_L25_KEY']=='synthetic-test-key'
    assert 'STORYTELLER_OPENAI_HYP007_L25_KEY' not in s.os.environ


def test_revocation_during_preflight_prevents_live(lease,monkeypatch):
    root,path,request,expires,deadline=lease
    calls=[]
    def wait(timeout):
        gate=json.loads(path.read_text());gate['live_inference_authorized']=False
        path.write_text(json.dumps(gate));return 0
    def launch(*_a,**_kw):
        calls.append(1);return SimpleNamespace(wait=wait,poll=lambda:0)
    monkeypatch.setattr(s.subprocess,'Popen',launch)
    with pytest.raises(ValueError):s.dispatch(request,'synthetic-test-key',expires,deadline,root=root)
    assert len(calls)==1


def test_timeout_kills_running_child(lease):
    _,_,_,expires,deadline=lease
    killed=[]
    def wait(timeout=None):
        if timeout is not None:raise subprocess.TimeoutExpired('synthetic',timeout)
        killed.append('reaped');return -1
    process=SimpleNamespace(wait=wait,poll=lambda:None,kill=lambda:killed.append('killed'))
    with pytest.raises(subprocess.TimeoutExpired):s.wait_child(process,expires,deadline)
    assert killed==['killed','reaped']


def test_close_does_not_persist_key_or_environment(lease,monkeypatch,capsys):
    root,_,_,expires,deadline=lease
    monkeypatch.setattr(s.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(s,'read_credential',lambda *_args:'synthetic-test-key')
    def interrupt(_delay):raise KeyboardInterrupt
    monkeypatch.setattr(s.time,'sleep',interrupt)
    assert s.supervise(expires,deadline,root=root)==0
    directories=list((root/'eval-results/credential-leases').iterdir())
    assert len(directories)==1
    status=json.loads((directories[0]/'status.json').read_text())
    assert status['phase']=='closed' and status['expires_at_utc']==expires.isoformat()
    assert 'synthetic-test-key' not in capsys.readouterr().out
    assert all('synthetic-test-key' not in p.read_text() for p in root.rglob('*') if p.is_file())


@pytest.mark.parametrize('unsafe_console',['no_tty','echo_fallback'])
def test_console_fails_closed_instead_of_echoing_key(lease,monkeypatch,unsafe_console):
    root,_,_,expires,deadline=lease
    monkeypatch.setattr(s.sys.stdin,'isatty',lambda:unsafe_console!='no_tty')
    def denied(*_args):
        if unsafe_console=='no_tty':pytest.fail('must not ask for key')
        raise OSError('synthetic terminal without hidden input')
    monkeypatch.setattr(s,'read_credential',denied)
    assert s.supervise(expires,deadline,root=root)==0
    status_path=next((root/'eval-results/credential-leases').glob('*/status.json'))
    assert json.loads(status_path.read_text())['phase']=='closed'


def test_rejected_request_is_consumed_without_retry(lease,monkeypatch):
    root,gate_path,request,expires,deadline=lease
    gate=json.loads(gate_path.read_text());gate['live_inference_authorized']=False
    gate_path.write_text(json.dumps(gate));request['manifest_sha256']=s.sha(gate_path)
    original=s.write_status
    def status(directory,expires,phase,**fields):
        original(directory,expires,phase,**fields)
        if phase=='idle':(directory/'request-test.json').write_text(json.dumps(request))
    monkeypatch.setattr(s,'write_status',status)
    monkeypatch.setattr(s.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(s,'read_credential',lambda *_args:'synthetic-test-key')
    monkeypatch.setattr(s.subprocess,'Popen',lambda *_a,**_kw:pytest.fail('closed gate'))
    def interrupt(_delay):raise KeyboardInterrupt
    monkeypatch.setattr(s.time,'sleep',interrupt)
    assert s.supervise(expires,deadline,root=root)==0
    directory=next((root/'eval-results/credential-leases').iterdir())
    assert (directory/'request-test.claimed').exists() and not (directory/'request-test.json').exists()


def test_two_individually_approved_lots_share_one_input_without_repeat(lease,monkeypatch):
    root,first_path,first,expires,deadline=lease
    gate=json.loads(first_path.read_text());gate['lot_id']='HYP-007-L26'
    frozen={}
    for relative in gate['implementation_sha256']:
        updated=relative.replace('_l25','_l26')
        path=root/updated;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_text('synthetic fixture\n')
        frozen[updated]=s.sha(path)
    gate['implementation_sha256']=frozen
    second_path=first_path.with_name(first_path.name.replace('-l25-','-l26-'))
    second_path.write_text(json.dumps(gate))
    second={'lot':26,'manifest_sha256':s.sha(second_path)}
    original=s.write_status
    def status(directory,expires,phase,**fields):
        original(directory,expires,phase,**fields)
        if phase=='idle' and 'last_lot' not in fields:
            for index,request in enumerate((first,second,first)):
                (directory/f'request-{index}.json').write_text(json.dumps(request))
    inputs=[];calls=[]
    def key_input(*_args):inputs.append(1);return 'synthetic-test-key'
    def dispatch(request,key,*_args,**_kwargs):
        assert key=='synthetic-test-key';calls.append(request['lot']);return 0
    monkeypatch.setattr(s,'write_status',status)
    monkeypatch.setattr(s.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(s,'read_credential',key_input)
    monkeypatch.setattr(s,'dispatch',dispatch)
    def interrupt(_delay):raise KeyboardInterrupt
    monkeypatch.setattr(s.time,'sleep',interrupt)
    assert s.supervise(expires,deadline,root=root)==0
    assert inputs==[1] and calls==[25,26]
