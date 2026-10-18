"""Focused offline boundaries for the new two-case 768-token color probe."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from datetime import timedelta
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from api.llm.contract import LLMInvocationError
from scripts import evaluate_narrator_summary_color as m
from scripts.evaluate_narrator_summary_color import SummaryColorObservationAdapter

KEY="SYNTHETIC_COLOR_KEY_NEVER_PERSIST"
LEAK="UNTRUSTED_COLOR_REASONING_NEVER_PERSIST"
TEXT="  Uma luminária ilumina a sala de leitura vazia.  "


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    real=m.shared._CallPacer; elapsed=[0.0]
    async def sleep(seconds):elapsed[0]+=seconds
    monkeypatch.setattr(m.shared,"_CallPacer",lambda interval:real(interval,_clock=lambda:elapsed[0],_sleeper=sleep))
    return elapsed


def completion(*,value=None,model=m.GROQ_QWEN_MODEL_ID,finish="stop"):
    return {"model":model,"id":"synthetic-color","choices":[{"finish_reason":finish,
        "message":{"content":json.dumps({"summary":TEXT} if value is None else value),"reasoning":LEAK}}]}


def install(monkeypatch,pacing,handler=None,transform=None):
    state={"calls":[],"requests":[],"instances":[]}
    class Gateway(SummaryColorObservationAdapter):
        def __init__(self,**kwargs):
            case_id=kwargs["case_id"]
            async def dispatch(request):
                state["calls"].append({"case_id":case_id,"request":request,"started":pacing[0]})
                return handler(case_id,request) if handler else httpx.Response(200,json=completion())
            super().__init__(**kwargs,transport=httpx.MockTransport(dispatch));state["instances"].append(self)
        async def generate_structured(self,request):
            state["requests"].append(request);result=await super().generate_structured(request)
            return transform(result) if transform else result
        async def generate_text(self,request):pytest.fail("No diagnostics or fallback")
    monkeypatch.setattr(m,"SummaryColorObservationAdapter",Gateway)
    return state


def run():return asyncio.run(m.evaluate_probe(m.prepare_experiment(),api_key=SecretStr(KEY)))


def main_at(monkeypatch,path):
    monkeypatch.setenv("GROQ_API_KEY",KEY);monkeypatch.setattr(m,"_new_run_directory",lambda *args:path)
    return m.main(["--live","--allow-synthetic-only","--batch-id",str(uuid4())])


def artifacts(path):
    rows=[json.loads(s) for s in (path/(m.CANDIDATE_ID+".jsonl")).read_text(encoding="utf-8").splitlines()]
    doc=json.loads((path/"summary.json").read_text(encoding="utf-8"));return rows,doc


def test_preflight_keyless_exact_new_bodies_prompt_variant_and_frozen_schema(monkeypatch,capsys):
    class Environment(dict):
        def get(self,key,*args):
            if key=="GROQ_API_KEY":pytest.fail("preflight credential read")
            return super().get(key,*args)
    monkeypatch.setattr(m.os,"environ",Environment())
    monkeypatch.setattr(m,"SummaryColorObservationAdapter",lambda **kwargs:pytest.fail("preflight client"))
    p=m.prepare_experiment();dossier=json.loads(m.DOSSIER_PATH.read_text(encoding="utf-8"))
    assert tuple(c['case_id'] for c in p.cases)==('reading-room-a','reading-room-b')
    for index,case_id in enumerate(m.CASE_IDS):
        body=m._fixed_payload(m._make_request(p,index))
        assert body==dossier['requests'][index]['body']
        assert m._canonical_sha(body)==m.PROPOSED_BODY_SHA256_BY_CASE[case_id]
        assert body['max_completion_tokens']==768 and body['reasoning_effort']=='none' and body['temperature']==0.65
        assert 'include_reasoning' not in body and len(body['messages'])==2
        case=json.loads(p.packets[index].split('\n',1)[1]);assert case==p.cases[index]
        assert ''.join(u['text'] for u in case['source_units'])==case['narrative']
        assert case['origin']=='agent_authored_synthetic_case'
    assert m.PROTOCOL=='record-summary-only-v1' and m.PROMPT_VARIANT=='record-summary-budget-v1'
    assert p.metadata['inputs']['prompt']['variant']==m.PROMPT_VARIANT
    assert p.metadata['inputs']['response_schema_sha256']=='56665f9935721c6e5909de1d3f8b7fb869de6cda7cecd4af0b3591d977a15616'
    assert p.metadata['summary_generation_parameters']['max_total_output_tokens']==1536
    assert p.metadata['max_calls']==2 and p.metadata['automatic_retries']==0
    assert m.main(['--preflight'])==0
    output=capsys.readouterr();assert json.loads(output.out)==p.metadata and output.err==''


def test_two_native_calls_order_fresh_instances_literal_measurements_and_artifact_roundtrip(monkeypatch,tmp_path,pacing):
    state=install(monkeypatch,pacing);assert main_at(monkeypatch,tmp_path)==0
    rows,doc=artifacts(tmp_path);summary=doc['summary']
    assert [c['case_id'] for c in state['calls']]==list(m.CASE_IDS)
    assert len(state['instances'])==2 and state['instances'][0] is not state['instances'][1]
    assert summary==m.summarize(rows) and doc['inputs']==m.prepare_experiment().metadata['inputs']
    for index,row in enumerate(rows):
        assert row['response_structure']=={'summary':TEXT} and row['summary_text']==TEXT
        assert row['instruction_measurements']==m.contract.measure_summary_words(TEXT)
        assert m._canonical_sha(json.loads(state['calls'][index]['request'].content))==m.PROPOSED_BODY_SHA256_BY_CASE[row['case_id']]
        assert row['kind']=='summary_color_call' and row['route_status']=='verified'
    assert summary['calls_made']==summary['schema_valid']==2 and summary['cases_skipped']==0
    assert [v['case_id'] for v in summary['case_measurements']]==list(m.CASE_IDS)
    assert summary['provider_observation'] is None and len(summary['provider_observations'])==2
    assert summary['usage_aggregate']['status']==summary['cost_aggregate']['status']=='unavailable'
    assert all(row['provider_observation']['usage']['reasoning_tokens'] is None for row in rows)
    assert summary['semantic_fidelity_review']=={'status':'not_performed','approval':None}
    assert summary['runtime_promoted'] is summary['automated_gates_passed'] is False
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_initial_and_between_wait_deadlines_after_checks(monkeypatch,pacing):
    start=m.utc_now();monkeypatch.setattr(m,'utc_now',lambda:start+timedelta(seconds=pacing[0]))
    original=m._check_prepared;calls=[0]
    def check(p):
        original(p);calls[0]+=1
        if calls[0] in {3,5}:pacing[0]+=2
    monkeypatch.setattr(m,'_check_prepared',check)
    def handler(case_id,request):pacing[0]+=1;return httpx.Response(200,json=completion())
    state=install(monkeypatch,pacing,handler);run()
    assert [c['started'] for c in state['calls']]==[62,124]
    assert [r.deadline for r in state['requests']]==[start+timedelta(seconds=122),start+timedelta(seconds=184)]


@pytest.mark.parametrize('mutation',['3072','old_case'])
def test_adapter_refuses_old_body_and_remains_single_use(mutation):
    p=m.prepare_experiment();calls=[]
    def handler(request):calls.append(request);return httpx.Response(200,json=completion())
    adapter=SummaryColorObservationAdapter(case_id=m.CASE_IDS[0],base_url=m.GROQ_OFFICIAL_BASE_URL,
        capability_set=m.shared._capabilities(p.candidate,p.target),api_key=SecretStr(KEY),reasoning_effort='none',transport=httpx.MockTransport(handler))
    exact=m._make_request(p,0)
    if mutation=='3072':changed=exact.model_copy(update={'parameters':exact.parameters.model_copy(update={'max_output_tokens':3072})})
    else:
        old=json.loads((m.PROJECT_ROOT/'evals/narrator/reports/record-summary-attachment-dossier-21cf338b-2026-09-07.json').read_text(encoding='utf-8'))['requests'][0]['body']['messages'][1]['content']
        changed=exact.model_copy(update={'messages':(exact.messages[0],exact.messages[1].model_copy(update={'content':old}))})
    with pytest.raises(LLMInvocationError):asyncio.run(adapter.generate_structured(changed))
    assert calls==[]
    asyncio.run(adapter.generate_structured(exact))
    with pytest.raises(LLMInvocationError):asyncio.run(adapter.generate_structured(m._make_request(p,0)))
    assert len(calls)==1


@pytest.mark.parametrize('mutation',['order','bool_as_zero'])
def test_prepared_mutation_blocks_dispatch(monkeypatch,mutation):
    p=m.prepare_experiment()
    if mutation=='order':p=replace(p,cases=tuple(reversed(p.cases)))
    else:p.metadata['runtime_promoted']=0
    monkeypatch.setattr(m,'SummaryColorObservationAdapter',lambda **kwargs:pytest.fail('gateway after drift'))
    with pytest.raises(ValueError):asyncio.run(m.evaluate_probe(p,api_key=SecretStr(KEY)))


def test_dossier_drift_during_wait_stops_before_gateway(monkeypatch):
    p=m.prepare_experiment()
    class Pacer:
        def __init__(self,interval):self._clock=lambda:0.0
        async def before_call(self,label):monkeypatch.setattr(m,'DOSSIER_SHA256','0'*64)
    monkeypatch.setattr(m.shared,'_CallPacer',Pacer)
    monkeypatch.setattr(m,'SummaryColorObservationAdapter',lambda **kwargs:pytest.fail('gateway after dossier drift'))
    with pytest.raises(ValueError):asyncio.run(m.evaluate_probe(p,api_key=SecretStr(KEY)))


@pytest.mark.parametrize('failure',['429','route','schema','length'])
def test_first_failure_stops_pair_and_never_retains_unvalidated_summary(monkeypatch,pacing,failure):
    def handler(case_id,request):
        assert case_id==m.CASE_IDS[0]
        if failure=='429':return httpx.Response(429,json={'error':{'code':'rate_limit_exceeded','message':LEAK}})
        return httpx.Response(200,json=completion(model='other' if failure=='route' else m.GROQ_QWEN_MODEL_ID,
            value={'summary':True} if failure=='schema' else None,finish='length' if failure=='length' else 'stop'))
    state=install(monkeypatch,pacing,handler);rows=run();summary=m.summarize(rows)
    assert len(state['calls'])==1 and rows[0]['schema_valid'] is False
    assert rows[1]=={'kind':'summary_color_skip','case_id':m.CASE_IDS[1],'call_made':False,'skipped_reason':'previous_operational_failure'}
    assert not {'response_structure','summary_text','instruction_measurements'}.intersection(rows[0])
    assert all(v['instruction_measurements'] is None for v in summary['case_measurements'])
    assert summary['process_exit_code']==(2 if failure=='429' else 1)
    assert summary['provider_observation']==summary['provider_observations'][0]['observation']
    assert LEAK not in json.dumps(rows)


def test_local_measurement_failure_retains_valid_A_and_skips_B(monkeypatch,tmp_path,pacing):
    state=install(monkeypatch,pacing)
    def fail(text):raise RuntimeError(LEAK)
    monkeypatch.setattr(m.contract,'measure_summary_words',fail)
    assert main_at(monkeypatch,tmp_path)==3
    rows,doc=artifacts(tmp_path)
    assert len(state['calls'])==1 and rows[0]['schema_valid'] is True
    assert rows[0]['summary_text']==TEXT and rows[0]['response_structure']=={'summary':TEXT}
    assert rows[0]['local_error']=={'code':'local_summary_color_failure'} and rows[1]['call_made'] is False
    assert doc['summary']['case_measurements'][0]['instruction_measurements'] is None
    assert doc['summary']['operational_probe_passed'] is False and LEAK not in json.dumps(rows)


@pytest.mark.parametrize('when',['wait','inflight'])
def test_cancel_A_records_exact_call_or_skip_inventory(monkeypatch,tmp_path,pacing,when):
    if when=='wait':
        class Pacer:
            def __init__(self,interval):self._clock=lambda:0.0
            async def before_call(self,label):raise asyncio.CancelledError()
        monkeypatch.setattr(m.shared,'_CallPacer',Pacer)
    def handler(case_id,request):raise asyncio.CancelledError()
    state=install(monkeypatch,pacing,handler);assert main_at(monkeypatch,tmp_path)==130
    rows,doc=artifacts(tmp_path)
    assert len(state['calls'])==(0 if when=='wait' else 1)
    assert tuple(r['case_id'] for r in rows)==m.CASE_IDS and rows[1]['call_made'] is False
    assert doc['summary']==m.summarize(rows,status='cancelled')
    assert doc['summary']['cases_skipped']==(2 if when=='wait' else 1)


def test_second_failure_preserves_A_and_never_makes_a_third_call(monkeypatch,pacing):
    def handler(case_id,request):
        return httpx.Response(200,json=completion()) if case_id==m.CASE_IDS[0] else httpx.Response(429,json={'error':{'message':LEAK}})
    state=install(monkeypatch,pacing,handler);rows=run();summary=m.summarize(rows)
    assert len(state['calls'])==2 and summary['cases_skipped']==0 and summary['process_exit_code']==2
    assert rows[0]['summary_text']==TEXT and rows[1]['schema_valid'] is False
    assert summary['case_measurements'][0]['instruction_measurements'] is not None
    assert summary['case_measurements'][1]['instruction_measurements'] is None


def test_word_limit_false_does_not_block_B_or_change_operational_success(monkeypatch,pacing):
    text=' '.join(['palavra']*32)
    state=install(monkeypatch,pacing,lambda case_id,request:httpx.Response(200,json=completion(value={'summary':text})))
    rows=run();summary=m.summarize(rows)
    assert len(state['calls'])==2 and summary['process_exit_code']==0
    assert all(v['instruction_measurements']['within_word_limit'] is False for v in summary['case_measurements'])
    assert all(r['summary_text']==text for r in rows) and summary['semantic_fidelity_review']['approval'] is None


@pytest.mark.parametrize('mutation',['order','skip_then_call','failed_then_call','missing_A_measurement'])
def test_summary_refuses_impossible_sequence(mutation):
    rows=[{'kind':'summary_color_call','case_id':case_id,'call_made':True,'schema_valid':True,'route_status':'verified',
        'summary_text':TEXT,'instruction_measurements':m.contract.measure_summary_words(TEXT)} for case_id in m.CASE_IDS]
    if mutation=='order':rows.reverse()
    elif mutation=='skip_then_call':rows[0].update(kind='summary_color_skip',call_made=False)
    elif mutation=='failed_then_call':rows[0]['schema_valid']=False
    else:rows[0].pop('instruction_measurements')
    with pytest.raises(ValueError):m.summarize(rows)


def test_forged_model_revalidation_stops_pair(monkeypatch,pacing):
    forged=m.contract.SummaryOnlyProposal.model_construct(summary=True)
    state=install(monkeypatch,pacing,transform=lambda result:result.model_copy(update={'value':forged}))
    rows=run();assert len(state['calls'])==1 and rows[0]['schema_valid'] is False
    assert rows[0]['schema_error']=={'code':'summary_color_schema_invalid'} and 'summary_text' not in rows[0]
    assert rows[1]['call_made'] is False
