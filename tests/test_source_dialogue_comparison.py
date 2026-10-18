"""Bounded 12-call composition with synthetic transport, real P/K/H and fresh SQLite."""
import asyncio
import copy
from datetime import timedelta
import json
import os
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest
from scripts import evaluate_source_dialogue_comparison as probe

KEY = "synthetic-dialogue-comparison-key-never-persist"
QUESTION = "O que você faz agora?"


def response(body, *, narrative=None, question=QUESTION, model=None, finish="stop", usage=80):
    packet = json.loads(body["messages"][1]["content"])
    npc = packet["context"]["canonical_scene"]["npcs_present"][0]
    color = "azul" if body["model"] == probe.MODELS[probe.QWEN_ID][0] else "verde"
    count = len(packet["context"]["attributed_sources"])
    endings = ("Uma folha solta permanece sobre a mesa, ao lado de um recipiente vazio.",
        "Uma corrente de ar vira a folha e revela um desenho no verso.",
        "O desenho no verso mostra uma linha curva cercada por pequenos pontos.")
    text = (f'{npc} indica uma pasta {color} apoiada sobre a mesa. "Há desenhos nesta pasta", comenta, '
        'sem sair de junto da janela. A luz atravessa o vidro e torna os traços visíveis. '
        f'{npc} afasta a mão e aguarda. '+endings[count])
    return httpx.Response(200, json={"model": model or body["model"], "choices": [{"finish_reason": finish,
        "message": {"role": "assistant", "content": json.dumps({"n": narrative or text, "q": question}, ensure_ascii=False)}}],
        "usage": None if usage is None else {"prompt_tokens": 100, "completion_tokens": usage, "total_tokens": 100+usage}})


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path/"results")
    from api.llm import contract
    from api.llm.adapters import groq, openai_compatible
    from api import narrative_source_input_service as service, rules_service
    base, clock = probe.utc_now()+timedelta(seconds=10), [0.0]
    def now(): return base+timedelta(seconds=clock[0])
    for module in (probe, probe.retained, contract, groq, openai_compatible): monkeypatch.setattr(module, "utc_now", now)
    async def sleeper(seconds):
        clock[0] += seconds
        await asyncio.sleep(0)
    def budget(): return probe.DispatchBudget(_clock=lambda: clock[0], _sleeper=sleeper)
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Declared dialogue/wait rolled"))
    produced, preparations, generations = [], [], []
    real_produce, real_prepare, real_execute = service.produce_source_player_action, probe.prepare_source_player_action, probe.execute_retained_source_turn
    def produce(request):
        produced.append(request)
        return real_produce(request)
    async def prepare(**kwargs):
        preparations.append((now(), kwargs['deadline'], kwargs['cancellation']))
        return await real_prepare(**kwargs)
    async def execute(**kwargs):
        if not isinstance(kwargs['gateway'], probe.retained.NoCallGateway):
            generations.append((now(), kwargs['deadline'], kwargs['cancellation']))
        return await real_execute(**kwargs)
    monkeypatch.setattr(service, "produce_source_player_action", produce)
    monkeypatch.setattr(probe, "prepare_source_player_action", prepare)
    monkeypatch.setattr(probe, "execute_retained_source_turn", execute)
    seen, overrides = [], {}
    def handle(request):
        body = json.loads(request.content)
        seen.append(body)
        action = overrides.get(len(seen))
        return action(body) if action else response(body)
    return dict(clock=clock, now=now, seen=seen, overrides=overrides, budget=budget, transport=httpx.MockTransport(handle),
        produced=produced, preparations=preparations, generations=generations)


async def run(harness):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_comparison(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path,
        transport=harness['transport'], budget=harness['budget']())
    return prepared, batch, path, rows


def expected(prepared, path):
    target = path.parent/(path.name+'-preflight.json')
    target.write_text(probe._json(prepared.metadata), encoding='utf-8')
    return target, probe.shared._sha256(target)


async def verify(prepared, batch, path):
    target, digest = expected(prepared, path)
    return await asyncio.to_thread(probe.verify_artifacts, path/'summary.json', target, batch, expected_preflight_sha256=digest)


