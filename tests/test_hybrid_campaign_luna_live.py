"""HYP-007 gate and transport-boundary tests; never contact OpenAI."""
import json
from decimal import Decimal

import pytest
from pydantic import SecretStr

from api.campaign_source_offline_corpus import PROSE
from api.campaign_source_profile import CampaignSourceProposal
from api.llm.contract import (
    MeasurementStatus, StructuredGenerationResult, TokenUsage, utc_now,
)
from scripts import evaluate_hybrid_campaign_luna_live as subject


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Exercise offline stubs without rewriting the closed historical L2 gate."""
    historical = subject.GATE
    gate = json.loads(historical.read_text(encoding="utf-8"))
    gate["implementation_sha256"] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    path = tmp_path / "offline-test-gate.json"
    path.write_text(json.dumps(gate), encoding="utf-8")
    monkeypatch.setattr(subject, "GATE", path)
    return historical


def test_historical_l2_manifest_rejects_new_implementation(isolated_current_manifest, monkeypatch):
    monkeypatch.setattr(subject, "GATE", isolated_current_manifest)
    with pytest.raises(ValueError, match="campaign_luna_implementation_drifted"):
        subject._gate()


class StubOpenAI(subject.OpenAIResponsesAdapter):
    usage = TokenUsage(status=MeasurementStatus.REPORTED, input_tokens=500,
                       output_tokens=100, total_tokens=600, source="synthetic test")

    async def generate_structured(self, request):
        causal = json.loads(request.messages[1].content)["context"]["causal_packet"]
        rule = causal["beat"]["selected_option_id"].split(".", 1)[0]
        payload = CampaignSourceProposal.model_validate({
            "n": PROSE[rule],
            "q": "" if causal["state_after"]["outcome"] else "O que você faz agora?",
            "realized_effects": causal["required_effects"],
        })
        return StructuredGenerationResult(
            value=payload,
            evidence=self._evidence(request=request, started_at=utc_now(),
                                    effective_model=request.target.model, usage=self.usage),
        )


def fake_adapter(caps, key):
    return StubOpenAI(base_url="https://invalid.test/v1", capability_set=caps,
                      api_key=key, reasoning_effort="low")


def test_campaign_adapter_schema_requires_every_property():
    adapter = subject.CampaignLunaAdapter(
        base_url="https://invalid.test/v1", capability_set=None,
        api_key=SecretStr("synthetic-test-only-key"), reasoning_effort="low",
    )
    schema = adapter._native_response_format(type("Request", (), {
        "response_model": CampaignSourceProposal,
    })())["schema"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in schema["properties"]["protocol"]


def test_paid_gate_records_l2_but_blocks_repeat_after_execution():
    gate = subject._gate()
    assert gate["lot_id"] == "HYP-007-L2"
    assert gate["live_inference_authorized"] is False
    assert gate["paid_ceiling_authorized"] is True
    with pytest.raises(ValueError, match="authorization_missing"):
        subject._require_live_gate(gate)


@pytest.mark.asyncio
async def test_production_entry_cannot_bypass_disabled_gate(tmp_path, monkeypatch):
    original_gate = subject._gate
    monkeypatch.setattr(subject, "_gate", lambda: {
        **original_gate(), "live_inference_authorized": False,
    })
    with pytest.raises(ValueError, match="authorization_missing"):
        await subject.run_batch(directory=tmp_path / "must-not-exist",
                                key=SecretStr("synthetic-test-only-key"))
    assert not (tmp_path / "must-not-exist").exists()


@pytest.mark.asyncio
async def test_production_l2_latch_blocks_repeat_before_batch_directory(tmp_path, monkeypatch):
    latch = tmp_path / "l2-once"
    latch.mkdir()
    monkeypatch.setattr(subject, "LOT_LOCK", latch)
    original_gate = subject._gate
    monkeypatch.setattr(subject, "_gate", lambda: {
        **original_gate(), "live_inference_authorized": True,
    })
    with pytest.raises(FileExistsError):
        await subject.run_batch(directory=tmp_path / "second-batch",
                                key=SecretStr("synthetic-test-only-key"))
    assert not (tmp_path / "second-batch").exists()


def test_started_batch_without_records_never_reports_zero_cost(tmp_path, monkeypatch, capsys):
    async def failed_run(*, directory, key):
        directory.mkdir(parents=True)
        raise ValueError("synthetic_failure_after_start")
    async def fake_preflight():
        return None
    original_gate = subject._gate
    monkeypatch.setattr(subject, "_gate", lambda: {
        **original_gate(), "paid_ceiling_authorized": True,
        "live_inference_authorized": True,
    })
    monkeypatch.setattr(subject, "preflight", fake_preflight)
    monkeypatch.setattr(subject, "run_batch", failed_run)
    monkeypatch.setattr(subject, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setenv(subject.KEY_ENV, "synthetic-test-only-key")
    assert subject.main(["--live", "--batch-id", "00000000-0000-0000-0000-000000000001"]) == 3
    assert "CUSTO FINAL LUNA: indisponivel" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_fake_transport_runs_17_causal_turns_and_reports_cost(tmp_path):
    result = await subject.run_batch(
        directory=tmp_path / "hyp-007", key=SecretStr("synthetic-test-only-key"),
        adapter_factory=fake_adapter,
    )
    assert result["status"] == "completed"
    assert result["attempted_calls"] == result["completed_turns"] == 17
    assert result["cost"]["status"] == "estimated"
    rows = subject.read_records(tmp_path / "hyp-007")
    assert len(rows) == 17
    assert all(row["record"]["call_made"] is True for row in rows)
    assert all(row["record"]["request_bytes"] <= 20_000 for row in rows)
    assert all(row["record"]["response"]["n"] for row in rows)


@pytest.mark.asyncio
async def test_missing_usage_stops_after_first_call_without_zero_cost(tmp_path):
    class UnknownUsage(StubOpenAI):
        usage = TokenUsage.unavailable()

    def factory(caps, key):
        return UnknownUsage(base_url="https://invalid.test/v1", capability_set=caps,
                            api_key=key, reasoning_effort="low")

    result = await subject.run_batch(
        directory=tmp_path / "unknown-usage", key=SecretStr("synthetic-test-only-key"),
        adapter_factory=factory,
    )
    assert result["status"] == "stopped"
    assert result["attempted_calls"] == 1
    assert result["cost"]["status"] == "unavailable"
    assert result["cost"]["estimated_total_usd"] is None


@pytest.mark.asyncio
async def test_semantic_rejection_stops_without_retry_or_partial_progression(tmp_path):
    class UnrealizedEffect(StubOpenAI):
        async def generate_structured(self, request):
            response = await super().generate_structured(request)
            value = CampaignSourceProposal.model_validate({
                "n": "A luz muda de tom nas paredes do Arquivo. Mara contempla a poeira "
                     "da bancada, mas nada muda durante esse intervalo.",
                "q": "O que você faz agora?",
                "realized_effects": response.value.realized_effects,
            })
            return StructuredGenerationResult(value=value, evidence=response.evidence)

    def factory(caps, key):
        return UnrealizedEffect(base_url="https://invalid.test/v1", capability_set=caps,
                                api_key=key, reasoning_effort="low")

    result = await subject.run_batch(
        directory=tmp_path / "unrealized", key=SecretStr("synthetic-test-only-key"),
        adapter_factory=factory,
    )
    assert result["status"] == "stopped"
    assert result["attempted_calls"] == 1
    assert result["completed_turns"] == 0
    assert result["cost"]["status"] == "estimated"


@pytest.mark.asyncio
async def test_budget_refuses_request_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "PROPOSED_LIMIT", Decimal("0.0000001"))
    result = await subject.run_batch(
        directory=tmp_path / "budget-refusal", key=SecretStr("synthetic-test-only-key"),
        adapter_factory=fake_adapter,
    )
    assert result["status"] == "stopped"
    assert result["attempted_calls"] == 0
    assert result["cost"]["status"] == "no_dispatch"
