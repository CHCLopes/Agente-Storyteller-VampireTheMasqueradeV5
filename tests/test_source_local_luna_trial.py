from __future__ import annotations

import json
import asyncio
import os
from datetime import timedelta
from pathlib import Path
import subprocess
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from scripts import run_source_local_luna_trial as luna
from api.llm.contract import utc_now
from api.narrative_source_capsule import create_source_turn_capsule
from api.narrative_source_context import SourceContextSnapshot
from api.narrative_source_preparation import DeclaredActionPreparation


ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
SCRIPT = ROOT / "scripts/run_source_local_luna_trial.py"
LAUNCHER = ROOT / "scripts/run_openai_luna_source_local_trial.ps1"


def test_keyless_preflight_freezes_manual_luna_lane() -> None:
    run_id = str(uuid4())
    env = os.environ.copy()
    env.pop(luna.KEY_ENV, None)
    result = subprocess.run(
        [
            str(PYTHON), str(SCRIPT), "--preflight-only", "--run-id", run_id,
            "--port", "8018", "--origin-port", "5178",
        ],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    document = json.loads(result.stdout)
    assert document["purpose"] == luna.PURPOSE
    assert document["protocol"] == luna.PROTOCOL
    assert document["target"] == {
        "profile": luna.TARGET_PROFILE,
        "provider": "OpenAI",
        "model": "gpt-5.6-luna",
    }
    assert document["generation_parameters"]["reasoning_effort"] == "low"
    assert document["budget"]["max_calls"] == 4
    assert document["budget"]["initial_quiet_seconds"] == 0
    assert document["budget"]["minimum_inter_call_delay_seconds"] == 0
    assert document["budget"]["deadline_seconds"] == 60
    assert document["external_provider_calls"] == 0


def test_launcher_masks_luna_key_and_keeps_bounded_contract() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "Read-Host 'Cole a chave OpenAI" in source
    assert "MANUAL-LUNA-USD-0.05" in source
    assert "-AsSecureString" in source
    assert luna.KEY_ENV in source
    assert "gpt-5.6-luna" in source
    assert "Test-Integer $budget.max_calls 4" in source
    assert "Start-Process -FilePath $preflight.paths.frontend_url" in source
    assert "navegador externo padrao" in source
    assert ".env" not in source
    assert "report_luna_test_cost.py" in source
    assert "Test-Integer $budget.initial_quiet_seconds 0" in source
    assert "if (-not $costDispatchPossible)" in source
    assert source.index("$costDispatchPossible = $true") < source.index("$server = New-IsolatedChild")


def test_luna_no_cooldown_keeps_budget_and_groq_spacing(tmp_path):
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    prepared = luna.prepare(spec)
    control = luna.LunaTrialControl(spec, prepared, clock=lambda: 0)
    from api.narrative_source_entry import SourcePlayerActionRequest
    for index in range(4):
        assert control.admit(SourcePlayerActionRequest(operation_id=str(index), player_input="Aguardo."))
        control.consume()
        control.release_dispatch()
    with pytest.raises(luna.base.TrialError):
        control.consume()
    assert control.calls == 4
    assert luna.BASE_CONTROL.delay_seconds == 60


def test_zero_delay_does_not_allow_concurrent_dispatch_or_unlock_owner(tmp_path):
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    control = luna.LunaTrialControl(spec, luna.prepare(spec), clock=lambda: 0)
    control.consume()
    with pytest.raises(luna.base.TrialError, match="concurrent_dispatch"):
        control.consume()
    assert control.calls == 1 and control.in_flight
    control.release_dispatch()
    assert not control.in_flight and not control.eligible


def test_four_luna_turns_commit_without_advancing_cooldown_clock(tmp_path):
    from fastapi.testclient import TestClient
    from tests.test_source_local_groq_trial import create_store, next_event, command, table_counts, REPLY, WAIT_REPLY
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    prepared = luna.prepare(spec)
    store = asyncio.run(create_store((spec, prepared)))
    control = luna.LunaTrialControl(spec, prepared, clock=lambda: 0)
    responses = [0]
    async def handler(_):
        responses[0] += 1
        return httpx.Response(200, json={"model": "gpt-5.6-luna", "output": [{"type": "message",
            "content": [{"type": "output_text", "text": json.dumps({"n": REPLY if responses[0] == 1 else WAIT_REPLY,
                "q": "O que você faz?"})}]}],
            "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35}})
    gateway = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"), transport=httpx.MockTransport(handler))
    app = luna.base.application(spec, store, prepared, control, gateway)
    with TestClient(app, base_url="http://127.0.0.1:8018") as client:
        with client.websocket_connect("/ws/source-local/" + spec.session_id,
                headers={"host": "127.0.0.1:8018", "origin": "http://127.0.0.1:5178"}) as socket:
            next_event(socket, "briefing")
            for index in range(4):
                socket.send_text(command(operation=str(index), text="Aguardo."))
                assert next_event(socket, "narrative_complete")["operation_id"] == str(index)
    assert table_counts(store) == {"attempts": 12, "turns": 4, "events": 4}
    assert responses[0] == control.calls == 4
    assert control.reason == "budget_completed"


@pytest.mark.asyncio
async def test_concurrent_luna_gateways_share_single_dispatch(tmp_path):
    from tests.test_source_local_groq_trial import request
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    prepared = luna.prepare(spec)
    control = luna.LunaTrialControl(spec, prepared, clock=lambda: 0)
    entered, release = asyncio.Event(), asyncio.Event()
    async def handler(_):
        entered.set()
        await release.wait()
        return httpx.Response(200, json={"model": "gpt-5.6-luna", "output": [{"type": "message",
            "content": [{"type": "output_text", "text": json.dumps({"n": "Mara permanece diante de você, atenta ao silêncio entre ambos.", "q": "O que você diz?"})}]}],
            "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35}})
    first = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"), transport=httpx.MockTransport(handler))
    second = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"), transport=httpx.MockTransport(handler))
    task = asyncio.create_task(first.generate_structured(request((spec, prepared))))
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        with pytest.raises(luna.base.TrialError, match="concurrent_dispatch"):
            await second.generate_structured(request((spec, prepared)))
        assert control.in_flight and control.calls == 1
    finally:
        release.set()
        await task
    assert not control.in_flight


@pytest.mark.asyncio
async def test_failed_luna_output_retains_usage_for_cost(tmp_path):
    from tests.test_source_local_groq_trial import request
    from scripts.report_luna_test_cost import summarize
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    spec.status_directory.mkdir()
    prepared = luna.prepare(spec)
    control = luna.LunaTrialControl(spec, prepared, clock=lambda: 0)
    rows = []
    async def handler(_):
        return httpx.Response(200, json={"model": "gpt-5.6-luna", "output": [],
            "usage": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100}})
    gateway = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"),
        transport=httpx.MockTransport(handler), record=rows.append)
    with pytest.raises(luna.LLMInvocationError):
        await gateway.generate_structured(request((spec, prepared)))
    assert summarize(rows, settled=True)["estimated_total_usd"] == "0.00032"
    assert not control.in_flight and not control.eligible


@pytest.mark.asyncio
async def test_manual_gateway_uses_luna_and_consumes_one_call(monkeypatch) -> None:
    spec = luna.LunaTrialSpec(
        str(uuid4()), 8018, 5178,
        ROOT / "eval-results" / ("source-local-luna-trial-" + str(uuid4())),
        Path(os.environ.get("TEMP", str(ROOT))) / ("storyteller-luna-test-" + str(uuid4())),
    )
    prepared = luna.prepare(spec)
    manifest = luna.base.create_source_setup_manifest(luna.base.SETUP, session_id=spec.session_id)
    snapshot = SourceContextSnapshot(
        origin=manifest.origin, current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )
    capsule = create_source_turn_capsule(
        snapshot, operation_id="manual-test", created_at=utc_now(),
        player_input="Aguardo.", preparation=DeclaredActionPreparation(),
        state=luna.base.player._state(), relationships={}, target=prepared.target,
        system_prompt=prepared.prompt,
        parameters=luna.GenerationParameters(temperature=0.65, max_output_tokens=768),
        npc_aliases=("Mara",),
    )
    request = luna.base.retained._request(capsule, utc_now() + timedelta(seconds=30))

    class Control:
        calls = 0
        def consume(self):
            self.calls += 1
        def block(self, reason):
            pass
        def release_dispatch(self):
            pass

    captured = {}
    async def handler(http_request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(http_request.content)
        return httpx.Response(200, json={
            "model": "gpt-5.6-luna",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"n": "Mara permanece diante de você, atenta ao silêncio entre ambos.", "q": "O que você diz?"})}]}],
            "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35},
        })
    control = Control()
    gateway = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"), transport=httpx.MockTransport(handler))
    result = await gateway.generate_structured(request)
    assert result.value.narrative.startswith("Mara")
    assert captured["body"]["model"] == "gpt-5.6-luna"
    assert captured["body"]["reasoning"] == {"effort": "low"}
    assert control.calls == 1


