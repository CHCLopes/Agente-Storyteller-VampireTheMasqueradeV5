"""Prospective L19 is isolated and closed; executed L18 evidence is immutable."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l19_live as subject
from scripts import evaluate_hybrid_campaign_luna_l18_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


def test_l19_closed_gate_and_executed_l18_runtime_drift():
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L19' and len(gate['implementation_sha256']) == 22
    assert gate['paid_ceiling_authorized'] is gate['live_inference_authorized'] is False
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert gate['max_calls'] == 17 and gate['max_estimated_usd'] == '0.15'
    assert subject.PROMPT == historical.PROMPT
    assert subject.LOT_LOCK != historical.LOT_LOCK and subject.KEY_ENV != historical.KEY_ENV
    assert hashlib.sha256(historical.GATE.read_bytes()).hexdigest() == '27b80c698893133466d860fbf38cc4b95c50379fed80db20cfca334c4652a9a1'
    with pytest.raises(ValueError, match='implementation_drifted'):
        historical._gate()


@pytest.mark.parametrize('old,new', [
    ('scripts/evaluate_hybrid_campaign_luna_l18_live.py', 'scripts/evaluate_hybrid_campaign_luna_l19_live.py'),
    ('scripts/preflight_hybrid_campaign_luna_l18.py', 'scripts/preflight_hybrid_campaign_luna_l19.py'),
    ('scripts/run_hybrid_campaign_luna_l18_live.ps1', 'scripts/run_hybrid_campaign_luna_l19_live.ps1'),
])
def test_l19_changes_only_lot_identity(old, new):
    expected = (subject.ROOT / old).read_text(encoding='utf-8').replace('L18','L19').replace('_l18','_l19').replace('-l18','-l19')
    assert (subject.ROOT / new).read_text(encoding='utf-8').splitlines() == expected.splitlines()


@pytest.mark.parametrize('field', ['retry', 'fallback', 'synthetic_only', 'admission_automatic'])
def test_l19_rejects_protocol_drift(field, tmp_path, monkeypatch):
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
    assert result['lot_id'] == 'HYP-007-L19'
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
