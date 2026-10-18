from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import UUID

import pytest

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"
from scripts import evaluate_narrator_summary_only as executor
from scripts.narrator_summary_only import measure_summary_words

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_summary_only_probe.ps1"
EVALUATOR = "scripts/evaluate_narrator_summary_only.py"
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


@pytest.fixture(scope="module")
def metadata():
    # The real pure preflight is the fixture source: no hand-maintained replica
    # of its shape, hashes, source units, or experimental scope.
    return executor.prepare_experiment().metadata


def _real_summary(code, mode="normal"):
    if mode in {"local_error_after_schema", "cancelled_after_schema"}:
        row = {"kind": "summary_only_call", "case_id": executor.CASE_ID,
               "call_made": True, "schema_valid": True, "route_status": "verified",
               "provider_observation": {"response_status": 200},
               "summary_text": "Resumo sintético válido.",
               "instruction_measurements": measure_summary_words("Resumo sintético válido.")}
        status = "local_error" if mode == "local_error_after_schema" else "cancelled"
        result = executor.summarize([row], status=status)
        assert result["process_exit_code"] == code
        assert result["transport_and_schema_passed"] is False
        return result
    if code in {3, 130}:
        row = {"kind": "summary_only_skip", "case_id": executor.CASE_ID,
               "call_made": False, "skipped_reason": "cancelled" if code == 130 else "local_error"}
        return executor.summarize([row], status="cancelled" if code == 130 else "local_error")
    row = {"kind": "summary_only_call", "case_id": executor.CASE_ID,
           "call_made": True, "schema_valid": code == 0,
           "route_status": "verified" if code != 2 else "unavailable",
           "provider_observation": {"response_status": 200 if code != 2 else None}}
    if code == 0:
        summary_text = "Resumo sintético válido."
        if mode == "long_summary":
            summary_text = " ".join(["palavra"] * 26)
        elif mode == "spaces_summary":
            summary_text = " " * 8
        row["summary_text"] = summary_text
        row["instruction_measurements"] = measure_summary_words(summary_text)
    if code == 2:
        row["llm_error"] = {"category": sorted(executor.AVAILABILITY_CATEGORIES)[0]}
    result = executor.summarize([row])
    assert result["process_exit_code"] == code
    return result


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


def _wrapper(shell, tmp_path, metadata, *, code=0, preexisting=True, blank=False,
             preflight_change=None, live_change=None, mode="normal", disk_drift=None):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_summary_only_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    inputs = metadata["inputs"]
    files = {inputs[name]["file"] for name in ("dossier", "case", "prompt")}
    files.add("evals/narrator/" + inputs["manifest"]["file"])
    files.update(item["file"] for item in inputs["implementation"])
    for relative in files:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    if disk_drift:
        with (project / disk_drift).open("ab") as stream:
            stream.write(b"\nsynthetic drift")
    meta = copy.deepcopy(metadata)
    fake = project / EVALUATOR
    fake.write_text(NATIVE_EVALUATOR, encoding="utf-8")
    meta["evaluator"]["sha256"] = hashlib.sha256(fake.read_bytes()).hexdigest()
    config = {"code": code, "mode": mode, "metadata": meta, "summary": _real_summary(code, mode),
              "preflight_change": preflight_change, "live_change": live_change}
    (project / "config.json").write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
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
def test_real_summary_pass_failure_skip_and_cancel_match_exit_and_restore_environment(shell, tmp_path, metadata, preexisting, code):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=code, preexisting=preexisting)
    assert result["exit_code"] == code, output
    assert len(calls) == 2
    assert calls[0]["arguments"] == ["--preflight"]
    assert calls[0]["key_present"] is False
    assert calls[1]["key_supplied"] is True
    arguments = calls[1]["arguments"]
    batch = arguments[arguments.index("--batch-id") + 1]
    assert str(UUID(batch)) == batch
    assert arguments == ["--live", "--allow-synthetic-only", "--batch-id", batch, "--api-key-env", "GROQ_API_KEY"]
    assert output.count(batch) == 1
    assert "word measurement does not evaluate semantic fidelity" in output
    assert "CAP-001 remain unapproved" in output


