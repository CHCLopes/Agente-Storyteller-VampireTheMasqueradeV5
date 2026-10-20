"""A separate, closed prospective L6; the executed L5 may not be rebased."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l6_live as subject
from scripts import evaluate_hybrid_campaign_luna_l5_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Exercise stubs without rebasing the executed L6 evidence."""
    original = subject.GATE
    gate = json.loads(original.read_text(encoding='utf-8'))
    gate['implementation_sha256'] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    path = tmp_path / original.name
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return original


def test_executed_l6_rejects_corrected_runtime(isolated_current_manifest, monkeypatch):
    assert hashlib.sha256(isolated_current_manifest.read_bytes()).hexdigest() == 'b0e582b28d46cb015f8e11aa7a6e0f37b26458168704a139963297fce1eb1c49'
    monkeypatch.setattr(subject, 'GATE', isolated_current_manifest)
    with pytest.raises(ValueError, match='implementation_drifted'):
        subject._gate()


def test_l6_gate_is_closed_and_l5_keeps_its_executed_manifest():
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L6'
    assert gate['live_inference_authorized'] is gate['paid_ceiling_authorized'] is False
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert gate['max_calls'] == 17 and gate['max_estimated_usd'] == '0.15'
    assert len(gate['implementation_sha256']) == 22
    assert subject.GATE != historical.GATE and subject.LOT_LOCK != historical.LOT_LOCK
    assert subject.KEY_ENV != historical.KEY_ENV
    assert hashlib.sha256(historical.GATE.read_bytes()).hexdigest() == 'bd9e07b289e78f98bb9a7c21fbd8059eae2a947aaa9c4d5ed6fc2852efa2c57d'
    with pytest.raises(ValueError, match='implementation_drifted'):
        historical._gate()


@pytest.mark.parametrize('old,new', [
    ('scripts/evaluate_hybrid_campaign_luna_l5_live.py', 'scripts/evaluate_hybrid_campaign_luna_l6_live.py'),
    ('scripts/preflight_hybrid_campaign_luna_l5.py', 'scripts/preflight_hybrid_campaign_luna_l6.py'),
    ('scripts/run_hybrid_campaign_luna_l5_live.ps1', 'scripts/run_hybrid_campaign_luna_l6_live.ps1'),
])
def test_l6_changes_only_batch_identity_not_transport_or_protocol(old, new):
    expected = (subject.ROOT / old).read_text(encoding='utf-8').replace('L5', 'L6').replace('_l5', '_l6').replace('-l5', '-l6')
    assert (subject.ROOT / new).read_text(encoding='utf-8').splitlines() == expected.splitlines()


@pytest.mark.parametrize('field', ['retry', 'fallback', 'admission_automatic', 'synthetic_only'])
def test_l6_refuses_protocol_drift(field, tmp_path, monkeypatch):
    gate = subject._gate()
    gate[field] = not gate[field]
    path = tmp_path / 'mutated.json'
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    with pytest.raises(ValueError, match='gate_drifted'):
        subject._gate()


def test_l6_keyless_cli_never_reads_credential_or_dispatches(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail('no real dispatch or credential access during preflight')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    lines = capsys.readouterr().out.splitlines()
    result = json.loads(lines[0])
    assert result['lot_id'] == 'HYP-007-L6'
    assert result['provider_calls'] == 0 and result['calls_planned'] == 17
    assert result['max_request_bytes_observed'] <= 20000
    assert 'CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada).' in lines


@pytest.mark.asyncio
async def test_l6_live_denied_before_credential_adapter_latch_and_output(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('the closed gate must precede credential and adapter')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, '__init__', forbidden)
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'blocked', key=SecretStr('synthetic-only'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'blocked').exists()


@pytest.mark.asyncio
async def test_l6_fake_schedule_completes_without_enabling_real_gate(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    result = await subject.run_batch(directory=tmp_path / 'fake', key=SecretStr('synthetic-only'),
                                     adapter_factory=fake_adapter)
    assert result['status'] == 'completed'
    assert result['attempted_calls'] == result['completed_turns'] == 17
    assert json.loads(subject.GATE.read_text(encoding='utf-8'))['live_inference_authorized'] is False


@pytest.mark.asyncio
async def test_l6_existing_latch_blocks_concurrent_or_repeated_batch(tmp_path, monkeypatch):
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
