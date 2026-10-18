"""Prospective L4 is reviewable offline and cannot spend before approval."""
import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l4_live as subject
from scripts import evaluate_hybrid_campaign_luna_l3_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.mark.asyncio
async def test_pending_l4_gate_blocks_production_before_claim_or_output(tmp_path, monkeypatch):
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L4'
    assert subject.GATE != historical.GATE and subject.LOT_LOCK != historical.LOT_LOCK
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': False, 'live_inference_authorized': False,
    })
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'forbidden', key=SecretStr('synthetic-test-key'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'forbidden').exists()


@pytest.mark.asyncio
async def test_prospective_l4_preflight_uses_same_v2_schedule_with_zero_calls(monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail('keyless preflight may not dispatch')
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    result = await subject.preflight()
    assert result['lot_id'] == 'HYP-007-L4'
    assert result['provider_calls'] == 0 and len(result['requests']) == 17
    assert result['max_request_bytes_observed'] <= 20_000


@pytest.mark.asyncio
async def test_l4_fake_transport_exercises_all_turns_without_enabling_real_gate(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    result = await subject.run_batch(directory=tmp_path / 'fake', key=SecretStr('synthetic-test-key'),
                                     adapter_factory=fake_adapter)
    assert result['lot_id'] == 'HYP-007-L4'
    assert result['attempted_calls'] == result['completed_turns'] == 17
    assert result['status'] == 'completed'
    assert result['cost']['status'] == 'estimated'
