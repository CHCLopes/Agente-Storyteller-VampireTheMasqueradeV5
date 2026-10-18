"""Bounded HYP-003 runner for Gemini Flash on an asserted Free Tier project."""

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from uuid import UUID, uuid5


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr

from api.llm.adapters.gemini import (
    GEMINI_OFFICIAL_BASE_URL,
    GEMINI_PROVIDER_LABEL,
    GeminiAdapter,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityRequirement,
    CancellationToken,
    ErrorCategory,
    GenerationParameters,
    LLMInvocationError,
    LLMMessage,
    LLMTarget,
    MessageRole,
    StructuredGenerationRequest,
    utc_now,
)
from scripts import evaluate_closed_world_render_plan as contract
from scripts import evaluate_narrator_models as shared
from scripts import narrator_source_profile as source_profile


VERSION = "gemini-free-closed-world-live-v4"
HYPOTHESIS_ID = "HYP-003-GEMINI-FREE-L4"
KEY_ENV = "STORYTELLER_HYP003_GEMINI_KEY"
OUTPUT_ROOT = ROOT / "eval-results"
CORPUS = ROOT / "evals/narrator/gemini_free_closed_world_contract_v1.json"
MANIFEST = ROOT / "evals/narrator/gemini_candidates_2026-09-05.json"
CANDIDATE_ID = "gemini-3.8-flash-free-synthetic-low"
MODEL = "gemini-3.8-flash"
REASONING = "low"
MAX_CASES = 8
MAX_PROVIDER_ATTEMPTS = 16
MAX_TRANSPORT_RETRIES_PER_CASE = 2
MAX_OUTPUT_TOKENS = 768
MAX_TOTAL_OUTPUT_TOKENS = MAX_CASES * MAX_OUTPUT_TOKENS
DEADLINE_SECONDS = 60
MINIMUM_INTERVAL_SECONDS = 60
TRANSPORT_RETRY_BASE_SECONDS = (60, 180)
TRANSPORT_RETRY_JITTER_MAX_SECONDS = 15
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
CHAIN_LOCAL_ERRORS = frozenset(
    {
        ErrorCategory.INVALID_STRUCTURED_OUTPUT.value,
        ErrorCategory.MALFORMED_RESPONSE.value,
        ErrorCategory.CONTENT_REJECTED.value,
    }
)


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _sha_value(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, code: str = "gemini_free_live_invalid") -> None:
    if not condition:
        raise ValueError(code)


def _batch(value: str) -> str:
    parsed = UUID(value)
    _require(str(parsed) == value and parsed.version == 4, "gemini_free_batch_invalid")
    return value


def run_path(batch_id: str) -> Path:
    return OUTPUT_ROOT / f"gemini-free-closed-world-{_batch(batch_id)}"


def _load_corpus() -> dict[str, Any]:
    corpus = contract._load_json(CORPUS)
    _require(corpus.get("hypothesis_id") == "gemini_free_closed_world_v1")
    compatibility = deepcopy(corpus)
    compatibility["hypothesis_id"] = "closed_world_render_plan_v1"
    contract.validate_corpus(compatibility)
    return corpus


@dataclass(frozen=True)
class PreparedLive:
    candidate: Any
    target: LLMTarget
    corpus: dict[str, Any]
    system_prompt: str
    metadata: dict[str, Any]