@pytest.mark.parametrize("preexisting", [False, True])
def test_blank_key_stops_after_keyless_preflight(shell, tmp_path, metadata, preexisting):
    result, calls, output = _wrapper(shell, tmp_path, metadata, blank=True, preexisting=preexisting)
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert calls[0]["key_present"] is False
    assert "(credential validation)" in output


PREFLIGHT_CHANGES = [
    ('selected_candidate_id', 'gpt-oss-120b-groq-free-synthetic-low'),
    ('purpose', 'inline_evidence_qwen_probe'),
    ('probe_kind', 'inline_evidence_qwen_probe'),
    ('experiment_version', 'record-inline-evidence-qwen-observation-v1'),
    ('protocol', 'record-inline-evidence-v1'),
    ('projection_valid', 0),
    ('full_record_derivation', True),
    ('actor_admission', 'approved'),
    ('structural_only', False),
    ('semantic_not_evaluated', 'true'),
    ('max_calls', 2),
    ('automatic_retries', 1),
    ('diagnostics_executed', True),
    ('runtime_promoted', True),
    ('automated_gates_passed', True),
    ('candidate_policy.reasoning_effort', 'low'),
    ('summary_generation_parameters.requested.max_output_tokens', 1536),
    ('summary_generation_parameters.transmitted.max_output_tokens', 6144),
    ('summary_generation_parameters.transmitted.reasoning_effort', 'medium'),
    ('summary_generation_parameters.max_total_output_tokens', 6144),
    ('inputs.case.case_id', 'uncertain-signal'),
    ('inputs.case.sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.prompt.sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.prompt.file_sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.response_schema_sha256', 'f83bc66cab29a079598f074db3ee4838a94882ef65f254866d0505aa29b37d9a'),
    ('inputs.provider_schema_sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.cases.0.source.origin', 'provider_generated'),
    ('inputs.cases.0.generation_context.version', 'record-summary-only-v1'),
    ('inputs.cases.0.generation_context.user_packet_sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.cases.0.generation_context.source_units.1.text', 'Incomplete statement.'),
    ('inputs.dossier.file', 'evals/narrator/reports/record-inline-evidence-qwen-dossier-6876955e-2026-09-07.json'),
    ('inputs.dossier.sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.dossier.body_sha256', 'bd7219cf1cd27f2ce1d80879370064b6ef7ac3d2b64f4be7a0d32da5db0326f7'),
    ('inputs.projection_policy', None),
    ('inputs.measurement_policy.max_words', 26),
    ('inputs.measurement_policy.method', 'other'),
    ('inputs.measurement_policy.pattern', '[a-z]+'),
    ('inputs.measurement_policy.changes_exit_code', True),
    ('inputs.measurement_policy.semantic_validation', True),
    ('inputs.measurement_policy.extra', True),
    ('inputs.observation_policy.raw_error_retained', True),
    ('inputs.observation_policy.raw_reasoning_retained', True),
    ('inputs.implementation', []),
    ('inputs.manifest.sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
]


@pytest.mark.parametrize("change", PREFLIGHT_CHANGES, ids=lambda c: c[0])
def test_preflight_drift_is_rejected_before_supplied_credential(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, preflight_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 1
    assert calls[0]["key_present"] is False
    assert "(offline preflight)" in output


@pytest.mark.parametrize("relative", [
    "evals/narrator/record_inline_case_v1.json",
    "evals/narrator/prompts/record-summary-only-v1.md",
    "scripts/narrator_summary_only.py",
    "scripts/narrator_record_budget_observer.py",
    "evals/narrator/reports/record-summary-only-dossier-94a95216-2026-09-07.json",
])
def test_fixed_file_drift_is_rejected_before_key(shell, tmp_path, metadata, relative):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, disk_drift=relative)
    assert result["exit_code"] == 3
    assert len(calls) == 1


LIVE_CHANGES = [
    ('batch_id', 'other'),
    ('process_exit_code', 130),
    ('summary.process_exit_code', True),
    ('summary.protocol', 'record-inline-evidence-v1'),
    ('summary.semantic_fidelity_review.approval', True),
    ('summary.support_coverage_review', {'status': 'not_performed', 'approval': None}),
    ('summary.projection_valid', 1),
    ('summary.projection', {'summary': 'old projected text'}),
    ('summary.projection_audit', {}),
    ('summary.full_record_derivation', True),
    ('summary.actor_admission', 'approved'),
    ('summary.calls_made', True),
    ('summary.schema_valid', '1'),
    ('summary.cases_skipped', 1),
    ('summary.operational_probe_passed', 'true'),
    ('summary.transport_and_schema_passed', False),
    ('summary.provider_observation', None),
    ('summary.route_verification.calls_made', True),
    ('summary.route_verification.verified_calls', '1'),
    ('summary.route_verification.unavailable_calls', 1),
    ('summary.route_verification.identity_consistent', 'true'),
    ('summary.instruction_measurements', None),
    ('summary.instruction_measurements.method', 'other'),
    ('summary.instruction_measurements.pattern', '[a-z]+'),
    ('summary.instruction_measurements.word_count', True),
    ('summary.instruction_measurements.word_count', '3'),
    ('summary.instruction_measurements.word_count', -1),
    ('summary.instruction_measurements.word_count', 601),
    ('summary.instruction_measurements.max_words', 26),
    ('summary.instruction_measurements.within_word_limit', False),
    ('summary.instruction_measurements.within_word_limit', 'true'),
    ('summary.instruction_measurements.semantic_fidelity_evaluated', True),
    ('summary.instruction_measurements.changes_exit_code', True),
    ('inputs.prompt.sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.provider_schema_sha256', '0000000000000000000000000000000000000000000000000000000000000000'),
    ('inputs.cases.0.generation_context.source_units.0.text', 'Cut statement.'),
    ('candidate_policy.reasoning_effort', 'low'),
]


@pytest.mark.parametrize("change", LIVE_CHANGES, ids=lambda c: c[0])
def test_summary_and_provenance_drift_fail_closed_without_retry(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, live_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "(summary verification)" in output


@pytest.mark.parametrize("mode", ["failed_preflight", "invalid_preflight_json"])
def test_failed_or_non_json_preflight_is_safely_discarded(shell, tmp_path, metadata, mode):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 1


@pytest.mark.parametrize("mode", ["duplicate_summary", "malformed_summary", "missing_summary"])
def test_missing_ambiguous_or_invalid_summary_does_not_report_success(shell, tmp_path, metadata, mode):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 2


def test_preexisting_artifact_is_not_reused(shell, tmp_path, metadata):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode="preexisting_artifact")
    assert result["exit_code"] == 0
    assert len(calls) == 2
    old = tmp_path / "isolated project/eval-results/old/summary.json"
    assert old.read_text() == "old malformed artifact"


@pytest.mark.parametrize("mode,expected", [("missing_summary", 130), ("partial_jsonl", 3)])
def test_cancellation_preserves_unverified_partial_evidence(shell, tmp_path, metadata, mode, expected):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=130, mode=mode)
    assert result["exit_code"] == expected
    assert len(calls) == 2
    if mode == "partial_jsonl":
        assert "partial local evidence" in output
        assert (tmp_path / "isolated project/eval-results/partial/records.jsonl").read_text() == "partial synthetic evidence"