def rewrite(prepared, batch, path, rows, edit=None):
    doc = probe._read_json(path/'summary.json')
    raw = path/'records.jsonl'
    raw.write_text(''.join(probe._json({'metadata': doc['metadata'], 'batch_id': batch, 'record': row})+'\n' for row in rows), encoding='utf-8')
    doc['artifacts']['records']['sha256'] = probe.shared._sha256(raw)
    for name, item in doc['artifacts']['databases'].items():
        database = path/item['file']
        item['sha256'] = probe.shared._sha256(database)
        item['sidecars'] = [{'file': p.name, 'sha256': probe.shared._sha256(p)} for p in probe._database_files(database) if p != database]
        doc['database_snapshots'][name] = probe._database_snapshot(database)
    try:
        doc['summary'] = probe.summarize(rows, prepared, batch)
        doc['process_exit_code'] = doc['summary']['process_exit_code']
    except ValueError:
        pass
    if edit: edit(doc)
    (path/'summary.json').write_text(probe._json(doc), encoding='utf-8')


def test_preflight_freezes_recipe_both_targets_and_taxonomy_without_database(harness, monkeypatch):
    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: pytest.fail('Preflight opened SQLite'))
    prepared = probe.prepare_experiment()
    assert prepared.metadata == probe.prepare_experiment().metadata
    assert prepared.metadata['generation_parameters'] == probe.PARAMETERS
    assert prepared.metadata['inputs']['corpus']['data'] == probe._read_json(probe.CORPUS_PATH)
    assert [(b.target.model, b.candidate.reasoning_effort) for b in prepared.blocks] == [probe.MODELS[cid] for cid in (probe.QWEN_ID, probe.GPT_OSS_ID, probe.GPT_OSS_ID, probe.QWEN_ID)]
    assert all(r['body_sha256'] is None and r['requires_retained_capsule'] and not r['is_live_request'] for r in prepared.metadata['first_request_templates'])
    assert 'frozen_requests' not in prepared.metadata and not harness['seen'] and not harness['produced']


@pytest.mark.asyncio
async def test_full_twelve_commits_both_targets_dynamic_sources_and_replay_preserve_originals(harness):
    prepared, batch, path, rows = await run(harness)
    doc = probe._read_json(path/'summary.json')
    assert doc['process_exit_code'] == 0, [(r.get('result'),r.get('local_error')) for r in rows]
    assert len(harness['seen']) == len(harness['produced']) == 12
    assert harness['clock'][0] == 720
    assert len({row['session_id'] for row in rows}) == 4
    assert all(s['counts'] == {'attempts':9,'turns':3,'events':3} for s in doc['database_snapshots'].values())
    assert doc['summary']['semantic_fidelity_review'] == {'status':'not_performed','approval':None}
    for offset, block in enumerate(prepared.blocks):
        local = rows[offset*3:offset*3+3]
        for i,row in enumerate(local):
            body = harness['seen'][offset*3+i]
            assert body == row['request']['request'] and row['request']['body_sha256'] == probe._sha(body)
            assert body['model'] == block.target.model and body['reasoning_effort'] == block.candidate.reasoning_effort
            assert body['max_completion_tokens'] == 768 and body['temperature'] == .65
            assert body['messages'][0]['content'] == block.prompt
            assert body['response_format']['json_schema']['strict'] is True
            if block.candidate.candidate_id == probe.GPT_OSS_ID: assert body['include_reasoning'] is False
            packet = json.loads(body['messages'][1]['content'])
            assert packet['player_input'] == block.case['turns'][i]['player_input']
            assert [s['text'] for s in packet['context']['attributed_sources']] == [r['response_structure']['n'] for r in local[:i]]
            assert row['capsule']['snapshot']['sources'] == [r['result']['envelope'] for r in local[:i]]
            assert row['input_claim']['request']['config']['npc_aliases'] == block.case['setup']['npcs_present']
            assert QUESTION not in probe._json(packet)
            assert row['replay_verified'] and row['input_replay_verified']
            beginning = probe.datetime.fromisoformat(row['operation_started_at'])
            deadline = probe.datetime.fromisoformat(row['deadline'])
            assert deadline-beginning == timedelta(seconds=60)
            assert row['request']['deadline'] == row['deadline']
    forward = [p for p in harness['preparations'] if p[1] in [g[1] for g in harness['generations']]]
    assert len(forward) == 12
    assert all(p[1:] == g[1:] for p,g in zip(forward,harness['generations']))
    before = {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    assert (await verify(prepared,batch,path))['verified']
    assert len(harness['produced']) == len(harness['seen']) == 12
    assert before == {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['policy','schema','length'])
async def test_second_turn_chain_failure_preserves_first_commit_and_other_blocks(harness, failure):
    harness['overrides'][2] = lambda body: response(body, question='Quem está aqui?') if failure=='policy' else response(body,narrative='curta') if failure=='schema' else response(body,finish='length')
    prepared,batch,path,rows = await run(harness)
    doc = probe._read_json(path/'summary.json')
    assert doc['process_exit_code'] == 1 and doc['summary']['global_stop_reason'] is None
    assert len(harness['seen']) == 11 and doc['summary']['turns_committed'] == 10
    assert rows[2]['reason'] == 'previous_chain_failure'
    assert doc['database_snapshots']['block-1']['counts'] == {'attempts':6,'turns':1,'events':1}
    assert (await verify(prepared,batch,path))['process_exit_code'] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['auth','rate','route','timeout'])
