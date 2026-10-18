from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import SecretStr

from api.llm.contract import (
    AdapterIdentity,
    ErrorCategory,
    InvocationEvidence,
    LLMInvocationError,
    NormalizedError,
    OperationPhase,
    Provenance,
    ProvenanceValue,
    StructuredGenerationResult,
)
from scripts import evaluate_narrator_models as module


ROOT = Path(module.PROJECT_ROOT)
MANIFEST = ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
CANDIDATE_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"


def _candidate():
    return module.load_candidates(MANIFEST)[CANDIDATE_ID]


def _proposal():
    return module.SceneContinuationProposal.model_validate({
        "n": (
            "A chuva fina escorre pelos postes e deixa o asfalto brilhando sob a "
            "luz vermelha. Você está num beco estreito, entre caixotes úmidos e "
            "uma parede coberta de pichações antigas. Um letreiro falha acima da "
            "rua, enquanto passos distantes quebram o silêncio sem decidir seu rumo."
        ),
        "o": "unresolved",
        "l": "Beco sob néon",
        "s": "O Neófito está em um beco estreito sob um letreiro instável.",
        "f": [{"k": "observation", "s": "Caixotes úmidos ocupam um lado do beco."}],
        "t": ["Identificar a origem dos passos"],
        "q": "O que você faz primeiro?",
    })


def _install_gateway(
    monkeypatch, *, error_category=None, wrong_model=False, proposal_override=None,
):
    requests = []

    class Gateway:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == module.GROQ_OFFICIAL_BASE_URL

        async def test_connection(self, request):
            pytest.fail("opening probe must not make text diagnostics")

        def stream_text(self, request):
            pytest.fail("opening probe must not make streaming diagnostics")

        async def generate_structured(self, request):
            requests.append(request)
            now = datetime.now(timezone.utc)
            evidence = InvocationEvidence(provenance=Provenance(
                invocation_id=request.invocation_id,
                requested_target=request.target,
                adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
                effective_provider=ProvenanceValue.observed("Groq"),
                effective_model=ProvenanceValue.reported(
                    "unexpected/model" if wrong_model else request.target.model
                ),
                started_at=now,
                finished_at=now,
            ))
            if error_category is not None:
                raise LLMInvocationError(NormalizedError(
                    category=error_category,
                    code="synthetic_failure",
                    phase=OperationPhase.RESPONSE,
                    invocation_id=request.invocation_id,
                    target=request.target,
                    safe_message="Synthetic test error.",
                    evidence=evidence,
                    retryable=True,
                ))
            return StructuredGenerationResult(
                value=proposal_override if proposal_override is not None else _proposal(),
                evidence=evidence,
            )

    monkeypatch.setattr(module, "GroqAdapter", Gateway)
    return requests


def _run_probe(*, max_output_tokens=768, **kwargs):
    return asyncio.run(module.evaluate_candidate(
        _candidate(),
        module.load_corpus(module.DEFAULT_CORPUS),
        api_key=SecretStr("synthetic-unit-test-key"),
        repetitions=1,
        deadline_seconds=60.0,
        temperature=0.65,
        max_output_tokens=max_output_tokens,
        opening_probe=True,
        **kwargs,
    ))


@pytest.mark.parametrize("max_output_tokens", [768, 2048])
def test_opening_probe_makes_one_real_turn_path_without_diagnostics_or_quality_approval(
    monkeypatch, max_output_tokens,
):
    requests = _install_gateway(monkeypatch)
    records, summary = _run_probe(
        inter_call_delay_seconds=120.0, max_output_tokens=max_output_tokens,
    )

    assert len(requests) == len(records) == 1
    request = requests[0]
    assert request.operation == "CAP-001.opening.establish-scene.r1"
    assert request.target.model == _candidate().model
    assert request.response_model is module.SceneContinuationProposal
    assert request.parameters.max_output_tokens == max_output_tokens
    assert request.parameters.temperature == 0.65
    assert request.messages[0].content == module.load_storyteller_prompt()
    opening = module.load_corpus(module.DEFAULT_CORPUS)["episodes"][0]
    assert request.messages[1].content == module.build_system_log(
        player_input="Onde estou?", outcome="unresolved", scene=None,
        known_context=opening["known_context"], protected_secrets=(),
    )
    assert summary["purpose"] == "operational_probe"
    assert summary["full_evaluation"] is False
    assert summary["human_review_required"] is True
    assert summary["operational_probe_passed"] is True
    assert summary["automated_gates_passed"] is False
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["diagnostics_executed"] is False
    assert summary["automatic_retries"] == 0
    assert summary["failure"] is None
    assert summary["usage_aggregate"]["expected_calls"] == 1
    assert summary["cost_aggregate"]["expected_calls"] == 1
    assert module._evaluation_exit_code(summary) == 0


