"""One-shot A2 comparison, isolated synthetic sessions and strict paid gate."""
from __future__ import annotations
import argparse
import asyncio
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID,uuid4
os.environ['STORYTELLER_DISABLE_DOTENV']='1'
import httpx
from pydantic import SecretStr
from api import rules_service
from api.experiments.expression_selection.contract import Choice,SelectionConfig,digest,json_text
from api.experiments.expression_selection.store import SelectionStore
from api.experiments.expression_selection.service import execute,build_request,SYSTEM_PROMPT
from api.experiments.expression_selection.transport import SelectionResponse
from api.llm.contract import (CancellationToken,CapabilityDescriptor,CapabilitySet,CapabilitySupport,
 GenerationParameters,LLMInvocationError,LLMTarget,MeasurementStatus,TokenUsage,utc_now)
from api.rules_service import PlayerSheetModel
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter
from scripts.preflight_hybrid_campaign_luna_l85 import CASES,_fixed_resolution
from scripts.report_luna_test_cost import summarize,display
from scripts.run_campaign_source_offline_trial import _initial_state
ROOT=Path(__file__).resolve().parents[1]
LOT_ID='HYP-007-L86'
GATE=ROOT/'evals/narrator/reports/hybrid-campaign-luna-l86-live-gate-2026-10-22.json'
LOCK=ROOT/'eval-results/hybrid-campaign-luna-l86-once'
TARGET=LLMTarget(profile='campaign-luna-hyp-007',provider='OpenAI',model='gpt-5.6-luna')
ACTUAL_OUTPUT_TOKENS=256
MAX_CALLS=17
MAX_REQUEST_BYTES=20000
LIMIT=Decimal('0.15')
INPUT_PRICE=Decimal('0.20');OUTPUT_PRICE=Decimal('1.20')
KEY_ENV='STORYTELLER_OPENAI_HYP007_L86_KEY'
FROZEN_FILES=(
 'scripts/evaluate_hybrid_campaign_luna_l86_live.py','scripts/preflight_hybrid_campaign_luna_l86.py',
 'api/experiments/expression_selection/contract.py','api/experiments/expression_selection/store.py',
 'api/experiments/expression_selection/service.py','api/experiments/expression_selection/transport.py',
 'api/campaign_progression_service.py','api/campaign_progression_catalog.py','api/campaign_expression_rendering.py',
 'api/rules_service.py','api/llm/contract.py','api/llm/adapters/openai_compatible.py',
 'scripts/evaluate_openai_luna_low_live.py','scripts/report_luna_test_cost.py','api/scene_service.py',
 'api/scene_resolution_service.py','api/scene_direction_catalog.py','api/scene_director_service.py',
 'api/narrative_source_action_producer.py','scripts/preflight_hybrid_campaign_luna_l85.py',
 'scripts/run_campaign_source_offline_trial.py','api/catalog_service.py')
SUPPORTING_FILES=('api/experiments/__init__.py','api/experiments/expression_selection/__init__.py',
 'api/turn_models.py','api/catalog_models.py','api/core/config.py','api/llm/structure_diagnostics.py',
 'api/narrative_source_preparation.py','api/narrative_source_context.py','api/narrative_source_input.py','api/local_request_security.py')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def gate():
 value=json.loads(GATE.read_text(encoding='utf-8'))
 expected={'hypothesis_id':'HYP-007','lot_id':LOT_ID,'target_model':TARGET.model,'reasoning_effort':'low',
 'max_calls':17,'max_output_tokens_per_call':768,'actual_max_output_tokens_per_call':ACTUAL_OUTPUT_TOKENS,
 'max_request_bytes':MAX_REQUEST_BYTES,'max_estimated_usd':str(LIMIT),'retry':False,'fallback':False,
 'admission_automatic':False,'synthetic_only':True,'profile':'campaign-selection-local-v1'}
 if any(type(value.get(k)) is not type(v) or value[k]!=v for k,v in expected.items()):raise ValueError('selection_live_gate_drift')
 if value.get('prompt_sha256')!=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest():raise ValueError('selection_live_prompt_drift')
 for key,files in [('implementation_sha256',FROZEN_FILES),('supporting_sha256',SUPPORTING_FILES)]:
  if set(value.get(key,{}))!=set(files) or any(value[key][name]!=sha(ROOT/name) for name in files):raise ValueError('selection_live_source_drift')
 return value

def require_live():
 value=gate()
 if value.get('paid_ceiling_authorized') is not True or value.get('live_inference_authorized') is not True:raise ValueError('selection_live_closed')

