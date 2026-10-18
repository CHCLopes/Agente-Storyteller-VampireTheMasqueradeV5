"""One-call continuity experiment, exercised through the real Groq adapter offline."""

import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from scripts import evaluate_narrator_continuity as probe


def test_preparation_admits_authored_seed_and_preserves_old_background():
    prepared = probe.prepare_probe()
    context = json.loads(prepared.packet.split("\n", 1)[1])["context"]
    focus = context["last_turn_focus"]["data"]
    assert prepared.scene.last_turn == 2
    assert focus["source_turn"] == "authored-continuity/authored-predecessor/r1"
    assert focus["visible_facts"][0]["reference"] == "visible_fact_0"
    assert "tinta azul" in focus["visible_facts"][0]["summary"]
    old = context["scene_background"]["data"]["older_details"]
    assert any("símbolo" in value for value in old)
    assert not any("tinta azul" in value for value in old)
    assert prepared.context_audit["user_packet_sha256"] == hashlib.sha256(prepared.packet.encode()).hexdigest()
    assert prepared.context_audit["budget"]["omitted_background_details"] == 0


@pytest.fixture
def cli_project(monkeypatch, tmp_path):
    # Preparation is independently exercised against real, allowlisted files.
    # CLI artifacts and every credential here remain synthetic and isolated.
    prepared = probe.prepare_probe()
    monkeypatch.setattr(probe, "prepare_probe", lambda: prepared)
    monkeypatch.setattr(probe, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path / "eval-results/continuity-probe")
    return prepared


def _summary():
    paths = list(probe.OUTPUT_ROOT.glob("*/summary.json"))
    assert len(paths) == 1
    return json.loads(paths[0].read_text(encoding="utf-8")), paths[0].parent


def test_default_cli_is_offline_and_does_not_construct_gateway(cli_project, monkeypatch):
    monkeypatch.setattr(probe, "_live_gateway", lambda *_: pytest.fail("offline gateway"))
    assert probe.main([]) == 0
    summary, directory = _summary()
    assert summary["mode"] == "offline_preparation" and summary["status"] == "prepared"
    assert summary["calls_started"] == 0 and summary["usage_aggregate"]["status"] == "not_requested"
    assert summary["cost_aggregate"]["total_amount"] is None
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["predecessor"]["provider_generated"] is False
    assert not summary["continuation_automated_passed"]
    assert not (directory / "response.json").exists()
    assert summary["request_artifact_sha256"] == hashlib.sha256((directory / "request.json").read_bytes()).hexdigest()


def _continuation():
    return {
        "n": "Na borda do painel de madeira, a tinta azul forma pequenas gotas sobre a poeira. Uma corrente de ar atravessa a fresta e faz vibrar um papel preso atrás da madeira. O rádio da bancada chia, enquanto a luz da janela ilumina a parede do fundo.",
        "o": "unresolved", "l": "Galpão de carga desativado",
        "s": "Uma corrente de ar faz vibrar um papel preso atrás do painel de madeira.",
        "p": [], "f": [{"k": "observation", "s": "Uma corrente de ar faz vibrar um papel preso atrás do painel de madeira.",
                           "v": "public", "i": 0.5, "p": True, "a": []}],
        "t": [], "r": [], "q": "O que você faz diante desse detalhe?",
    }


