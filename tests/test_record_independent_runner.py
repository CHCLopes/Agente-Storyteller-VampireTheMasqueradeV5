from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_record_independent_cases_probe.ps1"
SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]


def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def _shell_run(shell, command, cwd):
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment.pop("PSModulePath", None)
    environment["STORYTELLER_DISABLE_DOTENV"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=25,
    )


@lru_cache(maxsize=None)
def _policy(shell):
    result = _shell_run(shell, "Get-ExecutionPolicy", ROOT)
    return result.stdout.strip() if result.returncode == 0 else "Unavailable"


@pytest.fixture
def shell():
    selected = shutil.which("pwsh")
    if selected is None:
        pytest.skip("PowerShell 7 unavailable")
    if _policy(selected) in {"Unavailable", "Restricted", "AllSigned"}:
        pytest.skip("Host policy/module prevents execution; policy is not bypassed")
    return selected


@pytest.mark.parametrize("available_shell", SHELLS or [None], ids=lambda p: Path(p).stem if p else "unavailable")
def test_wrapper_parses_in_each_available_shell(available_shell, tmp_path):
    if available_shell is None:
        pytest.skip("PowerShell unavailable")
    result = _shell_run(available_shell, f"""
$tokens=$null; $errors=$null
$null=[System.Management.Automation.Language.Parser]::ParseFile({_ps(RUNNER)},[ref]$tokens,[ref]$errors)
if ($errors.Count) {{ exit 1 }}
""", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def _wrapper(shell, tmp_path, *, code=0, mode="normal", preexisting=True, blank=False, summary_fixture=None):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_record_independent_cases_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    for relative in ("evals/narrator/groq_candidates_2026-09-05.json", "evals/narrator/record_independent_cases_v1.json", "evals/narrator/reports/record-evidence-independent-cases-dossier-84ea2c0c-2026-09-07.json", "scripts/narrator_record_independent_cases.py"):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if "independent" in relative:
            path.write_bytes((ROOT / relative).read_bytes())
        else:
            path.write_text("synthetic fixture", encoding="utf-8")
    (project / "config.json").write_text(json.dumps({"code": code, "mode": mode, "summary_fixture": summary_fixture}), encoding="utf-8")
    (project / "scripts/evaluate_narrator_record_independent_cases.py").write_text(NATIVE_EVALUATOR, encoding="utf-8")
    if mode == "preexisting_artifact":
        old = project / "eval-results/old"
        old.mkdir(parents=True)
        (old / "summary.json").write_text("old malformed artifact", encoding="utf-8")
    result_path = project / "harness-result.json"
    command = f"""
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true
{'$env:GROQ_API_KEY='+_ps('synthetic-previous-sentinel') if preexisting else 'Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue'}
$key=ConvertTo-SecureString {_ps(' ' if blank else 'synthetic-supplied-sentinel')} -AsPlainText -Force
$global:LASTEXITCODE=0
& {_ps(runner)} -ApiKey $key
$result=@{{exit_code=$LASTEXITCODE; present=(Test-Path Env:GROQ_API_KEY); restored=($env:GROQ_API_KEY -eq 'synthetic-previous-sentinel'); preference=$PSNativeCommandUseErrorActionPreference}}
$result | ConvertTo-Json | Set-Content -LiteralPath {_ps(result_path)}
exit 0
"""
    completed = _shell_run(shell, command, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for sentinel in ("synthetic-supplied-sentinel", "synthetic-previous-sentinel", "synthetic-sensitive-error-payload"):
        assert sentinel not in completed.stdout + completed.stderr
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    assert result["present"] is result["restored"] is preexisting
    assert result["preference"] is True
    ledger = project / "calls.json"
    calls = json.loads(ledger.read_text()) if ledger.exists() else []
    return result, calls, completed.stdout


@pytest.mark.parametrize("preexisting", [False, True])
@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_one_live_child_follows_keyless_preflight_and_restores_environment(shell, tmp_path, preexisting, code):
    result,calls,output = _wrapper(shell,tmp_path,preexisting=preexisting,code=code)
    assert result["exit_code"] == code
    assert len(calls) == 2
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False
    assert calls[1]["key_supplied"] is True
    arguments=calls[1]["arguments"]
    batch=arguments[arguments.index("--batch-id")+1]
    assert str(UUID(batch)) == batch
    assert arguments == ["--live","--allow-synthetic-only","--batch-id",batch,"--api-key-env","GROQ_API_KEY"]
    assert output.count(batch) == 1
    assert "never approves narrative quality, runtime or CAP-001" in output


@pytest.mark.parametrize("preexisting", [False, True])
def test_blank_key_is_rejected_after_keyless_preflight_without_live_call(shell,tmp_path,preexisting):
    result,calls,_ = _wrapper(shell,tmp_path,preexisting=preexisting,blank=True)
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False


@pytest.mark.parametrize("mode", ['failed', 'invalid_json', 'wrong_candidate', 'old_claim_check', 'opening_case', 'reverse_cases', 'forged_origin', 'old_batch_source', 'wrong_binding', 'wrong_narrative_hash', 'wrong_source_type', 'source_audit_drift', 'wrong_corpus_hash', 'wrong_helper_hash', 'missing_helper', 'duplicate_helper', 'dossier_requests_reversed', 'old_experiment', 'wrong_prompt', 'old_prompt_hash', 'old_schema_change', 'only_schema_changed', 'dossier_hash', 'original_body', 'proposed_body', 'payload_fields', 'prompt_hash', 'wrong_user_version', 'more_calls', 'wrong_case', 'raw_error', 'retries', 'wrong_protocol', 'fuzzy_matching', 'rewrites_records', 'semantic_validation'])
def test_incoherent_preflight_never_reaches_supplied_credential_or_live_call(shell,tmp_path,mode):
    result,calls,_ = _wrapper(shell,tmp_path,mode="preflight_"+mode)
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False


@pytest.mark.parametrize("mode", ['missing_observations', 'duplicate_observation', 'reversed_observations', 'wrong_observation_id', 'singular_with_two_calls', 'helper_drift', 'wrong_batch', 'wrong_exit', 'old_experiment', 'summary_old_experiment', 'input_drift', 'schema_drift', 'admission_count', 'route_mismatch', 'duplicate_summary', 'summary_approved', 'support_policy_drift'])
def test_incoherent_new_artifact_is_rejected_without_retry_or_output_leak(shell,tmp_path,mode):
    result,calls,_ = _wrapper(shell,tmp_path,mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 2


@pytest.mark.parametrize("preexisting", [False, True])
def test_native_cancellation_without_summary_preserves_130_and_restores_key(shell,tmp_path,preexisting):
    result,calls,output = _wrapper(shell,tmp_path,code=130,mode="missing_summary",preexisting=preexisting)
    assert result["exit_code"] == 130
    assert len(calls) == 2
    assert "cancelled; no completed summary" in output


@pytest.mark.parametrize('mode', ['partial_jsonl'])
def test_cancellation_preserves_partial_artifacts_but_cannot_verify_them(shell,tmp_path,mode):
    result,calls,output = _wrapper(shell,tmp_path,code=130,mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "partial local evidence" in output
    partial=tmp_path / "isolated project/eval-results/partial"
    assert partial.is_dir()
    if mode == "partial_jsonl":
        assert (partial / "records.jsonl").read_text() == "partial synthetic evidence"


@pytest.mark.parametrize('field,value', [('calls_made', True), ('unavailable_calls', '0')])
def test_success_route_counts_require_integers_without_boolean_or_string_coercion(shell,tmp_path,field,value):
    result,calls,_ = _wrapper(shell,tmp_path,mode="invalid_route_count:"+field+":"+json.dumps(value))
    assert result["exit_code"] == 3
    assert len(calls) == 2


def test_mara_case_id_cannot_bypass_the_independent_case_identity(shell,tmp_path):
    result,calls,output = _wrapper(shell,tmp_path,mode="preflight_wrong_case_id")
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False
    assert "(offline preflight)" in output


@pytest.mark.parametrize("counts", [(1, 0), (2, 1), (1, True), (1, "1"), (0, 2)])
def test_case_accounting_cannot_hide_skips_or_create_success(shell, tmp_path, counts):
    result, calls, _ = _wrapper(shell, tmp_path, mode="case_accounting:" + json.dumps(counts))
    assert result["exit_code"] == 3 and len(calls) == 2


@pytest.mark.parametrize("mode", ["missing_single_observation", "scalar_observations"])
def test_partial_failure_requires_the_one_call_observation(shell, tmp_path, mode):
    result, calls, _ = _wrapper(shell, tmp_path, code=1, mode=mode)
    assert result["exit_code"] == 3 and len(calls) == 2


def test_second_case_failure_preserves_first_admission_without_retry(shell, tmp_path):
    result, calls, _ = _wrapper(shell, tmp_path, code=1, mode="second_case_failure")
    assert result["exit_code"] == 1 and len(calls) == 2


@pytest.mark.parametrize("second_skipped", [False, True])
def test_actual_executor_summary_shape_passes_wrapper_for_success_and_partial_failure(shell, tmp_path, second_skipped):
    from scripts import evaluate_narrator_record_independent_cases as probe
    # Mocked call/skip results flow through the real production summarizer. This
    # checks its JSON nesting without exercising transport or changing its data.
    rows = []
    for index, case_id in enumerate(probe.CASE_IDS):
        called = not (index == 1 and second_skipped)
        rows.append({
            "case_id": case_id, "call_made": called,
            "kind": "record_evidence_independent_cases_call" if called else "record_evidence_independent_cases_skip",
            "schema_valid": called, "envelope_valid": called,
            "final_schema_valid": called, "admitted": called and not second_skipped,
            "route_status": "verified" if called else "unavailable",
            "provider_observation": {"http_status": 200, "finish_reason": "stop"} if called else None,
        })
    summary = probe.summarize(rows)
    assert summary["calls_made"] == (1 if second_skipped else 2)
    assert summary["cases_skipped"] == int(second_skipped)
    assert summary["process_exit_code"] == (1 if second_skipped else 0)
    result, calls, output = _wrapper(shell, tmp_path, code=summary["process_exit_code"], summary_fixture=summary)
    assert result["exit_code"] == summary["process_exit_code"]
    assert len(calls) == 2 and "Summary:" in output


NATIVE_EVALUATOR = r'''

import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/"config.json").read_text())
code,mode=config["code"],config["mode"]
arguments=sys.argv[1:]
preflight=arguments==["--preflight"]
ledger=root/"calls.json"
calls=json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({"arguments":arguments,"key_present":"GROQ_API_KEY" in os.environ,"key_supplied":os.environ.get("GROQ_API_KEY")=="synthetic-supplied-sentinel"})
ledger.write_text(json.dumps(calls))
def digest(path): return hashlib.sha256((root/path).read_bytes()).hexdigest()
parameter={"temperature":0.65,"max_output_tokens":3072}
document={
 "purpose":"record_evidence_independent_cases_probe","probe_kind":"record_evidence_independent_cases_probe","full_evaluation":False,
 "synthetic_only":True,"runtime_promoted":False,"cap_001_status":"not_evaluated","automated_gates_passed":False,
 "human_review_required":True,"diagnostics_executed":False,"automatic_retries":0,"max_calls":2,"experiment_version":"record-evidence-independent-cases-v1",
 "selected_candidate_id":"gpt-oss-120b-groq-free-synthetic-low","repetitions":1,"causal_comparison":False,"narrative_generation_calls":0,
 "evaluator":{"file":"scripts/evaluate_narrator_record_independent_cases.py","sha256":digest("scripts/evaluate_narrator_record_independent_cases.py"),"python_version":"synthetic","git_commit":"synthetic","git_dirty":True},
 "evidence_generation_parameters":{"deadline_seconds":60,"minimum_inter_call_delay_seconds":60,"requested":parameter.copy(),"transmitted":dict(parameter,reasoning_effort="low"),"max_total_output_tokens":6144,"user_packet_budget":{"estimated_tokens":2000,"method":"characters_divided_by_4"}},
 "inputs":{
  "manifest":{"file":"groq_candidates_2026-09-05.json","sha256":digest("evals/narrator/groq_candidates_2026-09-05.json")},
  "corpus":{"file":"record_independent_cases_v1.json","sha256":digest("evals/narrator/record_independent_cases_v1.json")},
  "prompt":{"variant":"record-evidence-claim-check-v1","file":"evals/narrator/prompts/record-evidence-claim-check-v1.md","sha256":"dc338d3ff2f1cf3fa04222e717b5e3f060541fbf41cf4abd5a9cf7af66a74839"},
  "response_schema_sha256":"b"*64,"provider_schema_sha256":"c"*64,
  "final_schema_sha256":"bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2",
  "implementation":[{"file":"scripts/fixed_cases.py","sha256":"d"*64},{"file":"scripts/narrator_record_independent_cases.py","sha256":digest("scripts/narrator_record_independent_cases.py")}],
  "cases":[{'case_id': 'uncertain-signal', 'episode_id': 'independent-uncertainty', 'turn_id': 'derive-uncertainty', 'source': {'case_binding': 'record-independent-cases-v1', 'origin': 'agent_authored_synthetic_cases', 'synthetic_only': True, 'corpus_id': 'storyteller-record-independent-cases-v1', 'corpus_file': 'evals/narrator/record_independent_cases_v1.json', 'corpus_sha256': 'fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353', 'case_path': '/cases/0', 'case_id': 'uncertain-signal', 'episode_id': 'independent-uncertainty', 'turn_id': 'derive-uncertainty', 'field': 'narrative', 'narrative_sha256': '0fab6e6c72d44d20f2c8512650ba99861b069e381d6354bdc37c140b96dc865a', 'context_origin': 'original_synthetic_corpus', 'protected_secrets_count': 0}, 'generation_context': {'version': 'record-evidence-v1', 'user_packet_sha256': '8406c7783c645b9f8df1ca1d1d856c19f48f4f3fd6b178010a811d8613710602', 'source': {'case_binding': 'record-independent-cases-v1', 'origin': 'agent_authored_synthetic_cases', 'synthetic_only': True, 'corpus_id': 'storyteller-record-independent-cases-v1', 'corpus_file': 'evals/narrator/record_independent_cases_v1.json', 'corpus_sha256': 'fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353', 'case_path': '/cases/0', 'case_id': 'uncertain-signal', 'episode_id': 'independent-uncertainty', 'turn_id': 'derive-uncertainty', 'field': 'narrative', 'narrative_sha256': '0fab6e6c72d44d20f2c8512650ba99861b069e381d6354bdc37c140b96dc865a', 'context_origin': 'original_synthetic_corpus', 'protected_secrets_count': 0}, 'source_units': [{'id': 'n0', 'text': 'Synthetic complete statement.'}]}}, {'case_id': 'sensory-evidence', 'episode_id': 'independent-sensory', 'turn_id': 'derive-sensory', 'source': {'case_binding': 'record-independent-cases-v1', 'origin': 'agent_authored_synthetic_cases', 'synthetic_only': True, 'corpus_id': 'storyteller-record-independent-cases-v1', 'corpus_file': 'evals/narrator/record_independent_cases_v1.json', 'corpus_sha256': 'fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353', 'case_path': '/cases/1', 'case_id': 'sensory-evidence', 'episode_id': 'independent-sensory', 'turn_id': 'derive-sensory', 'field': 'narrative', 'narrative_sha256': '5db12d31eb1f50451261f84dbc5e4ca493728ecb3ef0b49bee7d02847608f79e', 'context_origin': 'original_synthetic_corpus', 'protected_secrets_count': 0}, 'generation_context': {'version': 'record-evidence-v1', 'user_packet_sha256': '67686acf1d0bbbf56575a8987ff18dd21019083e1bed740e06c1d6054efb3b96', 'source': {'case_binding': 'record-independent-cases-v1', 'origin': 'agent_authored_synthetic_cases', 'synthetic_only': True, 'corpus_id': 'storyteller-record-independent-cases-v1', 'corpus_file': 'evals/narrator/record_independent_cases_v1.json', 'corpus_sha256': 'fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353', 'case_path': '/cases/1', 'case_id': 'sensory-evidence', 'episode_id': 'independent-sensory', 'turn_id': 'derive-sensory', 'field': 'narrative', 'narrative_sha256': '5db12d31eb1f50451261f84dbc5e4ca493728ecb3ef0b49bee7d02847608f79e', 'context_origin': 'original_synthetic_corpus', 'protected_secrets_count': 0}, 'source_units': [{'id': 'n0', 'text': 'Synthetic complete statement.'}]}}],
  "dossier":{'file': 'evals/narrator/reports/record-evidence-independent-cases-dossier-84ea2c0c-2026-09-07.json', 'sha256': '24a3b302938e27481f131c9ecf1826fd9571c1fdf68e2ae3238fa0a94a3cdd36', 'original_body_sha256': '0ef02b6c4987318c829e7193e6cdbba67dcc58d6937e966fdcf3809c64cbd209', 'changed_payload_fields': ['messages[1].content'], 'requests': [{'case_id': 'uncertain-signal', 'body_sha256': 'dfeab91b18a02b969f887ff06877e576c6f6dc3fd1b55fcb652a1ec6ab5c4840'}, {'case_id': 'sensory-evidence', 'body_sha256': '2a762328afd75a5951071f9d39cffeee329e3184cfeaec2cc86dc13333f1b40b'}]},
  "support_resolution_policy":{'method': 'unique_exact_target_quote', 'quote_protocol': 'record-evidence-target-quotes-v1', 'matching': 'literal_unicode_code_points', 'ambiguous_quote': 'reject', 'missing_quote': 'reject', 'records_rewritten': False, 'offsets_purpose': 'audit_only', 'coverage_validation': False, 'entailment_validation': False},
  "observation_policy":{"max_error_body_bytes":65536,"raw_error_retained":False,"raw_reasoning_retained":False},
 },
}
def corrupt(doc,mode):
 changes={"wrong_candidate":("selected_candidate_id","other"),"wrong_purpose":("purpose","full_evaluation"),
  "string_false":("full_evaluation","False"),"promoted":("runtime_promoted",True),"approved":("automated_gates_passed",True),
  "not_synthetic":("synthetic_only",False),"retries":("automatic_retries",1),"diagnostics":("diagnostics_executed",True),
  "wrong_version":("experiment_version","record-evidence-v1"),
  "wrong_repetitions":("repetitions",2),"more_calls":("max_calls",3),"new_narratives":("narrative_generation_calls",1)}
 if mode in changes:
  name,value=changes[mode];doc[name]=value
 if mode=="old_claim_check": doc.update(purpose="record_evidence_claim_check_probe",probe_kind="record_evidence_claim_check_probe",experiment_version="record-evidence-claim-check-v1")
 if mode=="opening_case": doc["inputs"]["cases"][0].update(case_id="opening",episode_id="opening",turn_id="establish-scene")
 if mode=="reverse_cases": doc["inputs"]["cases"].reverse()
 if mode=="forged_origin": doc["inputs"]["cases"][0]["source"]["origin"]="model_generated"
 if mode=="old_batch_source": doc["inputs"]["cases"][0]["source"]["batch_id"]="bb98ae1e"
 if mode=="wrong_binding": doc["inputs"]["cases"][0]["source"]["case_binding"]="record-derivation-v1"
 if mode=="wrong_narrative_hash": doc["inputs"]["cases"][0]["source"]["narrative_sha256"]="0"*64
 if mode=="wrong_source_type": doc["inputs"]["cases"][0]["source"]["protected_secrets_count"]=False
 if mode=="source_audit_drift": doc["inputs"]["cases"][0]["generation_context"]["source"]["case_id"]="other"
 if mode=="wrong_corpus_hash": doc["inputs"]["corpus"]["sha256"]="0"*64
 if mode=="wrong_helper_hash": doc["inputs"]["implementation"][1]["sha256"]="0"*64
 if mode=="missing_helper": doc["inputs"]["implementation"].pop()
 if mode=="duplicate_helper": doc["inputs"]["implementation"].append(dict(doc["inputs"]["implementation"][1]))
 if mode=="dossier_requests_reversed": doc["inputs"]["dossier"]["requests"].reverse()
 if mode=="wrong_parameters": doc["evidence_generation_parameters"]["requested"]["max_output_tokens"]=769
 if mode=="wrong_manifest_hash": doc["inputs"]["manifest"]["sha256"]="0"*64
 if mode=="wrong_evaluator_hash": doc["evaluator"]["sha256"]="0"*64
 if mode=="missing_cases": doc["inputs"]["cases"]=[]
 if mode=="wrong_case_id": doc["inputs"]["cases"][0]["case_id"]="mara"
 if mode=="wrong_case": doc["inputs"]["cases"][0]["episode_id"]="player-agency"
 if mode=="missing_field": del doc["inputs"]["final_schema_sha256"]
 if mode=="wrong_prompt": doc["inputs"]["prompt"]["variant"]="record-evidence-target-quotes-v1"
 if mode=="missing_provider_schema": del doc["inputs"]["provider_schema_sha256"]
 if mode=="invalid_provider_schema": doc["inputs"]["provider_schema_sha256"]="invalid"
 if mode=="wrong_final_schema": doc["inputs"]["final_schema_sha256"]="0"*64
 if mode=="old_budget":
  doc["evidence_generation_parameters"]["requested"]["max_output_tokens"]=768
  doc["evidence_generation_parameters"]["transmitted"]["max_output_tokens"]=768
 if mode=="extra_case": doc["inputs"]["cases"].append(dict(doc["inputs"]["cases"][0],case_id="mara",episode_id="player-agency"))
 if mode=="missing_dossier": del doc["inputs"]["dossier"]
 if mode=="dossier_hash": doc["inputs"]["dossier"]["sha256"]="0"*64
 if mode=="original_body": doc["inputs"]["dossier"]["original_body_sha256"]="0"*64
 if mode=="proposed_body": doc["inputs"]["dossier"]["proposed_body_sha256"]="0"*64
 if mode=="payload_fields": doc["inputs"]["dossier"]["changed_payload_fields"].append("temperature")
 if mode=="observation_size": doc["inputs"]["observation_policy"]["max_error_body_bytes"]=65537
 if mode=="raw_error": doc["inputs"]["observation_policy"]["raw_error_retained"]=True
 if mode=="raw_reasoning": doc["inputs"]["observation_policy"]["raw_reasoning_retained"]=True
 if mode=="prompt_hash": doc["inputs"]["prompt"]["sha256"]="0"*64
 if mode=="wrong_user_version": doc["inputs"]["cases"][0]["generation_context"]["version"]="record-evidence-target-quotes-v1"
 if mode=="old_prompt_file": doc["inputs"]["prompt"]["file"]="evals/narrator/prompts/record-evidence-v1.md"
 if mode=="wrong_dossier_file": doc["inputs"]["dossier"]["file"]="evals/narrator/reports/record-evidence-request-dossier-2c1cafde-2026-09-07.json"
 if mode=="old_budget_experiment": doc.update(purpose="record_evidence_budget_probe",probe_kind="record_evidence_budget_probe",experiment_version="record-evidence-budget-1536-v1")
 if mode=="old_evidence_experiment": doc.update(purpose="record_evidence_probe",probe_kind="record_evidence_probe",experiment_version="record-evidence-v1")
 if mode=="old_experiment": doc.update(purpose="record_evidence_target_quotes_probe",probe_kind="record_evidence_target_quotes_probe",experiment_version="record-evidence-target-quotes-v1")
 if mode=="wrong_requested_budget": doc["evidence_generation_parameters"]["requested"]["max_output_tokens"]=1536
 if mode=="wrong_transmitted_budget": doc["evidence_generation_parameters"]["transmitted"]["max_output_tokens"]=1536
 if mode=="wrong_total_budget": doc["evidence_generation_parameters"]["max_total_output_tokens"]=1536
 if mode=="old_prompt_hash": doc["inputs"]["prompt"]["sha256"]="4583e3c1ade0896696636e7e8174e7183f73b85c46c524809862b632de948ae3"
 if mode=="old_schema_change": doc["inputs"]["dossier"]["changed_payload_fields"]=["messages[0].content","response_format"]
 if mode=="only_schema_changed": doc["inputs"]["dossier"]["changed_payload_fields"]=["response_format"]
 if mode=="wrong_protocol": doc["inputs"]["support_resolution_policy"]["quote_protocol"]="record-evidence-claim-check-v1"
 if mode=="fuzzy_matching": doc["inputs"]["support_resolution_policy"]["matching"]="normalized"
 if mode=="rewrites_records": doc["inputs"]["support_resolution_policy"]["records_rewritten"]=True
 if mode=="semantic_validation": doc["inputs"]["support_resolution_policy"]["entailment_validation"]=True
if preflight:
 if mode.startswith("preflight_"):
  selected=mode.removeprefix("preflight_")
  if selected in {"failed","invalid_json"}:
   print("synthetic-sensitive-error-payload");sys.exit(3 if selected=="failed" else 0)
  corrupt(document,selected)
 print(json.dumps(document));sys.exit(0)
document.update(batch_id=arguments[arguments.index("--batch-id")+1],process_exit_code=code)
document["summary"]={key:value for key,value in document.items() if key not in {"inputs","evaluator","evidence_generation_parameters","batch_id"}}
document["summary"].update({"calls_made":2 if code==0 else 1,"cases_skipped":0 if code==0 else 1,"schema_valid":2 if code==0 else 1,"envelope_valid":2 if code==0 else 1,"final_schema_valid":2 if code==0 else 1,"admitted":2 if code==0 else 0,"operational_probe_passed":code==0,
 "automated_gates_passed":False,"full_evaluation":False,"runtime_promoted":False,"human_review_required":True,
 "route_verification":{"status":"verified","calls_made":2 if code==0 else 1,"verified_calls":2 if code==0 else 1,"unavailable_calls":0,"mismatched_calls":0,"identity_consistent":True}})
document["summary"]["provider_observations"]=[{"case_id":case["case_id"],"observation":{"http_status":200}} for case in document["inputs"]["cases"][:document["summary"]["calls_made"]]]
document["summary"]["provider_observation"]=document["summary"]["provider_observations"][0]["observation"] if document["summary"]["calls_made"]==1 else None
if config["summary_fixture"] is not None: document["summary"]=config["summary_fixture"]
corrupt(document,mode)
if mode.startswith("summary_"): corrupt(document["summary"],mode.removeprefix("summary_"))
if mode=="summary_wrong_exit": document["summary"]["process_exit_code"]=130
if mode=="summary_wrong_cap": document["summary"]["cap_001_status"]="approved"
if mode=="summary_causal": document["summary"]["causal_comparison"]=True
if mode=="zero_failed_count": document["summary"].update(calls_made=0,schema_valid=0,envelope_valid=0,final_schema_valid=0,admitted=0)

if mode.startswith("invalid_route_count:"):
 _,field,value=mode.split(":",2);document["summary"]["route_verification"][field]=json.loads(value)
if mode.startswith("invalid_count:"):
 _,field,value=mode.split(":",2);document["summary"][field]=json.loads(value)
if mode.startswith("stage_counts:"):
 values=json.loads(mode.split(":",1)[1])
 document["summary"].update(zip(("calls_made","schema_valid","envelope_valid","final_schema_valid","admitted"),values))

if mode=="missing_observations": del document["summary"]["provider_observations"]
if mode=="duplicate_observation": document["summary"]["provider_observations"][1]=dict(document["summary"]["provider_observations"][0])
if mode=="reversed_observations": document["summary"]["provider_observations"].reverse()
if mode=="wrong_observation_id": document["summary"]["provider_observations"][0]["case_id"]="opening"
if mode=="singular_with_two_calls": document["summary"]["provider_observation"]={"http_status":200}
if mode=="helper_drift": document["inputs"]["implementation"][1]["sha256"]="0"*64
if mode=="missing_single_observation": document["summary"]["provider_observation"]=None
if mode=="scalar_observations": document["summary"]["provider_observations"]=document["summary"]["provider_observations"][0]
if mode.startswith("case_accounting:"):
 calls,skipped=json.loads(mode.split(":",1)[1]);document["summary"].update(calls_made=calls,cases_skipped=skipped)
if mode=="second_case_failure":
 document["summary"].update(calls_made=2,cases_skipped=0,schema_valid=1,envelope_valid=1,final_schema_valid=1,admitted=1)
 document["summary"]["provider_observations"].append({"case_id":"sensory-evidence","observation":{"http_status":400}})
 document["summary"]["provider_observation"]=None
if mode=="wrong_batch": document["batch_id"]="other"
if mode=="wrong_exit": document["process_exit_code"]=130
if mode=="prompt_drift": document["inputs"]["prompt"]["sha256"]="0"*64
if mode=="support_policy_drift": document["inputs"]["support_resolution_policy"]["quote_protocol"]="other"
if mode=="input_drift": document["inputs"]["cases"][0]["generation_context"]["user_packet_sha256"]="0"*64
if mode=="schema_drift": document["inputs"]["response_schema_sha256"]="0"*64
if mode=="dossier_drift": document["inputs"]["dossier"]["proposed_body_sha256"]="0"*64
if mode=="observation_drift": document["inputs"]["observation_policy"]["raw_error_retained"]=True
if mode=="provider_schema_drift": document["inputs"]["provider_schema_sha256"]="0"*64
if mode=="source_units_drift": document["inputs"]["cases"][0]["generation_context"]["source_units"][0]["text"]="Cut source."
if mode=="implementation_drift": document["inputs"]["implementation"][0]["sha256"]="0"*64
if mode=="missing_summary_fields": document["summary"]={}
if mode=="string_count": document["summary"]["calls_made"]="2"
if mode=="extra_count": document["summary"]["calls_made"]=2
if mode=="schema_count": document["summary"]["schema_valid"]=0
if mode=="envelope_count": document["summary"]["envelope_valid"]=0
if mode=="final_schema_count": document["summary"]["final_schema_valid"]=0
if mode=="admission_count": document["summary"]["admitted"]=0
if mode=="route_mismatch": document["summary"]["route_verification"]["mismatched_calls"]=1
if mode=="summary_approved": document["summary"]["automated_gates_passed"]=True
if mode=="false_success": document["summary"]["operational_probe_passed"]=False
if mode=="reordered_metadata":
 for key in ("inputs","evaluator","evidence_generation_parameters"):
  document[key]=dict(reversed(list(document[key].items())))
if mode in {"partial_jsonl","empty_directory"}:
 partial=root/"eval-results"/"partial";partial.mkdir(parents=True)
 if mode=="partial_jsonl":(partial/"records.jsonl").write_text("partial synthetic evidence")
if mode not in {"missing_summary","partial_jsonl","empty_directory"}:
 folder=root/"eval-results"/"synthetic-run";folder.mkdir(parents=True)
 (folder/"summary.json").write_text("malformed" if mode=="malformed_summary" else json.dumps(document))
 if mode in {"duplicate_summary","other_new_summary"}:
  other=root/"eval-results"/"other";other.mkdir()
  if mode=="other_new_summary":document["batch_id"]="other"
  (other/"summary.json").write_text(json.dumps(document))
print("synthetic-sensitive-error-payload")
print("synthetic-sensitive-error-payload",file=sys.stderr)
sys.exit(code)
'''
