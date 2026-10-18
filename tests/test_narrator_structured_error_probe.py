"""One fixed faithful request; offline errors and PowerShell credential boundaries."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from pydantic import SecretStr

from api.llm.contract import (
    AdapterIdentity, ErrorCategory, InvocationEvidence, LLMInvocationError,
    NormalizedError, OperationPhase, Provenance, ProvenanceValue, StructuredGenerationResult,
)
from scripts import evaluate_narrator_models as module

ROOT = module.PROJECT_ROOT
MANIFEST = ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
CANDIDATE = "gpt-oss-120b-groq-free-synthetic-low"
FAITHFUL = "scene-faithful-v1"
PROMPT_HASH = "76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2"
RUNNER = ROOT / "scripts/run_groq_structured_error_probe.ps1"
SHELLS = [path for name in ("pwsh", "powershell") if (path := shutil.which(name))]


def _proposal():
    return module.FocusedSceneContinuationProposal.model_validate({
        "n": "A chuva fina escorre pelos postes e deixa o asfalto brilhando sob a luz vermelha. "
             "Você está num beco estreito, entre caixotes úmidos e uma parede coberta de pichações antigas. "
             "Um letreiro falha acima da rua, enquanto passos distantes quebram o silêncio sem decidir seu rumo.",
        "o": "unresolved", "l": "Beco sob néon",
        "s": "O Neófito está em um beco estreito sob um letreiro instável.",
        "f": [{"k": "observation", "s": "Caixotes úmidos ocupam um lado do beco.", "a": []}],
        "t": ["Identificar a origem dos passos"], "q": "O que você faz primeiro?",
    })


def _gateway(monkeypatch, *, category=None, code="http_400", wrong_model=False, internal=False):
    requests = []
    class Gateway:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == module.GROQ_OFFICIAL_BASE_URL
        async def test_connection(self, request):
            pytest.fail("text diagnostic is forbidden")
        def stream_text(self, request):
            pytest.fail("streaming diagnostic is forbidden")
        async def generate_structured(self, request):
            requests.append(request)
            if internal:
                raise RuntimeError("synthetic-sensitive-error-payload")
            now = datetime.now(timezone.utc)
            evidence = InvocationEvidence(provenance=Provenance(
                invocation_id=request.invocation_id, requested_target=request.target,
                adapter=AdapterIdentity(name="groq-chat-completions", version="1.0"),
                effective_provider=ProvenanceValue.observed("Groq"),
                effective_model=ProvenanceValue.reported("unexpected/model" if wrong_model else request.target.model),
                started_at=now, finished_at=now,
            ))
            if category:
                raise LLMInvocationError(NormalizedError(
                    category=category, code=code, status_code=400 if category == ErrorCategory.INVALID_REQUEST else None,
                    phase=OperationPhase.RESPONSE, invocation_id=request.invocation_id, target=request.target,
                    safe_message="Safe synthetic provider failure.", evidence=evidence, retryable=True,
                ))
            return StructuredGenerationResult(value=_proposal(), evidence=evidence)
    monkeypatch.setattr(module, "GroqAdapter", Gateway)
    return requests, Gateway


def _run(**changes):
    arguments = dict(
        candidate=module.load_candidates(MANIFEST)[CANDIDATE], corpus=module.load_corpus(module.DEFAULT_CORPUS),
        api_key=SecretStr("synthetic-test-key"), repetitions=1, deadline_seconds=60,
        temperature=0.65, max_output_tokens=768, scene_focus=True, structured_error_probe=True,
        prompt=module.load_evaluation_prompt(FAITHFUL)[1],
    )
    arguments.update(changes)
    return asyncio.run(module.evaluate_candidate(**arguments))


def _args(**options):
    selected = {"live": None, "structured-error-probe": None, "manifest": str(MANIFEST),
                "candidate": CANDIDATE, "allow-synthetic-only": None, "prompt-variant": FAITHFUL,
                "max-output-tokens": "768"}
    selected.update(options)
    return [item for key, value in selected.items() if value is not False
            for item in (["--" + key] if value is None else ["--" + key, str(value)])]


def test_probe_is_exactly_the_actual_faithful_opening_request(monkeypatch):
    requests, gateway = _gateway(monkeypatch)
    records, summary = _run(inter_call_delay_seconds=300)
    assert len(requests) == len(records) == 1
    actual = requests[0]
    episode = module.load_corpus(module.DEFAULT_CORPUS)["episodes"][0]
    asyncio.run(module._run_turn(
        gateway=gateway(base_url=module.GROQ_OFFICIAL_BASE_URL), target=actual.target,
        prompt=module.load_evaluation_prompt(FAITHFUL)[1], episode_id=episode["episode_id"],
        turn=episode["turns"][0], repetition=1, scene=None, known_context=episode["known_context"],
        protected_secrets=(), deadline_seconds=60, temperature=0.65, max_output_tokens=768,
        scene_focus=True, last_focus=None,
    ))
    baseline = requests[1]
    assert actual.model_dump(exclude={"invocation_id", "deadline"}) == baseline.model_dump(exclude={"invocation_id", "deadline"})
    assert actual.response_model is module.FocusedSceneContinuationProposal
    assert actual.cancellation.is_cancelled is baseline.cancellation.is_cancelled is False
    assert hashlib.sha256(actual.messages[0].content.encode()).hexdigest() == PROMPT_HASH
    assert records[0]["generation_context"]
    assert records[0]["schema_valid"] is records[0]["admitted"] is True
    assert summary["purpose"] == "operational_probe"
    assert summary["evaluation_stage"] == summary["probe_kind"] == "structured_error_probe"
    assert summary["full_evaluation"] is summary["runtime_promoted"] is False
    assert summary["human_review_required"] is True
    assert summary["cap_001_status"] == "not_evaluated"
    assert summary["automated_gates_passed"] is summary["diagnostics_executed"] is False
    assert summary["automatic_retries"] == 0
    assert summary["narrative_calls"] == 1
    assert summary["operational_probe_passed"] is True
    assert module._evaluation_exit_code(summary) == 0


@pytest.mark.parametrize("category,code,exit_code", [
    (ErrorCategory.INVALID_REQUEST, "http_400", 1),
    (ErrorCategory.INVALID_REQUEST, "groq_json_validate_failed", 1),
    (ErrorCategory.INVALID_STRUCTURED_OUTPUT, "synthetic_structure_failure", 1),
    (ErrorCategory.RATE_LIMITED, "synthetic_rate_limit", 2),
    (ErrorCategory.TIMEOUT, "synthetic_timeout", 2),
])
def test_error_remains_one_attempt_and_never_becomes_quality_approval(monkeypatch, category, code, exit_code):
    requests, _ = _gateway(monkeypatch, category=category, code=code)
    records, summary = _run()
    assert len(requests) == len(records) == 1
    assert records[0]["llm_error"]["category"] == category.value
    assert records[0]["llm_error"]["code"] == code
    assert summary["failure"]["code"] == code
    assert summary["automatic_retries"] == 0
    assert summary["operational_probe_passed"] is summary["automated_gates_passed"] is False
    assert module._evaluation_exit_code(summary) == exit_code
    assert "synthetic-sensitive-error-payload" not in json.dumps([records, summary])


def test_route_mismatch_never_counts_as_probe_success(monkeypatch):
    requests, _ = _gateway(monkeypatch, wrong_model=True)
    _, summary = _run()
    assert len(requests) == 1
    assert summary["route_verification"]["status"] == "mismatch"
    assert summary["operational_probe_passed"] is False


@pytest.mark.parametrize("changes", [
    {"repetitions": 3}, {"opening_probe": True}, {"scene_focus": False},
    {"prompt": "alternative-system"}, {"max_output_tokens": 769}, {"max_output_tokens": 128},
    {"temperature": 0}, {"deadline_seconds": 61},
])
def test_direct_probe_rejects_scope_changes_before_gateway(monkeypatch, changes):
    monkeypatch.setattr(module, "GroqAdapter", lambda **_: pytest.fail("gateway constructed"))
    with pytest.raises(ValueError):
        _run(**changes)


def test_direct_probe_rejects_modified_corpus_or_candidate(monkeypatch):
    monkeypatch.setattr(module, "GroqAdapter", lambda **_: pytest.fail("gateway constructed"))
    corpus = module.load_corpus(module.DEFAULT_CORPUS)
    corpus["episodes"][0]["turns"][0]["player_input"] = "different data"
    candidate = module.load_candidates(MANIFEST)[CANDIDATE]
    for changes in ({"corpus": corpus}, {"candidate": replace(candidate, model="unapproved/model")}):
        with pytest.raises(ValueError):
            _run(**changes)


@pytest.mark.parametrize("options", [
    {"live": False}, {"opening-probe": None}, {"replay": "probe.jsonl"}, {"repetitions": "3"},
    {"candidate": "qwen-3.8-27b-groq-free-synthetic-nonthink"}, {"prompt-variant": False},
    {"prompt-variant": "scene-attributed-v1"}, {"max-output-tokens": "769"},
    {"max-output-tokens": "128"}, {"temperature": "0"}, {"deadline-seconds": "61"},
])
def test_cli_refuses_scope_changes_before_credential_read(monkeypatch, options):
    original = module.os.environ.get
    def guarded(name, default=None):
        if name.endswith("API_KEY"):
            pytest.fail("credential read before scope admission")
        return original(name, default)
    monkeypatch.setattr(module.os.environ, "get", guarded)
    monkeypatch.setattr(module, "evaluate_candidate", lambda **_: pytest.fail("evaluation reached"))
    with pytest.raises(SystemExit, match="fixed faithful opening configuration"):
        module.main(_args(**options))


@pytest.mark.parametrize("label", ["manifest", "corpus"])
def test_cli_refuses_alternative_paths_before_credential_read(monkeypatch, tmp_path, label):
    original_resolver = module._resolve_json_input
    monkeypatch.setattr(module, "_resolve_json_input", lambda path, *, label: tmp_path / path.name
                        if label == selected else original_resolver(path, label=label))
    selected = label
    monkeypatch.setattr(module, "_api_key_env_name", lambda *a: pytest.fail("credential stage reached"))
    with pytest.raises(SystemExit, match="fixed Groq manifest and synthetic corpus paths"):
        module.main(_args())


@pytest.mark.parametrize("outcome", ["success", "invalid_request", "internal", "cancel"])
def test_cli_persists_distinct_safe_artifacts_with_adapter_provenance(monkeypatch, tmp_path, capsys, outcome):
    requests, _ = _gateway(monkeypatch, category=ErrorCategory.INVALID_REQUEST if outcome == "invalid_request" else None,
                           code="groq_json_validate_failed", internal=outcome == "internal")
    if outcome == "cancel":
        async def cancelled(*a, **k):
            raise asyncio.CancelledError
        monkeypatch.setattr(module, "evaluate_candidate", cancelled)
    sentinel = "synthetic-probe-key-do-not-persist"
    monkeypatch.setenv("GROQ_API_KEY", sentinel)
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    result = module.main(_args(**{"batch-id": "synthetic-batch"}))
    assert result == {"success": 0, "invalid_request": 1, "internal": 3, "cancel": 130}[outcome]
    assert len(requests) == (0 if outcome == "cancel" else 1)
    path, = tmp_path.glob("*/summary.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["purpose"] == "operational_probe"
    assert document["probe_kind"] == "structured_error_probe"
    assert document["runtime_promoted"] is document["full_evaluation"] is False
    assert document["automatic_retries"] == 0
    assert document["diagnostics_executed"] is False
    assert document["human_review_required"] is True
    assert document["cap_001_status"] == "not_evaluated"
    assert document["inputs"]["structured_error_probe_adapter"] == {
        "file": "api/llm/adapters/groq.py", "sha256": module._sha256(ROOT / "api/llm/adapters/groq.py"),
    }
    assert document["inputs"]["scene_focus_experiment"]["response_schema_sha256"]
    assert document["evaluation_pacing"]["diagnostic_rate_limit_retry"] == {"enabled": False, "maximum_attempts_per_probe": 0}
    persisted = "".join(item.read_text(encoding="utf-8") for item in path.parent.iterdir())
    assert sentinel not in persisted
    assert "synthetic-sensitive-error-payload" not in persisted
    console = capsys.readouterr().out
    assert sentinel not in console
    assert "synthetic-sensitive-error-payload" not in console
    assert "groq_json_validate_failed" not in console
    if outcome in {"success", "invalid_request"}:
        record_file, = path.parent.glob("*.jsonl")
        lines = record_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["purpose"] == "operational_probe"
        assert record["probe_kind"] == "structured_error_probe"
        assert record["structured_error_probe_adapter"] == document["inputs"]["structured_error_probe_adapter"]


def test_structured_probe_cannot_be_imported_as_full_replay(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "_resolve_replay_input", lambda _: tmp_path / "probe.jsonl")
    monkeypatch.setattr(module, "_resolve_output_dir", lambda _: tmp_path)
    monkeypatch.setattr(module, "load_evaluation_records", lambda _: [{"purpose": "operational_probe", "probe_kind": "structured_error_probe"}])
    with pytest.raises(SystemExit, match="cannot be replayed as a CAP-001"):
        module.main(["--replay", "probe.jsonl", "--manifest", str(MANIFEST), "--candidate", CANDIDATE])


def _ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def _shell_run(shell, command, tmp_path):
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment.pop("PSModulePath", None)
    return subprocess.run([shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
                          cwd=tmp_path, env=environment, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=25)


@pytest.fixture(params=SHELLS or [None], ids=lambda p: Path(p).stem if p else "unavailable")
def available_shell(request):
    if request.param is None:
        pytest.skip("PowerShell unavailable")
    return request.param


@lru_cache(maxsize=None)
def _policy(shell):
    result = _shell_run(shell, "Get-ExecutionPolicy", ROOT)
    return result.stdout.strip() if result.returncode == 0 else "Unavailable"


@pytest.fixture
def shell(available_shell):
    if _policy(available_shell) in {"Unavailable", "Restricted", "AllSigned"}:
        pytest.skip("Host execution policy/module prevents execution; policy is not bypassed")
    return available_shell


def test_wrapper_parses_in_each_available_shell(available_shell, tmp_path):
    result = _shell_run(available_shell, f"""
