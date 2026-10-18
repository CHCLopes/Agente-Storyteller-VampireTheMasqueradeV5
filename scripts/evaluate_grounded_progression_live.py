"""Bounded live runner for HYP-001; preflight and verification are keyless."""

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
import sys
from typing import Any
from uuid import UUID, uuid5


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr

from api.llm.adapters.groq import GROQ_OFFICIAL_BASE_URL, GroqAdapter
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
from scripts import evaluate_grounded_progression_contract as offline
from scripts import evaluate_narrator_models as shared
from scripts import narrator_source_profile as source_profile


VERSION = "grounded-progression-live-v1"
KEY_ENV = "STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY"
OUTPUT_ROOT = ROOT / "eval-results"
MANIFEST = ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
LIVE_GATE = ROOT / "evals/narrator/reports/grounded-progression-live-gate-2026-09-22.json"
MAX_CALLS = 16
MAX_OUTPUT_TOKENS = 768
MAX_TOTAL_OUTPUT_TOKENS = MAX_CALLS * MAX_OUTPUT_TOKENS
DEADLINE_SECONDS = 60
MINIMUM_INTERVAL_SECONDS = 60
TEMPERATURE = 0.65
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024

QWEN_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"
GPT_ID = "gpt-oss-120b-groq-free-synthetic-low"
CANDIDATE_IDS = (QWEN_ID, GPT_ID)
TARGETS = {
    QWEN_ID: {
        "profile": "grounded-progression-qwen-3.8-27b-none",
        "model": "qwen/qwen3.8-27b",
        "reasoning": "none",
    },
    GPT_ID: {
        "profile": "grounded-progression-gpt-oss-120b-low",
        "model": "openai/gpt-oss-120b",
        "reasoning": "low",
    },
}
SCHEDULE = (
    (QWEN_ID, "wait-without-authorized-progression"),
    (QWEN_ID, "wait-with-authorized-event"),
    (GPT_ID, "wait-without-authorized-progression"),
    (GPT_ID, "wait-with-authorized-event"),
    (QWEN_ID, "known-object-state"),
    (GPT_ID, "known-object-state"),
    (GPT_ID, "unknown-object-state"),
    (QWEN_ID, "unknown-object-state"),
    (QWEN_ID, "favorable-mechanical-result"),
    (GPT_ID, "favorable-mechanical-result"),
    (GPT_ID, "unfavorable-mechanical-result"),
    (QWEN_ID, "unfavorable-mechanical-result"),
    (QWEN_ID, "npc-protected-secret"),
    (GPT_ID, "npc-protected-secret"),
    (GPT_ID, "ambiguous-action-preserves-choice"),
    (QWEN_ID, "ambiguous-action-preserves-choice"),
)
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


def _require(condition: bool, code: str = "grounded_progression_live_invalid") -> None:
    if not condition:
        raise ValueError(code)


def _batch(value: str) -> str:
    parsed = UUID(value)
    _require(str(parsed) == value and parsed.version == 4, "live_batch_invalid")
    return value


def run_path(batch_id: str) -> Path:
    return OUTPUT_ROOT / f"grounded-progression-{_batch(batch_id)}"


@dataclass(frozen=True)
class PreparedLive:
    candidates: dict[str, Any]
    targets: dict[str, LLMTarget]
    corpus: dict[str, Any]
    system_prompt: str
    metadata: dict[str, Any]


def _candidate_metadata(candidate: Any, target: LLMTarget) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "provider": candidate.provider_label,
        "model": candidate.model,
        "reasoning_effort": candidate.reasoning_effort,
        "target": target.model_dump(mode="json"),
    }


