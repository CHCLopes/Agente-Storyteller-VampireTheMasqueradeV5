"""SYSTEM-only experiments preserve the transport, contract and evidence."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from api.llm.contract import LLMTarget, MessageRole
from api.scene_service import SceneState
from scripts import evaluate_narrator_models as module


CONTROL = "h6-control-v1"
VARIANT = "scene-beat-v1"
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"
MANIFEST = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
CONTROL_SHA = "b943f9c644d827acb68e214e1c55b6132ffe2ffdf2c02bdb7c842a77990ce2d6"
VARIANT_SHA = "f58f30f69c70a22a4a04b28b524a6684418f17fcdacc2f6bbd2d5f87ec6eccd6"


def test_control_is_frozen_to_the_previous_live_system_prompt():
    path, prompt = module.load_evaluation_prompt(CONTROL)
    assert path.name == f"{CONTROL}.md"
    assert hashlib.sha256(prompt.encode()).hexdigest() == CONTROL_SHA
    assert module.load_evaluation_prompt("runtime")[1] == module.load_storyteller_prompt()


def test_variant_is_bounded_and_does_not_embed_corpus_answers():
    _, prompt = module.load_evaluation_prompt(VARIANT)
    assert hashlib.sha256(prompt.encode()).hexdigest() == VARIANT_SHA
    assert len(prompt.split()) <= 450
    assert prompt != module.load_evaluation_prompt(CONTROL)[1]
    for constraint in (
        "`expected_outcome.value`", "não autoriza contradizer fatos conhecidos",
        "sem cena, crie o local", "Intenção ampla não autoriza microações",
        "Confidenciais ficam fora", "35–70", "até 25", "até 15",
        "mudança exige `npc_action` ou `transition`", "observation/clue exigem `p:true`",
        "nem pedir ao jogador fatos do mundo ou decisões de NPC",
    ):
        assert constraint in prompt
    for corpus_name in ("galpão", "cadeado", "Mara", "Xerife", "cais", "Neófito"):
        assert corpus_name.casefold() not in prompt.casefold()


@pytest.mark.parametrize("value", ["../.env", "C:/secrets.txt", "https://example.com/prompt", "unknown"])
def test_cli_refuses_arbitrary_prompt_paths(value):
    with pytest.raises(SystemExit):
        module._parser().parse_args(["--candidate", CANDIDATE, "--prompt-variant", value])


def test_loader_refuses_unknown_id_without_reading(monkeypatch):
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("must not read"))
    with pytest.raises(ValueError, match="unknown"):
        module.load_evaluation_prompt("../.env")


def test_loader_refuses_redirected_path_before_reading(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "resolve", lambda self: tmp_path / "redirected.md")
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("must not read"))
    with pytest.raises(ValueError, match="allowlisted"):
        module.load_evaluation_prompt(VARIANT)


@pytest.mark.parametrize("variant", ["runtime", CONTROL, VARIANT])
def test_replay_cannot_claim_to_measure_a_new_prompt(variant):
    with pytest.raises(SystemExit, match="cannot be evaluated by --replay"):
        module.main(["--candidate", CANDIDATE, "--replay", "eval-results/missing.jsonl",
                     "--prompt-variant", variant])


def test_variant_still_requires_explicit_network_authorization():
    with pytest.raises(SystemExit, match="without explicit --live"):
        module.main(["--candidate", CANDIDATE, "--prompt-variant", VARIANT])


@pytest.mark.parametrize("episode_index", range(5))
def test_actual_turn_request_differs_only_in_system_content(episode_index):
    episode = module.load_corpus(module.DEFAULT_CORPUS)["episodes"][episode_index]
    requests = []

    class CapturedBeforeDispatch(Exception):
        pass

    class CaptureGateway:
        async def generate_structured(self, request):
            requests.append(request)
            raise CapturedBeforeDispatch

    for variant in (CONTROL, VARIANT):
        with pytest.raises(CapturedBeforeDispatch):
            asyncio.run(module._run_turn(
                gateway=CaptureGateway(), target=LLMTarget(profile="synthetic", provider="Groq", model="fixed"),
                prompt=module.load_evaluation_prompt(variant)[1], episode_id=episode["episode_id"],
                turn=episode["turns"][0], repetition=1,
                scene=SceneState.model_validate(episode["initial_scene"]) if episode["initial_scene"] else None,
                known_context=episode["known_context"], protected_secrets=tuple(episode["protected_secrets"]),
                deadline_seconds=60, temperature=0.65, max_output_tokens=768,
            ))
    control, variant = requests
    assert control.messages[0].role is MessageRole.SYSTEM
    assert control.messages[0].content != variant.messages[0].content
    assert control.messages[1:] == variant.messages[1:]
    assert control.target == variant.target
    assert control.parameters == variant.parameters
    assert control.required_capabilities == variant.required_capabilities
    assert control.response_model is variant.response_model
    # Request IDs/deadlines are intentionally fresh, not experimental factors.
    assert control.operation == variant.operation


@pytest.mark.parametrize("variant", [None, CONTROL, VARIANT])
def test_cli_hashes_and_dispatches_the_same_prompt_once(tmp_path, monkeypatch, variant):
    effective = variant or "runtime"
    path, expected_prompt = module.load_evaluation_prompt(effective)
    reads = []

    def load_once(selection):
        reads.append(selection)
        assert len(reads) == 1
        return path, expected_prompt

    async def evaluate(*args, **kwargs):
        assert kwargs["prompt"] == expected_prompt
        assert kwargs["max_output_tokens"] == 768
        return [{"kind": "narrative_turn", "call_made": False}], {
            "aborted_after_diagnostics": False, "aborted_during_narratives": False,
            "automated_gates_passed": False, "hard_gates": {"diagnostics_passed": True},
        }

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-only")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    monkeypatch.setattr(module, "load_evaluation_prompt", load_once)
    monkeypatch.setattr(module, "evaluate_candidate", evaluate)
    args = ["--live", "--manifest", str(MANIFEST), "--candidate", CANDIDATE,
            "--allow-synthetic-only", "--max-output-tokens", "768", "--batch-id", "prompt-ab-test"]
    if variant is not None:
        args += ["--prompt-variant", variant]
    assert module.main(args) == 1  # Failed gates never become successful experimentation.
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8"))
    record = json.loads(next(tmp_path.glob("*/*.jsonl")).read_text(encoding="utf-8"))
    prompt_meta = summary["inputs"]["prompt"]
    assert prompt_meta == {
        "variant": effective, "file": path.relative_to(module.PROJECT_ROOT).as_posix(),
        "sha256": hashlib.sha256(expected_prompt.encode()).hexdigest(),
    }
    assert record["prompt_variant"] == effective
    assert record["prompt_file"] == prompt_meta["file"]
    assert record["prompt_sha256"] == prompt_meta["sha256"]
    assert summary["batch_id"] == "prompt-ab-test"
    assert "synthetic-test-only" not in json.dumps(summary)
    assert "synthetic-test-only" not in json.dumps(record)


def test_explicit_snapshot_reaches_opening_probe_without_reloading(monkeypatch):
    captured = []

    async def capture(**kwargs):
        captured.append(kwargs["prompt"])
        return {"kind": "narrative_turn", "call_made": False}, None

    monkeypatch.setattr(module, "_run_turn", capture)
    monkeypatch.setattr(module, "load_storyteller_prompt", lambda: pytest.fail("snapshot was replaced"))
    asyncio.run(module.evaluate_candidate(
        module.load_candidates(MANIFEST)[CANDIDATE], module.load_corpus(module.DEFAULT_CORPUS),
        api_key=SecretStr("synthetic-test-only"), repetitions=1, deadline_seconds=60,
        temperature=0.65, max_output_tokens=768, opening_probe=True, prompt="frozen synthetic SYSTEM",
    ))
    assert captured == ["frozen synthetic SYSTEM"]


def test_screening_reuses_snapshot_for_every_turn_without_reloading(monkeypatch):
    captured = []

    async def diagnostics(*args, **kwargs):
        return []

    async def capture(**kwargs):
        captured.append(kwargs["prompt"])
        return {"kind": "narrative_turn", "call_made": False, "admitted": True}, kwargs["scene"]

    monkeypatch.setattr(module, "_run_diagnostics", diagnostics)
    monkeypatch.setattr(module, "_diagnostics_passed", lambda _: True)
    monkeypatch.setattr(module, "summarize", lambda *a: {"diagnostic_rate_limit_occurred": False})
    monkeypatch.setattr(module, "_run_turn", capture)
    monkeypatch.setattr(module, "load_storyteller_prompt", lambda: pytest.fail("snapshot was replaced"))
    asyncio.run(module.evaluate_candidate(
        module.load_candidates(MANIFEST)[CANDIDATE], module.load_corpus(module.DEFAULT_CORPUS),
        api_key=SecretStr("synthetic-test-only"), repetitions=1, deadline_seconds=60,
        temperature=0.65, max_output_tokens=768, prompt="frozen synthetic SYSTEM",
    ))
    assert captured == ["frozen synthetic SYSTEM"] * 7


@pytest.mark.parametrize("failure,expected_code", [(RuntimeError("private body"), 3), (KeyboardInterrupt(), 130)])
def test_variant_identity_survives_failed_or_cancelled_runs(tmp_path, monkeypatch, failure, expected_code):
    async def fail(*args, **kwargs):
        raise failure

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-only")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    monkeypatch.setattr(module, "evaluate_candidate", fail)
    assert module.main(["--live", "--candidate", CANDIDATE, "--manifest", str(MANIFEST),
                        "--allow-synthetic-only", "--prompt-variant", VARIANT]) == expected_code
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8"))
    assert summary["inputs"]["prompt"]["variant"] == VARIANT
    assert summary["process_exit_code"] == expected_code
    assert "private body" not in json.dumps(summary)
    assert "synthetic-test-only" not in json.dumps(summary)


def test_unavailable_prompt_fails_before_provider_or_credential_use(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(module, "load_evaluation_prompt", lambda _: (_ for _ in ()).throw(OSError()))
    with pytest.raises(SystemExit, match="no provider call"):
        module.main(["--live", "--candidate", CANDIDATE, "--manifest", str(MANIFEST),
                     "--allow-synthetic-only", "--prompt-variant", VARIANT])
