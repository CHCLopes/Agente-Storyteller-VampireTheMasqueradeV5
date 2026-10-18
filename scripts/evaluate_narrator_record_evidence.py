"""Bounded synthetic evidence-bearing derivation; structural checks never approve semantics."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import BaseModel, SecretStr, ValidationError
from scripts import evaluate_narrator_models as shared
from scripts import narrator_record_evidence as contract
from scripts import narrator_record_derivation as record_contract
from scripts.narrator_actor_contract import (
    FocusedSceneContinuationProposal, actor_identity_key, validate_actor_coherence,
)
from api.scene_director_service import SceneProposalError, validate_scene_continuation
from api.llm.adapters.groq import GroqAdapter, GROQ_OFFICIAL_BASE_URL, _normalize_groq_strict_schema
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement, CancellationToken, GenerationParameters,
    LLMInvocationError, LLMMessage, LLMTarget, MessageRole,
    StructuredGenerationRequest, utc_now,
)

CANDIDATE_ID = "gpt-oss-120b-groq-free-synthetic-low"
MANIFEST_PATH = PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
MANIFEST_SHA256 = "de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6"
FINAL_SCHEMA_SHA256 = "bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2"
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
PROBE_KIND = "record_evidence_probe"
MAX_CALLS = 2
AVAILABILITY_CATEGORIES = frozenset({"timeout", "rate_limited", "quota_exceeded", "provider_unavailable"})


def _scope() -> dict[str, Any]:
    return {
        "purpose": PROBE_KIND, "probe_kind": PROBE_KIND,
        "full_evaluation": False, "synthetic_only": True,
        "runtime_promoted": False, "cap_001_status": "not_evaluated",
        "automated_gates_passed": False, "human_review_required": True,
        "diagnostics_executed": False, "automatic_retries": 0,
        "max_calls": MAX_CALLS, "repetitions": 1, "causal_comparison": False,
        "narrative_generation_calls": 0, "support_validation_scope": "structural_only",
    }


def _parameters() -> dict[str, Any]:
    return {
        "deadline_seconds": 60, "minimum_inter_call_delay_seconds": 60,
        "requested": {"temperature": 0.65, "max_output_tokens": 768},
        "transmitted": {"temperature": 0.65, "max_output_tokens": 768, "reasoning_effort": "low"},
        "max_total_output_tokens": 1536,
        "user_packet_budget": {"estimated_tokens": 2000, "method": "characters_divided_by_4"},
    }


def _json_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    cases: tuple
    packets: tuple[str, ...]
    prompt: str
    metadata: dict[str, Any]


def prepare_experiment() -> PreparedExperiment:
    """Read only the frozen synthetic sources; never inspect a credential."""
    if shared._sha256(MANIFEST_PATH) != MANIFEST_SHA256:
        raise ValueError("Fixed manifest fingerprint differs")
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    if (
        candidate.adapter_kind != "groq" or candidate.model != "openai/gpt-oss-120b"
        or candidate.provider_label != "Groq" or candidate.effective_provider != "Groq"
        or candidate.upstream_provider is not None or candidate.structured_mode != "native"
        or candidate.reasoning_effort != "low" or candidate.campaign_data_eligible
    ):
        raise ValueError("Fixed synthetic candidate differs")
    cases = record_contract.load_fixed_cases()
    if len(cases) != MAX_CALLS or tuple(c.episode_id for c in cases) != ("opening", "player-agency"):
        raise ValueError("Fixed case sequence differs")
    prompt_path, prompt = contract.load_evidence_prompt()
    response_schema = contract.RecordEvidenceProposal.model_json_schema(by_alias=True)
    final_schema = FocusedSceneContinuationProposal.model_json_schema(by_alias=True)
    if _json_sha(final_schema) != FINAL_SCHEMA_SHA256:
        raise ValueError("Final actor schema differs")
    # Exercise the existing strict provider normalizer before credential access.
    provider_schema = _normalize_groq_strict_schema(response_schema)
    prepared_packets = tuple(contract.build_evidence_packet(case) for case in cases)
    target = LLMTarget(profile=f"record-evidence-{CANDIDATE_ID}", provider="Groq", model=candidate.model)
    provenance = shared._evaluator_provenance()
    provenance.update(file="scripts/evaluate_narrator_record_evidence.py",
                      sha256=shared._sha256(Path(__file__).resolve()))
    implementation_files = (
        "scripts/narrator_record_evidence.py", "scripts/narrator_record_derivation.py",
        "scripts/evaluate_narrator_models.py",
        "scripts/narrator_actor_contract.py", "api/scene_director_service.py", "api/scene_service.py",
        "api/llm/adapters/groq.py", "api/llm/adapters/openai_compatible.py", "api/llm/contract.py",
    )
    metadata = {
        **_scope(), "selected_candidate_id": CANDIDATE_ID,
        "evaluator": provenance, "candidate_policy": shared._candidate_policy_payload(candidate),
        "evidence_generation_parameters": _parameters(),
        "inputs": {
            "manifest": {"file": MANIFEST_PATH.name, "sha256": MANIFEST_SHA256},
            "corpus": {"file": record_contract.SOURCE_CORPUS_PATH.name, "sha256": record_contract.SOURCE_CORPUS_SHA256},
            "prompt": {"variant": contract.VERSION,
                       "file": prompt_path.relative_to(PROJECT_ROOT).as_posix(),
                       "sha256": hashlib.sha256(prompt.encode()).hexdigest()},
            "response_schema_sha256": _json_sha(response_schema),
            "provider_schema_sha256": _json_sha(provider_schema),
            "final_schema_sha256": _json_sha(final_schema),
            "implementation": [{"file": file, "sha256": shared._sha256(PROJECT_ROOT / file)}
                               for file in implementation_files],
            "cases": [
                {"case_id": case.case_id, "episode_id": case.episode_id, "turn_id": case.turn_id,
                 "source": copy.deepcopy(case.source), "generation_context": audit}
                for case, (_, audit) in zip(cases, prepared_packets)
            ],
        },
    }
    return PreparedExperiment(candidate, target, cases, tuple(p for p, _ in prepared_packets), prompt, metadata)


def _check_prepared(prepared: PreparedExperiment) -> None:
    current = prepare_experiment()
    if (
        current.metadata != prepared.metadata or current.packets != prepared.packets
        or current.prompt != prepared.prompt or current.cases != prepared.cases
        or current.target != prepared.target or current.candidate != prepared.candidate
    ):
        raise ValueError("Prepared experiment changed before dispatch")


def _route_status(evidence: dict[str, Any] | None, target: LLMTarget, invocation_id: str) -> str:
    if not evidence:
        return "unavailable"
    model, provider = evidence.get("effective_model", {}), evidence.get("effective_provider", {})
    if not model.get("value") or not provider.get("value"):
        return "unavailable"
    if (
        model != {"value": target.model, "source": "reported"}
        or provider != {"value": target.provider, "source": "observed"}
        or evidence.get("requested_target") != target.model_dump(mode="json")
        or evidence.get("invocation_id") != invocation_id
        or evidence.get("adapter", {}).get("name") != "groq-chat-completions"
    ):
        return "mismatch"
    return "verified"


def _emit(records: list[dict], row: dict, on_record: Callable[[dict], None] | None) -> None:
    records.append(row)
    if on_record is not None:
        on_record(row)


def _skip_remaining(prepared: PreparedExperiment, records: list[dict], reason: str,
                    on_record: Callable[[dict], None] | None = None) -> None:
    seen = {row["case_id"] for row in records}
    for case in prepared.cases:
        if case.case_id not in seen:
            _emit(records, {
                "kind": "record_evidence_skip", "case_id": case.case_id,
                "episode_id": case.episode_id, "turn_id": case.turn_id,
                "call_made": False, "skipped_reason": reason,
            }, on_record)


async def evaluate_probe(prepared: PreparedExperiment, *, api_key: SecretStr,
                         records: list[dict] | None = None,
                         on_record: Callable[[dict], None] | None = None) -> list[dict]:
    """Two independent calls at most. Failures are observations, never retries."""
    _check_prepared(prepared)
    if not api_key.get_secret_value().strip():
        raise ValueError("Blank credential")
    records = records if records is not None else []
    if records:
        raise ValueError("This probe starts with no records")
    gateway = GroqAdapter(
        base_url=GROQ_OFFICIAL_BASE_URL,
        capability_set=shared._capabilities(prepared.candidate, prepared.target),
        api_key=api_key, reasoning_effort="low",
    )
    pacer = shared._CallPacer(60.0)
    for index, case in enumerate(prepared.cases):
        _check_prepared(prepared)
        await pacer.before_call(f"record evidence {case.case_id}")
        _check_prepared(prepared)
        request = StructuredGenerationRequest(
            operation=f"record-evidence.{case.case_id}",
            target=prepared.target,
            messages=(LLMMessage(role=MessageRole.SYSTEM, content=prepared.prompt),
                      LLMMessage(role=MessageRole.USER, content=prepared.packets[index])),
            deadline=utc_now() + shared._seconds(60),
            cancellation=CancellationToken(),
            parameters=GenerationParameters(temperature=0.65, max_output_tokens=768),
            response_model=contract.RecordEvidenceProposal,
            required_capabilities=(
                CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
                CapabilityRequirement(name=CAPABILITY_STRUCTURED_GENERATION, allow_emulated=False),
            ),
        )
        row = {
            "kind": "record_evidence_call", "call_made": True,
            "case_id": case.case_id, "episode_id": case.episode_id, "turn_id": case.turn_id,
            "source": copy.deepcopy(case.source),
            "generation_context": copy.deepcopy(prepared.metadata["inputs"]["cases"][index]["generation_context"]),
            "fixed_narrative": case.narrative, "schema_valid": False, "envelope_valid": False,
            "final_schema_valid": False, "admitted": False, "route_status": "unavailable",
        }
        started = time.perf_counter()
        abort = False
        try:
            # Anchor spacing after integrity checks, at the actual dispatch boundary.
            pacer._last_call_started_at = pacer._clock()
            result = await gateway.generate_structured(request)
            row["evidence"] = shared._evidence_payload(result.evidence)
            row["route_status"] = _route_status(row["evidence"], prepared.target, request.invocation_id)
            raw = result.value
            if isinstance(raw, BaseModel) and not isinstance(raw, contract.RecordEvidenceProposal):
                raw = raw.model_dump(mode="json")
            try:
                envelope = contract.RecordEvidenceProposal.model_validate(raw)
            except ValidationError as exc:
                row["schema_errors"] = shared._schema_error_payload(exc)
                abort = True
            else:
                row["schema_valid"] = True
                row["response_envelope"] = envelope.model_dump(mode="json", by_alias=True)
                row["derived_records"] = envelope.records.model_dump(mode="json", by_alias=True)
                if row["route_status"] == "verified":
                    try:
                        support_audit = contract.validate_supports(case, envelope)
                    except contract.EvidenceEnvelopeError as exc:
                        row["envelope_error"] = {"code": exc.code}
                        abort = True
                    else:
                        row["envelope_valid"] = True
                        row["support_validation"] = support_audit
                        try:
                            proposal = record_contract.compose_derivation(case, envelope.records)
                        except ValidationError as exc:
                            row["final_schema_errors"] = shared._schema_error_payload(exc)
                        else:
                            row["final_schema_valid"] = True
                            row["composed_proposal"] = proposal.model_dump(mode="json")
                            if proposal.narrative != case.narrative:
                                raise ValueError("Fixed narrative changed")
                            try:
                                validate_actor_coherence(proposal, case.scene, player_aliases=("Neófito",))
                                admission_scene = case.scene
                                if case.scene is not None and {
                                    actor_identity_key(n) for n in case.scene.npcs_present
                                } == {actor_identity_key(n) for n in proposal.npcs_present}:
                                    admission_scene = case.scene.model_copy(update={"npcs_present": proposal.npcs_present})
                                validate_scene_continuation(
                                    proposal, facts=shared._mechanical_facts(case.outcome, case.turn_id),
                                    current_scene=admission_scene, player_input=case.player_input,
                                    protected_secrets=(), player_aliases=("Neófito",),
                                    npc_aliases=case.scene.npcs_present if case.scene is not None else (),
                                )
                                row["admitted"] = True
                            except SceneProposalError as exc:
                                shared._record_admission_failure(row, exc)
            if row["route_status"] != "verified":
                row["route_error"] = "effective_route_not_verified"
                abort = True
        except LLMInvocationError as exc:
            row["llm_error"] = shared._normalized_error_payload(exc.error)
            row["evidence"] = shared._evidence_payload(exc.error.evidence)
            row["route_status"] = _route_status(row["evidence"], prepared.target, request.invocation_id)
            abort = True
        except (asyncio.CancelledError, KeyboardInterrupt):
            row["cancelled"] = True
            raise
        except Exception:
            row["local_error"] = {"code": "local_evidence_failure"}
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - started, 6)
            _emit(records, row, on_record)
        if abort:
            _skip_remaining(prepared, records, "previous_operational_failure", on_record)
            break
    return records


def summarize(records: list[dict], *, status: str = "completed") -> dict[str, Any]:
    calls = [row for row in records if row.get("call_made") is True]
    verified = sum(row.get("route_status") == "verified" for row in calls)
    mismatched = sum(row.get("route_status") == "mismatch" for row in calls)
    unavailable = len(calls) - verified - mismatched
    schema_valid = sum(row.get("schema_valid") is True for row in calls)
    envelope_valid = sum(row.get("envelope_valid") is True for row in calls)
    final_schema_valid = sum(row.get("final_schema_valid") is True for row in calls)
    admitted = sum(row.get("admitted") is True for row in calls)
    transport_passed = (
        status == "completed" and len(calls) == MAX_CALLS and schema_valid == MAX_CALLS
        and verified == MAX_CALLS and not any(row.get("llm_error") for row in calls)
    )
    passed = (transport_passed and envelope_valid == MAX_CALLS
              and final_schema_valid == MAX_CALLS and admitted == MAX_CALLS)
    # Only a transient measurement view uses the legacy helper's recognized kind.
    # Persisted records retain their evidence kind and cannot become CAP data.
    measurement_view = [{**row, "kind": "narrative_turn"} for row in calls]
    availability_failure = any(
        row.get("llm_error", {}).get("category") in AVAILABILITY_CATEGORIES for row in calls
    )
    exit_code = (130 if status == "cancelled" else 3 if status == "local_error"
                 else 0 if passed else 2 if availability_failure else 1)
    return {
        **_scope(), "evaluation_stage": PROBE_KIND, "calls_made": len(calls),
        "schema_valid": schema_valid, "envelope_valid": envelope_valid,
        "final_schema_valid": final_schema_valid, "admitted": admitted,
        "cases_skipped": sum(row.get("call_made") is False for row in records),
        "transport_and_schema_passed": transport_passed, "operational_probe_passed": passed,
        "availability_failure": availability_failure,
        "semantic_fidelity_review": {"status": "not_performed", "approval": None},
        "support_coverage_review": {"status": "not_performed", "approval": None},
        "route_verification": {
            "status": "mismatch" if mismatched else "verified" if calls and verified == len(calls)
                      else "partial" if verified else "unavailable",
            "calls_made": len(calls), "verified_calls": verified,
            "unavailable_calls": unavailable, "mismatched_calls": mismatched,
            "identity_consistent": False if mismatched else True if calls and verified == len(calls) else None,
        },
        "usage_aggregate": shared._aggregate_usage(measurement_view, expected_calls=MAX_CALLS),
        "cost_aggregate": shared._aggregate_cost(measurement_view, expected_calls=MAX_CALLS),
        "process_exit_code": exit_code,
    }


def _batch_id(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("batch id must be a canonical UUID") from None
    if str(parsed) != value:
        raise argparse.ArgumentTypeError("batch id must be a canonical UUID")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two fixed synthetic record evidence envelopes; no narrative generation.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--allow-synthetic-only", action="store_true")
    parser.add_argument("--batch-id", type=_batch_id)
    parser.add_argument("--api-key-env", choices=("GROQ_API_KEY",), default="GROQ_API_KEY")
    return parser


def _new_run_directory(invocation_id: str, started: datetime) -> Path:
    if OUTPUT_ROOT.resolve() != (PROJECT_ROOT / "eval-results").resolve():
        raise ValueError("Fixed output root differs")
    run_dir = OUTPUT_ROOT / f"{started.strftime('%Y%m%dT%H%M%SZ')}-{invocation_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.preflight and (args.allow_synthetic_only or args.batch_id is not None):
        raise SystemExit("Preflight does not accept live-run options")
    if args.live and (not args.allow_synthetic_only or args.batch_id is None):
        raise SystemExit("Live evidence probe requires synthetic-only acknowledgement and a batch UUID")
    try:
        prepared = prepare_experiment()
    except Exception:
        print("Record evidence preflight failed; no credential was inspected and no call was made.", file=sys.stderr)
        return 3
    if args.preflight:
        print(json.dumps(prepared.metadata, ensure_ascii=False, sort_keys=True))
        return 0
    raw_key = os.environ.get(args.api_key_env, "").strip()
    if not raw_key:
        print("Record evidence credential is missing; no call was made.", file=sys.stderr)
        return 3
    api_key = SecretStr(raw_key)
    raw_key = ""
    started = datetime.now(timezone.utc)
    invocation_id = str(uuid4())
    records: list[dict] = []
    status = "completed"
    context = {
        **copy.deepcopy(prepared.metadata), "evaluation_invocation_id": invocation_id,
        "batch_id": args.batch_id, "started_at": started.isoformat(),
    }
    try:
        run_dir = _new_run_directory(invocation_id, started)
        output = run_dir / f"{CANDIDATE_ID}.jsonl"
        with output.open("x", encoding="utf-8", newline="\n") as destination:
            def persist(row: dict) -> None:
                destination.write(json.dumps({**context, **row}, ensure_ascii=False) + "\n")
                destination.flush()
            try:
                asyncio.run(evaluate_probe(prepared, api_key=api_key, records=records, on_record=persist))
            except (KeyboardInterrupt, asyncio.CancelledError):
                status = "cancelled"
                _skip_remaining(prepared, records, "cancelled", persist)
            except Exception:
                status = "local_error"
                _skip_remaining(prepared, records, "local_error", persist)
        summary = summarize(records, status=status)
        document = {
            **context, "finished_at": datetime.now(timezone.utc).isoformat(),
            "evaluation_status": status, "process_exit_code": summary["process_exit_code"],
            "summary": summary,
        }
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 130
    except Exception:
        print("Record evidence artifact persistence failed; inspect local evidence.", file=sys.stderr)
        return 3
    finally:
        api_key = SecretStr("")
    print(f"Record evidence finished (exit code {summary['process_exit_code']}): {summary_path}")
    print("Narrative quality, runtime and CAP-001 remain unapproved.")
    return summary["process_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
