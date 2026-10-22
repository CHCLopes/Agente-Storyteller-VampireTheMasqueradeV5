"""A2 acceptance: causal parity, closed choices, durable resume and isolation."""
import asyncio
from copy import deepcopy
from datetime import timedelta
from itertools import product
import json
import sqlite3
import httpx
import pytest
from api import rules_service
from api.rules_service import PlayerSheetModel,ResolutionResult
from api.llm.contract import CancellationToken,CapabilityDescriptor,CapabilitySet,CapabilitySupport,LLMTarget,utc_now
from api.experiments.expression_selection import contract
from api.experiments.expression_selection.contract import Choice,Preparation,SelectionConfig,digest,json_text
from api.experiments.expression_selection.service import execute
from api.experiments.expression_selection.store import SelectionStore
from api.experiments.expression_selection.transport import OpenAISelectionGateway
from scripts.preflight_hybrid_campaign_luna_l85 import CASES
from scripts.run_campaign_source_offline_trial import _initial_state

TARGET=LLMTarget(profile='selection-test',provider='synthetic-provider',model='synthetic-model')
VALID='{"utterance":"variant","atmosphere":"none","layout":"paragraph"}'

def receipt(success=False):
 return ResolutionResult(successes=3 if success else 0,is_success=success,bestial_failure=False,messy_critical=False,
  summary='Investigação resolvida.',normal_rolls=[8,8,8,5,4] if success else [2,2,2,3,4],hunger_rolls=[],margin=0 if success else -3)

def setup(tmp_path,mode='deterministic',*,emulated=False):
 store=SelectionStore(tmp_path/'selection.sqlite3',create=True)
 config=SelectionConfig(mode=mode,target=TARGET if mode=='model' else None,allow_emulated=emulated)
 store.create_session('s',config=config,sheet=PlayerSheetModel.model_validate(_initial_state()['player_sheet']))
 return store

def gateway(raw=VALID,*,emulated=False,handler=None):
 calls=[]
 def respond(request):
  body=json.loads(request.content);calls.append(body)
  assert request.headers.get('authorization') is None
  if handler:return handler(request,body)
  return httpx.Response(200,json={'model':TARGET.model,'choices':[{'message':{'content':raw},'finish_reason':'stop'}]})
 support=CapabilitySupport.EMULATED if emulated else CapabilitySupport.NATIVE
 caps=CapabilitySet(target=TARGET,descriptors=(CapabilityDescriptor(name='text_generation',support=CapabilitySupport.NATIVE),
  CapabilityDescriptor(name='structured_generation',support=support,source='offline mock')))
 return OpenAISelectionGateway(base_url='https://offline.invalid/v1',capability_set=caps,transport=httpx.MockTransport(respond)),calls

async def run(store,backend=None,op='op',attempt='a',resume=None,token=None):
 return await execute(store=store,session_id='s',operation_id=op,attempt_id=attempt,gateway=backend,
  deadline=utc_now()+timedelta(seconds=20),cancellation=token or CancellationToken(),resumes_attempt_id=resume)

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['deterministic','model'])
@pytest.mark.parametrize('case_id,actions,rules,outcome',CASES,ids=[x[0] for x in CASES])
async def test_matrix_and_restart(case_id,actions,rules,outcome,mode,tmp_path,monkeypatch):
 rolls=[]
 def roll(*a,**kw):rolls.append(1);return receipt(case_id=='CAMP-EVAL-06')
 monkeypatch.setattr(rules_service,'calculate_resolution',roll)
 store=setup(tmp_path,mode);backend,calls=gateway()
 for number,(action,rule) in enumerate(zip(actions,rules),1):
  op=f'op-{number}';p=store.prepare('s',op,action)
  assert p.effect.rule_id==rule
  assert store.prepare('s',op,action)==p
  result=await run(store,backend,op,attempt=f'a-{number}')
  assert result.status=='completed',result
  assert result.presentation.realized_effects==p.effect.beat.effect_keys
  assert result.presentation.segments[0].text==p.plan.critical[0].text
  assert all(s.origin=='application' for s in result.presentation.segments)
  store=SelectionStore(store.path)
  replay=await run(store,None,op,attempt=f'a-{number}')
  assert replay.presentation==result.presentation
 assert store.session('s').state.outcome==outcome
 assert len(calls)==(len(actions) if mode=='model' else 0)
 assert len(rolls)==(1 if case_id in {'CAMP-EVAL-06','CAMP-EVAL-07'} else 0)

