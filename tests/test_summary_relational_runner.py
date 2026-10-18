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

os.environ["STORYTELLER_DISABLE_DOTENV"]="1"

from scripts import evaluate_narrator_summary_relational as executor

from scripts.narrator_summary_only import measure_summary_words

ROOT = Path(__file__).resolve().parents[1]

RUNNER = ROOT / "scripts/run_groq_summary_relational_probe.ps1"

EVALUATOR = "scripts/evaluate_narrator_summary_relational.py"

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
        case_id = executor.CASE_ID
        row = {"kind": "summary_relational_call", "case_id": case_id, "arm_id": executor.ARM_IDS[index], "call_made": True,
               "schema_valid": schema, "route_status": "unavailable" if availability else "verified",
               "provider_observation": {"http_status": None if availability else 200, "request_id": "synthetic-" + executor.ARM_IDS[index]}}
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
        return {"kind": "summary_relational_skip", "case_id": executor.CASE_ID, "arm_id": executor.ARM_IDS[index],
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


def _wrapper(shell, tmp_path, metadata, *, code=0, preexisting=True, blank=False,
             preflight_change=None, live_change=None, mode="normal", disk_drift=None):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_summary_relational_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, "$python = " + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    inputs = metadata["inputs"]
    files = {inputs[name]["file"] for name in ("dossier", "case")}
    files.update(arm["prompt"]["file"] for arm in inputs["arms"])
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

@pytest.mark.parametrize("available_shell",SHELLS or [None],ids=lambda p:Path(p).stem if p else "unavailable")
def test_relational_wrapper_syntax(available_shell,tmp_path):
    if available_shell is None:pytest.skip("PowerShell unavailable")
    command="$tokens=$null; $errors=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile("+_ps(RUNNER)+",[ref]$tokens,[ref]$errors); if ($errors.Count) { exit 1 }"
    result=_shell_run(available_shell,command,tmp_path)
    assert result.returncode==0,result.stdout+result.stderr


def test_single_source_user_is_identical_and_schema_is_unchanged_across_arms(metadata):
    d=json.loads((ROOT/metadata["inputs"]["dossier"]["file"]).read_text(encoding="utf-8"))
    a,b=[r["body"] for r in d["requests"]]
    assert a["messages"][1]==b["messages"][1]
    assert a["messages"][0]!=b["messages"][0]
    assert json.loads(a["messages"][1]["content"].split("\n",1)[1])["case_id"]=="gallery-reflection"
    normalized=copy.deepcopy(b);normalized["messages"][0]=a["messages"][0]
    assert a==normalized
    assert [x["arm_id"] for x in metadata["inputs"]["arms"]]==["control","relational"]
    assert all(x["case_id"]=="gallery-reflection" for x in metadata["inputs"]["arms"])


@pytest.mark.parametrize("mode,code,call_count",[
    ("normal",0,2),("long_first",0,2),("availability_first",2,1),("schema_second",1,2),
    ("local_before_first",3,0),("cancel_after_first",130,1),("cancel_after_second",130,2),
])
def test_two_arm_real_summaries_keep_one_case_stops_exits_and_environment(shell,tmp_path,metadata,mode,code,call_count):
    result,calls,output=_wrapper(shell,tmp_path,metadata,mode=mode,code=code)
    assert result["exit_code"]==code,output
    assert len(calls)==2 and calls[0]["arguments"]==["--preflight"]
    assert calls[0]["key_present"] is False and calls[1]["key_supplied"] is True
    args=calls[1]["arguments"];batch=args[args.index("--batch-id")+1]
    assert str(UUID(batch))==batch
    assert args==["--live","--allow-synthetic-only","--batch-id",batch,"--api-key-env","GROQ_API_KEY"]
    summary=json.loads((tmp_path/"isolated project/eval-results/synthetic-run/summary.json").read_text())["summary"]
    assert summary["calls_made"]==call_count and summary["arms_skipped"]==2-call_count
    assert [(x["arm_id"],x["case_id"]) for x in summary["arm_measurements"]]==[("control","gallery-reflection"),("relational","gallery-reflection")]
    assert [x["arm_id"] for x in summary["provider_observations"]]==list(executor.ARM_IDS[:call_count])
    assert all(x["case_id"]=="gallery-reflection" for x in summary["provider_observations"])
    assert "768 tokens each and 1536 total" in output
    if mode=="long_first":assert summary["arm_measurements"][0]["instruction_measurements"]["within_word_limit"] is False
    assert summary["semantic_fidelity_review"]=={"status":"not_performed","approval":None}


@pytest.mark.parametrize("blank",[False,True])
def test_relational_credential_validation_and_absent_environment(shell,tmp_path,metadata,blank):
    result,calls,output=_wrapper(shell,tmp_path,metadata,preexisting=False,blank=blank)
    assert result["exit_code"]==(3 if blank else 0)
    assert len(calls)==(1 if blank else 2) and calls[0]["key_present"] is False
    if blank:assert "(credential validation)" in output


@pytest.mark.parametrize("change",[
    ("purpose","summary_color_qwen_probe"),
    ("protocol","record-summary-relational-v1"),
    ("summary_generation_parameters.max_total_output_tokens",768),
    ("inputs.case.case_id","control"),
    ("inputs.case.source.case_id","gallery-reflection"),
    ("inputs.case.generation_context.user_packet_sha256","0"*64),
    ("inputs.case.generation_context.source_units.0.text","Incomplete source."),
    ("inputs.arms.0.prompt.file","evals/narrator/prompts/record-summary-relational-v1.md"),
    ("inputs.arms.1.prompt.sha256","1eca37a720951743b0f989b3ed31b1fd726663345bad71016179966d5548d5ce"),
    ("inputs.arms.1.arm_id","control"),
    ("inputs.arms.1.arm_index",False),
    ("inputs.arms.1.case_id","relational"),
    ("inputs.arms.1.request.operation","summary-relational.control"),
    ("inputs.arms.0.request.body_sha256","7599cb88ff1f4085ada54469c7749d6ef7aaebbd2287ad207be47e29dd3043ec"),
    ("inputs.dossier.requests.1.case_id","relational"),
    ("inputs.dossier.requests.1.user_packet_sha256","0"*64),
    ("inputs.corpus",None),("inputs.cases",[]),("inputs.prompt",None),
    ("inputs.stopping_policy.order.0","relational"),
    ("inputs.stopping_policy.word_limit_failure_stops_next_arm",True),
],ids=lambda c:c[0])
def test_arm_case_source_system_mapping_and_budget_mismatch_precedes_key(shell,tmp_path,metadata,change):
    result,calls,output=_wrapper(shell,tmp_path,metadata,preflight_change=change)
    assert result["exit_code"]==3 and len(calls)==1
    assert calls[0]["key_present"] is False and "(offline preflight)" in output


@pytest.mark.parametrize("relative",[
    "evals/narrator/record_summary_relational_case_v1.json",
    "evals/narrator/prompts/record-summary-budget-v1.md",
    "evals/narrator/prompts/record-summary-relational-v1.md",
])
def test_each_actual_source_and_prompt_file_is_checked_before_key(shell,tmp_path,metadata,relative):
    result,calls,output=_wrapper(shell,tmp_path,metadata,disk_drift=relative)
    assert result["exit_code"]==3 and len(calls)==1 and "(offline preflight)" in output


@pytest.mark.parametrize("change",[
    ("evaluation_status","local_error"),("summary.calls_made",3),
    ("summary.arms_skipped",1),("summary.cases_skipped",0),
    ("summary.case_measurements",[]),
    ("summary.provider_observations.0.arm_id","relational"),
    ("summary.provider_observations.1.case_id","relational"),
    ("summary.arm_measurements.1.arm_id","control"),
    ("summary.arm_measurements.0.case_id","control"),
    ("summary.semantic_fidelity_review.approval",True),
],ids=lambda c:c[0])
def test_result_cannot_confuse_arm_with_case_or_promote_semantics(shell,tmp_path,metadata,change):
    result,calls,output=_wrapper(shell,tmp_path,metadata,live_change=change)
    assert result["exit_code"]==3 and len(calls)==2 and "(summary verification)" in output


@pytest.mark.parametrize("which",["measurement_for_skip","second_without_first"])
def test_partial_result_cannot_claim_unobserved_arm_or_skip_first_success(shell,tmp_path,metadata,which):
    if which=="measurement_for_skip":
        mode,code="cancel_after_first",130
        change=("summary.arm_measurements.1.instruction_measurements",measure_summary_words("Resumo sintético válido."))
    else:
        mode,code="schema_second",1
        change=("summary.arm_measurements.0.instruction_measurements",None)
    result,calls,output=_wrapper(shell,tmp_path,metadata,mode=mode,code=code,live_change=change)
    assert result["exit_code"]==3 and len(calls)==2 and "(summary verification)" in output


def test_two_new_run_summaries_are_rejected_without_retry(shell,tmp_path,metadata):
    result,calls,_=_wrapper(shell,tmp_path,metadata,mode="duplicate_summary")
    assert result["exit_code"]==3 and len(calls)==2
