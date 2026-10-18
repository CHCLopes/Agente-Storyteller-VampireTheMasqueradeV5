"""Bounded integration in temporary SQLite with HTTPX MockTransport and synthetic key."""
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

from scripts import evaluate_source_dialogue_continuity as probe

KEY = 'synthetic-dialogue-continuity-key-never-persisted'
N1 = ('Mara volta o rosto e responde: "É uma galeria. Posso falar do que está à vista, mas não conheço toda a história deste lugar." '
    'Ela indica a parede próxima e mantém a mão suspensa por um instante. A luz recorta os dedos antes que o braço desça. '
    '"O que você gostaria de saber sobre o que temos aqui?", acrescenta Mara, deixando a pergunta entre as duas vozes.')
N2 = ('Mara esclarece: "Quis dizer que posso descrever o que conheço desta galeria. A história completa não está ao meu alcance." '
    'Ela baixa a mão que havia erguido e olha para a parede próxima. "Não vou inventar uma explicação para preencher o que não sei", '
    'acrescenta Mara. A resposta mantém um limite claro, enquanto o ruído da água continua ao fundo.')
Q = 'O que você faz agora?'


def response(n=N1, q=Q, *, model=probe.GROQ_QWEN_MODEL_ID, finish='stop', usage=120):
    return httpx.Response(200, json={'model': model, 'choices': [{'finish_reason': finish,
        'message': {'role': 'assistant', 'content': json.dumps({'n': n, 'q': q}, ensure_ascii=False)}}],
        'usage': None if usage is None else {'prompt_tokens': 300, 'completion_tokens': usage, 'total_tokens': 300 + usage}})


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, 'OUTPUT_ROOT', tmp_path / 'results')
    from api.llm import contract
    from api.llm.adapters import groq, openai_compatible
    from api import narrative_source_input_service as service, rules_service
    base, clock = datetime.now(timezone.utc), [0.0]
    def now(): return base + timedelta(seconds=clock[0])
    for module in (probe, probe.retained, contract, groq, openai_compatible):
        monkeypatch.setattr(module, 'utc_now', now)
    async def sleep(seconds):
        clock[0] += seconds
        await asyncio.sleep(0)
    def budget(): return probe.DispatchBudget(_clock=lambda: clock[0], _sleeper=sleep)
    monkeypatch.setattr(rules_service.random, 'randint', lambda *args: pytest.fail('Dialogue must not roll'))
    produced, preparation_deadlines, generation_deadlines = [], [], []
    actual_produce, actual_prepare, actual_execute = service.produce_source_player_action, probe.prepare_source_player_action, probe.execute_retained_source_turn
    def produce(request):
        produced.append(request)
        return actual_produce(request)
    async def prepare(**kwargs):
        preparation_deadlines.append(kwargs['deadline'])
        return await actual_prepare(**kwargs)
    async def execute(**kwargs):
        if not isinstance(kwargs['gateway'], probe.NoCallGateway): generation_deadlines.append(kwargs['deadline'])
        return await actual_execute(**kwargs)
    monkeypatch.setattr(service, 'produce_source_player_action', produce)
    monkeypatch.setattr(probe, 'prepare_source_player_action', prepare)
    monkeypatch.setattr(probe, 'execute_retained_source_turn', execute)
    seen, replies = [], [response(), response(N2)]
    def handle(request):
        seen.append(json.loads(request.content))
        item = replies.pop(0)
        if isinstance(item, BaseException): raise item
        return item(request) if callable(item) else item
    return dict(clock=clock, now=now, seen=seen, replies=replies, budget=budget, transport=httpx.MockTransport(handle),
        produced=produced, preparation_deadlines=preparation_deadlines, generation_deadlines=generation_deadlines)


async def run(harness):
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch)
    rows = await probe.evaluate_probe(prepared, api_key=SecretStr(KEY), batch_id=batch, run_directory=path,
        transport=harness['transport'], budget=harness['budget']())
    return prepared, batch, path, rows


