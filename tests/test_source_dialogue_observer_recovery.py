"""Recorded 87e dialogue in real P/K/H, with new SQLite and a network-free fake.

Literal n/q came from records.jsonl of 87e187bb-61e7-4949-9574-4aea19f23c9f,
SHA-256 c64b4f9b5db3dcb15d0ef99aa218bc24eddfe29b9d86c64ea334246037e875f0.
This local regression does not rerun the provider or reclassify that observation.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from api import narrative_source_input_service, rules_service
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor, CapabilitySet, CapabilitySupport,
    GenerationParameters, LLMTarget, utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.narrative_source_coordinator import execute_retained_source_turn
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_input import create_source_producer_config
from api.narrative_source_input_service import prepare_source_player_action
from api.narrative_source_setup_service import create_source_trial_setup
from api.persistence import SQLitePersistence
from api.rules_service import PlayerSheetModel, StatusModel, TrackerModel

CAPTURED = ({'n': 'Mara se vira lentamente, os olhos percorrendo as paredes escuras da galeria por um instante antes de fixarem-se em você. Um leve sorriso, quase melancólico, surge em seus lábios enquanto ela ergue a mão, apontando vagamente para o vazio ao redor. — “É um espaço entre o que foi criado e o que se perdeu”, ela responde, a voz suave cortando o silêncio pesado do local. “Galerias guardam mais do que quadros, sabia? Guardam intenções.” Ela dá um passo à frente, a luz fraca dançando sobre seu rosto, e observa sua reação com uma curiosidade contida.', 'q': 'O que você faz em seguida?'}, {'n': 'Mara inclina a cabeça, o sorriso sumindo aos poucos, substituído por uma expressão mais séria. Ela levanta a mão, os dedos traçando um gesto invisível no ar, como se tentasse dar forma a um conceito abstrato. — “Intenção é o que resta quando a matéria falha”, diz ela, a voz baixa, quase um sussurro. “Cada obra traz a marca de quem a criou, mas também a ausência do que não pôde ser dito. É sobre o que ficou de fora, não só sobre o que está ali.” Ela para, observando você com atenção, esperando para ver se a explicação ressoa ou se permanece vaga.', 'q': 'Como você responde a Mara?'})
CAPTURED_SHA256 = ('f0650b4263cec422035bd1804e3439381d6223f79e43e04999cabe0ba3b0b1b9', 'd6d62b9687d57f566e2bd27b3e03fc881858d10c502f824b02ff818fcd153058')
ACTIONS = (
    'Digo a Mara: "Mara, o que é este lugar?"',
    'Digo a Mara: "Mara, explique melhor sua resposta."',
)
PROMPT_SHA256 = '473208c260c2284fdc2c65cfdcb767c8a701c64d652a9c691712be99878a779d'


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _snapshot(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        data = {table: sorted([list(row) for row in connection.execute(
            'SELECT * FROM "' + table + '"'
        )], key=_json) for table in tables}
        return ({table: len(rows) for table, rows in data.items()},
                hashlib.sha256(_json(data).encode()).hexdigest())
    finally:
        connection.rollback()
        connection.close()


def _initial_state():
    sheet = PlayerSheetModel(
        attributes={'Wits': 3}, skills={'Investigation': 2}, disciplines={},
        status=StatusModel(
            blood_potency=1, current_hunger=0, humanity=7,
            health_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
        ),
    )
    return {'player_sheet': sheet.model_dump(mode='json')}


def _config():
    prompt = Path(__file__).resolve().parents[1] / 'evals/narrator/prompts/narrative-source-dialogue-v1.md'
    assert hashlib.sha256(prompt.read_bytes()).hexdigest() == PROMPT_SHA256
    text = prompt.read_text(encoding='utf-8')
    assert text.startswith('---\n')
    system = text.split('---\n', 2)[2].strip()
    assert hashlib.sha256(system.encode()).hexdigest() == '393f522ec10fad6ab096df3e13de06f6b83314ce2c44352c3f120b6241247608'
    return create_source_producer_config(
        target=LLMTarget(profile='observer-recovery-synthetic', provider='fake', model='synthetic'),
        system_prompt=system,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        npc_aliases=('Mara',),
    )


def _gateway(config, payload):
    capabilities = CapabilitySet(target=config.target, descriptors=tuple(
        CapabilityDescriptor(name=name, support=CapabilitySupport.NATIVE)
        for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)
    ))
    return FakeLLMAdapter(capability_set=capabilities, structured_payload=payload)


class ForbiddenGateway:
    def capabilities(self, target):
        pytest.fail('Terminal replay queried a production gateway')

    async def generate_structured(self, request):
        pytest.fail('Terminal replay generated again')


@pytest.mark.anyio
@pytest.mark.parametrize('force_player_action', [False, True], ids=['captured-observer-recovery', 'genuine-player-action-remains-refused'])
async def test_recorded_dialogue_commits_dynamic_source_and_replays_without_production(
    tmp_path, monkeypatch, force_player_action,
):
    # Fixtures stay self-contained; regression never opens a historical database.
    assert tuple(hashlib.sha256(_json(p).encode()).hexdigest() for p in CAPTURED) == CAPTURED_SHA256
    state, config = _initial_state(), _config()
    store = SQLitePersistence(tmp_path / 'observer-recovery.sqlite3')
    await store.initialize()
    session = 'observer-recovery-local'
    await create_source_trial_setup(
        session_id=session, request={'location': 'Galeria', 'npcs_present': ['Mara'],
            'declared_objective': 'Conhecer melhor este lugar por meio da conversa.'},
        store=store, initial_state=state, relationships={},
    )
    assert _snapshot(store.db_path)[0]['attempts'] == 0
    rng_calls, produced = [], []

    def forbid_roll(*args, **kwargs):
        rng_calls.append((args, kwargs))
        pytest.fail('Declared dialogue or replay rolled dice')

    original = narrative_source_input_service.produce_source_player_action

    def produce(request):
        produced.append(request)
        return original(request)

    monkeypatch.setattr(rules_service.random, 'randint', forbid_roll)
    monkeypatch.setattr(narrative_source_input_service, 'produce_source_player_action', produce)
    results, claims, gateways = [], [], []
    for index, action in enumerate(ACTIONS):
        operation = 'dialogue-' + str(index + 1)
        deadline = utc_now() + timedelta(seconds=60)
        claim = await prepare_source_player_action(
            session_id=session, request=SourcePlayerActionRequest(operation_id=operation, player_input=action),
            store=SQLitePersistence(store.db_path), producer_config=config,
            deadline=deadline, cancellation=CancellationToken(),
        )
        assert claim.status == 'completed' and not claim.newly_claimed
        assert len(produced) == index + 1
        capsule = await SQLitePersistence(store.db_path).load_source_preparation(session, operation)
        assert capsule.npc_aliases == ('Mara',) and capsule.preparation.kind == 'declared_action'
        assert capsule.draft.state_changes == ()
        expected_sources = () if index == 0 else (results[0].envelope,)
        assert capsule.snapshot.sources == claim.request.snapshot.sources == expected_sources
        payload = dict(CAPTURED[index])
        if force_player_action and index == 1:
            payload['n'] += ' Você permanece imóvel.'
        gateway = _gateway(config, payload)
        chunks = []

        async def collect(text):
            chunks.append(text)

        result = await execute_retained_source_turn(
            session_id=session, operation_id=operation, store=SQLitePersistence(store.db_path),
            gateway=gateway, deadline=deadline, cancellation=CancellationToken(), on_chunk=collect,
        )
        assert len(gateway.requests) == 1
        request = gateway.requests[0]
        assert request.deadline == deadline
        user = json.loads(request.messages[1].content)
        assert user['player_input'] == action
        assert [source['text'] for source in user['context']['attributed_sources']] == ([] if index == 0 else [CAPTURED[0]['n']])
        assert all(p['q'] not in request.messages[1].content for p in CAPTURED)
        assert user['context']['canonical_scene'] == {'location': 'Galeria', 'npcs_present': ['Mara']}
        if force_player_action and index == 1:
            assert result.status == 'failed' and result.error == {'code': 'scene_player_agency_violation', 'stage': 'policy'}
            assert result.envelope is None and result.narrative is None and chunks == []
        else:
            assert result.status == 'completed', result.error
            assert result.envelope.projection.text == payload['n']
            assert result.envelope.question == payload['q']
            assert chunks == [payload['n'] + '\n\n' + payload['q']]
        results.append(result)
        claims.append(claim)
        gateways.append(gateway)
    counts, before = _snapshot(store.db_path)
    committed = 1 if force_player_action else 2
    assert {name: counts[name] for name in ('attempts', 'turns', 'events')} == {'attempts': 6, 'turns': committed, 'events': committed}
    assert all(counts[name] == 0 for name in ('memory_candidates', 'episodic_memories', 'consolidations'))
    campaign = await SQLitePersistence(store.db_path).load_campaign(session)
    assert campaign['state'] == state and campaign['relationships'] == {}
    assert campaign['current_turn'] == campaign['state_revision'] == committed
    assert len(produced) == 2 and not rng_calls

    def forbid_producer(*args, **kwargs):
        pytest.fail('Terminal replay prepared a new action')

    monkeypatch.setattr(narrative_source_input_service, 'produce_source_player_action', forbid_producer)
    for index, (claim, original_result) in enumerate(zip(claims, results)):
        operation = 'dialogue-' + str(index + 1)
        expired = utc_now() - timedelta(seconds=1)
        replay_claim = await prepare_source_player_action(
            session_id=session, request=SourcePlayerActionRequest(operation_id=operation, player_input=ACTIONS[index]),
            store=SQLitePersistence(store.db_path), producer_config=config,
            deadline=expired, cancellation=CancellationToken(),
        )
        assert not replay_claim.newly_claimed
        assert replay_claim.request == claim.request and replay_claim.completion == claim.completion
        replay = await execute_retained_source_turn(
            session_id=session, operation_id=operation, store=SQLitePersistence(store.db_path),
            gateway=ForbiddenGateway(), deadline=expired, cancellation=CancellationToken(),
            on_chunk=lambda value: pytest.fail('Terminal replay emitted another chunk'),
        )
        if original_result.status == 'completed':
            assert replay.status == 'completed' and replay.envelope == original_result.envelope
            assert replay.narrative == original_result.narrative
        else:
            assert replay.status == 'failed' and replay.error['code'] == 'source_turn_operation_terminal'
            assert await store.load_turn_by_operation(session, operation) is None
        assert _snapshot(store.db_path) == (counts, before)
    assert len(produced) == 2 and sum(len(gateway.requests) for gateway in gateways) == 2
    assert not rng_calls