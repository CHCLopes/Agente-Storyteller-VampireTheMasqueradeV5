"""HYP-005 L3-B with one auditable retry only for OpenRouter overload."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.llm.contract import LLMInvocationError
from pydantic import SecretStr
from scripts import evaluate_closed_world_render_live as base
from scripts import evaluate_closed_world_render_plan as offline
from scripts import evaluate_openrouter_free_narrators_l2_live as l2
from scripts import evaluate_openrouter_free_narrators_live as l1
from scripts import narrator_source_profile as source_profile


VERSION = "openrouter-free-narrators-live-v3"
HYPOTHESIS_ID = "HYP-005-OPENROUTER-FREE-L3-STRICT-OVERLOAD-RETRY"
KEY_ENV = l1.KEY_ENV
BASE_URL = l1.BASE_URL
MANIFEST = l1.MANIFEST
GATE = ROOT / "evals/narrator/reports/openrouter-free-narrators-l3-live-gate-2026-09-27.json"
MAX_SLOTS = 24
MAX_ATTEMPTS_PER_SLOT = 2
MAX_CALLS = 48
MAX_OUTPUT_TOKENS = 2048
MAX_TOTAL_OUTPUT_TOKENS = MAX_CALLS * MAX_OUTPUT_TOKENS
DEFAULT_RETRY_DELAY_SECONDS = 15.0
MAX_RETRY_AFTER_SECONDS = 60.0
RETRY_CATEGORY = "provider_unavailable"
RETRY_CODE = "openrouter_provider_overloaded"

NEMOTRON = l1.NEMOTRON
LFM = l1.LFM
DEEPSEEK = l1.DEEPSEEK
CANDIDATE_IDS = l1.CANDIDATE_IDS
TARGETS = l1.TARGETS
CASE_IDS = l1.CASE_IDS
SCHEDULE = l1.SCHEDULE
OpenRouterFreeAdapter = l1.OpenRouterFreeAdapter
_route_verified = l1._route_verified


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"openrouter-free-narrators-l3-{base._batch(batch_id)}"


def _is_retryable_overload(error: dict[str, Any]) -> bool:
    return bool(
        error.get("category") == RETRY_CATEGORY
        and error.get("code") == RETRY_CODE
        and error.get("retryable") is True
    )


def _retry_delay(error: dict[str, Any]) -> float | None:
    if not _is_retryable_overload(error):
        return None
    reported = error.get("retry_after_seconds")
    if reported is None:
        return DEFAULT_RETRY_DELAY_SECONDS
    if isinstance(reported, (int, float)) and not isinstance(reported, bool):
        value = float(reported)
        if 0 <= value <= MAX_RETRY_AFTER_SECONDS:
            return value
    return None


def prepare_live() -> base.PreparedLive:
    parent = l2.prepare_live()
    gate = offline._load_json(GATE)
    base._require(
        gate.get("hypothesis_id") == HYPOTHESIS_ID
        and gate.get("selected_option") == "L3-B"
        and gate.get("single_changed_variable")
        == {
            "name": "overload_retry_policy",
            "from": "zero_retries",
            "to": (
                "one_same_request_retry_only_for_"
                "provider_unavailable_openrouter_provider_overloaded"
            ),
        }
        and gate.get("live_inference_authorized") is True
        and gate.get("execution_window") == "new_free_daily_window_only"
        and gate.get("paid_spend_authorized") is False
        and gate.get("provider_calls_at_gate_creation") == 0,
        "openrouter_l3_gate_drifted",
    )
    constraints = gate.get("constraints", {})
    base._require(
        constraints.get("slots") == MAX_SLOTS
        and constraints.get("max_attempts_per_slot") == MAX_ATTEMPTS_PER_SLOT
        and constraints.get("max_calls") == MAX_CALLS
        and constraints.get("max_output_tokens_per_call") == MAX_OUTPUT_TOKENS
        and constraints.get("max_total_output_tokens") == MAX_TOTAL_OUTPUT_TOKENS
        and constraints.get("retry_category") == RETRY_CATEGORY
        and constraints.get("retry_code") == RETRY_CODE
        and constraints.get("retry_same_request_body") is True
        and constraints.get("retry_same_target") is True
        and constraints.get("retry_other_errors") is False
        and constraints.get("repair") is False
        and constraints.get("model_fallback") is False
        and constraints.get("provider_fallback") is False
        and constraints.get("reasoning_policy_changed") is False
        and constraints.get("reported_cost_must_equal_zero_openrouter_credits") is True,
        "openrouter_l3_constraints_drifted",
    )
    base._require(
        len(SCHEDULE) == MAX_SLOTS and len(set(SCHEDULE)) == MAX_SLOTS,
        "openrouter_l3_schedule_invalid",
    )

    implementation = (
        "scripts/evaluate_openrouter_free_narrators_l3_live.py",
        "scripts/evaluate_openrouter_free_narrators_l2_live.py",
        "scripts/evaluate_openrouter_free_narrators_live.py",
        "scripts/evaluate_closed_world_render_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
    )
    parent_metadata = parent.metadata
    metadata: dict[str, Any] = {
        "purpose": "prospective_free_cross_origin_model_admission_strict_overload_retry",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_slots": MAX_SLOTS,
        "max_calls": MAX_CALLS,
        "automatic_retries": 1,
        "repair": False,
        "model_fallback": False,
        "provider_fallback": False,
        "paid_spend_authorized": False,
        "zero_cost_must_be_reported_per_response": True,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "execution_window": "new_free_daily_window_only",
        "single_changed_variable": gate["single_changed_variable"],
        "retry_policy": {
            "max_attempts_per_slot": MAX_ATTEMPTS_PER_SLOT,
            "category": RETRY_CATEGORY,
            "code": RETRY_CODE,
            "retryable_must_be_true": True,
            "same_request_body": True,
            "same_target": True,
            "reported_retry_after_honored_up_to_seconds": MAX_RETRY_AFTER_SECONDS,
            "default_delay_seconds": DEFAULT_RETRY_DELAY_SECONDS,
            "all_other_errors_retried": False,
        },
        "generation_parameters": {
            **parent_metadata["generation_parameters"],
            "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
        },
        "routing_policy": parent_metadata["routing_policy"],
        "selected_candidates": parent_metadata["selected_candidates"],
        "schedule": parent_metadata["schedule"],
        "inputs": {
            "offline_preflight": parent_metadata["inputs"]["offline_preflight"],
            "l2_baseline": {
                "hypothesis_id": l2.HYPOTHESIS_ID,
                "batch_id": "47f0c07f-ed8a-49b1-a9a6-4b760e7c4ffd",
                "preflight_sha256": "bdb6969a598932d1f4bf9c4acbb744a97130b5bc3d0c03e4de4437c07c5f35fc",
                "records_sha256": "61ca88fa5046b0e875e631ba30fff4d159ccb0e65c9ee163ed5e8336190cf111",
            },
            "candidate_manifest": parent_metadata["inputs"]["candidate_manifest"],
            "live_gate": {
                "file": GATE.relative_to(ROOT).as_posix(),
                "sha256": base._sha_file(GATE),
            },
            "response_schema_sha256": base._sha_value(
                source_profile.NarrativeSourceProposal.model_json_schema()
            ),
            "implementation": [
                {"file": name, "sha256": base._sha_file(ROOT / name)}
                for name in implementation
            ],
        },
        "provider_calls": 0,
        "credential_inspected": False,
        "live_execution_requires_cli_opt_in": True,
        "admission": parent_metadata["admission"],
    }
    return base.PreparedLive(
        parent.candidates,
        parent.targets,
        parent.corpus,
        parent.system_prompt,
        metadata,
    )


def _check_prepared(prepared: base.PreparedLive) -> None:
    current = prepare_live()
    base._require(
        type(prepared) is base.PreparedLive
        and base._canonical(prepared.metadata) == base._canonical(current.metadata),
        "openrouter_l3_prepared_drifted",
    )


def _skip_row(identity: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **identity,
        "status": "skipped",
        "reason": reason,
        "call_made": False,
        "attempt_count": 0,
        "attempts": [],
    }


def _attempt_shell(index: int, request: Any, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempt_index": index,
        "call_made": False,
        "request": {
            "operation": request.operation,
            "invocation_id": request.invocation_id,
            "deadline": request.deadline.isoformat(),
            "body_sha256": base._sha_value(body),
            "target": request.target.model_dump(mode="json"),
        },
        "status": "pending",
        "response": None,
        "evidence": None,
        "error": None,
        "route_verified": False,
        "credential_echo_blocked": False,
        "retry_scheduled": False,
        "retry_delay_seconds": None,
    }


def _copy_final_attempt(row: dict[str, Any], attempt: dict[str, Any]) -> None:
    row.update(
        status=attempt["status"],
        response=attempt["response"],
        evidence=attempt["evidence"],
        error=attempt["error"],
        route_verified=attempt["route_verified"],
        credential_echo_blocked=attempt["credential_echo_blocked"],
    )


async def run_live(
    prepared: base.PreparedLive,
    *,
    api_key: SecretStr,
    batch_id: str,
    run_directory: Path,
    pacer: Any | None = None,
) -> dict[str, Any]:
    base._batch(batch_id)
    _check_prepared(prepared)
    secret = api_key.get_secret_value().strip() if type(api_key) is SecretStr else ""
    base._require(bool(secret), "live_credential_invalid")
    base._require(secret not in base._canonical(prepared.metadata), "live_credential_conflict")
    directory = Path(run_directory)
    base._require(
        directory.resolve() == run_path(batch_id).resolve(),
        "live_run_path_invalid",
    )
    directory.mkdir(parents=True, exist_ok=False)
    budget = base.DispatchBudget(pacer)
    prior_texts: dict[tuple[str, str], str] = {}
    failed_cases: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    global_stop: str | None = None
    started_at = base.utc_now().isoformat()

    for slot, (candidate_id, case_id) in enumerate(SCHEDULE):
        case = base._case(prepared, case_id)
        identity = base._row_identity(
            slot, candidate_id, case_id, case["prior_case_id"]
        )
        if global_stop is not None:
            rows.append(_skip_row(identity, f"global_{global_stop}"))
            continue
        if case["prior_case_id"] is not None and (
            candidate_id, case["prior_case_id"]
        ) in failed_cases:
            rows.append(_skip_row(identity, "prior_case_failed"))
            failed_cases.add((candidate_id, case_id))
            continue

        request = base._request(
            prepared, batch_id, candidate_id, case_id, prior_texts
        )
        reasoning = TARGETS[candidate_id]["reasoning"]
        body = base._request_body(request, reasoning)
        capsule = base._capsule(
            batch_id,
            slot,
            candidate_id,
            case_id,
            request,
            body,
            prior_texts,
            case["prior_case_id"],
        )
        row: dict[str, Any] = {
            **identity,
            "status": "pending",
            "call_made": False,
            "attempt_count": 0,
            "attempts": [],
            "capsule": capsule,
            "capsule_sha256": base._sha_value(capsule),
            "request": {
                "operation": request.operation,
                "invocation_id": request.invocation_id,
                "body_sha256": base._sha_value(body),
                "target": request.target.model_dump(mode="json"),
            },
            "response": None,
            "evidence": None,
            "error": None,
            "route_verified": False,
            "credential_echo_blocked": False,
        }

        for attempt_index in range(1, MAX_ATTEMPTS_PER_SLOT + 1):
            dispatch_request = request
            dispatch_body = body
            attempt = _attempt_shell(attempt_index, dispatch_request, dispatch_body)
            try:
                await budget.before_call(
                    f"HYP-005 L3 slot {slot + 1}/{MAX_SLOTS} "
                    f"attempt {attempt_index}/{MAX_ATTEMPTS_PER_SLOT}"
                )
                attempt["call_made"] = True
                row["call_made"] = True
                candidate = prepared.candidates[candidate_id]
                adapter = base.GroqAdapter(
                    base_url=base.GROQ_OFFICIAL_BASE_URL,
                    capability_set=base.shared._capabilities(
                        candidate, dispatch_request.target
                    ),
                    api_key=api_key,
                    reasoning_effort=reasoning,
                )
                result = await adapter.generate_structured(dispatch_request)
                response = result.value.model_dump(mode="json", by_alias=True)
                evidence = result.evidence.model_dump(mode="json")
                if base._contains_secret(
                    {"response": response, "evidence": evidence}, secret
                ):
                    attempt.update(
                        status="failed",
                        credential_echo_blocked=True,
                        error={"category": "credential_echo_blocked"},
                    )
                elif not _route_verified(evidence, dispatch_request.target):
                    attempt.update(
                        status="failed",
                        error={"category": "target_mismatch"},
                    )
                else:
                    attempt.update(
                        status="completed",
                        response=response,
                        evidence=evidence,
                        route_verified=True,
                    )
            except asyncio.CancelledError:
                attempt.update(status="failed", error={"category": "cancelled"})
            except LLMInvocationError as exc:
                error = base._safe_error(exc.error)
                if base._contains_secret(error, secret):
                    attempt.update(
                        status="failed",
                        credential_echo_blocked=True,
                        error={"category": "credential_echo_blocked"},
                    )
                else:
                    attempt.update(
                        status="failed",
                        error=error,
                        evidence=error.get("evidence"),
                    )
            except Exception:
                attempt.update(status="failed", error={"category": "local_error"})

            retry_delay = (
                _retry_delay(attempt["error"])
                if attempt["status"] == "failed"
                and attempt_index == 1
                and isinstance(attempt["error"], dict)
                else None
            )
            if retry_delay is not None:
                attempt["retry_scheduled"] = True
                attempt["retry_delay_seconds"] = retry_delay
            row["attempts"].append(attempt)
            row["attempt_count"] = len(row["attempts"])

            if retry_delay is not None:
                await asyncio.sleep(retry_delay)
                continue

            _copy_final_attempt(row, attempt)
            break

        base._require(row["status"] != "pending", "live_retry_terminal_state_missing")
        if row["status"] == "completed":
            response = row["response"]
            prior_texts[(candidate_id, case_id)] = (
                f"{response['n']}\n\n{response['q']}"
            )
        else:
            failed_cases.add((candidate_id, case_id))
            category = row.get("error", {}).get("category")
            if category not in base.CHAIN_LOCAL_ERRORS:
                global_stop = category or "local_error"
        rows.append(row)

    records = directory / "records.jsonl"
    records.write_text(
        "".join(
            base._canonical(
                {
                    "metadata": prepared.metadata,
                    "batch_id": batch_id,
                    "record": row,
                }
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    summary = summarize(rows)
    document = {
        "metadata": prepared.metadata,
        "batch_id": batch_id,
        "started_at": started_at,
        "finished_at": base.utc_now().isoformat(),
        "summary": summary,
        "artifacts": {
            "records": {
                "file": records.name,
                "sha256": base._sha_file(records),
            }
        },
        "process_exit_code": summary["process_exit_code"],
    }
    summary_path = directory / "summary.json"
    summary_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    secret = ""
    api_key = SecretStr("")
    return document


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base._require(len(rows) == MAX_SLOTS, "live_rows_incomplete")
    calls = sum(
        attempt.get("call_made") is True
        for row in rows
        for attempt in row.get("attempts", [])
    )
    base._require(calls <= MAX_CALLS, "live_call_budget_exhausted")
    completed = sum(row["status"] == "completed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    skipped = sum(row["status"] == "skipped" for row in rows)
    retried_slots = sum(row.get("attempt_count") == 2 for row in rows)
    categories = [
        row.get("error", {}).get("category")
        for row in rows
        if row.get("error") is not None
    ]
    if "cancelled" in categories:
        code = 130
    elif any(
        category in {"local_error", "credential_echo_blocked", "target_mismatch"}
        for category in categories
    ):
        code = 3
    elif any(
        category not in base.CHAIN_LOCAL_ERRORS for category in categories
    ):
        code = 2
    elif failed:
        code = 1
    else:
        code = 0
    return {
        "calls_made": calls,
        "retry_attempts": retried_slots,
        "retried_slots": retried_slots,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "max_slots": MAX_SLOTS,
        "max_calls": MAX_CALLS,
        "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
        "semantic_review_status": "not_performed",
        "qualified_candidates": [],
        "runtime_default_eligible": False,
        "process_exit_code": code,
    }


def _validate_attempts(
    row: dict[str, Any],
    request: Any,
    body: dict[str, Any],
) -> dict[str, Any]:
    attempts = row.get("attempts")
    base._require(
        isinstance(attempts, list)
        and len(attempts) in {1, 2}
        and row.get("attempt_count") == len(attempts)
        and row.get("call_made")
        == any(attempt.get("call_made") is True for attempt in attempts),
        "live_attempt_count_invalid",
    )
    body_sha256 = base._sha_value(body)
    for index, attempt in enumerate(attempts, start=1):
        base._require(
            attempt.get("attempt_index") == index
            and attempt.get("request", {}).get("operation") == request.operation
            and attempt.get("request", {}).get("invocation_id")
            == request.invocation_id
            and attempt.get("request", {}).get("body_sha256") == body_sha256
            and attempt.get("request", {}).get("target")
            == request.target.model_dump(mode="json")
            and attempt.get("credential_echo_blocked") is False,
            "live_attempt_identity_invalid",
        )
        if attempt.get("call_made") is not True:
            base._require(
                len(attempts) == 1
                and attempt.get("status") == "failed"
                and attempt.get("error") == {"category": "cancelled"},
                "live_undispatched_attempt_invalid",
            )
    if len(attempts) == 2:
        first = attempts[0]
        delay = _retry_delay(first.get("error", {}))
        base._require(
            first.get("status") == "failed"
            and delay is not None
            and first.get("retry_scheduled") is True
            and first.get("retry_delay_seconds") == delay,
            "live_retry_causality_invalid",
        )
    else:
        base._require(
            attempts[0].get("retry_scheduled") is False
            and attempts[0].get("retry_delay_seconds") is None,
            "live_unexpected_retry_marker",
        )
    final = attempts[-1]
    base._require(
        final.get("retry_scheduled") is False
        and final.get("retry_delay_seconds") is None,
        "live_terminal_retry_marker_invalid",
    )
    return final


def verify_artifacts(
    summary_path: Path,
    expected_preflight: Path,
    batch_id: str,
    *,
    expected_preflight_sha256: str,
) -> dict[str, Any]:
    base._batch(batch_id)
    prepared = base._expected_preflight(
        expected_preflight, expected_preflight_sha256
    )
    expected_summary = run_path(batch_id) / "summary.json"
    base._require(
        summary_path.resolve() == expected_summary.resolve()
        and summary_path.is_file(),
        "live_summary_path_invalid",
    )
    originals = {summary_path: base._sha_file(summary_path)}
    document = offline._load_json(summary_path)
    base._require(
        document.get("metadata") == prepared.metadata
        and document.get("batch_id") == batch_id,
        "live_summary_identity_invalid",
    )
    record_entry = document.get("artifacts", {}).get("records", {})
    records_path = summary_path.parent / record_entry.get("file", "")
    base._require(
        records_path.parent == summary_path.parent
        and records_path.name == "records.jsonl"
        and records_path.is_file()
        and base._sha_file(records_path) == record_entry.get("sha256"),
        "live_records_hash_invalid",
    )
    originals[records_path] = base._sha_file(records_path)
    envelopes = base._load_jsonl(records_path)
    base._require(len(envelopes) == MAX_SLOTS, "live_record_count_invalid")

    rows: list[dict[str, Any]] = []
    prior_texts: dict[tuple[str, str], str] = {}
    failed_cases: set[tuple[str, str]] = set()
    global_stop: str | None = None
    for slot, (envelope, scheduled) in enumerate(
        zip(envelopes, prepared.metadata["schedule"], strict=True)
    ):
        base._require(
            envelope.get("metadata") == prepared.metadata
            and envelope.get("batch_id") == batch_id,
            "live_envelope_invalid",
        )
        row = envelope.get("record")
        base._require(
            isinstance(row, dict)
            and all(row.get(key) == value for key, value in scheduled.items()),
            "live_record_identity_invalid",
        )
        expected_skip: str | None = None
        if global_stop is not None:
            expected_skip = f"global_{global_stop}"
        elif scheduled["prior_case_id"] is not None and (
            scheduled["candidate_id"], scheduled["prior_case_id"]
        ) in failed_cases:
            expected_skip = "prior_case_failed"

        if expected_skip is not None:
            base._require(
                row == _skip_row(scheduled, expected_skip),
                "live_skip_causality_invalid",
            )
            if expected_skip == "prior_case_failed":
                failed_cases.add(
                    (scheduled["candidate_id"], scheduled["case_id"])
                )
            rows.append(row)
            continue

        request = base._request(
            prepared,
            batch_id,
            scheduled["candidate_id"],
            scheduled["case_id"],
            prior_texts,
        )
        reasoning = TARGETS[scheduled["candidate_id"]]["reasoning"]
        body = base._request_body(request, reasoning)
        expected_capsule = base._capsule(
            batch_id,
            slot,
            scheduled["candidate_id"],
            scheduled["case_id"],
            request,
            body,
            prior_texts,
            scheduled["prior_case_id"],
        )
        base._require(
            row.get("capsule") == expected_capsule
            and row.get("capsule_sha256") == base._sha_value(expected_capsule)
            and row.get("request")
            == {
                "operation": request.operation,
                "invocation_id": request.invocation_id,
                "body_sha256": base._sha_value(body),
                "target": request.target.model_dump(mode="json"),
            },
            "live_capsule_link_invalid",
        )
        final = _validate_attempts(row, request, body)
        base._require(
            row.get("status") == final.get("status")
            and row.get("response") == final.get("response")
            and row.get("evidence") == final.get("evidence")
            and row.get("error") == final.get("error")
            and row.get("route_verified") == final.get("route_verified")
            and row.get("credential_echo_blocked")
            == final.get("credential_echo_blocked"),
            "live_final_attempt_projection_invalid",
        )

        if row["status"] == "completed":
            response = row.get("response")
            base._require(
                isinstance(response, dict)
                and isinstance(response.get("n"), str)
                and isinstance(response.get("q"), str)
                and row.get("error") is None
                and row.get("route_verified") is True
                and _route_verified(
                    row["evidence"],
                    prepared.targets[row["candidate_id"]],
                ),
                "live_completed_record_invalid",
            )
            prior_texts[
                (scheduled["candidate_id"], scheduled["case_id"])
            ] = f"{response['n']}\n\n{response['q']}"
        elif row["status"] == "failed":
            error = row.get("error")
            base._require(
                isinstance(error, dict)
                and isinstance(error.get("category"), str),
                "live_failed_record_invalid",
            )
            failed_cases.add(
                (scheduled["candidate_id"], scheduled["case_id"])
            )
            if error["category"] not in base.CHAIN_LOCAL_ERRORS:
                global_stop = error["category"]
        else:
            raise ValueError("live_record_status_invalid")
        rows.append(row)

    reconstructed = summarize(rows)
    base._require(
        document.get("summary") == reconstructed
        and document.get("process_exit_code")
        == reconstructed["process_exit_code"],
        "live_summary_reconstruction_failed",
    )
    base._require(
        all(base._sha_file(path) == digest for path, digest in originals.items()),
        "live_artifact_changed_during_verification",
    )
    return {
        "verified": True,
        "batch_id": batch_id,
        "process_exit_code": reconstructed["process_exit_code"],
        "summary_path": str(summary_path.resolve()),
    }


def configure() -> None:
    base.VERSION = VERSION
    base.KEY_ENV = KEY_ENV
    base.MANIFEST = MANIFEST
    base.LIVE_GATE = GATE
    base.MAX_CALLS = MAX_CALLS
    base.MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS
    base.MAX_TOTAL_OUTPUT_TOKENS = MAX_TOTAL_OUTPUT_TOKENS
    base.DEADLINE_SECONDS = 90
    base.MINIMUM_INTERVAL_SECONDS = 4
    base.CANDIDATE_IDS = CANDIDATE_IDS
    base.TARGETS = TARGETS
    base.SCHEDULE = SCHEDULE
    base.GROQ_OFFICIAL_BASE_URL = BASE_URL
    base.GroqAdapter = OpenRouterFreeAdapter
    base.run_path = run_path
    base.prepare_live = prepare_live
    base._check_prepared = _check_prepared
    base.run_live = run_live
    base.summarize = summarize
    base.verify_artifacts = verify_artifacts
    base._route_verified = _route_verified


def main(argv: list[str] | None = None) -> int:
    configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
