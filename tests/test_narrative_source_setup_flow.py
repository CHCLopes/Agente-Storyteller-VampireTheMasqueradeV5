"""Authored setup through actual player-intent producer to retained B execution.

These are synthetic scripted actions and authored model replies. They prove the
composition, never live narrative quality or an action chosen by the real user.
"""
from datetime import timedelta
import json
import sqlite3

import pytest

from api import narrative_source_input_service, rules_service
from api.llm.contract import CancellationToken, GenerationParameters, utc_now
from api.narrative_source_coordinator import execute_retained_source_turn
from api.narrative_source_entry import SourcePlayerActionRequest
from api.narrative_source_setup import SourceSetupRequest
from api.narrative_source_setup_service import create_source_trial_setup
from api.persistence import SQLitePersistence
from test_narrative_source_bridge import FIRST, QUESTION, SYSTEM, _gateway
from test_narrative_source_input_service import state
from api.narrative_source_input import create_source_producer_config
from test_narrative_source_preparation_bridge import INVESTIGATION_SUCCESS, INVESTIGATION_FAILURE

SESSION = "setup-flow-synthetic"
OBJECTIVE = "conhecer melhor este lugar por meio da conversa"
DIALOGUE = 'Pergunto a Mara: "Quero conhecer melhor este lugar por meio da conversa. O que você pode me contar?"'
REPLY = (
    'Mara volta o rosto para a pergunta e indica com a mão as prateleiras próximas. '
    '"Este lugar reúne objetos que as pessoas deixaram por aqui", diz, sem sair de '
    'junto da janela. Ela aproxima um recipiente vazio da borda para mostrar os '
    'pequenos desenhos gravados na cerâmica. A luz atravessa o vidro e torna os '
    'traços mais visíveis. "Posso falar do que está nesta prateleira", acrescenta. '
    'O recipiente fica apoiado sobre a madeira enquanto Mara afasta a mão e espera. '
    'Atrás dela, a cortina se move com uma corrente de ar, e a chuva permanece '
    'audível do lado de fora. Há espaço livre diante da prateleira; os demais '
    'objetos seguem em seus lugares, sob a iluminação irregular da galeria.'
)
WAIT_REPLY = (
    'Mara permanece junto à prateleira e gira devagar o recipiente que mostrou. '
    'Outro desenho aparece na cerâmica: uma linha curva cercada por pequenos pontos. '
    '"Este traço está do outro lado também", comenta, mantendo o objeto apoiado '
    'sobre a madeira. O ruído da chuva preenche a pausa entre as palavras. '
    'A cortina continua em movimento diante da janela, sem esconder a prateleira.'
)


def config():
    # Scene roster does not implicitly supply policy aliases. The trusted caller
    # binds its known NPC explicitly, preserving the existing agency validator.
    target, _ = _gateway()
    return create_source_producer_config(target=target, system_prompt=SYSTEM,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        npc_aliases=("Mara",))


def test_known_npc_pronoun_requires_explicit_server_policy_alias():
    from api.narrative_source_profile import validate_source_proposal
    from api.scene_director_service import SceneProposalError
    from api.scene_service import SceneState
    arguments = dict(current_scene=SceneState(location="Galeria", npcs_present=("Mara",)),
                     facts=(), player_input=DIALOGUE)
    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_source_proposal({"n": REPLY, "q": QUESTION}, **arguments)
    accepted = validate_source_proposal({"n": REPLY, "q": QUESTION}, npc_aliases=("Mara",), **arguments)
    assert accepted.narrative == REPLY


async def setup(tmp_path):
    store = SQLitePersistence(tmp_path / "setup-flow.sqlite3")
    await store.initialize()
    manifest = await create_source_trial_setup(session_id=SESSION,
        request=SourceSetupRequest(location="Galeria", npcs_present=("Mara",),
                                   declared_objective=OBJECTIVE),
        store=store, initial_state=state(), relationships={})
    return store, manifest


async def prepare(store, operation, action):
    return await narrative_source_input_service.prepare_source_player_action(
        session_id=SESSION, request=SourcePlayerActionRequest(operation_id=operation, player_input=action),
        store=store, producer_config=config(), deadline=utc_now()+timedelta(seconds=30),
        cancellation=CancellationToken())


async def execute(store, operation, text):
    _, gateway = _gateway(text)
    chunks = []
    async def collect(chunk): chunks.append(chunk)
    result = await execute_retained_source_turn(session_id=SESSION, operation_id=operation,
        store=store, gateway=gateway, deadline=utc_now()+timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect)
    assert result.status == "completed", result.error
    assert len(gateway.requests) == 1 and chunks == [text + "\n\n" + QUESTION]
    return result, json.loads(gateway.requests[0].messages[1].content)


def table_counts(store):
    connection = sqlite3.connect(store.db_path)
    try:
        return {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("attempts", "turns", "events")}
    finally:
        connection.close()