def expected(prepared, path):
    target = path.parent / (path.name + '-preflight.json')
    target.write_text(probe._json(prepared.metadata), encoding='utf-8')
    return target, probe.shared._sha256(target)


async def verify(prepared, batch, path):
    target, digest = expected(prepared, path)
    return await asyncio.to_thread(probe.verify_artifacts, path / 'summary.json', target, batch, expected_preflight_sha256=digest)


def rewrite(path, rows, edit=None):
    document = probe._read_json(path / 'summary.json')
    raw = path / 'records.jsonl'
    raw.write_text(''.join(probe._json({'metadata': document['metadata'], 'batch_id': document['batch_id'], 'record': row}) + '\n' for row in rows), encoding='utf-8')
    document['artifacts']['records']['sha256'] = probe.shared._sha256(raw)
    document['artifacts']['database']['sha256'] = probe.shared._sha256(path / probe.DATABASE_NAME)
    document['database_snapshot'] = probe._database_snapshot(path / probe.DATABASE_NAME)
    try:
        document['summary'] = probe.summarize(rows, document['evaluation_status'])
        document['process_exit_code'] = document['summary']['process_exit_code']
    except ValueError:
        pass
    if edit: edit(document)
    (path / 'summary.json').write_text(probe._json(document), encoding='utf-8')


def test_preflight_is_a_recipe_without_future_response_body_or_database(harness, monkeypatch):
    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: pytest.fail('Preflight attempted database access'))
    first = probe.prepare_experiment()
    assert first.metadata == probe.prepare_experiment().metadata
    assert first.metadata['generation_parameters'] == probe.PARAMETERS
    assert first.metadata['source_policy']['source_origin'] == 'runtime_committed_generated_narrative'
    assert first.metadata['source_policy']['npc_aliases'] == ['Mara']
    assert first.metadata['first_request_template']['body_sha256'] is None
    assert first.metadata['first_request_template']['is_live_request'] is False
    assert 'frozen_requests' not in first.metadata
    assert [r['player_input'] for r in first.metadata['turns']] == list(probe.PLAYER_INPUTS)
    assert not harness['seen'] and not harness['produced']


@pytest.mark.asyncio
async def test_two_commits_select_actual_first_n_and_replay_reopened_store_without_production(harness):
    prepared, batch, path, rows = await run(harness)
    document = probe._read_json(path / 'summary.json')
    assert document['process_exit_code'] == 0, rows
    assert document['summary']['turns_committed'] == document['summary']['producer_completions'] == 2
    assert document['database_snapshot']['counts'] == {'attempts': 6, 'turns': 2, 'events': 2}
    assert len(harness['seen']) == len(harness['produced']) == 2
    assert all(request.config.npc_aliases == ('Mara',) for request in harness['produced'])
    first, second = (json.loads(body['messages'][1]['content']) for body in harness['seen'])
    assert first['context']['attributed_sources'] == []
    assert [s['text'] for s in second['context']['attributed_sources']] == [N1]
    assert Q not in probe._json(second)
    assert second['player_input'] == probe.PLAYER_INPUTS[1]
    assert rows[1]['capsule']['snapshot']['sources'] == [rows[0]['result']['envelope']]
    assert rows[1]['input_claim']['request']['snapshot']['sources'] == [rows[0]['result']['envelope']]
    assert all(row['request']['body_sha256'] == probe._sha(body) for row, body in zip(rows, harness['seen']))
    assert all(row['replay_verified'] and row['input_replay_verified'] for row in rows)
    before = {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}
    assert (await verify(prepared, batch, path))['process_exit_code'] == 0
    assert len(harness['seen']) == len(harness['produced']) == 2
    assert before == {p.name: probe.shared._sha256(p) for p in path.iterdir() if p.is_file()}


