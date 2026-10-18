"""Bounded synthetic source-continuation probe, isolated from product turns."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4, uuid5

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr, ValidationError
from scripts import evaluate_narrator_models as shared
from scripts import narrator_source_profile as profile
from api.narrative_grounding import SourceProjection, NarrativeGroundingError
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from scripts.narrator_record_budget_observer import BudgetObservationAdapter
from api.llm.adapters.groq import GroqAdapter, GROQ_OFFICIAL_BASE_URL, GROQ_QWEN_MODEL_ID, _normalize_groq_strict_schema
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement, CapabilitySet, CancellationToken, GenerationParameters,
    GenerationRequest, LLMInvocationError, LLMMessage, LLMTarget, MessageRole,
    StructuredGenerationRequest, utc_now,
)

CANDIDATE_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"
TARGET_PROFILE = "narrative-source-qwen-3.8-27b-groq-free-synthetic-nonthink"
CASE_ID = "greenhouse-observe-wait"
TURN_IDS = ("observe", "wait")
PROBE_KIND = "narrative_source_probe"
EXPERIMENT_VERSION = "narrative-source-observation-v1"
PROTOCOL = "narrative-source-profile-v1"
PROMPT_VARIANT = "narrative-source-v1"
MAX_CALLS = 2
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
MANIFEST_PATH = PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
MANIFEST_SHA256 = "de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6"
CASE_PATH = PROJECT_ROOT / "evals/narrator/narrative_source_case_v1.json"
CASE_SHA256 = "32f99638fed2c2acf7cdd59744d1217e3e2357401d5186e7a506ed939cacd1d8"
COURTYARD_CASE_ID = "courtyard-observe-wait"
COURTYARD_CASE_PATH = PROJECT_ROOT / "evals/narrator/narrative_source_case_courtyard_v1.json"
COURTYARD_CASE_SHA256 = "c1441274bc8ceb088a7e30c5de0411310db642d14fee514ce6d04d867fa4f469"
CASE_CHOICES = (CASE_ID, COURTYARD_CASE_ID)
PROMPT_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-v1.md"
PROMPT_FILE_SHA256 = "8859291d17c6036166878802839204d8b770f17c442dcd178c24cc357929477d"
PROMPT_SHA256 = "147588db153513bb5da8a0aff3f0ef67773481b8feabc40093de4f8bd259084c"
CORE_SHA256 = "417962e0fffc216a77153748f742a86e2b761fd5a3041e74181d8803128b61a3"
PROFILE_SHA256 = "ba6c8e49b8d9dcadb8fcfc7500ebfe812485bbaf3062098f572743fdcd76e112"
AVAILABILITY_CATEGORIES = frozenset({"timeout", "rate_limited", "quota_exceeded", "provider_unavailable"})
PREFLIGHT_BATCH = "00000000-0000-0000-0000-000000000000"
MAX_ARTIFACT_BYTES = 1024 * 1024


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_sha(value: Any) -> str:
    return _sha(_canonical(value))


def _scope() -> dict[str, Any]:
    return {"purpose": PROBE_KIND, "probe_kind": PROBE_KIND,
            "experiment_version": EXPERIMENT_VERSION, "protocol": PROTOCOL,
            "selected_candidate_id": CANDIDATE_ID, "synthetic_only": True,
            "full_evaluation": False, "runtime_promoted": False,
            "canonical_admission": False, "cap_001_status": "not_evaluated",
            "automated_gates_passed": False, "human_review_required": True,
            "semantic_not_evaluated": True, "full_record_derivation": False,
            "diagnostics_executed": False, "automatic_retries": 0,
            "max_calls": MAX_CALLS, "repetitions": 1, "causal_comparison": False}


def _parameters() -> dict[str, Any]:
    return {"deadline_seconds": 60, "minimum_inter_call_delay_seconds": 60,
            "initial_quiet_seconds": 60,
            "requested": {"temperature": 0.65, "max_output_tokens": 768},
            "transmitted": {"temperature": 0.65, "max_output_tokens": 768, "reasoning_effort": "none"},
            "max_total_output_tokens": 1536,
            "user_packet_budget": {"estimated_tokens": 2000, "method": "characters_divided_by_4"}}


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    case: dict[str, Any]
    prompt: str
    metadata: dict[str, Any]


def _scene(prepared: PreparedExperiment) -> SceneState:
    return SceneState.model_validate(prepared.case["scene"])


def _invocation_id(batch_id: str, index: int) -> str:
    return str(uuid5(UUID(batch_id), f"narrative-source.{TURN_IDS[index]}"))


def build_user_packet(prepared: PreparedExperiment, index: int, batch_id: str,
                      prior_sources: tuple[SourceProjection, ...] = ()) -> str:
    _batch_id(batch_id)
    if type(index) is not int or index not in range(MAX_CALLS) or len(prior_sources) != index:
        raise ValueError("source_probe_source_chain_invalid")
    if index and (prior_sources[0].source.turn_id != TURN_IDS[0]
                  or prior_sources[0].source.invocation_id != _invocation_id(batch_id, 0)):
        raise ValueError("source_probe_source_chain_identity_invalid")
    turn = prepared.case["turns"][index]
    packet = _canonical({"turn": turn["turn_id"], "player_input": turn["player_input"],
                         "context": profile.build_source_context(
                             session_id=batch_id, current_scene=_scene(prepared), attributed_sources=prior_sources)})
    if (len(packet) + 3) // 4 > 2000:
        raise ValueError("source_probe_user_budget_exceeded")
    return packet


def _make_request(prepared: PreparedExperiment, index: int, batch_id: str,
                  prior_sources: tuple[SourceProjection, ...] = ()) -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        operation=f"narrative-source.{TURN_IDS[index]}", target=prepared.target,
        invocation_id=_invocation_id(batch_id, index),
        messages=(LLMMessage(role=MessageRole.SYSTEM, content=prepared.prompt),
                  LLMMessage(role=MessageRole.USER, content=build_user_packet(prepared, index, batch_id, prior_sources))),
        deadline=utc_now() + shared._seconds(60), cancellation=CancellationToken(),
        parameters=GenerationParameters(temperature=0.65, max_output_tokens=768),
        response_model=profile.NarrativeSourceProposal,
        required_capabilities=(CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
                               CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION, allow_emulated=False)))


def _fixed_payload(request: StructuredGenerationRequest) -> dict[str, Any]:
    builder = object.__new__(GroqAdapter)
    builder._reasoning_effort = "none"
    return builder._payload(request, stream=False, response_format=builder._native_response_format(request))


class NarrativeSourceObservationAdapter(BudgetObservationAdapter):
    def __init__(self, *, turn_id: str, approved_body_sha256: str,
                 base_url: str, capability_set: CapabilitySet, api_key: SecretStr | None,
                 reasoning_effort: str | None, adapter_version: str = "1.0", transport: Any = None):
        target = capability_set.target
        if (turn_id not in TURN_IDS or target.profile != TARGET_PROFILE or target.provider != "Groq"
                or target.model != GROQ_QWEN_MODEL_ID or reasoning_effort != "none"
                or re.fullmatch(r"[0-9a-f]{64}", approved_body_sha256) is None):
            raise ValueError("source_probe_observer_identity_invalid")
        super().__init__(base_url=base_url, capability_set=capability_set, api_key=api_key,
                         reasoning_effort=reasoning_effort, adapter_version=adapter_version, transport=transport)
        self._turn_id = turn_id
        self._approved_body_sha256 = approved_body_sha256

    def _effective_model(self, payload: dict[str, Any]) -> str | None:
        return GROQ_QWEN_MODEL_ID if payload.get("model") == GROQ_QWEN_MODEL_ID else None

    def _payload(self, request: GenerationRequest, *, stream: bool,
                 response_format: dict[str, Any] | None) -> dict[str, Any]:
        payload = GroqAdapter._payload(self, request, stream=stream, response_format=response_format)
        if (stream or self._dispatch_started or request.operation != f"narrative-source.{self._turn_id}"
                or _canonical_sha(payload) != self._approved_body_sha256):
            raise ValueError("source_probe_one_use_request_mismatch")
        self._dispatch_started = True
        return payload


def prepare_experiment(case_id: str = CASE_ID) -> PreparedExperiment:
    """Keyless preparation; the second USER is intentionally not knowable yet."""
    if case_id == CASE_ID:
        case_path, case_sha256 = CASE_PATH, CASE_SHA256
    elif case_id == COURTYARD_CASE_ID:
        case_path, case_sha256 = COURTYARD_CASE_PATH, COURTYARD_CASE_SHA256
    else:
        raise ValueError("source_probe_case_selection_invalid")
    for path, expected in ((MANIFEST_PATH, MANIFEST_SHA256), (case_path, case_sha256),
                           (PROMPT_PATH, PROMPT_FILE_SHA256),
                           (PROJECT_ROOT / "api/narrative_grounding.py", CORE_SHA256),
                           (PROJECT_ROOT / "scripts/narrator_source_profile.py", PROFILE_SHA256)):
        if shared._sha256(path) != expected:
            raise ValueError("source_probe_input_fingerprint_changed")
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    if (candidate.adapter_kind != "groq" or candidate.model != GROQ_QWEN_MODEL_ID
            or candidate.provider_label != "Groq" or candidate.effective_provider != "Groq"
            or candidate.upstream_provider is not None or candidate.structured_mode != "native"
            or candidate.reasoning_effort != "none" or candidate.campaign_data_eligible):
        raise ValueError("source_probe_candidate_invalid")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if (set(case) != {"schema", "case_id", "synthetic_only", "origin", "scene", "turns"}
            or case["schema"] != "storyteller.eval.narrative-source-case.v1"
            or case["case_id"] != case_id or case["synthetic_only"] is not True
            or case["origin"] != "agent_authored_synthetic_case"
            or tuple(t["turn_id"] for t in case["turns"]) != TURN_IDS):
        raise ValueError("source_probe_case_invalid")
    document = PROMPT_PATH.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    if front is None:
        raise ValueError("source_probe_prompt_invalid")
    prompt = document[front.end():].strip()
    if _sha(prompt) != PROMPT_SHA256 or profile.VERSION != PROTOCOL:
        raise ValueError("source_probe_prompt_or_profile_changed")
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=candidate.model)
    provenance = shared._evaluator_provenance()
    provenance.update(file="scripts/evaluate_narrator_source.py", sha256=shared._sha256(Path(__file__).resolve()))
    files = ("api/narrative_grounding.py", "scripts/narrator_source_profile.py", "api/scene_director_service.py",
             "api/scene_service.py", "api/turn_models.py", "scripts/narrator_record_budget_observer.py",
             "scripts/evaluate_narrator_models.py", "api/llm/adapters/groq.py",
             "api/llm/adapters/openai_compatible.py", "api/llm/contract.py")
    schema = profile.NarrativeSourceProposal.model_json_schema()
    metadata = {**_scope(), "evaluator": provenance,
        "candidate_policy": {name: getattr(candidate, name) for name in (
            "adapter_kind", "provider_label", "effective_provider", "upstream_provider", "structured_mode",
            "require_zdr", "allow_data_collection", "campaign_data_eligible", "expiration_date", "reasoning_effort")},
        "narrative_generation_parameters": _parameters(), "inputs": {
            "manifest": {"file": MANIFEST_PATH.name, "sha256": MANIFEST_SHA256},
            "case": {"file": case_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": case_sha256,
                     "case_id": case_id, "origin": case["origin"], "turns": copy.deepcopy(case["turns"]),
                     "canonical_scene": copy.deepcopy(case["scene"])},
            "prompt": {"variant": PROMPT_VARIANT, "file": PROMPT_PATH.relative_to(PROJECT_ROOT).as_posix(),
                       "file_sha256": PROMPT_FILE_SHA256, "sha256": PROMPT_SHA256},
            "response_schema_sha256": _canonical_sha(schema),
            "provider_schema_sha256": _canonical_sha(_normalize_groq_strict_schema(schema)),
            "source_policy": {"profile": PROTOCOL, "core_protocol": "narrative-source-v1",
                "normalization": profile.TEXT_NORMALIZATION, "source_field": "n", "question_is_source": False,
                "representation": "projected_source", "canonical_truth_confirmed": False,
                "session_id": "batch_id", "turn_ids": list(TURN_IDS),
                "invocation_id": "uuid5(batch_id,narrative-source.turn_id)",
                "user_serialization": "json_unicode_sorted_compact", "second_user": "previous_complete_source_only"},
            "observation_policy": {"max_error_body_bytes": 65536, "raw_error_retained": False, "raw_reasoning_retained": False},
            "stopping_policy": {"stop_on_first_operational_or_policy_failure": True, "fill_skips": False,
                                "narrative_retries": 0, "fallback": False},
            "implementation": [{"file": file, "sha256": shared._sha256(PROJECT_ROOT / file)} for file in files]}}
    prepared = PreparedExperiment(candidate, target, case, prompt, metadata)
    first = _make_request(prepared, 0, PREFLIGHT_BATCH)
    metadata["inputs"]["first_request"] = {"body_sha256": _canonical_sha(_fixed_payload(first)),
        "user_packet_sha256": _sha(first.messages[1].content),
        "user_estimated_tokens": (len(first.messages[1].content) + 3) // 4}
    return prepared


def _check_prepared(prepared: PreparedExperiment) -> None:
    if type(prepared) is not PreparedExperiment or type(prepared.candidate) is not shared.Candidate:
        raise ValueError("source_probe_prepared_type_invalid")
    current = prepare_experiment(prepared.case["case_id"])
    if (current.target != prepared.target or current.prompt != prepared.prompt
            or _canonical(asdict(current.candidate)) != _canonical(asdict(prepared.candidate))
            or _canonical(current.case) != _canonical(prepared.case)
            or _canonical(current.metadata) != _canonical(prepared.metadata)):
        raise ValueError("source_probe_prepared_drift")


def _request_record(request: StructuredGenerationRequest) -> dict:
    user = request.messages[1].content
    return {"operation": request.operation, "invocation_id": request.invocation_id,
            "user_packet": user, "user_packet_sha256": _sha(user),
            "body_sha256": _canonical_sha(_fixed_payload(request)),
            "user_estimated_tokens": (len(user) + 3) // 4}


def _project(prepared: PreparedExperiment, index: int, batch_id: str,
             proposal: profile.NarrativeSourceProposal) -> SourceProjection:
    invocation = _invocation_id(batch_id, index)
    return profile.create_source_projection(
        proposal, source_id=f"source-{invocation}", session_id=batch_id,
        turn_id=TURN_IDS[index], invocation_id=invocation,
        current_scene=_scene(prepared), facts=(), player_input=prepared.case["turns"][index]["player_input"])


def _skip_remaining(prepared: PreparedExperiment, records: list[dict], reason: str,
                    on_record: Callable[[dict], None] | None = None) -> None:
    seen = {row["turn_id"] for row in records}
    for turn_id in TURN_IDS:
        if turn_id not in seen:
            _emit(records, {"kind": "narrative_source_skip", "case_id": prepared.case["case_id"], "turn_id": turn_id,
                            "call_made": False, "skipped_reason": reason}, on_record)


async def evaluate_probe(prepared: PreparedExperiment, *, api_key: SecretStr, batch_id: str,
                         records: list[dict] | None = None,
                         on_record: Callable[[dict], None] | None = None) -> list[dict]:
    _check_prepared(prepared)
    _batch_id(batch_id)
    if not api_key.get_secret_value().strip():
        raise ValueError("source_probe_blank_credential")
    records = records if records is not None else []
    if records:
        raise ValueError("source_probe_records_must_be_empty")
    sources: tuple[SourceProjection, ...] = ()
    pacer = shared._CallPacer(60.0)
    pacer._last_call_started_at = pacer._clock()
    for index, turn_id in enumerate(TURN_IDS):
        _check_prepared(prepared)
        await pacer.before_call(f"narrative source {turn_id}")
        _check_prepared(prepared)
        request = _make_request(prepared, index, batch_id, sources)
        request_record = _request_record(request)
        gateway = NarrativeSourceObservationAdapter(
            turn_id=turn_id, approved_body_sha256=request_record["body_sha256"], base_url=GROQ_OFFICIAL_BASE_URL,
            capability_set=shared._capabilities(prepared.candidate, prepared.target), api_key=api_key, reasoning_effort="none")
        row = {"kind": "narrative_source_call", "case_id": prepared.case["case_id"], "turn_id": turn_id, "call_made": True,
               "request": request_record, "schema_valid": False, "policy_valid": False,
               "projection_valid": False, "route_status": "unavailable"}
        started = time.perf_counter()
        stage = "transport"
        try:
            pacer._last_call_started_at = pacer._clock()
            result = await gateway.generate_structured(request)
            row["evidence"] = shared._evidence_payload(result.evidence)
            row["route_status"] = _route_status(row["evidence"], prepared.target, request.invocation_id)
            if row["route_status"] != "verified":
                row["route_error"] = "effective_route_not_verified"
            else:
                stage = "schema"
                try:
                    if type(result.value) is not profile.NarrativeSourceProposal:
                        raise ValueError("source_probe_unexpected_model")
                    proposal = profile.NarrativeSourceProposal.model_validate(result.value)
                except (ValueError, TypeError):
                    row["schema_error"] = {"code": "source_probe_schema_invalid"}
                else:
                    row["response_structure"] = proposal.model_dump(mode="json", by_alias=True)
                    row["schema_valid"] = True
                    try:
                        stage = "policy"
                        profile.validate_source_proposal(proposal, current_scene=_scene(prepared), facts=(),
                            player_input=prepared.case["turns"][index]["player_input"])
                        row["policy_valid"] = True
                        stage = "projection"
                        projection = _project(prepared, index, batch_id, proposal)
                    except (SceneProposalError, profile.SourceProfileError, NarrativeGroundingError) as exc:
                        row["policy_error"] = {"code": exc.code}
                    else:
                        row["source_projection"] = projection.model_dump(mode="json")
                        row["projection_valid"] = True
                        sources = (*sources, projection)
        except LLMInvocationError as exc:
            row["llm_error"] = shared._normalized_error_payload(exc.error)
            row["evidence"] = shared._evidence_payload(exc.error.evidence)
            row["route_status"] = _route_status(row["evidence"], prepared.target, request.invocation_id)
        except (asyncio.CancelledError, KeyboardInterrupt):
            row["cancelled"] = True
            row["cancelled_stage"] = stage
            raise
        except Exception:
            row["local_error"] = {"code": "local_narrative_source_failure", "stage": stage}
            raise
        finally:
            row["provider_observation"] = copy.deepcopy(gateway.observation)
            row["latency_seconds"] = round(time.perf_counter() - started, 6)
            _emit(records, row, on_record)
        if not _call_succeeded(row):
            _skip_remaining(prepared, records, "previous_operational_failure", on_record)
            break
    return records


def _call_succeeded(row: dict) -> bool:
    return (all(row.get(key) is True for key in ("schema_valid", "policy_valid", "projection_valid"))
            and row.get("route_status") == "verified"
            and not any(row.get(key) for key in ("llm_error", "schema_error", "route_error", "policy_error", "local_error", "cancelled")))


def summarize(records: list[dict], *, status: str = "completed", case_id: str = CASE_ID) -> dict:
    if case_id not in CASE_CHOICES:
        raise ValueError("source_probe_case_selection_invalid")
    if status not in {"completed", "cancelled", "local_error"}:
        raise ValueError("source_probe_status_invalid")
    if (tuple(row.get("turn_id") for row in records) != TURN_IDS
            or any(row.get("case_id") != case_id or type(row.get("call_made")) is not bool
                   or row.get("kind") != ("narrative_source_call" if row["call_made"] else "narrative_source_skip") for row in records)):
        raise ValueError("source_probe_record_order_invalid")
    calls = [row for row in records if row["call_made"]]
    if any(row["call_made"] for row in records[len(calls):]) or (len(calls) == 2 and not _call_succeeded(calls[0])):
        raise ValueError("source_probe_stop_rule_invalid")
    skips = records[len(calls):]
    if status == "completed":
        if not calls or (skips and _call_succeeded(calls[-1])):
            raise ValueError("source_probe_completed_chain_incomplete")
        if any(row.get("skipped_reason") != "previous_operational_failure" for row in skips):
            raise ValueError("source_probe_completed_skip_reason_invalid")
        if any(not _call_succeeded(row) and not any(row.get(key) for key in
                ("llm_error", "schema_error", "route_error", "policy_error")) for row in calls):
            raise ValueError("source_probe_failed_call_without_failure")
    elif any(row.get("skipped_reason") != status for row in skips):
        raise ValueError("source_probe_interrupted_skip_reason_invalid")
    for row in calls:
        if any(type(row.get(key)) is not bool for key in ("schema_valid", "policy_valid", "projection_valid")):
            raise ValueError("source_probe_gate_types_invalid")
        if row["projection_valid"] > row["policy_valid"] or row["policy_valid"] > row["schema_valid"]:
            raise ValueError("source_probe_gate_order_invalid")
    if status == "completed" and any(row.get("local_error") or row.get("cancelled") for row in calls):
        raise ValueError("source_probe_status_contradiction")
    verified = sum(row.get("route_status") == "verified" for row in calls)
    mismatch = sum(row.get("route_status") == "mismatch" for row in calls)
    passed = status == "completed" and len(calls) == 2 and all(_call_succeeded(row) for row in calls)
    unavailable = any(row.get("llm_error", {}).get("category") in AVAILABILITY_CATEGORIES for row in calls)
    exit_code = 130 if status == "cancelled" else 3 if status == "local_error" else 0 if passed else 2 if unavailable else 1
    usage_rows = [{**row, "kind": "narrative_turn"} for row in calls]
    return {**_scope(), "evaluation_stage": PROBE_KIND, "calls_made": len(calls), "turns_skipped": 2-len(calls),
        **{key: sum(row[key] for row in calls) for key in ("schema_valid", "policy_valid", "projection_valid")},
        "operational_probe_passed": passed, "availability_failure": unavailable,
        "provider_observation": copy.deepcopy(calls[0].get("provider_observation")) if len(calls) == 1 else None,
        "provider_observations": [{"turn_id": row["turn_id"], "observation": copy.deepcopy(row.get("provider_observation"))} for row in calls],
        "route_verification": {"status": "mismatch" if mismatch else "verified" if calls and verified == len(calls) else "partial" if verified else "unavailable",
            "calls_made": len(calls), "verified_calls": verified, "mismatched_calls": mismatch,
            "unavailable_calls": len(calls)-verified-mismatch,
            "identity_consistent": False if mismatch else True if calls and verified == len(calls) else None},
        "usage_aggregate": shared._aggregate_usage(usage_rows, expected_calls=MAX_CALLS),
        "cost_aggregate": shared._aggregate_cost(usage_rows, expected_calls=MAX_CALLS),
        "semantic_fidelity_review": {"status": "not_performed", "approval": None}, "process_exit_code": exit_code}


def _read_json(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("source_probe_artifact_size_or_path_invalid")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_observation_snapshot(row: dict) -> None:
    """Check the bounded observer's wire shape, without inventing absent evidence."""
    observation = row.get("provider_observation")
    shapes = {
        "usage": {"input_tokens", "output_tokens", "total_tokens", "reasoning_tokens"},
        "error_body": {"status", "complete", "bytes", "json_valid"},
        "failed_generation": {"status", "present", "characters", "json_valid", "error_position"},
    }
    if (type(observation) is not dict or set(observation) != {
            "schema", "http_status", "request_id", "provider_code", "model", "finish_reason", *shapes}
            or observation["schema"] != "storyteller.eval.record-budget-observation.v1"
            or any(type(observation[key]) is not dict or set(observation[key]) != keys
                   for key, keys in shapes.items())):
        raise ValueError("source_probe_observation_shape_invalid")
    if (observation["model"] not in (None, GROQ_QWEN_MODEL_ID)
            or observation["provider_code"] not in (None, "json_validate_failed", "rate_limit_exceeded")
            or observation["finish_reason"] not in
                (None, "stop", "length", "content_filter", "tool_calls", "function_call", "unknown")
            or (observation["request_id"] is not None and
                (type(observation["request_id"]) is not str or
                 re.fullmatch(r"req_[a-z0-9]{26}", observation["request_id"]) is None))):
        raise ValueError("source_probe_observation_identity_invalid")
    body, failed = observation["error_body"], observation["failed_generation"]
    if (body["status"] not in ("unavailable", "reading", "complete", "parser_limit", "limit_exceeded",
                              "invalid_content_length", "read_error", "interrupted")
            or failed["status"] not in ("unavailable", "absent", "non_string", "observed", "parser_limit")
            or any(value is not None and type(value) is not bool for value in
                   (body["complete"], body["json_valid"], failed["present"], failed["json_valid"]))):
        raise ValueError("source_probe_observation_state_invalid")
    counts = (*observation["usage"].values(), body["bytes"], failed["characters"], failed["error_position"])
    if (any(value is not None and (type(value) is not int or value < 0) for value in counts)
            or (body["bytes"] is not None and body["bytes"] > 65536)
            or (observation["http_status"] is not None and
                (type(observation["http_status"]) is not int or not 100 <= observation["http_status"] <= 599))):
        raise ValueError("source_probe_observation_count_invalid")
    evidence, error = row.get("evidence") or {}, row.get("llm_error") or {}
    pairs = ((observation["model"], evidence.get("effective_model", {}).get("value")),
             (observation["http_status"], error.get("status_code")),
             (observation["request_id"], error.get("external_id")))
    if any(left is not None and right is not None and left != right for left, right in pairs):
        raise ValueError("source_probe_observation_evidence_mismatch")


