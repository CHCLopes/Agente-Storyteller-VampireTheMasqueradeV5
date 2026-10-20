"""Exactly one paid slot; supervisor envelope is not a multi-call authorization."""
import json
import pytest
from pydantic import SecretStr
from scripts import evaluate_hybrid_campaign_luna_l26_live as s
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_offline_manifest(tmp_path,monkeypatch):
    historical=s.GATE
    gate=json.loads(historical.read_text())
    gate['implementation_sha256']={name:s._sha((s.ROOT/name).read_bytes()) for name in s.FROZEN_FILES}
    path=tmp_path/'offline-probe-gate.json';path.write_text(json.dumps(gate))
    monkeypatch.setattr(s,'GATE',path)
    return historical


def test_real_historical_gate_is_not_rewritten_after_audit(isolated_offline_manifest,monkeypatch):
    assert json.loads(isolated_offline_manifest.read_text())['live_inference_authorized'] is False
    monkeypatch.setattr(s,'GATE',isolated_offline_manifest)
    with pytest.raises(ValueError,match='implementation_drifted'):s._gate()


def test_effective_limit_is_one_and_full_l25_stays_closed():
    gate=s._gate()
    assert gate['authorized_calls']==s.MAX_CALLS==1
    assert len(s.CASES)==1 and sum(len(case[1]) for case in s.CASES)==1
    assert gate['paid_ceiling_authorized'] is gate['live_inference_authorized'] is False
    assert gate['retry'] is gate['fallback'] is False
    full=s.ROOT/'evals/narrator/reports/hybrid-campaign-luna-l25-live-gate-2026-10-18.json'
    assert json.loads(full.read_text())['live_inference_authorized'] is False


@pytest.mark.parametrize('limit',[0,2,17])
def test_no_other_authorized_call_count_is_accepted(tmp_path,monkeypatch,limit):
    gate=s._gate();gate['authorized_calls']=limit
    path=tmp_path/'gate.json';path.write_text(json.dumps(gate))
    monkeypatch.setattr(s,'GATE',path)
    with pytest.raises(ValueError,match='gate_drifted'):s._gate()


@pytest.mark.asyncio
async def test_single_fake_call_completes_only_one_turn(tmp_path,monkeypatch):
    gate=s._gate()
    monkeypatch.setattr(s,'_gate',lambda:{**gate,'paid_ceiling_authorized':True,'live_inference_authorized':True})
    result=await s.run_batch(directory=tmp_path/'fake',key=SecretStr('synthetic-only'),adapter_factory=fake_adapter)
    assert result['status']=='completed' and result['planned_calls']==result['attempted_calls']==result['completed_turns']==1
    assert len((tmp_path/'fake/records.jsonl').read_text().splitlines())==1


def test_keyless_preflight_is_single_and_cannot_call_provider(monkeypatch,capsys):
    def denied(*_a,**_kw):pytest.fail('preflight may not dispatch')
    monkeypatch.setattr(s.CampaignLunaAdapter,'generate_structured',denied)
    monkeypatch.setattr(SecretStr,'get_secret_value',denied)
    assert s.main(['--preflight'])==0
    result=json.loads(capsys.readouterr().out.splitlines()[0])
    assert result['calls_planned']==1 and result['provider_calls']==0
