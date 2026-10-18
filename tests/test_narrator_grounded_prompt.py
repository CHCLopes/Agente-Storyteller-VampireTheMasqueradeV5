"""SYSTEM-only variants retain the exact scene-focus request contract."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from api.llm.contract import LLMTarget, MessageRole
from api.scene_director_service import project_scene, validate_scene_continuation
from api.scene_service import SceneState
from scripts import evaluate_narrator_models as module
from scripts.narrator_actor_contract import FocusedSceneContinuationProposal
from scripts.narrator_scene_focus import FOCUS_VERSION, focus_from_admitted_turn


GROUNDED = "scene-grounded-v1"
ATTRIBUTED = "scene-attributed-v1"
FAITHFUL = "scene-faithful-v1"
FAITHFUL_SYSTEM_SHA = "76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2"
ATTRIBUTED_SYSTEM_SHA = "da0b9087b7adcdfd2a70cf3d64c91b72eb163ce2d338f18268b10e4cd8f34aab"
GROUNDED_SYSTEM_SHA = "ff47d144200ddaac14c7db30f6328f73de5fb466730fe178fb49dc335dbac331"
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"
MANIFEST = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
FROZEN_PROMPT_HASHES = {
    "h6-control-v1": "b943f9c644d827acb68e214e1c55b6132ffe2ffdf2c02bdb7c842a77990ce2d6",
    "scene-beat-v1": "f58f30f69c70a22a4a04b28b524a6684418f17fcdacc2f6bbd2d5f87ec6eccd6",
    FOCUS_VERSION: "830454df2171dabcc0bb9aeb5f775fa7b6f29066ac0dbd2675f5de14ed8b4252",
}


def _cli_args(*extra, variant=GROUNDED):
    return ["--candidate", CANDIDATE, "--manifest", str(MANIFEST),
            "--allow-synthetic-only", "--prompt-variant", variant, *extra]


def _credential_guard(monkeypatch, *, synthetic_key=None):
    original_get = module.os.environ.get

    def guarded_get(name, default=None):
        if name.endswith("API_KEY"):
            if name == "GROQ_API_KEY" and synthetic_key is not None:
                return synthetic_key
            pytest.fail("credential accessed before configuration admission")
        return original_get(name, default)

    monkeypatch.setattr(module.os.environ, "get", guarded_get)


def test_grounded_registration_does_not_change_legacy_prompt_or_context_versions():
    assert module.GROUNDING_PROMPT_VERSION == GROUNDED
    assert module.FOCUS_PROMPT_VARIANTS == frozenset({FOCUS_VERSION, GROUNDED, ATTRIBUTED, FAITHFUL})
    assert module.ATTRIBUTION_PROMPT_VERSION == ATTRIBUTED
    assert module.FIDELITY_PROMPT_VERSION == FAITHFUL
    faithful_path, faithful_prompt = module.load_evaluation_prompt(FAITHFUL)
    assert faithful_path == module.PROJECT_ROOT / "evals/narrator/prompts/scene-faithful-v1.md"
    assert hashlib.sha256(faithful_prompt.encode()).hexdigest() == FAITHFUL_SYSTEM_SHA
    attributed_path, attributed_prompt = module.load_evaluation_prompt(ATTRIBUTED)
    assert attributed_path == module.PROJECT_ROOT / "evals/narrator/prompts/scene-attributed-v1.md"
    assert hashlib.sha256(attributed_prompt.encode()).hexdigest() == ATTRIBUTED_SYSTEM_SHA
    assert FOCUS_VERSION == "scene-focus-v1"
    path, prompt = module.load_evaluation_prompt(GROUNDED)
    assert path == module.PROJECT_ROOT / "evals/narrator/prompts/scene-grounded-v1.md"
    assert hashlib.sha256(prompt.encode()).hexdigest() == GROUNDED_SYSTEM_SHA
    assert prompt != module.load_evaluation_prompt(FOCUS_VERSION)[1]
    for variant, expected in FROZEN_PROMPT_HASHES.items():
        assert hashlib.sha256(module.load_evaluation_prompt(variant)[1].encode()).hexdigest() == expected
    assert module.load_evaluation_prompt("runtime")[1] == module.load_storyteller_prompt()


def _capture_pair(*, episode_id, turn, scene, known_context, secrets, focus=None,
                  baseline=FOCUS_VERSION, variant=GROUNDED):
    requests = []

    class CapturedBeforeDispatch(Exception):
        pass

    class CaptureGateway:
        async def generate_structured(self, request):
            requests.append(request)
            raise CapturedBeforeDispatch

    for selection in (baseline, variant):
        with pytest.raises(CapturedBeforeDispatch):
            asyncio.run(module._run_turn(
                gateway=CaptureGateway(), target=LLMTarget(profile="synthetic", provider="Groq", model="fixed"),
                prompt=module.load_evaluation_prompt(selection)[1], episode_id=episode_id,
                turn=turn, repetition=1, scene=scene, known_context=known_context,
                protected_secrets=secrets, deadline_seconds=60, temperature=0.65,
                max_output_tokens=768, scene_focus=True, last_focus=focus,
            ))
    control, grounded = requests
    assert control.messages[0].role is grounded.messages[0].role is MessageRole.SYSTEM
    assert control.messages[0].content != grounded.messages[0].content
    assert control.messages[1:] == grounded.messages[1:]
    assert control.response_model is grounded.response_model is FocusedSceneContinuationProposal
    # Compare every serialized request field; only fresh identity/deadline and
    # the independently checked SYSTEM message may differ. Cancellation is local.
    exclude = {"messages", "invocation_id", "deadline"}
    assert control.model_dump(exclude=exclude) == grounded.model_dump(exclude=exclude)
    assert control.cancellation.is_cancelled is grounded.cancellation.is_cancelled is False
    assert control.cancellation.reason is grounded.cancellation.reason is None
    return control, grounded


@pytest.mark.parametrize("baseline,variant", [(FOCUS_VERSION, GROUNDED), (GROUNDED, ATTRIBUTED), (ATTRIBUTED, FAITHFUL)])
@pytest.mark.parametrize("episode_index", range(5))
def test_actual_initial_episode_requests_differ_only_in_system(episode_index, baseline, variant):
    episode = module.load_corpus(module.DEFAULT_CORPUS)["episodes"][episode_index]
    _capture_pair(
        episode_id=episode["episode_id"], turn=episode["turns"][0],
        scene=SceneState.model_validate(episode["initial_scene"]) if episode["initial_scene"] else None,
        known_context=episode["known_context"], secrets=tuple(episode["protected_secrets"]),
        baseline=baseline, variant=variant,
    )


@pytest.mark.parametrize("baseline,variant", [(FOCUS_VERSION, GROUNDED), (GROUNDED, ATTRIBUTED), (ATTRIBUTED, FAITHFUL)])
def test_actual_continuation_requests_preserve_nonempty_admitted_focus(baseline, variant):
    fixture = json.loads((module.PROJECT_ROOT / "evals/narrator/experiments/continuity-probe-v1.json").read_text(encoding="utf-8"))
    scene = SceneState.model_validate(fixture["initial_scene"])
    predecessor = FocusedSceneContinuationProposal.model_validate(fixture["predecessor"])
    validate_scene_continuation(
        predecessor, facts=module._mechanical_facts("success", "authored-predecessor"),
        current_scene=scene, player_input=fixture["predecessor_turn"]["player_input"],
    )
    scene = project_scene(predecessor, previous=scene, turn_number=2)
    focus = focus_from_admitted_turn(
        predecessor, source_turn="authored-continuity/authored-predecessor/r1", scene_turn=2,
    )
    control, grounded = _capture_pair(
        episode_id=fixture["episode_id"], turn=fixture["continuation"], scene=scene,
        known_context=fixture["known_context"], secrets=(), focus=focus,
        baseline=baseline, variant=variant,
    )
    packet = json.loads(grounded.messages[1].content.split("\n", 1)[1])
    assert packet["context"]["last_turn_focus"]["data"] == focus.model_dump(mode="json")
    assert packet["context"]["last_turn_focus"]["data"]["visible_facts"]
    assert grounded.messages[1].content == control.messages[1].content


@pytest.mark.parametrize("variant", [GROUNDED, ATTRIBUTED, FAITHFUL])
def test_nonlive_grounded_selection_never_accesses_a_credential(monkeypatch, variant):
    _credential_guard(monkeypatch)
    with pytest.raises(SystemExit, match="without explicit --live"):
        module.main(_cli_args(variant=variant))


@pytest.mark.parametrize("selection", ["../.env", "C:/secrets.txt", "https://example.com/prompt", "unknown"])
def test_arbitrary_selection_is_refused_before_prompt_or_credential_read(monkeypatch, selection):
    _credential_guard(monkeypatch)
    monkeypatch.setattr(module, "load_evaluation_prompt", lambda _: pytest.fail("prompt read"))
    with pytest.raises(SystemExit):
        module.main(["--live", "--candidate", CANDIDATE, "--prompt-variant", selection])


@pytest.mark.parametrize("variant", [GROUNDED, ATTRIBUTED, FAITHFUL])
def test_missing_grounded_file_aborts_before_credential_or_provider(tmp_path, monkeypatch, variant):
    _credential_guard(monkeypatch)
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    monkeypatch.setitem(module.PROMPT_VARIANTS, variant, tmp_path / "missing-system.md")
    monkeypatch.setattr(module, "evaluate_candidate", lambda *a, **k: pytest.fail("provider reached"))
    with pytest.raises(SystemExit, match="no provider call"):
        module.main(_cli_args("--live", variant=variant))


@pytest.mark.parametrize("variant", [GROUNDED, ATTRIBUTED, FAITHFUL])
def test_redirected_grounded_prompt_is_refused_before_read(monkeypatch, tmp_path, variant):
    monkeypatch.setattr(Path, "resolve", lambda self: tmp_path / "redirected.md")
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("redirected file read"))
    with pytest.raises(ValueError, match="allowlisted"):
        module.load_evaluation_prompt(variant)


@pytest.mark.parametrize("variant", [FOCUS_VERSION, GROUNDED, ATTRIBUTED, FAITHFUL])
@pytest.mark.parametrize("marker", ["prompt_only", "context_only", "packet_only"])
def test_legacy_replay_refuses_every_focus_variant_before_schema_downgrade(monkeypatch, variant, marker):
    record = {
        "prompt_only": {"prompt_variant": variant},
        "context_only": {"scene_context_version": FOCUS_VERSION},
        "packet_only": {"generation_context": {"version": FOCUS_VERSION}},
    }[marker]
    monkeypatch.setattr(module.SceneContinuationProposal, "model_validate", lambda *a, **k: pytest.fail("legacy schema reached"))
    with pytest.raises(ValueError, match="legacy replay refused"):
        module.replay_admission([record], {})


@pytest.mark.parametrize("invalid_marker", [[], {}])
def test_untrusted_non_string_variant_does_not_crash_replay_filter(invalid_marker):
    with pytest.raises(ValueError, match="no narrative records"):
        module.replay_admission([{"prompt_variant": invalid_marker}], {})


@pytest.mark.parametrize("variant", [GROUNDED, ATTRIBUTED, FAITHFUL])
@pytest.mark.parametrize("extra,expected", [
    (["--replay", "eval-results/missing.jsonl"], "cannot be evaluated by --replay"),
    (["--live", "--opening-probe"], "full synthetic corpus"),
])
def test_grounded_cannot_use_legacy_replay_or_an_opening_probe(monkeypatch, tmp_path, extra, expected, variant):
    _credential_guard(monkeypatch)
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    with pytest.raises(SystemExit, match=expected):
        module.main(_cli_args(*extra, variant=variant))


@pytest.mark.parametrize("variant", [FOCUS_VERSION, GROUNDED, ATTRIBUTED, FAITHFUL])
def test_cli_uses_exact_prompt_hash_and_focus_contract_metadata(tmp_path, monkeypatch, capsys, variant):
    _credential_guard(monkeypatch, synthetic_key="synthetic-grounded-test")
    expected_path, expected_prompt = module.load_evaluation_prompt(variant)
    reads = []

    def load_once(selection):
        reads.append(selection)
        assert reads == [variant]
        return expected_path, expected_prompt

    async def capture(*args, **kwargs):
        assert kwargs["prompt"] == expected_prompt
        assert kwargs["scene_focus"] is True
        assert kwargs["max_output_tokens"] == 768
        assert kwargs["temperature"] == 0.65
        return [{"kind": "narrative_turn", "call_made": False}], {
            "hard_gates": {"diagnostics_passed": True}, "automated_gates_passed": False,
            "aborted_after_diagnostics": False, "aborted_during_narratives": False,
        }

    monkeypatch.setattr(module, "load_evaluation_prompt", load_once)
    monkeypatch.setattr(module, "evaluate_candidate", capture)
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    assert module.main(["--live", "--candidate", CANDIDATE, "--manifest", str(MANIFEST),
        "--allow-synthetic-only", "--prompt-variant", variant,
        "--max-output-tokens", "768", "--temperature", "0.65"]) == 1
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8"))
    record = json.loads(next(tmp_path.glob("*/*.jsonl")).read_text(encoding="utf-8"))
    expected_hash = hashlib.sha256(expected_prompt.encode()).hexdigest()
    assert summary["inputs"]["prompt"] == {
        "variant": variant, "file": expected_path.relative_to(module.PROJECT_ROOT).as_posix(),
        "sha256": expected_hash,
    }
    assert record["prompt_variant"] == variant
    assert record["prompt_sha256"] == expected_hash
    assert record["scene_context_version"] == FOCUS_VERSION
    metadata = summary["inputs"]["scene_focus_experiment"]
    assert metadata == record["scene_focus_experiment"]
    assert metadata["runtime_promoted"] is metadata["complete_ab_experiment"] is False
    assert metadata["human_review_required"] is True
    assert metadata["response_schema_sha256"] == hashlib.sha256(json.dumps(
        FocusedSceneContinuationProposal.model_json_schema(by_alias=True),
        sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()
    assert all(item["sha256"] == module._sha256(module.PROJECT_ROOT / item["file"])
               for item in metadata["implementation"])
    if variant in {GROUNDED, ATTRIBUTED, FAITHFUL}:
        assert metadata["version"] == variant
        assert metadata["context_contract_version"] == FOCUS_VERSION
        assert metadata["baseline_prompt_variant"] == {
            GROUNDED: FOCUS_VERSION, ATTRIBUTED: GROUNDED, FAITHFUL: ATTRIBUTED,
        }[variant]
        assert metadata["interventions"] == ["system_prompt"]
        assert metadata["causal_comparison"] is False
        assert "historical single-arm comparisons are not causal A/B" in capsys.readouterr().out
    else:
        assert metadata["version"] == FOCUS_VERSION
        assert metadata["interventions"] == ["system_prompt", "last_turn_context", "actor_contract"]
        assert "context_contract_version" not in metadata
        assert "baseline_prompt_variant" not in metadata
        assert "causal_comparison" not in metadata
    assert "synthetic-grounded-test" not in json.dumps(summary)
    assert "synthetic-grounded-test" not in json.dumps(record)


@pytest.mark.parametrize("variant", [FOCUS_VERSION, GROUNDED, ATTRIBUTED, FAITHFUL])
def test_rejected_predecessor_still_skips_both_continuations(monkeypatch, variant):
    calls = []

    async def diagnostics(*args, **kwargs):
        return []

    async def reject(**kwargs):
        calls.append(kwargs)
        return {"kind": "narrative_turn", "call_made": True, "admitted": False,
                "episode_id": kwargs["episode_id"], "turn_id": kwargs["turn"]["turn_id"],
                "repetition": 1}, kwargs["scene"]

    monkeypatch.setattr(module, "_run_diagnostics", diagnostics)
    monkeypatch.setattr(module, "_diagnostics_passed", lambda _: True)
    monkeypatch.setattr(module, "summarize", lambda *a: {"diagnostic_rate_limit_occurred": False})
    monkeypatch.setattr(module, "_run_turn", reject)
    prompt = module.load_evaluation_prompt(variant)[1]
    records, _ = asyncio.run(module.evaluate_candidate(
        module.load_candidates(MANIFEST)[CANDIDATE], module.load_corpus(module.DEFAULT_CORPUS),
        api_key=SecretStr("synthetic-grounded-test"), repetitions=1, deadline_seconds=60,
        temperature=0.65, max_output_tokens=768, prompt=prompt, scene_focus=True,
    ))
    assert len(calls) == 5
    assert all(call["scene_focus"] is True and call["prompt"] == prompt for call in calls)
    assert all(call["last_focus"] is None for call in calls)
    skips = [record for record in records if record["kind"] == "narrative_skip"]
    assert [record["turn_id"] for record in skips] == ["follow-discovered-detail", "wait-for-world-reaction"]
    assert all(record["blocked_by_turn_id"] == "investigate-success" for record in skips)
    assert all(record["call_made"] is False and "proposal" not in record for record in skips)