@pytest.mark.asyncio
async def test_pacing_precedes_P_and_same_deadline_reaches_preparation_and_H6(harness):
    prepared, batch, path, rows = await run(harness)
    assert harness['clock'][0] == 120
    forward = [d for d in harness['preparation_deadlines'] if d in harness['generation_deadlines']]
    assert forward == harness['generation_deadlines'] and len(forward) == 2
    for row, deadline in zip(rows, forward):
        beginning = datetime.fromisoformat(row['operation_started_at'])
        assert deadline - beginning == timedelta(seconds=60)
        assert row['request']['deadline'] == row['deadline'] == deadline.isoformat()
    assert (await verify(prepared, batch, path))['verified']


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['policy', 'schema', 'rate', 'route', 'length'])
async def test_first_generation_failure_skips_second_P_and_preserves_P_K_H(harness, failure):
    if failure == 'policy': reply = response(q='Quem está aqui?')
    elif failure == 'schema': reply = response(n='curta')
    elif failure == 'rate': reply = httpx.Response(429, json={'error': {'code': 'rate_limit_exceeded'}})
    elif failure == 'route': reply = response(model='unrequested-model')
    else: reply = response(finish='length')
    harness['replies'][0] = reply
    prepared, batch, path, rows = await run(harness)
    assert len(harness['produced']) == len(harness['seen']) == 1
    assert rows[1]['kind'] == 'source_dialogue_continuity_skip'
    assert rows[0]['input_claim']['status'] == 'completed' and rows[0]['result']['status'] != 'completed'
    assert probe._read_json(path / 'summary.json')['database_snapshot']['counts']['attempts'] == 3
    assert (await verify(prepared, batch, path))['process_exit_code'] != 0


@pytest.mark.asyncio
@pytest.mark.parametrize('location', ['n', 'q'])
async def test_key_echo_never_reaches_SQLite_sidecars_artifacts_or_stdout(harness, location, capsys, monkeypatch):
    harness['replies'][0] = response(n=N1 + ' ' + KEY) if location == 'n' else response(q=KEY)
    before_summary = []
    snapshot = probe._database_snapshot
    def inspect_before_summary(database):
        result = snapshot(database)
        if harness['seen'] and result['counts']['attempts'] == 3:
            assert not (database.parent / 'summary.json').exists()
            assert all(KEY.encode() not in p.read_bytes() for p in probe._database_files(database))
            before_summary.append(True)
        return result
    monkeypatch.setattr(probe, '_database_snapshot', inspect_before_summary)
    prepared, batch, path, rows = await run(harness)
    assert before_summary
    monkeypatch.setattr(probe, '_database_snapshot', snapshot)
    assert rows[0]['credential_echo_blocked'] and rows[0]['response_structure'] is None
    assert rows[0]['result']['status'] != 'completed' and len(harness['seen']) == 1
    assert probe._read_json(path / 'summary.json')['database_snapshot']['counts']['turns'] == 0
    assert all(KEY.encode() not in p.read_bytes() for p in path.iterdir() if p.is_file())
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    assert (await verify(prepared, batch, path))['verified']


@pytest.mark.asyncio
async def test_preparation_failure_has_only_P_without_second_production(harness, monkeypatch):
    from api import narrative_source_input_service as service
    from api.narrative_source_input import SourceInputFailure
    calls = []
    def refuse(request):
        calls.append(request)
        return SourceInputFailure(code='source_input_out_of_scope', stage='classification')
    monkeypatch.setattr(service, 'produce_source_player_action', refuse)
    prepared, batch, path, rows = await run(harness)
    assert len(calls) == 1 and not harness['seen']
    assert rows[0]['capsule'] is rows[0]['result'] is None and rows[0]['input_claim']['status'] == 'failed'
    assert probe._read_json(path / 'summary.json')['database_snapshot']['counts'] == {'attempts': 1, 'turns': 0, 'events': 0}
    assert (await verify(prepared, batch, path))['verified'] and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['wait', 'after_commit'])