@pytest.mark.asyncio
@pytest.mark.parametrize('actions,contains,expected_rule',[
 (['Mara, leve o registro'],'/help/','R-01'),
 (['Qual é a tarefa?','Qual é a tarefa?'],'/repeat/','R-01'),
 (['Aguardo','Espero','Qual é a tarefa?'],'/wet/wet/','R-01'),
 (['Aguardo','Espero','Mara, leve o registro'],'/help/wet/wet/','R-01'),
 (['Aguardo','Espero','Examino o registro'],'/wet/lost/','R-08'),
 (['Aguardo','Espero','Desisto'],'/wet/wet/','R-09'),
])
async def test_missing_state_variants(actions,contains,expected_rule,tmp_path,monkeypatch):
 monkeypatch.setattr(rules_service,'calculate_resolution',lambda *a,**kw:receipt())
 store=setup(tmp_path,'model');backend,_=gateway()
 for n,action in enumerate(actions):
  p=store.prepare('s',str(n),action)
  result=await run(store,backend,str(n),str(n));assert result.status=='completed',result
 assert p.effect.rule_id==expected_rule and contains in p.catalog.condition_key
 if expected_rule=='R-09':assert 'molhado' in result.presentation.text
 if expected_rule=='R-08':assert 'irrecuperável' in result.presentation.text

INVALID=[
 '{"utterance":"variant","atmosphere":"none","layout":"inline","narrative":"Você abre a porta."}',
 '{"utterance":"another-scene","atmosphere":"none","layout":"inline"}',
 '{"utterance":"variant","atmosphere":"none","layout":"inline","layout":"paragraph"}',
 '```json\n'+VALID+'\n```',VALID+' trailing','null','[]',
 '{"utterance":"variant","atmosphere":true,"layout":"inline"}',
 '{"utterance":"variant","atmosphere":"none"}',
 '{"utterance":"variant","atmosphere":"nоne","layout":"inline"}',
 ' '*513,
 '{"protocol":"campaign-source-expression-v2","plan_sha256":"forged","slots":[]}',
]
@pytest.mark.asyncio
@pytest.mark.parametrize('raw',INVALID)
@pytest.mark.parametrize('emulated',[False,True])
async def test_strict_rejection_no_effect_no_retry(raw,emulated,tmp_path):
 store=setup(tmp_path,'model',emulated=emulated);store.prepare('s','op','Aguardo');backend,calls=gateway(raw,emulated=emulated)
 r=await run(store,backend);assert r.status=='failed' and r.presentation is None
 assert store.session('s').state.revision==0
 assert (await run(store,backend)).status=='failed' and len(calls)==1
 with pytest.raises(ValueError,match='explicit_resume'):await run(store,backend,attempt='other')

@pytest.mark.asyncio
@pytest.mark.parametrize('emulated',[False,True])
async def test_wire_modes(emulated,tmp_path):
 store=setup(tmp_path,'model',emulated=emulated);store.prepare('s','op','Aguardo');backend,calls=gateway(emulated=emulated)
 result=await run(store,backend);assert result.status=='completed'
 assert ('response_format' in calls[0]) is (not emulated)
 assert result.presentation.selection.raw_output==VALID
 assert result.presentation.selection.evidence.provenance.requested_target==TARGET