@pytest.mark.parametrize("mode,within", [("long_summary", False), ("spaces_summary", True)])
def test_word_measurement_is_informative_and_does_not_change_operational_exit(shell, tmp_path, metadata, mode, within):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode=mode)
    assert result["exit_code"] == 0
    assert len(calls) == 2
    document = json.loads((tmp_path / "isolated project/eval-results/synthetic-run/summary.json").read_text())
    measured = document["summary"]["instruction_measurements"]
    assert measured["within_word_limit"] is within
    assert measured["word_count"] == (26 if mode == "long_summary" else 0)
    assert document["summary"]["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}


@pytest.mark.parametrize("code", [1, 2, 3, 130])
def test_measurement_cannot_be_attached_before_verified_schema(shell, tmp_path, metadata, code):
    injected = measure_summary_words("Resumo sintético válido.")
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=code,
                                    live_change=("summary.instruction_measurements", injected))
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "(summary verification)" in output


@pytest.mark.parametrize("mode,code", [("local_error_after_schema", 3), ("cancelled_after_schema", 130)])
def test_late_local_error_or_cancel_preserves_valid_schema_without_operational_promotion(shell, tmp_path, metadata, mode, code):
    result, calls, output = _wrapper(shell, tmp_path, metadata, mode=mode, code=code)
    assert result["exit_code"] == code
    assert len(calls) == 2
    assert "(summary verification)" not in output
    document = json.loads((tmp_path / "isolated project/eval-results/synthetic-run/summary.json").read_text())
    summary = document["summary"]
    assert summary["schema_valid"] == 1
    assert summary["instruction_measurements"] is not None
    assert summary["transport_and_schema_passed"] is summary["operational_probe_passed"] is False


