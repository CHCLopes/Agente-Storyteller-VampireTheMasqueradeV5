"""New four-slot diagnostic: HTTPX MockTransport only, no store or live credentials."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from scripts import evaluate_source_word_budget as probe

KEY = "synthetic-word-budget-test-key-not-persisted"
N_C1 = ('Bela aponta para o relógio menor sobre o balcão da relojoaria, mantendo as mãos afastadas das peças. '
    '"Este ponteiro está parado, mas o som continua vindo da caixa", explica. Um clique baixo interrompe sua fala, '
    'seguido por dois estalos curtos. Ela deixa um espaço livre diante do balcão e inclina a cabeça na direção do som. '
    'A luz da janela alcança o mostrador opaco, onde uma pequena sombra acompanha cada estalo. Bela observa o mecanismo '
    'por um instante e volta os olhos para a conversa, sem oferecer uma explicação para a diferença.')
N_C2 = ('Caio acompanha a bandeja com os olhos quando uma rajada levanta outra ponta do pano. A peça desliza um pouco '
    'sobre a mesa do pavilhão e para perto da borda, ainda apoiada. "Está chegando mais perto", comenta, sem estender '
    'as mãos. A cortina encosta na janela e produz um ruído seco, que termina junto com o vento. Por alguns instantes '
    'o pano permanece imóvel. A passagem até a porta continua livre, enquanto Caio espera junto à mesa. O movimento '
    'cessou, mas a bandeja ficou numa posição diferente.')
Q = "O que você faz agora?"


def response(n=N_C1, q=Q, *, model=probe.GROQ_QWEN_MODEL_ID, finish="stop", extra=None):
    value = {"model": model, "choices": [{"finish_reason": finish, "message": {"role": "assistant",
        "content": json.dumps({"n": n, "q": q}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 120, "total_tokens": 420}}
    value.update(extra or {})
    return httpx.Response(200, json=value)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path / "results")
    from api.llm import contract
    from api.llm.adapters import groq, openai_compatible
    base = datetime.now(timezone.utc)
    clock = [0.0]
    def now():
        return base + timedelta(seconds=clock[0])
    for module in (probe, contract, groq, openai_compatible):
        monkeypatch.setattr(module, "utc_now", now)
    async def sleep(seconds):
        clock[0] += seconds
        await asyncio.sleep(0)
    def budget():
        return probe.DispatchBudget(_clock=lambda: clock[0], _sleeper=sleep)
    def no_database(*args, **kwargs):
        pytest.fail("Pure word-budget observation attempted SQLite")
    monkeypatch.setattr(sqlite3, "connect", no_database)
    seen, replies = [], [response(), response(), response(N_C2), response(N_C2)]
    def handle(request):
        seen.append(json.loads(request.content))
        item = replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item(request) if callable(item) else item
    return dict(seen=seen, replies=replies, budget=budget, clock=clock, transport=httpx.MockTransport(handle))


async def run(harness, **kwargs):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path,
        transport=harness["transport"], budget=harness["budget"](), **kwargs)
    return prepared, batch, path, rows


def expected(prepared, path):
    target = path.parent / (path.name + "-preflight.json")
    target.write_text(probe._json(prepared.metadata), encoding="utf-8")
    return target, probe.shared._sha256(target)


def verify(prepared, batch, path):
    target, digest = expected(prepared, path)
    return probe.verify_artifacts(path / "summary.json", target, batch, expected_preflight_sha256=digest)


def rewrite(path, rows, *, status=None, document_change=None):
    document = probe._read_json(path / "summary.json")
    if status is not None:
        document["evaluation_status"] = status
    raw = "".join(probe._json({"metadata": document["metadata"], "batch_id": document["batch_id"], "record": row}) + "\n" for row in rows)
    (path / "records.jsonl").write_text(raw, encoding="utf-8")
    document["artifacts"]["records"]["sha256"] = probe.shared._sha256(path / "records.jsonl")
    try:
        document["summary"] = probe.summarize(rows, document["evaluation_status"])
        document["process_exit_code"] = document["summary"]["process_exit_code"]
    except ValueError:
        pass
    if document_change:
        document_change(document)
    (path / "summary.json").write_text(probe._json(document), encoding="utf-8")


def test_preflight_pairs_new_authored_contexts_with_one_exact_system_delta():
    first, again = probe.prepare_experiment(), probe.prepare_experiment()
    assert first.metadata == again.metadata
    assert first.prompts["B"] == first.prompts["A"].replace(probe.ORIGINAL_LENGTH, probe.MARGIN_LENGTH)
    frozen = first.metadata["frozen_requests"]
    assert [row["arm_id"] for row in frozen] == ["A", "B", "B", "A"]
    assert frozen[0]["user_packet"] == frozen[1]["user_packet"]
    assert frozen[2]["user_packet"] == frozen[3]["user_packet"]
    assert frozen[0]["user_packet"] != frozen[2]["user_packet"]
    for index, row in enumerate(frozen):
        assert row["request"]["reasoning_effort"] == "none"
        assert row["request"]["max_completion_tokens"] == 768
        assert row["request"]["response_format"]["json_schema"]["strict"] is True
        assert row["body_sha256"] == probe._sha(row["request"])
        packet = json.loads(row["user_packet"])
        assert packet["server_facts"] == []
        assert row["authored_source"]["provider_evidence"] is None
        assert row["authored_source"]["application_commit"] is False
        if index < 2:
            assert packet["context"]["attributed_sources"] == []
        else:
            assert packet["context"]["attributed_sources"][0]["text"] == first.corpus["contexts"]["C2"]["source_text"]
            assert row["authored_source"]["projection"]["source"]["invocation_id"].startswith("fixture-authorship-")
    assert first.metadata["generation_parameters"]["max_total_output_tokens"] == 4 * 768


@pytest.mark.parametrize("field,value", [("n", "palavra-dupla d’água palavra_com_sublinhado"), ("q", "um\u00a0dois três")])
def test_measurement_uses_the_existing_unicode_word_rule(field, value):
    payload = {"n": "texto", "q": "pergunta"}
    payload[field] = value
    result = probe.measurements(payload)
    assert result[field + "_words"] == len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", value, flags=re.UNICODE))
    assert result["total_words"] == result["n_words"] + result["q_words"]


@pytest.mark.parametrize("n,q,original,margin", [(29,0,False,False),(30,0,True,False),(70,10,True,True),
    (110,10,True,True),(111,9,True,False),(140,10,True,False),(141,10,False,False),(130,16,False,False)])
def test_requested_margin_is_measured_separately_from_immutable_policy(n, q, original, margin):
    measured = probe.measurements({"n": "palavra " * n, "q": "palavra " * q})
    assert measured["original_length_passed"] is original
    assert measured["margin_budget_met"] is margin


@pytest.mark.asyncio
async def test_four_frozen_http_requests_no_cross_arm_feedback_no_database_and_readonly_verifier(harness):
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 4
    assert [row["outcome"] for row in rows] == ["accepted"] * 4, rows
    for index, row in enumerate(rows):
        assert row["request"]["request"] == harness["seen"][index] == prepared.metadata["frozen_requests"][index]["request"]
        assert N_C1 not in row["request"]["user_packet"] and N_C2 not in row["request"]["user_packet"]
        assert row["measurements"] == probe.measurements(row["response_structure"])
    assert set(p.name for p in path.iterdir()) == {"summary.json", "records.jsonl"}
    hashes = {p.name: probe.shared._sha256(p) for p in path.iterdir()}
    assert verify(prepared, batch, path)["process_exit_code"] == 0
    assert hashes == {p.name: probe.shared._sha256(p) for p in path.iterdir()}
    assert harness["clock"][0] == 240


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["policy", "schema", "too_long", "q_too_long", "length", "429", "401", "503", "route", "timeout"])
async def test_typed_content_continues_but_operational_failures_stop_without_retry(harness, failure):
    if failure == "policy":
        reply = response(q="Quem está aqui?")
    elif failure == "schema":
        reply = response(n="curta")
    elif failure == "too_long":
        reply = response(n="A mesa permanece no local. " * 31)
    elif failure == "q_too_long":
        reply = response(q="O que você faz agora nesta sala com todos os detalhes que foram apresentados nesta conversa?")
    elif failure == "length":
        reply = response(finish="length")
    elif failure in ("429", "401", "503"):
        reply = httpx.Response(int(failure), json={"error": {"code": "rate_limit_exceeded" if failure == "429" else "synthetic_failure", "message": "synthetic"}})
    elif failure == "timeout":
        reply = httpx.ReadTimeout("synthetic")
    else:
        reply = response(model="unrequested-model")
    harness["replies"][0] = reply
    prepared, batch, path, rows = await run(harness)
    continuing = failure in ("policy", "schema", "too_long", "q_too_long")
    assert len(harness["seen"]) == (4 if continuing else 1), rows
    assert (rows[1]["kind"] == "source_word_budget_call") is continuing
    assert verify(prepared, batch, path)["verified"] is True
    assert probe._read_json(path / "summary.json")["process_exit_code"] != 0


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["n", "q", "metadata", "header", "error"])
async def test_known_key_echo_never_reaches_artifacts_or_output_and_stops_globally(harness, location, capsys):
    if location == "n":
        reply = response(n=N_C1 + " " + KEY)
    elif location == "q":
        reply = response(q=KEY)
    elif location == "metadata":
        reply = response(extra={"request_id": KEY})
    elif location == "header":
        reply = response(); reply.headers["x-request-id"] = KEY
    else:
        reply = httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": KEY}})
    harness["replies"][0] = reply
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 1 and rows[0]["credential_echo_blocked"] is True
    assert rows[0]["response_structure"] is rows[0]["evidence"] is rows[0]["llm_error"] is None
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir())
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_cancellation_during_initial_wait_writes_skips_without_http(harness, monkeypatch):
    async def cancel(self):
        raise asyncio.CancelledError
    monkeypatch.setattr(probe.DispatchBudget, "wait", cancel)
    prepared, batch, path, rows = await run(harness)
    assert not harness["seen"]
    assert rows[0]["outcome"] == "cancelled"
    assert verify(prepared, batch, path)["process_exit_code"] == 130


@pytest.mark.asyncio
async def test_unknown_local_transport_error_stops_and_redacts_exception(harness, monkeypatch):
    async def fail(self, request):
        raise RuntimeError(KEY)
    monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", fail)
    prepared, batch, path, rows = await run(harness)
    assert not harness["seen"] and rows[0]["local_error"]["stage"] == "transport"
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir())
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_duplicate_slot_fifth_call_and_early_http_fail_at_actual_dispatch(harness):
    budget = harness["budget"]()
    with pytest.raises(ValueError):
        budget.consume("slot-1")
    for slot, _, _ in probe.SLOTS:
        await budget.wait()
        budget.consume(slot)
        with pytest.raises(ValueError):
            budget.consume(slot)
    await budget.wait()
    with pytest.raises(ValueError):
        budget.consume("slot-5")
    assert budget.calls == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("attack", ["payload", "deadline", "duplicate"])
async def test_adapter_bound_request_rejects_mutation_expiry_and_reuse(harness, attack):
    prepared, batch, budget = probe.prepare_experiment(), str(uuid4()), harness["budget"]()
    await budget.wait()
    request = probe.make_request(prepared, 0, batch, deadline=probe.utc_now() + timedelta(seconds=60))
    adapter = probe.ObservationAdapter(prepared=prepared, request=request, api_key=SecretStr(KEY),
        budget=budget, slot="slot-1", transport=harness["transport"])
    if attack == "payload":
        request = request.model_copy(update={"parameters": probe.GenerationParameters(temperature=.2, max_output_tokens=768)})
    elif attack == "deadline":
        harness["clock"][0] += 61
    else:
        await adapter.generate_structured(request)
    with pytest.raises((ValueError, probe.LLMInvocationError)):
        await adapter.generate_structured(request)
    assert len(harness["seen"]) == (1 if attack == "duplicate" else 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["measure", "arm", "source", "request", "body_hash", "deadline", "created", "http", "evidence", "usage", "extra", "skip", "fifth", "status", "metadata"])
async def test_verifier_rejects_rehashed_forgery(harness, change):
    prepared, batch, path, rows = await run(harness)
    if change == "measure": rows[0]["measurements"]["n_words"] += 1
    elif change == "arm": rows[1]["arm_id"] = "A"
    elif change == "source": rows[2]["authored_source"]["provider_evidence"] = {"provider": "Groq"}
    elif change == "request": rows[1]["request"]["user_packet"] = "{}"
    elif change == "body_hash": rows[0]["request"]["body_sha256"] = "0" * 64
    elif change == "deadline": rows[0]["request"]["deadline"] = rows[0]["request_created_at"]
    elif change == "created": rows[0]["request_created_at"] = "2000-01-01T00:00:00+00:00"
    elif change == "http": rows[1]["http_started_at"] = rows[0]["http_started_at"]
    elif change == "evidence": rows[0]["evidence"]["invocation_id"] = str(uuid4())
    elif change == "usage": rows[0]["evidence"]["usage"]["input_tokens"] += 1
    elif change == "extra": rows[0]["provider_observation"]["free_text"] = "synthetic"
    elif change == "skip": rows[1] = probe._skip(1, "previous_operational_failure")
    elif change == "fifth": rows.append(copy.deepcopy(rows[0]))
    elif change == "status": rows[0]["policy_valid"] = False
    rewrite(path, rows, document_change=(lambda doc: doc["metadata"].update(max_calls=5)) if change == "metadata" else None)
    with pytest.raises((ValueError, TypeError)):
        verify(prepared, batch, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("attack", ["duplicate_json", "nan", "summary_extra", "wrong_path", "preflight_hash", "preflight_drift"])
async def test_artifact_and_preflight_envelopes_fail_closed(harness, attack, tmp_path):
    prepared, batch, path, rows = await run(harness)
    target, digest = expected(prepared, path)
    summary = path / "summary.json"
    if attack == "duplicate_json":
        summary.write_text(summary.read_text().replace('{"artifacts":', '{"batch_id":"fake","artifacts":', 1))
    elif attack == "nan":
        summary.write_text(summary.read_text().replace('"process_exit_code":0', '"process_exit_code":NaN', 1))
    elif attack == "summary_extra":
        rewrite(path, rows, document_change=lambda doc: doc.update(extra="unexpected"))
    elif attack == "wrong_path":
        other = tmp_path / "summary.json"; other.write_bytes(summary.read_bytes()); summary = other
    elif attack == "preflight_hash":
        digest = "0" * 64
    else:
        changed = copy.deepcopy(prepared.metadata); changed["generation_parameters"]["max_calls"] = 5
        target.write_text(probe._json(changed)); digest = probe.shared._sha256(target)
    with pytest.raises(ValueError):
        probe.verify_artifacts(summary, target, batch, expected_preflight_sha256=digest)


@pytest.mark.parametrize("change", ["target", "prompt", "corpus", "metadata", "candidate"])
def test_prepared_mutation_is_detected_before_live(change):
    prepared = probe.prepare_experiment()
    if change == "target": object.__setattr__(prepared, "target", probe.LLMTarget(profile="other", provider="Groq", model=probe.GROQ_QWEN_MODEL_ID))
    elif change == "prompt": prepared.prompts["B"] += " changed"
    elif change == "corpus": prepared.corpus["contexts"]["C1"]["player_input"] = "Aguardo."
    elif change == "candidate": object.__setattr__(prepared.candidate, "model", "other")
    else: prepared.metadata["slots"].reverse()
    with pytest.raises(ValueError): probe._check_prepared(prepared)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["blank", "echo", "exists", "path"])
async def test_pre_dispatch_refuses_invalid_credential_and_output(harness, failure, tmp_path):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path, key = probe.run_path(batch), SecretStr(KEY)
    if failure == "blank": key = SecretStr(" ")
    elif failure == "echo": key = SecretStr("Groq")
    elif failure == "exists": path.mkdir(parents=True)
    else: path = tmp_path / "wrong"
    with pytest.raises((ValueError, FileExistsError)):
        await probe.evaluate_probe(prepared, api_key=key, batch_id=batch, run_directory=path,
            transport=harness["transport"], budget=harness["budget"]())
    assert not harness["seen"]


@pytest.mark.parametrize("args", [["--preflight", "--api-key-env", probe.KEY_ENV], ["--preflight", "--allow-synthetic-only"],
    ["--live"], ["--live", "--allow-synthetic-only", "--batch-id", str(uuid4())],
    ["--verify-artifacts", "missing", "--api-key-env", probe.KEY_ENV], ["--api-key-env", KEY]])
def test_cli_rejects_invalid_modes_without_reading_a_credential(args, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid CLI reached environment credential lookup")
    monkeypatch.setattr(probe, "os", SimpleNamespace(environ=SimpleNamespace(get=forbidden)))
    assert probe.main(args) == 3
    assert KEY not in capsys.readouterr().err


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["unavailable", "http_error", "finish", "usage_unavailable", "output_limit", "finished_late"])
async def test_independent_review_false_successes_fail_even_after_rehash(harness, change):
    prepared, batch, path, rows = await run(harness)
    row = rows[0]
    if change == "unavailable":
        row["provider_observation"] = probe._unavailable_observation()
    elif change == "http_error":
        row["provider_observation"].update(http_status=429, finish_reason="length", provider_code="rate_limit_exceeded")
    elif change == "finish":
        row["provider_observation"]["finish_reason"] = "length"
    elif change == "usage_unavailable":
        row["provider_observation"]["usage"]["output_tokens"] = None
    elif change == "output_limit":
        for item in (row["evidence"]["usage"], row["provider_observation"]["usage"]):
            item.update(output_tokens=9999, total_tokens=10299)
    else:
        row["evidence"]["finished_at"] = (probe._aware(row["request"]["deadline"]) + timedelta(seconds=60)).isoformat()
    rewrite(path, rows)
    with pytest.raises(ValueError):
        verify(prepared, batch, path)
    # Adding the correct diagnostic cannot excuse later slots already dispatched.
    row["operational_error"] = probe._operational_error(row)
    assert row["operational_error"] is not None
    rewrite(path, rows)
    with pytest.raises(ValueError):
        verify(prepared, batch, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["output_limit", "actual_timeout", "late_adapter_return", "observer_unavailable"])
async def test_operational_signal_stops_live_path_preserving_original_capture(harness, monkeypatch, case):
    if case == "output_limit":
        harness["replies"][0] = response(extra={"usage": {"prompt_tokens": 300,
            "completion_tokens": 769, "total_tokens": 1069}})
    elif case == "actual_timeout":
        def delayed(request):
            harness["clock"][0] += 61
            return response()
        harness["replies"][0] = delayed
    else:
        original = probe.ObservationAdapter.generate_structured
        async def conflicting(self, request):
            result = await original(self, request)
            if case == "late_adapter_return":
                harness["clock"][0] += 61
                self.capture["evidence"]["finished_at"] = probe.utc_now().isoformat()
            else:
                self._observation = probe._unavailable_observation()
            return result
        monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", conflicting)
    prepared, batch, path, rows = await run(harness)
    row = rows[0]
    assert len(harness["seen"]) == 1
    assert all(item["kind"] == "source_word_budget_skip" for item in rows[1:])
    assert row["operational_error"] is not None
    assert row["evidence"] is not None
    if case == "actual_timeout":
        assert row["llm_error"]["category"] == "timeout"
    else:
        assert row["response_structure"] == {"n": N_C1, "q": Q}
        assert row["outcome"] == "accepted" and row["policy_valid"] is True
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_absent_provider_usage_stays_unknown_and_is_not_reported_as_measured_zero(harness):
    harness["replies"][:] = [response(n, extra={"usage": None}) for n in (N_C1, N_C1, N_C2, N_C2)]
    prepared, batch, path, rows = await run(harness)
    for row in rows:
        assert row["evidence"]["usage"]["status"] == "unavailable"
        assert probe._output_tokens(row) is None
        assert row["provider_observation"]["usage"]["output_tokens"] is None
        assert row["operational_error"] is None
    assert verify(prepared, batch, path)["process_exit_code"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["status", "category"])
async def test_normalized_http_failure_must_match_observer(harness, change):
    harness["replies"][0] = httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
    prepared, batch, path, rows = await run(harness)
    if change == "status":
        rows[0]["provider_observation"]["http_status"] = 503
    else:
        rows[0]["llm_error"]["category"] = "provider_unavailable"
    rewrite(path, rows)
    with pytest.raises(ValueError):
        verify(prepared, batch, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["error_body", "failed_generation"])
async def test_unavailable_nested_observation_cannot_hide_contradictory_data(harness, field):
    prepared, batch, path, rows = await run(harness)
    nested = rows[0]["provider_observation"][field]
    if field == "error_body":
        nested.update(complete=True, bytes=5, json_valid=True)
    else:
        nested.update(present=True, characters=5, json_valid=True)
    assert nested["status"] == "unavailable"
    rewrite(path, rows)
    with pytest.raises(ValueError):
        verify(prepared, batch, path)


@pytest.mark.asyncio
async def test_last_slot_operational_failure_never_sets_probe_passed(harness):
    harness["replies"][3] = response(N_C2, extra={"usage": {"prompt_tokens": 300,
        "completion_tokens": 769, "total_tokens": 1069}})
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 4
    assert all(row["outcome"] == "accepted" for row in rows)
    assert all(row["operational_error"] is None for row in rows[:3])
    assert rows[3]["operational_error"] is not None
    summary = probe._read_json(path / "summary.json")["summary"]
    assert summary["operational_probe_passed"] is False and summary["process_exit_code"] == 3
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_deadline_expired_before_adapter_dispatch_retains_no_call_timeout(harness, monkeypatch):
    original = probe.ObservationAdapter.generate_structured
    async def delayed(self, request):
        harness["clock"][0] += 61
        return await original(self, request)
    monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", delayed)
    prepared, batch, path, rows = await run(harness)
    assert not harness["seen"] and rows[0]["call_made"] is False
    assert rows[0]["llm_error"]["category"] == "timeout"
    assert rows[0]["evidence"] is not None
    assert all(row["kind"] == "source_word_budget_skip" for row in rows[1:])
    assert verify(prepared, batch, path)["process_exit_code"] == 3
