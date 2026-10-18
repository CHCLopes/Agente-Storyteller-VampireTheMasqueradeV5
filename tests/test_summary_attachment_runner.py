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
from scripts import evaluate_narrator_summary_attachment as executor
from scripts.narrator_summary_only import measure_summary_words

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_groq_summary_attachment_probe.ps1"
EVALUATOR = "scripts/evaluate_narrator_summary_attachment.py"
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
    def call(index, *, schema=True, availability=False):
        case_id = executor.CASE_IDS[index]
        row = {"kind": "summary_attachment_call", "case_id": case_id, "call_made": True,
               "schema_valid": schema, "route_status": "unavailable" if availability else "verified",
               "provider_observation": {"http_status": None if availability else 200, "request_id": "synthetic-" + case_id}}
        if availability:
            row["llm_error"] = {"category": sorted(executor.AVAILABILITY_CATEGORIES)[0]}
        if schema:
            text = "Resumo sintético válido."
            if mode == "long_first" and index == 0 or mode == "long_second" and index == 1:
                text = " ".join(["palavra"] * 26)
            row["summary_text"] = text
            row["instruction_measurements"] = measure_summary_words(text)
        return row

    def skip(index):
        return {"kind": "summary_attachment_skip", "case_id": executor.CASE_IDS[index],
                "call_made": False, "skipped_reason": "synthetic_prior_stop"}

    status = "local_error" if code == 3 else "cancelled" if code == 130 else "completed"
    if mode in {"local_after_second", "cancel_after_second"} or code == 0:
        rows = [call(0), call(1)]
    elif mode in {"local_after_first", "cancel_after_first"}:
        rows = [call(0), skip(1)]
    elif mode == "cancel_first_dispatch":
        rows = [call(0, schema=False, availability=True), skip(1)]
    elif code in {3, 130}:
        rows = [skip(0), skip(1)]
    elif mode in {"schema_second", "availability_second"}:
        rows = [call(0), call(1, schema=False, availability=code == 2)]
    else:
        rows = [call(0, schema=False, availability=code == 2), skip(1)]
    summary = executor.summarize(rows, status=status)
    assert summary["process_exit_code"] == code
    return summary


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
    runner = project / "scripts/run_groq_summary_attachment_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    inputs = metadata["inputs"]
    files = {inputs[name]["file"] for name in ("dossier", "prompt")}
    files.add("evals/narrator/" + inputs["corpus"]["file"])
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


@pytest.mark.parametrize("mode,code,calls_made,schema_valid", [
    ("normal", 0, 2, 2), ("long_first", 0, 2, 2), ("long_second", 0, 2, 2),
    ("schema_first", 1, 1, 0), ("schema_second", 1, 2, 1),
    ("availability_first", 2, 1, 0), ("availability_second", 2, 2, 1),
    ("local_before_first", 3, 0, 0), ("local_after_first", 3, 1, 1), ("local_after_second", 3, 2, 2),
    ("cancel_before_first", 130, 0, 0), ("cancel_after_first", 130, 1, 1),
    ("cancel_first_dispatch", 130, 1, 0), ("cancel_after_second", 130, 2, 2),
])
def test_real_two_case_summaries_preserve_order_stage_exit_and_nonblocking_word_limit(shell, tmp_path, metadata, mode, code, calls_made, schema_valid):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=code, mode=mode)
    assert result["exit_code"] == code, output
    assert len(calls) == 2  # One keyless preflight and one synthetic evaluator process.
    assert calls[0]["arguments"] == ["--preflight"] and calls[0]["key_present"] is False
    assert calls[1]["key_supplied"] is True
    args = calls[1]["arguments"]
    batch = args[args.index("--batch-id") + 1]
    assert str(UUID(batch)) == batch
    assert args == ["--live", "--allow-synthetic-only", "--batch-id", batch, "--api-key-env", "GROQ_API_KEY"]
    document = json.loads((tmp_path / "isolated project/eval-results/synthetic-run/summary.json").read_text())
    summary = document["summary"]
    assert summary["calls_made"] == calls_made
    assert summary["cases_skipped"] == 2 - calls_made
    assert summary["schema_valid"] == schema_valid
    assert [entry["case_id"] for entry in summary["case_measurements"]] == list(executor.CASE_IDS)
    assert len(summary["provider_observations"]) == calls_made
    assert summary["operational_probe_passed"] is (code == 0)
    if mode in {"long_first", "long_second"}:
        index = 0 if mode == "long_first" else 1
        assert summary["case_measurements"][index]["instruction_measurements"]["within_word_limit"] is False
        assert summary["calls_made"] == 2
    assert "word measurement does not evaluate semantic fidelity" in output
    assert "CAP-001 remain unapproved" in output


@pytest.mark.parametrize("blank", [False, True])
def test_environment_absence_and_empty_key_are_preserved(shell, tmp_path, metadata, blank):
    result, calls, output = _wrapper(shell, tmp_path, metadata, preexisting=False, blank=blank)
    assert result["exit_code"] == (3 if blank else 0)
    assert len(calls) == (1 if blank else 2)
    assert calls[0]["key_present"] is False
    if blank:
        assert "(credential validation)" in output


