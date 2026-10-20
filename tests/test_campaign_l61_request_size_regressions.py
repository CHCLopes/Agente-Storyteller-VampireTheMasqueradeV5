"""Replay synthetic L61 outputs without provider or credential access."""
import json
from decimal import Decimal
import httpx
import pytest
from pydantic import SecretStr
from api.campaign_source_profile import CampaignSourceProposal
from api.llm.contract import StructuredGenerationResult, utc_now
from scripts import evaluate_hybrid_campaign_luna_l61_live as subject
from test_hybrid_campaign_luna_live import StubOpenAI

@pytest.mark.asyncio
@pytest.mark.parametrize('compact',[None,'v16','v17','v18','v19','v20','v21','v22','v23'])
async def test_l61_observed_history_exceeds_body_guard_before_dispatch(tmp_path, monkeypatch,compact):
    records=subject.ROOT/'eval-results/hybrid-campaign-luna-l61-3ece37fd-21c2-49be-9c85-f2cbf06edf9e/records.jsonl'
    observed=[json.loads(line)['record'] for line in records.read_text(encoding='utf-8').splitlines()]
    responses=iter(row['response'] for row in observed if row['call_made'])
    if compact:
        monkeypatch.setattr(subject,'PROMPT',subject.ROOT/f'evals/narrator/prompts/hybrid-campaign-source-{compact}.md')
    sizes=[]
    class Replay(StubOpenAI):
        async def generate_structured(self,request):
            value=next(responses,None)
            if value is None:
                return await super().generate_structured(request)
            return StructuredGenerationResult(value=CampaignSourceProposal.model_validate(value),
                evidence=self._evidence(request=request,started_at=utc_now(),effective_model=request.target.model,usage=self.usage))
    original=subject.BoundedAdapter.generate_structured
    async def capture(self,request):
        body=self.adapter._payload(request,stream=False,response_format=self.adapter._native_response_format(request))
        sizes.append(len(httpx.Request('POST','https://invalid.test/v1/responses',json=body).content))
        return await original(self,request)
    monkeypatch.setattr(subject.BoundedAdapter,'generate_structured',capture)
    gate=json.loads(subject.GATE.read_text(encoding='utf-8'))
    gate['prompt_sha256']=subject._sha(subject.PROMPT.read_bytes())
    monkeypatch.setattr(subject,'_gate',lambda:dict(gate,paid_ceiling_authorized=True,live_inference_authorized=True))
    def factory(caps,key):
        return Replay(base_url='https://invalid.test/v1',capability_set=caps,api_key=key,reasoning_effort='low')
    result=await subject.run_batch(directory=tmp_path/'replay',key=SecretStr('synthetic-only'),adapter_factory=factory)
    if compact:
        assert result['attempted_calls']==17 and result['completed_turns']==17
        assert all(size<=subject.MAX_REQUEST_BYTES for size in sizes)
        print('V16_REPLAY_MAX_BYTES='+str(max(sizes)))
    else:
        assert result['attempted_calls']==7 and result['completed_turns']==7
        assert len(sizes)==8 and sizes[-1]>subject.MAX_REQUEST_BYTES
        assert all(size<=subject.MAX_REQUEST_BYTES for size in sizes[:-1])
        print('L61_REPLAY_BLOCKED_BYTES='+str(sizes[-1]))