def verify_artifacts(summary_path: Path, expected_preflight: Path, batch_id: str,
                     *, case_id: str = CASE_ID) -> dict:
    """Reconstruct local consistency, not authenticate a provider transcript."""
    _batch_id(batch_id)
    prepared = prepare_experiment(case_id)
    expected = _read_json(expected_preflight)
    if _canonical(expected) != _canonical(prepared.metadata):
        raise ValueError("source_probe_expected_preflight_changed")
    summary_path = summary_path.resolve()
    summary_path.relative_to(OUTPUT_ROOT.resolve())
    if summary_path.name != "summary.json":
        raise ValueError("source_probe_summary_path_invalid")
    document = _read_json(summary_path)
    for key, value in expected.items():
        if _canonical(document.get(key)) != _canonical(value):
            raise ValueError("source_probe_metadata_mismatch")
    if document.get("batch_id") != batch_id:
        raise ValueError("source_probe_batch_mismatch")
    evaluation_id = _batch_id(document["evaluation_invocation_id"])
    started = datetime.fromisoformat(document["started_at"])
    finished = datetime.fromisoformat(document["finished_at"])
    if started.tzinfo is None or finished.tzinfo is None or finished < started:
        raise ValueError("source_probe_artifact_times_invalid")
    if summary_path.parent.name != f"{started.strftime('%Y%m%dT%H%M%SZ')}-{evaluation_id}":
        raise ValueError("source_probe_run_identity_invalid")
    jsonl = summary_path.with_name(f"{CANDIDATE_ID}.jsonl")
    if not jsonl.is_file() or jsonl.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("source_probe_jsonl_invalid")
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    if len(rows) != MAX_CALLS:
        raise ValueError("source_probe_row_count_invalid")
    sources: tuple[SourceProjection, ...] = ()
    for index, row in enumerate(rows):
        for key in (*expected, "batch_id", "evaluation_invocation_id", "started_at"):
            if _canonical(row.get(key)) != _canonical(document[key]):
                raise ValueError("source_probe_row_metadata_mismatch")
        if row.get("call_made") is False:
            if row.get("skipped_reason") not in {"previous_operational_failure", "cancelled", "local_error"}:
                raise ValueError("source_probe_skip_reason_invalid")
            if any(key in row for key in ("response_structure", "source_projection", "evidence", "request")):
                raise ValueError("source_probe_skip_has_call_payload")
            continue
        if row.get("call_made") is not True:
            raise ValueError("source_probe_call_flag_invalid")
        request = _make_request(prepared, index, batch_id, sources)
        if _canonical(row.get("request")) != _canonical(_request_record(request)):
            raise ValueError("source_probe_request_chain_mismatch")
        _validate_observation_snapshot(row)
        route = _route_status(row.get("evidence"), prepared.target, request.invocation_id)
        if row.get("route_status") != route:
            raise ValueError("source_probe_saved_route_mismatch")
        interrupted_stage = None
        if row.get("local_error"):
            error = row["local_error"]
            if (document["evaluation_status"] != "local_error" or type(error) is not dict
                    or set(error) != {"code", "stage"}
                    or error["code"] != "local_narrative_source_failure"
                    or error["stage"] not in ("transport", "schema", "policy", "projection")):
                raise ValueError("source_probe_local_error_invalid")
            interrupted_stage = error["stage"]
        if row.get("cancelled"):
            if (document["evaluation_status"] != "cancelled" or row["cancelled"] is not True or interrupted_stage
                    or row.get("cancelled_stage") not in ("transport", "schema", "policy", "projection")):
                raise ValueError("source_probe_cancelled_state_invalid")
            interrupted_stage = row.get("cancelled_stage")
        if interrupted_stage is not None and interrupted_stage not in {"transport", "schema", "policy", "projection"}:
            raise ValueError("source_probe_interrupted_stage_invalid")
        structure = row.get("response_structure")
        has_structure = structure is not None
        if row.get("schema_valid") is not has_structure:
            raise ValueError("source_probe_saved_schema_mismatch")
        expected_policy = expected_projection = False
        if ((has_structure and interrupted_stage in {"transport", "schema"})
                or (not has_structure and interrupted_stage in {"policy", "projection"})):
            raise ValueError("source_probe_stage_payload_mismatch")
        if has_structure:
            if route != "verified" or row.get("llm_error") or row.get("schema_error"):
                raise ValueError("source_probe_structure_without_valid_route")
            proposal = profile.NarrativeSourceProposal.model_validate(structure)
            if _canonical(structure) != _canonical(proposal.model_dump(mode="json", by_alias=True)):
                raise ValueError("source_probe_structure_changed_by_validation")
            try:
                if interrupted_stage == "policy":
                    if row.get("policy_error") or "source_projection" in row:
                        raise ValueError("source_probe_interrupted_policy_has_result")
                else:
                    profile.validate_source_proposal(proposal, current_scene=_scene(prepared), facts=(),
                        player_input=prepared.case["turns"][index]["player_input"])
                    expected_policy = True
                    if interrupted_stage != "projection":
                        projection = _project(prepared, index, batch_id, proposal)
                        expected_projection = True
            except (SceneProposalError, profile.SourceProfileError, NarrativeGroundingError) as exc:
                if row.get("policy_error") != {"code": exc.code}:
                    raise ValueError("source_probe_policy_error_mismatch") from None
            else:
                if expected_projection:
                    if row.get("policy_error") or _canonical(row.get("source_projection")) != _canonical(projection.model_dump(mode="json")):
                        raise ValueError("source_probe_projection_mismatch")
                    sources = (*sources, projection)
                elif row.get("policy_error"):
                    raise ValueError("source_probe_interrupted_has_policy_result")
        if row.get("policy_valid") is not expected_policy or row.get("projection_valid") is not expected_projection:
            raise ValueError("source_probe_saved_policy_or_projection_mismatch")
        if not expected_projection and "source_projection" in row:
            raise ValueError("source_probe_unadmitted_projection")
    reconstructed = summarize(rows, status=document["evaluation_status"], case_id=prepared.case["case_id"])
    if (_canonical(document["summary"]) != _canonical(reconstructed)
            or type(document.get("process_exit_code")) is not int
            or document["process_exit_code"] != reconstructed["process_exit_code"]):
        raise ValueError("source_probe_summary_mismatch")
    return {"verified": True, "batch_id": batch_id, "summary_path": str(summary_path),
            "evaluation_status": document["evaluation_status"], "process_exit_code": reconstructed["process_exit_code"],
            "summary": reconstructed, "artifact_hashes": {"summary": shared._sha256(summary_path), "jsonl": shared._sha256(jsonl)},
            "verification_scope": "local_artifact_consistency_not_provider_authentication"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two dependent synthetic sources, without canonical promotion.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--verify-artifacts", type=Path)
    parser.add_argument("--case-id", choices=CASE_CHOICES, default=CASE_ID)
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--allow-synthetic-only", action="store_true")
    parser.add_argument("--batch-id", type=_batch_id)
    parser.add_argument("--api-key-env", choices=("GROQ_API_KEY",), default="GROQ_API_KEY")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.verify_artifacts is not None:
        if args.expected_preflight is None or args.batch_id is None or args.allow_synthetic_only:
            raise SystemExit("Artifact verification requires expected preflight and batch UUID only")
        try:
            result = verify_artifacts(args.verify_artifacts, args.expected_preflight, args.batch_id, case_id=args.case_id)
        except Exception:
            print("Narrative source artifact verification failed.", file=sys.stderr)
            return 3
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.preflight and (args.expected_preflight is not None or args.allow_synthetic_only or args.batch_id is not None):
        raise SystemExit("Preflight does not accept execution or verification options")
    if args.live and (not args.allow_synthetic_only or args.batch_id is None or args.expected_preflight is None):
        raise SystemExit("Live source probe requires synthetic-only acknowledgement, batch UUID and frozen preflight")
    if args.live and args.case_id != COURTYARD_CASE_ID:
        print("Closed greenhouse case is available for offline inspection only; no credential was inspected.", file=sys.stderr)
        return 3
    try:
        prepared = prepare_experiment(args.case_id)
        if args.live and _canonical(_read_json(args.expected_preflight)) != _canonical(prepared.metadata):
            raise ValueError("source_probe_expected_preflight_changed")
    except Exception:
        print("Narrative source preflight failed; no credential was inspected and no call was made.", file=sys.stderr)
        return 3
    if args.preflight:
        print(json.dumps(prepared.metadata, ensure_ascii=False, sort_keys=True))
        return 0
    raw_key = os.environ.get(args.api_key_env, "").strip()
    if not raw_key:
        print("Narrative source credential is missing; no call was made.", file=sys.stderr)
        return 3
    api_key = SecretStr(raw_key)
    raw_key = ""
    started = datetime.now(timezone.utc)
    evaluation_id = str(uuid4())
    records: list[dict] = []
    status = "completed"
    context = {**copy.deepcopy(prepared.metadata), "evaluation_invocation_id": evaluation_id,
               "batch_id": args.batch_id, "started_at": started.isoformat()}
    try:
        directory = _new_run_directory(evaluation_id, started)
        output = directory / f"{CANDIDATE_ID}.jsonl"
        with output.open("x", encoding="utf-8", newline="\n") as destination:
            def persist(row: dict) -> None:
                destination.write(json.dumps({**context, **row}, ensure_ascii=False) + "\n")
                destination.flush()
            try:
                asyncio.run(evaluate_probe(prepared, api_key=api_key, batch_id=args.batch_id, records=records, on_record=persist))
            except (KeyboardInterrupt, asyncio.CancelledError):
                status = "cancelled"
                _skip_remaining(prepared, records, "cancelled", persist)
            except Exception:
                status = "local_error"
                _skip_remaining(prepared, records, "local_error", persist)
        summary = summarize(records, status=status, case_id=prepared.case["case_id"])
        document = {**context, "finished_at": datetime.now(timezone.utc).isoformat(),
                    "evaluation_status": status, "process_exit_code": summary["process_exit_code"], "summary": summary}
        summary_path = directory / "summary.json"
        with summary_path.open("x", encoding="utf-8", newline="\n") as destination:
            destination.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:
        print("Narrative source artifact persistence failed; inspect local evidence.", file=sys.stderr)
        return 3
    finally:
        api_key = SecretStr("")
    print(f"Narrative source finished (exit code {summary['process_exit_code']}): {summary_path}")
    print("Attributed source preservation does not approve semantic truth, runtime or CAP-001.")
    return summary["process_exit_code"]


def _route_status(evidence: dict[str, Any] | None, target: LLMTarget, invocation_id: str) -> str:
    if not evidence:
        return "unavailable"
    model, provider = evidence.get("effective_model", {}), evidence.get("effective_provider", {})
    if not model.get("value") or not provider.get("value"):
        return "unavailable"
    if (model != {"value": target.model, "source": "reported"}
            or provider != {"value": target.provider, "source": "observed"}
            or evidence.get("requested_target") != target.model_dump(mode="json")
            or evidence.get("invocation_id") != invocation_id
            or evidence.get("adapter", {}).get("name") != "groq-chat-completions"):
        return "mismatch"
    return "verified"


def _emit(records: list[dict], row: dict, on_record: Callable[[dict], None] | None) -> None:
    records.append(row)
    if on_record is not None:
        on_record(row)


def _batch_id(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("batch id must be a canonical UUID") from None
    if str(parsed) != value:
        raise argparse.ArgumentTypeError("batch id must be a canonical UUID")
    return value


def _new_run_directory(invocation_id: str, started: datetime) -> Path:
    if OUTPUT_ROOT.resolve() != (PROJECT_ROOT / "eval-results").resolve():
        raise ValueError("Fixed output root differs")
    run_dir = OUTPUT_ROOT / f"{started.strftime('%Y%m%dT%H%M%SZ')}-{invocation_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


if __name__ == "__main__":
    raise SystemExit(main())