@pytest.mark.parametrize("mode,expected", [
    ("valid", 0), ("structure", 1), ("admission", 1), ("model_drift", 1),
    ("rate_limited", 2), ("timeout", 2), ("cancelled", 130), ("internal", 3),
])
def test_live_path_is_one_actual_adapter_call_with_exact_focus_and_no_retry(
    cli_project, monkeypatch, capsys, mode, expected,
):
    captured = []
    response = _continuation()
    if mode == "structure":
        response["f"][0].pop("a")
    if mode == "admission":
        response["l"] = "Outro galpão"

    def transport(request):
        captured.append(json.loads(request.content))
        if mode == "cancelled":
            raise asyncio.CancelledError
        if mode == "internal":
            raise RuntimeError("synthetic-key-must-not-leak")
        if mode == "timeout":
            raise httpx.ReadTimeout("synthetic provider timeout", request=request)
        if mode == "rate_limited":
            return httpx.Response(429, json={"error": {"message": "synthetic rate limit"}}, request=request)
        return httpx.Response(200, json={
            "id": "synthetic-continuity-response", "model": "different-model" if mode == "model_drift" else cli_project.candidate.model,
            "choices": [{"message": {"role": "assistant", "content": json.dumps(response)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
        }, request=request)

    def gateway(prepared, key):
        return probe.evaluator.GroqAdapter(
            base_url=probe.evaluator.GROQ_OFFICIAL_BASE_URL,
            capability_set=probe.evaluator._capabilities(prepared.candidate, prepared.target),
            api_key=key, reasoning_effort="low", transport=httpx.MockTransport(transport),
        )

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key-must-not-leak")
    monkeypatch.setattr(probe, "_live_gateway", gateway)
    assert probe.main(["--live"]) == expected
    summary, directory = _summary()
    assert len(captured) == summary["calls_started"] == 1
    assert captured[0]["model"] == cli_project.candidate.model
    assert captured[0]["max_completion_tokens"] == 768
    assert captured[0]["reasoning_effort"] == "low"
    assert captured[0]["messages"] == [
        {"role": "system", "content": cli_project.prompt}, {"role": "user", "content": cli_project.packet},
    ]
    assert summary["cap_001_status"] == "not_evaluated" and not summary["full_evaluation"]
    assert summary["continuity_human_assessment"] is None
    assert summary["continuation_automated_passed"] is (expected == 0)
    record = json.loads((directory / "response.json").read_text(encoding="utf-8"))
    if expected:
        assert "next_focus" not in record
    if mode in {"cancelled", "internal"}:
        assert summary["usage_aggregate"]["calls_made"] == 1
        assert summary["usage_aggregate"]["totals"]["total_tokens"] is None
    assert "synthetic-key-must-not-leak" not in capsys.readouterr().out
    assert all("synthetic-key-must-not-leak" not in path.read_text(encoding="utf-8")
               for path in directory.glob("*.json"))


def test_missing_key_makes_no_provider_attempt(cli_project, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(probe, "_live_gateway", lambda *_: pytest.fail("gateway without key"))
    assert probe.main(["--live"]) == 3
    summary, _ = _summary()
    assert summary["calls_started"] == 0 and summary["local_error"]["code"] == "missing_api_key"


def test_run_id_collision_never_overwrites_old_artifacts(cli_project):
    run_id = str(uuid4())
    assert probe.main(["--run-id", run_id]) == 0
    summary_path = probe.OUTPUT_ROOT / run_id / "summary.json"
    original = summary_path.read_bytes()
    assert probe.main(["--run-id", run_id, "--live"]) == 3
    assert summary_path.read_bytes() == original


@pytest.mark.parametrize("args", [["--run-id", "../escape"], ["--candidate", "other"], ["--fixture", "other.json"], ["--retries", "2"]])
def test_cli_cannot_change_profile_or_scope(args):
    with pytest.raises(SystemExit):
        probe.main(args)


def test_single_dispatch_rejects_second_call_and_foreign_packet():
    prepared = probe.prepare_probe()
    requests = []

    class StopBeforeResponse:
        async def generate_structured(self, request):
            requests.append(request)
            raise asyncio.CancelledError

    dispatch = probe.SingleDispatch(StopBeforeResponse(), prepared)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(probe.run_probe(prepared, dispatch))
    assert requests[0].operation.startswith("CONTINUITY-PROBE.")
    assert not requests[0].operation.startswith("CAP-001.")
    with pytest.raises(ValueError):
        asyncio.run(dispatch.generate_structured(requests[0]))
    assert len(requests) == 1
    different = probe.SingleDispatch(StopBeforeResponse(), replace(prepared, packet="foreign packet"))
    with pytest.raises(ValueError):
        asyncio.run(different.generate_structured(requests[0]))
    assert different.calls_started == 0