def prepare_live() -> PreparedLive:
    corpus = _load_corpus()
    candidates = shared.load_candidates(MANIFEST)
    candidate = candidates[CANDIDATE_ID]
    _require(
        candidate.adapter_kind == "gemini"
        and candidate.provider_label == GEMINI_PROVIDER_LABEL
        and candidate.effective_provider == GEMINI_PROVIDER_LABEL
        and candidate.upstream_provider is None
        and candidate.structured_mode == "native"
        and candidate.model == MODEL
        and candidate.reasoning_effort == REASONING
        and candidate.allow_data_collection is True
        and candidate.campaign_data_eligible is False,
        "gemini_free_candidate_invalid",
    )
    target = LLMTarget(
        profile="hyp-003-gemini-free-synthetic-low",
        provider=GEMINI_PROVIDER_LABEL,
        model=MODEL,
    )
    schedule = [
        {
            "slot": slot,
            "candidate_id": CANDIDATE_ID,
            "case_id": case["case_id"],
            "prior_case_id": case["prior_case_id"],
        }
        for slot, case in enumerate(corpus["cases"])
    ]
    _require(len(schedule) == MAX_CASES)
    sources = (
        "scripts/evaluate_gemini_free_closed_world_live.py",
        "scripts/evaluate_closed_world_render_plan.py",
        "scripts/narrator_source_profile.py",
        "api/llm/adapters/gemini.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
        "evals/narrator/prompts/narrative-source-progress-v1.md",
        "evals/narrator/prompts/closed-world-render-contract-v1.md",
    )
    metadata = {
        "purpose": "gemini_free_closed_world_hypothesis",
        "version": VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "option": "GEMINI-FREE-L4-INTEGRAL-TRANSPORT-RETRY",
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "free_tier_project_attestation_required": True,
        "free_tier_content_may_improve_google_products": True,
        "paid_spend_authorized": False,
        "max_cases": MAX_CASES,
        "max_provider_attempts": MAX_PROVIDER_ATTEMPTS,
        "automatic_retries": MAX_TRANSPORT_RETRIES_PER_CASE,
        "narrative_retries": 0,
        "transport_retry_policy": {
            "only_without_response": True,
            "eligible_http_statuses": [408, 429, "5xx"],
            "eligible_phases": ["connect"],
            "max_retries_per_case": MAX_TRANSPORT_RETRIES_PER_CASE,
            "global_attempt_cap": MAX_PROVIDER_ATTEMPTS,
            "backoff_base_seconds": list(TRANSPORT_RETRY_BASE_SECONDS),
            "deterministic_jitter_max_seconds": TRANSPORT_RETRY_JITTER_MAX_SECONDS,
            "all_attempts_persisted": True,
        },
        "repair": False,
        "fallback": False,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "generation_parameters": {
            "reasoning_effort": REASONING,
            "sampling_parameters_sent": False,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
            "deadline_seconds": DEADLINE_SECONDS,
            "minimum_global_start_interval_seconds": MINIMUM_INTERVAL_SECONDS,
        },
        "selected_candidate": {
            "candidate_id": candidate.candidate_id,
            "provider": candidate.provider_label,
            "model": candidate.model,
            "reasoning_effort": candidate.reasoning_effort,
            "target": target.model_dump(mode="json"),
        },
        "schedule": schedule,
        "inputs": {
            "corpus": {
                "file": CORPUS.relative_to(ROOT).as_posix(),
                "sha256": _sha_file(CORPUS),
            },
            "candidate_manifest": {
                "file": MANIFEST.relative_to(ROOT).as_posix(),
                "sha256": _sha_file(MANIFEST),
            },
            "response_schema_sha256": _sha_value(
                source_profile.NarrativeSourceProposal.model_json_schema()
            ),
            "implementation": [
                {"file": name, "sha256": _sha_file(ROOT / name)} for name in sources
            ],
        },
        "provider_calls": 0,
        "credential_inspected": False,
        "live_execution_requires_cli_opt_in": True,
    }
    return PreparedLive(
        candidate=candidate,
        target=target,
        corpus=corpus,
        system_prompt=contract.render_system_prompt(),
        metadata=metadata,
    )


def _check_prepared(prepared: PreparedLive) -> None:
    current = prepare_live()
    _require(
        type(prepared) is PreparedLive
        and _canonical(prepared.metadata) == _canonical(current.metadata)
        and prepared.system_prompt == current.system_prompt
    )


def _case(prepared: PreparedLive, case_id: str) -> dict[str, Any]:
    return next(case for case in prepared.corpus["cases"] if case["case_id"] == case_id)


def _invocation_id(batch_id: str, case_id: str, attempt_index: int) -> str:
    _require(0 <= attempt_index <= MAX_TRANSPORT_RETRIES_PER_CASE)
    return str(
        uuid5(
            UUID(_batch(batch_id)),
            f"{VERSION}.{CANDIDATE_ID}.{case_id}.attempt-{attempt_index + 1}",
        )
    )


def _payload_for_case(
    prepared: PreparedLive,
    case_id: str,
    prior_texts: dict[str, str],
) -> dict[str, Any]:
    case = _case(prepared, case_id)
    compatibility = deepcopy(case)
    payload = contract.render_case_payload(compatibility)
    payload["protocol"] = "gemini_free_closed_world_v1"
    prior_case_id = case["prior_case_id"]
    if prior_case_id is not None:
        _require(prior_case_id in prior_texts, "gemini_free_prior_source_missing")
        payload["attributed_source"] = {
            "case_id": prior_case_id,
            "content": prior_texts[prior_case_id],
        }
    return payload