@pytest.mark.anyio
@pytest.mark.parametrize("action,includes_objective", [("Aguardo.", False), (DIALOGUE, True)])
async def test_first_packet_only_carries_objective_when_scripted_player_action_contains_it(
        tmp_path, monkeypatch, action, includes_objective):
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Setup or dialogue rolled"))
    store, manifest = await setup(tmp_path)
    assert table_counts(store) == {"attempts": 0, "turns": 0, "events": 0}
    snapshot = await store.read_source_context_snapshot(SESSION)
    assert snapshot.current_turn == snapshot.state_revision == 0 and snapshot.sources == ()
    assert (await prepare(store, "first", action)).status == "completed"
    result, packet = await execute(store, "first", REPLY if includes_objective else FIRST)
    assert packet["context"]["canonical_scene"] == {"location": "Galeria", "npcs_present": ["Mara"]}
    assert packet["context"]["attributed_sources"] == []
    assert packet["player_input"] == action
    assert (OBJECTIVE in json.dumps(packet, ensure_ascii=False)) is includes_objective
    assert manifest.briefing not in json.dumps(packet, ensure_ascii=False)
    assert result.envelope.projection.text != manifest.briefing
    restored = await SQLitePersistence(store.db_path).read_source_setup_manifest(SESSION)
    assert restored == manifest
    assert (await store.load_campaign(SESSION))["current_turn"] == 1


@pytest.mark.anyio
async def test_dialogue_then_wait_preserves_authored_setup_and_attributed_source_on_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Conversation or wait rolled"))
    store, manifest = await setup(tmp_path)
    first_claim = await prepare(store, "dialogue", DIALOGUE)
    first, _ = await execute(store, "dialogue", REPLY)
    first_capsule = await store.load_source_preparation(SESSION, "dialogue")
    store = SQLitePersistence(store.db_path)
    assert await store.read_source_setup_manifest(SESSION) == manifest
    assert (await prepare(store, "wait", "Espero a reação de Mara.")).status == "completed"
    _, packet = await execute(store, "wait", WAIT_REPLY)
    assert [item["text"] for item in packet["context"]["attributed_sources"]] == [REPLY]
    assert QUESTION not in json.dumps(packet, ensure_ascii=False)
    before = table_counts(store)
    def forbidden(*args): pytest.fail("Replay produced or generated")
    monkeypatch.setattr(narrative_source_input_service, "produce_source_player_action", forbidden)
    assert await prepare(SQLitePersistence(store.db_path), "dialogue", DIALOGUE) == first_claim
    _, no_call_gateway = _gateway("must never be used")
    async def no_chunk(_): pytest.fail("Replay redelivered chunk")
    replay = await execute_retained_source_turn(session_id=SESSION, operation_id="dialogue",
        store=SQLitePersistence(store.db_path), gateway=no_call_gateway,
        deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=no_chunk)
    assert replay.envelope == first.envelope and replay.status == "completed"
    assert no_call_gateway.requests == [] and table_counts(store) == before
    assert await store.load_source_preparation(SESSION, "dialogue") == first_capsule
    assert await store.read_source_setup_manifest(SESSION) == manifest


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_investigation_after_dialogue_has_one_real_resolution_and_preserves_source(tmp_path, monkeypatch, success):
    store, manifest = await setup(tmp_path)
    assert (await prepare(store, "dialogue", DIALOGUE)).status == "completed"
    await execute(store, "dialogue", REPLY)
    faces = [6, 7, 8, 2, 3] if success else [1, 2, 3, 4, 5]
    rolled = []
    def dice(low, high):
        assert (low, high) == (1, 10)
        result = faces[len(rolled)]
        rolled.append(result)
        return result
    monkeypatch.setattr(rules_service.random, "randint", dice)
    claim = await prepare(store, "investigation", "Investigo a galeria.")
    assert claim.status == "completed"
    capsule = await store.load_source_preparation(SESSION, "investigation")
    assert capsule.preparation.resolution.is_success is success
    assert capsule.preparation.resolution.normal_rolls == faces and rolled == faces
    _, packet = await execute(store, "investigation", INVESTIGATION_SUCCESS if success else INVESTIGATION_FAILURE)
    assert [item["text"] for item in packet["context"]["attributed_sources"]] == [REPLY]
    assert packet["server_facts"] == [fact.model_dump(mode="json") for fact in capsule.draft.facts]
    assert await prepare(SQLitePersistence(store.db_path), "investigation", "Investigo a galeria.") == claim
    assert rolled == faces
    assert await store.read_source_setup_manifest(SESSION) == manifest


@pytest.mark.anyio
@pytest.mark.parametrize("action", ["Ataco Mara.", "Investigo."])
async def test_unsupported_or_ambiguous_action_keeps_setup_without_source_or_receipt(tmp_path, monkeypatch, action):
    monkeypatch.setattr(rules_service.random, "randint", lambda *args: pytest.fail("Refusal rolled"))
    store, manifest = await setup(tmp_path)
    claim = await prepare(store, "refused", action)
    assert claim.status == "failed"
    assert claim.completion.failure.code in {"source_input_out_of_scope", "source_input_clarification_required"}
    assert await store.load_source_preparation(SESSION, "refused") is None
    assert await store.load_attempt_by_operation(SESSION, "refused") is None
    assert await store.read_source_setup_manifest(SESSION) == manifest
    assert (await store.read_source_context_snapshot(SESSION)).current_turn == 0