def _schedule_metadata(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    cases = {case["case_id"]: case for case in corpus["cases"]}
    return [
        {
            "slot": index,
            "candidate_id": candidate_id,
            "case_id": case_id,
            "prior_case_id": cases[case_id]["prior_case_id"],
        }
        for index, (candidate_id, case_id) in enumerate(SCHEDULE)
    ]


def prepare_live() -> PreparedLive:
    offline_preflight = offline.prepare_protocol()
    corpus = offline.validate_corpus(offline._load_json(offline.CORPUS))
    gate = offline._load_json(LIVE_GATE)
    _require(
        gate.get("recommended_option") == "L1"
        and gate.get("live_inference_authorized") is True
        and gate.get("credential_status") in {"pending", "available_protected"}
        and gate.get("provider_calls_at_gate_creation") == 0,
        "live_gate_drifted",
    )
    candidates = shared.load_candidates(MANIFEST)
    selected: dict[str, Any] = {}
    targets: dict[str, LLMTarget] = {}
    for candidate_id in CANDIDATE_IDS:
        candidate = candidates[candidate_id]
        expected = TARGETS[candidate_id]
        _require(
            candidate.adapter_kind == "groq"
            and candidate.provider_label == "Groq"
            and candidate.effective_provider == "Groq"
            and candidate.upstream_provider is None
            and candidate.structured_mode == "native"
            and candidate.model == expected["model"]
            and candidate.reasoning_effort == expected["reasoning"]
            and candidate.campaign_data_eligible is False,
            "live_candidate_invalid",
        )
        target = LLMTarget(
            profile=expected["profile"], provider="Groq", model=expected["model"]
        )
        selected[candidate_id], targets[candidate_id] = candidate, target

    schedule = _schedule_metadata(corpus)
    _require(len(schedule) == MAX_CALLS and len(set(SCHEDULE)) == MAX_CALLS)
    implementation = (
        "scripts/evaluate_grounded_progression_live.py",
        "scripts/evaluate_grounded_progression_contract.py",
        "scripts/narrator_source_profile.py",
        "scripts/evaluate_narrator_models.py",
        "api/llm/adapters/groq.py",
        "api/llm/adapters/openai_compatible.py",
        "api/llm/contract.py",
    )
    metadata = {
        "purpose": "grounded_progression_live_comparison",
        "version": VERSION,
        "hypothesis_id": "grounded_progression_contract_v1",
        "option": "L1",
        "synthetic_only": True,
        "campaign_data_eligible": False,
        "max_calls": MAX_CALLS,
        "automatic_retries": 0,
        "repair": False,
        "fallback": False,
        "paid_spend_authorized": False,
        "human_review_required": True,
        "runtime_default_eligible": False,
        "generation_parameters": {
            "temperature": TEMPERATURE,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
            "deadline_seconds": DEADLINE_SECONDS,
            "minimum_global_start_interval_seconds": MINIMUM_INTERVAL_SECONDS,
        },
        "selected_candidates": [
            _candidate_metadata(selected[candidate_id], targets[candidate_id])
            for candidate_id in CANDIDATE_IDS
        ],
        "schedule": schedule,
        "inputs": {
            "offline_preflight": offline_preflight,
            "candidate_manifest": {
                "file": MANIFEST.relative_to(ROOT).as_posix(),
                "sha256": _sha_file(MANIFEST),
            },
            "live_gate": {
                "file": LIVE_GATE.relative_to(ROOT).as_posix(),
                "sha256": _sha_file(LIVE_GATE),
            },
            "response_schema_sha256": _sha_value(
                source_profile.NarrativeSourceProposal.model_json_schema()
            ),
            "implementation": [
                {"file": name, "sha256": _sha_file(ROOT / name)}
                for name in implementation
            ],
        },
        "provider_calls": 0,
        "credential_inspected": False,
        "live_execution_requires_cli_opt_in": True,
    }
    return PreparedLive(selected, targets, corpus, offline.render_system_prompt(), metadata)


def _check_prepared(prepared: PreparedLive) -> None:
    current = prepare_live()
    _require(type(prepared) is PreparedLive and _canonical(prepared.metadata) == _canonical(current.metadata))
    _require(prepared.system_prompt == current.system_prompt)


def _case(prepared: PreparedLive, case_id: str) -> dict[str, Any]:
    return next(case for case in prepared.corpus["cases"] if case["case_id"] == case_id)


def _invocation_id(batch_id: str, candidate_id: str, case_id: str) -> str:
    return str(uuid5(UUID(_batch(batch_id)), f"{VERSION}.{candidate_id}.{case_id}"))


def _payload_for_case(
    prepared: PreparedLive,
    candidate_id: str,
    case_id: str,
    prior_texts: dict[tuple[str, str], str],
) -> dict[str, Any]:
    case = _case(prepared, case_id)
    payload = offline.render_case_payload(case)
    prior_case_id = case["prior_case_id"]
    if prior_case_id is not None:
        key = (candidate_id, prior_case_id)
        _require(key in prior_texts, "live_prior_source_missing")
        payload["attributed_source"] = {
            "case_id": prior_case_id,
            "content": prior_texts[key],
        }
    return payload


def _request(
    prepared: PreparedLive,
    batch_id: str,
    candidate_id: str,
    case_id: str,
    prior_texts: dict[tuple[str, str], str],
) -> StructuredGenerationRequest:
    payload = _payload_for_case(prepared, candidate_id, case_id, prior_texts)
    return StructuredGenerationRequest(
        invocation_id=_invocation_id(batch_id, candidate_id, case_id),
        operation=f"{VERSION}.{candidate_id}.{case_id}",
        target=prepared.targets[candidate_id],
        messages=(
            LLMMessage(role=MessageRole.SYSTEM, content=prepared.system_prompt),
            LLMMessage(role=MessageRole.USER, content=_canonical(payload)),
        ),
        deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
        cancellation=CancellationToken(),
        parameters=GenerationParameters(
            temperature=TEMPERATURE, max_output_tokens=MAX_OUTPUT_TOKENS
        ),
        response_model=source_profile.NarrativeSourceProposal,
        required_capabilities=(
            CapabilityRequirement(name=CAPABILITY_TEXT_GENERATION),
            CapabilityRequirement(
                name=CAPABILITY_STRUCTURED_GENERATION, allow_emulated=False
            ),
        ),
    )


def _request_body(request: StructuredGenerationRequest, reasoning: str) -> dict[str, Any]:
    builder = object.__new__(GroqAdapter)
    builder._reasoning_effort = reasoning
    return GroqAdapter._payload(
        builder,
        request,
        stream=False,
        response_format=builder._native_response_format(request),
    )


def _capsule(
    batch_id: str,
    slot: int,
    candidate_id: str,
    case_id: str,
    request: StructuredGenerationRequest,
    body: dict[str, Any],
    prior_texts: dict[tuple[str, str], str],
    prior_case_id: str | None,
) -> dict[str, Any]:
    prior = prior_texts.get((candidate_id, prior_case_id)) if prior_case_id else None
    return {
        "protocol": VERSION,
        "batch_id": batch_id,
        "slot": slot,
        "candidate_id": candidate_id,
        "case_id": case_id,
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
    return (
        requested == target.model_dump(mode="json")
        and isinstance(model, dict)
        and model.get("value") == target.model
        and model.get("source") == "reported"
        and isinstance(provider, dict)
        and provider.get("value") == "Groq"
        and provider.get("source") in {"reported", "observed"}
    )


class DispatchBudget:
    def __init__(self, pacer: Any | None = None) -> None:
        self.calls = 0
        self.pacer = pacer or shared._CallPacer(MINIMUM_INTERVAL_SECONDS)

    async def before_call(self, label: str) -> None:
        _require(self.calls < MAX_CALLS, "live_call_budget_exhausted")
        await self.pacer.before_call(label)
        self.calls += 1


def _row_identity(slot: int, candidate_id: str, case_id: str, prior_case_id: str | None) -> dict[str, Any]:
    return {
        "slot": slot,
        "candidate_id": candidate_id,
        "case_id": case_id,
        "prior_case_id": prior_case_id,
    }


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
    pacer: Any | None = None,
) -> dict[str, Any]:
    _batch(batch_id)
    _check_prepared(prepared)
    secret = api_key.get_secret_value().strip() if type(api_key) is SecretStr else ""
    _require(bool(secret), "live_credential_invalid")
    _require(secret not in _canonical(prepared.metadata), "live_credential_conflict")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve(), "live_run_path_invalid")
    directory.mkdir(parents=True, exist_ok=False)
    budget = DispatchBudget(pacer)
    prior_texts: dict[tuple[str, str], str] = {}
    failed_cases: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    global_stop: str | None = None
    started_at = utc_now().isoformat()

    for slot, (candidate_id, case_id) in enumerate(SCHEDULE):
        case = _case(prepared, case_id)
        identity = _row_identity(slot, candidate_id, case_id, case["prior_case_id"])
        if global_stop is not None:
            rows.append({**identity, "status": "skipped", "reason": f"global_{global_stop}"})
            continue
        if case["prior_case_id"] is not None and (
            candidate_id, case["prior_case_id"]
        ) in failed_cases:
            rows.append({**identity, "status": "skipped", "reason": "prior_case_failed"})
            failed_cases.add((candidate_id, case_id))
            continue

        request = _request(prepared, batch_id, candidate_id, case_id, prior_texts)
        reasoning = TARGETS[candidate_id]["reasoning"]
        body = _request_body(request, reasoning)
        capsule = _capsule(
            batch_id, slot, candidate_id, case_id, request, body, prior_texts,
            case["prior_case_id"],
        )
        row: dict[str, Any] = {
            **identity,
            "status": "pending",
            "call_made": False,
            "capsule": capsule,
            "capsule_sha256": _sha_value(capsule),
            "request": {
                "operation": request.operation,
                "invocation_id": request.invocation_id,
                "deadline": request.deadline.isoformat(),
                "body_sha256": _sha_value(body),
            },
            "response": None,
            "evidence": None,
            "error": None,
            "route_verified": False,
            "credential_echo_blocked": False,
        }
        try:
            await budget.before_call(f"HYP-001 slot {slot + 1}/{MAX_CALLS}")
            dispatch_request = _request(
                prepared, batch_id, candidate_id, case_id, prior_texts
            )
            dispatch_body = _request_body(dispatch_request, reasoning)
            dispatch_capsule = _capsule(
                batch_id, slot, candidate_id, case_id, dispatch_request,
                dispatch_body, prior_texts, case["prior_case_id"],
            )
            _require(
                dispatch_capsule == capsule,
                "live_dispatch_capsule_drifted",
            )
            request = dispatch_request
            row["request"]["deadline"] = request.deadline.isoformat()
            row["call_made"] = True
            candidate = prepared.candidates[candidate_id]
            adapter = GroqAdapter(
                base_url=GROQ_OFFICIAL_BASE_URL,
                capability_set=shared._capabilities(candidate, request.target),
                api_key=api_key,
                reasoning_effort=reasoning,
            )
            result = await adapter.generate_structured(request)
            response = result.value.model_dump(mode="json", by_alias=True)
            evidence = result.evidence.model_dump(mode="json")
            if _contains_secret({"response": response, "evidence": evidence}, secret):
                row.update(
                    status="failed", credential_echo_blocked=True,
                    error={"category": "credential_echo_blocked"},
                )
                global_stop = "credential_echo_blocked"
            elif not _route_verified(evidence, request.target):
                row.update(status="failed", error={"category": "target_mismatch"})
                global_stop = "target_mismatch"
            else:
                text = f"{response['n']}\n\n{response['q']}"
                row.update(
                    status="completed", response=response, evidence=evidence,
                    route_verified=True,
                )
                prior_texts[(candidate_id, case_id)] = text
        except asyncio.CancelledError:
            row.update(status="failed", error={"category": "cancelled"})
            global_stop = "cancelled"
        except LLMInvocationError as exc:
            error = _safe_error(exc.error)
            if _contains_secret(error, secret):
                row.update(
                    status="failed", credential_echo_blocked=True,
                    error={"category": "credential_echo_blocked"},
                )
                global_stop = "credential_echo_blocked"
            else:
                category = error["category"]
                row.update(status="failed", error=error, evidence=error.get("evidence"))
                if category not in CHAIN_LOCAL_ERRORS:
                    global_stop = category
        except Exception:
            row.update(status="failed", error={"category": "local_error"})
            global_stop = "local_error"
        if row["status"] != "completed":
            failed_cases.add((candidate_id, case_id))
        rows.append(row)

    records = directory / "records.jsonl"
    records.write_text(
        "".join(_canonical({"metadata": prepared.metadata, "batch_id": batch_id, "record": row}) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = summarize(rows)
    document = {
        "metadata": prepared.metadata,
        "batch_id": batch_id,
        "started_at": started_at,
        "finished_at": utc_now().isoformat(),
        "summary": summary,
        "artifacts": {"records": {"file": records.name, "sha256": _sha_file(records)}},
        "process_exit_code": summary["process_exit_code"],
    }
    summary_path = directory / "summary.json"
    summary_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    secret = ""
    api_key = SecretStr("")
    return document


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    _require(len(rows) == MAX_CALLS, "live_rows_incomplete")
    calls = sum(row.get("call_made") is True for row in rows)
    completed = sum(row["status"] == "completed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    skipped = sum(row["status"] == "skipped" for row in rows)
    categories = [
        row.get("error", {}).get("category")
        for row in rows if row.get("error") is not None
    ]
    if "cancelled" in categories:
        code = 130
    elif any(category in {"local_error", "credential_echo_blocked", "target_mismatch"} for category in categories):
        code = 3
    elif any(category not in CHAIN_LOCAL_ERRORS for category in categories):
        code = 2
    elif failed:
        code = 1
    else:
        code = 0
    return {
        "calls_made": calls,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "max_calls": MAX_CALLS,
        "max_total_output_tokens": MAX_TOTAL_OUTPUT_TOKENS,
        "semantic_review_status": "not_performed",
        "qualified_candidates": [],
        "runtime_default_eligible": False,
        "process_exit_code": code,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    _require(path.stat().st_size <= MAX_ARTIFACT_BYTES, "live_records_too_large")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(
            line, object_pairs_hook=offline._unique_object,
            parse_constant=offline._reject_constant,
        )
        _require(isinstance(value, dict), "live_record_invalid")
        rows.append(value)
    return rows


def _expected_preflight(path: Path, expected_sha256: str) -> PreparedLive:
    _require(path.is_file() and _sha_file(path) == expected_sha256, "live_preflight_hash_invalid")
    observed = offline._load_json(path)
    prepared = prepare_live()
    _require(observed == prepared.metadata, "live_preflight_drifted")
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
    originals = {summary_path: _sha_file(summary_path)}
    document = offline._load_json(summary_path)
    _require(
        document.get("metadata") == prepared.metadata
        and document.get("batch_id") == batch_id,
        "live_summary_identity_invalid",
    )
    record_entry = document.get("artifacts", {}).get("records", {})
    records_path = summary_path.parent / record_entry.get("file", "")
    _require(
        records_path.parent == summary_path.parent
        and records_path.name == "records.jsonl"
        and records_path.is_file()
        and _sha_file(records_path) == record_entry.get("sha256"),
        "live_records_hash_invalid",
    )
    originals[records_path] = _sha_file(records_path)
    envelopes = _load_jsonl(records_path)
    _require(len(envelopes) == MAX_CALLS, "live_record_count_invalid")
    rows: list[dict[str, Any]] = []
    prior_texts: dict[tuple[str, str], str] = {}
    failed_cases: set[tuple[str, str]] = set()
    global_stop: str | None = None
    for slot, (envelope, scheduled) in enumerate(zip(envelopes, prepared.metadata["schedule"], strict=True)):
        _require(envelope.get("metadata") == prepared.metadata and envelope.get("batch_id") == batch_id)
        row = envelope.get("record")
        _require(isinstance(row, dict) and all(row.get(key) == value for key, value in scheduled.items()))
        expected_skip: str | None = None
        if global_stop is not None:
            expected_skip = f"global_{global_stop}"
        elif scheduled["prior_case_id"] is not None and (
            scheduled["candidate_id"], scheduled["prior_case_id"]
        ) in failed_cases:
            expected_skip = "prior_case_failed"

        if expected_skip is not None:
            _require(
                row == {**scheduled, "status": "skipped", "reason": expected_skip},
                "live_skip_causality_invalid",
            )
            if expected_skip == "prior_case_failed":
                failed_cases.add((scheduled["candidate_id"], scheduled["case_id"]))
            rows.append(row)
            continue

        _require(row.get("status") in {"completed", "failed"}, "live_record_status_invalid")
        request = _request(
            prepared, batch_id, scheduled["candidate_id"], scheduled["case_id"],
            prior_texts,
        )
        body = _request_body(request, TARGETS[scheduled["candidate_id"]]["reasoning"])
        expected_capsule = _capsule(
            batch_id, slot, scheduled["candidate_id"], scheduled["case_id"],
            request, body, prior_texts, scheduled["prior_case_id"],
        )
        capsule = row.get("capsule")
        _require(
            capsule == expected_capsule
            and row.get("capsule_sha256") == _sha_value(expected_capsule)
            and row.get("request", {}).get("operation") == request.operation
            and row.get("request", {}).get("body_sha256") == expected_capsule["body_sha256"]
            and row.get("request", {}).get("invocation_id") == expected_capsule["invocation_id"],
            "live_capsule_link_invalid",
        )

        if row["status"] == "completed":
            response = row.get("response")
            _require(
                row.get("call_made") is True
                and row.get("route_verified") is True
                and isinstance(response, dict)
                and isinstance(response.get("n"), str)
                and isinstance(response.get("q"), str)
                and row.get("evidence") is not None
                and row.get("error") is None
                and row.get("credential_echo_blocked") is False,
                "live_completed_record_invalid",
            )
            _require(_route_verified(row["evidence"], prepared.targets[row["candidate_id"]]))
            prior_texts[(scheduled["candidate_id"], scheduled["case_id"])] = (
                f"{response['n']}\n\n{response['q']}"
            )
        elif row["status"] == "failed":
            error = row.get("error")
            _require(isinstance(error, dict) and isinstance(error.get("category"), str))
            category = error["category"]
            _require(
                row.get("call_made") is True
                or (row.get("call_made") is False and category == "cancelled"),
                "live_failed_dispatch_state_invalid",
            )
            failed_cases.add((scheduled["candidate_id"], scheduled["case_id"]))
            if category not in CHAIN_LOCAL_ERRORS:
                global_stop = category
        else:
            raise ValueError("live_record_status_invalid")
        rows.append(row)
    summary = summarize(rows)
    _require(
        document.get("summary") == summary
        and document.get("process_exit_code") == summary["process_exit_code"],
        "live_summary_reconstruction_failed",
    )
    _require(all(_sha_file(path) == digest for path, digest in originals.items()))
    return {
        "verified": True,
        "batch_id": batch_id,
        "process_exit_code": summary["process_exit_code"],
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
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            _require(
                args.batch_id is None and args.expected_preflight is None
                and args.expected_preflight_sha256 is None
                and not args.allow_synthetic_only
            )
            print(json.dumps(prepare_live().metadata, ensure_ascii=False, indent=2))
            return 0
        _batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts is not None:
            _require(not args.allow_synthetic_only)
            print(json.dumps(verify_artifacts(
                args.verify_artifacts, args.expected_preflight, args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256,
            ), ensure_ascii=False, indent=2))
            return 0
        _require(args.live and args.allow_synthetic_only)
        prepared = _expected_preflight(args.expected_preflight, args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists(), "live_run_exists")
    except Exception:
        print("grounded_progression_live_preflight_or_verification_failed", file=sys.stderr)
        return 3
    raw_key = os.environ.get(KEY_ENV, "").strip()
    if not raw_key:
        print("grounded_progression_live_credential_missing", file=sys.stderr)
        return 3
    key = SecretStr(raw_key)
    raw_key = ""
    try:
        document = asyncio.run(run_live(
            prepared, api_key=key, batch_id=args.batch_id,
            run_directory=run_path(args.batch_id),
        ))
        print(json.dumps({
            "summary_path": str((run_path(args.batch_id) / "summary.json").resolve()),
            "process_exit_code": document["process_exit_code"],
        }, ensure_ascii=False))
        return document["process_exit_code"]
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("grounded_progression_live_local_failure", file=sys.stderr)
        return 3
    finally:
        key = SecretStr("")


if __name__ == "__main__":
    raise SystemExit(main())
