"""Three authored dialogue cases; synthetic HTTPX only, with no database or live key."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from scripts import evaluate_source_dialogue_response as probe

KEY = "synthetic-dialogue-response-key-not-persisted"
N_DIRECT = ('Mara volta o rosto e responde: "É uma galeria. Posso falar do que está à vista, mas não conheço toda a história deste lugar." '
    'Ela indica a parede próxima e mantém a mão suspensa por um instante. A luz recorta os dedos antes que o braço desça. '
    '"O que você gostaria de saber sobre o que temos aqui?", acrescenta Mara, deixando a pergunta entre as duas vozes.')
N_RECOVERY = ('Mara continua junto ao banco e responde: "Não conheço a história inteira deste lugar. Sei que estamos numa galeria, '
    'mas não posso explicar tudo o que aconteceu aqui." Ela afrouxa os dedos na alça da bolsa e encara a parede iluminada. '
    '"Posso conversar aqui antes de seguir", acrescenta Mara. A água permanece audível ao fundo, enquanto a resposta interrompe a pausa.')
N_WAIT = ('A borda da poça alcança a folha junto ao banco de pedra da Galeria. Uma faixa escura aparece no papel quando a água '
    'toca sua ponta, antes seca. Mara abaixa o rosto na direção da mancha e afasta a mão do corpo, mas ainda não recolhe a folha. '
    'O gotejar continua, acrescentando pequenos círculos à superfície da água.')
N_EXTRA_NPC = ('Mara permanece junto ao banco de pedra. A luz das tochas atravessa a Galeria e encontra a parede úmida. '
    'Ao fundo, a água continua pingando em intervalos regulares. Caio entra na galeria e acena para Mara.')
Q = "O que você faz agora?"


def response(n=N_DIRECT, q=Q, *, model=probe.GROQ_QWEN_MODEL_ID, finish="stop", extra=None, proposal=None):
    value = {"model": model, "choices": [{"finish_reason": finish, "message": {"role": "assistant",
        "content": json.dumps(proposal if proposal is not None else {"n": n, "q": q}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 120, "total_tokens": 420}}
    value.update(extra or {})
    return httpx.Response(200, json=value)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT_ROOT", tmp_path / "results")
    from api.llm import contract
    from api.llm.adapters import groq, openai_compatible
    base, clock = datetime.now(timezone.utc), [0.0]
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
        pytest.fail("Pure diagnostic attempted SQLite")
    monkeypatch.setattr(sqlite3, "connect", no_database)
    seen, replies = [], [response(), response(N_RECOVERY), response(N_WAIT)]
    def handle(request):
        seen.append(json.loads(request.content))
        item = replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item(request) if callable(item) else item
    return dict(seen=seen, replies=replies, budget=budget, clock=clock, transport=httpx.MockTransport(handle))


async def run(harness):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path,
        transport=harness["transport"], budget=harness["budget"]())
    return prepared, batch, path, rows


def expected(prepared, path):
    target = path.parent / (path.name + "-preflight.json")
    target.write_text(probe._json(prepared.metadata), encoding="utf-8")
    return target, probe.shared._sha256(target)


def verify(prepared, batch, path):
    target, digest = expected(prepared, path)
    return probe.verify_artifacts(path / "summary.json", target, batch, expected_preflight_sha256=digest)


def rewrite(path, rows, *, document_change=None):
    """Rehash malicious JSONL and derived summary to avoid testing only hash mismatch."""
    document = probe._read_json(path / "summary.json")
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


def test_preflight_freezes_three_independent_authored_contexts_and_same_public_contract(harness):
    prepared = probe.prepare_experiment()
    assert prepared.metadata == probe.prepare_experiment().metadata
    frozen = prepared.metadata["frozen_requests"]
    assert [(r["slot_id"], r["case_id"]) for r in frozen] == list(probe.SLOTS)
    assert len({r["user_packet"] for r in frozen}) == 3
    for index, row in enumerate(frozen):
        assert row["npc_aliases"] == ["Mara"]
        assert row["request"]["messages"][0]["content"] == prepared.prompt
        assert row["request"]["reasoning_effort"] == "none"
        assert row["request"]["max_completion_tokens"] == 768
        assert row["request"]["temperature"] == .65
        assert row["request"]["response_format"]["json_schema"]["strict"] is True
        assert row["body_sha256"] == probe._sha(row["request"])
        packet = json.loads(row["user_packet"])
        assert packet["player_input"] == prepared.corpus["cases"][index]["player_input"]
        assert packet["server_facts"] == []
        assert row["authored_source"]["provider_evidence"] is None
        assert row["authored_source"]["application_commit"] is False
        sources = packet["context"]["attributed_sources"]
        if index == 0:
            assert sources == [] and row["authored_source"]["projection"] is None
        else:
            assert len(sources) == 1
            assert sources[0]["text"] == prepared.corpus["cases"][index]["source_text"]
            assert Q not in row["user_packet"]
    assert prepared.metadata["generation_parameters"] == probe.PARAMETERS
    assert prepared.metadata["max_calls"] == 3
    assert not harness["seen"]


@pytest.mark.asyncio
async def test_success_uses_real_alias_policy_and_independent_sources_with_readonly_verification(harness, monkeypatch):
    observed = []
    original = probe.profile.validate_source_proposal
    def validate(*args, **kwargs):
        observed.append(kwargs.get("npc_aliases"))
        return original(*args, **kwargs)
    monkeypatch.setattr(probe.profile, "validate_source_proposal", validate)
    prepared, batch, path, rows = await run(harness)
    assert [row["outcome"] for row in rows] == ["accepted"] * 3, rows
    assert len(harness["seen"]) == 3 and harness["clock"][0] == 180
    assert observed and all(aliases == ("Mara",) for aliases in observed)
    for index, row in enumerate(rows):
        assert row["request"]["request"] == harness["seen"][index] == prepared.metadata["frozen_requests"][index]["request"]
        assert all(n not in row["request"]["user_packet"] for n in (N_DIRECT, N_RECOVERY, N_WAIT))
        assert row["measurements"]["length_passed"] is True
        created = probe._aware(row["request_created_at"])
        assert probe._aware(row["request"]["deadline"]) - created == timedelta(seconds=60)
        assert created == probe._aware(row["http_started_at"])
    assert set(p.name for p in path.iterdir()) == {"summary.json", "records.jsonl"}
    hashes = {p.name: probe.shared._sha256(p) for p in path.iterdir()}
    assert verify(prepared, batch, path)["process_exit_code"] == 0
    assert hashes == {p.name: probe.shared._sha256(p) for p in path.iterdir()}
    assert probe._read_json(path / "summary.json")["summary"]["semantic_fidelity_review"] == {"status": "not_performed", "approval": None}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["policy", "schema", "extra_schema", "player_agency", "too_long", "q_too_long", "length", "429", "401", "503", "route", "timeout"])
async def test_first_failure_stops_all_remaining_slots_without_retry(harness, failure):
    if failure == "policy": reply = response(q="Quem está aqui?")
    elif failure == "schema": reply = response(n="curta")
    elif failure == "extra_schema": reply = response(proposal={"n": N_DIRECT, "q": Q, "server_facts": ["inventado"]})
    elif failure == "player_agency": reply = response(n=N_DIRECT + " Você abre a porta.")
    elif failure == "too_long": reply = response(n="A parede permanece no local. " * 31)
    elif failure == "q_too_long": reply = response(q="O que você faz agora nesta sala com todos os detalhes que foram apresentados nesta conversa?")
    elif failure == "length": reply = response(finish="length")
    elif failure in ("429", "401", "503"):
        reply = httpx.Response(int(failure), json={"error": {"code": "rate_limit_exceeded" if failure == "429" else "synthetic_failure"}})
    elif failure == "timeout": reply = httpx.ReadTimeout("synthetic")
    else: reply = response(model="unrequested-model")
    harness["replies"][0] = reply
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 1, rows
    assert [row["kind"] for row in rows[1:]] == ["source_dialogue_response_skip"] * 2
    assert verify(prepared, batch, path)["process_exit_code"] != 0


@pytest.mark.asyncio
async def test_second_policy_failure_keeps_first_response_but_never_feeds_it_forward(harness):
    harness["replies"][1] = response(N_RECOVERY, q="Quem está aqui?")
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 2 and rows[0]["outcome"] == "accepted"
    assert rows[1]["outcome"] == "policy_rejected" and rows[2]["kind"] == "source_dialogue_response_skip"
    assert N_DIRECT not in rows[1]["request"]["user_packet"]
    assert verify(prepared, batch, path)["process_exit_code"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["n", "q", "metadata", "header", "error"])
async def test_key_echo_is_blocked_before_artifacts_and_stops(harness, location, capsys):
    if location == "n": reply = response(n=N_DIRECT + " " + KEY)
    elif location == "q": reply = response(q=KEY)
    elif location == "metadata": reply = response(extra={"request_id": KEY})
    elif location == "header": reply = response(); reply.headers["x-request-id"] = KEY
    else: reply = httpx.Response(429, json={"error": {"code": "rate_limit_exceeded", "message": KEY}})
    harness["replies"][0] = reply
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == 1 and rows[0]["credential_echo_blocked"] is True
    assert rows[0]["response_structure"] is rows[0]["evidence"] is rows[0]["llm_error"] is None
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir())
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["wait", "transport"])
async def test_cancellation_is_recorded_as_cancelled_with_remaining_skips(harness, monkeypatch, stage):
    if stage == "wait":
        async def cancel(self): raise asyncio.CancelledError
        monkeypatch.setattr(probe.DispatchBudget, "wait", cancel)
    else:
        harness["replies"][0] = asyncio.CancelledError()
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == (stage == "transport")
    assert rows[0]["outcome"] == "cancelled"
    assert all(row["reason"] == "cancelled" for row in rows[1:])
    assert verify(prepared, batch, path)["process_exit_code"] == 130


@pytest.mark.asyncio
async def test_raw_local_exception_is_never_persisted(harness, monkeypatch):
    async def fail(self, request): raise RuntimeError(KEY)
    monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", fail)
    prepared, batch, path, rows = await run(harness)
    assert not harness["seen"] and rows[0]["local_error"]["stage"] == "transport"
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir())
    assert verify(prepared, batch, path)["process_exit_code"] == 3


@pytest.mark.asyncio
async def test_global_budget_rejects_early_duplicate_out_of_order_and_fourth_dispatch(harness):
    budget = harness["budget"]()
    with pytest.raises(ValueError): budget.consume("slot-1")
    for slot, _ in probe.SLOTS:
        await budget.wait()
        with pytest.raises(ValueError): budget.consume("slot-99")
        budget.consume(slot)
        with pytest.raises(ValueError): budget.consume(slot)
    await budget.wait()
    with pytest.raises(ValueError): budget.consume("slot-4")
    assert budget.calls == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("attack", ["payload", "deadline", "duplicate", "url", "method", "body"])
async def test_exact_http_boundary_rejects_mutations_before_transport(harness, attack):
    prepared, batch, budget = probe.prepare_experiment(), str(uuid4()), harness["budget"]()
    await budget.wait()
    request = probe.make_request(prepared, 0, batch, deadline=probe.utc_now() + timedelta(seconds=60))
    adapter = probe.ObservationAdapter(prepared=prepared, request=request, api_key=SecretStr(KEY),
        budget=budget, slot="slot-1", transport=harness["transport"])
    if attack in ("url", "method", "body"):
        method = "GET" if attack == "method" else "POST"
        url = "https://invalid.example/chat/completions" if attack == "url" else probe.GROQ_OFFICIAL_BASE_URL + "/chat/completions"
        body = {} if attack == "body" else probe._body(request)
        with pytest.raises(ValueError): await adapter._dispatch(httpx.Request(method, url, json=body))
    else:
        if attack == "payload": request = request.model_copy(update={"parameters": probe.GenerationParameters(temperature=.2, max_output_tokens=768)})
        elif attack == "deadline": harness["clock"][0] += 60
        else: await adapter.generate_structured(request)
        with pytest.raises((ValueError, probe.LLMInvocationError)): await adapter.generate_structured(request)
    assert len(harness["seen"]) == (1 if attack == "duplicate" else 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["no_http", "case", "source", "question_source", "request", "body_hash", "deadline", "created", "overlap", "evidence", "usage", "observation_extra", "skip", "extra_record", "missing_record", "policy", "metadata"])
async def test_verifier_rejects_forged_records_even_with_new_hash_and_summary(harness, change):
    prepared, batch, path, rows = await run(harness)
    if change == "no_http": rows[0].update(call_made=False, http_started_at=None)
    elif change == "case": rows[1]["case_id"] = "direct-question"
    elif change == "source": rows[1]["authored_source"]["provider_evidence"] = {"provider": "Groq"}
    elif change == "question_source": rows[1]["authored_source"]["projection"]["source"]["text"] += Q
    elif change == "request": rows[1]["request"]["user_packet"] = "{}"
    elif change == "body_hash": rows[0]["request"]["body_sha256"] = "0" * 64
    elif change == "deadline": rows[0]["request"]["deadline"] = rows[0]["request_created_at"]
    elif change == "created": rows[0]["request_created_at"] = "2000-01-01T00:00:00+00:00"
    elif change == "overlap": rows[1]["http_started_at"] = rows[0]["http_started_at"]
    elif change == "evidence": rows[0]["evidence"]["invocation_id"] = str(uuid4())
    elif change == "usage": rows[0]["evidence"]["usage"]["input_tokens"] += 1
    elif change == "observation_extra": rows[0]["provider_observation"]["free_text"] = "synthetic"
    elif change == "skip": rows[1] = probe._skip(1, "previous_failure")
    elif change == "extra_record": rows.append(copy.deepcopy(rows[0]))
    elif change == "missing_record": rows.pop()
    elif change == "policy": rows[0]["policy_valid"] = False
    rewrite(path, rows, document_change=(lambda doc: doc["metadata"].update(max_calls=4)) if change == "metadata" else None)
    with pytest.raises((ValueError, TypeError)): verify(prepared, batch, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["unavailable", "http_error", "finish", "usage_unavailable", "output_limit", "finished_late", "total_output"])
async def test_observer_contradictions_or_limits_cannot_be_rehashed_into_success(harness, change):
    prepared, batch, path, rows = await run(harness)
    row = rows[0]
    if change == "unavailable": row["provider_observation"] = probe._unavailable_observation()
    elif change == "http_error": row["provider_observation"].update(http_status=429, finish_reason="length", provider_code="rate_limit_exceeded")
    elif change == "finish": row["provider_observation"]["finish_reason"] = "length"
    elif change == "usage_unavailable": row["provider_observation"]["usage"]["output_tokens"] = None
    elif change in ("output_limit", "total_output"):
        for item in (rows if change == "total_output" else [row]):
            for usage in (item["evidence"]["usage"], item["provider_observation"]["usage"]): usage.update(output_tokens=769, total_tokens=1069)
    else: row["evidence"]["finished_at"] = (probe._aware(row["request"]["deadline"]) + timedelta(seconds=60)).isoformat()
    rewrite(path, rows)
    with pytest.raises(ValueError): verify(prepared, batch, path)
    for index, item in enumerate(rows): item["operational_error"] = probe._operational_error(item, rows[:index])
    if change == "total_output": assert "batch_output_limit_exceeded" in rows[-1]["operational_error"]["codes"]
    rewrite(path, rows)
    with pytest.raises(ValueError): verify(prepared, batch, path)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["output_limit", "late_return", "unknown_usage", "last_slot"])
async def test_usage_and_deadline_observations_preserve_original_capture(harness, monkeypatch, failure):
    if failure in ("output_limit", "last_slot"):
        index = 2 if failure == "last_slot" else 0
        harness["replies"][index] = response(N_WAIT if index else N_DIRECT,
            extra={"usage": {"prompt_tokens": 300, "completion_tokens": 769, "total_tokens": 1069}})
    elif failure == "late_return":
        original = probe.ObservationAdapter.generate_structured
        async def delayed(self, request):
            result = await original(self, request)
            harness["clock"][0] += 61
            self.capture["evidence"]["finished_at"] = probe.utc_now().isoformat()
            return result
        monkeypatch.setattr(probe.ObservationAdapter, "generate_structured", delayed)
    else:
        harness["replies"][:] = [response(n, extra={"usage": None}) for n in (N_DIRECT, N_RECOVERY, N_WAIT)]
    prepared, batch, path, rows = await run(harness)
    assert len(harness["seen"]) == (3 if failure in ("unknown_usage", "last_slot") else 1)
    if failure == "unknown_usage":
        assert all(probe._output_tokens(row) is None for row in rows)
        assert all(row["evidence"]["usage"]["status"] == "unavailable" for row in rows)
    else:
        row = rows[2 if failure == "last_slot" else 0]
        assert row["operational_error"] is not None and row["response_structure"] is not None
    assert verify(prepared, batch, path)["process_exit_code"] == (0 if failure == "unknown_usage" else 3)


@pytest.mark.asyncio
@pytest.mark.parametrize("attack", ["duplicate_json", "nan", "wrong_path", "preflight_hash", "preflight_schema", "preflight_body", "preflight_aliases"])
async def test_artifact_envelopes_and_frozen_inputs_reject_forgery(harness, attack, tmp_path):
    prepared, batch, path, rows = await run(harness)
    target, digest = expected(prepared, path)
    summary = path / "summary.json"
    if attack == "duplicate_json": summary.write_text(summary.read_text().replace('{"artifacts":', '{"batch_id":"fake","artifacts":', 1))
    elif attack == "nan": summary.write_text(summary.read_text().replace('"process_exit_code":0', '"process_exit_code":NaN', 1))
    elif attack == "wrong_path":
        other = tmp_path / "summary.json"; other.write_bytes(summary.read_bytes()); summary = other
    elif attack == "preflight_hash": digest = "0" * 64
    else:
        changed = copy.deepcopy(prepared.metadata)
        if attack == "preflight_schema": changed["inputs"]["response_schema_sha256"] = "0" * 64
        elif attack == "preflight_body": changed["frozen_requests"][0]["request"]["temperature"] = .2
        else: changed["frozen_requests"][0]["npc_aliases"] = []
        target.write_text(probe._json(changed)); digest = probe.shared._sha256(target)
    with pytest.raises(ValueError): probe.verify_artifacts(summary, target, batch, expected_preflight_sha256=digest)


@pytest.mark.parametrize("change", ["prompt", "corpus", "metadata", "candidate"])
def test_prepared_mutations_fail_before_dispatch(change):
    prepared = probe.prepare_experiment()
    if change == "prompt": object.__setattr__(prepared, "prompt", prepared.prompt + " changed")
    elif change == "corpus": prepared.corpus["cases"][0]["npc_aliases"] = []
    elif change == "candidate": object.__setattr__(prepared.candidate, "model", "other")
    else: prepared.metadata["slots"].reverse()
    with pytest.raises(ValueError): probe._check_prepared(prepared)


@pytest.mark.parametrize("args", [["--preflight", "--api-key-env", probe.KEY_ENV], ["--preflight", "--allow-synthetic-only"],
    ["--live"], ["--verify-artifacts", "missing", "--api-key-env", probe.KEY_ENV], ["--api-key-env", KEY]])
def test_invalid_cli_has_closed_error_without_credential_access(args, monkeypatch, capsys):
    def forbidden(*args, **kwargs): pytest.fail("Invalid CLI accessed environment")
    monkeypatch.setattr(probe, "os", SimpleNamespace(environ=SimpleNamespace(pop=forbidden, get=forbidden)))
    assert probe.main(args) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and KEY not in captured.err


def test_preflight_cli_never_requests_a_key(harness, monkeypatch, capsys):
    def forbidden(*args, **kwargs): pytest.fail("Preflight accessed environment")
    monkeypatch.setattr(probe, "os", SimpleNamespace(environ=SimpleNamespace(pop=forbidden, get=forbidden)))
    assert probe.main(["--preflight"]) == 0
    assert json.loads(capsys.readouterr().out)["max_calls"] == 3
    assert not harness["seen"]


def test_known_free_text_roster_limitation_is_not_promoted_to_semantic_approval():
    prepared = probe.prepare_experiment()
    case = prepared.corpus["cases"][2]
    # Existing policy accepts this prose; this diagnostic must not invent a stronger gate.
    proposal = probe.profile.validate_source_proposal({"n": N_EXTRA_NPC, "q": Q},
        current_scene=probe.SceneState.model_validate(case["scene"]), facts=(), player_input=case["player_input"], npc_aliases=("Mara",))
    assert proposal.narrative == N_EXTRA_NPC
    assert prepared.metadata["semantic_review"]["status"] == "not_performed"
    assert prepared.metadata["semantic_review"]["approval"] is None


@pytest.mark.parametrize("mode", ["success", "preflight_drift"])
def test_live_removes_dedicated_key_before_git_children_and_verify_never_reads_it(harness, monkeypatch, capsys, mode):
    inherited = []
    def git(arguments, **kwargs):
        assert arguments in (["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain", "--untracked-files=normal"])
        child_environment = kwargs.get("env", os.environ)
        inherited.append(probe.KEY_ENV in child_environment)
        return SimpleNamespace(stdout="5e563824fcba4c53cc37b5084a8ce65f3fa30356\n" if arguments[1] == "rev-parse" else " M synthetic\n")
    monkeypatch.setattr(probe.shared.subprocess, "run", git)
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    path.parent.mkdir(parents=True)
    target, digest = expected(prepared, path)
    if mode == "preflight_drift":
        value = probe._read_json(target)
        value["max_calls"] = 4
        target.write_text(probe._json(value), encoding="utf-8")
        digest = probe.shared._sha256(target)
    original = probe.evaluate_probe
    async def synthetic_only(*args, **kwargs):
        assert kwargs["api_key"].get_secret_value() == KEY
        assert probe.KEY_ENV not in os.environ
        return await original(*args, **kwargs, transport=harness["transport"], budget=harness["budget"]())
    monkeypatch.setattr(probe, "evaluate_probe", synthetic_only)
    inherited.clear()
    monkeypatch.setenv(probe.KEY_ENV, KEY)
    code = probe.main(["--live", "--allow-synthetic-only", "--batch-id", batch,
        "--expected-preflight", str(target), "--expected-preflight-sha256", digest, "--api-key-env", probe.KEY_ENV])
    assert inherited and not any(inherited), "Dedicated live key would be inherited by provenance Git children"
    assert probe.KEY_ENV not in os.environ
    assert code == (0 if mode == "success" else 3)
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    if mode == "preflight_drift":
        assert not harness["seen"] and not path.exists()
    else:
        assert len(harness["seen"]) == 3
        def forbidden(*args, **kwargs): pytest.fail("Verifier accessed credential environment")
        monkeypatch.setattr(probe, "os", SimpleNamespace(environ=SimpleNamespace(pop=forbidden, get=forbidden)))
        assert probe.main(["--verify-artifacts", str(path / "summary.json"), "--batch-id", batch,
            "--expected-preflight", str(target), "--expected-preflight-sha256", digest]) == 0
        assert json.loads(capsys.readouterr().out)["verified"] is True
