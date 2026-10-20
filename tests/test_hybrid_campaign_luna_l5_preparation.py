"""Closed L5 boundaries under a test-only manifest; executed evidence stays frozen."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l5_live as subject
from scripts import evaluate_hybrid_campaign_luna_l4_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Match L2/L3 test isolation, never rebase the executed L5 manifest."""
    original = subject.GATE
    gate = json.loads(original.read_text(encoding='utf-8'))
    gate['implementation_sha256'] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    path = tmp_path / original.name
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return original


def test_executed_l5_manifest_refuses_the_corrected_runtime(isolated_current_manifest, monkeypatch):
    assert hashlib.sha256(isolated_current_manifest.read_bytes()).hexdigest() == 'bd9e07b289e78f98bb9a7c21fbd8059eae2a947aaa9c4d5ed6fc2852efa2c57d'
    monkeypatch.setattr(subject, 'GATE', isolated_current_manifest)
    with pytest.raises(ValueError, match='implementation_drifted'):
        subject._gate()


@pytest.mark.asyncio
async def test_pending_l5_gate_blocks_production_before_claim_or_output(tmp_path, monkeypatch):
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L5'
    assert subject.GATE != historical.GATE and subject.LOT_LOCK != historical.LOT_LOCK
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': False, 'live_inference_authorized': False,
    })
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'forbidden', key=SecretStr('synthetic-test-key'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'forbidden').exists()


@pytest.mark.asyncio
async def test_prospective_l5_preflight_uses_same_v2_schedule_with_zero_calls(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail('keyless preflight may not dispatch')
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    result = await subject.preflight()
    assert result['lot_id'] == 'HYP-007-L5'
    assert result['provider_calls'] == 0 and len(result['requests']) == 17
    assert result['max_request_bytes_observed'] <= 20_000


@pytest.mark.asyncio
async def test_l5_fake_transport_exercises_all_turns_without_enabling_real_gate(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    result = await subject.run_batch(directory=tmp_path / 'fake', key=SecretStr('synthetic-test-key'),
                                     adapter_factory=fake_adapter)
    assert result['lot_id'] == 'HYP-007-L5'
    assert result['attempted_calls'] == result['completed_turns'] == 17
    assert result['status'] == 'completed'
    assert result['cost']['status'] == 'estimated'


def test_current_gate_preserves_historical_manifests_and_freezes_security(isolated_current_manifest):
    gate = subject._gate()
    assert subject.GATE.name == 'hybrid-campaign-luna-l5-live-gate-2026-10-18.json'
    assert gate['live_inference_authorized'] is False
    assert gate['paid_ceiling_authorized'] is False
    assert len(subject.FROZEN_FILES) == 22
    assert 'api/local_request_security.py' in subject.FROZEN_FILES
    for name, digest in (
        ('hybrid-campaign-luna-l4-live-gate-2026-10-03.json',
         'f9f2befd2c3d36cd3b5f54afcc2c20830b8186c1b73d62b112e2e5c6cd0f2218'),
        ('hybrid-campaign-luna-l5-live-gate-2026-10-03.json',
         'fb921cf7ab1bd89a4361bdf497b87795e4faac3367b6cfac415bc8257e6c10e2'),
    ):
        path = isolated_current_manifest.parent / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert json.loads(path.read_text(encoding='utf-8'))['live_inference_authorized'] is False


@pytest.mark.parametrize('mutation,expected', [
    ('missing_security', 'manifest_missing'),
    ('security_drift', 'implementation_drifted'),
    ('prompt_drift', 'prompt_drifted'),
    ('retry', 'gate_drifted'),
    ('fallback', 'gate_drifted'),
    ('synthetic_only', 'gate_drifted'),
    ('admission_automatic', 'gate_drifted'),
])
def test_prospective_gate_rejects_drift(tmp_path, monkeypatch, mutation, expected):
    gate = subject._gate()
    if mutation == 'missing_security':
        del gate['implementation_sha256']['api/local_request_security.py']
    elif mutation == 'security_drift':
        gate['implementation_sha256']['api/local_request_security.py'] = '0' * 64
    elif mutation == 'prompt_drift':
        gate['prompt_sha256'] = '0' * 64
    else:
        gate[mutation] = not gate[mutation]
    path = tmp_path / 'mutated-gate.json'
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    with pytest.raises(ValueError, match=expected):
        subject._gate()


def test_keyless_cli_reports_zero_cost_without_reading_credential(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail('keyless preflight may not read a credential or dispatch')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    lines = capsys.readouterr().out.splitlines()
    assert json.loads(lines[0])['provider_calls'] == 0
    assert 'CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada).' in lines


@pytest.mark.asyncio
async def test_live_gate_denial_precedes_credential_and_adapter(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('closed live gate must precede credential access and adapter')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, '__init__', forbidden)
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'blocked', key=SecretStr('synthetic-test-key'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'blocked').exists()


@pytest.mark.asyncio
async def test_existing_latch_refuses_concurrent_or_repeated_batch(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    latch = tmp_path / 'once'
    latch.mkdir()
    monkeypatch.setattr(subject, 'LOT_LOCK', latch)
    with pytest.raises(FileExistsError):
        await subject.run_batch(directory=tmp_path / 'repeated', key=SecretStr('synthetic-test-key'))
    assert not (tmp_path / 'repeated').exists()


@pytest.mark.asyncio
async def test_revoked_gate_stops_before_second_dispatch(tmp_path, monkeypatch):
    gate = subject._gate()
    checks = []
    def per_dispatch_gate():
        checks.append(None)
        return {**gate, 'paid_ceiling_authorized': True,
                'live_inference_authorized': len(checks) == 1}
    monkeypatch.setattr(subject, '_gate', per_dispatch_gate)
    result = await subject.run_batch(directory=tmp_path / 'revoked',
                                    key=SecretStr('synthetic-test-key'),
                                    adapter_factory=fake_adapter)
    assert len(checks) == 2
    assert result['status'] == 'stopped'
    assert result['attempted_calls'] == result['completed_turns'] == 1
    rows = subject.read_records(tmp_path / 'revoked')
    assert rows[1]['record']['call_made'] is False
