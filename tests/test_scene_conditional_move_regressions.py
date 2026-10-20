"""HYP-007-L8: needing to move an object is not an executed move."""
import pytest
from datetime import timedelta

from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence


OBSERVED = {
    'n': 'Mara lança um olhar para a bancada baixa, onde o registro permanece ameaçado, e responde em voz baixa: “O risco é maior se a umidade alcançar o registro; qualquer manuseio descuidado pode piorar a situação. Se você precisar movê-lo, a superfície seca na Galeria é o lugar seguro para apoiá-lo. Por enquanto, o registro continua na bancada baixa do Arquivo.” Ela mantém as mãos afastadas, aguardando sua decisão, sem alterar a posição do registro.',
    'q': 'Que ação você toma diante do risco ao registro?',
}
OBSERVED_L37 = 'Mara volta o olhar para a bancada baixa, onde o registro continua ameaçado. “O risco atual é que qualquer umidade comprometa o registro antes que possamos protegê-lo. Se você precisar manipulá-lo, a superfície seca na Galeria é o lugar seguro para apoiá-lo.” A advertência vem baixa e precisa, enquanto o Arquivo permanece calmo ao redor. O registro permanece na bancada baixa do Arquivo; nada o desloca ainda.'


def check(text, *, players=()):
    return validate_source_proposal(
        {'n': text, 'q': OBSERVED['q']}, facts=(),
        current_scene=SceneState(location='Arquivo', npcs_present=('Mara',)),
        player_input='Como posso ajudar?', player_aliases=players, npc_aliases=('Mara',))


def test_exact_l8_conditional_is_admitted_without_rewriting():
    result = check(OBSERVED['n'])
    assert result.narrative == OBSERVED['n']


def test_exact_l37_conditional_is_admitted_without_rewriting():
    assert check(OBSERVED_L37).narrative == OBSERVED_L37


@pytest.mark.parametrize('conditional', [
    'Caso você precisar movê-lo,',
    'Se você não precisar movê-lo,',
    'Se você precisar movê-la,',
    'Se você precisar movê-los,',
    'Se você precisar manipulá-lo,',
    'Caso você precisar manipulá-la,',
])
def test_bounded_conditional_need_does_not_execute_an_action(conditional):
    text = OBSERVED['n'].replace('Se você precisar movê-lo,', conditional)
    assert check(text).narrative == text


@pytest.mark.parametrize('replacement', [
    'Você precisa movê-lo.',
    'Você move o registro.',
    'Você move-o para a Galeria.',
    'Se você precisar movê-lo, você move o registro.',
    'Se você precisar movê-lo, você abre a porta.',
    'Se você precisar movê-lo, você promete ajudar.',
    'Se você precisar movê-lo, Mara obriga você a movê-lo.',
    'Você precisa manipulá-lo.',
    'Você manipula o registro.',
    'Se você precisar manipulá-lo, você manipula o registro.',
    'Se você precisar manipulá-lo, você abre a porta.',
])
def test_conditional_does_not_authorize_actual_or_subsequent_player_action(replacement):
    text = OBSERVED['n'].replace('Se você precisar movê-lo,', replacement)
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('alias', ['Neófito', 'Violeta'])
def test_registered_player_alias_keeps_the_same_conditional_scope(alias):
    text = OBSERVED['n'].replace('Se você precisar movê-lo,', f'Se {alias} precisar movê-lo,')
    # Isolate the conditional from the separate conservative pronoun gate.
    # The exact live response remains unchanged in its dedicated regression.
    text = text.replace('Ela mantém', 'Mara mantém')
    assert check(text, players=(alias,)).narrative == text
    unsafe = text + f' {alias} move o registro.'
    with pytest.raises(SceneProposalError):
        check(unsafe, players=(alias,))


@pytest.mark.parametrize('alias', ['Neófito', 'Violeta'])
def test_conditional_does_not_relax_ambiguous_later_pronoun_policy(alias):
    text = OBSERVED['n'].replace('Se você precisar movê-lo,', f'Se {alias} precisar movê-lo,')
    with pytest.raises(SceneProposalError) as caught:
        check(text, players=(alias,))
    assert caught.value.evidence['subject'] == 'ambiguous_pronoun'
    assert caught.value.evidence['unauthorized_concepts'] == ['wait']


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe', [False, True])
@pytest.mark.parametrize('observed',[OBSERVED['n'],OBSERVED_L37])
async def test_exact_r01_commit_restart_replay_and_real_move_rollback(tmp_path, monkeypatch, unsafe, observed):
    def forbidden_roll(*_args, **_kwargs):
        pytest.fail('help question and replay may not roll')
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden_roll)
    db = tmp_path / 'conditional.sqlite3'
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, 'conditional', initial_state=state())
    text = observed + (' Você move o registro.' if unsafe else '')
    config, gateway = config_and_gateway(text, ('mara.replies.to_task', 'campaign.knows.safe_surface'), OBSERVED['q'])
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id='conditional', operation_id='conditional-1',
        player_input='Como posso ajudar?', config=config,
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken())
    chunks = []
    async def deliver(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id='conditional-1', gateway=gateway,
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=deliver)
    restarted = SQLitePersistence(db)
    snapshot = await read_campaign_source_snapshot(restarted, 'conditional')
    assert snapshot.progression.record == 'threatened' and snapshot.progression.outcome is None
    if unsafe:
        assert result.status == 'failed' and result.error_code == 'campaign_source_policy_failed'
        assert snapshot.current_turn == 0 and not snapshot.sources and not chunks
    else:
        assert result.status == 'completed' and snapshot.current_turn == 1
        replay = await execute_campaign_source_turn(
            store=restarted, capsule=prepared.capsule, operation_id='conditional-1', gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=deliver)
        assert replay.status == 'completed' and replay.envelope == result.envelope
        assert len(chunks) == 1
    assert len(gateway.requests) == 1
