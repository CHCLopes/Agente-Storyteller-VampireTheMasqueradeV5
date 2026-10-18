"""New player probe only: temporary SQLite and HTTPX MockTransport, no live calls."""
import asyncio
import copy
import json
import sqlite3
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from scripts import evaluate_source_player as probe
from tests.test_narrative_source_setup_flow import REPLY, WAIT_REPLY
from tests.test_narrative_source_bridge import QUESTION

KEY = "synthetic-source-player-credential-never-retain"


def response(n=REPLY, q=QUESTION, *, model=probe.GROQ_QWEN_MODEL_ID, finish="stop", extra=None):
    body = {"model": model, "choices": [{"finish_reason": finish,
        "message": {"role": "assistant", "content": json.dumps({"n": n, "q": q}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180}}
    body.update(extra or {})
    return httpx.Response(200, json=body)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path/"results")
    async def no_wait(self):
        pass
    monkeypatch.setattr(probe.DispatchBudget, "wait", no_wait)
    seen, replies = [], [response(), response(WAIT_REPLY)]
    def handler(request):
        seen.append(json.loads(request.content))
        return replies.pop(0)
    class Observed(probe.ObservationAdapter):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(probe, "ObservationAdapter", Observed)
    return seen, replies


async def run():
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path)
    return prepared, batch, path, rows


async def verify(prepared, batch, path):
    preflight = path.parent/(path.name+"-preflight.json")
    preflight.write_text(probe._json(prepared.metadata), encoding="utf-8")
    return await asyncio.to_thread(probe.verify_artifacts, path/"summary.json", preflight, batch,
        expected_preflight_sha256=probe.shared._sha256(preflight))


def rewrite(path, rows, edit=None):
    doc = probe._read_json(path/"summary.json")
    if edit:
        edit(doc)
    output = path/(probe.CANDIDATE_ID+".jsonl")
    output.write_text("".join(probe._json({"metadata": doc["metadata"], "batch_id": doc["batch_id"], "record": r})+"\n" for r in rows), encoding="utf-8")
    doc["artifacts"]["records"]["sha256"] = probe.shared._sha256(output)
    doc["artifacts"]["database"]["sha256"] = probe.shared._sha256(path/probe.DATABASE_NAME)
    doc["summary"] = probe.summarize(rows, doc["evaluation_status"])
    doc["process_exit_code"] = doc["summary"]["process_exit_code"]
    (path/"summary.json").write_text(probe._json(doc), encoding="utf-8")


@pytest.mark.asyncio
async def test_real_player_producer_setup_and_two_turns_replay_without_reproduction(harness, monkeypatch):
    from api import narrative_source_input_service as service, rules_service
    real, produced = service.produce_source_player_action, []
    def counted(request):
        produced.append(request)
        return real(request)
    monkeypatch.setattr(service, "produce_source_player_action", counted)
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Dialogue/wait must not roll"))
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert doc["process_exit_code"] == 0, rows
    assert len(produced) == len(harness[0]) == 2
    assert [r.player_input for r in produced] == list(probe.PLAYER_INPUTS)
    assert all(r.config.npc_aliases == ("Mara",) for r in produced)
    assert all(row["input_replay_verified"] and row["replay_verified"] for row in rows)
    assert doc["summary"]["producer_completions"] == doc["summary"]["turns_committed"] == 2
    assert doc["setup_manifest"]["origin"]["seed_scene"]["summary"] == ""
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone() == (6,)
        assert conn.execute("SELECT current_turn,state_revision FROM campaigns").fetchone() == (2, 2)
        assert conn.execute("SELECT count(*) FROM turns").fetchone() == (2,)
    first, second = (json.loads(body["messages"][1]["content"]) for body in harness[0])
    assert first["player_input"] == probe.PLAYER_INPUTS[0]
    assert second["player_input"] == probe.PLAYER_INPUTS[1]
    assert [s["text"] for s in second["context"]["attributed_sources"]] == [REPLY]
    assert QUESTION not in probe._json(second)
    assert "Preparação autorada" not in probe._json(first) + probe._json(second)
    assert all(row["request"]["body_sha256"] == probe._sha(body) for row, body in zip(rows, harness[0]))
    before = {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    assert (await verify(prepared, batch, path))["verified"] is True
    assert len(produced) == len(harness[0]) == 2
    assert before == {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}


@pytest.mark.parametrize("failure", ["policy", "429", "schema", "length", "route"])
@pytest.mark.asyncio
async def test_first_failure_stops_second_player_input_and_keeps_p_k_h(harness, failure):
    if failure == "policy": harness[1][0] = response(q="Quem está aqui?")
    elif failure == "429": harness[1][0] = httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": "synthetic quota"}})
    elif failure == "schema": harness[1][0] = response(n="curta")
    elif failure == "length": harness[1][0] = response(finish="length")
    else: harness[1][0] = response(model="wrong-model")
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert doc["process_exit_code"] == (2 if failure == "429" else 1), rows
    assert len(harness[0]) == 1 and rows[1]["kind"] == "source_player_skip"
    assert rows[0]["input_claim"]["status"] == "completed" and rows[0]["input_replay_verified"]
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone() == (3,)
        assert conn.execute("SELECT current_turn,state_revision FROM campaigns").fetchone() == (0, 0)
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.parametrize("location", ["n", "q", "metadata", "header", "error"])
@pytest.mark.asyncio
async def test_key_echo_is_rejected_before_sqlite_or_artifacts(harness, location, capsys):
    if location == "n": reply = response(n=REPLY+" "+KEY)
    elif location == "q": reply = response(q="O que você faz com "+KEY+"?")
    elif location == "metadata": reply = response(extra={"request_id": KEY})
    elif location == "header":
        reply = response()
        reply.headers["x-request-id"] = KEY
    else: reply = httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": KEY}})
    harness[1][0] = reply
    prepared, batch, path, rows = await run()
    assert rows[0]["credential_echo_blocked"] and rows[0]["response_structure"] is None
    assert len(harness[0]) == 1 and rows[0]["result"]["status"] != "completed"
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir() if p.is_file())
    captured = capsys.readouterr()
    assert KEY not in captured.out+captured.err
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_failed_producer_never_creates_k_h_or_second_input(harness, monkeypatch):
    from api import narrative_source_input_service as service
    from api.narrative_source_input import SourceInputFailure
    produced = []
    def refuse(request):
        produced.append(request)
        return SourceInputFailure(code="source_input_out_of_scope", stage="classification")
    monkeypatch.setattr(service, "produce_source_player_action", refuse)
    prepared, batch, path, rows = await run()
    assert len(produced) == 1 and not harness[0]
    assert rows[0]["input_claim"]["status"] == "failed" and rows[0]["capsule"] is rows[0]["result"] is None
    assert rows[1]["kind"] == "source_player_skip"
    assert probe._read_json(path/"summary.json")["process_exit_code"] == 1
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM turns").fetchone() == (0,)
    assert (await verify(prepared, batch, path))["verified"] is True
    assert len(produced) == 1


@pytest.mark.asyncio
async def test_pacing_http_limit_and_request_deadline_are_not_template_deadlines(harness, monkeypatch):
    deadlines = []
    real = probe.ObservationAdapter.generate_structured
    async def generate(self, request):
        deadlines.append((request.deadline-probe.utc_now()).total_seconds())
        return await real(self, request)
    monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", generate)
    prepared, batch, path, rows = await run()
    assert len(deadlines) == 2 and all(55 < seconds <= 60 for seconds in deadlines)
    clock, sleeps = [0.0], []
    async def sleeper(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    budget = probe.DispatchBudget()
    budget.pacer = probe.shared._CallPacer(60, _clock=lambda: clock[0], _sleeper=sleeper)
    budget.pacer._last_call_started_at = 0
    await budget.pacer.before_call(probe.PROBE_KIND)
    clock[0] = 62
    budget.consume()
    clock[0] = 80
    await budget.pacer.before_call(probe.PROBE_KIND)
    assert sleeps == [60, 42]
    budget.consume()
    capsule = probe.validate_source_turn_capsule(rows[0]["capsule"], session_id=batch, operation_id=rows[0]["operation_id"])
    request = probe._request(capsule)
    adapter = probe.ObservationAdapter(prepared=prepared, request=request, api_key=SecretStr(KEY), budget=budget)
    with pytest.raises(Exception):
        await adapter.generate_structured(request)
    assert budget.calls == 2 and not adapter.http_sent and len(harness[0]) == 2
    with pytest.raises(Exception):
        await adapter.generate_structured(request)
    assert len(harness[0]) == 2


@pytest.mark.asyncio
async def test_changed_effective_request_is_rejected_before_http(harness):
    prepared, batch, path, rows = await run()
    capsule = probe.validate_source_turn_capsule(rows[0]["capsule"], session_id=batch, operation_id=rows[0]["operation_id"])
    request, budget = probe._request(capsule), probe.DispatchBudget()
    adapter = probe.ObservationAdapter(prepared=prepared, request=request, api_key=SecretStr(KEY), budget=budget)
    changed = request.model_copy(update={"parameters": probe.GenerationParameters(temperature=.65, max_output_tokens=767)})
    with pytest.raises(Exception):
        await adapter.generate_structured(changed)
    assert not adapter.http_sent and budget.calls == 0 and len(harness[0]) == 2


@pytest.mark.parametrize("event", ["cancel", "drift"])
@pytest.mark.asyncio
async def test_cancellation_or_drift_after_retention_never_dispatches(harness, monkeypatch, event):
    async def changed(self):
        if event == "cancel": raise asyncio.CancelledError()
        monkeypatch.setattr(probe, "PLAYER_INPUTS", ("changed", probe.PLAYER_INPUTS[1]))
    monkeypatch.setattr(probe.DispatchBudget, "wait", changed)
    prepared, batch, path, rows = await run()
    assert not harness[0] and rows[0]["input_claim"]["status"] == "completed" and rows[0]["capsule"] is not None
    assert probe._read_json(path/"summary.json")["process_exit_code"] == (130 if event == "cancel" else 3)
    if event == "cancel": assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_cancellation_after_commit_recovers_without_another_call(harness, monkeypatch):
    real = probe.execute_retained_source_turn
    async def cancelled(**kwargs):
        result = await real(**kwargs)
        if not isinstance(kwargs["gateway"], probe.NoCallGateway) and result.status == "completed":
            raise asyncio.CancelledError()
        return result
    monkeypatch.setattr(probe, "execute_retained_source_turn", cancelled)
    prepared, batch, path, rows = await run()
    doc = probe._read_json(path/"summary.json")
    assert doc["process_exit_code"] == 130 and doc["summary"]["turns_committed"] == 1
    assert len(harness[0]) == 1 and rows[0]["replay_verified"]
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.parametrize("field", ["body", "capsule", "input", "setup", "source", "audit", "producer", "producer-request", "producer-completion", "roster", "orphan"])
@pytest.mark.asyncio
async def test_rehash_cannot_hide_mismatched_manifest_p_k_h_or_sources(harness, field):
    prepared, batch, path, rows = await run()
    edit = None
    if field == "body": rows[0]["request"]["request"]["max_completion_tokens"] = 767
    elif field == "capsule": rows[0]["capsule"]["player_input"] = "forged"
    elif field == "input": rows[0]["input_claim"]["request"]["config"]["npc_aliases"] = []
    elif field == "source": rows[0]["response_structure"]["n"] = WAIT_REPLY
    elif field == "audit": rows[0]["evidence"]["usage"]["input_tokens"] += 1
    elif field == "setup":
        changed = probe.create_source_setup_manifest({**probe.SETUP, "declared_objective": "changed"}, session_id=batch).model_dump(mode="json")
        def edit(doc): doc["setup_manifest"] = changed
        with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
            raw = json.loads(conn.execute("SELECT metadata_json FROM campaigns").fetchone()[0])
            raw["narrative_source_setup_manifest"] = changed
            conn.execute("UPDATE campaigns SET metadata_json=?", (probe._json(raw),))
    else:
        with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
            if field == "producer":
                conn.execute("UPDATE attempts SET result_hash=? WHERE operation_id=?", ("0"*64, probe.source_input_operation_id(batch, rows[0]["operation_id"])))
            elif field in ("producer-request", "producer-completion"):
                from api.narrative_source_input import REQUEST_KEY, COMPLETION_KEY
                p_id = probe.source_input_operation_id(batch, rows[0]["operation_id"])
                raw = json.loads(conn.execute("SELECT metadata_json FROM attempts WHERE operation_id=?", (p_id,)).fetchone()[0])
                if field == "producer-request": raw[REQUEST_KEY]["player_input"] = "changed"
                else: raw[COMPLETION_KEY]["capsule_sha256"] = "0"*64
                conn.execute("UPDATE attempts SET metadata_json=? WHERE operation_id=?", (probe._json(raw), p_id))
            elif field == "roster":
                raw = json.loads(conn.execute("SELECT metadata_json FROM campaigns").fetchone()[0])
                raw["narrative_source_setup_manifest"]["request"]["npcs_present"] = []
                conn.execute("UPDATE campaigns SET metadata_json=?", (probe._json(raw),))
            else:
                conn.row_factory = sqlite3.Row
                record = dict(conn.execute("SELECT * FROM attempts LIMIT 1").fetchone())
                record.pop("id")
                record.update(session_id="orphan", operation_id="orphan-op", attempt_id="orphan-attempt")
                conn.execute("INSERT INTO attempts ("+",".join(record)+") VALUES ("+",".join("?" for _ in record)+")", tuple(record.values()))
    rewrite(path, rows, edit)
    with pytest.raises(Exception):
        await verify(prepared, batch, path)


@pytest.mark.asyncio
async def test_missing_p_is_rejected_before_verifier_can_produce_a_replacement(harness, monkeypatch):
    from api import narrative_source_input_service as service
    prepared, batch, path, rows = await run()
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        conn.execute("DELETE FROM attempts WHERE operation_id=?", (probe.source_input_operation_id(batch, rows[0]["operation_id"]),))
    rewrite(path, rows)
    monkeypatch.setattr(service, "produce_source_player_action", lambda *args: pytest.fail("verifier produced a replacement"))
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)
    assert len(harness[0]) == 2


@pytest.mark.parametrize("syntax", ["duplicate", "nan"])
@pytest.mark.asyncio
async def test_jsonl_duplicate_keys_or_nonfinite_numbers_are_closed(harness, syntax):
    prepared, batch, path, rows = await run()
    file = path/(probe.CANDIDATE_ID+".jsonl")
    raw = file.read_text(encoding="utf-8")
    if syntax == "duplicate": raw = raw.replace('{"batch_id":', '{"batch_id":"'+batch+'","batch_id":', 1)
    else: raw = raw.replace(probe._json(rows[0]["http_started_at"]), 'NaN', 1)
    file.write_text(raw, encoding="utf-8")
    doc = probe._read_json(path/"summary.json")
    doc["artifacts"]["records"]["sha256"] = probe.shared._sha256(file)
    (path/"summary.json").write_text(probe._json(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)


def test_preflight_has_no_key_read_database_receipt_or_network(monkeypatch, capsys):
    original = probe.os.environ.get
    def guarded(key, *args):
        assert "KEY" not in key and "TOKEN" not in key
        return original(key, *args)
    monkeypatch.setattr(probe.os.environ, "get", guarded)
    monkeypatch.setattr(probe, "ProbePersistence", lambda *args: pytest.fail("preflight opened a database"))
    monkeypatch.setattr(probe, "prepare_source_player_action", lambda *args: pytest.fail("preflight produced action"))
    assert probe.main(["--preflight"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["purpose"] == "source_player_probe" and doc["experiment_version"] == "source-player-observation-v1"
    assert doc["generation_parameters"] == probe.PARAMETERS and doc["max_calls"] == 2
    assert doc["first_request_template"]["requires_retained_capsule"] is True
    assert doc["first_request_template"]["is_live_request"] is False
    assert doc["first_request_template"]["body_sha256"] is None
    assert "request" not in doc["first_request_template"]
    assert doc["inputs"]["case"]["data"]["producer_context"]["npc_aliases"] == ["Mara"]
    assert doc["inputs"]["prompt"]["sha256"] == probe.PROMPT_SHA256


@pytest.mark.parametrize("tamper", ["hash", "alias", "parameter", "case"])
def test_frozen_preflight_is_checked_before_reading_credential(tmp_path, monkeypatch, tamper, capsys):
    prepared = probe.prepare_experiment()
    data = copy.deepcopy(prepared.metadata)
    if tamper == "alias": data["inputs"]["case"]["data"]["producer_context"]["npc_aliases"] = []
    elif tamper == "parameter": data["generation_parameters"]["max_output_tokens"] = 999
    elif tamper == "case": data["inputs"]["case"]["data"]["turns"][0]["player_input"] = "changed"
    file = tmp_path/"preflight.json"
    file.write_text(probe._json(data), encoding="utf-8")
    digest = "0"*64 if tamper == "hash" else probe.shared._sha256(file)
    original = probe.os.environ.get
    def guarded(key, *args):
        assert key != probe.KEY_ENV
        return original(key, *args)
    monkeypatch.setattr(probe.os.environ, "get", guarded)
    code = probe.main(["--live", "--allow-synthetic-only", "--batch-id", str(uuid4()),
        "--expected-preflight", str(file), "--expected-preflight-sha256", digest])
    assert code == 3
    assert "source_player_probe_preflight_or_verification_failed" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_blank_credential_existing_path_and_foreign_path_never_dispatch(harness, tmp_path):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    with pytest.raises(ValueError):
        await probe.evaluate_probe(prepared, api_key=SecretStr(" "), batch_id=batch, run_directory=path)
    with pytest.raises(ValueError):
        await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=tmp_path/"foreign")
    assert not path.exists()
    path.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path)
    assert not harness[0]


@pytest.mark.parametrize("terminal", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_cancellation_after_p_settles_observes_existing_p_k_without_producing_again(harness, monkeypatch, terminal):
    from api import narrative_source_input_service as service
    from api.narrative_source_input import SourceInputFailure
    original_prepare = probe._prepare
    if terminal == "cancelled":
        monkeypatch.setattr(service, "produce_source_player_action", lambda request:
            SourceInputFailure(code="source_input_cancelled", stage="production"))
    async def cancelled_after_p(*args, **kwargs):
        result = await original_prepare(*args, **kwargs)
        if not kwargs.get("replay"):
            monkeypatch.setattr(service, "produce_source_player_action", lambda *args: pytest.fail("recovery reproduced P"))
            raise asyncio.CancelledError()
        return result
    monkeypatch.setattr(probe, "_prepare", cancelled_after_p)
    prepared, batch, path, rows = await run()
    assert not harness[0]
    assert rows[0]["input_claim"]["status"] == terminal and rows[0]["input_replay_verified"]
    assert (rows[0]["capsule"] is not None) == (terminal == "completed")
    doc = probe._read_json(path/"summary.json")
    assert doc["process_exit_code"] == 130 and doc["summary"]["turns_committed"] == 0
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone() == ((2 if terminal == "completed" else 1),)
    assert (await verify(prepared, batch, path))["verified"] is True


@pytest.mark.asyncio
async def test_valid_rolled_receipt_is_not_certified_for_this_declaration_only_fixture(harness, monkeypatch):
    from api import narrative_source_input_service as service
    from api.narrative_source_preparation import ResolvedActionPreparation
    from api.rules_service import V5ActionPayload, V5Attribute, V5Skill
    from tests.test_narrative_source_preparation import receipt
    def unrelated_roll(request):
        return ResolvedActionPreparation(action=V5ActionPayload(intent=request.player_input,
            attribute=V5Attribute.Intelligence, skill=V5Skill.INVESTIGATION, requires_roll=True,
            is_aggressive=False, inferred_difficulty=2), resolution=receipt())
    monkeypatch.setattr(service, "produce_source_player_action", unrelated_roll)
    prepared, batch, path, rows = await run()
    assert rows[0]["input_claim"]["status"] == "completed"
    assert rows[0]["capsule"]["preparation"]["kind"] == "ordinary_resolution"
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)


@pytest.mark.parametrize("change", ["code", "stage", "causal_code"])
@pytest.mark.asyncio
async def test_rehashed_h_diagnostic_must_be_closed_and_compatible_with_observed_proposal(harness, monkeypatch, change):
    async def delivery_failure(_text):
        raise RuntimeError("synthetic delivery failure")
    monkeypatch.setattr(probe.retained, "_no_chunk", delivery_failure)
    prepared, batch, path, rows = await run()
    assert rows[0]["result"]["error"]["code"] == "source_turn_delivery_failed"
    error = copy.deepcopy(rows[0]["result"]["error"])
    if change == "code": error["code"] = "PRIVATE_SENTINEL"
    elif change == "stage": error["stage"] = "PRIVATE_SENTINEL"
    else: error["code"] = "source_turn_preflight_failed"
    rows[0]["result"]["error"] = error
    with sqlite3.connect(path/probe.DATABASE_NAME) as conn:
        conn.row_factory = sqlite3.Row
        stored = dict(conn.execute("SELECT * FROM attempts WHERE operation_id=?", (rows[0]["operation_id"],)).fetchone())
        payload = {"status": stored["status"], "requested_turn": stored["requested_turn"],
            "user_input": stored["user_input"], "partial_narrative": stored["partial_narrative"], "error": error,
            "provenance": json.loads(stored["provenance_json"]), "usage": json.loads(stored["usage_json"]),
            "metadata": json.loads(stored["metadata_json"])}
        conn.execute("UPDATE attempts SET error_json=?,result_hash=? WHERE operation_id=?",
            (probe._json(error), probe._sha(payload), rows[0]["operation_id"]))
    rewrite(path, rows)
    with pytest.raises(ValueError):
        await verify(prepared, batch, path)