async def test_global_provider_failure_stops_remaining_blocks(harness, failure):
    def fail(body):
        if failure=='timeout': raise httpx.ReadTimeout('synthetic safe timeout')
        if failure=='route': return response(body,model='unrequested-model')
        return httpx.Response(401 if failure=='auth' else 429,json={'error':{'code':'rate_limit_exceeded'}})
    harness['overrides'][1] = fail
    prepared,batch,path,rows = await run(harness)
    doc=probe._read_json(path/'summary.json')
    assert doc['process_exit_code'] == 2 and len(harness['seen']) == 1
    assert set(doc['artifacts']['databases']) == {'block-1'}
    assert all(r['kind']=='source_dialogue_comparison_skip' for r in rows[1:])
    assert doc['database_snapshots']['block-1']['counts']['turns'] == 0
    assert (await verify(prepared,batch,path))['verified']


@pytest.mark.asyncio
async def test_unknown_usage_is_unknown_and_successful_OSS_uses_low(harness):
    harness['overrides'].update({i:lambda b:response(b,usage=None) for i in range(1,13)})
    prepared,batch,path,rows=await run(harness)
    assert probe._read_json(path/'summary.json')['summary']['usage_reported']['output_tokens'] is None
    assert all(row['evidence']['usage']['output_tokens'] is None for row in rows)
    assert (await verify(prepared,batch,path))['process_exit_code']==0


