"""L3 v2 dispatch boundaries, with synthetic keys and no external network."""
import json
from decimal import Decimal

import pytest
from pydantic import SecretStr

from scripts import evaluate_hybrid_campaign_luna_l3_live as subject
from scripts import evaluate_hybrid_campaign_luna_live as historical
from test_hybrid_campaign_luna_live import fake_adapter, StubOpenAI
from api.llm.contract import (
    TokenUsage, StructuredGenerationResult, ErrorCategory, LLMInvocationError,
    NormalizedError, OperationPhase, utc_now,
)
from api.campaign_source_profile import CampaignSourceProposal


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Closed L3 evidence is never rewritten to test later local corrections."""
    historical_gate = subject.GATE
    gate = json.loads(historical_gate.read_text(encoding='utf-8'))
    gate['implementation_sha256'] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    gate['live_inference_authorized'] = True  # test only; transport is stubbed
    path = tmp_path / 'offline-test-gate.json'
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return historical_gate


def test_closed_historical_l3_rejects_new_runtime(isolated_current_manifest, monkeypatch):
    gate = json.loads(isolated_current_manifest.read_text(encoding='utf-8'))
    assert gate['live_inference_authorized'] is False
    monkeypatch.setattr(subject, 'GATE', isolated_current_manifest)
    with pytest.raises(ValueError, match='implementation_drifted'):
        subject._gate()


def test_l3_is_separate_and_approved_with_frozen_v2():
    gate = subject._gate()
    assert gate["lot_id"] == "HYP-007-L3"
    subject._require_live_gate(gate)
    assert gate["content_version"] == "record-at-risk.v2"
    assert gate["policy_version"] == "campaign-progression.v2"
    assert subject.GATE != historical.GATE
    assert subject.PROMPT != historical.PROMPT
    assert subject.LOT_LOCK != historical.LOT_LOCK
    assert subject.KEY_ENV != historical.KEY_ENV
    assert json.loads(historical.GATE.read_text())["live_inference_authorized"] is False


@pytest.mark.asyncio
async def test_l3_preflight_checks_positions_and_has_zero_external_calls(monkeypatch):
    async def forbid(*args, **kwargs):
        pytest.fail("preflight must not contact OpenAI")
    monkeypatch.setattr(subject.CampaignLunaAdapter, "generate_structured", forbid)
    result = await subject.preflight()
    assert result["lot_id"] == "HYP-007-L3" and result["provider_calls"] == 0
    assert len(result["requests"]) == 17
    assert result["max_request_bytes_observed"] <= 20_000
    assert all(row["record_position_before"] == "bench" for row in result["requests"])
    assert all(row["record_position_after"] == (
        "dry_surface" if row["rule"] in {"R-05", "R-06"} else "bench")
        for row in result["requests"])


@pytest.mark.asyncio
async def test_fake_l3_completes_17_turns_and_prices_usage(tmp_path):
    result = await subject.run_batch(directory=tmp_path / "fake", key=SecretStr("synthetic-key"),
                                     adapter_factory=fake_adapter)
    assert result["lot_id"] == "HYP-007-L3"
    assert result["status"] == "completed"
    assert result["attempted_calls"] == result["completed_turns"] == 17
    assert result["cost"]["status"] == "estimated"
    assert Decimal(result["cost"]["estimated_total_usd"]) == Decimal("0.00374")


@pytest.mark.asyncio
async def test_l3_missing_usage_stops_at_one_call_and_reports_unknown_cost(tmp_path):
    class Unknown(StubOpenAI):
        usage = TokenUsage.unavailable()
    def factory(caps, key):
        return Unknown(base_url="https://invalid.test/v1", capability_set=caps,
                       api_key=key, reasoning_effort="low")
    result = await subject.run_batch(directory=tmp_path / "unknown", key=SecretStr("synthetic-key"),
                                     adapter_factory=factory)
    assert result["attempted_calls"] == 1 and result["status"] == "stopped"
    assert result["cost"]["estimated_total_usd"] is None


@pytest.mark.asyncio
async def test_l3_latch_refuses_second_production_start_before_directory(tmp_path, monkeypatch):
    latch = tmp_path / "once"
    latch.mkdir()
    monkeypatch.setattr(subject, "LOT_LOCK", latch)
    with pytest.raises(FileExistsError):
        await subject.run_batch(directory=tmp_path / "repeat", key=SecretStr("synthetic-key"))
    assert not (tmp_path / "repeat").exists()


@pytest.mark.asyncio
async def test_l3_disabled_gate_refuses_production_without_claiming_latch(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, "_gate", lambda: {**gate, "live_inference_authorized": False})
    monkeypatch.setattr(subject, "LOT_LOCK", tmp_path / "latch")
    with pytest.raises(ValueError, match="authorization_missing"):
        await subject.run_batch(directory=tmp_path / "forbidden", key=SecretStr("synthetic-key"))
    assert not subject.LOT_LOCK.exists()


def test_l3_prompt_drift_is_rejected(tmp_path, monkeypatch):
    drift = tmp_path / "prompt.md"
    drift.write_text("synthetic changed prompt", encoding="utf-8")
    monkeypatch.setattr(subject, "PROMPT", drift)
    with pytest.raises(ValueError, match="prompt_drifted"):
        subject._gate()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["provider", "semantic"])
async def test_l3_first_rejection_stops_without_retry_or_fallback(tmp_path, failure):
    class Rejecting(StubOpenAI):
        async def generate_structured(self, request):
            result = await super().generate_structured(request)
            return StructuredGenerationResult(value=CampaignSourceProposal.model_validate({
                "n": "A luz muda de tom nas paredes do Arquivo. Mara contempla a poeira "
                     "da bancada, mas nada muda durante esse intervalo.",
                "q": "O que você faz agora?", "realized_effects": result.value.realized_effects,
            }), evidence=result.evidence)
    def factory(caps, key):
        adapter = (Rejecting if failure == "semantic" else StubOpenAI)(
            base_url="https://invalid.test/v1", capability_set=caps,
            api_key=key, reasoning_effort="low")
        if failure == "provider":
            # Use the transport contract's failure path, rather than overriding
            # the adapter to repair or retry a provider error.
            async def unavailable(request):
                raise LLMInvocationError(NormalizedError(
                    category=ErrorCategory.PROVIDER_UNAVAILABLE,
                    code="synthetic_provider_unavailable", retryable=True,
                    phase=OperationPhase.DISPATCH, invocation_id=request.invocation_id,
                    target=request.target, safe_message="Synthetic provider unavailable.",
                    evidence=adapter._evidence(request=request, started_at=utc_now(),
                                              effective_model=request.target.model, usage=adapter.usage)))
            adapter.generate_structured = unavailable
        return adapter
    result = await subject.run_batch(directory=tmp_path / "reject", key=SecretStr("synthetic-key"),
                                     adapter_factory=factory)
    assert result["status"] == "stopped" and result["attempted_calls"] == 1
    assert result["completed_turns"] == 0
    rows = subject.read_records(tmp_path / "reject")
    assert rows[0]["record"]["error_code"] == (
        "synthetic_provider_unavailable" if failure == "provider" else "campaign_source_policy_failed")


@pytest.mark.asyncio
async def test_l3_budget_exhaustion_refuses_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "PROPOSED_LIMIT", Decimal("0.0000001"))
    result = await subject.run_batch(directory=tmp_path / "budget", key=SecretStr("synthetic-key"),
                                     adapter_factory=fake_adapter)
    assert result["attempted_calls"] == 0
    assert result["cost"]["status"] == "no_dispatch"
