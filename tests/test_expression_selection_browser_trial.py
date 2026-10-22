"""Focused browser boundary, idempotency and restart acceptance for isolated A2."""
from fastapi.testclient import TestClient
import pytest
from api.experiments.expression_selection.contract import SelectionConfig, Choice, Selection
from api.llm.contract import LLMTarget
from api.rules_service import PlayerSheetModel
from scripts.run_campaign_source_offline_trial import _initial_state
from scripts.run_expression_selection_browser_trial import create_app

TOKEN='synthetic-browser-test-token'

def client(path):
    return TestClient(create_app(path, access_token=TOKEN), base_url='http://127.0.0.1:8032', headers={'X-Trial-Token':TOKEN})

def start(c):
    response=c.post('/api/start');assert response.status_code==200
    return response.json()['session_id']

def action(c,sid,op,text):
    return c.post('/api/action',json={'session_id':sid,'operation_id':op,'player_input':text})

def test_complete_replay_restart(tmp_path):
    path=tmp_path/'a2.db';c=client(path);sid=start(c)
    first=action(c,sid,'a','Como posso ajudar?');assert first.status_code==200
    assert first.json()['turn']==1 and first.json()['provider_calls']==0
    assert action(c,sid,'a','Como posso ajudar?').json()==first.json()
    assert action(c,sid,'a','Desisto').status_code==409
    terminal=action(c,sid,'b','Retiro o registro');assert terminal.status_code==200
    assert terminal.json()['outcome']=='preserved'
    assert action(c,sid,'b','Retiro o registro').json()==terminal.json()
    assert action(c,sid,'c','Aguardo').status_code==409
    restarted=client(path)
    assert restarted.get('/api/session/'+sid).json()==terminal.json()
    assert len(restarted.app.state.selection_store.attempts(sid,'b'))==1


def test_unsupported_preserves_state_and_no_operation(tmp_path):
    c=client(tmp_path/'a2.db');sid=start(c)
    before=c.get('/api/session/'+sid).json()
    assert action(c,sid,'unknown','Por que?').status_code==422
    assert c.get('/api/session/'+sid).json()==before
    with c.app.state.selection_store._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM operations').fetchone()[0]==0
    assert action(c,sid,'known','Mara, leve o registro').status_code==200


@pytest.mark.parametrize('retained_choice',[False,True])
def test_explicit_resume_retains_preparation_without_rng(tmp_path,monkeypatch,retained_choice):
    path=tmp_path/'a2.db';c=client(path);sid=start(c);store=c.app.state.selection_store
    prepared=store.prepare(sid,'a','Como posso ajudar?')
    store.claim(sid,'a','interrupted')
    if retained_choice:
        store.save_selection(sid,'a','interrupted',Selection(choice=Choice(utterance='original',atmosphere='none',layout='inline'),origin='deterministic',source_attempt_id='interrupted'))
    restarted=client(path)
    assert restarted.get('/api/session/'+sid).json()['pending']['id']=='a'
    def forbidden(*args,**kwargs):raise AssertionError('Must reuse retained preparation')
    monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation',forbidden)
    monkeypatch.setattr('api.rules_service.calculate_resolution',forbidden)
    result=restarted.post('/api/resume',json={'session_id':sid,'operation_id':'a'})
    assert result.status_code==200 and result.json()['turn']==1
    assert restarted.app.state.selection_store.preparation(sid,'a')==prepared
    assert [a['status'] for a in store.attempts(sid,'a')]==['interrupted','completed']
    assert restarted.post('/api/resume',json={'session_id':sid,'operation_id':'a'}).json()==result.json()


def test_abandoned_preparation_cannot_reroll(tmp_path):
    c=client(tmp_path/'a2.db');sid=start(c);store=c.app.state.selection_store
    with store._connection(write=True) as db:
        db.execute("INSERT INTO operations(session_id,id,phase,input) VALUES(?,?,'preparing',?)",(sid,'a','Examino o registro'))
    assert c.post('/api/resume',json={'session_id':sid,'operation_id':'a'}).status_code==409
    cancelled=c.post('/api/cancel',json={'session_id':sid,'operation_id':'a'})
    assert cancelled.status_code==200 and cancelled.json()['turn']==0 and cancelled.json()['pending'] is None
    assert action(c,sid,'a','Examino o registro').status_code==409
    assert action(c,sid,'b','Desisto').status_code==200


def test_local_boundary_and_mode(tmp_path):
    c=client(tmp_path/'a2.db')
    assert c.post('/api/start',headers={'X-Trial-Token':''}).status_code==403
    assert c.post('/api/start',headers={'Origin':'https://external.invalid'}).status_code==403
    assert c.get('/',headers={'Host':'external.invalid'}).status_code==403
    store=c.app.state.selection_store
    store.create_session('model',config=SelectionConfig(mode='model',target=LLMTarget(profile='test',provider='test',model='test')),sheet=PlayerSheetModel.model_validate(_initial_state()['player_sheet']))
    assert c.get('/api/session/model').status_code==409
    assert action(c,'model','a','Desisto').status_code==409
    with store._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==0
    page=c.get('/');assert page.status_code==200
    assert 'textContent' in page.text and 'innerHTML' not in page.text
    assert page.headers['cache-control']=='no-store'


def test_distinct_long_operations_and_missing_session(tmp_path):
    c=client(tmp_path/'a2.db');sid=start(c)
    assert action(c,sid,'x'*159+'a','Como posso ajudar?').status_code==200
    assert action(c,sid,'x'*159+'b','Mara, leve o registro').json()['turn']==2
    assert c.get('/api/session/absent').status_code==404
