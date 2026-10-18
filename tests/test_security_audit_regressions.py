"""Local-only security boundaries; synthetic data and no external network."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api import main
from api.state_service import get_persistence
from api.memory_service import create_consolidation
from api.turn_models import ConsolidationScope
from test_operational_contract_api import _records, _accepted_candidate
from scripts.run_campaign_source_offline_trial import create_app


def test_foreign_origin_cannot_trigger_initializer(monkeypatch):
    spawn = Mock()
    monkeypatch.setattr('subprocess.Popen', spawn)
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        response = client.post('/api/initialization/retry', headers={'Origin': 'https://attacker.invalid'})
    assert response.status_code == 403
    spawn.assert_not_called()


def test_foreign_origin_websocket_rejected_before_accept():
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        with pytest.raises(WebSocketDisconnect) as stopped:
            with client.websocket_connect('/ws/initialization', headers={'Origin': 'https://attacker.invalid'}) as socket:
                socket.send_text('ping')
                socket.receive_text()
        assert stopped.value.code == 1008


def test_rebinding_host_cannot_reach_main_app():
    with TestClient(main.app, base_url='http://attacker.invalid:8000') as client:
        assert client.get('/health').status_code == 403


def test_rebinding_host_cannot_read_offline_trial_bootstrap(tmp_path):
    with TestClient(create_app(tmp_path / 'offline.sqlite3'), base_url='http://attacker.invalid:8021') as client:
        assert client.get('/').status_code == 403


@pytest.mark.parametrize('path', [
    '/api/initialization/logs', '/api/initialization/retry',
    '/api/llm/test-connection', '/session/local_player/memory/consolidate/scene',
    '/session/local_player/xp/award?amount=100', '/session/local_player/xp/upgrade',
])
def test_every_main_write_route_rejects_foreign_origin_before_dispatch(path):
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        assert client.post(path, headers={'Origin': 'https://attacker.invalid'}).status_code == 403


@pytest.mark.parametrize('headers', [
    [('Host', '127.0.0.1:8000'), ('Host', 'attacker.invalid')],
    [('Origin', 'http://127.0.0.1:8000'), ('Origin', 'https://attacker.invalid')],
    {'Origin': 'null'}, {'Origin': 'http://localhost.attacker.invalid:8000'},
    {'Origin': 'http://127.0.0.1:9001'}, {'Sec-Fetch-Site': 'cross-site'},
])
def test_ambiguous_or_foreign_request_metadata_is_denied(headers):
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        assert client.get('/health', headers=headers).status_code == 403


@pytest.mark.parametrize('origin', [None, 'http://127.0.0.1:8000',
    'http://localhost:5173', 'http://127.0.0.1:5173'])
def test_native_same_origin_and_explicit_dev_frontend_remain_available(origin):
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        assert client.get('/health', headers={'Origin': origin} if origin else {}).status_code == 200


def test_same_origin_websocket_still_operates():
    with TestClient(main.app, base_url='http://127.0.0.1:8000') as client:
        with client.websocket_connect('/ws/initialization', headers={'Origin': 'http://127.0.0.1:8000'}) as socket:
            socket.send_text('ping')
            # The initialization manager may first replay its latest log.
            while socket.receive_text() != 'pong':
                pass


async def seed_memories():
    fact, event, narrative, public, private = _records()
    store = get_persistence()
    await store.commit_turn(session_id='session-api', operation_id='security-seed',
        turn_id=event.turn_id, state={'revision': 1}, narrative=narrative,
        facts=(fact,), events=(event,),
        memory_candidates=tuple(_accepted_candidate(m, event.turn_id) for m in (public, private)),
        episodic_memories=(public, private))
    return store, public, private


@pytest.mark.asyncio
async def test_player_consolidation_excludes_private_sources():
    _, public, private = await seed_memories()
    result = await main.consolidate_memory('session-api', 'scene', main.ConsolidationRequest(summary='review'))
    assert result['success'] is True
    assert result['consolidation']['source_memory_ids'] == [public.memory_id]
    assert private.summary not in result['consolidation']['summary']
    assert result['consolidation']['visibility'] in {'public', 'player'}


@pytest.mark.asyncio
async def test_explicit_private_source_is_not_available_to_player():
    store, _, private = await seed_memories()
    result = await main.consolidate_memory('session-api', 'scene', main.ConsolidationRequest(
        summary='review', source_memory_ids=[private.memory_id]))
    assert result['success'] is False
    assert not await store.list_consolidations('session-api')


@pytest.mark.asyncio
async def test_private_consolidation_chain_cannot_be_superseded_by_player():
    store, public, private = await seed_memories()
    hidden = create_consolidation([private], consolidation_id='hidden-consolidation', scope=ConsolidationScope.SCENE)
    await store.save_consolidation(hidden)
    result = await main.consolidate_memory('session-api', 'scene', main.ConsolidationRequest(
        summary='review', source_memory_ids=[public.memory_id]))
    assert result['success'] is False
    assert 'hidden-consolidation' not in str(result)
    assert len(await store.list_consolidations('session-api')) == 1
