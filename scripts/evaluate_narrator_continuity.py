"""One synthetic continuation after an authored, locally admitted predecessor.

Offline preparation is the default. This is neither a full evaluation nor an
A/B experiment; the authored seed is never counted as a provider response.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Literal
from uuid import UUID, uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import BaseModel, ConfigDict, Field, SecretStr  # noqa: E402

from scripts import evaluate_narrator_models as evaluator  # noqa: E402
from scripts.narrator_actor_contract import (  # noqa: E402
    FocusedSceneContinuationProposal, validate_actor_coherence,
)
from scripts.narrator_scene_focus import (  # noqa: E402
    FOCUS_VERSION, LastAdmittedTurnFocus, build_focused_packet, focus_from_admitted_turn,
)
from api.scene_director_service import project_scene, validate_scene_continuation  # noqa: E402
from api.scene_service import SceneState  # noqa: E402

PURPOSE = "continuity_probe"
CANDIDATE_ID = "gpt-oss-120b-groq-free-synthetic-low"
MANIFEST = PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
FIXTURE = PROJECT_ROOT / "evals/narrator/experiments/continuity-probe-v1.json"
OUTPUT_ROOT = PROJECT_ROOT / "eval-results/continuity-probe"
OPERATION_PREFIX = "CONTINUITY-PROBE"
OUTPUT_TOKENS = 768
TEMPERATURE = 0.65
DEADLINE_SECONDS = 60


class ProbeTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    turn_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    player_input: str = Field(min_length=3, max_length=500)
    outcome: Literal["success", "failure", "unresolved"]


class ContinuityFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fixture_id: Literal["continuity-probe-v1"]
    synthetic_only: Literal[True]
    predecessor_origin: Literal["authored_synthetic_fixture"]
    episode_id: Literal["authored-continuity"]
    known_context: str = Field(min_length=3, max_length=600)
    protected_secrets: tuple[str, ...] = Field(max_length=2)
    initial_scene: SceneState
    predecessor_turn: ProbeTurn
    predecessor: FocusedSceneContinuationProposal
    continuation: ProbeTurn


@dataclass(frozen=True)
class PreparedProbe:
    fixture: ContinuityFixture
    scene: SceneState
    focus: LastAdmittedTurnFocus
    candidate: evaluator.Candidate
    target: evaluator.LLMTarget
    prompt: str
    packet: str
    context_audit: dict[str, Any]
    inputs: dict[str, Any]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _local_input(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if (resolved != path.absolute() or resolved.name == ".env" or resolved.name.startswith(".env.")
            or not resolved.is_relative_to(PROJECT_ROOT.resolve()) or not resolved.is_file()):
        raise ValueError("probe input must be a local project file")
    return resolved


def prepare_probe() -> PreparedProbe:
    """Validate the fixed predecessor before any credential access or gateway."""
    fixture_bytes = _local_input(FIXTURE).read_bytes()
    fixture = ContinuityFixture.model_validate_json(fixture_bytes)
    if fixture.predecessor_turn.turn_id == fixture.continuation.turn_id:
        raise ValueError("predecessor and continuation need distinct identities")
    validate_actor_coherence(fixture.predecessor, fixture.initial_scene, player_aliases=("Neófito",))
    validate_scene_continuation(
        fixture.predecessor,
        facts=evaluator._mechanical_facts(fixture.predecessor_turn.outcome, fixture.predecessor_turn.turn_id),
        current_scene=fixture.initial_scene,
        player_input=fixture.predecessor_turn.player_input,
        protected_secrets=fixture.protected_secrets,
        player_aliases=("Neófito",), npc_aliases=fixture.initial_scene.npcs_present,
    )
    scene = project_scene(
        fixture.predecessor, previous=fixture.initial_scene,
        turn_number=fixture.initial_scene.last_turn + 1,
    )
    source = f"{fixture.episode_id}/{fixture.predecessor_turn.turn_id}/r1"
    focus = focus_from_admitted_turn(fixture.predecessor, source_turn=source, scene_turn=scene.last_turn)
    if focus.source_turn != source or focus.scene_turn != scene.last_turn:
        raise ValueError("predecessor focus differs from the validated projection")
    if not focus.visible_facts:
        raise ValueError("continuity probe requires a visible predecessor fact")
    base_packet = evaluator.build_system_log(
        player_input=fixture.continuation.player_input, outcome=fixture.continuation.outcome,
        scene=scene, known_context=fixture.known_context, protected_secrets=fixture.protected_secrets,
    )
    packet, audit = build_focused_packet(
        base_packet, scene=scene, last_focus=focus, player_input=fixture.continuation.player_input,
        known_context=fixture.known_context, protected_secrets=fixture.protected_secrets,
    )
    manifest = _local_input(MANIFEST)
    candidate = evaluator.load_candidates(manifest)[CANDIDATE_ID]
    if (candidate.adapter_kind != "groq" or candidate.model != evaluator.GROQ_GPT_OSS_MODEL_ID
            or candidate.reasoning_effort != "low" or candidate.campaign_data_eligible):
        raise ValueError("continuity probe target differs from the fixed synthetic profile")
    prompt_path = _local_input(evaluator.PROMPT_VARIANTS[FOCUS_VERSION])
    prompt = evaluator.load_storyteller_prompt(prompt_path)
    target = evaluator.LLMTarget(
        profile=f"continuity-probe-{candidate.candidate_id}",
        provider=candidate.provider_label, model=candidate.model,
    )
    schema_text = json.dumps(FocusedSceneContinuationProposal.model_json_schema(by_alias=True),
                             ensure_ascii=False, sort_keys=True)
    inputs = {
        "fixture": {"file": FIXTURE.relative_to(PROJECT_ROOT).as_posix(),
                    "sha256": hashlib.sha256(fixture_bytes).hexdigest()},
        "manifest": {"file": MANIFEST.relative_to(PROJECT_ROOT).as_posix(),
                     "sha256": evaluator._sha256(manifest)},
        "prompt": {"variant": FOCUS_VERSION, "file": prompt_path.relative_to(PROJECT_ROOT).as_posix(),
                   "sha256": _hash_text(prompt)},
        "response_schema_sha256": _hash_text(schema_text),
        "implementation": [
            {"file": file, "sha256": evaluator._sha256(_local_input(PROJECT_ROOT / file))}
            for file in (
                "scripts/evaluate_narrator_continuity.py", "scripts/evaluate_narrator_models.py",
                "scripts/narrator_scene_focus.py", "scripts/narrator_actor_contract.py",
                "api/scene_director_service.py", "api/scene_service.py",
            )
        ],
    }
    return PreparedProbe(fixture, scene, focus, candidate, target, prompt, packet, audit, inputs)


class SingleDispatch:
    """Count the actual invocation boundary and refuse a different request."""
    def __init__(self, gateway, prepared: PreparedProbe):
        self.gateway = gateway
        self.prepared = prepared
        self.calls_started = 0

    async def generate_structured(self, request):
        prepared = self.prepared
        expected_operation = (f"{OPERATION_PREFIX}.{prepared.fixture.episode_id}."
                              f"{prepared.fixture.continuation.turn_id}.r1")
        if (
            self.calls_started or request.target != prepared.target
            or request.operation != expected_operation
            or request.response_model is not FocusedSceneContinuationProposal
            or tuple((message.role.value, message.content) for message in request.messages)
            != (("system", prepared.prompt), ("user", prepared.packet))
            or request.parameters.max_output_tokens != OUTPUT_TOKENS
            or request.parameters.temperature != TEMPERATURE
        ):
            raise ValueError("probe dispatch differs from the prepared request")
        self.calls_started += 1
        return await self.gateway.generate_structured(request)


async def run_probe(prepared: PreparedProbe, gateway: SingleDispatch):
    return await evaluator._run_turn(
        gateway=gateway, target=prepared.target, prompt=prepared.prompt,
        episode_id=prepared.fixture.episode_id,
        turn=prepared.fixture.continuation.model_dump(), repetition=1,
        scene=prepared.scene, known_context=prepared.fixture.known_context,
        protected_secrets=prepared.fixture.protected_secrets,
        deadline_seconds=DEADLINE_SECONDS, temperature=TEMPERATURE,
        max_output_tokens=OUTPUT_TOKENS, scene_focus=True, last_focus=prepared.focus,
        operation_prefix=OPERATION_PREFIX,
    )


def _live_gateway(prepared: PreparedProbe, key: SecretStr):
    return evaluator.GroqAdapter(
        base_url=evaluator.GROQ_OFFICIAL_BASE_URL,
        capability_set=evaluator._capabilities(prepared.candidate, prepared.target),
        api_key=key, reasoning_effort=prepared.candidate.reasoning_effort,
    )


def _write_json(path: Path, payload: Any) -> None:
    # Exclusive artifacts in a fresh, project-local UUID directory. Never amend
    # an earlier observation or accept arbitrary output destinations from CLI.
    with path.open("x", encoding="utf-8", newline="\n") as destination:
        json.dump(payload, destination, ensure_ascii=False, indent=2)
        destination.write("\n")


def _run_id(value: str) -> str:
    try:
        canonical = str(UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("run-id must be a UUID") from exc
    if value != canonical:
        raise argparse.ArgumentTypeError("run-id must be a canonical lowercase UUID")
    return canonical


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="One Groq call using GROQ_API_KEY; otherwise offline.")
    parser.add_argument("--run-id", type=_run_id, default=None)
    args = parser.parse_args(argv)
    run_id = args.run_id or str(uuid4())
    output_root = OUTPUT_ROOT.resolve()
    if (output_root != OUTPUT_ROOT.absolute() or not output_root.is_relative_to(PROJECT_ROOT.resolve())
            or output_root == PROJECT_ROOT.resolve()):
        print("Continuity probe refused: output must stay inside the project.", flush=True)
        return 3
    run_dir = output_root / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except OSError:
        print("Continuity probe refused: cannot create a new result directory.", flush=True)
        return 3
    summary: dict[str, Any] = {
        "schema": "storyteller.continuity-probe.v1", "purpose": PURPOSE,
        "run_id": run_id, "selected_candidate_id": CANDIDATE_ID, "prompt_variant": FOCUS_VERSION,
        "mode": "live" if args.live else "offline_preparation",
        "started_at": evaluator.utc_now().isoformat(), "full_evaluation": False,
        "cap_001_status": "not_evaluated", "human_review_required": True,
        "complete_ab_experiment": False, "runtime_promoted": False,
        "maximum_provider_calls": 1, "diagnostics_executed": False, "automatic_retries": 0,
        "fallback": False, "calls_started": 0, "continuation_automated_passed": False,
        "continuity_human_assessment": None,
    }
    prepared = None
    dispatch = None
    records: list[dict[str, Any]] = []
    exit_code = 3
    key = SecretStr("")
    try:
        prepared = prepare_probe()
        summary.update({
            "inputs": prepared.inputs, "candidate_policy": evaluator._candidate_policy_payload(prepared.candidate),
            "requested_target": prepared.target.model_dump(mode="json"),
            "generation_parameters": {"max_output_tokens": OUTPUT_TOKENS, "temperature": TEMPERATURE,
                                      "deadline_seconds": DEADLINE_SECONDS},
            "generation_context": prepared.context_audit,
            "predecessor": {"origin": "authored_synthetic_fixture", "provider_generated": False, "call_made": False,
                            "schema_valid": True, "admitted_locally": True, "projected_locally": True,
                            "source_turn": prepared.focus.source_turn, "scene_turn": prepared.scene.last_turn},
        })
        request_artifact = {
            "purpose": PURPOSE, "synthetic_only": True,
            "predecessor": summary["predecessor"], "inputs": prepared.inputs,
            "requested_target": summary["requested_target"],
            "generation_parameters": summary["generation_parameters"],
            "generation_context": prepared.context_audit,
            "messages": [{"role": "system", "content": prepared.prompt}, {"role": "user", "content": prepared.packet}],
            "response_schema": FocusedSceneContinuationProposal.model_json_schema(by_alias=True),
        }
        _write_json(run_dir / "request.json", request_artifact)
        summary["request_artifact_sha256"] = evaluator._sha256(run_dir / "request.json")
        if args.live:
            raw_key = os.environ.get("GROQ_API_KEY", "")
            if not raw_key.strip():
                summary.update({"status": "local_error", "local_error": {"code": "missing_api_key"}})
            else:
                key = SecretStr(raw_key)
                raw_key = ""
                dispatch = SingleDispatch(_live_gateway(prepared, key), prepared)
                record, _ = asyncio.run(run_probe(prepared, dispatch))
                record.update({"purpose": PURPOSE, "run_id": run_id, "prompt_variant": FOCUS_VERSION,
                               "cap_001_status": "not_evaluated", "predecessor": summary["predecessor"]})
                records.append(record)
                route = evaluator.summarize(prepared.candidate, records, 1)["route_verification"]
                error = record.get("llm_error") or {}
                availability = error.get("category") in evaluator._NARRATIVE_AVAILABILITY_ERROR_CATEGORIES
                passed = bool(record.get("schema_valid") and record.get("admitted")
                              and route["status"] == "verified" and not error)
                local_failure = bool(record.get("local_error") or error.get("category") == "adapter_failure")
                exit_code = 3 if local_failure else 2 if availability else 0 if passed else 1
                summary.update({
                    "status": "local_error" if local_failure else "observed",
                    "continuation_automated_passed": passed, "route_verification": route,
                    "schema_valid": record.get("schema_valid") is True, "admitted": record.get("admitted") is True,
                    "admission_error": record.get("admission_error"),
                    "admission_evidence": record.get("admission_evidence"),
                    "llm_error": record.get("llm_error"), "local_error": record.get("local_error"),
                    "latency_seconds": record.get("latency_seconds"),
                })
        else:
            summary["status"] = "prepared"
            exit_code = 0
    except (KeyboardInterrupt, asyncio.CancelledError):
        summary["status"] = "cancelled"
        exit_code = 130
    except Exception as exc:
        # Exception messages may contain a credential or hostile provider text.
        summary.update({"status": "local_error", "local_error": {"type": type(exc).__name__}})
        exit_code = 3
    finally:
        key = SecretStr("")
    summary["calls_started"] = dispatch.calls_started if dispatch else 0
    if summary["calls_started"] and not records:
        # A cancelled/failed await may not return the evaluator's local record.
        # Keep the attempt visible without inventing completion or measurements.
        records.append({
            "kind": "narrative_turn", "call_made": True, "purpose": PURPOSE,
            "run_id": run_id, "status": summary["status"], "completion_known": False,
            "prompt_variant": FOCUS_VERSION, "cap_001_status": "not_evaluated",
            "schema_valid": False, "admitted": False,
        })
    summary["usage_aggregate"] = evaluator._aggregate_usage(records, expected_calls=summary["calls_started"])
    summary["cost_aggregate"] = evaluator._aggregate_cost(records, expected_calls=summary["calls_started"])
    if not summary["calls_started"]:
        summary["usage_aggregate"].update({"status": "not_requested", "totals": None})
        summary["cost_aggregate"]["status"] = "not_requested"
    summary.update({"finished_at": evaluator.utc_now().isoformat(), "process_exit_code": exit_code})
    if records:
        _write_json(run_dir / "response.json", records[0])
    summary_path = run_dir / "summary.json"
    _write_json(summary_path, summary)
    print(f"Continuity probe {summary['status']} (exit {exit_code}); CAP-001 not evaluated: {summary_path}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