@pytest.mark.asyncio
async def test_manual_gateway_refreshes_live_status_after_record(monkeypatch, tmp_path) -> None:
    spec = luna.LunaTrialSpec(str(uuid4()), 8018, 5178, tmp_path / "run", tmp_path / "status")
    spec.status_directory.mkdir()
    prepared = luna.prepare(spec)
    manifest = luna.base.create_source_setup_manifest(luna.base.SETUP, session_id=spec.session_id)
    snapshot = SourceContextSnapshot(origin=manifest.origin, current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=())
    capsule = create_source_turn_capsule(snapshot, operation_id="manual-status", created_at=utc_now(),
        player_input="Aguardo.", preparation=DeclaredActionPreparation(), state=luna.base.player._state(),
        relationships={}, target=prepared.target, system_prompt=prepared.prompt,
        parameters=luna.GenerationParameters(temperature=0.65, max_output_tokens=768), npc_aliases=("Mara",))
    request = luna.base.retained._request(capsule, utc_now() + timedelta(seconds=30))

    class Control:
        calls = 0
        eligible = True
        reason = None
        def consume(self): self.calls += 1
        def block(self, reason): self.eligible = False; self.reason = reason
        def release_dispatch(self): pass

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "gpt-5.6-luna", "output": [{"type": "message",
            "content": [{"type": "output_text", "text": json.dumps({"n": "Mara permanece diante de você, atenta ao silêncio entre ambos.", "q": "O que você diz?"})}]}],
            "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35}})

    control = Control()
    records = []
    gateway = luna.LunaTrialGateway(spec, prepared, control, SecretStr("test-only"),
        transport=httpx.MockTransport(handler), record=records.append)
    await gateway.generate_structured(request)
    status = json.loads((spec.status_directory / "status.json").read_text(encoding="utf-8"))
    assert records[0]["outcome"] == "generated"
    assert status["status"] == "running"
    assert status["calls_started"] == 1
    assert status["admission_allowed"] is True
