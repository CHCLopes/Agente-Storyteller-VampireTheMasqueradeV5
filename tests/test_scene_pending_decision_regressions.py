"""L10: awaiting the player's decision does not assert a completed choice."""
from datetime import timedelta

import pytest

from api import rules_service
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state


OBSERVED = 'Mara lança um olhar para a bancada baixa, onde o registro permanece ameaçado, mas ainda intacto. “Você pode me ajudar a mantê-lo longe de qualquer umidade. O risco agora é danificar o registro durante o manuseio; se precisarmos movê-lo, a superfície seca na Galeria é o lugar seguro para apoiá-lo.” Ela volta a atenção para o objeto, mantendo as mãos afastadas até que você decida como proceder.'
QUESTION = 'Que providência você toma diante do risco ao registro?'
OBSERVED_L55 = 'Mara aponta para o registro ameaçado na bancada baixa do Arquivo, entre papéis e sinais de umidade próxima. “A tarefa é descobrir o que ainda pode ser preservado antes que a água alcance suas páginas.” Ela indica a Galeria com um gesto contido. “A superfície seca fica ali; pode servir para proteger o registro, se você decidir como agir.”'
OBSERVED_L44 = 'Você espera no Arquivo enquanto a infiltração alcança a bancada baixa. A água atinge o registro, que agora está molhado, e parte do conteúdo fica em risco. O registro permanece sobre a bancada. Mara observa a umidade avançar, tensa, e diz: “A água chegou ao registro. Ainda há algo a fazer, se você decidir agir.”'
OBSERVED_L43 = 'Mara volta-se para você, mantendo a atenção na bancada baixa. “O registro ainda corre risco aqui no Arquivo. Se for ajudar, leve em conta que há uma superfície seca na Galeria; é lá que o objeto pode ficar protegido enquanto você decide como proceder.” O registro permanece na bancada baixa, sem mudar de posição.'


def check(text, players=()):
    return validate_source_proposal(
        {'n': text, 'q': QUESTION}, facts=(),
        current_scene=SceneState(location='Arquivo', npcs_present=('Mara',)),
        player_input='Como posso ajudar?', player_aliases=players, npc_aliases=('Mara',))


def test_exact_live_response_does_not_execute_a_choice():
    assert check(OBSERVED).narrative == OBSERVED

def test_conditional_how_to_act_keeps_choice_open():
    assert check(OBSERVED_L55).narrative == OBSERVED_L55


def test_while_deciding_how_to_proceed_keeps_choice_open():
    assert check(OBSERVED_L43).narrative == OBSERVED_L43


def test_conditional_deciding_to_act_does_not_make_the_choice():
    result = validate_source_proposal({'n': OBSERVED_L44, 'q': 'O que você faz agora?'},
        facts=(), current_scene=SceneState(location='Arquivo', npcs_present=('Mara',)),
        player_input='Espero', npc_aliases=('Mara',))
    assert result.narrative == OBSERVED_L44


@pytest.mark.parametrize('text', [
    OBSERVED_L44 + ' Você decide agir.',
    OBSERVED_L44 + ' Você abre a porta.',
    OBSERVED_L44.replace('se você decidir agir', 'você decidir agir'),
    OBSERVED_L44.replace('se você decidir agir', 'se você decidir agir e abre a porta'),
])
def test_conditional_decision_never_authorizes_a_later_action(text):
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        validate_source_proposal({'n': text, 'q': 'O que você faz agora?'}, facts=(),
            current_scene=SceneState(location='Arquivo', npcs_present=('Mara',)),
            player_input='Espero', npc_aliases=('Mara',))


@pytest.mark.parametrize('text', [
    OBSERVED_L43 + ' Você decide partir.',
    OBSERVED_L43 + ' Você abre a porta.',
    OBSERVED_L43.replace('decide como proceder', 'decide ajudar'),
    OBSERVED_L43.replace('decide como proceder', 'decide como proceder e abre a porta'),
    OBSERVED_L43.replace('enquanto você decide', 'você decide'),
    OBSERVED_L55+' Você abre a porta.',
    OBSERVED_L55.replace('se você decidir como agir', 'você decidir como agir'),
    OBSERVED_L55.replace('se você decidir como agir', 'se você decidir como agir e abre a porta'),
])
def test_while_scope_never_waives_a_concrete_choice_or_later_action(text):
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('suffix', [
    'Você decide como proceder.',
    'Até que você decida como proceder, você decide ajudar.',
    'Até que você decida como proceder, você abre a porta.',
    'Até que você decida como proceder, Mara obriga você a partir.',
    'Você decida como proceder.',
])
def test_actual_choices_and_later_actions_are_not_authorized(suffix):
    text = 'Mara aguarda junto ao registro na bancada. O registro permanece ameaçado pela umidade no Arquivo, enquanto as gotas caem ao redor da bancada baixa. ' + suffix
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('alias', ['Neófito', 'Violeta'])
def test_registered_alias_has_the_same_pending_scope(alias):
    text = f'O registro permanece ameaçado pela umidade no Arquivo. Mara aguarda junto ao registro na bancada até que {alias} decida como proceder.'
    assert check(text, (alias,)).narrative == text
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text + f' {alias} decide partir.', (alias,))


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe', [False, True])
@pytest.mark.parametrize('observed', [OBSERVED, OBSERVED_L43,
    OBSERVED_L43.replace('enquanto você decide como proceder', 'se você decidir agir'), OBSERVED_L55])
async def test_r01_commit_restart_replay_and_unsafe_rollback(tmp_path, monkeypatch, unsafe, observed):
    def forbidden_roll(*_a, **_kw):
        pytest.fail('help question/replay may not roll')
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden_roll)
    db = tmp_path / 'pending.sqlite3'
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, 'pending', initial_state=state())
    text = observed + (' Você decide partir.' if unsafe else '')
    config, gateway = config_and_gateway(text, ('mara.replies.to_task', 'campaign.knows.safe_surface'), QUESTION)
    p = await prepare_campaign_source_player_action(
        store=store, session_id='pending', operation_id='pending-1', player_input='Como posso ajudar?',
        config=config, deadline=utc_now()+timedelta(seconds=60), cancellation=CancellationToken())
    chunks = []
    async def deliver(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=p.capsule, operation_id='pending-1', gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60), cancellation=CancellationToken(), on_chunk=deliver)
    restarted = SQLitePersistence(db)
    snapshot = await read_campaign_source_snapshot(restarted, 'pending')
    assert snapshot.progression.record == 'threatened' and snapshot.progression.outcome is None
    if unsafe:
        assert result.status == 'failed' and result.error_code == 'campaign_source_policy_failed'
        assert snapshot.current_turn == 0 and not snapshot.sources and not chunks
    else:
        assert result.status == 'completed' and snapshot.current_turn == 1
        replay = await execute_campaign_source_turn(
            store=restarted, capsule=p.capsule, operation_id='pending-1', gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=deliver)
        assert replay.status == 'completed' and replay.envelope == result.envelope
        assert len(chunks) == 1
    assert len(gateway.requests) == 1