@pytest.mark.parametrize(("category", "expected_exit"), [
    (ErrorCategory.RATE_LIMITED, 2),
    (ErrorCategory.TIMEOUT, 2),
    (ErrorCategory.INVALID_STRUCTURED_OUTPUT, 1),
])
def test_probe_error_never_retries_or_advances_to_another_turn(
    monkeypatch, category, expected_exit,
):
    requests = _install_gateway(monkeypatch, error_category=category)
    records, summary = _run_probe()
    assert len(requests) == len(records) == 1
    assert summary["operational_probe_passed"] is False
    assert summary["automated_gates_passed"] is False
    assert module._evaluation_exit_code(summary) == expected_exit
    assert summary["failure"]["category"] == (
        "availability" if expected_exit == 2 else "llm"
    )
    assert summary["failure"]["error_category"] == category.value
    diagnostic = module._opening_probe_diagnostic(summary)
    assert category.value in diagnostic
    assert "synthetic_failure" not in diagnostic


def test_probe_cannot_report_operational_success_for_another_model(monkeypatch):
    requests = _install_gateway(monkeypatch, wrong_model=True)
    _, summary = _run_probe()
    assert len(requests) == 1
    assert summary["route_verification"]["status"] == "mismatch"
    assert summary["operational_probe_passed"] is False
    assert module._evaluation_exit_code(summary) == 1
    assert summary["failure"] == {
        "category": "route", "code": "route_mismatch", "field": None,
    }
    assert "route could not be verified" in module._opening_probe_diagnostic(summary)


@pytest.mark.parametrize("max_output_tokens", [768, 2048])
def test_cli_persists_distinct_probe_artifacts_without_credentials(
    tmp_path, monkeypatch, max_output_tokens,
):
    requests = _install_gateway(monkeypatch)
    fake_key = "synthetic-probe-key-do-not-persist"
    monkeypatch.setenv("GROQ_API_KEY", fake_key)
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)

    result = module.main([
        "--live", "--opening-probe", "--manifest", str(MANIFEST),
        "--candidate", CANDIDATE_ID, "--allow-synthetic-only",
        "--max-output-tokens", str(max_output_tokens),
    ])
    assert result == 0
    assert len(requests) == 1
    summary_path, = tmp_path.glob("*/summary.json")
    document = json.loads(summary_path.read_text(encoding="utf-8"))
    assert document["purpose"] == "operational_probe"
    assert document["full_evaluation"] is False
    assert document["human_review_required"] is True
    assert document["cap_001_status"] == "not_evaluated"
    assert document["process_exit_code"] == 0
    assert document["summary"]["automated_gates_passed"] is False
    assert requests[0].parameters.max_output_tokens == max_output_tokens
    for kind in ("requested", "transmitted"):
        assert document["narrative_generation_parameters"][kind]["max_output_tokens"] == max_output_tokens
    assert document["evaluation_pacing"]["diagnostic_rate_limit_retry"] == {
        "enabled": False, "maximum_attempts_per_probe": 0,
    }
    record_path, = tmp_path.glob("*/*.jsonl")
    lines = record_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["purpose"] == "operational_probe"
    assert fake_key not in summary_path.read_text(encoding="utf-8")
    assert fake_key not in lines[0]


@pytest.mark.parametrize("extra_args", [["--repetitions", "3"], ["--replay", "saved.jsonl"]])
def test_probe_rejects_full_run_and_replay_before_credential_lookup(extra_args):
    with pytest.raises(SystemExit, match="requires one repetition"):
        module.main(["--opening-probe", "--candidate", CANDIDATE_ID, *extra_args])


def test_probe_requires_live_authority():
    with pytest.raises(SystemExit, match="explicit --live"):
        module.main(["--opening-probe", "--candidate", CANDIDATE_ID])


def test_probe_requires_exact_synthetic_opening_before_adapter_construction(monkeypatch):
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    corpus["episodes"].reverse()
    monkeypatch.setattr(module, "GroqAdapter", lambda **_: pytest.fail("unexpected adapter"))
    with pytest.raises(ValueError, match="synthetic opening/establish-scene"):
        asyncio.run(module.evaluate_candidate(
            _candidate(), corpus, api_key=SecretStr("synthetic-test-key"),
            repetitions=1, deadline_seconds=60, temperature=0.65,
            max_output_tokens=2048, opening_probe=True,
        ))


def test_operational_probe_cannot_be_replayed_as_an_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "probe.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: [{
        "purpose": "operational_probe", "kind": "narrative_turn",
    }])
    with pytest.raises(SystemExit, match="cannot be replayed as a CAP-001"):
        module.main([
            "--replay", "probe.jsonl", "--manifest", str(MANIFEST),
            "--candidate", CANDIDATE_ID,
        ])


def test_probe_wrapper_scopes_credential_and_checks_matching_artifact():
    source = (ROOT / "scripts/run_groq_narrator_probe.ps1").read_text(encoding="utf-8")
    assert "[System.Security.SecureString] $ApiKey" in source
    assert "--opening-probe" in source
    assert source.count("& $python $evaluator") == 1
    assert "finally {" in source
    assert "$env:GROQ_API_KEY = $previousGroqApiKey" in source
    assert "Remove-Item Env:GROQ_API_KEY" in source
    assert '$document.purpose -eq "operational_probe"' in source
    assert "$document.process_exit_code -eq $exitCode" in source
    assert "Set-Content" not in source
    assert "Start-Sleep" not in source


