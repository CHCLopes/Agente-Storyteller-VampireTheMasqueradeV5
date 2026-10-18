"""Offline execution proofs for two dependent, attributed narrative sources."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
from datetime import timedelta
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from api.llm.contract import LLMInvocationError
from api.narrative_grounding import SourceProjection
from scripts import evaluate_narrator_source as m
from scripts.evaluate_narrator_source import NarrativeSourceObservationAdapter

KEY = "SYNTHETIC_SOURCE_KEY_NEVER_PERSIST"
LEAK = "UNTRUSTED_SOURCE_REASONING_OR_ERROR_NEVER_PERSIST"
QUESTION = "O que você faz agora?"
FIRST = (
    "A água escorre pelos vidros da estufa enquanto a chuva ressoa do lado de fora. "
    "Uma luminária oscila sobre a bancada; entre os vasos fechados, um ruído baixo "
    "acompanha o movimento irregular das folhas próximas à janela."
)
SECOND = (
    "A luminária continua oscilando sobre a bancada da estufa, e a chuva mantém seu "
    "ritmo contra os vidros. O ruído entre os vasos diminui por um instante; junto "
    "à janela, as folhas voltam a se mover lentamente."
)


@pytest.fixture
def pacing(monkeypatch):
    real_pacer = m.shared._CallPacer
    state = {"time": 0.0, "waits": []}
    async def sleep(seconds):
        state["waits"].append(seconds)
        state["time"] += seconds
    monkeypatch.setattr(m.shared, "_CallPacer", lambda interval: real_pacer(
        interval, _clock=lambda: state["time"], _sleeper=sleep))
    return state


def completion(turn_id, *, value=None, model=m.GROQ_QWEN_MODEL_ID, finish="stop"):
    return {
        "id": "synthetic-source-completion", "model": model,
        "choices": [{"finish_reason": finish, "message": {
            "content": json.dumps(value if value is not None else {
                "n": FIRST if turn_id == "observe" else SECOND, "q": QUESTION,
            }), "reasoning": LEAK,
        }}],
        "usage": {"prompt_tokens": 18, "completion_tokens": 30, "total_tokens": 48},
    }


def install(monkeypatch, pacing, handler=None):
    state = {"calls": [], "requests": [], "instances": []}
    class Gateway(NarrativeSourceObservationAdapter):
        def __init__(self, **kwargs):
            turn_id = kwargs["turn_id"]
            async def dispatch(request):
                state["calls"].append({"turn_id": turn_id, "request": request, "started": pacing["time"]})
                return handler(turn_id, request) if handler else httpx.Response(200, json=completion(turn_id))
            super().__init__(**kwargs, transport=httpx.MockTransport(dispatch))
            state["instances"].append(self)
        async def generate_structured(self, request):
            state["requests"].append(request)
            return await super().generate_structured(request)
        async def generate_text(self, request):
            pytest.fail("No diagnostic, fallback or extra call belongs to this probe")
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", Gateway)
    return state


def evaluate(prepared=None, **kwargs):
    return asyncio.run(m.evaluate_probe(
        m.prepare_experiment() if prepared is None else prepared,
        api_key=SecretStr(KEY), batch_id=str(uuid4()), **kwargs,
    ))


def artifact_run(monkeypatch, tmp_path, case_id=m.COURTYARD_CASE_ID):
    root = tmp_path / "results"
    monkeypatch.setattr(m, "OUTPUT_ROOT", root)
    def directory(invocation_id, started):
        path = root / f"{started.strftime('%Y%m%dT%H%M%SZ')}-{invocation_id}"
        path.mkdir(parents=True, exist_ok=False)
        return path
    monkeypatch.setattr(m, "_new_run_directory", directory)
    monkeypatch.setenv("GROQ_API_KEY", KEY)
    expected = tmp_path / "preflight.json"
    expected.write_text(m._canonical(m.prepare_experiment(case_id).metadata), encoding="utf-8")
    batch = str(uuid4())
    exit_code = m.main(["--live", "--case-id", case_id, "--allow-synthetic-only", "--batch-id", batch,
                        "--expected-preflight", str(expected)])
    summary_path, = root.glob("*/summary.json")
    jsonl = summary_path.with_name(m.CANDIDATE_ID + ".jsonl")
    document = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    return {"exit": exit_code, "summary_path": summary_path, "jsonl": jsonl,
            "expected": expected, "batch": batch, "document": document, "rows": rows, "case_id": case_id}


def persist_changes(bundle, *, recompute=False):
    if recompute:
        summary = m.summarize(bundle["rows"], status=bundle["document"]["evaluation_status"], case_id=bundle["case_id"])
        bundle["document"]["summary"] = summary
        bundle["document"]["process_exit_code"] = summary["process_exit_code"]
    bundle["jsonl"].write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in bundle["rows"]), encoding="utf-8")
    bundle["summary_path"].write_text(json.dumps(bundle["document"], ensure_ascii=False), encoding="utf-8")


def verify(bundle):
    return m.verify_artifacts(bundle["summary_path"], bundle["expected"], bundle["batch"], case_id=bundle["case_id"])


def test_preflight_is_keyless_and_has_no_client_or_unknown_second_request(monkeypatch, capsys):
    class NoCredentials(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY":
                pytest.fail("Preflight inspected credentials")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", NoCredentials())
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kwargs: pytest.fail("Preflight created a client"))
    prepared = m.prepare_experiment()
    request = m._make_request(prepared, 0, m.PREFLIGHT_BATCH)
    body = m._fixed_payload(request)
    user = json.loads(request.messages[1].content)
    assert user["turn"] == "observe"
    assert user["context"]["canonical_scene"] == {"location": "Estufa", "npcs_present": []}
    assert user["context"]["attributed_sources"] == []
    assert body["max_completion_tokens"] == 768 and body["temperature"] == .65
    assert body["reasoning_effort"] == "none" and "include_reasoning" not in body
    assert set(body["response_format"]["json_schema"]["schema"]["properties"]) == {"n", "q"}
    assert prepared.metadata["inputs"]["first_request"]["body_sha256"] == m._canonical_sha(body)
    assert "second_request" not in prepared.metadata["inputs"]
    assert m.main(["--preflight"]) == 0
    assert json.loads(capsys.readouterr().out) == prepared.metadata


def test_blank_key_cannot_allocate_artifacts_or_dispatch(monkeypatch, tmp_path):
    expected = tmp_path / "preflight.json"
    expected.write_text(m._canonical(m.prepare_experiment(m.COURTYARD_CASE_ID).metadata), encoding="utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "  ")
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("Empty key allocated a run"))
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kwargs: pytest.fail("Empty key client"))
    assert m.main(["--live", "--case-id", m.COURTYARD_CASE_ID, "--allow-synthetic-only", "--batch-id", str(uuid4()),
                   "--expected-preflight", str(expected)]) == 3
    with pytest.raises(ValueError, match="source_probe_blank_credential"):
        asyncio.run(m.evaluate_probe(m.prepare_experiment(), api_key=SecretStr(""), batch_id=str(uuid4())))


def test_native_two_call_chain_retains_full_prior_n_without_q_and_reconstructs_artifacts(monkeypatch, tmp_path, pacing):
    case_id = m.COURTYARD_CASE_ID
    def handler(turn_id, request):
        text = (FIRST if turn_id == "observe" else SECOND)
        if case_id == m.COURTYARD_CASE_ID:
            text = text.replace("estufa", "área coberta")
        return httpx.Response(200, json=completion(turn_id, value={"n": text, "q": QUESTION}))
    state = install(monkeypatch, pacing, handler)
    bundle = artifact_run(monkeypatch, tmp_path, case_id)
    rows = bundle["rows"]
    assert bundle["exit"] == 0
    assert [call["turn_id"] for call in state["calls"]] == list(m.TURN_IDS)
    assert len(state["instances"]) == 2 and state["instances"][0] is not state["instances"][1]
    assert all(row["schema_valid"] and row["policy_valid"] and row["projection_valid"] for row in rows)
    expected_texts = [FIRST, SECOND] if case_id == m.CASE_ID else [text.replace("estufa", "área coberta") for text in (FIRST, SECOND)]
    assert [row["source_projection"]["text"] for row in rows] == expected_texts
    assert all(row["case_id"] == case_id for row in rows)
    assert json.loads(state["requests"][0].messages[1].content)["context"]["canonical_scene"] == m.prepare_experiment(case_id).case["scene"]
    second_user = json.loads(state["requests"][1].messages[1].content)
    assert second_user["context"]["attributed_sources"] == [rows[0]["source_projection"]]
    assert QUESTION not in state["requests"][1].messages[1].content
    assert second_user["player_input"] == m.prepare_experiment(case_id).case["turns"][1]["player_input"]
    for call, row in zip(state["calls"], rows):
        assert row["request"]["body_sha256"] == m._canonical_sha(json.loads(call["request"].content))
        assert row["source_projection"]["source"]["session_id"] == bundle["batch"]
        assert row["source_projection"]["source"]["invocation_id"] == row["request"]["invocation_id"]
    report = verify(bundle)
    assert report["verified"] is True and report["process_exit_code"] == 0
    assert report["verification_scope"] == "local_artifact_consistency_not_provider_authentication"
    summary = bundle["document"]["summary"]
    assert summary["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert summary["canonical_admission"] is summary["runtime_promoted"] is summary["automated_gates_passed"] is False
    assert KEY not in json.dumps(rows) and LEAK not in json.dumps(rows)


def test_initial_and_between_pacing_with_deadline_after_post_wait_check(monkeypatch, pacing):
    start = m.utc_now()
    monkeypatch.setattr(m, "utc_now", lambda: start + timedelta(seconds=pacing["time"]))
    original = m._check_prepared
    checks = []
    def check(prepared):
        original(prepared)
        checks.append(pacing["time"])
        if len(checks) in (3, 5):
            pacing["time"] += 2
    monkeypatch.setattr(m, "_check_prepared", check)
    def handler(turn_id, request):
        pacing["time"] += 1
        return httpx.Response(200, json=completion(turn_id))
    state = install(monkeypatch, pacing, handler)
    evaluate()
    assert [call["started"] for call in state["calls"]] == [62, 124]
    assert [r.deadline for r in state["requests"]] == [start + timedelta(seconds=122), start + timedelta(seconds=184)]


@pytest.mark.parametrize("failure", ["429", "schema", "route", "policy", "length"])
def test_first_failure_stops_dependency_and_persists_verifiable_skip(monkeypatch, tmp_path, pacing, failure):
    def handler(turn_id, request):
        assert turn_id == "observe"
        if failure == "429":
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": LEAK}})
        value = {"n": True, "q": QUESTION} if failure == "schema" else {"n": "Você abre a porta. " + FIRST, "q": QUESTION} if failure == "policy" else None
        return httpx.Response(200, json=completion(turn_id, value=value,
            model="other-model" if failure == "route" else m.GROQ_QWEN_MODEL_ID,
            finish="length" if failure == "length" else "stop"))
    state = install(monkeypatch, pacing, handler)
    bundle = artifact_run(monkeypatch, tmp_path)
    first, skipped = bundle["rows"]
    assert len(state["calls"]) == 1 and bundle["exit"] == (2 if failure == "429" else 1)
    assert skipped["kind"] == "narrative_source_skip" and skipped["turn_id"] == "wait"
    assert skipped["call_made"] is False and skipped["skipped_reason"] == "previous_operational_failure"
    assert "source_projection" not in first
    assert first["schema_valid"] is (failure == "policy")
    assert ("response_structure" in first) is (failure == "policy")
    assert LEAK not in json.dumps(bundle["rows"])
    assert verify(bundle)["verified"] is True


def test_second_error_keeps_first_source_without_third_call(monkeypatch, tmp_path, pacing):
    def handler(turn_id, request):
        return httpx.Response(200, json=completion(turn_id)) if turn_id == "observe" else httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": LEAK}})
    state = install(monkeypatch, pacing, handler)
    bundle = artifact_run(monkeypatch, tmp_path)
    assert len(state["calls"]) == 2 and bundle["exit"] == 2
    assert bundle["rows"][0]["source_projection"]["text"] == FIRST
    assert "source_projection" not in bundle["rows"][1]
    assert bundle["document"]["summary"]["turns_skipped"] == 0
    assert verify(bundle)["verified"] is True


@pytest.mark.parametrize("change", ["case", "metadata", "target"])
def test_prepared_drift_is_rejected_before_gateway(monkeypatch, change):
    prepared = m.prepare_experiment()
    if change == "case":
        prepared.case["turns"][0]["player_input"] = "Abro a porta."
    elif change == "metadata":
        prepared.metadata["canonical_admission"] = 0
    else:
        prepared = replace(prepared, target=prepared.target.model_copy(update={"model": "other-model"}))
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kwargs: pytest.fail("Drift reached client"))
    with pytest.raises(ValueError, match="source_probe_prepared_drift"):
        evaluate(prepared)


def test_input_drift_during_wait_is_checked_before_dispatch(monkeypatch, pacing):
    prepared = m.prepare_experiment()
    class Pacer:
        def __init__(self, interval): self._clock = lambda: 0.0
        async def before_call(self, label):
            monkeypatch.setattr(m, "CASE_SHA256", "0" * 64)
    monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kwargs: pytest.fail("Drift after wait reached client"))
    with pytest.raises(ValueError, match="source_probe_input_fingerprint_changed"):
        evaluate(prepared)


@pytest.mark.parametrize("when", ["second_wait", "second_dispatch"])
def test_cancellation_preserves_exact_dependent_call_inventory(monkeypatch, tmp_path, pacing, when):
    if when == "second_wait":
        real = m.shared._CallPacer
        class Pacer:
            def __init__(self, interval):
                self.inner = real(interval)
                self._clock = self.inner._clock
                self.count = 0
            @property
            def _last_call_started_at(self): return self.inner._last_call_started_at
            @_last_call_started_at.setter
            def _last_call_started_at(self, value): self.inner._last_call_started_at = value
            async def before_call(self, label):
                self.count += 1
                if self.count == 2: raise asyncio.CancelledError()
                await self.inner.before_call(label)
        monkeypatch.setattr(m.shared, "_CallPacer", Pacer)
    def handler(turn_id, request):
        if when == "second_dispatch" and turn_id == "wait": raise asyncio.CancelledError()
        return httpx.Response(200, json=completion(turn_id))
    state = install(monkeypatch, pacing, handler)
    bundle = artifact_run(monkeypatch, tmp_path)
    assert bundle["exit"] == 130 and len(state["calls"]) == (1 if when == "second_wait" else 2)
    assert bundle["document"]["evaluation_status"] == "cancelled"
    assert bundle["rows"][0]["source_projection"]["text"] == FIRST
    assert verify(bundle)["verified"] is True


@pytest.mark.parametrize("mutation", ["budget", "system", "operation"])
def test_native_adapter_binds_approved_body_operation_and_single_use(mutation):
    prepared = m.prepare_experiment()
    exact = m._make_request(prepared, 0, str(uuid4()))
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion("observe"))
    adapter = NarrativeSourceObservationAdapter(
        turn_id="observe", approved_body_sha256=m._canonical_sha(m._fixed_payload(exact)),
        base_url=m.GROQ_OFFICIAL_BASE_URL, capability_set=m.shared._capabilities(prepared.candidate, prepared.target),
        api_key=SecretStr(KEY), reasoning_effort="none", transport=httpx.MockTransport(handler),
    )
    if mutation == "budget":
        changed = exact.model_copy(update={"parameters": exact.parameters.model_copy(update={"max_output_tokens": 3072})})
    elif mutation == "system":
        changed = exact.model_copy(update={"messages": (exact.messages[0].model_copy(update={"content": "Different SYSTEM"}), exact.messages[1])})
    else:
        changed = exact.model_copy(update={"operation": "narrative-source.wait"})
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(changed))
    assert calls == []
    asyncio.run(adapter.generate_structured(exact))
    with pytest.raises(LLMInvocationError):
        asyncio.run(adapter.generate_structured(exact))
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["second_user", "first_source", "order", "gate_bool", "summary", "preflight"])
def test_artifact_reconstruction_refuses_tampering(monkeypatch, tmp_path, pacing, mutation):
    install(monkeypatch, pacing)
    bundle = artifact_run(monkeypatch, tmp_path)
    if mutation == "second_user":
        bundle["rows"][1]["request"]["user_packet"] += "ALTERED"
    elif mutation == "first_source":
        bundle["rows"][0]["source_projection"]["text"] += " ALTERED"
    elif mutation == "order":
        bundle["rows"].reverse()
    elif mutation == "gate_bool":
        bundle["rows"][0]["projection_valid"] = 1
    elif mutation == "summary":
        bundle["document"]["summary"]["calls_made"] = 1
    else:
        expected = json.loads(bundle["expected"].read_text(encoding="utf-8"))
        expected["canonical_admission"] = 0
        bundle["expected"].write_text(json.dumps(expected), encoding="utf-8")
    persist_changes(bundle)
    with pytest.raises((ValueError, TypeError)):
        verify(bundle)


def test_successful_first_call_cannot_claim_completed_operational_skip(monkeypatch, tmp_path, pacing):
    install(monkeypatch, pacing)
    bundle = artifact_run(monkeypatch, tmp_path)
    second = bundle["rows"][1]
    for field in ("request", "response_structure", "source_projection", "evidence", "provider_observation",
                  "latency_seconds", "schema_valid", "policy_valid", "projection_valid", "route_status"):
        second.pop(field, None)
    second.update(kind="narrative_source_skip", call_made=False, skipped_reason="previous_operational_failure")
    with pytest.raises(ValueError):
        persist_changes(bundle, recompute=True)
        verify(bundle)


def test_local_projection_exception_keeps_valid_structure_and_verifiable_partial(monkeypatch, tmp_path, pacing):
    install(monkeypatch, pacing)
    original = m._project
    def fail(*args, **kwargs): raise RuntimeError(LEAK)
    monkeypatch.setattr(m, "_project", fail)
    bundle = artifact_run(monkeypatch, tmp_path)
    monkeypatch.setattr(m, "_project", original)
    first, skipped = bundle["rows"]
    assert bundle["exit"] == 3 and first["schema_valid"] is first["policy_valid"] is True
    assert first["projection_valid"] is False and "source_projection" not in first
    assert first["local_error"] == {"code": "local_narrative_source_failure", "stage": "projection"}
    assert first["response_structure"] == {"n": FIRST, "q": QUESTION}
    assert skipped["call_made"] is False and LEAK not in json.dumps(bundle["rows"])
    assert verify(bundle)["verified"] is True



def test_frozen_preflight_mismatch_is_refused_before_credential_read(monkeypatch, tmp_path):
    expected = tmp_path / "preflight.json"
    metadata = m.prepare_experiment(m.COURTYARD_CASE_ID).metadata
    metadata["canonical_admission"] = 0
    expected.write_text(json.dumps(metadata), encoding="utf-8")
    class NoCredentials(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("Changed preflight reached credential read")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", NoCredentials())
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kwargs: pytest.fail("Changed preflight client"))
    assert m.main(["--live", "--case-id", m.COURTYARD_CASE_ID, "--allow-synthetic-only", "--batch-id", str(uuid4()),
                   "--expected-preflight", str(expected)]) == 3


@pytest.mark.parametrize("status", ["local_error", "cancelled"])
def test_interrupted_artifact_requires_an_explicit_valid_stage(monkeypatch, tmp_path, pacing, status):
    install(monkeypatch, pacing)
    bundle = artifact_run(monkeypatch, tmp_path)
    bundle["document"]["evaluation_status"] = status
    last = bundle["rows"][1]
    if status == "local_error":
        last["local_error"] = {"code": "local_narrative_source_failure", "stage": None}
    else:
        last["cancelled"] = True
        last.pop("cancelled_stage", None)
    persist_changes(bundle, recompute=True)
    with pytest.raises(ValueError):
        verify(bundle)



def test_provider_snapshot_rejects_free_text_even_with_a_consistently_recomputed_summary(monkeypatch, tmp_path, pacing):
    install(monkeypatch, pacing)
    bundle = artifact_run(monkeypatch, tmp_path)
    bundle["rows"][0]["provider_observation"]["unbounded_free_text"] = LEAK
    persist_changes(bundle, recompute=True)
    assert bundle["document"]["summary"]["provider_observations"][0]["observation"]["unbounded_free_text"] == LEAK
    with pytest.raises(ValueError, match="source_probe_observation_shape_invalid"):
        verify(bundle)


def test_courtyard_selection_is_keyless_distinct_and_uses_the_same_system(monkeypatch, capsys):
    class NoCredentials(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("Case selection inspected credentials")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", NoCredentials())
    monkeypatch.setattr(m, "NarrativeSourceObservationAdapter", lambda **kw: pytest.fail("Case selection client"))
    old = m.prepare_experiment()
    new = m.prepare_experiment(m.COURTYARD_CASE_ID)
    assert old.case["scene"]["location"] == "Estufa"
    assert new.case["scene"] == {"location": "Pátio coberto", "npcs_present": []}
    assert new.prompt == old.prompt
    assert new.metadata["inputs"]["first_request"] != old.metadata["inputs"]["first_request"]
    assert m.main(["--preflight", "--case-id", m.COURTYARD_CASE_ID]) == 0
    assert json.loads(capsys.readouterr().out) == new.metadata
    with pytest.raises(ValueError, match="case_selection_invalid"):
        m.prepare_experiment("../../arbitrary-case.json")


def test_case_swap_before_live_is_rejected_before_credential_or_allocation(monkeypatch, tmp_path):
    expected = tmp_path / "old-preflight.json"
    expected.write_text(m._canonical(m.prepare_experiment().metadata), encoding="utf-8")
    class NoCredentials(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("Wrong case reached credential")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", NoCredentials())
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("Wrong case allocated run"))
    assert m.main(["--live", "--case-id", m.COURTYARD_CASE_ID, "--allow-synthetic-only",
                   "--batch-id", str(uuid4()), "--expected-preflight", str(expected)]) == 3


def test_courtyard_fingerprint_drift_is_rejected_before_dispatch(monkeypatch, pacing):
    prepared = m.prepare_experiment(m.COURTYARD_CASE_ID)
    state = install(monkeypatch, pacing)
    monkeypatch.setattr(m, "COURTYARD_CASE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="fingerprint_changed"):
        evaluate(prepared)
    assert state["calls"] == []


def test_case_identity_cannot_be_mixed_in_summary_or_verification(monkeypatch, tmp_path, pacing):
    install(monkeypatch, pacing)
    bundle = artifact_run(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="expected_preflight_changed"):
        m.verify_artifacts(bundle["summary_path"], bundle["expected"], bundle["batch"], case_id=m.CASE_ID)
    bundle["rows"][1]["case_id"] = m.CASE_ID
    with pytest.raises(ValueError, match="record_order_invalid"):
        m.summarize(bundle["rows"], case_id=m.COURTYARD_CASE_ID)


def test_closed_greenhouse_live_mode_is_refused_before_credentials(monkeypatch, tmp_path):
    expected = tmp_path / "historical-preflight.json"
    expected.write_text(m._canonical(m.prepare_experiment().metadata), encoding="utf-8")
    class NoCredentials(dict):
        def get(self, key, *args):
            if key == "GROQ_API_KEY": pytest.fail("Closed case inspected credential")
            return super().get(key, *args)
    monkeypatch.setattr(m.os, "environ", NoCredentials())
    monkeypatch.setattr(m, "_new_run_directory", lambda *args: pytest.fail("Closed case allocated run"))
    assert m.main(["--live", "--case-id", m.CASE_ID, "--allow-synthetic-only",
                   "--batch-id", str(uuid4()), "--expected-preflight", str(expected)]) == 3
