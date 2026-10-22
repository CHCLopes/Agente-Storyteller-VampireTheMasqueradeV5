"""Offline transport, gates and evidence for the first A1 v2 lot."""
import json
from copy import deepcopy
from decimal import Decimal
import pytest
from pydantic import SecretStr
from api.llm.contract import StructuredGenerationResult, TokenUsage, MeasurementStatus, utc_now
from scripts import evaluate_hybrid_campaign_luna_l84_live as subject

class Stub(subject.CampaignLunaAdapter):
    invalid = False
    usage = TokenUsage(status=MeasurementStatus.REPORTED, input_tokens=500,
                       output_tokens=100, total_tokens=600, source='synthetic test')
    async def generate_structured(self, request):
        plan = json.loads(request.messages[1].content)['context']['realization_plan']
        raw = {'protocol': 'campaign-source-expression-v2',
               'plan_sha256': '0'*64 if self.invalid else plan['plan_sha256'],
               'slots': [{'slot_id': s['slot_id'], 'text': ''} for s in plan['slots']]}
        self.raw_output_text = json.dumps(raw, ensure_ascii=False)
        return StructuredGenerationResult(value=request.response_model.model_validate(raw),
            evidence=self._evidence(request=request, started_at=utc_now(),
                                    effective_model=request.target.model, usage=self.usage))

def factory(caps, key):
    return Stub(base_url='https://invalid.test/v1', capability_set=caps, api_key=key, reasoning_effort='low')

@pytest.fixture
def gate(tmp_path, monkeypatch):
    value = json.loads(subject.GATE.read_text(encoding='utf-8'))
    value.update(paid_ceiling_authorized=False, live_inference_authorized=False)
    for key, files in [('implementation_sha256', subject.FROZEN_FILES), ('supporting_sha256', subject.SUPPORTING_FILES)]:
        value[key] = {n: subject._sha((subject.ROOT/n).read_bytes()) for n in files}
    path = tmp_path/'gate.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return subject._gate()

def test_schema_nested_required_and_no_defaults():
    adapter = factory(None, SecretStr('synthetic-only'))
    schema = adapter._native_response_format(type('Request', (), {'response_model': subject.CampaignExpressionProposal})())['schema']
    def check(node):
        if isinstance(node, dict):
            assert 'default' not in node
            if 'properties' in node:
                assert set(node['required']) == set(node['properties'])
                assert node['additionalProperties'] is False
            for value in node.values(): check(value)
        elif isinstance(node, list):
            for value in node: check(value)
    check(schema)

def test_no_credential_or_provider_in_preflight(gate, monkeypatch, capsys):
    def forbidden(*a, **kw): pytest.fail('credential or network in preflight')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    data=json.loads(capsys.readouterr().out.splitlines()[0])
    assert data['provider_calls']==0 and data['calls_planned']==17
    assert data['max_request_bytes_observed']<=20000

@pytest.mark.asyncio
async def test_full_fake_lot_retains_plan_raw_response_and_presentation(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(subject, '_gate', lambda: dict(gate, paid_ceiling_authorized=True, live_inference_authorized=True))
    result=await subject.run_batch(directory=tmp_path/'fake', key=SecretStr('synthetic-only'), adapter_factory=factory)
    assert result['status']=='completed' and result['completed_turns']==17, result
    rows=[row['record'] for row in subject.read_records(tmp_path/'fake')]
    assert all(row['raw_output_text'] and row['player_text'] and row['realization_plan'] for row in rows)
    assert all(row['presentation']['expression']['plan_sha256']==row['realization_plan']['plan_sha256'] for row in rows)
    assert sum(row['call_made'] for row in rows)==17

@pytest.mark.asyncio
async def test_first_invalid_hash_stops_without_retry(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(subject, '_gate', lambda: dict(gate, paid_ceiling_authorized=True, live_inference_authorized=True))
    monkeypatch.setattr(Stub, 'invalid', True)
    result=await subject.run_batch(directory=tmp_path/'bad', key=SecretStr('synthetic-only'), adapter_factory=factory)
    assert result['status']=='stopped' and result['attempted_calls']==1 and result['completed_turns']==0
    rows=subject.read_records(tmp_path/'bad')
    assert len(rows)==1 and rows[0]['record']['raw_output_text']

@pytest.mark.asyncio
async def test_closed_gate_prevents_latch_and_provider(gate, tmp_path, monkeypatch):
    latch=tmp_path/'once'; monkeypatch.setattr(subject, 'LOT_LOCK', latch)
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path/'blocked', key=SecretStr('synthetic-only'))
    assert not latch.exists()

def test_supporting_drift_rejected(gate):
    value=deepcopy(gate)
    value['supporting_sha256'][subject.SUPPORTING_FILES[0]]='0'*64
    subject.GATE.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='supporting_drifted'): subject._gate()