$tokens=$null; $errors=$null
$null=[System.Management.Automation.Language.Parser]::ParseFile({_ps(RUNNER)},[ref]$tokens,[ref]$errors)
if ($errors.Count) {{ exit 1 }}
""", tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def _wrapper(shell, tmp_path, *, code=0, mode="normal", preexisting=True, blank=False):
    project = tmp_path / "isolated project"
    runner = project / "scripts/run_groq_structured_error_probe.ps1"
    runner.parent.mkdir(parents=True)
    source = RUNNER.read_text(encoding="utf-8")
    assignment = '$python = Join-Path $projectRoot ".venv\\Scripts\\python.exe"'
    assert source.count(assignment) == 1
    source = source.replace(assignment, '$python = ' + _ps(Path(sys.executable).resolve()))
    runner.write_text(source, encoding="utf-8")
    for relative in ("evals/narrator/groq_candidates_2026-09-05.json", "evals/narrator/corpus_v1.json",
                     "evals/narrator/prompts/scene-faithful-v1.md", "api/llm/adapters/groq.py"):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture", encoding="utf-8")
    (project / "config.json").write_text(json.dumps({"code": code, "mode": mode}), encoding="utf-8")
    evaluator = project / "scripts/evaluate_narrator_models.py"
    evaluator.write_text(NATIVE_EVALUATOR, encoding="utf-8")
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


NATIVE_EVALUATOR = r'''
import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/"config.json").read_text())
arguments=sys.argv[1:]
def option(name): return arguments[arguments.index(name)+1]
def digest(path): return hashlib.sha256((root/path).read_bytes()).hexdigest()
call={"arguments":arguments,"key_supplied":os.environ.get("GROQ_API_KEY")=="synthetic-supplied-sentinel"}
(root/"calls.json").write_text(json.dumps([call]))
code,mode=config["code"],config["mode"]
parameter={"temperature":0.65,"max_output_tokens":768}
document={
 "batch_id":option("--batch-id"),"selected_candidate_id":option("--candidate"),"process_exit_code":code,
 "purpose":"operational_probe","probe_kind":"structured_error_probe","full_evaluation":False,
 "runtime_promoted":False,"human_review_required":True,"synthetic_only":True,"cap_001_status":"not_evaluated",
 "repetitions":1,"diagnostics_executed":False,"automatic_retries":0,
 "narrative_generation_parameters":{"deadline_seconds":60,"requested":parameter.copy(),"transmitted":parameter.copy()},
 "evaluation_pacing":{"diagnostic_rate_limit_retry":{"enabled":False,"maximum_attempts_per_probe":0}},
 "evaluator":{"file":"scripts/evaluate_narrator_models.py","sha256":digest("scripts/evaluate_narrator_models.py")},
 "inputs":{
  "prompt":{"variant":"scene-faithful-v1","file":"evals/narrator/prompts/scene-faithful-v1.md","sha256":"76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2"},
  "manifest":{"file":"groq_candidates_2026-09-05.json","sha256":digest("evals/narrator/groq_candidates_2026-09-05.json")},
  "corpus":{"file":"corpus_v1.json","sha256":digest("evals/narrator/corpus_v1.json")},
  "structured_error_probe_adapter":{"file":"api/llm/adapters/groq.py","sha256":digest("api/llm/adapters/groq.py")},
  "scene_focus_experiment":{"version":"scene-faithful-v1","context_contract_version":"scene-focus-v1","baseline_prompt_variant":"scene-attributed-v1","interventions":["system_prompt"],"causal_comparison":False,"complete_ab_experiment":False,"runtime_promoted":False,"human_review_required":True,"response_schema_sha256":"bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2"},
 },
 "summary":{"purpose":"operational_probe","probe_kind":"structured_error_probe","evaluation_stage":"structured_error_probe","narrative_calls":1,"automated_gates_passed":False,"operational_probe_passed":code==0},
}
changes={
 "wrong_batch":("batch_id","other"),"wrong_candidate":("selected_candidate_id","other"),
 "wrong_exit":("process_exit_code",130),"wrong_purpose":("purpose","full_evaluation"),
 "wrong_kind":("probe_kind","opening_probe"),"promoted":("runtime_promoted",True),
 "string_false":("full_evaluation","False"),"no_review":("human_review_required",False),
 "retries":("automatic_retries",1),"diagnostics":("diagnostics_executed",True),
}
if mode in changes:
 field,value=changes[mode]; document[field]=value
if mode=="wrong_adapter_hash": document["inputs"]["structured_error_probe_adapter"]["sha256"]="a"*64
if mode=="wrong_evaluator_hash": document["evaluator"]["sha256"]="a"*64
if mode=="wrong_prompt_hash": document["inputs"]["prompt"]["sha256"]="a"*64
if mode=="wrong_schema_hash": document["inputs"]["scene_focus_experiment"]["response_schema_sha256"]="a"*64
if mode=="wrong_baseline": document["inputs"]["scene_focus_experiment"]["baseline_prompt_variant"]="scene-grounded-v1"
if mode=="wrong_budget": document["narrative_generation_parameters"]["transmitted"]["max_output_tokens"]=769
if mode=="wrong_count": document["summary"]["narrative_calls"]=2
if mode=="quality_approved": document["summary"]["automated_gates_passed"]=True
if mode!="missing_summary":
 folder=root/"eval-results"/"synthetic-run"; folder.mkdir(parents=True)
 (folder/"summary.json").write_text(json.dumps(document))
 if mode=="duplicate_summary":
  duplicate=root/"eval-results"/"duplicate"; duplicate.mkdir()
  (duplicate/"summary.json").write_text(json.dumps(document))
print("Offline synthetic structured probe child finished.")
sys.exit(code)
'''


@pytest.mark.parametrize("preexisting", [False, True])
@pytest.mark.parametrize("code", [0, 1, 2, 3, 130])
def test_wrapper_is_one_fixed_native_call_and_restores_environment(shell, tmp_path, preexisting, code):
    result, calls, output = _wrapper(shell, tmp_path, preexisting=preexisting, code=code)
    assert result["exit_code"] == code
    assert len(calls) == 1
    assert calls[0]["key_supplied"] is True
    arguments = calls[0]["arguments"]
    assert "--structured-error-probe" in arguments
    for name,value in (("--candidate",CANDIDATE),("--prompt-variant",FAITHFUL),("--repetitions","1"),
                       ("--deadline-seconds","60"),("--temperature","0.65"),("--max-output-tokens","768")):
        assert arguments[arguments.index(name)+1] == value
    assert "--opening-probe" not in arguments
    assert "--replay" not in arguments
    assert "never approves narrative quality, runtime or CAP-001" in output


@pytest.mark.parametrize("preexisting", [False, True])
def test_wrapper_blank_key_never_calls_child(shell, tmp_path, preexisting):
    result,calls,_ = _wrapper(shell,tmp_path,preexisting=preexisting,blank=True)
    assert result["exit_code"] == 3
    assert calls == []


@pytest.mark.parametrize("mode", [
    "wrong_batch","wrong_candidate","wrong_exit","wrong_purpose","wrong_kind","promoted","string_false",
    "no_review","retries","diagnostics","wrong_adapter_hash","wrong_evaluator_hash","wrong_prompt_hash",
    "wrong_schema_hash","wrong_baseline","wrong_budget","wrong_count","quality_approved","missing_summary","duplicate_summary",
])
def test_wrapper_rejects_incoherent_artifacts_without_retry_or_key_leak(shell,tmp_path,mode):
    result,calls,_ = _wrapper(shell,tmp_path,mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 1


@pytest.mark.parametrize("entry", ["cli", "direct"])
def test_faithful_system_drift_is_refused_before_credential_or_gateway(monkeypatch, entry):
    prompt_path, prompt = module.load_evaluation_prompt(FAITHFUL)
    monkeypatch.setattr(module, "load_evaluation_prompt", lambda _: (prompt_path, prompt + " changed"))
    monkeypatch.setattr(module, "_api_key_env_name", lambda *a: pytest.fail("credential stage reached"))
    monkeypatch.setattr(module, "GroqAdapter", lambda **k: pytest.fail("gateway constructed"))
    if entry == "cli":
        with pytest.raises(SystemExit, match="fixed faithful fingerprint"):
            module.main(_args())
    else:
        with pytest.raises(ValueError, match="fixed faithful opening configuration"):
            _run()


def test_focused_actor_validation_path_survives_summary_and_console():
    structure = {"stage": "schema_validation", "issues": [{"path": ["f", 0, "a"], "code": "missing"}], "truncated": False}
    record = {"kind": "narrative_turn", "call_made": True, "schema_valid": False, "admitted": False,
              "llm_error": {"category": "invalid_structured_output", "code": "structured_output_schema_mismatch",
                            "structure_validation": structure}}
    summary = module._summarize_opening_probe(module.load_candidates(MANIFEST)[CANDIDATE], record, structured_error_probe=True)
    assert summary["failure"]["structure_validation"] == structure
    assert "missing at f[0].a" in module._opening_probe_diagnostic(summary)
    assert "missing at f[0].a" not in module._opening_probe_structure_diagnostic(structure)


def test_local_context_failure_never_dispatches_and_is_reported_as_local(monkeypatch):
    requests, _ = _gateway(monkeypatch)
    def unavailable(*a, **k):
        raise module.SceneFocusBudgetError("synthetic limit")
    monkeypatch.setattr(module, "build_focused_packet", unavailable)
    records, summary = _run()
    assert requests == []
    assert len(records) == 1
    assert summary["local_failure"] is True
    assert summary["narrative_calls"] == 0
    assert module._evaluation_exit_code(summary) == 3


@pytest.mark.parametrize("preexisting", [False, True])
def test_wrapper_preserves_native_cancellation_without_summary_and_restores_key(shell, tmp_path, preexisting):
    result, calls, output = _wrapper(shell, tmp_path, code=130, mode="missing_summary", preexisting=preexisting)
    assert result["exit_code"] == 130
    assert len(calls) == 1
    assert "cancelled; no completed summary" in output


@pytest.mark.parametrize("mode", ["wrong_batch", "wrong_candidate", "wrong_kind", "duplicate_summary"])
def test_wrapper_cancellation_does_not_hide_new_incoherent_evidence(shell, tmp_path, mode):
    result, calls, _ = _wrapper(shell, tmp_path, code=130, mode=mode)
    assert result["exit_code"] == 3
    assert len(calls) == 1
