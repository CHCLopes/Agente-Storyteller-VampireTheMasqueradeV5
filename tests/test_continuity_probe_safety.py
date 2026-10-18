"""Adversarial probe boundaries using only copied synthetic inputs and fakes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts import evaluate_narrator_continuity as probe
from scripts.narrator_scene_focus import SceneFocusBudgetError


REAL_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "scripts/evaluate_narrator_continuity.py", "scripts/evaluate_narrator_models.py",
    "scripts/narrator_scene_focus.py", "scripts/narrator_actor_contract.py",
    "api/scene_director_service.py", "api/scene_service.py",
)


@pytest.fixture
def local_project(tmp_path, monkeypatch):
    root = tmp_path / "isolated project"
    files = (*SOURCE_FILES, "evals/narrator/groq_candidates_2026-09-05.json",
             "evals/narrator/experiments/continuity-probe-v1.json",
             "evals/narrator/prompts/scene-focus-v1.md")
    for name in files:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_ROOT / name, target)
    monkeypatch.setattr(probe, "PROJECT_ROOT", root)
    monkeypatch.setattr(probe, "FIXTURE", root / "evals/narrator/experiments/continuity-probe-v1.json")
    monkeypatch.setattr(probe, "MANIFEST", root / "evals/narrator/groq_candidates_2026-09-05.json")
    monkeypatch.setattr(probe, "OUTPUT_ROOT", root / "eval-results/continuity-probe")
    monkeypatch.setattr(probe.evaluator, "PROMPT_VARIANTS", {
        probe.FOCUS_VERSION: root / "evals/narrator/prompts/scene-focus-v1.md",
    })
    return root


def forbid_credentials_and_gateway(monkeypatch):
    class NoCredentials:
        def get(self, name, default=None):
            pytest.fail("credential access before live preflight completed")

    def no_gateway(*args, **kwargs):
        pytest.fail("gateway construction is not allowed on this path")

    monkeypatch.setattr(probe, "os", SimpleNamespace(environ=NoCredentials()))
    monkeypatch.setattr(probe, "_live_gateway", no_gateway)


def run_cli(*, live=False, run_id=None):
    identity = run_id or str(uuid4())
    code = probe.main((["--live"] if live else []) + ["--run-id", identity])
    directory = probe.OUTPUT_ROOT / identity
    return code, directory, json.loads((directory / "summary.json").read_text(encoding="utf-8"))


def mutate_fixture(mutate):
    data = json.loads(probe.FIXTURE.read_text(encoding="utf-8"))
    mutate(data)
    probe.FIXTURE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_offline_never_consults_api_environment_or_gateway(local_project, monkeypatch):
    forbid_credentials_and_gateway(monkeypatch)
    code, directory, summary = run_cli()
    assert code == 0 and summary["status"] == "prepared"
    assert summary["calls_started"] == 0
    assert summary["predecessor"]["origin"] == "authored_synthetic_fixture"
    assert summary["predecessor"]["provider_generated"] is False
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["continuation_automated_passed"] is False
    assert not (directory / "response.json").exists()


@pytest.mark.parametrize("failure", [
    "json", "missing_actor_contract", "outcome", "actor", "visibility",
    "no_visible_fact", "secret_disclosure", "private_actor", "same_turn_id",
])
def test_bad_predecessor_stops_before_key_or_packet(local_project, monkeypatch, failure):
    forbid_credentials_and_gateway(monkeypatch)
    if failure == "json":
        probe.FIXTURE.write_text("{broken", encoding="utf-8")
    else:
        def mutate(data):
            predecessor = data["predecessor"]
            if failure == "missing_actor_contract":
                predecessor["f"][0].pop("a")
            elif failure == "outcome":
                predecessor["o"] = "failure"
            elif failure == "actor":
                predecessor["p"] = ["Ivo"]
            elif failure == "visibility":
                predecessor["f"][0]["v"] = "administrator"
            elif failure == "no_visible_fact":
                predecessor["f"] = []
            elif failure == "secret_disclosure":
                data["protected_secrets"] = [predecessor["f"][0]["s"]]
            elif failure == "private_actor":
                predecessor["p"] = ["Celina"]
                predecessor["f"].append({
                    "k": "npc_action", "s": "Celina observa a porta em segredo.",
                    "v": "storyteller", "a": [{"n": "Celina", "p": "present"}],
                })
            else:
                data["continuation"]["turn_id"] = data["predecessor_turn"]["turn_id"]
        mutate_fixture(mutate)
    monkeypatch.setattr(probe.evaluator, "build_system_log", lambda **kwargs: pytest.fail("bad seed reached packet preparation"))
    code, directory, summary = run_cli(live=True)
    assert code == 3 and summary["calls_started"] == 0
    assert not (directory / "request.json").exists()
    assert "predecessor" not in summary


def test_projection_failure_does_not_create_focus_or_request(local_project, monkeypatch):
    forbid_credentials_and_gateway(monkeypatch)
    monkeypatch.setattr(probe, "project_scene", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("unprojectable seed")))
    monkeypatch.setattr(probe, "focus_from_admitted_turn", lambda *args, **kwargs: pytest.fail("unprojected seed acquired focus"))
    code, directory, summary = run_cli(live=True)
    assert code == 3 and summary["calls_started"] == 0
    assert not (directory / "request.json").exists()


@pytest.mark.parametrize("change", ["scene_turn", "episode", "repetition"])
def test_focus_mismatch_is_preflight_failure_before_credentials(local_project, monkeypatch, change):
    forbid_credentials_and_gateway(monkeypatch)
    original = probe.focus_from_admitted_turn

    def bad_focus(*args, **kwargs):
        focus = original(*args, **kwargs)
        update = {
            "scene_turn": {"scene_turn": focus.scene_turn + 1},
            "episode": {"source_turn": "other-episode/authored-predecessor/r1"},
            "repetition": {"source_turn": "authored-continuity/authored-predecessor/r2"},
        }[change]
        return focus.model_copy(update=update)

    monkeypatch.setattr(probe, "focus_from_admitted_turn", bad_focus)
    code, directory, summary = run_cli(live=True)
    assert code == 3 and summary["calls_started"] == 0
    assert not (directory / "request.json").exists()


def test_required_context_over_budget_prevents_key_read_and_dispatch(local_project, monkeypatch):
    forbid_credentials_and_gateway(monkeypatch)
    original = probe.build_focused_packet
    monkeypatch.setattr(probe, "build_focused_packet", lambda *args, **kwargs: original(*args, **kwargs, token_budget=1))
    code, directory, summary = run_cli(live=True)
    assert code == 3 and summary["calls_started"] == 0
    assert summary["local_error"]["type"] == SceneFocusBudgetError.__name__
    assert not (directory / "request.json").exists()


@pytest.mark.parametrize("destination", ["external", "project_root"])
def test_output_is_refused_before_preparation(local_project, tmp_path, monkeypatch, destination):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path / "outside" if destination == "external" else local_project)
    monkeypatch.setattr(probe, "prepare_probe", lambda: pytest.fail("invalid destination reached preparation"))
    assert probe.main(["--run-id", str(uuid4())]) == 3
    assert not (tmp_path / "outside").exists()


def test_existing_run_is_not_overwritten(local_project, monkeypatch):
    forbid_credentials_and_gateway(monkeypatch)
    identity = str(uuid4())
    first, directory, _ = run_cli(run_id=identity)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert first == 0
    assert probe.main(["--run-id", identity]) == 3
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.parametrize("flag", ["--model", "--manifest", "--fixture", "--prompt-variant", "--retries", "--output-dir"])
def test_cli_does_not_offer_scope_or_route_overrides(local_project, monkeypatch, flag):
    monkeypatch.setattr(probe, "prepare_probe", lambda: pytest.fail("unexpected CLI override reached preparation"))
    with pytest.raises(SystemExit) as caught:
        probe.main([flag, "unauthorized"])
    assert caught.value.code == 2
    assert not probe.OUTPUT_ROOT.exists()


@pytest.mark.parametrize("inside", [False, True], ids=["outside_project", "synthetic_dotenv_inside_project"])
def test_redirected_fixture_is_rejected_before_read(local_project, tmp_path, monkeypatch, inside):
    # This is newly authored sentinel data, never the application's real .env.
    target = local_project / ".env" if inside else tmp_path / "outside.json"
    target.write_text("synthetic-do-not-read-sentinel", encoding="utf-8")
    probe.FIXTURE.unlink()
    try:
        probe.FIXTURE.symlink_to(target)
    except OSError:
        pytest.skip("Host does not permit symbolic links; no permissions changed")
    original_read = Path.read_bytes

    def no_target_read(path):
        if path.resolve() == target.resolve():
            pytest.fail("redirected input was read before local-input rejection")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", no_target_read)
    with pytest.raises(ValueError, match="(?:local|project|regular|redirect|input)"):
        probe.prepare_probe()


def request_for(prepared):
    return SimpleNamespace(
        target=prepared.target,
        operation=f"{probe.OPERATION_PREFIX}.{prepared.fixture.episode_id}.{prepared.fixture.continuation.turn_id}.r1",
        response_model=probe.FocusedSceneContinuationProposal,
        messages=tuple(SimpleNamespace(role=SimpleNamespace(value=role), content=content)
                       for role, content in (("system", prepared.prompt), ("user", prepared.packet))),
        parameters=SimpleNamespace(max_output_tokens=probe.OUTPUT_TOKENS, temperature=probe.TEMPERATURE),
    )


@pytest.mark.parametrize("change", ["operation", "target", "schema", "prompt", "packet", "budget", "temperature"])
def test_dispatch_rejects_request_drift_without_call(local_project, change):
    prepared = probe.prepare_probe()
    request = request_for(prepared)
    if change == "operation":
        request.operation = request.operation.replace("CONTINUITY-PROBE", "CAP-001")
    elif change == "target":
        request.target = prepared.target.model_copy(update={"model": "unapproved-model"})
    elif change == "schema":
        request.response_model = probe.evaluator.SceneContinuationProposal
    elif change in {"prompt", "packet"}:
        request.messages[0 if change == "prompt" else 1].content += " changed"
    elif change == "budget":
        request.parameters.max_output_tokens += 1
    else:
        request.parameters.temperature += 0.1
    dispatch = probe.SingleDispatch(SimpleNamespace(generate_structured=lambda _: pytest.fail("drift reached gateway")), prepared)
    with pytest.raises(ValueError, match="prepared request"):
        asyncio.run(dispatch.generate_structured(request))
    assert dispatch.calls_started == 0


@pytest.mark.parametrize("raises", [False, True], ids=["success", "provider_failure"])
def test_one_dispatch_is_not_repeated_even_after_failure(local_project, raises):
    prepared = probe.prepare_probe()
    seen = []

    async def generate(request):
        seen.append(request)
        if raises:
            raise RuntimeError("synthetic provider failure")
        return "synthetic response"

    dispatch = probe.SingleDispatch(SimpleNamespace(generate_structured=generate), prepared)
    request = request_for(prepared)
    if raises:
        with pytest.raises(RuntimeError):
            asyncio.run(dispatch.generate_structured(request))
    else:
        assert asyncio.run(dispatch.generate_structured(request)) == "synthetic response"
    with pytest.raises(ValueError):
        asyncio.run(dispatch.generate_structured(request))
    assert len(seen) == dispatch.calls_started == 1


@pytest.mark.parametrize("after_dispatch", [False, True])
def test_cancellation_preserves_actual_attempt_count(local_project, monkeypatch, after_dispatch, capsys):
    sentinel = "synthetic-key-not-for-output"
    monkeypatch.setattr(probe, "os", SimpleNamespace(environ={"GROQ_API_KEY": sentinel}))
    seen = []
    if after_dispatch:
        async def generate(request):
            seen.append(request)
            raise asyncio.CancelledError()
        monkeypatch.setattr(probe, "_live_gateway", lambda *args: SimpleNamespace(generate_structured=generate))
    else:
        def cancel_preflight():
            raise asyncio.CancelledError()
        monkeypatch.setattr(probe, "prepare_probe", cancel_preflight)
        monkeypatch.setattr(probe, "_live_gateway", lambda *args: pytest.fail("cancelled preflight reached gateway"))
    code, directory, summary = run_cli(live=True)
    assert code == 130 and summary["status"] == "cancelled"
    assert summary["calls_started"] == len(seen) == int(after_dispatch)
    assert summary["cap_001_status"] == "not_evaluated"
    if after_dispatch:
        assert summary["usage_aggregate"]["status"] == "unavailable"
        assert summary["usage_aggregate"]["calls_made"] == 1
        assert summary["usage_aggregate"]["unavailable_calls"] == 1
        assert summary["usage_aggregate"]["totals"]["total_tokens"] is None
        assert summary["cost_aggregate"]["total_amount"] is None
        attempt = json.loads((directory / "response.json").read_text(encoding="utf-8"))
        assert attempt["completion_known"] is False
        assert attempt["admitted"] is False
        assert "proposal" not in attempt
        assert "next_focus" not in attempt
    else:
        assert summary["usage_aggregate"]["status"] == "not_requested"
        assert not (directory / "response.json").exists()
    assert sentinel not in capsys.readouterr().out
    assert all(sentinel not in path.read_text(encoding="utf-8") for path in directory.iterdir())