async def test_cancellation_does_not_create_second_operation_or_retry(harness, monkeypatch, stage):
    if stage == 'wait':
        async def cancel(self): raise asyncio.CancelledError
        monkeypatch.setattr(probe.DispatchBudget, 'wait', cancel)
    else:
        original = probe.execute_retained_source_turn
        async def cancel(**kwargs):
            result = await original(**kwargs)
            if not isinstance(kwargs['gateway'], probe.NoCallGateway): raise asyncio.CancelledError
            return result
        monkeypatch.setattr(probe, 'execute_retained_source_turn', cancel)
    prepared, batch, path, rows = await run(harness)
    assert len(harness['seen']) == len(harness['produced']) == (0 if stage == 'wait' else 1)
    assert rows[1]['kind'] == 'source_dialogue_continuity_skip'
    assert (await verify(prepared, batch, path))['process_exit_code'] == 130


@pytest.mark.asyncio
async def test_final_dispatch_blocks_early_duplicate_and_third_call(harness):
    budget = harness['budget']()
    with pytest.raises(ValueError): budget.consume('operation-1')
    await budget.wait(); budget.consume('operation-1')
    await budget.wait()
    with pytest.raises(ValueError): budget.consume('operation-1')
    budget.consume('operation-2')
    await budget.wait()
    with pytest.raises(ValueError): budget.consume('operation-3')
    assert budget.calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['over_budget', 'deadline', 'unknown_usage'])
async def test_operational_limits_precede_commit_and_unknown_usage_remains_unknown(harness, monkeypatch, failure):
    if failure == 'over_budget': harness['replies'][0] = response(usage=769)
    elif failure == 'unknown_usage': harness['replies'][:] = [response(usage=None), response(N2, usage=None)]
    else:
        original = probe._prepare
        async def late(*args, **kwargs):
            result = await original(*args, **kwargs)
            if not kwargs.get('replay'): harness['clock'][0] += 61
            return result
        monkeypatch.setattr(probe, '_prepare', late)
    prepared, batch, path, rows = await run(harness)
    if failure == 'unknown_usage':
        assert len(harness['seen']) == 2 and all(row['evidence']['usage']['output_tokens'] is None for row in rows)
        assert (await verify(prepared, batch, path))['process_exit_code'] == 0
    else:
        assert len(harness['seen']) == (1 if failure == 'over_budget' else 0)
        assert probe._read_json(path / 'summary.json')['database_snapshot']['counts']['turns'] == 0
        assert (await verify(prepared, batch, path))['process_exit_code'] != 0


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value', [('http_status', 503), ('finish_reason', 'length')])
async def test_rehashed_success_with_contradictory_observer_is_rejected(harness, field, value, monkeypatch):
    prepared, batch, path, rows = await run(harness)
    rows[0]['provider_observation'][field] = value
    rewrite(path, rows)
    with pytest.raises(ValueError): await verify(prepared, batch, path)
    observe = probe.ObservationAdapter._observe_metadata
    def contradictory(self, payload):
        observe(self, payload)
        self._observation[field] = value
    monkeypatch.setattr(probe.ObservationAdapter, '_observe_metadata', contradictory)
    harness['replies'][:] = [response(), response(N2)]
    seen = len(harness['seen'])
    prepared, batch, path, rows = await run(harness)
    assert len(harness['seen']) == seen + 1 and rows[1]['kind'] == 'source_dialogue_continuity_skip'
    assert rows[0]['operational_error']['codes'] == ['observer_outcome_mismatch']
    assert probe._read_json(path / 'summary.json')['database_snapshot']['counts']['turns'] == 0
    assert (await verify(prepared, batch, path))['process_exit_code'] == 3


