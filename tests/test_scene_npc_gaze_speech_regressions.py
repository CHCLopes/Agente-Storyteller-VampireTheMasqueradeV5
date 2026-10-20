"""HYP-007-L5: a known NPC addresses a player object, not a speaking player."""
import pytest
from datetime import timedelta

from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import CampaignSourceProposal, validate_campaign_source_proposal
from api.scene_director_service import SceneProposalError
from api.narrative_source_profile import validate_source_proposal
from api.scene_service import SceneState
from test_campaign_source_capsule import capsule
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence


OBSERVED = {
    'n': 'Você aguarda na quietude do Arquivo. O ar junto às paredes fica mais úmido, e a infiltração avança o bastante para tornar o risco imediato. Mara se inclina sobre a bancada baixa, sem tocar no registro; o registro permanece seco, ainda no mesmo lugar. Ela ergue os olhos para você e fala em voz baixa: “Não podemos esperar muito mais. Se essa umidade continuar, o Arquivo pode deixar de ser seguro.” A tensão substitui a calma, enquanto Mara observa as marcas de água e mantém a atenção voltada para a bancada.',
    'q': 'O que você faz diante do risco imediato?',
    'realized_effects': ['campaign.warning.visible'],
}
FILLER = (' A chuva pesa contra a janela enquanto o rádio chia no balcão. '
          'Uma corrente bate na porta, rompendo o silêncio da sala e ecoando pelo corredor.')


def check(text, *, players=(), npcs=('Mara',)):
    return validate_source_proposal(
        {'n': text + FILLER, 'q': 'Qual será sua próxima atitude?'},
        current_scene=SceneState(location='Arquivo', npcs_present=npcs),
        facts=(), player_input='Aguardo', player_aliases=players, npc_aliases=npcs,
    )


def test_exact_l5_response_passes_offline_without_rewriting_it():
    retained = capsule()
    packet = build_campaign_narrator_packet(retained.campaign_request, retained.campaign_effect)
    proposal = CampaignSourceProposal.model_validate(OBSERVED)
    assert validate_campaign_source_proposal(
        proposal, packet=packet, facts=retained.draft.facts, snapshot=retained.snapshot,
    ) == proposal


@pytest.mark.parametrize('text', [
    'Mara ergue os olhos para você e fala em voz baixa: “A água avança.”',
    'Mara levanta os olhos para você e fala em voz firme: “A água avança.”',
    'Mara se inclina sobre a bancada baixa, sem tocar no registro; o registro permanece seco, ainda no mesmo lugar. Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
])
def test_bounded_gaze_report_keeps_npc_subject(text):
    assert check(text).narrative.startswith(text)


@pytest.mark.parametrize('text', [
    'Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
    'Você sorri. Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
    'A voz menciona Mara. Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
    '“Mara se inclina sobre a bancada baixa, sem tocar no registro; o registro permanece seco, ainda no mesmo lugar.” Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
    'Mara se inclina sobre a bancada baixa, sem tocar no registro; o registro permanece seco, ainda no mesmo lugar. A visitante sorri. Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
    'Mara ergue os olhos para você que fala em voz baixa: “A água avança.”',
    'Mara ergue os olhos para você e você fala em voz baixa: “A água avança.”',
    'Mara ergue os olhos para você e o jogador fala em voz baixa: “A água avança.”',
    'Mara ergue os olhos para você e fala em voz baixa, mas você abre a porta.',
    'Mara ergue os olhos para você e fala em voz baixa: “Você abre a porta.”',
    'Mara ergue os olhos para você e fala em voz baixa: “Você promete ajudar.”',
    'Mara ergue os olhos para você e fala em voz baixa: “A água avança.” Você abre a porta.',
    'Mara ergue os olhos para você e fala em voz baixa e abre a porta.',
    'Mara ergue os olhos para você e obriga você a falar em voz baixa.',
    'Mara ergue os olhos para você e fala em voz baixa: “A água avança.',
])
def test_no_authority_is_granted_to_player_or_ambiguous_subject(text):
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('players,npcs', [(('Mara',), ('Mara',)), ((), ())])
def test_missing_or_colliding_npc_does_not_establish_subject(players, npcs):
    with pytest.raises(SceneProposalError):
        check('Mara ergue os olhos para você e fala em voz baixa: “A água avança.”',
              players=players, npcs=npcs)


@pytest.mark.parametrize('actor', ['Seu personagem', 'Sua personagem', 'O jogador', 'A jogadora', 'Você'])
def test_reserved_player_reference_cannot_become_npc_reporter(actor):
    with pytest.raises(SceneProposalError):
        check(actor + ' ergue os olhos para você e fala em voz baixa: “A água avança.”',
              npcs=(actor,))


@pytest.mark.parametrize('players,npcs', [
    (('Registro',), ('Mara',)),
    (('Bancada',), ('Mara',)),
    ((), ('Mara', 'Registro')),
])
def test_person_alias_in_object_frame_invalidates_pronoun_proof(players, npcs):
    with pytest.raises(SceneProposalError):
        check('Mara se inclina sobre a bancada baixa, sem tocar no registro; '
              'o registro permanece seco, ainda no mesmo lugar. '
              'Ela ergue os olhos para você e fala em voz baixa: “A água avança.”',
              players=players, npcs=npcs)


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe', [False, True])
async def test_recorded_warning_commit_restart_and_replay_stay_atomic(tmp_path, monkeypatch, unsafe):
    def forbidden_roll(*_args, **_kwargs):
        pytest.fail('a declared wait and its replay may not roll')
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden_roll)
    db = tmp_path / 'gaze.sqlite3'
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, 'gaze', initial_state=state())
    text = OBSERVED['n'] + (' Você promete ajudar.' if unsafe else '')
    config, gateway = config_and_gateway(text, tuple(OBSERVED['realized_effects']), OBSERVED['q'])
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id='gaze', operation_id='gaze-1', player_input='Aguardo',
        config=config, deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    chunks = []
    async def deliver(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id='gaze-1', gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=deliver,
    )
    restarted = SQLitePersistence(db)
    snapshot = await read_campaign_source_snapshot(restarted, 'gaze')
    assert len(gateway.requests) == 1
    if unsafe:
        assert result.status == 'failed' and result.error_code == 'campaign_source_policy_failed'
        assert snapshot.current_turn == 0 and snapshot.progression.record == 'threatened'
        assert not snapshot.sources and not chunks
    else:
        assert result.status == 'completed'
        assert snapshot.current_turn == 1 and snapshot.progression.record == 'warned'
        replay = await execute_campaign_source_turn(
            store=restarted, capsule=prepared.capsule, operation_id='gaze-1', gateway=gateway,
            deadline=utc_now() - timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=deliver,
        )
        assert replay.status == 'completed' and replay.envelope == result.envelope
        assert len(gateway.requests) == len(chunks) == 1