@pytest.mark.parametrize("code,status", [
    (0, 'local_error'),
    (0, 'cancelled'),
    (1, 'local_error'),
    (1, 'cancelled'),
    (2, 'local_error'),
    (2, 'cancelled'),
    (3, 'completed'),
    (3, 'cancelled'),
    (130, 'completed'),
    (130, 'local_error'),
    (0, 'unknown'),
    (0, ''),
    (0, None),
    (0, True),
    (0, 1),
    (0, {}),
    (0, []),
    (0, ['completed']),
    (0, 'Completed'),
], ids=['success-local-error', 'success-cancelled', 'schema-error-local-error', 'schema-error-cancelled', 'availability-local-error', 'availability-cancelled', 'local-error-completed', 'local-error-cancelled', 'cancelled-completed', 'cancelled-local-error', 'unknown', 'empty', 'null', 'bool', 'integer', 'object', 'array', 'string-array', 'wrong-case'])
def test_evaluation_status_must_match_exit_and_closed_status_domain(shell, tmp_path, metadata, code, status):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=code,
                                    live_change=("evaluation_status", status))
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "(summary verification)" in output


def test_missing_evaluation_status_is_rejected(shell, tmp_path, metadata):
    result, calls, output = _wrapper(shell, tmp_path, metadata, mode="missing_evaluation_status")
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "(summary verification)" in output


NATIVE_EVALUATOR = r"""
import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
args=sys.argv[1:]
ledger=root/'calls.json'
calls=json.loads(ledger.read_text()) if ledger.exists() else []
calls.append({'arguments':args,'key_present':'GROQ_API_KEY' in os.environ,'key_supplied':os.environ.get('GROQ_API_KEY')=='synthetic-supplied-sentinel'})
ledger.write_text(json.dumps(calls))
def change(doc,spec):
 if spec is None:return
 path,value=spec;names=path.split('.');item=doc
 for name in names[:-1]:item=item[int(name)] if isinstance(item,list) else item[name]
 name=names[-1]
 if isinstance(item,list):item[int(name)]=value
 else:item[name]=value
doc=config['metadata'];mode=config['mode'];code=config['code']
if args==['--preflight']:
 if mode in {'failed_preflight','invalid_preflight_json'}:
  print('synthetic-sensitive-error-payload');sys.exit(3 if mode=='failed_preflight' else 0)
 change(doc,config['preflight_change'])
 print(json.dumps(doc));sys.exit(0)
doc.update(batch_id=args[args.index('--batch-id')+1],evaluation_status='local_error' if code==3 else 'cancelled' if code==130 else 'completed',process_exit_code=code,summary=config['summary'])
if mode=='missing_evaluation_status':doc.pop('evaluation_status')
change(doc,config['live_change'])
if mode=='partial_jsonl':
 folder=root/'eval-results/partial';folder.mkdir(parents=True)
 (folder/'records.jsonl').write_text('partial synthetic evidence')
if mode not in {'missing_summary','partial_jsonl'}:
 folder=root/'eval-results/synthetic-run';folder.mkdir(parents=True)
 (folder/'summary.json').write_text('malformed' if mode=='malformed_summary' else json.dumps(doc))
 if mode=='duplicate_summary':
  other=root/'eval-results/other';other.mkdir()
  (other/'summary.json').write_text(json.dumps(doc))
print('synthetic-sensitive-error-payload')
print('synthetic-sensitive-error-payload',file=sys.stderr)
sys.exit(code)
"""