PREFLIGHT_CHANGES = [
    ("purpose", "summary_only_qwen_probe"),
    ("experiment_version", "record-summary-only-qwen-observation-v1"),
    ("max_calls", 1), ("summary_generation_parameters.max_total_output_tokens", 3072),
    ("summary_generation_parameters.minimum_inter_call_delay_seconds", 0),
    ("summary_generation_parameters.transmitted.max_output_tokens", 1536),
    ("inputs.corpus.sha256", "0" * 64), ("inputs.cases.0.case_id", "observatory-b"),
    ("inputs.cases.0.source.case_index", 1), ("inputs.cases.1.source.case_index", False),
    ("inputs.cases.1.generation_context.user_packet_sha256", "7a56db6bcaadb137df1aeb4e49652151ca12f0b3819e7b90ccfdd2c054454176"),
    ("inputs.cases.1.generation_context.source_units.0.text", "synthetic altered source"),
    ("inputs.dossier.requests.0.case_id", "observatory-b"),
    ("inputs.dossier.requests.1.body_sha256", "51265c46c0acf56e6a8b85470715e54606f65dabf6b146db415fb28ed4e4312d"),
    ("inputs.measurement_policy.changes_exit_code", True),
    ("inputs.stopping_policy.stop_on_first_operational_failure", False),
    ("inputs.stopping_policy.word_limit_failure_stops_next_case", True),
    ("inputs.stopping_policy.order.0", "observatory-b"),
]


@pytest.mark.parametrize("change", PREFLIGHT_CHANGES, ids=lambda c: c[0])
def test_two_case_preflight_bindings_and_budget_fail_before_credential(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, preflight_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 1 and calls[0]["key_present"] is False
    assert "(offline preflight)" in output


@pytest.mark.parametrize("relative", [
    "evals/narrator/record_summary_attachment_cases_v1.json",
    "evals/narrator/reports/record-summary-attachment-dossier-21cf338b-2026-09-07.json",
])
def test_new_fixed_files_are_verified_before_credential(shell, tmp_path, metadata, relative):
    result, calls, output = _wrapper(shell, tmp_path, metadata, disk_drift=relative)
    assert result["exit_code"] == 3
    assert len(calls) == 1 and "(offline preflight)" in output


LIVE_CHANGES = [
    ("evaluation_status", "local_error"), ("evaluation_status", True),
    ("summary.calls_made", 3), ("summary.calls_made", True),
    ("summary.cases_skipped", 1), ("summary.schema_valid", 3),
    ("summary.provider_observations", []), ("summary.provider_observations.0", None),
    ("summary.provider_observations.0.case_id", "observatory-b"),
    ("summary.provider_observations.1.observation", None),
    ("summary.provider_observation", {"http_status": 200}),
    ("summary.case_measurements", []), ("summary.case_measurements.0.case_id", "observatory-b"),
    ("summary.case_measurements.1.case_id", "observatory-a"),
    ("summary.case_measurements.0.extra", True),
    ("summary.case_measurements.1.instruction_measurements", None),
    ("summary.case_measurements.1.instruction_measurements.word_count", True),
    ("summary.case_measurements.1.instruction_measurements.within_word_limit", False),
    ("summary.case_measurements.1.instruction_measurements.semantic_fidelity_evaluated", True),
    ("summary.instruction_measurements", {}), ("summary.projection_valid", 2),
    ("summary.semantic_fidelity_review.approval", True),
    ("summary.route_verification.verified_calls", 1),
    ("summary.transport_and_schema_passed", False),
    ("inputs.cases.1.generation_context.user_packet_sha256", "0" * 64),
]


@pytest.mark.parametrize("change", LIVE_CHANGES, ids=lambda c: c[0])
def test_two_case_results_reject_incoherent_counts_order_measurements_and_scope(shell, tmp_path, metadata, change):
    result, calls, output = _wrapper(shell, tmp_path, metadata, live_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 2
    assert "(summary verification)" in output


@pytest.mark.parametrize("case", ["measurement_for_skipped_b", "second_call_without_first_measurement", "singular_observation_mismatch"])
def test_partial_results_respect_attempted_prefix_and_first_case_success(shell, tmp_path, metadata, case):
    if case == "measurement_for_skipped_b":
        mode, code = "cancel_after_first", 130
        change = ("summary.case_measurements.1.instruction_measurements", measure_summary_words("Resumo sintético válido."))
    elif case == "second_call_without_first_measurement":
        mode, code = "schema_second", 1
        change = ("summary.case_measurements.0.instruction_measurements", None)
    else:
        mode, code = "schema_first", 1
        change = ("summary.provider_observation", {"http_status": 999})
    result, calls, output = _wrapper(shell, tmp_path, metadata, mode=mode, code=code, live_change=change)
    assert result["exit_code"] == 3
    assert len(calls) == 2 and "(summary verification)" in output


@pytest.mark.parametrize("mode", ["duplicate_summary", "malformed_summary", "missing_summary", "missing_evaluation_status"])
def test_one_new_run_and_complete_summary_are_required(shell, tmp_path, metadata, mode):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 2


def test_preexisting_artifact_is_not_reused(shell, tmp_path, metadata):
    result, calls, _ = _wrapper(shell, tmp_path, metadata, mode="preexisting_artifact")
    assert result["exit_code"] == 0
    assert len(calls) == 2
    assert (tmp_path / "isolated project/eval-results/old/summary.json").read_text() == "old malformed artifact"


@pytest.mark.parametrize("mode,expected", [("missing_summary", 130), ("partial_jsonl", 3)])
def test_cancel_without_summary_keeps_partial_evidence_distinct(shell, tmp_path, metadata, mode, expected):
    result, calls, output = _wrapper(shell, tmp_path, metadata, code=130, mode=mode)
    assert result["exit_code"] == expected
    assert len(calls) == 2
    if mode == "partial_jsonl":
        assert "partial local evidence" in output
        assert (tmp_path / "isolated project/eval-results/partial/records.jsonl").read_text() == "partial synthetic evidence"


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