class ResponsesSelectionGateway(OpenAIResponsesAdapter):
 raw_output_text=None
 def capabilities(self,target):
  return self._capability_set if target==self._capability_set.target else CapabilitySet(target=target,descriptors=())
 def _output_text(self,payload):
  value=super()._output_text(payload);self.raw_output_text=value;return value
 async def select(self,request):
  result=await self.generate_structured(request)
  return SelectionResponse(raw=self.raw_output_text,evidence=result.evidence)

class SyntheticSelectionGateway(ResponsesSelectionGateway):
 async def select(self,request):
  self.raw_output_text='{"utterance":"variant","atmosphere":"none","layout":"paragraph"}'
  usage=TokenUsage(status=MeasurementStatus.REPORTED,input_tokens=500,output_tokens=50,total_tokens=550,source='synthetic preflight')
  evidence=self._evidence(request=request,started_at=utc_now(),effective_model=TARGET.model,usage=usage)
  return SelectionResponse(raw=self.raw_output_text,evidence=evidence)

class BoundedGateway:
 def __init__(self,adapter,row,ledger,*,live,key):self.adapter,self.row,self.ledger,self.live,self.key=adapter,row,ledger,live,key
 def capabilities(self,target):return self.adapter.capabilities(target)
 async def select(self,request):
  if self.row['select_called']:raise ValueError('selection_duplicate_dispatch')
  if request.target!=TARGET or request.response_model is not Choice or request.parameters.max_output_tokens!=ACTUAL_OUTPUT_TOKENS or request.parameters.temperature is not None:raise ValueError('selection_request_drift')
  body=self.adapter._payload(request,stream=False,response_format=self.adapter._native_response_format(request))
  encoded=httpx.Request('POST','https://api.openai.com/v1/responses',json=body).content
  if (body.get('model')!=TARGET.model or body.get('store') is not False or body.get('tools') or body.get('stream') is not False
   or body.get('reasoning')!={'effort':'low'} or body.get('max_output_tokens')!=ACTUAL_OUTPUT_TOKENS or len(encoded)>MAX_REQUEST_BYTES):raise ValueError('selection_body_drift')
  worst=(Decimal(len(encoded))*INPUT_PRICE+Decimal(ACTUAL_OUTPUT_TOKENS)*OUTPUT_PRICE)/Decimal(1000000)
  if self.ledger['spent']+worst>LIMIT:raise ValueError('selection_cost_guard')
  if self.live:require_live()
  self.row.update(select_called=True,call_made=self.live,request_bytes=len(encoded),request_sha256=hashlib.sha256(encoded).hexdigest())
  try:response=await self.adapter.select(request)
  except LLMInvocationError as exc:
   self.row['evidence']=exc.error.evidence.model_dump(mode='json') if exc.error.evidence else None
   self.row['provider_error_code']=exc.error.code
   raise
  finally:
   raw=self.adapter.raw_output_text
   if isinstance(raw,str):
    secret=self.key.get_secret_value() if self.live else ''
    if len(secret)>=12 and secret in raw:self.row['raw_output_text']=None;raise ValueError('credential_echo_blocked')
    self.row['raw_output_text']=raw
  evidence=response.evidence;self.row['evidence']=evidence.model_dump(mode='json')
  p=evidence.provenance
  if (p.requested_target!=TARGET or p.effective_provider.value!='OpenAI' or p.effective_provider.source.value!='observed'
   or p.effective_model.value!=TARGET.model or p.effective_model.source.value!='reported'):raise ValueError('selection_route_mismatch')
  usage=evidence.usage
  if any(type(n) is not int or n<0 for n in (usage.input_tokens,usage.output_tokens)):raise ValueError('selection_usage_missing')
  if self.live:self.ledger['spent']+=(Decimal(usage.input_tokens)*INPUT_PRICE+Decimal(usage.output_tokens)*OUTPUT_PRICE)/Decimal(1000000)
  return response

