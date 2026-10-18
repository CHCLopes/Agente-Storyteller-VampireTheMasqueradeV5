"""Synthetic HTTP/SQLite integration, real B producer; never live inference."""
import asyncio
import copy
from datetime import timedelta
import json
import sqlite3
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from scripts import evaluate_source_comparison as probe

KEY = "synthetic-comparison-key-never-retain"
QUESTION = "O que você faz agora?"


def response(body, *, narrative=None, question=QUESTION, model=None, finish="stop", extra=None):
    packet = json.loads(body["messages"][1]["content"])
    npc = packet["context"]["canonical_scene"]["npcs_present"][0]
    color = "azul" if body["model"] == probe.MODELS[probe.QWEN_ID][0] else "verde"
    count = len(packet["context"]["attributed_sources"])
    endings = ("Uma folha solta permanece sobre a mesa, ao lado de um recipiente vazio.",
        "Uma corrente de ar vira a folha e revela um desenho no verso.",
        "O desenho no verso mostra uma linha curva cercada por pequenos pontos.")
    text = (f'{npc} indica uma pasta {color} apoiada sobre a mesa. "Há desenhos nesta pasta", comenta, '
        'sem sair de junto da janela. A luz atravessa o vidro e torna os traços visíveis. '
        f'{npc} afasta a mão e aguarda. '+endings[count])
    payload = {"model": model or body["model"], "choices": [{"finish_reason": finish,
        "message": {"role": "assistant", "content": json.dumps({"n": narrative or text, "q": question}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180}}
    payload.update(extra or {})
    return httpx.Response(200, json=payload)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path/"results")
    base, clock = probe.utc_now()+timedelta(seconds=10), [0.0]
    monkeypatch.setattr(probe, "utc_now", lambda: base+timedelta(seconds=clock[0]))
    from api.llm.adapters import openai_compatible, groq
    monkeypatch.setattr(openai_compatible, "utc_now", probe.utc_now)
    monkeypatch.setattr(groq, "utc_now", probe.utc_now)
    async def sleeper(seconds):
        clock[0] += seconds
    real_budget = probe.DispatchBudget
    class Budget(real_budget):
        def __init__(self):
            super().__init__()
            self.pacer = probe.shared._CallPacer(60, _clock=lambda: clock[0], _sleeper=sleeper)
            self.last_dispatch = self.pacer._last_call_started_at = clock[0]
    monkeypatch.setattr(probe, "DispatchBudget", Budget)
    seen, overrides = [], {}
    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        action = overrides.get(len(seen))
        return action(body) if action else response(body)
    real_adapter = probe.ObservationAdapter
    class Adapter(real_adapter):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(probe, "ObservationAdapter", Adapter)
    return seen, overrides, clock


async def run():
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_comparison(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path)
    return prepared, batch, path, rows


async def verify(prepared, batch, path):
    preflight = path.parent/(path.name+"-preflight.json")
    preflight.write_text(probe._json(prepared.metadata), encoding="utf-8")
    return await asyncio.to_thread(probe.verify_artifacts, path/"summary.json", preflight, batch,
        expected_preflight_sha256=probe.shared._sha256(preflight))


def rewrite(prepared, batch, path, rows, edit=None):
    doc = probe._read_json(path/"summary.json")
    if edit:
        edit(doc)
    file = path/"records.jsonl"
    file.write_text("".join(probe._json({"metadata": doc["metadata"], "batch_id": batch, "record": r})+"\n" for r in rows), encoding="utf-8")
    doc["artifacts"]["records"]["sha256"] = probe.shared._sha256(file)
    for item in doc["artifacts"]["databases"].values():
        item["sha256"] = probe.shared._sha256(path/item["file"])
    doc["summary"] = probe.summarize(rows, prepared, batch)
    doc["process_exit_code"] = doc["summary"]["process_exit_code"]
    (path/"summary.json").write_text(probe._json(doc), encoding="utf-8")


@pytest.mark.asyncio
async def test_twelve_actual_producer_turns_isolated_histories_and_exact_candidate_payloads(harness, monkeypatch):
    from api import narrative_source_input_service as service, rules_service
    real, produced = service.produce_source_player_action, []
    def count(request):
        produced.append(request)
        return real(request)
    monkeypatch.setattr(service, "produce_source_player_action", count)
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("declarative comparison rolled"))
    old = {f: probe.shared._sha256(probe.PROJECT_ROOT/f) for f in probe.player.IMPLEMENTATION_FILES}
    prepared, batch, path, rows = await run()
    summary = probe._read_json(path/"summary.json")
    assert summary["process_exit_code"] == 0, rows
    assert len(harness[0]) == len(produced) == 12
    assert summary["summary"]["turns_committed"] == 12
    assert summary["summary"]["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}
    assert all(row["input_replay_verified"] and row["replay_verified"] for row in rows)
    assert len({row["session_id"] for row in rows}) == 4
    for block_index, block in enumerate(prepared.blocks):
        local = rows[block_index*3:block_index*3+3]
        with sqlite3.connect(path/(block.block_id+".sqlite3")) as conn:
            assert conn.execute("SELECT count(*) FROM attempts").fetchone() == (9,)
            assert conn.execute("SELECT current_turn,state_revision FROM campaigns").fetchone() == (3, 3)
            assert conn.execute("SELECT count(*) FROM turns").fetchone() == (3,)
        for i, row in enumerate(local):
            body = harness[0][block_index*3+i]
            assert body == row["request"]["request"]
            assert body["model"] == block.target.model
            assert body["reasoning_effort"] == block.candidate.reasoning_effort
            assert body["max_completion_tokens"] == 768
            assert body["response_format"]["json_schema"]["strict"] is True
            if block.candidate.candidate_id == probe.GPT_OSS_ID:
                assert body["include_reasoning"] is False
            packet = json.loads(body["messages"][1]["content"])
            assert packet["player_input"] == block.case["turns"][i]["player_input"]
            assert packet["context"]["canonical_scene"] == {"location": block.case["setup"]["location"], "npcs_present": block.case["setup"]["npcs_present"]}
            assert [s["text"] for s in packet["context"]["attributed_sources"]] == [r["response_structure"]["n"] for r in local[:i]]
            assert QUESTION not in probe._json(packet) and "Preparação autorada" not in probe._json(packet)
    before = {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    assert (await verify(prepared, batch, path))["verified"] is True
    assert len(produced) == len(harness[0]) == 12
    assert before == {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    assert old == {f: probe.shared._sha256(probe.PROJECT_ROOT/f) for f in old}


@pytest.mark.parametrize("failure", ["policy", "schema", "length", "content"])
@pytest.mark.asyncio
async def test_second_failure_preserves_first_commit_stops_its_chain_and_runs_planned_blocks(harness, failure):
    if failure == "policy":
        harness[1][2] = lambda b: response(b, question="Quem está aqui?")
    elif failure == "schema":
        harness[1][2] = lambda b: response(b, narrative="curta")
    elif failure == "length":
        harness[1][2] = lambda b: response(b, finish="length")
    else:
        harness[1][2] = lambda b: response(b, finish="content_filter")
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert doc["process_exit_code"] == 1, rows
    assert len(harness[0]) == 11 and rows[2]["reason"] == "previous_chain_failure"
    assert rows[0]["result"]["status"] == "completed"
    assert rows[3]["candidate_id"] == probe.GPT_OSS_ID and rows[3]["result"]["status"] == "completed"
    assert doc["summary"]["global_stop_reason"] is None and doc["summary"]["turns_committed"] == 10
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.parametrize("failure", ["429", "401", "503", "timeout", "route"])
@pytest.mark.asyncio
async def test_provider_global_failures_stop_all_remaining_blocks(harness, failure):
    if failure == "route":
        harness[1][2] = lambda b: response(b, model="wrong-model")
    elif failure == "timeout":
        def timeout(_body):
            raise httpx.ReadTimeout("synthetic bounded timeout")
        harness[1][2] = timeout
    else:
        harness[1][2] = lambda b: httpx.Response(int(failure), json={"error": {"code": "rate_limit_exceeded", "message": "synthetic failure"}})
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert len(harness[0]) == 2 and doc["process_exit_code"] == 2, rows
    assert all(row["kind"] == "source_comparison_skip" and row["reason"].startswith("global_") for row in rows[2:])
    assert set(doc["artifacts"]["databases"]) == {"block-1"}
    assert not doc["summary"]["operational_comparison_passed"]
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.parametrize("where", ["n", "q", "metadata", "header", "error"])
@pytest.mark.asyncio
async def test_known_key_echo_never_persists_and_stops_batch_with_dispatch_chronology(harness, capsys, where):
    def echo(body):
        if where == "n": return response(body, narrative="Uma pasta permanece sobre a mesa da oficina. "+KEY)
        if where == "q": return response(body, question="O que você faz com "+KEY+"?")
        if where == "metadata": return response(body, extra={"request_id": KEY})
        if where == "error": return httpx.Response(429, json={"error": {"message": KEY}})
        reply = response(body)
        reply.headers["x-request-id"] = KEY
        return reply
    harness[1][1] = echo
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert len(harness[0]) == 1 and doc["process_exit_code"] == 3
    assert rows[0]["credential_echo_blocked"] and rows[0]["http_started_at"] is not None
    assert all(KEY.encode() not in file.read_bytes() for file in path.iterdir() if file.is_file())
    captured = capsys.readouterr()
    assert KEY not in captured.out+captured.err
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_global_budget_caps_and_cross_block_clock_admission(harness):
    budget = probe.DispatchBudget()
    with pytest.raises(ValueError, match="spacing"):
        budget.consume("block-1")
    for block in ("block-1", "block-2", "block-3", "block-4"):
        for _ in range(3):
            await budget.wait(block)
            budget.consume(block)
        with pytest.raises(ValueError, match="limit"):
            budget.consume(block)
    assert budget.calls == 12 and harness[2][0] == 720
    await budget.wait("block-5")
    with pytest.raises(ValueError, match="limit"):
        budget.consume("block-5")


@pytest.mark.asyncio
async def test_changed_model_parameters_or_deadline_never_reaches_http(harness):
    prepared, batch, path, rows = await run()
    block, row = prepared.blocks[0], rows[0]
    capsule = probe.validate_source_turn_capsule(row["capsule"], session_id=row["session_id"], operation_id=row["operation_id"])
    for field, value in (("parameters", probe.GenerationParameters(temperature=.65, max_output_tokens=767)),
        ("deadline", probe.utc_now()+timedelta(seconds=100)),
        ("target", prepared.blocks[1].target)):
        request, budget = probe._request(capsule), probe.DispatchBudget()
        adapter = probe.ObservationAdapter(block=block, request=request, api_key=SecretStr(KEY), budget=budget)
        with pytest.raises(Exception):
            await adapter.generate_structured(request.model_copy(update={field: value}))
        assert not adapter.http_sent and budget.calls == 0
    assert len(harness[0]) == 12


@pytest.mark.parametrize("field", ["body", "reasoning", "capsule", "history", "audit", "clock", "deadline", "producer", "orphan", "setup", "effective-model"])
@pytest.mark.asyncio
async def test_rehashed_artifacts_cannot_hide_matrix_request_source_or_database_tampering(harness, field):
    prepared, batch, path, rows = await run()
    if field == "body": rows[0]["request"]["request"]["max_completion_tokens"] = 767
    elif field == "reasoning": rows[3]["request"]["request"]["reasoning_effort"] = "none"
    elif field == "capsule": rows[0]["capsule"]["player_input"] = "changed"
    elif field == "history": rows[5]["input_claim"]["request"]["snapshot"]["sources"] = copy.deepcopy(rows[2]["input_claim"]["request"]["snapshot"]["sources"])
    elif field == "audit": rows[0]["evidence"]["usage"]["input_tokens"] += 1
    elif field == "clock": rows[3]["http_started_at"] = rows[2]["http_started_at"]
    elif field == "deadline": rows[0]["request"]["deadline"] = rows[0]["deadline_created_at"]
    elif field == "effective-model": rows[3]["provider_observation"]["model"] = probe.MODELS[probe.QWEN_ID][0]
    else:
        with sqlite3.connect(path/"block-1.sqlite3") as conn:
            if field == "producer":
                conn.execute("UPDATE attempts SET result_hash=? WHERE operation_id=?", ("0"*64, probe.source_input_operation_id(rows[0]["session_id"], rows[0]["operation_id"])))
            elif field == "setup":
                raw = json.loads(conn.execute("SELECT metadata_json FROM campaigns").fetchone()[0])
                raw["narrative_source_setup_manifest"]["request"]["npcs_present"] = []
                conn.execute("UPDATE campaigns SET metadata_json=?", (probe._json(raw),))
            else:
                conn.row_factory = sqlite3.Row
                record = dict(conn.execute("SELECT * FROM attempts LIMIT 1").fetchone())
                record.pop("id")
                record.update(session_id="orphan", operation_id="orphan-op", attempt_id="orphan-attempt")
                conn.execute("INSERT INTO attempts ("+",".join(record)+") VALUES ("+",".join("?" for _ in record)+")", tuple(record.values()))
    rewrite(prepared, batch, path, rows)
    with pytest.raises(Exception):
        await verify(prepared, batch, path)


@pytest.mark.asyncio
async def test_missing_p_rejected_before_verifier_can_produce_or_call_again(harness, monkeypatch):
    from api import narrative_source_input_service as service
    prepared, batch, path, rows = await run()
    with sqlite3.connect(path/"block-1.sqlite3") as conn:
        conn.execute("DELETE FROM attempts WHERE operation_id=?", (probe.source_input_operation_id(rows[0]["session_id"], rows[0]["operation_id"]),))
    rewrite(prepared, batch, path, rows)
    monkeypatch.setattr(service, "produce_source_player_action", lambda *a: pytest.fail("audit produced replacement"))
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)
    assert len(harness[0]) == 12


@pytest.mark.parametrize("mode", ["cancel", "drift"])
@pytest.mark.asyncio
async def test_cancel_or_freeze_drift_after_retention_never_dispatches(harness, monkeypatch, mode):
    async def stop(self, block):
        if mode == "cancel": raise asyncio.CancelledError()
        monkeypatch.setattr(probe, "CORPUS_SHA256", "0"*64)
    monkeypatch.setattr(probe.DispatchBudget, "wait", stop)
    prepared, batch, path, rows = await run()
    assert not harness[0] and rows[0]["capsule"] is not None
    assert probe._read_json(path/"summary.json")["process_exit_code"] == (130 if mode == "cancel" else 3)
    if mode == "cancel": assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_unexpected_producer_failure_is_global_and_never_creates_k_h(harness, monkeypatch):
    from api import narrative_source_input_service as service
    from api.narrative_source_input import SourceInputFailure
    monkeypatch.setattr(service, "produce_source_player_action", lambda request: SourceInputFailure(code="source_input_out_of_scope", stage="classification"))
    prepared, batch, path, rows = await run()
    assert not harness[0] and rows[0]["capsule"] is rows[0]["result"] is None
    assert probe._read_json(path/"summary.json")["summary"]["global_stop_reason"] == "producer_failure"
    assert (await verify(prepared, batch, path))["verified"] is True


def test_preflight_does_not_read_keys_produce_receipts_or_open_database(monkeypatch, capsys):
    original = probe.os.environ.get
    def guarded(key, *args):
        assert "KEY" not in key and "TOKEN" not in key
        return original(key, *args)
    monkeypatch.setattr(probe.os.environ, "get", guarded)
    monkeypatch.setattr(probe, "ProbePersistence", lambda *args: pytest.fail("preflight opened database"))
    monkeypatch.setattr(probe, "prepare_source_player_action", lambda *args: pytest.fail("preflight created receipt"))
    assert probe.main(["--preflight"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["max_calls"] == 12 and doc["generation_parameters"] == probe.PARAMETERS
    assert doc["selected_candidate_ids"] == list(probe.CANDIDATE_IDS)
    assert all(not item["is_live_request"] and item["body_sha256"] is None for item in doc["first_request_templates"])


@pytest.mark.parametrize("field", ["hash", "candidate", "corpus", "code", "parameter"])
def test_preflight_tamper_rejected_before_credential_access(tmp_path, monkeypatch, capsys, field):
    doc = copy.deepcopy(probe.prepare_experiment().metadata)
    if field == "candidate": doc["inputs"]["candidates"][1]["reasoning_effort"] = "none"
    elif field == "corpus": doc["inputs"]["corpus"]["data"]["cases"][0]["turns"][0]["player_input"] = "changed"
    elif field == "code": doc["inputs"]["implementation"][0]["sha256"] = "0"*64
    elif field == "parameter": doc["generation_parameters"]["max_calls"] = 13
    path = tmp_path/"preflight.json"
    path.write_text(probe._json(doc), encoding="utf-8")
    digest = "0"*64 if field == "hash" else probe.shared._sha256(path)
    original = probe.os.environ.get
    def guarded(key, *args):
        assert key != probe.KEY_ENV
        return original(key, *args)
    monkeypatch.setattr(probe.os.environ, "get", guarded)
    assert probe.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4()), "--expected-preflight", str(path),
        "--expected-preflight-sha256", digest]) == 3
    assert "preflight_or_verification_failed" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_unapproved_paths_or_missing_key_are_rejected_before_dispatch(harness, tmp_path):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    with pytest.raises(ValueError):
        await probe.evaluate_comparison(prepared, api_key=SecretStr(" "), batch_id=batch, run_directory=probe.run_path(batch))
    with pytest.raises(ValueError):
        await probe.evaluate_comparison(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=tmp_path/"foreign")
    probe.run_path(batch).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        await probe.evaluate_comparison(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=probe.run_path(batch))
    assert not harness[0]


@pytest.mark.asyncio
async def test_rehashed_nocall_cannot_claim_provider_http_observation(harness, monkeypatch):
    async def cancel(self, block):
        raise asyncio.CancelledError()
    monkeypatch.setattr(probe.DispatchBudget, "wait", cancel)
    prepared, batch, path, rows = await run()
    assert rows[0]["capsule"] is not None and not rows[0]["call_made"]
    rows[0]["provider_observation"]["http_status"] = 200
    rewrite(prepared, batch, path, rows)
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)


@pytest.mark.parametrize("boundary", ["before_http", "after_deadline"])
@pytest.mark.asyncio
async def test_rehashed_provider_audit_cannot_violate_dispatch_deadline_chronology(harness, boundary):
    # A valid LLM response rejected by policy has no committed source whose
    # provenance hash could reject the tamper before the timing audit is tested.
    harness[1][1] = lambda b: response(b, question="Quem está aqui?")
    prepared, batch, path, rows = await run()
    row = rows[0]
    assert row["result"]["status"] == "failed" and row["response_structure"] is not None and row["llm_error"] is None
    if boundary == "before_http":
        changed = probe.datetime.fromisoformat(row["http_started_at"])-timedelta(seconds=1)
        row["evidence"]["started_at"] = (changed-timedelta(seconds=1)).isoformat()
    else:
        changed = probe.datetime.fromisoformat(row["request"]["deadline"])+timedelta(seconds=1)
    row["evidence"]["finished_at"] = changed.isoformat()
    with sqlite3.connect(path/"block-1.sqlite3") as conn:
        raw = json.loads(conn.execute("SELECT provenance_json FROM attempts WHERE operation_id=?", (row["operation_id"],)).fetchone()[0])
        raw["invocations"][0]["provenance"]["started_at"] = row["evidence"]["started_at"]
        raw["invocations"][0]["provenance"]["finished_at"] = row["evidence"]["finished_at"]
        conn.execute("UPDATE attempts SET provenance_json=? WHERE operation_id=?", (probe._json(raw), row["operation_id"]))
    rewrite(prepared, batch, path, rows)
    with pytest.raises(ValueError, match="source_comparison_evidence_(chronology|deadline)"):
        await verify(prepared, batch, path)


@pytest.mark.asyncio
async def test_provider_reporting_more_than_requested_completion_stops_global_budget(harness):
    harness[1][1] = lambda b: response(b, extra={"usage": {"prompt_tokens": 100, "completion_tokens": 769, "total_tokens": 869}})
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert len(harness[0]) == 1 and doc["process_exit_code"] == 2
    assert doc["summary"]["global_stop_reason"] == "reported_budget_exceeded"
    assert doc["summary"]["usage_reported"]["output_tokens"] == 769
    assert doc["summary"]["requested_output_token_ceiling"] == 768
    assert doc["summary"]["usage_reported"]["reasoning_tokens"] is None
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_real_executor_expired_deadline_without_llm_error_stops_whole_batch(harness, monkeypatch):
    real = probe.execute_retained_source_turn
    async def expired(**kwargs):
        kwargs["deadline"] = probe.retained.utc_now()-timedelta(seconds=1)
        return await real(**kwargs)
    monkeypatch.setattr(probe, "execute_retained_source_turn", expired)
    prepared, batch, path, rows = await run()
    assert not harness[0] and rows[0]["llm_error"] is None
    assert rows[0]["result"]["status"] == "timeout"
    assert probe._read_json(path/"summary.json")["summary"]["global_stop_reason"] == "timeout"
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_cancel_after_commit_replays_existing_p_k_h_without_new_call(harness, monkeypatch):
    real, calls = probe.execute_retained_source_turn, [0]
    async def cancelled(**kwargs):
        result = await real(**kwargs)
        calls[0] += 1
        if calls[0] == 1:
            raise asyncio.CancelledError()
        return result
    monkeypatch.setattr(probe, "execute_retained_source_turn", cancelled)
    prepared, batch, path, rows = await run()
    assert len(harness[0]) == 1 and rows[0]["result"]["status"] == "completed" and rows[0]["replay_verified"]
    assert probe._read_json(path/"summary.json")["process_exit_code"] == 130
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.parametrize("syntax", ["duplicate", "nan"])
@pytest.mark.asyncio
async def test_jsonl_ambiguous_or_nonfinite_data_remains_closed(harness, syntax):
    harness[1][1] = lambda b: httpx.Response(429, json={"error": {"message": "synthetic limit"}})
    prepared, batch, path, rows = await run()
    file = path/"records.jsonl"
    raw = file.read_text(encoding="utf-8")
    if syntax == "duplicate":
        raw = raw.replace('{"batch_id":', '{"batch_id":"'+batch+'","batch_id":', 1)
    else:
        raw = raw.replace(probe._json(rows[0]["http_started_at"]), "NaN", 1)
    file.write_text(raw, encoding="utf-8")
    doc = probe._read_json(path/"summary.json")
    doc["artifacts"]["records"]["sha256"] = probe.shared._sha256(file)
    (path/"summary.json").write_text(probe._json(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)


@pytest.mark.asyncio
async def test_cancelled_invocation_audit_uses_real_contract_status(harness, monkeypatch):
    observed = probe.ObservationAdapter
    class Cancelled(observed):
        async def generate_structured(self, request):
            request.cancellation.cancel("synthetic controlled cancellation")
            return await super().generate_structured(request)
    monkeypatch.setattr(probe, "ObservationAdapter", Cancelled)
    prepared, batch, path, rows = await run()
    row = rows[0]
    assert not harness[0] and row["llm_error"]["category"] == "cancelled"
    assert row["result"]["status"] == "cancelled"
    with sqlite3.connect(path/"block-1.sqlite3") as conn:
        audit = json.loads(conn.execute("SELECT provenance_json FROM attempts WHERE operation_id=?", (row["operation_id"],)).fetchone()[0])
        assert audit["invocations"][0]["status"] == "cancelled"
    assert (await verify(prepared, batch, path))["verified"] is True
