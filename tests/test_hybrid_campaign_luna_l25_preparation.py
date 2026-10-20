"""Prospective L25 is isolated and closed; executed L24 evidence is immutable."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l25_live as subject
from scripts import evaluate_hybrid_campaign_luna_l24_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_offline_manifest(tmp_path,monkeypatch):
    real=subject.GATE
    gate=json.loads(real.read_text())
    gate['implementation_sha256']={name:subject._sha((subject.ROOT/name).read_bytes()) for name in subject.FROZEN_FILES}
    path=tmp_path/'offline-current-gate.json';path.write_text(json.dumps(gate))
    monkeypatch.setattr(subject,'GATE',path)
    return real


def test_real_l25_remains_closed_and_needs_fresh_manifest(isolated_offline_manifest,monkeypatch):
    assert json.loads(isolated_offline_manifest.read_text())['live_inference_authorized'] is False
    monkeypatch.setattr(subject,'GATE',isolated_offline_manifest)
    with pytest.raises(ValueError,match='implementation_drifted'):subject._gate()


def test_l25_closed_gate_and_executed_l24_runtime_preserved():
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L25' and len(gate['implementation_sha256']) == 22
    assert gate['paid_ceiling_authorized'] is gate['live_inference_authorized'] is False
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert gate['max_calls'] == 17 and gate['max_estimated_usd'] == '0.15'
    assert subject.PROMPT.name == 'hybrid-campaign-source-v6.md' and historical.PROMPT.name == 'hybrid-campaign-source-v6.md'
    assert subject.LOT_LOCK != historical.LOT_LOCK and subject.KEY_ENV != historical.KEY_ENV
    assert hashlib.sha256(historical.GATE.read_bytes()).hexdigest() == '911d8d07e039d6e4ee609472fea011c14eeb06045eb06737a197a45298a60fb8'
    with pytest.raises(ValueError, match='implementation_drifted'):
        historical._gate()


@pytest.mark.parametrize('old,new', [
    ('scripts/evaluate_hybrid_campaign_luna_l24_live.py', 'scripts/evaluate_hybrid_campaign_luna_l25_live.py'),
    ('scripts/preflight_hybrid_campaign_luna_l24.py', 'scripts/preflight_hybrid_campaign_luna_l25.py'),
    ('scripts/run_hybrid_campaign_luna_l24_live.ps1', 'scripts/run_hybrid_campaign_luna_l25_live.ps1'),
])
def test_l25_changes_only_lot_identity(old, new):
    expected = (subject.ROOT / old).read_text(encoding='utf-8').replace('L24','L25').replace('_l24','_l25').replace('-l24','-l25').replace('source-v5','source-v6')
    assert (subject.ROOT / new).read_text(encoding='utf-8').splitlines() == expected.splitlines()


@pytest.mark.parametrize('field', ['retry', 'fallback', 'synthetic_only', 'admission_automatic'])
def test_l25_rejects_protocol_drift(field, tmp_path, monkeypatch):
    gate = subject._gate()
    gate[field] = not gate[field]
    path = tmp_path / 'mutated.json'
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    with pytest.raises(ValueError, match='gate_drifted'):
        subject._gate()


def test_keyless_cli_has_no_dispatch_or_credential_access(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail('preflight may not dispatch or read credential')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    lines = capsys.readouterr().out.splitlines()
    result = json.loads(lines[0])
    assert result['lot_id'] == 'HYP-007-L25'
    assert result['provider_calls'] == 0 and result['calls_planned'] == 17
    assert result['max_request_bytes_observed'] <= 20000
    assert 'CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada).' in lines


@pytest.mark.asyncio
async def test_live_denial_precedes_credential_adapter_latch_and_output(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('closed gate must precede credential and adapter')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, '__init__', forbidden)
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'blocked', key=SecretStr('synthetic-only'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'blocked').exists()


@pytest.mark.asyncio
async def test_fake_full_schedule_preserves_closed_real_gate(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    result = await subject.run_batch(directory=tmp_path / 'fake', key=SecretStr('synthetic-only'),
                                     adapter_factory=fake_adapter)
    assert result['status'] == 'completed' and result['completed_turns'] == 17
    assert json.loads(subject.GATE.read_text(encoding='utf-8'))['live_inference_authorized'] is False


@pytest.mark.asyncio
async def test_latch_blocks_concurrent_or_repeated_batch(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    latch = tmp_path / 'once'
    latch.mkdir()
    monkeypatch.setattr(subject, 'LOT_LOCK', latch)
    with pytest.raises(FileExistsError):
        await subject.run_batch(directory=tmp_path / 'second', key=SecretStr('synthetic-only'))
    assert not (tmp_path / 'second').exists()
