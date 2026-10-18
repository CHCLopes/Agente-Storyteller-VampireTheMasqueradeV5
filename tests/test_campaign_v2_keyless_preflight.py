"""Prospective v2 prompt/body rehearsal; never enable or modify the L2 gate."""
import pytest

from scripts import preflight_hybrid_campaign_luna as subject


@pytest.mark.asyncio
async def test_v2_prompt_and_all_17_requests_fit_existing_budget(monkeypatch):
    monkeypatch.setattr(subject, "PROMPT", subject.ROOT /
                        "evals/narrator/prompts/hybrid-campaign-source-v2.md")
    result = await subject.preflight()
    assert result["provider_calls"] == 0
    assert result["calls_planned"] == len(result["requests"]) == 17
    assert result["max_request_bytes_observed"] <= 20_000
    print(f"V2_KEYLESS_MAX_REQUEST_BYTES={result['max_request_bytes_observed']}")
    print(f"V2_PROMPT_SHA256={result['prompt_sha256']}")
