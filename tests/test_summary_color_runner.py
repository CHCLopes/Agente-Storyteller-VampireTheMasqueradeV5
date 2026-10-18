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

from scripts import evaluate_narrator_summary_color as executor

from scripts.narrator_summary_only import measure_summary_words

ROOT = Path(__file__).resolve().parents[1]

RUNNER = ROOT / "scripts/run_groq_summary_color_probe.ps1"

EVALUATOR = "scripts/evaluate_narrator_summary_color.py"

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
        row = {"kind": "summary_color_call", "case_id": case_id, "call_made": True,
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
        return {"kind": "summary_color_skip", "case_id": executor.CASE_IDS[index],
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
    runner = project / "scripts/run_groq_summary_color_probe.ps1"
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

REPLACEMENTS={'summary_attachment': 'summary_color', 'record-summary-attachment-qwen-observation-v1': 'record-summary-color-qwen-observation-v1', 'observatory-a': 'reading-room-a', 'observatory-b': 'reading-room-b', 'f21d9a8d17017626a28bcc3b0f1c97bf02b9a24e8057789baa96e8832de9ac8f': '2795503b86b084b24c7864f5368f12a5acc9889601a57b24e6e557d977cf710a', '$inputs.prompt.variant -cne "record-summary-only-v1"': '$inputs.prompt.variant -cne "record-summary-budget-v1"', 'evals/narrator/prompts/record-summary-only-v1.md': 'evals/narrator/prompts/record-summary-budget-v1.md', '71df999d6f1ff6f77ec2bd9f2744878e11ee31a43e4f3abd4302499e81c91146': '6a59513d8b99659f00548ed3d5300f3137e402f40a2e3f7fc26d674dbc9964f4', '94c47c36b620628bb07b74f308adb6d556db7050f31d2aa2c262daa693c0a5d7': '1eca37a720951743b0f989b3ed31b1fd726663345bad71016179966d5548d5ce', 'evals/narrator/reports/record-summary-attachment-dossier-21cf338b-2026-09-07.json': 'evals/narrator/reports/record-summary-color-dossier-95dd9fd2-2026-09-07.json', '0a81ebf88c7ef86e0830404933663ab4b5db6ab2768186f4aa7e24a3c5f405a7': 'd998a881504ac935a7a4a5ca248afa33b2a78c966668af3e52a0fcacd1a44915', '$estimatedTokens = @(170, 168)': '$estimatedTokens = @(172, 172)', '3072': '768', '6144': '1536', 'Summary attachment Qwen probe': 'Summary color Qwen probe', '3024c009e6ce91efac84ba39ba53c5b72b30fffd4e3d0bbdc6cceaaf116457d8': 'aa1def53c01ab1ff078e85634aaafe53d29f4531acd85fd537161356ff6b669b', '0309cd9a4aad5f54f45c792f1168616a65a69bdffd7eb97deb07674089c91b1c': '7045a45a0cc35c0780f4eed0e0f66fe259dbfa8fd08f5ae2a0180600c0e15ced', '7a56db6bcaadb137df1aeb4e49652151ca12f0b3819e7b90ccfdd2c054454176': '149c1ffdd529220e034dad6c372da216e51db67637c81484176d22a237068f3d', '51265c46c0acf56e6a8b85470715e54606f65dabf6b146db415fb28ed4e4312d': '25be06f95bc681bf84a9cf7c4fd62fedd726c150c508a4a3cd28b7307e339065', '55ed1c4959dfd9d335acfc2760479ec2d15dd2fb0c59e544391aa2c49a2f2790': '890dc5a5bed0be1a2e855a73fb424d04aa846a99206d6c94c66248b0dfc99d23', 'c99430cb5ab4770f8c992d43987d919720daa911fcbb224c548f84090c8192cf': '722e7eaf506e43050f94834beb6c32eb90ca1cf221fb0ab4fd6a81ef4575800b', 'a5448889ea27e163957405c5f5ca79eca73dedacda020832afaa20297a709d2d': 'ef2b18269066b38df7ef546ae7b292cb8fbb1fd90908b4330ced21759d396eb8', '7206a854871290ae9bc592a30468bec9ba51de3c81e4c713d834395c7b0a04d2': '032ce8babd9e14b2c55515c7e502c05c1ca2126ce41c2f49c50ba3edd47a5d3a'}

def test_color_wrapper_has_only_the_declared_finite_derivation():
    old=(ROOT/"scripts/run_groq_summary_attachment_probe.ps1").read_bytes()
    assert hashlib.sha256(old).hexdigest()=="3afa60dab804808605c12d5fd4666a428ceb042bb0a3dbc64a38b390903e34fe"
    for before,after in REPLACEMENTS.items():
        assert before.encode() in old
        old=old.replace(before.encode(),after.encode())
    assert RUNNER.read_bytes()==old


@pytest.mark.parametrize("available_shell",SHELLS or [None],ids=lambda p:Path(p).stem if p else "unavailable")
def test_color_wrapper_syntax(available_shell,tmp_path):
    if available_shell is None: pytest.skip("PowerShell unavailable")
    command="$tokens=$null; $errors=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile("+_ps(RUNNER)+",[ref]$tokens,[ref]$errors); if ($errors.Count) { exit 1 }"
    result=_shell_run(available_shell,command,tmp_path)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize("mode,code,call_count,schema_count",[
    ("normal",0,2,2),("availability_first",2,1,0),("schema_second",1,2,1),
    ("local_before_first",3,0,0),("cancel_after_first",130,1,1),
    ("cancel_after_second",130,2,2),("long_first",0,2,2),
])
def test_color_real_summaries_preserve_prefix_stop_exit_and_word_nonblocking(shell,tmp_path,metadata,mode,code,call_count,schema_count):
    result,calls,output=_wrapper(shell,tmp_path,metadata,code=code,mode=mode)
    assert result["exit_code"]==code,output
    assert len(calls)==2
    assert calls[0]["arguments"]==["--preflight"] and calls[0]["key_present"] is False
    assert calls[1]["key_supplied"] is True
    args=calls[1]["arguments"]; batch=args[args.index("--batch-id")+1]
    assert str(UUID(batch))==batch
    assert args==["--live","--allow-synthetic-only","--batch-id",batch,"--api-key-env","GROQ_API_KEY"]
    doc=json.loads((tmp_path/"isolated project/eval-results/synthetic-run/summary.json").read_text())
    summary=doc["summary"]
    assert summary["calls_made"]==call_count and summary["cases_skipped"]==2-call_count
    assert summary["schema_valid"]==schema_count
    assert [x["case_id"] for x in summary["case_measurements"]]==["reading-room-a","reading-room-b"]
    assert [x["case_id"] for x in summary["provider_observations"]]==list(executor.CASE_IDS[:call_count])
    assert "768 tokens each and 1536 total" in output
    if mode=="long_first":
        assert summary["case_measurements"][0]["instruction_measurements"]["within_word_limit"] is False
        assert summary["operational_probe_passed"] is True
    assert summary["semantic_fidelity_review"]=={"status":"not_performed","approval":None}


@pytest.mark.parametrize("blank",[False,True])
def test_color_secure_key_order_and_absent_environment_restoration(shell,tmp_path,metadata,blank):
    result,calls,output=_wrapper(shell,tmp_path,metadata,blank=blank,preexisting=False)
    assert result["exit_code"]==(3 if blank else 0)
    assert len(calls)==(1 if blank else 2)
    assert calls[0]["key_present"] is False
    if blank: assert "(credential validation)" in output


@pytest.mark.parametrize("change",[
    ("purpose","summary_attachment_qwen_probe"),
    ("protocol","record-summary-budget-v1"),
    ("summary_generation_parameters.requested.max_output_tokens",3072),
    ("summary_generation_parameters.transmitted.max_output_tokens",3072),
    ("summary_generation_parameters.max_total_output_tokens",6144),
    ("inputs.corpus.file","record_summary_attachment_cases_v1.json"),
    ("inputs.corpus.sha256","f21d9a8d17017626a28bcc3b0f1c97bf02b9a24e8057789baa96e8832de9ac8f"),
    ("inputs.prompt.variant","record-summary-only-v1"),
    ("inputs.prompt.sha256","94c47c36b620628bb07b74f308adb6d556db7050f31d2aa2c262daa693c0a5d7"),
    ("inputs.cases.0.case_id","reading-room-b"),
    ("inputs.dossier.requests.1.body_sha256","25be06f95bc681bf84a9cf7c4fd62fedd726c150c508a4a3cd28b7307e339065"),
    ("inputs.stopping_policy.stop_on_first_operational_failure",False),
    ("inputs.stopping_policy.order.0","reading-room-b"),
],ids=lambda c:c[0])
def test_color_caps_corpus_prompt_order_and_stop_policy_fail_before_key(shell,tmp_path,metadata,change):
    result,calls,output=_wrapper(shell,tmp_path,metadata,preflight_change=change)
    assert result["exit_code"]==3 and len(calls)==1
    assert calls[0]["key_present"] is False and "(offline preflight)" in output


@pytest.mark.parametrize("change",[
    ("evaluation_status","local_error"),
    ("summary.calls_made",3),
    ("summary.cases_skipped",1),
    ("summary.provider_observations.0.case_id","reading-room-b"),
    ("summary.case_measurements.1.case_id","reading-room-a"),
    ("summary.semantic_fidelity_review.approval",True),
    ("summary.route_verification.verified_calls",1),
],ids=lambda c:c[0])
def test_color_result_rejects_wrong_order_counts_status_and_approval(shell,tmp_path,metadata,change):
    result,calls,output=_wrapper(shell,tmp_path,metadata,live_change=change)
    assert result["exit_code"]==3 and len(calls)==2
    assert "(summary verification)" in output


@pytest.mark.parametrize("which",["measurement_for_skip","second_without_first"])
def test_color_partial_results_cannot_invent_skipped_case_or_erase_first_success(shell,tmp_path,metadata,which):
    if which=="measurement_for_skip":
        mode,code="cancel_after_first",130
        change=("summary.case_measurements.1.instruction_measurements",measure_summary_words("Resumo sintético válido."))
    else:
        mode,code="schema_second",1
        change=("summary.case_measurements.0.instruction_measurements",None)
    result,calls,output=_wrapper(shell,tmp_path,metadata,mode=mode,code=code,live_change=change)
    assert result["exit_code"]==3 and len(calls)==2
    assert "(summary verification)" in output


def test_color_rejects_ambiguous_new_run_without_retry(shell,tmp_path,metadata):
    result,calls,_=_wrapper(shell,tmp_path,metadata,mode="duplicate_summary")
    assert result["exit_code"]==3 and len(calls)==2
