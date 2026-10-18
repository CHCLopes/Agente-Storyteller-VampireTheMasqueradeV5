"""Campaign policy derives NPC attribution from the canonical roster."""
from datetime import timedelta

import pytest

from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_profile import CampaignSourceProfileError, validate_campaign_source_proposal
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from api.llm.testing import FakeLLMAdapter
from scripts.run_campaign_source_offline_trial import CONFIG, CAPABILITIES, _initial_state


# Retained HYP-007-L3 text, unchanged; no personal campaign or credential data.
OBSERVED_L3 = (
    'Mara mantém os olhos na bancada baixa, onde o registro ameaçado continua apoiado no Arquivo. '
    '“Você pode ajudar mantendo tudo estável por enquanto. O risco atual é piorar o estado do '
    'registro se ele for manipulado sem cuidado. Se precisarmos movê-lo, a superfície seca fica '
    'na Galeria; é para lá que devemos levá-lo, não para qualquer lugar.” Ela aponta '
    'discretamente para a passagem, mas não toca no objeto. A situação permanece sob controle, '
    'embora o registro ainda esteja em risco.'
)


async def prepared_packet(tmp_path):
    store = SQLitePersistence(tmp_path / 'npc.sqlite3')
    await create_campaign_source_session(store, 'npc-authority', initial_state=_initial_state())
    claim = await prepare_campaign_source_player_action(
        store=store, session_id='npc-authority', operation_id='npc-action',
        player_input='Como posso ajudar?', config=CONFIG,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken())
    assert claim.capsule is not None
    capsule = claim.capsule
    return capsule, build_campaign_narrator_packet(capsule.campaign_request, capsule.campaign_effect)


@pytest.mark.asyncio
async def test_retained_mara_pronoun_uses_canonical_roster_with_no_config_aliases(tmp_path):
    capsule, packet = await prepared_packet(tmp_path)
    assert capsule.config.npc_aliases == ()
    assert capsule.snapshot.canonical_scene.npcs_present == ('Mara',)
    value = {'n': OBSERVED_L3, 'q': 'O que você faz agora?',
             'realized_effects': packet.required_effects}
    admitted = validate_campaign_source_proposal(
        value, packet=packet, facts=capsule.draft.facts, snapshot=capsule.snapshot)
    assert admitted.narrative == OBSERVED_L3
    assert capsule.snapshot.progression.record_location == 'bench'


@pytest.mark.asyncio
@pytest.mark.parametrize('ending', [
    'Você aponta para a passagem e pega o registro da bancada.',
    'Seu personagem abre a porta lateral.',
    'Ela aponta para a passagem e pega o documento.',
    'Ivo mantém os olhos na bancada. Ele aponta para a passagem e pega o registro.',
])
async def test_roster_does_not_authorize_player_or_unanchored_pronoun(tmp_path, ending):
    capsule, packet = await prepared_packet(tmp_path)
    value = {
        'n': 'O registro ameaçado permanece na bancada do Arquivo. A superfície seca fica '
             'na Galeria, acessível pela passagem. A água continua caindo sobre o piso, '
             'e a escolha seguinte ainda pertence ao jogador. ' + ending +
             ' Mara aguarda a próxima decisão junto à bancada.',
        'q': 'O que você faz agora?', 'realized_effects': packet.required_effects,
    }
    with pytest.raises(CampaignSourceProfileError):
        validate_campaign_source_proposal(value, packet=packet,
            facts=capsule.draft.facts, snapshot=capsule.snapshot)


@pytest.mark.asyncio
async def test_player_npc_alias_collision_remains_conservative(tmp_path):
    capsule, packet = await prepared_packet(tmp_path)
    with pytest.raises(CampaignSourceProfileError):
        validate_campaign_source_proposal(
            {'n': OBSERVED_L3, 'q': 'O que você faz agora?',
             'realized_effects': packet.required_effects},
            packet=packet, facts=capsule.draft.facts, snapshot=capsule.snapshot,
            player_aliases=('Mara',))


@pytest.mark.asyncio
async def test_local_observed_text_commit_and_replay_use_same_roster(tmp_path):
    capsule, packet = await prepared_packet(tmp_path)
    store = SQLitePersistence(tmp_path / 'npc.sqlite3')
    gateway = FakeLLMAdapter(capability_set=CAPABILITIES, structured_payload={
        'n': OBSERVED_L3, 'q': 'O que você faz agora?',
        'realized_effects': packet.required_effects,
    })
    delivered = []
    async def collect(text):
        delivered.append(text)
    async def execute():
        return await execute_campaign_source_turn(
            store=store, capsule=capsule, operation_id=capsule.operation_id, gateway=gateway,
            deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
            on_chunk=collect)
    result = await execute()
    assert result.status == 'completed', result.error_code
    snapshot = await read_campaign_source_snapshot(SQLitePersistence(tmp_path / 'npc.sqlite3'),
                                                   'npc-authority')
    assert snapshot.current_turn == 1
    assert snapshot.progression.record_location == 'bench'
    assert snapshot.progression.known_information == ('safe_surface',)
    assert snapshot.sources[0].text == OBSERVED_L3
    replay = await execute()
    assert replay.envelope == result.envelope
    assert len(gateway.requests) == len(delivered) == 1
