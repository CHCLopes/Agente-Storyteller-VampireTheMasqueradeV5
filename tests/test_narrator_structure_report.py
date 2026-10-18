from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from api.llm.contract import (
    AdapterIdentity,
    ErrorCategory,
    InvocationEvidence,
    LLMTarget,
    NormalizedError,
    OperationPhase,
    Provenance,
    StructureValidationEvidence,
)
from scripts import evaluate_narrator_models as module


def _candidate():
    manifest = module.PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
    return module.load_candidates(manifest)["qwen-3.8-27b-groq-free-synthetic-nonthink"]


def _error(structure_validation=None):
    candidate = _candidate()
    target = LLMTarget(profile="probe-test", provider="Groq", model=candidate.model)
    now = datetime.now(timezone.utc)
    return NormalizedError(
        category=ErrorCategory.INVALID_STRUCTURED_OUTPUT,
        code="structured_output_schema_mismatch",
        phase=OperationPhase.STRUCTURE_VALIDATION,
        invocation_id="synthetic-structure-probe",
        target=target,
        safe_message="Structured output did not match the required schema.",
        evidence=InvocationEvidence(provenance=Provenance(
            invocation_id="synthetic-structure-probe",
            requested_target=target,
            adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
            started_at=now,
            finished_at=now,
        )),
        structure_validation=structure_validation,
    )


def _record(error_payload):
    return {
        "kind": "narrative_turn",
        "call_made": True,
        "episode_id": "opening",
        "turn_id": "establish-scene",
        "repetition": 1,
        "schema_valid": False,
        "admitted": False,
        "llm_error": error_payload,
    }


@pytest.mark.parametrize(("stage", "path", "code", "console_detail"), [
    ("schema_validation", ["n"], "missing", "missing at n"),
    ("schema_validation", [], "value_error", "value_error at response"),
    ("json_parse", [], "json_invalid", "json_invalid at response"),
    ("schema_validation", ["f", 0, "s"], "string_type", "string_type at f[0].s"),
    ("schema_validation", ["f"], "tuple_type", "tuple_type at f"),
    ("schema_validation", ["o"], "literal_error", "literal_error at o"),
])
def test_structure_cause_survives_payload_summary_and_safe_console(
    stage, path, code, console_detail,
):
    expected = {
        "stage": stage, "issues": [{"path": path, "code": code}], "truncated": False,
    }
    evidence = StructureValidationEvidence.model_validate(expected)
    payload = module._normalized_error_payload(_error(evidence))
    assert payload["structure_validation"] == expected

    summary = module._summarize_opening_probe(_candidate(), _record(payload))
    assert summary["failure"]["structure_validation"] == expected
    assert summary["failure"]["category"] == "llm"
    assert summary["full_evaluation"] is False
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["automated_gates_passed"] is False
    console = module._opening_probe_diagnostic(summary)
    assert stage in console
    assert console_detail in console


def test_legacy_errors_keep_shape_and_do_not_claim_structure_diagnostics():
    payload = module._normalized_error_payload(_error())
    assert "structure_validation" not in payload
    assert set(payload) == {
        "category", "code", "phase", "safe_message", "partial_output",
        "external_id", "status_code", "retryable", "retry_after_seconds", "rate_limit",
    }
    summary = module._summarize_opening_probe(_candidate(), _record(payload))
    assert "structure_validation" not in summary["failure"]
    console = module._opening_probe_diagnostic(summary)
    assert "Structure:" not in console
    assert "schema_validation" not in console
    assert "json_parse" not in console


@pytest.mark.parametrize("raw", [None, {}, {"stage": "unknown"}, "untrusted"])
def test_absent_or_invalid_structure_metadata_is_not_promoted_to_a_cause(raw):
    payload = module._normalized_error_payload(_error())
    payload["structure_validation"] = raw
    summary = module._summarize_opening_probe(_candidate(), _record(payload))
    assert "structure_validation" not in summary["failure"]
    assert "Structure:" not in module._opening_probe_diagnostic(summary)


def test_untrusted_structure_metadata_cannot_echo_secret_paths_messages_or_codes():
    secret = "private_prompt_or_key_123"
    raw = {
        "stage": "schema_validation",
        "issues": [
            {"path": [secret], "code": "missing", "input": secret, "msg": secret},
            {"path": ["f", 0, secret], "code": secret, "ctx": {"secret": secret}},
            {"path": ["f", 999999999, "s"], "code": "string_type"},
        ],
        "truncated": False,
        "raw_response": secret,
    }
    payload = module._normalized_error_payload(_error())
    payload["structure_validation"] = raw
    summary = module._summarize_opening_probe(_candidate(), _record(payload))
    sanitized = summary["failure"]["structure_validation"]
    serialized = json.dumps(sanitized)
    assert secret not in serialized
    assert "999999999" not in serialized
    assert "raw_response" not in serialized
    assert "validation_error" in serialized

    # Console revalidates metadata too, even when handed an untrusted summary.
    summary["failure"]["structure_validation"] = raw
    console = module._opening_probe_diagnostic(summary)
    assert secret not in console
    assert "999999999" not in console
    assert "schema_validation" in console


def test_console_bounds_issue_count_and_does_not_dump_metadata():
    evidence = {
        "stage": "schema_validation",
        "issues": [{"path": ["n"], "code": "missing"}] * 4,
        "truncated": False,
    }
    console = module._opening_probe_structure_diagnostic(evidence)
    assert console.count("missing at n") == 3
    assert "additional issues omitted" in console
