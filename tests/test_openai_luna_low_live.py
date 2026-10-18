from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from api.llm.contract import (
    CancellationToken, GenerationParameters, LLMMessage, LLMTarget, MessageRole,
    StructuredGenerationRequest, utc_now,
)
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter
from scripts.narrator_source_profile import NarrativeSourceProposal


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
RUNNER = ROOT / "scripts/evaluate_openai_luna_low_live.py"
LAUNCHER = ROOT / "scripts/run_openai_luna_low_live.ps1"
KEY_ENV = "STORYTELLER_OPENAI_LUNA_KEY"


def _keyless() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(KEY_ENV, None)
    return environment


def _request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        invocation_id=str(uuid4()),
        operation="test.luna.responses",
        target=LLMTarget(profile="test-luna", provider="OpenAI", model="gpt-5.6-luna"),
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content="Return JSON."),
            LLMMessage(role=MessageRole.USER, content="Narrate only supplied facts."),
        ),
        deadline=utc_now().replace(microsecond=0),
        cancellation=CancellationToken(),
        parameters=GenerationParameters(max_output_tokens=768),
        response_model=NarrativeSourceProposal,
    )


def test_preflight_freezes_luna_low_and_recloses_paid_live_after_batch() -> None:
    result = subprocess.run([str(PYTHON), str(RUNNER), "--preflight"], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    preflight = json.loads(result.stdout)
    assert preflight["hypothesis_id"] == "HYP-006-OPENAI-LUNA-LOW-L1"
    assert preflight["selected_candidates"][0]["model"] == "gpt-5.6-luna"
    assert preflight["generation_parameters"]["reasoning_effort"] == "low"
    assert preflight["max_calls"] == 8
    assert preflight["live_inference_authorized"] is False
    assert preflight["paid_spend_authorized"] is False
    assert preflight["provider_calls"] == 0
    assert preflight["credential_inspected"] is False


def test_live_is_refused_before_credential_or_directory_when_paid_gate_is_closed(tmp_path: Path) -> None:
    preflight_result = subprocess.run([str(PYTHON), str(RUNNER), "--preflight"], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    preflight = tmp_path / "preflight.json"
    preflight.write_text(preflight_result.stdout, encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(preflight.read_bytes()).hexdigest()
    batch_id = str(uuid4())
    expected = ROOT / f"eval-results/openai-luna-low-{batch_id}"
    result = subprocess.run([
        str(PYTHON), str(RUNNER), "--live", "--allow-synthetic-only", "--batch-id", batch_id,
        "--expected-preflight", str(preflight), "--expected-preflight-sha256", digest,
    ], cwd=ROOT, env=_keyless(), capture_output=True, text=True)
    assert result.returncode == 3
    assert "paid_authorization_missing" in result.stderr
    assert not expected.exists()


def test_launcher_requires_exact_paid_ceiling_and_masks_key() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert source.count("-AsSecureString") == 2
    assert "PAID-USD-0.05" in source
    assert "account_spend_limit_required_usd" in source
    assert ".env" not in source
    assert source.count('Remove-Item "Env:\\$credentialName"') == 1


@pytest.mark.asyncio
async def test_responses_adapter_uses_official_endpoint_low_effort_and_no_storage() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "model": "gpt-5.6-luna",
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"n": "A pedra permanece imóvel diante de você.", "q": "O que você faz?"})}],
            }],
            "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35},
        })

    adapter = OpenAIResponsesAdapter(
        base_url="https://api.openai.com/v1",
        capability_set=object(),
        api_key=SecretStr("test-only"),
        reasoning_effort="low",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.generate_structured(_request())

    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["body"]["model"] == "gpt-5.6-luna"
    assert captured["body"]["reasoning"] == {"effort": "low"}
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["type"] == "json_schema"
    assert "temperature" not in captured["body"]
    assert result.value.narrative.startswith("A pedra")
    assert result.evidence.provenance.effective_provider.value == "OpenAI"