def _request(
    prepared: PreparedLive,
    batch_id: str,
    case_id: str,
    prior_texts: dict[str, str],
    attempt_index: int = 0,
) -> StructuredGenerationRequest:
    payload = _payload_for_case(prepared, case_id, prior_texts)
    return StructuredGenerationRequest(
        invocation_id=_invocation_id(batch_id, case_id, attempt_index),
        operation=f"{VERSION}.{case_id}",
        target=prepared.target,
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content=prepared.system_prompt),
            LLMMessage(role=MessageRole.USER, content=_canonical(payload)),
        ),
        deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
        cancellation=CancellationToken(),
        parameters=GenerationParameters(max_output_tokens=MAX_OUTPUT_TOKENS),
        response_model=source_profile.NarrativeSourceProposal,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION, allow_emulated=False
            ),
        ),
    )


def _request_body(request: StructuredGenerationRequest) -> dict[str, Any]:
    builder = object.__new__(GeminiAdapter)
    builder._reasoning_effort = REASONING
    return GeminiAdapter._payload(
        builder,
        request,
        response_schema=source_profile.NarrativeSourceProposal.model_json_schema(),
        json_mode=True,
    )


def _capsule(
    batch_id: str,
    slot: int,
    case_id: str,
    request: StructuredGenerationRequest,
    body: dict[str, Any],
    prior_texts: dict[str, str],
    prior_case_id: str | None,
    attempt_index: int = 0,
) -> dict[str, Any]:
    prior = prior_texts.get(prior_case_id) if prior_case_id else None
    return {
        "protocol": VERSION,
        "batch_id": batch_id,
        "slot": slot,
        "candidate_id": CANDIDATE_ID,
        "case_id": case_id,
        "attempt_index": attempt_index,
        "prior_case_id": prior_case_id,
        "prior_source_sha256": (
            hashlib.sha256(prior.encode("utf-8")).hexdigest() if prior else None
        ),
        "invocation_id": request.invocation_id,
        "target": request.target.model_dump(mode="json"),
        "system_sha256": hashlib.sha256(
            request.messages[0].content.encode("utf-8")
        ).hexdigest(),
        "user_sha256": hashlib.sha256(
            request.messages[1].content.encode("utf-8")
        ).hexdigest(),
        "body_sha256": _sha_value(body),
    }


def _route_verified(evidence: dict[str, Any], target: LLMTarget) -> bool:
    provenance = evidence.get("provenance") if isinstance(evidence, dict) else None
    if not isinstance(provenance, dict):
        return False
    requested = provenance.get("requested_target")
    model = provenance.get("effective_model")
    provider = provenance.get("effective_provider")
    reported = model.get("value") if isinstance(model, dict) else None
    return (
        requested == target.model_dump(mode="json")
        and isinstance(reported, str)
        and (reported == MODEL or re.fullmatch(rf"{re.escape(MODEL)}-\d{{3}}", reported))
        is not None
        and isinstance(model, dict)
        and model.get("source") == "reported"
        and isinstance(provider, dict)
        and provider.get("value") == GEMINI_PROVIDER_LABEL
        and provider.get("source") in {"reported", "observed"}
    )


class DispatchBudget:
    def __init__(self, pacer: Any | None = None) -> None:
        self.calls = 0
        self.pacer = pacer or shared._CallPacer(MINIMUM_INTERVAL_SECONDS)

    async def before_call(self, label: str) -> None:
        _require(
            self.calls < MAX_PROVIDER_ATTEMPTS,
            "gemini_free_call_budget_exhausted",
        )
        await self.pacer.before_call(label)
        self.calls += 1


class TransportRetryWaiter:
    async def wait(self, delay_seconds: int, label: str) -> None:
        print(f"Transport backoff: waiting {delay_seconds}s before {label}")
        await asyncio.sleep(delay_seconds)


def _transport_retry_delay(batch_id: str, slot: int, retry_ordinal: int) -> int:
    _require(1 <= retry_ordinal <= MAX_TRANSPORT_RETRIES_PER_CASE)
    digest = hashlib.sha256(
        f"{_batch(batch_id)}:{slot}:{retry_ordinal}".encode("utf-8")
    ).digest()
    jitter = int.from_bytes(digest[:2], "big") % (
        TRANSPORT_RETRY_JITTER_MAX_SECONDS + 1
    )
    return TRANSPORT_RETRY_BASE_SECONDS[retry_ordinal - 1] + jitter


