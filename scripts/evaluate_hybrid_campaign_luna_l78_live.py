"""Paid-gated HYP-007 campaign evaluator; synthetic sessions only.

Preflight is keyless. Live stays disabled until both gate booleans are changed
after explicit human approval. No retry, fallback, alternate target or admission.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
from decimal import Decimal
import gc
import hashlib
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter
from uuid import UUID, uuid4

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

import httpx
from pydantic import SecretStr

from api import rules_service
from api.campaign_source_capsule import CampaignSourceConfig
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_profile import CampaignSourceProposal
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor, CapabilitySet, CapabilitySupport,
    GenerationParameters, LLMInvocationError, utc_now,
)
from api.persistence import SQLitePersistence
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter
from scripts.preflight_hybrid_campaign_luna_l78 import (
    CASES, DEADLINE_SECONDS, MAX_CALLS, MAX_OUTPUT_TOKENS,
    MAX_REQUEST_BYTES, PROMPT, ROOT, TARGET, _fixed_resolution, preflight,
)
from scripts.report_luna_test_cost import display, read_records, summarize
from scripts.run_campaign_source_offline_trial import _initial_state


GATE = ROOT / "evals/narrator/reports/hybrid-campaign-luna-l78-live-gate-2026-10-20.json"
OUTPUT_ROOT = ROOT / "eval-results"
LOT_ID = "HYP-007-L78"
LOT_PREFIX = "hybrid-campaign-luna-l78-"
LOT_LOCK = OUTPUT_ROOT / "hybrid-campaign-luna-l78-once"
KEY_ENV = "STORYTELLER_OPENAI_HYP007_L78_KEY"
PRICE_INPUT = Decimal("0.20")
PRICE_OUTPUT = Decimal("1.20")
PROPOSED_LIMIT = Decimal("0.15")
FROZEN_FILES = (
    "scripts/evaluate_hybrid_campaign_luna_l78_live.py",
    "scripts/run_hybrid_campaign_luna_l78_live.ps1",
    "scripts/preflight_hybrid_campaign_luna_l78.py",
    "scripts/evaluate_openai_luna_low_live.py",
    "scripts/report_luna_test_cost.py",
    "api/campaign_progression_catalog.py",
    "api/campaign_progression_service.py",
    "api/campaign_source_capsule.py",
    "api/campaign_source_context.py",
    "api/campaign_source_execution_service.py",
    "api/campaign_source_input_service.py",
    "api/campaign_source_profile.py",
    "api/campaign_source_preparation.py",
    "api/campaign_source_turn.py",
    "api/campaign_source_offline_corpus.py",
    "scripts/run_campaign_source_offline_trial.py",
    "api/local_request_security.py",
    "api/campaign_source_storage.py",
    "api/scene_director_service.py",
    "api/llm/contract.py",
    "api/persistence.py",
    "api/rules_service.py",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _gate() -> dict:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    expected = {
        "hypothesis_id": "HYP-007", "lot_id": LOT_ID,
        "target_model": TARGET.model,
        "reasoning_effort": "low", "max_calls": MAX_CALLS,
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS,
        "max_request_bytes": MAX_REQUEST_BYTES,
        "max_estimated_usd": str(PROPOSED_LIMIT),
        "admission_automatic": False,
        "retry": False,
        "fallback": False,
        "synthetic_only": True,
        "content_version": "record-at-risk.v2",
        "policy_version": "campaign-progression.v2",
        "input_usd_per_million_tokens": str(PRICE_INPUT),
        "output_usd_per_million_tokens": str(PRICE_OUTPUT),
    }
    if any(gate.get(key) != value for key, value in expected.items()):
        raise ValueError("campaign_luna_gate_drifted")
    if gate.get("prompt_sha256") != _sha(PROMPT.read_bytes()):
        raise ValueError("campaign_luna_prompt_drifted")
    frozen = gate.get("implementation_sha256")
    if type(frozen) is not dict or set(frozen) != set(FROZEN_FILES):
        raise ValueError("campaign_luna_manifest_missing")
    if any(frozen[name] != _sha((ROOT / name).read_bytes()) for name in FROZEN_FILES):
        raise ValueError("campaign_luna_implementation_drifted")
    return gate


def _require_live_gate(gate: dict) -> None:
    if gate.get("paid_ceiling_authorized") is not True or gate.get("live_inference_authorized") is not True:
        raise ValueError("campaign_luna_paid_authorization_missing")


class BoundedAdapter:
    """One request per slot, with a local body and cost guard before dispatch."""

    def __init__(self, adapter: OpenAIResponsesAdapter, *, case_id: str,
                 turn: int, spent: Decimal, key: SecretStr) -> None:
        self.adapter, self.spent, self.key = adapter, spent, key
        self.row = {
            "case_id": case_id, "turn": turn, "call_made": False,
            "status": "not_dispatched", "request_bytes": None,
            "request_sha256": None, "evidence": None,
            "response": None, "error_code": None, "generation_ms": None,
        }

    async def generate_structured(self, request):
        if self.row["call_made"]:
            raise ValueError("campaign_luna_duplicate_dispatch")
        if (request.target != TARGET or request.response_model is not CampaignSourceProposal
                or request.parameters.max_output_tokens != MAX_OUTPUT_TOKENS
                or request.parameters.temperature is not None):
            raise ValueError("campaign_luna_request_drifted")
        body = self.adapter._payload(
            request, stream=False,
            response_format=self.adapter._native_response_format(request),
        )
        if (body.get("model") != TARGET.model or body.get("store") is not False
                or body.get("stream") is not False
                or body.get("reasoning") != {"effort": "low"} or body.get("tools")
                or body.get("max_output_tokens") != MAX_OUTPUT_TOKENS):
            raise ValueError("campaign_luna_body_drifted")
        encoded = httpx.Request("POST", "https://api.openai.com/v1/responses",
                                json=body).content
        if len(encoded) > MAX_REQUEST_BYTES:
            raise ValueError("campaign_luna_request_too_large")
        # UTF-8 bytes are used as a deliberately conservative input-token proxy.
        # This is a local guard, not a billing guarantee; the account limit is separate.
        worst_next = (Decimal(len(encoded)) * PRICE_INPUT
                      + Decimal(MAX_OUTPUT_TOKENS) * PRICE_OUTPUT) / Decimal(1_000_000)
        if self.spent + worst_next > PROPOSED_LIMIT:
            raise ValueError("campaign_luna_budget_exhausted")
        gate = _gate()
        _require_live_gate(gate)
        if _sha(PROMPT.read_bytes()) != gate["prompt_sha256"]:
            raise ValueError("campaign_luna_prompt_drifted")
        self.row["request_bytes"] = len(encoded)
        self.row["request_sha256"] = _sha(encoded)
        print(f"Calling provider: {LOT_ID} {self.row['case_id']} turn {self.row['turn']}", flush=True)
        self.row["call_made"] = True
        self.row["status"] = "dispatched"
        started = perf_counter()
        try:
            response = await self.adapter.generate_structured(request)
        except LLMInvocationError as exc:
            self.row["generation_ms"] = round((perf_counter() - started) * 1000)
            self.row["status"] = "provider_error"
            self.row["error_code"] = exc.error.code
            self.row["evidence"] = exc.error.evidence.model_dump(mode="json") if exc.error.evidence else None
            raise
        except Exception:
            self.row["generation_ms"] = round((perf_counter() - started) * 1000)
            self.row["status"] = "transport_unknown"
            self.row["error_code"] = "unclassified_transport_error"
            raise
        self.row["generation_ms"] = round((perf_counter() - started) * 1000)
        evidence = response.evidence.model_dump(mode="json")
        self.row["evidence"] = evidence
        provenance = evidence.get("provenance", {})
        if (provenance.get("requested_target") != TARGET.model_dump(mode="json")
                or provenance.get("effective_provider", {}).get("value") != "OpenAI"
                or provenance.get("effective_provider", {}).get("source") != "observed"
                or provenance.get("effective_model", {}).get("value") != TARGET.model
                or provenance.get("effective_model", {}).get("source") != "reported"):
            self.row["status"] = "route_mismatch"
            raise ValueError("campaign_luna_route_mismatch")
        value = response.value.model_dump(mode="json", by_alias=True)
        secret = self.key.get_secret_value()
        if len(secret) >= 12 and secret in json.dumps(value, ensure_ascii=False):
            self.row["status"] = "credential_echo_blocked"
            raise ValueError("campaign_luna_credential_echo_blocked")
        self.row["response"] = value
        self.row["status"] = "generated"
        return response


class CampaignLunaAdapter(OpenAIResponsesAdapter):
    """OpenAI strict schema; retain stricter Pydantic validation after response."""

    def _native_response_format(self, request):
        result = super()._native_response_format(request)
        schema = result["schema"]
        schema["required"] = list(schema["properties"])
        schema["properties"]["protocol"].pop("default", None)
        return result


def _usage_cost(row: dict) -> Decimal | None:
    usage = (row.get("evidence") or {}).get("usage") or {}
    incoming, outgoing = usage.get("input_tokens"), usage.get("output_tokens")
    if any(type(value) is not int or value < 0 for value in (incoming, outgoing)):
        return None
    return (Decimal(incoming) * PRICE_INPUT + Decimal(outgoing) * PRICE_OUTPUT) / Decimal(1_000_000)


async def run_batch(*, directory: Path, key: SecretStr,
                    adapter_factory=None) -> dict:
    """Run once. Tests inject a fake adapter; production uses OpenAI only."""
    if adapter_factory is None:
        _require_live_gate(_gate())
        # A distinct, atomic latch prevents concurrent or accidental repeat L78 lots.
        LOT_LOCK.mkdir(parents=True, exist_ok=False)
    if directory.exists():
        raise ValueError("campaign_luna_batch_exists")
    directory.mkdir(parents=True)
    records = directory / "records.jsonl"
    prompt = PROMPT.read_text(encoding="utf-8").strip()
    config = CampaignSourceConfig(
        target=TARGET, system_prompt=prompt,
        parameters=GenerationParameters(max_output_tokens=MAX_OUTPUT_TOKENS),
        chronicle_name="Registro em risco — HYP-007 sintético",
    )
    caps = CapabilitySet(target=TARGET, descriptors=tuple(CapabilityDescriptor(
        name=name, support=CapabilitySupport.NATIVE,
    ) for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)))
    rows: list[dict] = []
    spent = Decimal(0)
    stop = None
    original_resolution = rules_service.calculate_resolution
    try:
        with tempfile.TemporaryDirectory(prefix="storyteller-hyp-007-live-") as temp:
            for case_id, inputs, expected_rules, expected_outcome in CASES:
                if stop:
                    break
                store = SQLitePersistence(Path(temp) / f"{case_id}.sqlite3")
                await create_campaign_source_session(store, case_id, initial_state=_initial_state())
                rules_service.calculate_resolution = lambda *_a, **_kw: _fixed_resolution(case_id == "CAMP-EVAL-06")
                for turn, (player_input, expected_rule) in enumerate(zip(inputs, expected_rules), 1):
                    if len(rows) >= MAX_CALLS:
                        stop = "call_limit"
                        break
                    row = {"case_id": case_id, "turn": turn, "rule": expected_rule,
                           "call_made": False, "status": "not_dispatched", "evidence": None}
                    bounded = None
                    turn_started = perf_counter()
                    try:
                        operation_id = f"{case_id}-{turn}-{uuid4().hex}"
                        row["operation_id"] = operation_id
                        prepared = await prepare_campaign_source_player_action(
                            store=store, session_id=case_id, operation_id=operation_id,
                            player_input=player_input, config=config,
                            deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
                            cancellation=CancellationToken(),
                        )
                        capsule = prepared.capsule
                        if capsule is None or capsule.campaign_effect.rule_id != expected_rule:
                            raise ValueError("campaign_luna_preparation_failed")
                        row["preparation_ms"] = round((perf_counter() - turn_started) * 1000)
                        row["capsule_sha256"] = capsule.fingerprint_sha256
                        adapter = (adapter_factory(caps, key) if adapter_factory else
                                   CampaignLunaAdapter(
                                       base_url="https://api.openai.com/v1",
                                       capability_set=caps, api_key=key,
                                       reasoning_effort="low",
                                   ))
                        bounded = BoundedAdapter(adapter, case_id=case_id,
                                                 turn=turn, spent=spent, key=key)
                        async def deliver(_text: str) -> None:
                            return None
                        result = await execute_campaign_source_turn(
                            store=store, capsule=capsule, operation_id=operation_id,
                            gateway=bounded,
                            deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
                            cancellation=CancellationToken(), on_chunk=deliver,
                        )
                        row.update(bounded.row)
                        if result.status != "completed":
                            row["status"] = "rejected"
                            row["error_code"] = row.get("error_code") or result.error_code
                            stop = result.error_code or "campaign_luna_turn_failed"
                        else:
                            row["status"] = "completed"
                            row["outcome"] = capsule.campaign_effect.after_state.outcome
                    except Exception:
                        if bounded is not None:
                            row.update(bounded.row)
                        row["status"] = "failed"
                        row["error_code"] = row.get("error_code") or "campaign_luna_local_failure"
                        stop = row["error_code"]
                    row["turn_ms"] = round((perf_counter() - turn_started) * 1000)
                    if row.get("call_made"):
                        cost = _usage_cost(row)
                        if cost is None:
                            stop = stop or "campaign_luna_usage_unavailable"
                        else:
                            spent += cost
                            if spent > PROPOSED_LIMIT:
                                stop = stop or "campaign_luna_budget_exceeded"
                    rows.append(row)
                    with records.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"record": row}, ensure_ascii=False, sort_keys=True) + "\n")
                    if stop:
                        break
                if not stop:
                    snapshot = await read_campaign_source_snapshot(store, case_id)
                    if snapshot.progression.outcome != expected_outcome:
                        stop = "campaign_luna_outcome_mismatch"
            gc.collect()
            await asyncio.sleep(0)
    finally:
        rules_service.calculate_resolution = original_resolution
        dispatched = any(row.get("call_made") for row in rows)
        cost = summarize(rows, settled=True) if dispatched else summarize([], no_dispatch=True)
        document = {
            "hypothesis_id": "HYP-007", "lot_id": LOT_ID,
            "status": "completed" if not stop and len(rows) == MAX_CALLS else "stopped",
            "stop_reason": stop, "planned_calls": MAX_CALLS,
            "attempted_calls": sum(row.get("call_made") is True for row in rows),
            "completed_turns": sum(row.get("status") == "completed" for row in rows),
            "cost": cost, "records_sha256": _sha(records.read_bytes()) if records.exists() else None,
        }
        (directory / "summary.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        display(cost)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--batch-id")
    args = parser.parse_args(argv)
    directory = None
    try:
        gate = _gate()
        if args.preflight:
            result = asyncio.run(preflight())
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            display(summarize([], no_dispatch=True))
            return 0
        _require_live_gate(gate)
        if not args.batch_id or str(UUID(args.batch_id)) != args.batch_id:
            raise ValueError("campaign_luna_batch_id_invalid")
        # Full keyless rehearsal before loading a credential or dispatching.
        asyncio.run(preflight())
        key_text = os.environ.pop(KEY_ENV, "")
        if not key_text.strip():
            raise ValueError("campaign_luna_credential_missing")
        key = SecretStr(key_text)
        key_text = ""
        directory = OUTPUT_ROOT / f"{LOT_PREFIX}{args.batch_id}"
        result = asyncio.run(run_batch(directory=directory, key=key))
        return 0 if result["status"] == "completed" else 2
    except (OSError, ValueError, json.JSONDecodeError):
        print("HYP-007 indisponível antes de execução aprovada ou por falha local.")
        if directory is not None and (directory / "records.jsonl").exists():
            try:
                observed = read_records(directory)
                if any(row.get("record", row).get("call_made") for row in observed):
                    display(summarize(observed, settled=False))
                else:
                    display(summarize([], no_dispatch=True))
            except (OSError, ValueError, TypeError, AttributeError):
                display(summarize([], settled=False))
        elif directory is not None and directory.exists():
            display(summarize([], settled=False))
        else:
            display(summarize([], no_dispatch=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