@pytest.mark.asyncio
@pytest.mark.parametrize('location',['n','q'])
async def test_OSS_key_echo_blocked_before_any_SQLite_sidecar_or_artifact(harness,monkeypatch,capsys,location):
    harness['overrides'][4]=lambda b:response(b,narrative=KEY) if location=='n' else response(b,question=KEY)
    inspected=[]; original=probe._database_snapshot
    def snapshot(database):
        result=original(database)
        if len(harness['seen'])==4 and database.name=='block-2.sqlite3':
            assert not (database.parent/'summary.json').exists()
            assert all(KEY.encode() not in p.read_bytes() for p in probe._database_files(database))
            inspected.append(True)
        return result
    monkeypatch.setattr(probe,'_database_snapshot',snapshot)
    prepared,batch,path,rows=await run(harness)
    monkeypatch.setattr(probe,'_database_snapshot',original)
    assert inspected and rows[3]['credential_echo_blocked'] and rows[3]['http_started_at']
    assert rows[3]['response_structure'] is rows[3]['evidence'] is None
    assert probe._read_json(path/'summary.json')['database_snapshots']['block-2']['counts']['turns']==0
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir() if p.is_file())
    out=capsys.readouterr(); assert KEY not in out.out+out.err
    assert (await verify(prepared,batch,path))['process_exit_code']==3


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['over_budget','late_response','expired_before_HTTP','observer','usage'])
async def test_precommit_guard_closes_global_on_limit_or_contradictory_success(harness,monkeypatch,failure):
    if failure=='over_budget': harness['overrides'][1]=lambda b:response(b,usage=769)
    elif failure=='late_response':
        def late(body):
            harness['clock'][0]+=61
            return response(body)
        harness['overrides'][1]=late
    elif failure=='expired_before_HTTP':
        original=probe._prepare
        async def late_prepare(*args,**kwargs):
            value=await original(*args,**kwargs)
            if not kwargs.get('replay'): harness['clock'][0]+=61
            return value
        monkeypatch.setattr(probe,'_prepare',late_prepare)
    else:
        original=probe.ObservationAdapter._observe_metadata
        def altered(self,payload):
            original(self,payload)
            if failure=='observer': self._observation['http_status']=503
            else: self._observation['usage']['output_tokens']=81
        monkeypatch.setattr(probe.ObservationAdapter,'_observe_metadata',altered)
    prepared,batch,path,rows=await run(harness)
    doc=probe._read_json(path/'summary.json')
    assert len(harness['seen'])==(0 if failure=='expired_before_HTTP' else 1)
    assert doc['summary']['global_stop_reason'] and doc['database_snapshots']['block-1']['counts']['turns']==0
    assert (await verify(prepared,batch,path))['verified']


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['producer','cancel_wait','local'])
async def test_pre_http_failures_do_not_create_later_P_or_call(harness,monkeypatch,failure):
    from api import narrative_source_input_service as service
    from api.narrative_source_input import SourceInputFailure
    if failure=='producer': monkeypatch.setattr(service,'produce_source_player_action',lambda request:SourceInputFailure(code='source_input_out_of_scope',stage='classification'))
    else:
        async def stop(self,block_id):
            if failure=='cancel_wait': raise asyncio.CancelledError
            raise ValueError('synthetic unsafe detail never printed')
        monkeypatch.setattr(probe.DispatchBudget,'wait',stop)
    prepared,batch,path,rows=await run(harness)
    assert not harness['seen'] and rows[1]['kind']=='source_dialogue_comparison_skip'
    assert (await verify(prepared,batch,path))['process_exit_code']==(130 if failure=='cancel_wait' else 3)


