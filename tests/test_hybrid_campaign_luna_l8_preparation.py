"""Prospective L8 is isolated and closed; executed L7 evidence is immutable."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l8_live as subject
from scripts import evaluate_hybrid_campaign_luna_l7_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Exercise stubs without rebasing the executed L8 manifest."""
    original = subject.GATE
    gate = json.loads(original.read_text(encoding='utf-8'))
    gate['implementation_sha256'] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    path = tmp_path / original.name
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return original


def test_executed_l8_rejects_corrected_runtime(isolated_current_manifest, monkeypatch):
    assert hashlib.sha256(isolated_current_manifest.read_bytes()).hexdigest() == '67e56e9ac2c6018f6045263a3cfef63105e6ed975c2649e0c1ca2f0c5c842d5c'
    monkeypatch.setattr(subject, 'GATE', isolated_current_manifest)
    with pytest.raises(ValueError, match='implementation_drifted'):
        subject._gate()


def test_l8_closed_gate_and_executed_l7_runtime_drift():
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L8' and len(gate['implementation_sha256']) == 22
    assert gate['paid_ceiling_authorized'] is gate['live_inference_authorized'] is False
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert gate['max_calls'] == 17 and gate['max_estimated_usd'] == '0.15'
    assert subject.PROMPT == historical.PROMPT
    assert subject.LOT_LOCK != historical.LOT_LOCK and subject.KEY_ENV != historical.KEY_ENV
    assert hashlib.sha256(historical.GATE.read_bytes()).hexdigest() == 'dc2d96b72df8fba484474b3ba73a5e1cbe0e062324e0222436c274018be2dcd4'
    with pytest.raises(ValueError, match='implementation_drifted'):
        historical._gate()


@pytest.mark.parametrize('old,new', [
    ('scripts/evaluate_hybrid_campaign_luna_l7_live.py', 'scripts/evaluate_hybrid_campaign_luna_l8_live.py'),
    ('scripts/preflight_hybrid_campaign_luna_l7.py', 'scripts/preflight_hybrid_campaign_luna_l8.py'),
    ('scripts/run_hybrid_campaign_luna_l7_live.ps1', 'scripts/run_hybrid_campaign_luna_l8_live.ps1'),
])
def test_l8_changes_only_lot_identity(old, new):
    expected = (subject.ROOT / old).read_text(encoding='utf-8').replace('L7','L8').replace('_l7','_l8').replace('-l7','-l8')
    assert (subject.ROOT / new).read_text(encoding='utf-8').splitlines() == expected.splitlines()


@pytest.mark.parametrize('field', ['retry', 'fallback', 'synthetic_only', 'admission_automatic'])
def test_l8_rejects_protocol_drift(field, tmp_path, monkeypatch):
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
    assert result['lot_id'] == 'HYP-007-L8'
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