@pytest.mark.parametrize("filename", [
    "run_groq_narrator_probe.ps1", "run_groq_narrator_comparison.ps1",
])
def test_groq_wrappers_use_explicit_output_budget_below_observed_account_limit(filename):
    source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
    # The confirmed account OTPM ceiling is 1000, not the combined 8000 TPM.
    # Keep the same explicit narrative budget in the isolated and full screenings.
    assert source.count("--max-output-tokens 768") == 1
    assert "--max-output-tokens 2048" not in source
    assert "Narrative output ceiling: 768 tokens" in source
    assert "--temperature 0.65" in source
    assert "--deadline-seconds 60" in source


def test_probe_admission_diagnostic_explains_scene_summary_agency_failure(
    tmp_path, monkeypatch, capsys,
):
    proposal = _proposal().model_copy(update={
        "scene_summary": "O Neófito desperta no beco sob um letreiro instável.",
    })
    requests = _install_gateway(monkeypatch, proposal_override=proposal)
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-unit-test-key")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)

    result = module.main([
        "--live", "--opening-probe", "--manifest", str(MANIFEST),
        "--candidate", CANDIDATE_ID, "--allow-synthetic-only",
    ])
    assert result == 1
    assert len(requests) == 1
    summary_path, = tmp_path.glob("*/summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))["summary"]
    assert summary["schema_valid"] == 1
    assert summary["admitted"] == 0
    assert summary["availability_failure"] is False
    assert summary["failure"] == {
        "category": "admission",
        "code": "scene_player_agency_violation",
        "field": "scene_summary",
    }
    assert summary["admission_error"] == "scene_player_agency_violation"
    assert summary["admission_evidence"]["field"] == "scene_summary"
    assert summary["automated_gates_passed"] is False
    output = capsys.readouterr().out
    assert "admission rejected (player agency violation in scene_summary)" in output
    assert proposal.scene_summary not in output
    assert "CAP-001 was not evaluated" in output


def test_valid_verification_question_does_not_promote_invented_opening_history(monkeypatch):
    proposal = _proposal().model_copy(update={
        "scene_summary": "Despertar na escuridão de um subsolo industrial, sem memória de chegada.",
        "player_prompt": "Como você verifica suas condições imediatas?",
    })
    requests = _install_gateway(monkeypatch, proposal_override=proposal)
    records, summary = _run_probe()
    assert len(requests) == len(records) == 1
    assert summary["schema_valid"] == 1
    assert summary["admitted"] == 0
    assert summary["failure"] == {
        "category": "admission", "code": "scene_player_agency_violation", "field": "scene_summary",
    }
    assert summary["admission_evidence"]["rule"] == "unestablished_opening_history"
    assert summary["automatic_retries"] == 0
    assert summary["cap_001_status"] == "not_evaluated"
    assert module._evaluation_exit_code(summary) == 1


def test_probe_summary_omits_secret_fields_and_console_never_echoes_free_codes(monkeypatch):
    _install_gateway(monkeypatch)
    records, _ = _run_probe()
    record = records[0]
    secret = "private_key_and_generated_prose_must_stay_out"
    record.update({
        "admitted": False,
        "admission_error": "scene_player_agency_violation",
        "admission_evidence": {
            "field": "scene_summary",
            "rule": "declared_player_actions_only",
            "clause_index": 0,
            "unknown_secret": secret,
            "clause": secret,
        },
        "unknown_secret": secret,
    })
    summary = module._summarize_opening_probe(_candidate(), record)
    assert summary["admission_evidence"] == {
        "field": "scene_summary",
        "rule": "declared_player_actions_only",
        "clause_index": 0,
    }
    assert secret not in json.dumps(summary)
    assert secret not in module._opening_probe_diagnostic(summary)

    for category in ("admission", "llm", "availability", "route", secret):
        diagnostic = module._opening_probe_diagnostic({
            "failure": {
                "category": category, "code": secret,
                "field": secret, "error_category": secret,
            },
        })
        assert secret not in diagnostic


def test_probe_llm_failure_takes_precedence_over_missing_route_or_admission(monkeypatch):
    _install_gateway(monkeypatch, error_category=ErrorCategory.TIMEOUT)
    records, _ = _run_probe()
    record = records[0]
    secret = "private message and key: synthetic-secret"
    record["evidence"] = None
    record["llm_error"].update({
        "code": secret, "safe_message": secret, "unknown_field": secret,
    })
    summary = module._summarize_opening_probe(_candidate(), record)
    assert summary["route_verification"]["status"] == "unavailable"
    assert summary["failure"] == {
        "category": "availability", "error_category": "timeout",
        "code": None, "field": None,
    }
    assert secret not in json.dumps(summary)
    assert "availability failure (timeout)" in module._opening_probe_diagnostic(summary)