async def run_batch(directory,*,live=False,key=None,adapter_factory=None):
 if live:
  require_live();LOCK.mkdir(exist_ok=False)
 if directory.exists():raise ValueError('selection_batch_exists')
 directory.mkdir(parents=True)
 store=SelectionStore(directory/'sessions.sqlite3',create=True)
 caps=CapabilitySet(target=TARGET,descriptors=tuple(CapabilityDescriptor(name=n,support=CapabilitySupport.NATIVE) for n in ('text_generation','structured_generation')))
 sheet=PlayerSheetModel.model_validate(_initial_state()['player_sheet'])
 original=rules_service.calculate_resolution;rows=[];stop=None;ledger={'spent':Decimal(0)}
 try:
  for case_id,actions,rules,outcome in CASES:
   rules_service.calculate_resolution=lambda *a,**kw:_fixed_resolution(case_id=='CAMP-EVAL-06')
   for mode in ('deterministic','model'):
    store.create_session(mode+'-'+case_id,config=SelectionConfig(mode=mode,target=TARGET if mode=='model' else None,
      parameters=GenerationParameters(max_output_tokens=ACTUAL_OUTPUT_TOKENS)),sheet=sheet)
   for number,(action,rule) in enumerate(zip(actions,rules),1):
    row={'case_id':case_id,'turn':number,'rule':rule,'player_input':action,'select_called':False,'call_made':False,'status':'prepared'}
    try:
     presentations={};states={}
     for mode in ('deterministic','model'):
      session_id=mode+'-'+case_id;operation='turn-'+str(number);attempt='attempt-'+str(number)
      preparation=store.prepare(session_id,operation,action)
      if preparation.effect.rule_id!=rule:raise ValueError('selection_rule_mismatch')
      if mode=='model':
       row['preparation']=preparation.model_dump(mode='json')
       adapter=(adapter_factory(caps,key) if adapter_factory else (ResponsesSelectionGateway if live else SyntheticSelectionGateway)(base_url='https://api.openai.com/v1',capability_set=caps,api_key=key or SecretStr(''),reasoning_effort='low'))
       bounded=BoundedGateway(adapter,row,ledger,live=live,key=key)
      result=await execute(store=store,session_id=session_id,operation_id=operation,attempt_id=attempt,
       deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),gateway=bounded if mode=='model' else None)
      if result.status!='completed':raise ValueError(result.error_code or 'selection_turn_failed')
      presentations[mode]=result.presentation.model_dump(mode='json');states[mode]=store.session(session_id).state.model_dump(mode='json')
      replay=await execute(store=SelectionStore(store.path),session_id=session_id,operation_id=operation,attempt_id=attempt,
       deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
      if replay.presentation!=result.presentation:raise ValueError('selection_live_replay_mismatch')
     if states['deterministic']!=states['model']:raise ValueError('selection_state_divergence')
     if presentations['deterministic']['realized_effects']!=presentations['model']['realized_effects']:raise ValueError('selection_effect_divergence')
     row.update(status='completed',presentations=presentations,state_after=states['model'])
    except Exception as exc:
     # Fixed product codes only; exception payload is not persisted.
     code=str(exc)
     safe=code if code.startswith('selection_') and len(code)<=80 and all(ch in 'abcdefghijklmnopqrstuvwxyz_' for ch in code) else 'selection_lot_turn_failed'
     row['status']='stopped';row['error_code']=safe;stop=safe
    rows.append(row)
    with (directory/'records.jsonl').open('a',encoding='utf-8') as handle:handle.write(json_text({'record':row})+'\n')
    if stop:break
   if stop:break
   if any(store.session(mode+'-'+case_id).state.outcome!=outcome for mode in ('model','deterministic')):stop='selection_outcome_mismatch';break
 finally:
  rules_service.calculate_resolution=original
  cost=summarize(rows,settled=True) if live else summarize([],no_dispatch=True)
  result={'lot_id':LOT_ID,'status':'completed' if not stop and len(rows)==17 else 'stopped','stop_reason':stop,
   'provider_calls':sum(bool(r['call_made']) for r in rows),'model_selections':sum(bool(r['select_called']) for r in rows),
   'completed_pairs':sum(r['status']=='completed' for r in rows),'cost':cost,
   'records_sha256':sha(directory/'records.jsonl') if rows else None,
   'max_request_bytes':max((r.get('request_bytes',0) for r in rows),default=0)}
  (directory/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return result

async def preflight():
 gate()
 with tempfile.TemporaryDirectory(prefix='selection-l86-preflight-') as tmp:
  result=await run_batch(Path(tmp)/'batch')
  if result['status']!='completed' or result['provider_calls']!=0:raise ValueError('selection_preflight_failed')
  return result

def main(argv=None):
 parser=argparse.ArgumentParser();m=parser.add_mutually_exclusive_group(required=True);m.add_argument('--preflight',action='store_true');m.add_argument('--live',action='store_true');parser.add_argument('--batch-id');args=parser.parse_args(argv)
 if args.preflight:
  print(json.dumps(asyncio.run(preflight()),ensure_ascii=False));return 0
 require_live()
 if not args.batch_id or str(UUID(args.batch_id))!=args.batch_id:raise ValueError('selection_batch_id')
 asyncio.run(preflight())
 key_text=os.environ.pop(KEY_ENV,'')
 if not key_text:raise ValueError('selection_credential_missing')
 key=SecretStr(key_text);key_text=''
 result=asyncio.run(run_batch(ROOT/'eval-results'/('hybrid-campaign-luna-l86-'+args.batch_id),live=True,key=key))
 display(result['cost']);return 0 if result['status']=='completed' else 2

if __name__=='__main__':raise SystemExit(main())