@pytest.mark.asyncio
async def test_emulated_requires_explicit_allowance(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo');backend,calls=gateway(emulated=True)
 result=await run(store,backend);assert result.error_code=='selection_capability_missing' and not calls

@pytest.mark.asyncio
async def test_cancel_after_valid_selection_reuses_it_on_resume(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo');token=CancellationToken()
 def respond(request,body):
  token.cancel('test after response')
  return httpx.Response(200,json={'model':TARGET.model,'choices':[{'message':{'content':VALID},'finish_reason':'stop'}]})
 # Cancel just after select returns, so the transport itself completes normally.
 backend,calls=gateway()
 original=backend.select
 async def select(request):
  response=await original(request);token.cancel('after generation');return response
 backend.select=select
 result=await run(store,backend,token=token);assert result.status=='cancelled'
 assert store.session('s').state.revision==0
 store=SelectionStore(store.path)
 result=await run(store,None,attempt='resume',resume='a')
 assert result.status=='completed' and len(calls)==1
 assert result.presentation.selection.source_attempt_id=='a'

@pytest.mark.asyncio
async def test_atomic_rollback_retains_choice_without_redelivery(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo');backend,calls=gateway()
 with sqlite3.connect(store.path) as c:c.execute("CREATE TRIGGER reject_commit BEFORE UPDATE ON sessions BEGIN SELECT RAISE(ABORT,'injected'); END")
 result=await run(store,backend)
 assert result.status=='failed' and result.presentation is None and store.session('s').state.revision==0
 with sqlite3.connect(store.path) as c:c.execute('DROP TRIGGER reject_commit')
 result=await run(SelectionStore(store.path),None,attempt='resume',resume='a')
 assert result.status=='completed' and len(calls)==1

@pytest.mark.asyncio
async def test_concurrent_attempt_single_dispatch_and_explicit_recovery(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo');backend,calls=gateway()
 entered=asyncio.Event();release=asyncio.Event();original=backend.select
 async def delayed(request):
  entered.set();await release.wait();return await original(request)
 backend.select=delayed
 task=asyncio.create_task(run(store,backend));await entered.wait()
 assert (await run(SelectionStore(store.path),backend)).status=='pending'
 with pytest.raises(ValueError,match='explicit_resume'):await run(store,backend,attempt='other')
 old=store.attempts('s','op')[0]
 store.recover_interrupted('s','op','a',expected_invocation_id=old['invocation_id'])
 release.set();assert (await task).status=='failed'
 assert store.session('s').state.revision==0
 backend.select=original
 result=await run(store,backend,attempt='resume',resume='a')
 assert result.status=='completed' and len(calls)==2

@pytest.mark.asyncio
async def test_replay_uses_retained_bytes_not_current_renderers(tmp_path,monkeypatch):
 store=setup(tmp_path);store.prepare('s','op','Aguardo');result=await run(store)
 def forbidden(*a,**kw):pytest.fail('replay used current builder, renderer or RNG')
 monkeypatch.setattr(contract,'render',forbidden);monkeypatch.setattr(contract,'build_catalog',forbidden)
 monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
 replay=await run(SelectionStore(store.path));assert replay.presentation.text.encode()==result.presentation.text.encode()

@pytest.mark.parametrize('mutation',['catalog_text','catalog_refs','plan_actor','cross_version','revision'])
def test_rehashed_preparation_tampering_rejected(mutation,tmp_path):
 store=setup(tmp_path);p=store.prepare('s','op','Aguardo');raw=p.model_dump(mode='json')
 if mutation=='catalog_text':raw['catalog']['utterances'][1]['text']='Mara diz: “As páginas secaram.”'
 if mutation=='catalog_refs':raw['catalog']['utterances'][1]['fact_refs']=['foreign.fact']
 if mutation=='plan_actor':
  raw['plan']['critical'][0]['actor']='player'
  raw['plan']['plan_sha256']=digest({k:v for k,v in raw['plan'].items() if k!='plan_sha256'})
 if mutation=='cross_version':raw['protocol']='campaign-expression-capsule-v2'
 if mutation=='revision':raw['request']['base_revision']=99
 raw['fingerprint_sha256']=digest({k:v for k,v in raw.items() if k!='fingerprint_sha256'})
 with pytest.raises(ValueError):Preparation.model_validate(raw)

@pytest.mark.asyncio
async def test_rehashed_history_text_rejected(tmp_path):
 store=setup(tmp_path);store.prepare('s','op','Aguardo');await run(store)
 with sqlite3.connect(store.path) as c:
  raw=json.loads(c.execute('SELECT presentation FROM operations').fetchone()[0]);old=raw['segments'][1]['text'];new=old.replace('água','fogo')
  raw['text']=raw['text'].replace(old,new);raw['segments'][1]['text']=new
  raw['fingerprint_sha256']=digest({k:v for k,v in raw.items() if k!='fingerprint_sha256'})
  c.execute('UPDATE operations SET presentation=?',(json_text(raw),))
 with pytest.raises(ValueError):store.session('s')

@pytest.mark.asyncio
async def test_all_eight_combinations_and_no_state_mutation(tmp_path):
 store=setup(tmp_path,'model');p=store.prepare('s','op','Aguardo');backend,_=gateway()
 claimed=store.claim('s','op','a');request=__import__('api.experiments.expression_selection.service',fromlist=['build_request']).build_request(p,claimed['invocation_id'],utc_now()+timedelta(seconds=10),CancellationToken())
 response=await backend.select(request)
 from api.experiments.expression_selection.contract import Selection
 for values in product(('original','variant'),('none','position'),('inline','paragraph')):
  choice=Choice(**dict(zip(('utterance','atmosphere','layout'),values)))
  selected=Selection(choice=choice,origin='model',source_attempt_id='a',raw_output=json_text(choice),evidence=response.evidence)
  presentation=contract.render(p,selected)
  assert contract.validate_retained_presentation(p,presentation)==presentation
 assert store.session('s').state.revision==0

def test_rng_claim_failure_never_rerolls_same_operation(tmp_path,monkeypatch):
 store=setup(tmp_path);calls=[]
 def fail(*a,**kw):calls.append(1);raise RuntimeError('RNG failed')
 monkeypatch.setattr(rules_service,'calculate_resolution',fail)
 with pytest.raises(RuntimeError):store.prepare('s','op','Examino o registro')
 with pytest.raises(ValueError,match='preparation_unavailable'):store.prepare('s','op','Examino o registro')
 assert len(calls)==1 and store.session('s').state.revision==0

def test_product_database_refused_without_mutation(tmp_path):
 p=tmp_path/'product.sqlite3'
 with sqlite3.connect(p) as c:c.execute('CREATE TABLE campaigns(id TEXT)')
 original=p.read_bytes()
 with pytest.raises(ValueError,match='not_experimental'):SelectionStore(p)
 with pytest.raises(FileExistsError):SelectionStore(p,create=True)
 assert p.read_bytes()==original

def test_session_and_operation_isolation(tmp_path):
 store=setup(tmp_path);store.prepare('s','op','Aguardo')
 with pytest.raises(ValueError,match='operation_reuse'):store.prepare('s','op','Desisto')
 with pytest.raises(ValueError,match='operation_pending'):store.prepare('s','other','Desisto')
 with pytest.raises(ValueError):SelectionConfig(mode='deterministic',target=TARGET)
 with pytest.raises(ValueError):SelectionConfig(mode='model')

@pytest.mark.asyncio
async def test_cancel_before_generation_and_timeout_no_provider(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo');backend,calls=gateway();token=CancellationToken();token.cancel('before')
 result=await run(store,backend,token=token);assert result.status=='cancelled' and not calls
 result=await execute(store=store,session_id='s',operation_id='op',attempt_id='timeout',resumes_attempt_id='a',gateway=backend,
  deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken())
 assert result.error_code=='selection_deadline' and not calls

@pytest.mark.asyncio
async def test_task_cancellation_retains_preparation_and_allows_explicit_resume(tmp_path):
 store=setup(tmp_path,'model');p=store.prepare('s','op','Aguardo');backend,calls=gateway();entered=asyncio.Event()
 original=backend.select
 async def blocked(request):entered.set();await asyncio.Event().wait()
 backend.select=blocked
 task=asyncio.create_task(run(store,backend));await entered.wait();task.cancel()
 with pytest.raises(asyncio.CancelledError):await task
 assert store.preparation('s','op')==p and store.session('s').state.revision==0
 backend.select=original
 assert (await run(SelectionStore(store.path),backend,attempt='resume',resume='a')).status=='completed'
 assert len(calls)==1

@pytest.mark.asyncio
async def test_provider_failure_and_route_mismatch_no_fallback(tmp_path):
 store=setup(tmp_path,'model');store.prepare('s','op','Aguardo')
 backend,calls=gateway(handler=lambda r,b:httpx.Response(503,json={'error':{'message':'synthetic unavailable'}}))
 result=await run(store,backend);assert result.error_code=='selection_provider_failure' and len(calls)==1
 backend,other=gateway(handler=lambda r,b:httpx.Response(200,json={'model':'wrong-model','choices':[{'message':{'content':VALID},'finish_reason':'stop'}]}))
 result=await run(store,backend,attempt='resume',resume='a')
 assert result.status=='failed' and len(other)==1 and store.session('s').state.revision==0

@pytest.mark.asyncio
async def test_recovery_after_retaining_choice_reuses_original_invocation(tmp_path):
 store=setup(tmp_path,'model');p=store.prepare('s','op','Aguardo');backend,calls=gateway()
 claim=store.claim('s','op','a')
 from api.experiments.expression_selection.service import build_request
 from api.experiments.expression_selection.contract import Selection
 response=await backend.select(build_request(p,claim['invocation_id'],utc_now()+timedelta(seconds=10),CancellationToken()))
 selected=Selection(choice=contract.parse_choice(response.raw),origin='model',source_attempt_id='a',raw_output=response.raw,evidence=response.evidence)
 store.save_selection('s','op','a',selected)
 store=SelectionStore(store.path)
 with pytest.raises(ValueError,match='recovery_cas'):store.recover_interrupted('s','op','a',expected_invocation_id='wrong')
 store.recover_interrupted('s','op','a',expected_invocation_id=claim['invocation_id'])
 result=await run(store,None,attempt='resume',resume='a')
 assert result.status=='completed' and result.presentation.selection.evidence==response.evidence and len(calls)==1

def test_interrupted_preparation_cannot_be_replayed_or_rerolled(tmp_path,monkeypatch):
 store=setup(tmp_path);observed=[]
 original=__import__('api.experiments.expression_selection.store',fromlist=['produce_preparation']).produce_preparation
 def interrupted(*args,**kw):
  # Simulate process loss after claim. Recovery wins CAS before old finalization.
  observed.append(1);store.recover_preparation('s','op');return original(*args,**kw)
 monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation',interrupted)
 with pytest.raises(ValueError,match='claim_lost'):store.prepare('s','op','Aguardo')
 with pytest.raises(ValueError,match='unavailable'):store.prepare('s','op','Aguardo')
 assert observed==[1]
 with pytest.raises(ValueError,match='recovery_cas'):store.recover_preparation('s','op')

@pytest.mark.parametrize('field,value',[('speaker',None),('effect_refs',['forged']),('fact_refs',['foreign'])])
def test_rehashed_catalog_attribution_rejected(field,value,tmp_path):
 store=setup(tmp_path);p=store.prepare('s','op','Aguardo');raw=p.model_dump(mode='json')
 raw['catalog']['utterances'][1][field]=value;raw['fingerprint_sha256']=digest({k:v for k,v in raw.items() if k!='fingerprint_sha256'})
 with pytest.raises(ValueError):Preparation.model_validate(raw)
