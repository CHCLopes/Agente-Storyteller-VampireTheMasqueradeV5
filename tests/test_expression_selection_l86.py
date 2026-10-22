"""L86 harness gates, fake pairing and first-failure behavior, no inference."""
import json
import pytest
from pydantic import SecretStr
from scripts import evaluate_hybrid_campaign_luna_l86_live as lot
from api.experiments.expression_selection.transport import SelectionResponse

@pytest.mark.asyncio
async def test_complete_keyless_preflight(monkeypatch):
 def forbidden(*a,**kw):pytest.fail('credential or real adapter used during preflight')
 monkeypatch.setattr(SecretStr,'get_secret_value',forbidden)
 monkeypatch.setattr(lot.ResponsesSelectionGateway,'select',forbidden)
 result=await lot.preflight()
 assert result['completed_pairs']==17 and result['provider_calls']==0 and result['model_selections']==17
 assert result['max_request_bytes']<20000

@pytest.mark.asyncio
async def test_invalid_first_choice_stops_once(tmp_path):
 class Invalid(lot.SyntheticSelectionGateway):
  async def select(self,request):
   response=await super().select(request)
   self.raw_output_text='{"utterance":"foreign","atmosphere":"none","layout":"inline"}'
   return SelectionResponse(raw=self.raw_output_text,evidence=response.evidence)
 result=await lot.run_batch(tmp_path/'bad',adapter_factory=lambda caps,key:Invalid(base_url='https://offline.invalid/v1',capability_set=caps,api_key=SecretStr(''),reasoning_effort='low'))
 assert result['status']=='stopped' and result['model_selections']==1 and result['completed_pairs']==0
 assert result['provider_calls']==0

@pytest.mark.asyncio
async def test_closed_live_gate_prevents_latch(tmp_path,monkeypatch):
 latch=tmp_path/'once';monkeypatch.setattr(lot,'LOCK',latch)
 with pytest.raises(ValueError,match='closed'):await lot.run_batch(tmp_path/'live',live=True,key=SecretStr('synthetic'))
 assert not latch.exists()

def test_manifest_support_drift_fails(tmp_path,monkeypatch):
 value=json.loads(lot.GATE.read_text());value['supporting_sha256'][lot.SUPPORTING_FILES[0]]='0'*64
 path=tmp_path/'gate.json';path.write_text(json.dumps(value));monkeypatch.setattr(lot,'GATE',path)
 with pytest.raises(ValueError,match='source_drift'):lot.gate()