@pytest.mark.asyncio
async def test_rehashed_success_requires_empty_error_observation(harness):
    prepared, batch, path, original = await run(harness)
    accepted = []
    for section, field, value in [('error_body', 'bytes', 7), ('failed_generation', 'characters', 7)]:
        rows = copy.deepcopy(original)
        rows[0]['provider_observation'][section][field] = value
        rewrite(path, rows)
        try:
            await verify(prepared, batch, path)
        except ValueError:
            pass
        else:
            accepted.append(section)
    assert accepted == [], 'Contradictory unavailable snapshots accepted: ' + ','.join(accepted)


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['source', 'question', 'aliases', 'request', 'deadline', 'overlap', 'capsule', 'snapshot', 'extra_record', 'database'])
async def test_rehashed_forgery_cannot_replace_dynamic_source_or_persistence(harness, change):
    prepared, batch, path, rows = await run(harness)
    if change == 'source': rows[1]['capsule']['snapshot']['sources'][0]['projection']['source']['text'] = N2
    elif change == 'question': rows[1]['capsule']['snapshot']['sources'][0]['projection']['source']['text'] += Q
    elif change == 'aliases': rows[1]['input_claim']['request']['config']['npc_aliases'] = []
    elif change == 'request': rows[1]['request']['user_packet'] = '{}'
    elif change == 'deadline': rows[1]['request']['deadline'] = rows[0]['deadline']
    elif change == 'overlap': rows[1]['operation_started_at'] = rows[0]['operation_started_at']
    elif change == 'capsule': rows[1]['capsule']['system_prompt'] += ' altered'
    elif change == 'extra_record': rows.append(copy.deepcopy(rows[1]))
    elif change == 'database':
        with sqlite3.connect(path / probe.DATABASE_NAME) as conn:
            conn.execute('UPDATE campaigns SET state_revision=99')
    rewrite(path, rows, edit=(lambda doc: doc['database_snapshot']['counts'].update(turns=99)) if change == 'snapshot' else None)
    with pytest.raises((ValueError, TypeError)): await verify(prepared, batch, path)


@pytest.mark.parametrize('mode', ['preflight', 'invalid'])
def test_non_live_CLI_never_accesses_credential(harness, monkeypatch, capsys, mode):
    def forbidden(*args, **kwargs): pytest.fail('Non-live CLI accessed key')
    monkeypatch.setattr(probe, 'os', SimpleNamespace(environ=SimpleNamespace(pop=forbidden, get=forbidden)))
    code = probe.main(['--preflight'] if mode == 'preflight' else ['--live'])
    assert code == (0 if mode == 'preflight' else 3)
    assert not harness['seen'] and not harness['produced']
    assert KEY not in capsys.readouterr().err


def test_live_credential_is_removed_before_Git_provenance(harness, monkeypatch, capsys):
    observed = []
    def git(arguments, **kwargs):
        observed.append(probe.KEY_ENV in kwargs.get('env', os.environ))
        return SimpleNamespace(stdout='5e563824fcba4c53cc37b5084a8ce65f3fa30356\n' if arguments[1] == 'rev-parse' else ' M synthetic\n')
    monkeypatch.setattr(probe.shared.subprocess, 'run', git)
    prepared, batch = probe.prepare_experiment(), str(uuid4())
    path = probe.run_path(batch); path.parent.mkdir(parents=True)
    target, digest = expected(prepared, path)
    original = probe.evaluate_probe
    async def local(*args, **kwargs):
        assert kwargs['api_key'].get_secret_value() == KEY
        return await original(*args, **kwargs, transport=harness['transport'], budget=harness['budget']())
    monkeypatch.setattr(probe, 'evaluate_probe', local)
    observed.clear(); monkeypatch.setenv(probe.KEY_ENV, KEY)
    assert probe.main(['--live', '--allow-synthetic-only', '--batch-id', batch, '--expected-preflight', str(target),
        '--expected-preflight-sha256', digest, '--api-key-env', probe.KEY_ENV]) == 0
    assert observed and not any(observed) and probe.KEY_ENV not in os.environ
    captured = capsys.readouterr(); assert KEY not in captured.out + captured.err