def _is_strict_transport_retry(error: dict[str, Any]) -> bool:
    status = error.get("status_code")
    eligible_status = status in {408, 429} or (
        isinstance(status, int) and 500 <= status <= 599
    )
    return (
        error.get("retryable") is True
        and error.get("partial_output") is False
        and error.get("phase") == "connect"
        and eligible_status
        and error.get("category")
        in {
            ErrorCategory.TIMEOUT.value,
            ErrorCategory.RATE_LIMITED.value,
            ErrorCategory.PROVIDER_UNAVAILABLE.value,
        }
    )


def _safe_error(error: Any) -> dict[str, Any]:
    return error.model_dump(mode="json")


def _contains_secret(value: object, secret: str) -> bool:
    return bool(secret) and secret in _canonical(value)


async def run_live(
    prepared: PreparedLive,
    *,
    api_key: SecretStr,
    batch_id: str,
    run_directory: Path,
    free_tier_project_confirmed: bool,
    pacer: Any | None = None,
    retry_waiter: Any | None = None,
) -> dict[str, Any]:
    _batch(batch_id)
    _check_prepared(prepared)
    _require(free_tier_project_confirmed, "gemini_free_tier_not_confirmed")
    secret = api_key.get_secret_value().strip() if type(api_key) is SecretStr else ""
    _require(bool(secret), "gemini_free_credential_invalid")
    _require(secret not in _canonical(prepared.metadata), "gemini_free_credential_conflict")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve(), "gemini_free_run_path_invalid")
    directory.mkdir(parents=True, exist_ok=False)
    budget = DispatchBudget(pacer)
    retry_waiter = retry_waiter or TransportRetryWaiter()
    prior_texts: dict[str, str] = {}
    failed_cases: set[str] = set()
    rows: list[dict[str, Any]] = []
    global_stop: str | None = None
    started_at = utc_now().isoformat()
    adapter = GeminiAdapter(
        base_url=GEMINI_OFFICIAL_BASE_URL,
        capability_set=shared._capabilities(prepared.candidate, prepared.target),
        api_key=api_key,
        reasoning_effort=REASONING,
    )

    for scheduled in prepared.metadata["schedule"]:
        slot = scheduled["slot"]
        case_id = scheduled["case_id"]
        prior_case_id = scheduled["prior_case_id"]
        identity = dict(scheduled)
        if global_stop is not None:
            rows.append({**identity, "status": "skipped", "reason": f"global_{global_stop}"})
            continue
        if prior_case_id is not None and prior_case_id in failed_cases:
            rows.append({**identity, "status": "skipped", "reason": "prior_case_failed"})
            failed_cases.add(case_id)
            continue

        row: dict[str, Any] = {
            **identity,
            "status": "pending",
            "call_made": False,
            "attempt_count": 0,
            "transport_retry_count": 0,
            "attempts": [],
            "response": None,
            "evidence": None,
            "error": None,
            "route_verified": False,
            "credential_echo_blocked": False,
        }
        previous_invocation_id: str | None = None
        for attempt_index in range(MAX_TRANSPORT_RETRIES_PER_CASE + 1):
            if budget.calls >= MAX_PROVIDER_ATTEMPTS:
                row.update(
                    status="failed",
                    error={"category": "transport_retry_budget_exhausted"},
                )
                global_stop = "transport_retry_budget_exhausted"
                break
            request = _request(
                prepared, batch_id, case_id, prior_texts, attempt_index
            )
            body = _request_body(request)
            capsule = _capsule(
                batch_id,
                slot,
                case_id,
                request,
                body,
                prior_texts,
                prior_case_id,
                attempt_index,
            )
            attempt: dict[str, Any] = {
                "attempt_index": attempt_index,
                "retry_of_invocation_id": previous_invocation_id,
                "call_made": False,
                "capsule": capsule,
                "capsule_sha256": _sha_value(capsule),
                "request": {
                    "operation": request.operation,
                    "invocation_id": request.invocation_id,
                    "deadline": request.deadline.isoformat(),
                    "body_sha256": _sha_value(body),
                },
                "status": "pending",
                "response": None,
                "evidence": None,
                "error": None,
                "route_verified": False,
                "credential_echo_blocked": False,
                "retry_eligible": False,
                "retry_scheduled": False,
                "retry_delay_seconds": None,
                "retry_exhaustion_reason": None,
            }
            should_retry = False
            try:
                await budget.before_call(
                    f"HYP-003 Gemini slot {slot + 1}/{MAX_CASES} "
                    f"attempt {attempt_index + 1}/{MAX_TRANSPORT_RETRIES_PER_CASE + 1}"
                )
                dispatch_request = _request(
                    prepared, batch_id, case_id, prior_texts, attempt_index
                )
                dispatch_body = _request_body(dispatch_request)
                dispatch_capsule = _capsule(
                    batch_id,
                    slot,
                    case_id,
                    dispatch_request,
                    dispatch_body,
                    prior_texts,
                    prior_case_id,
                    attempt_index,
                )
                _require(
                    dispatch_capsule == capsule,
                    "gemini_free_dispatch_capsule_drifted",
                )
                request = dispatch_request
                attempt["request"]["deadline"] = request.deadline.isoformat()
                attempt["call_made"] = True
                row["call_made"] = True
                result = await adapter.generate_structured(request)
                response = result.value.model_dump(mode="json", by_alias=True)
                evidence = result.evidence.model_dump(mode="json")
                if _contains_secret(
                    {"response": response, "evidence": evidence}, secret
                ):
                    attempt.update(
                        status="failed",
                        credential_echo_blocked=True,
                        error={"category": "credential_echo_blocked"},
                    )
                    global_stop = "credential_echo_blocked"
                elif not _route_verified(evidence, request.target):
                    attempt.update(
                        status="failed",
                        response=response,
                        evidence=evidence,
                        error={"category": "target_mismatch"},
                    )
                    global_stop = "target_mismatch"
                else:
                    attempt.update(
                        status="completed",
                        response=response,
                        evidence=evidence,
                        route_verified=True,
                    )
                    text = f"{response['n']}\n\n{response['q']}"
                    row.update(
                        status="completed",
                        response=response,
                        evidence=evidence,
                        route_verified=True,
                    )
                    prior_texts[case_id] = text
            except asyncio.CancelledError:
                attempt.update(status="failed", error={"category": "cancelled"})
                global_stop = "cancelled"
            except LLMInvocationError as exc:
                error = _safe_error(exc.error)
                if _contains_secret(error, secret):
                    attempt.update(
                        status="failed",
                        credential_echo_blocked=True,
                        error={"category": "credential_echo_blocked"},
                    )
                    global_stop = "credential_echo_blocked"
                else:
                    category = error["category"]
                    eligible = _is_strict_transport_retry(error)
                    can_retry_case = attempt_index < MAX_TRANSPORT_RETRIES_PER_CASE
                    can_retry_global = budget.calls < MAX_PROVIDER_ATTEMPTS
                    should_retry = eligible and can_retry_case and can_retry_global
                    attempt.update(
                        status="failed",
                        error=error,
                        evidence=error.get("evidence"),
                        retry_eligible=eligible,
                    )
                    if should_retry:
                        delay = _transport_retry_delay(
                            batch_id, slot, attempt_index + 1
                        )
                        attempt.update(
                            retry_scheduled=True,
                            retry_delay_seconds=delay,
                        )
                    else:
                        if eligible and not can_retry_case:
                            attempt["retry_exhaustion_reason"] = (
                                "per_case_retry_limit"
                            )
                        elif eligible and not can_retry_global:
                            attempt["retry_exhaustion_reason"] = (
                                "global_attempt_cap"
                            )
                        row.update(
                            status="failed",
                            error=error,
                            evidence=error.get("evidence"),
                        )
                        if category not in CHAIN_LOCAL_ERRORS:
                            global_stop = category
            except Exception:
                attempt.update(
                    status="failed", error={"category": "local_error"}
                )
                global_stop = "local_error"

            row["attempts"].append(attempt)
            row["attempt_count"] = len(row["attempts"])
            row["transport_retry_count"] = max(0, row["attempt_count"] - 1)
            previous_invocation_id = request.invocation_id
            if should_retry:
                await retry_waiter.wait(
                    attempt["retry_delay_seconds"],
                    f"slot {slot + 1}/{MAX_CASES} attempt {attempt_index + 2}",
                )
                continue
            if row["status"] == "pending":
                row.update(
                    status="failed",
                    error=attempt["error"],
                    evidence=attempt["evidence"],
                    credential_echo_blocked=attempt["credential_echo_blocked"],
                )
            break
        if row["status"] != "completed":
            failed_cases.add(case_id)
        rows.append(row)

    records = directory / "records.jsonl"
    records.write_text(
        "".join(
            _canonical(
                {"metadata": prepared.metadata, "batch_id": batch_id, "record": row}
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
        "finished_at": utc_now().isoformat(),
        "free_tier_project_confirmed": True,
        "summary": summary,
        "artifacts": {"records": {"file": records.name, "sha256": _sha_file(records)}},
        "process_exit_code": summary["process_exit_code"],
    }
    summary_path = directory / "summary.json"
    summary_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    secret = ""
    api_key = SecretStr("")
    return document


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    _require(len(rows) == MAX_CASES, "gemini_free_rows_incomplete")
    calls = sum(
        sum(attempt.get("call_made") is True for attempt in row.get("attempts", []))
        for row in rows
    )
    retries = sum(row.get("transport_retry_count", 0) for row in rows)
    _require(calls <= MAX_PROVIDER_ATTEMPTS, "gemini_free_attempt_cap_exceeded")
    completed = sum(row["status"] == "completed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    skipped = sum(row["status"] == "skipped" for row in rows)
    categories = [
        row.get("error", {}).get("category")
        for row in rows
        if row.get("error") is not None
    ]
    usages = [
        row.get("evidence", {}).get("usage", {})
        for row in rows
        if row.get("status") == "completed"
    ]
    input_tokens = sum(
        value.get("input_tokens") or 0 for value in usages if isinstance(value, dict)
    )
    output_tokens = sum(
        value.get("output_tokens") or 0 for value in usages if isinstance(value, dict)
    )
    if "cancelled" in categories:
        code = 130
    elif any(
        category in {"local_error", "credential_echo_blocked", "target_mismatch"}
        for category in categories
    ):
        code = 3
    elif any(category not in CHAIN_LOCAL_ERRORS for category in categories):
        code = 2
    elif failed:
        code = 1
    else:
        code = 0
    return {
        "calls_made": calls,
        "transport_retries_made": retries,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "max_cases": MAX_CASES,
        "max_provider_attempts": MAX_PROVIDER_ATTEMPTS,
        "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
        "reported_input_tokens": input_tokens,
        "reported_output_tokens": output_tokens,
        "free_tier_project_confirmed": True,
        "paid_spend_authorized": False,
        "semantic_review_status": "not_performed",
        "qualified_candidates": [],
        "runtime_default_eligible": False,
        "process_exit_code": code,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    _require(path.stat().st_size <= MAX_ARTIFACT_BYTES, "gemini_free_records_too_large")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(
            line,
            object_pairs_hook=contract._unique_object,
            parse_constant=contract._reject_constant,
        )
        _require(isinstance(value, dict), "gemini_free_record_invalid")
        rows.append(value)
    return rows


def _expected_preflight(path: Path, expected_sha256: str) -> PreparedLive:
    _require(
        path.is_file() and _sha_file(path) == expected_sha256,
        "gemini_free_preflight_hash_invalid",
    )
    observed = contract._load_json(path)
    prepared = prepare_live()
    _require(observed == prepared.metadata, "gemini_free_preflight_drifted")
    return prepared


def verify_artifacts(
    summary_path: Path,
    expected_preflight: Path,
    batch_id: str,
    *,
    expected_preflight_sha256: str,
) -> dict[str, Any]:
    _batch(batch_id)
    prepared = _expected_preflight(expected_preflight, expected_preflight_sha256)
    expected_summary = run_path(batch_id) / "summary.json"
    _require(summary_path.resolve() == expected_summary.resolve() and summary_path.is_file())
    document = contract._load_json(summary_path)
    _require(
        document.get("metadata") == prepared.metadata
        and document.get("batch_id") == batch_id
        and document.get("free_tier_project_confirmed") is True,
        "gemini_free_summary_identity_invalid",
    )
    record_entry = document.get("artifacts", {}).get("records", {})
    records_path = summary_path.parent / record_entry.get("file", "")
    _require(
        records_path.parent == summary_path.parent
        and records_path.name == "records.jsonl"
        and records_path.is_file()
        and _sha_file(records_path) == record_entry.get("sha256"),
        "gemini_free_records_hash_invalid",
    )
    envelopes = _load_jsonl(records_path)
    _require(len(envelopes) == MAX_CASES, "gemini_free_record_count_invalid")
    rows: list[dict[str, Any]] = []
    prior_texts: dict[str, str] = {}
    failed_cases: set[str] = set()
    global_stop: str | None = None
    verified_calls = 0
    for envelope, scheduled in zip(
        envelopes, prepared.metadata["schedule"], strict=True
    ):
        _require(
            envelope.get("metadata") == prepared.metadata
            and envelope.get("batch_id") == batch_id
        )
        row = envelope.get("record")
        _require(
            isinstance(row, dict)
            and all(row.get(key) == value for key, value in scheduled.items())
        )
        prior_case_id = scheduled["prior_case_id"]
        expected_skip = None
        if global_stop is not None:
            expected_skip = f"global_{global_stop}"
        elif prior_case_id is not None and prior_case_id in failed_cases:
            expected_skip = "prior_case_failed"
        if expected_skip is not None:
            _require(
                row == {**scheduled, "status": "skipped", "reason": expected_skip},
                "gemini_free_skip_causality_invalid",
            )
            if expected_skip == "prior_case_failed":
                failed_cases.add(scheduled["case_id"])
            rows.append(row)
            continue

        _require(row.get("status") in {"completed", "failed"})
        attempts = row.get("attempts")
        _require(isinstance(attempts, list), "gemini_free_attempts_invalid")
        if not attempts:
            _require(
                row.get("status") == "failed"
                and row.get("call_made") is False
                and row.get("attempt_count") == 0
                and row.get("transport_retry_count") == 0
                and row.get("error")
                == {"category": "transport_retry_budget_exhausted"},
                "gemini_free_attempt_budget_record_invalid",
            )
            failed_cases.add(scheduled["case_id"])
            global_stop = "transport_retry_budget_exhausted"
            rows.append(row)
            continue
        _require(
            1 <= len(attempts) <= MAX_TRANSPORT_RETRIES_PER_CASE + 1
            and row.get("call_made") is True
            and row.get("attempt_count") == len(attempts)
            and row.get("transport_retry_count") == len(attempts) - 1,
            "gemini_free_attempt_count_invalid",
        )
        prior_invocation_id: str | None = None
        for attempt_index, attempt in enumerate(attempts):
            _require(
                isinstance(attempt, dict)
                and attempt.get("attempt_index") == attempt_index
                and attempt.get("retry_of_invocation_id") == prior_invocation_id
                and attempt.get("call_made") is True
                and attempt.get("status") in {"completed", "failed"},
                "gemini_free_attempt_identity_invalid",
            )
            verified_calls += 1
            _require(
                verified_calls <= MAX_PROVIDER_ATTEMPTS,
                "gemini_free_attempt_cap_exceeded",
            )
            request = _request(
                prepared,
                batch_id,
                scheduled["case_id"],
                prior_texts,
                attempt_index,
            )
            body = _request_body(request)
            capsule = _capsule(
                batch_id,
                scheduled["slot"],
                scheduled["case_id"],
                request,
                body,
                prior_texts,
                prior_case_id,
                attempt_index,
            )
            _require(
                attempt.get("capsule") == capsule
                and attempt.get("capsule_sha256") == _sha_value(capsule)
                and attempt.get("request", {}).get("operation") == request.operation
                and attempt.get("request", {}).get("invocation_id")
                == request.invocation_id
                and isinstance(attempt.get("request", {}).get("deadline"), str)
                and attempt.get("request", {}).get("body_sha256") == _sha_value(body),
                "gemini_free_attempt_capsule_link_invalid",
            )
            is_final = attempt_index == len(attempts) - 1
            if not is_final:
                error = attempt.get("error")
                _require(
                    attempt.get("status") == "failed"
                    and isinstance(error, dict)
                    and _is_strict_transport_retry(error)
                    and attempt.get("response") is None
                    and attempt.get("route_verified") is False
                    and attempt.get("credential_echo_blocked") is False
                    and attempt.get("retry_eligible") is True
                    and attempt.get("retry_scheduled") is True
                    and attempt.get("retry_delay_seconds")
                    == _transport_retry_delay(
                        batch_id, scheduled["slot"], attempt_index + 1
                    )
                    and attempt.get("retry_exhaustion_reason") is None,
                    "gemini_free_transport_retry_invalid",
                )
            else:
                _require(
                    attempt.get("retry_scheduled") is False
                    and attempt.get("retry_delay_seconds") is None,
                    "gemini_free_final_attempt_retry_invalid",
                )
                final_error = attempt.get("error")
                if isinstance(final_error, dict) and _is_strict_transport_retry(
                    final_error
                ):
                    expected_exhaustion = (
                        "per_case_retry_limit"
                        if len(attempts) == MAX_TRANSPORT_RETRIES_PER_CASE + 1
                        else "global_attempt_cap"
                    )
                    _require(
                        attempt.get("retry_eligible") is True
                        and attempt.get("retry_exhaustion_reason")
                        == expected_exhaustion
                        and (
                            expected_exhaustion != "global_attempt_cap"
                            or verified_calls == MAX_PROVIDER_ATTEMPTS
                        ),
                        "gemini_free_retry_exhaustion_invalid",
                    )
                else:
                    _require(
                        attempt.get("retry_exhaustion_reason") is None,
                        "gemini_free_unexpected_retry_exhaustion",
                    )
            prior_invocation_id = request.invocation_id
        final_attempt = attempts[-1]
        if row["status"] == "completed":
            response = row.get("response")
            _require(
                final_attempt.get("status") == "completed"
                and final_attempt.get("response") == response
                and final_attempt.get("evidence") == row.get("evidence")
                and final_attempt.get("route_verified") is True
                and final_attempt.get("error") is None
                and row.get("route_verified") is True
                and isinstance(response, dict)
                and isinstance(response.get("n"), str)
                and isinstance(response.get("q"), str)
                and row.get("error") is None
                and row.get("credential_echo_blocked") is False
                and _route_verified(row.get("evidence"), prepared.target),
                "gemini_free_completed_record_invalid",
            )
            prior_texts[scheduled["case_id"]] = f"{response['n']}\n\n{response['q']}"
        else:
            error = row.get("error")
            _require(
                final_attempt.get("status") == "failed"
                and final_attempt.get("error") == error
                and final_attempt.get("evidence") == row.get("evidence")
                and isinstance(error, dict)
                and isinstance(error.get("category"), str),
                "gemini_free_failed_record_invalid",
            )
            failed_cases.add(scheduled["case_id"])
            if error["category"] not in CHAIN_LOCAL_ERRORS:
                global_stop = error["category"]
        rows.append(row)
    reconstructed = summarize(rows)
    _require(
        document.get("summary") == reconstructed
        and document.get("process_exit_code") == reconstructed["process_exit_code"],
        "gemini_free_summary_reconstruction_failed",
    )
    return {
        "verified": True,
        "batch_id": batch_id,
        "process_exit_code": reconstructed["process_exit_code"],
        "summary_path": str(summary_path.resolve()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--verify-artifacts", type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env", choices=(KEY_ENV,), default=KEY_ENV)
    parser.add_argument("--allow-synthetic-only", action="store_true")
    parser.add_argument("--confirm-free-tier-project", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            _require(
                args.batch_id is None
                and args.expected_preflight is None
                and args.expected_preflight_sha256 is None
                and not args.allow_synthetic_only
                and not args.confirm_free_tier_project
            )
            print(json.dumps(prepare_live().metadata, ensure_ascii=False, indent=2))
            return 0
        _batch(args.batch_id)
        _require(
            args.expected_preflight is not None
            and args.expected_preflight_sha256 is not None
        )
        if args.verify_artifacts is not None:
            _require(not args.allow_synthetic_only and not args.confirm_free_tier_project)
            result = verify_artifacts(
                args.verify_artifacts,
                args.expected_preflight,
                args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        _require(
            args.live and args.allow_synthetic_only and args.confirm_free_tier_project,
            "gemini_free_live_opt_in_missing",
        )
        prepared = _expected_preflight(
            args.expected_preflight, args.expected_preflight_sha256
        )
        secret = os.environ.get(args.api_key_env, "").strip()
        if not secret:
            print("gemini_free_credential_missing", file=sys.stderr)
            return 3
        document = asyncio.run(
            run_live(
                prepared,
                api_key=SecretStr(secret),
                batch_id=args.batch_id,
                run_directory=run_path(args.batch_id),
                free_tier_project_confirmed=True,
            )
        )
        return int(document["process_exit_code"])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"gemini_free_fail_closed:{type(exc).__name__}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
