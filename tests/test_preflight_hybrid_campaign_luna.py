"""HYP-007 preparation proves schedule and request envelope without network."""
import pytest

from scripts import preflight_hybrid_campaign_luna as subject


@pytest.mark.asyncio
async def test_keyless_preflight_rehearses_fixed_campaign_without_paid_dispatch(monkeypatch):
    async def refuse_dispatch(*_args, **_kwargs):
        raise AssertionError("paid_adapter_must_not_be_called")
    monkeypatch.setattr(subject.OpenAIResponsesAdapter, "generate_structured", refuse_dispatch)
    result = await subject.preflight()
    assert result["provider_calls"] == 0
    assert result["calls_planned"] == len(result["requests"]) == 17
    assert result["model"] == "gpt-5.6-luna"
    assert result["reasoning_effort"] == "low"
    assert result["store"] is False
    assert result["max_request_bytes_observed"] <= result["request_byte_limit"]
    assert tuple(row["case_id"] for row in result["requests"] if row["turn"] == 1) == tuple(
        case_id for case_id, *_ in subject.CASES
    )


def test_schedule_output_and_request_limits_are_bounded():
    assert sum(len(inputs) for _, inputs, _, _ in subject.CASES) == subject.MAX_CALLS == 17
    assert subject.MAX_OUTPUT_TOKENS == 768
    assert subject.MAX_REQUEST_BYTES == 20_000
    assert subject.DEADLINE_SECONDS == 60