@pytest.mark.asyncio
async def test_hard_budget_enforces_spacing_unique_operations_per_block_and_total(harness):
    budget=harness['budget']()
    with pytest.raises(ValueError):budget.consume('block-1','op-1')
    for i in range(12):
        await budget.wait('block-'+str(i//3+1)); budget.consume('block-'+str(i//3+1),'op-'+str(i))
        with pytest.raises(ValueError):budget.consume('block-'+str(i//3+1),'duplicate')
        if i==2:
            await budget.wait('block-1')
            with pytest.raises(ValueError):budget.consume('block-1','fourth')
    await budget.wait('block-4')
    with pytest.raises(ValueError):budget.consume('block-4','thirteenth')
    assert budget.calls==12


@pytest.mark.asyncio
async def test_rehashed_foreign_sources_requests_observers_and_database_are_rejected(harness):
    prepared,batch,path,baseline=await run(harness)
    original_summary=(path/'summary.json').read_bytes()
    variants=['cross_block','question','aliases','reasoning','model','deadline','late_request','overlap','http503','finish_length','error_body','failed_generation','usage','snapshot','extra','missing','database']
    for change in variants:
        (path/'summary.json').write_bytes(original_summary)
        rows=copy.deepcopy(baseline); edit=None
        if change=='cross_block':rows[4]['capsule']['snapshot']['sources']=rows[1]['capsule']['snapshot']['sources']
        elif change=='question':rows[1]['capsule']['snapshot']['sources'][0]['projection']['source']['text']+=QUESTION
        elif change=='aliases':rows[4]['input_claim']['request']['config']['npc_aliases']=[]
        elif change in ('reasoning','model'):
            request=rows[3]['request']; request['request']['reasoning_effort' if change=='reasoning' else 'model']='none' if change=='reasoning' else probe.MODELS[probe.QWEN_ID][0]
            request['body_sha256']=probe._sha(request['request'])
        elif change=='deadline':rows[1]['request']['deadline']=rows[0]['deadline']
        elif change=='late_request':rows[1]['request_created_at']=(probe.datetime.fromisoformat(rows[1]['deadline'])+timedelta(seconds=1)).isoformat()
        elif change=='overlap':rows[1]['operation_started_at']=rows[0]['operation_started_at']
        elif change=='http503':rows[3]['provider_observation']['http_status']=503
        elif change=='finish_length':rows[3]['provider_observation']['finish_reason']='length'
        elif change=='error_body':rows[3]['provider_observation']['error_body']['bytes']=7
        elif change=='failed_generation':rows[3]['provider_observation']['failed_generation']['characters']=7
        elif change=='usage':rows[3]['provider_observation']['usage']['output_tokens']=769
        elif change=='snapshot':edit=lambda doc:doc['database_snapshots']['block-2']['counts'].update(turns=99)
        elif change=='extra':rows.append(copy.deepcopy(rows[-1]))
        elif change=='missing':rows.pop()
        elif change=='database':
            with sqlite3.connect(path/'block-2.sqlite3') as conn:conn.execute('UPDATE campaigns SET state_revision=99')
        rewrite(prepared,batch,path,rows,edit)
        with pytest.raises((ValueError,TypeError),match='.'):
            await verify(prepared,batch,path)


@pytest.mark.parametrize('mode',['preflight','invalid','verify'])
def test_non_live_CLI_does_not_access_key(harness,monkeypatch,capsys,mode):
    def forbidden(*args,**kwargs):pytest.fail('Non-live accessed credential')
    monkeypatch.setattr(probe,'os',SimpleNamespace(environ=SimpleNamespace(pop=forbidden,get=forbidden)))
    if mode=='verify':
        monkeypatch.setattr(probe,'verify_artifacts',lambda *a,**k: {'verified':True})
        args=['--verify-artifacts','unused','--batch-id',str(uuid4()),'--expected-preflight','unused','--expected-preflight-sha256','0'*64]
    else:args=['--preflight'] if mode=='preflight' else ['--live']
    assert probe.main(args)==(3 if mode=='invalid' else 0)
    assert not harness['seen']; captured=capsys.readouterr();assert KEY not in captured.out+captured.err


def test_live_pop_removes_key_before_Git_and_drift_stops_without_HTTP(harness,monkeypatch,capsys):
    inherited=[]
    def git(arguments,**kwargs):
        inherited.append(probe.KEY_ENV in kwargs.get('env',os.environ))
        return SimpleNamespace(stdout='5e563824fcba4c53cc37b5084a8ce65f3fa30356\n' if arguments[1]=='rev-parse' else ' M synthetic\n')
    monkeypatch.setattr(probe.shared.subprocess,'run',git)
    prepared,batch=probe.prepare_experiment(),str(uuid4());path=probe.run_path(batch);path.parent.mkdir(parents=True)
    target,digest=expected(prepared,path)
    original=probe._expected
    def drift(*args,**kwargs):
        value=original(*args,**kwargs)
        raise ValueError('synthetic private diagnostic')
    monkeypatch.setattr(probe,'_expected',drift)
    inherited.clear();monkeypatch.setenv(probe.KEY_ENV,KEY)
    assert probe.main(['--live','--allow-synthetic-only','--batch-id',batch,'--expected-preflight',str(target),'--expected-preflight-sha256',digest,'--api-key-env',probe.KEY_ENV])==3
    assert inherited and not any(inherited) and probe.KEY_ENV not in os.environ
    assert not path.exists() and not harness['seen'];captured=capsys.readouterr();assert KEY not in captured.out+captured.err

@pytest.mark.asyncio
async def test_extra_event_with_rehashed_database_and_snapshot_is_rejected(harness):
    harness['overrides'][2]=lambda b:httpx.Response(401,json={'error':{'message':'synthetic authentication failure'}})
    prepared,batch,path,rows=await run(harness)
    assert (await verify(prepared,batch,path))['verified']
    database=path/'block-1.sqlite3'
    with probe.retained._ClosingConnection(sqlite3.connect(database)) as conn:
        columns=[r[1] for r in conn.execute('PRAGMA table_info(events)') if r[1]!='id']
        original=dict(zip(columns,conn.execute('SELECT '+','.join(columns)+' FROM events LIMIT 1').fetchone()))
        original.update(event_id=str(uuid4()),sequence=99)
        conn.execute('INSERT INTO events('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',list(original.values()))
        conn.commit()
    rewrite(prepared,batch,path,rows)
    with pytest.raises(ValueError):await verify(prepared,batch,path)


@pytest.mark.asyncio
async def test_cancel_after_commit_preserves_it_and_stops_all_future_operations(harness,monkeypatch):
    original=probe.execute_retained_source_turn
    async def cancel(**kwargs):
        result=await original(**kwargs)
        if not isinstance(kwargs['gateway'],probe.retained.NoCallGateway):raise asyncio.CancelledError
        return result
    monkeypatch.setattr(probe,'execute_retained_source_turn',cancel)
    prepared,batch,path,rows=await run(harness)
    assert rows[0]['result']['status']=='completed' and rows[0]['replay_verified']
    assert len(harness['seen'])==len(harness['produced'])==1
    assert probe._read_json(path/'summary.json')['database_snapshots']['block-1']['counts']=={'attempts':3,'turns':1,'events':1}
    assert (await verify(prepared,batch,path))['process_exit_code']==130


@pytest.mark.parametrize('field',['schema','recipe'])
def test_rehashed_preflight_is_rejected_before_SQLite_or_HTTP(harness,monkeypatch,capsys,field):
    prepared,batch=probe.prepare_experiment(),str(uuid4());path=probe.run_path(batch);path.parent.mkdir(parents=True)
    forged=copy.deepcopy(prepared.metadata)
    if field=='schema':forged['first_request_templates'][1]['provider_static']['response_schema']={'type':'object'}
    else:forged['first_request_templates'][1]['player_input']='Espero sem falar.'
    target=path.parent/'forged-preflight.json';target.write_text(probe._json(forged),encoding='utf-8')
    monkeypatch.setenv(probe.KEY_ENV,KEY)
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('Rejected preflight opened SQLite'))
    assert probe.main(['--live','--allow-synthetic-only','--batch-id',batch,'--expected-preflight',str(target),'--expected-preflight-sha256',probe.shared._sha256(target),'--api-key-env',probe.KEY_ENV])==3
    assert not path.exists() and not harness['seen'] and probe.KEY_ENV not in os.environ
    out=capsys.readouterr();assert KEY not in out.out+out.err


@pytest.mark.asyncio
async def test_final_dispatch_rejects_changed_body_route_and_deadline_before_budget(harness):
    harness['overrides'][2]=lambda b:httpx.Response(401,json={'error':{'message':'synthetic authentication failure'}})
    prepared,batch,path,rows=await run(harness)
    block=prepared.blocks[0]
    capsule=probe.validate_source_turn_capsule(rows[0]['capsule'],session_id=rows[0]['session_id'],operation_id=rows[0]['operation_id'])
    deadline=harness['now']()+timedelta(seconds=60)
    request=probe._request(capsule,deadline)
    budget=harness['budget']()
    adapter=probe.ObservationAdapter(experiment=prepared,block=block,request=request,operation=rows[0]['operation_id'],api_key=SecretStr(KEY),budget=budget,transport=harness['transport'])
    body=probe._body(request,block.candidate.reasoning_effort)
    for target,body_override in [('https://invalid.example/chat/completions',body),(probe.GROQ_OFFICIAL_BASE_URL+'/chat/completions',{**body,'model':'other'})]:
        with pytest.raises(ValueError):await adapter._dispatch(httpx.Request('POST',target,json=body_override))
    harness['clock'][0]+=61
    with pytest.raises(ValueError):await adapter._dispatch(httpx.Request('POST',probe.GROQ_OFFICIAL_BASE_URL+'/chat/completions',json=body))
    assert budget.calls==0 and not adapter.http_sent and len(harness['seen'])==2
